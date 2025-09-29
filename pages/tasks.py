import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from sqlalchemy import text
import time
from constants import connect_db
import uuid
from auth import validate_token

# --- Initial Imports and Setup ---
# This part is assumed to be at the top of your script.
st.set_page_config(layout="wide", page_title="Timesheet App")
st.markdown("<style> .main > div { padding-top: 0rem !important; } .block-container { padding-top: 2rem !important; }</style>", unsafe_allow_html=True)

validate_token()

role = st.session_state.get("role", "Unknown")
user_app = st.session_state.get("app", "Unknown")
user_access = st.session_state.get("access", [])
user_id = st.session_state.get("user_id", "Unknown")
username = st.session_state.get("username", "Unknown")
start_date = st.session_state.get("start_date", None)
level = st.session_state.get("level", "Unknown")
report_to = st.session_state.get("report_to", "Unknown")
token = st.session_state.token
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


# # In a real app, this would be replaced with a secure login system.
# if 'user_id' not in st.session_state:
#     st.session_state.user_id = 5 # Admin User ID
#     st.session_state.username = "Umer"
#     st.session_state.session_id = str(uuid.uuid4())
#     st.session_state.role = "user"  # Roles: 'user', 'admin'
#     # For an admin, 'level' primarily matters if they are also a manager.
#     # 'report_to' is irrelevant for the admin's own tasks.
#     st.session_state.level = "worker" # Levels: 'worker', 'reporting_manager', 'both'
#     st.session_state.report_to = 4 # Admin doesn't report to anyone

# --- Activity Logging ---
def log_activity(conn, user_id, username, session_id, action, details):
    """Logs user activity to the database."""
    try:
        ist = pytz.timezone('Asia/Kolkata')
        ist_time = datetime.now(ist)
        with conn.session as s:
            s.execute(text("""
                INSERT INTO activity_log (user_id, username, session_id, action, details, timestamp)
                VALUES (:user_id, :username, :session_id, :action, :details, :timestamp)
            """), {
                "user_id": user_id, "username": username, "session_id": session_id,
                "action": action, "details": details, "timestamp": ist_time.strftime('%Y-%m-%d %H:%M:%S')
            })
            s.commit()
    except Exception as e:
        st.error(f"Error logging activity: {e}")

# --- Helper Functions ---
def get_current_week_details():
    """Calculates current fiscal week and dates."""
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist).date()
    # Monday is 0 and Sunday is 6. This is consistent with isocalendar().
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=5) # Saturday
    fiscal_week = today.isocalendar()[1]
    return fiscal_week, start_of_week, end_of_week

# NEW: Function to specifically get previous week's details
def get_previous_week_details():
    """Calculates the previous fiscal week and its dates."""
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist).date()
    # Go to last week (e.g., from Monday, go back one day to Sunday)
    previous_week_date = today - timedelta(days=7)
    start_of_last_week = previous_week_date - timedelta(days=previous_week_date.weekday())
    end_of_last_week = start_of_last_week + timedelta(days=5) # Saturday
    previous_fiscal_week = previous_week_date.isocalendar()[1]
    return previous_fiscal_week, start_of_last_week, end_of_last_week

# NEW: Core logic to decide which timesheet to show
def determine_timesheet_week_to_display(conn, user_id):
    """
    Determines which week's timesheet to display.
    If it's Monday and last week's timesheet is pending ('draft' or 'rejected'),
    it returns last week's details. Otherwise, returns the current week's details.
    """
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist).date()
    current_fiscal_week, current_start_of_week, current_end_of_week = get_current_week_details()

    # Grace period check: Only on Monday (weekday() == 0)
    if today.weekday() == 0:
        prev_fiscal_week, prev_start_of_week, prev_end_of_week = get_previous_week_details()

        try:
            query = "SELECT status FROM timesheets WHERE user_id = :user_id AND fiscal_week = :fiscal_week"
            df = conn.query(query, params={"user_id": user_id, "fiscal_week": prev_fiscal_week}, ttl=0)

            if not df.empty and df.iloc[0]['status'] in ['draft', 'rejected']:
                # User has a pending timesheet from last week. Show that one.
                return prev_fiscal_week, prev_start_of_week, prev_end_of_week, True # True indicates a late submission
        except Exception as e:
            st.error(f"Error checking previous week's timesheet: {e}")
            # Fallback to current week on error
            return current_fiscal_week, current_start_of_week, current_end_of_week, False

    # Default behavior for any other day or if last week's sheet is fine
    return current_fiscal_week, current_start_of_week, current_end_of_week, False


