import streamlit as st
import pandas as pd
from sqlalchemy import text
import time

st.set_page_config(
    page_title="BookTracker → eBook Store Sync",
    page_icon="📚",
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

# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_booktracker_books():
    """Fetch all books with isbn and subject from booktracker."""
    return conn_booktracker.query(
        "SELECT book_id, title, subject FROM books",
        ttl=0
    )

def fetch_ebook_products():
    """Fetch all products from ebook_store, including the real PK (id)."""
    return conn_ebook.query(
        "SELECT id, book_id, title FROM products",
        ttl=0
    )

def fetch_ebook_subjects():
    """Fetch existing subjects from ebook_store."""
    return conn_ebook.query(
        "SELECT id, name FROM subjects",
        ttl=0
    )

def fetch_product_subjects():
    """Fetch existing product-subject links."""
    return conn_ebook.query(
        "SELECT product_id, subject_id FROM product_subjects",
        ttl=0
    )

def normalize(title: str) -> str:
    return title.strip().lower() if title else ""

def get_or_create_subject(session, subject_name: str, existing_subjects: dict) -> int | None:
    """Return subject id, creating it if necessary. Updates existing_subjects in-place."""
    name = subject_name.strip()
    if not name:
        return None
    key = name.lower()
    if key in existing_subjects:
        return existing_subjects[key]
    slug = name.lower().replace(" ", "-").replace("/", "-")
    result = session.execute(
        text("""
            INSERT INTO subjects (name, slug, status, created_at)
            VALUES (:name, :slug, 'active', NOW())
        """),
        {"name": name, "slug": slug}
    )
    new_id = result.lastrowid
    existing_subjects[key] = new_id
    return new_id

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("# 📚 BookTracker → eBook Store")
st.markdown("<p style='color:#666; font-size:0.85rem; margin-top:-0.6rem;'>Sync book_id · isbn · subjects from BookTracker into your eBook Store</p>", unsafe_allow_html=True)
st.divider()

# Preview section
col_l, col_r = st.columns(2)

with col_l:
    st.markdown('<div class="section-title">BookTracker — Source</div>', unsafe_allow_html=True)
    if st.button("🔍 Load Preview", key="load_bt"):
        with st.spinner("Fetching…"):
            df_bt = fetch_booktracker_books()
            st.session_state["df_bt"] = df_bt

    if "df_bt" in st.session_state:
        df_bt = st.session_state["df_bt"]
        st.dataframe(df_bt, use_container_width=True, height=240)
        st.caption(f"{len(df_bt)} books in BookTracker")

with col_r:
    st.markdown('<div class="section-title">eBook Store — Destination</div>', unsafe_allow_html=True)
    if st.button("🔍 Load Preview", key="load_eb"):
        with st.spinner("Fetching…"):
            df_eb = fetch_ebook_products()
            st.session_state["df_eb"] = df_eb

    if "df_eb" in st.session_state:
        df_eb = st.session_state["df_eb"]
        st.dataframe(df_eb, use_container_width=True, height=240)
        st.caption(f"{len(df_eb)} products in eBook Store")

st.divider()

# ── Dry Run / Analysis ────────────────────────────────────────────────────────
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
                    "BT subject": bt_row["subject"],
                    "EB id (PK)": eb_map[norm_title]["id"],
                    "EB book_id (current)": eb_map[norm_title]["book_id"],
                })
            else:
                unmatched_bt.append(bt_row["title"])

        for norm_title, eb_row in eb_map.items():
            if norm_title not in bt_map:
                unmatched_eb.append(eb_row["title"])

        st.session_state["analysis"] = {
            "matched": matched,
            "unmatched_bt": unmatched_bt,
            "unmatched_eb": unmatched_eb,
        }

