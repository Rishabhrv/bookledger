import streamlit as st
import pandas as pd
from auth import validate_token
from constants import log_activity, initialize_click_and_session_id, connect_db, clean_url_params

logo = "logo/logo_black.png"
fevicon = "logo/favicon_black.ico"
small_logo = "logo/favicon_white.ico"

st.set_page_config(page_title='Author Open Positions', page_icon="👤", layout="wide")

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


def has_access(user_role, user_app, user_access):
    # Sales app always has access
    if user_app == 'sales':
        return True
    
    # Admins always have access
    if user_role == 'admin':
        return True
    
    # Regular users with specific app and permission
    if (user_role == 'user' and 
        user_app == 'main' and 
        'Open Author Positions' in user_access):
        return True
    
    return False

if not has_access(user_role, user_app, user_access):
    st.error("⚠️ Access Denied: You don't have permission to access this page.")
    st.stop()

st.cache_data.clear()

st.markdown("""
    <style>
            
        /* Remove Streamlit's default top padding */
        .main > div {
            padding-top: 0px !important;
        }
        /* Ensure the first element has minimal spacing */
        .block-container {
            padding-top: 11px !important;  /* Small padding for breathing room */
        }
            """, unsafe_allow_html=True)

conn = connect_db()


# Initialize logged_click_ids if not present
if "logged_click_ids" not in st.session_state:
    st.session_state.logged_click_ids = set()

# Log navigation if click_id is present and not already logged
if click_id and click_id not in st.session_state.logged_click_ids:
    try:
        log_activity(
            conn,
            st.session_state.user_id,
            st.session_state.username,
            st.session_state.session_id,
            "navigated to page",
            f"Page: Open Author Positions"
        )
        st.session_state.logged_click_ids.add(click_id)
    except Exception as e:
        st.error(f"Error logging navigation: {str(e)}")


# Custom CSS (removed .publisher-badge, using .pill-badge for publishers)
st.markdown("""
<style>
.status-badge-red {
    background-color: #FFEBEE;
    color: #F44336;
    padding: 5px 17px;
    border-radius: 12px;
    font-weight: bold;
    display: inline-flex;
    align-items: center;
    font-size: 20px;
    margin-bottom: 15px;
}
.badge-count {
    background-color: rgba(255, 255, 255, 0.9);
    color: inherit;
    padding: 2px 6px;
    border-radius: 10px;
    margin-left: 6px;
    font-size: 14px;
    font-weight: normal;
}
.table-header {
    font-weight: bold;
    font-size: 14px;
    color: #333;
    padding: 8px;
    border-bottom: 2px solid #ddd;
    margin-bottom: 10px;
}
.table-row {
    padding: 7px 5px;
    background-color: #ffffff;
    font-size: 13px; 
    margin-bottom: 5px;
    margin-top: 5px;    
}
.table-row:hover {
    background-color: #f1f1f1; 
}
.container-spacing {
    margin-bottom: 30px;
}
.pill-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
    text-align: center;
    min-width: 80px;
}
.publisher-Penguin { background-color: #fff3e0; color: #ef6c00; }
.publisher-HarperCollins { background-color: #e6f3ff; color: #0052cc; }
.publisher-Macmillan { background-color: #f0e6ff; color: #6200ea; }
.publisher-RandomHouse { background-color: #e6ffe6; color: #2e7d32; }
.publisher-default { background-color: #f5f5f5; color: #616161; }
            
.date-pill {
    display: inline-block;
    padding: 2px 5px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 500;
    background-color: #e0f7fa;
    color: #006064;
    margin-left: 3px;
}
.author-type-double { background-color: #e6f3ff; color: #0052cc; }
.author-type-triple { background-color: #f0e6ff; color: #6200ea; }
.author-type-multiple { background-color: #f5f5f5; color:#616161; }
.position-occupied { background-color: #e6ffe6; color: #2e7d32; }
.position-vacant { background-color: #ffe6e6; color: #d32f2f; }
.position-na { background-color: #f5f5f5; color: #616161; }
</style>
""", unsafe_allow_html=True)

