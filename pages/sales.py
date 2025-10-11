import streamlit as st
from constants import log_activity
from constants import connect_db

conn = connect_db()

# if "activity_logged" not in st.session_state:
#     log_activity(
#                 conn,
#                 st.session_state.user_id,
#                 st.session_state.username,
#                 st.session_state.session_id,
#                 "logged in",
#                 f"App: {st.session_state.app}"
#             )
#     st.session_state.activity_logged = True

st.session_state.username = 'Harsh'

# Get the logged-in user's name
user_name = st.session_state.username

# Fetch books filtered by publishing_consultant matching the logged-in user
query = """
    SELECT DISTINCT 
        b.book_id, 
        b.title, 
        b.date, 
        b.isbn, 
        b.apply_isbn,
        b.publisher,
        ba.total_amount,
        ba.publishing_consultant
    FROM books b
    INNER JOIN book_authors ba ON b.book_id = ba.book_id
    WHERE ba.publishing_consultant = %s
    ORDER BY b.date DESC
"""

try:
    books = conn.query(query, params=[user_name], show_spinner=False)
    
    if books.empty:
        st.info(f"No books found for publishing consultant: {user_name}")
    else:
        st.success(f"Found {len(books)} books assigned to {user_name}")
        # Display the filtered books for verification
        st.dataframe(books)
        
except Exception as e:
    st.error(f"Error fetching books: {e}")
    books = None