if "analysis" in st.session_state:
    a = st.session_state["analysis"]
    c1, c2, c3 = st.columns(3)
    for col, label, val, color in [
        (c1, "Matched", len(a["matched"]), "#7ec8a0"),
        (c2, "Only in BookTracker", len(a["unmatched_bt"]), "#e8c07a"),
        (c3, "Only in eBook Store", len(a["unmatched_eb"]), "#7aace0"),
    ]:
        col.markdown(f"""
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value" style="color:{color}">{val}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")
    if a["matched"]:
        st.markdown("**Matched books (will be synced)**")
        st.dataframe(pd.DataFrame(a["matched"]), use_container_width=True, height=220)
    if a["unmatched_bt"]:
        with st.expander(f"⚠️ {len(a['unmatched_bt'])} BookTracker books with NO match in eBook Store"):
            st.write(a["unmatched_bt"])
    if a["unmatched_eb"]:
        with st.expander(f"ℹ️ {len(a['unmatched_eb'])} eBook Store products with NO match in BookTracker"):
            st.write(a["unmatched_eb"])

st.divider()

# ── Sync Options ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Sync Options</div>', unsafe_allow_html=True)

col_opt1, col_opt2 = st.columns(2)
with col_opt1:
    update_book_id = st.checkbox("Update book_id", value=True, help="Overwrite book_id in products with BookTracker's value")
    sync_subjects  = st.checkbox("Sync subjects",  value=True, help="Add subject tags to product_subjects table")
with col_opt2:
    overwrite_existing = st.checkbox("Overwrite existing book_id", value=False,
                                      help="If unchecked, only fills NULL/empty fields")

st.divider()

# ── Execute Sync ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Execute Sync</div>', unsafe_allow_html=True)

if st.button("🚀 Start Sync", type="primary"):

    if "analysis" not in st.session_state or not st.session_state["analysis"]["matched"]:
        st.warning("Run the Dry Analysis first to identify matches.")
    else:
        matched_rows = st.session_state["analysis"]["matched"]

        log_lines  = []
        ok = skip = err = subj_new = subj_link = 0

        log_placeholder = st.empty()
        prog = st.progress(0)
        total = len(matched_rows)

        # Pre-fetch current subjects from ebook store
        df_subj = fetch_ebook_subjects()
        existing_subjects = {row["name"].lower(): row["id"] for _, row in df_subj.iterrows()}

        # Pre-fetch product_subjects links
        df_ps = fetch_product_subjects()
        existing_links = set(zip(df_ps["product_id"], df_ps["subject_id"]))

        # Re-fetch ebook products for current book_id/isbn
        df_eb = fetch_ebook_products()
        eb_lookup = {normalize(r["title"]): r for _, r in df_eb.iterrows()}

        def render_log():
            html = "<div class='log-box'>" + "".join(log_lines[-80:]) + "</div>"
            log_placeholder.markdown(html, unsafe_allow_html=True)

        try:
            with conn_ebook.session as s:
                for i, row in enumerate(matched_rows):
                    title       = row["BookTracker Title"]
                    bt_book_id  = row["BT book_id"]
                    bt_subject  = row["BT subject"]
                    eb_current  = eb_lookup.get(normalize(title))

                    if eb_current is None:
                        log_lines.append(f"<span class='log-warn'>⚠ SKIP  [{title}] — not found in current products table</span><br>")
                        skip += 1
                        continue

                    # Use the real PK (products.id) for the FK in product_subjects
                    product_pk = int(eb_current["id"])

                    # Build UPDATE fields
                    updates = {}
                    if update_book_id:
                        if overwrite_existing or not eb_current["book_id"]:
                            updates["book_id"] = int(bt_book_id)

                    if updates:
                        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
                        updates["_title"] = title
                        s.execute(
                            text(f"UPDATE products SET {set_clause} WHERE title = :_title"),
                            updates
                        )
                        log_lines.append(f"<span class='log-ok'>✔ UPDATED [{title}] — {', '.join(k for k in updates if k != '_title')}</span><br>")
                        ok += 1
                    else:
                        log_lines.append(f"<span class='log-info'>→ SKIP   [{title}] — no fields to update (overwrite off)</span><br>")
                        skip += 1

                    # Subjects
                    if sync_subjects and bt_subject:
                        raw_subjects = [s2.strip() for s2 in bt_subject.replace(";", ",").split(",") if s2.strip()]
                        for subj_name in raw_subjects:
                            subj_id = get_or_create_subject(s, subj_name, existing_subjects)
                            if subj_id is None:
                                continue
                            if (product_pk, subj_id) not in existing_links:
                                s.execute(
                                    text("INSERT INTO product_subjects (product_id, subject_id) VALUES (:pid, :sid)"),
                                    {"pid": product_pk, "sid": subj_id}
                                )
                                existing_links.add((product_pk, subj_id))
                                subj_link += 1
                                log_lines.append(f"<span class='log-info'>  ↳ linked subject [{subj_name}] to product pk={product_pk}</span><br>")
                            if subj_id not in [v for k, v in existing_subjects.items()]:
                                subj_new += 1

                    prog.progress((i + 1) / total)
                    render_log()

                s.commit()
                log_lines.append("<br><span class='log-ok'>✅ COMMIT successful</span><br>")
                render_log()

        except Exception as e:
            err += 1
            log_lines.append(f"<br><span class='log-err'>❌ FATAL ERROR: {e}</span><br>")
            render_log()
            st.error(f"Sync failed: {e}")

        # Summary
        st.divider()
        st.markdown('<div class="section-title">Sync Summary</div>', unsafe_allow_html=True)
        s1, s2, s3, s4 = st.columns(4)
        for col, label, val, color in [
            (s1, "Updated",        ok,        "#7ec8a0"),
            (s2, "Skipped",        skip,      "#e8c07a"),
            (s3, "Subject Links",  subj_link, "#7aace0"),
            (s4, "Errors",         err,       "#e07a7a"),
        ]:
            col.markdown(f"""
            <div class="metric-card">
                <div class="label">{label}</div>
                <div class="value" style="color:{color}">{val}</div>
            </div>""", unsafe_allow_html=True)

        if err == 0:
            st.success("Sync completed successfully!", icon="✅")
            st.toast("Sync completed!", icon="✅")
        else:
            st.error("Sync completed with errors. Check the log above.")
            st.toast("Sync completed with errors", icon="❌")