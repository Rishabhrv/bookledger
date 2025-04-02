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
        with st.spinner("Connecting to MySQL..."):
            conn = st.connection('mysql', type='sql')
        return conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

# Connect to MySQL
conn = connect_db()

# Fetch books from the database
query = "SELECT book_id, title, date, isbn, apply_isbn, deliver, price, is_single_author FROM books"
books = conn.query(query,show_spinner = False)

# Function to fetch book details (title, is_single_author, num_copies, print_status)
def fetch_book_details(book_id, conn):
    query = f"""
    SELECT title, date, apply_isbn, isbn, is_single_author, num_copies, print_status
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
    def book_details_section():
        with st.container(border=True):
            st.markdown("<h5 style='color: #4CAF50;'>Book Details</h5>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            book_title = col1.text_input("Book Title", placeholder="Enter Book Title..", key="book_title")
            book_date = col2.date_input("Date", value=date.today(), key="book_date")
            
            # Add the "Single Author" toggle (default is off, meaning multiple authors allowed)
            is_single_author = st.toggle("Single Author Book?", value=False, key="single_author_toggle",
                                         help="Enable this to restrict the book to a single author.")
            
            return {
                "title": book_title,
                "date": book_date,
                "is_single_author": is_single_author  # Add this to book_data
            }

    def author_details_section(conn, is_single_author):
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
        agent_options = ["Select Agent"] + unique_agents + ["Add New..."]
        consultant_options = ["Select Consultant"] + unique_consultants + ["Add New..."]

        with st.container(border=True):
            st.markdown("<h5 style='color: #4CAF50;'>Author Details</h5>", unsafe_allow_html=True)
            
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

    def insert_author(conn, name, email, phone):
        with conn.session as s:
            s.execute(text("""
                INSERT INTO authors (name, email, phone)
                VALUES (:name, :email, :phone)
                ON DUPLICATE KEY UPDATE name=name
            """), params={"name": name, "email": email, "phone": phone})
            s.commit()
            return s.execute(text("SELECT LAST_INSERT_ID();")).scalar()

    def is_author_active(author):
        """Check if an author is 'active' (i.e., has at least one non-empty field)."""
        return bool(author["name"] or author["email"] or author["phone"] or author["corresponding_agent"] or author["publishing_consultant"])

    def validate_form(book_data, author_data, is_single_author):
        """Validate that all required fields are filled for book and active authors, and positions are unique."""
        errors = []

        # Validate book details
        if not book_data["title"]:
            errors.append("Book title is required.")
        if not book_data["date"]:
            errors.append("Book date is required.")

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
        book_data = book_details_section()
        st.markdown(" ")
        author_data = author_details_section(conn, book_data["is_single_author"])

    # --- Save, Clear, and Cancel Buttons ---
    col1, col2 = st.columns([7,1])
    with col1:
        if st.button("Save", key="dialog_save", type="primary"):
            errors = validate_form(book_data, author_data, book_data["is_single_author"])
            if errors:
                st.error("\n".join(errors), icon="🚨")
            else:
                with conn.session as s:
                    try:
                        # Insert book (include is_single_author)
                        s.execute(text("""
                            INSERT INTO books (title, date, is_single_author)
                            VALUES (:title, :date, :is_single_author)
                        """), params={"title": book_data["title"], "date": book_data["date"], "is_single_author": book_data["is_single_author"]})
                        book_id = s.execute(text("SELECT LAST_INSERT_ID();")).scalar()

                        # Process only active authors
                        active_authors = [a for a in author_data if is_author_active(a)]
                        for author in active_authors:
                            if author["author_id"]:
                                # Use existing author
                                author_id_to_link = author["author_id"]
                            else:
                                # Insert new author
                                author_id_to_link = insert_author(conn, author["name"], author["email"], author["phone"])

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
                        st.success("Book and Authors Saved Successfully!", icon="✅")
                        time.sleep(1)  # Give user time to see the success message
                        st.session_state.authors = [
                            {"name": "", "email": "", "phone": "", "author_id": None, "author_position": f"{i+1}{'st' if i == 0 else 'nd' if i == 1 else 'rd' if i == 2 else 'th'}", "corresponding_agent": "", "publishing_consultant": ""}
                            for i in range(4)
                        ]  # Reset authors
                        st.rerun()  # Close the dialog by rerunning the app
                    except Exception as db_error:
                        s.rollback()
                        st.error(f"Database error during save: {db_error}", icon="❌")

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
    # Fetch current book details (title and date) from the database
    book_details = fetch_book_details(book_id, conn)
    if book_details.empty:
        st.error("❌ Book not found in database.")
        return
    
    # Extract current title and date from the DataFrame
    current_title = book_details.iloc[0]['title']
    current_date = book_details.iloc[0]['date']

    # Main container
    with st.container():
        # Header with Book ID
        #st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {current_title}</h3>", unsafe_allow_html=True)
        st.markdown(f"### {book_id} - {current_title}", unsafe_allow_html=True)

        st.markdown("<h5 style='color: #4CAF50;'>Book Details</h5>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            col1, col2 = st.columns([3,1])
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
            with conn.session as s:
                if apply_isbn and receive_isbn and new_isbn:
                    s.execute(
                        text("""
                            UPDATE books 
                            SET apply_isbn = :apply_isbn, 
                                isbn = :isbn, 
                                isbn_receive_date = :isbn_receive_date, 
                                title = :title, 
                                date = :date 
                            WHERE book_id = :book_id
                        """),
                        {
                            "apply_isbn": 1, 
                            "isbn": new_isbn, 
                            "isbn_receive_date": isbn_receive_date, 
                            "title": new_title, 
                            "date": new_date, 
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
                                date = :date 
                            WHERE book_id = :book_id
                        """),
                        {
                            "apply_isbn": 1, 
                            "title": new_title, 
                            "date": new_date, 
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
                                date = :date 
                            WHERE book_id = :book_id
                        """),
                        {
                            "apply_isbn": 0, 
                            "title": new_title, 
                            "date": new_date, 
                            "book_id": book_id
                        }
                    )
                s.commit()
            st.success("Book Details Updated Successfully")
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
                    st.success("Book Price Updated Successfully")
                    st.rerun()
                except ValueError:
                    st.error("Please enter a valid whole number")

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
                            st.success(f"Payment updated for {row['name']}")
                            st.cache_data.clear()
                            st.rerun()


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
        # Use session state to track whether this author's expander is open
        expander_key = f"expander_{author_id}"
        if expander_key not in st.session_state.expander_states:
            st.session_state.expander_states[expander_key] = False  # Default to collapsed

        # Wrap each author in an expander, preserving its state
        with st.expander(f"📖 {row['name']} (Author ID: {author_id})", expanded=st.session_state.expander_states[expander_key]):
            # Callback to update expander state when it's toggled
            def update_expander_state():
                st.session_state.expander_states[expander_key] = not st.session_state.expander_states[expander_key]

            # This button is optional; you can use it to manually toggle if needed
            # st.button("Toggle", on_click=update_expander_state, key=f"toggle_{author_id}")

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
                                "✅ Welcome Mail Sent",
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
                                "✅ Agreement Received",
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

                    # Submit button
                    if st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary"):
                        # Convert boolean values to integers for database
                        for key in updates:
                            if isinstance(updates[key], bool):
                                updates[key] = int(updates[key])

                        try:
                            with st.spinner("Saving changes..."):
                                update_book_authors(row['id'], updates, conn)
                                st.cache_data.clear()
                                st.success(f"✅ Updated details for {row['name']} (Author ID: {row['author_id']})")
                        except Exception as e:
                            st.error(f"❌ Error updating author details: {e}")
    

    # Fetch existing authors for this book
    book_authors = fetch_book_authors(book_id, conn)
    existing_author_count = len(book_authors)
    # Determine if toggle should be editable
    toggle_editable = existing_author_count <= 1  # Editable only if 0 or 1 author


    if existing_author_count == 1:
        # Add toggle for single/multiple authors
        toggle_col1, toggle_col2 = st.columns([3, 4])
        with toggle_col1:
            new_is_single_author = st.toggle(
                "Single Author?",
                value=is_single_author,
                key=f"single_author_toggle_{book_id}",
                help="Toggle between single and multiple authors",
                disabled=not toggle_editable  # Disable if more than 1 author
            )

    # If toggle state changes and is editable, update the database
        if toggle_editable and new_is_single_author != is_single_author:
            try:
                with st.spinner("Updating author mode..."):
                    with conn.session as s:  # Use session context
                        s.execute(
                            text("UPDATE books SET is_single_author = :is_single_author WHERE book_id = :book_id"),
                            {"is_single_author": int(new_is_single_author), "book_id": book_id}
                        )
                        s.commit()
                    st.success(f"✅ Updated to {'Single' if new_is_single_author else 'Multiple'} Author mode")
                    st.cache_data.clear()
                    is_single_author = new_is_single_author  # Update local variable
            except Exception as e:
                st.error(f"❌ Error updating author mode: {e}")


    available_slots = MAX_AUTHORS - existing_author_count

    # If is_single_author is True and there is already one author, prevent adding more
    if is_single_author and existing_author_count >= 1:
        st.warning("⚠️ This book is marked as 'Single Author'. No additional authors can be added.")
        if st.button("Close"):
            st.rerun()
        return

    # If the maximum number of authors is already reached (regardless of is_single_author)
    if existing_author_count >= MAX_AUTHORS:
        st.warning("⚠️ This book already has the maximum number of authors (4). No more authors can be added.")
        if st.button("Close"):
            st.rerun()
        return

    if existing_author_count == 0:
        st.warning(f"⚠️ No authors found for Book ID: {book_id}")

    # Helper function to ensure backward compatibility
    def ensure_author_fields(author):
        """Ensure all required fields are present in the author dict."""
        default_author = {
            "name": "",
            "email": "",
            "phone": "",
            "author_id": None,
            "author_position": None,
            "corresponding_agent": "",
            "publishing_consultant": ""
        }
        for key, default_value in default_author.items():
            if key not in author:
                author[key] = default_value
        return author

    # Initialize or reinitialize session state for new authors
    def initialize_new_authors(slots):
        """Initialize or reinitialize st.session_state.new_authors with the correct number of slots."""
        return [
            {"name": "", "email": "", "phone": "", "author_id": None, "author_position": None, "corresponding_agent": "", "publishing_consultant": ""}
            for _ in range(slots)
        ]

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

    # Get existing positions and author IDs to prevent duplicates
    existing_positions = [author["author_position"] for _, author in book_authors.iterrows()]
    existing_author_ids = [author["author_id"] for _, author in book_authors.iterrows()]

    # Author selection and form
    st.markdown(f"### Add Up to {available_slots} New Authors")
    all_authors = get_all_authors(conn)
    author_options = ["Add New Author"] + [f"{a.name} (ID: {a.author_id})" for a in all_authors]
    unique_agents, unique_consultants = get_unique_agents_and_consultants(conn)
    agent_options = ["Select Agent"] + unique_agents + ["Add New..."]
    consultant_options = ["Select Consultant"] + unique_consultants + ["Add New..."]

    # Render expanders
    for i in range(available_slots):
        with st.expander(f"New Author {i+1}", expanded=False):
            with st.container(border=False):
                #st.markdown(f"<h5 style='color: #4CAF50;'>New Author {i+1}</h5>", unsafe_allow_html=True)
                st.markdown(f"#### New Author {i+1}", unsafe_allow_html=True)

                # If is_single_author is True, disable all inputs if an author already exists
                disabled = is_single_author and existing_author_count >= 1
                if disabled and i == 0:
                    st.warning("⚠️ This section is disabled because the book is marked as 'Single Author' and already has one author.")

                # Author selection or new author
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
                        st.session_state.new_authors[i]["name"] = selected_author_details.name
                        st.session_state.new_authors[i]["email"] = selected_author_details.email
                        st.session_state.new_authors[i]["phone"] = selected_author_details.phone
                        st.session_state.new_authors[i]["author_id"] = selected_author_details.author_id
                elif selected_author == "Add New Author" and not disabled:
                    st.session_state.new_authors[i]["author_id"] = None

                col1, col2 = st.columns(2)
                st.session_state.new_authors[i]["name"] = col1.text_input(
                    f"Author Name {i+1}", st.session_state.new_authors[i]["name"], key=f"new_name_{i}",
                    placeholder="Enter author name..", help="Enter the full name of the author.", disabled=disabled
                )
                # Dynamically update available positions for this author
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

    return st.session_state.new_authors

    # Single button to save all new authors
    col1, col2 = st.columns([7, 1])
    with col1:
        if st.button("Add Authors to Book", key="add_authors_to_book", type="primary"):
            errors = []
            # Only consider authors that are complete (all required fields filled)
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
                            if is_author_complete(author):  # Double-check completeness
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
                        st.success("✅ New authors added successfully!")
                        del st.session_state.new_authors  # Reset state
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error adding authors: {e}")

    with col2:
        if st.button("Cancel", key="cancel_add_authors", type="secondary"):
            del st.session_state.new_authors  # Reset state
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
    # Fetch book details for title
    book_details = fetch_book_details(book_id, conn)
    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        col1, col2 = st.columns([6, 1])
        with col1:
            st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
            #st.markdown(f"### {book_id} : {book_title}")
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
               front_cover_start, front_cover_end, front_cover_by,
               back_cover_start, back_cover_end, back_cover_by, book_pages
        FROM books WHERE book_id = {book_id}
    """
    book_operations = conn.query(query,show_spinner = False)
    
    if book_operations.empty:
        st.warning(f"No operation details found for Book ID: {book_id}")
        current_data = {}
    else:
        current_data = book_operations.iloc[0].to_dict()

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
            
            # Determine status
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
            
            # Streamlit-integrated status display
            html = f"""
                <div class="status-box {status_class}">
                    <strong>{op_name}</strong><br>
                    {status_text}
                </div>
            """
            st.markdown(html, unsafe_allow_html=True)

    # Your existing tab code would follow here...

   # Fetch unique names for each role
    writing_names = fetch_unique_names("writing_by")
    proofreading_names = fetch_unique_names("proofreading_by")
    formatting_names = fetch_unique_names("formatting_by")
    front_cover_names = fetch_unique_names("front_cover_by")
    back_cover_names = fetch_unique_names("back_cover_by")

    # Sort the lists and ensure no empty entries
    writing_names = sorted([name for name in writing_names if name])
    proofreading_names = sorted([name for name in proofreading_names if name])
    formatting_names = sorted([name for name in formatting_names if name])
    front_cover_names = sorted([name for name in front_cover_names if name])
    back_cover_names = sorted([name for name in back_cover_names if name])

    # Initialize session state for text inputs
    if f"writing_by_{book_id}" not in st.session_state:
        st.session_state[f"writing_by_{book_id}"] = current_data.get('writing_by', "")
    if f"proofreading_by_{book_id}" not in st.session_state:
        st.session_state[f"proofreading_by_{book_id}"] = current_data.get('proofreading_by', "")
    if f"formatting_by_{book_id}" not in st.session_state:
        st.session_state[f"formatting_by_{book_id}"] = current_data.get('formatting_by', "")
    if f"front_cover_by_{book_id}" not in st.session_state:
        st.session_state[f"front_cover_by_{book_id}"] = current_data.get('front_cover_by', "")
    if f"back_cover_by_{book_id}" not in st.session_state:
        st.session_state[f"back_cover_by_{book_id}"] = current_data.get('back_cover_by', "")

    # Define options for selectboxes
    writing_options = ["Select Writer"] + writing_names + ["Add New..."]
    proofreading_options = ["Select Proofreader"] + proofreading_names + ["Add New..."]
    formatting_options = ["Select Formatter"] + formatting_names + ["Add New..."]
    front_cover_options = ["Select Front Cover Designer"] + front_cover_names + ["Add New..."]
    back_cover_options = ["Select Back Cover Designer"] + back_cover_names + ["Add New..."]

    # Define tabs for each operation
    tab1, tab2, tab3, tab4 = st.tabs(["✍️ Writing", "🔍 Proofreading", "📏 Formatting", "🎨 Book Cover"])

    # Writing Tab
    with tab1:
        with st.form(key=f"writing_form_{book_id}", border=False):
            selected_writer = st.selectbox(
                "Writer",
                writing_options,
                index=writing_options.index(st.session_state[f"writing_by_{book_id}"]) if st.session_state[f"writing_by_{book_id}"] in writing_names else 0,
                key=f"writing_select_{book_id}",
                help="Select an existing writer or 'Add New...' to enter a new one."
            )
            if selected_writer == "Add New...":
                st.session_state[f"writing_by_{book_id}"] = st.text_input(
                    "New Writer Name",
                    value="",
                    key=f"writing_new_input_{book_id}",
                    placeholder="Enter new writer name..."
                )
            elif selected_writer != "Select Writer":
                st.session_state[f"writing_by_{book_id}"] = selected_writer

            writing_by = st.text_input(
                "Writing By",
                value=st.session_state[f"writing_by_{book_id}"],
                key=f"writing_by_input_{book_id}"
            )
            col1, col2 = st.columns(2)
            with col1:
                writing_start_date = st.date_input("Start Date", value=current_data.get('writing_start', None), key=f"writing_start_date_{book_id}")
                writing_start_time = st.time_input("Start Time", value=current_data.get('writing_start', None), key=f"writing_start_time_{book_id}")
            with col2:
                writing_end_date = st.date_input("End Date", value=current_data.get('writing_end', None), key=f"writing_end_date_{book_id}")
                writing_end_time = st.time_input("End Time", value=current_data.get('writing_end', None), key=f"writing_end_time_{book_id}")
            if st.form_submit_button("💾 Save Writing", use_container_width=True):
                writing_start = f"{writing_start_date} {writing_start_time}" if writing_start_date and writing_start_time else None
                writing_end = f"{writing_end_date} {writing_end_time}" if writing_end_date and writing_end_time else None
                if writing_start and writing_end and writing_start > writing_end:
                    st.error("Start date/time must be before end date/time.")
                else:
                    updates = {
                        "writing_start": writing_start,
                        "writing_end": writing_end,
                        "writing_by": writing_by if writing_by else None
                    }
                    update_operation_details(book_id, updates)
                    st.session_state[f"writing_by_{book_id}"] = writing_by
                    st.success("✅ Updated Writing details")

    # Proofreading Tab
    with tab2:
        with st.form(key=f"proofreading_form_{book_id}", border=False):
            selected_proofreader = st.selectbox(
                "Proofreader",
                proofreading_options,
                index=proofreading_options.index(st.session_state[f"proofreading_by_{book_id}"]) if st.session_state[f"proofreading_by_{book_id}"] in proofreading_names else 0,
                key=f"proofreading_select_{book_id}",
                help="Select an existing proofreader or 'Add New...' to enter a new one."
            )
            if selected_proofreader == "Add New...":
                st.session_state[f"proofreading_by_{book_id}"] = st.text_input(
                    "New Proofreader Name",
                    value="",
                    key=f"proofreading_new_input_{book_id}",
                    placeholder="Enter new proofreader name..."
                )
            elif selected_proofreader != "Select Proofreader":
                st.session_state[f"proofreading_by_{book_id}"] = selected_proofreader

            proofreading_by = st.text_input(
                "Proofreading By",
                value=st.session_state[f"proofreading_by_{book_id}"],
                key=f"proofreading_by_input_{book_id}"
            )
            col1, col2 = st.columns(2)
            with col1:
                proofreading_start_date = st.date_input("Start Date", value=current_data.get('proofreading_start', None), key=f"proofreading_start_date_{book_id}")
                proofreading_start_time = st.time_input("Start Time", value=current_data.get('proofreading_start', None), key=f"proofreading_start_time_{book_id}")
            with col2:
                proofreading_end_date = st.date_input("End Date", value=current_data.get('proofreading_end', None), key=f"proofreading_end_date_{book_id}")
                proofreading_end_time = st.time_input("End Time", value=current_data.get('proofreading_end', None), key=f"proofreading_end_time_{book_id}")
            if st.form_submit_button("💾 Save Proofreading", use_container_width=True):
                proofreading_start = f"{proofreading_start_date} {proofreading_start_time}" if proofreading_start_date and proofreading_start_time else None
                proofreading_end = f"{proofreading_end_date} {proofreading_end_time}" if proofreading_end_date and proofreading_end_time else None
                if proofreading_start and proofreading_end and proofreading_start > proofreading_end:
                    st.error("Start date/time must be before end date/time.")
                else:
                    updates = {
                        "proofreading_start": proofreading_start,
                        "proofreading_end": proofreading_end,
                        "proofreading_by": proofreading_by if proofreading_by else None
                    }
                    update_operation_details(book_id, updates)
                    st.session_state[f"proofreading_by_{book_id}"] = proofreading_by
                    st.success("✅ Updated Proofreading details")

    # Formatting Tab
    with tab3:
        with st.form(key=f"formatting_form_{book_id}", border=False):
            selected_formatter = st.selectbox(
                "Formatter",
                formatting_options,
                index=formatting_options.index(st.session_state[f"formatting_by_{book_id}"]) if st.session_state[f"formatting_by_{book_id}"] in formatting_names else 0,
                key=f"formatting_select_{book_id}",
                help="Select an existing formatter or 'Add New...' to enter a new one."
            )
            if selected_formatter == "Add New...":
                st.session_state[f"formatting_by_{book_id}"] = st.text_input(
                    "New Formatter Name",
                    value="",
                    key=f"formatting_new_input_{book_id}",
                    placeholder="Enter new formatter name..."
                )
            elif selected_formatter != "Select Formatter":
                st.session_state[f"formatting_by_{book_id}"] = selected_formatter

            formatting_by = st.text_input(
                "Formatting By",
                value=st.session_state[f"formatting_by_{book_id}"],
                key=f"formatting_by_input_{book_id}"
            )
            col1, col2 = st.columns(2)
            with col1:
                formatting_start_date = st.date_input("Start Date", value=current_data.get('formatting_start', None), key=f"formatting_start_date_{book_id}")
                formatting_start_time = st.time_input("Start Time", value=current_data.get('formatting_start', None), key=f"formatting_start_time_{book_id}")
            with col2:
                formatting_end_date = st.date_input("End Date", value=current_data.get('formatting_end', None), key=f"formatting_end_date_{book_id}")
                formatting_end_time = st.time_input("End Time", value=current_data.get('formatting_end', None), key=f"formatting_end_time_{book_id}")
            
            book_pages = st.number_input(
                "Total Book Pages",
                min_value=0,
                value=current_data.get('book_pages', 1) if current_data.get('book_pages') else 0,
                step=1,
                key=f"book_pages_{book_id}"
            )
            
            if st.form_submit_button("💾 Save Formatting", use_container_width=True):
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
                    st.session_state[f"formatting_by_{book_id}"] = formatting_by
                    st.success("✅ Updated Formatting details")

    # Book Cover Tab
    with tab4:
        with st.expander("📚 Front Cover Details", expanded=False):
            st.subheader("Front Cover")
            with st.form(key=f"front_cover_form_{book_id}", border=False):
                selected_front_cover = st.selectbox(
                    "Front Cover Designer",
                    front_cover_options,
                    index=front_cover_options.index(st.session_state[f"front_cover_by_{book_id}"]) if st.session_state[f"front_cover_by_{book_id}"] in front_cover_names else 0,
                    key=f"front_cover_select_{book_id}",
                    help="Select an existing front cover designer or 'Add New...' to enter a new one."
                )
                if selected_front_cover == "Add New...":
                    st.session_state[f"front_cover_by_{book_id}"] = st.text_input(
                        "New Front Cover Designer Name",
                        value="",
                        key=f"front_cover_new_input_{book_id}",
                        placeholder="Enter new front cover designer name..."
                    )
                elif selected_front_cover != "Select Front Cover Designer":
                    st.session_state[f"front_cover_by_{book_id}"] = selected_front_cover

                front_cover_by = st.text_input(
                    "Front Cover By",
                    value=st.session_state[f"front_cover_by_{book_id}"],
                    key=f"front_cover_by_input_{book_id}"
                )
                col1, col2 = st.columns(2)
                with col1:
                    front_cover_start_date = st.date_input("Front Start Date", value=current_data.get('front_cover_start', None), key=f"front_cover_start_date_{book_id}")
                    front_cover_start_time = st.time_input("Front Start Time", value=current_data.get('front_cover_start', None), key=f"front_cover_start_time_{book_id}")
                with col2:
                    front_cover_end_date = st.date_input("Front End Date", value=current_data.get('front_cover_end', None), key=f"front_cover_end_date_{book_id}")
                    front_cover_end_time = st.time_input("Front End Time", value=current_data.get('front_cover_end', None), key=f"front_cover_end_time_{book_id}")
                
                front_submit = st.form_submit_button("💾 Save Front Cover", use_container_width=True)

        with st.expander("📚 Back Cover Details", expanded=False):
            st.subheader("Back Cover")
            with st.form(key=f"back_cover_form_{book_id}", border=False):
                selected_back_cover = st.selectbox(
                    "Back Cover Designer",
                    back_cover_options,
                    index=back_cover_options.index(st.session_state[f"back_cover_by_{book_id}"]) if st.session_state[f"back_cover_by_{book_id}"] in back_cover_names else 0,
                    key=f"back_cover_select_{book_id}",
                    help="Select an existing back cover designer or 'Add New...' to enter a new one."
                )
                if selected_back_cover == "Add New...":
                    st.session_state[f"back_cover_by_{book_id}"] = st.text_input(
                        "New Back Cover Designer Name",
                        value="",
                        key=f"back_cover_new_input_{book_id}",
                        placeholder="Enter new back cover designer name..."
                    )
                elif selected_back_cover != "Select Back Cover Designer":
                    st.session_state[f"back_cover_by_{book_id}"] = selected_back_cover

                back_cover_by = st.text_input(
                    "Back Cover By",
                    value=st.session_state[f"back_cover_by_{book_id}"],
                    key=f"back_cover_by_input_{book_id}"
                )
                col1, col2 = st.columns(2)
                with col1:
                    back_cover_start_date = st.date_input("Back Start Date", value=current_data.get('back_cover_start', None), key=f"back_cover_start_date_{book_id}")
                    back_cover_start_time = st.time_input("Back Start Time", value=current_data.get('back_cover_start', None), key=f"back_cover_start_time_{book_id}")
                with col2:
                    back_cover_end_date = st.date_input("Back End Date", value=current_data.get('back_cover_end', None), key=f"back_cover_end_date_{book_id}")
                    back_cover_end_time = st.time_input("Back End Time", value=current_data.get('back_cover_end', None), key=f"back_cover_end_time_{book_id}")
                
                back_submit = st.form_submit_button("💾 Save Back Cover", use_container_width=True)

        # Handle form submissions
        if front_submit:
            front_cover_start = f"{front_cover_start_date} {front_cover_start_time}" if front_cover_start_date and front_cover_start_time else None
            front_cover_end = f"{front_cover_end_date} {front_cover_end_time}" if front_cover_end_date and front_cover_end_time else None
            if front_cover_start and front_cover_end and front_cover_start > front_cover_end:
                    st.error("Start date/time must be before end date/time.")
            else:
                updates = {
                    "front_cover_start": front_cover_start,
                    "front_cover_end": front_cover_end,
                    "front_cover_by": front_cover_by if front_cover_by else None
                }
                update_operation_details(book_id, updates)
                st.session_state[f"front_cover_by_{book_id}"] = front_cover_by  # Update session state after save
                st.success("✅ Updated Front Cover details")

        if back_submit:
            back_cover_start = f"{back_cover_start_date} {back_cover_start_time}" if back_cover_start_date and back_cover_start_time else None
            back_cover_end = f"{back_cover_end_date} {back_cover_end_time}" if back_cover_end_date and back_cover_end_time else None
            if back_cover_start and back_cover_end and back_cover_start > back_cover_end:
                    st.error("Start date/time must be before end date/time.")
            else:
                updates = {
                    "back_cover_start": back_cover_start,
                    "back_cover_end": back_cover_end,
                    "back_cover_by": back_cover_by if back_cover_by else None
                }
                update_operation_details(book_id, updates)
                st.session_state[f"back_cover_by_{book_id}"] = back_cover_by  # Update session state after save
                st.success("✅ Updated Back Cover details")

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
        col1,col2 = st.columns([6,1])
        with col1:
            st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
            #st.markdown(f"## {book_id} : {book_title}")
        with col2:
            if st.button(":material/refresh: Refresh", key="refresh_inventory", type="tertiary"):
                st.cache_data.clear()
    else:
        st.markdown(f"### Inventory & Delivery for Book ID: {book_id}")
        st.warning("Book title not found.")

    # Custom CSS for better aesthetics
    st.markdown("""
        <style>
        .info-box { 
            background-color: #f9f9f9; 
            border-radius: 8px; 
            margin-bottom: 10px; 
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1); 
        }
        .section-header {
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        .print-run-box, .new-print-run-box, .inventory-box {
            background-color: #ffffff;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .print-run-table {
            background-color: #ffffff;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .print-run-table-header {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            font-weight: bold;
            color: #2c3e50;
            padding: 8px;
            background-color: #f1f3f5;
            border-bottom: 1px solid #e0e0e0;
            border-radius: 5px 5px 0 0;
        }
        .print-run-table-row {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            padding: 8px;
            border-bottom: 1px solid #e0e0e0;
        }
        .print-run-table-row:last-child {
            border-bottom: none;
        }
        .print-run-table-row:hover {
            background-color: #f9f9f9;
        }
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

    # Fetch current inventory details from the books table (only fields we need)
    query = f"""
        SELECT ready_to_print, print_status, amazon_link, flipkart_link, 
               google_link, agph_link, google_review, book_mrp
        FROM books WHERE book_id = {book_id}
    """
    book_data = conn.query(query,show_spinner = False)
    
    if book_data.empty:
        st.warning(f"No inventory details found for Book ID: {book_id}")
        current_data = {}
    else:
        current_data = book_data.iloc[0].to_dict()

    # Define tabs for Printing and Inventory
    tab1, tab2 = st.tabs(["📚 Printing", "📦 Inventory"])

    # Printing Tab
    with tab1:
        with st.form(key=f"inventory_form_{book_id}", border=False):
            # Checkboxes (Compact and aligned)
            col1, col2 = st.columns([1, 1])
            with col1:
                ready_to_print = st.checkbox(
                    "Ready to Print?", 
                    value=current_data.get('ready_to_print', False), 
                    key=f"ready_to_print_{book_id}",
                    help="Check if the book is ready for printing."
                )
            with col2:
                print_status = st.checkbox(
                    "Printed?", 
                    value=current_data.get('print_status', False), 
                    key=f"print_status_{book_id}",
                    disabled=not ready_to_print,
                    help="Check if the book has been printed. Requires 'Ready to Print' to be checked."
                )

            # Print Runs Section (Visible only if 'Printed' is checked)
            if print_status:
                st.markdown('<div class="section-header">Print Runs</div>', unsafe_allow_html=True)
                
                # Fetch existing print runs
                print_runs_query = f"""
                    SELECT print_date, num_copies, print_by, print_cost, print_type, binding, book_size
                    FROM print_runs 
                    WHERE book_id = {book_id}
                    ORDER BY print_date DESC
                """
                print_runs_data = conn.query(print_runs_query,show_spinner = False)

                # Display existing print runs in an expander (collapsible)
                with st.expander("View Existing Print Runs", expanded=True):
                    if not print_runs_data.empty:
                        st.markdown('<div class="print-run-table">', unsafe_allow_html=True)
                        # Table Header
                        st.markdown("""
                            <div class="print-run-table-header">
                                <div>Date</div>
                                <div>Copies</div>
                                <div>Print By</div>
                                <div>Cost</div>
                                <div>Type</div>
                                <div>Binding</div>
                                <div>Size</div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Table Rows
                        for idx, row in print_runs_data.iterrows():
                            st.markdown(f"""
                                <div class="print-run-table-row">
                                    <div>{row['print_date']}</div>
                                    <div>{int(row['num_copies'])}</div>
                                    <div>{row['print_by'] or 'N/A'}</div>
                                    <div>{row['print_cost'] or 'N/A'}</div>
                                    <div>{row['print_type']}</div>
                                    <div>{row['binding']}</div>
                                    <div>{row['book_size']}</div>
                                </div>
                            """, unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.info("No print runs found. Add a new print run below.")

                # Add New Print Run Section
                st.markdown('<div class="section-header">Add New Print Run</div>', unsafe_allow_html=True)
                with st.container(border=True):
                    st.markdown('<div class="new-print-run-box">', unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        new_print_date = st.date_input(
                            "Print Date", 
                            value=date.today(), 
                            key=f"new_print_date_{book_id}"
                        )
                        print_cost = st.text_input(
                            "Print Cost", 
                            key=f"print_cost_{book_id}"
                        )
                    with col2:
                        new_num_copies = st.number_input(
                            "Number of Copies", 
                            min_value=0, 
                            step=1, 
                            key=f"new_num_copies_{book_id}"
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
                            options=["6x9","A4"], 
                            key=f"book_size_{book_id}"
                        )
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                print_by = None
                print_cost = None
                print_type = None
                binding = None
                book_size = None

            # Submit Button (Compact and aligned)
            save_printing = st.form_submit_button(
                "💾 Save Printing", 
                use_container_width=True,
                help="Click to save changes to printing details."
            )

            # Handle form submission (moved inside the form context)
            if save_printing:
                try:
                    # Fetch values from session state to ensure latest form inputs
                    ready_to_print_value = st.session_state[f"ready_to_print_{book_id}"]
                    print_status_value = st.session_state[f"print_status_{book_id}"]
                    
                    updates = {
                        "ready_to_print": ready_to_print_value,
                        "print_status": print_status_value,
                    }
                    update_inventory_delivery_details(book_id, updates, conn)

                    # Save new print run if applicable
                    if print_status_value and st.session_state[f"new_num_copies_{book_id}"] > 0:
                        with conn.session as session:
                            session.execute(
                                text("""
                                    INSERT INTO print_runs (book_id, print_date, num_copies, print_by, print_cost, print_type, binding, book_size)
                                    VALUES (:book_id, :print_date, :num_copies, :print_by, :print_cost, :print_type, :binding, :book_size)
                                """),
                                {
                                    "book_id": book_id, 
                                    "print_date": st.session_state[f"new_print_date_{book_id}"], 
                                    "num_copies": st.session_state[f"new_num_copies_{book_id}"],
                                    "print_by": st.session_state[f"print_by_{book_id}"] if st.session_state[f"print_by_{book_id}"] else None,
                                    "print_cost": float(st.session_state[f"print_cost_{book_id}"]) if st.session_state[f"print_cost_{book_id}"] else None,
                                    "print_type": st.session_state[f"print_type_{book_id}"],
                                    "binding": st.session_state[f"binding_{book_id}"],
                                    "book_size": st.session_state[f"book_size_{book_id}"]
                                }
                            )
                            session.commit()

                    st.success("✅ Updated Printing details")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"❌ Error saving printing details: {str(e)}")

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
                        
                        st.success("✅ Updated Inventory details")
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
    
    # Check if query is a number (for book_id)
    if query.isdigit():
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
srcol1, srcol2, srcol3, srcol4 = st.columns([7, 4, 1, 1]) 

with srcol1:
    search_query = st.text_input("🔎 Search Books", "", placeholder="Search by ID, title, ISBN, or date...", key="search_bar",
                                 label_visibility="collapsed")
    filtered_books = filter_books(books, search_query)

# Add filtering popover next to the Add New Book button
with srcol2:
    with st.popover("Filter by Date & Status", use_container_width=True):
        # Extract unique years from the dataset
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
            st.session_state.status_filter = None  # Default: no status filter applied (single value, not a list)
        if 'clear_filters_trigger' not in st.session_state:
            st.session_state.clear_filters_trigger = 0  # Use a counter instead of boolean

        col1, col2 = st.columns([3, 1])
        with col1:
            st.write("Filter by Year:")

        with col2:
            # Clear filters button
            if st.button(":material/restart_alt: Reset", key="clear_filters", help="Clear all filters", use_container_width=True, type="tertiary"):
                st.session_state.year_filter = None
                st.session_state.month_filter = None
                st.session_state.start_date_filter = None
                st.session_state.end_date_filter = None
                st.session_state.status_filter = None  # Reset status filter to None
                st.session_state.clear_filters_trigger += 1
                st.rerun()

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

        # Status filter with pills (Delivered or On Going, single selection)
        st.write("Filter by Status:")
        status_options = ["Delivered", "On Going"]
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
                status_mapping = {"Delivered": 1, "On Going": 0}
                selected_status_value = status_mapping[st.session_state.status_filter]
                filtered_books = filtered_books[filtered_books['deliver'] == selected_status_value]
            st.success(f"Filter {', '.join(applied_filters)}")

# Add page size selection
with srcol4:
    page_size_options = [40, 100, "All"]
    if 'page_size' not in st.session_state:
        st.session_state.page_size = page_size_options[0]  # Default page size
    st.session_state.page_size = st.selectbox("Books per page", options=page_size_options, index=0, key="page_size_select",
                                              label_visibility="collapsed")

# Add New Book button
with srcol3:
    if st.button(":material/add: Book", type="secondary", help="Add New Book", use_container_width=True):
        add_book_dialog(conn)

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
column_size = [1, 4, 1, 1, 1, 2]

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
                    
                    if row['is_single_author'] == 1:
                        # For single-author books, show "Single" in a pill-shaped badge
                        badge_content = "Single"
                        badge_style = "color: #2aba25; font-size: 12px; background-color: #f7f7f7; padding: 2px 6px; border-radius: 12px;"
                    else:
                        # For multi-author books, show the author count as before
                        badge_content = str(author_count)
                        badge_style = "color: #2aba25; font-size:14px; background-color: #f7f7f7; padding: 1px 4px; border-radius: 10px;"
                    
                    # Display the title and the appropriate badge
                    st.markdown(
                        f"{row['title']} <span style='{badge_style}'>{badge_content}</span>",
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
                        if st.button(price_icon, key=f"price_btn_{row['book_id']}", help="Edit Price"):
                            manage_price_dialog(row['book_id'], row['price'],conn)
                    with btn_col3:
                        if st.button(author_icon, key=f"edit_author_{row['book_id']}", help="Edit Authors"):
                            edit_author_dialog(row['book_id'], conn)
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

                



                



# def example():
#     rain(
#         emoji="🎈",
#         font_size=50,
#         falling_speed=2,
#         animation_length="infinite",
#     )

# example()



 