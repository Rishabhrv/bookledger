import streamlit as st
from datetime import date
from sqlalchemy import text
import time

st.cache_data.clear()

# --- Database Connection ---
def connect_db():
    try:
        conn = st.connection('mysql', type='sql')
        return conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

# --- UI Components ---
def book_details_section():
    st.markdown("<h5>Book Details", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    book_title = col1.text_input("Book Title", placeholder="Enter Book Title..")
    book_date = col2.date_input("Date", value=date.today())
    return {
        "title": book_title,
        "date": book_date
    }

def author_details_section(conn):
    if "authors" not in st.session_state:
        st.session_state.authors = [{"name": "", "email": "", "phone": "", "author_id": None}]

    def add_author():
        st.session_state.authors.append({"name": "", "email": "", "phone": "", "author_id": None})

    def remove_author(index):
        del st.session_state.authors[index]

    def get_author_suggestions(conn, search_term):
        if not search_term:
            return []
        with conn.session as s:
            try:
                query = text("""
                    SELECT author_id, name, email, phone
                    FROM authors
                    WHERE name LIKE CONCAT(:prefix, '%')
                    LIMIT 5
                """)
                authors = s.execute(query, params={"prefix": search_term}).fetchall()
                if authors:
                    st.info(f"Found {len(authors)} authors matching '{search_term}'.", icon="🔍")
                return authors
            except Exception as e:
                return []

    with st.container(border=True): 
        st.markdown("<h5>Author Details", unsafe_allow_html=True)
        for i, author in enumerate(st.session_state.authors):
            with st.container():
                col1, col2, col3, col4, col5, col6  = st.columns([3, 2, 2, 2, 2, 1])

                author_name_input_key = f"author_name_{i}"
                author_name = col1.text_input(f"Author Name {i+1}", author["name"], key=author_name_input_key,placeholder='Enter Auhtor name..')

                suggestions = get_author_suggestions(conn, author_name)  # Pass author_name for suggestions

                suggestion_options = []
                disabled_suggestion = False
                suggestion_placeholder = "Type to search authors..."  # Default placeholder

                if suggestions:
                    suggestion_names = [f"{a.name} (ID: {a.author_id})" for a in suggestions]
                    suggestion_options = [""] + suggestion_names
                    suggestion_placeholder = "Suggested authors found..."  # Placeholder when suggestions exist
                else:
                    suggestion_options = ["No authors found"]
                    disabled_suggestion = True
                    suggestion_placeholder = "No authors found"  # Placeholder when no authors found

                selected_suggestion = col2.selectbox(
                    f"Suggestions {i+1}",
                    suggestion_options,
                    index=0,
                    key=f"author_suggestion_{i}",
                    label_visibility="hidden",
                    disabled=disabled_suggestion,
                    placeholder=suggestion_placeholder  # Set the placeholder text
                )

                if selected_suggestion and selected_suggestion != "No authors found": 
                    if "(ID: " in selected_suggestion:  
                        selected_author_id = int(selected_suggestion.split('(ID: ')[1][:-1])
                        selected_author = next((a for a in suggestions if a.author_id == selected_author_id), None)
                        if selected_author:
                            st.session_state.authors[i]["name"] = selected_author.name
                            st.session_state.authors[i]["email"] = selected_author.email
                            st.session_state.authors[i]["phone"] = selected_author.phone
                            st.session_state.authors[i]["author_id"] = selected_author.author_id
                else:
                    st.session_state.authors[i]["name"] = author_name

                st.session_state.authors[i]["email"] = col3.text_input(f"Email {i+1}", author["email"])
                st.session_state.authors[i]["phone"] = col4.text_input(f"Phone {i+1}", author["phone"])
                selected_position = col5.selectbox(
                    f"Position {i+1}",
                    ["1st", "2nd", "3rd", "4th"],
                    key=f"author_position_{i}"
                )
                st.session_state.authors[i]["author_position"] = selected_position
                if col6.button(":material/close:", key=f"remove_{i}", type="tertiary", ):
                    remove_author(i)
                    st.rerun()

        if st.button(":material/add:"):
            add_author()
            st.rerun()
    return st.session_state.authors


def insert_author(conn, name, email, phone):
    with conn.session as s:
        s.execute(text("""
            INSERT INTO authors (name, email, phone)
            VALUES (:name, :email, :phone)
            ON DUPLICATE KEY UPDATE name=name # Still keep name as ON DUPLICATE KEY for example, you can adjust based on your needs
        """), params={"name": name, "email": email, "phone": phone})
        s.commit()
        return s.execute(text("SELECT LAST_INSERT_ID();")).scalar()

# --- Main App ---
conn = connect_db()

# --- Combined Container ---
with st.container():
    book_data = book_details_section()
    st.markdown(" ")
    author_data = author_details_section(conn)

# --- Save Functionality ---
conn = connect_db()
if st.button(label="Save"):
    if not book_data["title"] or not book_data["date"]:
        st.warning("Please fill in all book details.")
    else:
        with conn.session as s:
            try:
                # Insert book
                s.execute(text("""
                    INSERT INTO books (title, date)
                    VALUES (:title, :date)
                """), params={"title": book_data["title"], "date": book_data["date"]})
                book_id = s.execute(text("SELECT LAST_INSERT_ID();")).scalar()

                # Process authors and links
                for author in author_data:
                    if author["name"] and author["email"] and author["phone"]:
                        author_id_to_link = author["author_id"] or insert_author(conn, author["name"], author["email"], author["phone"])
                        if book_id and author_id_to_link:
                            s.execute(text("""
                                INSERT INTO book_authors (book_id, author_id, author_position)
                                VALUES (:book_id, :author_id, :author_position)
                            """), params={"book_id": book_id, "author_id": author_id_to_link, "author_position": author["author_position"]})
                s.commit()
                st.success("Book and Authors Saved Successfully!")
            except Exception as db_error:
                s.rollback()
                st.error(f"Database error during save: {db_error}")