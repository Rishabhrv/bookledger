import streamlit as st
import pandas as pd
from sqlalchemy.sql import text
from datetime import datetime
import altair as alt
from time import sleep
from auth import validate_token
from constants import connect_db, connect_db_ag, log_activity, initialize_click_and_session_id

#Set page configuration
st.set_page_config(
    layout="wide",  # Set layout to wide mode
    page_title="Academic Guru",
    page_icon="🎓"
)

st.markdown("""
    <style>
            
        /* Remove Streamlit's default top padding */
        .main > div {
            padding-top: 0px !important;
        }
        /* Ensure the first element has minimal spacing */
        .block-container {
            padding-top: 7px !important;  /* Small padding for breathing room */
        }
            """, unsafe_allow_html=True)

# ==============================================================================
# Validation
# ==============================================================================

validate_token()
initialize_click_and_session_id()

user_role = st.session_state.get("role", None)
username = st.session_state.get("username", "Unknown")
user_app = st.session_state.get("app", None)
user_access = st.session_state.get("access", None)
token = st.session_state.token

# Initialize session state
if "logged_click_ids" not in st.session_state:
    st.session_state.logged_click_ids = set()
if "activity_logged" not in st.session_state:
    st.session_state.activity_logged = False

users_conn = connect_db()
conn = connect_db_ag()

click_id = st.session_state.get("click_id", None)
session_id = st.session_state.get("session_id", None)


# Log page access if coming from main page and click_id is new
if user_app in ["main", "tasks"] and click_id and click_id not in st.session_state.logged_click_ids:
    try:
        log_activity(
            users_conn,
            st.session_state.user_id,
            st.session_state.username,
            session_id,
            "navigated to page",
            f"Page: Academic Guru",
        )
        st.session_state.logged_click_ids.add(click_id)
    except Exception as e:
        st.error(f"Error logging navigation: {str(e)}")


# ==============================================================================
# CSS STYLES
# ==============================================================================
st.markdown("""
    <style>
    .data-row {
        margin-bottom: 0px;
        font-size: 14px;
        color: #212529;
        padding: 12px 0;
        transition: background-color 0.2s ease;
    }
    .data-row:hover {
        background-color: #f8f9fa;
    }
    .client-name {
        font-weight: 600;
        color: #333;
    }
    .client-sub {
        font-size: 12px;
        color: #666;
        margin-top: 2px;
    }
    .month-header {
        font-size: 15px;
        font-weight: 600;
        color: #2c3e50;
        padding: 5px 12px;
        border-left: 4px solid #e74c3c;
        margin: 20px 0 15px;
        border-radius: 4px;
    }
    .topic-text {
        font-weight: 500;
        color: #2c3e50;
    }
    .branch-text {
        font-size: 11px;
        font-weight: 500;
        color: #5c7cfa;
        background-color: #f8f9ff;
        border: 1px solid #e0e7ff;
        padding: 1px 8px;
        border-radius: 12px;
        display: inline-block;
        margin-bottom: 4px;
        letter-spacing: 0.3px;
    }
    .services-text {
        font-size: 12px;
        color: #555;
        font-style: italic;
    }
    .assignee-badge {
        font-size: 11px;
        font-weight: 600;
        color: #495057;
        background-color: #f8f9fa;
        padding: 2px 10px;
        border-radius: 20px;
        display: inline-flex;
        align-items: center;
        border: 1px solid #dee2e6;
        margin-left: 8px;
        vertical-align: middle;
    }
    .table-header {
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        color: #6c757d;
        padding: 10px 0;
        border-bottom: 2px solid #dee2e6;
        margin-bottom: 10px;
    }
    .row-divider {
        border-top: 1px solid #e9ecef;
        margin: 0;
        padding: 0;
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
        text-align: center;
        min-width: 80px;
    }
    /* Status Badges */
    .badge-new { background-color: #E3F2FD; color: #1976D2; }            /* Blue */
    .badge-in-progress { background-color: #FBE9E7; color: #D84315; }     /* Indigo */
    .badge-completed { background-color: #E8F5E9; color: #2E7D32; }      /* Green */
    .badge-changes-required { background-color: #E8EAF6; color: #3949AB; } /* Deep Orange */
    .badge-on-hold { background-color: #F5F5F5; color: #616161; border: 1px solid #E0E0E0; } /* Grey */
    .badge-cancelled { background-color: #FFEBEE; color: #C62828; }      /* Red */
    
    /* Payment Badges */
    .badge-paid { background-color: #E8F5E9; color: #2E7D32; }
    .badge-unpaid { background-color: #FFEBEE; color: #C62828; }
    .badge-partial { background-color: #FFF3E0; color: #EF6C00; }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:FILL@1" rel="stylesheet" />
""", unsafe_allow_html=True)

# ==============================================================================
# DATA FETCHING
# ==============================================================================

