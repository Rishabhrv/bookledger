import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from io import BytesIO
from auth import validate_token
from constants import log_activity, initialize_click_and_session_id, connect_db, clean_url_params


logo = "logo/logo_black.png"
fevicon = "logo/favicon_black.ico"
small_logo = "logo/favicon_white.ico"

st.set_page_config(page_title='AGPH Prints', page_icon="🖨️", layout="wide")

st.logo(logo,
size = "large",
icon_image = small_logo
)

validate_token()
initialize_click_and_session_id()

user_role = st.session_state.get("role", None)
user_app = st.session_state.get("app", None)
user_access = st.session_state.get("access", None)
session_id = st.session_state.session_id
click_id = st.session_state.get("click_id", None)




if user_role != 'admin' and not (
    user_role == 'user' and 
    user_app == 'main' and 
    'Print Management' in user_access 
):
    st.error("⚠️ Access Denied: You don't have permission to access this page.")
    st.stop()

st.cache_data.clear()

st.markdown("""
    <style>
            
        /* Remove Streamlit's default top padding */
        .main > div {
            padding-top: 0px !important;
        }
        /* Ensure the first element has minimal spacing */
        .block-container {
            padding-top: 28px !important;  /* Small padding for breathing room */
        }
            """, unsafe_allow_html=True)


# Custom CSS for headings with badge and improved table styling
st.markdown("""
<style>
/* Heading styles from the provided CSS */
.status-badge-red {
    background-color: #FFEBEE;
    color: #F44336;
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: bold;
    display: inline-flex;
    align-items: center;
    font-size: 20px;
    margin-bottom: 10px;
}
            
.status-badge-non {
    background-color: #E8F5E9;
    color: #4CAF50;
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: bold;
    display: inline-flex;
    align-items: center;
    font-size: 16px;
    margin-bottom: 12px;
}
            
.status-badge-nonn {
    background-color: white;
    color: #4CAF50;
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: bold;
    display: inline-flex;
    align-items: center;
    font-size: 14px;
    margin-bottom: 5px;
}
            
.status-badge-yellow {
    background-color: #FFFDE7;
    color: #F9A825;
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: bold;
    display: inline-flex;
    align-items: center;
    font-size: 20px;
    margin-bottom: 12px;
}
.status-badge-green {
    background-color: #E8F5E9;
    color: #4CAF50;
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: bold;
    display: inline-flex;
    align-items: center;
    font-size: 20px;
    margin-bottom: 12px;
}
        
.badge-count {
    background-color: rgba(255, 255, 255, 0.9);
    color: inherit;
    padding: 2px 6px;
    border-radius: 10px;
    margin-left: 6px;
    font-size: 14px;
    font-weight: normal;
}
/* Table and container styles from previous version */
.table-header {
    font-weight: bold;
    font-size: 15px;
    color: #333;
    padding: 10px;
    border-bottom: 2px solid #ddd;
}
.table-row {
    padding: 6px 10px;
    background-color: #ffffff;
    font-size: 14px; /* Smaller font size as requested previously */
    margin-bottom: 5px;
    margin-top: 5px;    
}

.table-row:hover {
    background-color: #f1f1f1; /* Hover effect */
}
.container-spacing {
    margin-bottom: 30px;
}
</style>
""", unsafe_allow_html=True)

conn = connect_db()

# Initialize logged_click_ids if not present
if "logged_click_ids" not in st.session_state:
    st.session_state.logged_click_ids = set()

# Log navigation if click_id is present and not already logged
if click_id and click_id not in st.session_state.logged_click_ids:
    try:
        log_activity(
            conn,
            st.session_state.user_id,
            st.session_state.username,
            st.session_state.session_id,
            "navigated to page",
            f"Page: Print Management"
        )
        st.session_state.logged_click_ids.add(click_id)
    except Exception as e:
        st.error(f"Error logging navigation: {str(e)}")

