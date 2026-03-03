import streamlit as st
import pandas as pd
from sqlalchemy import text
import time

st.set_page_config(
    page_title="BookTracker → eBook Sync",
    page_icon="🔄",
    layout="wide",
)

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,700;1,9..144,300&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Mono', monospace;
}
h1, h2, h3 { font-family: 'Fraunces', serif; }

.metric-card {
    background: #1a1a1a;
    border: 1px solid #2e2e2e;
    border-radius: 8px;
    padding: 1.2rem 1.5rem;
    text-align: center;
}
.metric-card .label { font-size: 0.72rem; color: #888; letter-spacing: 0.12em; text-transform: uppercase; }
.metric-card .value { font-size: 2rem; font-family: 'Fraunces', serif; color: #c8b88a; margin-top: 0.2rem; }

.log-box {
    background: #111;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 1rem 1.2rem;
    font-size: 0.78rem;
    max-height: 340px;
    overflow-y: auto;
    color: #aaa;
    line-height: 1.8;
}
.log-ok   { color: #7ec8a0; }
.log-warn { color: #e8c07a; }
.log-err  { color: #e07a7a; }
.log-info { color: #7aace0; }

div[data-testid="stButton"] button {
    background: #c8b88a;
    color: #0f0f0f;
    border: none;
    border-radius: 4px;
    font-family: 'DM Mono', monospace;
    font-weight: 500;
    letter-spacing: 0.06em;
    padding: 0.55rem 1.4rem;
}
div[data-testid="stButton"] button:hover { background: #ddd0a8; }

.section-title {
    font-family: 'Fraunces', serif;
    font-size: 1.1rem;
    color: #c8b88a;
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 0.4rem;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ── DB Connections ────────────────────────────────────────────────────────────
@st.cache_resource
def connect_booktracker_db():
    try:
        return st.connection("mysql", type="sql")
    except Exception as e:
        st.error(f"Error connecting to BookTracker DB: {e}")
        st.stop()

@st.cache_resource
def connect_ebook_db():
    try:
        return st.connection("ebook", type="sql")
    except Exception as e:
        st.error(f"Error connecting to eBook Store DB: {e}")
        st.stop()

conn_booktracker = connect_booktracker_db()
conn_ebook       = connect_ebook_db()

def normalize(val: str) -> str:
    return val.strip().lower() if val else ""

def is_empty(val):
    if pd.isna(val): return True
    if val is None: return True
    if str(val).strip() == "": return True
    return False

# ── Helper: Book Sync Logic ───────────────────────────────────────────────────
def show_book_sync():
    st.markdown("# 📚 BookTracker → eBook Store")
    st.markdown("<p style='color:#666; font-size:0.85rem; margin-top:-0.6rem;'>Sync book_id · sku (from isbn) · subjects from BookTracker into your eBook Store</p>", unsafe_allow_html=True)
    st.divider()

    def fetch_booktracker_books():
        return conn_booktracker.query("SELECT book_id, title, isbn, subject FROM books", ttl=0)

    def fetch_ebook_products():
        return conn_ebook.query("SELECT id, book_id, title, sku FROM products", ttl=0)

    def fetch_ebook_subjects():
        return conn_ebook.query("SELECT id, name FROM subjects", ttl=0)

    def fetch_product_subjects():
        return conn_ebook.query("SELECT product_id, subject_id FROM product_subjects", ttl=0)

    def get_or_create_subject(session, subject_name: str, existing_subjects: dict) -> int | None:
        name = subject_name.strip()
        if not name: return None
        key = name.lower()
        if key in existing_subjects: return existing_subjects[key]
        slug = name.lower().replace(" ", "-").replace("/", "-")
        result = session.execute(
            text("INSERT INTO subjects (name, slug, status, created_at) VALUES (:name, :slug, 'active', NOW())"),
            {"name": name, "slug": slug}
        )
        new_id = result.lastrowid
        existing_subjects[key] = new_id
        return new_id

    # UI: Preview
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown('<div class="section-title">BookTracker — Source</div>', unsafe_allow_html=True)
        if st.button("🔍 Load Preview", key="load_bt"):
            with st.spinner("Fetching…"):
                st.session_state["df_bt"] = fetch_booktracker_books()
        if "df_bt" in st.session_state:
            st.dataframe(st.session_state["df_bt"], use_container_width=True, height=240)

    with col_r:
        st.markdown('<div class="section-title">eBook Store — Destination</div>', unsafe_allow_html=True)
        if st.button("🔍 Load Preview", key="load_eb"):
            with st.spinner("Fetching…"):
                st.session_state["df_eb"] = fetch_ebook_products()
        if "df_eb" in st.session_state:
            st.dataframe(st.session_state["df_eb"], use_container_width=True, height=240)

    st.divider()

    # UI: Analysis
    st.markdown('<div class="section-title">Pre-flight Analysis</div>', unsafe_allow_html=True)
    if st.button("🧪 Run Dry Analysis"):
        with st.spinner("Analysing matches…"):
            df_bt = fetch_booktracker_books()
            df_eb = fetch_ebook_products()
            bt_map = {normalize(r.title): r for _, r in df_bt.iterrows()}
            eb_map = {normalize(r.title): r for _, r in df_eb.iterrows()}
            matched, unmatched_bt, unmatched_eb = [], [], []
            for norm_title, bt_row in bt_map.items():
                if norm_title in eb_map:
                    matched.append({
                        "BookTracker Title": bt_row["title"],
                        "BT book_id": bt_row["book_id"],
                        "BT isbn (→ SKU)": bt_row["isbn"],
                        "BT subject": bt_row["subject"],
                        "EB id (PK)": eb_map[norm_title]["id"],
                        "EB book_id (current)": eb_map[norm_title]["book_id"],
                        "EB sku (current)": eb_map[norm_title]["sku"],
                    })
                else: unmatched_bt.append(bt_row["title"])
            for norm_title, eb_row in eb_map.items():
                if norm_title not in bt_map: unmatched_eb.append(eb_row["title"])
            st.session_state["analysis"] = {"matched": matched, "unmatched_bt": unmatched_bt, "unmatched_eb": unmatched_eb}

    if "analysis" in st.session_state:
        a = st.session_state["analysis"]
        c1, c2, c3 = st.columns(3)
        for col, label, val, color in [(c1, "Matched", len(a["matched"]), "#7ec8a0"), (c2, "Only in BookTracker", len(a["unmatched_bt"]), "#e8c07a"), (c3, "Only in eBook Store", len(a["unmatched_eb"]), "#7aace0")]:
            col.markdown(f'<div class="metric-card"><div class="label">{label}</div><div class="value" style="color:{color}">{val}</div></div>', unsafe_allow_html=True)
        if a["matched"]:
            st.markdown("**Matched books (will be synced)**")
            st.dataframe(pd.DataFrame(a["matched"]), use_container_width=True, height=220)

    st.divider()

    # UI: Options & Sync
    st.markdown('<div class="section-title">Sync Options</div>', unsafe_allow_html=True)
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        st.markdown("**Data Fields**")
        update_book_id = st.checkbox("Sync book_id", value=True)
        update_sku = st.checkbox("Sync SKU", value=True)
        sync_subjects = st.checkbox("Sync subjects", value=True)
    with col_opt2:
        st.markdown("**Overwrite Settings**")
        overwrite_book_id = st.checkbox("Overwrite existing book_id", value=False)
        overwrite_sku = st.checkbox("Overwrite existing SKU", value=False)
        overwrite_subjects = st.checkbox("Overwrite existing subjects", value=False, help="If checked, old subject links for matched books will be deleted first")

    if st.button("🚀 Start Sync", type="primary"):
        if "analysis" not in st.session_state or not st.session_state["analysis"]["matched"]:
            st.warning("Run the Dry Analysis first.")
        else:
            matched_rows = st.session_state["analysis"]["matched"]
            log_lines, ok, skip, err, subj_link = [], 0, 0, 0, 0
            log_placeholder = st.empty()
            prog = st.progress(0)
            
            df_subj = fetch_ebook_subjects()
            existing_subjects = {row["name"].lower(): row["id"] for _, row in df_subj.iterrows()}
            df_ps = fetch_product_subjects()
            existing_links = set(zip(df_ps["product_id"], df_ps["subject_id"]))
            df_eb = fetch_ebook_products()
            eb_lookup = {normalize(r["title"]): r for _, r in df_eb.iterrows()}

            try:
                with conn_ebook.session as s:
                    for i, row in enumerate(matched_rows):
                        title, bt_book_id, bt_isbn, bt_subject = row["BookTracker Title"], row["BT book_id"], row["BT isbn (→ SKU)"], row["BT subject"]
                        eb_current = eb_lookup.get(normalize(title))
                        
                        if eb_current is None: # Fix: Truth value of Series check
                            continue
                            
                        product_pk = int(eb_current["id"])
                        updates = {}
                        if update_book_id and (overwrite_book_id or is_empty(eb_current["book_id"])): updates["book_id"] = int(bt_book_id)
                        if update_sku and (overwrite_sku or is_empty(eb_current["sku"])): updates["sku"] = bt_isbn
                        
                        if updates:
                            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
                            updates["_title"] = title
                            s.execute(text(f"UPDATE products SET {set_clause} WHERE title = :_title"), updates)
                            log_lines.append(f"<span class='log-ok'>✔ UPDATED [{title}]</span><br>")
                            ok += 1
                        else: skip += 1

                        if sync_subjects and bt_subject:
                            # Handle Overwrite Subjects
                            if overwrite_subjects:
                                s.execute(text("DELETE FROM product_subjects WHERE product_id = :pid"), {"pid": product_pk})
                                # Clear local link cache for this product
                                existing_links = {link for link in existing_links if link[0] != product_pk}

                            for subj_name in [s2.strip() for s2 in bt_subject.replace(";", ",").split(",") if s2.strip()]:
                                subj_id = get_or_create_subject(s, subj_name, existing_subjects)
                                if subj_id and (product_pk, subj_id) not in existing_links:
                                    s.execute(text("INSERT INTO product_subjects (product_id, subject_id) VALUES (:pid, :sid)"), {"pid": product_pk, "sid": subj_id})
                                    existing_links.add((product_pk, subj_id))
                                    subj_link += 1
                        
                        prog.progress((i + 1) / len(matched_rows))
                        log_placeholder.markdown(f"<div class='log-box'>{''.join(log_lines[-50:])}</div>", unsafe_allow_html=True)
                    s.commit()
                    st.success("Sync completed!")
            except Exception as e:
                st.error(f"Sync failed: {e}")

# ── Helper: Author Sync Logic ──────────────────────────────────────────────────
def show_author_sync():
    st.markdown("# ✍️ Author Data Importer")
    st.markdown("<p style='color:#666; font-size:0.85rem; margin-top:-0.6rem;'>Sync Bio & Photos from BookTracker to eBook Store</p>", unsafe_allow_html=True)
    st.divider()

    OLD_PATH_BASE = "/home/rishabhvyas/mis_files/author_photo/"
    NEW_PATH_BASE = "/home/rishabhvyas/EbookApp/Backend/uploads/authors/"

    def fetch_bt_authors(): return conn_booktracker.query("SELECT author_id, name, about_author, author_photo FROM authors", ttl=0)
    def fetch_eb_authors(): return conn_ebook.query("SELECT id, name, profile_image, bio FROM authors", ttl=0)
    def transform_path(old_path):
        if pd.isna(old_path) or str(old_path).strip() == "": return None
        return str(old_path).replace(OLD_PATH_BASE, NEW_PATH_BASE)

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown('<div class="section-title">Source: BookTracker</div>', unsafe_allow_html=True)
        if st.button("🔍 Load BT Authors"): st.session_state["df_bt_auth"] = fetch_bt_authors()
        if "df_bt_auth" in st.session_state: st.dataframe(st.session_state["df_bt_auth"], use_container_width=True, height=200)

    with col_r:
        st.markdown('<div class="section-title">Dest: eBook Store</div>', unsafe_allow_html=True)
        if st.button("🔍 Load EB Authors"): st.session_state["df_eb_auth"] = fetch_eb_authors()
        if "df_eb_auth" in st.session_state: st.dataframe(st.session_state["df_eb_auth"], use_container_width=True, height=200)

    st.divider()
    if st.button("🧪 Run Analysis"):
        df_bt, df_eb = fetch_bt_authors(), fetch_eb_authors()
        bt_map = {normalize(r["name"]): r for _, r in df_bt.iterrows()}
        eb_map = {normalize(r["name"]): r for _, r in df_eb.iterrows()}
        matches = []
        for name_key, bt_row in bt_map.items():
            if name_key in eb_map:
                eb_row = eb_map[name_key]
                if pd.notna(bt_row["about_author"]) or pd.notna(bt_row["author_photo"]):
                    matches.append({"Name": bt_row["name"], "EB_ID": eb_row["id"], "New_Mapped_Path": transform_path(bt_row["author_photo"]), "Full_Bio": bt_row["about_author"]})
        st.session_state["author_matches"] = matches

    if "author_matches" in st.session_state:
        st.dataframe(pd.DataFrame(st.session_state["author_matches"]), use_container_width=True)

    st.divider()
    c1, c2 = st.columns(2)
    overwrite_bio = c1.checkbox("Overwrite existing Bio?", value=False)
    overwrite_img = c2.checkbox("Overwrite existing Profile Image?", value=False)

    if st.button("🚀 Start Final Sync", type="primary"):
        if "author_matches" not in st.session_state: st.error("Run Analysis first.")
        else:
            matches, log_lines, updated, skipped = st.session_state["author_matches"], [], 0, 0
            log_placeholder, prog = st.empty(), st.progress(0)
            eb_state = {r["id"]: r for _, r in fetch_eb_authors().iterrows()}
            try:
                with conn_ebook.session as s:
                    for i, row in enumerate(matches):
                        auth_id, curr_eb, update_payload = row["EB_ID"], eb_state.get(row["EB_ID"]), {}
                        
                        if curr_eb is None: continue # Fix: Safety check

                        if pd.notna(row["Full_Bio"]) and (overwrite_bio or is_empty(curr_eb.get("bio"))): update_payload["bio"] = row["Full_Bio"]
                        if row["New_Mapped_Path"] and (overwrite_img or is_empty(curr_eb.get("profile_image"))): update_payload["profile_image"] = row["New_Mapped_Path"]
                        
                        if update_payload:
                            set_stmt = ", ".join([f"{k} = :{k}" for k in update_payload])
                            update_payload["aid"] = auth_id
                            s.execute(text(f"UPDATE authors SET {set_stmt} WHERE id = :aid"), update_payload)
                            log_lines.append(f"<span class='log-ok'>✔ {row['Name']} updated</span><br>")
                            updated += 1
                        else: skipped += 1
                        prog.progress((i + 1) / len(matches))
                        log_placeholder.markdown(f"<div class='log-box'>{''.join(log_lines[-50:])}</div>", unsafe_allow_html=True)
                    s.commit()
                    st.success(f"Sync Complete! {updated} updated, {skipped} skipped.")
            except Exception as e: st.error(f"Error: {e}")

# ── Main Navigation ──────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Database Transfer")
page = st.sidebar.radio("Select Feature", ["📚 Book Sync", "✍️ Author Sync"])

if page == "📚 Book Sync":
    show_book_sync()
else:
    show_author_sync()
