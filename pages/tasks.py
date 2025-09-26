import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from sqlalchemy import text
import time
from constants import connect_db
import uuid



# --- Placeholder for User Authentication ---
if 'user_id' not in st.session_state:
    st.session_state.user_id = 1
    st.session_state.username = "employee_user"
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.role = "user"
    st.session_state.level = "worker"
    st.session_state.report_to = 1

# --- Activity Logging ---
def log_activity(conn, user_id, username, session_id, action, details):
    """Logs user activity to the database with error handling."""
    try:
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

# --- Helper Functions ---
def get_current_week_details():
    """Calculates current fiscal week and dates."""
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist).date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=5)
    fiscal_week = today.isocalendar()[1]
    return fiscal_week, start_of_week, end_of_week, today

def get_or_create_timesheet(conn, user_id, fiscal_week):
    """Fetches or creates a timesheet for the current week."""
    try:
        query_str = "SELECT id, status FROM timesheets WHERE user_id = :user_id AND fiscal_week = :fiscal_week"
        timesheet_df = conn.query(query_str, params={"user_id": user_id, "fiscal_week": fiscal_week}, ttl=0)
        
        if not timesheet_df.empty:
            return timesheet_df.iloc[0]['id'], timesheet_df.iloc[0]['status']
        
        manager_id = st.session_state.report_to
        with conn.session as s:
            s.execute(
                text("""
                    INSERT INTO timesheets (user_id, manager_id, fiscal_week, status)
                    VALUES (:user_id, :manager_id, :fiscal_week, 'draft')
                """),
                {"user_id": user_id, "manager_id": manager_id, "fiscal_week": fiscal_week}
            )
            result = s.execute(text("SELECT LAST_INSERT_ID()"))
            new_id = result.fetchone()[0]
            s.commit()
            log_activity(conn, st.session_state.user_id, st.session_state.username, 
                        st.session_state.session_id, "CREATE_TIMESHEET", 
                        f"Created new draft timesheet (ID: {new_id}) for week {fiscal_week}")
            return new_id, 'draft'
    except Exception as e:
        st.error(f"Error getting/creating timesheet: {e}")
        return None, None

def get_weekly_work(conn, timesheet_id):
    """Fetches work entries for a timesheet."""
    try:
        query_str = """
            SELECT id, work_date, work_name, work_description, work_duration 
            FROM work 
            WHERE timesheet_id = :timesheet_id 
            ORDER BY work_date ASC
        """
        df = conn.query(query_str, params={"timesheet_id": timesheet_id}, ttl=5)
        if not df.empty and 'work_date' in df.columns:
            df['work_date'] = pd.to_datetime(df['work_date']).dt.date
        return df
    except Exception as e:
        st.error(f"Error fetching work entries: {e}")
        return pd.DataFrame()

def can_submit_timesheet(conn, timesheet_id):
    """Checks if timesheet can be submitted (has entries and is draft)."""
    try:
        status_query = "SELECT status FROM timesheets WHERE id = :id"
        status_df = conn.query(status_query, params={"id": timesheet_id}, ttl=0)
        if status_df.empty or status_df.iloc[0]['status'] != 'draft':
            return False
        
        work_query = "SELECT COUNT(*) as count FROM work WHERE timesheet_id = :timesheet_id"
        work_count = conn.query(work_query, params={"timesheet_id": timesheet_id}, ttl=0)
        return work_count.iloc[0]['count'] > 0
    except Exception as e:
        st.error(f"Error checking submission eligibility: {e}")
        return False

def get_manager_name(conn, manager_id):
    """Fetches the manager's name from the userss table."""
    try:
        query = "SELECT username FROM userss WHERE id = :manager_id"
        result = conn.query(query, params={"manager_id": manager_id}, ttl=0)
        if not result.empty:
            return result.iloc[0]['username']
        return "Unknown Manager"
    except Exception as e:
        st.error(f"Error fetching manager name: {e}")
        return "Unknown Manager"

