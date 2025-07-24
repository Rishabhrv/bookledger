
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
            padding-top: 7px !important;  /* Small padding for breathing room */
        }
            """, unsafe_allow_html=True)

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
    .checklist-action {
        font-weight: bold;
        color: #1f77b4;
        margin-right: 8px;
        min-width: 60px;
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
        flex-grow: 1;
    }
    .details_checklist {
        color: #333;
        font-size: 13px;
        word-break: break-word;
        padding: 4px 8px;
        border-radius: 4px;
        display: flex;
        flex-direction: column;
        line-height: 1.4;
        flex-grow: 1;
    }
    .column-border {
        border-right: 1px solid #e0e0e0;
        padding-right: 20px;
    }
    .checklist-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .checklist-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .checklist-title {
        font-size: 16px;
        font-weight: bold;
        color: #333;
    }
    .checklist-timestamp {
        font-size: 12px;
        color: #6c757d;
    }
    .checklist-info {
        font-size: 14px;
        color: #555;
        margin-bottom: 12px;
    }
    .checklist-status {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    .status-item {
        font-size: 13px;
        padding: 4px 8px;
        border-radius: 12px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .status-completed {
        background-color: #d4edda;
        color: #155724;
    }
    .status-pending {
        background-color: #fff3cd;
        color: #856404;
    }
    .checklist-item {
        padding: 6px;
        font-size: 14px;
        border-left: 2px solid #1f77b4;
        margin-left: 20px;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
    }
    .highlight-author {
        font-weight: 501;
        font-size: 14px;
        color: #292929;
    }
    .highlight-update {
        background-color: #47a65b;
        color: #ffffff;
        padding: 2px 8px;
        border-radius: 16px;
        font-size: 12px;
        font-weight: 501;
        display: inline-block; /* Changed to inline-block to fit text */
        align-items: center;
        justify-content: center;
        margin-top: 3px;
        gap: 4px;
        line-height: 1.2;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        white-space: nowrap; /* Prevents text wrapping */
        max-width: fit-content; /* Ensures badge size fits content */
    }
        </style>
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

# Fetch checklist updates with book and author details
def get_checklist_updates(selected_date):
    conn = connect_db()
    query = """
        SELECT al.timestamp, al.details, b.book_id, b.title, a.author_id, a.name,
               ba.welcome_mail_sent, ba.photo_recive, ba.id_proof_recive, ba.author_details_sent,
               ba.cover_agreement_sent, ba.agreement_received, ba.digital_book_sent,
               ba.digital_book_approved, ba.plagiarism_report
        FROM activity_log al
        JOIN book_authors ba ON al.details LIKE CONCAT('%Book ID: ', ba.book_id, '%') AND 
                               al.details LIKE CONCAT('%Author ID: ', ba.author_id, '%')
        JOIN books b ON ba.book_id = b.book_id
        JOIN authors a ON ba.author_id = a.author_id
        WHERE DATE(al.timestamp) = :selected_date
        AND al.action = 'updated checklist'
        ORDER BY al.timestamp DESC
    """
    params = {"selected_date": selected_date}
    
    with conn.session as s:
        result = s.execute(text(query), params=params)
        df = pd.DataFrame(result.fetchall(), columns=[
            "timestamp", "details", "book_id", "title", "author_id", "name",
            "welcome_mail_sent", "photo_recive", "id_proof_recive", "author_details_sent",
            "cover_agreement_sent", "agreement_received", "digital_book_sent",
            "digital_book_approved", "plagiarism_report"
        ])
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
        'navigated to page': '➡️',
        'changed author type': '✍️',
        'updated writing details': '📝',
        'updated author': '📲',
        'updated proofreading details' : '🔦',
        'updated formatting details': '📑',
        'updated formatting correction': '📑',
        'updated writing correction': '✏️',
        'updated proofreading correction': '🕵',
        'added formatting correction': '📄',
        'added proofreading correction': '🕵',
        'updated writing correction details': '✏️',
        'added writing correction': '✏️',
        'updated cover details': '🎨',
        'edited print edition' : '🖨️',
        'updated book': '📚',
        'toggled checkbox': '☑️',
        'updated writing corrections': '✏️',
        'opened dialog': '💬',
        'added print edition': '🖨️',
        'updated links': '🔗',
        'updated sales': '💰',
        'searched': '🔎',
        'updated book details': '📖',
        'cleaned old logs': '🧹',
        'updated checklist': '✅'
    }
    return action_emojis.get(action.lower(), '⚙️')

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

# Create two columns for main activity log and checklist updates
col_main, col_checklist = st.columns([1.5, 1])

# Main Activity Log
with col_main:
    st.markdown('<div class="column-border">', unsafe_allow_html=True)
    
    # Fetch data for main activity log
    selected_user_param = selected_user if selected_user != 'All' else None
    selected_action_param = selected_action if selected_action and selected_action != 'All' else None
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
                                <div class="action">{emoji} {row['action']} → </div>
                                <div class="details">{row['details']}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        user_filter = f" for {selected_user}" if selected_user and selected_user != 'All' else ''
        action_filter = f" and action {selected_action}" if selected_action else ''
        search_filter = f" with search term {search_term}" if search_term else ''
        st.info(f"No activities found for {selected_date.strftime('%B %d, %Y')}{user_filter}{action_filter}{search_filter}.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Checklist Updates
with col_checklist:
    st.write("#### ✅ Author Updates")
    
    # Fetch checklist updates with book and author details
    checklist_df = get_checklist_updates(selected_date.strftime('%Y-%m-%d'))
    
    if not checklist_df.empty:
        # Group by book_id and title for a tree-like structure
        grouped = checklist_df.groupby(['book_id', 'title'])
        
        for (book_id, title), book_group in grouped:
            with st.expander(f"📖 {title} (ID: {book_id})", expanded=True):
                # Sort updates by timestamp, most recent first
                book_group = book_group.sort_values('timestamp', ascending=False)
                
                for _, row in book_group.iterrows():
                    formatted_time = format_timestamp(row['timestamp'])
                    # Extract changed field and value from details
                    changed_field = row['details'].split(', ')[-1].split(' changed to ')[0]
                    changed_value = row['details'].split(' changed to ')[-1].strip("'")
                    st.markdown(
                        f"""
                        <div class="checklist-item">
                            <div class="timestamp">{formatted_time}</div>
                            <div class="details_checklist">
                                <span class="highlight-author">{row['name']} : ID {row['author_id']}</span>
                                <span class="highlight-update">{changed_field} → {changed_value}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
    else:
        st.info(f"No author checklist updates found for {selected_date.strftime('%B %d, %Y')}.")