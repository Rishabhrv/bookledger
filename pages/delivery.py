import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from auth import validate_token
from constants import log_activity, initialize_click_and_session_id, connect_db, show_book_details, fetch_all_printeditions, fetch_all_book_authors
import streamlit.components.v1 as components

logo = "logo/logo_black.png"
fevicon = "logo/favicon_black.ico"
small_logo = "logo/favicon_white.ico"

st.set_page_config(page_title='AGPH Delivery Management', page_icon="🚚", layout="wide")

st.logo(logo,
size = "large",
icon_image = small_logo
)

validate_token()
initialize_click_and_session_id()

user_role = st.session_state.get("role", None)
user_app = st.session_state.get("app", None)
user_access = st.session_state.get("access", None)
session_id = st.session_state.session_id
click_id = st.session_state.get("click_id", None)

# Define access for Delivery Management
if user_role != 'admin' and not (
    user_role == 'user' and 
    user_app == 'main' and 
    ('Printing & Delivery' in user_access or 'Print Management' in user_access)
):
    st.error("⚠️ Access Denied: You don't have permission to access this page.")
    st.stop()

st.cache_data.clear()

st.markdown("""
    <style>
        .main > div { padding-top: 0px !important; }
        .block-container { padding-top: 28px !important; }
        .status-badge-blue {
            background-color: #E3F2FD; color: #1976D2; padding: 4px 12px;
            border-radius: 20px; font-weight: bold; display: inline-flex;
            align-items: center; font-size: 18px; margin-bottom: 15px;
            border: 1px solid #BBDEFB;
        }
        .badge-count {
            background-color: #1976D2; color: white;
            padding: 2px 8px; border-radius: 12px; margin-left: 8px;
            font-size: 14px; font-weight: 600;
        }
        .table-header {
            font-weight: 700; font-size: 13px; color: #4B5563;
            padding: 12px 5px; border-bottom: 2px solid #E5E7EB;
            text-transform: uppercase; letter-spacing: 0.05em;
        }
        .table-row {
            padding: 12px 5px; background-color: #ffffff; font-size: 14px;
            display: flex; align-items: center;
        }
        .author-tag {
            background-color: #EFF6FF; color: #1E40AF; padding: 2px 10px;
            border-radius: 9999px; font-size: 11px; margin-right: 4px; margin-top: 4px;
            display: inline-block; border: 1px solid #DBEAFE; font-weight: 600;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .missing-info-text {
            color: #B91C1C; font-size: 13px; line-height: 1.4;
            margin-bottom: 3px; font-weight: 600;
            display: flex; align-items: flex-start;
        }
        .missing-info-text::before {
            content: "•"; color: #EF4444; margin-right: 6px; font-size: 18px; line-height: 1;
        }
        .ready-badge {
            background-color: #F0FDF4; color: #166534; padding: 4px 12px;
            border-radius: 9999px; font-size: 13px; font-weight: 700;
            border: 1px solid #DCFCE7;
        }
        .delivered-badge {
            background-color: #F9FAFB; color: #374151; padding: 4px 12px;
            border-radius: 9999px; font-size: 13px; font-weight: 700;
            border: 1px solid #E5E7EB;
        }
        .book-id-text {
            color: #6B7280; font-family: monospace; font-weight: 600;
        }
        .month-header {
            font-size: 15px;
            font-weight: 600;
            color: #2c3e50;
            padding: 5px 12px;
            border-left: 4px solid #e74c3c;
            margin: 20px 0 15px;
            border-radius: 4px;
            background-color: #f8f9fa;
        }
        .row-divider {
            border-top: 1px solid #e9ecef;
            margin: 0;
            padding: 0;
        }
    </style>
""", unsafe_allow_html=True)

conn = connect_db()

if "logged_delivery_click_ids" not in st.session_state:
    st.session_state.logged_delivery_click_ids = set()

if click_id and click_id not in st.session_state.logged_delivery_click_ids:
    try:
        log_activity(conn, st.session_state.user_id, st.session_state.username,
                    st.session_state.session_id, "navigated to page", "Page: Delivery Management")
        st.session_state.logged_delivery_click_ids.add(click_id)
    except Exception as e:
        st.error(f"Error logging navigation: {str(e)}")

