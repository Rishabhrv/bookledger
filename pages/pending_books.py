import streamlit as st
import pandas as pd
from datetime import datetime, date


logo = "logo/logo_black.png"
fevicon = "logo/favicon_black.ico"
small_logo = "logo/favicon_white.ico"

st.set_page_config(page_title='Pending Books', page_icon="⏳", layout="wide")

st.logo(logo,
size = "large",
icon_image = small_logo
)

st.markdown("""
    <style>
            
        /* Remove Streamlit's default top padding */
        .main > div {
            padding-top: 0px !important;
        }
        /* Ensure the first element has minimal spacing */
        .block-container {
            padding-top: 28px !important;  /* Small padding for breathing room */
        }
            """, unsafe_allow_html=True)



# --- Database Connection ---
def connect_db():
    try:
        # Use st.cache_resource to only connect once
        @st.cache_resource
        def get_connection():
            return st.connection('mysql', type='sql')
        conn = get_connection()
        return conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

# Connect to MySQL
conn = connect_db()

# Fetch books from the database where deliver = 0
query = """
SELECT book_id, title, date
FROM books
WHERE deliver = 0
"""
books_data = conn.query(query, show_spinner=False)


# Custom CSS for headings with badge and improved table styling
st.markdown("""
<style>
/* Heading styles from the provided CSS */
.status-badge-red {
    background-color: #FFEBEE;
    color: #F44336;
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: bold;
    display: inline-flex;
    align-items: center;
    font-size: 25px;
    margin-bottom: 10px;
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
/* Table and container styles from previous version */
.table-header {
    font-weight: bold;
    font-size: 16px;
    color: #333;
    padding: 10px;
    border-bottom: 2px solid #ddd;
}
.table-row {
    padding: 14px 10px;
    background-color: #ffffff;
    font-size: 15px; /* Smaller font size as requested previously */
    margin-bottom: 5px;
    margin-top: 5px;    
}

.table-row:hover {
    background-color: #f1f1f1; /* Hover effect */
}
.container-spacing {
    margin-bottom: 30px;
}
</style>
""", unsafe_allow_html=True)


with st.container():
    col1, col2 = st.columns([16, 2], vertical_alignment="bottom")
    with col1:
        st.markdown(f'<div class="status-badge-red">Pending Books<span class="badge-count">{len(books_data)}</span></div>', unsafe_allow_html=True)

    if not books_data.empty:
        column_widths = [0.7, 4, 0.8, 1.2, 1, 1, 0.8]

        with st.container(border=True):
            cols = st.columns(column_widths, vertical_alignment="bottom")
            cols[0].markdown('<div class="table-header">Book ID</div>', unsafe_allow_html=True)
            cols[1].markdown('<div class="table-header">Book Title</div>', unsafe_allow_html=True)
            cols[2].markdown('<div class="table-header">Date</div>', unsafe_allow_html=True)
            cols[3].markdown('<div class="table-header">Since Enrolled</div>', unsafe_allow_html=True)
            cols[4].markdown('<div class="table-header">Status</div>', unsafe_allow_html=True)
            cols[5].markdown('<div class="table-header">Stuck Reason</div>', unsafe_allow_html=True)
            cols[6].markdown('<div class="table-header">Actions</div>', unsafe_allow_html=True)

            for _, book in books_data.iterrows():
                cols = st.columns(column_widths, vertical_alignment="bottom")
                cols[0].markdown(f'<div class="table-row">{book["book_id"]}</div>', unsafe_allow_html=True)
                cols[1].markdown(f'<div class="table-row">{book["title"]}</div>', unsafe_allow_html=True)
                cols[2].markdown(f'<div class="table-row">{book["date"].strftime("%Y-%m-%d") if pd.notnull(book["date"]) else ""}</div>', unsafe_allow_html=True)
                cols[3].markdown(f'<div class="table-row">{(date.today() - book["date"]).days if pd.notnull(book["date"]) else ""} days</div>', unsafe_allow_html=True)
                cols[4].markdown(f'<div class="table-row"></div>', unsafe_allow_html=True)
                cols[5].markdown(f'<div class="table-row"></div>', unsafe_allow_html=True)
                with cols[6]:
                    if st.button(":material/visibility:", key=f"view_{book['book_id']}", ):
                        # Placeholder for dialog function
                        pass
    else:
        st.info("No books are currently listed with deliver = 0.")

st.markdown('<div class="container-spacing"></div>', unsafe_allow_html=True)