def fetch_orders(conn):
    try:
        query = """
            SELECT 
                o.order_id,
                c.full_name,
                c.university,
                c.phone,
                o.branch,
                o.title_topic,
                o.deadline,
                o.total_amount,
                o.payment_status,
                o.status as order_status,
                o.created_at,
                o.assignee,
                (SELECT COALESCE(SUM(amount), 0) FROM order_payments WHERE order_id = o.order_id) as total_paid,
                GROUP_CONCAT(CONCAT(COALESCE(os.custom_name, s.service_name), '||', os.status) SEPARATOR ', ') as services_list,
                GROUP_CONCAT(os.status SEPARATOR ',') as service_statuses
            FROM orders o
            JOIN clients c ON o.client_id = c.client_id
            LEFT JOIN order_services os ON o.order_id = os.order_id
            LEFT JOIN services s ON os.service_id = s.service_id
            GROUP BY o.order_id, c.full_name, c.university, c.phone, o.branch, o.title_topic, o.deadline, o.total_amount, o.payment_status, o.status, o.created_at, o.assignee
            ORDER BY o.order_id DESC
        """
        df = conn.query(query, ttl=0)
        
        if not df.empty:
            df['deadline'] = pd.to_datetime(df['deadline'])
            df['created_at'] = pd.to_datetime(df['created_at'])

            def get_derived_status(row):
                if not row['service_statuses']: return 'New'
                statuses = str(row['service_statuses']).split(',')
                
                if 'CHANGES_REQUIRED' in statuses: return 'Changes Required'
                if 'IN_PROGRESS' in statuses: return 'In Progress'
                
                # Mixed progress check
                has_completed = 'COMPLETED' in statuses
                has_not_started = 'NOT_STARTED' in statuses
                if has_completed and has_not_started: return 'In Progress'
                
                if 'ON_HOLD' in statuses: return 'On Hold'
                if all(s == 'COMPLETED' for s in statuses): return 'Completed'
                if all(s == 'NOT_STARTED' for s in statuses): return 'New'
                
                return 'In Progress'

            df['order_status'] = df.apply(get_derived_status, axis=1)
            
        return df
    except Exception as e:
        st.error(f"Error fetching orders: {e}")
        return pd.DataFrame()

# ==============================================================================
# HELPERS
# ==============================================================================
def render_status_badge(status):
    badge_class = f"badge-{status.lower().replace(' ', '-')}"
    return f'<span class="badge {badge_class}">{status}</span>'

def fetch_all_usernames(conn):
    try:
        with conn.session as s:
            users_res = s.execute(text("SELECT username FROM userss ORDER BY username"))
            users = [row[0] for row in users_res]
            return users
    except Exception as e:
        st.error(f"User Fetch Error: {e}")
        return []

def get_service_options(conn):
    try:
        df = conn.query("SELECT service_name FROM services ORDER BY service_name", ttl=0)
        return df['service_name'].tolist()
    except Exception as e:
        st.error(f"Error fetching services: {e}")
        return []

# ==============================================================================
# FILTERS
# ==============================================================================

def all_filters(df):
    if 'filters' not in st.session_state:
        st.session_state.filters = {'status': None, 'payment': None}

    col1, col2, col3, col4 = st.columns([4, 4, 2, 1], vertical_alignment="center")
    
    with col1:
        search_query = st.text_input(
            "Search",
            placeholder="Search by Client, Topic, ID or Assignee...",
            label_visibility="collapsed",
            key="search_input"
        )
        
    with col2:
        with st.popover("Filters", width="stretch"):
            if st.button("Reset Filters", width="stretch"):
                st.session_state.filters = {'status': None, 'payment': None}
                st.session_state.page = 0
                st.rerun()
                
            st.session_state.filters['status'] = st.pills(
                "Status", 
                options=['New', 'In Progress', 'On Hold', 'Changes Required', 'Completed'],
                default=st.session_state.filters['status']
            )
            
            st.session_state.filters['payment'] = st.pills(
                "Payment", 
                options=['PENDING', 'PAID', 'PARTIAL'],
                default=st.session_state.filters['payment']
            )

    with col3:
        if st.button("➕ New Order", type="primary", use_container_width=True):
            add_order_dialog(conn, users_conn)

    with col4:
        with st.popover("Settings", use_container_width=True):
            if st.button("Edit Client", use_container_width=True, type="tertiary"):
                edit_client_dialog(conn)
            if st.button("Edit Services", use_container_width=True, type="tertiary"):
                manage_services_config_dialog(conn)

    filtered_df = df.copy()
    if search_query:
        search_query = search_query.lower()
        filtered_df = filtered_df[
            filtered_df['full_name'].str.lower().str.contains(search_query) |
            filtered_df['title_topic'].str.lower().str.contains(search_query) |
            filtered_df['order_id'].astype(str).str.contains(search_query) |
            filtered_df['assignee'].astype(str).str.lower().str.contains(search_query)
        ]
    
    if st.session_state.filters['status']:
        filtered_df = filtered_df[filtered_df['order_status'] == st.session_state.filters['status']]
        
    if st.session_state.filters['payment']:
        filtered_df = filtered_df[filtered_df['payment_status'] == st.session_state.filters['payment']]

    return filtered_df

# ==============================================================================
# DIALOGS
# ==============================================================================