def get_pending_delivery_books(conn):
    query = """
    SELECT 
        b.book_id, b.title, b.date,
        GROUP_CONCAT(DISTINCT a.name SEPARATOR ', ') AS author_names,
        lb.batch_id, lb.batch_name, lb.print_receive_date,
        TRIM(TRAILING ' | ' FROM CONCAT(
            CASE WHEN SUM(CASE WHEN (
                ba.address_line1 IS NULL OR ba.address_line1 = '' OR
                ba.city_del IS NULL OR ba.city_del = '' OR
                ba.state_del IS NULL OR ba.state_del = '' OR
                ba.pincode IS NULL OR ba.pincode = '' OR
                ba.country IS NULL OR ba.country = ''
            ) THEN 1 ELSE 0 END) > 0 THEN 'Address | ' ELSE '' END,
            CASE WHEN SUM(CASE WHEN (ba.number_of_books IS NULL OR ba.number_of_books = 0) THEN 1 ELSE 0 END) > 0 THEN 'Copies to Send | ' ELSE '' END
        )) AS missing_info
    FROM books b
    JOIN book_authors ba ON b.book_id = ba.book_id
    JOIN authors a ON ba.author_id = a.author_id
    JOIN (
        SELECT pe.book_id, pb.batch_id, pb.batch_name, pb.print_receive_date,
               ROW_NUMBER() OVER(PARTITION BY pe.book_id ORDER BY pb.print_receive_date DESC, pb.batch_id DESC) as rn
        FROM PrintEditions pe
        JOIN BatchDetails bd ON pe.print_id = bd.print_id
        JOIN PrintBatches pb ON bd.batch_id = pb.batch_id
        WHERE pb.status = 'Received'
    ) lb ON b.book_id = lb.book_id AND lb.rn = 1
    WHERE b.print_status = 1 AND b.deliver = 0 AND b.is_cancelled = 0
    GROUP BY b.book_id, lb.batch_id, lb.batch_name, lb.print_receive_date
    ORDER BY lb.print_receive_date DESC, b.date DESC;
    """
    return conn.query(query, ttl=0)

def get_delivered_books(conn):
    query = """
    SELECT 
        b.book_id, b.title, b.date, b.publisher, b.apply_isbn, b.isbn, b.isbn_receive_date, 
        b.is_publish_only, b.is_thesis_to_book, b.deliver,
        b.writing_start, b.writing_end, b.writing_by,
        b.proofreading_start, b.proofreading_end, b.proofreading_by,
        b.formatting_start, b.formatting_end, b.formatting_by,
        b.cover_start, b.cover_end, b.cover_by,
        GROUP_CONCAT(DISTINCT a.name SEPARATOR ', ') AS author_names,
        MAX(ba.delivery_date) AS delivery_date,
        lb.batch_id, lb.batch_name, lb.print_receive_date
    FROM books b
    JOIN book_authors ba ON b.book_id = ba.book_id
    JOIN authors a ON ba.author_id = a.author_id
    LEFT JOIN (
        SELECT pe.book_id, pb.batch_id, pb.batch_name, pb.print_receive_date,
               ROW_NUMBER() OVER(PARTITION BY pe.book_id ORDER BY pb.print_receive_date DESC, pb.batch_id DESC) as rn
        FROM PrintEditions pe
        JOIN BatchDetails bd ON pe.print_id = bd.print_id
        JOIN PrintBatches pb ON bd.batch_id = pb.batch_id
    ) lb ON b.book_id = lb.book_id AND lb.rn = 1
    WHERE b.deliver = 1
    GROUP BY 
        b.book_id, b.title, b.date, b.publisher, b.apply_isbn, b.isbn, b.isbn_receive_date, 
        b.is_publish_only, b.is_thesis_to_book, b.deliver,
        b.writing_start, b.writing_end, b.writing_by,
        b.proofreading_start, b.proofreading_end, b.proofreading_by,
        b.formatting_start, b.formatting_end, b.formatting_by,
        b.cover_start, b.cover_end, b.cover_by,
        lb.batch_id, lb.batch_name, lb.print_receive_date
    ORDER BY delivery_date DESC;
    """
    return conn.query(query, ttl=0)

def update_book_authors(id, updates, conn):
    set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
    query = f"UPDATE book_authors SET {set_clause} WHERE id = :id"
    params = updates.copy()
    params["id"] = int(id)
    with conn.session as session:
        session.execute(text(query), params)
        session.commit()

def has_valid_delivery_info(row) -> bool:
    """
    An author is considered ready for delivery only when ALL of these are filled:
      - address_line1  (street / house number)
      - city_del
      - state_del
      - pincode
      - country
      - number_of_books > 0
    'country' defaulting to "India" is intentional — the user still must have
    filled address_line1 + city + state + pincode for the slip to be usable.
    """
    def filled(val) -> bool:
        return bool(val and str(val).strip())

    return (
        filled(row.get("address_line1"))
        and filled(row.get("city_del"))
        and filled(row.get("state_del"))
        and filled(row.get("pincode"))
        and filled(row.get("country"))
        and int(row.get("number_of_books") or 0) > 0
    )

