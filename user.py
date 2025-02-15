import streamlit as st
import pandas as pd
import datetime

# Initialize session state for authors
if 'authors' not in st.session_state:
    st.session_state.authors = {}
if 'book_data' not in st.session_state:
    st.session_state.book_data = []

st.title("Book Data Entry")

# Book Details Input
st.subheader("Book Details")
book_id = st.text_input("Book ID")
book_title = st.text_input("Book Title")
date = st.date_input("Date", datetime.date.today())
apply_isbn = st.checkbox("Apply ISBN")
isbn = st.text_input("ISBN", disabled=not apply_isbn)  # Disable if Apply ISBN is not checked
send_cover_page = st.checkbox("Send Cover Page and Agreement")
agreement_received = st.checkbox("Agreement Received")
digital_prof = st.checkbox("Digital Prof")
plagiarism_report = st.checkbox("Plagiarism Report")
confirmation = st.checkbox("Confirmation")
ready_to_print = st.checkbox("Ready to Print")
print_book = st.checkbox("Print")
deliver = st.checkbox("Deliver")
amazon_link = st.text_input("Amazon Link")
agph_link = st.text_input("AGPH Link")
google_link = st.text_input("Google Link")
flipkart_link = st.text_input("Flipkart Link")


# Author Details Input (Dynamic)
st.subheader("Author Details")

author_count = st.number_input("Number of Authors", min_value=1, step=1, value=1)

for i in range(author_count):
    st.subheader(f"Author {i+1}")
    author_id = st.text_input(f"Author ID {i+1}")
    author_name = st.text_input(f"Author Name {i+1}")
    position = st.text_input(f"Position {i+1}")
    email = st.text_input(f"Email {i+1}")
    contact = st.text_input(f"Contact {i+1}")

    st.session_state.authors[f"author_{i+1}"] = {
        'Author Id': author_id,
        'Author Name': author_name,
        'Position': position,
        'Email': email,
        'Contact': contact
    }

# Save Data
if st.button("Save Book Data"):
    book_data = {
        'Book ID': book_id,
        'Book Title': book_title,
        'Date': date.strftime("%Y-%m-%d"), # Format date for storage
        'Apply ISBN': apply_isbn,
        'ISBN': isbn,
        'Send Cover Page and Agreement': send_cover_page,
        'Agreement Received': agreement_received,
        'Digital Prof': digital_prof,
        'Plagiarism Report': plagiarism_report,
        'Confirmation': confirmation,
        'Ready to Print': ready_to_print,
        'Print': print_book,
        'Deliver': deliver,
        'Amazon Link': amazon_link,
        'AGPH Link': agph_link,
        'Google Link': google_link,
        'Flipkart Link': flipkart_link,
    }

    # Add author data to the book data
    for author_key, author_details in st.session_state.authors.items():
        book_data.update({f"{author_key}_{key}": value for key, value in author_details.items()})

    st.session_state.book_data.append(book_data) # Append to the list of dictionaries
    st.success("Book data saved successfully!")

# Display Saved Data (Optional)
if st.button("Display Saved Data"):
    if st.session_state.book_data:
        df = pd.DataFrame(st.session_state.book_data)
        st.dataframe(df)  # or st.table(df) for a static table
    else:
        st.info("No book data saved yet.")

# Download Data as CSV
if st.session_state.book_data:
    df = pd.DataFrame(st.session_state.book_data)
    csv = df.to_csv(index=False).encode('utf-8')

    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name='book_data.csv',
        mime='text/csv',
    )