def get_week_dates_from_week_number(year, week_number):
    """Calculates the start and end dates of a given fiscal week and year."""
    try:
        start_of_week = datetime.fromisocalendar(year, week_number, 1).date() # 1 for Monday
        end_of_week = start_of_week + timedelta(days=5) # Saturday
        return f"({start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')})"
    except ValueError:
        return ""

def get_or_create_timesheet(conn, user_id, fiscal_week):
    """Fetches or creates a timesheet for the current week."""
    try:
        query = "SELECT id, status, review_notes FROM timesheets WHERE user_id = :user_id AND fiscal_week = :fiscal_week"
        df = conn.query(query, params={"user_id": user_id, "fiscal_week": fiscal_week}, ttl=0)
        if not df.empty:
            return df.iloc[0]['id'], df.iloc[0]['status'], df.iloc[0]['review_notes']

        # --- CHANGE 1: Handle case where user has no manager ---
        # If report_to is "Unknown" or not a valid ID, set manager_id to None.
        manager_id = st.session_state.get("report_to")
        if manager_id == "Unknown" or not manager_id:
            manager_id = None

        with conn.session as s:
            s.execute(text("INSERT INTO timesheets (user_id, manager_id, fiscal_week, status) VALUES (:user_id, :manager_id, :fiscal_week, 'draft')"),
                      {"user_id": user_id, "manager_id": manager_id, "fiscal_week": fiscal_week})
            s.commit()

        new_df = conn.query(query, params={"user_id": user_id, "fiscal_week": fiscal_week}, ttl=0)
        new_id = new_df.iloc[0]['id']
        log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id,
                     "CREATE_TIMESHEET", f"Created new draft timesheet (ID: {new_id}) for week {fiscal_week}")
        return new_id, 'draft', None
    except Exception as e:
        st.error(f"Error getting/creating timesheet: {e}")
        return None, None, None

def get_weekly_work(conn, timesheet_id):
    """Fetches work entries for a timesheet."""
    try:
        query = """
            SELECT id, work_date, work_name, work_description, work_duration, entry_type, reason
            FROM work WHERE timesheet_id = :timesheet_id ORDER BY work_date ASC
        """
        df = conn.query(query, params={"timesheet_id": timesheet_id}, ttl=5)
        if not df.empty:
            df['work_date'] = pd.to_datetime(df['work_date']).dt.date
        return df
    except Exception as e:
        st.error(f"Error fetching work entries: {e}")
        return pd.DataFrame()

# CHANGED: Enhanced query to fetch manager's name for detailed views.
def get_user_timesheet_history(conn, user_id):
    """Fetches all past timesheets for a specific user with total hours and manager details."""
    try:
        query = """
            SELECT
                t.id, t.fiscal_week, t.status, t.submitted_at, t.reviewed_at, t.review_notes,
                manager.username AS manager_name,
                COALESCE(SUM(w.work_duration), 0) as total_logged_hours,
                COALESCE(SUM(CASE WHEN w.entry_type = 'work' THEN w.work_duration ELSE 0 END), 0) as total_working_hours
            FROM timesheets t
            LEFT JOIN work w ON t.id = w.timesheet_id
            LEFT JOIN userss manager ON t.manager_id = manager.id
            WHERE t.user_id = :user_id
            GROUP BY t.id, t.fiscal_week, t.status, t.submitted_at, t.reviewed_at, t.review_notes, manager.username
            ORDER BY t.fiscal_week DESC
        """
        return conn.query(query, params={"user_id": user_id}, ttl=10)
    except Exception as e:
        st.error(f"Error fetching timesheet history: {e}")
        return pd.DataFrame()

