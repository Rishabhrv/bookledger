import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import date
import time
from streamlit_extras.let_it_rain import rain


st.cache_data.clear()

# --- Database Connection ---
def connect_db():
    try:
        conn = st.connection('mysql', type='sql')
        return conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

# Connect to MySQL
conn = st.connection("mysql", type="sql")

# Fetch books from the database
query = "SELECT book_id, title, date, isbn, apply_isbn, deliver, price FROM books"
books = conn.query(query)

# Convert 'date' column to datetime objects if it's not already
if not pd.api.types.is_datetime64_any_dtype(books['date']):
    books['date'] = pd.to_datetime(books['date'])

def get_isbn_display(isbn, apply_isbn):
    if pd.notna(isbn):
        return f"**<span style='color:#47b354; background-color:#f7f7f7; font-size:14px; padding: 2px 6px; border-radius: 4px;'>{isbn}</span>**"  # Grayish background and smaller font for valid ISBN
    elif apply_isbn == 0:
        return f"**<span style='color:#eb7150; background-color:#f7f7f7; font-size:14px; padding: 2px 6px; border-radius: 4px;'>Not Applied</span>**"  # Red for Not Applied
    elif apply_isbn == 1:
        return f"**<span style='color:#e0ab19; background-color:#f7f7f7; font-size:14px; padding: 2px 6px; border-radius: 4px;'>Not Received</span>**"  # Orange for Not Received
    return f"**<span style='color:#000000; background-color:#f7f7f7; font-size:14px; padding: 2px 6px; border-radius: 4px;'>-</span>**"  # Black for default/unknown case


