import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import date
import time
import re
import os
import base64
import json
import hashlib
import hmac


# Set page configuration
st.set_page_config(
    menu_items={
        'About': "AGPH",
        'Get Help': None,
        'Report a bug': None,   
    },
    layout="wide",  # Set layout to wide mode
    initial_sidebar_state="collapsed",
    page_title="AGPH Books",
)

# Inject CSS to remove the menu (optional)
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
"""

st.markdown(hide_menu_style, unsafe_allow_html=True)

# Use the same secret key as MasterSheet3
SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key') 

def validate_token():
    # Store token in session_state if it is found in URL parameters
    if 'token' not in st.session_state:
        params = st.query_params
        if 'token' in params:
            st.session_state.token = params['token']
        else:
            st.error("Access Denied: Login Required")
            st.stop()

    token = st.session_state.token

    try:
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid token format")

        header = json.loads(base64.urlsafe_b64decode(parts[0] + '==').decode('utf-8'))
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + '==').decode('utf-8'))

        signature = base64.urlsafe_b64decode(parts[2] + '==')
        expected_signature = hmac.new(
            SECRET_KEY.encode(),
            f"{parts[0]}.{parts[1]}".encode(),
            hashlib.sha256
        ).digest()

        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid token signature")

        if 'exp' in payload and payload['exp'] < time.time():
            raise ValueError("Token has expired")

        # Store validated user info in session_state
        st.session_state.user = payload['user']
        st.session_state.role = payload['role']

    except ValueError as e:
        st.error(f"Access Denied: {e}")
        st.stop()

validate_token()

st.cache_data.clear()

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

# Fetch books from the database
query = "SELECT book_id, title, date, isbn, apply_isbn, deliver, price, is_single_author, is_publish_only, publisher FROM books"
books = conn.query(query,show_spinner = False)

# Function to fetch book details (title, is_single_author, num_copies, print_status)
def fetch_book_details(book_id, conn):
    query = f"""
    SELECT title, date, apply_isbn, isbn, is_single_author, num_copies, print_status,is_publish_only
    FROM books
    WHERE book_id = '{book_id}'
    """
    return conn.query(query,show_spinner = False)

# Convert 'date' column to datetime objects if it's not already
if not pd.api.types.is_datetime64_any_dtype(books['date']):
    books['date'] = pd.to_datetime(books['date'])

def get_isbn_display(isbn, apply_isbn):
    if pd.notna(isbn):
        return f"**<span style='color:#47b354; background-color:#ffffff; font-size:12px; padding: 2px 6px; border-radius: 4px;'>{isbn}</span>**"  # Grayish background and smaller font for valid ISBN
    elif apply_isbn == 0:
        return f"**<span style='color:#ed633e; background-color:#ffffff; font-size:14px; padding: 2px 6px; border-radius: 4px;'>Not Applied</span>**"  # Red for Not Applied
    elif apply_isbn == 1:
        return f"**<span style='color:#606975; background-color:#ffffff; font-size:14px; padding: 2px 6px; border-radius: 4px;'>Not Received</span>**"  # Orange for Not Received
    return f"**<span style='color:#000000; background-color:#ffffff; font-size:14px; padding: 2px 6px; border-radius: 4px;'>-</span>**"  # Black for default/unknown case


# Function to get status with outlined pill styling
def get_status_pill(deliver_value):

    pill_style = (
        "padding: 2px 6px; "  
        "border-radius: 4px; " 
        "background-color: #ffffff; "  
        "font-size: 14px; "  
        "font-weight: bold; "  
        "display: inline-block;"  
    )

    # Determine status and colors
    if deliver_value == 1:
        status = "Delivered"
        text_color = "#47b354" 
    else:
        status = "On Going"
        text_color = "#e0ab19"  

    return f"<span style='{pill_style} color: {text_color};'>{status}</span>"


###################################################################################################################################
##################################--------------- Edit Auhtor Details ----------------------------##################################
###################################################################################################################################


@st.dialog("Manage Authors", width="large")
def edit_author_detail(conn):
    # Fetch all authors from database
    with conn.session as s:
        authors = s.execute(
            text("SELECT author_id, name, email, phone FROM authors ORDER BY name")
        ).fetchall()
    
    if not authors:
        st.error("❌ No authors found in database.")
        return

    # Convert to dictionary for easier handling
    author_dict = {f"{author.name} (ID: {author.author_id})": author for author in authors}
    author_options = list(author_dict.keys())

    st.markdown("### Author List", unsafe_allow_html=True)
    with st.container(border=True):
        # Author selection
        selected_author_name = st.selectbox(
            "Select Author",
            options=author_options,
            key="author_select",
            help="Select an author to edit or delete"
        )
        
        selected_author = author_dict[selected_author_name]
        # Highlight author ID with green color
        st.markdown(
            f"#### Selected ID: <span style='color: #2196F3; font-weight: bold;'>{selected_author.author_id}</span>",
            unsafe_allow_html=True
        )

    # Highlight author name with blue color
    st.markdown(
        f"### Editing: <span style='color: #4CAF50;'>{selected_author.name}</span>",
        unsafe_allow_html=True
    )
    with st.container(border=True):
        # Edit fields with NULL handling
        new_name = st.text_input(
            "Author Name",
            value=selected_author.name,
            key=f"name_{selected_author.author_id}"
        )
        new_email = st.text_input(
            "Email",
            value=selected_author.email if selected_author.email is not None else "",
            key=f"email_{selected_author.author_id}"
        )
        new_phone = st.text_input(
            "Phone",
            value=selected_author.phone if selected_author.phone is not None else "",
            key=f"phone_{selected_author.author_id}"
        )

        btn_col1, btn_col2 = st.columns([3, 1])

        with btn_col1:
            with st.container():
                if st.button("Save Changes", 
                            key=f"save_{selected_author.author_id}", 
                            type="primary",
                            use_container_width=True):
                    with st.spinner("Saving changes..."):
                        time.sleep(1)
                        with conn.session as s:
                            s.execute(
                                text("""
                                    UPDATE authors 
                                    SET name = :name, 
                                        email = :email, 
                                        phone = :phone 
                                    WHERE author_id = :author_id
                                """),
                                {
                                    "name": new_name,
                                    "email": new_email if new_email else None,
                                    "phone": new_phone if new_phone else None,
                                    "author_id": selected_author.author_id
                                }
                            )
                            s.commit()
                        st.success("Author Updated Successfully!", icon="✔️")

        with btn_col2:
            delete_key = f"delete_{selected_author.author_id}"
            if "confirm_delete" not in st.session_state:
                st.session_state["confirm_delete"] = False

            if st.button("🗑️", 
                        key=delete_key, 
                        type="secondary",
                        help = f"Delete {selected_author.name}",
                        use_container_width=True):
                st.session_state["confirm_delete"] = True

        # Move confirmation dialog outside the column layout
        if st.session_state["confirm_delete"]:
            st.warning(f"Are you sure you want to delete {selected_author.name} (ID: {selected_author.author_id})?")

            # Full-width confirmation buttons
            confirm_col1, confirm_col2 = st.columns([4, 1])
            with confirm_col1:
                if st.button("❌ Cancel", key=f"cancel_{delete_key}"):
                    st.session_state["confirm_delete"] = False
            with confirm_col2:
                if st.button("✔️ Confirm", key=f"confirm_{delete_key}"):
                    with st.spinner("Deleting author..."):
                        time.sleep(2)
                        with conn.session as s:
                            s.execute(
                                text("DELETE FROM authors WHERE author_id = :author_id"),
                                {"author_id": selected_author.author_id}
                            )
                            s.commit()
                        st.success("Author Deleted Successfully!", icon="✔️")
                        st.session_state["confirm_delete"] = False





###################################################################################################################################
##################################--------------- Add New Book & Auhtor ----------------------------##################################
###################################################################################################################################

@st.dialog("Add Book and Authors", width="large")
def add_book_dialog(conn):

    # --- Helper Function to Ensure Backward Compatibility ---
    def ensure_author_fields(author):
        default_author = {
            "name": "",
            "email": "",
            "phone": "",
            "author_id": None,
            "author_position": "1st",  # Default position, will be overridden
            "corresponding_agent": "",
            "publishing_consultant": ""
        }
        # Update the author dict with any missing keys, preserving existing values
        for key, default_value in default_author.items():
            if key not in author:
                author[key] = default_value
        return author

    # --- UI Components Inside Dialog ---
    def publisher_section():
        with st.container(border=True):
            st.markdown("<h5 style='color: #4CAF50;'>Publisher</h5>", unsafe_allow_html=True)
            publisher = st.radio(
                "Select Publisher",
                ["AGPH", "Cipher", "AG Classics", "AG Kids", "NEET/JEE"],
                key="publisher_select",
                horizontal=True,
                help="Select the publisher for this book."
            )
            return publisher

    def book_details_section(publisher):
        with st.container(border=True):
            st.markdown("<h5 style='color: #4CAF50;'>Book Details</h5>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            book_title = col1.text_input("Book Title", placeholder="Enter Book Title..", key="book_title")
            book_date = col2.date_input("Date", value=date.today(), key="book_date")
            
            # Determine if toggles should be enabled based on publisher
            toggles_enabled = publisher in ["AGPH", "Cipher", "AG Classics"]
            
            # Columns for toggles
            col3, col4 = st.columns(2)
            # Add the "Single Author" toggle (default is off, meaning multiple authors allowed)
            is_single_author = col3.toggle(
                "Single Author Book?",
                value=False,
                key="single_author_toggle",
                help="Enable this to restrict the book to a single author.",
                disabled=not toggles_enabled
            )
            # Add the "Publish Only" toggle
            is_publish_only = col4.toggle(
                "Publish Only?",
                value=False,
                key="publish_only_toggle",
                help="Enable this to mark the book as publish only.",
                disabled=not toggles_enabled
            )
            
            if not toggles_enabled:
                st.warning("Single Author and Publish Only options are disabled for AG Kids and NEET/JEE publishers.")
            
            return {
                "title": book_title,
                "date": book_date,
                "is_single_author": is_single_author if toggles_enabled else False,
                "is_publish_only": is_publish_only if toggles_enabled else False,
                "publisher": publisher
            }

    def author_details_section(conn, is_single_author, publisher):
        # Check if author section should be disabled
        author_section_disabled = publisher in ["AG Kids", "NEET/JEE"]

        if "authors" not in st.session_state:
            # Initialize exactly 4 authors with default positions
            st.session_state.authors = [
                {"name": "", "email": "", "phone": "", "author_id": None, "author_position": f"{i+1}{'st' if i == 0 else 'nd' if i == 1 else 'rd' if i == 2 else 'th'}", "corresponding_agent": "", "publishing_consultant": ""}
                for i in range(4)
            ]
        else:
            # Ensure backward compatibility for existing session state
            st.session_state.authors = [ensure_author_fields(author) for author in st.session_state.authors]

        def get_all_authors(conn):
            with conn.session as s:
                try:
                    query = text("SELECT author_id, name, email, phone FROM authors ORDER BY name")
                    authors = s.execute(query).fetchall()
                    return authors
                except Exception as e:
                    st.error(f"Error fetching authors: {e}")
                    return []

        # Fetch unique corresponding agents and publishing consultants
        def get_unique_agents_and_consultants(conn):
            with conn.session as s:
                try:
                    agent_query = text("SELECT DISTINCT corresponding_agent FROM book_authors WHERE corresponding_agent IS NOT NULL AND corresponding_agent != '' ORDER BY corresponding_agent")
                    agents = [row[0] for row in s.execute(agent_query).fetchall()]
                    
                    consultant_query = text("SELECT DISTINCT publishing_consultant FROM book_authors WHERE publishing_consultant IS NOT NULL AND publishing_consultant != '' ORDER BY publishing_consultant")
                    consultants = [row[0] for row in s.execute(consultant_query).fetchall()]
                    
                    return agents, consultants
                except Exception as e:
                    st.error(f"Error fetching agents/consultants: {e}")
                    return [], []

        all_authors = get_all_authors(conn)
        author_options = ["Add New Author"] + [f"{a.name} (ID: {a.author_id})" for a in all_authors]
        unique_agents, unique_consultants = get_unique_agents_and_consultants(conn)

        # Add "Add New..." option to agent and consultant lists
        agent_options = ["Select Agent"] + ["Add New..."] + unique_agents 
        consultant_options = ["Select Consultant"] + ["Add New..."] + unique_consultants 

        with st.container(border=True):
            st.markdown("<h5 style='color: #4CAF50;'>Author Details</h5>", unsafe_allow_html=True)
            
            if author_section_disabled:
                st.warning("Author details are disabled for AG Kids and NEET/JEE publishers.")
                return st.session_state.authors
            
            tab_titles = [f"Author {i+1}" for i in range(4)]
            tabs = st.tabs(tab_titles)

            for i, tab in enumerate(tabs):
                disabled = is_single_author and i > 0
                with tab:
                    if disabled:
                        st.warning("Can't Add More Authors in 'Single Author' Mode")
                    else:
                        selected_author = st.selectbox(
                            f"Select Author {i+1}",
                            author_options,
                            key=f"author_select_{i}",
                            help="Select an existing author or 'Add New Author' to enter new details.",
                            disabled=disabled
                        )

                        if selected_author != "Add New Author" and selected_author and not disabled:
                            selected_author_id = int(selected_author.split('(ID: ')[1][:-1])
                            selected_author_details = next((a for a in all_authors if a.author_id == selected_author_id), None)
                            if selected_author_details:
                                st.session_state.authors[i]["name"] = selected_author_details.name
                                st.session_state.authors[i]["email"] = selected_author_details.email
                                st.session_state.authors[i]["phone"] = selected_author_details.phone
                                st.session_state.authors[i]["author_id"] = selected_author_details.author_id
                        elif selected_author == "Add New Author" and not disabled:
                            st.session_state.authors[i]["author_id"] = None

                        col1, col2 = st.columns(2)
                        st.session_state.authors[i]["name"] = col1.text_input(f"Author Name {i+1}", st.session_state.authors[i]["name"], key=f"name_{i}", placeholder="Enter Author name..", disabled=disabled)
                        available_positions = ["1st", "2nd", "3rd", "4th"]
                        taken_positions = [a["author_position"] for a in st.session_state.authors if a != st.session_state.authors[i]]
                        available_positions = [p for p in available_positions if p not in taken_positions or p == st.session_state.authors[i]["author_position"]]
                        st.session_state.authors[i]["author_position"] = col2.selectbox(
                            f"Position {i+1}",
                            available_positions,
                            index=available_positions.index(st.session_state.authors[i]["author_position"]) if st.session_state.authors[i]["author_position"] in available_positions else 0,
                            key=f"author_position_{i}",
                            disabled=disabled
                        )
                        
                        col3, col4 = st.columns(2)
                        st.session_state.authors[i]["phone"] = col3.text_input(f"Phone {i+1}", st.session_state.authors[i]["phone"], key=f"phone_{i}", placeholder="Enter phone..", disabled=disabled)
                        st.session_state.authors[i]["email"] = col4.text_input(f"Email {i+1}", st.session_state.authors[i]["email"], key=f"email_{i}", placeholder="Enter email..", disabled=disabled)
                        
                        col5, col6 = st.columns(2)

                        selected_agent = col5.selectbox(
                            f"Corresponding Agent {i+1}",
                            agent_options,
                            index=agent_options.index(st.session_state.authors[i]["corresponding_agent"]) if st.session_state.authors[i]["corresponding_agent"] in unique_agents else 0,
                            key=f"agent_select_{i}",
                            disabled=disabled
                        )
                        if selected_agent == "Add New..." and not disabled:
                            st.session_state.authors[i]["corresponding_agent"] = col5.text_input(
                                f"New Agent Name {i+1}",
                                value="",
                                key=f"agent_input_{i}",
                                placeholder="Enter new agent name..."
                            )
                        elif selected_agent != "Select Agent" and not disabled:
                            st.session_state.authors[i]["corresponding_agent"] = selected_agent

                        selected_consultant = col6.selectbox(
                            f"Publishing Consultant {i+1}",
                            consultant_options,
                            index=consultant_options.index(st.session_state.authors[i]["publishing_consultant"]) if st.session_state.authors[i]["publishing_consultant"] in unique_consultants else 0,
                            key=f"consultant_select_{i}",
                            disabled=disabled
                        )
                        if selected_consultant == "Add New..." and not disabled:
                            st.session_state.authors[i]["publishing_consultant"] = col6.text_input(
                                f"New Consultant Name {i+1}",
                                value="",
                                key=f"consultant_input_{i}",
                                placeholder="Enter new consultant name..."
                            )
                        elif selected_consultant != "Select Consultant" and not disabled:
                            st.session_state.authors[i]["publishing_consultant"] = selected_consultant

        return st.session_state.authors

    def is_author_active(author):
        """Check if an author is 'active' (i.e., has at least one non-empty field)."""
        return bool(author["name"] or author["email"] or author["phone"] or author["corresponding_agent"] or author["publishing_consultant"])

    def validate_form(book_data, author_data, is_single_author, publisher):
        """Validate that all required fields are filled for book and active authors, and positions are unique."""
        errors = []

        # Validate book details
        if not book_data["title"]:
            errors.append("Book title is required.")
        if not book_data["date"]:
            errors.append("Book date is required.")
        if not book_data["publisher"]:
            errors.append("Publisher is required.")

        # Skip author validation if publisher is AG Kids or NEET/JEE (author section disabled)
        if publisher not in ["AG Kids", "NEET/JEE"]:
            # Validate author details (only for active authors)
            active_authors = [a for a in author_data if is_author_active(a)]
            if not active_authors:
                errors.append("At least one author must be provided.")

            # If "Single Author" is toggled on, ensure exactly one author is active
            if is_single_author and len(active_authors) > 1:
                errors.append("Only one author is allowed when 'Single Author' is selected.")

            # Track existing author IDs to prevent duplicates
            existing_author_ids = set()
            for i, author in enumerate(author_data):
                if is_author_active(author):
                    if not author["name"]:
                        errors.append(f"Author {i+1} name is required.")
                    if not author["email"]:
                        errors.append(f"Author {i+1} email is required.")
                    if not author["phone"]:
                        errors.append(f"Author {i+1} phone is required.")
                    if not author["publishing_consultant"]:
                        errors.append(f"Author {i+1} publishing consultant is required.")
                    if author["author_id"]:
                        if author["author_id"] in existing_author_ids:
                            errors.append(f"Author {i+1} (ID: {author['author_id']}) is already added. Please remove duplicates.")
                        existing_author_ids.add(author["author_id"])

            # Validate unique positions for active authors
            active_positions = [author["author_position"] for author in active_authors]
            if len(active_positions) != len(set(active_positions)):
                errors.append("All active authors must have unique positions.")

        return errors

    # --- Combined Container Inside Dialog ---
    with st.container():
        publisher = publisher_section()
        st.markdown(" ")
        book_data = book_details_section(publisher)
        st.markdown(" ")
        author_data = author_details_section(conn, book_data["is_single_author"], publisher)

    # --- Save, Clear, and Cancel Buttons ---
    col1, col2 = st.columns([7,1])
    with col1:
        if st.button("Save", key="dialog_save", type="primary"):
            errors = validate_form(book_data, author_data, book_data["is_single_author"], publisher)
            if errors:
                st.error("\n".join(errors), icon="🚨")
            else:
                with st.spinner("Saving..."):
                    time.sleep(2)
                    with conn.session as s:
                        try:
                            # Insert book with publisher and other fields
                            s.execute(text("""
                                INSERT INTO books (title, date, is_single_author, is_publish_only, publisher)
                                VALUES (:title, :date, :is_single_author, :is_publish_only, :publisher)
                            """), params={
                                "title": book_data["title"], 
                                "date": book_data["date"], 
                                "is_single_author": book_data["is_single_author"],
                                "is_publish_only": book_data["is_publish_only"],
                                "publisher": book_data["publisher"]
                            })
                            book_id = s.execute(text("SELECT LAST_INSERT_ID();")).scalar()

                            # Process only active authors if publisher allows authors
                            if publisher not in ["AG Kids", "NEET/JEE"]:
                                active_authors = [a for a in author_data if is_author_active(a)]
                                for author in active_authors:
                                    if author["author_id"]:
                                        # Use existing author
                                        author_id_to_link = author["author_id"]
                                    else:
                                        # Insert new author
                                        s.execute(text("""
                                            INSERT INTO authors (name, email, phone)
                                            VALUES (:name, :email, :phone)
                                            ON DUPLICATE KEY UPDATE name=name
                                        """), params={"name": author["name"], "email": author["email"], "phone": author["phone"]})
                                        author_id_to_link = s.execute(text("SELECT LAST_INSERT_ID();")).scalar()

                                    if book_id and author_id_to_link:
                                        s.execute(text("""
                                            INSERT INTO book_authors (book_id, author_id, author_position, corresponding_agent, publishing_consultant)
                                            VALUES (:book_id, :author_id, :author_position, :corresponding_agent, :publishing_consultant)
                                        """), params={
                                            "book_id": book_id,
                                            "author_id": author_id_to_link,
                                            "author_position": author["author_position"],
                                            "corresponding_agent": author["corresponding_agent"],
                                            "publishing_consultant": author["publishing_consultant"]
                                        })
                            s.commit()
                            st.success("Book and Authors Saved Successfully!", icon="✔️")
                            time.sleep(1)
                            st.session_state.authors = [
                                {"name": "", "email": "", "phone": "", "author_id": None, "author_position": f"{i+1}{'st' if i == 0 else 'nd' if i == 1 else 'rd' if i == 2 else 'th'}", "corresponding_agent": "", "publishing_consultant": ""}
                                for i in range(4)
                            ]
                            st.rerun()
                        except Exception as db_error:
                            s.rollback()
                            st.error(f"Database error: {db_error}")

    with col2:
        if st.button("Cancel", key="dialog_cancel", type="secondary"):
            st.session_state.authors = [
                {"name": "", "email": "", "phone": "", "author_id": None, "author_position": f"{i+1}{'st' if i == 0 else 'nd' if i == 1 else 'rd' if i == 2 else 'th'}", "corresponding_agent": "", "publishing_consultant": ""}
                for i in range(4)
            ]  # Reset authors
            st.rerun()


###################################################################################################################################
##################################--------------- Edit ISBN Dialog ----------------------------##################################
###################################################################################################################################

from datetime import datetime

@st.dialog("Manage ISBN and Book Title", width="large")
def manage_isbn_dialog(conn, book_id, current_apply_isbn, current_isbn, current_isbn_receive_date=None):
    # Fetch current book details (title, date, and is_publish_only) from the database
    book_details = fetch_book_details(book_id, conn)
    if book_details.empty:
        st.error("❌ Book not found in database.")
        return
    
    # Extract current title, date, and is_publish_only from the DataFrame
    current_title = book_details.iloc[0]['title']
    current_date = book_details.iloc[0]['date']
    current_is_publish_only = book_details.iloc[0].get('is_publish_only', 0) == 1  # Default to False if not present

    # Main container
    with st.container():
        # Header with Book ID
        st.markdown(f"### {book_id} - {current_title}", unsafe_allow_html=True)

        st.markdown("<h5 style='color: #4CAF50;'>Book Details</h5>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            col1, col2 = st.columns([3, 1])
            with col1:
                new_title = st.text_input(
                    "Book Title",
                    value=current_title,
                    key=f"title_{book_id}",
                    help="Enter the book title"
                )
            with col2:
                new_date = st.date_input(
                    "Book Date",
                    value=current_date if current_date else datetime.today(),
                    key=f"date_{book_id}",
                    help="Select the book date"
                )
            # Add is_publish_only toggle
            new_is_publish_only = st.toggle(
                "Publish Only?",
                value=current_is_publish_only,
                key=f"is_publish_only_{book_id}",
                help="Enable this to mark the book as publish only (disables writing operations)"
            )
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<h5 style='color: #4CAF50;'>ISBN Details</h5>", unsafe_allow_html=True)
        # ISBN Details Section
        with st.container(border=True):
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            apply_isbn = st.checkbox(
                "ISBN Applied?",
                value=bool(current_apply_isbn),
                key=f"apply_{book_id}",
                help="Check if ISBN application has been made"
            )
            receive_isbn = st.checkbox(
                "ISBN Received?",
                value=bool(pd.notna(current_isbn)),
                key=f"receive_{book_id}",
                disabled=not apply_isbn,
                help="Check if ISBN has been received (requires ISBN Applied)"
            )
            
            if apply_isbn and receive_isbn:
                col3, col4 = st.columns(2)
                with col3:
                    new_isbn = st.text_input(
                        "ISBN",
                        value=current_isbn if pd.notna(current_isbn) else "",
                        key=f"isbn_input_{book_id}",
                        help="Enter the ISBN number"
                    )
                with col4:
                    default_date = current_isbn_receive_date if current_isbn_receive_date else datetime.today()
                    isbn_receive_date = st.date_input(
                        "ISBN Receive Date",
                        value=default_date,
                        key=f"date_input_{book_id}",
                        help="Select the date ISBN was received"
                    )
            else:
                new_isbn = None
                isbn_receive_date = None
            st.markdown('</div>', unsafe_allow_html=True)

        # Save Button
        if st.button("Save Changes", key=f"save_isbn_{book_id}", type="secondary"):
            with st.spinner("Saving changes..."):
                time.sleep(2) 
                with conn.session as s:
                    if apply_isbn and receive_isbn and new_isbn:
                        s.execute(
                            text("""
                                UPDATE books 
                                SET apply_isbn = :apply_isbn, 
                                    isbn = :isbn, 
                                    isbn_receive_date = :isbn_receive_date, 
                                    title = :title, 
                                    date = :date,
                                    is_publish_only = :is_publish_only
                                WHERE book_id = :book_id
                            """),
                            {
                                "apply_isbn": 1, 
                                "isbn": new_isbn, 
                                "isbn_receive_date": isbn_receive_date, 
                                "title": new_title, 
                                "date": new_date,
                                "is_publish_only": 1 if new_is_publish_only else 0,
                                "book_id": book_id
                            }
                        )
                    elif apply_isbn and not receive_isbn:
                        s.execute(
                            text("""
                                UPDATE books 
                                SET apply_isbn = :apply_isbn, 
                                    isbn = NULL, 
                                    isbn_receive_date = NULL, 
                                    title = :title, 
                                    date = :date,
                                    is_publish_only = :is_publish_only
                                WHERE book_id = :book_id
                            """),
                            {
                                "apply_isbn": 1, 
                                "title": new_title, 
                                "date": new_date,
                                "is_publish_only": 1 if new_is_publish_only else 0,
                                "book_id": book_id
                            }
                        )
                    else:
                        s.execute(
                            text("""
                                UPDATE books 
                                SET apply_isbn = :apply_isbn, 
                                    isbn = NULL, 
                                    isbn_receive_date = NULL, 
                                    title = :title, 
                                    date = :date,
                                    is_publish_only = :is_publish_only
                                WHERE book_id = :book_id
                            """),
                            {
                                "apply_isbn": 0, 
                                "title": new_title, 
                                "date": new_date,
                                "is_publish_only": 1 if new_is_publish_only else 0,
                                "book_id": book_id
                            }
                        )
                    s.commit()
                st.success("Book Details Updated Successfully!", icon="✔️")
                time.sleep(1)
                st.rerun()


###################################################################################################################################
##################################--------------- Edit Price Dialog ----------------------------##################################
###################################################################################################################################


@st.dialog("Manage Book Price and Author Payments", width="large")
def manage_price_dialog(book_id, current_price, conn):
    # Fetch book details for title
    book_details = fetch_book_details(book_id, conn)
    book_title = book_details.iloc[0]['title'] if not book_details.empty else "Unknown Title"
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
    with col2:
        if st.button(":material/refresh: Refresh", key="refresh_price", type="tertiary"):
            st.cache_data.clear()

    # Updated Streamlit-aligned CSS with improved visuals
    st.markdown("""
        <style>
                
        .payment-status {
            font-size: 12px;
            padding: 3px 8px;
            border-radius: 12px;
            margin-left: 10px;
            display: inline-block;
        }
        .status-paid { background-color: #e6ffe6; color: #006600; }
        .status-partial { background-color: #fff3e6; color: #cc6600; }
        .status-pending { background-color: #ffe6e6; color: #cc0000; }
        .payment-box {
            padding: 10px;
            border-radius: 6px;
            margin: 0 4px 8px 0;
            text-align: center;
            font-size: 14px;
            line-height: 1.5;
            border: 1px solid #e0e0e0;
            background-color: #ffffff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: transform 0.2s ease, background-color 0.2s ease;
        }
        .payment-box:hover {
            background-color: #f9f9f9;
            transform: translateY(-2px);
        }
        .status-paid {
            background-color: #f0f9eb;
            border-color: #b7e1a1;
            color: #2e7d32;
        }
        .status-partial {
            background-color: #fff4e6;
            border-color: #ffd8a8;
            color: #e65100;
        }
        .status-pending {
            background-color: #f6f6f6;
            border-color: #d9d9d9;
            color: #666666;
        }
        .author-name {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .payment-text {
            font-size: 14px;
            font-weight: 400;
        }
        .agent-text {
            font-size: 11px;
            color: #888888;
            margin-top: 6px;
            font-style: italic;
        }
        .status-badge {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 10px;
            display: inline-block;
            margin-top: 4px;
        }
        .status-paid .status-badge { background-color: #2e7d32; color: #ffffff; }
        .status-partial .status-badge { background-color: #e65100; color: #ffffff; }
        .status-pending .status-badge { background-color: #666666; color: #ffffff; }
        </style>
    """, unsafe_allow_html=True)

    # Payment Status Overview
    book_authors = fetch_book_authors(book_id, conn)
    
    if book_authors.empty:
        st.warning(f"No authors found for Book ID: {book_id}")
    else:
        cols = st.columns(len(book_authors), gap="small")
        for i, (_, row) in enumerate(book_authors.iterrows()):
            total_amount = int(row.get('total_amount', 0) or 0)
            emi1 = int(row.get('emi1', 0) or 0)
            emi2 = int(row.get('emi2', 0) or 0)
            emi3 = int(row.get('emi3', 0) or 0)
            amount_paid = emi1 + emi2 + emi3
            agent = row.get('corresponding_agent', 'Unknown Agent')

            # Determine payment status
            if amount_paid >= total_amount and total_amount > 0:
                status_class = "status-paid"
                status_text = f"₹{amount_paid}/₹{total_amount}"
                badge_text = "Paid"
            elif amount_paid > 0:
                status_class = "status-partial"
                status_text = f"₹{amount_paid}/₹{total_amount}"
                badge_text = "Partial"
            else:
                status_class = "status-pending"
                status_text = "₹0/₹{total_amount}" if total_amount > 0 else "N/A"
                badge_text = "Pending"

            with cols[i]:
                html = f"""
                    <div class="payment-box {status_class}">
                        <div class="author-name">{row['name']}</div>
                        <div class="payment-text">{status_text}</div>
                        <div class="status-badge">{badge_text}</div>
                        <div class="agent-text">{agent}</div>
                    </div>
                """
                st.markdown(html, unsafe_allow_html=True)

    contrn = st.container(border=True)
    with contrn:
        # Section 1: Book Price
        st.markdown("<h5 style='color: #4CAF50;'>Book Price</h5>", unsafe_allow_html=True)
        col1,col2 = st.columns([1,1])
        with col1:
            price_str = st.text_input(
                "Book Price (₹)",
                value=str(int(current_price)) if pd.notna(current_price) else "",
                key=f"price_{book_id}",
                placeholder="Enter whole amount"
            )
            
            if st.button("Save Book Price", key=f"save_price_{book_id}"):
                with st.spinner("Saving..."):
                    time.sleep(2)
                    try:
                        price = int(price_str) if price_str.strip() else None
                        if price is not None and price < 0:
                            st.error("Price cannot be negative")
                            return
                            
                        with conn.session as s:
                            s.execute(
                                text("UPDATE books SET price = :price WHERE book_id = :book_id"),
                                {"price": price, "book_id": book_id}
                            )
                            s.commit()
                        st.success("Book Price Updated Successfully", icon="✔️")
                    except ValueError:
                        st.error("Please enter a valid whole number", icon="🚨")

    cont = st.container(border=True)
    with cont:
        # Section 2: Author Payments with Tabs
        st.markdown("<h5 style='color: #4CAF50;'>Author Payments</h5>", unsafe_allow_html=True)
        if not book_authors.empty:
            total_author_amounts = 0
            updated_authors = []

            # Create tabs for each author
            tab_titles = [f"{row['name']} (ID: {row['author_id']})" for _, row in book_authors.iterrows()]
            tabs = st.tabs(tab_titles)

            for tab, (_, row) in zip(tabs, book_authors.iterrows()):
                # Inside the `for tab, (_, row) in zip(tabs, book_authors.iterrows()):` loop
                with tab:
                    # Fetch existing payment details
                    total_amount = int(row.get('total_amount', 0) or 0)
                    emi1 = int(row.get('emi1', 0) or 0)
                    emi2 = int(row.get('emi2', 0) or 0)
                    emi3 = int(row.get('emi3', 0) or 0)
                    emi1_date = row.get('emi1_date', None)
                    emi2_date = row.get('emi2_date', None)
                    emi3_date = row.get('emi3_date', None)
                    # New fields for payment mode and transaction ID (now nullable in DB)
                    emi1_payment_mode = row.get('emi1_payment_mode', None)  # Could be None
                    emi2_payment_mode = row.get('emi2_payment_mode', None)  # Could be None
                    emi3_payment_mode = row.get('emi3_payment_mode', None)  # Could be None
                    emi1_transaction_id = row.get('emi1_transaction_id', '')
                    emi2_transaction_id = row.get('emi2_transaction_id', '')
                    emi3_transaction_id = row.get('emi3_transaction_id', '')
                    amount_paid = emi1 + emi2 + emi3

                    # Payment status (unchanged)
                    if amount_paid >= total_amount and total_amount > 0:
                        status = '<span class="payment-status status-paid">Fully Paid</span>'
                    elif amount_paid > 0:
                        status = '<span class="payment-status status-partial">Partially Paid</span>'
                    else:
                        status = '<span class="payment-status status-pending">Pending</span>'
                    st.markdown(f"**Payment Status:** {status}", unsafe_allow_html=True)

                    # Total Amount Due (unchanged)
                    total_str = st.text_input(
                        "Total Amount Due (₹)",
                        value=str(total_amount) if total_amount > 0 else "",
                        key=f"total_{row['id']}",
                        placeholder="Enter whole amount"
                    )

                    # EMI Payments with Dates, Payment Mode, and Transaction ID
                    st.markdown("#### EMI Details")
                    payment_modes = ["Cash", "UPI", "Bank Deposit"]

                    # EMI 1
                    st.markdown("**EMI 1**")
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        emi1_str = st.text_input(
                            "Amount (₹)",
                            value=str(emi1) if emi1 > 0 else "",
                            key=f"emi1_{row['id']}"
                        )
                    with col2:
                        emi1_date_new = st.date_input(
                            "Date",
                            value=pd.to_datetime(emi1_date) if emi1_date else None,
                            key=f"emi1_date_{row['id']}"
                        )
                    with col3:
                        emi1_mode = st.selectbox(
                            "Payment Mode",
                            payment_modes,
                            index=payment_modes.index(emi1_payment_mode) if emi1_payment_mode in payment_modes else 0,
                            key=f"emi1_mode_{row['id']}"
                        )
                    if emi1_mode in ["UPI", "Bank Deposit"]:
                        emi1_txn_id = st.text_input(
                            "Transaction ID",
                            value=emi1_transaction_id,
                            key=f"emi1_txn_{row['id']}",
                            placeholder="Enter Transaction ID"
                        )
                    else:
                        emi1_txn_id = ""

                    # EMI 2
                    st.markdown("**EMI 2**")
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        emi2_str = st.text_input(
                            "Amount (₹)",
                            value=str(emi2) if emi2 > 0 else "",
                            key=f"emi2_{row['id']}"
                        )
                    with col2:
                        emi2_date_new = st.date_input(
                            "Date",
                            value=pd.to_datetime(emi2_date) if emi2_date else None,
                            key=f"emi2_date_{row['id']}"
                        )
                    with col3:
                        emi2_mode = st.selectbox(
                            "Payment Mode",
                            payment_modes,
                            index=payment_modes.index(emi2_payment_mode) if emi2_payment_mode in payment_modes else 0,
                            key=f"emi2_mode_{row['id']}"
                        )
                    if emi2_mode in ["UPI", "Bank Deposit"]:
                        emi2_txn_id = st.text_input(
                            "Transaction ID",
                            value=emi2_transaction_id,
                            key=f"emi2_txn_{row['id']}",
                            placeholder="Enter Transaction ID"
                        )
                    else:
                        emi2_txn_id = ""

                    # EMI 3
                    st.markdown("**EMI 3**")
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        emi3_str = st.text_input(
                            "Amount (₹)",
                            value=str(emi3) if emi3 > 0 else "",
                            key=f"emi3_{row['id']}"
                        )
                    with col2:
                        emi3_date_new = st.date_input(
                            "Date",
                            value=pd.to_datetime(emi3_date) if emi3_date else None,
                            key=f"emi3_date_{row['id']}"
                        )
                    with col3:
                        emi3_mode = st.selectbox(
                            "Payment Mode",
                            payment_modes,
                            index=payment_modes.index(emi3_payment_mode) if emi3_payment_mode in payment_modes else 0,
                            key=f"emi3_mode_{row['id']}"
                        )
                    if emi3_mode in ["UPI", "Bank Deposit"]:
                        emi3_txn_id = st.text_input(
                            "Transaction ID",
                            value=emi3_transaction_id,
                            key=f"emi3_txn_{row['id']}",
                            placeholder="Enter Transaction ID"
                        )
                    else:
                        emi3_txn_id = ""

                    # Calculate remaining balance
                    try:
                        new_total = int(total_str) if total_str.strip() else 0
                        new_emi1 = int(emi1_str) if emi1_str.strip() else 0
                        new_emi2 = int(emi2_str) if emi2_str.strip() else 0
                        new_emi3 = int(emi3_str) if emi3_str.strip() else 0
                        new_paid = new_emi1 + new_emi2 + new_emi3
                        remaining = new_total - new_paid
                        total_author_amounts += new_total
                        updated_authors.append((row['id'], new_total, new_emi1, new_emi2, new_emi3, 
                                                emi1_date_new, emi2_date_new, emi3_date_new,
                                                emi1_mode, emi2_mode, emi3_mode,
                                                emi1_txn_id, emi2_txn_id, emi3_txn_id))
                    except ValueError:
                        st.error("Please enter valid whole numbers for all fields")
                        return

                    st.markdown(f"<span style='color:green'>**Total Paid:** ₹{new_paid}</span> | <span style='color:red'>**Remaining Balance:** ₹{remaining}</span>", unsafe_allow_html=True)

                    # Save button
                    if st.button("Save Payment", key=f"save_payment_{row['id']}"):
                        with st.spinner("Saving Payment..."):
                            time.sleep(2)
                            if new_paid > new_total:
                                st.error("Total EMI payments cannot exceed total amount")
                            elif new_total < 0 or new_emi1 < 0 or new_emi2 < 0 or new_emi3 < 0:
                                st.error("Amounts cannot be negative")
                            else:
                                book_price = int(price_str) if price_str.strip() else current_price
                                if pd.isna(book_price):
                                    st.error("Please set a book price first")
                                    return
                                if total_author_amounts > book_price:
                                    st.error(f"Total author amounts (₹{total_author_amounts}) cannot exceed book price (₹{book_price})")
                                    return

                                updates = {
                                    "total_amount": new_total,
                                    "emi1": new_emi1,
                                    "emi2": new_emi2,
                                    "emi3": new_emi3,
                                    "emi1_date": emi1_date_new,
                                    "emi2_date": emi2_date_new,
                                    "emi3_date": emi3_date_new,
                                    "emi1_payment_mode": emi1_mode,
                                    "emi2_payment_mode": emi2_mode,
                                    "emi3_payment_mode": emi3_mode,
                                    "emi1_transaction_id": emi1_txn_id,
                                    "emi2_transaction_id": emi2_txn_id,
                                    "emi3_transaction_id": emi3_txn_id
                                }
                                update_book_authors(row['id'], updates, conn)
                                st.success(f"Payment updated for {row['name']}", icon="✔️")
                                st.cache_data.clear()


###################################################################################################################################
##################################--------------- Edit Auhtor Dialog ----------------------------##################################
###################################################################################################################################



# Function to fetch book_author details along with author details for a given book_id
def fetch_book_authors(book_id, conn):
    query = f"""
    SELECT ba.id, ba.book_id, ba.author_id, a.name, a.email, a.phone, 
           ba.author_position, ba.welcome_mail_sent, ba.corresponding_agent, 
           ba.publishing_consultant, ba.photo_recive, ba.id_proof_recive, 
           ba.author_details_sent, ba.cover_agreement_sent, ba.agreement_received, 
           ba.digital_book_sent, ba.digital_book_approved, ba.plagiarism_report, 
           ba.printing_confirmation, ba.delivery_address, ba.delivery_charge, 
           ba.number_of_books, ba.total_amount, ba.emi1, ba.emi2, ba.emi3,
           ba.emi1_date, ba.emi2_date, ba.emi3_date,
           ba.delivery_date, ba.tracking_id, ba.delivery_vendor,
           ba.emi1_payment_mode, ba.emi2_payment_mode, ba.emi3_payment_mode,
           ba.emi1_transaction_id, ba.emi2_transaction_id, ba.emi3_transaction_id
    FROM book_authors ba
    JOIN authors a ON ba.author_id = a.author_id
    WHERE ba.book_id = '{book_id}'
    """
    return conn.query(query, show_spinner = False)

# Function to update book_authors table
def update_book_authors(id, updates, conn):
    set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
    query = f"UPDATE book_authors SET {set_clause} WHERE id = :id"
    params = updates.copy()
    params["id"] = int(id)
    with conn.session as session:
        session.execute(text(query), params)
        session.commit()

# Function to delete a book_author entry
def delete_book_author(id, conn):
    query = "DELETE FROM book_authors WHERE id = :id"
    with conn.session as session:
        session.execute(text(query), {"id": int(id)})
        session.commit()

# Constants
MAX_AUTHORS = 4

# Updated dialog for editing author details with improved UI
@st.dialog("Edit Author Details", width='large')
def edit_author_dialog(book_id, conn):
    # Fetch book details for title, is_single_author, num_copies, and print_status
    book_details = fetch_book_details(book_id, conn)
    if book_details.empty:
        st.markdown(f"### Authors for Book ID: {book_id}")
        st.error("❌ Book details not found.")
        if st.button("Close"):
            st.rerun()
        return

    book_title = book_details.iloc[0]['title']
    is_single_author = book_details.iloc[0]['is_single_author']
    num_copies = book_details.iloc[0]['num_copies']
    print_status = book_details.iloc[0]['print_status']
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
    with col2:
        if st.button(":material/refresh: Refresh", key="refresh_author", type="tertiary"):
            st.cache_data.clear()

    # Custom CSS for better aesthetics
    st.markdown("""
        <style>
        .stTabs { padding-bottom: 10px; }
        .info-box { 
            background-color: #f0f2f6; 
            border-radius: 8px; 
            margin-bottom: 10px; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
        }
        .error-box {
            background-color: #ffcccc;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .success-box {
            background-color: #e6ffe6;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Fetch author details
    book_authors = fetch_book_authors(book_id, conn)
    if book_authors.empty:
        st.warning(f"No authors found for Book ID: {book_id}")
        if st.button("Close"):
            st.rerun()
        return

    # Initialize session state for expander states if not already set
    if 'expander_states' not in st.session_state:
        st.session_state.expander_states = {}

    for _, row in book_authors.iterrows():
        author_id = row['author_id']
        author_position = row['author_position']
        # Use session state to track whether this author's expander is open
        expander_key = f"expander_{author_id}"
        if expander_key not in st.session_state.expander_states:
            st.session_state.expander_states[expander_key] = False  # Default to collapsed

        # Wrap each author in an expander, preserving its state
        with st.expander(f"📖 {row['name']} (ID: {author_id}) Position: {author_position}", expanded=st.session_state.expander_states[expander_key]):

            # Display author details in a styled box
            with st.container():
                st.markdown('<div class="info-box">', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**📌 Author ID:** {row['author_id']}")
                    st.markdown(f"**👤 Name:** {row['name']}")
                with col2:
                    st.markdown(f"**📧 Email:** {row['email'] or 'N/A'}")
                    st.markdown(f"**📞 Phone:** {row['phone'] or 'N/A'}")
                st.markdown('</div>', unsafe_allow_html=True)

                # Tabs for organizing fields (disable Delivery tab if print_status is 0)
                tab_titles = ["Checklists", "Basic Info", "Delivery"]
                tab_objects = st.tabs(tab_titles)
                
                with st.form(key=f"edit_form_{row['id']}", border=False):
                    updates = {}

                    # Tab 1: Basic Info
                    with tab_objects[1]:
                        col3, col4 = st.columns(2)
                        with col3:
                            existing_positions = [author['author_position'] for _, author in book_authors.iterrows() if author['id'] != row['id']]
                            available_positions = [pos for pos in ["1st", "2nd", "3rd", "4th"] if pos not in existing_positions]
                            updates['author_position'] = st.selectbox(
                                "Author Position",
                                available_positions,
                                index=available_positions.index(row['author_position']) if row['author_position'] in available_positions else 0,
                                help="Select the author's position in the book.",
                                key=f"author_position_{row['id']}"
                            )
                        with col4:
                            updates['corresponding_agent'] = st.text_input(
                                "Corresponding Agent",
                                value=row['corresponding_agent'] or "",
                                help="Enter the name of the corresponding agent.",
                                key=f"corresponding_agent_{row['id']}"
                            )
                        updates['publishing_consultant'] = st.text_input(
                            "Publishing Consultant",
                            value=row['publishing_consultant'] or "",
                            help="Enter the name of the publishing consultant.",
                            key=f"publishing_consultant_{row['id']}"
                        )

                    # Tab 2: Checklists
                    with tab_objects[0]:
                        col5, col6 = st.columns(2)
                        with col5:
                            updates['welcome_mail_sent'] = st.checkbox(
                                "✔️ Welcome Mail Sent",
                                value=bool(row['welcome_mail_sent']),
                                help="Check if the welcome email has been sent.",
                                key=f"welcome_mail_sent_{row['id']}"
                            )
                            updates['digital_book_sent'] = st.checkbox(
                                "📘 Digital Book Sent",
                                value=bool(row['digital_book_sent']),
                                help="Check if the digital book has been sent.",
                                key=f"digital_book_sent_{row['id']}"
                            )
                            updates['digital_book_approved'] = st.checkbox(
                                "✔️ Digital Book Approved",
                                value=bool(row['digital_book_approved']),
                                help="Check if the digital book has been approved.",
                                key=f"digital_book_approved_{row['id']}"
                            )
                            updates['plagiarism_report'] = st.checkbox(
                                "📝 Plagiarism Report",
                                value=bool(row['plagiarism_report']),
                                help="Check if the plagiarism report has been received.",
                                key=f"plagiarism_report_{row['id']}"
                            )
                            updates['photo_recive'] = st.checkbox(
                                "📷 Photo Received",
                                value=bool(row['photo_recive']),
                                help="Check if the author's photo has been received.",
                                key=f"photo_recive_{row['id']}"
                            )
                        with col6:
                            updates['id_proof_recive'] = st.checkbox(
                                "🆔 ID Proof Received",
                                value=bool(row['id_proof_recive']),
                                help="Check if the author's ID proof has been received.",
                                key=f"id_proof_recive_{row['id']}"
                            )
                            updates['author_details_sent'] = st.checkbox(
                                "✉️ Author Details Sent",
                                value=bool(row['author_details_sent']),
                                help="Check if the author's details have been sent.",
                                key=f"author_details_sent_{row['id']}"
                            )
                            updates['cover_agreement_sent'] = st.checkbox(
                                "📜 Cover Agreement Sent",
                                value=bool(row['cover_agreement_sent']),
                                help="Check if the cover agreement has been sent.",
                                key=f"cover_agreement_sent_{row['id']}"
                            )
                            updates['agreement_received'] = st.checkbox(
                                "✔️ Agreement Received",
                                value=bool(row['agreement_received']),
                                help="Check if the agreement has been received.",
                                key=f"agreement_received_{row['id']}"
                            )
                            updates['printing_confirmation'] = st.checkbox(
                                "🖨️ Printing Confirmation",
                                value=bool(row['printing_confirmation']),
                                help="Check if printing confirmation has been received.",
                                key=f"printing_confirmation_{row['id']}"
                            )

                    # Tab 3: Delivery (disabled if print_status is 0)
                    with tab_objects[2]:
                        if print_status == 0:
                            st.warning("⚠️ Delivery details are disabled because printing status is not confirmed.")
                        else:
                            col7, col8, col9 = st.columns(3)
                            with col7:
                                updates['delivery_address'] = st.text_area(
                                    "Delivery Address",
                                    value=row['delivery_address'] or "",
                                    height=100,
                                    help="Enter the delivery address.",
                                    key=f"delivery_address_{row['id']}"
                                )
                                updates['delivery_date'] = st.date_input(
                                    "Delivery Date",
                                    value=row['delivery_date'],
                                    help="Enter the delivery date.",
                                    key=f"delivery_date_{row['id']}"
                                )
                            with col8:
                                updates['delivery_charge'] = st.number_input(
                                    "Delivery Charge (₹)",
                                    min_value=0.0,
                                    step=0.01,
                                    value=float(row['delivery_charge'] or 0.0),
                                    help="Enter the delivery charge in INR.",
                                    key=f"delivery_charge_{row['id']}"
                                )
                                updates['tracking_id'] = st.text_input(
                                    "Tracking ID",
                                    value=row['tracking_id'] or "",
                                    help="Enter the tracking ID for the delivery.",
                                    key=f"tracking_id_{row['id']}"
                                )
                            with col9:
                                updates['number_of_books'] = st.number_input(
                                    "Number of Books",
                                    min_value=0,
                                    step=1,
                                    value=int(row['number_of_books'] or 0),
                                    help="Enter the number of books to deliver.",
                                    key=f"number_of_books_{row['id']}"
                                )
                                updates['delivery_vendor'] = st.text_input(
                                    "Delivery Vendor",
                                    value=row['delivery_vendor'] or "",
                                    help="Enter the name of the delivery vendor.",
                                    key=f"delivery_vendor_{row['id']}"
                                )

                   # Submit and Remove buttons
                    col_submit, col_remove = st.columns([8, 1])
                    with col_submit:
                        if st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary"):
                            # Convert boolean values to integers for database
                            for key in updates:
                                if isinstance(updates[key], bool):
                                    updates[key] = int(updates[key])

                            try:
                                with st.spinner("Saving changes..."):
                                    time.sleep(2)
                                    update_book_authors(row['id'], updates, conn)
                                    st.cache_data.clear()
                                    st.success(f"✔️ Updated details for {row['name']} (Author ID: {row['author_id']})")
                            except Exception as e:
                                st.error(f"❌ Error updating author details: {e}")

                    with col_remove:
                        # Initialize session state for confirmation
                        confirmation_key = f"confirm_remove_{row['id']}"
                        if confirmation_key not in st.session_state:
                            st.session_state[confirmation_key] = False

                        if st.form_submit_button("🗑️", use_container_width=True, type="secondary", help = f"Remove {row['name']} from this book"):
                            st.session_state[confirmation_key] = True

                # Confirmation form outside the main form
                if st.session_state[confirmation_key]:
                    with st.form(f"confirm_form_{row['id']}", border=False):
                        st.warning(f"Are you sure you want to remove {row['name']} (Author ID: {row['author_id']}) from Book ID: {book_id}?")
                        col_confirm, col_cancel = st.columns(2)
                        with col_confirm:
                            if st.form_submit_button("Yes, Remove", use_container_width=True, type="primary"):
                                try:
                                    with st.spinner("Removing author..."):
                                        time.sleep(2)
                                        delete_book_author(row['id'], conn)
                                        st.cache_data.clear()
                                        st.success(f"✔️ Removed {row['name']} (Author ID: {row['author_id']}) from this book")
                                        st.session_state[confirmation_key] = False  # Reset confirmation state
                                except Exception as e:
                                    st.error(f"❌ Error removing author: {e}")
                        with col_cancel:
                            if st.form_submit_button("Cancel", use_container_width=True):
                                st.session_state[confirmation_key] = False  # Reset confirmation state
    

    book_authors = fetch_book_authors(book_id, conn)
    existing_author_count = len(book_authors)
    toggle_editable = existing_author_count <= 1  # Editable only if 0 or 1 author

    if existing_author_count == 1:
        toggle_col1, toggle_col2 = st.columns([3, 4])
        with toggle_col1:
            new_is_single_author = st.toggle(
                "Single Author?",
                value=is_single_author,
                key=f"single_author_toggle_{book_id}",
                help="Toggle between single and multiple authors",
                disabled=not toggle_editable
            )

        if toggle_editable and new_is_single_author != is_single_author:
            try:
                with st.spinner("Updating author mode..."):
                    with conn.session as s:
                        time.sleep(2)
                        s.execute(
                            text("UPDATE books SET is_single_author = :is_single_author WHERE book_id = :book_id"),
                            {"is_single_author": int(new_is_single_author), "book_id": book_id}
                        )
                        s.commit()
                    st.success(f"✔️ Updated to {'Single' if new_is_single_author else 'Multiple'} Author mode")
                    st.cache_data.clear()
                    is_single_author = new_is_single_author
            except Exception as e:
                st.error(f"❌ Error updating author mode: {e}")

    available_slots = MAX_AUTHORS - existing_author_count
    # st.write(f"Debug: Available slots = {available_slots}")  # Debug statement

    if is_single_author and existing_author_count >= 1:
        st.warning("⚠️ This book is marked as 'Single Author'. No additional authors can be added.")
        if st.button("Close"):
            st.rerun()
        return

    if existing_author_count >= MAX_AUTHORS:
        st.warning("⚠️ This book already has the maximum number of authors (4). No more authors can be added.")
        if st.button("Close"):
            st.rerun()
        return

    if existing_author_count == 0:
        st.warning(f"⚠️ No authors found for Book ID: {book_id}")

    # Helper functions (unchanged for brevity)
    def ensure_author_fields(author):
        default_author = {
            "name": "", "email": "", "phone": "", "author_id": None, "author_position": None,
            "corresponding_agent": "", "publishing_consultant": ""
        }
        for key, default_value in default_author.items():
            if key not in author:
                author[key] = default_value
        return author

    def initialize_new_authors(slots):
        return [
            {"name": "", "email": "", "phone": "", "author_id": None, "author_position": None,
            "corresponding_agent": "", "publishing_consultant": ""}
            for _ in range(slots)
        ]

    # Initialize session state
    if "new_authors" not in st.session_state or len(st.session_state.new_authors) != available_slots:
        st.session_state.new_authors = initialize_new_authors(available_slots)
    else:
        st.session_state.new_authors = [ensure_author_fields(author) for author in st.session_state.new_authors]

    # Check if new_authors exists and has the correct length; reinitialize if not
    if "new_authors" not in st.session_state or len(st.session_state.new_authors) != available_slots:
        st.session_state.new_authors = initialize_new_authors(available_slots)
    else:
        st.session_state.new_authors = [ensure_author_fields(author) for author in st.session_state.new_authors]

    def get_all_authors(conn):
        """Fetch all authors from the database."""
        with conn.session as s:
            try:
                query = text("SELECT author_id, name, email, phone FROM authors ORDER BY name")
                authors = s.execute(query).fetchall()
                return authors
            except Exception as e:
                st.error(f"❌ Error fetching authors: {e}")
                return []
            
    def get_unique_agents_and_consultants(conn):
        with conn.session as s:
            try:
                agent_query = text("SELECT DISTINCT corresponding_agent FROM book_authors WHERE corresponding_agent IS NOT NULL AND corresponding_agent != '' ORDER BY corresponding_agent")
                agents = [row[0] for row in s.execute(agent_query).fetchall()]
                
                consultant_query = text("SELECT DISTINCT publishing_consultant FROM book_authors WHERE publishing_consultant IS NOT NULL AND publishing_consultant != '' ORDER BY publishing_consultant")
                consultants = [row[0] for row in s.execute(consultant_query).fetchall()]
                
                return agents, consultants
            except Exception as e:
                st.error(f"Error fetching agents/consultants: {e}")
                return [], []

    def validate_email(email):
        """Validate email format."""
        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(email_pattern, email))

    def validate_phone(phone):
        """Validate phone number format (basic validation)."""
        phone_pattern = r"^\+?\d{10,15}$"
        return bool(re.match(phone_pattern, phone))

    def is_author_complete(author):
        """Check if an author entry is complete (all required fields are filled)."""
        return (
            author["name"] and
            author["email"] and validate_email(author["email"]) and
            author["phone"] and validate_phone(author["phone"]) and
            author["author_position"] and
            author["corresponding_agent"] and
            author["publishing_consultant"]
        )

    def validate_author(author, existing_positions, existing_author_ids, all_new_authors, index, is_single_author):
        """Validate an author's details, including single author constraint."""
        if not author["name"]:
            return False, "Author name is required."
        if not author["email"]:
            return False, "Email is required."
        if not validate_email(author["email"]):
            return False, "Invalid email format."
        if not author["phone"]:
            return False, "Phone number is required."
        if not validate_phone(author["phone"]):
            return False, "Invalid phone number format (e.g., +919876543210 or 9876543210)."
        if not author["author_position"]:
            return False, "Author position is required."
        if not author["corresponding_agent"]:
            return False, "Corresponding agent is required."
        if not author["publishing_consultant"]:
            return False, "Publishing consultant is required."
        
        # Check for duplicate positions
        if author["author_position"] in existing_positions:
            return False, f"Position '{author['author_position']}' is already taken by an existing author."
        new_positions = [a["author_position"] for i, a in enumerate(all_new_authors) if i != index and a["author_position"]]
        if author["author_position"] in new_positions:
            return False, f"Position '{author['author_position']}' is already taken by another new author."
        
        # Check for duplicate authors
        if author["author_id"] and author["author_id"] in existing_author_ids:
            return False, f"Author '{author['name']}' (ID: {author['author_id']}) is already linked to this book."
        new_author_ids = [a["author_id"] for i, a in enumerate(all_new_authors) if i != index and a["author_id"]]
        if author["author_id"] and author["author_id"] in new_author_ids:
            return False, f"Author '{author['name']}' (ID: {author['author_id']}) is already added as a new author."

        # If is_single_author is True, ensure only one author is added in total
        if is_single_author and existing_author_count + len([a for a in all_new_authors if is_author_complete(a)]) > 1:
            return False, "Only one author is allowed because this book is marked as 'Single Author'."

        return True, ""

    # Author selection and form
    st.markdown(f"### Add Up to {available_slots} New Authors")
    all_authors = get_all_authors(conn)
    author_options = ["Add New Author"] + [f"{a.name} (ID: {a.author_id})" for a in all_authors]
    unique_agents, unique_consultants = get_unique_agents_and_consultants(conn)
    agent_options = ["Select Agent"] + unique_agents + ["Add New..."]
    consultant_options = ["Select Consultant"] + unique_consultants + ["Add New..."]

    existing_positions = [author["author_position"] for _, author in book_authors.iterrows()]
    existing_author_ids = [author["author_id"] for _, author in book_authors.iterrows()]

    # Render expanders
    for i in range(available_slots):
        with st.expander(f"New Author {i+1}", expanded=False):
            with st.container(border=False):
                st.markdown(f"#### New Author {i+1}")
                disabled = is_single_author and existing_author_count >= 1
                if disabled and i == 0:
                    st.warning("⚠️ This section is disabled because the book is marked as 'Single Author' and already has one author.")

                selected_author = st.selectbox(
                    f"Select Author {i+1}",
                    author_options,
                    key=f"new_author_select_{i}",
                    help="Select an existing author or 'Add New Author' to enter new details.",
                    disabled=disabled
                )

                if selected_author != "Add New Author" and selected_author and not disabled:
                    selected_author_id = int(selected_author.split('(ID: ')[1][:-1])
                    selected_author_details = next((a for a in all_authors if a.author_id == selected_author_id), None)
                    if selected_author_details:
                        st.session_state.new_authors[i].update({
                            "name": selected_author_details.name,
                            "email": selected_author_details.email,
                            "phone": selected_author_details.phone,
                            "author_id": selected_author_details.author_id
                        })
                elif selected_author == "Add New Author" and not disabled:
                    st.session_state.new_authors[i]["author_id"] = None

                col1, col2 = st.columns(2)
                st.session_state.new_authors[i]["name"] = col1.text_input(
                    f"Author Name {i+1}", st.session_state.new_authors[i]["name"], key=f"new_name_{i}",
                    placeholder="Enter author name..", help="Enter the full name of the author.", disabled=disabled
                )
                current_new_positions = [a["author_position"] for j, a in enumerate(st.session_state.new_authors) if j != i and a["author_position"]]
                all_taken_positions = existing_positions + current_new_positions
                available_positions = [pos for pos in ["1st", "2nd", "3rd", "4th"] if pos not in all_taken_positions]
                if available_positions:
                    st.session_state.new_authors[i]["author_position"] = col2.selectbox(
                        f"Position {i+1}",
                        available_positions,
                        key=f"new_author_position_{i}",
                        help="Select a unique position for this author.",
                        disabled=disabled
                    )
                elif not disabled:
                    st.error("❌ No available positions left.")

                col3, col4 = st.columns(2)
                st.session_state.new_authors[i]["phone"] = col3.text_input(
                    f"Phone {i+1}", st.session_state.new_authors[i]["phone"], key=f"new_phone_{i}",
                    placeholder="Enter phone..", help="Enter a valid phone number (e.g., +919876543210 or 9876543210).", disabled=disabled
                )
                st.session_state.new_authors[i]["email"] = col4.text_input(
                    f"Email {i+1}", st.session_state.new_authors[i]["email"], key=f"new_email_{i}",
                    placeholder="Enter email..", help="Enter a valid email address (e.g., author@example.com).", disabled=disabled
                )

                col5, col6 = st.columns(2)
                selected_agent = col5.selectbox(
                    f"Corresponding Agent {i+1}",
                    agent_options,
                    index=agent_options.index(st.session_state.new_authors[i]["corresponding_agent"]) if st.session_state.new_authors[i]["corresponding_agent"] in unique_agents else 0,
                    key=f"new_agent_select_{i}",
                    help="Select an existing agent or 'Add New...' to enter a new one.",
                    disabled=disabled
                )
                if selected_agent == "Add New..." and not disabled:
                    st.session_state.new_authors[i]["corresponding_agent"] = col5.text_input(
                        f"New Agent Name {i+1}",
                        value="",
                        key=f"new_agent_input_{i}",
                        placeholder="Enter new agent name...",
                        help="Enter the name of the new corresponding agent."
                    )
                elif selected_agent != "Select Agent" and not disabled:
                    st.session_state.new_authors[i]["corresponding_agent"] = selected_agent

                selected_consultant = col6.selectbox(
                    f"Publishing Consultant {i+1}",
                    consultant_options,
                    index=consultant_options.index(st.session_state.new_authors[i]["publishing_consultant"]) if st.session_state.new_authors[i]["publishing_consultant"] in unique_consultants else 0,
                    key=f"new_consultant_select_{i}",
                    help="Select an existing consultant or 'Add New...' to enter a new one.",
                    disabled=disabled
                )
                if selected_consultant == "Add New..." and not disabled:
                    st.session_state.new_authors[i]["publishing_consultant"] = col6.text_input(
                        f"New Consultant Name {i+1}",
                        value="",
                        key=f"new_consultant_input_{i}",
                        placeholder="Enter new consultant name...",
                        help="Enter the name of the new publishing consultant."
                    )
                elif selected_consultant != "Select Consultant" and not disabled:
                    st.session_state.new_authors[i]["publishing_consultant"] = selected_consultant

    # Button section
    col1, col2 = st.columns([7, 1])
    with col1:
        if st.button("Add Authors to Book", key="add_authors_to_book", type="primary"):
            errors = []
            active_authors = [author for author in st.session_state.new_authors if is_author_complete(author)]
            if not active_authors:
                st.error("❌ Please fill in the details for at least one author to proceed.")
            else:
                for i, author in enumerate(active_authors):
                    is_valid, error_message = validate_author(author, existing_positions, existing_author_ids, st.session_state.new_authors, i, is_single_author)
                    if not is_valid:
                        errors.append(f"Author {i+1}: {error_message}")
                if errors:
                    for error in errors:
                        st.markdown(f'<div class="error-box">❌ {error}</div>', unsafe_allow_html=True)
                else:
                    try:
                        for author in active_authors:
                            if is_author_complete(author):
                                author_id_to_link = author["author_id"] or insert_author(conn, author["name"], author["email"], author["phone"])
                                if book_id and author_id_to_link:
                                    with conn.session as s:
                                        s.execute(
                                            text("""
                                                INSERT INTO book_authors (book_id, author_id, author_position, corresponding_agent, publishing_consultant)
                                                VALUES (:book_id, :author_id, :author_position, :corresponding_agent, :publishing_consultant)
                                            """),
                                            params={
                                                "book_id": book_id,
                                                "author_id": author_id_to_link,
                                                "author_position": author["author_position"],
                                                "corresponding_agent": author["corresponding_agent"],
                                                "publishing_consultant": author["publishing_consultant"]
                                            }
                                        )
                                        s.commit()
                        st.cache_data.clear()
                        st.success("✔️ New authors added successfully!")
                        del st.session_state.new_authors
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error adding authors: {e}")

    with col2:
        if st.button("Cancel", key="cancel_add_authors", type="secondary"):
            del st.session_state.new_authors
            st.rerun()

def insert_author(conn, name, email, phone):
    with conn.session as s:
        s.execute(
            text("""
                INSERT INTO authors (name, email, phone)
                VALUES (:name, :email, :phone)
                ON DUPLICATE KEY UPDATE name=name
            """),
            params={"name": name, "email": email, "phone": phone}
        )
        s.commit()
        return s.execute(text("SELECT LAST_INSERT_ID();")).scalar()
    

###################################################################################################################################
##################################--------------- Edit Operations Dialog ----------------------------##################################
###################################################################################################################################

@st.cache_data
def fetch_unique_names(column):
    query = f"SELECT DISTINCT {column} AS name FROM books WHERE {column} IS NOT NULL AND {column} != ''"
    return sorted(conn.query(query,show_spinner = False)['name'].tolist())

@st.dialog("Edit Operation Details", width='large')
def edit_operation_dialog(book_id, conn):
    # Fetch book details for title and is_publish_only
    book_details = fetch_book_details(book_id, conn)
    is_publish_only = False
    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        is_publish_only = book_details.iloc[0].get('is_publish_only', 0) == 1
        col1, col2 = st.columns([6, 1])
        with col1:
            st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
        with col2:
            if st.button(":material/refresh: Refresh", key="refresh_operations", type="tertiary"):
                st.cache_data.clear()
    else:
        st.markdown(f"### Operations for Book ID: {book_id}")
        st.warning("Book title not found.")

    # Streamlit-aligned CSS
    st.markdown("""
        <style>
        .status-box {
            padding: 6px 8px;
            border-radius: 4px;
            margin: 0 4px 4px 0;
            text-align: center;
            font-size: 12px;
            line-height: 1.4;
            border: 1px solid #e6e6e6;
            background-color: #ffffff;
        }
        .status-complete {
            background-color: #f0f9eb;
            border-color: #b7e1a1;
            color: #2e7d32;
        }
        .status-ongoing {
            background-color: #fff4e6;
            border-color: #ffd8a8;
            color: #e65100;
        }
        .status-pending {
            background-color: #f6f6f6;
            border-color: #d9d9d9;
            color: #666666;
        }
        </style>
    """, unsafe_allow_html=True)

    # Fetch operation details
    query = f"""
        SELECT writing_start, writing_end, writing_by, 
               proofreading_start, proofreading_end, proofreading_by, 
               formatting_start, formatting_end, formatting_by, 
               front_cover_start, front_cover_end,
               back_cover_start, back_cover_end, book_pages
        FROM books WHERE book_id = {book_id}
    """
    book_operations = conn.query(query, show_spinner=False)
    
    if book_operations.empty:
        st.warning(f"No operation details found for Book ID: {book_id}")
        current_data = {}
    else:
        current_data = book_operations.iloc[0].to_dict()

    # Initialize session state for all worker fields
    worker_keys = [
        f"writing_by_{book_id}",
        f"proofreading_by_{book_id}",
        f"formatting_by_{book_id}",
        f"cover_by_{book_id}"
    ]
    worker_defaults = [
        current_data.get('writing_by', ""),
        current_data.get('proofreading_by', ""),
        current_data.get('formatting_by', ""),
        current_data.get('cover_by', "")
    ]

    for key, default in zip(worker_keys, worker_defaults):
        if key not in st.session_state:
            st.session_state[key] = default

    # Streamlit-style Status Overview
    cols = st.columns(5, gap="small")
    operations = [
        ("Writing", "writing_start", "writing_end"),
        ("Proofreading", "proofreading_start", "proofreading_end"),
        ("Formatting", "formatting_start", "formatting_end"),
        ("Front Cover", "front_cover_start", "front_cover_end"),
        ("Back Cover", "back_cover_start", "back_cover_end")
    ]

    for i, (op_name, start_field, end_field) in enumerate(operations):
        with cols[i]:
            start = current_data.get(start_field)
            end = current_data.get(end_field)
            if end:
                status_class = "status-complete"
                end_date = str(end).split()[0] if end else ""
                status_text = f"Done<br>{end_date}"
            elif start:
                status_class = "status-ongoing"
                status_text = "Ongoing"
            else:
                status_class = "status-pending"
                status_text = "Pending"
            html = f"""
                <div class="status-box {status_class}">
                    <strong>{op_name}</strong><br>
                    {status_text}
                </div>
            """
            st.markdown(html, unsafe_allow_html=True)

    # Fetch unique names for each role
    writing_names = fetch_unique_names("writing_by")
    proofreading_names = fetch_unique_names("proofreading_by")
    formatting_names = fetch_unique_names("formatting_by")

    # Initialize session state for text inputs
    for key, value in [
        (f"writing_by_{book_id}", current_data.get('writing_by', "")),
        (f"proofreading_by_{book_id}", current_data.get('proofreading_by', "")),
        (f"formatting_by_{book_id}", current_data.get('formatting_by', "")),
    ]:
        if key not in st.session_state:
            st.session_state[key] = value

    # Define options for selectboxes
    writing_options = ["Select Writer"] + writing_names + ["Add New..."]
    proofreading_options = ["Select Proofreader"] + proofreading_names + ["Add New..."]
    formatting_options = ["Select Formatter"] + formatting_names + ["Add New..."]

    # Define tabs
    tab1, tab2, tab3, tab4 = st.tabs(["✍️ Writing", "🔍 Proofreading", "📏 Formatting", "🎨 Book Cover"])

    # Writing Tab
    with tab1:
        if is_publish_only:
            st.warning("Writing section is disabled because this book is in 'Publish Only' mode.")
        
        # Worker selection outside the form
        writing_options = ["Select Writer"] + fetch_unique_names("writing_by") + ["Add New..."]
        selected_writer = st.selectbox(
            "Writer",
            writing_options,
            index=(writing_options.index(st.session_state[f"writing_by_{book_id}"]) 
                if st.session_state[f"writing_by_{book_id}"] in writing_options else 0),
            key=f"writing_select_{book_id}",
            disabled=is_publish_only
        )
        
        if selected_writer == "Add New..." and not is_publish_only:
            new_writer = st.text_input(
                "New Writer Name",
                key=f"writing_new_input_{book_id}",
                placeholder="Enter new writer name..."
            )
            if new_writer:
                st.session_state[f"writing_by_{book_id}"] = new_writer
        elif selected_writer != "Select Writer" and not is_publish_only:
            st.session_state[f"writing_by_{book_id}"] = selected_writer

        writing_by = st.session_state[f"writing_by_{book_id}"] if st.session_state[f"writing_by_{book_id}"] != "Select Writer" else ""

        # Rest of the form
        with st.form(key=f"writing_form_{book_id}", border=False):
            col1, col2 = st.columns(2)
            with col1:
                writing_start_date = st.date_input(
                    "Start Date", 
                    value=current_data.get('writing_start'), 
                    key=f"writing_start_date_{book_id}",
                    disabled=is_publish_only
                )
                writing_start_time = st.time_input(
                    "Start Time", 
                    value=current_data.get('writing_start'), 
                    key=f"writing_start_time_{book_id}",
                    disabled=is_publish_only
                )
            with col2:
                writing_end_date = st.date_input(
                    "End Date", 
                    value=current_data.get('writing_end'), 
                    key=f"writing_end_date_{book_id}",
                    disabled=is_publish_only
                )
                writing_end_time = st.time_input(
                    "End Time", 
                    value=current_data.get('writing_end'), 
                    key=f"writing_end_time_{book_id}",
                    disabled=is_publish_only
                )
            
            book_pages = st.number_input(
                "Total Book Pages",
                min_value=0,
                value=current_data.get('book_pages', 0) if current_data.get('book_pages') is not None else 0,
                step=1,
                key=f"book_pages_writing_{book_id}",
                disabled=is_publish_only
            )

            if st.form_submit_button("💾 Save Writing", use_container_width=True, disabled=is_publish_only):
                with st.spinner("Saving Writing details..."):
                    time.sleep(2)
                    writing_start = f"{writing_start_date} {writing_start_time}" if writing_start_date and writing_start_time else None
                    writing_end = f"{writing_end_date} {writing_end_time}" if writing_end_date and writing_end_time else None
                    if writing_start and writing_end and writing_start > writing_end:
                        st.error("Start date/time must be before end date/time.")
                    else:
                        updates = {
                            "writing_start": writing_start,
                            "writing_end": writing_end,
                            "writing_by": writing_by if writing_by else None,
                            "book_pages": book_pages
                        }
                        update_operation_details(book_id, updates)
                        st.success("✔️ Updated Writing details")
                        if selected_writer == "Add New..." and writing_by:
                            st.cache_data.clear()

    # Proofreading Tab
    with tab2:
        # Worker selection outside the form
        proofreading_options = ["Select Proofreader"] + fetch_unique_names("proofreading_by") + ["Add New..."]
        selected_proofreader = st.selectbox(
            "Proofreader",
            proofreading_options,
            index=(proofreading_options.index(st.session_state[f"proofreading_by_{book_id}"]) 
                if st.session_state[f"proofreading_by_{book_id}"] in proofreading_options else 0),
            key=f"proofreading_select_{book_id}"
        )
        
        if selected_proofreader == "Add New...":
            new_proofreader = st.text_input(
                "New Proofreader Name",
                key=f"proofreading_new_input_{book_id}",
                placeholder="Enter new proofreader name..."
            )
            if new_proofreader:
                st.session_state[f"proofreading_by_{book_id}"] = new_proofreader
        elif selected_proofreader != "Select Proofreader":
            st.session_state[f"proofreading_by_{book_id}"] = selected_proofreader

        proofreading_by = st.session_state[f"proofreading_by_{book_id}"] if st.session_state[f"proofreading_by_{book_id}"] != "Select Proofreader" else ""

        # Rest of the form
        with st.form(key=f"proofreading_form_{book_id}", border=False):
            col1, col2 = st.columns(2)
            with col1:
                proofreading_start_date = st.date_input("Start Date", value=current_data.get('proofreading_start'), key=f"proofreading_start_date_{book_id}")
                proofreading_start_time = st.time_input("Start Time", value=current_data.get('proofreading_start'), key=f"proofreading_start_time_{book_id}")
            with col2:
                proofreading_end_date = st.date_input("End Date", value=current_data.get('proofreading_end'), key=f"proofreading_end_date_{book_id}")
                proofreading_end_time = st.time_input("End Time", value=current_data.get('proofreading_end'), key=f"proofreading_end_time_{book_id}")
            
            book_pages = st.number_input(
                "Total Book Pages",
                min_value=0,
                value=current_data.get('book_pages', 0) if current_data.get('book_pages') is not None else 0,
                step=1,
                key=f"book_pages_proofreading_{book_id}"
            )

            if st.form_submit_button("💾 Save Proofreading", use_container_width=True):
                with st.spinner("Saving Proofreading details..."):
                    time.sleep(2)
                    proofreading_start = f"{proofreading_start_date} {proofreading_start_time}" if proofreading_start_date and proofreading_start_time else None
                    proofreading_end = f"{proofreading_end_date} {proofreading_end_time}" if proofreading_end_date and proofreading_end_time else None
                    if proofreading_start and proofreading_end and proofreading_start > proofreading_end:
                        st.error("Start date/time must be before end date/time.")
                    else:
                        updates = {
                            "proofreading_start": proofreading_start,
                            "proofreading_end": proofreading_end,
                            "proofreading_by": proofreading_by if proofreading_by else None,
                            "book_pages": book_pages
                        }
                        update_operation_details(book_id, updates)
                        st.success("✔️ Updated Proofreading details")
                        if selected_proofreader == "Add New..." and proofreading_by:
                            st.cache_data.clear()

    # Formatting Tab
    with tab3:
        # Worker selection outside the form
        formatting_options = ["Select Formatter"] + fetch_unique_names("formatting_by") + ["Add New..."]
        selected_formatter = st.selectbox(
            "Formatter",
            formatting_options,
            index=(formatting_options.index(st.session_state[f"formatting_by_{book_id}"]) 
                if st.session_state[f"formatting_by_{book_id}"] in formatting_options else 0),
            key=f"formatting_select_{book_id}"
        )
        
        if selected_formatter == "Add New...":
            new_formatter = st.text_input(
                "New Formatter Name",
                key=f"formatting_new_input_{book_id}",
                placeholder="Enter new formatter name..."
            )
            if new_formatter:
                st.session_state[f"formatting_by_{book_id}"] = new_formatter
        elif selected_formatter != "Select Formatter":
            st.session_state[f"formatting_by_{book_id}"] = selected_formatter

        formatting_by = st.session_state[f"formatting_by_{book_id}"] if st.session_state[f"formatting_by_{book_id}"] != "Select Formatter" else ""

        # Rest of the form
        with st.form(key=f"formatting_form_{book_id}", border=False):
            col1, col2 = st.columns(2)
            with col1:
                formatting_start_date = st.date_input("Start Date", value=current_data.get('formatting_start'), key=f"formatting_start_date_{book_id}")
                formatting_start_time = st.time_input("Start Time", value=current_data.get('formatting_start'), key=f"formatting_start_time_{book_id}")
            with col2:
                formatting_end_date = st.date_input("End Date", value=current_data.get('formatting_end'), key=f"formatting_end_date_{book_id}")
                formatting_end_time = st.time_input("End Time", value=current_data.get('formatting_end'), key=f"formatting_end_time_{book_id}")
            
            book_pages = st.number_input(
                "Total Book Pages",
                min_value=0,
                value=current_data.get('book_pages', 0) if current_data.get('book_pages') is not None else 0,
                step=1,
                key=f"book_pages_formatting_{book_id}"
            )

            if st.form_submit_button("💾 Save Formatting", use_container_width=True):
                with st.spinner("Saving Formatting details..."):
                    time.sleep(2)
                    formatting_start = f"{formatting_start_date} {formatting_start_time}" if formatting_start_date and formatting_start_time else None
                    formatting_end = f"{formatting_end_date} {formatting_end_time}" if formatting_end_date and formatting_end_time else None
                    if formatting_start and formatting_end and formatting_start > formatting_end:
                        st.error("Start date/time must be before end date/time.")
                    else:
                        updates = {
                            "formatting_start": formatting_start,
                            "formatting_end": formatting_end,
                            "formatting_by": formatting_by if formatting_by else None,
                            "book_pages": book_pages
                        }
                        update_operation_details(book_id, updates)
                        st.success("✔️ Updated Formatting details")
                        if selected_formatter == "Add New..." and formatting_by:
                            st.cache_data.clear()

    # Book Cover Tab
    with tab4:
        # Worker selection outside the form
        cover_options = ["Select Cover Designer"] + fetch_unique_names("cover_by") + ["Add New..."]
        selected_cover = st.selectbox(
            "Cover Designer",
            cover_options,
            index=(cover_options.index(st.session_state[f"cover_by_{book_id}"]) 
                   if st.session_state[f"cover_by_{book_id}"] in cover_options else 0),
            key=f"cover_select_{book_id}"
        )
        
        if selected_cover == "Add New...":
            new_cover_designer = st.text_input(
                "New Cover Designer Name",
                key=f"cover_new_input_{book_id}",
                placeholder="Enter new cover designer name..."
            )
            if new_cover_designer:
                st.session_state[f"cover_by_{book_id}"] = new_cover_designer
        elif selected_cover != "Select Cover Designer":
            st.session_state[f"cover_by_{book_id}"] = selected_cover

        cover_by = st.session_state[f"cover_by_{book_id}"] if st.session_state[f"cover_by_{book_id}"] != "Select Cover Designer" else ""

        # Rest of the form
        with st.form(key=f"cover_form_{book_id}", border=False):
            st.subheader("Front Cover")
            col1, col2 = st.columns(2)
            with col1:
                front_cover_start_date = st.date_input("Front Start Date", value=current_data.get('front_cover_start'), key=f"front_cover_start_date_{book_id}")
                front_cover_start_time = st.time_input("Front Start Time", value=current_data.get('front_cover_start'), key=f"front_cover_start_time_{book_id}")
            with col2:
                front_cover_end_date = st.date_input("Front End Date", value=current_data.get('front_cover_end'), key=f"front_cover_end_date_{book_id}")
                front_cover_end_time = st.time_input("Front End Time", value=current_data.get('front_cover_end'), key=f"front_cover_end_time_{book_id}")

            st.subheader("Back Cover")
            col1, col2 = st.columns(2)
            with col1:
                back_cover_start_date = st.date_input("Back Start Date", value=current_data.get('back_cover_start'), key=f"back_cover_start_date_{book_id}")
                back_cover_start_time = st.time_input("Back Start Time", value=current_data.get('back_cover_start'), key=f"back_cover_start_time_{book_id}")
            with col2:
                back_cover_end_date = st.date_input("Back End Date", value=current_data.get('back_cover_end'), key=f"back_cover_end_date_{book_id}")
                back_cover_end_time = st.time_input("Back End Time", value=current_data.get('back_cover_end'), key=f"back_cover_end_time_{book_id}")

            if st.form_submit_button("💾 Save Cover Details", use_container_width=True):
                with st.spinner("Saving Cover details..."):
                    time.sleep(2)
                    front_cover_start = f"{front_cover_start_date} {front_cover_start_time}" if front_cover_start_date and front_cover_start_time else None
                    front_cover_end = f"{front_cover_end_date} {front_cover_end_time}" if front_cover_end_date and front_cover_end_time else None
                    back_cover_start = f"{back_cover_start_date} {back_cover_start_time}" if back_cover_start_date and back_cover_start_time else None
                    back_cover_end = f"{back_cover_end_date} {back_cover_end_time}" if back_cover_end_date and back_cover_end_time else None
                    
                    if front_cover_start and front_cover_end and front_cover_start > front_cover_end:
                        st.error("Front cover start date/time must be before end date/time.")
                    elif back_cover_start and back_cover_end and back_cover_start > back_cover_end:
                        st.error("Back cover start date/time must be before end date/time.")
                    else:
                        updates = {
                            "front_cover_start": front_cover_start,
                            "front_cover_end": front_cover_end,
                            "back_cover_start": back_cover_start,
                            "back_cover_end": back_cover_end,
                            "cover_by": cover_by if cover_by else None
                        }
                        update_operation_details(book_id, updates)
                        st.success("✔️ Updated Cover details")
                        if selected_cover == "Add New..." and cover_by:
                            st.cache_data.clear()

def update_operation_details(book_id, updates):
    """Update operation details in the books table."""
    set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
    query = f"UPDATE books SET {set_clause} WHERE book_id = :id"
    params = updates.copy()
    params["id"] = int(book_id)
    with conn.session as session:
        session.execute(text(query), params)
        session.commit()

###################################################################################################################################
##################################--------------- Edit Inventory Dialog ----------------------------##################################
###################################################################################################################################


@st.dialog("Edit Printing & Inventory", width='large')
def edit_inventory_delivery_dialog(book_id, conn):
    # Fetch book details for title
    book_details = fetch_book_details(book_id, conn)
    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        col1, col2 = st.columns([6,1])
        with col1:
            st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
        with col2:
            if st.button(":material/refresh: Refresh", key="refresh_inventory", type="tertiary"):
                st.cache_data.clear()
    else:
        st.markdown(f"### Inventory & Delivery for Book ID: {book_id}")
        st.warning("Book title not found.")

    # Fetch current inventory details
    query = f"""
        SELECT ready_to_print, print_status, amazon_link, flipkart_link, 
               google_link, agph_link, google_review, book_mrp
        FROM books WHERE book_id = {book_id}
    """
    book_data = conn.query(query, show_spinner=False)
    
    if book_data.empty:
        st.warning(f"No inventory details found for Book ID: {book_id}")
        current_data = {}
    else:
        current_data = book_data.iloc[0].to_dict()

    # Define tabs for Printing and Inventory
    tab1, tab2 = st.tabs(["📚 Printing", "📦 Inventory"])


    st.markdown("""
        <style>
        .print-run-table {
            font-size: 11px;
            border-radius: 5px;
            overflow-x: auto;
            margin-bottom: 8px;
        }

        .print-run-table-header,
        .print-run-table-row {
            display: grid;
            grid-template-columns: 0.5fr 1fr 1fr 0.6fr 1fr 0.8fr 0.7fr 0.7fr 0.7fr 0.8fr;
            padding: 4px 6px;
            align-items: center;
            box-sizing: border-box;
            min-width: 100%;
        }

        .print-run-table-header {
            background-color: #f1f3f5;
            font-weight: 600;
            font-size: 12px;
            color: #2c3e50;
            border-bottom: 1px solid #dcdcdc;
            border-radius: 5px 5px 0 0;
        }

        .print-run-table-row {
            border-bottom: 1px solid #e0e0e0;
            background-color: #fff;
        }

        .print-run-table-row:last-child {
            border-bottom: none;
        }

        .print-run-table-row:hover {
            background-color: #f9f9f9;
        }

        .status-received, .status-sent, .status-pending {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            text-align: center;
            font-size: 10px;
            color: #fff;
            min-width: 60px;
        }

        .status-received { background-color: #27ae60; }
        .status-sent { background-color: #e67e22; }
        .status-pending { background-color: #7f8c8d; }
                
        .inventory-summary {
            background-color: #e8f4f8;
            border: 1px solid #b3d4fc;
            border-radius: 5px;

            margin-bottom: 10px;
        }
        .inventory-summary-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        .inventory-summary-item {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            text-align: center;
            font-size: 14px;
            color: #2c3e50;
        }
        .inventory-summary-item strong {
            display: block;
            font-size: 16px;
            font-weight: bold;
        }
        .inventory-summary-item .icon {
            font-size: 24px;
            margin-bottom: 5px;
        }
        .value-green { color: #2ecc71; }
        .value-orange { color: #f39c12; }
        .value-red { color: #e74c3c; }
        </style>
    """, unsafe_allow_html=True)

    # Printing Tab
    with tab1:
        # Independent Checkbox with instant save
        def save_ready_to_print():
            updates = {"ready_to_print": st.session_state[f"ready_to_print_{book_id}"]}
            update_inventory_delivery_details(book_id, updates, conn)
            st.cache_data.clear()

        col1, _ = st.columns([1, 3])
        with col1:
            ready_to_print = st.checkbox(
                label="Ready to Print?",
                value=current_data.get('ready_to_print', False),
                key=f"ready_to_print_{book_id}",
                help="Check if the book is ready for printing.",
                on_change=save_ready_to_print
            )

        # Fetch print runs data (always shown, but edit/add only if ready_to_print is True)
        st.markdown('<div class="section-header">Print Runs</div>', unsafe_allow_html=True)
        print_runs_query = f"""
            SELECT id, print_sent_date, print_received_date, num_copies, print_by, 
                print_cost, print_type, binding, book_size
            FROM print_runs 
            WHERE book_id = {book_id}
            ORDER BY print_sent_date DESC
        """
        print_runs_data = conn.query(print_runs_query, show_spinner=False)

        # 1. Print Run Table Expander
        with st.expander("View Existing Print Runs", expanded=True):
            if not print_runs_data.empty:
                st.markdown('<div class="print-run-table">', unsafe_allow_html=True)
                st.markdown("""
                    <div class="print-run-table-header">
                        <div>ID</div>
                        <div>Sent Date</div>
                        <div>Received Date</div>
                        <div>Copies</div>
                        <div>Print By</div>
                        <div>Cost</div>
                        <div>Type</div>
                        <div>Binding</div>
                        <div>Size</div>
                        <div>Status</div>
                    </div>
                """, unsafe_allow_html=True)
                
                for idx, row in print_runs_data.iterrows():
                    status = ("Received" if row['print_received_date'] 
                            else "Sent" if row['print_sent_date'] 
                            else "Pending")
                    status_class = f"status-{status.lower()}"
                    
                    st.markdown(f"""
                        <div class="print-run-table-row">
                            <div>{row['id']}</div>
                            <div>{row['print_sent_date'] or 'N/A'}</div>
                            <div>{row['print_received_date'] or 'N/A'}</div>
                            <div>{int(row['num_copies'])}</div>
                            <div>{row['print_by'] or 'N/A'}</div>
                            <div>{row['print_cost'] or 'N/A'}</div>
                            <div>{row['print_type']}</div>
                            <div>{row['binding']}</div>
                            <div>{row['book_size']}</div>
                            <div><div class="{status_class}">{status.capitalize()}</div></div>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("No print runs found. Add a new print run below if ready.")

        # 2. Edit Existing Print Run Expander (only if ready_to_print and data exists)
        if ready_to_print and not print_runs_data.empty:
            with st.expander("Edit Existing Print Run", expanded=False):
                selected_print_run_id = st.selectbox(
                    "Select Print Run to Edit",
                    options=print_runs_data['id'].tolist(),
                    format_func=lambda x: f"ID {x} - Sent {print_runs_data[print_runs_data['id'] == x]['print_sent_date'].iloc[0]}",
                    key=f"select_print_run_{book_id}"
                )

                if selected_print_run_id:
                    edit_row = print_runs_data[print_runs_data['id'] == selected_print_run_id].iloc[0]
                    
                    with st.form(key=f"edit_form_{book_id}_{selected_print_run_id}", border=False):
                        edit_num_copies = st.number_input(
                            "Number of Copies",
                            min_value=0,
                            step=1,
                            value=int(edit_row['num_copies']),
                            key=f"edit_num_copies_{book_id}_{selected_print_run_id}"
                        )
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_print_sent_date = st.date_input(
                                "Print Sent Date",
                                value=edit_row['print_sent_date'],
                                key=f"edit_print_sent_date_{book_id}_{selected_print_run_id}"
                            )
                            edit_print_cost = st.text_input(
                                "Print Cost",
                                value=str(edit_row['print_cost'] or ""),
                                key=f"edit_print_cost_{book_id}_{selected_print_run_id}"
                            )
                        with col2:
                            edit_print_received_date = st.date_input(
                                "Print Received Date",
                                value=edit_row['print_received_date'],
                                key=f"edit_print_received_date_{book_id}_{selected_print_run_id}"
                            )
                            edit_print_by = st.text_input(
                                "Print By",
                                value=edit_row['print_by'] or "",
                                key=f"edit_print_by_{book_id}_{selected_print_run_id}"
                            )
                        print_col1, print_col2, print_col3 = st.columns(3)
                        with print_col1:
                            edit_print_type = st.selectbox(
                                "Print Type",
                                options=["B&W", "Color"],
                                index=["B&W", "Color"].index(edit_row['print_type']),
                                key=f"edit_print_type_{book_id}_{selected_print_run_id}"
                            )
                        with print_col2:
                            edit_binding = st.selectbox(
                                "Binding",
                                options=["Paperback", "Hardcover"],
                                index=["Paperback", "Hardcover"].index(edit_row['binding']),
                                key=f"edit_binding_{book_id}_{selected_print_run_id}"
                            )
                        with print_col3:
                            edit_book_size = st.selectbox(
                                "Book Size",
                                options=["6x9", "A4"],
                                index=["6x9", "A4"].index(edit_row['book_size']),
                                key=f"edit_book_size_{book_id}_{selected_print_run_id}"
                            )

                        save_edit = st.form_submit_button("💾 Save Edited Print Run", use_container_width=True)

                        if save_edit:
                            with st.spinner("Saving edited print run..."):
                                time.sleep(2)
                                try:
                                    with conn.session as session:
                                        # Update print_runs table
                                        session.execute(
                                            text("""
                                                UPDATE print_runs 
                                                SET print_sent_date = :print_sent_date, 
                                                    print_received_date = :print_received_date, 
                                                    num_copies = :num_copies, 
                                                    print_by = :print_by, 
                                                    print_cost = :print_cost, 
                                                    print_type = :print_type, 
                                                    binding = :binding, 
                                                    book_size = :book_size
                                                WHERE id = :id
                                            """),
                                            {
                                                "id": selected_print_run_id,
                                                "print_sent_date": edit_print_sent_date,
                                                "print_received_date": edit_print_received_date,
                                                "num_copies": edit_num_copies,
                                                "print_by": edit_print_by,
                                                "print_cost": float(edit_print_cost) if edit_print_cost else None,
                                                "print_type": edit_print_type,
                                                "binding": edit_binding,
                                                "book_size": edit_book_size
                                            }
                                        )
                                        
                                        # If print_received_date is set, update print_status in books table
                                        if edit_print_received_date is not None:
                                            session.execute(
                                                text("""
                                                    UPDATE books 
                                                    SET print_status = 1 
                                                    WHERE book_id = :book_id
                                                """),
                                                {"book_id": book_id}
                                            )
                                        
                                        session.commit()
                                    st.success("✔️ Updated Print Run")
                                    st.cache_data.clear()
                                except Exception as e:
                                    st.error(f"❌ Error saving print run: {str(e)}")

        # 3. Add New Print Run Expander (only if ready_to_print is True)
        if ready_to_print:
            with st.expander("Add New Print Run", expanded=False):
                with st.form(key=f"new_print_form_{book_id}", border=False):
                    new_num_copies = st.number_input(
                        label="Number of Copies",
                        min_value=0,
                        step=1,
                        value=0,
                        key=f"new_num_copies_{book_id}"
                    )
                    col1, col2 = st.columns(2)
                    with col1:
                        new_print_sent_date = st.date_input(
                            "Print Sent Date",
                            value=date.today(),
                            key=f"new_print_sent_date_{book_id}"
                        )
                        print_cost = st.text_input(
                            "Print Cost",
                            key=f"print_cost_{book_id}"
                        )
                    with col2:
                        new_print_received_date = st.date_input(
                            "Print Received Date",
                            value=None,
                            key=f"new_print_received_date_{book_id}"
                        )
                        print_by = st.text_input(
                            "Print By",
                            key=f"print_by_{book_id}"
                        )
                    print_col1, print_col2, print_col3 = st.columns(3)
                    with print_col1:
                        print_type = st.selectbox(
                            "Print Type",
                            options=["B&W", "Color"],
                            key=f"print_type_{book_id}"
                        )
                    with print_col2:
                        binding = st.selectbox(
                            "Binding",
                            options=["Paperback", "Hardcover"],
                            key=f"binding_{book_id}"
                        )
                    with print_col3:
                        book_size = st.selectbox(
                            "Book Size",
                            options=["6x9", "A4"],
                            key=f"book_size_{book_id}"
                        )

                    save_new_print = st.form_submit_button("💾 Save New Print Run", use_container_width=True)

                    if save_new_print:
                        with st.spinner("Saving new print run..."):
                            time.sleep(2)
                            try:
                                if st.session_state[f"new_num_copies_{book_id}"] > 0:
                                    with conn.session as session:
                                        # Insert into print_runs table
                                        session.execute(
                                            text("""
                                                INSERT INTO print_runs (book_id, print_sent_date, print_received_date, 
                                                    num_copies, print_by, print_cost, print_type, binding, book_size)
                                                VALUES (:book_id, :print_sent_date, :print_received_date, :num_copies, 
                                                    :print_by, :print_cost, :print_type, :binding, :book_size)
                                            """),
                                            {
                                                "book_id": book_id,
                                                "print_sent_date": st.session_state[f"new_print_sent_date_{book_id}"],
                                                "print_received_date": st.session_state[f"new_print_received_date_{book_id}"],
                                                "num_copies": st.session_state[f"new_num_copies_{book_id}"],
                                                "print_by": st.session_state[f"print_by_{book_id}"],
                                                "print_cost": (float(st.session_state[f"print_cost_{book_id}"]) 
                                                            if st.session_state[f"print_cost_{book_id}"] else None),
                                                "print_type": st.session_state[f"print_type_{book_id}"],
                                                "binding": st.session_state[f"binding_{book_id}"],
                                                "book_size": st.session_state[f"book_size_{book_id}"]
                                            }
                                        )
                                        
                                        # If print_received_date is set, update print_status in books table
                                        if st.session_state[f"new_print_received_date_{book_id}"] is not None:
                                            session.execute(
                                                text("""
                                                    UPDATE books 
                                                    SET print_status = 1 
                                                    WHERE book_id = :book_id
                                                """),
                                                {"book_id": book_id}
                                            )
                                        
                                        session.commit()
                                    st.success("✔️ Added New Print Run")
                                    st.cache_data.clear()
                                else:
                                    st.warning("Please enter a number of copies greater than 0.")
                            except Exception as e:
                                st.error(f"❌ Error saving new print run: {str(e)}") 

    # Inventory Tab
    with tab2:
        # Check if print_status is 1
        if not current_data.get('print_status', False):
            st.warning("Inventory details are only available after the book has been printed. Please set 'Printed?' to true in the Printing tab.")
        else:
            # Fetch existing print runs (for inventory calculation)
            print_runs_query = f"""
                SELECT print_date, num_copies 
                FROM print_runs 
                WHERE book_id = {book_id}
                ORDER BY print_date
            """
            print_runs_data = conn.query(print_runs_query,show_spinner = False)
            
            # Fetch existing inventory details (assuming you have an inventory table)
            inventory_query = f"""
                SELECT rack_number, amazon_sales, flipkart_sales, website_sales, direct_sales 
                FROM inventory 
                WHERE book_id = {book_id}
            """
            inventory_data = conn.query(inventory_query,show_spinner = False)
            
            inventory_current = inventory_data.iloc[0] if not inventory_data.empty else {
                'rack_number': '', 'amazon_sales': 0, 'flipkart_sales': 0, 'website_sales': 0, 'direct_sales': 0
            }

            # Calculate current inventory (convert to integers)
            total_copies_printed = int(print_runs_data['num_copies'].sum()) if not print_runs_data.empty else 0

            # Fetch copies sent to authors from book_authors table
            author_copies_query = f"""
                SELECT SUM(number_of_books) as total_author_copies
                FROM book_authors 
                WHERE book_id = {book_id}
            """
            author_copies_data = conn.query(author_copies_query,show_spinner = False)
            copies_sent_to_authors = int(author_copies_data.iloc[0]['total_author_copies'] or 0) if not author_copies_data.empty else 0

            total_sales = int(inventory_current.get('amazon_sales', 0) + 
                              inventory_current.get('flipkart_sales', 0) + 
                              inventory_current.get('website_sales', 0) + 
                              inventory_current.get('direct_sales', 0))
            current_inventory = int(total_copies_printed - total_sales - copies_sent_to_authors)

            # Determine color class for Current Inventory based on thresholds
            if current_inventory <= 10:  # Low inventory threshold
                inventory_color_class = "value-red"
            elif current_inventory <= 50:  # Warning threshold
                inventory_color_class = "value-orange"
            else:  # Healthy inventory
                inventory_color_class = "value-green"

            # Display current inventory status at the top (Improved Layout with Icons)
            st.markdown('<div class="section-header">Inventory Summary</div>', unsafe_allow_html=True)
            st.markdown(f"""
                <div class="inventory-summary-grid">
                    <div class="inventory-summary-item">
                        <div class="icon"></div>
                        <strong>{total_copies_printed}</strong>
                        Total Copies Printed
                    </div>
                    <div class="inventory-summary-item">
                        <div class="icon"></div>
                        <strong>{copies_sent_to_authors}</strong>
                        Copies Sent to Authors
                    </div>
                    <div class="inventory-summary-item">
                        <div class="icon"></div>
                        <strong>{total_sales}</strong>
                        Total Sales
                    </div>
                    <div class="inventory-summary-item">
                        <div class="icon"></div>
                        <strong class="{inventory_color_class}">{current_inventory}</strong>
                        Current Inventory
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            with st.form(key=f"new_inventory_form_{book_id}", border=False):
                # Pricing Section
                st.markdown('<div class="section-header">Pricing & Storage</div>', unsafe_allow_html=True)
                with st.container(border = True):
                    st.markdown('<div class="inventory-box">', unsafe_allow_html=True)
                    col1,col2 = st.columns(2)

                    with col1:
                        book_mrp = st.text_input(
                            "Book MRP", 
                            value=str(current_data.get('book_mrp', 0.0)) if current_data.get('book_mrp') is not None else "", 
                            key=f"book_mrp_{book_id}" 
                        )

                    with col2:
                        rack_number = st.text_input(
                        "Rack Number", 
                        value=inventory_current.get('rack_number', ''),
                        key=f"rack_number_{book_id}"
                    )
                    st.markdown('</div>', unsafe_allow_html=True)

                # Sales Tracking Section
                st.markdown('<div class="section-header">Sales Tracking</div>', unsafe_allow_html=True)
                with st.container(border = True):
                    st.markdown('<div class="inventory-box">', unsafe_allow_html=True)
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        amazon_sales = st.number_input(
                            "Amazon Sales", 
                            min_value=0,
                            value=int(inventory_current.get('amazon_sales', 0)),
                            key=f"amazon_sales_{book_id}"
                        )
                    with col2:
                        flipkart_sales = st.number_input(
                            "Flipkart Sales", 
                            min_value=0,
                            value=int(inventory_current.get('flipkart_sales', 0)),
                            key=f"flipkart_sales_{book_id}"
                        )
                    with col3:
                        website_sales = st.number_input(
                            "Website Sales", 
                            min_value=0,
                            value=int(inventory_current.get('website_sales', 0)),
                            key=f"website_sales_{book_id}"
                        )
                    with col4:
                        direct_sales = st.number_input(
                            "Direct Sales", 
                            min_value=0,
                            value=int(inventory_current.get('direct_sales', 0)),
                            key=f"direct_sales_{book_id}"
                        )
                    st.markdown('</div>', unsafe_allow_html=True)

                # Links and Reviews Section (Collapsible)
                st.markdown('<div class="section-header">Links and Reviews</div>', unsafe_allow_html=True)
                with st.expander("Links and Reviews", expanded=False):
                    st.markdown('<div class="inventory-box">', unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        amazon_link = st.text_input(
                            "Amazon Link", 
                            value=current_data.get('amazon_link', ""), 
                            key=f"amazon_link_{book_id}"
                        )
                        flipkart_link = st.text_input(
                            "Flipkart Link", 
                            value=current_data.get('flipkart_link', ""), 
                            key=f"flipkart_link_{book_id}"
                        )
                        google_link = st.text_input(
                            "Google Link", 
                            value=current_data.get('google_link', ""), 
                            key=f"google_link_{book_id}"
                        )
                    with col2:
                        agph_link = st.text_input(
                            "AGPH Link", 
                            value=current_data.get('agph_link', ""), 
                            key=f"agph_link_{book_id}"
                        )
                        google_review = st.text_input(
                            "Google Review", 
                            value=current_data.get('google_review', ""), 
                            key=f"google_review_{book_id}"
                        )
                    st.markdown('</div>', unsafe_allow_html=True)

                # Submit Button
                save_inventory = st.form_submit_button(
                    "💾 Save Inventory", 
                    use_container_width=True,
                    help="Click to save changes to inventory details."
                )

                # Handle form submission (moved inside the form context)
                if save_inventory:
                    with st.spinner("Saving Inventory details..."):
                        time.sleep(2)
                        try:
                            # Update books table for links, reviews, and MRP
                            book_updates = {
                                "book_mrp": float(st.session_state[f"book_mrp_{book_id}"]) if st.session_state[f"book_mrp_{book_id}"] else None,
                                "amazon_link": st.session_state[f"amazon_link_{book_id}"] if st.session_state[f"amazon_link_{book_id}"] else None,
                                "flipkart_link": st.session_state[f"flipkart_link_{book_id}"] if st.session_state[f"flipkart_link_{book_id}"] else None,
                                "google_link": st.session_state[f"google_link_{book_id}"] if st.session_state[f"google_link_{book_id}"] else None,
                                "agph_link": st.session_state[f"agph_link_{book_id}"] if st.session_state[f"agph_link_{book_id}"] else None,
                                "google_review": st.session_state[f"google_review_{book_id}"] if st.session_state[f"google_review_{book_id}"] else None
                            }
                            update_inventory_delivery_details(book_id, book_updates, conn)

                            # Update inventory details (using MariaDB/MySQL syntax)
                            inventory_updates = {
                                "book_id": book_id,
                                "rack_number": st.session_state[f"rack_number_{book_id}"] if st.session_state[f"rack_number_{book_id}"] else None,
                                "amazon_sales": st.session_state[f"amazon_sales_{book_id}"],
                                "flipkart_sales": st.session_state[f"flipkart_sales_{book_id}"],
                                "website_sales": st.session_state[f"website_sales_{book_id}"],
                                "direct_sales": st.session_state[f"direct_sales_{book_id}"]
                            }
                            with conn.session as session:
                                session.execute(
                                    text("""
                                        INSERT INTO inventory (book_id, rack_number, amazon_sales, flipkart_sales, website_sales, direct_sales)
                                        VALUES (:book_id, :rack_number, :amazon_sales, :flipkart_sales, :website_sales, :direct_sales)
                                        ON DUPLICATE KEY UPDATE 
                                            rack_number = VALUES(rack_number),
                                            amazon_sales = VALUES(amazon_sales),
                                            flipkart_sales = VALUES(flipkart_sales),
                                            website_sales = VALUES(website_sales),
                                            direct_sales = VALUES(direct_sales)
                                    """),
                                    inventory_updates
                                )
                                session.commit()
                            
                            st.success("✔️ Updated Inventory details!")
                            st.cache_data.clear()
                        except Exception as e:
                            st.error(f"❌ Error saving inventory details: {str(e)}")

def update_inventory_delivery_details(book_id, updates, conn):
    """Update inventory and delivery details in the books table."""
    try:
        set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
        query = f"UPDATE books SET {set_clause} WHERE book_id = :id"
        params = updates.copy()
        params["id"] = int(book_id)  # Ensure book_id is an integer
        with conn.session as session:
            session.execute(text(query), params)
            session.commit()
        st.cache_data.clear()
    except Exception as e:
        st.error(f"❌ Error updating books table: {str(e)}")
        raise



###################################################################################################################################
##################################--------------- Book Table ----------------------------##################################
###################################################################################################################################

# Group books by month (for display purposes only, not for pagination)
grouped_books = books.groupby(pd.Grouper(key='date', freq='ME'))

# Query to get author count per book
author_count_query = """
    SELECT book_id, COUNT(author_id) as author_count
    FROM book_authors
    GROUP BY book_id
"""
author_counts = conn.query(author_count_query,show_spinner = False)
# Convert to dictionary for easy lookup
author_count_dict = dict(zip(author_counts['book_id'], author_counts['author_count']))

# Custom CSS for modern table styling and pagination controls
st.markdown("""
    <style>
            
        /* Remove Streamlit's default top padding */
        .main > div {
            padding-top: 0px !important;
        }
        /* Ensure the first element has minimal spacing */
        .block-container {
            padding-top: 25px !important;  /* Small padding for breathing room */
        }

        .data-row {
            margin-bottom: 30px;
            border-bottom: 1px solid #e9ecef;
            font-size: 14px;
            color: #212529;
            transition: background-color 0.2s;
        }
        .month-header {
            font-size: 16px;
            font-weight: 500;
            color: #343a40;
            margin: 0px 0 8px 0;
        }
        .popover-button {
            background-color: #007bff;
            color: white;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 12px;
        }
            
        .month-header {
            font-size: 16px;
            font-weight: bold;
            color: #333;
            padding: 3px 10px;
            border-left: 3px solid #f54242; /* Blue side border */
            display: inline-block;
        }

        /* Pagination Styling */
        .pagination-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-top: 20px;
            gap: 10px;
        }
        .pagination-button {
            background-color: #007bff;
            color: white;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 14px;
            border: none;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .pagination-button:disabled {
            background-color: #d3d3d3;
            cursor: not-allowed;
        }
        .pagination-button:hover:not(:disabled) {
            background-color: #0056b3;
        }
        .pagination-info {
            font-size: 14px;
            color: #343a40;
        }
    </style>
""", unsafe_allow_html=True)

# Function to filter books based on search query
def filter_books(df, query):
    if not query or not query.strip():  # Handle empty or whitespace-only queries
        return df
    
    query = query.strip()  # Remove leading/trailing whitespace
    
    # Author search (starts with @)
    if query.startswith('@'):
        author_query = query[1:].lower()  # Remove @ and convert to lowercase
        # Query to get book_ids associated with the author
        author_book_ids_query = """
            SELECT DISTINCT ba.book_id
            FROM book_authors ba
            JOIN authors a ON ba.author_id = a.author_id
            WHERE LOWER(a.name) LIKE :author_query
        """
        # Fetch book IDs matching the author
        author_book_ids = conn.query(
            author_book_ids_query,
            params={"author_query": f"%{author_query}%"},
            show_spinner=False
        )
        # Filter the original DataFrame using these book IDs
        matching_book_ids = author_book_ids['book_id'].tolist()
        return df[df['book_id'].isin(matching_book_ids)]
    
    # Check if query is a number (for book_id)
    elif query.isdigit():
        query_len = len(query)
        if 1 <= query_len <= 4:  # Book ID (1-4 digits)
            return df[df['book_id'].astype(str) == query]
    
    # Check if query matches ISBN format (e.g., 978-81-970707-9-2)
    elif re.match(r'^\d{3}-\d{2}-\d{5,7}-\d{1,2}-\d$', query):
        # Compare directly with ISBN as stored (with hyphens)
        return df[df['isbn'].astype(str) == query]
    
    # Check if query matches date format (YYYY-MM-DD)
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', query):
        try:
            # Validate date by converting to datetime
            pd.to_datetime(query)
            return df[df['date'].astype(str) == query]
        except ValueError:
            # If date is invalid, return empty dataframe
            return df[df['book_id'].isna()]  # Returns empty df
    
    # Default case: search in title (partial match)
    else:
        query = query.lower()
        return df[df['title'].str.lower().str.contains(query, na=False)]

# Function to filter books based on day, month, year, and date range
def filter_books_by_date(df, day=None, month=None, year=None, start_date=None, end_date=None):
    filtered_df = df.copy()
    if day:
        filtered_df = filtered_df[filtered_df['date'].dt.day == day]
    if month:
        filtered_df = filtered_df[filtered_df['date'].dt.month == month]
    if year:
        filtered_df = filtered_df[filtered_df['date'].dt.year == year]
    if start_date:
        start_date = pd.Timestamp(start_date)
        filtered_df = filtered_df[filtered_df['date'] >= start_date]
    if end_date:
        end_date = pd.Timestamp(end_date)
        filtered_df = filtered_df[filtered_df['date'] <= end_date]
    return filtered_df

c1,c2 = st.columns([14,1], vertical_alignment="bottom")

with c1:
    st.markdown("## 📚 Book List")

with c2:
    if st.button(":material/refresh: Refresh", key="refresh_books", type="tertiary"):
        st.cache_data.clear()

# Search Functionality and Page Size Selection
srcol1, srcol2, srcol3, srcol4, srcol5 = st.columns([7, 4, 1.1, 1, 1], gap="small") 

with srcol1:
    search_query = st.text_input("🔎 Search Books", "", placeholder="Search by ID, title, ISBN, date, or @author...", key="search_bar",
                                 label_visibility="collapsed")
    filtered_books = filter_books(books, search_query)

# Add filtering popover next to the Add New Book button
with srcol2:
    with st.popover("Filter by Date, Status & Publisher", use_container_width=True):
        # Extract unique publishers and years from the dataset
        unique_publishers = sorted(books['publisher'].dropna().unique())
        unique_years = sorted(books['date'].dt.year.unique())

        # Use session state to manage filter values
        if 'year_filter' not in st.session_state:
            st.session_state.year_filter = None
        if 'month_filter' not in st.session_state:
            st.session_state.month_filter = None
        if 'start_date_filter' not in st.session_state:
            st.session_state.start_date_filter = None
        if 'end_date_filter' not in st.session_state:
            st.session_state.end_date_filter = None
        if 'status_filter' not in st.session_state:
            st.session_state.status_filter = None
        if 'publisher_filter' not in st.session_state:
            st.session_state.publisher_filter = None  # New filter for publisher
        if 'clear_filters_trigger' not in st.session_state:
            st.session_state.clear_filters_trigger = 0

        col1, col2 = st.columns([3, 1])
        with col1:
            st.write("Filter by Publisher:")

        with col2:
            # Clear filters button
            if st.button(":material/restart_alt: Reset", key="clear_filters", help="Clear all filters", use_container_width=True, type="tertiary"):
                st.session_state.year_filter = None
                st.session_state.month_filter = None
                st.session_state.start_date_filter = None
                st.session_state.end_date_filter = None
                st.session_state.status_filter = None
                st.session_state.publisher_filter = None  # Reset publisher filter
                st.session_state.clear_filters_trigger += 1
                st.rerun()

        # Publisher filter with pills
        publisher_options = unique_publishers
        selected_publisher = st.pills(
            "Publishers",
            options=publisher_options,
            key=f"publisher_pills_{st.session_state.clear_filters_trigger}",
            label_visibility='collapsed'
        )
        # Update session state for publisher filter
        if selected_publisher:
            st.session_state.publisher_filter = selected_publisher
        elif selected_publisher is None and "publisher_pills_callback" not in st.session_state:
            st.session_state.publisher_filter = None

        # Year filter
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write("Filter by Year:")

        with col2:
            pass  # Clear button is already above

        year_options = [str(year) for year in unique_years]
        selected_year = st.pills(
            "Years",
            options=year_options,
            key=f"year_pills_{st.session_state.clear_filters_trigger}",
            label_visibility='collapsed'
        )
        # Update session state only if a year is selected
        if selected_year:
            st.session_state.year_filter = int(selected_year)
        elif selected_year is None and "year_pills_callback" not in st.session_state:
            st.session_state.year_filter = None

        # Month filter with pills (only shown if a year is selected)
        if st.session_state.year_filter:
            year_books = books[books['date'].dt.year == st.session_state.year_filter]
            unique_months = sorted(year_books['date'].dt.month.unique())
            
            month_names = {
                1: "January", 2: "February", 3: "March", 4: "April", 
                5: "May", 6: "June", 7: "July", 8: "August", 
                9: "September", 10: "October", 11: "November", 12: "December"
            }
            
            st.write("Filter by Month:")
            month_options = [month_names[month] for month in unique_months]
            selected_month = st.pills(
                "Months",
                options=month_options,
                key=f"month_pills_{st.session_state.clear_filters_trigger}",
                label_visibility='collapsed'
            )
            # Convert selected month name back to number
            if selected_month:
                st.session_state.month_filter = next(
                    (num for num, name in month_names.items() if name == selected_month),
                    None
                )
            elif selected_month is None and "month_pills_callback" not in st.session_state:
                st.session_state.month_filter = None
        else:
            st.session_state.month_filter = None

        # Date range filter
        min_date = books['date'].min().date()
        max_date = books['date'].max().date()

        start_date_key = f"start_date_{st.session_state.clear_filters_trigger}"
        end_date_key = f"end_date_{st.session_state.clear_filters_trigger}"
        st.session_state.start_date_filter = st.date_input(
            "Start Date", 
            value=st.session_state.start_date_filter, 
            min_value=min_date, 
            max_value=max_date, 
            key=start_date_key
        )
        st.session_state.end_date_filter = st.date_input(
            "End Date", 
            value=st.session_state.end_date_filter, 
            min_value=min_date, 
            max_value=max_date, 
            key=end_date_key
        )

        # Validate date range
        if st.session_state.start_date_filter and st.session_state.end_date_filter:
            if st.session_state.start_date_filter > st.session_state.end_date_filter:
                st.error("Start Date must be before or equal to End Date.")
                st.session_state.start_date_filter = None
                st.session_state.end_date_filter = None

        # Status filter with pills (Delivered, On Going, Pending Payment, single selection)
        st.write("Filter by Status:")
        status_options = ["Delivered", "On Going", "Pending Payment"]
        selected_status = st.pills(
            "Status",
            options=status_options,
            key=f"status_pills_{st.session_state.clear_filters_trigger}",
            label_visibility='collapsed'
        )
        # Update status_filter based on selection (None if no selection)
        st.session_state.status_filter = selected_status

        # Apply filters
        applied_filters = []
        if st.session_state.publisher_filter:
            applied_filters.append(f"Publisher={st.session_state.publisher_filter}")
        if st.session_state.month_filter:
            applied_filters.append(f"Month={month_names.get(st.session_state.month_filter)}")
        if st.session_state.year_filter:
            applied_filters.append(f"Year={st.session_state.year_filter}")
        if st.session_state.start_date_filter:
            applied_filters.append(f"Start Date={st.session_state.start_date_filter}")
        if st.session_state.end_date_filter:
            applied_filters.append(f"End Date={st.session_state.end_date_filter}")
        if st.session_state.status_filter:
            applied_filters.append(f"Status={st.session_state.status_filter}")

        if applied_filters:
            # Apply publisher filter first
            if st.session_state.publisher_filter:
                filtered_books = filtered_books[filtered_books['publisher'] == st.session_state.publisher_filter]
            
            # Apply date filters
            filtered_books = filter_books_by_date(
                filtered_books, 
                None,  # No day filter
                st.session_state.month_filter, 
                st.session_state.year_filter, 
                st.session_state.start_date_filter, 
                st.session_state.end_date_filter
            )
            
            # Apply status filter
            if st.session_state.status_filter:
                if st.session_state.status_filter == "Pending Payment":
                    # Query to get book_ids with partial payments
                    pending_payment_query = """
                        SELECT DISTINCT book_id
                        FROM book_authors
                        WHERE total_amount > 0 
                        AND COALESCE(emi1, 0) + COALESCE(emi2, 0) + COALESCE(emi3, 0) < total_amount
                    """
                    pending_book_ids = conn.query(pending_payment_query, show_spinner=False)
                    matching_book_ids = pending_book_ids['book_id'].tolist()
                    filtered_books = filtered_books[filtered_books['book_id'].isin(matching_book_ids)]
                else:
                    # Existing status filter for Delivered and On Going
                    status_mapping = {"Delivered": 1, "On Going": 0}
                    selected_status_value = status_mapping[st.session_state.status_filter]
                    filtered_books = filtered_books[filtered_books['deliver'] == selected_status_value]
            st.success(f"Filter {', '.join(applied_filters)}")


# Add page size selection
with srcol5:
    page_size_options = [40, 100, "All"]
    if 'page_size' not in st.session_state:
        st.session_state.page_size = page_size_options[0]  # Default page size
    st.session_state.page_size = st.selectbox("Books per page", options=page_size_options, index=0, key="page_size_select",
                                              label_visibility="collapsed")

# Add New Book button
with srcol3:
    if st.button(":material/add: Book", type="secondary", help="Add New Book", use_container_width=True):
        add_book_dialog(conn)

with srcol4:
    with st.popover("More", use_container_width=True, help = "More Options"):
        if st.button("Edit Authors", key="edit_author_btn", type ="tertiary", icon = "✏️"):
            edit_author_detail(conn)
    

# Pagination Logic (Modified)
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

# Apply sorting to the filtered books (sort by date in descending order)
filtered_books = filtered_books.sort_values(by='date', ascending=False)

# Determine if pagination should be enabled
# Pagination is enabled only if page_size is "All" and no search/filter is applied
pagination_enabled = st.session_state.page_size == "All" and not (
    search_query or any([
        st.session_state.month_filter,
        st.session_state.year_filter,
        st.session_state.start_date_filter,
        st.session_state.end_date_filter
    ])
)

# Apply pagination or limit the number of books based on page size
if pagination_enabled:
    # Pagination is enabled: Show all books with pagination
    page_size = 40  # Default page size for pagination when "All" is selected
    total_books = len(filtered_books)
    total_pages = max(1, (total_books + page_size - 1) // page_size)
    st.session_state.current_page = min(st.session_state.current_page, total_pages)  # Ensure current page is valid
    start_idx = (st.session_state.current_page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_books = filtered_books.iloc[start_idx:end_idx]
else:
    # Pagination is disabled: Show only the top N books based on page_size
    if st.session_state.page_size == "All":
        paginated_books = filtered_books
    else:
        page_size = st.session_state.page_size
        paginated_books = filtered_books.head(page_size)


# :material/done: (Simple check mark)
# :material/task_alt: (Check mark in a circle, modern)
# :material/verified: (Verified badge with check)
# :material/check_box: (Checked box)
# :material/thumb_up: (Thumbs up)
# :material/star: (Star, for excellence)
# :material/flag: (Flag, for reaching a goal)

# :material/hourglass_empty: (Empty hourglass)
# :material/pending: (Dots indicating waiting)
# :material/aut renew: (Circular arrows, for "in progress")
# :material/schedule: (Clock, for "time-based")
# :material/build: (Wrench, for "under construction")
# :material/sync: (Sync arrows)
# :material/more_time: (Clock with plus sign)

# price_icon = "✔️"
# isbn_icon = "⏳"
# author_icon = "❌"
# ops_icon = "✔️"
# delivery_icon = "⏳"

#actual icons
price_icon = ":material/currency_rupee:"
isbn_icon = ":material/edit_document:"
author_icon = ":material/manage_accounts:"
ops_icon = ":material/manufacturing:"
delivery_icon = ":material/local_shipping:"


# price_icon = ":material/check_circle:"
# isbn_icon = ":material/hourglass_top:"
# author_icon = ":material/cancel:"
# ops_icon = ":material/check_circle:"
# delivery_icon = ":material/hourglass_top:"

# Display the table
column_size = [0.5, 4, 1, 1, 1, 2]

cont = st.container(border=False)
with cont:
    if paginated_books.empty:
        st.warning("No books available.")
    else:
        if search_query:
            st.warning(f"Showing {len(paginated_books)} results for '{search_query}'")

        # Group and sort paginated books by month (for display purposes only)
        grouped_books = paginated_books.groupby(pd.Grouper(key='date', freq='ME'))
        reversed_grouped_books = reversed(list(grouped_books))

        # Table Body
        for month, monthly_books in reversed_grouped_books:
            monthly_books = monthly_books.sort_values(by='date', ascending=False)
            num_books = len(monthly_books)
            st.markdown(f'<div class="month-header">{month.strftime("%B %Y")} ({num_books} books)</div>', unsafe_allow_html=True)
            
            for _, row in monthly_books.iterrows():
                st.markdown('<div class="data-row">', unsafe_allow_html=True)
                col1, col2, col3, col4, col5, col6 = st.columns(column_size)
                with col1:
                    st.write(row['book_id'])
                with col2:
                    author_count = author_count_dict.get(row['book_id'], 0)
                    badge_content = ""
                    badge_style = ""
                    publish_badge = ""
                    publisher_badge = ""
                    
                    # Handle the author count/single badge
                    if row['is_single_author'] == 1:
                        badge_content = "Single"
                        badge_style = "color: #2aba25; font-size: 12px; background-color: #f7f7f7; padding: 2px 6px; border-radius: 12px;"
                    else:
                        badge_content = str(author_count)
                        badge_style = "color: #2aba25; font-size: 14px; background-color: #f7f7f7; padding: 1px 4px; border-radius: 10px;"
                    
                    # Handle the "Publish Only" badge
                    if row['is_publish_only'] == 1:
                        publish_badge = '<span style="color: #ff9800; font-size: 12px; background-color: #fff3e0; padding: 2px 6px; border-radius: 12px; margin-left: 5px;">Publish Only</span>'
                    
                    # Handle the publisher badge with distinct colors
                    publisher = row.get('publisher', '')  # Safe access
                    publisher_colors = {
                        "Cipher": {"color": "#ffffff", "background": "#673ab7"},  # White text on deep purple
                        "AG Classics": {"color": "#ffffff", "background": "#d81b60"},  # White text on magenta
                        "AG Kids": {"color": "#ffffff", "background": "#f57c00"},  # White text on light blue
                        "NEET/JEE": {"color": "#ffffff", "background": "#0288d1"}  # White text on orange
                    }
                    if publisher in publisher_colors:
                        style = publisher_colors[publisher]
                        publisher_style = f"color: {style['color']}; font-size: 12px; background-color: {style['background']}; padding: 2px 6px; border-radius: 12px; margin-left: 5px;"
                        publisher_badge = f'<span style="{publisher_style}">{publisher}</span>'
                    
                    # Display the title with all badges
                    st.markdown(
                        f"{row['title']} <span style='{badge_style}'>{badge_content}</span>{publish_badge}{publisher_badge}",
                        unsafe_allow_html=True
                    )
                with col3:
                    st.write(row['date'].strftime('%Y-%m-%d'))
                with col4:
                    st.markdown(get_isbn_display(row["isbn"], row["apply_isbn"]), unsafe_allow_html=True)
                with col5:
                    st.markdown(get_status_pill(row["deliver"]), unsafe_allow_html=True)
                with col6:
                    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns([1, 1, 1, 1, 1])
                    with btn_col1:
                        if st.button(isbn_icon, key=f"isbn_{row['book_id']}", help="Edit Book Title & ISBN"):
                            manage_isbn_dialog(conn, row['book_id'], row['apply_isbn'], row['isbn'])
                    with btn_col2:
                        publisher = row.get('publisher', '')
                        if publisher not in ["AG Kids", "NEET/JEE"]:
                            if st.button(price_icon, key=f"price_btn_{row['book_id']}", help="Edit Price"):
                                manage_price_dialog(row['book_id'], row['price'], conn)
                        else:
                            st.button(price_icon, key=f"price_btn_{row['book_id']}", help="Price management disabled for this publisher", disabled=True)
                    with btn_col3:
                        publisher = row.get('publisher', '')
                        if publisher not in ["AG Kids", "NEET/JEE"]:
                            if st.button(author_icon, key=f"edit_author_{row['book_id']}", help="Edit Authors"):
                                edit_author_dialog(row['book_id'], conn)
                        else:
                            st.button(author_icon, key=f"edit_author_{row['book_id']}", help="Author editing disabled for this publisher", disabled=True)
                    with btn_col4:
                        if st.button(ops_icon, key=f"ops_{row['book_id']}", help="Edit Operations"):
                            edit_operation_dialog(row['book_id'], conn)
                    with btn_col5:
                        if st.button(delivery_icon, key=f"delivery_{row['book_id']}", help="Edit Delivery"):
                            edit_inventory_delivery_dialog(row['book_id'], conn)
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


        # Pagination Controls (only show if pagination is enabled)
        if pagination_enabled:
            total_books = len(filtered_books)
            total_pages = max(1, (total_books + page_size - 1) // page_size)
            current_page = st.session_state.current_page

            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            with col1:
                st.markdown('<div class="pagination-container">', unsafe_allow_html=True)
                prev_disabled = current_page == 1
                next_disabled = current_page == total_pages
            with col2:
                # Previous Button
                if st.button("Previous", key="prev_page", disabled=prev_disabled, help="Go to previous page"):
                    st.session_state.current_page -= 1
                    st.rerun()
            with col3:
                # Page Info
                st.markdown(f'<span class="pagination-info">Page {current_page} of {total_pages}</span>', unsafe_allow_html=True)
            with col4:
                # Next Button
                if st.button("Next", key="next_page", disabled=next_disabled, help="Go to next page"):
                    st.session_state.current_page += 1
                    st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)

        # # Add informational message if pagination is disabled due to specific page size
        # if not pagination_enabled and st.session_state.page_size != "All":
        #     st.info(f"Showing the {st.session_state.page_size} most recent books. Pagination is disabled. To view all books with pagination, select 'All' in the 'Books per page' dropdown.")