# FIXED: This function now correctly gets the manager from the timesheets table.
def get_all_users_with_managers(conn):
    """
    Fetches all users (excluding admin) and their most recent manager
    from the timesheets table.
    """
    try:
        # This query first finds the most recent timesheet for each user,
        # then joins that to get the manager's name.
        query = """
            WITH LatestManager AS (
                SELECT
                    user_id,
                    manager_id,
                    ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY fiscal_week DESC, id DESC) as rn
                FROM timesheets
            )
            SELECT
                u.id,
                u.username,
                COALESCE(m.username, 'N/A') as manager_name
            FROM userss u
            LEFT JOIN (
                SELECT user_id, manager_id FROM LatestManager WHERE rn = 1
            ) AS lm ON u.id = lm.user_id
            LEFT JOIN userss m ON lm.manager_id = m.id
            WHERE u.role != 'admin'
            ORDER BY u.username ASC
        """
        return conn.query(query, ttl=3600)
    except Exception as e:
        st.error(f"Error fetching users: {e}")
        return pd.DataFrame()

def check_all_days_filled(work_df, start_of_week_date):
    """Checks if there's at least one entry for each day from Monday to Saturday."""
    if work_df.empty:
        return False, ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    weekdays_required = {start_of_week_date + timedelta(days=i) for i in range(6)}
    work_dates_entered = set(pd.to_datetime(work_df['work_date']).dt.date.unique())

    missing_dates = weekdays_required - work_dates_entered
    if not missing_dates:
        return True, []

    missing_day_names = sorted([d.strftime('%A') for d in missing_dates])
    return False, missing_day_names

def get_manager_name(conn, manager_id):
    """Fetches the manager's name."""
    try:
        result = conn.query("SELECT username FROM userss WHERE id = :manager_id", params={"manager_id": manager_id}, ttl=3600)
        return result.iloc[0]['username'] if not result.empty else "Unknown Manager"
    except Exception as e:
        st.error(f"Error fetching manager name: {e}")
        return "Unknown Manager"

def submit_timesheet_for_approval(conn, timesheet_id, current_status):
    """Submits timesheet, updating status and timestamp."""
    try:
        with conn.session as s:
            s.execute(text("""
                UPDATE timesheets
                SET status = 'submitted', submitted_at = NOW(), review_notes = NULL
                WHERE id = :id AND status IN ('draft', 'rejected')
            """), {"id": timesheet_id})
            s.commit()

        action = "RESUBMIT_TIMESHEET" if current_status == 'rejected' else "SUBMIT_TIMESHEET"
        details = f"{action.replace('_', ' ').title()} for timesheet ID: {timesheet_id}"
        log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, action, details)

        st.session_state.timesheet_status = 'submitted'
        st.success("Timesheet submitted successfully! ✅")
        time.sleep(1)
    except Exception as e:
        st.error(f"Failed to submit timesheet: {e}")

# NEW: Helper to format timestamps gracefully
def format_timestamp(ts):
    """Formats a pandas timestamp or returns a default string if NaT."""
    if pd.isna(ts) or ts is None:
        return "N/A"
    return ts.strftime('%b %d, %Y, %I:%M %p')

# NEW: Function to get users with pending timesheets for the manager
def get_late_submitters_for_manager(conn, manager_id):
    """
    Checks on Monday for direct reports who have not submitted the previous week's timesheet.
    """
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist).date()

    # This check is most relevant on Monday and Tuesday
    if today.weekday() not in [0, 1]: # 0=Monday, 1=Tuesday
        return []

    prev_fiscal_week, _, _ = get_previous_week_details()

    try:
        query = """
            SELECT u.username
            FROM userss u
            JOIN timesheets t ON u.id = t.user_id
            WHERE t.manager_id = :manager_id
              AND t.fiscal_week = :fiscal_week
              AND t.status IN ('draft', 'rejected')
        """
        df = conn.query(query, params={"manager_id": manager_id, "fiscal_week": prev_fiscal_week}, ttl=300)
        return df['username'].tolist()
    except Exception as e:
        st.error(f"Error fetching late submitters: {e}")
        return []

