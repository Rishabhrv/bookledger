import streamlit as st
import pandas as pd
from sqlalchemy import text
import io
import re
import gzip
import time
import requests
from datetime import datetime, timedelta

try:
    from rapidfuzz import process as rf_process, fuzz as rf_fuzz
    USE_RAPIDFUZZ = True
except ImportError:
    from difflib import SequenceMatcher
    USE_RAPIDFUZZ = False


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Link Importer", page_icon="🔗", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Fraunces:wght@400;600;700&display=swap');

html, body, [class*="css"] { font-family: 'DM Mono', monospace; }
h1, h2, h3 { font-family: 'Fraunces', serif !important; }
section[data-testid="stSidebar"] {border-right: 1px solid #1e1e2e; }

.match-card {
    background: #13131f; border: 1px solid #1e1e2e;
    border-radius: 8px; padding: 14px 18px; margin-bottom: 10px; font-size: 13px;
}
.match-card.exact   { border-left: 4px solid #4ade80; }
.match-card.fuzzy   { border-left: 4px solid #facc15; }
.match-card.nomatch { border-left: 4px solid #f87171; }

.badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 500; margin-left: 6px;
}
.badge-exact   { background: #14532d; color: #4ade80; }
.badge-fuzzy   { background: #422006; color: #facc15; }
.badge-nomatch { background: #450a0a; color: #f87171; }

.stat-box {
    background: #13131f; border: 1px solid #1e1e2e;
    border-radius: 8px; padding: 20px; text-align: center;
}
.stat-num { font-size: 32px; font-family: 'Fraunces', serif; font-weight: 700; }
.stat-lbl { font-size: 12px; color: #888; margin-top: 4px; }

.url-text      { font-size: 11px; color: #60a5fa; word-break: break-all; margin-top: 4px; }
.asin-text     { font-size: 11px; color: #f59e0b; margin-bottom: 2px; }
.title-text    { font-size: 13px; color: #e8e4dc; margin-bottom: 4px; }
.db-title-text { font-size: 12px; color: #a0a0a0; }
</style>
""", unsafe_allow_html=True)


# ── Amazon constants ──────────────────────────────────────────────────────────
ENDPOINT        = "https://sellingpartnerapi-eu.amazon.com"
MARKETPLACE_ID  = "A21TJRUUN4KGV"
AMAZON_BASE_URL = "https://www.amazon.in/dp/"


# ── DB connection ─────────────────────────────────────────────────────────────
@st.cache_resource
def connect_db():
    try:
        return st.connection("mysql", type="sql")
    except Exception as e:
        st.error(f"DB connection error: {e}")
        st.stop()

conn = connect_db()


@st.cache_data(ttl=120)
def load_db_books():
    return conn.query(
        "SELECT book_id, title, agph_link, amazon_link FROM books WHERE title IS NOT NULL",
        ttl=120,
    )


# ── Text helpers ──────────────────────────────────────────────────────────────
def normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clean_title(raw: str) -> str:
    """General cleaner — strips ' | ' / ' - ' publisher suffixes (AGPH CSV)."""
    for sep in (" | ", " \u2013 ", " - "):
        if sep in raw:
            raw = raw.split(sep)[0].strip()
            break
    return raw.strip()


def clean_amazon_title(raw: str) -> str:
    """
    Cleans Amazon-mangled titles such as:
      'Handbook on Research Methodology [Paperback] [Jul 30, 2024] Dr. Samapti Paul; ...'
    Steps:
      1. Drop everything after the last ']' — author info always trails the last bracket.
      2. Remove all remaining [Paperback] / [Nov 28, 2024] bracket groups.
      3. Strip trailing dashes / punctuation and collapse whitespace.
    """
    last_bracket = raw.rfind("]")
    if last_bracket != -1:
        raw = raw[:last_bracket + 1]
    raw = re.sub(r"\[.*?\]", "", raw)
    raw = re.sub(r"[-\u2013]+$", "", raw.strip())
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


# ── Core matching engine ──────────────────────────────────────────────────────
def match_against_db(items: list, db_df: pd.DataFrame, fuzzy_threshold: float) -> list:
    db_titles = db_df["title"].tolist()
    db_ids    = db_df["book_id"].tolist()
    db_norm   = [normalize(t) for t in db_titles]

    results = []
    for item in items:
        query = normalize(item["clean_title"])

        if USE_RAPIDFUZZ:
            hit = rf_process.extractOne(query, db_norm, scorer=rf_fuzz.token_sort_ratio, score_cutoff=0)
            best_score = hit[1] / 100.0 if hit else 0.0
            best_idx   = hit[2]          if hit else -1
        else:
            best_score, best_idx = 0.0, -1
            for i, db_n in enumerate(db_norm):
                s = SequenceMatcher(None, query, db_n).ratio()
                if s > best_score:
                    best_score, best_idx = s, i

        if best_score >= 0.9999:
            match_type = "exact"
        elif best_score >= fuzzy_threshold:
            match_type = "fuzzy"
        else:
            match_type = "no_match"
            best_idx   = -1

        result = dict(item)
        result.update({
            "db_book_id": db_ids[best_idx]    if best_idx >= 0 else None,
            "db_title":   db_titles[best_idx] if best_idx >= 0 else None,
            "score":      round(best_score, 4),
            "match_type": match_type,
        })
        results.append(result)
    return results


# ── Card HTML builder (pure string, no st.markdown per card) ──────────────────
def card_html(m: dict) -> str:
    badge_cls  = {"exact": "badge-exact", "fuzzy": "badge-fuzzy", "no_match": "badge-nomatch"}[m["match_type"]]
    badge_text = {"exact": "EXACT", "fuzzy": f"FUZZY {m['score']:.0%}", "no_match": "NO MATCH"}[m["match_type"]]
    card_cls   = {"exact": "exact",  "fuzzy": "fuzzy",  "no_match": "nomatch"}[m["match_type"]]

    db_info = (
        f'<div class="db-title-text">&#8594; DB: <em>{m["db_title"]}</em></div>'
        if m["db_title"] else
        '<div class="db-title-text" style="color:#f87171">&#8594; No database match found</div>'
    )

    existing_note = ""
    if m.get("existing_url"):
        existing_note = (
            f'<div class="db-title-text" style="color:#a78bfa;margin-top:4px">'
            f'&#9888; Already has link &mdash; will be skipped: '
            f'<span style="color:#7c3aed">{m["existing_url"]}</span></div>'
        )

    extra_top = m.get("extra_top", "")

    return (
        f'<div class="match-card {card_cls}">'
        f'{extra_top}'
        f'<div class="title-text">{m["clean_title"]}'
        f'<span class="badge {badge_cls}">{badge_text}</span></div>'
        f'{db_info}{existing_note}'
        f'<div class="url-text">{m["url"]}</div>'
        f'</div>'
    )


def render_cards(items: list):
    """Render all cards in ONE st.markdown call — avoids Streamlit stripping HTML."""
    if not items:
        return
    st.markdown("".join(card_html(m) for m in items), unsafe_allow_html=True)


# ── Stats row ─────────────────────────────────────────────────────────────────
def render_stats(matches: list):
    exact   = [m for m in matches if m["match_type"] == "exact"]
    fuzzy   = [m for m in matches if m["match_type"] == "fuzzy"]
    no_m    = [m for m in matches if m["match_type"] == "no_match"]
    has_url = [m for m in matches if m.get("existing_url")]

    cols = st.columns(5)
    for col, num, color, label in [
        (cols[0], len(exact),   "#4ade80", "Exact matches"),
        (cols[1], len(fuzzy),   "#facc15", "Fuzzy matches"),
        (cols[2], len(no_m),    "#f87171", "No match"),
        (cols[3], len(has_url), "#a78bfa", "Already have URL"),
        (cols[4], len(matches), "#e8e4dc", "Total"),
    ]:
        with col:
            st.markdown(
                f'<div class="stat-box">'
                f'<div class="stat-num" style="color:{color}">{num}</div>'
                f'<div class="stat-lbl">{label}</div></div>',
                unsafe_allow_html=True,
            )
    st.markdown("")
    return exact, fuzzy, no_m, has_url


# ── Tabs + fuzzy checkboxes ───────────────────────────────────────────────────
def render_tabs(matches, exact, fuzzy, no_m, key_prefix: str = ""):
    tab_all, tab_exact, tab_fuzzy, tab_none = st.tabs([
        f"All ({len(matches)})",
        f"✅ Exact ({len(exact)})",
        f"⚠️ Fuzzy ({len(fuzzy)})",
        f"❌ No match ({len(no_m)})",
    ])
    fuzzy_selected = {}

    with tab_all:
        render_cards(matches)

    with tab_exact:
        if exact:
            render_cards(exact)
        else:
            st.info("No exact matches found.")

    with tab_fuzzy:
        if fuzzy:
            st.warning("Review these carefully before importing.")
            for i, m in enumerate(fuzzy):
                col_cb, col_card = st.columns([0.05, 0.95])
                with col_cb:
                    checked = st.checkbox(
                        "", value=True,
                        key=f"{key_prefix}fuzzy_{i}",
                        label_visibility="collapsed",
                    )
                with col_card:
                    # Single card — still one st.markdown call per card here,
                    # which is fine because each is wrapped in its own column context
                    st.markdown(card_html(m), unsafe_allow_html=True)
                fuzzy_selected[i] = checked
        else:
            st.info("No fuzzy matches.")

    with tab_none:
        if no_m:
            st.error("These could not be matched and will be skipped.")
            render_cards(no_m)
        else:
            st.success("All items were matched!")

    return fuzzy_selected


# ── Import runner ─────────────────────────────────────────────────────────────
def run_import(importable: list, db_column: str, no_matches: list, already_have_url: list):
    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.markdown(
            f"Ready to update **{len(importable)}** books with `{db_column}`. "
            f"**{len(no_matches)}** unmatched + **{len(already_have_url)}** already have a link → skipped."
        )
    with col_btn:
        do_import = st.button(
            "🚀 Import Now", type="primary",
            disabled=len(importable) == 0,
            use_container_width=True,
            key=f"import_btn_{db_column}",
        )

    if not do_import:
        return

    success_ids, failed_rows = [], []
    bar = st.progress(0, text="Importing…")

    with conn.session as s:
        for idx, m in enumerate(importable):
            try:
                s.execute(
                    text(f"""
                        UPDATE books
                        SET {db_column} = :url
                        WHERE book_id = :book_id
                          AND ({db_column} IS NULL OR TRIM({db_column}) = '')
                    """),
                    {"url": m["url"], "book_id": m["db_book_id"]},
                )
                success_ids.append(m["db_book_id"])
            except Exception as e:
                failed_rows.append({"title": m["clean_title"], "error": str(e)})

            bar.progress((idx + 1) / len(importable), text=f"Processing {idx + 1} / {len(importable)}…")

        try:
            s.commit()
            bar.empty()
            st.success(f"✅ Successfully updated **{len(success_ids)}** books!")
            for f in failed_rows:
                st.warning(f"⚠️ `{f['title']}` — {f['error']}")
        except Exception as e:
            s.rollback()
            bar.empty()
            st.error(f"❌ Commit failed — rolled back: {e}")

    load_db_books.clear()

    all_rows = importable + no_matches + already_have_url
    buf = io.StringIO()
    pd.DataFrame([{
        "Title (source)": m.get("raw_title", m["clean_title"]),
        "Title (clean)":  m["clean_title"],
        "URL":            m["url"],
        "DB Title":       m.get("db_title") or "",
        "DB book_id":     m.get("db_book_id") or "",
        "Match Type":     m["match_type"],
        "Score":          m["score"],
        "Imported":       "Yes" if m.get("db_book_id") in success_ids else "No",
    } for m in all_rows]).to_csv(buf, index=False)

    st.download_button(
        "📥 Download Report", data=buf.getvalue(),
        file_name=f"{db_column}_import_report.csv", mime="text/csv",
    )


# ═════════════════════════════════════════════════════════════════════════════
# PAGE LAYOUT
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("# 🔗 Link Importer")
st.markdown("Import **AGPH** and **Amazon** product links into the books database.")
st.divider()

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    fuzzy_threshold = st.slider("Fuzzy match threshold", 0.60, 1.00, 0.82, 0.01,
                                 help="Minimum similarity score to accept a fuzzy match")
    st.markdown("---")
    st.markdown("🟢 **Exact** — score = 1.0")
    st.markdown(f"🟡 **Fuzzy** — score ≥ {fuzzy_threshold:.2f}")
    st.markdown("🔴 **No match** — score below threshold")
    st.markdown("🟣 **Skipped** — already has link")
    st.markdown("---")
    if USE_RAPIDFUZZ:
        st.success("⚡ rapidfuzz active", icon="✅")
    else:
        st.warning("Install rapidfuzz for faster matching:\n`pip install rapidfuzz`")

# Load DB (shared by both tabs)
with st.spinner("Loading books from database…"):
    try:
        db_df = load_db_books()
    except Exception as e:
        st.error(f"Failed to load books: {e}")
        st.stop()

st.success(f"Loaded **{len(db_df)}** books from database.")
st.divider()

tab_agph, tab_amazon = st.tabs(["📦 AGPH Links (CSV)", "🛒 Amazon Links (SP-API)"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — AGPH CSV
# ══════════════════════════════════════════════════════════════════════════════
with tab_agph:
    st.markdown("### Step 1 — Upload CSV")
    st.caption("CSV must have two columns: **Title** and **URL**")

    uploaded = st.file_uploader("Upload CSV", type=["csv"],
                                 label_visibility="collapsed", key="agph_csv")

    if not uploaded:
        st.info("Upload a CSV file to get started.")
    else:
        try:
            csv_df = pd.read_csv(uploaded).iloc[:, :2]
            csv_df.columns = ["Title", "URL"]
            csv_df.dropna(subset=["Title", "URL"], inplace=True)
        except Exception as e:
            st.error(f"Failed to read CSV: {e}")
            st.stop()

        st.success(f"Loaded **{len(csv_df)}** rows from CSV.")
        st.markdown("### Step 2 — Match Titles")

        agph_items = [{
            "raw_title":   str(row["Title"]).strip(),
            "clean_title": clean_title(str(row["Title"]).strip()),
            "url":         str(row["URL"]).strip(),
        } for _, row in csv_df.iterrows()]

        with st.spinner("Matching titles…"):
            matches = match_against_db(agph_items, db_df, fuzzy_threshold)

        existing_map = dict(zip(db_df["book_id"], db_df.get("agph_link", pd.Series(dtype=str))))
        for m in matches:
            ex = existing_map.get(m["db_book_id"]) if m["db_book_id"] else None
            m["existing_url"] = ex if pd.notna(ex) and str(ex).strip() else None

        exact, fuzzy, no_m, has_url = render_stats(matches)
        fuzzy_selected = render_tabs(matches, exact, fuzzy, no_m, key_prefix="agph_")

        st.divider()
        st.markdown("### Step 3 — Import to Database")

        importable = [m for m in exact if not m.get("existing_url")]
        for i, m in enumerate(fuzzy):
            if fuzzy_selected.get(i, True) and not m.get("existing_url"):
                importable.append(m)

        already_have_url = [m for m in exact + fuzzy if m.get("existing_url")]
        run_import(importable, "agph_link", no_m, already_have_url)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — AMAZON SP-API
# ══════════════════════════════════════════════════════════════════════════════
with tab_amazon:
    st.markdown("### Step 1 — Fetch Amazon Listings")
    st.caption("Connects to SP-API and downloads your active listings report (~30–90 sec).")

    def get_lwa_access_token():
        if "amz_access_token" in st.session_state:
            if datetime.now() < st.session_state.get("amz_token_expiry", datetime.min):
                return st.session_state.amz_access_token
        resp = requests.post(
            "https://api.amazon.com/auth/o2/token",
            data={
                "grant_type":    "refresh_token",
                "refresh_token": st.secrets["amazon"]["REFRESH_TOKEN"],
                "client_id":     st.secrets["amazon"]["LWA_APP_ID"],
                "client_secret": st.secrets["amazon"]["LWA_CLIENT_SECRET"],
            },
        )
        if resp.status_code != 200:
            st.error("Failed to obtain Amazon access token.")
            return None
        token = resp.json()["access_token"]
        st.session_state.amz_access_token = token
        st.session_state.amz_token_expiry = datetime.now() + timedelta(minutes=55)
        return token

    def _request_and_download_report(access_token, report_type, status_label):
        """Request a report, poll until DONE, return raw text or None."""
        reports_url = f"{ENDPOINT}/reports/2021-06-30/reports"
        resp = requests.post(
            reports_url,
            json={"reportType": report_type, "marketplaceIds": [MARKETPLACE_ID]},
            headers={"x-amz-access-token": access_token},
        )
        if resp.status_code != 202:
            st.error(f"Error creating report {report_type}: {resp.text}")
            return None

        report_id   = resp.json()["reportId"]
        status_slot = st.empty()

        while True:
            time.sleep(5)
            s_resp = requests.get(f"{reports_url}/{report_id}",
                                   headers={"x-amz-access-token": access_token})
            if s_resp.status_code != 200:
                st.error(f"Error polling {report_type}: {s_resp.text}")
                return None
            meta   = s_resp.json()
            status = meta.get("processingStatus", "")
            status_slot.info(f"⏳ {status_label}: **{status}**…")
            if status == "DONE":
                document_id = meta.get("reportDocumentId")
                status_slot.success(f"✅ {status_label} ready!")
                time.sleep(0.3)
                status_slot.empty()
                break
            elif status in ("CANCELLED", "FATAL"):
                status_slot.error(f"❌ {status_label} failed: {status}")
                return None

        doc_resp = requests.get(
            f"{ENDPOINT}/reports/2021-06-30/documents/{document_id}",
            headers={"x-amz-access-token": access_token},
        )
        if doc_resp.status_code != 200:
            st.error(f"Error getting document URL: {doc_resp.text}")
            return None

        doc_data = doc_resp.json()
        dl_resp  = requests.get(doc_data["url"])
        if doc_data.get("compressionAlgorithm") == "GZIP":
            return gzip.decompress(dl_resp.content).decode("utf-8", errors="ignore")
        return dl_resp.content.decode("utf-8", errors="ignore")

    def _parse_tsv(report_text):
        """Robustly parse a TSV report text into a DataFrame."""
        lines = report_text.split("\n")
        header_idx, found = 0, False
        for i, line in enumerate(lines[:50]):
            ll = line.lower()
            if ("sku" in ll and "asin" in ll) or "seller-sku" in ll \
                    or "item-name" in ll or "listing-id" in ll:
                header_idx, found = i, True
                break
        if not found:
            max_tabs = 0
            for i, line in enumerate(lines[:50]):
                t = line.count("\t")
                if t > max_tabs:
                    max_tabs, header_idx = t, i
        try:
            df = pd.read_csv(io.StringIO(report_text), sep="\t", header=header_idx,
                             on_bad_lines="skip", quoting=3, dtype=str)
        except Exception:
            df = pd.read_csv(io.StringIO(report_text), sep="\t", header=header_idx,
                             on_bad_lines="skip", engine="python", dtype=str)
        df.columns = [c.strip() for c in df.columns]
        return df

    def _lookup_titles_from_catalog(access_token, asins: list, progress_slot) -> dict:
        """
        Batch-lookup titles for a list of ASINs via the Catalog Items API.
        Returns dict {asin: title}.
        """
        title_map = {}
        batch_size = 20   # API allows up to 20 ASINs per request
        total = len(asins)
        for i in range(0, total, batch_size):
            batch = asins[i:i + batch_size]
            params = {
                "MarketplaceIds": MARKETPLACE_ID,
                "identifiers":    ",".join(batch),
                "identifiersType": "ASIN",
                "includedData":   "summaries",
            }
            resp = requests.get(
                f"{ENDPOINT}/catalog/2022-04-01/items",
                params=params,
                headers={"x-amz-access-token": access_token},
            )
            if resp.status_code == 200:
                for item in resp.json().get("items", []):
                    asin = item.get("asin", "")
                    summaries = item.get("summaries", [])
                    if summaries:
                        title_map[asin] = summaries[0].get("itemName", "")
            progress_slot.info(
                f"⏳ Fetching titles via Catalog API… {min(i + batch_size, total)}/{total}"
            )
            time.sleep(0.3)   # gentle rate limiting
        return title_map

    def fetch_amazon_listings(access_token):
        """
        Two-report strategy:
          1. GET_FLAT_FILE_OPEN_LISTINGS_DATA  → all SKUs + ASINs (no titles)
          2. GET_MERCHANT_LISTINGS_ALL_DATA     → titles for active listings
          3. Catalog Items API                  → fill in titles missing from report 2
        """
        # ── Step A: get all open ASINs ────────────────────────────────────────
        st.info("📋 Step 1/3 — Fetching all open listings (SKU + ASIN)…")
        open_text = _request_and_download_report(
            access_token, "GET_FLAT_FILE_OPEN_LISTINGS_DATA", "Open listings report"
        )
        if open_text is None:
            return None

        open_df = _parse_tsv(open_text)
        asin_col_open = next((c for c in open_df.columns if c.lower() == "asin"), None)
        if not asin_col_open:
            st.error(f"No ASIN column in open listings report. Columns: {list(open_df.columns)}")
            return None

        all_asins = (
            open_df[asin_col_open]
            .dropna()
            .str.strip()
            .pipe(lambda s: s[s.str.startswith("B")])
            .drop_duplicates()
            .tolist()
        )
        st.info(f"📋 Found **{len(all_asins)}** unique ASINs in open listings.")

        # ── Step B: get titles from ALL_DATA report ───────────────────────────
        st.info("📋 Step 2/3 — Fetching titles from listings report…")
        all_text = _request_and_download_report(
            access_token, "GET_MERCHANT_LISTINGS_ALL_DATA", "Listings all-data report"
        )

        asin_title_map = {}
        if all_text:
            all_df = _parse_tsv(all_text)
            t_col = next((c for c in all_df.columns if "item-name" in c.lower()), None)
            a_col = next((c for c in all_df.columns if c.lower() in ("asin1", "asin")), None)
            if t_col and a_col:
                for _, row in all_df.iterrows():
                    asin  = str(row[a_col]).strip()
                    title = str(row[t_col]).strip()
                    if asin and title and title.lower() != "nan":
                        asin_title_map[asin] = title

        # ── Step C: Catalog API for any ASIN still missing a title ───────────
        missing_asins = [a for a in all_asins if a not in asin_title_map]
        if missing_asins:
            st.info(f"📋 Step 3/3 — Looking up titles for {len(missing_asins)} ASINs via Catalog API…")
            catalog_slot = st.empty()
            catalog_map  = _lookup_titles_from_catalog(access_token, missing_asins, catalog_slot)
            catalog_slot.empty()
            asin_title_map.update(catalog_map)

        # ── Build final DataFrame ─────────────────────────────────────────────
        rows = []
        for asin in all_asins:
            title = asin_title_map.get(asin, "")
            if title:
                rows.append({"amazon_title": title, "asin": asin})

        if not rows:
            st.error("Could not resolve titles for any ASIN. Please check API permissions.")
            return None

        result = pd.DataFrame(rows)
        result.drop_duplicates(subset=["asin"], inplace=True)
        result.reset_index(drop=True, inplace=True)
        return result

    if st.button("🔄 Fetch Amazon Listings", type="primary", key="amz_fetch"):
        with st.spinner("Authenticating…"):
            token = get_lwa_access_token()
        if token:
            with st.spinner("Requesting listings report…"):
                st.session_state.amazon_listings = fetch_amazon_listings(token)
            if st.session_state.get("amazon_listings") is not None:
                st.success(f"✅ Fetched **{len(st.session_state.amazon_listings)}** listings.")

    listings_df = st.session_state.get("amazon_listings")

    if listings_df is None:
        st.info("Click **Fetch Amazon Listings** to begin.")
    else:
        st.success(f"✅ **{len(listings_df)}** listings loaded (cached — re-fetch to refresh).")

        with st.expander("Preview Amazon listings", expanded=False):
            st.dataframe(listings_df.head(20), use_container_width=True)

        st.markdown("### Step 2 — Match Titles")

        amz_items = [{
            "raw_title":   str(row["amazon_title"]).strip(),
            "clean_title": clean_amazon_title(str(row["amazon_title"]).strip()),
            "asin":        str(row["asin"]).strip(),
            "url":         f"{AMAZON_BASE_URL}{str(row['asin']).strip()}",
            "extra_top":   f'<div class="asin-text">ASIN: {str(row["asin"]).strip()}</div>',
        } for _, row in listings_df.iterrows()]

        with st.spinner("Matching Amazon listings to database titles…"):
            matches = match_against_db(amz_items, db_df, fuzzy_threshold)

        existing_map = dict(zip(db_df["book_id"], db_df.get("amazon_link", pd.Series(dtype=str))))
        for m in matches:
            ex = existing_map.get(m["db_book_id"]) if m["db_book_id"] else None
            m["existing_url"] = ex if pd.notna(ex) and str(ex).strip() else None

        exact, fuzzy, no_m, has_url = render_stats(matches)
        fuzzy_selected = render_tabs(matches, exact, fuzzy, no_m, key_prefix="amz_")

        st.divider()
        st.markdown("### Step 3 — Import to Database")

        importable = [m for m in exact if not m.get("existing_url")]
        for i, m in enumerate(fuzzy):
            if fuzzy_selected.get(i, True) and not m.get("existing_url"):
                importable.append(m)

        already_have_url = [m for m in exact + fuzzy if m.get("existing_url")]
        run_import(importable, "amazon_link", no_m, already_have_url)