def submit_timesheet_for_approval(conn, timesheet_id):
    """Submits timesheet for approval."""
    try:
        with conn.session as s:
            s.execute(
                text("""
                    UPDATE timesheets 
                    SET status = 'submitted', submitted_at = NOW()
                    WHERE id = :id AND status = 'draft'
                """),
                {"id": timesheet_id}
            )
            s.commit()
        log_activity(conn, st.session_state.user_id, st.session_state.username, 
                    st.session_state.session_id, "SUBMIT_TIMESHEET", 
                    f"Submitted timesheet ID: {timesheet_id} to manager ID: {st.session_state.report_to}")
        st.session_state.timesheet_status = 'submitted'
        st.success("Timesheet submitted successfully to your manager! ✅")
        time.sleep(1)
    except Exception as e:
        st.error(f"Failed to submit timesheet: {e}")

# --- Dialogs ---
@st.dialog("➕ Add New Work Entry")
def add_work_dialog(conn, timesheet_id, start_date, end_date):
    """Dialog for adding new work entry with validation."""
    with st.form("new_work_form"):
        st.write("Fill in the details of the work you completed.")
        work_date = st.date_input(
            "Date of Work",
            value=datetime.now(pytz.timezone('Asia/Kolkata')).date(),
            min_value=start_date,
            max_value=end_date
        )
        work_name = st.text_input("Work Title / Task Name", max_chars=100, 
                                placeholder="e.g., Developed login page")
        work_description = st.text_area("Work Description", max_chars=500, 
                                     placeholder="e.g., Implemented frontend and backend for user authentication")
        work_duration = st.number_input("Time Taken (in hours)", min_value=0.25, 
                                      max_value=12.0, value=1.0, step=0.25)

        submitted = st.form_submit_button("Add Entry", type="primary")

        if submitted:
            if not work_name.strip():
                st.warning("Work Title cannot be empty.")
                return
            if work_duration <= 0:
                st.warning("Work duration must be greater than 0 hours.")
                return

            try:
                with conn.session as s:
                    s.execute(
                        text("""
                            INSERT INTO work (timesheet_id, work_date, work_name, work_description, work_duration)
                            VALUES (:ts_id, :w_date, :w_name, :w_desc, :w_dur)
                        """),
                        {
                            "ts_id": timesheet_id, 
                            "w_date": work_date, 
                            "w_name": work_name.strip(),
                            "w_desc": work_description.strip(),
                            "w_dur": work_duration
                        }
                    )
                    s.commit()
                log_activity(conn, st.session_state.user_id, st.session_state.username, 
                           st.session_state.session_id, "ADD_WORK", 
                           f"Added work '{work_name}' for {work_duration} hours")
                st.toast(f"Added '{work_name}' to your timesheet! 🎉")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error adding work entry: {e}")

@st.dialog("Confirm Submission")
def confirm_submission_dialog(conn, timesheet_id):
    """Dialog to confirm timesheet submission with manager info."""
    manager_name = get_manager_name(conn, st.session_state.report_to)
    st.warning(f"☠️ Are you sure you want to submit this timesheet to {manager_name} for approval? You won't be able to make changes after submitting.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, Submit", use_container_width=True, type="primary"):
            if can_submit_timesheet(conn, timesheet_id):
                submit_timesheet_for_approval(conn, timesheet_id)
                st.rerun()
            else:
                st.error("Cannot submit timesheet: Either no work entries exist or timesheet is already submitted.")
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()

