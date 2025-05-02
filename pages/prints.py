import streamlit as st
import pandas as pd
from datetime import date, datetime
from sqlalchemy.sql import text
from auth import validate_token

logo = "logo/logo_black.png"
fevicon = "logo/favicon_black.ico"
small_logo = "logo/favicon_white.ico"

st.set_page_config(page_title='AGPH Search', page_icon="🔍", layout="wide")

st.logo(logo,
size = "large",
icon_image = small_logo
)

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


conn = connect_db()

# Function to fetch books for the table (redesigned to avoid duplicates)
def fetch_print_ready_books():
    query = """
    WITH ReadyToPrint AS (
    SELECT 
        b.book_id,
        b.title,
        b.date,
        COALESCE(pr.num_copies, b.num_copies) AS num_copies,
        'Ready for Print' AS status,
        pr.print_type,
        pr.binding,
        pr.book_size
    FROM books b
    LEFT JOIN print_runs pr ON b.book_id = pr.book_id
        AND pr.status = 'Planned'
        AND pr.id = (
            SELECT MAX(id)
            FROM print_runs pr2
            WHERE pr2.book_id = pr.book_id
            AND pr2.status = 'Planned'
        )
    WHERE 
        b.writing_complete = 1 
        AND b.proofreading_complete = 1 
        AND b.formatting_complete = 1 
        AND b.cover_page_complete = 1
        AND b.print_status = 0
        AND NOT EXISTS (
            SELECT 1 
            FROM book_authors ba 
            WHERE ba.book_id = b.book_id 
            AND (
                ba.welcome_mail_sent != 1 
                OR ba.photo_recive != 1 
                OR ba.id_proof_recive != 1 
                OR ba.author_details_sent != 1 
                OR ba.cover_agreement_sent != 1 
                OR ba.agreement_received != 1 
                OR ba.digital_book_sent != 1 
                OR ba.printing_confirmation != 1
            )
        )
        AND NOT EXISTS (
            SELECT 1
            FROM batch_books bb
            JOIN batches bt ON bb.batch_id = bt.batch_id
            WHERE bb.book_id = b.book_id
            AND bt.status = 'Sent'
            AND bt.receiving_date IS NULL
        )
        AND NOT EXISTS (
            SELECT 1
            FROM print_runs pr3
            WHERE pr3.book_id = b.book_id
            AND pr3.status = 'Completed'
        )
),
LatestPrintRun AS (
    SELECT 
        book_id,
        num_copies,
        print_type,
        binding,
        book_size
    FROM print_runs pr
    WHERE num_copies > 0
    AND status = 'Planned'
    AND id = (
        SELECT MAX(id)
        FROM print_runs pr2
        WHERE pr2.book_id = pr.book_id
        AND pr2.num_copies > 0
        AND pr2.status = 'Planned'
    )
),
ReprintBooks AS (
    SELECT 
        b.book_id,
        b.title,
        b.date,
        lpr.num_copies,
        'Ready for Reprint' AS status,
        lpr.print_type,
        lpr.binding,
        lpr.book_size
    FROM books b
    JOIN LatestPrintRun lpr ON b.book_id = lpr.book_id
    WHERE EXISTS (
        SELECT 1
        FROM print_runs pr
        WHERE pr.book_id = b.book_id
        AND pr.status = 'Completed'
    )
    AND NOT EXISTS (
        SELECT 1
        FROM batch_books bb
        JOIN batches bt ON bb.batch_id = bt.batch_id
        WHERE bb.book_id = b.book_id
        AND bt.status = 'Sent'
        AND bt.receiving_date IS NULL
    )
)
SELECT 
    book_id,
    title,
    date,
    num_copies,
    status,
    print_type,
    binding,
    book_size
FROM ReadyToPrint
UNION
SELECT 
    book_id,
    title,
    date,
    num_copies,
    status,
    print_type,
    binding,
    book_size
FROM ReprintBooks
ORDER BY title;
    """
    return conn.query(query, ttl=0, show_spinner=False)