# --- Dialogs ---
@st.dialog("➕ Add New Entry")
def add_work_dialog(conn, timesheet_id, start_date, end_date):
    """Dialog for adding a new work/leave/holiday entry."""
    entry_type = st.selectbox("Entry Type", ("Work", "Holiday", "Leave", "Half Day"), key="entry_type_modal")
    with st.form("new_entry_form"):
        work_date = st.date_input("Date", value=datetime.now(pytz.timezone('Asia/Kolkata')).date(), min_value=start_date, max_value=end_date)
        if entry_type == "Work":
            work_name = st.text_input("Work Title", placeholder="e.g., Developed login page")
            work_description = st.text_area("Description", placeholder="e.g., Implemented frontend and backend...")
            work_duration = st.number_input("Time (hours)", min_value=0.25, max_value=8.0, value=1.0, step=0.25)
            reason = None
        else:
            work_description = None
            if entry_type == "Holiday":
                reason = st.text_input("Holiday Name", placeholder="e.g., Independence Day")
                work_duration = 8.0
            elif entry_type == "Leave":
                reason = st.text_area("Reason for Leave", placeholder="e.g., Personal reason")
                work_duration = 8.0
            else: # Half Day
                reason = st.text_area("Reason for Half Day", placeholder="e.g., Doctor's appointment")
                work_duration = 4.0
            work_name = entry_type

        if st.form_submit_button("Add Entry", type="primary"):
            is_valid = (entry_type == "Work" and work_name and work_name.strip()) or \
                       (entry_type != "Work" and reason and reason.strip())
            if not is_valid:
                st.warning("A title or reason is required.")
                return

            try:
                with conn.session as s:
                    s.execute(text("""
                        INSERT INTO work (timesheet_id, work_date, work_name, work_description, work_duration, entry_type, reason)
                        VALUES (:ts_id, :w_date, :w_name, :w_desc, :w_dur, :e_type, :reason)
                    """), {
                        "ts_id": timesheet_id, "w_date": work_date, "w_name": work_name.strip(),
                        "w_desc": work_description.strip() if work_description else None, "w_dur": work_duration,
                        "e_type": entry_type.lower().replace(" ", "_"), "reason": reason.strip() if reason else None
                    })
                    s.commit()
                log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, f"ADD_ENTRY", f"Added {entry_type} entry for {work_duration} hours")
                st.toast(f"Entry added to your timesheet! 🎉")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error adding entry: {e}")

@st.dialog("Confirm Deletion")
def delete_work_entry(conn, work_id):
    """Deletes a specific work entry from the database."""
    st.warning("Are you sure you want to delete this entry? This action cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Yes, Delete", type="primary", use_container_width=True):
        try:
            with conn.session as s:
                s.execute(text("DELETE FROM work WHERE id = :work_id"), {"work_id": work_id})
                s.commit()
            log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "DELETE_ENTRY", f"Deleted work entry ID: {work_id}")
            st.toast("Entry deleted successfully.", icon="🗑️")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Error deleting entry: {e}")
    if c2.button("Cancel", use_container_width=True):
        st.rerun()

@st.dialog("Confirm Submission")
def confirm_submission_dialog(conn, timesheet_id, current_status):
    """Dialog to confirm timesheet submission."""
    manager_name = get_manager_name(conn, st.session_state.report_to)
    if current_status == 'rejected':
        st.info("You are resubmitting a previously rejected timesheet.")
    st.warning(f"Submit this timesheet to **{manager_name}** for approval? This action cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Yes, Submit", use_container_width=True, type="primary"):
        submit_timesheet_for_approval(conn, timesheet_id, current_status)
        st.rerun()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()

