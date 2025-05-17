import streamlit as st
import pandas as pd
from auth import validate_token

logo = "logo/logo_black.png"
fevicon = "logo/favicon_black.ico"
small_logo = "logo/favicon_white.ico"

st.set_page_config(page_title='AGPH Search', page_icon="🔍", layout="wide")

st.logo(logo,
size = "large",
icon_image = small_logo
)

# Inject CSS to remove the menu (optional)
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_menu_style, unsafe_allow_html=True)

validate_token()

user_role = st.session_state.get("role", None)
user_app = st.session_state.get("app", None)
user_access = st.session_state.get("access", None)


if user_role != 'admin' and not (
    user_role == 'user' and 
    user_app == 'main' and 
    'Advance Search' in user_access 
):
    st.error("⚠️ Access Denied: You don't have permission to access this page.")
    st.stop()

# Initialize session state for new visitors
if "visited" not in st.session_state:
    st.session_state.visited = False

# Check if the user is new
if not st.session_state.visited:
    st.cache_data.clear()  # Clear cache for new visitors
    st.session_state.visited = True  # Mark as visited


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

# SQL query to consolidate book data with updated conditions
query = """
WITH RankedAuthors AS (
    SELECT 
        ba.*,
        ROW_NUMBER() OVER (PARTITION BY ba.book_id ORDER BY ba.author_position, ba.id) AS rn
    FROM book_authors ba
)
SELECT 
    b.book_id AS `Book ID`,
    b.title AS `Book Title`,
    b.date AS `Date`,
    COUNT(ba.author_id) AS `No of Author`,
    MAX(CASE WHEN rn = 1 THEN ba.author_id END) AS `Author Id 1`,
    MAX(CASE WHEN rn = 2 THEN ba.author_id END) AS `Author Id 2`,
    MAX(CASE WHEN rn = 3 THEN ba.author_id END) AS `Author Id 3`,
    MAX(CASE WHEN rn = 4 THEN ba.author_id END) AS `Author Id 4`,
    MAX(CASE WHEN rn = 1 THEN a.name END) AS `Author Name 1`,
    MAX(CASE WHEN rn = 2 THEN a.name END) AS `Author Name 2`,
    MAX(CASE WHEN rn = 3 THEN a.name END) AS `Author Name 3`,
    MAX(CASE WHEN rn = 4 THEN a.name END) AS `Author Name 4`,
    MAX(CASE WHEN rn = 1 THEN ba.author_position END) AS `Position 1`,
    MAX(CASE WHEN rn = 2 THEN ba.author_position END) AS `Position 2`,
    MAX(CASE WHEN rn = 3 THEN ba.author_position END) AS `Position 3`,
    MAX(CASE WHEN rn = 4 THEN ba.author_position END) AS `Position 4`,
    MAX(CASE WHEN rn = 1 THEN ba.corresponding_agent END) AS `Corresponding Author/Agent 1`,
    MAX(CASE WHEN rn = 2 THEN ba.corresponding_agent END) AS `Corresponding Author/Agent 2`,
    MAX(CASE WHEN rn = 3 THEN ba.corresponding_agent END) AS `Corresponding Author/Agent 3`,
    MAX(CASE WHEN rn = 4 THEN ba.corresponding_agent END) AS `Corresponding Author/Agent 4`,
    MAX(CASE WHEN rn = 1 THEN ba.publishing_consultant END) AS `Publishing Consultant 1`,
    MAX(CASE WHEN rn = 2 THEN ba.publishing_consultant END) AS `Publishing Consultant 2`,
    MAX(CASE WHEN rn = 3 THEN ba.publishing_consultant END) AS `Publishing Consultant 3`,
    MAX(CASE WHEN rn = 4 THEN ba.publishing_consultant END) AS `Publishing Consultant 4`,
    MAX(CASE WHEN rn = 1 THEN a.email END) AS `Email Address 1`,
    MAX(CASE WHEN rn = 2 THEN a.email END) AS `Email Address 2`,
    MAX(CASE WHEN rn = 3 THEN a.email END) AS `Email Address 3`,
    MAX(CASE WHEN rn = 4 THEN a.email END) AS `Email Address 4`,
    MAX(CASE WHEN rn = 1 THEN a.phone END) AS `Contact No. 1`,
    MAX(CASE WHEN rn = 2 THEN a.phone END) AS `Contact No. 2`,
    MAX(CASE WHEN rn = 3 THEN a.phone END) AS `Contact No. 3`,
    MAX(CASE WHEN rn = 4 THEN a.phone END) AS `Contact No. 4`,
    CASE 
        WHEN b.writing_end IS NOT NULL 
        AND b.proofreading_end IS NOT NULL 
        AND b.formatting_end IS NOT NULL 
        THEN 'TRUE' 
        ELSE 'FALSE' 
    END AS `Book Complete`,
    CASE WHEN b.apply_isbn = 1 THEN 'TRUE' ELSE 'FALSE' END AS `Apply ISBN`,
    b.isbn AS `ISBN`,
    MAX(CASE WHEN ba.cover_agreement_sent = 1 THEN 'TRUE' ELSE 'FALSE' END) AS `Send Cover Page and Agreement`,
    MAX(CASE WHEN ba.agreement_received = 1 THEN 'TRUE' ELSE 'FALSE' END) AS `Agreement Received`,
    MAX(CASE WHEN ba.digital_book_approved = 1 THEN 'TRUE' ELSE 'FALSE' END) AS `Digital Prof`,
    MAX(CASE WHEN ba.printing_confirmation = 1 THEN 'TRUE' ELSE 'FALSE' END) AS `Confirmation`,
    MAX(CASE WHEN rn = 1 THEN CASE WHEN ba.welcome_mail_sent = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Welcome Mail / Confirmation 1`,
    MAX(CASE WHEN rn = 2 THEN CASE WHEN ba.welcome_mail_sent = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Welcome Mail / Confirmation 2`,
    MAX(CASE WHEN rn = 3 THEN CASE WHEN ba.welcome_mail_sent = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Welcome Mail / Confirmation 3`,
    MAX(CASE WHEN rn = 4 THEN CASE WHEN ba.welcome_mail_sent = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Welcome Mail / Confirmation 4`,
    MAX(CASE WHEN rn = 1 THEN CASE WHEN ba.author_details_sent = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Author Detail 1`,
    MAX(CASE WHEN rn = 2 THEN CASE WHEN ba.author_details_sent = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Author Detail 2`,
    MAX(CASE WHEN rn = 3 THEN CASE WHEN ba.author_details_sent = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Author Detail 3`,
    MAX(CASE WHEN rn = 4 THEN CASE WHEN ba.author_details_sent = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Author Detail 4`,
    MAX(CASE WHEN rn = 1 THEN CASE WHEN ba.photo_recive = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Photo 1`,
    MAX(CASE WHEN rn = 2 THEN CASE WHEN ba.photo_recive = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Photo 2`,
    MAX(CASE WHEN rn = 3 THEN CASE WHEN ba.photo_recive = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Photo 3`,
    MAX(CASE WHEN rn = 4 THEN CASE WHEN ba.photo_recive = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Photo 4`,
    MAX(CASE WHEN rn = 1 THEN CASE WHEN ba.id_proof_recive = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `ID Proof 1`,
    MAX(CASE WHEN rn = 2 THEN CASE WHEN ba.id_proof_recive = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `ID Proof 2`,
    MAX(CASE WHEN rn = 3 THEN CASE WHEN ba.id_proof_recive = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `ID Proof 3`,
    MAX(CASE WHEN rn = 4 THEN CASE WHEN ba.id_proof_recive = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `ID Proof 4`,
    b.cover_by AS `Cover Page`,
    NULL AS `Back Page Update`,
    MAX(CASE WHEN rn = 1 THEN CASE WHEN ba.cover_agreement_sent = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Send Cover Page and Agreement 1`,
    MAX(CASE WHEN rn = 2 THEN CASE WHEN ba.cover_agreement_sent = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Send Cover Page and Agreement 2`,
    MAX(CASE WHEN rn = 3 THEN CASE WHEN ba.cover_agreement_sent = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Send Cover Page and Agreement 3`,
    MAX(CASE WHEN rn = 4 THEN CASE WHEN ba.cover_agreement_sent = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Send Cover Page and Agreement 4`,
    MAX(CASE WHEN rn = 1 THEN CASE WHEN ba.agreement_received = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Agreement Received 1`,
    MAX(CASE WHEN rn = 2 THEN CASE WHEN ba.agreement_received = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Agreement Received 2`,
    MAX(CASE WHEN rn = 3 THEN CASE WHEN ba.agreement_received = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Agreement Received 3`,
    MAX(CASE WHEN rn = 4 THEN CASE WHEN ba.agreement_received = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Agreement Received 4`,
    MAX(CASE WHEN rn = 1 THEN CASE WHEN ba.digital_book_approved = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Digital Prof 1`,
    MAX(CASE WHEN rn = 2 THEN CASE WHEN ba.digital_book_approved = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Digital Prof 2`,
    MAX(CASE WHEN rn = 3 THEN CASE WHEN ba.digital_book_approved = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Digital Prof 3`,
    MAX(CASE WHEN rn = 4 THEN CASE WHEN ba.digital_book_approved = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Digital Prof 4`,
    MAX(CASE WHEN rn = 1 THEN CASE WHEN ba.printing_confirmation = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Confirmation 1`,
    MAX(CASE WHEN rn = 2 THEN CASE WHEN ba.printing_confirmation = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Confirmation 2`,
    MAX(CASE WHEN rn = 3 THEN CASE WHEN ba.printing_confirmation = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Confirmation 3`,
    MAX(CASE WHEN rn = 4 THEN CASE WHEN ba.printing_confirmation = 1 THEN 'TRUE' ELSE 'FALSE' END END) AS `Confirmation 4`,
    CASE WHEN b.ready_to_print = 1 THEN 'TRUE' ELSE 'FALSE' END AS `Ready to Print`,
    CASE WHEN b.print_status = 1 THEN 'TRUE' ELSE 'FALSE' END AS `Print`,
    b.amazon_link AS `Amazon Link`,
    b.agph_link AS `AGPH Link`,
    b.google_link AS `Google Link`,
    b.flipkart_link AS `Flipkart Link`,
    NULL AS `Final Mail`,
    CASE WHEN b.deliver = 1 THEN 'TRUE' ELSE 'FALSE' END AS `Deliver`,
    CASE WHEN b.google_review = 1 THEN 'TRUE' ELSE 'FALSE' END AS `Google Review`,
    NULL AS `Remark`,
    MAX(ba.delivery_date) AS `Delivery Date`,
    CASE WHEN b.writing_end IS NOT NULL THEN 'TRUE' ELSE 'FALSE' END AS `Writing Complete`,
    b.writing_by AS `Writing By`,
    DATE(b.writing_start) AS `Writing Start Date`,
    TIME_FORMAT(b.writing_start, '%H:%i:%s') AS `Writing Start Time`,
    DATE(b.writing_end) AS `Writing End Date`,
    TIME_FORMAT(b.writing_end, '%H:%i:%s') AS `Writing End Time`,
    CASE WHEN b.proofreading_end IS NOT NULL THEN 'TRUE' ELSE 'FALSE' END AS `Proofreading Complete`,
    b.proofreading_by AS `Proofreading By`,
    DATE(b.proofreading_start) AS `Proofreading Start Date`,
    TIME_FORMAT(b.proofreading_start, '%H:%i:%s') AS `Proofreading Start Time`,
    DATE(b.proofreading_end) AS `Proofreading End Date`,
    TIME_FORMAT(b.proofreading_end, '%H:%i:%s') AS `Proofreading End Time`,
    CASE WHEN b.formatting_end IS NOT NULL THEN 'TRUE' ELSE 'FALSE' END AS `Formating Complete`,
    b.formatting_by AS `Formating By`,
    DATE(b.formatting_start) AS `Formating Start Date`,
    TIME_FORMAT(b.formatting_start, '%H:%i:%s') AS `Formating Start Time`,
    DATE(b.formatting_end) AS `Formating End Date`,
    TIME_FORMAT(b.formatting_end, '%H:%i:%s') AS `Formating End Time`,
    MONTHNAME(b.date) AS `Month`,
    YEAR(b.date) AS `Year`,
    DATEDIFF(CURDATE(), b.date) AS `Since Enrolled`
FROM books b
LEFT JOIN RankedAuthors ba ON b.book_id = ba.book_id AND ba.rn <= 4
LEFT JOIN authors a ON ba.author_id = a.author_id
GROUP BY 
    b.book_id, b.title, b.date, b.apply_isbn, b.isbn, b.ready_to_print, b.print_status, b.deliver, 
    b.google_review, b.flipkart_link, b.google_link, b.agph_link, b.amazon_link, 
    b.writing_by, b.proofreading_by, b.formatting_by, 
    b.writing_start, b.writing_end, b.proofreading_start, b.proofreading_end, 
    b.formatting_start, b.formatting_end, b.cover_by
ORDER BY b.book_id;
"""