# Function to fetch running batches
def fetch_running_batches():
    query = """
    SELECT 
        bt.batch_id,
        bt.batch_name,
        bt.print_sent_date,
        COUNT(bb.id) AS num_books
    FROM batches bt
    LEFT JOIN batch_books bb ON bt.batch_id = bb.batch_id
    WHERE bt.status = 'Sent' AND bt.receiving_date IS NULL
    GROUP BY bt.batch_id, bt.batch_name, bt.print_sent_date
    ORDER BY bt.print_sent_date DESC;
    """
    return conn.query(query, ttl=0, show_spinner=False)

# Function to fetch books in a specific batch
def fetch_batch_books(batch_id):
    query = """
    SELECT 
        b.book_id,
        b.title,
        bb.num_copies,
        COALESCE(pr.print_type, NULL) AS print_type,
        COALESCE(pr.binding, NULL) AS binding,
        COALESCE(pr.book_size, NULL) AS book_size
    FROM batch_books bb
    JOIN books b ON bb.book_id = b.book_id
    LEFT JOIN print_runs pr ON b.book_id = pr.book_id
        AND pr.print_sent_date = (
            SELECT MAX(print_sent_date)
            FROM print_runs pr2
            WHERE pr2.book_id = b.book_id
            AND pr2.print_sent_date IS NOT NULL
        )
    WHERE bb.batch_id = :batch_id;
    """
    return conn.query(query, params={"batch_id": batch_id}, ttl=0, show_spinner=False)

# Function to fetch batch history (completed batches)
def fetch_batch_history(year, month):
    query = """
    SELECT 
        bt.batch_id,
        bt.batch_name,
        bt.print_sent_date,
        bt.print_by,
        bt.receiving_date,
        bt.status
    FROM batches bt
    WHERE (bt.status = 'Received' OR bt.receiving_date IS NOT NULL)
        AND YEAR(bt.receiving_date) = :year
        AND MONTH(bt.receiving_date) = :month
    ORDER BY bt.receiving_date DESC;
    """
    return conn.query(query, params={"year": year, "month": month}, ttl=0, show_spinner=False)

# Dialog for batch creation
@st.dialog("Create New Batch")
def create_batch_dialog(books_df):
    st.write("Enter batch details and select books to include.")
    
    # Form inputs
    print_sent_date = st.date_input("Print Sent Date", value=date.today())
    print_by = st.text_input("Print By")
    
    # Book selection (all books selected by default)
    selected_books = st.multiselect(
        "Select Books",
        options=books_df["title"],
        default=books_df["title"].tolist()
    )
    
    # Form submission
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Create Batch"):
            if not print_by:
                st.error("Print By is required.")
            elif not selected_books:
                st.error("At least one book must be selected.")
            else:
                try:
                    with conn.session as session:
                        # Generate batch name
                        batch_name = f"Batch_{print_sent_date.strftime('%Y_%m_%d')}"
                        
                        # Insert into batches table
                        session.execute(
                            text("""
                            INSERT INTO batches (batch_name, print_sent_date, print_by, created_at, status)
                            VALUES (:batch_name, :print_sent_date, :print_by, :created_at, 'Sent')
                            """),
                            {
                                "batch_name": batch_name,
                                "print_sent_date": print_sent_date,
                                "print_by": print_by,
                                "created_at": datetime.now()
                            }
                        )
                        
                        # Get the inserted batch_id
                        batch_id = session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                        
                        # Insert into batch_books and update print_runs for reprints
                        for book_title in selected_books:
                            book_row = books_df[books_df["title"] == book_title].iloc[0]
                            book_id = book_row["book_id"]
                            num_copies = book_row["num_copies"]
                            
                            # Insert into batch_books
                            session.execute(
                                text("""
                                INSERT INTO batch_books (batch_id, book_id, num_copies)
                                VALUES (:batch_id, :book_id, :num_copies)
                                """),
                                {
                                    "batch_id": batch_id,
                                    "book_id": book_id,
                                    "num_copies": num_copies
                                }
                            )
                            
                            # If reprint, update print_runs
                            if book_row["status"] == "Ready for Reprint":
                                session.execute(
                                    text("""
                                    UPDATE print_runs
                                    SET print_sent_date = :print_sent_date
                                    WHERE book_id = :book_id
                                    AND print_sent_date IS NULL
                                    AND num_copies > 0
                                    """),
                                    {
                                        "print_sent_date": print_sent_date,
                                        "book_id": book_id
                                    }
                                )
                        
                        session.commit()
                        st.success(f"Batch {batch_name} created successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error creating batch: {e}")
    
    with col2:
        if st.button("Cancel"):
            st.rerun()

