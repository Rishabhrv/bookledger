import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from sqlalchemy import text
import time
from constants import connect_db, get_page_url, log_activity, initialize_click_and_session_id, get_total_unread_count, connect_ict_db
from urllib.parse import urlencode, quote
import uuid
from auth import validate_token
import calendar
from datetime import datetime, timedelta, date


# --- Initial Imports and Setup ---
# This part is assumed to be at the top of your script.
st.set_page_config(layout="wide", page_title="Timesheet", initial_sidebar_state="collapsed", page_icon="⏱️")
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

conn = connect_db()
ict_conn = connect_ict_db()

CHAT_URL  = st.secrets["general"]["CHAT_URL"]

# Initialize session state
if "logged_click_ids" not in st.session_state:
    st.session_state.logged_click_ids = set()
if "activity_logged" not in st.session_state:
    st.session_state.activity_logged = False


if user_app in ["main", "operations", "sales"]:
    initialize_click_and_session_id()

session_id = st.session_state.get("session_id", "Unknown")
click_id = st.session_state.get("click_id", None)


# Ensure user_id and username are set
if not all(key in st.session_state for key in ["user_id", "username"]):
    st.error("Session not initialized. Please log in again.")
    st.stop()

# Log login for direct access (tasks)
if user_app == "tasks" and not st.session_state.activity_logged:
    try:
        log_activity(
            conn,
            st.session_state.user_id,
            st.session_state.username,
            st.session_state.session_id,
            "logged in",
            f"App: {user_app}, Access: {st.session_state.get('access', ['direct'])[0]}"
        )
        st.session_state.activity_logged = True
    except Exception as e:
        st.error(f"Error logging login: {str(e)}")

# Log page access if coming from main page and click_id is new
if user_app in ["main", "operations", "sales"] and click_id and click_id not in st.session_state.logged_click_ids:
    try:
        log_activity(
            conn,
            st.session_state.user_id,
            st.session_state.username,
            st.session_state.session_id,
            "navigated to page",
            f"Page: Tasks"
        )
        st.session_state.logged_click_ids.add(click_id)
    except Exception as e:
        st.error(f"Error logging navigation: {str(e)}")


total_unread = get_total_unread_count(ict_conn, st.session_state.user_id)

if user_app == "tasks" and total_unread > 0:
    if "unread_toast_shown" not in st.session_state:
        st.toast(f"You have {total_unread} unread messages!", icon="💬", duration="infinite")
        st.session_state.unread_toast_shown = True


###################################################################################################################################
##################################--------------- Helper ----------------------------########################################
###################################################################################################################################


# --- Helper Functions ---
def get_current_week_details():
    """Calculates current fiscal week and dates."""
    today = get_ist_date()
    # Monday is 0 and Sunday is 6. This is consistent with isocalendar().
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=5) # Saturday
    fiscal_week = today.isocalendar()[1]
    return fiscal_week, start_of_week, end_of_week

# NEW: Function to specifically get previous week's details
def get_previous_week_details():
    """Calculates the previous fiscal week and its dates."""
    today = get_ist_date()
    # Go to last week (e.g., from Monday, go back one day to Sunday)
    previous_week_date = today - timedelta(days=7)
    start_of_last_week = previous_week_date - timedelta(days=previous_week_date.weekday())
    end_of_last_week = start_of_last_week + timedelta(days=5) # Saturday
    previous_fiscal_week = previous_week_date.isocalendar()[1]
    return previous_fiscal_week, start_of_last_week, end_of_last_week

def get_week_dates_from_fiscal_week(fiscal_week):
    """Get start and end dates for a given fiscal week."""
    try:
        year = datetime.now().isocalendar()[0]  # Assume current year, adjust if needed
        start_of_week = datetime.fromisocalendar(year, fiscal_week, 1).date()
        end_of_week = start_of_week + timedelta(days=5)
        return start_of_week, end_of_week
    except:
        return None, None

def determine_timesheet_week_to_display(conn, user_id):
    """
    Determines which week's timesheet to display.
    STRICT: Forces user to fill ALL missing weeks before current week.
    Checks both for missing weeks AND pending (draft/rejected) weeks.
    """
    today = get_ist_date()
    current_fiscal_week, current_start_of_week, current_end_of_week = get_current_week_details()

    try:
        # Get all existing timesheets for this user
        existing_query = """
            SELECT fiscal_week, status 
            FROM timesheets 
            WHERE user_id = :user_id
            ORDER BY fiscal_week ASC
        """
        existing_df = conn.query(existing_query, params={"user_id": user_id}, ttl=0)
        
        if existing_df.empty:
            # No timesheets at all, show current week
            return current_fiscal_week, current_start_of_week, current_end_of_week, False
        
        # Get the earliest timesheet week
        earliest_week = existing_df.iloc[0]['fiscal_week']
        
        # Check each week from earliest to current
        for week in range(earliest_week, current_fiscal_week):
            week_exists = week in existing_df['fiscal_week'].values
            
            if not week_exists:
                # This week is MISSING - user must fill it first
                try:
                    year = datetime.now().isocalendar()[0]
                    missing_start = datetime.fromisocalendar(year, week, 1).date()
                    missing_end = missing_start + timedelta(days=5)
                    date_range = f"{missing_start.strftime('%b %d')} - {missing_end.strftime('%d, %Y')}"
                    
                    st.warning(
                        f"⚠️ **Missing Timesheet Detected:** Week {week} ({date_range}) "
                        "has not been filled. You must complete all previous weeks before accessing the current week."
                    )
                    
                    return week, missing_start, missing_end, True
                except ValueError:
                    st.error(f"Error calculating dates for week {week}")
                    continue
            else:
                # Week exists, check if it's pending (draft/rejected)
                week_status = existing_df[existing_df['fiscal_week'] == week].iloc[0]['status']
                if week_status in ['draft', 'rejected']:
                    try:
                        year = datetime.now().isocalendar()[0]
                        pending_start = datetime.fromisocalendar(year, week, 1).date()
                        pending_end = pending_start + timedelta(days=5)
                        date_range = f"{pending_start.strftime('%b %d')} - {pending_end.strftime('%d, %Y')}"
                        
                        st.warning(
                            f"⚠️ **Pending Timesheet Detected:** Week {week} ({date_range}) "
                            f"is in **{week_status.upper()}** status. "
                            "You must complete and submit it before accessing the current week."
                        )
                        
                        return week, pending_start, pending_end, True
                    except ValueError:
                        st.error(f"Error calculating dates for week {week}")
                        continue
        
        # Check Monday grace period for previous week
        if today.weekday() == 0:  # Monday
            prev_fiscal_week, prev_start_of_week, prev_end_of_week = get_previous_week_details()
            
            if prev_fiscal_week in existing_df['fiscal_week'].values:
                prev_status = existing_df[existing_df['fiscal_week'] == prev_fiscal_week].iloc[0]['status']
                if prev_status in ['draft', 'rejected']:
                    st.warning(
                        "**Monday Grace Period:** Previous week's timesheet is pending. "
                        "Please complete and submit it now."
                    )
                    return prev_fiscal_week, prev_start_of_week, prev_end_of_week, True

    except Exception as e:
        st.error(f"Error checking timesheets: {e}")
        return current_fiscal_week, current_start_of_week, current_end_of_week, False

    # All previous weeks are complete, show current week
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
    """Fetches or creates a timesheet for the specified week. Blocks creation if previous weeks are missing or pending."""
    try:
        # First, check if timesheet already exists for this week
        query = "SELECT id, status, review_notes FROM timesheets WHERE user_id = :user_id AND fiscal_week = :fiscal_week"
        df = conn.query(query, params={"user_id": user_id, "fiscal_week": fiscal_week}, ttl=0)
        
        if not df.empty:
            return df.iloc[0]['id'], df.iloc[0]['status'], df.iloc[0]['review_notes']

        # Before creating new timesheet, check for missing or pending previous weeks
        # Get all existing timesheets
        existing_query = """
            SELECT fiscal_week, status 
            FROM timesheets 
            WHERE user_id = :user_id
            ORDER BY fiscal_week ASC
        """
        existing_df = conn.query(existing_query, params={"user_id": user_id}, ttl=0)
        
        if not existing_df.empty:
            earliest_week = existing_df.iloc[0]['fiscal_week']
            
            # Check all weeks from earliest to the week we're trying to create
            for week in range(earliest_week, fiscal_week):
                week_exists = week in existing_df['fiscal_week'].values
                
                if not week_exists:
                    # Missing week found - block creation
                    st.error(
                        f"❌ **Cannot create week {fiscal_week}'s timesheet!** "
                        f"Week {week} is missing. "
                        "Please complete all previous weeks first."
                    )
                    return None, None, None
                else:
                    # Check if week is pending
                    week_status = existing_df[existing_df['fiscal_week'] == week].iloc[0]['status']
                    if week_status in ['draft', 'rejected']:
                        st.error(
                            f"❌ **Cannot create week {fiscal_week}'s timesheet!** "
                            f"Week {week} is still in **{week_status.upper()}** status. "
                            "Please complete and submit all previous pending timesheets first."
                        )
                        return None, None, None

        # Safe to create new timesheet
        manager_id = st.session_state.get("report_to")
        if manager_id == "Unknown" or not manager_id:
            st.error("Manager not assigned. Cannot create timesheet. Contact admin for assistance.")
            st.stop()

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
        df = conn.query(query, params={"timesheet_id": timesheet_id}, ttl=0)
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
        return conn.query(query, params={"user_id": user_id}, ttl=0)
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
    """Submits timesheet, updating status and timestamp (IST timezone)."""
    try:
        # Get current time in IST
        submitted_time = get_ist_time()

        with conn.session as s:
            s.execute(text("""
                UPDATE timesheets
                SET status = 'submitted',
                    submitted_at = :submitted_at,
                    review_notes = NULL
                WHERE id = :id AND status IN ('draft', 'rejected')
            """), {"id": timesheet_id, "submitted_at": submitted_time})
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
    today = get_ist_date()

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
    
def get_monthly_summary(conn, user_id: int, year: int, month: int, statuses: list[str] = None) -> dict:
    try:
        start_date = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)

        query = """
            SELECT
                w.work_date,
                w.entry_type,
                w.work_duration,
                w.work_name,
                COALESCE(w.work_description, '') AS work_description,
                t.id AS timesheet_id,
                t.status
            FROM work w
            JOIN timesheets t ON w.timesheet_id = t.id
            WHERE
                t.user_id = :user_id
                AND w.work_date >= :start_date
                AND w.work_date <= :end_date
        """
        params = {"user_id": user_id, "start_date": start_date, "end_date": end_date}
        if statuses:
            query += " AND t.status IN :statuses"
            params["statuses"] = statuses
        query += " ORDER BY w.work_date;"

        df = conn.query(sql=query, params=params, ttl=0)
        if df.empty:
            return {}

        df['work_date'] = pd.to_datetime(df['work_date']).dt.date
        DOWNTIME_TYPES = {'no_internet', 'power_cut', 'system_failure', 'other'}

        summary_data = {}
        for work_date, group in df.groupby('work_date'):
            total_hours = group['work_duration'].sum()
            entry_types = set(group['entry_type'])
            
            # Calculate ALL downtime hours for this day (don't deduplicate)
            downtime_entries = group[group['entry_type'].isin(DOWNTIME_TYPES)]
            total_downtime_hours = downtime_entries['work_duration'].sum()
            
            # Day status classification (for UI display)
            status = 'work'  # Default
            if 'leave' in entry_types:
                status = 'leave'
            elif 'holiday' in entry_types:
                status = 'holiday'
            elif 'half_day' in entry_types:
                status = 'half_day'
            elif total_downtime_hours > 0 and 'work' not in entry_types:
                # Day is purely downtime or downtime dominant
                if len(downtime_entries) > 0:
                    # Use the type with most instances or hours
                    most_common_type = downtime_entries['entry_type'].mode().iloc[0]
                    status = most_common_type
            # Keep as 'work' if mixed work + downtime

            type_hours = group.groupby('entry_type')['work_duration'].sum().to_dict()
            holiday_name = None
            if 'holiday' in entry_types:
                holiday_row = group[group['entry_type'] == 'holiday'].iloc[0]
                holiday_name = holiday_row['work_name']

            day_summary = {
                'status': status,
                'total_hours': total_hours,
                'total_downtime_hours': total_downtime_hours,  # NEW: Track all downtime
                'type_hours': type_hours,
                'downtime_types': downtime_entries['entry_type'].tolist(),  # NEW: Track which types
                'holiday_name': holiday_name,
                'timesheet_id': group['timesheet_id'].iloc[0],
                'timesheet_status': group['status'].iloc[0]
            }
            
            summary_data[work_date] = day_summary

        return summary_data

    except Exception as e:
        st.error(f"Error fetching monthly summary: {e}")
        return {}

def get_daily_checklist_monthly_summary(conn, user_id: int, year: int, month: int) -> dict:
    try:
        start_date = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)

        # Fetch submissions and logs status
        query = """
            SELECT 
                s.date, 
                s.status as submission_status,
                l.status as log_status,
                r.task_name
            FROM daily_checklist_submissions s
            JOIN daily_checklist_logs l ON s.id = l.submission_id
            JOIN daily_responsibilities r ON l.responsibility_id = r.id
            WHERE s.user_id = :user_id 
            AND s.date >= :start_date 
            AND s.date <= :end_date
        """
        df = conn.query(query, params={"user_id": user_id, "start_date": start_date, "end_date": end_date}, ttl=0)
        
        if df.empty:
            return {}

        df['date'] = pd.to_datetime(df['date']).dt.date
        
        summary_data = {}
        for checklist_date, group in df.groupby('date'):
            # Determine daily status based on tasks
            statuses = set(group['log_status'])
            
            if 'rejected' in statuses:
                day_status = 'rejected'
            elif 'started' in statuses:
                day_status = 'started'
            elif all(s == 'approved' for s in statuses):
                day_status = 'approved'
            elif 'submitted' in statuses or 'approved' in statuses:
                day_status = 'submitted'
            else:
                day_status = 'pending'
                
            summary_data[checklist_date] = {
                'status': day_status,
                'tasks': group[['task_name', 'log_status']].to_dict('records')
            }
            
        return summary_data
    except Exception as e:
        return {}

def get_user_lifetime_stats(conn, user_id: int) -> dict:
    try:
        # Total work hours
        query_work = """
            SELECT COALESCE(SUM(w.work_duration), 0) AS total_work_hours
            FROM work w
            JOIN timesheets t ON w.timesheet_id = t.id
            WHERE t.user_id = :user_id AND w.entry_type = 'work'
        """
        df_work = conn.query(sql=query_work, params={"user_id": user_id}, ttl=0)
        total_work_hours = df_work['total_work_hours'].iloc[0] if not df_work.empty else 0

        # Leave days
        query_leave = """
            SELECT COUNT(DISTINCT w.work_date) AS leave_days
            FROM work w
            JOIN timesheets t ON w.timesheet_id = t.id
            WHERE t.user_id = :user_id AND w.entry_type = 'leave'
        """
        df_leave = conn.query(sql=query_leave, params={"user_id": user_id}, ttl=0)
        leave_days = df_leave['leave_days'].iloc[0] if not df_leave.empty else 0

        # Half days
        query_half = """
            SELECT COUNT(DISTINCT w.work_date) AS half_days
            FROM work w
            JOIN timesheets t ON w.timesheet_id = t.id
            WHERE t.user_id = :user_id AND w.entry_type = 'half_day'
        """
        df_half = conn.query(sql=query_half, params={"user_id": user_id}, ttl=0)
        half_days = df_half['half_days'].iloc[0] if not df_half.empty else 0

        # Holiday days
        query_holiday = """
            SELECT COUNT(DISTINCT w.work_date) AS holiday_days
            FROM work w
            JOIN timesheets t ON w.timesheet_id = t.id
            WHERE t.user_id = :user_id AND w.entry_type = 'holiday'
        """
        df_holiday = conn.query(sql=query_holiday, params={"user_id": user_id}, ttl=0)
        holiday_days = df_holiday['holiday_days'].iloc[0] if not df_holiday.empty else 0

        # Total downtime hours and breakdown
        query_downtime = """
            SELECT 
                COALESCE(SUM(CASE WHEN w.entry_type = 'no_internet' THEN w.work_duration ELSE 0 END), 0) AS no_internet_hours,
                COALESCE(SUM(CASE WHEN w.entry_type = 'power_cut' THEN w.work_duration ELSE 0 END), 0) AS power_cut_hours,
                COALESCE(SUM(CASE WHEN w.entry_type = 'system_failure' THEN w.work_duration ELSE 0 END), 0) AS system_failure_hours,
                COALESCE(SUM(CASE WHEN w.entry_type = 'other' THEN w.work_duration ELSE 0 END), 0) AS other_downtime_hours,
                COALESCE(SUM(CASE WHEN w.entry_type IN ('no_internet', 'power_cut', 'system_failure', 'other') 
                          THEN w.work_duration ELSE 0 END), 0) AS total_downtime_hours
            FROM work w
            JOIN timesheets t ON w.timesheet_id = t.id
            WHERE t.user_id = :user_id 
            AND w.entry_type IN ('no_internet', 'power_cut', 'system_failure', 'other')
        """
        df_downtime = conn.query(sql=query_downtime, params={"user_id": user_id}, ttl=0)
        downtime_row = df_downtime.iloc[0] if not df_downtime.empty else {}
        
        total_downtime_hours = downtime_row.get('total_downtime_hours', 0)
        no_internet_hours = downtime_row.get('no_internet_hours', 0)
        power_cut_hours = downtime_row.get('power_cut_hours', 0)
        system_failure_hours = downtime_row.get('system_failure_hours', 0)
        other_downtime_hours = downtime_row.get('other_downtime_hours', 0)

        # Total unique working days (excluding leaves, holidays, half_days)
        query_working_days = """
            SELECT COUNT(DISTINCT w.work_date) AS working_days
            FROM work w
            JOIN timesheets t ON w.timesheet_id = t.id
            WHERE t.user_id = :user_id 
            AND w.entry_type = 'work'
        """
        df_working_days = conn.query(sql=query_working_days, params={"user_id": user_id}, ttl=0)
        working_days = df_working_days['working_days'].iloc[0] if not df_working_days.empty else 0

        # Average daily work hours
        avg_daily_hours = total_work_hours / working_days if working_days > 0 else 0

        return {
            # Core hours
            'total_work_hours': round(total_work_hours, 2),
            'total_downtime_hours': round(total_downtime_hours, 2),
            'leave_days': leave_days,
            'half_days': half_days,
            'holiday_days': holiday_days,
            'working_days': working_days,
            'avg_daily_hours': round(avg_daily_hours, 2),
            
            # Downtime breakdown
            'downtime_breakdown': {
                'no_internet': round(no_internet_hours, 2),
                'power_cut': round(power_cut_hours, 2),
                'system_failure': round(system_failure_hours, 2),
                'other': round(other_downtime_hours, 2)
            },
            
            # REMOVED: total_billable_hours
            # REMOVED: downtime_percentage - now just use total_downtime_hours directly
        }

    except Exception as e:
        st.error(f"Error fetching lifetime stats: {e}")
        return {
            'total_work_hours': 0, 
            'total_downtime_hours': 0, 
            'leave_days': 0, 
            'half_days': 0, 
            'holiday_days': 0, 
            'working_days': 0, 
            'avg_daily_hours': 0,
            'downtime_breakdown': {
                'no_internet': 0, 
                'power_cut': 0, 
                'system_failure': 0, 
                'other': 0
            }
        }

    except Exception as e:
        st.error(f"Error fetching lifetime stats: {e}")
        return {
            'total_work_hours': 0, 'total_downtime_hours': 0, 'leave_days': 0, 
            'half_days': 0, 'holiday_days': 0, 'working_days': 0, 'avg_daily_hours': 0,
            'downtime_breakdown': {'no_internet': 0, 'power_cut': 0, 'system_failure': 0, 'other': 0},
            'submitted_timesheets': 0, 'approved_timesheets': 0, 'pending_timesheets': 0,
            'downtime_percentage': 0
        }

def get_activity_log_for_user(conn, selected_date, username, allowed_actions=None):
    query = """
        SELECT timestamp, user_id, username, session_id, action, details 
        FROM activity_log 
        WHERE DATE(timestamp) = :selected_date AND LOWER(username) = LOWER(:username)
    """
    params = {"selected_date": selected_date, "username": username}
    
    if allowed_actions:
        # Robust expansion for IN clause with case-insensitivity
        action_placeholders = [f":action_{i}" for i in range(len(allowed_actions))]
        query += f" AND LOWER(action) IN ({', '.join(action_placeholders)})"
        for i, action in enumerate(allowed_actions):
            params[f"action_{i}"] = action.strip().lower()
        
    query += " ORDER BY timestamp DESC"
    return conn.query(query, params=params, ttl=0)

