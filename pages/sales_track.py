import streamlit as st
import pandas as pd
import time
from datetime import datetime, date
from sqlalchemy import text
from constants import log_activity, initialize_click_and_session_id, connect_db
import uuid
from auth import validate_token
from pages.academic_guru import add_order_dialog

st.set_page_config(page_title='Sales Tracking', page_icon="📈", layout="wide")

logo = "logo/logo_black.png"
small_logo = "logo/favicon_white.ico"

st.logo(logo, size="large", icon_image=small_logo)

# Validate token and initialize session
validate_token()
initialize_click_and_session_id()

# Access control
user_role = st.session_state.get("role", None)
user_app = st.session_state.get("app", None)
user_access = st.session_state.get("access", [])

# Allow Admin or User with 'Inventory' or 'Sales' access
# Adjust permissions as needed based on your specific requirements
if user_role != 'admin' and not (
    user_role == 'user' and 
    user_app == 'main' and 
    ('Inventory' in user_access or 'Sales' in user_access or 'Sales Tracking' in user_access)
):
    st.error("⚠️ Access Denied: You don't have permission to access this page.")
    st.stop()

conn = connect_db()

# Initialize Table
def init_db():
    try:
        with conn.session as s:
            s.execute(text("""
                CREATE TABLE IF NOT EXISTS sales_orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    book_id VARCHAR(255),
                    source ENUM('Amazon', 'Flipkart', 'Website', 'Direct'),
                    quantity INT,
                    order_date DATE,
                    order_id VARCHAR(255),
                    customer_details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            s.commit()
            
            # Check and add new columns if they don't exist
            columns_to_add = [
                ("order_status", "VARCHAR(50) DEFAULT 'New Order'"),
                ("status_date", "DATE"),
                ("customer_name", "VARCHAR(255)"),
                ("customer_phone", "VARCHAR(50)"),
                ("shipping_address", "TEXT"),
                ("corresponding_person", "VARCHAR(255)"),
                ("organization", "VARCHAR(255)"),
                ("city", "VARCHAR(100)"),
                ("discounted_price", "DECIMAL(10,2)")
            ]
            
            for col_name, col_def in columns_to_add:
                try:
                    # Check if column exists
                    check_query = text(f"SHOW COLUMNS FROM sales_orders LIKE '{col_name}'")
                    result = s.execute(check_query).fetchone()
                    if not result:
                        s.execute(text(f"ALTER TABLE sales_orders ADD COLUMN {col_name} {col_def}"))
                        s.commit()
                except Exception as e:
                    st.warning(f"Could not check/add column {col_name}: {e}")

    except Exception as e:
        st.error(f"Error initializing database: {e}")

init_db()

st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #2c3e50;
    }
    .metric-label {
        font-size: 14px;
        color: #6c757d;
    }
    </style>
""", unsafe_allow_html=True)

# Fetch Books for Dropdown
@st.cache_data
def fetch_books():
    query = "SELECT book_id, title, book_mrp FROM books WHERE is_cancelled = 0 ORDER BY title"
    return conn.query(query, show_spinner=False)

books_df = fetch_books()
book_options = {f"{row['title']} (ID: {row['book_id']})": row['book_id'] for _, row in books_df.iterrows()}
book_prices = {row['book_id']: row['book_mrp'] for _, row in books_df.iterrows()}

# Header
col1, col2 = st.columns([11, 1], vertical_alignment="bottom")
with col1:
    st.title("Sales Tracking")
with col2:
    if st.button(":material/refresh: Refresh", key="refresh", type="tertiary"):
        st.cache_data.clear()

# Add New Order Section
@st.dialog("Printed Book Order", width="large", on_dismiss="rerun")
def add_order_dialog():
    st.subheader("Order Details")
    c1, c2, c3 = st.columns(3)
    with c1:
        selected_book_label = st.selectbox("Select Book", options=list(book_options.keys()), index=None, placeholder="Choose a book...")
        # Get MRP for selected book
        selected_mrp = 0.0
        if selected_book_label:
            bid = book_options[selected_book_label]
            selected_mrp = float(book_prices.get(bid, 0.0) or 0.0)
            st.caption(f"MRP: ₹{selected_mrp:,.2f}")

    with c2:
        # Trigger rerun on change to update conditional fields
        source = st.selectbox("Source", ["Amazon", "Flipkart", "Website", "Direct"])
    with c3:
        quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
    
    c4, c5, c6 = st.columns(3)
    with c4:
        discounted_price = None
        if source == "Direct":
            discounted_price = st.number_input("Discounted Price (Per Unit)", min_value=0.0, value=selected_mrp, step=10.0, help="Selling price per book")
    with c5:
        order_date = st.date_input("Order Date", value=datetime.now())
    with c6:
        order_id = st.text_input("Order ID", placeholder="e.g., #12345")
        
    # Status Selection
    status_options = ["New Order", "Shipped", "Delivered", "Returned", "Exchanged"]
    order_status = st.selectbox("Order Status", status_options)

    # Status Date
    date_label = f"{order_status} Date" if order_status != "New Order" else "Status Date"
    status_date = st.date_input(date_label, value=datetime.now(), help=f"Date when order was {order_status}")

    st.divider()
    st.subheader("Customer Details")
    
    city = None
    customer_name = None
    customer_phone = None
    shipping_address = None
    corresponding_person = None
    organization = None
    
    if source in ["Amazon", "Flipkart", "Website"]:
        cc1, cc2 = st.columns(2)
        with cc1:
            customer_name = st.text_input("Customer Name", placeholder="Enter Name")
        with cc2:
            customer_phone = st.text_input("Customer Number", placeholder="Enter Phone Number")
        
        cc3, cc4 = st.columns([1, 2])
        with cc3:
            city = st.text_input("City", placeholder="Enter City")
        with cc4:
            shipping_address = st.text_area("Address", placeholder="Enter Shipping Address", height=68)
        
    elif source == "Direct":
        cc1, cc2 = st.columns(2)
        with cc1:
            corresponding_person = st.text_input("Corresponding Person", placeholder="Person Name")
        with cc2:
            organization = st.text_input("Organization", placeholder="Organization Name")
        
        cc3, cc4 = st.columns([1, 2])
        with cc3:
            city = st.text_input("City", placeholder="Enter City")
        with cc4:
            shipping_address = st.text_area("Location / Address", placeholder="Enter Location or Address", height=68)

    if st.button("Record Sale", type="primary"):
        if not selected_book_label:
            st.error("Please select a book.")
        elif not order_id:
            st.error("Order ID is required.")
        elif not city:
            st.error("City is required.")
        else:
            book_id = book_options[selected_book_label]
            
            # Construct legacy customer_details string for backward compatibility
            details_parts = []
            if customer_name: details_parts.append(f"Name: {customer_name}")
            if customer_phone: details_parts.append(f"Phone: {customer_phone}")
            if city: details_parts.append(f"City: {city}")
            if corresponding_person: details_parts.append(f"Person: {corresponding_person}")
            if organization: details_parts.append(f"Org: {organization}")
            if shipping_address: details_parts.append(f"Addr: {shipping_address}")
            
            # If existing logic used manual input, keep it effectively populated
            customer_details_str = " | ".join(details_parts) if details_parts else ""

            try:
                with conn.session as s:
                    # 1. Insert into sales_orders with new columns
                    s.execute(
                        text("""
                            INSERT INTO sales_orders (
                                book_id, source, quantity, order_date, order_id, customer_details,
                                order_status, status_date, customer_name, customer_phone, 
                                shipping_address, corresponding_person, organization, city, discounted_price
                            )
                            VALUES (
                                :book_id, :source, :quantity, :order_date, :order_id, :customer_details,
                                :order_status, :status_date, :customer_name, :customer_phone, 
                                :shipping_address, :corresponding_person, :organization, :city, :discounted_price
                            )
                        """),
                        {
                            "book_id": book_id,
                            "source": source,
                            "quantity": quantity,
                            "order_date": order_date,
                            "order_id": order_id,
                            "customer_details": customer_details_str,
                            "order_status": order_status,
                            "status_date": status_date,
                            "customer_name": customer_name,
                            "customer_phone": customer_phone,
                            "shipping_address": shipping_address,
                            "corresponding_person": corresponding_person,
                            "organization": organization,
                            "city": city,
                            "discounted_price": discounted_price
                        }
                    )

                    # 2. Update inventory table
                    # Map source to inventory column
                    source_map = {
                        "Amazon": "amazon_sales",
                        "Flipkart": "flipkart_sales",
                        "Website": "website_sales",
                        "Direct": "direct_sales"
                    }
                    inv_col = source_map[source]

                    # Check if inventory record exists
                    exists = s.execute(text("SELECT 1 FROM inventory WHERE book_id = :book_id"), {"book_id": book_id}).fetchone()
                    
                    if exists:
                        s.execute(
                            text(f"UPDATE inventory SET {inv_col} = COALESCE({inv_col}, 0) + :quantity WHERE book_id = :book_id"),
                            {"quantity": quantity, "book_id": book_id}
                        )
                    else:
                        # Create new inventory record
                        s.execute(
                            text(f"INSERT INTO inventory (book_id, {inv_col}) VALUES (:book_id, :quantity)"),
                            {"book_id": book_id, "quantity": quantity}
                        )

                    s.commit()
                
                log_activity(
                    conn,
                    st.session_state.user_id,
                    st.session_state.username,
                    st.session_state.session_id,
                    "recorded sale",
                    f"Book: {book_id}, Source: {source}, Qty: {quantity}, Status: {order_status}"
                )
                st.success("✅ Sale recorded successfully!")
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"Error recording sale: {e}")