@st.dialog("Reject Timesheet")
def reject_timesheet_dialog(conn, timesheet_id):
    """Dialog for managers/admins to reject a timesheet."""
    with st.form("reject_form"):
        notes = st.text_area("Reason for Rejection", placeholder="e.g., Please provide more detail for Wednesday's entry.")
        if st.form_submit_button("Reject Timesheet", type="primary"):
            if not notes.strip():
                st.warning("A reason for rejection is required.")
                return
            try:
                with conn.session as s:
                    s.execute(text("UPDATE timesheets SET status = 'rejected', reviewed_at = NOW(), review_notes = :notes WHERE id = :id"),
                              {"id": timesheet_id, "notes": notes.strip()})
                    s.commit()
                log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "REJECT_TIMESHEET", f"Rejected timesheet ID: {timesheet_id}")
                st.success(f"Timesheet {timesheet_id} has been rejected.")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error rejecting timesheet: {e}")

# --- UI Rendering Functions ---
def render_work_entry(conn, work_row, is_editable):
    """Renders a single work entry."""
    with st.container(border=True):
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            entry_type = work_row.get('entry_type', 'work')
            icon_map = {'holiday': '🏖️', 'leave': '🌴', 'half_day': '🌗'}
            if entry_type in icon_map:
                st.markdown(f"{icon_map[entry_type]} **{work_row['work_name']}**")
                st.caption(f"Reason: {work_row['reason']}")
            else:
                st.markdown(f"**{work_row['work_name']}**")
                if work_row['work_description']:
                    st.caption(f"{work_row['work_description']}")
            st.markdown(f"**`{float(work_row['work_duration']):.2f} hrs`**")
        with col2:
            if is_editable:
                work_id = work_row['id']
                st.button("🗑️", key=f"del_{work_row['id']}", on_click=delete_work_entry,
                          args=(conn, work_id), use_container_width=True, help="Delete this entry")


def render_weekly_work_grid(conn, work_df, start_of_week_date, is_editable=False):
    """Displays work entries in a 6-column grid (Mon-Sat)."""
    days_of_week = [(start_of_week_date + timedelta(days=i)) for i in range(6)]
    cols = st.columns(6)
    for i, day_date in enumerate(days_of_week):
        with cols[i]:
            st.subheader(f"{day_date.strftime('%a')}", anchor=False)
            st.caption(f"{day_date.strftime('%d %b')}")
            day_work_df = work_df[work_df['work_date'] == day_date]
            if not day_work_df.empty:
                for _, row in day_work_df.iterrows():
                    render_work_entry(conn, row, is_editable)
                day_working_hours = day_work_df[day_work_df['entry_type'] == 'work']['work_duration'].sum()
                if day_working_hours > 0:
                    st.markdown(f"**Total Work: `{float(day_working_hours):.2f} hrs`**")
            else:
                st.info("_No entries._", icon="💤")

