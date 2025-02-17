import streamlit as st
from datetime import date
from sqlalchemy import text
from streamlit_extras.no_default_selectbox import selectbox


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
                st.write(f"**Debug:** Error in get_author_suggestions: {e}")  # Debug st.write
                return []

    with st.container(border=True):  # Container for Author Details - will be moved later, but keep it for now for individual testing
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

                if selected_suggestion and selected_suggestion != "No authors found":  # Check if a suggestion is selected and not "No authors found"
                    if "(ID: " in selected_suggestion:  # only process if it's not the empty "" option
                        selected_author_id = int(selected_suggestion.split('(ID: ')[1][:-1])
                        selected_author = next((a for a in suggestions if a.author_id == selected_author_id), None)
                        if selected_author:
                            st.session_state.authors[i]["name"] = selected_author.name
                            st.session_state.authors[i]["email"] = selected_author.email
                            st.session_state.authors[i]["phone"] = selected_author.phone
                            st.session_state.authors[i]["author_id"] = selected_author.author_id
                else:
                    st.session_state.authors[i]["name"] = author_name

                st.session_state.authors[i]["email"] = col3.text_input(f"Email {i+1}", author["email"], placeholder= "Enter Email..")
                st.session_state.authors[i]["phone"] = col4.text_input(f"Phone {i+1}", author["phone"], placeholder= "Enter Phone..")
                selected_position = col5.selectbox(
                    f"Position {i+1}",
                    ["1st", "2nd", "3rd", "4th"],
                    key=f"author_position_{i}"
                )
                st.session_state.authors[i]["author_position"] = selected_position
                if col6.button("❌", key=f"remove_{i}", type="tertiary"):
                    remove_author(i)
                    st.rerun()

        if st.button("➕"):
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

def insert_book_author_link(conn, book_id, author_id,author_position):
    with conn.session as s:
        try:
            s.execute(text("""
                INSERT INTO book_authors (book_id, author_id,author_position)
                VALUES (:book_id, :author_id, :author_position)
            """), params={"book_id": book_id, "author_id": author_id, "author_position": author_position})
            s.commit()
            return True
        except Exception as e:
            s.rollback()
            st.error(f"Error linking book and author: {e}")
            return False


# --- Main App ---
conn = connect_db()

# --- Combined Container ---
with st.container():
    book_data = book_details_section()
    st.markdown(" ")
    author_data = author_details_section(conn)


# --- Save Functionality ---
if st.button("Save Book"):
    if not book_data["title"] or not book_data["date"]:
        st.warning("Please fill in all book details (Title and Date).")
    else:
        with conn.session as s:
            try:
                s.execute(text("""
                    INSERT INTO books (title, date)
                    VALUES (:title, :date)
                """), params={
                    "title": book_data["title"],
                    "date": book_data["date"],
                })
                s.commit()

                book_id = s.execute(text("SELECT LAST_INSERT_ID();")).scalar()

                for author in author_data:
                    if author["name"] and author["email"] and author["phone"]:
                        author_id_to_link = None

                        if author["author_id"]:
                            author_id_to_link = author["author_id"]
                            st.success(f"Using existing author '{author['name']}' (ID: {author_id_to_link})")
                        else:
                            author_id_to_link = insert_author(conn, author["name"], author["email"], author["phone"])
                            st.success(f"New author '{author['name']}' added with ID: {author_id_to_link}")

                        if book_id and author_id_to_link:
                            link_inserted = insert_book_author_link(conn, book_id, author_id_to_link,author["author_position"])
                            if link_inserted:
                                st.success(f"Linked Book ID {book_id} with Author ID {author_id_to_link}")
                            else:
                                raise Exception("Failed to insert book-author link")

                st.success("Book and Authors Saved Successfully!")
                st.session_state.authors = [{"name": "", "email": "", "phone": "", "author_id": None}]

            except Exception as db_error:
                s.rollback()
                st.error(f"Database error during save: {db_error}")