# Edit Order Dialog
@st.dialog("Edit Order Details", width="large", on_dismiss="rerun")
def edit_order_dialog(order_data):
    # Helper to safely get string values
    def get_val(val):
        if pd.isna(val) or val is None:
            return ""
        return str(val)

    st.subheader("Order Details")
    c1, c2, c3 = st.columns(3)
    with c1:
        # Display Book as Read-only
        st.text_input("Book", value=f"{order_data['title']} ({order_data['book_id']})", disabled=True)
        book_id = order_data['book_id']
    with c2:
        current_source = order_data['source'] if order_data['source'] in ["Amazon", "Flipkart", "Website", "Direct"] else "Amazon"
        source = st.selectbox("Source", ["Amazon", "Flipkart", "Website", "Direct"], index=["Amazon", "Flipkart", "Website", "Direct"].index(current_source))
    with c3:
        quantity = st.number_input("Quantity", min_value=1, step=1, value=int(order_data['quantity']))
    
    c4, c5, c6 = st.columns(3)
    with c4:
        discounted_price = None
        if source == "Direct":
            current_discount = order_data.get('discounted_price')
            if pd.isna(current_discount): current_discount = 0.0
            discounted_price = st.number_input("Discounted Price", min_value=0.0, value=float(current_discount), step=10.0)
            
        # Handle date conversion if needed
        o_date = order_data['order_date']
        if isinstance(o_date, str):
            try:
                o_date = datetime.strptime(o_date, '%Y-%m-%d').date()
            except:
                o_date = datetime.now().date()
        elif isinstance(o_date, datetime):
            o_date = o_date.date()
        elif o_date is None or pd.isna(o_date):
            o_date = datetime.now().date()
            
    with c5:
        order_date = st.date_input("Order Date", value=o_date)
    with c6:
        order_id = st.text_input("Order ID", value=get_val(order_data['order_id']))

    c7, c8 = st.columns(2)
    with c7:
        status_options = ["New Order", "Shipped", "Delivered", "Returned", "Exchanged"]
        current_status = order_data['order_status'] if order_data['order_status'] in status_options else "New Order"
        order_status = st.selectbox("Order Status", status_options, index=status_options.index(current_status))
    with c8:
        # Status Date
        s_date = order_data['status_date']
        if not s_date or pd.isna(s_date):
            s_date = datetime.now().date()
        elif isinstance(s_date, str):
            try:
                s_date = datetime.strptime(s_date, '%Y-%m-%d').date()
            except:
                 s_date = datetime.now().date()
        elif isinstance(s_date, datetime):
            s_date = s_date.date()
            
        date_label = f"{order_status} Date" if order_status != "New Order" else "Status Date"
        status_date = st.date_input(date_label, value=s_date)

    st.divider()
    st.subheader("Customer Details")
    
    # Extract existing values safely
    cn = get_val(order_data['customer_name'])
    cp = get_val(order_data['customer_phone'])
    sa = get_val(order_data['shipping_address'])
    cperson = get_val(order_data['corresponding_person'])
    org = get_val(order_data['organization'])
    c_city = get_val(order_data.get('city', ''))

    customer_name = None
    customer_phone = None
    shipping_address = None
    corresponding_person = None
    organization = None
    city = None

    # Determine fields to show based on CURRENT selection, defaulting to existing data
    if source in ["Amazon", "Flipkart", "Website"]:
        cc1, cc2 = st.columns(2)
        with cc1:
            customer_name = st.text_input("Customer Name", value=cn)
        with cc2:
            customer_phone = st.text_input("Customer Number", value=cp)
        
        cc3, cc4 = st.columns([1, 2])
        with cc3:
            city = st.text_input("City", value=c_city)
        with cc4:
            shipping_address = st.text_area("Address", value=sa, height=68)
        
    elif source == "Direct":
        cc1, cc2 = st.columns(2)
        with cc1:
            corresponding_person = st.text_input("Corresponding Person", value=cperson)
        with cc2:
            organization = st.text_input("Organization", value=org)
            
        cc3, cc4 = st.columns([1, 2])
        with cc3:
            city = st.text_input("City", value=c_city)
        with cc4:
            shipping_address = st.text_area("Location / Address", value=sa, height=68)

    if st.button("Update Order", type="primary"):
        # Construct legacy string
        details_parts = []
        if customer_name: details_parts.append(f"Name: {customer_name}")
        if customer_phone: details_parts.append(f"Phone: {customer_phone}")
        if city: details_parts.append(f"City: {city}")
        if corresponding_person: details_parts.append(f"Person: {corresponding_person}")
        if organization: details_parts.append(f"Org: {organization}")
        if shipping_address: details_parts.append(f"Addr: {shipping_address}")
        customer_details_str = " | ".join(details_parts) if details_parts else ""

        try:
            with conn.session as s:
                # Update sales_orders
                s.execute(
                    text("""
                        UPDATE sales_orders 
                        SET source = :source, quantity = :quantity, 
                            order_date = :order_date, order_id = :order_id, customer_details = :customer_details,
                            order_status = :order_status, status_date = :status_date, 
                            customer_name = :customer_name, customer_phone = :customer_phone,
                            shipping_address = :shipping_address, corresponding_person = :corresponding_person,
                            organization = :organization, city = :city, discounted_price = :discounted_price
                        WHERE id = :id
                    """),
                    {
                        "id": order_data['id'],
                        "source": source,
                        "quantity": quantity,
                        "order_date": order_date,
                        "order_id": order_id,
                        "customer_details": customer_details_str,
                        "order_status": order_status,
                        "status_date": status_date,
                        "customer_name": customer_name,
                        "customer_phone": customer_phone,
                        "shipping_address": shipping_address,
                        "corresponding_person": corresponding_person,
                        "organization": organization,
                        "city": city,
                        "discounted_price": discounted_price
                    }
                )

                # Handle inventory adjustments
                old_qty = int(order_data['quantity'])
                old_source = order_data['source']
                
                source_map = {
                    "Amazon": "amazon_sales",
                    "Flipkart": "flipkart_sales",
                    "Website": "website_sales",
                    "Direct": "direct_sales"
                }

                # Revert old
                old_inv_col = source_map.get(old_source, "amazon_sales")
                s.execute(
                    text(f"UPDATE inventory SET {old_inv_col} = GREATEST(COALESCE({old_inv_col}, 0) - :qty, 0) WHERE book_id = :book_id"),
                    {"qty": old_qty, "book_id": book_id}
                )

                # Apply new
                new_inv_col = source_map.get(source, "amazon_sales")
                # Check exist
                exists = s.execute(text("SELECT 1 FROM inventory WHERE book_id = :book_id"), {"book_id": book_id}).fetchone()
                if exists:
                    s.execute(
                        text(f"UPDATE inventory SET {new_inv_col} = COALESCE({new_inv_col}, 0) + :qty WHERE book_id = :book_id"),
                        {"qty": quantity, "book_id": book_id}
                    )
                else:
                    s.execute(
                        text(f"INSERT INTO inventory (book_id, {new_inv_col}) VALUES (:book_id, :qty)"),
                        {"book_id": book_id, "qty": quantity}
                    )

                s.commit()
            
            log_activity(
                conn,
                st.session_state.user_id,
                st.session_state.username,
                st.session_state.session_id,
                "updated sale",
                f"Order ID: {order_data['id']}, New Status: {order_status}"
            )
            st.success("✅ Order updated successfully!")
            st.cache_data.clear()
            time.sleep(1)
            st.rerun()

        except Exception as e:
            st.error(f"Error updating order: {e}")


