import streamlit as st
import pandas as pd
from sqlalchemy import text  # Import text for raw SQL queries
from datetime import date
from admin import author_details_section

st.cache_data.clear()

# Connect to MySQL
conn = st.connection("mysql", type="sql")

# Fetch books from the database
query = "SELECT book_id, title, date, isbn, apply_isbn, deliver FROM books"
books = conn.query(query)

# Convert 'date' column to datetime objects if it's not already
if not pd.api.types.is_datetime64_any_dtype(books['date']):
    books['date'] = pd.to_datetime(books['date'])

def get_isbn_display(isbn, apply_isbn):
    if pd.notna(isbn):
        return f"**<span style='color:#47b354;'>{isbn}</span>**"  # Gray for valid ISBN
    elif apply_isbn == 0:
        return f"**<span style='color:#5c3c3b;'>Not Applied</span>**"  # Red for Not Applied
    elif apply_isbn == 1:
        return f"**<span style='color:#e0ab19;'>Not Received</span>**"  # Orange for Not Received
    return f"**:<span style='color:#000000;'>-</span>**"  # Black for default/unknown case

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
    params["id"] = int(id) 
    with conn.session as session:  
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
            margin-bottom: 10px; 
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1); 
        }
        .stTextInput>div>div>input, .stSelectbox>div>div>select {
            border-radius: 5px;
            padding: 6px;
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
                            "printing_confirmation": int(printing_confirmation)
                        }
                        update_book_authors(row['id'], updates)
                        st.cache_data.clear()
                        st.success(f"✅ Updated details for {row['name']} (Author ID: {row['author_id']})")

    # Local state for new authors
    if "local_authors" not in st.session_state:
        st.session_state.local_authors = [{"name": "", "email": "", "phone": "", "author_id": None}]

    def add_local_author():
        st.session_state.local_authors.append({"name": "", "email": "", "phone": "", "author_id": None})

    def remove_local_author(index):
        del st.session_state.local_authors[index]

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

    st.markdown("### Add New Author")

    with st.container(border=True):
        st.markdown("<h5>Author Details", unsafe_allow_html=True)
        for i, author in enumerate(st.session_state.local_authors):
            with st.container():
                col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 2, 2, 2, 1])

                author_name_input_key = f"local_author_name_{i}"
                author_name = col1.text_input(f"Author Name {i+1}", author["name"], key=author_name_input_key, placeholder='Enter Author name..')

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
                    key=f"local_author_suggestion_{i}",
                    label_visibility="hidden",
                    disabled=disabled_suggestion,
                    placeholder=suggestion_placeholder
                )

                if selected_suggestion and selected_suggestion != "No authors found":
                    if "(ID: " in selected_suggestion:
                        selected_author_id = int(selected_suggestion.split('(ID: ')[1][:-1])
                        selected_author = next((a for a in suggestions if a.author_id == selected_author_id), None)
                        if selected_author:
                            st.session_state.local_authors[i]["name"] = selected_author.name
                            st.session_state.local_authors[i]["email"] = selected_author.email
                            st.session_state.local_authors[i]["phone"] = selected_author.phone
                            st.session_state.local_authors[i]["author_id"] = selected_author.author_id
                else:
                    st.session_state.local_authors[i]["name"] = author_name

                st.session_state.local_authors[i]["email"] = col3.text_input(f"Email {i+1}", author["email"])
                st.session_state.local_authors[i]["phone"] = col4.text_input(f"Phone {i+1}", author["phone"])
                selected_position = col5.selectbox(
                    f"Position {i+1}",
                    ["1st", "2nd", "3rd", "4th"],
                    key=f"local_author_position_{i}"
                )
                st.session_state.local_authors[i]["author_position"] = selected_position
                if col6.button(":material/close:", key=f"remove_local_{i}", type="tertiary"):
                    remove_local_author(i)
                    st.rerun() # Refresh the dialog to show the new authors.

        if st.button(":material/add:"):
            add_local_author()
            st.rerun() # Refresh the dialog to show the new authors.

    if st.button("Add New Authors to Book"):
        for author in st.session_state.local_authors:
            if author["name"] and author["email"] and author["phone"]:
                author_id_to_link = author["author_id"] or insert_author(conn, author["name"], author["email"], author["phone"])
                if book_id and author_id_to_link:
                    with conn.session as s:
                        s.execute(text("""INSERT INTO book_authors (book_id, author_id, author_position) VALUES (:book_id, :author_id, :author_position)"""), params={"book_id": book_id, "author_id": author_id_to_link, "author_position": author["author_position"]})
                        s.commit()
        st.cache_data.clear()
        st.success("New Authors added successfully")
        st.session_state.local_authors = [{"name": "", "email": "", "phone": "", "author_id": None}] #reset local author state.
        st.rerun()

