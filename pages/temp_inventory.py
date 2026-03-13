import streamlit as st
import pandas as pd
import time
from auth import validate_token
from constants import connect_db, initialize_click_and_session_id, log_activity
from sqlalchemy import text

# Page configuration
st.set_page_config(page_title='Temporary Inventory Check', page_icon="📋", layout="wide")

# UI styling
st.markdown("""
    <style>
    .main > div {
        padding-top: 1rem !important;
    }
    .header-style {
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .table-header {
        font-weight: bold;
        background-color: #f0f2f6;
        padding: 8px;
        border-bottom: 2px solid #ddd;
    }
    .table-row {
        padding: 8px;
        border-bottom: 1px solid #eee;
    }
    .status-badge {
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
    }
    .status-pending { background-color: #fff3cd; color: #856404; }
    .status-verified { background-color: #d4edda; color: #155724; }
    </style>
    """, unsafe_allow_html=True)

# Authentication and Session Initialization
validate_token()
initialize_click_and_session_id()

if 'pending_page' not in st.session_state:
    st.session_state['pending_page'] = 1
if 'verified_page' not in st.session_state:
    st.session_state['verified_page'] = 1

BOOKS_PER_PAGE = 50

logo = "logo/logo_black.png"
small_logo = "logo/favicon_white.ico"

st.logo(logo, size="large", icon_image=small_logo)

def paginate_dataframe(df, page_key):
    total_pages = (len(df) + BOOKS_PER_PAGE - 1) // BOOKS_PER_PAGE
    if total_pages == 0:
        return df, 1, 0
    
    st.session_state[page_key] = max(1, min(st.session_state[page_key], total_pages))
    start_idx = (st.session_state[page_key] - 1) * BOOKS_PER_PAGE
    end_idx = min(start_idx + BOOKS_PER_PAGE, len(df))
    return df.iloc[start_idx:end_idx], total_pages, len(df)

def render_pagination_controls(page_key, total_pages, total_items):
    if total_pages <= 1:
        return
    
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    with col1:
        if st.button("First", key=f"first_{page_key}", disabled=st.session_state[page_key] == 1):
            st.session_state[page_key] = 1
            st.rerun()
    with col2:
        if st.button("Prev", key=f"prev_{page_key}", disabled=st.session_state[page_key] == 1):
            st.session_state[page_key] -= 1
            st.rerun()
    with col3:
        st.markdown(f"<div style='text-align: center;'>Page {st.session_state[page_key]} of {total_pages}<br>({total_items} items)</div>", unsafe_allow_html=True)
    with col4:
        if st.button("Next", key=f"next_{page_key}", disabled=st.session_state[page_key] == total_pages):
            st.session_state[page_key] += 1
            st.rerun()
    with col5:
        if st.button("Last", key=f"last_{page_key}", disabled=st.session_state[page_key] == total_pages):
            st.session_state[page_key] = total_pages
            st.rerun()

@st.dialog("Update Physical Count", width="medium")
def update_physical_count(book_id, title, current_cell, current_stock, temp_count):
    st.markdown(f"### Update: {title} (ID: {book_id})")
    
    new_cell = st.text_input("Cell Number", value=str(current_cell) if pd.notnull(current_cell) else "")
    new_physical_count = st.number_input("Actual Physical Count", min_value=0, value=int(temp_count), step=1)
    
    st.info(f"System Stock: {current_stock}")

    if st.button("Save & Mark as Verified", type="primary", use_container_width=True):
        conn = connect_db()
        try:
            with conn.session as session:
                # Update or Insert into inventory
                check_query = text("SELECT COUNT(*) FROM inventory WHERE book_id = :book_id")
                exists = session.execute(check_query, {"book_id": book_id}).fetchone()[0]
                
                if exists:
                    update_query = text("""
                        UPDATE inventory 
                        SET rack_number = :rack_number, 
                            temp_physical_count = :temp_count,
                            inventory_check_done = 1
                        WHERE book_id = :book_id
                    """)
                else:
                    update_query = text("""
                        INSERT INTO inventory (book_id, rack_number, temp_physical_count, inventory_check_done)
                        VALUES (:book_id, :rack_number, :temp_count, 1)
                    """)
                
                session.execute(update_query, {
                    "book_id": book_id,
                    "rack_number": new_cell if new_cell else None,
                    "temp_count": new_physical_count
                })
                session.commit()
                
                log_activity(
                    conn,
                    st.session_state.user_id,
                    st.session_state.username,
                    st.session_state.session_id,
                    "updated physical count",
                    f"Book ID: {book_id}, Physical Count: {new_physical_count}, Cell: {new_cell}"
                )
                
                st.success("Updated successfully!")
                time.sleep(1)
                st.cache_data.clear()
                st.rerun()
        except Exception as e:
            st.error(f"Error updating: {str(e)}")