col1, col2, col3 = st.columns([4, 2, 1], vertical_alignment="center")
with col1:
    search_order = st.text_input("Search", placeholder="Search Order ID, Book, Customer, Phone...", label_visibility="collapsed")
with col2:
    with st.popover("Filter Orders", width="stretch"):
        st.caption("Filter Options")
        filter_date_range = st.date_input("Date Range", value=[], help="Select start and end date")
        filter_source = st.multiselect("Source", ["Amazon", "Flipkart", "Website", "Direct"])
        filter_status = st.multiselect("Status", ["New Order", "Shipped", "Delivered", "Returned", "Exchanged"])
        # Book filter
        filter_books = st.multiselect("Book", options=list(book_options.keys()), placeholder="Select specific books")

with col3:
        if st.button("➕ New Order", type="primary", use_container_width=True):
            add_order_dialog()

st.write("")
    
    

# Build Query
base_query = """
    SELECT 
        so.id, so.book_id, b.title, b.book_mrp, so.source, so.quantity, so.order_date, so.order_id, 
        so.customer_details, so.order_status, so.status_date,
        so.customer_name, so.customer_phone, so.shipping_address,
        so.corresponding_person, so.organization, so.city, so.discounted_price
    FROM sales_orders so
    LEFT JOIN books b ON so.book_id = b.book_id
    WHERE 1=1
"""
params = {}

