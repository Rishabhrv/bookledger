
import streamlit as st
import pandas as pd
from sqlalchemy import text
from constants import log_activity, initialize_click_and_session_id, connect_db
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
initialize_click_and_session_id()

user_role = st.session_state.get("role", None)
user_app = st.session_state.get("app", None)
user_access = st.session_state.get("access", None)
session_id = st.session_state.session_id
click_id = st.session_state.get("click_id", None)


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
    /* Clean, minimal design with subtle accents */
    .tree-item {
        padding: 10px 14px;
        font-size: 14px;
        border-left: 2px solid #1f77b4;
        margin-left: 20px;
        margin-bottom: 8px;
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 10px;
    }
    
    .tree-item:hover {
        background-color: #f8f9fa;
    }
    
    .session-node {
        font-size: 14px;
        font-weight: 600;
        color: #495057;
        margin-left: 15px;
        margin-bottom: 8px;
        margin-top: 6px;
        padding: 6px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .session-duration {
        font-size: 12px;
        color: #6c757d;
        font-weight: 400;
        font-style: italic;
    }
    
    .timestamp {
        color: #6c757d;
        font-size: 12px;
        font-weight: 500;
        white-space: nowrap;
    }
    
    .action {
        font-weight: 600;
        color: #1f77b4;
        white-space: nowrap;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    
    .details {
        color: #333;
        font-size: 13px;
        word-break: break-word;
        background-color: #f8f9fa;
        padding: 5px 10px;
        border-radius: 4px;
        flex: 1;
        min-width: 200px;
        line-height: 1.5;
    }
    
    .details_checklist {
        color: #333;
        font-size: 13px;
        word-break: break-word;
        padding: 4px 0;
        display: flex;
        flex-direction: column;
        gap: 6px;
        line-height: 1.5;
        flex: 1;
    }
    
    .column-border {
        border-right: 1px solid #e0e0e0;
        padding-right: 20px;
    }
    
    .checklist-item {
        padding: 8px 12px;
        font-size: 14px;
        border-left: 2px solid #27ae60;
        margin-left: 12px;
        margin-bottom: 8px;
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 10px;
    }
    
    .checklist-item:hover {
        background-color: #f8f9fa;
    }
    
    .highlight-author {
        font-weight: 600;
        font-size: 13px;
        color: #333;
    }
    
    .highlight-update {
        background-color: #27ae60;
        color: #ffffff;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        white-space: nowrap;
        max-width: fit-content;
    }
    
    /* Subtle arrow styling */
    .action-arrow {
        color: #adb5bd;
        font-weight: 400;
        margin: 0 2px;
    }
</style>
""", unsafe_allow_html=True)

st.cache_data.clear()

# Connect to MySQL
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
            f"Page: Activity Log"
        )
        st.session_state.logged_click_ids.add(click_id)
    except Exception as e:
        st.error(f"Error logging navigation: {str(e)}")


# Fetch activity log data for a specific date, user, and action
def get_activity_log(selected_date, selected_user=None, selected_action=None, search_term=None):
    conn = connect_db()
    query = "SELECT timestamp, user_id, username, session_id, action, details FROM activity_log WHERE 1=1"
    params = {}
    
    if search_term:
        query += " AND (details LIKE :search OR action LIKE :search)"
        params["search"] = f"%{search_term}%"
    else:
        query += " AND DATE(timestamp) = :selected_date"
        params["selected_date"] = selected_date
        
    if selected_user:
        query += " AND username = :selected_user"
        params["selected_user"] = selected_user
    if selected_action:
        query += " AND action = :selected_action"
        params["selected_action"] = selected_action
    query += " ORDER BY timestamp DESC LIMIT 1000"
    
    with conn.session as s:
        result = s.execute(text(query), params=params)
        df = pd.DataFrame(result.fetchall(), columns=["timestamp", "user_id", "username", "session_id", "action", "details"])
        s.commit()
    return df

import re

# Fetch daily summary metrics
def get_daily_summary(selected_date, id_preference="Book"):
    conn = connect_db()
    query = """
        SELECT action, details 
        FROM activity_log 
        WHERE DATE(timestamp) = :selected_date
    """
    with conn.session as s:
        result = s.execute(text(query), {"selected_date": selected_date})
        df = pd.DataFrame(result.fetchall(), columns=["action", "details"])
    
    if df.empty:
        return None

    def extract_info(details_series, pref):
        ids = []
        effective_type = "B"
        for d in details_series.dropna():
            b_match = re.search(r"Book ID: (\d+)", d)
            a_match = re.search(r"Author ID: (\d+)", d)
            
            b_id = b_match.group(1) if b_match else None
            a_id = a_match.group(1) if a_match else None
            
            if pref == "Author" and a_id:
                ids.append(a_id)
                effective_type = "A"
            elif b_id:
                ids.append(b_id)
                # Keep effective_type as B unless we found Author IDs earlier
            elif a_id:
                ids.append(a_id)
                effective_type = "A"
        return sorted(list(set(ids)), key=int), effective_type

    summary = {}
    
    # Define metrics: (Label, Filter Condition)
    metrics_config = [
        ("📚 New Books", df['action'].str.contains('added book', case=False, na=False)),
        ("👥 New Authors", df['action'].str.contains('added author', case=False, na=False)),
        ("💰 Payments", df['action'].isin(['registered payment', 'approved payment'])),
        ("🛠️ Corrections", df['action'].str.contains('correction', case=False, na=False)),
        ("📧 Welcome Mail", (df['action'] == 'sent welcome email') | (df['details'].str.contains("Welcome Mail Sent changed to 'True'", na=False))),
        ("📥 Author Details", df['details'].str.contains("Author Details Received changed to 'True'", na=False)),
        ("📷 Author Photo", df['details'].str.contains("Photo Received changed to 'True'", na=False)),
        ("🆔 ID Proof", df['details'].str.contains("ID Proof Received changed to 'True'", na=False)),
        ("📜 Cover & Agreement", df['details'].str.contains("Cover Agreement Sent changed to 'True'", na=False)),
        ("✍🏻 Agreement Recvd", df['details'].str.contains("Agreement Received changed to 'True'", na=False)),
        ("📤 Digital Proof", df['details'].str.contains("Digital Book Sent changed to 'True'", na=False)),
        ("🖨️ Print Confirm", df['details'].str.contains("Printing Confirmation Received changed to 'True'", na=False))
    ]

    for label, condition in metrics_config:
        filtered = df[condition]
        if not filtered.empty:
            ids, id_type = extract_info(filtered['details'], id_preference)
            summary[label] = {"count": len(filtered), "ids": ids, "id_type": id_type}
        else:
            summary[label] = {"count": 0, "ids": [], "id_type": "B"}
            
    return summary

# Add this new function for the compact summary
def display_whatsapp_summary(selected_date, summary_data):
    if not summary_data:
        return
    
    # Filter only positive values
    active_metrics = {k: v for k, v in summary_data.items() if v['count'] > 0}
    
    if not active_metrics:
        st.info("No major updates today.")
        return

    def format_ids(ids, id_type):
        if not ids: return ""
        # Join all IDs without truncation, but keep it clean
        return f"{id_type}: {', '.join(ids)}"

    # Create a compact string for copying
    summary_text = f"*Daily Update Summary - {selected_date.strftime('%d/%m/%Y')}*\n\n"
    for label, data in active_metrics.items():
        id_str = format_ids(data['ids'], data['id_type'])
        summary_text += f"{label}: {data['count']} ({id_str})\n"
    
    # Display in a nice, compact card for screenshotting
    rows_html = ""
    for k, v in active_metrics.items():
        id_display = format_ids(v['ids'], v['id_type'])
        rows_html += f"""<div style="margin-bottom: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;"><div style="display: flex; justify-content: space-between; align-items: center;"><span style="font-size: 14px; font-weight: 600; color: #1e293b;">{k}</span><span style="background: #f1f5f9; color: #1f77b4; padding: 2px 12px; border-radius: 6px; font-size: 14px; font-weight: 700; border: 1px solid #e2e8f0;">{v['count']}</span></div><div style="font-size: 12px; color: #475569; font-family: 'JetBrains Mono', 'Courier New', monospace; line-height: 1.5; margin-top: 4px; word-break: break-all; letter-spacing: -0.2px; font-weight: 600;">{id_display}</div></div>"""

    # Use a simpler container with NO indentation to avoid rendering issues
    card_html = f"""<div style="background-color: #ffffff; padding: 28px; border: 1px solid #e2e8f0; border-radius: 12px; width: 520px; margin: 10px auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);"><div style="text-align: center; color: #0f172a; font-size: 20px; font-weight: 800; border-bottom: 3px solid #1f77b4; padding-bottom: 12px; margin-bottom: 20px; letter-spacing: -0.5px;">📊 DAILY UPDATE: {selected_date.strftime('%d %b %Y')}</div>{rows_html}<div style="text-align: center; font-size: 11px; color: #94a3b8; margin-top: 16px; border-top: 1px solid #f1f5f9; padding-top: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">BookLedger System • {datetime.now().strftime('%I:%M %p')}</div></div>"""
    
    st.markdown(card_html, unsafe_allow_html=True)

# Fetch detailed records for a specific metric
def get_metric_details(label, selected_date):
    conn = connect_db()
    conditions = {
        "📚 New Books": "action LIKE '%added book%'",
        "👥 New Authors": "action LIKE '%added author%'",
        "💰 Payments": "action IN ('registered payment', 'approved payment')",
        "🛠️ Corrections": "action LIKE '%correction%'",
        "📧 Welcome Mail": "(action = 'sent welcome email' OR (action = 'updated checklist' AND details LIKE '%Welcome Mail Sent changed to ''True''%'))",
        "📥 Author Details": "details LIKE '%Author Details Received changed to ''True''%'",
        "📷 Author Photo": "details LIKE '%Photo Received changed to ''True''%'",
        "🆔 ID Proof": "details LIKE '%ID Proof Received changed to ''True''%'",
        "📜 Cover & Agreement": "details LIKE '%Cover Agreement Sent changed to ''True''%'",
        "✍🏻 Agreement Recvd": "details LIKE '%Agreement Received changed to ''True''%'",
        "📤 Digital Proof": "details LIKE '%Digital Book Sent changed to ''True''%'",
        "🖨️ Print Confirm": "details LIKE '%Printing Confirmation Received changed to ''True''%'"
    }
    condition = conditions.get(label, "1=0")
    query = f"SELECT timestamp, username, details FROM activity_log WHERE DATE(timestamp) = :selected_date AND {condition} ORDER BY timestamp DESC"
    with conn.session as s:
        result = s.execute(text(query), {"selected_date": selected_date})
        df = pd.DataFrame(result.fetchall(), columns=["Time", "User", "Details"])
    if not df.empty:
        df['Time'] = pd.to_datetime(df['Time']).dt.strftime('%I:%M %p')
    return df

@st.dialog("Activity Breakdown", width="large")
def show_metric_details(label, selected_date):
    st.markdown(f"#### {label} Breakdown")
    st.caption(f"Records for {selected_date}")
    details_df = get_metric_details(label, selected_date)
    if not details_df.empty:
        st.dataframe(
            details_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Time": st.column_config.TextColumn("Time", width="small"),
                "User": st.column_config.TextColumn("By", width="small"),
                "Details": st.column_config.TextColumn("Activity Details", width="large")
            }
        )
    else:
        st.info("No detailed records found.")

# Fetch checklist updates with book and author details
def get_checklist_updates(selected_date, search_term=None):
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
        WHERE al.action = 'updated checklist'
    """
    params = {}
    if search_term:
        query += " AND (al.details LIKE :search OR b.title LIKE :search OR a.name LIKE :search)"
        params["search"] = f"%{search_term}%"
    else:
        query += " AND DATE(al.timestamp) = :selected_date"
        params["selected_date"] = selected_date
        
    query += " ORDER BY al.timestamp DESC LIMIT 500"
    
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

# Fetch email history
def get_email_history(selected_date, search_term=None):
    conn = connect_db()
    query = """
        SELECT timestamp, recipient, sender_email, status, book_id, book_title, triggered_by, details 
        FROM email_history 
        WHERE 1=1
    """
    params = {}
    
    if search_term:
        query += " AND (recipient LIKE :search OR sender_email LIKE :search OR details LIKE :search OR book_title LIKE :search OR book_id LIKE :search)"
        params["search"] = f"%{search_term}%"
    else:
        query += " AND DATE(timestamp) = :selected_date"
        params["selected_date"] = selected_date
        
    query += " ORDER BY timestamp DESC LIMIT 500"
    
    with conn.session as s:
        result = s.execute(text(query), params=params)
        df = pd.DataFrame(result.fetchall(), columns=["Timestamp", "Recipient", "Sender Email", "Status", "Book ID", "Book Title", "Triggered By", "Details"])
    return df

# Format timestamp for display
def format_timestamp(ts):
    if isinstance(ts, pd.Timestamp):
        ts = ts.strftime('%Y-%m-%d %H:%M:%S')
    return datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').strftime('%d %b, %I:%M %p')

# Calculate session duration
def calculate_session_duration(session_group):
    timestamps = pd.to_datetime(session_group['timestamp'])
    duration = timestamps.max() - timestamps.min()
    total_seconds = int(duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Format duration more readably
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


# Assign emojis based on action type
def get_action_emoji(action):
    action_emojis = {
        'logged in': '🔐',
        'navigated to page': '🧭',
        'changed author type': '✍️',
        'updated writing details': '📝',
        'updated author': '👤',
        'updated proofreading details': '🔍',
        'updated formatting details': '📐',
        'updated formatting correction': '📐',
        'updated writing correction': '✏️',
        'updated proofreading correction': '🔎',
        'added formatting correction': '➕',
        'added proofreading correction': '➕',
        'updated writing correction details': '✏️',
        'added writing correction': '➕',
        'updated cover details': '🎨',
        'edited print edition': '🖨️',
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
        'updated checklist': '✅',
        'sent isbn email': '📧'
    }
    return action_emojis.get(action.lower(), '⚙️')

# Header with improved layout
col1, col2 = st.columns([12, 1], vertical_alignment="bottom")

with col1:
    st.markdown("## 📝 Activity Log")
with col2:
    if st.button("🔄 Refresh", key="refresh", type="tertiary", use_container_width=True):
        st.cache_data.clear()

# Fetch distinct users and actions for pills
conn = connect_db()
with conn.session as s:
    result = s.execute(text("SELECT DISTINCT username FROM activity_log ORDER BY username"))
    users_df = pd.DataFrame(result.fetchall(), columns=["username"])
    result = s.execute(text("SELECT DISTINCT action FROM activity_log ORDER BY action"))
    actions_df = pd.DataFrame(result.fetchall(), columns=["action"])
    s.commit()

user_options = ['All'] + sorted(users_df['username'].tolist())
action_options = sorted(actions_df['action'].tolist())

# Improved filters layout
col1, col2, col3, col4 = st.columns([1, 4, 2, 2], gap="small")

with col1:
    default_date = date.today()
    selected_date = st.date_input("📅 Date", value=default_date, 
                                  label_visibility="collapsed", key="date_input")

with col2:
    search_term = st.text_input("🔍 Search", "", 
                                placeholder="Search by Book ID, Author ID, or Details...", 
                                key="search_bar",
                                label_visibility="collapsed")

with col3:
    selected_action = st.selectbox("🎯 Action", options=action_options, 
                                   index=None, label_visibility="collapsed", 
                                   placeholder="Filter by Action")

with col4:
    selected_user = st.selectbox("👥 User", options=user_options, 
                                 index=0, label_visibility="collapsed", 
                                 placeholder="Filter by User")

st.write("")

# Display Daily Summary in Expander (Only if not searching globally)
if not search_term:
    with st.expander("📈 Daily Update Summary", expanded=False):
        col_sum_h, col_sum_t = st.columns([8, 2], vertical_alignment="bottom")
        with col_sum_t:
            id_pref_toggle = st.toggle("Show Author IDs", value=True, key="id_pref_toggle")
            id_pref = "Author" if id_pref_toggle else "Book"

        summary_data = get_daily_summary(selected_date.strftime('%Y-%m-%d'), id_preference=id_pref)
        if summary_data:
            # Display as a nice grid (6x2)
            summary_items = list(summary_data.items())
            rows = [summary_items[i:i+6] for i in range(0, len(summary_items), 6)]
            for row in rows:
                cols = st.columns(6)
                for idx, (label, data) in enumerate(row):
                    value = data['count']
                    if value > 0:
                        with cols[idx]:
                            st.markdown(
                                f"""
                                <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 3px solid #1f77b4; height: 100px; display: flex; flex-direction: column; justify-content: space-between;">
                                    <div>
                                        <div style="font-size: 11px; color: #6c757d; font-weight: 600; text-transform: uppercase; line-height: 1.2;">{label}</div>
                                        <div style="font-size: 22px; font-weight: 700; color: #1f77b4; margin-top: 4px;">{value}</div>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                            if st.button("View Details", key=f"details_{label}_{idx}", type="tertiary", use_container_width=True):
                                show_metric_details(label, selected_date.strftime('%Y-%m-%d'))
                    else:
                        with cols[idx]:
                            st.markdown(
                                f"""
                                <div style="background-color: #ffffff; padding: 10px; border-radius: 8px; border: 1px solid #f1f3f4; height: 100px; opacity: 0.6;">
                                    <div style="font-size: 11px; color: #adb5bd; font-weight: 600; text-transform: uppercase; line-height: 1.2;">{label}</div>
                                    <div style="font-size: 22px; font-weight: 700; color: #ced4da; margin-top: 4px;">0</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

            # Call the compact summary display
            display_whatsapp_summary(selected_date, summary_data)
else:
    st.info(f"🔎 Showing search results for '**{search_term}**' across all dates.")

st.write("")

tab1, tab2 = st.tabs(["📝 Activity Log", "📧 Email History"])

with tab1:
    # Create two columns for main activity log and checklist updates
    col_main, col_checklist = st.columns([1.5, 1], gap="medium")

    # Main Activity Log
    with col_main:
        st.markdown('<div class="column-border">', unsafe_allow_html=True)
        
        # Fetch data for main activity log
        selected_user_param = selected_user if selected_user != 'All' else None
        selected_action_param = selected_action if selected_action and selected_action != 'All' else None
        df = get_activity_log(selected_date.strftime('%Y-%m-%d'), selected_user_param, selected_action_param, search_term=search_term)

        # Display activities in tree view
        if not df.empty:
            # Show activity count
            st.caption(f"📊 {len(df)} activities found")
            
            grouped = df.groupby(['user_id', 'username'])
            
            for (user_id, username), user_group in grouped:
                with st.expander(f"👤 **{username}** • ID: {user_id}", expanded=True):
                    # Sort sessions by most recent activity
                    session_groups = user_group.groupby('session_id').agg({'timestamp': 'max'}).reset_index()
                    session_groups = session_groups.sort_values('timestamp', ascending=False)
                    
                    for idx, session_id in enumerate(session_groups['session_id'], 1):
                        session_group = user_group[user_group['session_id'] == session_id].sort_values('timestamp', ascending=False)
                        duration = calculate_session_duration(session_group)
                        activity_count = len(session_group)
                        st.markdown(
                            f'<div class="session-node">📂 Session {idx} • '
                            f'{activity_count} {"activity" if activity_count == 1 else "activities"} • '
                            f'<span class="session-duration">⏱️ {duration}</span></div>', 
                            unsafe_allow_html=True
                        )
                        
                        # Display activities as tree leaves
                        for _, row in session_group.iterrows():
                            formatted_time = format_timestamp(row['timestamp'])
                            emoji = get_action_emoji(row['action'])
                            st.markdown(
                                f"""
                                <div class="tree-item">
                                    <span class="timestamp">🕐 {formatted_time}</span>
                                    <span class="action">{emoji} {row['action']}</span>
                                    <span class="action-arrow">→</span>
                                    <span class="details">{row['details']}</span>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
        else:
            user_filter = f" for **{selected_user}**" if selected_user and selected_user != 'All' else ''
            action_filter = f" with action **{selected_action}**" if selected_action else ''
            search_filter = f" matching **'{search_term}'**" if search_term else ''
            st.info(f"📭 No activities found for **{selected_date.strftime('%B %d, %Y')}**{user_filter}{action_filter}{search_filter}.")
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Checklist Updates
    with col_checklist:
        st.markdown("#### ✅ Author Checklist Updates")
        
        # Fetch checklist updates with book and author details
        checklist_df = get_checklist_updates(selected_date.strftime('%Y-%m-%d'), search_term=search_term)
        
        if not checklist_df.empty:
            # Show update count
            st.caption(f"📊 {len(checklist_df)} checklist updates")
            
            # Group by book_id and title for a tree-like structure
            grouped = checklist_df.groupby(['book_id', 'title'])
            
            for (book_id, title), book_group in grouped:
                update_count = len(book_group)
                label = "update" if update_count == 1 else "updates"
                with st.expander(f"📖 **{title}** • {update_count} {label}",expanded=True):
                    # Sort updates by timestamp, most recent first
                    book_group = book_group.sort_values('timestamp', ascending=False)
                    
                    for _, row in book_group.iterrows():
                        formatted_time = format_timestamp(row['timestamp'])
                        # Extract changed field and value from details
                        try:
                            changed_field = row['details'].split(', ')[-1].split(' changed to ')[0]
                            changed_value = row['details'].split(' changed to ')[-1].strip("'")
                        except:
                            changed_field = "Update"
                            changed_value = row['details']
                        
                        st.markdown(
                            f"""
                            <div class="checklist-item">
                                <span class="timestamp">🕐 {formatted_time}</span>
                                <div class="details_checklist">
                                    <span class="highlight-author">👤 {row['name']} • ID: {row['author_id']}</span>
                                    <span class="highlight-update">✨ {changed_field} → {changed_value}</span>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
        else:
            st.info(f"📭 No author checklist updates for **{selected_date.strftime('%B %d, %Y')}**.")

with tab2:
    st.markdown("### 📧 Email History")
    email_df = get_email_history(selected_date.strftime('%Y-%m-%d'), search_term)
    
    if not email_df.empty:
        st.caption(f"📊 {len(email_df)} email records found")
        st.dataframe(
            email_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Timestamp": st.column_config.DatetimeColumn("Time", format="h:mm a"),
                "Recipient": "To",
                "Sender Email": "From",
                "Status": st.column_config.TextColumn("Status"),
                "Book ID": "Book ID",
                "Book Title": "Book Title",
                "Triggered By": "Sent By",
                "Details": "Details"
            }
        )
    else:
        st.info(f"📭 No email history found for **{selected_date.strftime('%B %d, %Y')}**.")