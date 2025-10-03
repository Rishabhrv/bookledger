import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from sqlalchemy import text
import time
from constants import connect_db
import uuid
from auth import validate_token
import calendar
from datetime import datetime, timedelta, date


# --- Initial Imports and Setup ---
# This part is assumed to be at the top of your script.
st.set_page_config(layout="wide", page_title="Timesheet App", initial_sidebar_state="collapsed")
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


###################################################################################################################################
##################################--------------- Helper ----------------------------########################################
###################################################################################################################################


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

        df = conn.query(sql=query, params=params, ttl=60)

        if df.empty:
            return {}

        df['work_date'] = pd.to_datetime(df['work_date']).dt.date

        summary_data = {}
        for work_date, group in df.groupby('work_date'):
            total_hours = group['work_duration'].sum()
            statuses_set = set(group['entry_type'])
            status = 'work'
            
            if 'leave' in statuses_set:
                status = 'leave'
            elif 'holiday' in statuses_set:
                status = 'holiday'
            elif 'half_day' in statuses_set:
                status = 'half_day'
            elif 'power_cut' in statuses_set:
                status = 'power_cut'
            elif 'no_internet' in statuses_set:
                status = 'no_internet'
            elif 'other' in statuses_set:
                status = 'other'
            elif len(statuses_set) > 1:
                status = group['entry_type'].iloc[0]
            elif len(statuses_set) == 1:
                status = list(statuses_set)[0]

            type_hours = group.groupby('entry_type')['work_duration'].sum().to_dict()

            holiday_name = None
            if 'holiday' in statuses_set:
                holiday_name = group[group['entry_type'] == 'holiday']['work_name'].iloc[0]

            day_summary = {
                'status': status,
                'total_hours': total_hours,
                'type_hours': type_hours,
                'holiday_name': holiday_name,
                'timesheet_id': group['timesheet_id'].iloc[0],
                'timesheet_status': group['status'].iloc[0]
            }
            
            summary_data[work_date] = day_summary

        return summary_data

    except Exception as e:
        st.error(f"Error fetching monthly summary: {e}")
        return {}

def get_user_lifetime_stats(conn, user_id: int) -> dict:
    try:
        query_work = """
            SELECT SUM(w.work_duration) AS total_work_hours
            FROM work w
            JOIN timesheets t ON w.timesheet_id = t.id
            WHERE t.user_id = :user_id AND w.entry_type = 'work'
        """
        params = {"user_id": user_id}
        df_work = conn.query(sql=query_work, params=params, ttl=60)
        total_work_hours = df_work['total_work_hours'].iloc[0] if not df_work.empty else 0

        query_leave = """
            SELECT COUNT(DISTINCT w.work_date) AS leave_days
            FROM work w
            JOIN timesheets t ON w.timesheet_id = t.id
            WHERE t.user_id = :user_id AND w.entry_type = 'leave'
        """
        df_leave = conn.query(sql=query_leave, params=params, ttl=60)
        leave_days = df_leave['leave_days'].iloc[0] if not df_leave.empty else 0

        query_half = """
            SELECT COUNT(DISTINCT w.work_date) AS half_days
            FROM work w
            JOIN timesheets t ON w.timesheet_id = t.id
            WHERE t.user_id = :user_id AND w.entry_type = 'half_day'
        """
        df_half = conn.query(sql=query_half, params=params, ttl=60)
        half_days = df_half['half_days'].iloc[0] if not df_half.empty else 0

        return {
            'total_work_hours': total_work_hours or 0,
            'leave_days': leave_days,
            'half_days': half_days
        }

    except Exception as e:
        st.error(f"Error fetching lifetime stats: {e}")
        return {'total_work_hours': 0, 'leave_days': 0, 'half_days': 0}

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
        df = conn.query(sql=query, params=params, ttl=60)
        
        if df.empty:
            return [], {}
        
        years = sorted(df['year'].astype(int).unique().tolist())
        month_by_year = {y: sorted(df[df['year']==y]['month'].astype(int).tolist()) for y in years}
        return years, month_by_year

    except Exception as e:
        st.error(f"Error fetching available months/years: {e}")
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
        df = conn.query(sql=query, params=params, ttl=60)

        if not df.empty:
            df['work_date'] = pd.to_datetime(df['work_date']).dt.date
        
        return df

    except Exception as e:
        st.error(f"Error fetching weekly work details: {e}")
        return pd.DataFrame()

