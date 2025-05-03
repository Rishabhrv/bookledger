import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text


logo = "logo/logo_black.png"
fevicon = "logo/favicon_black.ico"
small_logo = "logo/favicon_white.ico"

st.set_page_config(page_title='AGPH Search', page_icon="🔍", layout="wide")

st.logo(logo,
size = "large",
icon_image = small_logo
)


# Database connection
def connect_db():
    try:
        @st.cache_resource
        def get_connection():
            return st.connection('mysql', type='sql')
        conn = get_connection()
        return conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

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
        COALESCE(pe.print_cost, 5.00) AS print_cost
    FROM 
        books b
    LEFT JOIN 
        PrintEditions pe ON b.book_id = pe.book_id 
        AND pe.edition_number = (SELECT MIN(edition_number) FROM PrintEditions WHERE book_id = b.book_id)
    WHERE 
        b.print_status = 0
        AND b.writing_complete = 1
        AND b.proofreading_complete = 1
        AND b.formatting_complete = 1
        AND b.cover_page_complete = 1
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
        b.book_id, b.title, b.date, pe.copies_planned, pe.book_size, pe.binding, pe.print_cost;
    """
    df = conn.query(query, ttl=0)  # Disable caching
    return df

# Fetch books eligible for reprint (latest unbatched edition only, not in running batches)
def get_reprint_eligible_books(conn):
    query = """
    SELECT 
        b.book_id, 
        b.title, 
        b.isbn,
        'Reprint' AS print_type,
        pe.book_size,
        pe.binding,
        pe.print_color,
        pe.print_cost,
        pe.copies_planned
    FROM 
        books b
    JOIN (
        SELECT 
            pe2.book_id,
            pe2.book_size,
            pe2.binding,
            pe2.print_color,
            pe2.print_cost,
            pe2.copies_planned,
            ROW_NUMBER() OVER (PARTITION BY pe2.book_id ORDER BY pe2.edition_number DESC, pe2.print_date DESC) AS rn
        FROM 
            PrintEditions pe2
        WHERE 
            NOT EXISTS (
                SELECT 1 
                FROM BatchDetails bd 
                WHERE bd.print_id = pe2.print_id
            )
    ) pe ON b.book_id = pe.book_id AND pe.rn = 1
    WHERE 
        b.print_status = 1
        AND NOT EXISTS (
            SELECT 1
            FROM BatchDetails bd
            JOIN PrintBatches pb ON bd.batch_id = pb.batch_id
            WHERE bd.print_id IN (SELECT print_id FROM PrintEditions pe3 WHERE pe3.book_id = b.book_id)
            AND pb.status = 'Sent'
        )
    GROUP BY 
        b.book_id, b.title, b.isbn, pe.book_size, pe.binding, pe.print_color, pe.print_cost, pe.copies_planned;
    """
    df = conn.query(query, ttl=0)  # Disable caching
    return df

# Fetch all existing batches
def get_batches(conn):
    query = """
    SELECT 
        batch_id, 
        batch_name, 
        created_at, 
        print_sent_date, 
        print_receive_date, 
        total_copies, 
        status, 
        printer_name
    FROM 
        PrintBatches
    ORDER BY 
        created_at DESC;
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
        pe.edition_number
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

# Create a new print edition for a book
def create_print_edition(conn, book_id, num_copies, book_size, binding, print_color, print_cost):
    with conn.session as session:
        # Calculate next edition number
        result = session.execute(
            text("SELECT COALESCE(MAX(edition_number), 0) + 1 AS next_edition FROM PrintEditions WHERE book_id = :book_id"),
            {"book_id": book_id}
        )
        edition_number = result.fetchone()[0]
        
        # Insert new print edition
        result = session.execute(
            text("""
                INSERT INTO PrintEditions 
                    (book_id, edition_number, book_size, binding, print_color, print_cost, copies_planned, print_date)
                VALUES 
                    (:book_id, :edition_number, :book_size, :binding, :print_color, :print_cost, :copies_planned, CURDATE())
            """),
            {
                "book_id": book_id,
                "edition_number": edition_number,
                "book_size": book_size,
                "binding": binding,
                "print_color": print_color,
                "print_cost": print_cost,
                "copies_planned": num_copies
            }
        )
        print_id = result.lastrowid
        session.commit()
    return print_id

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
        
        first_print_ids = []
        for book in selected_books:
            print_id = create_print_edition(
                conn, 
                book['book_id'], 
                book['num_copies'], 
                book['book_size'], 
                book['binding'], 
                book['print_color'], 
                book['print_cost']
            )
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
        
        session.execute(
            text("""
                UPDATE PrintBatches 
                SET print_receive_date = :receive_date, status = 'Received'
                WHERE batch_id = :batch_id
            """),
            {"receive_date": receive_date, "batch_id": batch_id}
        )
        session.commit()