def calculate_session_duration(session_group):
    timestamps = pd.to_datetime(session_group['timestamp'])
    duration = timestamps.max() - timestamps.min()
    total_seconds = int(duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0: return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0: return f"{minutes}m {seconds}s"
    else: return f"{seconds}s"

def get_action_emoji(action):
    action_emojis = {
        'logged in': '🔐', 'navigated to page': '🧭', 'changed author type': '✍️',
        'updated writing details': '📝', 'updated author': '👤', 'updated proofreading details': '🔍',
        'updated formatting details': '📐', 'updated formatting correction': '📐', 'updated writing correction': '✏️',
        'updated proofreading correction': '🔎', 'added formatting correction': '➕', 'added proofreading correction': '➕',
        'updated writing correction details': '✏️', 'added writing correction': '➕', 'updated cover details': '🎨',
        'edited print edition': '🖨️', 'updated book': '📚', 'toggled checkbox': '☑️',
        'updated writing corrections': '✏️', 'opened dialog': '💬', 'added print edition': '🖨️',
        'updated links': '🔗', 'updated sales': '💰', 'searched': '🔎', 'updated book details': '📖',
        'cleaned old logs': '🧹', 'updated checklist': '✅'
    }
    return action_emojis.get(action.lower(), '⚙️')

def display_lifetime_stats(conn, user_id):
    """Enhanced lifetime statistics with icons and styling."""
    stats = get_user_lifetime_stats(conn, user_id)
    
    # Row 1: Work metrics with green theme
    row1_cols = st.columns(5)
    
    row1_metrics = [
        ("Total Work Hours", f"{stats['total_work_hours']} hrs", "🕐"),
        ("Working Days", stats['working_days'], "📅"),
        ("Leave Days", stats['leave_days'], "🏖️"),
        ("Half Days", stats['half_days'], "⏰"),
        ("Holiday Days", stats['holiday_days'], "🎉")
    ]
    
    for i, (label, value, icon) in enumerate(row1_metrics):
        with row1_cols[i]:
            st.metric(f"{icon} {label}", value)
    
    # Row 2: Productivity & Downtime with mixed theme
    row2_cols = st.columns(5)
    
    # Avg daily hours
    with row2_cols[0]:
        st.metric("📊 Avg Daily Hours", f"{stats['avg_daily_hours']} hrs")
    
    # Downtime metrics with warning colors
    downtime_icons = {
        'no_internet': "🌐",
        'power_cut': "⚡",
        'system_failure': "💻",
        'other': "❓"
    }
    
    for i, downtime_type in enumerate(['no_internet', 'power_cut', 'system_failure', 'other']):
        hours = stats['downtime_breakdown'][downtime_type]
        icon = downtime_icons.get(downtime_type, "⛔")
        display_name = downtime_type.replace('_', ' ').title()
        
        with row2_cols[i + 1]:
            st.metric(f"{icon} {display_name}", f"{hours} hrs")
    
    # Total downtime highlight
    total_downtime = stats['total_downtime_hours']
    if total_downtime > 0:
        st.warning(f"**Total Downtime: {total_downtime} hours** across all categories")

def display_monthly_stats(monthly_summary, selected_year, selected_month, 
                         expected_working_days, expected_working_hours):
    """
    Enhanced monthly statistics display with icons and styling.
    Similar structure to display_lifetime_stats.
    """
    # Calculate monthly metrics from summary
    total_work_hours_month = sum(d.get('type_hours', {}).get('work', 0) for d in monthly_summary.values())
    leave_days_month = len([d for d in monthly_summary.values() if 'leave' in d.get('type_hours', {})])
    half_days_month = len([d for d in monthly_summary.values() if 'half_day' in d.get('type_hours', {})])
    working_days_month = len([d for d in monthly_summary.values() if d.get('type_hours', {}).get('work', 0) > 0])
    total_downtime_month = calculate_monthly_downtime(monthly_summary)
    
    # Row 1: Monthly work metrics with borders
    st.markdown(f"### **📅 {calendar.month_name[selected_month]} {selected_year} Summary**")
    row1_cols = st.columns(5, border=True)
    
    row1_metrics = [
        ("Working Days", working_days_month, f"expected {expected_working_days}", "🖥️"),
        ("Work Hours", f"{total_work_hours_month:.1f}h", f"expected {expected_working_hours:.1f}h", "🕐"),
        ("Leave Days", leave_days_month, None, "🏖️"),
        ("Half Days", half_days_month, None, "⏰"),
        ("Downtime", f"{total_downtime_month:.1f}h", None, "⛔")
    ]
    
    for i, (label, value, delta, icon) in enumerate(row1_metrics):
        with row1_cols[i]:
            metric_display = f"{icon} {label}"
            if delta:
                st.metric(metric_display, value, delta=delta)
            else:
                st.metric(metric_display, value)

def calculate_monthly_downtime(summary_data):
    """Calculate total downtime from monthly summary."""
    DOWNTIME_TYPES = ['no_internet', 'power_cut', 'system_failure', 'other']
    total_downtime = 0
    
    for day_data in summary_data.values():
        # Method 1: Use the new total_downtime_hours field (preferred)
        if 'total_downtime_hours' in day_data:
            total_downtime += day_data['total_downtime_hours']
        else:
            # Fallback: Sum all downtime types from type_hours
            day_downtime = sum(day_data.get('type_hours', {}).get(dt, 0) for dt in DOWNTIME_TYPES)
            total_downtime += day_downtime
    
    return total_downtime

def get_week_checklist_status(week_dates, daily_summary):
    """Determines the aggregated status for a week of checklists."""
    statuses = [daily_summary[d]['status'] for d in week_dates if d in daily_summary]
    if not statuses:
        return None
    if 'rejected' in statuses:
        return 'rejected'
    if 'started' in statuses:
        return 'started'
    if 'submitted' in statuses:
        return 'submitted'
    if all(s == 'approved' for s in statuses):
        return 'approved'
    return 'pending'

def display_checklist_monthly_stats(monthly_summary, selected_year, selected_month, expected_working_days):
    """Displays monthly summary statistics for daily checklists."""
    approved_days = len([d for d in monthly_summary.values() if d['status'] == 'approved'])
    submitted_days = len([d for d in monthly_summary.values() if d['status'] == 'submitted'])
    rejected_days = len([d for d in monthly_summary.values() if d['status'] == 'rejected'])
    pending_days = len([d for d in monthly_summary.values() if d['status'] in ['pending', 'started']])

    st.markdown(f"### **📅 {calendar.month_name[selected_month]} {selected_year} Checklist Summary**")
    cols = st.columns(5, border=True)
    
    metrics = [
        ("Working Days", expected_working_days, None, "📅"),
        ("Approved", approved_days, None, "✅"),
        ("Submitted", submitted_days, None, "📤"),
        ("Rejected", rejected_days, None, "❌"),
        ("Pending", pending_days, None, "🕒")
    ]
    
    for i, (label, value, delta, icon) in enumerate(metrics):
        with cols[i]:
            st.metric(f"{icon} {label}", value)

def get_available_months_years(conn, user_id: int) -> tuple:
    try:
        query = """
            SELECT DISTINCT
                EXTRACT(YEAR FROM w.work_date) AS year,
                EXTRACT(MONTH FROM w.work_date) AS month
            FROM work w
            JOIN timesheets t ON w.timesheet_id = t.id
            WHERE t.user_id = :user_id
            ORDER BY year, month;
        """
        params = {"user_id": user_id}
        df = conn.query(sql=query, params=params, ttl=0)
        
        if df.empty:
            return [], {}
        
        years = sorted(df['year'].astype(int).unique().tolist())
        month_by_year = {y: sorted(df[df['year']==y]['month'].astype(int).tolist()) for y in years}
        return years, month_by_year

    except Exception as e:
        st.error(f"Error fetching available months/years: {e}")
        return [], {}

def get_checklist_available_months_years(conn, user_id: int) -> tuple:
    try:
        query = """
            SELECT DISTINCT
                EXTRACT(YEAR FROM date) AS year,
                EXTRACT(MONTH FROM date) AS month
            FROM daily_checklist_submissions
            WHERE user_id = :user_id
            ORDER BY year, month;
        """
        params = {"user_id": user_id}
        df = conn.query(sql=query, params=params, ttl=0)
        
        if df.empty:
            return [], {}
        
        years = sorted(df['year'].astype(int).unique().tolist())
        month_by_year = {y: sorted(df[df['year']==y]['month'].astype(int).tolist()) for y in years}
        return years, month_by_year

    except Exception as e:
        st.error(f"Error fetching checklist available months/years: {e}")
        return [], {}

def get_work_for_week(conn, user_id: int, week_start_date: date) -> pd.DataFrame:
    try:
        week_end_date = week_start_date + timedelta(days=6)

        query = """
            SELECT
                w.id,
                w.work_date,
                w.entry_type,
                w.work_name,
                COALESCE(w.work_description, '') AS work_description,
                COALESCE(w.reason, '') AS reason,
                w.work_duration,
                t.id AS timesheet_id,
                t.status,
                COALESCE(t.review_notes, '') AS review_notes
            FROM work w
            JOIN timesheets t ON w.timesheet_id = t.id
            WHERE
                t.user_id = :user_id
                AND w.work_date BETWEEN :start_date AND :end_date
            ORDER BY w.work_date ASC, w.id ASC;
        """
        params = {"user_id": user_id, "start_date": week_start_date, "end_date": week_end_date}
        df = conn.query(sql=query, params=params, ttl=0)

        if not df.empty:
            df['work_date'] = pd.to_datetime(df['work_date']).dt.date
        
        return df

    except Exception as e:
        st.error(f"Error fetching weekly work details: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_direct_reports(_conn, manager_id: int) -> pd.DataFrame:
    try:
        # Include users where manager is assigned explicitly OR via user_app_access default
        query = """
            SELECT DISTINCT u.id, u.username FROM userss u
            LEFT JOIN timesheets t ON u.id = t.user_id
            LEFT JOIN daily_responsibilities dr ON u.id = dr.user_id
            LEFT JOIN daily_checklist_submissions dcs ON u.id = dcs.user_id
            LEFT JOIN user_app_access uaa ON u.id = uaa.user_id
            WHERE t.manager_id = :manager_id 
               OR dr.manager_id = :manager_id
               OR dcs.manager_id = :manager_id
               OR (uaa.report_to = :manager_id AND uaa.app = 'tasks')
            ORDER BY u.username;
        """
        params = {"manager_id": manager_id}
        df = _conn.query(sql=query, params=params, ttl=0)
        return df
    except Exception as e:
        st.error(f"Error fetching direct reports: {e}")
        return pd.DataFrame()
    
def get_weekly_timesheet_details(conn, user_id: int, week_start_date: date) -> pd.DataFrame:
    """
    Fetches comprehensive weekly timesheet details, including work entries,
    timesheet status, timestamps, and manager/reviewer information.
    """
    try:
        week_end_date = week_start_date + timedelta(days=6)

        query = """
            SELECT
                w.id,
                w.work_date,
                w.entry_type,
                w.work_name,
                COALESCE(w.work_description, '') AS work_description,
                COALESCE(w.reason, '') AS reason,
                w.work_duration,
                t.id AS timesheet_id,
                t.status,
                t.submitted_at,
                t.reviewed_at,
                COALESCE(t.review_notes, '') AS review_notes,
                m.username AS manager_name
            FROM work w
            JOIN timesheets t ON w.timesheet_id = t.id
            LEFT JOIN userss m ON t.manager_id = m.id
            WHERE
                t.user_id = :user_id
                AND w.work_date BETWEEN :start_date AND :end_date
            ORDER BY w.work_date ASC, w.id ASC;
        """
        params = {"user_id": user_id, "start_date": week_start_date, "end_date": week_end_date}
        df = conn.query(sql=query, params=params, ttl=0)

        if not df.empty:
            df['work_date'] = pd.to_datetime(df['work_date']).dt.date
            df['submitted_at'] = pd.to_datetime(df['submitted_at'])
            df['reviewed_at'] = pd.to_datetime(df['reviewed_at'])
            
        return df

    except Exception as e:
        st.error(f"Error fetching weekly timesheet details: {e}")
        return pd.DataFrame()


def render_status_metric(value: str):
    """Renders a status metric with custom styling to control font size."""
    st.markdown(
        f"""
        <div style='text-align: center;'>
            <p style='font-size: 1.5rem; font-weight: 600; margin: 2px 0 0 0;'>{value}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_compact_metric(label: str, value: str, help_text: str = ""):
    st.markdown(
        f"""
        <div style='text-align: center;' title='{help_text}'>
            <span style='font-size: 0.8rem; color: #808495; text-transform: uppercase; letter-spacing: 0.5px;'>{label}</span>
            <p style='font-size: 1.25rem; font-weight: 600; margin: 2px 0 0 0;'>{value}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_status_detail(label: str, person: str, ts: datetime):
    """Renders the submission/review details in a compact format for a column."""
    st.markdown(f"""
        <div style='text-align: center; line-height: 1.4;'>
            <span style='font-size: 0.8rem; color: #808495; text-transform: uppercase; letter-spacing: 0.5px;'>{label}</span>
            <p style='font-size: 1.1rem; font-weight: 600; margin: 2px 0 0 0;'>{person}</p>
            <span style='font-size: 0.75rem; color: #808495; padding-bottom: 5px'>{ts.strftime('%b %d, %I:%M %p')}</span>
        </div>
        """, unsafe_allow_html=True)
    
    
def get_submitted_timesheet_users(conn, manager_id):
    """
    Retrieves usernames of direct reports who have submitted their timesheets for the current or previous week.
    
    Args:
        conn: Database connection object.
        manager_id (int): ID of the manager.
    
    Returns:
        list: List of usernames who have submitted their timesheets.
    """
    today = get_ist_date()
    
    # Determine the fiscal week to check
    if today.weekday() in [0, 1]:  # Monday or Tuesday, check previous week
        fiscal_week, _, _ = get_previous_week_details()
    else:
        # Assume get_current_week_details() exists to get current week's fiscal week
        fiscal_week, _, _ = get_current_week_details()  # Replace with actual function if different
    
    try:
        query = """
            SELECT u.username
            FROM userss u
            JOIN timesheets t ON u.id = t.user_id
            WHERE t.manager_id = :manager_id
              AND t.fiscal_week = :fiscal_week
              AND t.status = 'submitted'
        """
        df = conn.query(query, params={"manager_id": manager_id, "fiscal_week": fiscal_week}, ttl=0)
        return df['username'].tolist()
    except Exception as e:
        st.error(f"Error fetching submitted timesheet users: {e}")
        return []


def get_user_details(user_id):
    """
    Retrieve user details (username, role, associate_id, designation, report_to username) from the database.
    
    Args:
        user_id (int): The ID of the user to fetch details for.
    
    Returns:
        dict: Dictionary containing username, role, associate_id, designation, and report_to (username or None).
              Returns None if the user is not found or an error occurs.
    """
    conn = connect_db()
    try:
        query = """
            SELECT 
                u.username,
                u.role,
                u.associate_id,
                u.designation,
                r.username AS report_to
            FROM userss u
            LEFT JOIN user_app_access uaa ON u.id = uaa.user_id
            LEFT JOIN userss r ON uaa.report_to = r.id
            WHERE u.id = :user_id
        """
        result = conn.query(query, params={"user_id": user_id}, ttl=0)
        
        if result.empty:
            return None
        
        user_details = {
            "username": result['username'].iloc[0],
            "role": result['role'].iloc[0],
            "associate_id": result['associate_id'].iloc[0],
            "designation": result['designation'].iloc[0],
            "report_to": result['report_to'].iloc[0] if not result['report_to'].isna().iloc[0] else None
        }
        return user_details
    
    except Exception as e:
        st.error(f"Error fetching user details: {e}")
        return None
    
def get_recent_work_titles(conn, user_id, limit=15):
    """Fetch recent distinct work titles for the user."""
    try:
        query = """
            SELECT DISTINCT work_name
            FROM (
                SELECT w.work_name, w.created_at
                FROM work w
                JOIN timesheets t ON w.timesheet_id = t.id
                WHERE t.user_id = :user_id 
                AND w.entry_type = 'work'
                AND w.work_name IS NOT NULL 
                AND w.work_name != '' 
                AND w.work_name != 'Work'
                ORDER BY w.created_at DESC
                LIMIT :limit
            ) AS subquery
        """
        result = conn.query(query, params={"user_id": user_id, "limit": limit}, ttl=0)
        titles = [row['work_name'] for _, row in result.iterrows()]
        if not titles:
            st.warning("No recent work titles found. Please add a new work title.")
        return titles
    except Exception as e:
        st.error(f"Error fetching work titles: {e}")
        return []
    
# Helper function to get current IST time
def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

# Helper function to get current IST time
def get_ist_date():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).date()
    
###################################################################################################################################
##################################--------------- Dialogs----------------------------########################################
###################################################################################################################################



@st.dialog("⚙️ Manage Entry", width="small")
def manage_work_entry(conn, work_entry_row, start_date, end_date):
    """A single dialog for both editing and deleting a work entry, including new types."""
    entry_type_map = {
        "work": "Work", "holiday": "Holiday", "leave": "Leave", "half_day": "Half Day",
        "no_internet": "No Internet", "power_cut": "Power Cut", "system_failure": "System Failure", "other": "Other"
    }
    entry_types = list(entry_type_map.values())
    current_entry_type = entry_type_map.get(work_entry_row['entry_type'], "Work")

    try:
        default_index = entry_types.index(current_entry_type)
    except ValueError:
        default_index = 0

    # Initialize session state for tracking entry type changes
    if f"prev_entry_type_{work_entry_row['id']}" not in st.session_state:
        st.session_state[f"prev_entry_type_{work_entry_row['id']}"] = current_entry_type

    # --- Edit Form ---
    with st.form(f"edit_entry_form_{work_entry_row['id']}"):


        entry_type_selection = st.selectbox(
            "Entry Type",
            entry_types,
            index=default_index,
            key=f"entry_type_edit_{work_entry_row['id']}"
        )

        # Check if entry type has changed
        entry_type_changed = st.session_state[f"prev_entry_type_{work_entry_row['id']}"] != entry_type_selection

        work_date = st.date_input(
            "Date",
            value=pd.to_datetime(work_entry_row['work_date']).date(),
            min_value=start_date,
            max_value=end_date
        )

        current_week_work_titles = get_recent_work_titles(
            conn, st.session_state.user_id
        )

        # Logic to display correct fields based on selected entry type
        if entry_type_selection == "Work":
            # Only use existing data if entry type hasn't changed
            work_name_value = '' if entry_type_changed else work_entry_row.get('work_name', '')
            # Find the index of existing work title in current week titles
            default_index = None
            if work_name_value and work_name_value in current_week_work_titles:
                default_index = current_week_work_titles.index(work_name_value)

            work_name = st.selectbox(
                "Work Title",
                options=current_week_work_titles,
                index= default_index,
                format_func=lambda x: x,
                placeholder="Select existing work or type new...",
                key=f"work_title_select_{work_entry_row['id']}",
                accept_new_options=True
            )
            
            work_desc_value = '' if entry_type_changed else (work_entry_row.get('work_description', '') or '')
            work_description = st.text_area("Description", value=work_desc_value, placeholder="e.g., Implemented frontend and backend...")
            duration_value = 1.0 if entry_type_changed else float(work_entry_row.get('work_duration', 1.0))
            
            col1, col2 = st.columns(2)
            with col1:
                hours = st.number_input("Hours", min_value=0, max_value=8, value=int(duration_value), step=1)
            with col2:
                minutes = st.number_input("Minutes", min_value=0, max_value=59, value=int((duration_value % 1) * 60), step=5)
            work_duration = hours + minutes / 60.0
            reason = None
            
        elif entry_type_selection == "Holiday":
            work_name = entry_type_selection
            work_description = None
            reason_value = '' if entry_type_changed else (work_entry_row.get('reason', '') or '')
            reason = st.text_input("Holiday Name", value=reason_value, placeholder="e.g., Independence Day")
            work_duration = 0.0
            
        elif entry_type_selection == "Leave":
            work_name = entry_type_selection
            work_description = None
            reason_value = '' if entry_type_changed else (work_entry_row.get('reason', '') or '')
            reason = st.text_area("Reason for Leave", value=reason_value, placeholder="e.g., Personal reason")
            work_duration = 0.0
            
        elif entry_type_selection == "Half Day":
            work_name = entry_type_selection
            work_description = None
            reason_value = '' if entry_type_changed else (work_entry_row.get('reason', '') or '')
            reason = st.text_area("Reason for Half Day", value=reason_value, placeholder="e.g., Doctor's appointment")
            work_duration = 0.0
            
        elif entry_type_selection in ("No Internet", "Power Cut"):
            work_name = entry_type_selection
            work_description = None
            reason = entry_type_selection
            st.text_input("Reason", value=entry_type_selection, disabled=True)
            duration_value = 1.0 if entry_type_changed else float(work_entry_row.get('work_duration', 1.0))
            col1, col2 = st.columns(2)
            with col1:
                hours = st.number_input("Downtime Hours", min_value=0, max_value=8, value=int(duration_value), step=1)
            with col2:
                minutes = st.number_input("Downtime Minutes", min_value=0, max_value=59, value=int((duration_value % 1) * 60), step=1)
            work_duration = hours + minutes / 60.0
            
        elif entry_type_selection == "System Failure":
            work_name = entry_type_selection
            work_description = None
            reason_value = '' if entry_type_changed else (work_entry_row.get('reason', '') or '')
            reason = st.text_area("Problem Description", value=reason_value, placeholder="e.g., PC won't boot, Blue screen error, Hardware malfunction...")
            duration_value = 1.0 if entry_type_changed else float(work_entry_row.get('work_duration', 1.0))
            col1, col2 = st.columns(2)
            with col1:
                hours = st.number_input("Downtime Hours", min_value=0, max_value=8, value=int(duration_value), step=1)
            with col2:
                minutes = st.number_input("Downtime Minutes", min_value=0, max_value=59, value=int((duration_value % 1) * 60), step=1)
            work_duration = hours + minutes / 60.0
            
        elif entry_type_selection == "Other":
            work_name = entry_type_selection
            work_description = None
            reason_value = '' if entry_type_changed else (work_entry_row.get('reason', '') or '')
            reason = st.text_area("Reason", value=reason_value, placeholder="Please specify the reason for the downtime.")
            duration_value = 1.0 if entry_type_changed else float(work_entry_row.get('work_duration', 1.0))
            col1, col2 = st.columns(2)
            with col1:
                hours = st.number_input("Downtime Hours", min_value=0, max_value=8, value=int(duration_value), step=1)
            with col2:
                minutes = st.number_input("Downtime Minutes", min_value=0, max_value=59, value=int((duration_value % 1) * 60), step=1)
            work_duration = hours + minutes / 60.0

        col1, col2 = st.columns([1.5, 1])
        with col1:
            submit_button = st.form_submit_button("💾 Update Entry", type="primary", width='stretch')
        with col2:
            delete_button = st.form_submit_button("🗑️ Delete Entry", type="secondary", width='stretch')

        if submit_button:
            # Update the previous entry type tracker
            st.session_state[f"prev_entry_type_{work_entry_row['id']}"] = entry_type_selection
            
            is_valid = False
            if entry_type_selection == "Work":
                is_valid = work_name and work_name.strip()
            elif entry_type_selection in ("Holiday", "Leave", "Half Day", "System Failure", "Other"):
                is_valid = reason and reason.strip()
            elif entry_type_selection in ("No Internet", "Power Cut"):
                is_valid = True

            if not is_valid:
                st.warning("A title or reason is required.")
                return

            try:
                with conn.session as s:
                    s.execute(text("""
                        UPDATE work SET
                            work_date = :w_date, work_name = :w_name, work_description = :w_desc,
                            work_duration = :w_dur, entry_type = :e_type, reason = :reason
                        WHERE id = :work_id
                    """), {
                        "work_id": work_entry_row['id'], "w_date": work_date, "w_name": work_name.strip(),
                        "w_desc": work_description.strip() if work_description else None, "w_dur": work_duration,
                        "e_type": entry_type_selection.lower().replace(" ", "_"), "reason": reason.strip() if reason else None
                    })
                    s.commit()
                log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "UPDATE_ENTRY", f"Updated entry ID: {work_entry_row['id']}")
                st.session_state.last_selected_date = work_date
                st.toast("Entry updated successfully! ✨")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error updating entry: {e}")

        if delete_button:
            try:
                with conn.session as s:
                    s.execute(text("DELETE FROM work WHERE id = :work_id"), {"work_id": work_entry_row['id']})
                    s.commit()
                log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "DELETE_ENTRY", f"Deleted work entry ID: {work_entry_row['id']}")
                # Clean up session state
                if f"prev_entry_type_{work_entry_row['id']}" in st.session_state:
                    del st.session_state[f"prev_entry_type_{work_entry_row['id']}"]
                st.toast("Entry deleted successfully.", icon="🗑️")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting entry: {e}")

