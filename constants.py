# constants.py

from sqlalchemy import text
import streamlit as st
from datetime import datetime
import pytz
import json
import pandas as pd

ACCESS_TO_BUTTON = {
    # Loop buttons (table)
    "ISBN": "manage_isbn_dialog",
    "Payment": "manage_price_dialog",
    "Authors": "edit_author_dialog",
    "Operations": "edit_operation_dialog",
    "Printing & Delivery": "edit_inventory_delivery_dialog",
    "DatadashBoard": "datadashoard",
    "Advance Search": "advance_search",
    "Team Dashboard": "team_dashboard",
    "Print Management": "print_management",
    "Inventory": "inventory",
    "Open Author Positions": "open_author_positions",
    "Pending Work": "pending_books",
    "IJISEM": "ijisem",
    "Academic Guru": "academic_guru",
    "Tasks": "tasks",
    "Details": "details",
    "Message": "messages",
    "Attendance": "attendance",
    "Extra Books": "extra_books",
    "Sales Tracking": "sales_track",
    # Non-loop buttons
    "Add Book": "add_book_dialog",
    "Pending Checklist": "pending_checklist_dialog",
    "Authors Edit": "edit_author_detail"
}

BASE_URL  = st.secrets["general"]["BASE_URL"]
CHAT_URL  = st.secrets["general"]["CHAT_URL"]

# Predefined list of educational subjects
VALID_SUBJECTS = [
    "Mathematics", "Physics", "Chemistry", "Biology", "Computer Science",
    "History", "Geography", "Literature", "Economics", "Business Studies",
    "Political Science", "Sociology", "Psychology", "Engineering", "Medicine",
    "Education", "General Science", "Management", "Marketing", "Medical", "Self Help", 
    "Physical Education", "Commerce", "Law", "Social Science"
]

@st.dialog("Authentication Failed", dismissible=False)
def error_dialog(error_message):
    st.error(error_message)
    st.stop()


@st.cache_resource
def connect_db():
    try:
        return st.connection("mysql", type="sql")
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

@st.cache_resource
def connect_ijisem_db():
    try:
        return st.connection("ijisem", type="sql")
    except Exception as e:
        st.error(f"Error connecting to IJISET DB: {e}")
        st.stop()


@st.cache_resource
def connect_ict_db():
    try:
        return st.connection("ict", type="sql")
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

@st.cache_resource
def connect_db_ag():
    try:
        conn = st.connection('ag', type='sql')
        return conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()


def get_page_url(page_path, token):
    """Generate a URL with the token as a query parameter."""
    # Decide which base URL to use based on the path
    if page_path.startswith("/"):
        base = CHAT_URL
        return f"{base}?token={token}"
    else:
        base = BASE_URL
        return f"{base}/{page_path}?token={token}"

