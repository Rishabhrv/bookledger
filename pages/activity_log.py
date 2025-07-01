
import streamlit as st
import pandas as pd
from sqlalchemy import text
from constants import log_activity
from constants import connect_db
from auth import validate_token


logo = "logo/logo_black.png"
fevicon = "logo/favicon_black.ico"
small_logo = "logo/favicon_white.ico"

st.set_page_config(page_title='Activity Log', page_icon="🕵🏻", layout="wide")

st.logo(logo,
size = "large",
icon_image = small_logo
)

validate_token()

user_role = st.session_state.get("role", None)
user_app = st.session_state.get("app", None)
user_access = st.session_state.get("access", None)

if user_role != "admin":
    st.error("You do not have permission to access this page.")
    st.stop()

st.cache_data.clear()

# st.markdown("""
#     <style>
            
#         /* Remove Streamlit's default top padding */
#         .main > div {
#             padding-top: 0px !important;
#         }
#         /* Ensure the first element has minimal spacing */
#         .block-container {
#             padding-top: 8px !important;  /* Small padding for breathing room */
#         }
#             """, unsafe_allow_html=True)

# Connect to MySQL
conn = connect_db()

# Initialize session state from query parameters
query_params = st.query_params
click_id = query_params.get("click_id", [None])
session_id = query_params.get("session_id", [None])

# Set session_id in session state
st.session_state.session_id = session_id

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
            f"Page: Activity Log"
        )
        st.session_state.logged_click_ids.add(click_id)
    except Exception as e:
        st.error(f"Error logging navigation: {str(e)}")


def display_activity_log(conn, user_id=None, session_id=None):
    try:
        with conn.session as s:
            query = "SELECT * FROM activity_log WHERE 1=1"
            params = {}
            if user_id:
                query += " AND user_id = :user_id"
                params["user_id"] = user_id
            if session_id:
                query += " AND session_id = :session_id"
                params["session_id"] = session_id
            query += " ORDER BY timestamp DESC"

            # FIXED: use mappings()
            logs = s.execute(text(query), params).mappings().all()

            if logs:
                log_data = [{
                    "Timestamp": log["timestamp"],
                    "User ID": log["user_id"],
                    "Username": log["username"],
                    "Session ID": log["session_id"],
                    "Action": log["action"],
                    "Details": log["details"]
                } for log in logs]

                st.dataframe(pd.DataFrame(log_data), use_container_width=True)
            else:
                st.info("No activities logged for the selected criteria.")
    except Exception as e:
        st.error(f"Error fetching activity log: {e}")




display_activity_log(conn)