def insert_author(conn, name, email, phone):
    with conn.session as s:
        s.execute(text("""INSERT INTO authors (name, email, phone) VALUES (:name, :email, :phone) ON DUPLICATE KEY UPDATE name=name"""), params={"name": name, "email": email, "phone": phone})
        s.commit()
        return s.execute(text("SELECT LAST_INSERT_ID();")).scalar()

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
            writing_start_date = st.date_input("Start Date", value=current_data.get('writing_start', None), key=f"writing_start_date_{book_id}")
            writing_start_time = st.time_input("Start Time", value=current_data.get('writing_start', None), key=f"writing_start_time_{book_id}")
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
            proofreading_start_date = st.date_input("Start Date", value=current_data.get('proofreading_start', None), key=f"proofreading_start_date_{book_id}")
            proofreading_start_time = st.time_input("Start Time", value=current_data.get('proofreading_start', None), key=f"proofreading_start_time_{book_id}")
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
            formatting_start_date = st.date_input("Start Date", value=current_data.get('formatting_start', None), key=f"formatting_start_date_{book_id}")
            formatting_start_time = st.time_input("Start Time", value=current_data.get('formatting_start', None), key=f"formatting_start_time_{book_id}")
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
                front_cover_start_date = st.date_input("Front Start Date", value=current_data.get('front_cover_start', None), key=f"front_cover_start_date_{book_id}")
                front_cover_start_time = st.time_input("Front Start Time", value=current_data.get('front_cover_start', None), key=f"front_cover_start_time_{book_id}")
                front_cover_end_date = st.date_input("Front End Date", value=current_data.get('front_cover_end', None), key=f"front_cover_end_date_{book_id}")
                front_cover_end_time = st.time_input("Front End Time", value=current_data.get('front_cover_end', None), key=f"front_cover_end_time_{book_id}")
                front_submit = st.form_submit_button("💾 Save Front Cover", use_container_width=True)

        with st.expander("📚 Back Cover Details", expanded=False):
            # Back Cover Section
            st.subheader("Back Cover")
            with st.form(key=f"back_cover_form_{book_id}", border=False):
                back_cover_by = st.text_input("Back Cover By", value=current_data.get('back_cover_by', ""), key=f"back_cover_by_{book_id}")
                back_cover_start_date = st.date_input("Back Start Date", value=current_data.get('back_cover_start', None), key=f"back_cover_start_date_{book_id}")
                back_cover_start_time = st.time_input("Back Start Time", value=current_data.get('back_cover_start', None), key=f"back_cover_start_time_{book_id}")
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
                # Create two columns for the input fields
                col1, col2 = st.columns(2)
                
                with col1:
                    deliver_date = st.date_input("Delivery Date", 
                                            value=current_data.get('deliver_date', None), 
                                            key=f"deliver_date_{book_id}")
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

# Display books
st.markdown("## 📚 Book List")
cont = st.container(border = True)
with cont:

    if books.empty:
        st.warning("No books available.")
    else:
        # Table Header
        with st.container():
            header_col1, header_col2, header_col3, header_col4, header_col5, header_col6, header_col7 = st.columns([1, 3, 2, 2, 1, 2, 3])
            with header_col1:
                st.markdown("**ID**")
            with header_col2:
                st.markdown("**Title**")
            with header_col3:
                st.markdown("**Date**")
            with header_col4:
                st.markdown("**ISBN**")
            with header_col5:
                st.markdown("**Authors**")
            with header_col6:
                st.markdown("**Status**")
            with header_col7:
                st.markdown("**Actions**")

        for month, monthly_books in reversed_grouped_books:
            st.markdown(f"##### {month.strftime('%B %Y')}")
            for _, row in monthly_books.iterrows():
                col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 3, 2, 2, 1, 2, 3])
                
                with col1:
                    st.write(row['book_id'])
                with col2:
                    st.write(row['title'])
                with col3:
                    st.write(row['date'].strftime('%Y-%m-%d'))
                with col4:
                    st.markdown(get_isbn_display(row["isbn"], row["apply_isbn"]), unsafe_allow_html=True)
                with col5:
                    author_count = author_count_dict.get(row['book_id'], 0)  
                    st.write(f"{author_count}")
                with col6:
                    st.markdown(get_status_pill(row["deliver"]), unsafe_allow_html=True) 
                with col7:
                    # Reordered buttons: ISBN first, View last
                    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
                    with btn_col1:
                        if st.button(":material/edit_document:", key=f"isbn_{row['book_id']}"):
                            manage_isbn_dialog(row['book_id'], row['apply_isbn'], row['isbn'])
                    with btn_col2:
                        if st.button(":material/manage_accounts:", key=f"edit_author_{row['book_id']}"):
                            edit_author_dialog(row['book_id']) 
                    with btn_col3:
                        if st.button(":material/edit_note:", key=f"edit_ops_{row['book_id']}"):
                           edit_operation_dialog(row['book_id'])
                    with btn_col4:
                        if st.button(":material/local_shipping:", key=f"view_{row['book_id']}"):
                            edit_inventory_delivery_dialog(row['book_id'])

            st.markdown("---")