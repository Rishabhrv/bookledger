import streamlit as st
import pandas as pd
from sqlalchemy import text
from constants import connect_db, log_activity, initialize_click_and_session_id, clean_url_params
from datetime import datetime
import time
from auth import validate_token

# Initialize Session
validate_token()
initialize_click_and_session_id()

# Page Config
st.set_page_config(
    page_title="Payments",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
            
        /* Remove Streamlit's default top padding */
        .main > div {
            padding-top: 0px !important;
        }
        /* Ensure the first element has minimal spacing */
        .block-container {
            padding-top: 8px !important;  /* Small padding for breathing room */
        }
            """, unsafe_allow_html=True)

# Custom CSS matching team_dashboard.py
st.markdown("""
<style>
    .header-row {
        padding-bottom: 5px;
        margin-bottom: 10px;
    }
    .header {
        font-weight: bold;
        font-size: 14px; 
    }
    .header-line {
        border-bottom: 1px solid #ddd;
        margin-top: -5px;
    }
    .pill {
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 12px;
        display: inline-block;
        margin-right: 4px;
    }
    /* Standardized badge colors */
    
    .header-status-badge-orange {
        background-color: #FFEFE6;
        color: #E65100;
        padding: 3px 6px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
    }
    .header-status-badge-green {
        background-color: #E8F5E9;
        color: #4CAF50;
        padding: 3px 6px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
    }
    .status-badge-red {
        background-color: #FFEBEE;
        color: #F44336;
        font-size: 12px;
        padding: 3px 6px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
    }
    .status-badge-yellow {
        background-color: #FFF3E0;
        color: #FB8C00;
        font-size: 12px;
        padding: 3px 6px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
    }
    .status-badge-orange {
        background-color: #FFEFE6;
        color: #E65100;
        font-size: 12px;
        padding: 3px 6px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
    }
    .status-badge-green {
        background-color: #E8F5E9;
        color: #4CAF50;
        padding: 3px 6px;
        font-size: 12px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
    }
    .status-badge-grey {
        background-color: #f5f5f5;
        color: #757575;
        padding: 3px 6px;
        font-size: 12px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
    }
    .badge-count {
        background-color: rgba(255, 255, 255, 0.9);
        color: inherit;
        padding: 2px 6px;
        border-radius: 10px;
        margin-left: 6px;
        font-size: 12px;
        font-weight: normal;
    }
    
    [data-testid="stElementToolbar"] {display: none;}
    
    /* Table specific overrides */
    .stButton button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Database Connection
conn = connect_db()

# Check Permissions
if st.session_state.get("role") != "admin":
    st.error("⛔ Access Denied: This page is for Administrators only.")
    st.stop()

col1, col2 = st.columns([10, 1], vertical_alignment="bottom")
with col1:
    st.title("Payments")
with col2:
    if st.button(":material/refresh: Refresh Data", key="refresh_main", type="tertiary"):
        st.cache_data.clear()

# --- Helper Functions ---

def fetch_all_transactions(conn, start_date):
    query = """
    SELECT 
        ap.id, 
        ap.amount, 
        ap.payment_date, 
        ap.payment_mode, 
        ap.transaction_id, 
        ap.status, 
        ap.remark,
        ap.requested_by,
        ap.approved_by,
        ap.approved_at,
        ap.rejection_reason,
        ba.book_id, 
        ba.id as book_author_id,
        b.title, 
        a.name as author_name, 
        ba.publishing_consultant
    FROM author_payments ap
    JOIN book_authors ba ON ap.book_author_id = ba.id
    JOIN authors a ON ba.author_id = a.author_id
    JOIN books b ON ba.book_id = b.book_id
    WHERE b.date >= :start_date
    ORDER BY ap.payment_date DESC, ap.id DESC
    """
    return conn.query(query, params={"start_date": start_date}, ttl=0)

def fetch_payment_overview(conn, start_date):
    query = """
    SELECT 
        b.book_id,
        b.title,
        b.price as book_price,
        b.date,
        ba.id as book_author_id,
        a.name as author_name,
        ba.total_amount as amount_due,
        ba.publishing_consultant,
        ba.corresponding_agent,
        COALESCE((SELECT SUM(amount) FROM author_payments WHERE book_author_id = ba.id AND status = 'Approved'), 0) as amount_paid,
        COALESCE((SELECT SUM(amount) FROM author_payments WHERE book_author_id = ba.id AND status = 'Pending'), 0) as amount_pending
    FROM book_authors ba
    JOIN books b ON ba.book_id = b.book_id
    JOIN authors a ON ba.author_id = a.author_id
    WHERE b.date >= :start_date
    ORDER BY b.date DESC
    """
    return conn.query(query, params={"start_date": start_date}, ttl=0)

def fetch_book_authors(book_id, conn):
    query = f"""
    SELECT ba.id, ba.book_id, ba.author_id, a.name, a.email, a.phone, a.about_author, a.author_photo, a.city, a.state,
           ba.author_position, ba.welcome_mail_sent, ba.corresponding_agent, 
           ba.publishing_consultant, ba.photo_recive, ba.id_proof_recive, 
           ba.author_details_sent, ba.cover_agreement_sent, ba.agreement_received, 
           ba.digital_book_sent, 
           ba.printing_confirmation, ba.delivery_address, ba.delivery_charge, 
           ba.number_of_books, ba.total_amount, 
           ba.delivery_date, ba.tracking_id, ba.delivery_vendor,
           ba.remark,
           COALESCE((SELECT SUM(amount) FROM author_payments WHERE book_author_id = ba.id AND status = 'Approved'), 0) as amount_paid
    FROM book_authors ba
    JOIN authors a ON ba.author_id = a.author_id
    WHERE ba.book_id = '{book_id}'
    """
    return conn.query(query, show_spinner = False)

def update_book_authors(id, updates, conn):
    set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
    query = f"UPDATE book_authors SET {set_clause} WHERE id = :id"
    params = updates.copy()
    params["id"] = int(id)
    with conn.session as session:
        session.execute(text(query), params)
        session.commit()

@st.dialog("Manage Book Payments", width="large")
def manage_price_dialog(book_id, conn):
    # Fetch book details for title and price
    book_details = fetch_book_details(book_id, conn)
    book_title = book_details.iloc[0]['title'] if not book_details.empty else "Unknown Title"
    current_price = book_details.iloc[0]['price'] if not book_details.empty else None
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
    with col2:
        if st.button(":material/refresh: Refresh", key="refresh_price", type="tertiary"):
            st.cache_data.clear()

    # Updated Streamlit-aligned CSS with improved visuals
    st.markdown("""
        <style>
                
        .payment-status {
            font-size: 12px;
            padding: 3px 8px;
            border-radius: 12px;
            margin-left: 10px;
            display: inline-block;
        }
        .status-paid { background-color: #e6ffe6; color: #006600; }
        .status-partial { background-color: #fff3e6; color: #cc6600; }
        .status-pending { background-color: #ffe6e6; color: #cc0000; }
        .payment-box {
            padding: 10px;
            border-radius: 6px;
            margin: 0 4px 8px 0;
            text-align: center;
            font-size: 14px;
            line-height: 1.5;
            border: 1px solid #e0e0e0;
            background-color: #ffffff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: transform 0.2s ease, background-color 0.2s ease;
        }
        .payment-box:hover {
            background-color: #f9f9f9;
            transform: translateY(-2px);
        }
        .status-paid {
            background-color: #f0f9eb;
            border-color: #b7e1a1;
            color: #2e7d32;
        }
        .status-partial {
            background-color: #fff4e6;
            border-color: #ffd8a8;
            color: #e65100;
        }
        .status-pending {
            background-color: #f6f6f6;
            border-color: #d9d9d9;
            color: #666666;
        }
        .author-name {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .payment-text {
            font-size: 14px;
            font-weight: 400;
        }
        .agent-text {
            font-size: 11px;
            color: #888888;
            margin-top: 6px;
            font-style: italic;
        }
        .status-badge {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 10px;
            display: inline-block;
            margin-top: 4px;
        }
        .status-paid .status-badge { background-color: #2e7d32; color: #ffffff; }
        .status-partial .status-badge { background-color: #e65100; color: #ffffff; }
        .status-pending .status-badge { background-color: #666666; color: #ffffff; }
        </style>
    """, unsafe_allow_html=True)

    # Payment Status Overview
    book_authors = fetch_book_authors(book_id, conn)
    
    if book_authors.empty:
        st.warning(f"No authors found for Book ID: {book_id}")
    else:
        # --- Grouping Logic ---
        book_authors['agent_clean'] = book_authors['corresponding_agent'].fillna('').str.strip()
        all_agents = set(book_authors[book_authors['agent_clean'] != '']['agent_clean'])
        
        def assign_group(row):
            if row['agent_clean'] != '': return row['agent_clean']
            if row['name'] in all_agents: return row['name']
            return f"INDV_{row['id']}"
            
        book_authors['payment_group'] = book_authors.apply(assign_group, axis=1)
        
        agent_summary = book_authors.groupby('payment_group').agg({
            'total_amount': 'sum',
            'amount_paid': 'sum',
            'publishing_consultant': 'first',
            'name': list
        }).reset_index()

        # Calculate book total paid
        total_book_paid = float(book_authors['amount_paid'].sum())
        total_book_expected = float(current_price) if pd.notna(current_price) else 0.0
        total_book_remaining = total_book_expected - total_book_paid

        # Determine book status color
        if total_book_paid >= total_book_expected and total_book_expected > 0:
            book_status_class, book_badge_text = "status-paid", "Fully Paid"
        elif total_book_paid > 0:
            book_status_class, book_badge_text = "status-partial", "Partially Paid"
        else:
            book_status_class, book_badge_text = "status-pending", "Pending"

        cols = st.columns(len(agent_summary) + 1, gap="small")
        
        with cols[0]:
            html = f"""
                <div class="payment-box {book_status_class}" style="border-left: 5px solid #4CAF50;">
                    <div class="author-name">Total Book Price</div>
                    <div class="payment-text">₹{int(total_book_paid)}/₹{int(total_book_expected)}</div>
                    <div class="status-badge">{book_badge_text}</div>
                    <div class="agent-text">Remaining: ₹{int(total_book_remaining)}</div>
                </div>
            """
            st.markdown(html, unsafe_allow_html=True)

        for i, row in agent_summary.iterrows():
            total_amount = int(row['total_amount'] or 0)
            amount_paid = float(row['amount_paid'] or 0)
            agent_consultant = row['publishing_consultant'] or 'Unknown Agent'
            group_id = row['payment_group']
            
            if group_id.startswith("INDV_"):
                display_name, is_group = row['name'][0], False
            else:
                display_name, is_group = group_id, True
            
            member_names = ", ".join(row['name'])

            if amount_paid >= total_amount and total_amount > 0:
                status_class, badge_text = "status-paid", "Paid"
            elif amount_paid > 0:
                status_class, badge_text = "status-partial", "Partial"
            else:
                status_class, badge_text = "status-pending", "Pending"

            with cols[i+1]:
                group_style = "border-top: 3px solid #3b82f6;" if is_group else ""
                html = f"""
                    <div class="payment-box {status_class}" style="{group_style}" title="Covers: {member_names}">
                        <div class="author-name">{display_name}</div>
                        <div class="payment-text">₹{int(amount_paid)}/₹{total_amount}</div>
                        <div class="status-badge">{badge_text}</div>
                        <div class="agent-text">{agent_consultant}</div>
                    </div>
                """
                st.markdown(html, unsafe_allow_html=True)

    # Section 1: Book Price
    with st.container(border=True):
        st.markdown("<h5 style='color: #4CAF50;'>Book Price</h5>", unsafe_allow_html=True)
        col1,col2 = st.columns([1,1], gap="small", vertical_alignment="bottom")
        with col1:
            price_str = st.text_input(
                "Book Price (₹)",
                value=str(int(current_price)) if pd.notna(current_price) else "",
                key=f"price_{book_id}",
                placeholder="Enter whole amount"
            )

        with col2:
            if st.button("Save Price", key=f"save_price_{book_id}"):
                with st.spinner("Saving..."):
                    import time
                    time.sleep(1)
                    try:
                        price = int(price_str) if price_str.strip() else None
                        if price is not None and price < 0:
                            st.error("Price cannot be negative")
                            return
                        with conn.session as s:
                            s.execute(
                                text("UPDATE books SET price = :price WHERE book_id = :book_id"),
                                {"price": price, "book_id": book_id}
                            )
                            s.commit()
                        
                        log_activity(
                            conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id,
                            "updated book price", f"Book: {book_title} ({book_id}), New Price: ₹{price}"
                        )
                        st.toast("Book Price Updated Successfully", icon="✔️", duration="long")
                        st.cache_data.clear()
                    except ValueError:
                        st.error("Please enter a valid whole number", icon="🚨")
    
    # Section 2: Author Payments with Tabs
    with st.container(border=True):
        st.markdown("<h5 style='color: #4CAF50;'>Author Payments</h5>", unsafe_allow_html=True)
        if not book_authors.empty:
            groups = book_authors.groupby('payment_group')
            tab_names, group_keys = [], []
            for name, group_df in groups:
                if name.startswith("INDV_"): tab_names.append(group_df.iloc[0]['name'])
                else: tab_names.append(f"👤 {name} (Agent)")
                group_keys.append(name)

            tabs = st.tabs(tab_names)

            for tab, group_id in zip(tabs, group_keys):
                group_df = groups.get_group(group_id)
                with tab:
                    if group_id.startswith("INDV_"):
                        lead_author, is_group = group_df.iloc[0], False
                    else:
                        matches = group_df[group_df['name'] == group_id]
                        lead_author, is_group = (matches.iloc[0] if not matches.empty else group_df.iloc[0]), True
                    
                    ba_ids = tuple(group_df['id'].tolist())
                    anchor_ba_id = lead_author['id']
                    total_amount_sum = int(group_df['total_amount'].sum() or 0)
                    total_paid_sum = float(group_df['amount_paid'].sum() or 0)
                    
                    if total_paid_sum >= total_amount_sum and total_amount_sum > 0:
                        status_html = '<span class="payment-status status-paid">Fully Paid</span>'
                    elif total_paid_sum > 0:
                        status_html = '<span class="payment-status status-partial">Partially Paid</span>'
                    else:
                        status_html = '<span class="payment-status status-pending">Pending</span>'
                    
                    st.markdown(f"**Payment Status:** {status_html}", unsafe_allow_html=True)
                    if is_group: st.info(f"**Authors Covered by {group_id}:** {', '.join(group_df['name'].tolist())}")

                    # --- Section: Individual Author Metadata ---
                    st.markdown("##### 📝 Manage Amounts")
                    for _, row in group_df.iterrows():
                        cur_ba_id = row['id']
                        mcol1, mcol2, mcol3 = st.columns([1, 2, 0.5])
                        with mcol1:
                            new_total_str = st.text_input(
                                f"₹ Total ({row['name']})",
                                value=str(int(row['total_amount'] or 0)) if (row['total_amount'] or 0) > 0 else "",
                                key=f"total_{cur_ba_id}"
                            )
                        with mcol2:
                            new_remark = st.text_input(
                                f"Remark ({row['name']})", value=row.get('remark', '') or "", key=f"remark_{cur_ba_id}"
                            )
                        with mcol3:
                            st.write("")
                            if st.button("Save", key=f"save_meta_{cur_ba_id}", use_container_width=True):
                                try:
                                    nt = int(new_total_str) if new_total_str.strip() else 0
                                    update_book_authors(cur_ba_id, {"total_amount": nt, "remark": new_remark}, conn)
                                    log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "updated author total & remark", f"Book: {book_id}, Author: {row['name']}, Total: ₹{nt}")
                                    st.toast(f"Updated {row['name']}!", icon="✔️")
                                    st.cache_data.clear()
                                except ValueError: st.error("Invalid amount")

                    st.write("---")

                    # --- Section: Payment History ---
                    st.markdown(f"##### 🧾 Payment History {'(Group)' if is_group else ''}")
                    history_query = "SELECT * FROM author_payments WHERE book_author_id IN :ba_ids ORDER BY payment_date DESC"
                    history = conn.query(history_query, params={"ba_ids": ba_ids}, ttl=0, show_spinner=False)
                    
                    if not history.empty:
                        for _, p in history.iterrows():
                            pay_ba_row = group_df[group_df['id'] == p['book_author_id']]
                            pay_author_name = pay_ba_row.iloc[0]['name'] if not pay_ba_row.empty else "Unknown"
                            hcol1, hcol2, hcol3, hcol4, hcol5, hcol6 = st.columns([1, 1, 1, 1, 1, 0.4])
                            with hcol1:
                                st.write(f"₹{p['amount']}")
                                if is_group: st.caption(f"Ref: {pay_author_name}")
                            with hcol2: st.write(p['payment_date'].strftime('%d %b %Y'))
                            with hcol3: st.write(f"**{p['payment_mode']}**")
                            with hcol4: st.write(f"ID: {p['transaction_id']}" if p['transaction_id'] else "-")
                            with hcol5:
                                p_status = p.get('status', 'Pending')
                                status_color = "green" if p_status == 'Approved' else "red" if p_status == 'Rejected' else "orange"
                                st.markdown(f"<span style='color:{status_color}'>{p_status}</span>", unsafe_allow_html=True)
                            with hcol6:
                                if st.button(":material/delete:", key=f"del_pay_{p['id']}"):
                                    with conn.session as s:
                                        s.execute(text("DELETE FROM author_payments WHERE id = :pid"), {"pid": p['id']})
                                        s.commit()
                                    st.rerun()
                    else: st.info("No payment records found.")

                    st.write("---")
                    
                    # --- Section: Add New Payment ---
                    st.markdown(f"##### ➕ Add New Payment {'(Group)' if is_group else ''}")
                    acol1, acol2, acol3 = st.columns([1, 1, 1])
                    with acol1: add_amt = st.text_input("Amount (₹)", key=f"add_amt_ui_{group_id}", placeholder="0")
                    with acol2: add_date = st.date_input("Date", value=datetime.now(), key=f"add_date_ui_{group_id}")
                    with acol3: add_mode = st.selectbox("Mode", ["Cash", "UPI", "Bank Deposit"], key=f"add_mode_ui_{group_id}")
                    
                    add_txn = st.text_input("Transaction ID", key=f"add_txn_ui_{group_id}") if add_mode in ["UPI", "Bank Deposit"] else ""
                    add_rem = st.text_input("Note", key=f"add_rem_ui_{group_id}")

                    if st.button(f"➕ Register {'Group ' if is_group else ''}Payment", key=f"btn_add_ui_{group_id}", type="primary", use_container_width=True):
                        try:
                            amt = float(add_amt) if add_amt.strip() else 0
                            if amt <= 0: st.error("Enter a valid amount")
                            else:
                                is_admin = st.session_state.get("role") == "admin"
                                initial_status = 'Approved' if is_admin else 'Pending'
                                with conn.session as s:
                                    s.execute(text("""INSERT INTO author_payments (book_author_id, amount, payment_date, payment_mode, transaction_id, remark, status, created_by, requested_by, approved_by, approved_at) VALUES (:ba_id, :amt, :date, :mode, :txn, :remark, :status, :created_by, :requested_by, :approved_by, :approved_at)"""), {"ba_id": anchor_ba_id, "amt": amt, "date": add_date, "mode": add_mode, "txn": add_txn, "remark": add_rem, "status": initial_status, "created_by": st.session_state.get("user_id"), "requested_by": st.session_state.get("username", "Unknown"), "approved_by": st.session_state.get("username") if is_admin else None, "approved_at": datetime.now() if is_admin else None})
                                    s.commit()
                                st.success("Payment registered!")
                                st.rerun()
                        except ValueError: st.error("Invalid amount")

                    remaining = total_amount_sum - total_paid_sum
                    st.markdown(f"<div style='text-align:right; font-size:16px; margin-top:10px;'><b>Total Paid:</b> <span style='color:green'>₹{int(total_paid_sum)}</span> | <b>Remaining:</b> <span style='color:red'>₹{int(remaining)}</span></div>", unsafe_allow_html=True)