def get_direct_reports(conn, manager_id: int) -> pd.DataFrame:
    try:
        query = """
            SELECT DISTINCT u.id, u.username FROM userss u
            JOIN timesheets t ON u.id = t.user_id
            WHERE t.manager_id = :manager_id
            ORDER BY u.username;
        """
        params = {"manager_id": manager_id}
        df = conn.query(sql=query, params=params, ttl=60)
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
        df = conn.query(sql=query, params=params, ttl=60)

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
    
###################################################################################################################################
##################################--------------- Dialogs----------------------------########################################
###################################################################################################################################



@st.dialog("⚙️ Manage Entry", width="small")
def manage_work_entry(conn, work_entry_row, start_date, end_date):
    """A single dialog for both editing and deleting a work entry, including new types."""
    entry_type_map = {
        "work": "Work", "holiday": "Holiday", "leave": "Leave", "half_day": "Half Day",
        "no_internet": "No Internet", "power_cut": "Power Cut", "other": "Other"
    }
    entry_types = list(entry_type_map.values())
    current_entry_type = entry_type_map.get(work_entry_row['entry_type'], "Work")

    try:
        default_index = entry_types.index(current_entry_type)
    except ValueError:
        default_index = 0

    # --- Edit Form ---
    with st.form(f"edit_entry_form_{work_entry_row['id']}"):
        st.subheader("Edit Entry Details")

        entry_type_selection = st.selectbox(
            "Entry Type",
            entry_types,
            index=default_index,
            key=f"entry_type_edit_{work_entry_row['id']}"
        )

        work_date = st.date_input(
            "Date",
            value=pd.to_datetime(work_entry_row['work_date']).date(),
            min_value=start_date,
            max_value=end_date
        )

        # Logic to display correct fields based on selected entry type
        if entry_type_selection == "Work":
            work_name = st.text_input("Work Title", value=work_entry_row.get('work_name', ''), placeholder="e.g., Developed login page")
            work_description = st.text_area("Description", value=work_entry_row.get('work_description', '') or '', placeholder="e.g., Implemented frontend and backend...")
            col1, col2 = st.columns(2)
            with col1:
                hours = st.number_input("Hours", min_value=0, max_value=8, value=int(float(work_entry_row.get('work_duration', 1.0))), step=1)
            with col2:
                minutes = st.number_input("Minutes", min_value=0, max_value=59, value=int((float(work_entry_row.get('work_duration', 1.0)) % 1) * 60), step=5)
            work_duration = hours + minutes / 60.0
            reason = None
        elif entry_type_selection == "Holiday":
            work_name = entry_type_selection
            work_description = None
            reason = st.text_input("Holiday Name", value=work_entry_row.get('reason', '') or '', placeholder="e.g., Independence Day")
            work_duration = 0.0
        elif entry_type_selection == "Leave":
            work_name = entry_type_selection
            work_description = None
            reason = st.text_area("Reason for Leave", value=work_entry_row.get('reason', '') or '', placeholder="e.g., Personal reason")
            work_duration = 0.0
        elif entry_type_selection == "Half Day":
            work_name = entry_type_selection
            work_description = None
            reason = st.text_area("Reason for Half Day", value=work_entry_row.get('reason', '') or '', placeholder="e.g., Doctor's appointment")
            work_duration = 0.0
        elif entry_type_selection in ("No Internet", "Power Cut"):
            work_name = entry_type_selection
            work_description = None
            reason = entry_type_selection
            st.text_input("Reason", value=entry_type_selection, disabled=True)
            col1, col2 = st.columns(2)
            with col1:
                hours = st.number_input("Downtime Hours", min_value=0, max_value=8, value=int(float(work_entry_row.get('work_duration', 1.0))), step=1)
            with col2:
                minutes = st.number_input("Downtime Minutes", min_value=0, max_value=59, value=int((float(work_entry_row.get('work_duration', 1.0)) % 1) * 60), step=1)
            work_duration = hours + minutes / 60.0
        elif entry_type_selection == "Other":
            work_name = entry_type_selection
            work_description = None
            reason = st.text_area("Reason", value=work_entry_row.get('reason', '') or '', placeholder="Please specify the reason for the downtime.")
            col1, col2 = st.columns(2)
            with col1:
                hours = st.number_input("Downtime Hours", min_value=0, max_value=8, value=int(float(work_entry_row.get('work_duration', 1.0))), step=1)
            with col2:
                minutes = st.number_input("Downtime Minutes", min_value=0, max_value=59, value=int((float(work_entry_row.get('work_duration', 1.0)) % 1) * 60), step=1)
            work_duration = hours + minutes / 60.0

        col1, col2 = st.columns([1.5, 1])
        with col1:
            submit_button = st.form_submit_button("💾 Update Entry", type="primary", use_container_width=True)
        with col2:
            delete_button = st.form_submit_button("🗑️ Delete Entry", type="secondary", use_container_width=True)

        if submit_button:
            is_valid = False
            if entry_type_selection == "Work":
                is_valid = work_name and work_name.strip()
            elif entry_type_selection in ("Holiday", "Leave", "Half Day", "Other"):
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
                st.toast("Entry deleted successfully.", icon="🗑️")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting entry: {e}")