@st.dialog("Manage Delivery", width="medium")
def manage_delivery_dialog(book_id, book_title, conn):
    # ─────────────────────────────────────────────────────────────────────────
    # KEY PRINCIPLE: Never call st.rerun() from a plain button's body.
    # Every navigation/save action uses on_click= callbacks which run BEFORE
    # Streamlit's rerun, so state is already set when the dialog re-renders.
    # st.form is intentionally NOT used for author cards — form_submit_button
    # triggers a rerun that closes the dialog. Instead, each widget gets a
    # unique session_state key and the save button uses on_click=.
    # ─────────────────────────────────────────────────────────────────────────

    # ── Ensure slip_generated_date column exists ──────────────────────────────
    try:
        with conn.session as s:
            s.execute(text("SELECT slip_generated_date FROM book_authors LIMIT 1"))
    except Exception:
        with conn.session as s:
            s.execute(text("ALTER TABLE book_authors ADD COLUMN slip_generated_date DATE"))
            s.commit()

    # ── Tab / state keys ──────────────────────────────────────────────────────
    TAB_DETAILS = "1 · Fill Details"
    TAB_PREVIEW = "2 · Preview Slip"
    TAB_CONFIRM = "3 · Confirm Delivery"
    tab_key     = f"dlv_tab_{book_id}"
    html_key    = f"dlv_html_{book_id}"
    date_key    = f"dlv_date_{book_id}"
    saved_key   = f"dlv_saved_{book_id}"   # tracks which author IDs were just saved

    if date_key  not in st.session_state:
        st.session_state[date_key]  = datetime.now().date()
    if saved_key not in st.session_state:
        st.session_state[saved_key] = set()

    # ── Fetch fresh data ──────────────────────────────────────────────────────
    query = """
        SELECT ba.id, ba.book_id, ba.author_id, a.name, a.phone,
               ba.delivery_address, ba.address_line1, ba.address_line2,
               ba.city_del, ba.state_del, ba.pincode, ba.country,
               ba.delivery_charge, ba.number_of_books, ba.delivery_date,
               ba.tracking_id, ba.delivery_vendor, ba.slip_generated_date
        FROM book_authors ba
        JOIN authors a ON ba.author_id = a.author_id
        WHERE ba.book_id = :book_id
    """
    authors          = conn.query(query, params={"book_id": book_id}, ttl=0)
    if authors.empty:
        st.warning("No authors found for this book.")
        return

    eligible_authors = authors[authors.apply(has_valid_delivery_info, axis=1)]
    total_authors    = len(authors)
    ready_count      = len(eligible_authors)
    slips_done       = int(authors["slip_generated_date"].notna().sum())

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(f"#### 📚 {book_id}: {book_title}")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(
        [TAB_DETAILS, TAB_PREVIEW, TAB_CONFIRM],
        on_change="rerun",
        key=tab_key,
    )

    # =========================================================================
    # TAB 1 — Fill Details
    # =========================================================================
    with tab1:
        missing = total_authors - ready_count
        if missing:
            st.warning(
                f"**{missing} author(s)** still need an address or copy count. "
                "Expand their card, fill in the details, and save."
            )
        else:
            st.success("All authors are ready. Click **Generate & Preview Slips** below.")

        st.write("")

        # ── Per-author cards ──────────────────────────────────────────────────
        for _, row in authors.iterrows():
            row_id   = row["id"]
            has_info = has_valid_delivery_info(row)
            icon     = "✅" if has_info else "⚠️"

            # Show a ✔ badge if this author was saved during this dialog session
            just_saved = row_id in st.session_state[saved_key]
            label      = f"{icon} {row['name']}"
            if just_saved:
                label += "  — ✔ saved"

            with st.expander(label, expanded=not has_info):

                # ── Widget keys (unique per author row) ───────────────────────
                k = lambda field: f"dlv_{field}_{row_id}"   # noqa: E731

                # Seed session_state only on first render (don't overwrite edits)
                defaults = {
                    k("n_bks"): int(row["number_of_books"]  or 0),
                    k("d_chg"): float(row["delivery_charge"] or 0.0),
                    k("d_vnd"): row["delivery_vendor"] or "",
                    k("t_id"):  row["tracking_id"]     or "",
                    k("addr1"): row["address_line1"]   or "",
                    k("addr2"): row["address_line2"]   or "",
                    k("city"):  row["city_del"]        or "",
                    k("state"): row["state_del"]       or "",
                    k("pin"):   row["pincode"]         or "",
                    k("ctry"):  row["country"]         or "India",
                }
                for sk, sv in defaults.items():
                    if sk not in st.session_state:
                        st.session_state[sk] = sv

                if row["delivery_address"] and not (row["address_line1"] or row["city_del"]):
                    st.info(f"Legacy address on file: {row['delivery_address']}")

                # ── 2-column grid layout ──────────────────────────────────────
                #   Left col  : Copies | Charge | Vendor | Tracking
                #   Right col : Addr1  | Addr2  | City+PIN | State+Country
                left, right = st.columns([1,2], gap="small")

                with left:
                    st.number_input(
                        "Copies to Send", min_value=0, step=1,
                        key=k("n_bks"),
                    )
                    st.number_input(
                        "Delivery Charge (₹)", min_value=0.0, step=0.01, format="%.2f",
                        key=k("d_chg"),
                    )
                    st.text_input("Delivery Vendor", key=k("d_vnd"))
                    st.text_input("Tracking ID",     key=k("t_id"))

                with right:
                    st.text_input("Address Line 1", key=k("addr1"))
                    st.text_input("Address Line 2", key=k("addr2"))
                    pin_col, city_col = st.columns([1, 1])
                    city_col.text_input("City",     key=k("city"))
                    pin_col.text_input("PIN Code",  key=k("pin"))
                    state_col, ctry_col = st.columns([1, 1])
                    state_col.text_input("State",   key=k("state"))
                    ctry_col.text_input("Country",  key=k("ctry"))

                # ── Save callback — on_click, zero rerun issues ───────────────
                def make_save_cb(rid, rname, legacy_addr):
                    def _save():
                        kk = lambda f: f"dlv_{f}_{rid}"   # noqa: E731
                        parts = [
                            st.session_state[kk("addr1")],
                            st.session_state[kk("addr2")],
                            st.session_state[kk("city")],
                            st.session_state[kk("state")],
                            st.session_state[kk("pin")],
                            st.session_state[kk("ctry")],
                        ]
                        full_addr = ", ".join([p.strip() for p in parts if p and p.strip()])
                        updates = {
                            "number_of_books":  st.session_state[kk("n_bks")],
                            "delivery_charge":  st.session_state[kk("d_chg")],
                            "delivery_vendor":  st.session_state[kk("d_vnd")],
                            "tracking_id":      st.session_state[kk("t_id")],
                            "address_line1":    st.session_state[kk("addr1")],
                            "address_line2":    st.session_state[kk("addr2")],
                            "city_del":         st.session_state[kk("city")],
                            "state_del":        st.session_state[kk("state")],
                            "pincode":          st.session_state[kk("pin")],
                            "country":          st.session_state[kk("ctry")],
                            "delivery_address": full_addr or legacy_addr,
                        }
                        try:
                            update_book_authors(rid, updates, conn)
                            log_activity(
                                conn, st.session_state.user_id,
                                st.session_state.username, st.session_state.session_id,
                                "updated delivery details",
                                f"Book ID: {book_id}, Author: {rname}",
                            )
                            st.session_state[saved_key].add(rid)
                        except Exception as e:
                            st.session_state[f"dlv_err_{rid}"] = str(e)
                    return _save

                st.button(
                    "💾 Save",
                    key=f"save_btn_{row_id}",
                    type="secondary",
                    use_container_width=True,
                    on_click=make_save_cb(row_id, row["name"], row["delivery_address"]),
                )

                # Show error if save failed
                err = st.session_state.pop(f"dlv_err_{row_id}", None)
                if err:
                    st.error(f"Save failed: {err}")

        # ── Generate slips button ─────────────────────────────────────────────
        st.write("")

        if eligible_authors.empty:
            st.error("At least one author needs an address and copy count to generate slips.")
        else:
            def go_to_preview():
                slip_css = """
                <style>
                    @media print {
                        @page { size: A4; margin: 0mm; }
                        body  { margin:0; padding:0; }
                        .slip { height:148mm; width:210mm; padding:10mm;
                                box-sizing:border-box; page-break-after:always;
                                overflow:hidden; display:flex; flex-direction:column; }
                        .slip:last-child { page-break-after:auto; }
                    }
                    body  { font-family:'Segoe UI',Arial,sans-serif; background:#eee; margin:0; padding:8px; }
                    .slip { width:100%; max-width:188mm; margin:8px auto; background:#fff;
                            border:2px dashed #444; padding:14px; box-sizing:border-box; }
                    .hdr  { text-align:center; border-bottom:2px solid #1e4976; padding-bottom:6px; margin-bottom:10px; }
                    .to-box   { flex:1; border:1.2px solid #1e4976; padding:8px; border-radius:6px; background:#f8fbff; min-height:100px; }
                    .from-box { flex:1; border:1.2px solid #ccc;    padding:8px; border-radius:6px; background:#fafafa;  min-height:100px; }
                </style>"""

                slips_html = ""
                # Re-query to pick up any saves done this session
                fresh = conn.query(query, params={"book_id": book_id}, ttl=0)
                fresh_eligible = fresh[fresh.apply(has_valid_delivery_info, axis=1)]

                for _, row in fresh_eligible.iterrows():
                    parts       = [row["address_line1"], row["address_line2"],
                                   row["city_del"], row["state_del"], row["pincode"], row["country"]]
                    full_addr   = ", ".join([str(p).strip() for p in parts if p and str(p).strip()])
                    author_addr = full_addr or row["delivery_address"] or "Address Pending"
                    slips_html += f"""
                    <div class="slip">
                        <div class="hdr">
                            <h2 style="margin:0;color:#1e4976;text-transform:uppercase;font-size:20px;">Delivery Slip</h2>
                            <p style="margin:2px 0;font-size:12px;font-weight:bold;color:#555;">Author Copy Bundle</p>
                        </div>
                        <div style="margin-bottom:10px;">
                            <table style="width:100%;border-collapse:collapse;font-size:13px;">
                                <tr>
                                    <td style="padding:4px;font-weight:bold;width:22%;border:1px solid #ddd;background:#f9f9f9;">Book Title:</td>
                                    <td style="padding:4px;border:1px solid #ddd;font-weight:600;">{book_title}</td>
                                </tr>
                                <tr>
                                    <td style="padding:4px;font-weight:bold;border:1px solid #ddd;background:#f9f9f9;">Quantity:</td>
                                    <td style="padding:4px;border:1px solid #ddd;">{int(row['number_of_books'])} Copies</td>
                                </tr>
                            </table>
                        </div>
                        <div style="display:flex;gap:12px;margin-bottom:10px;">
                            <div class="to-box">
                                <h3 style="margin:0 0 5px;color:#1e4976;border-bottom:1px solid #1e4976;padding-bottom:2px;text-transform:uppercase;font-size:11px;">TO (Recipient):</h3>
                                <p style="margin:3px 0;font-weight:bold;font-size:16px;">{row['name']}</p>
                                <p style="margin:3px 0;font-size:13px;line-height:1.4;white-space:pre-wrap;">{author_addr}</p>
                                <p style="margin:8px 0 0;font-size:13px;border-top:1px solid #d0e3ff;padding-top:3px;font-weight:bold;">Contact: {row['phone'] or 'N/A'}</p>
                            </div>
                            <div class="from-box">
                                <h3 style="margin:0 0 5px;color:#333;border-bottom:1px solid #ccc;padding-bottom:2px;text-transform:uppercase;font-size:11px;">FROM (Sender):</h3>
                                <p style="margin:3px 0;font-weight:bold;font-size:14px;color:#1e4976;">AGPH Books</p>
                                <p style="margin:5px 0;font-size:11px;line-height:1.3;color:#444;">
                                    57-First Floor, Susheela Bhawan, Priyadarshini Phase-3,<br>
                                    near Meenakshi Planet City, Bagmugaliya,<br>
                                    Bhopal, Madhya Pradesh 462043
                                </p>
                                <p style="margin:5px 0 0;font-weight:bold;font-size:12px;border-top:1px solid #ddd;padding-top:3px;">Contact: 9981933372</p>
                            </div>
                        </div>
                        <div style="font-size:10px;color:#999;border-top:1px solid #eee;padding-top:4px;">
                            Generated: {datetime.now().strftime('%d %b %Y')} &nbsp;|&nbsp; AGPH Books
                        </div>
                    </div>"""

                full_html = (
                    f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
                    f"<title>Delivery Slips – {book_title}</title>"
                    f"{slip_css}</head><body>{slips_html}</body></html>"
                )
                st.session_state[html_key] = full_html
                st.session_state[tab_key]  = TAB_PREVIEW
                log_activity(conn, st.session_state.user_id, st.session_state.username,
                            st.session_state.session_id, "generated delivery slips", f"Book ID: {book_id}")

            st.button(
                f"Generate & Preview Slips for {ready_count} author(s) →",
                type="primary", use_container_width=True,
                on_click=go_to_preview,
                key=f"go_preview_{book_id}",
            )

    # =========================================================================
    # TAB 2 — Preview & Download
    # =========================================================================
    with tab2:
        html_content = st.session_state.get(html_key)

        if not html_content:
            st.info("Go to **Fill Details** first and click **Generate & Preview Slips**.")
        else:
            st.markdown("Scroll through all slips below. Download, then continue to set the delivery date.")
            components.html(html_content, height=440, scrolling=True)

            dl_col, next_col = st.columns(2)

            dl_col.download_button(
                "📥 Download / Print Slips",
                data=html_content,
                file_name=f"delivery_slips_{book_id}.html",
                mime="text/html",
                use_container_width=True,
                type="primary",
                key=f"dl_btn_{book_id}",
            )

            def go_to_confirm():
                try:
                    with conn.session as s:
                        s.execute(
                            text("UPDATE book_authors SET slip_generated_date = CURDATE() WHERE book_id = :bid"),
                            {"bid": book_id},
                        )
                        s.commit()
                    log_activity(conn, st.session_state.user_id, st.session_state.username,
                                st.session_state.session_id, "printed delivery slips", f"Book ID: {book_id}")
                except Exception:
                    pass  # non-fatal
                st.session_state[tab_key] = TAB_CONFIRM

            next_col.button(
                "Continue → Set Delivery Date",
                type="secondary", use_container_width=True,
                on_click=go_to_confirm,
                key=f"go_confirm_{book_id}",
            )

    # =========================================================================
    # TAB 3 — Confirm Delivery
    # =========================================================================
    with tab3:
        if not st.session_state.get(html_key) and slips_done == 0:
            st.info("Complete **Fill Details** and **Preview Slip** steps first.")
        else:
            st.markdown("#### 🗓️ Select Delivery Date")
            st.caption(
                "Pick the dispatch date. Confirming will save it for all authors "
                "and remove this book from the pending delivery list."
            )

            delivery_date = st.date_input(
                "Delivery / Dispatch Date",
                value=st.session_state[date_key],
                key=f"final_date_{book_id}",
            )
            st.session_state[date_key] = delivery_date

            st.divider()
            st.warning(
                f"Confirming will mark **{book_title}** as dispatched on "
                f"**{delivery_date.strftime('%d %b %Y')}** and remove it from the queue."
            )

            def confirm_delivery():
                try:
                    d = st.session_state[f"final_date_{book_id}"]
                    with conn.session as s:
                        s.execute(
                            text("UPDATE books SET deliver = 1 WHERE book_id = :bid"),
                            {"bid": book_id},
                        )
                        s.execute(
                            text("UPDATE book_authors SET delivery_date = :d WHERE book_id = :bid"),
                            {"d": d, "bid": book_id},
                        )
                        s.commit()
                    log_activity(
                        conn, st.session_state.user_id,
                        st.session_state.username, st.session_state.session_id,
                        "marked book as delivered",
                        f"Book ID: {book_id}, Title: {book_title}",
                    )
                    for k in [html_key, date_key, tab_key, saved_key]:
                        st.session_state.pop(k, None)
                    st.session_state[f"dlv_done_{book_id}"] = True
                except Exception as e:
                    st.session_state[f"dlv_confirm_err_{book_id}"] = str(e)

            st.button(
                "🚚 Confirm & Mark as Delivered",
                type="primary", use_container_width=True,
                on_click=confirm_delivery,
                key=f"confirm_del_{book_id}",
            )

            if st.session_state.pop(f"dlv_done_{book_id}", False):
                st.success(f"✅ **{book_title}** marked as delivered!")
                import time
                time.sleep(1)
                st.rerun()

            err = st.session_state.pop(f"dlv_confirm_err_{book_id}", None)
            if err:
                st.error(f"Error: {err}")

