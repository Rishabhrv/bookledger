# constants.py

from sqlalchemy import text
import streamlit as st
from datetime import datetime
import pytz

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