@st.dialog("Reject Timesheet")
def reject_timesheet_dialog(conn, timesheet_id):
    """Dialog for rejecting a timesheet with notes."""
    with st.form("reject_timesheet_form"):
        st.write("Provide a reason for rejecting the timesheet.")
        review_notes = st.text_area("Rejection Reason", max_chars=500, placeholder="e.g., Incomplete work entries")
        submitted = st.form_submit_button("Reject", type="primary")

        if submitted:
            if not review_notes.strip():
                st.warning("Rejection reason cannot be empty.")
                return
            try:
                with conn.session as s:
                    s.execute(
                        text("""
                            UPDATE timesheets 
                            SET status = 'rejected', reviewed_at = NOW(), review_notes = :review_notes
                            WHERE id = :id AND status = 'submitted'
                        """),
                        {"id": timesheet_id, "review_notes": review_notes}
                    )
                    s.commit()
                log_activity(conn, st.session_state.user_id, st.session_state.username, 
                            st.session_state.session_id, "REJECT_TIMESHEET", 
                            f"Rejected timesheet ID: {timesheet_id} with reason: {review_notes}")
                st.success(f"Timesheet {timesheet_id} rejected!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Error rejecting timesheet: {e}")

# --- Manager Dashboard ---
def manager_dashboard(conn):
    """Displays timesheets assigned to the manager for review."""
    if st.session_state.level not in ['reporting_manager', 'both']:
        st.error("Access denied: You are not a reporting manager.")
        st.stop()

    st.subheader("📋 Manager Dashboard: Timesheet Approvals", anchor=False, divider="rainbow")
    
    query = """
        SELECT t.id, t.user_id, u.username, t.fiscal_week, t.status, t.submitted_at, t.review_notes
        FROM timesheets t
        JOIN userss u ON t.user_id = u.id
        WHERE t.manager_id = :manager_id AND t.status IN ('submitted', 'rejected')
        ORDER BY t.submitted_at DESC
    """
    timesheets_df = conn.query(query, params={"manager_id": st.session_state.user_id}, ttl=0)

    if timesheets_df.empty:
        st.info("No timesheets pending approval.")
        return

    for _, row in timesheets_df.iterrows():
        with st.expander(f"Timesheet ID: {row['id']} - {row['username']} (Week {row['fiscal_week']})"):
            st.write(f"**Submitted At**: {row['submitted_at']}")
            st.write(f"**Status**: {row['status'].upper()}")
            if row['review_notes']:
                st.write(f"**Review Notes**: {row['review_notes']}")

            work_df = get_weekly_work(conn, row['id'])
            if not work_df.empty:
                st.write("**Work Entries**:")
                for _, work_row in work_df.iterrows():
                    with st.container(border=True):
                        st.markdown(f"**{work_row['work_name']}**")
                        if work_row['work_description']:
                            st.caption(f"{work_row['work_description']}")
                        st.markdown(f"**Date**: {work_row['work_date']}")
                        st.markdown(f"**Hours**: {float(work_row['work_duration']):.2f}")
            else:
                st.write("_No work entries._")

            if row['status'] == 'submitted':
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Approve Timesheet {row['id']}", key=f"approve_{row['id']}", use_container_width=True):
                        try:
                            with conn.session as s:
                                s.execute(
                                    text("""
                                        UPDATE timesheets 
                                        SET status = 'approved', reviewed_at = NOW()
                                        WHERE id = :id AND status = 'submitted'
                                    """),
                                    {"id": row['id']}
                                )
                                s.commit()
                            log_activity(conn, st.session_state.user_id, st.session_state.username, 
                                        st.session_state.session_id, "APPROVE_TIMESHEET", 
                                        f"Approved timesheet ID: {row['id']}")
                            st.success(f"Timesheet {row['id']} approved!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error approving timesheet: {e}")
                with col2:
                    if st.button(f"Reject Timesheet {row['id']}", key=f"reject_{row['id']}", use_container_width=True):
                        reject_timesheet_dialog(conn, row['id'])

