import streamlit as st
import pandas as pd
from sqlalchemy import text  # Import text for raw SQL queries

st.cache_data.clear()

# Connect to MySQL
conn = st.connection("mysql", type="sql")

# Fetch books from the database
query = "SELECT book_id, title, date, isbn, apply_isbn, deliver FROM books"
books = conn.query(query)

# Convert 'date' column to datetime objects if it's not already
if not pd.api.types.is_datetime64_any_dtype(books['date']):
    books['date'] = pd.to_datetime(books['date'])

# Function to get ISBN display logic
def get_isbn_display(isbn, apply_isbn):
    if pd.notna(isbn):
        return isbn
    elif apply_isbn == 0:
        return "Not Applied"
    elif apply_isbn == 1:
        return "Not Received"
    return "-"

# Function to get status with outlined pill styling
def get_status_pill(deliver_value):
    status = "Delivered" if deliver_value == 1 else "On Going"
    color = "green" if deliver_value == 1 else "orange"
    return f"**:{color}[{status}]**"

# Function to fetch book details (for title and book_id)
def fetch_book_details(book_id):
    query = f"SELECT book_id, title FROM books WHERE book_id = '{book_id}'"
    return conn.query(query)

# Function to fetch book_author details along with author details for a given book_id
def fetch_book_authors(book_id):
    query = f"""
    SELECT ba.id, ba.book_id, ba.author_id, a.name, a.email, a.phone, 
           ba.author_position, ba.welcome_mail_sent, ba.corresponding_agent, 
           ba.publishing_consultant, ba.photo_recive, ba.id_proof_recive, 
           ba.author_details_sent, ba.cover_agreement_sent, ba.agreement_received, 
           ba.digital_book_sent, ba.digital_book_approved, ba.plagiarism_report, 
           ba.printing_confirmation
    FROM book_authors ba
    JOIN authors a ON ba.author_id = a.author_id
    WHERE ba.book_id = '{book_id}'
    """
    return conn.query(query)

from sqlalchemy import text

# Function to update book_authors table
def update_book_authors(id, updates):
    set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
    query = f"UPDATE book_authors SET {set_clause} WHERE id = :id"
    params = updates.copy()
    params["id"] = int(id)  # Ensure id is an integer (adjust if needed)
    #print("Query:", query)
    #print("Params:", params)
    with conn.session as session:  # Explicit session management
        result = session.execute(text(query), params)
        #print("Rows affected:", result.rowcount)
        session.commit()
        #print("Commit executed")