def log_activity(conn, user_id, username, session_id, action, details, session=None):
    try:
        # Get current time in Indian Standard Time
        ist = pytz.timezone('Asia/Kolkata')
        ist_time = datetime.now(ist)

        params = {
            "user_id": user_id,
            "username": username,
            "session_id": session_id,
            "action": action,
            "details": details,
            "timestamp": ist_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        stmt = text("""
            INSERT INTO activity_log (user_id, username, session_id, action, details, timestamp)
            VALUES (:user_id, :username, :session_id, :action, :details, :timestamp)
        """)

        if session:
            session.execute(stmt, params)
        else:
            with conn.session as s:
                s.execute(stmt, params)
                s.commit()
    except Exception as e:
        st.error(f"Error logging activity: {e}")


def clean_old_logs(conn, days_to_keep=180):
    """
    Delete activity_log entries older than `days_to_keep` days and log the cleanup action.

    Parameters:
    - conn: Database connection object
    - days_to_keep: Number of days to retain logs (default is 30)
    """
    try:
        with conn.session as s:
            # Delete logs older than `days_to_keep` days
            result = s.execute(
                text(f"""
                    DELETE FROM activity_log 
                    WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL :days DAY
                """),
                {"days": days_to_keep}
            )
            deleted_count = result.rowcount
            s.commit()

            # Log the cleanup action
            if deleted_count > 0:
                log_activity(
                    conn,
                    user_id=st.session_state.get("user_id", "system"),
                    username=st.session_state.get("username", "system"),
                    session_id=st.session_state.get("session_id", "system"),
                    action="cleaned old logs",
                    details=f"Deleted {deleted_count} log entries older than {days_to_keep} days"
                )
    except Exception as e:
        st.error(f"Error cleaning old logs: {str(e)}")


def initialize_click_and_session_id():
    # Initialize session state from query parameters
    if "session_id" not in st.session_state:
        session_id = st.query_params.get("session_id", [None])[0]
        if not session_id:
            error_dialog("⚠️ Access Denied: You don't have permission to access this page.")
        if session_id:
            st.session_state.session_id = session_id
        
    if "click_id" not in st.session_state:
        click_id = st.query_params.get("click_id", [None])[0]
        if not click_id:
            error_dialog("⚠️ Access Denied: You don't have permission to access this page.")
        if click_id:
            st.session_state.click_id = click_id
    
    return st.session_state.session_id, st.session_state.click_id

def clean_url_params():
    # ✅ Clean URL after extracting values
    if "session_id" in st.query_params:
        del st.query_params["session_id"]
    if "click_id" in st.query_params:
        del st.query_params["click_id"]

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
        pe.page_number,
        pe.page_type,
        pe.cover_type,
        pe.print_id
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
            (b.is_thesis_to_book = 1 AND b.proofreading_complete = 1 AND b.formatting_complete = 1 AND b.cover_page_complete = 1)
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
        b.book_id, b.title, b.date, pe.copies_planned, pe.book_size, pe.binding, pe.print_cost, pe.page_number, pe.page_type, pe.cover_type, pe.print_id;
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
            pe.page_number,
            pe.page_type,
            pe.cover_type,
            pe.print_id
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
                pe2.page_number,
                pe2.page_type,
                pe2.cover_type,
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
            b.book_id, b.title, b.isbn, pe.book_size, pe.binding, pe.print_color, pe.print_cost, pe.copies_planned, pe.page_number, pe.page_type, pe.cover_type, pe.print_id;
    """
    df = conn.query(query, ttl=0)  # Disable caching
    return df


def get_total_unread_count(ict_conn, user_id):
    """
    Calculates total unread messages (Private + Group) for a specific user.
    Returns 0 if user_id is invalid or no unread messages found.
    """
    if not user_id or user_id == "Unknown":
        return 0

    try:
        # 1. Private Chat Unread
        private_query = f"""
            SELECT COUNT(*) AS count
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE m.sender_id != {user_id} 
            AND m.seen = 0
            AND (c.user1_id = {user_id} OR c.user2_id = {user_id})
        """
        private_res = ict_conn.query(private_query, ttl=0, show_spinner = False)
        private_count = private_res.iloc[0]["count"] if not private_res.empty else 0

        # 2. Group Chat Unread
        group_query = f"""
            SELECT COUNT(*) AS count
            FROM group_messages gm
            JOIN group_members gu ON gm.group_id = gu.group_id
            WHERE gu.user_id = {user_id}
            AND gm.sender_id != {user_id}
            AND gm.id NOT IN (
                SELECT message_id 
                FROM group_message_seen 
                WHERE user_id = {user_id}
            )
        """
        group_res = ict_conn.query(group_query, ttl=0, show_spinner = False)
        group_count = group_res.iloc[0]["count"] if not group_res.empty else 0

        return int(private_count + group_count)

    except Exception as e:
        # Optional: st.error(f"Error fetching unread counts: {e}")
        return 0
    
# Function to check if all conditions are met for ready_to_print
def check_ready_to_print(book_id, conn):
    query = """
    SELECT CASE 
        WHEN (
            (b.is_publish_only = 1 OR b.is_thesis_to_book = 1 OR b.writing_complete = 1)
            AND b.proofreading_complete = 1 
            AND b.formatting_complete = 1 
            AND b.cover_page_complete = 1
            AND NOT EXISTS (
                SELECT 1 
                FROM book_authors ba 
                WHERE ba.book_id = :book_id 
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
        ) THEN 1 
        ELSE 0 
    END AS ready_to_print
    FROM books b
    WHERE b.book_id = :book_id
    """
    result = conn.query(query, params={"book_id": book_id}, ttl=0, show_spinner=False)
    return result.iloc[0]['ready_to_print'] == 1



def fetch_tags(conn):

    try:
        # Fetch and process tags
        with conn.session as s:
            tag_query = text("SELECT tags FROM books WHERE tags IS NOT NULL AND tags != ''")
            all_tags = s.execute(tag_query).fetchall()
            
            unique_tags = set()
            for row in all_tags[:5]:
                if row[0] and isinstance(row[0], str):
                    try:
                        tags = json.loads(row[0])  # Parse JSON array
                        unique_tags.update(tags)
                    except json.JSONDecodeError:
                        st.error(f"Invalid JSON in tags: {row[0]} -> Skipped")
                else:
                    st.error(f"Raw tag: {row[0]} -> Skipped (invalid or empty)")
            
            # Collect unique tags from all rows
            for row in all_tags:
                if row[0] and isinstance(row[0], str):
                    try:
                        tags = json.loads(row[0])
                        unique_tags.update(tags)
                    except json.JSONDecodeError:
                        st.write(f"Invalid JSON in tags: {row[0]} -> Skipped")
            
            # Convert to sorted list
            sorted_tags = sorted(unique_tags)

            return sorted_tags
    except Exception as e:
        st.error(f"Error fetching tags: {e}")
        return []
    
# New function to fetch detailed print information for a specific book_id
def fetch_print_details(book_id, conn):
    query = """
    SELECT pe.book_id, pe.print_id, bd.batch_id, pe.copies_planned, pb.print_sent_date, pb.print_receive_date, pb.status
    FROM PrintEditions pe
    LEFT JOIN BatchDetails bd ON pe.print_id = bd.print_id
    LEFT JOIN PrintBatches pb ON bd.batch_id = pb.batch_id
    WHERE pe.book_id = :book_id
    """
    return conn.query(query, params={'book_id': book_id}, show_spinner=False)

@st.cache_data
def fetch_all_book_authors(book_ids, _conn):
    if not book_ids:  # Handle empty book_ids
        return pd.DataFrame(columns=[
            'id', 'book_id', 'author_id', 'name', 'email', 'phone', 'author_position',
            'welcome_mail_sent', 'corresponding_agent', 'publishing_consultant',
            'photo_recive', 'id_proof_recive', 'author_details_sent',
            'cover_agreement_sent', 'agreement_received', 'digital_book_sent',
            'printing_confirmation', 'delivery_address', 
            'address_line1', 'address_line2', 'city_del', 'state_del', 'pincode', 'country',
            'delivery_charge', 'number_of_books', 'total_amount', 'delivery_date',
            'tracking_id', 'delivery_vendor', 'amount_paid', 'isbn_sent_at'
        ])
    query = """
    SELECT ba.id, ba.book_id, ba.author_id, a.name, a.email, a.phone,
           ba.author_position, ba.welcome_mail_sent, ba.corresponding_agent, 
           ba.publishing_consultant, ba.photo_recive, ba.id_proof_recive, 
           ba.author_details_sent, ba.cover_agreement_sent, ba.agreement_received, 
           ba.digital_book_sent, ba.printing_confirmation, ba.delivery_address, 
           ba.address_line1, ba.address_line2, ba.city_del, ba.state_del, ba.pincode, ba.country,
           ba.delivery_charge, ba.number_of_books, ba.total_amount,
           ba.delivery_date, ba.tracking_id, ba.delivery_vendor, ba.isbn_sent_at,
           COALESCE((SELECT SUM(amount) FROM author_payments WHERE book_author_id = ba.id AND status = 'Approved'), 0) as amount_paid
    FROM book_authors ba
    JOIN authors a ON ba.author_id = a.author_id
    WHERE ba.book_id IN :book_ids
    """
    try:
        return _conn.query(query, params={'book_ids': tuple(book_ids)}, show_spinner=False)
    except Exception as e:
        st.error(f"Error fetching book authors: {e}")
        return pd.DataFrame(columns=[
            'id', 'book_id', 'author_id', 'name', 'email', 'phone', 'author_position',
            'welcome_mail_sent', 'corresponding_agent', 'publishing_consultant',
            'photo_recive', 'id_proof_recive', 'author_details_sent',
            'cover_agreement_sent', 'agreement_received', 'digital_book_sent',
            'printing_confirmation', 'delivery_address', 'delivery_charge',
            'number_of_books', 'total_amount', 'delivery_date',
            'tracking_id', 'delivery_vendor', 'amount_paid'
        ])

@st.cache_data
def fetch_all_printeditions(book_ids, _conn):
    if not book_ids:  # Handle empty book_ids
        return pd.DataFrame(columns=['book_id', 'print_id', 'status'])
    query = """
    SELECT book_id, print_id, status
    FROM PrintEditions
    WHERE book_id IN :book_ids
    """
    try:
        return _conn.query(query, params={'book_ids': tuple(book_ids)}, show_spinner=False)
    except Exception as e:
        st.error(f"Error fetching print editions: {e}")
        return pd.DataFrame(columns=['book_id', 'print_id', 'status'])

def show_book_details(book_id, book_row, authors_df, printeditions_df):
    conn = connect_db()
    # Calculate days since enrolled
    enrolled_date = book_row['date'] if pd.notnull(book_row['date']) else None
    if enrolled_date:
        # Convert both to date objects
        today = datetime.now().date()
        enrolled_date = enrolled_date.date() if hasattr(enrolled_date, 'date') else enrolled_date
        days_since_enrolled = (today - enrolled_date).days
    else:
        days_since_enrolled = "N/A"
    
    # Count authors
    author_count = len(authors_df[authors_df['book_id'] == book_id])

    if book_row.get('deliver', 0) == 0:
        deliver_status = "Undelivered"
    else:
        deliver_status = "Delivered"

    # Book Title and Archive Toggle

    st.markdown(f"<div class='book-title'>{book_row['title']} (ID: {book_id})</div>", unsafe_allow_html=True)
    # Book Info in Compact Grid Layout
    st.markdown("<div class='info-grid'>", unsafe_allow_html=True)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"<div class='info-box'><span class='info-label'>Publisher:</span>{book_row['publisher']}</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='info-box'><span class='info-label'>Enrolled:</span>{enrolled_date.strftime('%d %b %Y') if enrolled_date else 'N/A'}</div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='info-box'><span class='info-label'>Since:</span>{days_since_enrolled} days</div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='info-box'><span class='info-label'>Authors:</span>{author_count}</div>", unsafe_allow_html=True)
    with col5:
        st.markdown(f"<div class='info-box'><span class='info-label'>Status:</span>{deliver_status}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ISBN Status Table
    st.markdown("<h4 class='section-title'>ISBN Status</h4>", unsafe_allow_html=True)
    
    # Determine ISBN Status
    apply_isbn = book_row.get('apply_isbn', 0) == 1
    isbn_val = book_row.get('isbn')
    isbn_received = pd.notnull(isbn_val) and str(isbn_val).strip() != ''
    isbn_date_raw = book_row.get('isbn_receive_date')
    
    if isbn_date_raw and pd.notnull(isbn_date_raw):
        try:
            isbn_date = pd.to_datetime(isbn_date_raw).strftime('%d %b %Y')
        except:
            isbn_date = str(isbn_date_raw)
    else:
        isbn_date = "-"

    isbn_table_html = f"""
    <table class='compact-table'>
        <tr><th>Applied</th><th>Received</th><th>Received Date</th><th>ISBN</th></tr>
        <tr>
            <td>{'✅' if apply_isbn else '❌'}</td>
            <td>{'✅' if isbn_received else '❌'}</td>
            <td>{isbn_date}</td>
            <td>{isbn_val if isbn_received else '-'}</td>
        </tr>
    </table>
    """
    st.markdown(isbn_table_html, unsafe_allow_html=True)

    # Author Checklists (Full Sequence)
    st.markdown("<h4 class='section-title'>Author Checklist</h4>", unsafe_allow_html=True)
    book_authors_df = authors_df[authors_df['book_id'] == book_id]
    if not book_authors_df.empty:
        checklist_columns = [
            'welcome_mail_sent', 'author_details_sent', 'photo_recive',
            'cover_agreement_sent', 'digital_book_sent', 'id_proof_recive',
            'agreement_received', 'printing_confirmation'
        ]
        checklist_labels = [
            'Welcome', 'Details', 'Photo',
            'Cover/Agr', 'Digital', 'ID Proof', 'Agreement', 'Print Conf'
        ]
        
        # Build HTML table for full checklist
        table_html = """
        <style>
            .compact-table {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 12px;
                color: #1f2937;
                border-collapse: collapse;
                width: 100%;
            }
            .compact-table th, .compact-table td {
                padding: 8px 10px;
                text-align: center;
                border-bottom: 1px solid #e2e8f0;
            }
            .compact-table th {
                background: #f1f5f9;
                font-weight: 600;
            }
            .compact-table td {
                color: #4b5563;
            }
        </style>
        <table class='compact-table'>
            <tr><th>ID</th><th>Name</th><th>Consultant</th><th>Pos</th><th>Payment</th>
        """
        for label in checklist_labels:
            table_html += f"<th>{label}</th>"
        table_html += "</tr>"
        
        for _, author in book_authors_df.iterrows():
            # Payment status logic
            total = float(author.get('total_amount', 0) or 0)
            paid = float(author.get('amount_paid', 0) or 0)
            if total <= 0:
                p_status = '<span style="color:#666; font-size:10px;">⚪ Pending</span>'
            elif paid >= total:
                p_status = '<span style="color:#166534; font-size:10px;">✅ Paid</span>'
            elif paid > 0:
                p_status = '<span style="color:#854d0e; font-size:10px;">🟠 Partial</span>'
            else:
                p_status = '<span style="color:#b91c1c; font-size:10px;">🔴 Unpaid</span>'

            table_html += f"<tr><td>{author['author_id']}</td><td>{author['name']}</td><td>{author['publishing_consultant']}</td><td>{author['author_position']}</td><td>{p_status}</td>"
            for col, label in zip(checklist_columns, checklist_labels):
                status = '✅' if author[col] else '❌'
                table_html += f"<td>{status}</td>"
            table_html += "</tr>"
        table_html += "</table>"
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("No authors found for this book.")


    # Operations Status
    st.markdown("<h4 class='section-title'>Operations Status</h4>", unsafe_allow_html=True)
    operations = [
        ('Writing', 'writing_start', 'writing_end', 'writing_by'),
        ('Proofreading', 'proofreading_start', 'proofreading_end', 'proofreading_by'),
        ('Formatting', 'formatting_start', 'formatting_end', 'formatting_by'),
        ('Cover Design', 'cover_start', 'cover_end', 'cover_by')
    ]
    # Check if book is publish-only or thesis-to-book
    is_publish_only = book_row.get('is_publish_only', 0) == 1
    is_thesis_to_book = book_row.get('is_thesis_to_book', 0) == 1
    
    table_html = "<table class='compact-table'><tr><th>Operation</th><th>Start</th><th>End</th><th>By</th><th>Status</th></tr>"
    for op_name, start_field, end_field, by_field in operations:
        by_who = book_row.get(by_field)
        by_who = by_who if pd.notnull(by_who) and str(by_who).strip() != '' else '-'
        
        start_val = book_row.get(start_field)
        end_val = book_row.get(end_field)
        
        start_str = start_val.strftime('%d %b %Y') if pd.notnull(start_val) else '-'
        end_str = end_val.strftime('%d %b %Y') if pd.notnull(end_val) else '-'
        
        if op_name == 'Writing' and (is_publish_only or is_thesis_to_book):
            status = '📖 Publish Only' if is_publish_only else '📚 Thesis to Book'
            by_who = '-'
            start_str = '-'
            end_str = '-'
        else:
            if pd.notnull(start_val) and pd.notnull(end_val):
                status = '✅ Done'
            elif pd.notnull(start_val):
                status = '⏳ Active'
            else:
                status = '❌ Pending'
        table_html += f"<tr><td>{op_name}</td><td>{start_str}</td><td>{end_str}</td><td>{by_who}</td><td>{status}</td></tr>"
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)

    # Correction History
    requests_query = """
    SELECT ac.*, COALESCE(a.name, 'Internal Team') AS author_name 
    FROM author_corrections ac
    LEFT JOIN authors a ON ac.author_id = a.author_id
    WHERE ac.book_id = :book_id 
    ORDER BY ac.created_at DESC
    """
    corrections_query = """
    SELECT * FROM corrections 
    WHERE book_id = :book_id 
    ORDER BY correction_start DESC
    """
    
    requests_df = conn.query(requests_query, params={"book_id": str(book_id)}, show_spinner=False)
    corrections_df = conn.query(corrections_query, params={"book_id": str(book_id)}, show_spinner=False)

    if not requests_df.empty or not corrections_df.empty:
        with st.expander("📝 Correction History", expanded=False):
            if not requests_df.empty:
                st.markdown("**Correction Requests**")
                req_table = "<table class='compact-table'><tr><th>Source</th><th>Round</th><th>Date</th><th>Correction</th></tr>"
                for _, req in requests_df.iterrows():
                    date_str = req['created_at'].strftime('%d %b %Y, %I:%M %p') if pd.notnull(req['created_at']) else '-'
                    text_val = req['correction_text'] if pd.notnull(req['correction_text']) and str(req['correction_text']).strip() != '' else "File uploaded"
                    
                    is_internal = pd.isnull(req['author_id'])
                    if is_internal:
                        source_badge = '<span style="background-color:#F3E5F5; color:#8E24AA; padding:2px 6px; border-radius:8px; font-size:10px; font-weight:bold;">Internal Team</span>'
                    else:
                        source_badge = f'<span style="background-color:#E3F2FD; color:#1976D2; padding:2px 6px; border-radius:8px; font-size:10px; font-weight:bold;">{req["author_name"]}</span>'
                    
                    req_table += f"<tr><td>{source_badge}</td><td>{req['round_number']}</td><td>{date_str}</td><td>{text_val}</td></tr>"
                req_table += "</table>"
                st.markdown(req_table, unsafe_allow_html=True)
            
            if not corrections_df.empty:
                st.markdown("<br>**Team Correction Actions**", unsafe_allow_html=True)
                corr_table = "<table class='compact-table'><tr><th>Section</th><th>Round</th><th>Worker</th><th>Start</th><th>End</th></tr>"
                for _, corr in corrections_df.iterrows():
                    start_str = corr['correction_start'].strftime('%d %b %Y, %I:%M %p') if pd.notnull(corr['correction_start']) else '-'
                    end_str = corr['correction_end'].strftime('%d %b %Y, %I:%M %p') if pd.notnull(corr['correction_end']) else '⏳ Active'
                    
                    section_display = corr['section'].capitalize()
                    if corr.get('is_internal') == 1:
                        section_display += ' <span style="background-color:#F3E5F5; color:#8E24AA; padding:1px 4px; border-radius:4px; font-size:9px; font-weight:bold;">Internal Team</span>'
                        
                    corr_table += f"<tr><td>{section_display}</td><td>{corr['round_number']}</td><td>{corr['worker']}</td><td>{start_str}</td><td>{end_str}</td></tr>"
                corr_table += "</table>"
                st.markdown(corr_table, unsafe_allow_html=True)


    st.markdown("<h4 class='section-title'>Print Editions</h4>", unsafe_allow_html=True)
    book_print_details_df = fetch_print_details(book_id, conn)
    
    # Check for basic print editions if detailed ones are missing
    book_printeditions_df = printeditions_df[printeditions_df['book_id'] == book_id]
    
    has_prints = not book_print_details_df.empty or not book_printeditions_df.empty
    
    if has_prints:
        # Show Print Editions Table
        if not book_print_details_df.empty:
            table_html = "<table class='compact-table'><tr><th>Batch ID</th><th>Copies</th><th>Sent Date</th><th>Receive Date</th><th>Status</th></tr>"
            for _, row in book_print_details_df.iterrows():
                sent_date = row['print_sent_date'].strftime('%d %b %Y') if pd.notnull(row['print_sent_date']) else 'N/A'
                receive_date = row['print_receive_date'].strftime('%d %b %Y') if pd.notnull(row['print_receive_date']) else 'N/A'
                batch_id = row['batch_id'] if pd.notnull(row['batch_id']) else 'N/A'
                copies = row['copies_planned'] if pd.notnull(row['copies_planned']) else 'N/A'
                table_html += f"<tr><td>{batch_id}</td><td>{copies}</td><td>{sent_date}</td><td>{receive_date}</td><td>{row['status']}</td></tr>"
            table_html += "</table>"
            st.markdown(table_html, unsafe_allow_html=True)
        elif not book_printeditions_df.empty:
            table_html = "<table class='compact-table'><tr><th>Print ID</th><th>Status</th></tr>"
            for _, row in book_printeditions_df.iterrows():
                table_html += f"<tr><td>{row['print_id']}</td><td>{row['status']}</td></tr>"
            table_html += "</table>"
            st.markdown(table_html, unsafe_allow_html=True)

        # Author Delivery Table (Only if printed)
        st.markdown("<h4 class='section-title'>Author Delivery</h4>", unsafe_allow_html=True)
        if not book_authors_df.empty:
            table_html = "<table class='compact-table'><tr><th>Author</th><th>Status</th><th>Copies</th><th>Date</th></tr>"
            for _, author in book_authors_df.iterrows():
                delivery_date = author.get('delivery_date')
                if pd.notnull(delivery_date):
                    try:
                        d_date = pd.to_datetime(delivery_date).strftime('%d %b %Y')
                    except:
                        d_date = str(delivery_date)
                    status = "✅ Delivered"
                else:
                    d_date = "-"
                    status = "❌ Pending"
                table_html += f"<tr><td>{author['name']}</td><td>{status}</td><td>{author.get('number_of_books', '❌ Pending')}</td><td>{d_date}</td></tr>"
            table_html += "</table>"
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.info("No authors found.")

    else:
        st.info("Book not printed yet.")

    # Additional Details: Links & Inventory (Only if printed)
    if has_prints:
        st.markdown("---")
        col_links, col_inv = st.columns(2)

        with col_links:
            st.markdown("<h4 class='section-title'>Store Links</h4>", unsafe_allow_html=True)
            links_data = [
                ("Amazon", book_row.get('amazon_link'), "https://img.icons8.com/color/48/000000/amazon.png"),
                ("Flipkart", book_row.get('flipkart_link'), "https://img.icons8.com/?size=100&id=UU2im0hihoyi&format=png&color=000000"),
                ("Google Books", book_row.get('google_link'), "https://img.icons8.com/color/48/000000/google-logo.png"),
                ("AGPH Store", book_row.get('agph_link'), "https://img.icons8.com/fluency/48/shopping-bag.png")
            ]
            
            table_html = "<table class='compact-table'><tr><th>Store</th><th>Link</th></tr>"
            for name, link, icon in links_data:
                if link and str(link).strip() and str(link) != 'None':
                    status = f'<a href="{link}" target="_blank"><img src="{icon}" width="24" height="24" title="{name}"></a>'
                else:
                    status = "❌"
                table_html += f"<tr><td>{name}</td><td>{status}</td></tr>"
            table_html += "</table>"
            st.markdown(table_html, unsafe_allow_html=True)

        with col_inv:
            st.markdown("<h4 class='section-title'>Inventory</h4>", unsafe_allow_html=True)
            try:
                # Total Printed
                total_printed = book_print_details_df[book_print_details_df['status'] == 'Received']['copies_planned'].sum() if not book_print_details_df.empty else 0

                # Fetch inventory sales
                inv_res = conn.query(f"SELECT amazon_sales, flipkart_sales, website_sales, direct_sales FROM inventory WHERE book_id = '{book_id}'", show_spinner=False)
                
                if not inv_res.empty:
                    inv_data = inv_res.iloc[0]
                    amazon = int(inv_data['amazon_sales']) if pd.notnull(inv_data['amazon_sales']) else 0
                    flipkart = int(inv_data['flipkart_sales']) if pd.notnull(inv_data['flipkart_sales']) else 0
                    website = int(inv_data['website_sales']) if pd.notnull(inv_data['website_sales']) else 0
                    direct = int(inv_data['direct_sales']) if pd.notnull(inv_data['direct_sales']) else 0
                else:
                    amazon = flipkart = website = direct = 0
                
                total_sales = amazon + flipkart + website + direct

                # Author Copies
                author_copies = book_authors_df['number_of_books'].fillna(0).astype(int).sum() if not book_authors_df.empty else 0
                
                current_inv = int(total_printed - total_sales - author_copies)
                
                # Inventory Table
                inv_table_html = f"""
                <table class='compact-table'>
                    <tr><th>Category</th><th>Count</th></tr>
                    <tr><td>Total Printed</td><td>{total_printed}</td></tr>
                    <tr><td>Amazon Sales</td><td>{amazon}</td></tr>
                    <tr><td>Flipkart Sales</td><td>{flipkart}</td></tr>
                    <tr><td>Website Sales</td><td>{website}</td></tr>
                    <tr><td>Direct Sales</td><td>{direct}</td></tr>
                    <tr><td>Author Copies</td><td>{author_copies}</td></tr>
                    <tr style='font-weight:bold; background-color:#f8f9fa;'><td>Current Stock</td><td>{current_inv}</td></tr>
                </table>
                """
                st.markdown(inv_table_html, unsafe_allow_html=True)
            
            except Exception as e:
                st.error(f"Error: {str(e)}")