# Batch creation dialog
@st.dialog("Create New Batch", width="large")
def create_batch_dialog():
    conn = connect_db()
    st.subheader("New Batch Details")
    
    batch_name = st.text_input("Batch Name", value=f"Batch {datetime.now().strftime('%Y-%m-%d')}")
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
            'print_cost': book['print_cost'],  # Use queried print_cost
            'print_type': book['print_type']
        })
    for _, book in reprint_books.iterrows():
        all_books.append({
            'book_id': book['book_id'],
            'title': book['title'],
            'num_copies': book['copies_planned'] if book['copies_planned'] else 100,
            'book_size': book['book_size'] if book['book_size'] else '6x9',
            'binding': book['binding'] if book['binding'] else 'Paperback',
            'print_color': book['print_color'] if book['print_color'] else 'Black & White',
            'print_cost': book['print_cost'] if book['print_cost'] else 5.00,
            'print_type': book['print_type']
        })
    
    # Multiselect with all books pre-selected
    book_options = [f"{book['title']} ({book['print_type']})" for book in all_books]
    default_books = book_options  # Pre-select all
    selected_titles = st.multiselect("Select Books for Batch", book_options, default=default_books)
    
    # Filter selected books
    selected_books = [book for book in all_books if f"{book['title']} ({book['print_type']})" in selected_titles]
    
    # Validate required fields for each selected book
    required_fields = ['num_copies', 'book_size', 'binding', 'print_color', 'print_cost']
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
                st.success(f"Batch {batch_id} created successfully with {len(selected_books)} books!")
                st.rerun()  # Close dialog and refresh page
            except Exception as e:
                st.error(f"Error creating batch: {str(e)}")

# Batch edit dialog
@st.dialog("Edit Running Batch")
def edit_batch_dialog(running_batches):
    conn = connect_db()
    st.subheader("Edit Running Batch")
    
    batch_options = {f"{row['batch_name']} (ID: {row['batch_id']})": row['batch_id'] for _, row in running_batches.iterrows()}
    selected_batch = st.selectbox("Select Batch", list(batch_options.keys()))
    batch_id = batch_options[selected_batch]
    receive_date = st.date_input("Print Receive Date", value=datetime.now())
    
    if st.button("Update Batch"):
        try:
            update_batch_receive_date(conn, batch_id, receive_date)
            st.success(f"Batch {batch_id} updated successfully!")
            st.rerun()  # Close dialog and refresh page
        except Exception as e:
            st.error(f"Error updating batch: {str(e)}")

