import streamlit as st
from datetime import date
import pandas as pd

# --- Database Connection ---
def connect_db():
    try:
        conn = st.connection('mysql', type='sql')
        return conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

# --- Author Search and Suggestions ---
def search_authors(search_term):
    if not search_term:
        return []
    conn = connect_db()
    query = "SELECT author_id, name, email, phone FROM authors WHERE name LIKE %s LIMIT 5"
    df = conn.query(query, params=('%' + search_term + '%',))
    return df.to_dict('records') if not df.empty else []

# --- Database Operations ---
def insert_or_update_author(author_data):
    conn = connect_db()
    with conn.session as cursor:
        query = """
        INSERT INTO authors (name, email, phone)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            email = VALUES(email),
            phone = VALUES(phone)
        """
        cursor.execute(query, (author_data['name'], author_data['email'], author_data['phone']))
        return cursor.lastrowid if cursor.lastrowid else conn.query(
            "SELECT author_id FROM authors WHERE email = %s", 
            params=(author_data['email'],)
        ).iloc[0]['author_id']

def insert_book(book_data):
    conn = connect_db()
    with conn.session as cursor:
        query = "INSERT INTO books (title, date) VALUES (%s, %s)"
        cursor.execute(query, (book_data['title'], book_data['date']))
        return cursor.lastrowid

def link_book_authors(book_id, author_id, position):
    conn = connect_db()
    with conn.session as cursor:
        query = """
        INSERT INTO book_authors (book_id, author_id, author_position)
        VALUES (%s, %s, %s)
        """
        cursor.execute(query, (book_id, author_id, position))

# --- UI Components ---
def book_details_section():
    st.markdown("<h5>Book Details</h5>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    book_title = col1.text_input("Book Title", placeholder="Enter Book Title..")
    book_date = col2.date_input("Date", value=date.today())
    return {
        "title": book_title,
        "date": book_date
    }

def author_details_section():
    st.markdown("<h5>Author Details</h5>", unsafe_allow_html=True)
    
    # Initialize session state for authors
    if 'authors' not in st.session_state:
        st.session_state.authors = []
    
    # Search existing authors
    search_term = st.text_input("Search Authors", placeholder="Type to search existing authors...")
    suggestions = search_authors(search_term)
    
    if suggestions and search_term:
        selected_author = st.selectbox(
            "Suggested Authors",
            options=[f"{a['name']} ({a['email']})" for a in suggestions],
            index=None,
            placeholder="Select an existing author or add new..."
        )
        if selected_author and st.button("Add Selected Author"):
            selected = suggestions[[a['name'] + f" ({a['email']})" for a in suggestions].index(selected_author)]
            if len(st.session_state.authors) < 4 and not any(a['email'] == selected['email'] for a in st.session_state.authors):
                st.session_state.authors.append({
                    'author_id': selected['author_id'],
                    'name': selected['name'],
                    'email': selected['email'],
                    'phone': selected['phone'],
                    'position': len(st.session_state.authors) + 1
                })

    # Add new author manually
    with st.expander("Add New Author", expanded=False):
        new_name = st.text_input("Author Name", key="new_name")
        new_email = st.text_input("Email", key="new_email")
        new_phone = st.text_input("Phone", key="new_phone")
        
        if st.button("Add Author") and new_name and new_email:
            if len(st.session_state.authors) < 4:
                if not any(a['email'] == new_email for a in st.session_state.authors):
                    st.session_state.authors.append({
                        'author_id': None,
                        'name': new_name,
                        'email': new_email,
                        'phone': new_phone,
                        'position': len(st.session_state.authors) + 1
                    })
                else:
                    st.warning("Author with this email already added!")
            else:
                st.warning("Maximum 4 authors allowed per book!")

    # Display current authors
    if st.session_state.authors:
        st.subheader("Current Authors")
        for i, author in enumerate(st.session_state.authors):
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                col1.write(f"{author['name']}")
                col2.write(f"{author['email']}")
                col3.write(f"Position: {author['position']}")
                if col4.button("Remove", key=f"remove_{i}"):
                    st.session_state.authors.pop(i)
                    # Reassign positions
                    for j, a in enumerate(st.session_state.authors):
                        a['position'] = j + 1
                    st.rerun()

# --- Main App ---
def main():
    st.title("Book Tracker")
    
    # Book Details
    book_data = book_details_section()
    
    # Author Details
    author_details_section()
    
    # Save Button
    if st.button("Save"):
        if not book_data['title']:
            st.error("Please enter a book title!")
            return
        
        if not st.session_state.authors:
            st.error("Please add at least one author!")
            return

        conn = connect_db()
        try:
            with conn.session as cursor:
                # Start transaction
                cursor.execute("START TRANSACTION")
                
                # Insert book
                book_id = insert_book(book_data)
                
                # Insert/update authors and link to book
                for author in st.session_state.authors:
                    author_id = author['author_id']
                    if not author_id:
                        author_id = insert_or_update_author(author)
                    link_book_authors(book_id, author_id, author['position'])
                
                # Commit transaction
                cursor.execute("COMMIT")
                
                st.success("Book and author details saved successfully!")
                
                # Clear session state and cache
                st.session_state.authors = []
                st.cache_data.clear()
                st.rerun()
                
        except Exception as e:
            # Rollback on error
            conn.session.execute("ROLLBACK")
            st.error(f"Error saving data: {e}")

if __name__ == "__main__":
    main()