# Fetch ready-to-print books (not printed, not in running batches)
def get_ready_to_print_books(conn):
    query = """
    SELECT 
        b.book_id, 
        b.title, 
        b.date, 
        COALESCE(pe.copies_planned, b.num_copies) AS num_copies,
        'First Print' AS print_type,
        COALESCE(pe.book_size, '6x9') AS book_size,
        COALESCE(pe.binding, 'Paperback') AS binding,
        COALESCE(pe.print_cost, 00.00) AS print_cost,
        b.book_pages,
        pe.print_id  # Added to fetch existing print_id
    FROM 
        books b
    LEFT JOIN 
        PrintEditions pe ON b.book_id = pe.book_id 
        AND pe.edition_number = (SELECT MIN(edition_number) FROM PrintEditions WHERE book_id = b.book_id)
    WHERE 
        b.print_status = 0
        AND (
            (b.is_publish_only = 1 AND b.proofreading_complete = 1 AND b.formatting_complete = 1 AND b.cover_page_complete = 1)
            OR
            (b.writing_complete = 1 AND b.proofreading_complete = 1 AND b.formatting_complete = 1 AND b.cover_page_complete = 1)
        )
        AND b.book_id IN (
            SELECT ba2.book_id
            FROM book_authors ba2
            GROUP BY ba2.book_id
            HAVING 
                MIN(ba2.welcome_mail_sent) = 1
                AND MIN(ba2.agreement_received) = 1
                AND MIN(ba2.digital_book_sent) = 1
                AND MIN(ba2.printing_confirmation) = 1
                AND MIN(ba2.photo_recive) = 1
                AND MIN(ba2.id_proof_recive) = 1
                AND MIN(ba2.author_details_sent) = 1
                AND MIN(ba2.cover_agreement_sent) = 1
        )
        AND NOT EXISTS (
            SELECT 1
            FROM BatchDetails bd
            JOIN PrintBatches pb ON bd.batch_id = pb.batch_id
            WHERE bd.print_id IN (SELECT print_id FROM PrintEditions pe3 WHERE pe3.book_id = b.book_id)
            AND pb.status = 'Sent'
        )
    GROUP BY 
        b.book_id, b.title, b.date, pe.copies_planned, pe.book_size, pe.binding, pe.print_cost, b.book_pages, pe.print_id;
    """
    df = conn.query(query, ttl=0)  # Disable caching
    return df

def get_reprint_eligible_books(conn):
    query = """
        SELECT 
            b.book_id, 
            b.title,
            b.date,
            b.isbn,
            'Reprint' AS print_type,
            COALESCE(pe.book_size, '6x9') AS book_size,
            COALESCE(pe.binding, 'Paperback') AS binding,
            COALESCE(pe.print_cost, 0.00) AS print_cost,
            pe.print_color,
            pe.copies_planned,
            b.book_pages,
            pe.print_id  # Ensure print_id is fetched
        FROM 
            books b
        JOIN (
            SELECT 
                pe2.book_id,
                pe2.book_size,
                pe2.binding,
                pe2.print_color,
                COALESCE(pe2.print_cost, 0.00) AS print_cost,
                pe2.copies_planned,
                pe2.print_id,
                ROW_NUMBER() OVER (PARTITION BY pe2.book_id ORDER BY pe2.edition_number DESC, pe2.print_date DESC) AS rn
            FROM 
                PrintEditions pe2
        ) pe ON b.book_id = pe.book_id AND pe.rn = 1
        LEFT JOIN 
            BatchDetails bd ON pe.print_id = bd.print_id
        WHERE 
            b.print_status = 1
            AND bd.print_id IS NULL
        GROUP BY 
            b.book_id, b.title, b.isbn, pe.book_size, pe.binding, pe.print_color, pe.print_cost, pe.copies_planned, b.book_pages, pe.print_id;
    """
    df = conn.query(query, ttl=0)  # Disable caching
    return df

