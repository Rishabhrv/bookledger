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
    "Tasks": "tasks",
    "Details": "details",
    "Message": "messages",
    "Attendance": "attendance",
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


def get_page_url(page_path, token):
    """Generate a URL with the token as a query parameter."""
    # Decide which base URL to use based on the path
    if page_path.startswith("/"):
        base = CHAT_URL
        return f"{base}?token={token}"
    else:
        base = BASE_URL
        return f"{base}/{page_path}?token={token}"

def log_activity(conn, user_id, username, session_id, action, details):
    try:
        # Get current time in Indian Standard Time
        ist = pytz.timezone('Asia/Kolkata')
        ist_time = datetime.now(ist)

        with conn.session as s:
            s.execute(
                text("""
                    INSERT INTO activity_log (user_id, username, session_id, action, details, timestamp)
                    VALUES (:user_id, :username, :session_id, :action, :details, :timestamp)
                """),
                {
                    "user_id": user_id,
                    "username": username,
                    "session_id": session_id,
                    "action": action,
                    "details": details,
                    "timestamp": ist_time.strftime('%Y-%m-%d %H:%M:%S')
                }
            )
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