@st.dialog("Book Details", width="large")
def show_book_details_(book_id, book_row, authors_df, printeditions_df):
    show_book_details(book_id, book_row, authors_df, printeditions_df)

def delivery_management_page():
    col1, col2= st.columns([8, 1], vertical_alignment="bottom")
    with col1: st.write("## 🚚 Delivery Management")
    with col2:
        if st.button(":material/refresh: Refresh", key="refresh", type="tertiary"): 
            st.cache_data.clear()
            st.rerun()

    tab_pending, tab_delivered = st.tabs(["🕒 Pending Delivery", "✅ Delivered History"])

    with tab_pending:
        pending_books = get_pending_delivery_books(conn)
        st.markdown(f'<div class="status-badge-blue">Pending Delivery <span class="badge-count">{len(pending_books)}</span></div>', unsafe_allow_html=True)
        st.caption("Books that have been printed and are awaiting delivery. Click the edit icon to manage delivery details and generate slips.")

        with st.container(border=True):
            col_sizes = [0.8, 4, 1.5, 1, 1, 0.8]
            if not pending_books.empty:
                header_cols = st.columns(col_sizes)
                headers = ["Book ID", "Title & Authors", "Missing Info", "Batch", "Print Date", "Action"]
                for col, text_val in zip(header_cols, headers):
                    col.markdown(f'<div class="table-header">{text_val}</div>', unsafe_allow_html=True)
                
                first_row = True
                for _, row in pending_books.iterrows():
                    if not first_row:
                        st.markdown('<div class="row-divider"></div>', unsafe_allow_html=True)
                    first_row = False

                    with st.container():
                        cols = st.columns(col_sizes)
                        cols[0].markdown(f'<div class="table-row"><span class="book-id-text">{row["book_id"]}</span></div>', unsafe_allow_html=True)
                        
                        authors_html = "".join([f'<span class="author-tag">{name.strip()}</span>' for name in row["author_names"].split(",")])
                        cols[1].markdown(f"""
                            <div class="table-row" style="display:block;">
                                <div style="font-weight:600; font-size:15px; margin-bottom:4px;">{row["title"]}</div>
                                <div style="line-height:1;">{authors_html}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        missing = row["missing_info"]
                        if missing:
                            missing_items = missing.split("|")
                            missing_html = "".join([f'<div class="missing-info-text">⚠️ {m.strip()}</div>' for m in missing_items])
                            cols[2].markdown(f'<div class="table-row" style="display:block; line-height:1.2;">{missing_html}</div>', unsafe_allow_html=True)
                        else:
                            cols[2].markdown(f'<div class="table-row"><span class="ready-badge">✅ Ready</span></div>', unsafe_allow_html=True)
                            
                        batch_info = f"{row['batch_name']} ({row['batch_id']})" if row["batch_id"] else "-"
                        cols[3].markdown(f'<div class="table-row">{batch_info}</div>', unsafe_allow_html=True)
                        cols[4].markdown(f'<div class="table-row">{row["print_receive_date"].strftime("%d %b %Y") if row["print_receive_date"] else "-"}</div>', unsafe_allow_html=True)                        
                        with cols[5]:
                            st.markdown('<div style="padding-top: 10px;">', unsafe_allow_html=True)
                            if st.button(":material/edit:", key=f"edit_{row['book_id']}", type="secondary", help="Manage Delivery"):
                                manage_delivery_dialog(row['book_id'], row['title'], conn)
                            st.markdown('</div>', unsafe_allow_html=True)
            else: st.info("No books pending delivery.")

    with tab_delivered:
        delivered_books = get_delivered_books(conn)
        book_ids = delivered_books['book_id'].tolist()
        authors_data = fetch_all_book_authors(book_ids, conn)
        printeditions_data = fetch_all_printeditions(book_ids, conn)

        # Initialize filter states
        if 'del_history_page' not in st.session_state: st.session_state.del_history_page = 0

        def reset_del_filters():
            st.session_state.search_del = ""
            st.session_state.del_year_pills = None
            st.session_state.del_month_pills = None
            st.session_state.del_history_page = 0

        # Layout for Search and Filters
        f_col1, f_col2 = st.columns([4, 2], vertical_alignment="bottom")
        
        with f_col1:
            search_query = st.text_input("🔍 Search Book ID or Title", key="search_del", placeholder="Search in all delivered books...")
        
        with f_col2:
            with st.popover("📅 Date Filters", use_container_width=True):
                st.button("Reset All", on_click=reset_del_filters, use_container_width=True)
                
                if not delivered_books.empty:
                    delivered_books['delivery_date'] = pd.to_datetime(delivered_books['delivery_date'])
                    years = sorted(delivered_books['delivery_date'].dt.year.unique(), reverse=True)
                    
                    selected_year = st.pills("Select Year", options=years, key="del_year_pills", selection_mode="single")
                    
                    if selected_year:
                        year_data = delivered_books[delivered_books['delivery_date'].dt.year == selected_year]
                        # Sort months chronologically
                        months = year_data['delivery_date'].dt.strftime('%B').unique().tolist()
                        month_order = ["January", "February", "March", "April", "May", "June", 
                                       "July", "August", "September", "October", "November", "December"]
                        available_months = [m for m in month_order if m in months]
                        
                        selected_month = st.pills("Select Month", options=available_months, key="del_month_pills", selection_mode="single")
                    else:
                        selected_month = None
                else:
                    selected_year = None
                    selected_month = None

        # Apply Filters
        filtered_df = delivered_books.copy()
        if not filtered_df.empty:
            if 'date' in filtered_df.columns:
                filtered_df['date'] = pd.to_datetime(filtered_df['date'])
            
            # Year Filter
            if selected_year:
                filtered_df = filtered_df[filtered_df['delivery_date'].dt.year == selected_year]
            
            # Month Filter
            if selected_month:
                filtered_df = filtered_df[filtered_df['delivery_date'].dt.strftime('%B') == selected_month]
            
            # Search Filter
            if search_query:
                filtered_df = filtered_df[
                    (filtered_df['book_id'].astype(str).str.contains(search_query, case=False)) |
                    (filtered_df['title'].str.contains(search_query, case=False))
                ]

        # Pagination Logic
        items_per_page = 50
        total_items = len(filtered_df)
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        
        if 'del_history_page' not in st.session_state:
            st.session_state.del_history_page = 0
            
        if st.session_state.del_history_page >= total_pages:
            st.session_state.del_history_page = total_pages - 1

        start_idx = st.session_state.del_history_page * items_per_page
        end_idx = start_idx + items_per_page
        paginated_df = filtered_df.iloc[start_idx:end_idx]

        # Header Info
        st.markdown(f'<div class="status-badge-blue">Delivered Books <span class="badge-count">{total_items}</span></div>', unsafe_allow_html=True)
        
        applied_filters_text = []
        if selected_year: applied_filters_text.append(f"Year: {selected_year}")
        if selected_month: applied_filters_text.append(f"Month: {selected_month}")
        if search_query: applied_filters_text.append(f"Search: '{search_query}'")
        
        if applied_filters_text:
            st.caption(f"Active Filters: {', '.join(applied_filters_text)}")

        with st.container(border=True):
            del_col_sizes = [0.8, 3.5, 1, 1, 1, 1, 0.8]
            header_cols = st.columns(del_col_sizes)
            headers = ["Book ID", "Title & Authors", "Enrolled On", "Batch", "Print Date", "Delivered On", "Action"]
            for col, text_val in zip(header_cols, headers):
                col.markdown(f'<div class="table-header">{text_val}</div>', unsafe_allow_html=True)

            if not paginated_df.empty:
                # Group paginated results by month
                paginated_df['month_year'] = paginated_df['delivery_date'].dt.to_period('M')
                grouped = paginated_df.groupby('month_year')
                
                # Iterate in reverse order (newest months first)
                for month_period, month_df in sorted(grouped, key=lambda x: x[0], reverse=True):
                    month_label = month_period.to_timestamp().strftime('%B %Y')
                    month_count = len(month_df)
                    st.markdown(f'<div class="month-header">{month_label} ({month_count} Delivered)</div>', unsafe_allow_html=True)
                    
                    first_row = True
                    for _, row in month_df.iterrows():
                        if not first_row:
                            st.markdown('<div class="row-divider"></div>', unsafe_allow_html=True)
                        first_row = False
                        
                        cols = st.columns(del_col_sizes)
                        cols[0].markdown(f'<div class="table-row"><span class="book-id-text">{row["book_id"]}</span></div>', unsafe_allow_html=True)
                        
                        authors_html = "".join([f'<span class="author-tag">{name.strip()}</span>' for name in row["author_names"].split(",")])
                        cols[1].markdown(f"""
                            <div class="table-row" style="display:block;">
                                <div style="font-weight:600; font-size:15px; margin-bottom:4px;">{row["title"]}</div>
                                <div style="line-height:1;">{authors_html}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        enroll_date_str = row["date"].strftime("%d %b %Y") if pd.notnull(row["date"]) else "-"
                        cols[2].markdown(f'<div class="table-row">{enroll_date_str}</div>', unsafe_allow_html=True)
                        
                        batch_info = f"{row['batch_name']} ({int(row['batch_id'])})" if row["batch_id"] else "-"
                        cols[3].markdown(f'<div class="table-row">{batch_info}</div>', unsafe_allow_html=True)
                        
                        print_date_str = row["print_receive_date"].strftime("%d %b %Y") if pd.notnull(row["print_receive_date"]) else "-"
                        cols[4].markdown(f'<div class="table-row">{print_date_str}</div>', unsafe_allow_html=True)
                        
                        delivery_date_str = row["delivery_date"].strftime("%d %b %Y") if pd.notnull(row["delivery_date"]) else "-"
                        cols[5].markdown(f'<div class="table-row" style="font-weight:600;">{delivery_date_str}</div>', unsafe_allow_html=True)
                        
                        with cols[6]:
                            col1,col2 = st.columns([1,1], gap="small")
                            with col1:
                                if st.button(":material/edit:", key=f"view_{row['book_id']}", help="Print Slip"):
                                    manage_delivery_dialog(row['book_id'], row['title'], conn)
                            with col2:
                                if st.button(":material/visibility:", key=f"action_pending_{row['book_id']}", help="View Details"):
                                    show_book_details_(row['book_id'], row, authors_data, printeditions_data)
            else:
                st.info("No delivered books found matching your criteria.")

        if total_items > 0:
            st.info(f"Showing {start_idx + 1}-{min(end_idx, total_items)} of {total_items} books")

        # Pagination Controls
        if total_pages > 1:
            st.write("")
            p_col1, p_col2, p_col3, p_col4 = st.columns([1, 2, 1, 2], vertical_alignment="center")
            with p_col1:
                if st.session_state.del_history_page > 0:
                    if st.button("Previous", key="prev_del"):
                        st.session_state.del_history_page -= 1
                        st.rerun()
            with p_col2:
                st.write(f"Page {st.session_state.del_history_page + 1} of {total_pages}")
            with p_col3:
                if st.session_state.del_history_page < total_pages - 1:
                    if st.button("Next", key="next_del"):
                        st.session_state.del_history_page += 1
                        st.rerun()
            with p_col4:
                page_options = list(range(1, total_pages + 1))
                selected_page = st.selectbox(
                    "Go to page",
                    options=page_options,
                    index=st.session_state.del_history_page,
                    key="page_selector_del",
                    label_visibility="collapsed"
                )
                if selected_page != st.session_state.del_history_page + 1:
                    st.session_state.del_history_page = selected_page - 1
                    st.rerun()

if __name__ == "__main__":
    delivery_management_page()