# Function to get status with outlined pill styling
def get_status_pill(deliver_value):

    pill_style = (
        "padding: 2px 6px; "  
        "border-radius: 4px; " 
        "background-color: #f7f7f7; "  
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


# Function to fetch book details (for title and book_id)
def fetch_book_details(book_id):
    query = f"SELECT book_id, title FROM books WHERE book_id = '{book_id}'"
    return conn.query(query)


###################################################################################################################################
##################################--------------- Add New Book & Auhtor ----------------------------##################################
###################################################################################################################################

@st.dialog("Add Book and Authors", width="large")
def add_book_dialog():
    conn = connect_db()

    # --- UI Components Inside Dialog ---
    def book_details_section():
        st.markdown("<h5>Book Details</h5>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        book_title = col1.text_input("Book Title", placeholder="Enter Book Title..", key="book_title")
        book_date = col2.date_input("Date", value=date.today(), key="book_date")
        return {
            "title": book_title,
            "date": book_date
        }

    def author_details_section(conn):
        if "authors" not in st.session_state:
            # Initialize exactly 4 authors with default positions
            st.session_state.authors = [
                {"name": "", "email": "", "phone": "", "author_id": None, "author_position": f"{i+1}{'st' if i == 0 else 'nd' if i == 1 else 'rd' if i == 2 else 'th'}"}
                for i in range(4)
            ]

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
                    st.error(f"Error fetching author suggestions: {e}")
                    return []

        with st.container(border=True):
            st.markdown("<h5>Author Details</h5>", unsafe_allow_html=True)
            
            # Create tabs for each author
            tab_titles = [f"Author {i+1}" for i in range(4)]
            tabs = st.tabs(tab_titles)

            for i, tab in enumerate(tabs):
                with tab:
                    col1, col2 = st.columns([2, 1])
                    
                    # Author Name and Suggestions
                    author_name_input_key = f"author_name_{i}"
                    author_name = col1.text_input(f"Author Name {i+1}", st.session_state.authors[i]["name"], key=author_name_input_key, placeholder='Enter Author name..')

                    suggestions = get_author_suggestions(conn, author_name)

                    suggestion_options = []
                    disabled_suggestion = False
                    suggestion_placeholder = "Type to search authors..."

                    if suggestions:
                        suggestion_names = [f"{a.name} (ID: {a.author_id})" for a in suggestions]
                        suggestion_options = [""] + suggestion_names
                        suggestion_placeholder = "Suggested authors found..."
                    else:
                        suggestion_options = ["No authors found"]
                        disabled_suggestion = True
                        suggestion_placeholder = "No authors found"

                    selected_suggestion = col2.selectbox(
                        f"Suggestions {i+1}",
                        suggestion_options,
                        index=0,
                        key=f"author_suggestion_{i}",
                        label_visibility="hidden",
                        disabled=disabled_suggestion,
                        placeholder=suggestion_placeholder
                    )

                    if selected_suggestion and selected_suggestion != "No authors found": 
                        if "(ID: " in selected_suggestion:  
                            selected_author_id = int(selected_suggestion.split('(ID: ')[1][:-1])
                            selected_author = next((a for a in suggestions if a.author_id == selected_author_id), None)
                            if selected_author:
                                # Update the author details with the selected existing author
                                st.session_state.authors[i]["name"] = selected_author.name
                                st.session_state.authors[i]["email"] = selected_author.email
                                st.session_state.authors[i]["phone"] = selected_author.phone
                                st.session_state.authors[i]["author_id"] = selected_author.author_id
                    else:
                        # If no suggestion is selected, update the name but preserve other fields
                        st.session_state.authors[i]["name"] = author_name
                        if not st.session_state.authors[i]["author_id"]:  # If not an existing author, ensure fields are not overwritten
                            st.session_state.authors[i]["email"] = st.session_state.authors[i].get("email", "")
                            st.session_state.authors[i]["phone"] = st.session_state.authors[i].get("phone", "")

                    # Email, Phone, and Position in a more compact layout
                    col3, col4 = st.columns(2)
                    st.session_state.authors[i]["email"] = col3.text_input(f"Email {i+1}", st.session_state.authors[i]["email"], key=f"email_{i}", placeholder="Enter email..")
                    st.session_state.authors[i]["phone"] = col4.text_input(f"Phone {i+1}", st.session_state.authors[i]["phone"], key=f"phone_{i}", placeholder="Enter phone..")

                    # Position selection (ensure uniqueness)
                    col5, _ = st.columns([1, 1])
                    available_positions = ["1st", "2nd", "3rd", "4th"]
                    # Remove positions already taken by other authors
                    taken_positions = [a["author_position"] for a in st.session_state.authors if a != st.session_state.authors[i]]
                    available_positions = [p for p in available_positions if p not in taken_positions or p == st.session_state.authors[i]["author_position"]]
                    st.session_state.authors[i]["author_position"] = col5.selectbox(
                        f"Position {i+1}",
                        available_positions,
                        index=available_positions.index(st.session_state.authors[i]["author_position"]) if st.session_state.authors[i]["author_position"] in available_positions else 0,
                        key=f"author_position_{i}"
                    )

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
        return bool(author["name"] or author["email"] or author["phone"])

    def validate_form(book_data, author_data):
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
        author_data = author_details_section(conn)

    # --- Save Functionality Inside Dialog ---
    col1, col2 = st.columns([7,1])
    if col1.button("Save", key="dialog_save", type="primary"):
        errors = validate_form(book_data, author_data)
        if errors:
            st.error("\n".join(errors), icon="🚨")
        else:
            with conn.session as s:
                try:
                    # Insert book
                    s.execute(text("""
                        INSERT INTO books (title, date)
                        VALUES (:title, :date)
                    """), params={"title": book_data["title"], "date": book_data["date"]})
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
                                INSERT INTO book_authors (book_id, author_id, author_position)
                                VALUES (:book_id, :author_id, :author_position)
                            """), params={"book_id": book_id, "author_id": author_id_to_link, "author_position": author["author_position"]})
                    s.commit()
                    st.success("Book and Authors Saved Successfully!", icon="✅")
                    time.sleep(1)  # Give user time to see the success message
                    st.session_state.authors = [
                        {"name": "", "email": "", "phone": "", "author_id": None, "author_position": f"{i+1}{'st' if i == 0 else 'nd' if i == 1 else 'rd' if i == 2 else 'th'}"}
                        for i in range(4)
                    ]  # Reset authors
                    st.rerun()  # Close the dialog by rerunning the app
                except Exception as db_error:
                    s.rollback()
                    st.error(f"Database error during save: {db_error}", icon="❌")

    if col2.button("Cancel", key="dialog_cancel", type="secondary"):
        st.session_state.authors = [
            {"name": "", "email": "", "phone": "", "author_id": None, "author_position": f"{i+1}{'st' if i == 0 else 'nd' if i == 1 else 'rd' if i == 2 else 'th'}"}
            for i in range(4)
        ]  # Reset authors
        st.rerun()



###################################################################################################################################
##################################--------------- Edit Auhtor Dialog ----------------------------##################################
###################################################################################################################################


# Function to fetch book_author details along with author details for a given book_id
def fetch_book_authors(book_id):
    query = f"""
    SELECT ba.id, ba.book_id, ba.author_id, a.name, a.email, a.phone, 
           ba.author_position, ba.welcome_mail_sent, ba.corresponding_agent, 
           ba.publishing_consultant, ba.photo_recive, ba.id_proof_recive, 
           ba.author_details_sent, ba.cover_agreement_sent, ba.agreement_received, 
           ba.digital_book_sent, ba.digital_book_approved, ba.plagiarism_report, 
           ba.printing_confirmation, ba.delivery_address, ba.delivery_charge, 
           ba.number_of_books, ba.total_amount, ba.emi1, ba.emi2, ba.emi3,
           ba.emi1_date, ba.emi2_date, ba.emi3_date
    FROM book_authors ba
    JOIN authors a ON ba.author_id = a.author_id
    WHERE ba.book_id = '{book_id}'
    """
    return conn.query(query)

# Function to update book_authors table
def update_book_authors(id, updates):
    set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
    query = f"UPDATE book_authors SET {set_clause} WHERE id = :id"
    params = updates.copy()
    params["id"] = int(id) 
    with conn.session as session:  
        session.execute(text(query), params)
        session.commit()

# Updated dialog for editing author details with improved UI
@st.dialog("Edit Author Details", width='large')
def edit_author_dialog(book_id):
    # Constants
    MAX_AUTHORS = 4
    # Fetch book details for title
    book_details = fetch_book_details(book_id)
    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        st.markdown(f"## {book_id} : {book_title}")
    else:
        st.markdown(f"### Authors for Book ID: {book_id}")
        st.warning("Book title not found.")

    # Custom CSS for better aesthetics
    st.markdown("""
        <style>
        .info-box { 
            background-color: #f9f9f9; 
            padding: 0px; 
            border-radius: 8px; 
            margin-bottom: 5px; 
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1); 
        }
        .stTextInput>div>div>input, .stSelectbox>div>div>select {
            border-radius: 5px;
            padding: 3px;
        }
        .stCheckbox>div {
            padding-top: 4px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Fetch author details
    book_authors = fetch_book_authors(book_id)
    
    if book_authors.empty:
        st.warning(f"No authors found for Book ID: {book_id}")
    else:
        for _, row in book_authors.iterrows():
            # Expander for author details
            with st.expander(f"📖 {row['name']} (ID: {row['author_id']})", expanded=False):
                # Read-only details with styling
                st.markdown('<div class="info-box">', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**📌 Author ID:** {row['author_id']}")
                    st.markdown(f"**👤 Name:** {row['name']}")
                with col2:
                    st.markdown(f"**📧 Email:** {row['email'] or 'N/A'}")
                    st.markdown(f"**📞 Phone:** {row['phone'] or 'N/A'}")
                st.markdown("---")
                
                # Editable section
                with st.form(key=f"edit_form_{row['id']}", border=False):
                    st.markdown("### ✏️ Edit Author Details", unsafe_allow_html=True)

                    col3, col4 = st.columns([3,2])
                    with col3:
                        author_position = st.selectbox("Author Position", ["1st", "2nd", "3rd", "4th"], index=0)
                        corresponding_agent = st.text_input("Corresponding Agent", value=row['corresponding_agent'] or "")
                        publishing_consultant = st.text_input("Publishing Consultant", value=row['publishing_consultant'] or "")
                    with col4:
                        welcome_mail_sent = st.checkbox("✅ Welcome Mail Sent", value=bool(row['welcome_mail_sent']))
                        digital_book_sent = st.checkbox("📘 Digital Book Sent", value=bool(row['digital_book_sent']))
                        digital_book_approved = st.checkbox("✔️ Digital Book Approved", value=bool(row['digital_book_approved']))
                        plagiarism_report = st.checkbox("📝 Plagiarism Report", value=bool(row['plagiarism_report']))
                    
                    # Additional checkboxes
                    col5, col6 = st.columns(2)
                    with col5:
                        photo_recive = st.checkbox("📷 Photo Received", value=bool(row['photo_recive']))
                        id_proof_recive = st.checkbox("🆔 ID Proof Received", value=bool(row['id_proof_recive']))
                        author_details_sent = st.checkbox("✉️ Author Details Sent", value=bool(row['author_details_sent']))
                    with col6:
                        cover_agreement_sent = st.checkbox("📜 Cover Agreement Sent", value=bool(row['cover_agreement_sent']))
                        agreement_received = st.checkbox("✅ Agreement Received", value=bool(row['agreement_received']))
                        printing_confirmation = st.checkbox("🖨️ Printing Confirmation", value=bool(row['printing_confirmation']))

                    # New delivery section
                    st.markdown("### 🚚 Delivery Details")
                    col7, col8, col9 = st.columns(3)
                    with col7:
                        delivery_address = st.text_area("Delivery Address", value=row['delivery_address'] or "", height=100)
                    with col8:
                        delivery_charge = st.number_input("Delivery Charge (₹)", min_value=0.0, step=0.01, value=float(row['delivery_charge'] or 0.0))
                    with col9:
                        number_of_books = st.number_input("Number of Books", min_value=0, step=1, value=int(row['number_of_books'] or 0))

                    # Submit button
                    if st.form_submit_button("💾 Save Changes", use_container_width=True):
                        updates = {
                            "author_position": author_position,
                            "welcome_mail_sent": int(welcome_mail_sent),
                            "corresponding_agent": corresponding_agent,
                            "publishing_consultant": publishing_consultant,
                            "photo_recive": int(photo_recive),
                            "id_proof_recive": int(id_proof_recive),
                            "author_details_sent": int(author_details_sent),
                            "cover_agreement_sent": int(cover_agreement_sent),
                            "agreement_received": int(agreement_received),
                            "digital_book_sent": int(digital_book_sent),
                            "digital_book_approved": int(digital_book_approved),
                            "plagiarism_report": int(plagiarism_report),
                            "printing_confirmation": int(printing_confirmation),
                            "delivery_address": delivery_address,
                            "delivery_charge": delivery_charge,
                            "number_of_books": number_of_books
                        }
                        update_book_authors(row['id'], updates)
                        st.cache_data.clear()
                        st.success(f"✅ Updated details for {row['name']} (Author ID: {row['author_id']})")

    existing_author_count = len(book_authors)
    available_slots = MAX_AUTHORS - existing_author_count

    if existing_author_count >= MAX_AUTHORS:
        st.warning("This book already has the maximum number of authors (4). No more authors can be added.")
        if st.button("Close"):
            st.rerun()
        return

    if existing_author_count == 0:
        st.warning(f"No authors found for Book ID: {book_id}")

    # Initialize session state for new authors
    if "new_authors" not in st.session_state:
        st.session_state.new_authors = [
            {"name": "", "email": "", "phone": "", "author_id": None, "author_position": None}
            for _ in range(available_slots)
        ]

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
                st.error(f"Error fetching suggestions: {e}")
                return []

    def validate_author(author, existing_positions, existing_author_ids):
        """Validate an author's details."""
        if not (author["name"] and author["email"] and author["phone"] and author["author_position"]):
            return False, "All fields (Name, Email, Phone, Position) are required for each author."
        if author["author_position"] in existing_positions:
            return False, f"Position '{author['author_position']}' is already taken."
        if author["author_id"] in existing_author_ids:
            return False, f"Author '{author['name']}' is already linked to this book."
        return True, ""

    # Get existing positions and author IDs to prevent duplicates
    existing_positions = [author["author_position"] for _, author in book_authors.iterrows()]
    existing_author_ids = [author["author_id"] for _, author in book_authors.iterrows()]

    st.markdown(f"### Add Up to {available_slots} New Authors")

    # Use tabs for static number of new authors
    tabs = st.tabs([f"Author {i+1}" for i in range(available_slots)])

    for i, tab in enumerate(tabs):
        with tab:
            with st.container(border=True):
                st.markdown(f"#### New Author {i+1}", unsafe_allow_html=True)
                col1, col2 = st.columns([2, 1])

                # Author Name with Suggestions
                with col1:
                    author_name_input_key = f"new_author_name_{i}"
                    author_name = st.text_input("Author Name", st.session_state.new_authors[i]["name"], key=author_name_input_key, placeholder='Enter Author name..')

                    suggestions = get_author_suggestions(conn, author_name)
                    suggestion_options = []
                    disabled_suggestion = False
                    suggestion_placeholder = "Type to search authors..."

                    if suggestions:
                        suggestion_names = [f"{a.name} (ID: {a.author_id})" for a in suggestions]
                        suggestion_options = [""] + suggestion_names
                        suggestion_placeholder = "Suggested authors found..."
                    else:
                        suggestion_options = ["No authors found"]
                        disabled_suggestion = True
                        suggestion_placeholder = "No authors found"

                    selected_suggestion = st.selectbox(
                        "Suggestions",
                        suggestion_options,
                        index=0,
                        key=f"new_author_suggestion_{i}",
                        label_visibility="hidden",
                        disabled=disabled_suggestion,
                        placeholder=suggestion_placeholder
                    )

                    if selected_suggestion and selected_suggestion != "No authors found":
                        if "(ID: " in selected_suggestion:
                            selected_author_id = int(selected_suggestion.split('(ID: ')[1][:-1])
                            selected_author = next((a for a in suggestions if a.author_id == selected_author_id), None)
                            if selected_author:
                                st.session_state.new_authors[i]["name"] = selected_author.name
                                st.session_state.new_authors[i]["email"] = selected_author.email
                                st.session_state.new_authors[i]["phone"] = selected_author.phone
                                st.session_state.new_authors[i]["author_id"] = selected_author.author_id
                    else:
                        st.session_state.new_authors[i]["name"] = author_name

                # Email, Phone, and Position
                with col2:
                    st.session_state.new_authors[i]["email"] = st.text_input("Email", st.session_state.new_authors[i]["email"], key=f"new_author_email_{i}")
                    st.session_state.new_authors[i]["phone"] = st.text_input("Phone", st.session_state.new_authors[i]["phone"], key=f"new_author_phone_{i}")
                    available_positions = [pos for pos in ["1st", "2nd", "3rd", "4th"] if pos not in existing_positions]
                    if available_positions:
                        st.session_state.new_authors[i]["author_position"] = st.selectbox(
                            "Position",
                            available_positions,
                            key=f"new_author_position_{i}"
                        )
                    else:
                        st.error("No available positions left.")

    # Single button to save all new authors
    if st.button("Add Authors to Book", key="add_authors_to_book"):
        errors = []
        active_authors = [author for author in st.session_state.new_authors if any(author.values())]  # Only consider authors with at least one field filled

        for author in active_authors:
            is_valid, error_message = validate_author(author, existing_positions, existing_author_ids)
            if not is_valid:
                errors.append(error_message)
            else:
                existing_positions.append(author["author_position"])  # Update positions for validation of next author

        if errors:
            for error in errors:
                st.error(error)
        else:
            for author in active_authors:
                if author["name"] and author["email"] and author["phone"]:
                    author_id_to_link = author["author_id"] or insert_author(conn, author["name"], author["email"], author["phone"])
                    if book_id and author_id_to_link:
                        with conn.session as s:
                            s.execute(
                                text("""
                                    INSERT INTO book_authors (book_id, author_id, author_position)
                                    VALUES (:book_id, :author_id, :author_position)
                                """),
                                params={
                                    "book_id": book_id,
                                    "author_id": author_id_to_link,
                                    "author_position": author["author_position"]
                                }
                            )
                            s.commit()
            st.cache_data.clear()
            st.success("New Authors added successfully")
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

@st.dialog("Edit Operation Details", width='large')
def edit_operation_dialog(book_id):
    # Fetch book details for title
    book_details = fetch_book_details(book_id)
    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        st.markdown(f"## {book_id} : {book_title}")
    else:
        st.markdown(f"### Operations for Book ID: {book_id}")
        st.warning("Book title not found.")

    # Custom CSS for better aesthetics
    st.markdown("""
        <style>
        .info-box { 
            background-color: #f9f9f9; 
            padding: 10px; 
            border-radius: 8px; 
            margin-bottom: 10px; 
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1); 
        }
        .stTextInput>div>div>input, .stDateInput>div>div>input, .stTimeInput>div>div>input {
            border-radius: 5px;
            padding: 6px;
        }
        .stTab {
            background-color: #ffffff;
            padding: 10px;
            border-radius: 8px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Fetch current operation details from the books table
    query = f"""
        SELECT writing_start, writing_end, writing_by, 
               proofreading_start, proofreading_end, proofreading_by, 
               formatting_start, formatting_end, formatting_by, 
               front_cover_start, front_cover_end, front_cover_by,
               back_cover_start, back_cover_end, back_cover_by
        FROM books WHERE book_id = {book_id}
    """
    book_operations = conn.query(query)
    
    if book_operations.empty:
        st.warning(f"No operation details found for Book ID: {book_id}")
        current_data = {}
    else:
        current_data = book_operations.iloc[0].to_dict()

    # Define tabs for each operation
    tab1, tab2, tab3, tab4 = st.tabs(["✍️ Writing", "🔍 Proofreading", "📏 Formatting", "🎨 Book Cover"])

    # Writing Tab
    with tab1:
        with st.form(key=f"writing_form_{book_id}", border=False):

            writing_by = st.text_input("Writing By", value=current_data.get('writing_by', ""), key=f"writing_by_{book_id}")
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
                updates = {
                    "writing_start": writing_start,
                    "writing_end": writing_end,
                    "writing_by": writing_by if writing_by else None
                }
                update_operation_details(book_id, updates)
                st.success("✅ Updated Writing details")

    # Proofreading Tab
    with tab2:
        with st.form(key=f"proofreading_form_{book_id}", border=False):
            proofreading_by = st.text_input("Proofreading By", value=current_data.get('proofreading_by', ""), key=f"proofreading_by_{book_id}")

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
                updates = {
                    "proofreading_start": proofreading_start,
                    "proofreading_end": proofreading_end,
                    "proofreading_by": proofreading_by if proofreading_by else None
                }
                update_operation_details(book_id, updates)
                st.success("✅ Updated Proofreading details")

    # Formatting Tab
    with tab3:
        with st.form(key=f"formatting_form_{book_id}", border=False):
            formatting_by = st.text_input("Formatting By", value=current_data.get('formatting_by', ""), key=f"formatting_by_{book_id}")
            col1, col2 = st.columns(2)
            with col1:
                formatting_start_date = st.date_input("Start Date", value=current_data.get('formatting_start', None), key=f"formatting_start_date_{book_id}")
                formatting_start_time = st.time_input("Start Time", value=current_data.get('formatting_start', None), key=f"formatting_start_time_{book_id}")
            with col2:
                formatting_end_date = st.date_input("End Date", value=current_data.get('formatting_end', None), key=f"formatting_end_date_{book_id}")
                formatting_end_time = st.time_input("End Time", value=current_data.get('formatting_end', None), key=f"formatting_end_time_{book_id}")
            if st.form_submit_button("💾 Save Formatting", use_container_width=True):
                formatting_start = f"{formatting_start_date} {formatting_start_time}" if formatting_start_date and formatting_start_time else None
                formatting_end = f"{formatting_end_date} {formatting_end_time}" if formatting_end_date and formatting_end_time else None
                updates = {
                    "formatting_start": formatting_start,
                    "formatting_end": formatting_end,
                    "formatting_by": formatting_by if formatting_by else None
                }
                update_operation_details(book_id, updates)
                st.success("✅ Updated Formatting details")

    # Updated Book Cover Tab
    with tab4:
        with st.expander("📚 Front Cover Details", expanded=False):
            # Front Cover Section
            st.subheader("Front Cover")
            with st.form(key=f"front_cover_form_{book_id}", border=False):
                front_cover_by = st.text_input("Front Cover By", value=current_data.get('front_cover_by', ""), key=f"front_cover_by_{book_id}")
                col1, col2 = st.columns(2)
                with col1:
                    front_cover_start_date = st.date_input("Front Start Date", value=current_data.get('front_cover_start', None), key=f"front_cover_start_date_{book_id}")
                    front_cover_start_time = st.time_input("Front Start Time", value=current_data.get('front_cover_start', None), key=f"front_cover_start_time_{book_id}")
                with col2:
                    front_cover_end_date = st.date_input("Front End Date", value=current_data.get('front_cover_end', None), key=f"front_cover_end_date_{book_id}")
                    front_cover_end_time = st.time_input("Front End Time", value=current_data.get('front_cover_end', None), key=f"front_cover_end_time_{book_id}")
                front_submit = st.form_submit_button("💾 Save Front Cover", use_container_width=True)

        with st.expander("📚 Back Cover Details", expanded=False):
            # Back Cover Section
            st.subheader("Back Cover")
            with st.form(key=f"back_cover_form_{book_id}", border=False):
                back_cover_by = st.text_input("Back Cover By", value=current_data.get('back_cover_by', ""), key=f"back_cover_by_{book_id}")
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
            updates = {
                "front_cover_start": front_cover_start,
                "front_cover_end": front_cover_end,
                "front_cover_by": front_cover_by if front_cover_by else None
            }
            update_operation_details(book_id, updates)
            st.success("✅ Updated Front Cover details")
            

        if back_submit:
            back_cover_start = f"{back_cover_start_date} {back_cover_start_time}" if back_cover_start_date and back_cover_start_time else None
            back_cover_end = f"{back_cover_end_date} {back_cover_end_time}" if back_cover_end_date and back_cover_end_time else None
            updates = {
                "back_cover_start": back_cover_start,
                "back_cover_end": back_cover_end,
                "back_cover_by": back_cover_by if back_cover_by else None
            }
            update_operation_details(book_id, updates)
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


@st.dialog("Edit Inventory & Delivery Details", width='large')
def edit_inventory_delivery_dialog(book_id):
    # Fetch book details for title
    book_details = fetch_book_details(book_id)
    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        st.markdown(f"## {book_id} : {book_title}")
    else:
        st.markdown(f"### Inventory & Delivery for Book ID: {book_id}")
        st.warning("Book title not found.")

    # Custom CSS for better aesthetics
    st.markdown("""
        <style>
        .info-box { 
            background-color: #f9f9f9; 
            padding: 10px; 
            border-radius: 8px; 
            margin-bottom: 10px; 
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1); 
        }
        .stTextInput>div>div>input, .stDateInput>div>div>input, .stNumberInput>div>div>input {
            border-radius: 5px;
            padding: 6px;
        }
        .stTab {
            background-color: #ffffff;
            padding: 10px;
            border-radius: 8px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Fetch current inventory and delivery details from the books table
    query = f"""
        SELECT ready_to_print, print_status, print_by, print_cost, book_mrp, book_pages,
               deliver, deliver_date, tracking_id, amazon_link, flipkart_link, 
               google_link, agph_link, google_review
        FROM books WHERE book_id = {book_id}
    """
    book_data = conn.query(query)
    
    if book_data.empty:
        st.warning(f"No inventory & delivery details found for Book ID: {book_id}")
        current_data = {}
    else:
        current_data = book_data.iloc[0].to_dict()

    # Define tabs for Inventory and Delivery
    tab1, tab2 = st.tabs(["📚 Printing", "🚚 Delivery"])

    # Inventory Tab
    with tab1:
        with st.form(key=f"inventory_form_{book_id}", border=False):
            # Checkboxes at the top (full width)
            ready_to_print = st.checkbox("Ready to Print?", value=current_data.get('ready_to_print', False), key=f"ready_to_print_{book_id}")
            print_status = st.checkbox("Printed?", 
                                    value=current_data.get('print_status', False), 
                                    key=f"print_status_{book_id}",
                                    disabled=not ready_to_print)
            
            if print_status:
                # Create two columns for the input fields
                col1, col2 = st.columns(2)
                
                with col1:
                    print_by = st.text_input("Print By", 
                                        value=current_data.get('print_by', ""), 
                                        key=f"print_by_{book_id}")
                    print_cost = st.text_input("Print Cost", 
                                            value=str(current_data.get('print_cost', 0.0)) if current_data.get('print_cost') is not None else "", 
                                            key=f"print_cost_{book_id}")
                    book_mrp = st.text_input("Book MRP", 
                                        value=str(current_data.get('book_mrp', 0.0)) if current_data.get('book_mrp') is not None else "", 
                                        key=f"book_mrp_{book_id}")
                    book_pages = st.text_input("Book Pages", 
                                            value=str(current_data.get('book_pages', 0)) if current_data.get('book_pages') is not None else "", 
                                            key=f"book_pages_{book_id}")
                
                with col2:
                    book_size = st.selectbox("Book Size", 
                                        options=["A4", "6x9"], 
                                        index=["A4", "6x9"].index(current_data.get('book_size', "A4")) if current_data.get('book_size') in ["A4", "6x9"] else 0, 
                                        key=f"book_size_{book_id}")
                    print_type = st.selectbox("Print Type", 
                                            options=["B&W", "Color"], 
                                            index=["B&W", "Color"].index(current_data.get('print_type', "B&W")) if current_data.get('print_type') in ["B&W", "Color"] else 0, 
                                            key=f"print_type_{book_id}")
                    binding = st.selectbox("Binding", 
                                        options=["Paperback", "Hardcover"], 
                                        index=["Paperback", "Hardcover"].index(current_data.get('binding', "Paperback")) if current_data.get('binding') in ["Paperback", "Hardcover"] else 0, 
                                        key=f"binding_{book_id}")
                    num_copies = st.number_input("Number of Copies", 
                                            min_value=0, 
                                            value=current_data.get('num_copies', 0) if current_data.get('num_copies') is not None else 0, 
                                            key=f"num_copies_{book_id}")
            else:
                print_by = current_data.get('print_by', "")
                print_cost = str(current_data.get('print_cost', 0.0)) if current_data.get('print_cost') is not None else ""
                book_mrp = str(current_data.get('book_mrp', 0.0)) if current_data.get('book_mrp') is not None else ""
                book_pages = str(current_data.get('book_pages', 0)) if current_data.get('book_pages') is not None else ""
                book_size = current_data.get('book_size', None)
                print_type = current_data.get('print_type', None)
                binding = current_data.get('binding', None)
                num_copies = current_data.get('num_copies', 0) if current_data.get('num_copies') is not None else 0
            
            if st.form_submit_button("💾 Save Inventory", use_container_width=True):
                updates = {
                    "ready_to_print": ready_to_print,
                    "print_status": print_status,
                    "print_by": print_by if print_by else None,
                    "print_cost": float(print_cost) if print_cost else None,
                    "book_mrp": float(book_mrp) if book_mrp else None,
                    "book_pages": int(book_pages) if book_pages else None,
                    "book_size": book_size if print_status else None,
                    "print_type": print_type if print_status else None,
                    "binding": binding if print_status else None,
                    "num_copies": int(num_copies) if num_copies else None
                }
                update_inventory_delivery_details(book_id, updates)
                st.success("✅ Updated Inventory details")

    # Delivery Tab
    with tab2:
        with st.form(key=f"delivery_form_{book_id}", border=False):
            # Checkbox at the top (full width)
            deliver = st.checkbox("Delivered?", 
                                value=current_data.get('deliver', False), 
                                key=f"deliver_{book_id}")
            
            if deliver:

                deliver_date = st.date_input("Delivery Date", 
                                            value=current_data.get('deliver_date', None), 
                                            key=f"deliver_date_{book_id}")
                # Create two columns for the input fields
                col1, col2 = st.columns(2)
                
                with col1:
                    
                    tracking_id = st.text_input("Tracking ID", 
                                            value=current_data.get('tracking_id', ""), 
                                            key=f"tracking_id_{book_id}")
                    amazon_link = st.text_input("Amazon Link", 
                                            value=current_data.get('amazon_link', ""), 
                                            key=f"amazon_link_{book_id}")
                    flipkart_link = st.text_input("Flipkart Link", 
                                                value=current_data.get('flipkart_link', ""), 
                                                key=f"flipkart_link_{book_id}")
                
                with col2:
                    google_link = st.text_input("Google Link", 
                                            value=current_data.get('google_link', ""), 
                                            key=f"google_link_{book_id}")
                    agph_link = st.text_input("AGPH Link", 
                                            value=current_data.get('agph_link', ""), 
                                            key=f"agph_link_{book_id}")
                    google_review = st.text_input("Google Review", 
                                                value=current_data.get('google_review', ""), 
                                                key=f"google_review_{book_id}")
            else:
                deliver_date = current_data.get('deliver_date', None)
                tracking_id = current_data.get('tracking_id', "")
                amazon_link = current_data.get('amazon_link', "")
                flipkart_link = current_data.get('flipkart_link', "")
                google_link = current_data.get('google_link', "")
                agph_link = current_data.get('agph_link', "")
                google_review = current_data.get('google_review', "")
            
            if st.form_submit_button("💾 Save Delivery", use_container_width=True):
                updates = {
                    "deliver": deliver,
                    "deliver_date": deliver_date,
                    "tracking_id": tracking_id if tracking_id else None,
                    "amazon_link": amazon_link if amazon_link else None,
                    "flipkart_link": flipkart_link if flipkart_link else None,
                    "google_link": google_link if google_link else None,
                    "agph_link": agph_link if agph_link else None,
                    "google_review": google_review if google_review else None
                }
                update_inventory_delivery_details(book_id, updates)
                st.success("✅ Updated Delivery details")

def update_inventory_delivery_details(book_id, updates):
    """Update inventory and delivery details in the books table."""
    set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
    query = f"UPDATE books SET {set_clause} WHERE book_id = :id"
    params = updates.copy()
    params["id"] = int(book_id)  # Ensure book_id is an integer
    with conn.session as session:
        session.execute(text(query), params)
        session.commit()
    st.cache_data.clear()

###################################################################################################################################
##################################--------------- Edit ISBN Dialog ----------------------------##################################
###################################################################################################################################

# Separate function for ISBN dialog using @st.dialog
@st.dialog("Manage ISBN")
def manage_isbn_dialog(book_id, current_apply_isbn, current_isbn):
    apply_isbn = st.checkbox("ISBN Applied?", value=bool(current_apply_isbn), key=f"apply_{book_id}")
    receive_isbn = st.checkbox("ISBN Received?", value=bool(pd.notna(current_isbn)), key=f"receive_{book_id}", disabled=not apply_isbn)
    
    if apply_isbn and receive_isbn:
        new_isbn = st.text_input("Enter ISBN", value=current_isbn if pd.notna(current_isbn) else "", key=f"isbn_input_{book_id}")
    else:
        new_isbn = None

    if st.button("Save ISBN", key=f"save_isbn_{book_id}"):
        with conn.session as s:
            if apply_isbn and receive_isbn and new_isbn:
                s.execute(
                    text("UPDATE books SET apply_isbn = :apply_isbn, isbn = :isbn WHERE book_id = :book_id"),
                    {"apply_isbn": 1, "isbn": new_isbn, "book_id": book_id}
                )
            elif apply_isbn and not receive_isbn:
                s.execute(
                    text("UPDATE books SET apply_isbn = :apply_isbn, isbn = NULL WHERE book_id = :book_id"),
                    {"apply_isbn": 1, "book_id": book_id}
                )
            else:
                s.execute(
                    text("UPDATE books SET apply_isbn = :apply_isbn, isbn = NULL WHERE book_id = :book_id"),
                    {"apply_isbn": 0, "book_id": book_id}
                )
            s.commit()
        st.success("ISBN Updated Successfully")
        st.rerun()


###################################################################################################################################
##################################--------------- Edit Price Dialog ----------------------------##################################
###################################################################################################################################


# New Price dialog
@st.dialog("Manage Book Price and Author Payments", width="large")
def manage_price_dialog(book_id, current_price):

    # Fetch book details for title
    book_details = fetch_book_details(book_id)
    book_title = book_details.iloc[0]['title'] if not book_details.empty else "Unknown Title"
    st.markdown(f"## {book_id} : {book_title}")

    # CSS for payment status styling
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
        </style>
    """, unsafe_allow_html=True)

    # Section 1: Book Price
    st.markdown("### 📖 Book Price")
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

    st.markdown("#### Payment Status Overview")
    st.markdown("""
        <style>
        .payment-overview {
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }
        .payment-overview h4 {
            color: #333;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .author-card {
            background-color: #fff;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            border-left: 5px solid;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        .status-paid {
            color: #28a745;
            font-weight: bold;
        }
        .status-partial {
            color: #ffc107;
            font-weight: bold;
        }
        .status-pending {
            color: #dc3545;
            font-weight: bold;
        }
        .author-card.status-paid {
            border-left-color: #28a745;
        }
        .author-card.status-partial {
            border-left-color: #ffc107;
        }
        .author-card.status-pending {
            border-left-color: #dc3545;
        }
        .payment-details {
            font-size: 0.9em;
            color: #666;
            margin-top: 10px;
        }
        .progress-bar {
            background-color: #e9ecef;
            border-radius: 5px;
            height: 10px;
            margin-top: 10px;
        }
        .progress-fill {
            height: 100%;
            border-radius: 5px;
        }
        .progress-fill.status-paid {
            background-color: #28a745;
        }
        .progress-fill.status-partial {
            background-color: #ffc107;
        }
        .progress-fill.status-pending {
            background-color: #dc3545;
        }
        </style>
    """, unsafe_allow_html=True)
    
    book_authors = fetch_book_authors(book_id)
    if book_authors.empty:
        st.warning(f"No authors found for Book ID: {book_id}")
    else:
        with st.container():
            st.markdown('<div class="payment-overview">', unsafe_allow_html=True)
            for _, row in book_authors.iterrows():
                total_amount = int(row.get('total_amount', 0) or 0)
                emi1 = int(row.get('emi1', 0) or 0)
                emi2 = int(row.get('emi2', 0) or 0)
                emi3 = int(row.get('emi3', 0) or 0)
                amount_paid = emi1 + emi2 + emi3

                # Determine payment status
                if amount_paid >= total_amount and total_amount > 0:
                    status = 'status-paid'
                    status_text = 'Fully Paid'
                elif amount_paid > 0:
                    status = 'status-partial'
                    status_text = 'Partially Paid'
                else:
                    status = 'status-pending'
                    status_text = 'Pending'

                # Calculate payment progress percentage
                progress_percentage = min((amount_paid / total_amount) * 100, 100) if total_amount > 0 else 0

                # Display author payment details in a card-like structure
                st.markdown(
                    f"""
                    <div class="author-card {status}">
                        <div>
                            <strong>{row['name']}</strong> (ID: {row['author_id']} - {row['author_position']})
                            <span class="payment-status {status}">&nbsp;&nbsp;• {status_text}</span>
                        </div>
                        <div class="payment-details">
                            Total Amount: ₹{total_amount} | Paid: ₹{amount_paid} 
                            (EMI 1: ₹{emi1}, EMI 2: ₹{emi2}, EMI 3: ₹{emi3})
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill {status}" style="width: {progress_percentage}%"></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            st.markdown('</div>', unsafe_allow_html=True)

    # Section 2: Author Payments with Tabs
    st.markdown("### 👤 Author Payments")
    if not book_authors.empty:
        total_author_amounts = 0
        updated_authors = []

        # Create tabs for each author
        tab_titles = [f"{row['name']} (ID: {row['author_id']})" for _, row in book_authors.iterrows()]
        tabs = st.tabs(tab_titles)

        for tab, (_, row) in zip(tabs, book_authors.iterrows()):
            with tab:
                # Fetch existing payment details
                total_amount = int(row.get('total_amount', 0) or 0)
                emi1 = int(row.get('emi1', 0) or 0)
                emi2 = int(row.get('emi2', 0) or 0)
                emi3 = int(row.get('emi3', 0) or 0)
                emi1_date = row.get('emi1_date', None)
                emi2_date = row.get('emi2_date', None)
                emi3_date = row.get('emi3_date', None)
                amount_paid = emi1 + emi2 + emi3

                # Payment status inside tab
                if amount_paid >= total_amount and total_amount > 0:
                    status = '<span class="payment-status status-paid">Fully Paid</span>'
                elif amount_paid > 0:
                    status = '<span class="payment-status status-partial">Partially Paid</span>'
                else:
                    status = '<span class="payment-status status-pending">Pending</span>'
                st.markdown(f"**Payment Status:** {status}", unsafe_allow_html=True)

                # Total Amount Due
                total_str = st.text_input(
                    "Total Amount Due (₹)",
                    value=str(total_amount) if total_amount > 0 else "",
                    key=f"total_{row['id']}",
                    placeholder="Enter whole amount"
                )

                # EMI Payments with Dates
                st.markdown("#### EMI Details")
                col1, col2 = st.columns(2)
                
                with col1:
                    emi1_str = st.text_input(
                        "EMI 1 Amount (₹)",
                        value=str(emi1) if emi1 > 0 else "",
                        key=f"emi1_{row['id']}"
                    )
                    emi2_str = st.text_input(
                        "EMI 2 Amount (₹)",
                        value=str(emi2) if emi2 > 0 else "",
                        key=f"emi2_{row['id']}"
                    )
                    emi3_str = st.text_input(
                        "EMI 3 Amount (₹)",
                        value=str(emi3) if emi3 > 0 else "",
                        key=f"emi3_{row['id']}"
                    )
                
                with col2:
                    emi1_date_new = st.date_input(
                        "EMI 1 Date",
                        value=pd.to_datetime(emi1_date) if emi1_date else None,
                        key=f"emi1_date_{row['id']}"
                    )
                    emi2_date_new = st.date_input(
                        "EMI 2 Date",
                        value=pd.to_datetime(emi2_date) if emi2_date else None,
                        key=f"emi2_date_{row['id']}"
                    )
                    emi3_date_new = st.date_input(
                        "EMI 3 Date",
                        value=pd.to_datetime(emi3_date) if emi3_date else None,
                        key=f"emi3_date_{row['id']}"
                    )

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
                                          emi1_date_new, emi2_date_new, emi3_date_new))
                except ValueError:
                    st.error("Please enter valid whole numbers for all fields")
                    return

                st.markdown(f"**Total Paid:** ₹{new_paid} | **Remaining Balance:** ₹{remaining}")

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
                            "emi3_date": emi3_date_new
                        }
                        update_book_authors(row['id'], updates)
                        st.success(f"Payment updated for {row['name']}")
                        st.cache_data.clear()
                        st.rerun()



@st.dialog("Ok")
def write_on_me():
    st.write("You clicked the button!")


###################################################################################################################################
##################################--------------- Book Table ----------------------------##################################
###################################################################################################################################

# Group books by month
grouped_books = books.groupby(pd.Grouper(key='date', freq='ME'))

# Reverse the order of grouped months
reversed_grouped_books = reversed(list(grouped_books))

# Query to get author count per book
author_count_query = """
    SELECT book_id, COUNT(author_id) as author_count
    FROM book_authors
    GROUP BY book_id
"""
author_counts = conn.query(author_count_query)
# Convert to dictionary for easy lookup
author_count_dict = dict(zip(author_counts['book_id'], author_counts['author_count']))

# Custom CSS for modern table styling
st.markdown("""
    <style>
            
        /* Remove Streamlit's default top padding */
        .main > div {
            padding-top: 0px !important;
        }
        /* Ensure the first element has minimal spacing */
        .block-container {
            padding-top: 42px !important;  /* Small padding for breathing room */
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
            
    </style>
""", unsafe_allow_html=True)

col1,col2 = st.columns([9, 1])

with col1:
    st.markdown("## 📚 Book List")
with col2:
    if st.button("Add Book", type = "tertiary"):
        add_book_dialog()

column_size = [1, 4, 1, 1, 1,2] 

#st.markdown("## 📚 Book List")
cont = st.container(border=False)
with cont:
    if books.empty:
        st.warning("No books available.")
    else:
        # Table Header
        header_col1, header_col2, header_col3, header_col4, header_col5, header_col6 = st.columns(column_size)
        with header_col1: st.markdown("###### ID")
        with header_col2: st.markdown("###### Title")
        with header_col3: st.markdown("###### Date")
        with header_col4: st.markdown("###### ISBN")
        with header_col5: st.markdown("###### Status")
        with header_col6: st.markdown("###### Actions")

        # Table Body
        for month, monthly_books in reversed_grouped_books:
            st.markdown(f'<div class="month-header"><b>{month.strftime("%B %Y")}</b></div>', unsafe_allow_html=True)
            for _, row in monthly_books.iterrows():
                st.markdown('<div class="data-row">', unsafe_allow_html=True)
                col1, col2, col3, col4, col5, col6 = st.columns(column_size)
                with col1: st.write(row['book_id'])
                with col2: 
                    author_count = author_count_dict.get(row['book_id'], 0)
                    st.markdown(
                        f"{row['title']} <span style='color: #2aba25; font-size:14px; margin-left: 5px; background-color: #f7f7f7; padding: 1px 4px; border-radius: 10px;'>{author_count}</span>",
                        unsafe_allow_html=True
                    )
                with col3: st.write(row['date'].strftime('%Y-%m-%d'))
                with col4: st.markdown(get_isbn_display(row["isbn"], row["apply_isbn"]), unsafe_allow_html=True)
                with col5: st.markdown(get_status_pill(row["deliver"]), unsafe_allow_html=True)
                with col6:
                    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns([1, 1, 1, 1, 1])
                    with btn_col1:
                        if st.button(":material/edit_document:", key=f"isbn_{row['book_id']}"):
                            manage_isbn_dialog(row['book_id'], row['apply_isbn'], row['isbn'])
                    with btn_col2:
                        if st.button(":material/currency_rupee:", key=f"price_btn_{row['book_id']}"):
                            manage_price_dialog(row['book_id'], row['price'])
                    with btn_col3:
                        if st.button(":material/manage_accounts:", key=f"edit_author_{row['book_id']}"):
                            edit_author_dialog(row['book_id'])
                    with btn_col4:
                        if st.button(":material/manufacturing:", key=f"ops_{row['book_id']}"):
                            edit_operation_dialog(row['book_id'])
                    with btn_col5:
                        if st.button(":material/local_shipping:", key=f"delivery_{row['book_id']}"):
                            edit_inventory_delivery_dialog(row['book_id'])
                
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


# def example():
#     rain(
#         emoji="🎈",
#         font_size=50,
#         falling_speed=2,
#         animation_length="infinite",
#     )

# example()