# Fetch running batches (status = 'Sent')
def get_running_batches(conn):
    query = """
    SELECT 
        batch_id, 
        batch_name, 
        created_at, 
        print_sent_date, 
        total_copies, 
        status, 
        printer_name
    FROM 
        PrintBatches
    WHERE 
        status = 'Sent'
    ORDER BY 
        created_at DESC;
    """
    df = conn.query(query, ttl=0)  # Disable caching
    return df

# Fetch books in a specific batch
def get_batch_books(conn, batch_id):
    query = """
    SELECT 
        b.book_id,
        b.title,
        bd.copies_in_batch,
        pe.book_size,
        pe.binding,
        pe.print_color,
        pe.print_cost,
        pe.edition_number,
        b.book_pages
    FROM 
        BatchDetails bd
    JOIN 
        PrintEditions pe ON bd.print_id = pe.print_id
    JOIN 
        books b ON pe.book_id = b.book_id
    WHERE 
        bd.batch_id = :batch_id
    ORDER BY 
        b.book_id;
    """
    df = conn.query(query, ttl=0, params={"batch_id": batch_id})
    return df

# Create a new batch and assign books
def create_batch(conn, batch_name, printer_name, print_sent_date, selected_books):
    total_copies = sum(book['num_copies'] for book in selected_books)
    
    with conn.session as session:
        # Insert new batch
        result = session.execute(
            text("""
                INSERT INTO PrintBatches 
                    (batch_name, printer_name, created_at, print_sent_date, total_copies, status)
                VALUES 
                    (:batch_name, :printer_name, CURDATE(), :print_sent_date, :total_copies, 'Sent')
            """),
            {
                "batch_name": batch_name,
                "printer_name": printer_name,
                "print_sent_date": print_sent_date,
                "total_copies": total_copies
            }
        )
        batch_id = result.lastrowid
        
        # Collect print_ids and handle first print books
        first_print_ids = []
        print_ids = []
        for book in selected_books:
            print_id = book['print_id']  # Use the existing print_id
            print_ids.append(print_id)  # Collect print_id for status update
            session.execute(
                text("""
                    INSERT INTO BatchDetails 
                        (batch_id, print_id, copies_in_batch)
                    VALUES 
                        (:batch_id, :print_id, :copies_in_batch)
                """),
                {
                    "batch_id": batch_id,
                    "print_id": print_id,
                    "copies_in_batch": book['num_copies']
                }
            )
            if book['print_type'] == 'First Print':
                first_print_ids.append(book['book_id'])
        
        # Update first-print books to mark as printed
        if first_print_ids:
            session.execute(
                text("UPDATE books SET print_status = 1 WHERE book_id IN :book_ids"),
                {"book_ids": tuple(first_print_ids)}
            )
        
        # Update PrintEditions status to 'In Printing'
        if print_ids:
            session.execute(
                text("UPDATE PrintEditions SET status = 'In Printing' WHERE print_id IN :print_ids"),
                {"print_ids": tuple(print_ids)}
            )
        
        session.commit()
    return batch_id

# Update batch receive date
def update_batch_receive_date(conn, batch_id, receive_date):
    with conn.session as session:
        # Verify batch is running
        result = session.execute(
            text("SELECT status FROM PrintBatches WHERE batch_id = :batch_id"),
            {"batch_id": batch_id}
        )
        status = result.fetchone()[0]
        if status != 'Sent':
            raise ValueError("Only running batches can be edited")
        
        # Update the batch status to 'Received'
        session.execute(
            text("""
                UPDATE PrintBatches 
                SET print_receive_date = :receive_date, status = 'Received'
                WHERE batch_id = :batch_id
            """),
            {"receive_date": receive_date, "batch_id": batch_id}
        )

        # Update PrintEditions status to 'Received' for all print_ids in this batch
        session.execute(
            text("""
                UPDATE PrintEditions 
                SET status = 'Received' 
                WHERE print_id IN (SELECT print_id FROM BatchDetails WHERE batch_id = :batch_id)
            """),
            {"batch_id": batch_id}
        )

        session.commit()