@st.dialog("➕ Add New Entry", width="small")
def add_work_dialog(conn, timesheet_id, start_date, end_date):
    """Dialog for adding a new entry, including downtime reasons with system failure, with support for previous week's unsubmitted timesheet."""
    entry_options = ("Work", "Holiday", "Leave", "Half Day", "No Internet", "Power Cut", "System Failure", "Other")
    entry_type = st.selectbox("Entry Type", entry_options, key="entry_type_modal")

    today = get_ist_date()
    
    # Check if the previous week's timesheet is unsubmitted (draft or rejected) for the user
    prev_fiscal_week, prev_start_date, prev_end_date = get_previous_week_details()
    allow_prev_week = False
    try:
        query = """
            SELECT status
            FROM timesheets
            WHERE user_id = :user_id AND fiscal_week = :fiscal_week
        """
        result = conn.query(query, params={"user_id": st.session_state.user_id, "fiscal_week": prev_fiscal_week}, ttl=0)
        if not result.empty and result['status'].iloc[0] in ('draft', 'rejected'):
            allow_prev_week = True
    except Exception as e:
        st.error(f"Error checking previous timesheet status: {e}")

    # Set date range based on whether previous week's timesheet is unsubmitted
    if allow_prev_week and today.weekday() in [0, 1]:  # Monday or Tuesday
        min_date = prev_start_date
        max_date = end_date  # Allow up to current week's end date
    else:
        min_date = start_date
        max_date = end_date

    # Clamp default_date to be within min_date and max_date
    default_date = st.session_state.get('last_selected_date', today)
    if default_date < min_date:
        default_date = min_date
    elif default_date > max_date:
        default_date = max_date

    with st.form("new_entry_form"):
        work_date = st.date_input("Date", value=default_date, min_value=min_date, max_value=max_date)

        current_week_work_titles = get_recent_work_titles(
            conn, st.session_state.user_id
        )

        # Initialize variables
        work_name = None
        work_description = None
        work_duration = 0.0
        reason = None

        if entry_type == "Work":
            work_name = st.selectbox(
                "Work Title",
                options=current_week_work_titles,
                index=None,
                format_func=lambda x: x,
                placeholder="Select existing work or type new...",
                help="Select from your recent work titles or type a new one",
                accept_new_options=True
            )
            work_description = st.text_area("Description", placeholder="e.g., Implemented frontend and backend...")
            col1, col2 = st.columns(2)
            with col1:
                hours = st.number_input("Hours", min_value=0, max_value=8, value=1, step=1)
            with col2:
                minutes = st.number_input("Minutes", min_value=0, max_value=59, value=0, step=5)
            work_duration = hours + minutes / 60.0
            reason = None
        elif entry_type == "Holiday":
            reason = st.text_input("Holiday Name", placeholder="e.g., Independence Day")
            work_duration = 0.0
            work_name = entry_type
        elif entry_type == "Leave":
            reason = st.text_area("Reason for Leave", placeholder="e.g., Personal reason")
            work_duration = 0.0
            work_name = entry_type
        elif entry_type == "Half Day":
            reason = st.text_area("Reason for Half Day", placeholder="e.g., Doctor's appointment")
            work_duration = 0.0
            work_name = entry_type
        elif entry_type in ("No Internet", "Power Cut", "System Failure"):
            work_name = entry_type
            if entry_type == "System Failure":
                reason = st.text_area("System Problem", placeholder="e.g., Blue screen error or software crash")
            else:
                reason = entry_type
            col1, col2 = st.columns(2)
            with col1:
                hours = st.number_input("Downtime Hours", min_value=0, max_value=8, value=1, step=1)
            with col2:
                minutes = st.number_input("Downtime Minutes", min_value=0, max_value=59, value=0, step=1)
            work_duration = hours + minutes / 60.0
        elif entry_type == "Other":
            work_name = entry_type
            reason = st.text_area("Reason", placeholder="Please specify the reason for the downtime.")
            col1, col2 = st.columns(2)
            with col1:
                hours = st.number_input("Downtime Hours", min_value=0, max_value=8, value=1, step=1)
            with col2:
                minutes = st.number_input("Downtime Minutes", min_value=0, max_value=59, value=0, step=1)
            work_duration = hours + minutes / 60.0

        if st.form_submit_button("Add Entry", type="primary"):
            # Determine the correct timesheet_id based on the selected date
            selected_timesheet_id = timesheet_id
            if allow_prev_week and work_date <= prev_end_date:
                try:
                    query = """
                        SELECT id
                        FROM timesheets
                        WHERE user_id = :user_id AND fiscal_week = :fiscal_week
                    """
                    result = conn.query(query, params={"user_id": st.session_state.user_id, "fiscal_week": prev_fiscal_week}, ttl=0)
                    if not result.empty:
                        selected_timesheet_id = result['id'].iloc[0]
                except Exception as e:
                    st.error(f"Error fetching previous timesheet ID: {e}")
                    return

            # Validation Logic
            is_valid = False
            if entry_type == "Work":
                is_valid = work_name and work_name.strip()
            elif entry_type in ("Holiday", "Leave", "Half Day", "System Failure", "Other"):
                is_valid = reason and reason.strip()
            elif entry_type in ("No Internet", "Power Cut"):
                is_valid = True

            if not is_valid:
                st.warning("A title or reason is required.")
                return

            try:
                with conn.session as s:
                    s.execute(text("""
                        INSERT INTO work (timesheet_id, work_date, work_name, work_description, work_duration, entry_type, reason)
                        VALUES (:ts_id, :w_date, :w_name, :w_desc, :w_dur, :e_type, :reason)
                    """), {
                        "ts_id": selected_timesheet_id, "w_date": work_date, "w_name": work_name.strip(),
                        "w_desc": work_description.strip() if work_description else None, "w_dur": work_duration,
                        "e_type": entry_type.lower().replace(" ", "_"), "reason": reason.strip() if reason else None
                    })
                    s.commit()
                log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, f"ADD_ENTRY", f"Added {entry_type} entry for {work_duration} hours")
                st.session_state.last_selected_date = work_date
                st.toast(f"Entry added to your timesheet! 🎉")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error adding entry: {e}")


@st.dialog("Daily Checklist Details", width="large")
def show_daily_checklist_dialog(conn, user_id, username, selected_date, is_manager=False, is_admin=False):
    """Dialog for viewing daily checklist details with timestamps and approval actions."""
    st.subheader(f"✅ Daily Checklist: {username}", anchor=False)
    st.caption(f"Date: {selected_date.strftime('%B %d, %Y')}")

    submission_df = get_today_submission(conn, user_id, selected_date)
    if submission_df.empty:
        st.info("No checklist data for this day.")
        return

    sub_row = submission_df.iloc[0]
    sub_id = sub_row['id']
    status = sub_row['status']
    start_time = sub_row['start_time']
    end_time = sub_row['end_time']
    
    # Robustly identify if current user is an admin to grant oversight
    is_admin = is_admin or st.session_state.get("role") == "admin"
    
    # Header Metrics (Compact)
    c1, c2, c3, c4 = st.columns(4)
    status_map_color = {"approved": "🟢", "submitted": "🟠", "rejected": "🔴", "pending": "🔵", "started": "▶️"}
    
    with c1:
        render_compact_metric("Status", f"{status_map_color.get(status, '⚪')} {status.upper()}")
    
    with c2:
        start_val = pd.to_datetime(start_time).strftime("%I:%M %p") if start_time else "—"
        render_compact_metric("Started At", start_val)
        
    with c3:
        sub_val = pd.to_datetime(sub_row['submitted_at']).strftime("%I:%M %p") if sub_row['submitted_at'] else "—"
        render_compact_metric("Submitted At", sub_val)
    
    with c4:
        total_time_str = "—"
        if start_time and end_time:
            duration = end_time - start_time
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            total_time_str = f"{int(hours)}h {int(minutes)}m"
        render_compact_metric("Total Duration", total_time_str)

    st.markdown("---")
    
    # Detailed Logs with Hierarchy
    logs_df = get_checklist_logs(conn, sub_id)
    resp_df = conn.query("SELECT id, task_name, description, manager_id FROM daily_responsibilities WHERE user_id = :user_id", params={"user_id": user_id}, ttl=0)
    merged_df = logs_df.merge(resp_df, left_on='responsibility_id', right_on='id', suffixes=('', '_master'))
    
    # --- Progress bar for Manager ---
    total_tasks = merged_df['responsibility_id'].nunique()
    latest_per_task = merged_df.groupby('responsibility_id').last()
    done_count = int(latest_per_task['status'].isin(['approved', 'submitted']).sum())
    st.progress(done_count / max(total_tasks, 1), text=f"{done_count} of {total_tasks} tasks submitted or approved")
    
    st.write("**Tasks Breakdown:**")
    
    # Sort for hierarchy
    merged_df = merged_df.sort_values(['responsibility_id', 'id'])

    status_icons = {"pending": "🕒", "started": "▶️", "completed": "⏹️", "submitted": "📤", "approved": "✅", "rejected": "❌"}
    status_colors = {
        "pending": ("#f0f2f6", "#31333f"),
        "started": ("#fff4e5", "#b35900"),
        "completed": ("#e6ffed", "#22863a"),
        "submitted": ("#f5f0ff", "#6f42c1"),
        "approved": ("#e6ffed", "#22863a"),
        "rejected": ("#ffeef0", "#d73a49")
    }

    for resp_id, group in merged_df.groupby('responsibility_id'):
        group = group.reset_index(drop=True)
        latest = group.iloc[-1]
        
        # Robust manager identification for visibility filtering and actions
        if pd.notna(latest['manager_id']):
            task_manager_id_raw = latest['manager_id']
        elif pd.notna(latest.get('manager_id_master')):
            task_manager_id_raw = latest['manager_id_master']
        else:
            task_manager_id_raw = sub_row['manager_id']
        
        is_this_task_manager = False
        if pd.notna(task_manager_id_raw):
            try:
                is_this_task_manager = int(st.session_state.user_id) == int(task_manager_id_raw)
            except (ValueError, TypeError):
                is_this_task_manager = False
        
        # Visibility filtering: In manager context, only show assigned tasks.
        if is_manager and not is_admin and not is_this_task_manager:
            continue

        with st.container(border=True):
            st.markdown(f"#### 📋 {group.iloc[0]['task_name']}")
            
            # Show description if available
            if pd.notna(group.iloc[0].get('description')) and group.iloc[0]['description']:
                st.markdown(f"""
                    <div style='color: #64748b; font-size: 0.8rem; margin-top: -12px; margin-bottom: 12px; margin-left: 28px; font-style: italic; line-height: 1.4;'>
                        {group.iloc[0]['description']}
                    </div>
                """, unsafe_allow_html=True)
            
            for i, (idx, row) in enumerate(group.iterrows()):
                status = row['status']
                is_latest = (i == len(group) - 1)
                
                # Visual distinction for previous attempts
                bg_style = "background-color: #f8f9fa;" if not is_latest else ""
                border_style = f"border-left: 5px solid {status_colors.get(status, ('#ccc', '#ccc'))[1]};"
                st.markdown(f'<div style="{bg_style} {border_style} padding: 15px; border-radius: 8px; margin-bottom: 10px;">', unsafe_allow_html=True)
                
                # Title row within the card
                c_title, c_badge = st.columns([0.7, 0.3])
                if not is_latest:
                    c_title.markdown(f"**Attempt #{i+1}**")
                
                bg, fg = status_colors.get(status, ("#f0f2f6", "#31333f"))
                badge_html = f"""
                    <div style='background-color: {bg}; color: {fg}; padding: 3px 10px; 
                    border-radius: 12px; font-size: 0.75rem; font-weight: 700; 
                    display: inline-block; text-transform: uppercase;'>
                        {status_icons.get(status, '')} {status}
                    </div>
                """
                c_badge.markdown(f"<div style='text-align:right'>{badge_html}</div>", unsafe_allow_html=True)

                # Metadata row
                m1, m2, m3, m4, m5 = st.columns(5)
                
                def render_meta_dlg(col, label, val):
                    col.markdown(f"""
                        <div style='line-height: 1.2;'>
                            <p style='color: #808495; font-size: 0.65rem; font-weight: 600; text-transform: uppercase; margin-bottom: 2px;'>{label}</p>
                            <p style='font-size: 0.85rem; font-weight: 500; margin-bottom: 0;'>{val}</p>
                        </div>
                    """, unsafe_allow_html=True)

                render_meta_dlg(m1, "Reporting To", row.get('manager_name') if pd.notna(row.get('manager_name')) else "Default")
                render_meta_dlg(m2, "Start", pd.to_datetime(row['start_time']).strftime('%I:%M %p') if pd.notna(row['start_time']) else "—")
                render_meta_dlg(m3, "End", pd.to_datetime(row['end_time']).strftime('%I:%M %p') if pd.notna(row['end_time']) else "—")
                render_meta_dlg(m4, "Submitted", pd.to_datetime(row['submitted_at']).strftime('%I:%M %p') if pd.notna(row['submitted_at']) else "—")
                
                dur_val = "—"
                if pd.notna(row['end_time']) and pd.notna(row['start_time']):
                    dur = pd.to_datetime(row['end_time']) - pd.to_datetime(row['start_time'])
                    dur_val = f"{int(dur.total_seconds()//60)}m"
                render_meta_dlg(m5, "Duration", dur_val)

                # If is_manager is True, it means we are in a context where oversight is already granted (like Dashboard)
                if (is_this_task_manager or is_admin) and row['status'] == 'submitted' and is_latest:
                    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                    c_app, c_rej = st.columns(2)
                    if c_app.button("Approve", key=f"app_t_dlg_{row['id']}", type="primary", use_container_width=True):
                        try:
                            now = get_ist_time()
                            with conn.session as s:
                                s.execute(text("UPDATE daily_checklist_logs SET status = 'approved', reviewed_at = :now WHERE id = :id"),
                                          {"now": now, "id": row['id']})
                                s.commit()
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
                    
                    with c_rej.popover("Reject", use_container_width=True):
                        notes = st.text_area("Reason for Rejection", key=f"rej_notes_dlg_{row['id']}")
                        if st.button("Confirm Reject", key=f"rej_conf_dlg_{row['id']}", type="secondary", use_container_width=True):
                            if not notes.strip(): st.warning("Reason is required.")
                            else:
                                try:
                                    now = get_ist_time()
                                    with conn.session as s:
                                        s.execute(text("UPDATE daily_checklist_logs SET status = 'rejected', reviewed_at = :now, review_notes = :notes WHERE id = :id"),
                                                  {"now": now, "notes": notes.strip(), "id": row['id']})
                                        s.commit()
                                    st.rerun()
                                except Exception as e: st.error(f"Error: {e}")
                
                # Notes and Feedback
                if pd.notna(row.get('resubmission_notes')) and row.get('resubmission_notes'):
                    st.markdown(f"<div style='margin-top: 10px; font-size: 0.85rem;'>📝 <b>Correction:</b> {row['resubmission_notes']}</div>", unsafe_allow_html=True)
                if pd.notna(row['review_notes']) and row['review_notes']:
                    st.markdown(f"<div style='margin-top: 5px; font-size: 0.85rem; color: #d73a49;'>💬 <b>Manager Feedback:</b> {row['review_notes']}</div>", unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)

@st.dialog("Confirm Submission")
def confirm_submission_dialog(conn, timesheet_id, current_status):
    """Dialog to confirm timesheet submission."""
    manager_name = get_manager_name(conn, st.session_state.report_to)
    if current_status == 'rejected':
        st.info("You are resubmitting a previously rejected timesheet.")
    st.warning(f"Submit this timesheet to **{manager_name}** for approval? This action cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Yes, Submit", width='stretch', type="primary"):
        submit_timesheet_for_approval(conn, timesheet_id, current_status)
        st.rerun()
    if c2.button("Cancel", width='stretch'):
        st.rerun()