def get_open_author_positions(conn):
    query = """
    WITH author_counts AS (
        SELECT 
            b.book_id,
            b.title,
            b.date,
            b.author_type,
            b.publisher,
            COUNT(ba.author_id) as author_count,
            MAX(CASE WHEN ba.author_position = '1st' THEN CONCAT('Booked by ', ba.publishing_consultant) ELSE NULL END) as position_1,
            MAX(CASE WHEN ba.author_position = '2nd' THEN CONCAT('Booked by ', ba.publishing_consultant) ELSE NULL END) as position_2,
            MAX(CASE WHEN ba.author_position = '3rd' THEN CONCAT('Booked by ', ba.publishing_consultant) ELSE NULL END) as position_3,
            MAX(CASE WHEN ba.author_position = '4th' THEN CONCAT('Booked by ', ba.publishing_consultant) ELSE NULL END) as position_4
        FROM books b
        LEFT JOIN book_authors ba ON b.book_id = ba.book_id
        WHERE b.author_type IN ('Double', 'Triple', 'Multiple')
        GROUP BY b.book_id, b.title, b.date, b.author_type, b.publisher
        HAVING 
            (b.author_type = 'Double' AND COUNT(ba.author_id) < 2) OR
            (b.author_type = 'Triple' AND COUNT(ba.author_id) < 3) OR
            (b.author_type = 'Multiple' AND COUNT(ba.author_id) < 4)
    )
    SELECT 
        book_id,
        title,
        date,
        author_type,
        publisher,
        COALESCE(position_1, 'Vacant') as position_1,
        CASE 
            WHEN author_type IN ('Double', 'Triple', 'Multiple') THEN COALESCE(position_2, 'Vacant')
            ELSE 'N/A'
        END as position_2,
        CASE 
            WHEN author_type IN ('Triple', 'Multiple') THEN COALESCE(position_3, 'Vacant')
            ELSE 'N/A'
        END as position_3,
        CASE 
            WHEN author_type = 'Multiple' THEN COALESCE(position_4, 'Vacant')
            ELSE 'N/A'
        END as position_4
    FROM author_counts;
    """
    df = conn.query(query)
    return df

