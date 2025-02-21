import streamlit as st
import pandas as pd

# Connect to MySQL
conn = st.connection("mysql", type="sql")

# Function to fetch author details for a given book_id
def fetch_authors_for_book(book_id):
    query = """
    SELECT 
        a.author_id, a.name, a.email, a.phone,
        ba.author_position, ba.welcome_mail_sent, ba.corresponding_agent, ba.publishing_consultant,
        ba.photo_recive, ba.id_proof_recive, ba.author_details_sent, ba.cover_agreement_sent,
        ba.agreement_received, ba.digital_book_sent, ba.digital_book_approved, ba.plagiarism_report,
        ba.printing_confirmation
    FROM authors a
    JOIN book_authors ba ON a.author_id = ba.author_id
    WHERE ba.book_id = :book_id
    """
    authors_data = conn.query(query, params={"book_id": book_id})
    return authors_data

# Function to update author details in the database
def update_author_details(author_id, book_id, updated_data):
    # Update authors table
    authors_query = """
    UPDATE authors
    SET name = :name, email = :email, phone = :phone
    WHERE author_id = :author_id
    """
    conn.session.execute(authors_query, {
        "author_id": author_id,
        "name": updated_data["name"],
        "email": updated_data["email"],
        "phone": updated_data["phone"]
    })

    # Update book_authors table
    book_authors_query = """
    UPDATE book_authors
    SET author_position = :author_position, welcome_mail_sent = :welcome_mail_sent,
        corresponding_agent = :corresponding_agent, publishing_consultant = :publishing_consultant,
        photo_recive = :photo_recive, id_proof_recive = :id_proof_recive,
        author_details_sent = :author_details_sent, cover_agreement_sent = :cover_agreement_sent,
        agreement_received = :agreement_received, digital_book_sent = :digital_book_sent,
        digital_book_approved = :digital_book_approved, plagiarism_report = :plagiarism_report,
        printing_confirmation = :printing_confirmation
    WHERE book_id = :book_id AND author_id = :author_id
    """
    conn.session.execute(book_authors_query, {
        "book_id": book_id,
        "author_id": author_id,
        **updated_data
    })
    conn.session.commit()

# Edit Author Page
def edit_author_page():
    # Get book_id from URL or query parameter (assuming passed via URL like '/edit_author/{book_id}')
    book_id = st.query_params.get("book_id", None)  # Adjust based on your routing method
    if not book_id:
        st.error("No book ID provided.")
        return

    st.markdown(f"## Edit Author Details for Book ID: {book_id}")

    # Fetch authors associated with the book
    authors_data = fetch_authors_for_book(book_id)

    if authors_data.empty:
        st.warning("No authors found for this book.")
        return

    # Display form for each author
    for index, row in authors_data.iterrows():
        st.markdown(f"### Author {index + 1} (ID: {row['author_id']})")
        with st.form(key=f"author_form_{row['author_id']}"):
            # Fields from authors table
            name = st.text_input("Name", value=row["name"], key=f"name_{row['author_id']}")
            email = st.text_input("Email", value=row["email"], key=f"email_{row['author_id']}")
            phone = st.text_input("Phone", value=row["phone"], key=f"phone_{row['author_id']}")

            # Fields from book_authors table
            author_position = st.number_input("Author Position", min_value=1, max_value=4, value=row["author_position"] or 1, key=f"pos_{row['author_id']}")
            welcome_mail_sent = st.checkbox("Welcome Mail Sent", value=bool(row["welcome_mail_sent"]), key=f"welcome_{row['author_id']}")
            corresponding_agent = st.text_input("Corresponding Agent", value=row["corresponding_agent"] or "", key=f"agent_{row['author_id']}")
            publishing_consultant = st.text_input("Publishing Consultant", value=row["publishing_consultant"] or "", key=f"consultant_{row['author_id']}")
            photo_recive = st.checkbox("Photo Received", value=bool(row["photo_recive"]), key=f"photo_{row['author_id']}")
            id_proof_recive = st.checkbox("ID Proof Received", value=bool(row["id_proof_recive"]), key=f"id_{row['author_id']}")
            author_details_sent = st.checkbox("Author Details Sent", value=bool(row["author_details_sent"]), key=f"details_{row['author_id']}")
            cover_agreement_sent = st.checkbox("Cover Agreement Sent", value=bool(row["cover_agreement_sent"]), key=f"cover_{row['author_id']}")
            agreement_received = st.checkbox("Agreement Received", value=bool(row["agreement_received"]), key=f"agreement_{row['author_id']}")
            digital_book_sent = st.checkbox("Digital Book Sent", value=bool(row["digital_book_sent"]), key=f"digital_sent_{row['author_id']}")
            digital_book_approved = st.checkbox("Digital Book Approved", value=bool(row["digital_book_approved"]), key=f"digital_approved_{row['author_id']}")
            plagiarism_report = st.checkbox("Plagiarism Report", value=bool(row["plagiarism_report"]), key=f"plagiarism_{row['author_id']}")
            printing_confirmation = st.checkbox("Printing Confirmation", value=bool(row["printing_confirmation"]), key=f"printing_{row['author_id']}")

            # Submit button for this author's form
            submit_button = st.form_submit_button(label="Save Changes")

            if submit_button:
                updated_data = {
                    "name": name,
                    "email": email,
                    "phone": phone,
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
                update_author_details(row["author_id"], book_id, updated_data)
                st.success(f"Updated details for Author ID: {row['author_id']}")

# Run the page
if __name__ == "__main__":
    edit_author_page()