if filter_source:
    base_query += " AND so.source IN :sources"
    params["sources"] = tuple(filter_source)

if filter_status:
    base_query += " AND so.order_status IN :statuses"
    params["statuses"] = tuple(filter_status)

if filter_books:
    # Extract book_ids from selected labels
    selected_book_ids = [book_options[label] for label in filter_books]
    base_query += " AND so.book_id IN :book_ids"
    params["book_ids"] = tuple(selected_book_ids)

if len(filter_date_range) == 2:
    base_query += " AND so.order_date BETWEEN :start_date AND :end_date"
    params["start_date"] = filter_date_range[0]
    params["end_date"] = filter_date_range[1]

if search_order:
    search_term = f"%{search_order}%"
    base_query += """ AND (
        so.order_id LIKE :search OR 
        so.book_id LIKE :search OR 
        b.title LIKE :search OR
        so.customer_name LIKE :search OR
        so.customer_phone LIKE :search OR
        so.organization LIKE :search OR
        so.corresponding_person LIKE :search OR
        so.city LIKE :search
    )"""
    params["search"] = search_term

base_query += " ORDER BY so.order_date DESC, so.created_at DESC"

# Fetch Data
try:
    orders_df = conn.query(base_query, params=params, show_spinner=False)
except Exception as e:
    st.error(f"Error fetching orders: {e}")
    orders_df = pd.DataFrame()