@st.dialog("Create New Batch", width="medium")
def create_batch_dialog():
    conn = connect_db()
    st.subheader("New Batch Details")
    
    batch_name = st.text_input("Batch Name", value=f"{datetime.now().strftime('%B %Y')}")
    printer_name = st.text_input("Printer Name", value="Default Printer")
    print_sent_date = st.date_input("Print Sent Date", value=datetime.now())
    
    # Fetch both first prints and reprints
    first_print_books = get_ready_to_print_books(conn)
    reprint_books = get_reprint_eligible_books(conn)
    
    # Combine first prints and reprints for multiselect
    all_books = []
    for _, book in first_print_books.iterrows():
        all_books.append({
            'book_id': book['book_id'],
            'title': book['title'],
            'num_copies': book['num_copies'],
            'book_size': book['book_size'],
            'binding': book['binding'],
            'print_color': 'Black & White',  # Default for first prints
            'print_type': book['print_type'],
            'book_pages': book['book_pages'],
            'print_id': book['print_id']  # Include print_id
        })
    for _, book in reprint_books.iterrows():
        all_books.append({
            'book_id': book['book_id'],
            'title': book['title'],
            'num_copies': book['copies_planned'] if book['copies_planned'] else 7,
            'book_size': book['book_size'] if book['book_size'] else '6x9',
            'binding': book['binding'] if book['binding'] else 'Paperback',
            'print_color': book['print_color'] if book['print_color'] else 'Black & White',
            'print_type': book['print_type'],
            'book_pages': book['book_pages'],
            'print_id': book['print_id']  # Include print_id
        })
    
    # Multiselect with all books pre-selected
    book_options = [f"{book['title']} ({book['print_type']})" for book in all_books]
    default_books = book_options  # Pre-select all
    selected_titles = st.multiselect("Select Books for Batch", book_options, default=default_books)
    
    # Filter selected books
    selected_books = [book for book in all_books if f"{book['title']} ({book['print_type']})" in selected_titles]
    
    # Validate required fields for each selected book
    required_fields = ['num_copies', 'book_size', 'binding', 'print_color', 'print_id']
    invalid_books = []
    for book in selected_books:
        missing_fields = [field for field in required_fields if not book.get(field)]
        if missing_fields:
            invalid_books.append(f"{book['title']} (Missing: {', '.join(missing_fields)})")
    
    if invalid_books:
        error_message = "The following books have missing details:\n- " + "\n- ".join(invalid_books)
        st.error(error_message)
        return
    
    if st.button("Add Batch"):
        if not selected_books:
            st.error("No books selected for the batch.")
        else:
            try:
                batch_id = create_batch(conn, batch_name, printer_name, print_sent_date, selected_books)
                # Log the batch creation
                try:
                    log_activity(
                        conn,
                        st.session_state.user_id,
                        st.session_state.username,
                        st.session_state.session_id,
                        "added batch",
                        f"Batch ID: {batch_id}"
                    )
                except Exception as e:
                    st.error(f"Error logging batch creation: {str(e)}")
                st.success(f"Batch {batch_id} created successfully with {len(selected_books)} books!")
                st.rerun()  # Close dialog and refresh page
            except Exception as e:
                st.error(f"Error creating batch: {str(e)}")