# Streamlit app
st.title("Book Printing Management")

# Ready to Print/Reprint Books
st.subheader("Books Ready to Print or Reprint")

# New Batch button
if st.button("New Batch"):
    books_df = fetch_print_ready_books()
    create_batch_dialog(books_df)

# Filters
col1, col2 = st.columns(2)
with col1:
    search_term = st.text_input("Search by Title or Book ID", "")
with col2:
    status_filter = st.selectbox("Filter by Status", ["All", "Ready for Print", "Ready for Reprint"])

# Fetch and filter data
books_df = fetch_print_ready_books()
if search_term:
    books_df = books_df[
        books_df["title"].str.contains(search_term, case=False, na=False) |
        books_df["book_id"].astype(str).str.contains(search_term, na=False)
    ]
if status_filter != "All":
    books_df = books_df[books_df["status"] == status_filter]

# Display table
st.dataframe(
    books_df[["book_id", "title", "date", "num_copies", "print_type", "binding", "book_size"]],
    use_container_width=True,
    column_config={
        "book_id": "Book ID",
        "title": "Title",
        "date": "Date",
        "num_copies": "Copies Requested",
        "print_type": "Print Type",
        "binding": "Binding",
        "book_size": "Book Size"
    }
)

st.stop()

# Running Batches
st.subheader("Running Print Batches")
running_batches_df = fetch_running_batches()
if not running_batches_df.empty:
    for _, batch in running_batches_df.iterrows():
        st.subheader(f"Batch {batch['batch_name']} (ID: {batch['batch_id']}, Sent: {batch['print_sent_date']}, Books: {batch['num_books']})")
        batch_books_df = fetch_batch_books(batch['batch_id'])
        if not batch_books_df.empty:
            st.dataframe(
                batch_books_df[["book_id", "title", "num_copies", "print_type", "binding", "book_size"]],
                use_container_width=True,
                column_config={
                    "book_id": "Book ID",
                    "title": "Title",
                    "num_copies": "Copies",
                    "print_type": "Print Type",
                    "binding": "Binding",
                    "book_size": "Book Size"
                }
            )
        else:
            st.write("No books in this batch.")
        st.divider()
else:
    st.write("No running batches.")

# Batch History
st.subheader("Batch History (Completed Batches)")
col1, col2 = st.columns(2)
with col1:
    year = st.selectbox("Select Year", list(range(2020, 2030)), index=list(range(2020, 2030)).index(2025))
with col2:
    month = st.selectbox("Select Month", ["January", "February", "March", "April", "May", "June", 
                                         "July", "August", "September", "October", "November", "December"], 
                         index=4)  # Default to May

# Convert month name to number
month_map = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}
month_num = month_map[month]

history_df = fetch_batch_history(year, month_num)
if not history_df.empty:
    for _, batch in history_df.iterrows():
        st.subheader(f"Batch {batch['batch_name']} (ID: {batch['batch_id']}, Sent: {batch['print_sent_date']}, "
                     f"Received: {batch['receiving_date']}, Print By: {batch['print_by']}, Status: {batch['status']})")
        batch_books_df = fetch_batch_books(batch['batch_id'])
        if not batch_books_df.empty:
            st.dataframe(
                batch_books_df[["book_id", "title", "num_copies", "print_type", "binding", "book_size"]],
                use_container_width=True,
                column_config={
                    "book_id": "Book ID",
                    "title": "Title",
                    "num_copies": "Copies",
                    "print_type": "Print Type",
                    "binding": "Binding",
                    "book_size": "Book Size"
                }
            )
        else:
            st.write("No books in this batch.")
        st.divider()
else:
    st.write(f"No completed batches found for {month} {year}.")