# Metrics Section (Filtered Data)
with st.expander("📊 Filtered Metrics", expanded=True):
    if not orders_df.empty:
        # Define sources to display
        sources = ["Amazon", "Flipkart", "Website", "Direct"]
        cols = st.columns(len(sources) + 1)
        
        # 1. Total Orders
        total_orders = len(orders_df)
        cols[0].metric("Total Orders", total_orders)
        
        # 2. Source-wise Metrics
        source_counts = orders_df['source'].value_counts()
        for i, src in enumerate(sources):
            count = int(source_counts.get(src, 0))
            cols[i+1].metric(f"{src}", count)
            
    else:
        st.info("No data available for metrics.")

# Pagination
total_pages = 0
if not orders_df.empty:
    page_size = 20
    total_items = len(orders_df)
    total_pages = (total_items + page_size - 1) // page_size
    
    if "sales_page" not in st.session_state:
        st.session_state.sales_page = 1
        
    # Ensure current page is valid
    st.session_state.sales_page = max(1, min(st.session_state.sales_page, total_pages))
    
    start_idx = (st.session_state.sales_page - 1) * page_size
    end_idx = min(start_idx + page_size, total_items)
    
    display_df = orders_df.iloc[start_idx:end_idx]

    # Custom Table Display
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
        .source-badge {
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
            color: white;
            display: inline-block;
            margin-right: 5px;
        }
        .city-badge {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
            background-color: #f1f3f5;
            color: #495057;
            border: 1px solid #dee2e6;
            display: inline-block;
        }
        .badge-amazon { background-color: #FF9900; }
        .badge-flipkart { background-color: #2874F0; }
        .badge-website { background-color: #2ecc71; }
        .badge-direct { background-color: #34495e; }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:FILL@1" rel="stylesheet" />
    """, unsafe_allow_html=True)

    col_sizes = [0.8, 2.5, 0.8, 0.8, 0.5, 0.8, 1.0, 1.5, 0.6]
    headers = ["Order ID", "Book", "Date", "Source", "Qty", "Price", "City", "Status", "Action"]

    # Table Header
    header_cols = st.columns(col_sizes)
    for col, header in zip(header_cols, headers):
        col.markdown(f'<div class="table-header">{header}</div>', unsafe_allow_html=True)

    # Group by month
    display_df['order_month'] = pd.to_datetime(display_df['order_date']).dt.to_period('M')
    grouped_orders = display_df.groupby('order_month')
    reversed_grouped_orders = sorted(list(grouped_orders), key=lambda x: x[0], reverse=True)

    for month, monthly_orders in reversed_grouped_orders:
        if monthly_orders.empty: continue
        
        st.markdown(
            f'<div class="month-header">{month.strftime("%B %Y")} ({len(monthly_orders)} Orders)</div>',
            unsafe_allow_html=True
        )

        for _, row in monthly_orders.iterrows():
            with st.container():
                cols = st.columns(col_sizes, vertical_alignment="center")
                
                # Order ID
                cols[0].markdown(f"<span style='color:#888; font-weight:500'>#{row['order_id'] or '-'}</span>", unsafe_allow_html=True)
                
                # Book & Customer
                with cols[1]:
                    cust_info = row['customer_name'] or row['corresponding_person'] or ""
                    cust_suffix = f" <br><small style='color: #6c757d;'>👤 {cust_info}</small>" if cust_info else ""
                    st.markdown(f"""
                        <div class="client-name">{row['title']} <span style="color:#888; font-weight:normal">({row['book_id']})</span></div>
                        {cust_suffix}
                    """, unsafe_allow_html=True)
                
                # Order Date
                cols[2].write(row['order_date'].strftime('%d %b %Y'))

                # Source
                badge_class = f"badge-{row['source'].lower()}"
                cols[3].markdown(f"<span class='source-badge {badge_class}'>{row['source']}</span>", unsafe_allow_html=True)
                
                # Quantity
                cols[4].write(row['quantity'])
                
                # Price
                mrp = float(row['book_mrp'] or 0)
                disc_price = float(row['discounted_price'] or 0)
                
                with cols[5]:
                    if row['source'] == 'Direct' and disc_price > 0 and disc_price != mrp:
                        st.markdown(f"""
                            <div>₹{disc_price:,.0f}</div>
                            <div style="font-size:11px; color:#999; text-decoration:line-through;">₹{mrp:,.0f}</div>
                        """, unsafe_allow_html=True)
                    else:
                        st.write(f"₹{mrp:,.0f}")

                # City (Pill Badge)
                with cols[6]:
                    if row['city']:
                        st.markdown(f"<span class='city-badge'>{row['city']}</span>", unsafe_allow_html=True)
                    else:
                        st.write("-")

                # Status & Status Date
                with cols[7]:
                    status_color_map = {
                        "New Order": "#3498db",
                        "Shipped": "#f39c12",
                        "Delivered": "#27ae60",
                        "Returned": "#e74c3c",
                        "Exchanged": "#9b59b6"
                    }
                    color = status_color_map.get(row['order_status'], "#7f8c8d")
                    status_date_str = row['status_date'].strftime('%d %b %Y') if row['status_date'] else "-"
                    st.markdown(f"""
                        <span style='color: {color}; font-weight: 600; font-size: 13px;'>{row['order_status']}</span>
                        <br><small style='color: #6c757d;'>📅 {status_date_str}</small>
                    """, unsafe_allow_html=True)

                # Action
                with cols[8]:
                    if st.button("✏️", key=f"edit_{row['id']}", help="Edit Order"):
                        edit_order_dialog(row)

                st.markdown('<div class="row-divider"></div>', unsafe_allow_html=True)
                st.markdown('<div class="data-row"></div>', unsafe_allow_html=True)

# Pagination Controls
if total_pages > 1:
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([1, 2, 1, 2], vertical_alignment="center")
    
    with col1:
        if st.button("Previous", disabled=st.session_state.sales_page == 1, key="prev_btn"):
            st.session_state.sales_page -= 1
            st.rerun()
    
    with col2:
        st.write(f"Page {st.session_state.sales_page} of {total_pages}", unsafe_allow_html=True)
    
    with col3:
        if st.button("Next", disabled=st.session_state.sales_page == total_pages, key="next_btn"):
            st.session_state.sales_page += 1
            st.rerun()
            
    with col4:
        page_options = list(range(1, total_pages + 1))
        # Ensure current page is in options
        if st.session_state.sales_page not in page_options:
             st.session_state.sales_page = 1
             
        selected_page = st.selectbox(
            "Go to page",
            options=page_options,
            index=page_options.index(st.session_state.sales_page),
            key="page_selector",
            label_visibility="collapsed"
        )
        if selected_page != st.session_state.sales_page:
            st.session_state.sales_page = selected_page
            st.rerun()

else:
    if orders_df.empty:
        st.info("No orders found.")