# --- Main Application Page ---
def timesheet_page():
    """Renders the main timesheet page UI and logic."""
    st.set_page_config(layout="wide", page_title="My Timesheet")

    st.markdown("""
    <style>
        .main > div {
            padding-top: 0px !important;
        }
        .block-container {
            padding-top: 30px !important;
        }
        .stMetric > div > div > div {
            padding: 1rem;
            border-radius: 10px;
            background-color: #f0f2f6;
            text-align: center;
        }
        .stMetric > div > div > div > div {
            font-size: 1.5rem;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

    if 'user_id' not in st.session_state:
        st.warning("Please log in to view your timesheet.")
        st.stop()

    page = st.sidebar.selectbox("Select Page", ["My Timesheet", "Manager Dashboard"] if st.session_state.level in ['reporting_manager', 'both'] else ["My Timesheet"])

    conn = connect_db()
    if page == "Manager Dashboard":
        manager_dashboard(conn)
    else:
        st.subheader("📝 My Weekly Timesheet", anchor=False, divider="rainbow")
        fiscal_week, start_of_week, end_of_week, today = get_current_week_details()
        timesheet_id, timesheet_status = get_or_create_timesheet(conn, st.session_state.user_id, fiscal_week)
        
        if timesheet_id is None:
            st.error("Failed to load timesheet. Please try again.")
            st.stop()

        if 'timesheet_status' not in st.session_state:
            st.session_state.timesheet_status = timesheet_status

        col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
        with col1:
            start_month = start_of_week.strftime('%b')
            end_month = end_of_week.strftime('%b')
            date_range_str = f"{start_of_week.strftime('%b %d')} - {end_of_week.strftime('%d, %Y')}" if start_month == end_month else f"{start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')}"
            status_color = "🟢" if st.session_state.timesheet_status == "approved" else "🟠" if st.session_state.timesheet_status == "submitted" else "🟠"
            st.markdown(
                f"""
                <div style="
                    padding:5px 1px;
                    border-radius:999px;
                    font-size:1.2rem;
                    letter-spacing:0.3px;">
                    <b>Week {fiscal_week}</b> · {date_range_str} · {status_color} {st.session_state.timesheet_status.upper()}
                </div>
                """,
                unsafe_allow_html=True,
            )

        is_draft = st.session_state.timesheet_status == 'draft'
        with col2:
            if st.button("➕ Add Work", use_container_width=True, disabled=not is_draft, 
                        help="Add a new work entry for this week"):
                add_work_dialog(conn, timesheet_id, start_of_week, end_of_week)

        with col3:
            if st.button("✔️ Submit for Approval", type="primary", use_container_width=True, 
                        disabled=not is_draft or not can_submit_timesheet(conn, timesheet_id), 
                        help="You can only submit a draft timesheet with work entries"):
                confirm_submission_dialog(conn, timesheet_id)

        st.markdown("---")

        work_df = get_weekly_work(conn, timesheet_id)
        days_of_week = [(start_of_week + timedelta(days=i)) for i in range(6)]
        cols = st.columns(6)
        total_weekly_hours = 0

        for i, day_date in enumerate(days_of_week):
            with cols[i]:
                st.subheader(f"{day_date.strftime('%A')}", anchor=False)
                st.caption(f"{day_date.strftime('%d %b')}")
                
                day_work_df = work_df[work_df['work_date'] == day_date]
                total_day_hours = 0

                if not day_work_df.empty:
                    for _, row in day_work_df.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{row['work_name']}**")
                            if row['work_description']:
                                st.caption(f"{row['work_description']}")
                            st.markdown(f"**`{float(row['work_duration']):.2f} hrs`**")
                            total_day_hours += row['work_duration']
                    
                    st.markdown(f"**Total: `{float(total_day_hours):.2f} hrs`**")
                    total_weekly_hours += total_day_hours
                else:
                    st.write("_No work logged._")
        
        st.markdown("---")
        st.metric("**Total Weekly Hours**", f"{float(total_weekly_hours):.2f} Hours")

if __name__ == "__main__":
    timesheet_page()