@st.dialog("Edit Running Batch")
def edit_batch_dialog(running_batches):
    conn = connect_db()
    st.subheader("Edit Running Batch")
    
    if running_batches.empty:
        st.warning("No batch found")
        return

    batch_options = {f"{row['batch_name']} (ID: {row['batch_id']})": row['batch_id'] for _, row in running_batches.iterrows()}

    selected_batch_label = st.selectbox("Select Batch", list(batch_options.keys()))

    if not selected_batch_label:
        st.warning("No batch selected")
        return

    batch_id = batch_options.get(selected_batch_label)
    receive_date = st.date_input("Print Receive Date", value=datetime.now())
    
    if st.button("Update Batch"):
        try:
            update_batch_receive_date(conn, batch_id, receive_date)
            # Log the batch update
            try:
                log_activity(
                    conn,
                    st.session_state.user_id,
                    st.session_state.username,
                    st.session_state.session_id,
                    "updated batch",
                    f"Batch ID: {batch_id}"
                )
            except Exception as e:
                st.error(f"Error logging batch update: {str(e)}")
            st.success(f"Batch {batch_id} updated successfully!")
            st.rerun()  # Close dialog and refresh page
        except Exception as e:
            st.error(f"Error updating batch: {str(e)}")

# Batch details dialog for completed batches
@st.dialog("Batch Books Details", width="large")
def view_batch_books_dialog(batch_id, batch_name):
    conn = connect_db()
    st.subheader(f"Books in Batch: {batch_name} (ID: {batch_id})")
    
    batch_books = get_batch_books(conn, batch_id)
    if not batch_books.empty:
        # Calculate total unique books
        total_books = len(batch_books['book_id'].unique())
        st.markdown(f"**Total Books:** {total_books}")
        
        st.dataframe(batch_books[['book_id', 'title', 'copies_in_batch', 'book_size', 'binding', 'print_color', 'edition_number', 'book_pages']],
                     hide_index=True, column_config={
                         'book_id': st.column_config.TextColumn("Book ID"),
                         'title': st.column_config.TextColumn("Title"),
                         'copies_in_batch': st.column_config.NumberColumn("Copies in Batch"),
                         'book_size': st.column_config.TextColumn("Book Size"),
                         'binding': st.column_config.TextColumn("Binding"),
                         'print_color': st.column_config.TextColumn("Print Color"),
                         'edition_number': st.column_config.NumberColumn("Edition Number"),
                         'book_pages': st.column_config.NumberColumn("Number of Pages")
                     })
    else:
        st.info("No books found in this batch.")