@st.dialog("Weekly Timesheet Details", width="large")
def show_weekly_dialog(conn, user_id, username, week_start_date, is_manager=False, is_admin = False):
    """Dialog for viewing weekly timesheet details with a dynamic horizontal layout, including System Failure."""
    week_end_date = week_start_date + timedelta(days=6)
    # Calculate week number
    week_number = week_start_date.isocalendar().week
    col1, col2 = st.columns([2,7], vertical_alignment="bottom")
    with col1:
        st.subheader(f"Week #{week_number} Summary for {username}", anchor=False)
    with col2:
        st.caption(f"{week_start_date.strftime('%b %d')} - {week_end_date.strftime('%b %d, %Y')}")

    df = get_weekly_timesheet_details(conn, user_id, week_start_date)

    if df.empty:
        st.info("No entries for this week.")
        return

    # --- Data Extraction and Calculation ---
    timesheet_id, status, review_notes, submitted_at, reviewed_at, manager_name = (
        df[col].iloc[0] for col in ['timesheet_id', 'status', 'review_notes', 'submitted_at', 'reviewed_at', 'manager_name']
    )
    manager_name = manager_name if pd.notna(manager_name) else "N/A"
    
    status_map = {"approved": "🟢 APPROVED", "submitted": "🟠 SUBMITTED", "rejected": "🔴 REJECTED", "draft": "🔵 DRAFT"}
    status_icon = status_map.get(status, "⚪️ Unknown")

    total_logged = df['work_duration'].sum()
    total_working = df[df['entry_type'] == 'work']['work_duration'].sum()
    leave_count = df[df['entry_type'] == 'leave']['work_date'].nunique()
    half_day_count = df[df['entry_type'] == 'half_day']['work_date'].nunique()
    
    # **MODIFIED**: Include 'system_failure' in downtime types
    downtime_types = ['power_cut', 'no_internet', 'system_failure', 'other']
    total_downtime = df[df['entry_type'].isin(downtime_types)]['work_duration'].sum()

    # --- UI Logic ---
    with st.container(border=True):
        display_items = []
        
        display_items.append({'type': 'status', 'label': 'Status', 'value': status_icon})
        
        if status in ['submitted', 'approved', 'rejected'] and pd.notna(submitted_at):
            display_items.append({'type': 'detail', 'label': 'Submitted To', 'person': manager_name, 'ts': submitted_at})
            
        if status in ['approved', 'rejected'] and pd.notna(reviewed_at):
            display_items.append({'type': 'detail', 'label': 'Reviewed By', 'person': manager_name, 'ts': reviewed_at})
        
        # **UNCHANGED**: Metrics including downtime
        display_items.extend([
            {'type': 'metric', 'label': 'Logged', 'value': f"{total_logged:.2f} hrs", 'help': 'Total hours for all entry types.'},
            {'type': 'metric', 'label': 'Working', 'value': f"{total_working:.2f} hrs", 'help': 'Total hours logged as "work".'},
            {'type': 'metric', 'label': 'Downtime', 'value': f"{total_downtime:.2f} hrs", 'help': 'Total hours for power cuts, no internet, system failures, or other issues.'},
            {'type': 'metric', 'label': 'Leaves', 'value': f"{leave_count}", 'help': 'Total number of full-day leaves.'},
            {'type': 'metric', 'label': 'Half Days', 'value': f"{half_day_count}", 'help': 'Total number of half-days taken.'}
        ])
        
        cols = st.columns(len(display_items), vertical_alignment='center')
        
        # --- Rendering Loop (Unchanged) ---
        for i, item in enumerate(display_items):
            with cols[i]:
                if item['type'] == 'status':
                    render_status_metric(item['value']) 
                elif item['type'] == 'detail':
                    render_status_detail(item['label'], item['person'], item['ts'])
                elif item['type'] == 'metric':
                    render_compact_metric(item['label'], item['value'], item['help'])
        
        st.markdown("")  # Small spacer
    
    st.markdown("")

    # Render the detailed grid of daily entries
    #render_weekly_work_grid(conn, df, week_start_date, is_editable=False)
    render_grouped_timesheet(conn, df, week_start_date, is_editable=False)

    st.markdown("")

    if review_notes:
        st.warning(f"**Manager's Feedback:** {review_notes}", icon="⚠️")

    # --- Manager Approval/Rejection Logic ---
    if (is_manager or is_admin) and status == 'submitted':
        
        st.markdown("")
        with st.form(f"timesheet_action_form_{timesheet_id}", border=False):
            action_col1, action_col2 = st.columns(2)
            
            with action_col1:
                if st.form_submit_button("Approve", width='stretch', type="primary"):
                    try:
                        with conn.session as s:
                            # Update with IST timestamp
                            ist_time = get_ist_time()
                            s.execute(
                                text("""
                                    UPDATE timesheets 
                                    SET status = 'approved', 
                                        reviewed_at = :ist_time,
                                        review_notes = NULL
                                    WHERE id = :id
                                """),
                                {"id": timesheet_id, "ist_time": ist_time}
                            )
                            s.commit()
                            
                            # Log with IST time
                            log_activity(
                                conn, 
                                st.session_state.user_id, 
                                st.session_state.username, 
                                st.session_state.session_id, 
                                "APPROVE_TIMESHEET", 
                                f"Approved timesheet ID: {timesheet_id} for user {username} at {ist_time.strftime('%Y-%m-%d %H:%M:%S IST')}"
                            )
                            
                        st.success(f"Timesheet for {username} approved successfully.")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error approving timesheet: {e}")

            with action_col2:
                with st.popover("Request Revision", width='stretch'):
                    notes = st.text_area(
                        "Reason for Revision", 
                        placeholder="e.g., Please provide more detail for Wednesday's System Failure entry.",
                        key=f"revision_notes_{timesheet_id}"
                    )
                    if st.form_submit_button("Request Revision", width='stretch', type="secondary"):
                        if not notes.strip():
                            st.warning("A reason for revision is required.")
                        else:
                            try:
                                with conn.session as s:
                                    # Update with IST timestamp
                                    ist_time = get_ist_time()
                                    s.execute(
                                        text("""
                                            UPDATE timesheets 
                                            SET status = 'rejected', 
                                                reviewed_at = :ist_time,
                                                review_notes = :notes
                                            WHERE id = :id
                                        """),
                                        {"id": timesheet_id, "notes": notes.strip(), "ist_time": ist_time}
                                    )
                                    s.commit()
                                    
                                    # Log with IST time
                                    log_activity(
                                        conn, 
                                        st.session_state.user_id, 
                                        st.session_state.username, 
                                        st.session_state.session_id, 
                                        "REQUEST_REVISION_TIMESHEET", 
                                        f"Requested revision for timesheet ID: {timesheet_id} for user {username} at {ist_time.strftime('%Y-%m-%d %H:%M:%S IST')} with notes: {notes.strip()}"
                                    )
                                    
                                st.success(f"Revision requested for {username}'s timesheet.")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error requesting revision: {e}")

###################################################################################################################################
##################################--------------- User Interface ----------------------------########################################
###################################################################################################################################


def render_grouped_timesheet(conn, work_df, start_of_week_date, is_editable=False):
    """
    Renders a unified timesheet in a grid format (Entry Name x Day of Week).
    Includes daily total work hours at the bottom.
    """
    if work_df.empty:
        st.info("No entries for this week. Click '➕ Add Entry' to get started.", icon="📝")
        return

    # --- 1. Define Week Details & Icon Mapping ---
    days_of_week_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    week_dates = [(start_of_week_date + timedelta(days=i)) for i in range(6)]
    icon_map = {
        'holiday': '🏖️', 'leave': '🌴', 'half_day': '🌗', 'no_internet': '🌐',
        'power_cut': '🔌', 'other': '❓', 'system_failure': '⚠️'
    }

    # --- 2. Create the Header Row ---
    header_cols = st.columns([2, 1, 1, 1, 1, 1, 1])
    header_cols[0].markdown("**Work**")
    for i, day_name in enumerate(days_of_week_names):
        # MODIFIED: Used a markdown header to make the day name slightly bigger and bolder
        header_cols[i+1].markdown(f"##### {day_name}")
        header_cols[i+1].caption(f"{week_dates[i].strftime('%d %b')}")

    st.markdown("<hr style='margin-top:0; margin-bottom:1rem;'>", unsafe_allow_html=True)

    # --- 3. Process and Display ALL Entries in a Unified Grid ---
    unique_entry_names = work_df['work_name'].unique()

    for entry_name in unique_entry_names:
        data_cols = st.columns([1.5, 1, 1, 1, 1, 1, 1])
        data_cols[0].markdown(f"**{entry_name}**")

        for i, day_date in enumerate(week_dates):
            day_entries = work_df[
                (work_df['work_name'] == entry_name) &
                (work_df['work_date'] == day_date)
            ]

            with data_cols[i+1]:
                if not day_entries.empty:
                    entry_type = day_entries.iloc[0]['entry_type']

                    if entry_type == 'work':
                        total_hours = day_entries['work_duration'].sum()
                        with st.popover(f"`{total_hours:.1f} hrs`", width = "stretch"):
                            st.markdown(f"**{entry_name}** on **{day_date.strftime('%a, %b %d')}**")
                            # (Popover content for work entries remains the same)
                            for _, entry_row in day_entries.iterrows():
                                with st.container(border=True):
                                    c1, c2 = st.columns([0.8, 0.2])
                                    c1.caption(f"{entry_row.get('work_description', '_No description_')}")
                                    c1.markdown(f"**`{float(entry_row['work_duration']):.2f} hrs`**")
                                    if is_editable:
                                        c2.button("⚙️", key=f"manage_{entry_row['id']}", on_click=manage_work_entry, args=(conn, entry_row, start_of_week_date, start_of_week_date + timedelta(days=5)), help="Manage this entry", type="tertiary")
                    else:
                        entry_row = day_entries.iloc[0]
                        icon = icon_map.get(entry_type, '❓')
                        duration = entry_row['work_duration']
                        
                        # MODIFIED: Create a dynamic popover label that includes hours if they exist
                        popover_label = f"{icon}"
                        if duration > 0:
                            popover_label += f" `{duration:.1f} hrs`"

                        with st.popover(popover_label, width='stretch'):
                            # (Popover content for other entries remains the same)
                            st.markdown(f"{icon} **{entry_row['work_name']}** on **{day_date.strftime('%a, %b %d')}**")
                            with st.container(border=True):
                                c1, c2 = st.columns([0.8, 0.2])
                                if entry_row.get('reason'):
                                    c1.caption(f"_{entry_row['reason']}_")
                                if duration > 0:
                                    c1.markdown(f"**`{float(duration):.2f} hrs`**")
                                else:
                                    c1.markdown(f"**{entry_row['work_name']}**")
                                if is_editable:
                                    c2.button("⚙️", key=f"manage_{entry_row['id']}", on_click=manage_work_entry, args=(conn, entry_row, start_of_week_date, start_of_week_date + timedelta(days=5)), help="Manage this entry", type="tertiary")
                else:
                    st.markdown("<p style='text-align: center;'>—</p>", unsafe_allow_html=True)
    
    st.markdown("<hr style='margin-top:1rem; margin-bottom:1rem;'>", unsafe_allow_html=True)

    # --- NEW: 4. Display Daily Total Work Hours at the Bottom with Conditional Formatting ---
    total_cols = st.columns([1.5, 1, 1, 1, 1, 1, 1])
    total_cols[0].markdown("**Total (Work)**")

    # Filter for work entries only to calculate totals
    work_entries_df = work_df[work_df['entry_type'] == 'work']
    
    TARGET_HOURS = 8.0  # Define target hours threshold
    
    for i, day_date in enumerate(week_dates):
        day_total_hours = work_entries_df[work_entries_df['work_date'] == day_date]['work_duration'].sum()
        
        # Determine color based on hours
        if day_total_hours >= TARGET_HOURS:
            color = "#28a745"  # Green for at or above target
        elif day_total_hours >= TARGET_HOURS * 0.75:  # 6+ hours
            color = "#fd7e14"  # Orange for slightly below target
        else:
            color = "#dc3545"  # Red for significantly below target
        
        with total_cols[i+1]:
            st.markdown(
                f"<div style='text-align: center;'>"
                f"<span style='background-color: #f7f7f7; padding: 3px 6px; "
                f"border-radius: 4px; font-weight: 600; color: {color}; font-size: 0.8em;'>"
                f"{day_total_hours:.1f} hrs</span></div>",
                unsafe_allow_html=True
            )

#with st.badge

# def render_grouped_timesheet(conn, work_df, start_of_week_date, is_editable=False):
#     """
#     Renders a unified timesheet in a grid format (Entry Name x Day of Week).
#     Includes daily total work hours at the bottom.
#     """
#     if work_df.empty:
#         st.info("No entries for this week. Click '➕ Add Entry' to get started.", icon="📝")
#         return

#     # --- 1. Define Week Details & Icon Mapping ---
#     days_of_week_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
#     week_dates = [(start_of_week_date + timedelta(days=i)) for i in range(6)]
#     icon_map = {
#         'holiday': '🏖️', 'leave': '🌴', 'half_day': '🌗', 'no_internet': '🌐',
#         'power_cut': '🔌', 'other': '❓', 'system_failure': '⚠️'
#     }

#     # --- 2. Create the Header Row ---
#     header_cols = st.columns([2, 1, 1, 1, 1, 1, 1])
#     header_cols[0].markdown("**Work**")
#     for i, day_name in enumerate(days_of_week_names):
#         header_cols[i+1].markdown(f"##### {day_name}")
#         header_cols[i+1].caption(f"{week_dates[i].strftime('%d %b')}")

#     st.markdown("<hr style='margin-top:0; margin-bottom:1rem;'>", unsafe_allow_html=True)

#     # --- 3. Process and Display ALL Entries in a Unified Grid ---
#     unique_entry_names = work_df['work_name'].unique()

#     # --- MODIFIED: Create a color map to assign a unique color to each work name ---
#     badge_colors = ["blue", "green", "orange", "red", "violet"]
#     color_map = {
#         name: badge_colors[i % len(badge_colors)]
#         for i, name in enumerate(unique_entry_names)
#     }

#     for entry_name in unique_entry_names:
#         data_cols = st.columns([1.5, 1, 1, 1, 1, 1, 1])

#         # --- MODIFIED: Use st.badge for a more distinct UI in the 'Work' column ---
#         assigned_color = color_map.get(entry_name, "gray") # Default to gray if not in map
#         with data_cols[0]:
#             st.badge(entry_name, color=assigned_color)

#         for i, day_date in enumerate(week_dates):
#             day_entries = work_df[
#                 (work_df['work_name'] == entry_name) &
#                 (work_df['work_date'] == day_date)
#             ]

#             with data_cols[i+1]:
#                 if not day_entries.empty:
#                     entry_type = day_entries.iloc[0]['entry_type']

#                     if entry_type == 'work':
#                         total_hours = day_entries['work_duration'].sum()
#                         with st.popover(f"`{total_hours:.1f} hrs`", width='stretch'):
#                             st.markdown(f"**{entry_name}** on **{day_date.strftime('%a, %b %d')}**")
#                             for _, entry_row in day_entries.iterrows():
#                                 with st.container(border=True):
#                                     c1, c2 = st.columns([0.8, 0.2])
#                                     c1.caption(f"{entry_row.get('work_description', '_No description_')}")
#                                     c1.markdown(f"**`{float(entry_row['work_duration']):.2f} hrs`**")
#                                     if is_editable:
#                                         c2.button("⚙️", key=f"manage_{entry_row['id']}", on_click=manage_work_entry, args=(conn, entry_row, start_of_week_date, start_of_week_date + timedelta(days=5)), help="Manage this entry", type="tertiary")
#                     else:
#                         entry_row = day_entries.iloc[0]
#                         icon = icon_map.get(entry_type, '❓')
#                         duration = entry_row['work_duration']

#                         popover_label = f"{icon}"
#                         if duration > 0:
#                             popover_label += f" `{duration:.1f} hrs`"

#                         with st.popover(popover_label, width='stretch'):
#                             st.markdown(f"{icon} **{entry_row['work_name']}** on **{day_date.strftime('%a, %b %d')}**")
#                             with st.container(border=True):
#                                 c1, c2 = st.columns([0.8, 0.2])
#                                 if entry_row.get('reason'):
#                                     c1.caption(f"_{entry_row['reason']}_")
#                                 if duration > 0:
#                                     c1.markdown(f"**`{float(duration):.2f} hrs`**")
#                                 else:
#                                     c1.markdown(f"**{entry_row['work_name']}**")
#                                 if is_editable:
#                                     c2.button("⚙️", key=f"manage_{entry_row['id']}", on_click=manage_work_entry, args=(conn, entry_row, start_of_week_date, start_of_week_date + timedelta(days=5)), help="Manage this entry", type="tertiary")
#                 else:
#                     st.markdown("<p style='text-align: center;'>—</p>", unsafe_allow_html=True)

#     st.markdown("<hr style='margin-top:1rem; margin-bottom:1rem;'>", unsafe_allow_html=True)

#     # --- 4. Display Daily Total Work Hours at the Bottom with Conditional Formatting ---
#     total_cols = st.columns([1.5, 1, 1, 1, 1, 1, 1])
#     total_cols[0].markdown("**Total (Work)**")

#     work_entries_df = work_df[work_df['entry_type'] == 'work']
#     TARGET_HOURS = 8.0

#     for i, day_date in enumerate(week_dates):
#         day_total_hours = work_entries_df[work_entries_df['work_date'] == day_date]['work_duration'].sum()

#         if day_total_hours >= TARGET_HOURS:
#             color = "#28a745"
#         elif day_total_hours >= TARGET_HOURS * 0.75:
#             color = "#fd7e14"
#         else:
#             color = "#dc3545"

#         with total_cols[i+1]:
#             st.markdown(
#                 f"<div style='text-align: center;'>"
#                 f"<span style='background-color: #f7f7f7; padding: 3px 6px; "
#                 f"border-radius: 4px; font-weight: 600; color: {color}; font-size: 0.8em;'>"
#                 f"{day_total_hours:.1f} hrs</span></div>",
#                 unsafe_allow_html=True
#             )

def inject_custom_css():
    st.markdown("""
        <style>
            .tree-item { padding: 10px 14px; font-size: 14px; border-left: 2px solid #1f77b4; margin-left: 20px; margin-bottom: 8px; display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
            .tree-item:hover { background-color: #f8f9fa; }
            .session-node { font-size: 14px; font-weight: 600; color: #495057; margin-left: 15px; margin-bottom: 8px; margin-top: 6px; padding: 6px 0; display: flex; align-items: center; gap: 8px; }
            .session-duration { font-size: 12px; color: #6c757d; font-weight: 400; font-style: italic; }
            .timestamp { color: #6c757d; font-size: 12px; font-weight: 500; white-space: nowrap; }
            .action { font-weight: 600; color: #1f77b4; white-space: nowrap; display: flex; align-items: center; gap: 5px; }
            .details { color: #333; font-size: 13px; word-break: break-word; background-color: #f8f9fa; padding: 5px 10px; border-radius: 4px; flex: 1; min-width: 200px; line-height: 1.5; }
            .day-card {
                padding: 10px;
                border-radius: 8px;
                border: 1px solid #ddd;
                height: 140px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                margin-bottom: 10px;
            }
            .day-card:hover {
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                border-color: #bbb;
            }
            .day-card-work { background-color: #D4EDDA; } /* Green */
            .day-card-leave { background-color: #FEE2E2; } /* Red */
            .day-card-half_day { background-color: #FFEDD5; } /* Orange */
            .day-card-holiday { background-color: #F3E8FF; } /* Purple */
            .day-card-power_cut { background-color: #D7CCC8; } /* Brown */
            .day-card-no_internet { background-color: #FEF9C3; } /* Yellow */
            .day-card-other { background-color: #DBEAFE; } /* Blue */
            .day-card-weekend { background-color: #F5F5F5; } /* Grey for Sunday */
            .day-card-empty { background-color: #FAFAFA; border-style: dashed; } /* Past empty */
            .day-card-future { background-color: #ECEFF1; } /* Light gray for future */
            .day-card-rejected { background-color: #FEE2E2; } /* Red */
            .day-card-started { background-color: #FFF4E5; } /* Orange-ish */
            .day-number { font-weight: bold; font-size: 1.2em; text-align: left; }
            .day-name { font-size: 0.9em; color: #666; }
            .day-summary { font-size: 0.85em; margin-top: 5px; line-height: 1.3; overflow-y: auto; max-height: 70px; }
            .header-card {
                padding-bottom: 0.75rem; /* 12px */
                font-weight: 600;
                font-size: 0.75rem; /* 12px */
                text-align: center;
                color: #313438; /* Slate 500 */
                margin-bottom: 1.3rem; /* 8px */
                text-transform: uppercase;
                letter-spacing: 0.05em;
                border-bottom: 2px solid #d0d2d6; /* Light border instead of hr */
                background-color: transparent;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 40px;
            }
            .status-indicator {
                font-size: 0.8em;
                text-align: center;
                margin-bottom: 5px;
            }
        </style>
    """, unsafe_allow_html=True)

