import streamlit as st
import pandas as pd
from sqlalchemy import text  # Import text for raw SQL queries
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
        return f"**<span style='color:#6b6621;'>Not Received</span>**"  # Orange for Not Received
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
                        if st.button(":material/manufacturing:", key=f"edit_ops_{row['book_id']}"):
                            st.write(f"Editing operations for book {row['book_id']} (implement edit logic here)")
                    with btn_col4:
                        if st.button(":material/visibility:", key=f"view_{row['book_id']}"):
                            st.write(f"Viewing book {row['book_id']} (implement view logic here)")

            st.markdown("---")