# Streamlit app
def print_management_page():
    conn = connect_db()

    col1, col2, col3 = st.columns([8, 0.7, 1], vertical_alignment="bottom")
    with col1:
        st.write("## 📖 Print Management")
    with col2:
        if st.button(":material/refresh: Refresh", key="refresh", type="tertiary"):
            st.cache_data.clear()
    with col3:
        if st.button(":material/arrow_back: Go Back", key="back_button", type="tertiary", width="stretch"):
            st.switch_page('app.py')

    tab1, tab2, tab3, tab4 = st.tabs(["Ready for Print", "Reprint Eligible", "Running Batches", "Completed Batches"])
    
    with tab1:
        # Section 1: Show Ready-to-Print Books (First Prints)
        first_print_books = get_ready_to_print_books(conn)
        
        with st.container():
            col1, col2 = st.columns([16, 2], vertical_alignment="bottom")
            with col1:
                st.markdown(f'<div class="status-badge-red">Ready for Print <span class="badge-count">{len(first_print_books)}</span></div>', unsafe_allow_html=True)
            with col2:
                if st.button(":material/add: New Batch", type="secondary"):
                    create_batch_dialog()
            if not first_print_books.empty:    
                ready_to_print_column = [.6, 3, 0.8, 0.8, 0.8, 0.8, 0.8]
                
                with st.container(border=True):
                    cols = st.columns(ready_to_print_column)
                    cols[0].markdown('<div class="table-header">Book ID</div>', unsafe_allow_html=True)
                    cols[1].markdown('<div class="table-header">Title</div>', unsafe_allow_html=True)
                    cols[2].markdown('<div class="table-header">Date</div>', unsafe_allow_html=True)
                    cols[3].markdown('<div class="table-header">Copies</div>', unsafe_allow_html=True)
                    cols[4].markdown('<div class="table-header">Pages</div>', unsafe_allow_html=True)
                    cols[5].markdown('<div class="table-header">Binding</div>', unsafe_allow_html=True)
                    cols[6].markdown('<div class="table-header">Book Size</div>', unsafe_allow_html=True)

                    for _, book in first_print_books.iterrows():
                        cols = st.columns(ready_to_print_column)
                        cols[0].write(f'<div class="table-row">{book["book_id"]}</div>', unsafe_allow_html=True)
                        cols[1].markdown(f'<div class="table-row">{book["title"]}</div>', unsafe_allow_html=True)
                        cols[2].markdown(f'<div class="table-row">{book["date"].strftime("%Y-%m-%d") if book["date"] else ""}</div>', unsafe_allow_html=True)
                        cols[3].markdown(f'<div class="table-row">{book["num_copies"]}</div>', unsafe_allow_html=True)
                        cols[4].markdown(f'<div class="table-row">{book["book_pages"]}</div>', unsafe_allow_html=True)
                        cols[5].markdown(f'<div class="table-row">{book["binding"]}</div>', unsafe_allow_html=True)
                        cols[6].markdown(f'<div class="table-row">{book["book_size"]}</div>', unsafe_allow_html=True)
            else:
                st.info("No books are ready for first print.")
        
        st.markdown('<div class="container-spacing"></div>', unsafe_allow_html=True)

    with tab2:
        # Section 2: Show Reprint-Eligible Books (Unbatched Editions)
        reprint_eligible_books = get_reprint_eligible_books(conn)
        
        with st.container():
            st.markdown(f'<div class="status-badge-red">Books Eligible for Reprint <span class="badge-count">{len(reprint_eligible_books)}</span></div>', unsafe_allow_html=True)
            if not reprint_eligible_books.empty:
                ready_to_reprint_column = [.7, 3, 1, 1, 1, 1]
                with st.container(border=True):
                    cols = st.columns(ready_to_reprint_column)
                    cols[0].markdown('<div class="table-header">Book ID</div>', unsafe_allow_html=True)
                    cols[1].markdown('<div class="table-header">Title</div>', unsafe_allow_html=True)
                    cols[2].markdown('<div class="table-header">Date</div>', unsafe_allow_html=True)
                    cols[3].markdown('<div class="table-header">Pages</div>', unsafe_allow_html=True)
                    cols[4].markdown('<div class="table-header">Book Size</div>', unsafe_allow_html=True)
                    cols[5].markdown('<div class="table-header">Binding</div>', unsafe_allow_html=True)
                    
                    for _, book in reprint_eligible_books.iterrows():
                        cols = st.columns(ready_to_reprint_column)
                        cols[0].markdown(f'<div class="table-row">{book["book_id"]}</div>', unsafe_allow_html=True)
                        cols[1].markdown(f'<div class="table-row">{book["title"]}</div>', unsafe_allow_html=True)
                        cols[2].markdown(f'<div class="table-row">{book["date"].strftime("%Y-%m-%d") if book["date"] else ""}</div>', unsafe_allow_html=True)
                        cols[3].markdown(f'<div class="table-row">{book["book_pages"]}</div>', unsafe_allow_html=True)
                        cols[4].markdown(f'<div class="table-row">{book["book_size"]}</div>', unsafe_allow_html=True)
                        cols[5].markdown(f'<div class="table-row">{book["binding"]}</div>', unsafe_allow_html=True)
            else:
                st.info("No books are eligible for reprint.")
        
        st.markdown('<div class="container-spacing"></div>', unsafe_allow_html=True)

    with tab3:
        # Section 3: Manage Running Batches
        running_batches = get_running_batches(conn)
        with st.container():
            col1, col2 = st.columns([16, 2], vertical_alignment="bottom")
            with col1:
                st.markdown(f'<div class="status-badge-yellow">Running Batches (Sent) <span class="badge-count">{len(running_batches)}</span></div>', unsafe_allow_html=True)
            with col2:
                if st.button(":material/edit: Edit Batch", type="secondary"):
                    edit_batch_dialog(running_batches)
            if not running_batches.empty:
                with st.expander('View Running Batches', expanded=True):
                    for _, batch in running_batches.iterrows():
                        with st.container(border=False):
                            # Batch details in a clean layout
                            batch_books = get_batch_books(conn, batch['batch_id'])
                            st.markdown(f'<div class="status-badge-non">{batch["batch_name"]} (ID: {batch["batch_id"]})</div>', unsafe_allow_html=True)
                            details_cols = st.columns([2, 2, 2, 2, 2, 0.8])
                            details_cols[0].write(f" **Created:** {batch['created_at'].strftime('%Y-%m-%d')}")
                            details_cols[1].write(f"**Sent:** {batch['print_sent_date'].strftime('%Y-%m-%d')}")
                            details_cols[2].write(f"**Total Books:** {len(batch_books)}")
                            details_cols[3].write(f"**Total Copies:** {batch['total_copies']}")
                            details_cols[4].write(f"**Printer:** {batch['printer_name']}")
                            
                            # Add Excel download button
                            if not batch_books.empty:
                                # Prepare Excel file
                                excel_data = pd.DataFrame({
                                    'S.no.': range(1, len(batch_books) + 1),
                                    'Book Title': batch_books['title'],
                                    'Number of Book Copies': batch_books['copies_in_batch'],
                                    'Number of Pages': batch_books['book_pages'],
                                    'Book Size': batch_books['book_size'],
                                    'Book Pages': 'White 70 GSM',
                                    'Cover Page': '300 GSM Glossy',
                                    'Binding': 'Perfect Binding',
                                })
                                
                                # Convert to Excel
                                output = BytesIO()
                                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                    excel_data.to_excel(writer, index=False, sheet_name='Batch Books')
                                excel_bytes = output.getvalue()
                                
                                details_cols[5].download_button(
                                    label=" :material/download: Export",
                                    data=excel_bytes,
                                    file_name=f"batch_{batch['batch_id']}_books.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key=f"download_excel_{batch['batch_id']}",
                                    type="tertiary"
                                )
                            
                            # Books table
                            if not batch_books.empty:
                                running_batches_column = [0.8, 4, 0.7, 0.7, 0.7, 1, 1, 1.2]
                                with st.container(border=True):
                                    cols = st.columns(running_batches_column)
                                    cols[0].markdown('<div class="table-header">Book ID</div>', unsafe_allow_html=True)
                                    cols[1].markdown('<div class="table-header">Title</div>', unsafe_allow_html=True)
                                    cols[2].markdown('<div class="table-header">Edition</div>', unsafe_allow_html=True)
                                    cols[3].markdown('<div class="table-header">Copies</div>', unsafe_allow_html=True)
                                    cols[4].markdown('<div class="table-header">Pages</div>', unsafe_allow_html=True)
                                    cols[5].markdown('<div class="table-header">Book Size</div>', unsafe_allow_html=True)
                                    cols[6].markdown('<div class="table-header">Binding</div>', unsafe_allow_html=True)
                                    cols[7].markdown('<div class="table-header">Print Color</div>', unsafe_allow_html=True)

                                    for _, book in batch_books.iterrows():
                                        cols = st.columns(running_batches_column)
                                        cols[0].markdown(f'<div class="table-row">{book["book_id"]}</div>', unsafe_allow_html=True)
                                        cols[1].markdown(f'<div class="table-row">{book["title"]}</div>', unsafe_allow_html=True)
                                        cols[2].markdown(f'<div class="table-row">{book["edition_number"]}</div>', unsafe_allow_html=True)
                                        cols[3].markdown(f'<div class="table-row">{book["copies_in_batch"]}</div>', unsafe_allow_html=True)
                                        cols[4].markdown(f'<div class="table-row">{book["book_pages"]}</div>', unsafe_allow_html=True)
                                        cols[5].markdown(f'<div class="table-row">{book["book_size"]}</div>', unsafe_allow_html=True)
                                        cols[6].markdown(f'<div class="table-row">{book["binding"]}</div>', unsafe_allow_html=True)
                                        cols[7].markdown(f'<div class="table-row">{book["print_color"]}</div>', unsafe_allow_html=True)
                                        
                            else:
                                st.info("No books found in this batch.")
            else:
                st.info("No running batches found.")
        
        st.markdown('<div class="container-spacing"></div>', unsafe_allow_html=True)
    

    with tab4:
        # Section 4: Completed Batches with Custom Table
        completed_batches = conn.query("""
            SELECT 
                pb.batch_id, 
                pb.batch_name, 
                pb.created_at, 
                pb.print_receive_date, 
                pb.total_copies,
                COUNT(DISTINCT bd.print_id) AS total_books
            FROM 
                PrintBatches pb
            LEFT JOIN 
                BatchDetails bd ON pb.batch_id = bd.batch_id
            WHERE 
                pb.status = 'Received'
            GROUP BY 
                pb.batch_id, pb.batch_name, pb.created_at, pb.print_receive_date, pb.total_copies
            ORDER BY 
                pb.created_at DESC
        """, ttl=0)
        with st.container():
            st.markdown(f'<div class="status-badge-green">Completed Batches <span class="badge-count">{len(completed_batches)}</span></div>', unsafe_allow_html=True)
            if not completed_batches.empty:
                with st.container(border=True):
                    cols = st.columns([1, 2, 2, 2, 1, 1, 1])
                    cols[0].markdown('<div class="table-header">Batch ID</div>', unsafe_allow_html=True)
                    cols[1].markdown('<div class="table-header">Batch Name</div>', unsafe_allow_html=True)
                    cols[2].markdown('<div class="table-header">Created At</div>', unsafe_allow_html=True)
                    cols[3].markdown('<div class="table-header">Received Date</div>', unsafe_allow_html=True)
                    cols[4].markdown('<div class="table-header">Total Copies</div>', unsafe_allow_html=True)
                    cols[5].markdown('<div class="table-header">Total Books</div>', unsafe_allow_html=True)
                    cols[6].markdown('<div class="table-header">Action</div>', unsafe_allow_html=True)
                    
                    for _, batch in completed_batches.iterrows():
                        cols = st.columns([1, 2, 2, 2, 1, 1, 1], vertical_alignment="bottom")
                        cols[0].markdown(f'<div class="table-row">{batch["batch_id"]}</div>', unsafe_allow_html=True)
                        cols[1].markdown(f'<div class="table-row">{batch["batch_name"]}</div>', unsafe_allow_html=True)
                        cols[2].markdown(f'<div class="table-row">{batch["created_at"].strftime("%Y-%m-%d")}</div>', unsafe_allow_html=True)
                        cols[3].markdown(f'<div class="table-row">{batch["print_receive_date"].strftime("%Y-%m-%d") if batch["print_receive_date"] else ""}</div>', unsafe_allow_html=True)
                        cols[4].markdown(f'<div class="table-row">{batch["total_copies"]}</div>', unsafe_allow_html=True)
                        cols[5].markdown(f'<div class="table-row">{batch["total_books"]}</div>', unsafe_allow_html=True)
                        if cols[6].button(":material/visibility:", key=f"view_{batch['batch_id']}", type="secondary"):
                            view_batch_books_dialog(batch['batch_id'], batch['batch_name'])
            else:
                st.info("No completed batches found.")

if __name__ == "__main__":
    print_management_page()