# Main page
def open_author_positions_page():
    # Header
    col1, col2, col3 = st.columns([8, 0.7, 1], vertical_alignment="bottom")
    with col1:
        st.markdown("## 👤 Open Author Positions")
    with col2:
        if st.button(":material/refresh: Refresh", key="refresh", type="tertiary"):
            st.cache_data.clear()
    with col3:
        if st.button(":material/arrow_back: Go Back", key="back_button", type="tertiary", width="stretch"):
            st.switch_page('app.py')
    
    # Connect to database
    conn = connect_db()
    
    # Fetch data
    open_positions_df = get_open_author_positions(conn)
    
    # Top layout with 3 columns
    col1, col2, col3 = st.columns([1.5, 4.1, 3.5], vertical_alignment="bottom", gap="small")
    
    with col1:
        # Placeholder for filtered count
        count_placeholder = st.empty()
    
    with col2:
        search_term = st.text_input("Search by Book ID or Title", "", placeholder="Enter Book ID or Title", 
                                    key="search_input", label_visibility="collapsed")
    
    with col3:
        with st.popover("Filters & Sort", width="stretch"):
            # Filter Controls
            st.markdown("###### Filters:")
            author_type_filter = st.pills(
                "Filter by Author Type:",
                options=['Double', 'Triple', 'Multiple'],
                default=[],
                key="author_type_filter"
            )
            
            vacant_positions = st.pills(
                "Filter by Number of Vacant Positions:",
                options=[1, 2, 3],
                default=[],
                key="vacant_positions_filter"
            )
            
            # Sorting Controls
            st.markdown("###### Sort Options:")
            sort_column = st.selectbox(
                "Sort by",
                options=['book_id', 'title', 'date', 'author_type', 'publisher', 'position_1', 'position_2', 'position_3', 'position_4'],
                index=0
            )
            sort_order = st.radio("Sort Order", ['Ascending', 'Descending'], horizontal=True, index=1)
    
    # Apply filters
    filtered_df = open_positions_df.copy()
    if search_term:
        filtered_df = filtered_df[
            filtered_df['title'].str.contains(search_term, case=False, na=False) |
            filtered_df['book_id'].astype(str).str.contains(search_term, case=False, na=False)
        ]
    if author_type_filter:
        filtered_df = filtered_df[filtered_df['author_type'].isin(author_type_filter)]
    if vacant_positions:
        filtered_df['vacant_count'] = filtered_df[['position_1', 'position_2', 'position_3', 'position_4']].apply(
            lambda x: sum(1 for pos in x if pos == 'Vacant'), axis=1
        )
        filtered_df = filtered_df[filtered_df['vacant_count'].isin(vacant_positions)]
        filtered_df = filtered_df.drop(columns=['vacant_count'])
    
    # Apply sorting
    if sort_column:
        filtered_df = filtered_df.sort_values(
            by=sort_column,
            ascending=(sort_order == 'Ascending')
        )
    
    # Update Open Positions badge with filtered count
    count_placeholder.markdown(
        f'<div class="status-badge-red">Open Positions <span class="badge-count">{len(filtered_df)}</span></div>',
        unsafe_allow_html=True
    )
    
    # Custom Table
    if not filtered_df.empty:
        # Format date column and calculate days since
        filtered_df['date'] = pd.to_datetime(filtered_df['date'])
        from datetime import datetime
        current_date = datetime.now()
        filtered_df['days_since'] = (current_date - filtered_df['date']).dt.days
        filtered_df['date_str'] = filtered_df['date'].dt.strftime('%Y-%m-%d')
        
        # Define column widths (adjusted for publisher column removal)
        column_widths = [0.6, 3.1, 0.8, 0.7, 1,1,1,1]
        
        with st.container(border=True):
            # Table Headers
            cols = st.columns(column_widths)
            cols[0].markdown('<div class="table-header">Book ID</div>', unsafe_allow_html=True)
            cols[1].markdown('<div class="table-header">Title</div>', unsafe_allow_html=True)
            cols[2].markdown('<div class="table-header">Date</div>', unsafe_allow_html=True)
            cols[3].markdown('<div class="table-header">Author Type</div>', unsafe_allow_html=True)
            cols[4].markdown('<div class="table-header">Position 1</div>', unsafe_allow_html=True)
            cols[5].markdown('<div class="table-header">Position 2</div>', unsafe_allow_html=True)
            cols[6].markdown('<div class="table-header">Position 3</div>', unsafe_allow_html=True)
            cols[7].markdown('<div class="table-header">Position 4</div>', unsafe_allow_html=True)
            
            # Table Rows
            for _, book in filtered_df.iterrows():
                cols = st.columns(column_widths)
                cols[0].markdown(f'<div class="table-row">{book["book_id"]}</div>', unsafe_allow_html=True)
                
                # Publisher pill using pill-badge class
                publisher_class = {
                    'AGPH': 'publisher-Penguin',
                    'Cipher': 'publisher-HarperCollins',
                    'AG Volumes': 'publisher-Macmillan',
                    'AG Classics': 'publisher-RandomHouse'
                }.get(book['publisher'], 'publisher-default')
                
                publisher_badge = f'<span class="pill-badge {publisher_class}" style="margin-left: 8px;">{book["publisher"]}</span>'
                cols[1].markdown(f'<div class="table-row">{book["title"]}{publisher_badge}</div>', unsafe_allow_html=True)
                
                cols[2].markdown(
                    f'<div class="table-row">{book["date_str"]} <span class="date-pill">{book["days_since"]}</span></div>',
                    unsafe_allow_html=True
                )

                # Author Type pill
                author_type_class = {
                    'Double': 'author-type-double',
                    'Triple': 'author-type-triple',
                    'Multiple': 'author-type-multiple'
                }.get(book['author_type'], '')
                cols[3].markdown(
                    f'<div class="pill-badge {author_type_class}">{book["author_type"]}</div>',
                    unsafe_allow_html=True
                )
                
                # Position pills
                for i, pos in enumerate(['position_1', 'position_2', 'position_3', 'position_4'], 4):
                    status = book[pos]
                    status_class = {
                        'Vacant': 'position-vacant',
                        'N/A': 'position-na'
                    }.get(status, 'position-occupied')  # Default to occupied for 'Booked by' names
                    cols[i].markdown(
                        f'<div class="pill-badge {status_class}">{status}</div>',
                        unsafe_allow_html=True
                    )
    else:
        st.info("No books with open author positions match the selected criteria.")
    
    st.markdown('<div class="container-spacing"></div>', unsafe_allow_html=True)

    # --- Extra Books Section ---
    def fetch_extra_books_list(conn):
        try:
            return conn.query("""
                SELECT book_id, title, rewritten_at, reason, book_pages
                FROM extra_books 
                ORDER BY rewritten_at DESC
            """, ttl=0)
        except Exception:
            return pd.DataFrame()

    extra_books_df = fetch_extra_books_list(conn)
    
    # st.markdown("### 📚 Extra Books (Available for Re-enrollment)")
    st.markdown(
        f'<div class="status-badge-red">Extra Books <span class="badge-count">{len(extra_books_df)}</span></div>',
        unsafe_allow_html=True
    )

    if not extra_books_df.empty:
        # Format rewritten_at
        extra_books_df['rewritten_at'] = pd.to_datetime(extra_books_df['rewritten_at']).dt.strftime('%Y-%m-%d')
        
        with st.container(border=True):
            # Headers
            eb_cols = st.columns([0.8, 3, 1, 1, 1])
            eb_cols[0].markdown('<div class="table-header">Book ID</div>', unsafe_allow_html=True)
            eb_cols[1].markdown('<div class="table-header">Title</div>', unsafe_allow_html=True)
            eb_cols[2].markdown('<div class="table-header">Pages</div>', unsafe_allow_html=True)
            eb_cols[3].markdown('<div class="table-header">Archived Date</div>', unsafe_allow_html=True)
            eb_cols[4].markdown('<div class="table-header">Reason</div>', unsafe_allow_html=True)

            
            # Rows
            for _, row in extra_books_df.iterrows():
                eb_cols = st.columns([0.8, 3, 1, 1, 1])
                eb_cols[0].markdown(f'<div class="table-row">{row["book_id"]}</div>', unsafe_allow_html=True)
                eb_cols[1].markdown(f'<div class="table-row">{row["title"]}</div>', unsafe_allow_html=True)
                eb_cols[2].markdown(f'<div class="table-row">{row["book_pages"]}</div>', unsafe_allow_html=True)
                eb_cols[3].markdown(f'<div class="table-row">{row["rewritten_at"]}</div>', unsafe_allow_html=True)
                eb_cols[4].markdown(f'<div class="table-row" style="color:#d32f2f;">{row["reason"] or "-"}</div>', unsafe_allow_html=True)
    else:
        st.info("No extra books available.")

    st.markdown('<div class="container-spacing"></div>', unsafe_allow_html=True)

# Run the page
if __name__ == "__main__":
    open_author_positions_page()