def fetch_book_details(book_id, conn):
    query = f"""
    SELECT title, price
    FROM books
    WHERE book_id = '{book_id}'
    """
    return conn.query(query, show_spinner = False)

def fetch_payment_overview(conn, start_date):
    query = """
    SELECT 
        b.book_id,
        b.title,
        b.price as book_price,
        b.date,
        ba.id as book_author_id,
        a.name as author_name,
        ba.total_amount as amount_due,
        ba.publishing_consultant,
        ba.corresponding_agent,
        COALESCE((SELECT SUM(amount) FROM author_payments WHERE book_author_id = ba.id AND status = 'Approved'), 0) as amount_paid,
        COALESCE((SELECT SUM(amount) FROM author_payments WHERE book_author_id = ba.id AND status = 'Pending'), 0) as amount_pending
    FROM book_authors ba
    JOIN books b ON ba.book_id = b.book_id
    JOIN authors a ON ba.author_id = a.author_id
    WHERE b.date >= :start_date
    ORDER BY b.date DESC
    """
    return conn.query(query, params={"start_date": start_date}, ttl=0)

def update_payment_status(payment_id, new_status, approved_by, conn, rejection_reason=None):
    try:
        with conn.session as s:
            s.execute(
                text("""UPDATE author_payments 
                       SET status = :status, 
                           approved_by = :approved_by, 
                           approved_at = CURRENT_TIMESTAMP,
                           rejection_reason = :rejection_reason
                       WHERE id = :id"""),
                {"status": new_status, "approved_by": approved_by, "id": payment_id, "rejection_reason": rejection_reason}
            )
            s.commit()
        return True
    except Exception as e:
        st.error(f"Error updating status: {e}")
        return False