# CSS Styles for this dialog
st.markdown("""
    <style>
    .pay-card {
        background: #fff;
        padding: 8px;
        border-radius: 10px;
        border: 1px solid #eee;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .pay-label {
        font-size: 0.85rem;
        color: #666;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
    }
    .pay-val {
        font-size: 1.5rem;
        font-weight: 700;
        color: #2c3e50;
    }
    .pay-val.due { color: #d32f2f; }
    .pay-val.paid { color: #2e7d32; }
    
    .history-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 0;
        border-bottom: 1px solid #f1f1f1;
    }
    .history-amt { font-weight: 600; color: #333; font-size: 1.1rem; }
    .history-date { color: #888; font-size: 0.9rem; }
    .history-idx { 
        background: #f8f9fa; color: #666; 
        padding: 2px 8px; border-radius: 4px; 
        font-size: 0.8rem; font-weight: 500;
    }
    </style>
""", unsafe_allow_html=True)

@st.dialog("Update Payment", on_dismiss="rerun", width="medium")
def payment_dialog(order_id, conn):

    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"<h3 style='color:#4CAF50;'>Order ID: {order_id}</h3>", 
                    unsafe_allow_html=True)
    with col2:
        if st.button(":material/refresh: Refresh", key="refresh_payment", type="tertiary"):
            st.cache_data.clear()
    try:
        with conn.session as session:
            query = text("SELECT total_amount FROM orders WHERE order_id = :order_id")
            result = session.execute(query, {'order_id': order_id}).fetchone()
            current_total_amount = result.total_amount if result and result.total_amount else 0

            payments_query = text("SELECT payment_id, amount, payment_date FROM order_payments WHERE order_id = :order_id ORDER BY created_at")
            payments = session.execute(payments_query, {'order_id': order_id}).fetchall()
            
            total_paid = sum(p.amount for p in payments)
            due_amount = max(0, current_total_amount - total_paid)
            
            # Metrics Section
            c1, c2, c3 = st.columns(3, gap="medium")
            with c1:
                st.markdown(f"""
                    <div class="pay-card">
                        <div class="pay-label">Total Amount</div>
                        <div class="pay-val">₹{current_total_amount:,.0f}</div>
                    </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                    <div class="pay-card">
                        <div class="pay-label">Total Paid</div>
                        <div class="pay-val paid">₹{total_paid:,.0f}</div>
                    </div>
                """, unsafe_allow_html=True)
            with c3:
                color_class = "due" if due_amount > 0 else "paid"
                st.markdown(f"""
                    <div class="pay-card">
                        <div class="pay-label">Due Amount</div>
                        <div class="pay-val {color_class}">₹{due_amount:,.0f}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            
    except Exception as e:
        st.error(f"Error fetching payment data: {e}")
        current_total_amount = 0
        payments = []
        total_paid = 0
    
    st.write("")

    new_total_amount = st.number_input(
        "Total Payment Amount (₹)",
        min_value=0.0,
        step=500.0,
        format="%.2f",
        value=float(current_total_amount) if current_total_amount else 0.0,
        key=f"total_payment_{order_id}"
    )

    if new_total_amount != current_total_amount:
         if st.button("Update Total Amount", key=f"update_total_{order_id}"):
            with conn.session as session:
                 session.execute(text("UPDATE orders SET total_amount = :amt WHERE order_id = :oid"),
                                 {'amt': new_total_amount, 'oid': order_id})
                 session.commit()
            st.success("Total amount updated.")


    if total_paid < new_total_amount and len(payments) < 10:
        st.subheader("Add New Payment")
        with st.form(key=f"add_payment_form_{order_id}"):
            c_add1, c_add2 = st.columns(2)
            with c_add1:
                new_payment_amount = st.number_input("Amount (₹)", min_value=0.0, step=500.0, format="%.2f")
            with c_add2:
                new_payment_date = st.date_input("Payment Date", value=datetime.now())
                
            submit_payment = st.form_submit_button("Add Payment")
            
            if submit_payment:
                if new_payment_amount > 0:
                    try:
                        with conn.session as session:
                            session.execute(text("""
                                INSERT INTO order_payments (order_id, amount, payment_date)
                                VALUES (:oid, :amt, :dt)
                            """), {'oid': order_id, 'amt': new_payment_amount, 'dt': new_payment_date})
                            
                            updated_paid = total_paid + new_payment_amount
                            new_status = 'PENDING'
                            if updated_paid >= new_total_amount:
                                new_status = 'Completed'
                            elif updated_paid > 0:
                                new_status = 'PARTIAL'
                                
                            session.execute(text("UPDATE orders SET payment_status = :status WHERE order_id = :oid"),
                                            {'status': new_status, 'oid': order_id})
                            session.commit()
                        st.success("Payment added successfully!")
                    except Exception as e:
                        st.error(f"Error adding payment: {e}")
    elif len(payments) >= 10:
        st.warning("Maximum 10 EMIs reached.")
    elif total_paid >= new_total_amount and new_total_amount > 0:
        st.success("Order is fully paid!")

    st.subheader("Payment History")
    
    if payments:
        for idx, p in enumerate(payments):
            st.markdown(f"""
                <div class="history-row">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span class="history-idx">EMI {idx+1}</span>
                        <span class="history-amt">₹{p.amount:,.0f}</span>
                    </div>
                    <span class="history-date">{p.payment_date}</span>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No payments recorded yet.")



@st.dialog("Service Management", width="large", on_dismiss="rerun")
def manage_services_dialog(order_id, conn, users_conn):
    header_info = f"Order #{order_id}"
    try:
        with conn.session as session:
            h_res = session.execute(text("SELECT o.title_topic, c.full_name FROM orders o JOIN clients c ON o.client_id = c.client_id WHERE o.order_id = :oid"), {'oid': order_id}).fetchone()
            if h_res:
                header_info = f"{h_res[0]} ({h_res[1]})"
    except Exception:
        pass

    st.write(f"### 📋 {header_info} Services")
    
    # 1. FETCH DATA
    users = fetch_all_usernames(users_conn)
    
    query = """
        SELECT os.order_service_id, s.service_name, os.custom_name,
               os.start_date, os.end_date, os.assignee, os.status
        FROM order_services os
        JOIN services s ON os.service_id = s.service_id
        WHERE os.order_id = :oid
    """
    df = conn.query(query, params={'oid': order_id}, ttl=0)
    
    if df.empty:
        st.info("No services found.")
        return

    # 2. PREPARE DATAFRAME FOR UI
    # We map status to emojis to give it "color" since editable cells can't have bg colors
    status_map = {
        'NOT_STARTED': '⚪ NOT STARTED',
        'IN_PROGRESS': '🔵 IN PROGRESS',
        'CHANGES_REQUIRED': '🟡 CHANGES REQUIRED',
        'ON_HOLD': '🟠 ON HOLD',
        'COMPLETED': '🟢 COMPLETED'
    }
    # Reverse map for database saving
    rev_status_map = {v: k for k, v in status_map.items()}
    
    # Format DF for display
    display_df = df.copy()
    display_df['status'] = display_df['status'].map(status_map).fillna('⚪ NOT STARTED')
    display_df['service'] = display_df['custom_name'].fillna(display_df['service_name'])
    
    # 3. CONFIGURE THE EDITOR
    # This turns the table into a smart interface
    edited_df = st.data_editor(
        display_df[['order_service_id', 'service', 'start_date', 'end_date', 'assignee', 'status']],
        column_config={
            "order_service_id": None, # Hide ID
            "service": st.column_config.TextColumn("Service Name", disabled=True, width="medium"),
            "start_date": st.column_config.DatetimeColumn("Start", format="D MMM YYYY, h:mm a"),
            "end_date": st.column_config.DatetimeColumn("End", format="D MMM YYYY, h:mm a"),
            "assignee": st.column_config.SelectboxColumn("Assignee", options=[None] + users, width="small"),
            "status": st.column_config.SelectboxColumn("Status", options=list(status_map.values()), width="medium", required=True),
        },
        hide_index=True,
        use_container_width=True,
        key=f"editor_{order_id}"
    )

    col1, col2 = st.columns([7, 1])

    with col2:
        # 4. SAVE CHANGES
        # We detect changes by comparing the returned dataframe with the original
        if st.button("Save All Changes", type="primary", use_container_width=True):
            changes_found = False
            try:
                with conn.session as session:
                    for idx, row in edited_df.iterrows():
                        # Strip emojis back to DB format
                        clean_status = rev_status_map.get(row['status'], 'NOT_STARTED')
                        
                        session.execute(text("""
                            UPDATE order_services 
                            SET start_date = :s, end_date = :e, assignee = :a, status = :st
                            WHERE order_service_id = :id
                        """), {
                            's': row['start_date'], 'e': row['end_date'],
                            'a': row['assignee'], 'st': clean_status,
                            'id': row['order_service_id']
                        })
                    session.commit()
                    st.success("Saved!")
                    st.toast("Data Saved successfully!", icon="✅")
            except Exception as e:
                st.error(f"Save failed: {e}")
    with col1:
        st.caption("Tip: You can drag column borders to resize or click headers to sort.")


@st.dialog("Add New Academic Work Order", width="large", on_dismiss="rerun")
def add_order_dialog(conn, users_conn):

    col1, col2 = st.columns([1,1.3])

    with col1:
        # --- 1. Client Selection Section ---
        with st.container():
            st.subheader("👤 Client Information")
            
            client_mode = st.radio(
                "Client Type", 
                ["New Client", "Existing Client"], 
                horizontal=True, 
                label_visibility="collapsed",
                index = 0
            )

            if client_mode == "Existing Client":
                with conn.session as s:
                    clients_result = s.execute(text("SELECT client_id, full_name, email FROM clients ORDER BY full_name"))
                    clients = [(row[0], f"{row[1]} ({row[2]})" if row[2] else row[1]) for row in clients_result]
                    clients.insert(0, (None, "-- Select Existing Client --"))

                selected_client = st.selectbox(
                    "Select Client",
                    options=[c[0] for c in clients],
                    format_func=lambda x: next((name for cid, name in clients if cid == x), "-- Select Existing Client --"),
                    key="existing_client_id"
                )
            else:
                col_n1, col_n2 = st.columns(2)
                with col_n1:
                    new_name = st.text_input("Full Name", placeholder="Enter full name")
                    new_phone = st.text_input("Phone / WhatsApp", placeholder="Enter phone number")
                with col_n2:
                    new_email = st.text_input("Email", placeholder="Enter email")
                    new_university = st.text_input("University / College", placeholder="Enter university or college name")


    with col2:
        st.space(40)
        # --- 2. Project Details Section ---
        with st.container():
            st.subheader("📄 Project Details")
            
            col_p1, col_p2 = st.columns([2, 1])
            with col_p1:
                topic = st.text_input("Project / Thesis Topic", placeholder="Machine Learning for Disease Prediction")
            with col_p2:
                branch = st.text_input("Academic Branch", placeholder="Computer Science")

            # Assignee and Logistics in a compact row
            col_l1, col_l2, col_l3 = st.columns(3)
            
            users = fetch_all_usernames(users_conn)
            users.insert(0, None)

            with col_l1:
                assignee = st.selectbox("Assignee", options=users)
            with col_l2:
                registration_date = st.date_input("Order Date", value=datetime.now())
            with col_l3:
                deadline = st.date_input("Final Deadline *", value=None)

    st.write("") # Spacer

    # --- 3. Services & Requirements ---
    with st.container():
        st.subheader("🛠️ Services & Fee")
        
        service_options = get_service_options(conn)

        col1, col2 = st.columns([2, 1])

        with col1:
            selected_services = st.multiselect("Select Services Required", options=service_options)
        with col2:
            total_amount = st.number_input("Agreed Amount (₹)", min_value=0.0, step=500.0)

        # Show journal field only if publishing is selected
        if any("Publishing" in s for s in selected_services):
            journal_name = st.text_input("Journal / Conference Name")
        else:
            journal_name = None

        requirements = st.text_area("Additional Instructions", height=100, placeholder="Specific formatting rules, word count, etc.")

    # --- 4. Submit Action ---
    st.write("") # Spacer
    if st.button("Create New Order", type="primary", use_container_width=True):
        # Validation Logic
        errors = []
        if client_mode == "New Client":
            if not new_name.strip():
                errors.append("Full Name is required.")
            if not new_phone.strip():
                errors.append("Phone / WhatsApp is required.")
        else:
            if not selected_client:
                errors.append("Please select an existing client.")

        if not topic.strip():
            errors.append("Project / Thesis Topic is required.")
        if not branch.strip():
            errors.append("Academic Branch is required.")
        if not deadline:
            errors.append("Final Deadline is required.")
        if not selected_services:
            errors.append("At least one service must be selected.")
        if total_amount <= 0:
            errors.append("Agreed Amount must be greater than 0.")

        if errors:
            for error in errors:
                st.error(error)
            return

        try:
            with conn.session as session:
                # 1. Handle Client ID
                if client_mode == "New Client":
                    result = session.execute(text("""
                        INSERT INTO clients (full_name, email, phone, university)
                        VALUES (:name, :email, :phone, :university)
                    """), {
                        "name": new_name.strip(),
                        "email": new_email.strip() or None,
                        "phone": new_phone.strip() or None,
                        "university": new_university.strip() or None
                    })
                    session.flush()
                    final_client_id = result.lastrowid
                else:
                    final_client_id = selected_client

                # 2. Insert Order
                order_result = session.execute(text("""
                    INSERT INTO orders 
                    (client_id, branch, title_topic, requirements, deadline, total_amount, payment_status, status, created_at, assignee)
                    VALUES 
                    (:client_id, :branch, :topic, :requirements, :deadline, :amount, 'PENDING', 'NEW', :created_at, :assignee)
                """), {
                    "client_id": final_client_id,
                    "branch": branch.strip(),
                    "topic": topic.strip(),
                    "requirements": requirements.strip() or None,
                    "deadline": deadline,
                    "amount": total_amount or None,
                    "created_at": registration_date,
                    "assignee": assignee
                })
                session.flush()
                order_id = order_result.lastrowid

                # 3. Insert Services
                for service_name in selected_services:
                    custom_name = f"{service_name} - {journal_name.strip()}" if journal_name and "Publishing" in service_name else None
                    session.execute(text("""
                        INSERT INTO order_services (order_id, service_id, custom_name, service_deadline, status)
                        VALUES (:order_id, (SELECT service_id FROM services WHERE service_name = :s_name), :c_name, :deadline, 'NOT_STARTED')
                    """), {
                        "order_id": order_id, 
                        "s_name": service_name, 
                        "c_name": custom_name, 
                        "deadline": deadline
                    })

                session.commit()
                st.success(f"✅ Order #{order_id} created successfully!")

        except Exception as e:
            st.error(f"Database Error: {str(e)}")

@st.dialog("Edit Order Details", width="medium", on_dismiss="rerun")
def edit_order_dialog(order_id, conn, users_conn):
    try:
        with conn.session as session:
            order = session.execute(text("""
                SELECT branch, title_topic, requirements, deadline, created_at, assignee 
                FROM orders WHERE order_id = :order_id
            """), {'order_id': order_id}).fetchone()
            
            if not order:
                st.error("Order not found.")
                return

            services_res = session.execute(text("""
                SELECT s.service_name FROM order_services os 
                JOIN services s ON os.service_id = s.service_id 
                WHERE os.order_id = :order_id
            """), {'order_id': order_id}).fetchall()
            existing_services = [row[0] for row in services_res]

    except Exception as e:
        st.error(f"Error fetching order: {e}")
        return

    service_options = get_service_options(conn)

    with st.container():
        # === Assignee ===
        users = fetch_all_usernames(users_conn)
        users.insert(0, None)

        # Find index of current assignee if exists
        try:
            assignee_index = users.index(order.assignee)
        except ValueError:
            assignee_index = 0

        assignee = st.selectbox("Assignee", options=users, index=assignee_index, key=f"edit_assignee_{order_id}")

        col1, col2 = st.columns(2)
        with col1:
            branch = st.text_input("Branch", value=order.branch, key=f"edit_branch_{order_id}")
            registration_date = st.date_input("Order Date", value=order.created_at, key=f"edit_reg_{order_id}")
        with col2:
            topic = st.text_input("Topic", value=order.title_topic, key=f"edit_topic_{order_id}")
            deadline = st.date_input("Deadline", value=order.deadline, key=f"edit_deadline_{order_id}")

        selected_services = st.multiselect(
            "Services",
            options=service_options,
            default=[s for s in existing_services if s in service_options],
            key=f"edit_services_{order_id}"
        )

        requirements = st.text_area("Requirements", value=order.requirements if order.requirements else "", key=f"edit_req_{order_id}")

        st.markdown("---")
        
        col_actions = st.columns([1, 1, 1])
        
        with col_actions[0]:
            if st.button("Update Order", type="primary", use_container_width=True, key=f"update_{order_id}"):
                if not topic.strip() or not branch.strip() or not selected_services:
                    st.error("Missing required fields.")
                else:
                    try:
                        with conn.session as session:
                            session.execute(text("""
                                UPDATE orders 
                                SET branch = :branch, title_topic = :topic, requirements = :req, 
                                    deadline = :deadline, created_at = :created_at, assignee = :assignee
                                WHERE order_id = :order_id
                            """), {
                                'branch': branch, 'topic': topic, 'req': requirements,
                                'deadline': deadline, 'created_at': registration_date,
                                'assignee': assignee, 'order_id': order_id
                            })

                            session.execute(text("DELETE FROM order_services WHERE order_id = :order_id"), {'order_id': order_id})
                            for service_name in selected_services:
                                session.execute(text("""
                                    INSERT INTO order_services 
                                    (order_id, service_id, service_deadline, status)
                                    VALUES 
                                    (:order_id, 
                                     (SELECT service_id FROM services WHERE service_name = :service_name),
                                     :deadline,
                                     'NOT_STARTED')
                                """), {"order_id": order_id, "service_name": service_name, "deadline": deadline})
                            session.commit()
                            st.success("Updated!")
                    except Exception as e:
                        st.error(f"Error: {e}")

        with col_actions[2]:
            if st.button("Delete Order", type="secondary", use_container_width=True, key=f"del_btn_{order_id}"):
                st.session_state[f"confirm_delete_{order_id}"] = True

    if st.session_state.get(f"confirm_delete_{order_id}", False):
        st.error("Are you sure you want to delete this order?")
        if st.button("Yes, Delete", type="primary", key=f"yes_del_{order_id}"):
            try:
                with conn.session as session:
                    session.execute(text("DELETE FROM order_services WHERE order_id = :order_id"), {'order_id': order_id})
                    session.execute(text("DELETE FROM orders WHERE order_id = :order_id"), {'order_id': order_id})
                    session.commit()
                st.success("Deleted.")
            except Exception as e:
                st.error(f"Error: {e}")

@st.dialog("Edit Client Details", width="medium", on_dismiss="rerun")
def edit_client_dialog(conn):
    # Fetch all clients
    try:
        with conn.session as s:
            clients = s.execute(text("SELECT client_id, full_name, email, phone, university FROM clients ORDER BY full_name")).fetchall()
        
        if not clients:
            st.warning("No clients found.")
            return

        client_dict = {c.client_id: c for c in clients}
        client_options = {c.client_id: f"{c.full_name} ({c.university or 'No Uni'})" for c in clients}
        
        selected_id = st.selectbox("Select Client", options=list(client_options.keys()), format_func=lambda x: client_options[x])
        
        if selected_id:
            client = client_dict[selected_id]
            st.write("")
            with st.form("edit_client_form"):
                new_name = st.text_input("Full Name", value=client.full_name)
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    new_phone = st.text_input("Phone / WhatsApp", value=client.phone or "")
                with col_c2:
                    new_email = st.text_input("Email", value=client.email or "")
                
                new_uni = st.text_input("University", value=client.university or "")
                
                if st.form_submit_button("Update Client Details", type="primary"):
                    try:
                        with conn.session as s:
                            s.execute(text("""
                                UPDATE clients 
                                SET full_name = :name, email = :email, phone = :phone, university = :uni
                                WHERE client_id = :cid
                            """), {
                                "name": new_name, "email": new_email or None, 
                                "phone": new_phone or None, "uni": new_uni or None,
                                "cid": selected_id
                            })
                            s.commit()
                        st.success("Client updated successfully!")
                    except Exception as e:
                        st.error(f"Error updating client: {e}")
    except Exception as e:
        st.error(f"Database error: {e}")

@st.dialog("Manage Offered Services", width="medium", on_dismiss="rerun")
def manage_services_config_dialog(conn):
    st.caption("Manage the master list of services offered.")
    
    # --- Add New Service ---
    with st.container():
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        new_svc_name = c1.text_input("Add New Service", placeholder="e.g. Statistical Analysis", label_visibility="visible")
        if c2.button("Add Service", type="primary", use_container_width=True):
            if new_svc_name.strip():
                try:
                    with conn.session as s:
                        s.execute(text("INSERT INTO services (service_name) VALUES (:name)"), {"name": new_svc_name.strip()})
                        s.commit()
                    st.success("Added!")
                except Exception as e:
                    st.error(f"Error adding: {e}")
            else:
                st.warning("Please enter a service name.")
    
    st.divider()

    # --- List Services ---
    try:
        # Fetch directly to list
        with conn.session as s:
            services = s.execute(text("SELECT service_id, service_name FROM services ORDER BY service_name")).fetchall()
        
        if not services:
            st.info("No services defined.")
            return

        for svc in services:
            col1, col2 = st.columns([4, 1], vertical_alignment="center")
            col1.write(svc.service_name)
            if col2.button("🗑️", key=f"del_btn_{svc.service_id}"):
                try:
                    with conn.session as s:
                        s.execute(text("DELETE FROM services WHERE service_id = :id"), {"id": svc.service_id})
                        s.commit()
                except Exception:
                    st.error("Cannot delete (in use).")

    except Exception as e:
        st.error(f"Error loading services: {e}")

# ==============================================================================
# MAIN PAGE
# ==============================================================================


col1,col2= st.columns([11,1], vertical_alignment="bottom")
with col1:
    st.title("Academic Guru 🎓")

with col2:
    if st.button(":material/refresh: Refresh", key="refresh_price", type="tertiary"):
        st.cache_data.clear()

# Load Data
with st.spinner("Fetching orders..."):
    df = fetch_orders(conn)

# Filters and Action Bar
filtered_df = all_filters(df)



with st.expander("📊Overview", expanded=False):
    # Metrics
    if not df.empty:
        st.write("")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Orders", len(df), border=True)
        m2.metric("Pending", len(df[df['order_status'] == 'PENDING']), border=True)
        m3.metric("In Progress", len(df[df['order_status'] == 'IN_PROGRESS']), border=True)
        m4.metric("Completed", len(df[df['order_status'] == 'COMPLETED']), border=True)

st.write("")

col_sizes = [0.4, 0.6, 3, 0.7, 0.7, 0.7, 1]
# Table Header
header_cols = st.columns(col_sizes)
headers = ["ID", "Client", "Topic / Services / Assignee", "Dates", "Payments", "Status", "Actions"]

for col, header in zip(header_cols, headers):
    col.markdown(f'<div class="table-header">{header}</div>', unsafe_allow_html=True)

# Pagination Setup
items_per_page = 40
total_pages = max(1, (len(filtered_df) + items_per_page - 1) // items_per_page)

if 'page' not in st.session_state:
    st.session_state.page = 0

if st.session_state.page >= total_pages:
    st.session_state.page = total_pages - 1
elif total_pages == 0:
    st.session_state.page = 0

start_idx = st.session_state.page * items_per_page
end_idx = start_idx + items_per_page
paginated_df = filtered_df.iloc[start_idx:end_idx]

# Table Rows
if paginated_df.empty:
    st.info("No orders found matching your criteria.")
else:
    # Group by month
    grouped_orders = paginated_df.groupby(pd.Grouper(key='created_at', freq='ME'))
    reversed_grouped_orders = reversed(list(grouped_orders))

    for month, monthly_orders in reversed_grouped_orders:
        if monthly_orders.empty: continue
        
        monthly_orders = monthly_orders.sort_values(by='created_at', ascending=False)
        num_orders = len(monthly_orders)
        
        st.markdown(
            f'<div class="month-header">{month.strftime("%B %Y")} ({num_orders} Orders)</div>',
            unsafe_allow_html=True
        )

        for index, row in monthly_orders.iterrows():
            with st.container():
                cols = st.columns(col_sizes, vertical_alignment="center")
                
                # ID
                cols[0].markdown(f"<span style='color:#888; font-weight:500'>#{row['order_id']}</span>", unsafe_allow_html=True)
                
                # Client & Assignee
                with cols[1]:
                    uni = row['university'] if row['university'] else "Unknown University"
                    phone = row['phone'] if row['phone'] else "No Phone"
                    
                    st.markdown(f"""
                        <div class="client-name">{row['full_name']}</div>
                        <div class="client-sub">
                            <span class="material-symbols-rounded" style="font-size:14px">school</span> {uni}
                        </div>
                        <div class="client-sub">
                            <span class="material-symbols-rounded" style="font-size:14px">call</span> {phone}
                        </div>
                        
                    """, unsafe_allow_html=True)
                    
                # Topic & Services
                with cols[2]:
                    if row['assignee']:
                        assignee_display = f'<span class="assignee-badge"><span class="material-symbols-rounded" style="font-size:14px; margin-right:4px;">person</span>{row["assignee"]}</span>'
                    else:
                        assignee_display = f'<span class="assignee-badge" style="background-color: #fff5f5; color: #e03131; border-color: #ffa8a8;"><span class="material-symbols-rounded" style="font-size:14px; margin-right:4px;">person_off</span>Unassigned</span>'
                    
                    # Parse and Color Code Services
                    colored_services = []
                    if row['services_list']:
                        # Status Color & Symbol Map
                        status_info = {
                            'NOT_STARTED': {'color': '#D32F2F', 'sym': '✘'},      # Red
                            'IN_PROGRESS': {'color': '#1976D2', 'sym': '↻'},      # Blue
                            'CHANGES_REQUIRED': {'color': '#EF6C00', 'sym': '⚠'}, # Orange
                            'ON_HOLD': {'color': '#616161', 'sym': '⏸'},          # Grey
                            'COMPLETED': {'color': '#2E7D32', 'sym': '✔'}         # Green
                        }
                        
                        raw_services = row['services_list'].split(', ')
                        for item in raw_services:
                            if '||' in item:
                                name, status = item.split('||')
                                info = status_info.get(status, {'color': '#555', 'sym': ''})
                                colored_services.append(f'<span style="color:{info["color"]}; font-weight:500;" title="{status.replace("_", " ")}">{info["sym"]} {name}</span>')
                            else:
                                colored_services.append(item)
                    
                    services_html = " ,  ".join(colored_services) if colored_services else 'No services specified'

                    st.markdown(f"""
                        <div class="branch-text">{row['branch']}</div>
                        <div class="topic-text">{row['title_topic']}  {assignee_display}</div>
                        <div class="services-text">{services_html}</div>
                    """, unsafe_allow_html=True)
                    
                # Dates
                with cols[3]:
                    created_str = row['created_at'].strftime('%Y-%m-%d') if pd.notnull(row['created_at']) else "-"
                    deadline_str = row['deadline'].strftime('%Y-%m-%d') if pd.notnull(row['deadline']) else "-"
                    st.markdown(f"""
                        <div style="font-size:12px; color:#888;">Reg: {created_str}</div>
                        <div style="font-size:12px; color:#d9534f; font-weight:600;">Due: {deadline_str}</div>
                    """, unsafe_allow_html=True)
                
                # Amount
                total = row['total_amount'] if row['total_amount'] else 0
                paid = row['total_paid'] if row['total_paid'] else 0
                due = max(0, total - paid)
                
                with cols[4]:
                    if due == 0 and total > 0:
                         st.markdown(f"""
                            <div style="font-weight:600; color:#2E7D32;">Paid</div>
                            <div style="font-size:12px; color:#888;">₹{total:,.0f}</div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                            <div style="font-weight:600; color:#C62828;">₹{due:,.0f} Due</div>
                            <div style="font-size:12px; color:#888;">Total: ₹{total:,.0f}</div>
                        """, unsafe_allow_html=True)
                
                # Status
                with cols[5]:
                    st.markdown(render_status_badge(row['order_status']), unsafe_allow_html=True)
                    
                # Action
                with cols[6]:
                    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1], vertical_alignment="center", gap="small")
                    with btn_col1:
                        if st.button(":material/edit_note:", key=f"edit_{row['order_id']}", help="Edit Order"):
                            edit_order_dialog(row['order_id'], conn, users_conn)
                    with btn_col2:
                        if st.button(":material/currency_rupee:", key=f"pay_{row['order_id']}", help="Payments"):
                            payment_dialog(row['order_id'], conn)
                    with btn_col3:
                         if st.button(":material/design_services:", key=f"services_{row['order_id']}", help="Manage Services"):
                            manage_services_dialog(row['order_id'], conn, users_conn)

                st.markdown('<div class="row-divider"></div>', unsafe_allow_html=True)
                st.markdown('<div class="data-row"></div>', unsafe_allow_html=True)

# Pagination Controls
if total_pages > 1:
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([1, 2, 1, 2], vertical_alignment="center")
    
    with col1:
        if st.session_state.page > 0:
            if st.button("Previous", key="prev_button"):
                st.session_state.page -= 1
                st.rerun()
    
    with col2:
        st.write(f"Page {st.session_state.page + 1} of {total_pages}", unsafe_allow_html=True)
    
    with col3:
        if st.session_state.page < total_pages - 1:
            if st.button("Next", key="next_button"):
                st.session_state.page += 1
                st.rerun()
    
    with col4:
        page_options = list(range(1, total_pages + 1))
        selected_page = st.selectbox(
            "Go to page",
            options=page_options,
            index=st.session_state.page,
            key="page_selector",
            label_visibility="collapsed"
        )
        if selected_page != st.session_state.page + 1:
            st.session_state.page = selected_page - 1
            st.rerun()