# --- Page Implementations ---
# MODIFIED: This page now handles the grace period for late submissions.
def my_timesheet_page(conn):
    """Renders the main page for the user's timesheet."""
    st.subheader(f"📝 {st.session_state.username}'s Weekly Timesheet", anchor=False, divider="rainbow")

    # Determine which week to show: current or previous (if pending on Monday)
    fiscal_week, start_of_week, end_of_week, is_late_submission = determine_timesheet_week_to_display(conn, st.session_state.user_id)

    # Display a warning if the user is filling out a late timesheet
    if is_late_submission:
        st.warning(
            "**Action Required:** Your timesheet for the previous week was not submitted on time. "
            "Please complete and submit it before proceeding to the current week.",
            icon="⚠️"
        )

    timesheet_id, status, notes = get_or_create_timesheet(conn, st.session_state.user_id, fiscal_week)
    if timesheet_id is None:
        st.error("Failed to load timesheet. Please refresh.")
        st.stop()

    st.session_state.timesheet_status = status
    c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
    with c1:
        date_range = f"{start_of_week.strftime('%b %d')} - {end_of_week.strftime('%d, %Y')}"
        status_map = {"approved": "🟢", "submitted": "🟠", "rejected": "🔴", "draft": "🔵"}
        st.markdown(f"<h5>Week {fiscal_week} <small>({date_range})</small> {status_map.get(status, '⚪️')} {status.upper()}</h5>", unsafe_allow_html=True)
    
    is_editable = status in ['draft', 'rejected']
    if c2.button("➕ Add Entry", use_container_width=True, disabled=not is_editable, help="Add a new work, holiday, or leave entry."):
        add_work_dialog(conn, timesheet_id, start_of_week, end_of_week)

    submit_button_text = "✔️ Resubmit" if status == 'rejected' else "✔️ Submit"
    if c3.button(submit_button_text, type="primary", use_container_width=True, disabled=not is_editable):
        work_df_check = get_weekly_work(conn, timesheet_id)
        if work_df_check.empty:
            st.warning("Cannot submit an empty timesheet.")
        else:
            is_complete, missing_days = check_all_days_filled(work_df_check, start_of_week)
            if is_complete:
                confirm_submission_dialog(conn, timesheet_id, status)
            else:
                st.error(f"Please add entries for all days. Missing: **{', '.join(missing_days)}**.", icon="❗")

    if status == 'rejected':
        st.warning(f"**Manager's Feedback:** {notes}", icon="⚠️")
        st.info("Your timesheet has been returned. Please make the required changes and resubmit.", icon="ℹ️")

    st.markdown("---")
    work_df = get_weekly_work(conn, timesheet_id)
    render_weekly_work_grid(conn, work_df, start_of_week, is_editable=is_editable)
    st.markdown("---")
    total_logged_hours = work_df['work_duration'].sum()
    working_hours = work_df[work_df['entry_type'] == 'work']['work_duration'].sum()
    col_met1, col_met2 = st.columns(2)
    col_met1.metric("**Total Logged Hours** (Work + Leave/Holiday)", f"{total_logged_hours:.2f} Hours")
    col_met2.metric("**Total Working Hours** (Actual Work)", f"{working_hours:.2f} Hours")


def timesheet_history_page(conn):
    """Renders the page displaying all past timesheets for the logged-in user."""
    st.subheader("📜 My Timesheet History", anchor=False, divider="rainbow")
    history_df = get_user_timesheet_history(conn, st.session_state.user_id)
    if history_df.empty:
        st.info("No timesheet history found.")
        return
    status_map = {"approved": "🟢", "submitted": "🟠", "rejected": "🔴", "draft": "🔵"}
    for _, row in history_df.iterrows():
        work_df = get_weekly_work(conn, row['id'])
        date_range_str, start_of_that_week = "", None
        if not work_df.empty:
            first_entry_date = work_df['work_date'].min()
            year = first_entry_date.year
            start_of_that_week = first_entry_date - timedelta(days=first_entry_date.weekday())
            date_range_str = get_week_dates_from_week_number(year, row['fiscal_week'])
        expander_title = (f"**Week {row['fiscal_week']}** {date_range_str} | "
                          f"Working: **{float(row['total_working_hours']):.2f}h** | "
                          f"Logged: **{float(row['total_logged_hours']):.2f}h** | "
                          f"Status: {status_map.get(row['status'], '⚪️')} **{row['status'].upper()}**")
        with st.expander(expander_title):
            if not work_df.empty and start_of_that_week:
                render_weekly_work_grid(conn, work_df, start_of_that_week, is_editable=False)
            else:
                st.info("No work entries were found for this timesheet.")
            if pd.notna(row['review_notes']):
                st.warning(f"**Manager's Feedback:** {row['review_notes']}", icon="⚠️")