def render_day_card(day, daily_data, is_current_month, is_weekend, is_future):
    if not is_current_month:
        st.markdown('<div class="day-card day-card-empty"></div>', unsafe_allow_html=True)
        return

    date_obj = day
    status = daily_data.get('status', 'empty')
    type_hours = daily_data.get('type_hours', {})
    holiday_name = daily_data.get('holiday_name')

    css_class = f"day-card-{status}" if status != 'empty' else "day-card-future" if is_future else "day-card-weekend" if is_weekend else "day-card-empty"

    day_name = calendar.day_abbr[date_obj.weekday()]

    summary_lines = []
    work_hours = type_hours.get('work', 0)
    non_work_types = {k: v for k, v in type_hours.items() if k != 'work'}

    for typ, hours in sorted(non_work_types.items()):
        if typ == 'holiday':
            name = holiday_name or 'Holiday'
            line = f"🏖️ {name}"
        else:
            display_name = {
                'leave': 'Leave',
                'half_day': 'Half Day',
                'power_cut': 'Power Cut',
                'no_internet': 'No Internet',
                'other': 'Other',
            }.get(typ, typ.replace('_', ' ').capitalize())
            emoji = {
                'leave': '🌴',
                'half_day': '🌗',
                'power_cut': '⚡',
                'no_internet': '📶',
                'system_failure': '⚠️',
                'other': '🔍',
            }.get(typ, '')
            line = f"{emoji} {hours:.1f}h {display_name}"
        summary_lines.append(line)

    if work_hours > 0:
        summary_lines.append(f"✅ {work_hours:.1f}h Work")

    if not summary_lines:
        if not is_weekend:
            summary_lines.append("📅 No Activity")

    summary_text = "<br>".join(summary_lines)

    card_html = f"""
    <div class="day-card {css_class}">
        <div>
            <div class="day-number">{date_obj.day}</div>
            <div class="day-name">{day_name}</div>
            <div class="day-summary">{summary_text}</div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def render_checklist_day_card(day, daily_data, is_current_month, is_weekend, is_future):
    if not is_current_month:
        st.markdown('<div class="day-card day-card-empty"></div>', unsafe_allow_html=True)
        return

    date_obj = day
    status = daily_data.get('status', 'empty')
    tasks = daily_data.get('tasks', [])

    # Map status to CSS classes (reuse or extend existing)
    status_class_map = {
        'approved': 'day-card-work', # Green
        'submitted': 'day-card-half_day', # Orange/Yellowish
        'rejected': 'day-card-rejected', # Red
        'started': 'day-card-started', # Blue
        'pending': 'day-card-empty'
    }
    
    css_class = status_class_map.get(status, "day-card-empty")
    if is_future: css_class = "day-card-future"
    elif is_weekend and status == 'empty': css_class = "day-card-weekend"

    day_name = calendar.day_abbr[date_obj.weekday()]

    summary_lines = []
    if tasks:
        # Show first 2 tasks and a count if more
        for t in tasks[:2]:
            icon = "✅" if t['log_status'] == 'approved' else "📤" if t['log_status'] == 'submitted' else "▶️" if t['log_status'] == 'started' else "🕒"
            summary_lines.append(f"{icon} {t['task_name'][:15]}...")
        if len(tasks) > 2:
            summary_lines.append(f"and {len(tasks)-2} more...")
    else:
        if not is_future and not is_weekend:
            summary_lines.append("📅 No Checklist")

    summary_text = "<br>".join(summary_lines)

    card_html = f"""
    <div class="day-card {css_class}">
        <div>
            <div class="day-number">{date_obj.day}</div>
            <div class="day-name">{day_name}</div>
            <div class="day-summary">{summary_text}</div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def render_work_entry(conn, work_row, is_editable, week_bounds):
    """Renders a single work entry with one 'Manage' button and new icons."""
    with st.container(border=True):
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            entry_type = work_row.get('entry_type', 'work')
            icon_map = {
                'holiday': '🏖️', 'leave': '🌴', 'half_day': '🌗',
                'no_internet': '🌐', 'power_cut': '🔌', 'other': '❓',
                'system_failure': '⚠️'
            }
            if entry_type in icon_map:
                st.markdown(f"{icon_map[entry_type]} **{work_row['work_name']}**")
                # Only show reason caption if it's meaningful (not redundant)
                if entry_type in ['holiday', 'leave', 'half_day', 'other'] and work_row.get('reason'):
                    st.caption(f"Reason: **{work_row['reason']}**")
            else:  # 'work' type
                st.markdown(f"**{work_row['work_name']}**")
                if work_row.get('work_description'):
                    st.caption(f"{work_row['work_description']}")
            st.markdown(f"**`{float(work_row['work_duration']):.2f} hrs`**")
        with col2:
            if is_editable:
                st.button(
                    "⚙️",
                    key=f"manage_{work_row['id']}",
                    on_click=manage_work_entry,
                    args=(conn, work_row, week_bounds['start'], week_bounds['end']),
                    width='stretch',
                    help="Manage this entry (Edit or Delete)",
                    type="tertiary"
                )


def render_weekly_work_grid(conn, work_df, start_of_week_date, is_editable=False):
    """Displays work entries in a 6-column grid (Mon-Sat)."""
    days_of_week = [(start_of_week_date + timedelta(days=i)) for i in range(6)]
    cols = st.columns(6)

    # Defines the date boundaries for the entire week
    week_bounds = {'start': start_of_week_date, 'end': start_of_week_date + timedelta(days=5)}

    for i, day_date in enumerate(days_of_week):
        with cols[i]:
            st.subheader(f"{day_date.strftime('%a')}", anchor=False)
            st.caption(f"{day_date.strftime('%d %b')}")
            day_work_df = work_df[work_df['work_date'] == day_date]

            if not day_work_df.empty:
                for _, row in day_work_df.iterrows():
                    # Passes the full week_bounds dictionary down to the rendering function
                    render_work_entry(conn, row, is_editable, week_bounds)

                day_working_hours = day_work_df[day_work_df['entry_type'] == 'work']['work_duration'].sum()
                if day_working_hours > 0:
                    st.markdown(f"**Total Work: `{float(day_working_hours):.2f} hrs`**")
            else:
                st.info("_No entries._", icon="💤")
                                

###################################################################################################################################
##################################--------------- Pages----------------------------########################################
###################################################################################################################################


def my_timesheet_page(conn):
    """Renders the main page for the user's timesheet."""
    st.subheader(f"📝 {st.session_state.username}'s Weekly Timesheet", anchor=False, divider="rainbow")

    # Determine which week to show: current or previous pending
    fiscal_week, start_of_week, end_of_week, is_late_submission = determine_timesheet_week_to_display(conn, st.session_state.user_id)

    timesheet_id, status, notes = get_or_create_timesheet(conn, st.session_state.user_id, fiscal_week)
    
    if timesheet_id is None:
        st.stop()  # Stop execution - user must resolve pending timesheets first

    st.session_state.timesheet_status = status
    
    # Rest of the UI code remains the same...
    c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
    with c1:
        date_range = f"{start_of_week.strftime('%b %d')} - {end_of_week.strftime('%d, %Y')}"
        status_map = {"approved": "🟢", "submitted": "🟠", "rejected": "🔴", "draft": "🔵"}
        st.markdown(f"<h5>Week {fiscal_week} <small>({date_range})</small> {status_map.get(status, '⚪️')} {status.upper()}</h5>", unsafe_allow_html=True)
    
    is_editable = status in ['draft', 'rejected']
    if c2.button("➕ Add Entry", width='stretch', disabled=not is_editable, help="Add a new work, holiday, or leave entry."):
        add_work_dialog(conn, timesheet_id, start_of_week, end_of_week)

    submit_button_text = "✔️ Resubmit" if status == 'rejected' else "✔️ Submit"
    if c3.button(submit_button_text, type="primary", width='stretch', disabled=not is_editable):
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
        st.info("Your timesheet has been returned. Please make the required changes and resubmit.", icon="ℹ️")
        st.warning(f"**Manager's Feedback:** {notes}", icon="⚠️")

    st.markdown("---")
    work_df = get_weekly_work(conn, timesheet_id)
    render_grouped_timesheet(conn, work_df, start_of_week, is_editable=is_editable)
    st.markdown("---")
    total_logged_hours = work_df['work_duration'].sum()
    working_hours = work_df[work_df['entry_type'] == 'work']['work_duration'].sum()
    col_met1, col_met2 = st.columns(2)
    col_met1.metric("**Total Logged Hours** (Work + Leave/Holiday)", f"{total_logged_hours:.2f} Hours")
    col_met2.metric("**Total Working Hours** (Actual Work)", f"{working_hours:.2f} Hours")

def timesheet_history_page(conn):
    st.subheader("📜 My Timesheet History", anchor=False, divider="rainbow")
    inject_custom_css()

    user_id = st.session_state.user_id
    username = st.session_state.get('username', 'You')  # Assuming username is in session_state; adjust if needed

    available_years, month_by_year = get_available_months_years(conn, user_id)
    
    if not available_years:
        st.info("No timesheet history available.")
        return

    current_date = datetime.now()
    default_year = current_date.year if current_date.year in available_years else max(available_years)
    st.session_state.setdefault('selected_year_hist', default_year)

    available_months_for_year = month_by_year.get(st.session_state['selected_year_hist'], [])
    if not available_months_for_year:
        st.session_state['selected_year_hist'] = max(available_years)
        available_months_for_year = month_by_year[max(available_years)]

    default_month = current_date.month if current_date.month in available_months_for_year else max(available_months_for_year)
    st.session_state.setdefault('selected_month_hist', default_month)

    c1, c2 = st.columns(2)
    with c1:
        st.selectbox(
            "Year",
            options=available_years,
            key="selected_year_hist",
            label_visibility="collapsed"
        )

    available_months_for_year = month_by_year.get(st.session_state['selected_year_hist'], [])

    with c2:
        st.selectbox(
            "Month",
            options=available_months_for_year,
            format_func=lambda month: calendar.month_name[month],
            key="selected_month_hist",
            label_visibility="collapsed"
        )

    selected_year = st.session_state['selected_year_hist']
    selected_month = st.session_state['selected_month_hist']

    monthly_summary = get_monthly_summary(conn, user_id, selected_year, selected_month)
    
    total_days = calendar.monthrange(selected_year, selected_month)[1]
    expected_working_days = 0
    for day in range(1, total_days + 1):
        date_obj = date(selected_year, selected_month, day)
        if date_obj.weekday() == 6:
            continue
        if date_obj in monthly_summary and monthly_summary[date_obj]['status'] == 'holiday':
            continue
        expected_working_days += 1
    expected_working_hours = expected_working_days * 8

    # Display enhanced monthly stats
    display_monthly_stats(
        monthly_summary, selected_year, selected_month,
        expected_working_days, expected_working_hours
    )

    with st.expander("Lifetime Statistics", expanded=False):
        display_lifetime_stats(conn, user_id)
    
    days_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    header_cols = st.columns([1,1,1,1,1,1,0.8])
    for i, header in enumerate(days_headers):
        with header_cols[i]:
            st.markdown(f'<div class="header-card">{header}</div>', unsafe_allow_html=True)
    with header_cols[6]:
        st.markdown(f'<div class="header-card">View</div>', unsafe_allow_html=True)

    cal = calendar.Calendar()
    status_map = {"approved": "🟢", "submitted": "🟠", "rejected": "🔴", "draft": "🔵"}
    status_display = {"approved": "Approved", "submitted": "Submitted", "rejected": "Rejected", "draft": "Draft"}
    now_date = datetime.now().date()
    for week in cal.monthdatescalendar(selected_year, selected_month):
        cols = st.columns([1,1,1,1,1,1,0.8])
        for i, day_date in enumerate(week[:-1]):
            with cols[i]:
                is_current_month = (day_date.month == selected_month)
                is_weekend = (day_date.weekday() == 6)  # Only Sunday is weekend
                is_future = day_date > datetime.now().date()
                daily_data = monthly_summary.get(day_date, {})
                render_day_card(day_date, daily_data, is_current_month, is_weekend, is_future)
        with cols[6]:
            if any(d.month == selected_month for d in week):
                week_start_date = week[0]
                # Get status from one day in the week
                week_days = [d for d in week[:-1] if d in monthly_summary]
                timesheet_status = None
                if week_days:
                    timesheet_status = monthly_summary[week_days[0]]['timesheet_status']
                
                is_future_week = week_start_date > now_date
                has_timesheet = bool(week_days and timesheet_status)
                disabled = is_future_week or not has_timesheet
                # Calculate week number
                week_number = week_start_date.isocalendar().week
                
                
                if disabled:
                    button_text = "No Data" if not has_timesheet else "Future"
                    st.button(button_text, key=f"week_btn_hist_{week_start_date}_disabled", width='stretch', disabled=True)
                    st.caption(f"Week {week_number}", unsafe_allow_html=True)
                else:
                    status_emoji = status_map.get(timesheet_status, '⚪️')
                    status_label = status_display.get(timesheet_status, "Unknown")
                    if st.button(f"{status_emoji} {status_label}", key=f"week_btn_hist_{week_start_date}", width='stretch'):
                        st.session_state.show_week_details_for = week_start_date
                        st.rerun()
                    st.caption(f"Week {week_number}", unsafe_allow_html=True)

    if "show_week_details_for" not in st.session_state:
        st.session_state.show_week_details_for = None
        
    if st.session_state.show_week_details_for:
        show_weekly_dialog(conn, user_id, username, st.session_state.show_week_details_for)
        st.session_state.show_week_details_for = None


@st.cache_data(ttl=60)
def get_all_pending_daily_submissions_for_manager(_conn, manager_id):
    """
    Retrieves all daily submissions for a manager that have at least one 'submitted' task,
    where the manager is responsible for that specific task based on a fallback hierarchy.
    """
    query = """
        SELECT DISTINCT s.*, u.username 
        FROM daily_checklist_submissions s
        JOIN userss u ON s.user_id = u.id
        JOIN daily_checklist_logs l ON s.id = l.submission_id
        LEFT JOIN daily_responsibilities dr ON l.responsibility_id = dr.id
        WHERE COALESCE(l.manager_id, dr.manager_id, s.manager_id) = :manager_id
        AND l.status = 'submitted'
        ORDER BY s.date DESC, u.username ASC
    """
    return _conn.query(query, params={"manager_id": manager_id}, ttl=0)

def get_daily_submissions_for_manager(conn, manager_id, date):
    # Only show users who have at least one task that is NOT pending or started,
    # and the manager is responsible for that specific task.
    query = """
        SELECT DISTINCT s.*, u.username 
        FROM daily_checklist_submissions s
        JOIN userss u ON s.user_id = u.id
        JOIN daily_checklist_logs l ON s.id = l.submission_id
        LEFT JOIN daily_responsibilities dr ON l.responsibility_id = dr.id
        WHERE COALESCE(l.manager_id, dr.manager_id, s.manager_id) = :manager_id
        AND s.date = :date
        AND l.status NOT IN ('pending', 'started')
    """
    return conn.query(query, params={"manager_id": manager_id, "date": date}, ttl=0)