@st.dialog("Review Payment Request", width="large")
def show_approval_dialog(row, conn):
    # Fetch Author Summary
    summary_query = """
    SELECT 
        total_amount as amount_due,
        COALESCE((SELECT SUM(amount) FROM author_payments WHERE book_author_id = :ba_id AND status = 'Approved'), 0) as amount_paid,
        COALESCE((SELECT SUM(amount) FROM author_payments WHERE book_author_id = :ba_id AND status = 'Pending'), 0) as amount_pending
    FROM book_authors
    WHERE id = :ba_id
    """
    summary_df = conn.query(summary_query, params={"ba_id": row['book_author_id']}, ttl=0)
    summary = summary_df.iloc[0] if not summary_df.empty else {"amount_due": 0, "amount_paid": 0, "amount_pending": 0}
    
    # Fetch History
    history_query = """
    SELECT payment_date, amount, payment_mode, transaction_id, status, remark, requested_by
    FROM author_payments 
    WHERE book_author_id = :ba_id 
    ORDER BY payment_date DESC
    """
    history = conn.query(history_query, params={"ba_id": row['book_author_id']}, ttl=0)

    # Header section (Compact)
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"<h3 style='margin-bottom:0;'>{row['author_name']}</h3>", unsafe_allow_html=True)
        st.markdown(f"<span style='color:#666; font-size:14px;'>Book: <b>{row['title']}</b> ({row['book_id']})</span>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div style='text-align: right; font-size: 13px; color: #888;'>Requested: {row['payment_date'].strftime('%d %b %Y')} by {row['requested_by'] or 'Unknown'}</div>", unsafe_allow_html=True)

    # Financial Summary (Custom Compact HTML)
    amount_due = float(summary['amount_due'] or 0)
    amount_paid = float(summary['amount_paid'] or 0)
    amount_pending = float(summary['amount_pending'] or 0)
    balance = max(0.0, amount_due - amount_paid)

    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; background-color: #fcfcfc; padding: 12px; border: 1px solid #eee; border-radius: 8px; margin: 10px 0;">
        <div style="text-align: center; flex: 1;">
            <div style="font-size: 11px; color: #666; text-transform: uppercase;">Total Due</div>
            <div style="font-weight: bold; font-size: 16px;">₹{amount_due:,.0f}</div>
        </div>
        <div style="text-align: center; flex: 1; border-left: 1px solid #eee;">
            <div style="font-size: 11px; color: #666; text-transform: uppercase;">Paid</div>
            <div style="font-weight: bold; font-size: 16px; color: #2e7d32;">₹{amount_paid:,.0f}</div>
        </div>
        <div style="text-align: center; flex: 1; border-left: 1px solid #eee;">
            <div style="font-size: 11px; color: #666; text-transform: uppercase;">Pending Appr.</div>
            <div style="font-weight: bold; font-size: 16px; color: #f57c00;">₹{amount_pending:,.0f}</div>
        </div>
        <div style="text-align: center; flex: 1; border-left: 1px solid #eee;">
            <div style="font-size: 11px; color: #666; text-transform: uppercase;">Balance</div>
            <div style="font-weight: bold; font-size: 16px; color: #d32f2f;">₹{balance:,.0f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Current Request Details (Compact Grid)
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1.2, 0.8, 1.2, 1.8])
        with c1:
            st.markdown(f"<small style='color:#666;'>AMOUNT TO APPROVE</small><br><h4 style='color: #2e7d32; margin-top:0;'>₹{row['amount']:,.2f}</h4>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<small style='color:#666;'>MODE</small><br><b>{row['payment_mode']}</b>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<small style='color:#666;'>TXN ID</small><br><code>{row['transaction_id'] or '-'}</code>", unsafe_allow_html=True)
        with c4:
            st.markdown(f"<small style='color:#666;'>REMARK</small><br><span style='font-size: 14px;'>{row['remark'] or '-'}</span>", unsafe_allow_html=True)

    # History & Actions in one row to save vertical space
    hist_col, act_col = st.columns([3, 2])
    
    with hist_col:
        with st.expander(f"📜 History ({len(history)})", expanded=False):
            if not history.empty:
                st.dataframe(
                    history[['payment_date', 'amount', 'status']],
                    column_config={
                        "payment_date": st.column_config.DateColumn("Date", format="DD MMM"),
                        "amount": st.column_config.NumberColumn("Amount", format="₹%.0f"),
                    },
                    hide_index=True,
                    use_container_width=True,
                    height=150
                )
            else:
                st.caption("No previous records.")

    with act_col:
        st.write("") # Alignment
        b1, b2 = st.columns(2)
        with b1:
            if st.button("✅ Approve", key=f"dlg_app_{row['id']}", type="primary", use_container_width=True):
                if update_payment_status(row['id'], "Approved", st.session_state.username, conn):
                    log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "approved payment", f"Book: {row['title']} ({row['book_id']}), Author: {row['author_name']}, Amount: ₹{row['amount']}, Mode: {row['payment_mode']}")
                    st.toast(f"Approved ₹{row['amount']} for {row['author_name']}", icon="✅")
                    time.sleep(1)
                    st.rerun()
        with b2:
            with st.popover("❌ Reject", use_container_width=True):
                st.markdown("##### Confirm Rejection")
                reason = st.text_input("Reason", placeholder="e.g. Txn mismatch...", key=f"rej_reason_{row['id']}")
                if st.button("Confirm Reject", key=f"btn_rej_{row['id']}", type="secondary", use_container_width=True):
                    if update_payment_status(row['id'], "Rejected", st.session_state.username, conn, reason):
                        log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "rejected payment", f"Book: {row['title']} ({row['book_id']}), Author: {row['author_name']}, Amount: ₹{row['amount']}, Reason: {reason}")
                        st.toast(f"Rejected ₹{row['amount']}", icon="🚫")
                        time.sleep(1)
                        st.rerun()