# MODIFIED: Dashboard now alerts managers to late submissions.
def manager_dashboard(conn):
    """Displays timesheets for manager review (direct reports only)."""
    st.subheader("📋 Manager Dashboard", anchor=False, divider="rainbow")
    
    # Check for and display alerts about late submissions
    late_submitters = get_late_submitters_for_manager(conn, st.session_state.user_id)
    if late_submitters:
        st.warning(f"**Pending Submissions:** The following users have not submitted their timesheet from last week: **{', '.join(late_submitters)}**.", icon="🔔")
    
    st.caption("This dashboard shows submitted timesheets from your direct reports.")
    query = """
        SELECT t.id, u.username, t.fiscal_week, t.status, t.submitted_at FROM timesheets t
        JOIN userss u ON t.user_id = u.id
        WHERE t.manager_id = :manager_id AND t.status IN ('submitted', 'approved', 'rejected')
        ORDER BY CASE t.status WHEN 'submitted' THEN 1 WHEN 'approved' THEN 2 WHEN 'rejected' THEN 3 END, t.submitted_at DESC
    """
    df = conn.query(query, params={"manager_id": st.session_state.user_id}, ttl=0)
    if df.empty:
        st.info("No timesheets are pending for your review.")
        return

    status_map = {"approved": "✅", "submitted": "⏳", "rejected": "❌"}
    for _, row in df.iterrows():
        work_df = get_weekly_work(conn, row['id'])
        date_range_str, start_of_week = "", None
        if not work_df.empty:
            first_entry = work_df['work_date'].min()
            year = first_entry.year
            start_of_week = first_entry - timedelta(days=first_entry.weekday())
            date_range_str = get_week_dates_from_week_number(year, row['fiscal_week'])
        
        title = f"{status_map.get(row['status'])} **{row['username']}** - Week {row['fiscal_week']} {date_range_str} (Status: {row['status'].upper()})"
        with st.expander(title):
            if not work_df.empty and start_of_week:
                render_weekly_work_grid(conn, work_df, start_of_week)
                total_logged_hours = work_df['work_duration'].sum()
                working_hours = work_df[work_df['entry_type'] == 'work']['work_duration'].sum()
                m_col1, m_col2 = st.columns(2)
                m_col1.metric("Total Logged Hours", f"{total_logged_hours:.2f}")
                m_col2.metric("Total Working Hours", f"{working_hours:.2f}")
            else:
                st.info("No work entries found.")

            if row['status'] == 'submitted':
                st.markdown("---")
                c1, c2 = st.columns(2)
                if c1.button("Approve", key=f"mgr_approve_{row['id']}", use_container_width=True, type="primary"):
                    with conn.session as s:
                        s.execute(text("UPDATE timesheets SET status = 'approved', reviewed_at = NOW() WHERE id = :id"), {"id": row['id']})
                        s.commit()
                    st.success(f"Timesheet for {row['username']} approved.")
                    time.sleep(1)
                    st.rerun()
                if c2.button("Reject", key=f"mgr_reject_{row['id']}", use_container_width=True):
                    reject_timesheet_dialog(conn, row['id'])