def render_daily_checklist_inline(conn, sub_row, is_manager=False, is_admin=False, key_suffix=""):
    """Renders the daily checklist details directly in the page."""
    sub_id = sub_row['id']
    username = sub_row['username']
    user_id = sub_row['user_id']
    status = sub_row['status']
    start_time = sub_row['start_time']
    end_time = sub_row['end_time']
    
    # Robustly identify if current user is an admin to grant oversight
    is_admin = is_admin or st.session_state.get("role") == "admin"

    status_icons = {"pending": "🕒", "started": "▶️", "completed": "⏹️", "submitted": "📤", "approved": "✅", "rejected": "❌"}
    status_colors = {
        "pending": ("#f0f2f6", "#31333f"),
        "started": ("#fff4e5", "#b35900"),
        "completed": ("#e6ffed", "#22863a"),
        "submitted": ("#f5f0ff", "#6f42c1"),
        "approved": ("#e6ffed", "#22863a"),
        "rejected": ("#ffeef0", "#d73a49")
    }

    with st.container(border=True):
        st.markdown(f"### ✅ {username}'s Checklist")

        # Header Metrics (Compact)
        c1, c2, c3, c4 = st.columns(4)
        
        status_map_color = {"approved": "🟢", "submitted": "🟠", "rejected": "🔴", "pending": "🔵", "started": "▶️"}
        
        with c1:
            render_compact_metric("Overall Status", f"{status_map_color.get(status, '⚪')} {status.upper()}")
        
        with c2:
            start_val = pd.to_datetime(start_time).strftime("%I:%M %p") if pd.notna(start_time) and start_time else "—"
            render_compact_metric("Started At", start_val)
            
        with c3:
            sub_val = pd.to_datetime(sub_row['submitted_at']).strftime("%I:%M %p") if pd.notna(sub_row['submitted_at']) and sub_row['submitted_at'] else "—"
            render_compact_metric("Submitted At", sub_val)

        with c4:
            total_time_str = "—"
            if pd.notna(start_time) and pd.notna(end_time) and start_time and end_time:
                duration = pd.to_datetime(end_time) - pd.to_datetime(start_time)
                hours, remainder = divmod(duration.total_seconds(), 3600)
                minutes, _ = divmod(remainder, 60)
                total_time_str = f"{int(hours)}h {int(minutes)}m"
            render_compact_metric("Total Duration", total_time_str)

        st.markdown("---")

        # Detailed Logs
        logs_df = get_checklist_logs(conn, sub_id)
        resp_df = conn.query("SELECT id, task_name, description, manager_id FROM daily_responsibilities WHERE user_id = :user_id",
                                params={"user_id": user_id}, ttl=0)
        merged_df = (logs_df
                        .merge(resp_df, left_on='responsibility_id', right_on='id', suffixes=('', '_master'))
                        .sort_values(['responsibility_id', 'id']))

        # --- Progress bar for Manager ---
        total_tasks = merged_df['responsibility_id'].nunique()
        latest_per_task = merged_df.groupby('responsibility_id').last()
        done_count = int(latest_per_task['status'].isin(['approved', 'submitted']).sum())
        st.progress(done_count / max(total_tasks, 1), text=f"{done_count} of {total_tasks} tasks submitted or approved")

        for resp_id, group in merged_df.groupby('responsibility_id'):
            group = group.reset_index(drop=True)
            latest = group.iloc[-1]

            # Robust manager identification for visibility filtering and actions
            if pd.notna(latest['manager_id']):
                task_manager_id_raw = latest['manager_id']
            elif pd.notna(latest.get('manager_id_master')):
                task_manager_id_raw = latest['manager_id_master']
            else:
                task_manager_id_raw = sub_row['manager_id']
            
            is_this_task_manager = False
            if pd.notna(task_manager_id_raw):
                try:
                    is_this_task_manager = int(st.session_state.user_id) == int(task_manager_id_raw)
                except (ValueError, TypeError):
                    is_this_task_manager = False
            
            # Visibility filtering: In manager context, only show assigned tasks.
            # Admins see everything.
            if is_manager and not is_admin and not is_this_task_manager:
                continue

            latest_status = latest['status']

            # Identify if there was a previous rejection for this specific task (to show context to manager)
            prev_rejected_row = None
            if latest_status in ['pending', 'started', 'completed', 'submitted'] and len(group) > 1:
                for idx in range(len(group)-2, -1, -1):
                    if group.iloc[idx]['status'] == 'rejected':
                        prev_rejected_row = group.iloc[idx]
                        break

            with st.container(border=True):
                # Task name + latest status badge
                col_title, col_badge = st.columns([0.7, 0.3])
                col_title.markdown(f"#### 📋 {group.iloc[0]['task_name']}")
                
                # Show description if available
                if pd.notna(group.iloc[0].get('description')) and group.iloc[0]['description']:
                    st.markdown(f"""
                        <div style='color: #64748b; font-size: 0.8rem; margin-top: -10px; margin-bottom: 10px; margin-left: 28px; font-style: italic; line-height: 1.4;'>
                            {group.iloc[0]['description']}
                        </div>
                    """, unsafe_allow_html=True)
                
                bg, fg = status_colors.get(latest_status, ("#f0f2f6", "#31333f"))
                badge_html = f"""
                    <div style='background-color: {bg}; color: {fg}; padding: 4px 12px; 
                    border-radius: 16px; font-size: 0.8rem; font-weight: 700; 
                    display: inline-block; text-transform: uppercase; letter-spacing: 0.5px;'>
                        {status_icons.get(latest_status, '')} {latest_status}
                    </div>
                """
                col_badge.markdown(f"<div style='text-align:right'>{badge_html}</div>", unsafe_allow_html=True)

                # Metadata Columns
                m1, m2, m3, m4, m5 = st.columns(5)
                
                def render_meta_col_mgr(col, label, val):
                    col.markdown(f"""
                        <div style='line-height: 1.2;'>
                            <p style='color: #808495; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; margin-bottom: 2px;'>{label}</p>
                            <p style='font-size: 0.95rem; font-weight: 500; margin-bottom: 0;'>{val}</p>
                        </div>
                    """, unsafe_allow_html=True)

                start_val = pd.to_datetime(latest['start_time']).strftime('%I:%M %p') if pd.notna(latest['start_time']) else "—"
                end_val = pd.to_datetime(latest['end_time']).strftime('%I:%M %p') if pd.notna(latest['end_time']) else "—"
                sub_val = pd.to_datetime(latest['submitted_at']).strftime('%I:%M %p') if pd.notna(latest['submitted_at']) else "—"
                
                dur_val = "—"
                if pd.notna(latest['start_time']) and pd.notna(latest['end_time']):
                    dur = pd.to_datetime(latest['end_time']) - pd.to_datetime(latest['start_time'])
                    dur_val = f"{int(dur.total_seconds() // 60)}m"

                render_meta_col_mgr(m1, "Reporting To", latest.get('manager_name') if pd.notna(latest.get('manager_name')) else "Default")
                render_meta_col_mgr(m2, "Start", start_val)
                render_meta_col_mgr(m3, "End", end_val)
                render_meta_col_mgr(m4, "Submitted", sub_val)
                render_meta_col_mgr(m5, "Duration", dur_val)

                # Notes and Feedback for LATEST attempt
                if (pd.notna(latest.get('resubmission_notes')) and latest.get('resubmission_notes')) or \
                   (pd.notna(latest.get('review_notes')) and latest.get('review_notes')):
                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                
                # Contextual Info for Manager (show why it was rejected previously)
                if prev_rejected_row is not None and pd.notna(prev_rejected_row['review_notes']):
                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                    st.warning(f"**History Context:** Task was previously rejected because: {prev_rejected_row['review_notes']}", icon="⚠️")
                
                st.write("")
                # Previous attempts
                if len(group) > 1:
                    with st.expander(f"🕓 View Full History ({len(group)})", expanded=True):
                        for i, (_, hist_row) in enumerate(group.iloc[::-1].iterrows()):
                            h_idx = len(group) - i
                            h_bg, h_fg = status_colors.get(hist_row['status'], ("#f0f2f6", "#31333f"))
                            
                            c_bg = "#f8f9fa"
                            if hist_row['status'] == 'approved': c_bg = "#f0fff4"
                            elif hist_row['status'] == 'rejected': c_bg = "#fff5f5"

                            st.markdown(f"""
                                <div style='background-color: {c_bg}; padding: 10px; border-radius: 6px; border-left: 3px solid {h_fg}; margin-bottom: 8px;'>
                                    <div style='display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 4px;'>
                                        <b>Attempt #{h_idx}</b>
                                        <b style='color: {h_fg};'>{hist_row['status'].upper()}</b>
                                    </div>
                                    <div style='font-size: 0.8rem; color: #555;'>
                                        Start: {pd.to_datetime(hist_row['start_time']).strftime('%I:%M %p') if pd.notna(hist_row['start_time']) else '—'} | 
                                        End: {pd.to_datetime(hist_row['end_time']).strftime('%I:%M %p') if pd.notna(hist_row['end_time']) else '—'} |
                                        Sub: {pd.to_datetime(hist_row['submitted_at']).strftime('%I:%M %p') if pd.notna(hist_row['submitted_at']) else '—'}
                                        {f" | Reviewed: {pd.to_datetime(hist_row['reviewed_at']).strftime('%I:%M %p')}" if pd.notna(hist_row['reviewed_at']) else ""}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                                        
                            if pd.notna(hist_row.get('resubmission_notes')) and hist_row.get('resubmission_notes'):
                                st.markdown(f"<div style='margin: -5px 0 8px 12px; font-size: 0.8rem; color: #444;'>📝 <b>Correction:</b> {hist_row['resubmission_notes']}</div>", unsafe_allow_html=True)
                            if pd.notna(hist_row.get('review_notes')) and hist_row.get('review_notes'):
                                st.markdown(f"<div style='margin: -5px 0 8px 12px; font-size: 0.8rem; color: #d73a49;'>💬 <b>Feedback:</b> {hist_row['review_notes']}</div>", unsafe_allow_html=True)
                                    
                with st.container():
                    if (is_this_task_manager or is_admin) and latest['status'] == 'submitted':
                        c_app, c_rej = st.columns(2)
                        if c_app.button("✅ Approve", key=f"app_t_inline_{latest['id']}{key_suffix}", type="primary", use_container_width=True):
                            try:
                                now = get_ist_time()
                                with conn.session as s:
                                    s.execute(text("UPDATE daily_checklist_logs SET status = 'approved', reviewed_at = :now WHERE id = :id"),
                                                {"now": now, "id": latest['id']})
                                    
                                    # Log the activity for audit trail
                                    log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, 
                                                    "APPROVE_CHECKLIST_TASK", f"Approved task '{group.iloc[0]['task_name']}' for {username}")
                                    
                                    # Check if all tasks for this submission are now approved
                                    check_query = "SELECT status FROM daily_checklist_logs WHERE submission_id = :sid"
                                    all_statuses = s.execute(text(check_query), {"sid": sub_id}).fetchall()
                                    if all(row[0] == 'approved' for row in all_statuses):
                                        s.execute(text("UPDATE daily_checklist_submissions SET status = 'approved', reviewed_at = :now WHERE id = :sid"),
                                                    {"now": now, "sid": sub_id})
                                    
                                    s.commit()
                                st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
        
                        with c_rej.popover("❌ Reject", use_container_width=True):
                            notes = st.text_area("Reason for rejection", key=f"rej_notes_inline_{latest['id']}{key_suffix}")
                            if st.button("Confirm Reject", key=f"rej_conf_inline_{latest['id']}{key_suffix}", type="secondary", use_container_width=True):
                                if not notes.strip():
                                    st.warning("A reason is required.")
                                else:
                                    try:
                                        now = get_ist_time()
                                        with conn.session as s:
                                            s.execute(text("UPDATE daily_checklist_logs SET status = 'rejected', reviewed_at = :now, review_notes = :notes WHERE id = :id"),
                                                        {"now": now, "notes": notes.strip(), "id": latest['id']})
                                            
                                            # Log the activity for audit trail
                                            log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, 
                                                            "REJECT_CHECKLIST_TASK", f"Rejected task '{group.iloc[0]['task_name']}' for {username}. Reason: {notes.strip()}")
                                            
                                            s.execute(text("UPDATE daily_checklist_submissions SET status = 'rejected', reviewed_at = :now WHERE id = :sid"),
                                                        {"now": now, "sid": sub_id})
                                            s.commit()
                                        st.rerun()
                                    except Exception as e: st.error(f"Error: {e}")

def manager_dashboard(conn):
    st.subheader("📋 Manager Dashboard", anchor=False, divider="rainbow")
    
    # Alerts about late submissions (Weekly + Daily)
    late_submitters_weekly = get_late_submitters_for_manager(conn, st.session_state.user_id)
    late_submitters_daily = get_checklist_late_submitters_for_manager(conn, st.session_state.user_id)
    
    if late_submitters_weekly:
        st.warning(f"**Pending Weekly Timesheets:** {', '.join(late_submitters_weekly)} have not submitted their timesheet from last week.", icon="🔔")
    
    if late_submitters_daily:
        st.error(f"**Pending Daily Checklists:** {', '.join(late_submitters_daily)} have pending or missing checklists for previous working days.", icon="⚠️")
    
    inject_custom_css()
    users_df = get_direct_reports(conn, st.session_state.user_id)
    
    if users_df.empty:
        st.info("No direct reports found.")
        return

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        selected_user = st.selectbox(
            "Select Employee",
            options=users_df['username'],
            label_visibility="collapsed",
            key="mgr_user_select"
        )
    
    if not selected_user:
        st.info("Please select an employee to continue.")
        return

    user_info = users_df[users_df['username'] == selected_user].iloc[0]
    selected_user_id = user_info['id']
    
    tab_weekly, tab_pending, tab_history, tab_activity = st.tabs(["📅 Weekly Timesheets", "⏳ Pending Approvals", "📊 Checklist History", "🕵️ User Activity"])

    with tab_pending:
        # Section 1: All Pending Approvals (Across all dates)
        st.write("### ⏳ Pending Approvals (All Dates)")
        pending_subs = get_all_pending_daily_submissions_for_manager(conn, st.session_state.user_id)
        
        # Filter for selected user if any
        user_pending = pending_subs[pending_subs['username'] == selected_user] if not pending_subs.empty else pd.DataFrame()
        
        if user_pending.empty:
            st.success(f"✨ No pending approvals found for **{selected_user}**.")
        else:
            for _, row in user_pending.iterrows():
                st.write(f"📅 **Date: {row['date'].strftime('%B %d, %Y')}**")
                render_daily_checklist_inline(conn, row, is_manager=True, is_admin=(st.session_state.role == 'admin'))

    with tab_history:
        # Section 2: Checklist Calendar
        st.write("### 📅 Checklist Calendar")
        
        # Reuse existing year/month selection if possible, or create local ones
        c_daily_1, c_daily_2 = st.columns(2)
        with c_daily_1:
            # We can try to use st.session_state.selected_year_mgr or similar if they overlap
            y_options = [datetime.now().year, datetime.now().year - 1]
            sel_y = st.selectbox("Year", options=y_options, key="mgr_daily_cal_year")
        with c_daily_2:
            m_options = list(range(1, 13))
            sel_m = st.selectbox("Month", options=m_options, format_func=lambda x: calendar.month_name[x], index=datetime.now().month-1, key="mgr_daily_cal_month")

        daily_summary = get_daily_checklist_monthly_summary(conn, selected_user_id, sel_y, sel_m)
        
        # Calculate expected working days
        total_days_in_month = calendar.monthrange(sel_y, sel_m)[1]
        expected_working_days = sum(1 for d in range(1, total_days_in_month + 1) if date(sel_y, sel_m, d).weekday() != 6)
        
        # Display metrics
        display_checklist_monthly_stats(daily_summary, sel_y, sel_m, expected_working_days)
        
        st.write("---")

        # Render Calendar Grid
        days_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        header_cols = st.columns([1,1,1,1,1,1,0.8])
        for i, header in enumerate(days_headers):
            with header_cols[i]: st.markdown(f'<div class="header-card">{header}</div>', unsafe_allow_html=True)
        with header_cols[6]: st.markdown(f'<div class="header-card">Details</div>', unsafe_allow_html=True)

        status_map = {"approved": "🟢", "submitted": "🟠", "rejected": "🔴", "pending": "🔵", "started": "▶️"}
        status_display = {"approved": "Approved", "submitted": "Submitted", "rejected": "Rejected", "pending": "Pending", "started": "Started"}

        cal = calendar.Calendar()
        for week in cal.monthdatescalendar(sel_y, sel_m):
            cols = st.columns([1,1,1,1,1,1,0.8])
            for i, day_date in enumerate(week[:-1]):
                with cols[i]:
                    is_current_month = (day_date.month == sel_m)
                    is_weekend = (day_date.weekday() == 6)
                    is_future = day_date > datetime.now().date()
                    daily_data = daily_summary.get(day_date, {})
                    render_checklist_day_card(day_date, daily_data, is_current_month, is_weekend, is_future)

            with cols[6]:
                if any(d.month == sel_m for d in week):
                    week_dates = [d for d in week[:-1] if d.month == sel_m]
                    if week_dates:
                        # aggregated status for the week
                        week_status = get_week_checklist_status(week_dates, daily_summary)
                        has_data = week_status is not None
                        
                        if not has_data:
                            st.button("No Data", key=f"view_daily_week_{week[0]}_nodata", width='stretch', disabled=True)
                        else:
                            status_emoji = status_map.get(week_status, '⚪️')
                            status_label = status_display.get(week_status, "Summary")
                            if st.button(f"{status_emoji} {status_label}", key=f"view_daily_week_{week[0]}", width='stretch', help="Click to see summary for this whole week"):
                                show_weekly_checklist_summary_dialog(conn, selected_user_id, selected_user, week_dates, is_manager=True)
                    
                    st.caption(f"Week {week[0].isocalendar().week}", unsafe_allow_html=True)
        
        # REMOVED: Redundant inline week viewing logic to simplify the UI

    with tab_weekly:
        # Check for and display submitted timesheets as a temporary toast notification
        if 'submitted_timesheet_notified' not in st.session_state:
            st.session_state.submitted_timesheet_notified = False
        
        if not st.session_state.submitted_timesheet_notified:
            submitted_users = get_submitted_timesheet_users(conn, st.session_state.user_id)
            if submitted_users:
                st.toast(f"**Submitted Timesheets:** {', '.join(submitted_users)} have submitted their timesheet.", icon="✅", duration="infinite")
                st.session_state.submitted_timesheet_notified = True
        
        st.caption("Select a year and month to view their timesheets.")
        
        available_years, month_by_year = get_available_months_years(conn, selected_user_id)
        
        if not available_years:
            st.info("No timesheet data available for this user.")
        else:
            current_date = datetime.now()
            default_year = current_date.year if current_date.year in available_years else max(available_years)
            st.session_state.setdefault('selected_year_mgr', default_year)

            available_months_for_year = month_by_year.get(st.session_state['selected_year_mgr'], [])
            if not available_months_for_year:
                st.session_state['selected_year_mgr'] = max(available_years)
                available_months_for_year = month_by_year[max(available_years)]

            default_month = current_date.month if current_date.month in available_months_for_year else max(available_months_for_year)
            st.session_state.setdefault('selected_month_mgr', default_month)

            with c2:
                st.selectbox("Year", options=available_years, key="selected_year_mgr", label_visibility="collapsed")

            available_months_for_year = month_by_year.get(st.session_state['selected_year_mgr'], [])

            with c3:
                st.selectbox(
                    "Month",
                    options=available_months_for_year,
                    format_func=lambda month: calendar.month_name[month],
                    key="selected_month_mgr",
                    label_visibility="collapsed"
                )

            selected_year = st.session_state['selected_year_mgr']
            selected_month = st.session_state['selected_month_mgr']

            monthly_summary = get_monthly_summary(conn, selected_user_id, selected_year, selected_month, statuses=['submitted', 'approved', 'rejected'])
            
            total_days = calendar.monthrange(selected_year, selected_month)[1]
            expected_working_days = 0
            for day in range(1, total_days + 1):
                date_obj = date(selected_year, selected_month, day)
                if date_obj.weekday() == 6: continue
                if date_obj in monthly_summary and monthly_summary[date_obj]['status'] == 'holiday': continue
                expected_working_days += 1
            expected_working_hours = expected_working_days * 8

            display_monthly_stats(monthly_summary, selected_year, selected_month, expected_working_days, expected_working_hours)

            with st.expander("Lifetime Statistics", expanded=False):
                display_lifetime_stats(conn, selected_user_id)
            
            days_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            header_cols = st.columns([1,1,1,1,1,1,0.8])
            for i, header in enumerate(days_headers):
                with header_cols[i]: st.markdown(f'<div class="header-card">{header}</div>', unsafe_allow_html=True)
            with header_cols[6]: st.markdown(f'<div class="header-card">View</div>', unsafe_allow_html=True)

            cal = calendar.Calendar()
            status_map = {"approved": "🟢", "submitted": "🟠", "rejected": "🔴", "draft": "🔵"}
            status_display = {"approved": "Approved", "submitted": "Submitted", "rejected": "Rejected", "draft": "Draft"}
            now_date = datetime.now().date()
            for week in cal.monthdatescalendar(selected_year, selected_month):
                cols = st.columns([1,1,1,1,1,1,0.8])
                for i, day_date in enumerate(week[:-1]):
                    with cols[i]:
                        is_current_month = (day_date.month == selected_month)
                        is_weekend = (day_date.weekday() == 6)
                        is_future = day_date > datetime.now().date()
                        daily_data = monthly_summary.get(day_date, {})
                        render_day_card(day_date, daily_data, is_current_month, is_weekend, is_future)
                with cols[6]:
                    if any(d.month == selected_month for d in week):
                        week_start_date = week[0]
                        week_days = [d for d in week[:-1] if d in monthly_summary]
                        timesheet_status = monthly_summary[week_days[0]]['timesheet_status'] if week_days else None
                        is_future_week = week_start_date > now_date
                        has_timesheet = bool(week_days and timesheet_status)
                        disabled = is_future_week or not has_timesheet
                        week_number = week_start_date.isocalendar().week
                        
                        if disabled:
                            button_text = "No Data" if not has_timesheet else "Future"
                            st.button(button_text, key=f"week_btn_mgr_{week_start_date}_disabled", width='stretch', disabled=True)
                        else:
                            status_emoji = status_map.get(timesheet_status, '⚪️')
                            status_label = status_display.get(timesheet_status, "Unknown")
                            if st.button(f"{status_emoji} {status_label}", key=f"week_btn_mgr_{week_start_date}", width='stretch'):
                                st.session_state.show_week_details_for = week_start_date
                                st.rerun()
                        st.caption(f"Week {week_number}", unsafe_allow_html=True)

    with tab_activity:
        # Get allowed actions for this manager for the selected user
        allowed_actions = []
        is_admin_user = st.session_state.get("role") == 'admin'
        curr_user_id = st.session_state.get("user_id")
        
        if not is_admin_user:
            try:
                # Ensure IDs are integers for robust database matching
                uid_int = int(selected_user_id)
                mid_int = int(curr_user_id)
                
                resp_logs_df = conn.query("""
                    SELECT log_actions FROM daily_responsibilities 
                    WHERE user_id = :uid 
                    AND (manager_id = :mid OR manager_id IS NULL) 
                    AND is_active = 1
                """, params={"uid": uid_int, "mid": mid_int}, ttl=0)
                
                if not resp_logs_df.empty:
                    for actions in resp_logs_df['log_actions'].dropna():
                        # Extract and clean actions from the comma-separated string
                        allowed_actions.extend([a.strip() for a in actions.split(',') if a.strip()])
                
                allowed_actions = list(set(allowed_actions)) # Deduplicate
            except Exception as e:
                st.error(f"Error fetching allowed actions: {e}")

        selected_date_act = st.date_input("Select Date", value=get_ist_date(), key="mgr_act_date")
        
        if is_admin_user:
            df_logs = get_activity_log_for_user(conn, selected_date_act, selected_user)
        elif not allowed_actions:
            st.info(f"No specific activity logs assigned to you for {selected_user}.")
            df_logs = pd.DataFrame()
        else:
            df_logs = get_activity_log_for_user(conn, selected_date_act, selected_user, allowed_actions=allowed_actions)
        
        if not df_logs.empty:
            st.caption(f"📊 {len(df_logs)} activities found")
            grouped = df_logs.groupby('session_id')
            # Sort sessions by most recent activity
            session_groups = df_logs.groupby('session_id').agg({'timestamp': 'max'}).reset_index()
            session_groups = session_groups.sort_values('timestamp', ascending=False)
            
            for idx, session_id in enumerate(session_groups['session_id'], 1):
                session_group = df_logs[df_logs['session_id'] == session_id].sort_values('timestamp', ascending=False)
                duration = calculate_session_duration(session_group)
                activity_count = len(session_group)
                st.markdown(
                    f'<div class="session-node">📂 Session {idx} • '
                    f'{activity_count} {"activity" if activity_count == 1 else "activities"} • '
                    f'<span class="session-duration">⏱️ {duration}</span></div>', 
                    unsafe_allow_html=True
                )
                
                for _, row in session_group.iterrows():
                    formatted_time = pd.to_datetime(row['timestamp']).strftime('%I:%M %p')
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
            st.info(f"No activities found for {selected_user} on {selected_date_act.strftime('%B %d, %Y')}")

    if "show_week_details_for" not in st.session_state:
        st.session_state.show_week_details_for = None
        
    if st.session_state.show_week_details_for:
        show_weekly_dialog(conn, selected_user_id, selected_user, st.session_state.show_week_details_for, is_manager=True)
        st.session_state.show_week_details_for = None



def get_daily_submissions_for_admin(conn, user_id, date):
    query = """
        SELECT DISTINCT s.*, u.username 
        FROM daily_checklist_submissions s
        JOIN userss u ON s.user_id = u.id
        JOIN daily_checklist_logs l ON s.id = l.submission_id
        WHERE s.user_id = :user_id 
        AND s.date = :date
        AND l.status IN ('submitted', 'approved', 'rejected')
    """
    return conn.query(query, params={"user_id": user_id, "date": date}, ttl=0)

def admin_dashboard(conn):
    st.subheader("👑 Admin Dashboard", anchor=False, divider="rainbow")
    st.caption("Select an employee and navigate the calendar to view their timesheets.")
    inject_custom_css()

    users_df = get_all_users_with_managers(conn)
    if users_df.empty:
        st.error("Could not load users.")
        return

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        selected_user = st.selectbox(
            "Select Employee",
            options=users_df['username'],
            label_visibility="collapsed"
        )
    
    if not selected_user:
        st.info("Please select an employee to continue.")
        return

    user_info = users_df[users_df['username'] == selected_user].iloc[0]
    selected_user_id = user_info['id']

    tab_weekly, tab_daily = st.tabs(["📅 Weekly Timesheets", "✅ Daily Checklists"])

    with tab_daily:
        available_checklist_years, checklist_month_by_year = get_checklist_available_months_years(conn, selected_user_id)
        
        if not available_checklist_years:
            st.info("No checklist data available for this user.")
        else:
            # Upgrade Admin's Daily Checklist view to use the same calendar system
            c_daily_1, c_daily_2 = st.columns(2)
            with c_daily_1:
                sel_y = st.selectbox("Year", options=available_checklist_years, index=len(available_checklist_years)-1, key="admin_daily_cal_year")
            with c_daily_2:
                m_options = checklist_month_by_year.get(sel_y, [])
                current_month = datetime.now().month
                default_m_index = m_options.index(current_month) if current_month in m_options else len(m_options)-1
                sel_m = st.selectbox("Month", options=m_options, format_func=lambda x: calendar.month_name[x], index=default_m_index, key="admin_daily_cal_month")

            daily_summary = get_daily_checklist_monthly_summary(conn, selected_user_id, sel_y, sel_m)
            
            # Display summary metrics
            total_days_in_month = calendar.monthrange(sel_y, sel_m)[1]
            expected_working_days = sum(1 for d in range(1, total_days_in_month + 1) if date(sel_y, sel_m, d).weekday() != 6)
            display_checklist_monthly_stats(daily_summary, sel_y, sel_m, expected_working_days)
            
            st.write("---")

            # Render Calendar Grid
            days_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            header_cols = st.columns([1,1,1,1,1,1,0.8])
            for i, header in enumerate(days_headers):
                with header_cols[i]: st.markdown(f'<div class="header-card">{header}</div>', unsafe_allow_html=True)
            with header_cols[6]: st.markdown(f'<div class="header-card">Week View</div>', unsafe_allow_html=True)

            status_map = {"approved": "🟢", "submitted": "🟠", "rejected": "🔴", "pending": "🔵", "started": "▶️"}
            status_display = {"approved": "Approved", "submitted": "Submitted", "rejected": "Rejected", "pending": "Pending", "started": "Started"}

            cal = calendar.Calendar()
            for week in cal.monthdatescalendar(sel_y, sel_m):
                cols = st.columns([1,1,1,1,1,1,0.8])
                for i, day_date in enumerate(week[:-1]):
                    with cols[i]:
                        is_current_month = (day_date.month == sel_m)
                        is_weekend = (day_date.weekday() == 6)
                        is_future = day_date > datetime.now().date()
                        daily_data = daily_summary.get(day_date, {})
                        render_checklist_day_card(day_date, daily_data, is_current_month, is_weekend, is_future)

                with cols[6]:
                    if any(d.month == sel_m for d in week):
                        week_dates = [d for d in week[:-1] if d.month == sel_m]
                        if week_dates:
                            # aggregated status for the week
                            week_status = get_week_checklist_status(week_dates, daily_summary)
                            has_data = week_status is not None
                            
                            if not has_data:
                                st.button("No Data", key=f"admin_view_daily_week_{week[0]}_nodata", width='stretch', disabled=True)
                            else:
                                status_emoji = status_map.get(week_status, '⚪️')
                                status_label = status_display.get(week_status, "Summary")
                                if st.button(f"{status_emoji} {status_label}", key=f"admin_view_daily_week_{week[0]}", width='stretch', help="Click to see summary for this whole week"):
                                    show_weekly_checklist_summary_dialog(conn, selected_user_id, selected_user, week_dates, is_admin=True)
                        
                        st.caption(f"Week {week[0].isocalendar().week}", unsafe_allow_html=True)

    with tab_weekly:
        available_years, month_by_year = get_available_months_years(conn, selected_user_id)
        
        if not available_years:
            st.info("No timesheet data available for this user.")
        else:
            current_date = datetime.now()
            default_year = current_date.year if current_date.year in available_years else max(available_years)
            st.session_state.setdefault('selected_year', default_year)

            available_months_for_year = month_by_year.get(st.session_state['selected_year'], [])
            if not available_months_for_year:
                st.session_state['selected_year'] = max(available_years)
                available_months_for_year = month_by_year[max(available_years)]

            default_month = current_date.month if current_date.month in available_months_for_year else max(available_months_for_year)
            st.session_state.setdefault('selected_month', default_month)

            with c2:
                st.selectbox(
                    "Year",
                    options=available_years,
                    key="selected_year",
                    label_visibility="collapsed"
                )

            available_months_for_year = month_by_year.get(st.session_state['selected_year'], [])

            with c3:
                st.selectbox(
                    "Month",
                    options=available_months_for_year,
                    format_func=lambda month: calendar.month_name[month],
                    key="selected_month",
                    label_visibility="collapsed"
                )

            selected_year = st.session_state['selected_year']
            selected_month = st.session_state['selected_month']

            monthly_summary = get_monthly_summary(conn, selected_user_id, selected_year, selected_month)
            
            total_days = calendar.monthrange(selected_year, selected_month)[1]
            expected_working_days = 0
            for day in range(1, total_days + 1):
                date_obj = date(selected_year, selected_month, day)
                if date_obj.weekday() == 6:
                    continue
                if date_obj in monthly_summary and monthly_summary[date_obj]['status'] == 'holiday':
                    continue
                expected_working_days += 1
            expected_working_hours = expected_working_days * 8

            # Display enhanced monthly stats
            display_monthly_stats(
                monthly_summary, selected_year, selected_month,
                expected_working_days, expected_working_hours
            )

            with st.expander("Lifetime Statistics", expanded=False):
                display_lifetime_stats(conn, selected_user_id)
            
            days_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            header_cols = st.columns([1,1,1,1,1,1,0.8], vertical_alignment="bottom")
            for i, header in enumerate(days_headers):
                with header_cols[i]:
                    st.markdown(f'<div class="header-card">{header}</div>', unsafe_allow_html=True)
            with header_cols[6]:
                st.markdown(f'<div class="header-card">Timesheet</div>', unsafe_allow_html=True)
            

            cal = calendar.Calendar()
            status_map = {"approved": "🟢", "submitted": "🟠", "rejected": "🔴", "draft": "🔵"}
            status_display = {"approved": "Approved", "submitted": "Submitted", "rejected": "Rejected", "draft": "Draft"}
            now_date = datetime.now().date()
            for week in cal.monthdatescalendar(selected_year, selected_month):
                cols = st.columns([1,1,1,1,1,1,0.8])
                for i, day_date in enumerate(week[:-1]):
                    with cols[i]:
                        is_current_month = (day_date.month == selected_month)
                        is_weekend = (day_date.weekday() == 6)  # Only Sunday is weekend
                        is_future = day_date > datetime.now().date()
                        daily_data = monthly_summary.get(day_date, {})
                        render_day_card(day_date, daily_data, is_current_month, is_weekend, is_future)
                with cols[6]:
                    if any(d.month == selected_month for d in week):
                        week_start_date = week[0]
                        # Get status from one day in the week
                        week_days = [d for d in week[:-1] if d in monthly_summary]
                        timesheet_status = None
                        if week_days:
                            timesheet_status = monthly_summary[week_days[0]]['timesheet_status']
                        
                        is_future_week = week_start_date > now_date
                        has_timesheet = bool(week_days and timesheet_status)
                        disabled = is_future_week or not has_timesheet
                        # Calculate week number
                        week_number = week_start_date.isocalendar().week
                        
                        if disabled:
                            button_text = "No Data" if not has_timesheet else "Future"
                            st.button(button_text, key=f"week_btn_{week_start_date}_disabled", width='stretch', disabled=True)
                            st.caption(f"Week {week_number}", unsafe_allow_html=True)
                        else:
                            status_emoji = status_map.get(timesheet_status, '⚪️')
                            status_label = status_display.get(timesheet_status, "Unknown")
                            if st.button(f"{status_emoji} {status_label}", key=f"week_btn_{week_start_date}", width='stretch'):
                                st.session_state.show_week_details_for = week_start_date
                                st.rerun()
                            st.caption(f"Week {week_number}", unsafe_allow_html=True)

    if "show_week_details_for" not in st.session_state:
        st.session_state.show_week_details_for = None
        
    if st.session_state.show_week_details_for:
        show_weekly_dialog(conn, selected_user_id, selected_user, st.session_state.show_week_details_for, is_admin = True)
        st.session_state.show_week_details_for = None



###################################################################################################################################
##################################--------------- Daily Checklist ----------------------------########################################
###################################################################################################################################

def get_daily_responsibilities(conn, user_id):
    query = "SELECT id, task_name, description, manager_id FROM daily_responsibilities WHERE user_id = :user_id AND is_active = 1"
    return conn.query(query, params={"user_id": user_id}, ttl=0)

def get_today_submission(conn, user_id, date):
    query = """
        SELECT s.*, u.username 
        FROM daily_checklist_submissions s
        JOIN userss u ON s.user_id = u.id
        WHERE s.user_id = :user_id AND s.date = :date
    """
    return conn.query(query, params={"user_id": user_id, "date": date}, ttl=0)

@st.cache_data(ttl=600)
def get_checklist_late_submitters_for_manager(_conn, manager_id):
    """
    Checks for direct reports who have not submitted their daily checklist for any day since their start date.
    """
    today = get_ist_date()
    try:
        # Get direct reports
        reports_df = get_direct_reports(_conn, manager_id)
        if reports_df.empty:
            return []
        
        late_users = []
        for _, user in reports_df.iterrows():
            user_id = user['id']
            # Get user joining date
            user_info = get_user_details(user_id)
            if not user_info or not st.session_state.start_date: # Fallback to session state start_date
                continue
            
            start_date = pd.to_datetime(st.session_state.start_date).date()
            
            # Find earliest missing or unsubmitted date
            # We'll check the last 7 days for performance, or since joining if later
            check_start = max(start_date, today - timedelta(days=7))
            
            query = """
                SELECT DISTINCT s.date FROM daily_checklist_submissions s
                JOIN daily_checklist_logs l ON s.id = l.submission_id
                WHERE s.user_id = :user_id 
                AND s.date >= :check_start 
                AND s.date < :today
                AND (s.manager_id = :manager_id OR l.manager_id = :manager_id)
                AND l.status IN ('submitted', 'approved')
            """
            submitted_dates_df = _conn.query(query, params={"user_id": user_id, "check_start": check_start, "today": today, "manager_id": manager_id}, ttl=0)
            submitted_dates = set(submitted_dates_df['date']) if not submitted_dates_df.empty else set()
            
            # Check each working day
            curr = check_start
            while curr < today:
                if curr.weekday() != 6: # Not Sunday
                    if curr not in submitted_dates:
                        late_users.append(user['username'])
                        break
                curr += timedelta(days=1)
                
        return sorted(list(set(late_users)))
    except Exception as e:
        return []

def determine_checklist_date_to_display(conn, user_id):
    """
    Determines which date's checklist to display.
    Forces user to fill missing checklists before today.
    """
    today = get_ist_date()
    
    try:
        # Get all existing checklists for this user (limited to last 30 days for performance)
        lookback_date = today - timedelta(days=30)
        
        # Enhanced query using CTE to find the latest status of EACH responsibility
        existing_query = """
            WITH LatestLogs AS (
                SELECT submission_id, responsibility_id, status,
                       ROW_NUMBER() OVER(PARTITION BY submission_id, responsibility_id ORDER BY id DESC) as rn
                FROM daily_checklist_logs
            )
            SELECT s.date, s.status as sub_status,
                   COUNT(l.responsibility_id) as total_tasks,
                   COUNT(CASE WHEN l.status IN ('submitted', 'approved') THEN 1 END) as completed_tasks
            FROM daily_checklist_submissions s
            LEFT JOIN LatestLogs l ON s.id = l.submission_id AND l.rn = 1
            WHERE s.user_id = :user_id
            AND s.date >= :lookback_date
            GROUP BY s.date, s.status
            ORDER BY s.date ASC
        """
        existing_df = conn.query(existing_query, params={"user_id": user_id, "lookback_date": lookback_date}, ttl=0)
        
        # Determine check start: joining date or lookback_date
        start_date_raw = st.session_state.get("start_date")
        if start_date_raw:
            start_date = pd.to_datetime(start_date_raw).date()
            check_start = max(start_date, lookback_date)
        else:
            check_start = lookback_date

        # Check each day from check_start to today
        curr = check_start
        while curr < today:
            if curr.weekday() != 6: # Not Sunday
                # Find if checklist exists for this date
                day_match = existing_df[existing_df['date'] == curr] if not existing_df.empty else pd.DataFrame()
                
                if day_match.empty:
                    # Missing entirely
                    st.warning(f"⚠️ **Missing Daily Checklist:** You must complete the checklist for **{curr.strftime('%A, %b %d')}** before accessing today's.")
                    return curr, True
                else:
                    # Check if all tasks are submitted or approved
                    row = day_match.iloc[0]
                    if row['total_tasks'] == 0:
                        # Day initialized but no tasks? Might happen if admin just added responsibility
                        # Let them proceed to it to trigger sync
                        st.warning(f"⚠️ **Pending Daily Checklist:** Your checklist for **{curr.strftime('%A, %b %d')}** has no tasks yet. Please initialize it.")
                        return curr, True
                    
                    if row['completed_tasks'] < row['total_tasks']:
                        # Some tasks are still pending, started, completed (but not submitted), or rejected
                        st.warning(f"⚠️ **Pending Daily Checklist:** You have **{row['total_tasks'] - row['completed_tasks']}** tasks pending or rejected for **{curr.strftime('%A, %b %d')}**. Please finish them first.")
                        return curr, True
            curr += timedelta(days=1)
            
    except Exception as e:
        pass

    return today, False

def get_checklist_logs(conn, submission_id):
    query = """
        SELECT l.*, u.username as manager_name 
        FROM daily_checklist_logs l 
        LEFT JOIN userss u ON l.manager_id = u.id 
        WHERE l.submission_id = :submission_id
    """
    return conn.query(query, params={"submission_id": submission_id}, ttl=0)

@st.dialog("Weekly Checklist Summary", width="large")
def show_weekly_checklist_summary_dialog(conn, user_id, username, week_dates, is_manager=False, is_admin=False):
    """Dialog that shows all checklist entries for a week using tabs for quick navigation."""
    st.subheader(f"📅 Weekly Summary: {username}", anchor=False)
    
    # Robustly identify if current user is an admin to grant oversight
    is_admin = is_admin or st.session_state.get("role") == "admin"
    
    # Filter for dates in the current month to match the calendar week
    active_dates = [d for d in week_dates]
    
    tabs = st.tabs([d.strftime('%a, %b %d') for d in active_dates])
    
    for i, date_obj in enumerate(active_dates):
        with tabs[i]:
            submission_df = get_today_submission(conn, user_id, date_obj)
            if submission_df.empty:
                st.info(f"No checklist data for {date_obj.strftime('%A, %b %d')}.")
            else:
                render_daily_checklist_inline(conn, submission_df.iloc[0], is_manager=is_manager, is_admin=is_admin, key_suffix="_weekly")

def daily_checklist_page(conn):
    st.subheader(f"✅ Daily Responsibilities Checklist", anchor=False, divider="rainbow")
    inject_custom_css()
    user_id = st.session_state.user_id
    username = st.session_state.username
    
    tab_active, tab_history = st.tabs(["⚡ Active Checklist", "📊 History"])

    with tab_history:
        # Year/Month selection
        c_hist_1, c_hist_2 = st.columns(2)
        with c_hist_1:
            y_options = [datetime.now().year, datetime.now().year - 1]
            sel_y = st.selectbox("Year", options=y_options, key="user_daily_hist_year")
        with c_hist_2:
            m_options = list(range(1, 13))
            sel_m = st.selectbox("Month", options=m_options, format_func=lambda x: calendar.month_name[x], index=datetime.now().month-1, key="user_daily_hist_month")

        daily_summary = get_daily_checklist_monthly_summary(conn, user_id, sel_y, sel_m)
        
        # Calculate expected working days for metrics
        total_days_in_month = calendar.monthrange(sel_y, sel_m)[1]
        expected_working_days = sum(1 for d in range(1, total_days_in_month + 1) if date(sel_y, sel_m, d).weekday() != 6)
        
        # Display summary metrics
        display_checklist_monthly_stats(daily_summary, sel_y, sel_m, expected_working_days)
        
        st.write("---")

        # Render Calendar Grid
        days_headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        header_cols = st.columns([1,1,1,1,1,1,0.8])
        for i, header in enumerate(days_headers):
            with header_cols[i]: st.markdown(f'<div class="header-card">{header}</div>', unsafe_allow_html=True)
        with header_cols[6]: st.markdown(f'<div class="header-card">Week View</div>', unsafe_allow_html=True)

        status_map = {"approved": "🟢", "submitted": "🟠", "rejected": "🔴", "pending": "🔵", "started": "▶️"}
        status_display = {"approved": "Approved", "submitted": "Submitted", "rejected": "Rejected", "pending": "Pending", "started": "Started"}

        cal = calendar.Calendar()
        for week in cal.monthdatescalendar(sel_y, sel_m):
            cols = st.columns([1,1,1,1,1,1,0.8])
            for i, day_date in enumerate(week[:-1]):
                with cols[i]:
                    is_current_month = (day_date.month == sel_m)
                    is_weekend = (day_date.weekday() == 6)
                    is_future = day_date > datetime.now().date()
                    daily_data = daily_summary.get(day_date, {})
                    render_checklist_day_card(day_date, daily_data, is_current_month, is_weekend, is_future)
                    
            with cols[6]:
                if any(d.month == sel_m for d in week):
                    week_dates = [d for d in week[:-1] if d.month == sel_m]
                    if week_dates:
                        # aggregated status for the week
                        week_status = get_week_checklist_status(week_dates, daily_summary)
                        has_data = week_status is not None
                        
                        if not has_data:
                            st.button("No Data", key=f"user_view_daily_week_{week[0]}_nodata", width='stretch', disabled=True)
                        else:
                            status_emoji = status_map.get(week_status, '⚪️')
                            status_label = status_display.get(week_status, "Summary")
                            if st.button(f"{status_emoji} {status_label}", key=f"user_view_daily_week_{week[0]}", width='stretch', help="Click to see summary for this whole week"):
                                show_weekly_checklist_summary_dialog(conn, user_id, username, week_dates)
                    
                    st.caption(f"Week {week[0].isocalendar().week}", unsafe_allow_html=True)

    with tab_active:
        # NEW: Determine the correct date to show (missing previous days first)
        display_date, is_historical = determine_checklist_date_to_display(conn, user_id)
        
        if is_historical:
            st.info(f"📅 Showing pending checklist for **{display_date.strftime('%A, %b %d, %Y')}**")
        
        # 1. Get or Create Submission for the display date
        submission_df = get_today_submission(conn, user_id, display_date)
        
        if submission_df.empty:
            responsibilities = get_daily_responsibilities(conn, user_id)
            if responsibilities.empty:
                st.info("Please add at least one responsibility in the section below to get started.")
            else:
                # Auto-initialize the day's record
                try:
                    manager_id = None
                    user_info = get_user_details(user_id)
                    if user_info and user_info['report_to']:
                        mgr_res = conn.query("SELECT id FROM userss WHERE username = :uname", params={"uname": user_info['report_to']}, ttl=3600)
                        if not mgr_res.empty:
                            manager_id = int(mgr_res.iloc[0]['id'])

                    with conn.session as s:
                        s.execute(text("INSERT INTO daily_checklist_submissions (user_id, date, manager_id) VALUES (:uid, :date, :mid)"),
                                  {"uid": user_id, "date": display_date, "mid": manager_id})
                        s.commit()
                        
                        res = s.execute(text("SELECT id FROM daily_checklist_submissions WHERE user_id = :uid AND date = :date"),
                                        {"uid": user_id, "date": display_date}).fetchone()
                        sub_id = res[0]
                        
                        for _, row in responsibilities.iterrows():
                            # Use responsibility specific manager if set, else use the submission default manager
                            task_manager_id = row['manager_id'] if pd.notna(row['manager_id']) else manager_id
                            s.execute(text("INSERT INTO daily_checklist_logs (submission_id, responsibility_id, manager_id) VALUES (:sid, :rid, :mid)"),
                                      {"sid": sub_id, "rid": row['id'], "mid": task_manager_id})
                        s.commit()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error initializing: {e}")
            
            return

        # 2. Submission exists
        sub_row = submission_df.iloc[0]
        sub_id = sub_row['id']
        today = display_date # Correctly scope today to display_date for historical logs

        # SYNC: Check for newly added or updated master responsibilities
        try:
            master_resp = get_daily_responsibilities(conn, user_id)
            existing_logs = get_checklist_logs(conn, sub_id)
            
            # 1. Handle Missing Tasks
            missing_resp_ids = set(master_resp['id']) - set(existing_logs['responsibility_id'])
            if missing_resp_ids:
                with conn.session as s:
                    for rid in missing_resp_ids:
                        resp_row = master_resp[master_resp['id'] == rid].iloc[0]
                        task_manager_id = resp_row['manager_id'] if pd.notna(resp_row['manager_id']) else sub_row['manager_id']
                        s.execute(text("INSERT INTO daily_checklist_logs (submission_id, responsibility_id, manager_id) VALUES (:sid, :rid, :mid)"),
                                  {"sid": sub_id, "rid": rid, "mid": task_manager_id})
                    s.commit()
                st.rerun()

            # 2. Sync Manager IDs for all tasks if they changed in master (or are NULL)
            with conn.session as s:
                needs_rerun = False
                for _, m_row in master_resp.iterrows():
                    # Sync to the latest manager assignment from master responsibility
                    target_manager_id = m_row['manager_id'] if pd.notna(m_row['manager_id']) else sub_row['manager_id']
                    
                    # Update logs where manager_id is missing or different
                    res = s.execute(text("""
                        UPDATE daily_checklist_logs 
                        SET manager_id = :mid 
                        WHERE responsibility_id = :rid 
                        AND submission_id = :sid 
                        AND (manager_id IS NULL OR manager_id != :mid)
                    """), {"mid": target_manager_id, "rid": m_row['id'], "sid": sub_id})
                    
                    if res.rowcount > 0:
                        needs_rerun = True
                
                if needs_rerun:
                    s.commit()
                    st.rerun()
        except Exception as e:
            pass
        
        # REPAIR: If manager_id is NULL, try to fix it now
        if pd.isna(sub_row['manager_id']):
            try:
                user_info = get_user_details(user_id)
                if user_info and user_info['report_to']:
                    mgr_res = conn.query("SELECT id FROM userss WHERE username = :uname", params={"uname": user_info['report_to']}, ttl=3600)
                    if not mgr_res.empty:
                        m_id = int(mgr_res.iloc[0]['id'])
                        with conn.session as s:
                            s.execute(text("UPDATE daily_checklist_submissions SET manager_id = :mid WHERE id = :sid"), {"mid": m_id, "sid": sub_id})
                            s.commit()
                        st.rerun()
            except:
                pass
        
        logs_df = get_checklist_logs(conn, sub_id)
        resp_df = conn.query("SELECT id, task_name, description, manager_id FROM daily_responsibilities WHERE user_id = :user_id", params={"user_id": user_id}, ttl=0)
        merged_df = logs_df.merge(resp_df, left_on='responsibility_id', right_on='id', suffixes=('', '_master'))
        
        active_activity = any(merged_df['status'] == 'started')
        merged_df = merged_df.sort_values(['responsibility_id', 'id'])

        # --- Progress bar ---
        total_tasks = merged_df['responsibility_id'].nunique()
        latest_per_task = merged_df.groupby('responsibility_id').last()
        done_count = int(latest_per_task['status'].isin(['approved', 'submitted']).sum())
        st.progress(done_count / max(total_tasks, 1), text=f"{done_count} of {total_tasks} tasks submitted or approved")

        if active_activity:
            st.warning("A task is currently in progress — finish it before starting another.", icon="⚠️")

        st.markdown("")

        status_icons = {"pending": "🕒", "started": "▶️", "completed": "⏹️", "submitted": "📤", "approved": "✅", "rejected": "❌"}
        status_colors = {
            "pending": ("#f0f2f6", "#31333f"),
            "started": ("#fff4e5", "#b35900"),
            "completed": ("#e6ffed", "#22863a"),
            "submitted": ("#f5f0ff", "#6f42c1"),
            "approved": ("#e6ffed", "#22863a"),
            "rejected": ("#ffeef0", "#d73a49")
        }

        for resp_id, group in merged_df.groupby('responsibility_id'):
            group = group.reset_index(drop=True)
            latest = group.iloc[-1]
            latest_status = latest['status']
            
            # Identify if there was a previous rejection for this specific task
            prev_rejected_row = None
            if latest_status in ['pending', 'started', 'completed'] and len(group) > 1:
                # Look backwards for the most recent rejected row
                for idx in range(len(group)-2, -1, -1):
                    if group.iloc[idx]['status'] == 'rejected':
                        prev_rejected_row = group.iloc[idx]
                        break

            with st.container(border=True):
                # Task title + current status on same line
                col_title, col_badge = st.columns([0.7, 0.3])
                col_title.markdown(f"### 📋 {group.iloc[0]['task_name']}")
                
                # Show description if available
                if pd.notna(group.iloc[0].get('description')) and group.iloc[0]['description']:
                    st.markdown(f"""
                        <div style='color: #64748b; font-size: 0.85rem; margin-top: -10px; margin-bottom: 12px; margin-left: 47px; font-style: italic; line-height: 1.4;'>
                            {group.iloc[0]['description']}
                        </div>
                    """, unsafe_allow_html=True)
                
                bg, fg = status_colors.get(latest_status, ("#f0f2f6", "#31333f"))
                badge_html = f"""
                    <div style='background-color: {bg}; color: {fg}; padding: 6px 14px; 
                    border-radius: 20px; font-size: 0.85rem; font-weight: 700; 
                    display: inline-block; text-transform: uppercase; letter-spacing: 0.8px; 
                    border: 1px solid {fg}22;'>
                        {status_icons.get(latest_status, '')} {latest_status}
                    </div>
                """
                col_badge.markdown(f"<div style='text-align:right; padding-top:10px'>{badge_html}</div>", unsafe_allow_html=True)

                # Metadata columns for the latest attempt
                m1, m2, m3, m4, m5 = st.columns(5)
                
                def render_meta_col(col, label, val):
                    col.markdown(f"""
                        <div style='line-height: 1.2;'>
                            <p style='color: #808495; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 4px;'>{label}</p>
                            <p style='font-size: 1rem; font-weight: 500; margin-bottom: 0;'>{val}</p>
                        </div>
                    """, unsafe_allow_html=True)

                start_val = pd.to_datetime(latest['start_time']).strftime('%I:%M %p') if pd.notna(latest['start_time']) else "—"
                end_val = pd.to_datetime(latest['end_time']).strftime('%I:%M %p') if pd.notna(latest['end_time']) else "—"
                sub_val = pd.to_datetime(latest['submitted_at']).strftime('%I:%M %p') if pd.notna(latest['submitted_at']) else "—"
                
                duration_val = "—"
                if pd.notna(latest['start_time']) and pd.notna(latest['end_time']):
                    dur = pd.to_datetime(latest['end_time']) - pd.to_datetime(latest['start_time'])
                    mins = int(dur.total_seconds() // 60)
                    duration_val = f"{mins} mins" if mins < 60 else f"{mins//60}h {mins%60}m"
                
                mgr_val = latest.get('manager_name') if pd.notna(latest.get('manager_name')) else "Default"

                render_meta_col(m1, "Reporting To", mgr_val)
                render_meta_col(m2, "Start Time", start_val)
                render_meta_col(m3, "End Time", end_val)
                render_meta_col(m4, "Submitted At", sub_val)
                render_meta_col(m5, "Duration", duration_val)

                # Notes and Feedback for LATEST attempt
                if (pd.notna(latest.get('resubmission_notes')) and latest.get('resubmission_notes')) or \
                   (pd.notna(latest['review_notes']) and latest['review_notes']):
                    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                
                # Contextual Feedback for Retries (Show previous rejection reason if current is a retry)
                if prev_rejected_row is not None and pd.notna(prev_rejected_row['review_notes']):
                    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                    st.warning(f"**Rejection Feedback (Previous Attempt):** {prev_rejected_row['review_notes']}", icon="⚠️")

                st.write("")

                # Previous attempts collapsed
                if len(group) > 1:
                    with st.expander(f"🕓 View Attempt History ({len(group)})", expanded=True):
                        # Show all attempts in reverse order for better hierarchy
                        for i, (_, hist_row) in enumerate(group.iloc[::-1].iterrows()):
                            h_idx = len(group) - i
                            is_latest_hist = (i == 0)
                            h_bg, h_fg = status_colors.get(hist_row['status'], ("#f0f2f6", "#31333f"))
                            
                            # Use a clearer background for approved/rejected rows in history
                            card_bg = "#f8f9fa"
                            if hist_row['status'] == 'approved': card_bg = "#f0fff4"
                            elif hist_row['status'] == 'rejected': card_bg = "#fff5f5"

                            st.markdown(f"""
                                <div style='background-color: {card_bg}; padding: 12px; border-radius: 8px; border-left: 4px solid {h_fg}; margin-bottom: 12px;'>
                                    <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'>
                                        <span style='font-weight: 700; font-size: 0.95rem;'>Attempt #{h_idx} {"(Latest)" if is_latest_hist else ""}</span>
                                        <span style='color: {h_fg}; font-weight: 800; font-size: 0.85rem; text-transform: uppercase;'>{hist_row['status']}</span>
                                    </div>
                                    <div style='display: flex; flex-wrap: wrap; gap: 15px; color: #555; font-size: 0.85rem; margin-bottom: 8px;'>
                                        <span><b>Start:</b> {pd.to_datetime(hist_row['start_time']).strftime('%I:%M %p') if pd.notna(hist_row['start_time']) else '—'}</span>
                                        <span><b>End:</b> {pd.to_datetime(hist_row['end_time']).strftime('%I:%M %p') if pd.notna(hist_row['end_time']) else '—'}</span>
                                        <span><b>Submitted:</b> {pd.to_datetime(hist_row['submitted_at']).strftime('%I:%M %p') if pd.notna(hist_row['submitted_at']) else '—'}</span>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # Notes placed inside the history context but after the main block
                            if pd.notna(hist_row.get('resubmission_notes')) and hist_row.get('resubmission_notes'):
                                st.markdown(f"<div style='margin: -8px 0 10px 15px; padding: 5px 10px; border-left: 2px solid #6f42c1; font-size: 0.85rem; color: #444;'>📝 <b>Correction:</b> {hist_row['resubmission_notes']}</div>", unsafe_allow_html=True)
                            if pd.notna(hist_row['review_notes']) and hist_row['review_notes']:
                                st.markdown(f"<div style='margin: -8px 0 10px 15px; padding: 5px 10px; border-left: 2px solid #d73a49; font-size: 0.85rem; color: #b31d28;'>💬 <b>Feedback:</b> {hist_row['review_notes']}</div>", unsafe_allow_html=True)

                # Latest attempt: actions
                st.markdown("<hr style='margin: 15px 0; opacity: 0.1;'>", unsafe_allow_html=True)
                col_actions = st.columns([1])[0] # Use full width for actions

                with col_actions:
                    row = latest
                    status = latest_status
                    attempt_index = len(group) - 1

                    if status == 'pending':
                        if st.button("▶️ Start Task", key=f"start_{row['id']}", disabled=active_activity,
                                     help="Finish the active task before starting another." if active_activity else None,
                                     use_container_width=True, type="secondary"):
                            try:
                                now = get_ist_time()
                                with conn.session as s:
                                    s.execute(text("UPDATE daily_checklist_logs SET status = 'started', start_time = :now WHERE id = :id"),
                                              {"now": now, "id": row['id']})
                                    if pd.isna(sub_row['start_time']):
                                        s.execute(text("UPDATE daily_checklist_submissions SET start_time = :now WHERE id = :id"),
                                                  {"now": now, "id": sub_id})
                                    s.commit()
                                st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
                    
                    elif status == 'started':
                        if st.button("⏹️ End Task", key=f"end_{row['id']}", type="primary", use_container_width=True):
                            try:
                                now = get_ist_time()
                                # 1. Get/Create Timesheet for the checklist date
                                f_week = today.isocalendar()[1]
                                ts_id, ts_status, _ = get_or_create_timesheet(conn, user_id, f_week)
                                
                                # DUR CALCULATION: Consistent across both cases
                                duration = 0.0
                                if row['start_time']:
                                    start_time = pd.to_datetime(row['start_time'])
                                    if start_time.tzinfo is None:
                                        start_time = pytz.timezone('Asia/Kolkata').localize(start_time)
                                    diff = now - start_time
                                    duration = max(0.0, diff.total_seconds() / 3600.0)

                                if not ts_id:
                                    # Still allow ending the task in Checklist Logs to avoid deadlock
                                    with conn.session as s:
                                        s.execute(text("UPDATE daily_checklist_logs SET status = 'completed', end_time = :now WHERE id = :id"),
                                                  {"now": now, "id": row['id']})
                                        s.execute(text("UPDATE daily_checklist_submissions SET end_time = :now WHERE id = :id"),
                                                  {"now": now, "id": sub_id})
                                        s.commit()
                                    st.warning("⚠️ **Task Ended, but NOT logged to Timesheet.** You have pending timesheets from previous weeks that must be submitted first. Please fix them and then manually log this duration.")
                                    time.sleep(3)
                                    st.rerun()
                                    return
                                
                                # 3. Proceed with normal auto-log if timesheet exists
                                with conn.session as s:
                                    # Update Daily Checklist Logs
                                    s.execute(text("UPDATE daily_checklist_logs SET status = 'completed', end_time = :now WHERE id = :id"),
                                              {"now": now, "id": row['id']})
                                    s.execute(text("UPDATE daily_checklist_submissions SET end_time = :now WHERE id = :id"),
                                              {"now": now, "id": sub_id})
                                    
                                    # Auto-log to Weekly Timesheet ('work' table)
                                    s.execute(text("""
                                        INSERT INTO work (timesheet_id, work_date, work_name, work_description, work_duration, entry_type)
                                        VALUES (:ts_id, :w_date, :w_name, :w_desc, :w_dur, 'work')
                                    """), {
                                        "ts_id": ts_id,
                                        "w_date": today,
                                        "w_name": row['task_name'],
                                        "w_desc": f"Completed Responsibility: {row['task_name']}",
                                        "w_dur": round(duration, 2),
                                    })
                                    s.commit()
                                
                                log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, 
                                             "COMPLETED_RESPONSIBILITY", f"Auto-logged {row['task_name']} to timesheet ({round(duration, 2)} hrs)")
                                st.toast(f"Task completed and logged to timesheet! ✨")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
                    
                    elif status == 'completed':
                        is_correction_attempt = (attempt_index > 0 or row.get('is_correction', False))
                        
                        if is_correction_attempt:
                            with st.popover("📤 Submit Correction", use_container_width=True):
                                resub_note = st.text_area("What did you correct?", placeholder="Describe what was fixed…", key=f"resub_note_submit_{row['id']}")
                                if st.button("Confirm Submission", key=f"conf_sub_{row['id']}", type="primary", use_container_width=True):
                                    if not resub_note.strip():
                                        st.warning("Please describe what was corrected.")
                                    else:
                                        try:
                                            now = get_ist_time()
                                            with conn.session as s:
                                                s.execute(text("UPDATE daily_checklist_logs SET status = 'submitted', submitted_at = :now, resubmission_notes = :note WHERE id = :id"),
                                                          {"now": now, "note": resub_note.strip(), "id": row['id']})
                                                s.execute(text("UPDATE daily_checklist_submissions SET status = 'submitted', submitted_at = :now WHERE id = :id"),
                                                          {"now": now, "id": sub_id})
                                                s.commit()
                                            st.rerun()
                                        except Exception as e: st.error(f"Error: {e}")
                        else:
                            if st.button("📤 Submit for Review", key=f"submit_{row['id']}", type="primary", use_container_width=True):
                                try:
                                    now = get_ist_time()
                                    with conn.session as s:
                                        s.execute(text("UPDATE daily_checklist_logs SET status = 'submitted', submitted_at = :now WHERE id = :id"),
                                                  {"now": now, "id": row['id']})
                                        s.execute(text("UPDATE daily_checklist_submissions SET status = 'submitted', submitted_at = :now WHERE id = :id"),
                                                  {"now": now, "id": sub_id})
                                        s.commit()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    
                    elif status == 'submitted':
                        st.button("⌛ Awaiting Manager Review", key=f"wait_{row['id']}", disabled=True, use_container_width=True)
                    
                    elif status == 'approved':
                        st.success("✅ Task Approved", icon="🎉")
                    
                    elif status == 'rejected':
                        if st.button("↺ Retry / Correct Task", key=f"retry_btn_{row['id']}", type="primary", use_container_width=True):
                            try:
                                with conn.session as s:
                                    s.execute(text("""
                                        INSERT INTO daily_checklist_logs (submission_id, responsibility_id, status, is_correction, manager_id)
                                        VALUES (:sid, :rid, 'pending', 1, :mid)
                                    """), {"sid": sub_id, "rid": row['responsibility_id'], "mid": row['manager_id']})
                                    s.commit()
                                st.rerun()
                            except Exception as e: st.error(f"Error: {e}")