@st.dialog("Book Payment Details", width="large")
def show_book_payment_details(book_id, title, price, group, all_transactions, conn):
    st.markdown(f"### 📖 {book_id} : {title}")
    st.markdown(f"**Book Price:** ₹{price if pd.notna(price) else 'N/A'}")
    
    # --- Grouping Logic ---
    book_authors = fetch_book_authors(book_id, conn)
    book_authors['agent_clean'] = book_authors['corresponding_agent'].fillna('').str.strip()
    all_agents = set(book_authors[book_authors['agent_clean'] != '']['agent_clean'])
    
    def assign_group(row):
        if row['agent_clean'] != '': return row['agent_clean']
        if row['name'] in all_agents: return row['name']
        return f"INDV_{row['id']}"
        
    book_authors['payment_group'] = book_authors.apply(assign_group, axis=1)
    groups = book_authors.groupby('payment_group')

    for group_id, group_df in groups:
        is_group = not group_id.startswith("INDV_")
        display_name = group_id if is_group else group_df.iloc[0]['name']
        
        # Totals for the group/individual
        total_due = float(group_df['total_amount'].sum() or 0)
        total_paid = float(group_df['amount_paid'].sum() or 0)
        
        # Calculate pending for this group from all_transactions
        ba_ids = group_df['id'].tolist()
        group_txns = all_transactions[all_transactions['book_author_id'].isin(ba_ids)]
        total_pending = float(group_txns[group_txns['status'] == 'Pending']['amount'].sum() or 0)

        # Status badge
        if total_paid >= total_due and total_due > 0:
            status_class, status_text = "status-badge-green", "Fully Paid"
        elif total_paid > 0:
            status_class, status_text = "status-badge-yellow", "Partially Paid"
        else:
            status_class, status_text = "status-badge-red", "Unpaid"

        # Group Container
        st.markdown(f"""
        <div style="background-color: white; border:1px solid #ddd; border-radius:8px; padding:15px; margin: 10px 0; {'border-left: 5px solid #3b82f6;' if is_group else ''}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h4 style="margin:0; color:#333;">{'👥' if is_group else '👤'} {display_name}</h4>
                    <small style="color:#666;">{'Group Agent' if is_group else 'Consultant: ' + str(group_df.iloc[0]['publishing_consultant'])}</small>
                </div>
                <div style="text-align:right;">
                    <span class="{status_class}">
                        {status_text}
                    </span>
                </div>
            </div>
            {f'<div style="font-size:12px; color:#666; margin-top:5px;"><b>Covers:</b> {", ".join(group_df["name"].tolist())}</div>' if is_group else ''}
            <hr style="margin:10px 0;">
            <div style="display:flex; justify-content:space-between;">
                <div><small>Total Due</small><br><strong>₹{total_due:,.0f}</strong></div>
                <div><small>Paid (Approved)</small><br><strong style="color:green">₹{total_paid:,.0f}</strong></div>
                <div><small>Pending Approval</small><br><strong style="color:orange">₹{total_pending:,.0f}</strong></div>
                <div><small>Balance</small><br><strong style="color:red">₹{max(0, total_due - total_paid):,.0f}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not group_txns.empty:
            with st.expander(f"Show History {'(Group)' if is_group else ''} ({len(group_txns)})"):
                st.dataframe(
                    group_txns[['payment_date', 'amount', 'payment_mode', 'transaction_id', 'status', 'remark', 'requested_by']],
                    column_config={
                        "payment_date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
                        "amount": st.column_config.NumberColumn("Amount", format="₹%.2f"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
        else: st.caption("No transaction history.")

# --- UI Controls (Popover for Filters) ---
top_col1, top_col2 = st.columns([5, 2])
with top_col1:
    search_query = st.text_input("🔍 Search", placeholder="Enter Book ID, Title or Author Name...", label_visibility="collapsed", key="pay_search")
with top_col2:
    with st.popover("⚙️ Filters", use_container_width=True):
        st.subheader("Filter Options")
        start_date_filter = st.date_input("Show Books From", value=datetime(2026, 2, 1), key="pay_start_date")
        view_filter = st.selectbox("Status Filter", ["All", "Pending Payments", "Unpaid Authors", "Fully Paid"], key="pay_status_filter")
        
        if st.button("Reset All", use_container_width=True):
            # Clear filter keys from session state
            for key in ["pay_search", "pay_start_date", "pay_status_filter"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.pay_page = 0
            st.rerun()

# --- Pagination & Filter Reset Logic ---
if 'pay_page' not in st.session_state:
    st.session_state.pay_page = 0

if 'prev_filters' not in st.session_state:
    st.session_state.prev_filters = {}

current_filters = {
    "search": search_query,
    "date": start_date_filter,
    "view": view_filter
}

if current_filters != st.session_state.prev_filters:
    st.session_state.pay_page = 0
    st.session_state.prev_filters = current_filters

# --- Fetch Data ---
def fetch_activity_logs(conn):
    query = """
    SELECT timestamp, username, action, details 
    FROM activity_log 
    WHERE action LIKE '%payment%' 
       OR action LIKE '%price%' 
       OR action LIKE '%approved%' 
       OR action LIKE '%rejected%'
    ORDER BY timestamp DESC 
    LIMIT 1000
    """
    return conn.query(query)

all_transactions = fetch_all_transactions(conn, start_date_filter)
overview_df = fetch_payment_overview(conn, start_date_filter)

# Define Tabs
tab_overview, tab_history, tab_logs = st.tabs(["📊 Payment Overview", "🧾 Recent Transactions", "📜 Payment Logs"])

with tab_overview:
    if not overview_df.empty:
        
        pending_txns = all_transactions[all_transactions['status'] == 'Pending']

        # --- Pending Approvals Section ---
        if not pending_txns.empty:
            # Title with Badge
            st.markdown(f"<h5><span class='header-status-badge-orange'>Pending Approvals <span class='badge-count'>{len(pending_txns)}</span></span></h5>", 
                        unsafe_allow_html=True)
            
            with st.container(border=True):
                # Table Header
                column_sizes_app = [0.5, 3, 1.2, 1.2, 1, 0.8]
                st.markdown('<div class="header-row">', unsafe_allow_html=True)
                h_cols_app = st.columns(column_sizes_app)
                headers_app = ["Book ID", "Title / Author", "Date", "Requested By", "Amount", "Action"]
                for i, h in enumerate(headers_app):
                    h_cols_app[i].markdown(f'<div class="header">{h}</div>', unsafe_allow_html=True)
                st.markdown('</div><div class="header-line"></div>', unsafe_allow_html=True)

                # Group pending by book
                pending_groups = pending_txns.groupby(['book_id', 'title'])

                for (bid, btitle), p_group in pending_groups:
                    # Book Summary Row
                    b_cols = st.columns(column_sizes_app, vertical_alignment="center")
                    with b_cols[0]: st.markdown(f"**{bid}**")
                    with b_cols[1]: st.markdown(f"**{btitle}**")
                    with b_cols[4]: st.markdown(f"**₹{p_group['amount'].sum():,.0f}**")
                    
                    # Individual Payment Rows
                    for _, p_row in p_group.iterrows():
                        row_cols = st.columns(column_sizes_app, vertical_alignment="center")
                        with row_cols[0]: st.write("") # Indent
                        with row_cols[1]: st.markdown(f"↳ {p_row['author_name']}")
                        with row_cols[2]: st.write(p_row['payment_date'].strftime('%d %b %Y'))
                        with row_cols[3]: st.markdown(f'<span class="pill" style="background-color:#e9ecef; color:#495057;">{p_row["requested_by"] or "Unknown"}</span>', unsafe_allow_html=True)
                        with row_cols[4]: st.write(f"₹{p_row['amount']:,.0f}")
                        with row_cols[5]:
                            if st.button("Review", key=f"rev_{p_row['id']}", help="View Details & Approve/Reject", type="secondary"):
                                show_approval_dialog(p_row, conn)
            st.write("")

        # --- Payment Overview (Hierarchical View) ---
        
        # Filter Logic
        filtered_overview = overview_df.copy()
        
        if search_query:
            s = search_query.lower()
            filtered_overview = filtered_overview[
                filtered_overview['book_id'].astype(str).str.lower().str.contains(s) |
                filtered_overview['title'].astype(str).str.lower().str.contains(s) |
                filtered_overview['author_name'].astype(str).str.lower().str.contains(s)
            ]

        # Pre-filter by view_filter to make pagination accurate
        book_ids_to_keep = []
        temp_groups = filtered_overview.groupby('book_id')
        for b_id, group in temp_groups:
            total_book_due = group['amount_due'].sum()
            total_book_paid = group['amount_paid'].sum()
            total_book_pending = group['amount_pending'].sum()
            
            show = True
            if view_filter == "Pending Payments":
                if total_book_pending == 0: show = False
            elif view_filter == "Unpaid Authors":
                if total_book_paid >= total_book_due: show = False
            elif view_filter == "Fully Paid":
                if total_book_paid < total_book_due or total_book_due == 0: show = False
                
            if show:
                book_ids_to_keep.append(b_id)
                
        filtered_overview = filtered_overview[filtered_overview['book_id'].isin(book_ids_to_keep)]

        # Group by Book
        book_groups = list(filtered_overview.groupby(['book_id', 'title', 'book_price'], sort=False))
        
        if not book_groups:
            st.info("No records match your search or filter.")
        else:
            # Pagination Logic
            items_per_page = 40
            total_books = len(book_groups)
            total_pages = max(1, (total_books + items_per_page - 1) // items_per_page)

            # Initialize or validate session state page
            if 'pay_page' not in st.session_state:
                st.session_state.pay_page = 0
            
            if st.session_state.pay_page >= total_pages:
                st.session_state.pay_page = total_pages - 1
            elif st.session_state.pay_page < 0:
                st.session_state.pay_page = 0

            start_idx = st.session_state.pay_page * items_per_page
            end_idx = start_idx + items_per_page
            
            # Display Table
            with st.container(border=True):
                # Title with Badge
                st.markdown(f"<h5><span class='header-status-badge-green'>Books Payment List <span class='badge-count'>{len(book_groups)}</span></span></h5>", 
                            unsafe_allow_html=True)
                
                st.markdown('<div class="header-row">', unsafe_allow_html=True)
                # Table Header
                column_sizes_main = [0.6, 3, 0.8, 0.8, 0.8, 0.8, 0.8]
                h_cols_main = st.columns(column_sizes_main)
                headers_main = ["Book ID", "Book Title", "Status", "Total", "Paid", "Balance", "Action"]
                for i, h in enumerate(headers_main):
                    h_cols_main[i].markdown(f'<div class="header">{h}</div>', unsafe_allow_html=True)
                st.markdown('</div><div class="header-line"></div>', unsafe_allow_html=True)

                for (book_id, title, price), group in book_groups[start_idx:end_idx]:
                    # Aggregations for the book
                    total_paid = group['amount_paid'].sum()
                    total_due = group['amount_due'].sum()
                    total_pending = group['amount_pending'].sum()
                    author_count = len(group)
                    
                    # Determine Status Pill
                    if total_pending > 0:
                        status_pill = f'<span class="status-badge-yellow">Approval Pending</span>'
                    elif total_paid >= total_due and total_due > 0:
                        status_pill = f'<span class="status-badge-green">Complete</span>'
                    elif total_paid > 0:
                        status_pill = f'<span class="status-badge-orange">Partial</span>'
                    else:
                        status_pill = f'<span class="status-badge-red">Pending</span>'

                    # Render Book Row
                    row_cols = st.columns(column_sizes_main, vertical_alignment="center")
                    with row_cols[0]: st.markdown(f"**{book_id}**")
                    with row_cols[1]: st.markdown(f"**{title}**")
                    with row_cols[2]: st.markdown(status_pill, unsafe_allow_html=True)
                    with row_cols[3]: st.markdown(f"**₹{price if pd.notna(price) else 0:,.0f}**")
                    with row_cols[4]: st.markdown(f"**₹{total_paid:,.0f}**")
                    with row_cols[5]: st.markdown(f"**₹{max(0, total_due - total_paid):,.0f}**")
                    with row_cols[6]:
                        btn_c1, btn_c2 = st.columns([1,1])
                        with btn_c1:
                            if st.button(":material/visibility:", key=f"view_{book_id}", help="View Details"):
                                show_book_payment_details(book_id, title, price, group, all_transactions, conn)
                        with btn_c2:
                            if st.button(":material/currency_rupee:", key=f"man_{book_id}", help="Manage Price & Payments"):
                                manage_price_dialog(book_id, conn)
                    
                    # Render Author Rows (Grouped by Agent)
                    group['agent_clean'] = group['corresponding_agent'].fillna('').str.strip()
                    all_agents_set = set(group[group['agent_clean'] != '']['agent_clean'])
                    
                    def assign_disp_group(row):
                        if row['agent_clean'] != '': return row['agent_clean']
                        if row['author_name'] in all_agents_set: return row['author_name']
                        return f"INDV_{row['book_author_id']}"
                    
                    group['disp_group'] = group.apply(assign_disp_group, axis=1)
                    disp_groups = group.groupby('disp_group')

                    for dg_id, dg_df in disp_groups:
                        is_dg_group = not dg_id.startswith("INDV_")
                        dg_name = dg_id if is_dg_group else dg_df.iloc[0]['author_name']
                        
                        dg_paid = dg_df['amount_paid'].sum()
                        dg_due = dg_df['amount_due'].sum()
                        dg_pending = dg_df['amount_pending'].sum()
                        dg_balance = max(0, dg_due - dg_paid)
                        
                        if dg_pending > 0: dg_status = "🟡 Processing"
                        elif dg_paid >= dg_due and dg_due > 0: dg_status = "✅ Paid"
                        elif dg_paid > 0: dg_status = "🟠 Partial"
                        else: dg_status = "🔴 Unpaid"

                        a_cols = st.columns(column_sizes_main, vertical_alignment="center")
                        with a_cols[0]: st.write("") # Indent
                        with a_cols[1]: 
                            st.markdown(f"↳ {'👥' if is_dg_group else ''} {dg_name}")
                            if is_dg_group: st.caption(f"Covers: {', '.join(dg_df['author_name'].tolist())}")
                        with a_cols[2]: st.caption(dg_status)
                        with a_cols[3]: st.markdown(f"<span style='color:#666'>₹{dg_due:,.0f}</span>", unsafe_allow_html=True)
                        with a_cols[4]: st.markdown(f"<span style='color:#2e7d32'>₹{dg_paid:,.0f}</span>", unsafe_allow_html=True)
                        with a_cols[5]: st.markdown(f"<span style='color:#d32f2f'>₹{dg_balance:,.0f}</span>", unsafe_allow_html=True)
                        with a_cols[6]: st.write("")

                    st.markdown("<hr style='margin: 5px 0; border: 0.1px solid #f8f9fa;'>", unsafe_allow_html=True)

            # Pagination controls at the bottom
            if total_pages > 1:
                st.divider()
                col1, col2, col3, col4 = st.columns([1, 2, 1, 2], vertical_alignment="center")
                
                with col1:
                    if st.session_state.pay_page > 0:
                        if st.button("Previous", key="prev_pay_button"):
                            st.session_state.pay_page -= 1
                            st.rerun()
                
                with col2:
                    st.write(f"Page **{st.session_state.pay_page + 1}** of **{total_pages}** (Total: {total_books} books)")
                
                with col3:
                    if st.session_state.pay_page < total_pages - 1:
                        if st.button("Next", key="next_pay_button"):
                            st.session_state.pay_page += 1
                            st.rerun()
                
                with col4:
                    page_options = list(range(1, total_pages + 1))
                    selected_page = st.selectbox(
                        "Go to page",
                        options=page_options,
                        index=st.session_state.pay_page,
                        key="pay_page_selector",
                        label_visibility="collapsed"
                    )
                    if selected_page != st.session_state.pay_page + 1:
                        st.session_state.pay_page = selected_page - 1
                        st.rerun()
    else:
        st.info("No payment data available from selected date.")

with tab_history:
    if not all_transactions.empty:
        # Search for history tab specifically
        hist_search = st.text_input("🔍 Search Transactions", placeholder="Search by Book ID, Author, Txn ID...", key="hist_search_input")
        
        filtered_hist = all_transactions.copy()
        if hist_search:
            hs = hist_search.lower()
            filtered_hist = filtered_hist[
                filtered_hist['book_id'].astype(str).str.lower().str.contains(hs) |
                filtered_hist['title'].astype(str).str.lower().str.contains(hs) |
                filtered_hist['author_name'].astype(str).str.lower().str.contains(hs) |
                filtered_hist['transaction_id'].astype(str).str.lower().str.contains(hs) |
                filtered_hist['requested_by'].astype(str).str.lower().str.contains(hs)
            ]

        # History Pagination Logic
        items_per_page_hist = 40
        total_hist = len(filtered_hist)
        total_pages_hist = max(1, (total_hist + items_per_page_hist - 1) // items_per_page_hist)

        if 'hist_page' not in st.session_state:
            st.session_state.hist_page = 0
        
        # Reset page if search changes
        if 'prev_hist_search' not in st.session_state:
            st.session_state.prev_hist_search = ""
        if hist_search != st.session_state.prev_hist_search:
            st.session_state.hist_page = 0
            st.session_state.prev_hist_search = hist_search

        if st.session_state.hist_page >= total_pages_hist:
            st.session_state.hist_page = total_pages_hist - 1
        
        start_idx_h = st.session_state.hist_page * items_per_page_hist
        end_idx_h = start_idx_h + items_per_page_hist
        paged_hist = filtered_hist.iloc[start_idx_h:end_idx_h]

        with st.container(border=True):
            st.markdown(f"<h5><span class='header-status-badge-orange'>Transaction History <span class='badge-count'>{len(filtered_hist)}</span></span></h5>", 
                        unsafe_allow_html=True)
            
            st.markdown('<div class="header-row">', unsafe_allow_html=True)
            # Table Header
            column_sizes_hist = [1.2, 1, 2.5, 1.2, 1, 1.2, 1.3, 1.3]
            h_cols_hist = st.columns(column_sizes_hist)
            headers_hist = ["Date", "Book ID", "Author / Title", "Amount", "Mode", "Status", "Requested", "Approved"]
            for i, h in enumerate(headers_hist):
                h_cols_hist[i].markdown(f'<div class="header">{h}</div>', unsafe_allow_html=True)
            st.markdown('</div><div class="header-line"></div>', unsafe_allow_html=True)

            for _, row in paged_hist.iterrows():
                r_cols = st.columns(column_sizes_hist, vertical_alignment="center")
                
                # Color status
                status = row['status']
                if status == 'Approved': s_color, s_bg = '#4CAF50', '#E8F5E9'
                elif status == 'Pending': s_color, s_bg = '#FB8C00', '#FFF3E0'
                else: s_color, s_bg = '#F44336', '#FFEBEE'

                with r_cols[0]: st.write(row['payment_date'].strftime('%d %b %Y'))
                with r_cols[1]: st.write(row['book_id'])
                with r_cols[2]: 
                    st.markdown(f"**{row['author_name']}**")
                    st.caption(row['title'])
                with r_cols[3]: st.markdown(f"<span style='color:#2e7d32; font-weight:bold;'>₹{row['amount']:,.0f}</span>", unsafe_allow_html=True)
                with r_cols[4]: st.write(row['payment_mode'])
                with r_cols[5]: 
                    st.markdown(f'<span class="pill" style="background-color:{s_bg}; color:{s_color}; font-weight:bold; border:none;">{status}</span>', unsafe_allow_html=True)
                    if status == 'Rejected' and row['rejection_reason']:
                        st.caption(f"Reason: {row['rejection_reason']}")
                with r_cols[6]: 
                    st.markdown(f'<span class="pill" style="background-color:#f8f9fa; color:#6c757d; font-size:11px;">{row["requested_by"] or "Unknown"}</span>', unsafe_allow_html=True)
                    if row['transaction_id']: st.caption(f"Txn: {row['transaction_id']}")
                with r_cols[7]:
                    if row['approved_by']:
                        st.markdown(f'<span class="pill" style="background-color:#E8F5E9; color:#2e7d32; font-size:11px;">{row["approved_by"]}</span>', unsafe_allow_html=True)
                        if row['approved_at']:
                            st.caption(pd.to_datetime(row['approved_at']).strftime('%d %b, %H:%M'))
                    else:
                        st.write("-")
                
                st.markdown("<hr style='margin: 5px 0; border: 0.1px solid #f8f9fa;'>", unsafe_allow_html=True)

        # Pagination controls for History
        if total_pages_hist > 1:
            st.divider()
            h_col1, h_col2, h_col3, h_col4 = st.columns([1, 2, 1, 2], vertical_alignment="center")
            
            with h_col1:
                if st.session_state.hist_page > 0:
                    if st.button("Previous", key="prev_hist_button"):
                        st.session_state.hist_page -= 1
                        st.rerun()
            
            with h_col2:
                st.write(f"Page **{st.session_state.hist_page + 1}** of **{total_pages_hist}** (Total: {total_hist} transactions)")
            
            with h_col3:
                if st.session_state.hist_page < total_pages_hist - 1:
                    if st.button("Next", key="next_hist_button"):
                        st.session_state.hist_page += 1
                        st.rerun()
            
            with h_col4:
                h_page_options = list(range(1, total_pages_hist + 1))
                h_selected_page = st.selectbox(
                    "Go to page",
                    options=h_page_options,
                    index=st.session_state.hist_page,
                    key="hist_page_selector",
                    label_visibility="collapsed"
                )
                if h_selected_page != st.session_state.hist_page + 1:
                        st.session_state.hist_page = h_selected_page - 1
                        st.rerun()
                else:
                    st.info("No transactions found for the selected period.")
                
with tab_logs:
    logs_df = fetch_activity_logs(conn)
    if not logs_df.empty:
        log_search = st.text_input("🔍 Search Logs", placeholder="Search by user, activity or details...", key="log_search_input")
        
        filtered_logs = logs_df.copy()
        if log_search:
            ls = log_search.lower()
            filtered_logs = filtered_logs[
                filtered_logs['username'].astype(str).str.lower().str.contains(ls) |
                filtered_logs['action'].astype(str).str.lower().str.contains(ls) |
                filtered_logs['details'].astype(str).str.lower().str.contains(ls)
            ]

        # Logs Pagination
        items_per_page_logs = 50
        total_logs = len(filtered_logs)
        total_pages_logs = max(1, (total_logs + items_per_page_logs - 1) // items_per_page_logs)

        if 'log_page' not in st.session_state:
            st.session_state.log_page = 0
        
        if log_search != st.session_state.get('prev_log_search', ''):
            st.session_state.log_page = 0
            st.session_state.prev_log_search = log_search

        if st.session_state.log_page >= total_pages_logs:
            st.session_state.log_page = total_pages_logs - 1
        
        start_idx_l = st.session_state.log_page * items_per_page_logs
        end_idx_l = start_idx_l + items_per_page_logs
        paged_logs = filtered_logs.iloc[start_idx_l:end_idx_l]

        with st.container(border=True):
            st.markdown(f"<h5><span class='header-status-badge-green'>Payment Logs <span class='badge-count'>{len(filtered_logs)}</span></span></h5>", 
                        unsafe_allow_html=True)
            
            st.markdown('<div class="header-row">', unsafe_allow_html=True)
            l_cols_h = st.columns([1.5, 1.5, 2, 5])
            l_headers = ["Timestamp", "User", "Action", "Details"]
            for i, h in enumerate(l_headers):
                l_cols_h[i].markdown(f'<div class="header">{h}</div>', unsafe_allow_html=True)
            st.markdown('</div><div class="header-line"></div>', unsafe_allow_html=True)

            for _, row in paged_logs.iterrows():
                r_cols = st.columns([1.5, 1.5, 2, 5], vertical_alignment="center")
                with r_cols[0]: 
                    st.write(pd.to_datetime(row['timestamp']).strftime('%d %b, %H:%M'))
                with r_cols[1]: 
                    st.markdown(f"**{row['username']}**")
                with r_cols[2]: 
                    st.markdown(f"*{row['action']}*")
                with r_cols[3]: 
                    st.write(row['details'])

        if total_pages_logs > 1:
            st.divider()
            l_col1, l_col2, l_col3 = st.columns([1, 4, 1], vertical_alignment="center")
            with l_col1:
                if st.button("Previous", key="prev_log_btn", disabled=st.session_state.log_page == 0):
                    st.session_state.log_page -= 1
                    st.rerun()
            with l_col2:
                st.write(f"<div style='text-align:center;'>Page {st.session_state.log_page + 1} of {total_pages_logs}</div>", unsafe_allow_html=True)
            with l_col3:
                if st.button("Next", key="next_log_btn", disabled=st.session_state.log_page == total_pages_logs - 1):
                    st.session_state.log_page += 1
                    st.rerun()
    else:
        st.info("No activity logs found.")
                