@st.dialog("➕ Add New Entry", width="small")
def add_work_dialog(conn, timesheet_id, start_date, end_date):
    """Dialog for adding a new entry, including downtime reasons."""
    entry_options = ("Work", "Holiday", "Leave", "Half Day", "No Internet", "Power Cut", "Other")
    entry_type = st.selectbox("Entry Type", entry_options, key="entry_type_modal")

    default_date = st.session_state.get('last_selected_date', datetime.now(pytz.timezone('Asia/Kolkata')).date())
    with st.form("new_entry_form"):
        work_date = st.date_input("Date", value=default_date, min_value=start_date, max_value=end_date)

        # Initialize variables
        work_name = None
        work_description = None
        work_duration = 0.0
        reason = None

        if entry_type == "Work":
            work_name = st.text_input("Work Title", placeholder="e.g., Developed login page")
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
        elif entry_type in ("No Internet", "Power Cut"):
            work_name = entry_type
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
            # Validation Logic
            is_valid = False
            if entry_type == "Work":
                is_valid = work_name and work_name.strip()
            elif entry_type in ("Holiday", "Leave", "Half Day", "Other"):
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
                        "ts_id": timesheet_id, "w_date": work_date, "w_name": work_name.strip(),
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


# --- MODIFIED FUNCTION ---
@st.dialog("Weekly Timesheet Details", width="large")
def show_weekly_dialog(conn, user_id, username, week_start_date, is_manager=False):
    """Dialog for viewing weekly timesheet details with a dynamic horizontal layout."""
    week_end_date = week_start_date + timedelta(days=6)
    st.subheader(f"Week Summary for {username}", anchor=False)
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
    
    # **NEW**: Calculate downtime
    downtime_types = ['power_cut', 'no_internet', 'other']
    total_downtime = df[df['entry_type'].isin(downtime_types)]['work_duration'].sum()

    # --- UI Logic ---
    with st.container(border=True):
        display_items = []
        
        display_items.append({'type': 'status', 'label': 'Status', 'value': status_icon})
        
        if status in ['submitted', 'approved', 'rejected'] and pd.notna(submitted_at):
            display_items.append({'type': 'detail', 'label': 'Submitted To', 'person': manager_name, 'ts': submitted_at})
            
        if status in ['approved', 'rejected'] and pd.notna(reviewed_at):
            display_items.append({'type': 'detail', 'label': 'Reviewed By', 'person': manager_name, 'ts': reviewed_at})
        
        # **MODIFIED**: Added 'Downtime' to the list of metrics
        display_items.extend([
            {'type': 'metric', 'label': 'Logged', 'value': f"{total_logged:.2f} hrs", 'help': 'Total hours for all entry types.'},
            {'type': 'metric', 'label': 'Working', 'value': f"{total_working:.2f} hrs", 'help': 'Total hours logged as "work".'},
            {'type': 'metric', 'label': 'Downtime', 'value': f"{total_downtime:.2f} hrs", 'help': 'Total hours for power cuts, no internet, or other issues.'},
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

    st.divider()

    # Render the detailed grid of daily entries
    render_weekly_work_grid(conn, df, week_start_date, is_editable=False)

    if review_notes:
        st.warning(f"**Manager's Feedback:** {review_notes}", icon="⚠️")

    # Manager Actions (remains the same)
    if is_manager and status == 'submitted':
        with st.form("timesheet_action_form", border=False):
            action_col1, action_col2 = st.columns([1,1])
            
            if action_col1.form_submit_button("Approve", use_container_width=True, type="primary"):
                try:
                    # Your existing approval logic here...
                    st.success(f"Timesheet for {username} approved.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error approving timesheet: {e}")

            with action_col2:
                with st.popover("Request Revision", use_container_width=True):
                    notes = st.text_area(
                        "Reason for Rejection", 
                        placeholder="e.g., Please provide more detail for Wednesday's entry.",
                        key=f"reject_notes_{timesheet_id}"
                    )
                    if st.form_submit_button("Reject", use_container_width=True):
                        if not notes.strip():
                            st.warning("A reason for rejection is required.")
                        else:
                            try:
                                # Your existing rejection logic here...
                                st.success(f"Timesheet {timesheet_id} has been rejected.")
                                time.sleep(1)
                            except Exception as e:
                                st.error(f"Error rejecting timesheet: {e}")

###################################################################################################################################
##################################--------------- Pages----------------------------########################################
###################################################################################################################################


# --- Page Implementations ---
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
        st.info("Your timesheet has been returned. Please make the required changes and resubmit.", icon="ℹ️")
        st.warning(f"**Manager's Feedback:** {notes}", icon="⚠️")

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

    total_work_hours_month = sum(d.get('type_hours', {}).get('work', 0) for d in monthly_summary.values())
    leave_days_month = len([d for d in monthly_summary.values() if 'leave' in d.get('type_hours', {})])
    half_days_month = len([d for d in monthly_summary.values() if 'half_day' in d.get('type_hours', {})])
    working_days_month = len([d for d in monthly_summary.values() if d.get('type_hours', {}).get('work', 0) > 0])
    total_downtime_month = sum(d.get('type_hours', {}).get('power_cut', 0) + d.get('type_hours', {}).get('no_internet', 0) for d in monthly_summary.values())

    lifetime_stats = get_user_lifetime_stats(conn, user_id)
    total_work_hours_user = lifetime_stats['total_work_hours']
    leave_days_user = lifetime_stats['leave_days']
    half_days_user = lifetime_stats['half_days']

    with st.container():
        st.subheader(f"{calendar.month_name[selected_month]} {selected_year}", anchor=False)
        cols = st.columns(5, border=True)
        with cols[0]:
            st.metric("Working Days", working_days_month, delta=f"expected {expected_working_days}")
        with cols[1]:
            st.metric("Work Hours", f"{total_work_hours_month:.1f}", delta=f"expected {expected_working_hours:.1f}")
        with cols[2]:
            st.metric("Leave Days", leave_days_month)
        with cols[3]:
            st.metric("Half Days", half_days_month)
        with cols[4]:
            st.metric("Downtime", f"{total_downtime_month:.1f}h")

    with st.expander("Lifetime Statistics", expanded=False):
        cols = st.columns(3)
        with cols[0]:
            st.metric("Total Work Hours", f"{total_work_hours_user:.1f}")
        with cols[1]:
            st.metric("Total Leave Days", leave_days_user)
        with cols[2]:
            st.metric("Total Half Days", half_days_user)
    
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
                
                if disabled:
                    button_text = "No Data" if not has_timesheet else "Future"
                    st.button(button_text, key=f"week_btn_hist_{week_start_date}_disabled", use_container_width=True, disabled=True)
                else:
                    status_emoji = status_map.get(timesheet_status, '⚪️')
                    status_label = status_display.get(timesheet_status, "Unknown")
                    if st.button(f"{status_emoji} {status_label}", key=f"week_btn_hist_{week_start_date}", use_container_width=True):
                        st.session_state.show_week_details_for = week_start_date
                        st.rerun()

    if "show_week_details_for" not in st.session_state:
        st.session_state.show_week_details_for = None
        
    if st.session_state.show_week_details_for:
        show_weekly_dialog(conn, user_id, username, st.session_state.show_week_details_for, is_manager=False)
        st.session_state.show_week_details_for = None

def manager_dashboard(conn):
    st.subheader("📋 Manager Dashboard", anchor=False, divider="rainbow")
    
    # Check for and display alerts about late submissions
    late_submitters = get_late_submitters_for_manager(conn, st.session_state.user_id)
    if late_submitters:
        st.warning(f"**Pending Submissions:** The following users have not submitted their timesheet from last week: **{', '.join(late_submitters)}**.", icon="🔔")
    
    st.caption("Select a direct report to view their timesheets.")
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
            label_visibility="collapsed"
        )
    
    if not selected_user:
        st.info("Please select an employee to continue.")
        return

    user_info = users_df[users_df['username'] == selected_user].iloc[0]
    selected_user_id = user_info['id']
    
    available_years, month_by_year = get_available_months_years(conn, selected_user_id)
    
    if not available_years:
        st.info("No timesheet data available for this user.")
        return

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
        st.selectbox(
            "Year",
            options=available_years,
            key="selected_year_mgr",
            label_visibility="collapsed"
        )

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
        if date_obj.weekday() == 6:
            continue
        if date_obj in monthly_summary and monthly_summary[date_obj]['status'] == 'holiday':
            continue
        expected_working_days += 1
    expected_working_hours = expected_working_days * 8

    total_work_hours_month = sum(d.get('type_hours', {}).get('work', 0) for d in monthly_summary.values())
    leave_days_month = len([d for d in monthly_summary.values() if 'leave' in d.get('type_hours', {})])
    half_days_month = len([d for d in monthly_summary.values() if 'half_day' in d.get('type_hours', {})])
    working_days_month = len([d for d in monthly_summary.values() if d.get('type_hours', {}).get('work', 0) > 0])
    total_downtime_month = sum(d.get('type_hours', {}).get('power_cut', 0) + d.get('type_hours', {}).get('no_internet', 0) for d in monthly_summary.values())

    lifetime_stats = get_user_lifetime_stats(conn, selected_user_id)
    total_work_hours_user = lifetime_stats['total_work_hours']
    leave_days_user = lifetime_stats['leave_days']
    half_days_user = lifetime_stats['half_days']

    with st.container():
        st.subheader(f"{calendar.month_name[selected_month]} {selected_year}", anchor=False)
        cols = st.columns(5, border=True)
        with cols[0]:
            st.metric("Working Days", working_days_month, delta=f"expected {expected_working_days}")
        with cols[1]:
            st.metric("Work Hours", f"{total_work_hours_month:.1f}", delta=f"expected {expected_working_hours:.1f}")
        with cols[2]:
            st.metric("Leave Days", leave_days_month)
        with cols[3]:
            st.metric("Half Days", half_days_month)
        with cols[4]:
            st.metric("Downtime", f"{total_downtime_month:.1f}h")

    with st.expander("Lifetime Statistics", expanded=False):
        cols = st.columns(3)
        with cols[0]:
            st.metric("Total Work Hours", f"{total_work_hours_user:.1f}")
        with cols[1]:
            st.metric("Total Leave Days", leave_days_user)
        with cols[2]:
            st.metric("Total Half Days", half_days_user)
    
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
                
                if disabled:
                    button_text = "No Data" if not has_timesheet else "Future"
                    st.button(button_text, key=f"week_btn_mgr_{week_start_date}_disabled", use_container_width=True, disabled=True)
                else:
                    status_emoji = status_map.get(timesheet_status, '⚪️')
                    status_label = status_display.get(timesheet_status, "Unknown")
                    if st.button(f"{status_emoji} {status_label}", key=f"week_btn_mgr_{week_start_date}", use_container_width=True):
                        st.session_state.show_week_details_for = week_start_date
                        st.rerun()

    if "show_week_details_for" not in st.session_state:
        st.session_state.show_week_details_for = None
        
    if st.session_state.show_week_details_for:
        show_weekly_dialog(conn, selected_user_id, selected_user, st.session_state.show_week_details_for, is_manager=True)
        st.session_state.show_week_details_for = None


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
    
    available_years, month_by_year = get_available_months_years(conn, selected_user_id)
    
    if not available_years:
        st.info("No timesheet data available for this user.")
        return

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

    total_work_hours_month = sum(d.get('type_hours', {}).get('work', 0) for d in monthly_summary.values())
    leave_days_month = len([d for d in monthly_summary.values() if 'leave' in d.get('type_hours', {})])
    half_days_month = len([d for d in monthly_summary.values() if 'half_day' in d.get('type_hours', {})])
    working_days_month = len([d for d in monthly_summary.values() if d.get('type_hours', {}).get('work', 0) > 0])
    total_downtime_month = sum(d.get('type_hours', {}).get('power_cut', 0) + d.get('type_hours', {}).get('no_internet', 0) for d in monthly_summary.values())

    lifetime_stats = get_user_lifetime_stats(conn, selected_user_id)
    total_work_hours_user = lifetime_stats['total_work_hours']
    leave_days_user = lifetime_stats['leave_days']
    half_days_user = lifetime_stats['half_days']

    with st.container():
        st.subheader(f"{calendar.month_name[selected_month]} {selected_year}", anchor=False)
        cols = st.columns(5, border = True)
        with cols[0]:
            st.metric("Working Days", working_days_month, delta=f"expected {expected_working_days}")
        with cols[1]:
            st.metric("Work Hours", f"{total_work_hours_month:.1f}", delta=f"expected {expected_working_hours:.1f}")
        with cols[2]:
            st.metric("Leave Days", leave_days_month)
        with cols[3]:
            st.metric("Half Days", half_days_month)
        with cols[4]:
            st.metric("Downtime", f"{total_downtime_month:.1f}h")

    with st.expander("Lifetime Statistics", expanded=False):
        cols = st.columns(3)
        with cols[0]:
            st.metric("Total Work Hours", f"{total_work_hours_user:.1f}")
        with cols[1]:
            st.metric("Total Leave Days", leave_days_user)
        with cols[2]:
            st.metric("Total Half Days", half_days_user)
    
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
                
                if disabled:
                    button_text = "No Data" if not has_timesheet else "Future"
                    st.button(button_text, key=f"week_btn_{week_start_date}_disabled", use_container_width=True, disabled=True)
                else:
                    status_emoji = status_map.get(timesheet_status, '⚪️')
                    status_label = status_display.get(timesheet_status, "Unknown")
                    if st.button(f"{status_emoji} {status_label}", key=f"week_btn_{week_start_date}", use_container_width=True):
                        st.session_state.show_week_details_for = week_start_date
                        st.rerun()

    if "show_week_details_for" not in st.session_state:
        st.session_state.show_week_details_for = None
        
    if st.session_state.show_week_details_for:
        show_weekly_dialog(conn, selected_user_id, selected_user, st.session_state.show_week_details_for)
        st.session_state.show_week_details_for = None



###################################################################################################################################
##################################--------------- User Interface ----------------------------########################################
###################################################################################################################################

def inject_custom_css():
    st.markdown("""
        <style>
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

def render_work_entry(conn, work_row, is_editable, week_bounds):
    """Renders a single work entry with one 'Manage' button and new icons."""
    with st.container(border=True):
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            entry_type = work_row.get('entry_type', 'work')
            icon_map = {
                'holiday': '🏖️', 'leave': '🌴', 'half_day': '🌗',
                'no_internet': '🌐', 'power_cut': '🔌', 'other': '❓'
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
                    use_container_width=True,
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
##################################--------------- Main----------------------------########################################
###################################################################################################################################

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