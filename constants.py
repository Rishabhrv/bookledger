# constants.py

from sqlalchemy import text
import streamlit as st

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
    # Non-loop buttons
    "Add Book": "add_book_dialog",
    "Authors Edit": "edit_author_detail"
}


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



from datetime import datetime
def log_activity(conn, user_id, username, session_id, action, details):
    try:
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
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            )
            s.commit()
    except Exception as e:
        st.error(f"Error logging activity: {e}")


def clean_old_logs(conn, days_to_keep=30):
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