# Updated dialog for editing author details with improved UI
@st.dialog("Edit Author Details", width='large')
def edit_author_dialog(book_id):
    # Fetch book details for title
    book_details = fetch_book_details(book_id)
    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        st.markdown(f"# {book_id} : {book_title}")
    else:
        st.markdown(f"### Authors for Book ID: {book_id}")
        st.warning("Book title not found.")

    # Fetch author details
    book_authors = fetch_book_authors(book_id)
    
    if book_authors.empty:
        st.warning(f"No authors found for Book ID: {book_id}")
    else:
        for idx, row in book_authors.iterrows():
            # Use an expander for each author to collapse/expand details
            with st.expander(f"Author: {row['name']} (ID: {row['author_id']})", expanded=False):
                # Read-only author details with improved layout
                st.markdown("""
                    <style>
                    .info-box { 
                        background-color: #f9f9f9; 
                        padding: 10px; 
                        border-radius: 5px; 
                        margin-bottom: 10px; 
                    }
                    </style>
                    <div class="info-box">
                """, unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Author ID**: {row['author_id']}")
                    st.markdown(f"**Name**: {row['name']}")
                with col2:
                    st.markdown(f"**Email**: {row['email'] or 'N/A'}")
                    st.markdown(f"**Phone**: {row['phone'] or 'N/A'}")
                st.markdown("</div>", unsafe_allow_html=True)

                # Editable section for book_authors fields
                with st.form(key=f"edit_form_{row['id']}"):
                    st.markdown("#### Edit Details", unsafe_allow_html=True)
                    
                    # Selectbox for author_position
                    position_options = ["1st", "2nd", "3rd", "4th"]
                    default_position = row['author_position'] if row['author_position'] in position_options else "1st"
                    author_position = st.selectbox(
                        "Author Position",
                        options=position_options,
                        index=position_options.index(default_position)
                    )

                    # Split checkboxes into two columns for better layout
                    col3, col4 = st.columns(2)
                    with col3:
                        welcome_mail_sent = st.checkbox("Welcome Mail Sent", value=bool(row['welcome_mail_sent']))
                        photo_recive = st.checkbox("Photo Received", value=bool(row['photo_recive']))
                        id_proof_recive = st.checkbox("ID Proof Received", value=bool(row['id_proof_recive']))
                        author_details_sent = st.checkbox("Author Details Sent", value=bool(row['author_details_sent']))
                        cover_agreement_sent = st.checkbox("Cover Agreement Sent", value=bool(row['cover_agreement_sent']))
                        agreement_received = st.checkbox("Agreement Received", value=bool(row['agreement_received']))
                    with col4:
                        digital_book_sent = st.checkbox("Digital Book Sent", value=bool(row['digital_book_sent']))
                        digital_book_approved = st.checkbox("Digital Book Approved", value=bool(row['digital_book_approved']))
                        plagiarism_report = st.checkbox("Plagiarism Report", value=bool(row['plagiarism_report']))
                        printing_confirmation = st.checkbox("Printing Confirmation", value=bool(row['printing_confirmation']))

                    # Text inputs
                    corresponding_agent = st.text_input("Corresponding Agent", value=row['corresponding_agent'] or "")
                    publishing_consultant = st.text_input("Publishing Consultant", value=row['publishing_consultant'] or "")

                    # Submit button with styling
                    if st.form_submit_button("Save Changes", use_container_width=True):
                        updates = {
                            "author_position": author_position,
                            "welcome_mail_sent": 1 if welcome_mail_sent else 0,
                            "corresponding_agent": corresponding_agent,
                            "publishing_consultant": publishing_consultant,
                            "photo_recive": 1 if photo_recive else 0,
                            "id_proof_recive": 1 if id_proof_recive else 0,
                            "author_details_sent": 1 if author_details_sent else 0,
                            "cover_agreement_sent": 1 if cover_agreement_sent else 0,
                            "agreement_received": 1 if agreement_received else 0,
                            "digital_book_sent": 1 if digital_book_sent else 0,
                            "digital_book_approved": 1 if digital_book_approved else 0,
                            "plagiarism_report": 1 if plagiarism_report else 0,
                            "printing_confirmation": 1 if printing_confirmation else 0
                        }
                        update_book_authors(row['id'], updates)
                        st.cache_data.clear()
                        st.success(f"Updated details for {row['name']} (Author ID: {row['author_id']})")
            #st.markdown("---")  # Separator between authors

# Group books by month
grouped_books = books.groupby(pd.Grouper(key='date', freq='ME'))

# Reverse the order of grouped months
reversed_grouped_books = reversed(list(grouped_books))

# Display books
st.markdown("## 📚 Book List")

if books.empty:
    st.warning("No books available.")
else:
    for month, monthly_books in reversed_grouped_books:
        st.markdown(f"##### {month.strftime('%B %Y')}")
        for _, row in monthly_books.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([1, 3, 2, 2, 2, 3])
            
            with col1:
                st.write(row['book_id'])
            with col2:
                st.write(row['title'])
            with col3:
                st.write(row['date'].strftime('%Y-%m-%d'))
            with col4:
                st.write(get_isbn_display(row["isbn"], row["apply_isbn"]))
            with col5:
                st.markdown(get_status_pill(row["deliver"]), unsafe_allow_html=True)
            with col6:
                btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
                with btn_col1:
                    if st.button("👁️", key=f"view_{row['book_id']}"):
                        st.write(f"Viewing book {row['book_id']} (implement view logic here)")
                with btn_col2:
                    if st.button("✍️", key=f"edit_author_{row['book_id']}"):
                        edit_author_dialog(row['book_id'])
                with btn_col3:
                    if st.button("⚙️", key=f"edit_ops_{row['book_id']}"):
                        st.write(f"Editing operations for book {row['book_id']} (implement edit logic here)")
                with btn_col4:
                    if st.button("🗑️", key=f"archive_{row['book_id']}"):
                        st.write(f"Archiving book {row['book_id']} (implement archive logic here)")
        
        st.markdown("---")