# NEW & OVERHAULED: Admin Dashboard Page
def admin_dashboard(conn):
    """Admin dashboard to view and manage all employees' timesheets with enhanced UI."""
    st.subheader("👑 Admin Dashboard", anchor=False, divider="rainbow")
    st.caption("View and manage timesheets for any employee in the organization.")

    users_df = get_all_users_with_managers(conn)
    if users_df.empty:
        st.error("Could not load users.")
        return

    selected_user = st.selectbox(
        "Select an Employee",
        users_df['username'],
        index=None,
        placeholder="Search for an employee..."
    )

    if not selected_user:
        st.info("Select an employee from the dropdown to view their timesheet history.", icon="👈")
        return

    st.markdown("---")

    selected_user_id = users_df[users_df['username'] == selected_user]['id'].iloc[0]
    manager_name = users_df[users_df['username'] == selected_user]['manager_name'].iloc[0]
    
    st.header(f"Timesheet History for: {selected_user}", anchor=False)
    st.info(f"**Reports to:** {manager_name}", icon="🧑‍💼")


    history_df = get_user_timesheet_history(conn, selected_user_id)
    if history_df.empty:
        st.warning(f"No timesheet history found for {selected_user}.", icon="📂")
        return

    status_map = {"approved": "✅", "submitted": "⏳", "rejected": "❌", "draft": "📝"}
    status_color = {"approved": "green", "submitted": "orange", "rejected": "red", "draft": "blue"}

    for _, row in history_df.iterrows():
        work_df = get_weekly_work(conn, row['id'])
        date_range_str, start_of_week = "", None
        if not work_df.empty:
            first_entry = work_df['work_date'].min()
            year = first_entry.year
            start_of_week = first_entry - timedelta(days=first_entry.weekday())
            date_range_str = get_week_dates_from_week_number(year, row['fiscal_week'])

        expander_title = (f"{status_map.get(row['status'])} **Week {row['fiscal_week']}** {date_range_str} | "
                          f"Status: **:{status_color.get(row['status'], 'grey')}[{row['status'].upper()}]**")

        with st.expander(expander_title):
            col1, col2, col3 = st.columns(3)
            col1.metric("Logged Hours", f"{float(row['total_logged_hours']):.2f}h")
            col2.metric("Working Hours", f"{float(row['total_working_hours']):.2f}h")
            col3.metric("Status", row['status'].title())
            
            st.markdown(
                f"""
                <div style="font-size: 0.9rem; padding-left: 5px;">
                <b>Submitted:</b> {format_timestamp(row['submitted_at'])} <br>
                <b>Reviewed:</b> {format_timestamp(row['reviewed_at'])}
                </div>
                """, unsafe_allow_html=True
            )

            if pd.notna(row['review_notes']):
                st.warning(f"**Review Notes:** {row['review_notes']}", icon="✍️")
            
            st.markdown("---")

            if not work_df.empty and start_of_week:
                render_weekly_work_grid(conn, work_df, start_of_week, is_editable=False)
            else:
                st.info("No work entries found for this timesheet.")

            if row['status'] == 'submitted':
                st.markdown("---")
                btn_c1, btn_c2 = st.columns(2)
                if btn_c1.button("Approve", key=f"admin_approve_{row['id']}", use_container_width=True, type="primary"):
                    with conn.session as s:
                        s.execute(text("UPDATE timesheets SET status = 'approved', reviewed_at = NOW() WHERE id = :id"), {"id": row['id']})
                        s.commit()
                    log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "ADMIN_APPROVE", f"Admin approved timesheet ID: {row['id']} for user {selected_user}")
                    st.success(f"Timesheet for {selected_user} approved.")
                    time.sleep(1)
                    st.rerun()
                if btn_c2.button("Reject", key=f"admin_reject_{row['id']}", use_container_width=True):
                    reject_timesheet_dialog(conn, row['id'])

# --- Main App Runner ---
def main():
    if 'user_id' not in st.session_state:
        st.warning("Please log in to use the application.")
        st.stop()

    conn = connect_db()

    with st.sidebar:
        st.header(f"Welcome, {st.session_state.username}!")
        st.caption(f"Role: {st.session_state.role.title()}")
        st.markdown("---")
        
        pages = []
        # CHANGED: Admins do not see personal timesheet pages.
        if st.session_state.role != 'admin':
            pages.extend(["My Timesheet", "Timesheet History"])

        # Add Manager Dashboard if user is a reporting manager (applies to admins too).
        if st.session_state.level in ['reporting_manager', 'both']:
            pages.append("Manager Dashboard")

        # NEW: Add Admin Dashboard only if user is an admin.
        if st.session_state.role == 'admin':
            pages.append("Admin Dashboard")

        # NEW: Set the default page based on role.
        default_index = 0
        if st.session_state.role == 'admin':
            try:
                # Land on Admin Dashboard if it exists.
                default_index = pages.index("Admin Dashboard")
            except ValueError:
                # Fallback to Manager Dashboard if admin is only a manager.
                if "Manager Dashboard" in pages:
                    default_index = pages.index("Manager Dashboard")

        if not pages:
            st.warning("No pages available for your user role.")
            st.stop()
            
        page = st.radio("Navigation", pages, index=default_index, label_visibility="collapsed")
        st.markdown("---")
        # You can add logout button or other info here

    page_map = {
        "My Timesheet": my_timesheet_page,
        "Timesheet History": timesheet_history_page,
        "Manager Dashboard": manager_dashboard,
        "Admin Dashboard": admin_dashboard
    }
    
    # Run the selected page function
    if page in page_map:
        page_map[page](conn)

if __name__ == "__main__":
    main()