###################################################################################################################################
##################################--------------- Main----------------------------########################################
###################################################################################################################################

# --- Main App Runner ---
def main():
    if 'user_id' not in st.session_state:
        st.warning("Please log in to use the application.")
        st.stop()

    user_details = get_user_details(user_id)

    with st.sidebar:
        st.header(f"Welcome, {user_details['username']}!")
        st.caption(f"Associate ID: **{user_details['associate_id']}**")
        st.caption(f"Designation: **{user_details['designation']}**")
        st.caption(f"Report To: **{user_details['report_to']}**")
        st.markdown("---")
        
        pages = []
        # CHANGED: Admins do not see personal timesheet pages.
        if st.session_state.role != 'admin':
            pages.extend(["My Timesheet", "Daily Checklist", "Timesheet History"])

        # Add Manager Dashboard if user is a reporting manager (applies to admins too).
        if st.session_state.level in ['reporting_manager', 'both']:
            pages.append("Manager Dashboard")

        # NEW: Add Admin Dashboard only if user is an admin.
        if st.session_state.role == 'admin':
            pages.append("Admin Dashboard")

        # Set the default landing page.
        default_index = 0
        if st.session_state.role == 'admin':
            try:
                # Admins land on Admin Dashboard.
                default_index = pages.index("Admin Dashboard")
            except ValueError:
                if "Manager Dashboard" in pages:
                    default_index = pages.index("Manager Dashboard")
        # Standard users and Managers now both land on "My Timesheet" (index 0) by default.
        # Managers can still navigate to their Dashboard via the sidebar.

        if not pages:
            st.warning("No pages available for your user role.")
            st.stop()
            
        page = st.radio("Navigation", pages, index=default_index, label_visibility="collapsed")
        st.markdown("---")
        # You can add logout button or other info here
        click_id = str(uuid.uuid4())
        query_params = {
            "click_id": click_id,
            "session_id": st.session_state.session_id
        }
        message_url = get_page_url('/', token) + f"&{urlencode(query_params, quote_via=quote)}"
        st.link_button("💬 Message", message_url, width='stretch', help= "Connect with Team")

    page_map = {
        "Daily Checklist": daily_checklist_page,
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