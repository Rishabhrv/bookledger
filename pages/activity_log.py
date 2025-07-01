
import streamlit as st
import pandas as pd
from sqlalchemy import text
from constants import log_activity
from constants import connect_db
from auth import validate_token
from datetime import datetime, date


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

st.cache_data.clear()

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


# Fetch activity log data for a specific date, user, and action
def get_activity_log(selected_date, selected_user=None, selected_action=None):
    conn = connect_db()
    query = """
        SELECT timestamp, user_id, username, session_id, action, details 
        FROM activity_log 
        WHERE DATE(timestamp) = :selected_date
    """
    params = {"selected_date": selected_date}
    if selected_user:
        query += " AND username = :selected_user"
        params["selected_user"] = selected_user
    if selected_action:
        query += " AND action = :selected_action"
        params["selected_action"] = selected_action
    query += " ORDER BY timestamp DESC"
    
    with conn.session as s:
        result = s.execute(text(query), params=params)
        df = pd.DataFrame(result.fetchall(), columns=["timestamp", "user_id", "username", "session_id", "action", "details"])
        s.commit()
    return df

# Format timestamp for display
def format_timestamp(ts):
    if isinstance(ts, pd.Timestamp):
        ts = ts.strftime('%Y-%m-%d %H:%M:%S')
    return datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p')

# Calculate session duration
def calculate_session_duration(session_group):
    timestamps = pd.to_datetime(session_group['timestamp'])
    duration = timestamps.max() - timestamps.min()
    total_seconds = int(duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# Assign emojis based on action type
def get_action_emoji(action):
    action_emojis = {
        'logged in': '🔐',
        'navigated to page': '📄',
        'changed author type': '✍️',
        'updated writing details': '📝',
        'updated author': '👤',
        'opened dialog': '🖱️',
        'added print edition': '📚',
        'updated links': '🔗',
        'updated sales': '💰',
        'updated book details': '📖',
        'cleaned old logs': '🧹'
    }
    return action_emojis.get(action.lower(), '⚙️')

# Custom CSS for tree view and filter styling
def apply_tree_style():
    st.markdown("""
        <style>
        .tree-item {
            padding: 6px;
            font-size: 14px;
            border-left: 2px solid #1f77b4;
            margin-left: 20px;
            margin-bottom: 6px;
        }
        .user-node {
            font-size: 16px;
            font-weight: bold;
            color: #333;
            margin-bottom: 8px;
        }
        .session-node {
            font-size: 15px;
            font-weight: bold;
            color: #555;
            margin-left: 15px;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
        }
        .session-duration {
            font-size: 12px;
            color: #6c757d;
            margin-left: 10px;
            font-style: italic;
        }
        .timestamp {
            color: #6c757d;
            font-size: 12px;
            min-width: 80px;
            margin-right: 8px;
            display: inline-block;
        }
        .action {
            font-weight: bold;
            color: #1f77b4;
            margin-right: 8px;
            min-width: 140px;
            display: inline-block;
        }
        .details {
            color: #333;
            font-size: 13px;
            word-break: break-word;
            background-color: #f1f3f5;
            padding: 4px 8px;
            border-radius: 4px;
            display: inline-block;
            line-height: 1.4;
        }
        </style>
    """, unsafe_allow_html=True)

# Apply custom CSS
apply_tree_style()

col1, col2 = st.columns([12, 1], vertical_alignment="bottom")

with col1:
    st.write("## 📝 Activity Log")
with col2:
    if st.button(":material/refresh: Refresh", key="refresh", type="tertiary"):
        st.cache_data.clear()

# Fetch distinct users and actions for pills
conn = connect_db()
with conn.session as s:
    result = s.execute(text("SELECT DISTINCT username FROM activity_log"))
    users_df = pd.DataFrame(result.fetchall(), columns=["username"])
    result = s.execute(text("SELECT DISTINCT action FROM activity_log"))
    actions_df = pd.DataFrame(result.fetchall(), columns=["action"])
    s.commit()

user_options = ['All'] + sorted(users_df['username'].tolist())
action_options = sorted(actions_df['action'].tolist())


# Filters and search bar
col1, col2, col3 = st.columns([1, 6, 2], gap="small")

# Date picker
with col2:
    search_term = st.text_input("Search by Book ID, Author ID, or Details", "", 
                                placeholder="Enter Book ID, Author ID, or any term...", key="search_bar",
                                label_visibility="collapsed")
 
with col3:
    selected_action = st.selectbox("Filter by Action", options=action_options, 
                                   index=None, label_visibility="collapsed", placeholder="Filter by Action")
    
with col1:
    default_date = date.today()
    selected_date = st.date_input("Select Date", value=default_date, 
                                      label_visibility="collapsed", key="date_input")

    

selected_user = st.segmented_control("Filter by User", options=user_options, 
                                         default=user_options[0], label_visibility="collapsed")


# Fetch data
selected_user_param = selected_user if selected_user != 'All' else None
selected_action_param = selected_action if selected_action != 'All' else None
df = get_activity_log(selected_date.strftime('%Y-%m-%d'), selected_user_param, selected_action_param)

# Apply search filter
if search_term:
    df = df[df['details'].str.contains(search_term, case=False, na=False)]

# Display activities in tree view
if not df.empty:
    grouped = df.groupby(['user_id', 'username'])
    
    for (user_id, username), user_group in grouped:
        with st.expander(f"👤 {username} (ID: {user_id})", expanded=True):
            # Sort sessions by most recent activity
            session_groups = user_group.groupby('session_id').agg({'timestamp': 'max'}).reset_index()
            session_groups = session_groups.sort_values('timestamp', ascending=False)
            
            for session_id in session_groups['session_id']:
                session_group = user_group[user_group['session_id'] == session_id].sort_values('timestamp', ascending=False)
                duration = calculate_session_duration(session_group)
                st.markdown(f'<div class="session-node">📂 Session <span class="session-duration">(Duration: {duration})</span></div>', unsafe_allow_html=True)
                
                # Display activities as tree leaves
                for _, row in session_group.iterrows():
                    formatted_time = format_timestamp(row['timestamp'])
                    emoji = get_action_emoji(row['action'])
                    st.markdown(
                        f"""
                        <div class="tree-item">
                            <div class="timestamp">{formatted_time}</div>
                            <div class="action">{emoji} {row['action']}</div>
                            <div class="details">{row['details']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info(f"No activities found for {selected_date.strftime('%B %d, %Y')}"
            f"{' for ' + selected_user if selected_user != 'All' else ''}"
            f"{' and action ' + selected_action if selected_action != 'All' else ''}"
            f"{' with search term ' + search_term if search_term else ''}.")