def fetch_inventory_data():
    conn = connect_db()
    query = """
    SELECT
        b.book_id,
        b.title,
        i.rack_number,
        COALESCE(i.temp_physical_count, 0) as temp_physical_count,
        COALESCE(i.inventory_check_done, 0) as inventory_check_done,
        COALESCE(
            (SELECT SUM(bd.copies_in_batch) 
             FROM BatchDetails bd 
             JOIN PrintEditions pe ON bd.print_id = pe.print_id 
             WHERE pe.book_id = b.book_id), 
            0
        ) AS total_printed,
        COALESCE(
            (SELECT SUM(ba.number_of_books) 
             FROM book_authors ba 
             WHERE ba.book_id = b.book_id), 
            0
        ) AS author_copies,
        COALESCE(i.website_sales, 0) AS website_sales,
        COALESCE(i.amazon_sales, 0) AS amazon_sales,
        COALESCE(i.flipkart_sales, 0) AS flipkart_sales,
        COALESCE(i.direct_sales, 0) AS direct_sales
    FROM books b
    LEFT JOIN inventory i ON b.book_id = i.book_id
    WHERE b.deliver = 1
    """
    df = conn.query(query, show_spinner="Fetching inventory data...")
    
    # Fill NaN values for numeric columns to prevent conversion errors
    numeric_cols = ['total_printed', 'author_copies', 'website_sales', 'amazon_sales', 'flipkart_sales', 'direct_sales', 'temp_physical_count']
    df[numeric_cols] = df[numeric_cols].fillna(0).astype(int)
    
    # Calculate System Stock
    df['System Stock'] = (
        df['total_printed'] - 
        df['author_copies'] - 
        df['website_sales'] - 
        df['amazon_sales'] - 
        df['flipkart_sales'] - 
        df['direct_sales']
    )
    
    return df

# Header Section
col1, col2 = st.columns([7, 1.5])
with col1:
    st.markdown('<div class="header-style">📋 Godown Inventory Tracking</div>', unsafe_allow_html=True)
with col2:
    if st.button("🔄 Refresh Data", type="secondary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

try:
    all_data = fetch_inventory_data()
    
    # Summary Metrics
    total_books = len(all_data)
    verified_books_count = len(all_data[all_data['inventory_check_done'] == 1])
    pending_books_count = total_books - verified_books_count
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Delivered Books", total_books)
    m2.metric("Verified", verified_books_count, delta=f"{(verified_books_count/total_books*100):.1f}%" if total_books > 0 else "0%")
    m3.metric("Pending", pending_books_count)

    # Search
    search_query = st.text_input("🔍 Search by Book ID or Title", placeholder="Search...")
    if search_query:
        all_data = all_data[
            all_data['title'].str.contains(search_query, case=False, na=False) |
            all_data['book_id'].astype(str).str.contains(search_query, case=False, na=False)
        ]

    # Tabs for organization
    tab1, tab2 = st.tabs([f"⏳ Pending ({len(all_data[all_data['inventory_check_done'] == 0])})", 
                           f"✅ Verified ({len(all_data[all_data['inventory_check_done'] == 1])})"])

    with tab1:
        pending_df = all_data[all_data['inventory_check_done'] == 0]
        if pending_df.empty:
            st.success("All books in this view are verified!")
        else:
            paged_pending, p_total_pages, p_total_items = paginate_dataframe(pending_df, 'pending_page')
            
            col_widths = [1, 4, 1.5, 1.5, 1]
            # Header
            hcols = st.columns(col_widths)
            hcols[0].markdown("**ID**")
            hcols[1].markdown("**Title**")
            hcols[2].markdown("**Cell**")
            hcols[3].markdown("**System Stock**")
            hcols[4].markdown("**Action**")
            
            for _, row in paged_pending.iterrows():
                rcols = st.columns(col_widths, vertical_alignment="center")
                rcols[0].write(row['book_id'])
                rcols[1].write(row['title'])
                rcols[2].write(row['rack_number'] if pd.notnull(row['rack_number']) else "-")
                rcols[3].write(row['System Stock'])
                if rcols[4].button("Update", key=f"upd_{row['book_id']}", type="secondary"):
                    update_physical_count(row['book_id'], row['title'], row['rack_number'], row['System Stock'], row['temp_physical_count'])
            
            render_pagination_controls('pending_page', p_total_pages, p_total_items)

    with tab2:
        verified_df = all_data[all_data['inventory_check_done'] == 1]
        if verified_df.empty:
            st.info("No books verified yet.")
        else:
            paged_verified, v_total_pages, v_total_items = paginate_dataframe(verified_df, 'verified_page')
            
            # Table for verified books
            col_widths_v = [1, 4, 1.5, 1.5, 1.5, 1]
            hcols_v = st.columns(col_widths_v)
            hcols_v[0].markdown("**ID**")
            hcols_v[1].markdown("**Title**")
            hcols_v[2].markdown("**Cell**")
            hcols_v[3].markdown("**System**")
            hcols_v[4].markdown("**Actual**")
            hcols_v[5].markdown("**Action**")

            for _, row in paged_verified.iterrows():
                rcols_v = st.columns(col_widths_v, vertical_alignment="center")
                rcols_v[0].write(row['book_id'])
                rcols_v[1].write(row['title'])
                rcols_v[2].write(row['rack_number'])
                rcols_v[3].write(row['System Stock'])
                
                # Highlight discrepancy
                diff = row['temp_physical_count'] - row['System Stock']
                color = "green" if diff == 0 else "red"
                rcols_v[4].markdown(f":{color}[{row['temp_physical_count']}]")
                
                if rcols_v[5].button("Edit", key=f"edit_{row['book_id']}"):
                    update_physical_count(row['book_id'], row['title'], row['rack_number'], row['System Stock'], row['temp_physical_count'])
            
            render_pagination_controls('verified_page', v_total_pages, v_total_items)

    # CSV Download for all data
    st.markdown("---")
    csv = all_data.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Full Inventory Tracking Data (CSV)",
        data=csv,
        file_name='inventory_tracking.csv',
        mime='text/csv',
        use_container_width=True
    )

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