with st.spinner("Data fetching in progress...", show_time=False):
    conn = connect_db()
    operations_data = conn.query(query, show_spinner=False)

try:
    # Function to get book and author details with error handling
    def get_book_and_author_details(book_info):
        try:
            book_details = []
            no_of_authors = int(book_info.get('No of Author', 0))  # Use `.get` to handle missing keys
            
            for i in range(1, no_of_authors + 1):
                # Safely get author details
                author_data = {
                    "Author ID": book_info.get(f'Author Id {i}', None),
                    "Author Name": book_info.get(f'Author Name {i}', None),
                    "Position": book_info.get(f'Position {i}', None),
                    "Email": book_info.get(f'Email Address {i}', None),
                    "Contact": book_info.get(f'Contact No. {i}', None),
                    "Publishing Consultant": book_info.get(f'Publishing Consultant {i}', None),
                    "Welcome Mail": book_info.get(f'Welcome Mail / Confirmation {i}', None),
                    "Author Detail": book_info.get(f'Author Detail {i}', None),
                    "Photo": book_info.get(f'Photo {i}', None),
                    "ID Proof": book_info.get(f'ID Proof {i}', None),
                    "Send Cover Page": book_info.get(f'Send Cover Page and Agreement {i}', None),
                    "Agreement Received": book_info.get(f'Agreement Received {i}', None),
                    "Digital Prof": book_info.get(f'Digital Prof {i}', None),
                    "Confirmation": book_info.get(f'Confirmation {i}', None),
                }
                book_details.append(author_data)
            return book_details
        except Exception:
            st.error("Something went wrong while retrieving author details.")
            return []


    # Initialize session state for the text input field
    if "previous_search_column" not in st.session_state:
        st.session_state["previous_search_column"] = ""
    if "search_query" not in st.session_state:
        st.session_state["search_query"] = ""

    col1, col2 = st.columns([8,1], vertical_alignment="bottom")

    with col1:
        # Title
        st.write("## 📚 AGPH Advance Search")
    
    with col2:
        if st.button(":material/arrow_back: Go Back", key="back_button", type="tertiary", use_container_width=True):
            st.switch_page('app.py')

    # Columns for search inputs
    col1, col2 = st.columns(2)

    # Dropdown for selecting the search column
    with col1:
        search_column = st.selectbox(
            "🗃️ Select Column to Search:", 
            ['Book ID', 'Book Title', 'Author Name', 'ISBN', 'Author Email', 'Author Phone']
        )

    # Check if the selected column has changed
    if search_column != st.session_state["previous_search_column"]:
        # Reset the search query if the column changes
        st.session_state["search_query"] = ""
        st.session_state["previous_search_column"] = search_column

    # Text input for search query
    with col2:
        search_query = st.text_input(
            "🔍 Enter your search term:", 
            value=st.session_state["search_query"],
            key="search_query"
        )

    # Filter results
    filtered_data = pd.DataFrame()
    try:
        if search_query:
            if search_column == "Author Name":
                # Logic for Author Name
                mask = (operations_data['Author Name 1'].str.contains(search_query, case=False, na=False) |
                        operations_data['Author Name 2'].str.contains(search_query, case=False, na=False) |
                        operations_data['Author Name 3'].str.contains(search_query, case=False, na=False) |
                        operations_data['Author Name 4'].str.contains(search_query, case=False, na=False))
                filtered_data = operations_data[mask]
            elif search_column == "Book Title":
                # Logic for Book Title
                filtered_data = operations_data[
                    operations_data['Book Title'].str.contains(search_query, case=False, na=False)
                ]
            elif search_column == "Book ID":
                # Logic for Book ID
                try:
                    book_id = int(search_query)
                    filtered_data = operations_data[operations_data['Book ID'] == book_id]
                except ValueError:
                    st.error("Book ID must be a number!")
            elif search_column == "ISBN":
                # Logic for ISBN
                operations_data['ISBN'] = operations_data['ISBN'].astype(str).str.strip()
                filtered_data = operations_data[operations_data['ISBN'] == search_query]
            elif search_column == "Author Email":
                # Logic for Author Email
                mask = (operations_data['Email Address 1'].str.contains(search_query, case=False, na=False) |
                        operations_data['Email Address 2'].str.contains(search_query, case=False, na=False) |
                        operations_data['Email Address 3'].str.contains(search_query, case=False, na=False) |
                        operations_data['Email Address 4'].str.contains(search_query, case=False, na=False))
                filtered_data = operations_data[mask]
            elif search_column == "Author Phone":
                # Logic for Author Phone
                # Basic validation: ensure query contains only digits, spaces, or hyphens
                if search_query.replace(" ", "").replace("-", "").isdigit():
                    mask = (operations_data['Contact No. 1'].str.contains(search_query, case=False, na=False) |
                            operations_data['Contact No. 2'].str.contains(search_query, case=False, na=False) |
                            operations_data['Contact No. 3'].str.contains(search_query, case=False, na=False) |
                            operations_data['Contact No. 4'].str.contains(search_query, case=False, na=False))
                    filtered_data = operations_data[mask]
                else:
                    st.error("Phone number must contain only digits, spaces, or hyphens!")
    except Exception:
        st.error("Something went wrong while processing your search query.")


    # full dataframe search
    # mask = operations.apply(lambda row: row.astype(str).str.contains(search_string, case=False, na=False).any(), axis=1)
    # result = operations[mask]

    # Display results
    if not filtered_data.empty:
        st.success(f"Found {len(filtered_data)} results for '{search_query}' in '{search_column}'")

        for _, book in filtered_data.iterrows():
            # Determine book status
            deliver_status = str(book['Deliver']).strip().lower()
            status = "Pending" if deliver_status == "false" else "Delivered"
            status_color = "#ff6b6b" if status == "Pending" else "#51cf66"

            # Handle missing ISBN
            
            isbn_display = (
                            str(book['ISBN']).lower().strip()
                            if pd.notna(book['ISBN']) and str(book['ISBN']).lower().strip() != "nan" and book['ISBN'] != ""
                            else "<span style='color:#ff6b6b;font-weight:bold;'>Pending</span>"
                        )

            # Helper function for highlighting boolean values
            def highlight_boolean(value):
                value = str(value).strip().lower()
                if value == "true":
                    return "<span style='color: #51cf66; font-weight: bold;'> Yes</span>"
                else:
                    return "<span style='color: #ff6b6b; font-weight: bold;'> No</span>"

            def generate_link_icons(book):
                icons = {
                    "Amazon Link": "https://img.icons8.com/color/48/000000/amazon.png",
                    "Google Link": "https://img.icons8.com/color/48/000000/google-logo.png",
                    "Flipkart Link": "https://img.icons8.com/?size=100&id=UU2im0hihoyi&format=png&color=000000",
                    "AGPH Link": "https://img.icons8.com/ios-filled/50/000000/open-book.png",
                }
                links_html = ""
                for column, icon_url in icons.items():
                    # Safely retrieve the link and handle missing or invalid values
                    link = book.get(column, None)
                    if link is not None and pd.notna(link) and str(link).strip() != "":
                        links_html += f"<a href='{str(link).strip()}' target='_blank'><img src='{icon_url}' alt='{column}' style='width:24px; margin-right:8px;'></a>"
                return links_html


            with st.container():
                st.markdown(
                    f"""
                    <div style="
                        background-color: #f8f9fa;
                        padding: 20px;
                        border-radius: 12px;
                        margin-bottom: 20px;
                        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
                        border: 1px solid #dee2e6;
                        font-family: 'Arial', sans-serif;">
                        <h3 style="
                            color: #495057;
                            background-color: #e9ecef;
                            padding: 10px 15px;
                            border-radius: 8px;
                            margin-bottom: 20px;
                            font-weight: 600;
                            text-align: center;">
                            📖 {book['Book Title']}
                            <span style="
                                background-color: {status_color};
                                color: white;
                                padding: 5px 10px;
                                border-radius: 15px;
                                font-size: 14px;
                                margin-left: 10px;">
                                {status}
                            </span>
                        </h3>
                        <div style="
                            display: grid;
                            grid-template-columns: repeat(3, 1fr);
                            gap: 20px;
                            font-size: 14px;
                            color: #343a40;">
                            <div>
                                <p>🔖 <b>Book ID:</b> {book['Book ID']}</p>
                                <p>📚 <b>ISBN:</b> {isbn_display}</p>
                                <p>📅 <b>Enroll Date:</b> {book['Date']}</p>
                                <p>🗓️ <b>Book Month:</b> {book['Month']}</p>
                                <p>⌛ <b>Since Enrolled:</b> {book['Since Enrolled']}</p>
                            </div>
                            <div>
                                <p>👥 <b>No of Authors:</b> {book['No of Author']}</p>
                                <p>✅ <b>Book Done:</b> {highlight_boolean(book['Book Complete'])}</p>
                                <p>📄 <b>Agreement Received:</b> {highlight_boolean(book['Agreement Received'])}</p>
                                <p>📤 <b>Send Cover Page:</b> {highlight_boolean(book['Send Cover Page and Agreement'])}</p>
                                <p>🖼️ <b>Digital Prof:</b> {highlight_boolean(book['Digital Prof'])}</p>
                            </div>
                            <div>
                                <p>🔔 <b>Confirmation:</b> {highlight_boolean(book['Confirmation'])}</p>
                                <p>🖨️ <b>Ready to Print:</b> {highlight_boolean(book['Ready to Print'])}</p>
                                <p>📦 <b>Print:</b> {highlight_boolean(book['Print'])}</p>
                                <p>🚚 <b>Deliver:</b> {highlight_boolean(book['Deliver'])}</p>
                                <div><p>🔗 <b>Links:</b> {generate_link_icons(book)}</p></div>
                            </div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Expandable section for author details
                with st.expander("📋 View Author Details"):
                    authors = get_book_and_author_details(book)  # Fetch authors details
                    total_authors = len(authors)

                    # Helper function to highlight boolean values
                    def highlight_boolean(value):
                        value = str(value).strip().lower()
                        if value == "true":
                            return "<span style='color: #51cf66; font-weight: bold;'>Yes</span>"
                        else:
                            return "<span style='color: #ff6b6b; font-weight: bold;'>No</span>"

                    # Create a 4-column layout for author cards
                    for idx, author in enumerate(authors, start=1):
                        if idx % 4 == 1:  # Start a new row for every 4 authors
                            cols = st.columns(4)  # Create 4 columns

                        # Card content
                        with cols[(idx - 1) % 4]:
                            st.markdown(
                                f"""
                                <div style="
                                    background-color: #ffffff;
                                    border-radius: 12px;
                                    box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
                                    padding: 15px;
                                    margin-bottom: 20px;
                                    border: 1px solid #dee2e6;
                                    font-family: 'Arial', sans-serif;">
                                    <h4 style="
                                        color: #495057;
                                        background-color: #e9ecef;
                                        padding: 10px;
                                        border-radius: 8px;
                                        margin-bottom: 15px;
                                        text-align: center;">
                                        Author {idx} 
                                        <span style="font-size: 14px; font-weight: 400; color: #868e96;">
                                            ({author['Position']})
                                        </span>
                                    </h4>
                                    <p style="font-size: 16px; font-weight: bold; color: #1c7ed6; margin-bottom: 10px;">
                                        {author['Author Name']}
                                    </p>
                                    <p><b>Author ID:</b> {author['Author ID']}</p>
                                    <p><b>Email:</b> {author['Email']}</p>
                                    <p><b>Contact:</b> {author['Contact']}</p>
                                    <p><b>Publishing Consultant:</b> 
                                    <span style="color:rgb(236, 116, 35); font-weight: bold;">{author['Publishing Consultant']}</span>
                                    </p>
                                    <p><b>Welcome Mail:</b> {highlight_boolean(author['Welcome Mail'])}</p>
                                    <p><b>Photo:</b> {highlight_boolean(author['Photo'])}</p>
                                    <p><b>ID Proof:</b> {highlight_boolean(author['ID Proof'])}</p>
                                    <p><b>Send Cover Page:</b> {highlight_boolean(author['Send Cover Page'])}</p>
                                    <p><b>Agreement Received:</b> {highlight_boolean(author['Agreement Received'])}</p>
                                    <p><b>Digital Profile:</b> {highlight_boolean(author['Digital Prof'])}</p>
                                    <p><b>Confirmation:</b> {highlight_boolean(author['Confirmation'])}</p>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                def handle_missing(value):
                    if pd.isna(value) or str(value).strip().lower() in ["nan", ""]:
                        return "<span style='color: #ff6b6b; font-weight: bold;'>Pending</span>"
                    return value

                with st.expander("📘 Operation Details"):
                    # Layout: Three cards in a row
                    col1, col2, col3 = st.columns(3)

                    # Writing Details
                    with col1:
                        status = "Done" if book['Writing Complete'] == "TRUE" else "Pending"
                        status_color = "#51cf66" if status == "Done" else "#ff6b6b"
                        st.markdown(
                            f"""
                            <div style="
                                background-color: #ffffff;
                                border-radius: 12px;
                                box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
                                padding: 15px;
                                margin-bottom: 20px;
                                border: 1px solid #dee2e6;
                                font-family: 'Arial', sans-serif;">
                                <h4 style="
                                    color: #495057;
                                    background-color: #e9ecef;
                                    padding: 10px;
                                    border-radius: 8px;
                                    margin-bottom: 15px;
                                    text-align: center;
                                    font-size: 20px;">
                                    ✍️ Writing Details 
                                    <span style="
                                    background-color: {status_color};
                                    color: white;
                                    padding: 5px 10px;
                                    border-radius: 15px;
                                    font-size: 12px;
                                    margin-left: 10px;">
                                    {status}
                                </span>
                                </h4>
                                <div style="font-size: 14px; color: #495057; line-height: 1.6;">
                                    <p><b>Writing Complete:</b> {highlight_boolean(book['Writing Complete'])}</p>
                                    <p><b>Written By:</b> 
                                        <span style="color: #1c7ed6; font-weight: bold;">{handle_missing(book['Writing By'])}</span>
                                    </p>
                                    <p><b>Start Date:</b> {handle_missing(book['Writing Start Date'])}</p>
                                    <p><b>Start Time:</b> {handle_missing(book['Writing Start Time'])}</p>
                                    <p><b>End Date:</b> {handle_missing(book['Writing End Date'])}</p>
                                    <p><b>End Time:</b> {handle_missing(book['Writing End Time'])}</p>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    # Proofreading Details
                    with col2:
                        status = "Done" if book['Proofreading Complete'] == "TRUE" else "Pending"
                        status_color = "#51cf66" if status == "Done" else "#ff6b6b"
                        st.markdown(
                            f"""
                            <div style="
                                background-color: #ffffff;
                                border-radius: 12px;
                                box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
                                padding: 15px;
                                margin-bottom: 20px;
                                border: 1px solid #dee2e6;
                                font-family: 'Arial', sans-serif;">
                                <h4 style="
                                    color: #495057;
                                    background-color: #e9ecef;
                                    padding: 10px;
                                    border-radius: 8px;
                                    margin-bottom: 15px;
                                    text-align: center;
                                    font-size: 20px;">
                                    📝 Proofreading Details 
                                    <span style="
                                        background-color: {status_color};
                                        color: white;
                                        padding: 5px 10px;
                                        border-radius: 15px;
                                        font-size: 12px;
                                        margin-left: 10px;">
                                        {status}
                                    </span>
                                </h4>
                                <div style="font-size: 14px; color: #495057; line-height: 1.6;">
                                    <p><b>Proofreading Complete:</b> {highlight_boolean(book['Proofreading Complete'])}</p>
                                    <p><b>Proofread By:</b> 
                                        <span style="color: #1c7ed6; font-weight: bold;">{handle_missing(book['Proofreading By'])}</span>
                                    </p>
                                    <p><b>Start Date:</b> {handle_missing(book['Proofreading Start Date'])}</p>
                                    <p><b>Start Time:</b> {handle_missing(book['Proofreading Start Time'])}</p>
                                    <p><b>End Date:</b> {handle_missing(book['Proofreading End Date'])}</p>
                                    <p><b>End Time:</b> {handle_missing(book['Proofreading End Time'])}</p>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    # Formatting Details
                    with col3:
                        status = "Done" if book['Formating Complete'] == "TRUE" else "Pending"
                        status_color = "#51cf66" if status == "Done" else "#ff6b6b"
                        st.markdown(
                            f"""
                            <div style="
                                background-color: #ffffff;
                                border-radius: 12px;
                                box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
                                padding: 15px;
                                margin-bottom: 20px;
                                border: 1px solid #dee2e6;
                                font-family: 'Arial', sans-serif;">
                                <h4 style="
                                    color: #495057;
                                    background-color: #e9ecef;
                                    padding: 10px;
                                    border-radius: 8px;
                                    margin-bottom: 15px;
                                    text-align: center;
                                    font-size: 20px;">
                                    📂 Formatting Details 
                                    <span style="
                                        background-color: {status_color};
                                        color: white;
                                        padding: 5px 10px;
                                        border-radius: 15px;
                                        font-size: 12px;
                                        margin-left: 10px;">
                                        {status}
                                    </span>
                                </h4>
                                <div style="font-size: 14px; color: #495057; line-height: 1.6;">
                                    <p><b>Formatting Complete:</b> {highlight_boolean(book['Formating Complete'])}</p>
                                    <p><b>Formatted By:</b> 
                                        <span style="color: #1c7ed6; font-weight: bold;">{handle_missing(book['Formating By'])}</span>
                                    </p>
                                    <p><b>Start Date:</b> {handle_missing(book['Formating Start Date'])}</p>
                                    <p><b>Start Time:</b> {handle_missing(book['Formating Start Time'])}</p>
                                    <p><b>End Date:</b> {handle_missing(book['Formating End Date'])}</p>
                                    <p><b>End Time:</b> {handle_missing(book['Formating End Time'])}</p>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )


    else:
        if search_query:
            st.error(f"No results found for '{search_query}' in '{search_column}'")
        else:
            st.info("Enter a search term to begin.")

except Exception as e:
    st.error(f"An error occurred: {e}")
    st.error("Likely Data is not Correct")

