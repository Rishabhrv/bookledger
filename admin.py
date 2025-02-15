import streamlit as st
from datetime import date
from sqlalchemy import text


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
    book_title = col1.text_input("Book Title")
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

    def get_author_suggestions(conn, search_term): # Changed parameter name to search_term
        if not search_term:
            return []
        with conn.session as s:
            authors = s.execute(text("""
                SELECT author_id, name, email, phone
                FROM authors
                WHERE name LIKE :prefix || '%' OR email LIKE :prefix || '%' OR phone LIKE :prefix || '%' # Added OR conditions for email and phone
                LIMIT 5
            """), params={"prefix": search_term}).fetchall() # Using search_term as prefix
            if not authors: # Handle no authors found case
                return ["No authors found"] # Return special string
            return authors


    with st.container(border=True): # Container for Author Details - will be moved later, but keep it for now for individual testing
        st.markdown("<h5>Author Details", unsafe_allow_html=True)
        for i, author in enumerate(st.session_state.authors):
            with st.container():
                col1, col2, col3, col4, col5  = st.columns([3, 2, 3, 2, 1])

                author_name_input_key = f"author_name_{i}"
                author_name = col1.text_input(f"Author Name {i+1}", author["name"], key=author_name_input_key)

                suggestions = get_author_suggestions(conn, author_name) # Pass author_name for suggestions

                suggestion_names = [] # Initialize outside if-else
                suggestion_options = []
                disabled_suggestion = False # Flag to disable suggestion box

                if suggestions and suggestions[0] != "No authors found": # Check if suggestions are valid authors and not "No authors found"
                    suggestion_names = [f"{a.name} (ID: {a.author_id})" for a in suggestions]
                    suggestion_options = [""] + suggestion_names # Add empty string for no selection
                elif suggestions and suggestions[0] == "No authors found": # Handle "No authors found" case
                    suggestion_options = ["No authors found"]
                    disabled_suggestion = True # Disable selectbox when no authors found
                else: # No suggestions at all (empty list from get_author_suggestions when search_term is empty initially)
                    suggestion_options = [""] # Keep it empty

                selected_suggestion = col2.selectbox(
                    f"Suggestions {i+1}",
                    suggestion_options,
                    index=0,
                    key=f"author_suggestion_{i}",
                    label_visibility="hidden",
                    disabled=disabled_suggestion # Disable suggestion box if no authors found
                )

                if selected_suggestion and selected_suggestion != "No authors found": # Check if a suggestion is selected and not "No authors found"
                    if "(ID: " in selected_suggestion: # only process if it's not the empty "" option
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
                if col5.button("❌", key=f"remove_{i}", type="tertiary"):
                    remove_author(i)
                    st.rerun()

        if st.button("➕"):
            add_author()
            st.rerun()
    return st.session_state.authors

# --- Database Interaction Functions ---
def get_author_by_name(conn, name):
    with conn.session as s:
        result = s.execute(text("""
            SELECT author_id, name, email, phone
            FROM authors
            WHERE name = :name
        """), params={"name": name}).fetchone()
        return result

def insert_author(conn, name, email, phone):
    with conn.session as s:
        s.execute(text("""
            INSERT INTO authors (name, email, phone)
            VALUES (:name, :email, :phone)
            ON DUPLICATE KEY UPDATE name=name # Still keep name as ON DUPLICATE KEY for example, you can adjust based on your needs
        """), params={"name": name, "email": email, "phone": phone})
        s.commit()
        return s.execute(text("SELECT LAST_INSERT_ID();")).scalar()

def insert_book_author_link(conn, book_id, author_id):
    with conn.session as s:
        try:
            s.execute(text("""
                INSERT INTO book_authors (book_id, author_id)
                VALUES (:book_id, :author_id)
            """), params={"book_id": book_id, "author_id": author_id})
            s.commit()
            return True
        except Exception as e:
            s.rollback()
            st.error(f"Error linking book and author: {e}")
            return False


# --- Main App ---
conn = connect_db()

# --- Combined Container ---
with st.container(): # Main container to wrap both sections
    book_data = book_details_section()
    author_data = author_details_section(conn)
# --- End Combined Container ---


# --- Save Functionality ---
if st.button("💾 Save Book"):
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
                            link_inserted = insert_book_author_link(conn, book_id, author_id_to_link)
                            if link_inserted:
                                st.success(f"Linked Book ID {book_id} with Author ID {author_id_to_link}")
                            else:
                                raise Exception("Failed to insert book-author link")

                st.success("Book and Authors Saved Successfully!")
                st.session_state.authors = [{"name": "", "email": "", "phone": "", "author_id": None}]

            except Exception as db_error:
                s.rollback()
                st.error(f"Database error during save: {db_error}")