# Streamlit app
def print_management_page():
    conn = connect_db()

    # Section 1: Show Ready-to-Print Books (First Prints)
    first_print_books = get_ready_to_print_books(conn)
    
    if not first_print_books.empty:    
        col1, col2 = st.columns([18, 2])
        with col1:
            st.write(f" ### {len(first_print_books)} Books ready for First Print")
        with col2:
            if st.button(":material/add: New Batch"):
                create_batch_dialog()
        st.dataframe(first_print_books[['book_id', 'title', 'date', 'num_copies', 'print_type', 'binding', 'book_size', 'print_cost']], 
                     hide_index=True, column_config={
                         'book_id': st.column_config.TextColumn("Book ID"),
                         'title': st.column_config.TextColumn("Title"),
                         'date': st.column_config.DateColumn("Date"),
                         'num_copies': st.column_config.NumberColumn("Number of Copies"),
                         'print_type': st.column_config.TextColumn("Print Type"),
                         'binding': st.column_config.TextColumn("Binding"),
                         'book_size': st.column_config.TextColumn("Book Size"),
                         'print_cost': st.column_config.NumberColumn("Print Cost")
                     })
    else:
        st.info("No books are ready for first print.")

    # Section 2: Show Reprint-Eligible Books (Unbatched Editions)
    reprint_eligible_books = get_reprint_eligible_books(conn)
    
    if not reprint_eligible_books.empty:
        st.write(f"### {len(reprint_eligible_books)} Books eligible for Reprint:")
        st.dataframe(reprint_eligible_books[['book_id', 'title','print_type', 'book_size', 'binding', 'print_cost']],
                     hide_index=True, column_config={
                         'book_id': st.column_config.TextColumn("Book ID"),
                         'title': st.column_config.TextColumn("Title"),
                         'print_type': st.column_config.TextColumn("Print Type"),
                         'book_size': st.column_config.TextColumn("Book Size"),
                         'binding': st.column_config.TextColumn("Binding"),
                         'print_cost': st.column_config.NumberColumn("Print Cost")
                     })
    else:
        st.info("No books are eligible for reprint.")

    # Section 3: Manage Existing Batches
    # Running Batches with Book Details
    running_batches = get_running_batches(conn)
    if not running_batches.empty:
        col1, col2 = st.columns([18, 2])
        with col1:
            st.write(f"### {len(running_batches)} Running Batches (status: Sent):")
        with col2:
            if st.button(":material/edit: Edit Batch"):
                edit_batch_dialog(running_batches)
        for _, batch in running_batches.iterrows():
            st.markdown(f"##### Batch: {batch['batch_name']} (ID: {batch['batch_id']})")
            st.write(f"Created: {batch['created_at']}, Sent: {batch['print_sent_date']}, Total Copies: {batch['total_copies']}, Printer: {batch['printer_name']}")
            batch_books = get_batch_books(conn, batch['batch_id'])
            if not batch_books.empty:
                st.dataframe(batch_books[['book_id', 'title', 'copies_in_batch', 'book_size', 'binding', 'print_color', 'print_cost', 'edition_number']],
                             hide_index=True, column_config={
                                 'book_id': st.column_config.TextColumn("Book ID"),
                                 'title': st.column_config.TextColumn("Title"),
                                 'copies_in_batch': st.column_config.NumberColumn("Copies in Batch"),
                                 'book_size': st.column_config.TextColumn("Book Size"),
                                 'binding': st.column_config.TextColumn("Binding"),
                                 'print_color': st.column_config.TextColumn("Print Color"),
                                 'print_cost': st.column_config.NumberColumn("Print Cost"),
                                 'edition_number': st.column_config.NumberColumn("Edition Number")
                             })
            else:
                st.info("No books found in this batch.")
    else:
        st.info("No running batches found.")
    
    # All Batches with Completed Batch Details
    st.subheader("All Batches")
    batches = get_batches(conn)
    if not batches.empty:
        st.write(f"Found {len(batches)} total batches:")
        st.dataframe(batches[['batch_id', 'batch_name', 'created_at', 'print_sent_date', 'print_receive_date', 'status', 'total_copies']],
                     hide_index=True, column_config={
                         'batch_id': st.column_config.TextColumn("Batch ID"),
                         'batch_name': st.column_config.TextColumn("Batch Name"),
                         'created_at': st.column_config.DateColumn("Created At"),
                         'print_sent_date': st.column_config.DateColumn("Print Sent Date"),
                         'print_receive_date': st.column_config.DateColumn("Print Receive Date"),
                         'status': st.column_config.TextColumn("Status"),
                         'total_copies': st.column_config.NumberColumn("Total Copies")
                     })
        
        st.subheader("Completed Batch Details")
        completed_batches = batches[batches['status'] == 'Received']
        if not completed_batches.empty:
            for _, batch in completed_batches.iterrows():
                st.markdown(f"##### Batch: {batch['batch_name']} (ID: {batch['batch_id']})")
                st.write(f"Created: {batch['created_at']}, Sent: {batch['print_sent_date']}, Received: {batch['print_receive_date']}, Total Copies: {batch['total_copies']}, Printer: {batch['printer_name']}")
                batch_books = get_batch_books(conn, batch['batch_id'])
                if not batch_books.empty:
                    st.dataframe(batch_books[['book_id', 'title', 'copies_in_batch', 'book_size', 'binding', 'print_color', 'print_cost', 'edition_number']],
                                 hide_index=True, column_config={
                                     'book_id': st.column_config.TextColumn("Book ID"),
                                     'title': st.column_config.TextColumn("Title"),
                                     'copies_in_batch': st.column_config.NumberColumn("Copies in Batch"),
                                     'book_size': st.column_config.TextColumn("Book Size"),
                                     'binding': st.column_config.TextColumn("Binding"),
                                     'print_color': st.column_config.TextColumn("Print Color"),
                                     'print_cost': st.column_config.NumberColumn("Print Cost"),
                                     'edition_number': st.column_config.NumberColumn("Edition Number")
                                 })
                else:
                    st.info("No books found in this batch.")
        else:
            st.info("No completed batches found.")
    else:
        st.info("No batches found.")

if __name__ == "__main__":
    print_management_page()