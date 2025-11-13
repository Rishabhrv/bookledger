import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date, time as dt_time
import calendar
from sqlalchemy import text
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict
import re
from auth import validate_token
from constants import log_activity, initialize_click_and_session_id, connect_db


# Page Configuration
st.set_page_config(page_title="Attendance Management", page_icon="📅", layout="wide")

st.markdown("""
    <style>
            
        /* Remove Streamlit's default top padding */
        .main > div {
            padding-top: 0px !important;
        }
        /* Ensure the first element has minimal spacing */
        .block-container {
            padding-top: 10px !important;  /* Small padding for breathing room */
        }
            """, unsafe_allow_html=True)

def connect_db_attendance():
    try:
        # Use st.cache_resource to only connect once
        @st.cache_resource
        def get_connection():
            return st.connection('attendance', type='sql')
        conn = get_connection()
        return conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()


validate_token()
initialize_click_and_session_id()

user_role = st.session_state.get("role", None)
user_app = st.session_state.get("app", None)
user_access = st.session_state.get("access", None)
session_id = st.session_state.session_id
click_id = st.session_state.get("click_id", None)


if user_role != 'admin' and not (
    user_role == 'user' and 
    user_app == 'main' and 
    'Attendance' in user_access 
):
    st.error("⚠️ Access Denied: You don't have permission to access this page.")
    st.stop()

# Initialize session state for new visitors
if "visited" not in st.session_state:
    st.session_state.visited = False

# Check if the user is new
if not st.session_state.visited:
    st.cache_data.clear()  # Clear cache for new visitors
    st.session_state.visited = True  # Mark as visited

conn = connect_db_attendance()
conn_log = connect_db()


# Initialize logged_click_ids if not present
if "logged_click_ids" not in st.session_state:
    st.session_state.logged_click_ids = set()

# Log navigation if click_id is present and not already logged
if click_id and click_id not in st.session_state.logged_click_ids:
    try:
        log_activity(
            conn_log,
            st.session_state.user_id,
            st.session_state.username,
            st.session_state.session_id,
            "navigated to page",
            f"Page: Attendance Log"
        )
        st.session_state.logged_click_ids.add(click_id)
    except Exception as e:
        st.error(f"Error logging navigation: {str(e)}")



# --- Attendance Logic Constants ---
SCHEDULED_IN = dt_time(9, 30)
SCHEDULED_OUT = dt_time(18, 0)
LATE_THRESHOLD = (datetime.combine(date.min, SCHEDULED_IN) + timedelta(minutes=5)).time()
EARLY_ARRIVAL_THRESHOLD = (datetime.combine(date.min, SCHEDULED_IN) - timedelta(minutes=8)).time()
OVERTIME_THRESHOLD = (datetime.combine(date.min, SCHEDULED_OUT) + timedelta(minutes=10)).time()


# Custom CSS for better UI
st.markdown("""
<style>
    .block-container {
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 100%;
    }
    
    /* Modern Calendar styling */
    .calendar-container {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin: 1rem 0;
    }
    
    
    .calendar-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 8px;
    }
    
    .calendar-table th {
        padding: 12px;
        background: #f8f9fa;
        font-weight: 600;
        color: #495057;
        border-radius: 8px;
        text-align: center;
    }
    
    .calendar-day {
        padding: 12px;
        border-radius: 10px;
        text-align: center;
        min-height: 90px;
        vertical-align: top;
        background: #f8f9fa;
        border: 2px solid #e9ecef;
        transition: all 0.3s;
        position: relative;
    }
    
    .calendar-day:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    .day-number {
        font-size: 1.1rem;
        font-weight: bold;
        color: #495057;
        margin-bottom: 8px;
    }
    
    .day-info {
        font-size: 0.75rem;
        line-height: 1.4;
        color: #6c757d;
    }
    
    .time-badge {
        display: inline-block;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.7rem;
        margin: 2px 0;
        font-weight: 500;
    }
    
    /* Status colors - Subtle refined version */
    /* Status colors - Balanced subtlety */
    .status-present {
        background: linear-gradient(135deg, #e8f5e8 0%, #d4edd4 100%);
        border: 1px solid #5cb85c !important;
    }

    .status-overtime {
        background: linear-gradient(135deg, #f0f8ff 0%, #e0f0ff 100%);
        border: 1px solid #4a86e8 !important;
    }

    .status-half-day {
        background: linear-gradient(135deg, #fff8e0 0%, #ffefbf 100%);
        border: 1px solid #e6b400 !important;
    }

    .status-leave {
        background: linear-gradient(135deg, #fde8e8 0%, #f9d6d6 100%);
        border: 1px solid #e05c5c !important;
    }

    .status-holiday {
        background: linear-gradient(135deg, #f0ebfa 0%, #e6ddf7 100%);
        border: 1px solid #8a6dc7 !important;
    }

    .status-late {
        background: linear-gradient(135deg, #ffefe0 0%, #ffe4cc 100%);
        border: 1px solid #e67e22 !important;
    }

    .status-early-out {
        background: linear-gradient(135deg, #f7e8fa 0%, #f2ddf7 100%);
        border: 1px solid #c669d1 !important;
    }
    
    .status-early-arrival {
        background: linear-gradient(135deg, #e0f7ff 0%, #ccefff 100%);
        border: 1px solid #3498db !important;
    }
    
    /* Legend */
    .legend-container {
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
        margin: 1rem 0;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 10px;
    }
    
    .legend-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.85rem;
    }
    
    .legend-box {
        width: 20px;
        height: 20px;
        border-radius: 4px;
        border: 2px solid;
    }
    
    
    /* Multi-month container */
    .year-calendar-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        margin-top: 1rem;
    }
    
    .month-card {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .month-mini-calendar {
        width: 100%;
        border-collapse: separate;
        border-spacing: 4px;
    }
    
    .month-mini-calendar th {
        padding: 6px;
        background: #f8f9fa;
        font-size: 0.7rem;
        font-weight: 600;
        color: #495057;
        border-radius: 4px;
    }
    
    .mini-day {
        padding: 8px;
        border-radius: 6px;
        text-align: center;
        font-size: 0.8rem;
        min-height: 35px;
        background: #f8f9fa;
        border: 1px solid #e9ecef;
    }
</style>
""", unsafe_allow_html=True)


def get_all_employees(conn):
    """Fetch all active employees"""
    try:
        with conn.session as s:
            result = s.execute(text("SELECT employee_id, employee_name, designation FROM employees WHERE employment_status = 'Active' ORDER BY employee_name"))
            return result.fetchall()
    except Exception as e:
        st.error(f"Error fetching employees: {e}")
        return []

def get_all_employees_with_status(conn):
    """Fetch all employees with their employment status"""
    try:
        with conn.session as s:
            result = s.execute(text("SELECT employee_id, employee_code, employee_name, designation, employment_status FROM employees ORDER BY employment_status = 'Active' DESC, employee_name"))
            return result.fetchall()
    except Exception as e:
        st.error(f"Error fetching employees: {e}")
        return []

def update_employee_status(conn, employee_id, status):
    """Update an employee's employment status"""
    try:
        with conn.session as s:
            s.execute(text("""
                UPDATE employees 
                SET employment_status = :status 
                WHERE employee_id = :emp_id
            """), {"status": status, "emp_id": employee_id})
            s.commit()
        return True
    except Exception as e:
        st.error(f"Error updating employee status: {e}")
        return False

def update_employee(conn, emp_id, details):
    """Update employee details."""
    try:
        with conn.session as s:
            s.execute(text("""
                UPDATE employees 
                SET 
                    employee_name = :name,
                    designation = :dept,
                    employment_status = :status
                WHERE employee_id = :emp_id
            """), {
                "name": details['employee_name'],
                "dept": details['designation'],
                "status": details['employment_status'],
                "emp_id": emp_id
            })
            s.commit()
        return True
    except Exception as e:
        st.error(f"Error updating employee {details['employee_name']}: {e}")
        return False
    
    
def get_employee_full_year_attendance(conn, employee_id, year):
    """Get full year attendance data for all months"""
    try:
        with conn.session as s:
            result = s.execute(text("""
                SELECT attendance_date, check_in_time, check_out_time, status, notes
                FROM attendance
                WHERE employee_id = :emp_id AND YEAR(attendance_date) = :year
                ORDER BY attendance_date
            """), {"emp_id": employee_id, "year": year})
            return result.fetchall()
    except Exception as e:
        st.error(f"Error fetching year attendance: {e}")
        return []
    

def get_employee_monthly_attendance(conn, employee_id, year, month):
    """Get monthly attendance for an employee, including exception flags"""
    try:
        with conn.session as s:
            result = s.execute(text("""
                SELECT 
                    attendance_date, 
                    check_in_time, 
                    check_out_time, 
                    status, 
                    notes,
                    CASE 
                        WHEN check_in_time IS NOT NULL 
                        AND check_in_time > :late_threshold 
                        THEN 1 ELSE 0 
                    END as is_late,
                    CASE 
                        WHEN check_out_time IS NOT NULL 
                        AND check_out_time < :scheduled_out 
                        THEN 1 ELSE 0 
                    END as is_early,
                    CASE 
                        WHEN check_out_time IS NOT NULL 
                        AND check_out_time > :overtime_threshold 
                        THEN 1 ELSE 0 
                    END as is_overtime,
                    CASE
                        WHEN check_in_time IS NOT NULL
                        AND check_in_time < :early_arrival_threshold
                        THEN 1 ELSE 0
                    END as is_early_arrival
                FROM attendance
                WHERE employee_id = :emp_id 
                AND YEAR(attendance_date) = :year 
                AND MONTH(attendance_date) = :month
                ORDER BY attendance_date
            """), {
                "emp_id": employee_id, 
                "year": year, 
                "month": month,
                "late_threshold": LATE_THRESHOLD,
                "scheduled_out": SCHEDULED_OUT,
                "overtime_threshold": OVERTIME_THRESHOLD,
                "early_arrival_threshold": EARLY_ARRIVAL_THRESHOLD
            })
            return result.fetchall()
    except Exception as e:
        st.error(f"Error fetching monthly attendance: {e}")
        return [] 
    

def mark_attendance(conn, employee_id, attendance_date, check_in, check_out, status, notes):
    """Mark or update attendance for an employee"""
    try:
        with conn.session as s:
            s.execute(text("""
                INSERT INTO attendance (employee_id, attendance_date, check_in_time, check_out_time, status, notes)
                VALUES (:emp_id, :att_date, :check_in, :check_out, :status, :notes)
                ON DUPLICATE KEY UPDATE 
                    check_in_time = :check_in,
                    check_out_time = :check_out,
                    status = :status,
                    notes = :notes
            """), {
                "emp_id": employee_id,
                "att_date": attendance_date,
                "check_in": check_in,
                "check_out": check_out,
                "status": status,
                "notes": notes
            })
            s.commit()
        return True
    except Exception as e:
        st.error(f"Error marking attendance: {e}")
        return False


# Add this new function to calculate working days
def get_month_working_days(conn, year, month):
    """Calculate total working days in a month excluding Sundays and holidays"""
    try:
        # Get first and last day of the month
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        
        # Get holidays from holidays table
        with conn.session as s:
            holidays = s.execute(text("""
                SELECT holiday_date
                FROM holidays
                WHERE YEAR(holiday_date) = :year
                AND MONTH(holiday_date) = :month
            """), {"year": year, "month": month}).fetchall()
        
        holiday_dates = {h[0] for h in holidays}
        
        # Count working days (excluding Sundays and holidays)
        working_days = 0
        current_day = first_day
        while current_day <= last_day:
            # Check if day is not Sunday (weekday() == 6) and not a holiday
            if current_day.weekday() != 6 and current_day not in holiday_dates:
                working_days += 1
            current_day += timedelta(days=1)
        
        return working_days
    except Exception as e:
        st.error(f"Error calculating working days: {e}")
        return 0
    
def get_all_available_years(conn):
    """Get distinct years from attendance data, ordered by most recent"""
    try:
        with conn.session as s:
            result = s.execute(text("""
                SELECT DISTINCT YEAR(attendance_date) as year
                FROM attendance
                ORDER BY year DESC
            """))
            years = [row[0] for row in result.fetchall()]
            return years
    except Exception as e:
        st.error(f"Error fetching available years: {e}")
        return []

def get_all_available_months_for_year(conn, year):
    """Get distinct months for a given year from attendance data, ordered by most recent"""
    try:
        with conn.session as s:
            result = s.execute(text("""
                SELECT DISTINCT MONTH(attendance_date) as month
                FROM attendance
                WHERE YEAR(attendance_date) = :year
                ORDER BY month DESC
            """), {"year": year})
            months = [row[0] for row in result.fetchall()]
            return months
    except Exception as e:
        st.error(f"Error fetching available months: {e}")
        return []
    
# Existing working days functions
def get_year_working_days(conn, year):
    """Calculate total working days in a year excluding Sundays and holidays"""
    try:
        first_day = date(year, 1, 1)
        last_day = date(year, 12, 31)
        with conn.session as s:
            holidays = s.execute(text("""
                SELECT holiday_date
                FROM holidays
                WHERE YEAR(holiday_date) = :year
            """), {"year": year}).fetchall()
        holiday_dates = {h[0] for h in holidays}
        working_days = 0
        current_day = first_day
        while current_day <= last_day:
            if current_day.weekday() != 6 and current_day not in holiday_dates:
                working_days += 1
            current_day += timedelta(days=1)
        return working_days
    except Exception as e:
        st.error(f"Error calculating working days: {e}")
        return 0

# Updated function for Team Insights
def get_all_employees_attendance(conn, year, month=None):
    """Fetch attendance data for all active employees"""
    try:
        with conn.session as s:
            if month:
                result = s.execute(text("""
                    SELECT e.employee_id, e.employee_name, e.designation,
                           a.attendance_date, a.check_in_time, a.check_out_time, a.status
                    FROM employees e
                    LEFT JOIN attendance a ON e.employee_id = a.employee_id
                    WHERE e.employment_status = 'Active'
                    AND (a.attendance_date IS NULL OR 
                         (YEAR(a.attendance_date) = :year AND MONTH(a.attendance_date) = :month))
                    ORDER BY e.employee_id, a.attendance_date
                """), {"year": year, "month": month})
            else:
                result = s.execute(text("""
                    SELECT e.employee_id, e.employee_name, e.designation,
                           a.attendance_date, a.check_in_time, a.check_out_time, a.status
                    FROM employees e
                    LEFT JOIN attendance a ON e.employee_id = a.employee_id
                    WHERE e.employment_status = 'Active'
                    AND (a.attendance_date IS NULL OR YEAR(a.attendance_date) = :year)
                    ORDER BY e.employee_id, a.attendance_date
                """), {"year": year})
            rows = result.fetchall()
            return rows
    except Exception as e:
        st.error(f"Error fetching team attendance: {e}")
        return []

def get_employee_yearly_attendance(conn, employee_id, year):
    """Get yearly attendance statistics"""
    try:
        with conn.session as s:
            result = s.execute(text("""
                SELECT 
                    COUNT(*) as total_days,
                    SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present_days,
                    SUM(CASE WHEN status = 'Half Day' THEN 1 ELSE 0 END) as half_days,
                    SUM(CASE WHEN status = 'Leave' THEN 1 ELSE 0 END) as leave_days,
                    SUM(CASE WHEN status = 'Holiday' THEN 1 ELSE 0 END) as holidays
                FROM attendance
                WHERE employee_id = :emp_id AND YEAR(attendance_date) = :year
            """), {"emp_id": employee_id, "year": year})
            return result.fetchone()
    except Exception as e:
        st.error(f"Error fetching yearly attendance: {e}")
        return None

def get_employee_available_years(conn, employee_id):
    """Get distinct years from attendance data for a specific employee, ordered by most recent"""
    try:
        with conn.session as s:
            result = s.execute(text("""
                SELECT DISTINCT YEAR(attendance_date) as year
                FROM attendance
                WHERE employee_id = :emp_id
                ORDER BY year DESC
            """), {"emp_id": employee_id})
            years = [row[0] for row in result.fetchall()]
            return years
    except Exception as e:
        st.error(f"Error fetching available years: {e}")
        return []

def get_available_months_for_year(conn, employee_id, year):
    """Get distinct months for a given year from attendance data, ordered by most recent"""
    try:
        with conn.session as s:
            result = s.execute(text("""
                SELECT DISTINCT MONTH(attendance_date) as month
                FROM attendance
                WHERE employee_id = :emp_id AND YEAR(attendance_date) = :year
                ORDER BY month DESC
            """), {"emp_id": employee_id, "year": year})
            months = [row[0] for row in result.fetchall()]
            return months
    except Exception as e:
        st.error(f"Error fetching available months: {e}")
        return []


def get_daily_attendance(conn, attendance_date):
    """Get attendance for all employees on a specific date, including exception flags"""
    try:
        with conn.session as s:
            result = s.execute(text("""
                SELECT 
                    e.employee_name,
                    e.designation,
                    COALESCE(a.check_in_time, '-') as check_in,
                    COALESCE(a.check_out_time, '-') as check_out,
                    COALESCE(a.status, 'Absent') as status,
                    COALESCE(a.notes, '') as notes,
                    CASE 
                        WHEN a.check_in_time IS NOT NULL 
                        AND a.check_in_time > :late_threshold 
                        THEN 1 ELSE 0 
                    END as is_late,
                    CASE 
                        WHEN a.check_out_time IS NOT NULL 
                        AND a.check_out_time < :scheduled_out 
                        THEN 1 ELSE 0 
                    END as is_early,
                    CASE 
                        WHEN a.check_out_time IS NOT NULL 
                        AND a.check_out_time > :overtime_threshold 
                        THEN 1 ELSE 0 
                    END as is_overtime,
                    CASE
                        WHEN a.check_in_time IS NOT NULL
                        AND a.check_in_time < :early_arrival_threshold
                        THEN 1 ELSE 0
                    END as is_early_arrival
                FROM employees e
                LEFT JOIN attendance a ON e.employee_id = a.employee_id 
                    AND a.attendance_date = :att_date
                WHERE e.employment_status = 'Active'
                ORDER BY e.employee_name
            """), {
                "att_date": attendance_date,
                "late_threshold": LATE_THRESHOLD,
                "scheduled_out": SCHEDULED_OUT,
                "overtime_threshold": OVERTIME_THRESHOLD,
                "early_arrival_threshold": EARLY_ARRIVAL_THRESHOLD
            })
            return result.fetchall()
    except Exception as e:
        st.error(f"Error fetching daily attendance: {e}")
        return []

def determine_day_status(status, check_in_time, check_out_time):
    """Determine the visual status of a day based on attendance data"""
    if status == 'Holiday':
        return 'status-holiday', '🏖️ Holiday'
    elif status == 'Leave':
        return 'status-leave', '❌ Leave'
    elif status == 'Half Day':
        return 'status-half-day', '🕐 Half Day'
    elif status == 'Absent':
        return 'status-absent', '❌ Absent'
    elif status == 'Present':
        # Convert timedelta to time if needed
        if check_in_time:
            if isinstance(check_in_time, timedelta):
                total_seconds = int(check_in_time.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                check_in_time = dt_time(hours, minutes)
        
        if check_out_time:
            if isinstance(check_out_time, timedelta):
                total_seconds = int(check_out_time.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                check_out_time = dt_time(hours, minutes)
        
        is_early_arrival = check_in_time and check_in_time < EARLY_ARRIVAL_THRESHOLD
        is_late = check_in_time and check_in_time > LATE_THRESHOLD
        is_early_out = check_out_time and check_out_time < SCHEDULED_OUT
        is_overtime = check_out_time and check_out_time > OVERTIME_THRESHOLD
        
        if is_early_arrival:
            return 'status-early-arrival', '🌅 Early Arrival'
        elif is_late and is_early_out:
            return 'status-early-out', '⚠️ Late + Early'
        elif is_late:
            return 'status-late', '⏰ Late Arrival'
        elif is_early_out:
            return 'status-early-out', '🏃 Early Exit'
        elif is_overtime:
            return 'status-overtime', '🌙 Overtime'
        else:
            return 'status-present', '✅ On Time'
    
    return '', ''

def inject_custom_css():
    """Inject custom CSS for *calendar styling only*"""
    st.markdown("""
        <style>
            .day-card {
                padding: 10px;
                border-radius: 10px;
                border: 2px solid #e0e0e0;
                height: 165px;
                display: flex;
                flex-direction: column;
                margin-bottom: 10px;
                transition: all 0.3s ease;
                background: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                overflow: hidden;
            }
            .day-card-container {
                max-width: 95%;
                margin: 0 auto;
            }
            .day-card:hover {
                box-shadow: 0 6px 16px rgba(0,0,0,0.12);
                transform: translateY(-3px);
            }
            .day-card-present { 
                background: linear-gradient(135deg, #D4EDDA 0%, #C3E6CB 100%); 
                border-color: #28a745; 
            }
            .day-card-late { 
                background: linear-gradient(135deg, #FFE5D0 0%, #FFDCC5 100%); 
                border-color: #fd7e14; 
            }
            .day-card-early-out { 
                background: linear-gradient(135deg, #F8E6FF 0%, #F0D9FF 100%); 
                border-color: #e83e8c; 
            }
            .day-card-half-day { 
                background: linear-gradient(135deg, #FFF3CD 0%, #FFEAA7 100%); 
                border-color: #ffc107; 
            }
            .day-card-leave { 
                background: linear-gradient(135deg, #F8D7DA 0%, #F5C6CB 100%); 
                border-color: #dc3545; 
            }
            .day-card-holiday { 
                background: linear-gradient(135deg, #E2D9F3 0%, #D6C9EB 100%); 
                border-color: #6f42c1; 
            }
            .day-card-absent { 
                background: linear-gradient(135deg, #F8D7DA 0%, #F5C6CB 100%); 
                border-color: #dc3545; 
            }
            .day-card-empty { 
                background: linear-gradient(135deg, #FAFAFA 0%, #F5F5F5 100%); 
                border-style: dashed;
                border-color: #d0d0d0;
            }

            .day-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding-bottom: 6px;
                margin-bottom: 8px;
                border-bottom: 1.5px solid rgba(0,0,0,0.08);
                flex-shrink: 0;
            }
            .day-number { 
                font-weight: 700; 
                font-size: 1.5em; 
                line-height: 1;
                color: #2c3e50;
            }
            .day-name { 
                font-size: 0.75em; 
                color: #7f8c8d; 
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.4px;
            }
            
            .day-summary { 
                font-size: 0.78em; 
                line-height: 1.45;
                flex-grow: 1;
                display: flex;
                flex-direction: column;
                gap: 5px;
                overflow: hidden;
            }
            
            .time-container {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 6px;
                margin: 5px 0;
                padding: 6px;
                background: rgba(255,255,255,0.5);
                border-radius: 6px;
            }
            .time-block {
                text-align: center;
                padding: 3px;
            }
            .time-label {
                font-size: 0.62em;
                font-weight: 700;
                color: #7f8c8d;
                display: block;
                text-transform: uppercase;
                letter-spacing: 0.3px;
                margin-bottom: 2px;
            }
            .time-value {
                font-size: 1.2em;
                font-weight: 700;
                color: #2c3e50;
                display: block;
            }
            .exception-container {
                display: flex;
                flex-wrap: wrap;
                gap: 4px;
                margin-top: 4px;
            }
            .day-summary .exception {
                display: inline-flex;
                align-items: center;
                gap: 2px;
                padding: 3px 6px;
                border-radius: 5px;
                font-size: 0.9em;
                font-weight: 600;
                color: white;
                white-space: nowrap;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            .exception-early-in-bg { 
                background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); 
            }
            .exception-late-in-bg { 
                background: linear-gradient(135deg, #e67e22 0%, #d35400 100%); 
            }
            .exception-early-out-bg { 
                background: linear-gradient(135deg, #c669d1 0%, #a855b8 100%); 
            }
            .exception-overtime-bg { 
                background: linear-gradient(135deg, #27ae60 0%, #229954 100%); 
            }

            .header-card {
                padding: 8px;
                font-weight: 700;
                font-size: 0.7rem;
                text-align: center;
                color: #2c3e50;
                margin-bottom: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 0.8px;
                border-bottom: 3px solid #3498db;
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                border-radius: 8px 8px 0 0;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 38px;
            }
        </style>
    """, unsafe_allow_html=True)

def calculate_time_diff_for_cards(time_str, reference_time, diff_type):
    """
    Calculate time difference and return formatted string for cards
    diff_type: 'late', 'early', 'overtime', or 'early_arrival'
    """
    if pd.isna(time_str) or time_str == '-' or time_str == '' or time_str is None:
        return ''
    
    try:
        # Parse the time string
        if isinstance(time_str, str):
            actual_time = pd.to_datetime(time_str).time()
        else:
            actual_time = time_str
        
        # Convert to datetime for calculation
        ref_datetime = datetime.combine(date.today(), reference_time)
        actual_datetime = datetime.combine(date.today(), actual_time)
        
        # Calculate difference in minutes
        diff = (actual_datetime - ref_datetime).total_seconds() / 60
        
        if diff_type == 'late' and diff > 0:
            hours = int(diff // 60)
            mins = int(diff % 60)
            if hours > 0:
                return f"+{hours}h {mins}m"
            else:
                return f"+{mins}m"

        elif diff_type == 'early_arrival' and diff < 0:
            diff = abs(diff)
            hours = int(diff // 60)
            mins = int(diff % 60)
            if hours > 0:
                return f"-{hours}h {mins}m"
            else:
                return f"-{mins}m"
                
        elif diff_type == 'early' and diff < 0:
            diff = abs(diff)
            hours = int(diff // 60)
            mins = int(diff % 60)
            if hours > 0:
                return f"-{hours}h {mins}m"
            else:
                return f"-{mins}m"
                
        elif diff_type == 'overtime' and diff > 0:
            hours = int(diff // 60)
            mins = int(diff % 60)
            if hours > 0:
                return f"+{hours}h {mins}m"
            else:
                return f"+{mins}m"
        
        return ''
    except Exception as e:
        return ''


def render_daily_report_table(df_display):
    """
    Renders a custom, self-contained HTML table for the daily attendance report.
    
    This redesigned version (v3) uses a "Google" design philosophy:
    - Merges exceptions (Late, OT, etc.) *inline* with the Check In/Out times.
    - Uses subtle, professional exception badges (light background, colored text).
    - Ensures consistent row height and vertical alignment for a cleaner UI.
    - Prioritizes information hierarchy (time is primary, exception is secondary).
    """
    
    # --- 🎨 UPGRADED CSS STYLES ---
    table_css = """
    <style>
        .daily-report-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0 4px; /* Reduced from 8px to make rows closer */
            margin-top: 1rem; /* Slightly reduced margin */
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }

        /* --- ✨ Modern Header --- */
        .daily-report-table th {
            background: #f8f9fa;
            color: #495057;
            padding: 8px 12px; /* Reduced padding from 10px 14px */
            text-align: left;
            font-weight: 600;
            border: none;
            position: sticky;
            top: 0;
            z-index: 1;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 0.7rem; /* Reduced from 0.75rem */
            border-bottom: 1px solid #e9ecef; /* Thinner border */
        }

        .daily-report-table th:first-child { border-top-left-radius: 6px; } /* Smaller radius */
        .daily-report-table th:last-child { border-top-right-radius: 6px; }

        /* --- 🖌️ Modern Table Body --- */
        .daily-report-table td {
            background-color: #ffffff;
            padding: 8px 10px; /* Reduced from 12px 14px */
            border: 1px solid #e9ecef;
            vertical-align: middle;
            box-shadow: 0 1px 1px rgba(0,0,0,0.03); /* Lighter shadow */
            font-size: 0.75rem; /* Reduced from 0.825rem */
            color: #212529;
        }

        .daily-report-table tbody tr {
            transition: all 0.15s ease-in-out;
            border-radius: 6px; /* Smaller radius */
        }

        /* --- 💡 Subtle Hover Effect --- */
        .daily-report-table tbody tr:hover td {
            background-color: #f9fafb;
        }
        
        .daily-report-table tbody tr:hover {
            box-shadow: 0 2px 6px rgba(0,0,0,0.05); /* Slightly lighter shadow */
        }

        .daily-report-table tbody tr td:first-child {
            border-top-left-radius: 6px;
            border-bottom-left-radius: 6px;
        }

        .daily-report-table tbody tr td:last-child {
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
        }

        /* --- 🏷️ Status Badges --- */
        .status-badge {
            display: inline-flex;
            align-items: center;
            padding: 2px 6px; /* Reduced from 3px 8px */
            border-radius: 10px; /* Slightly smaller */
            font-size: 0.7rem; /* Reduced from 0.75rem */
            font-weight: 600;
            border: 1px solid transparent; /* Thinner border */
        }
        .status-Present { background: #d4edda; color: #155724; border-color: #c3e6cb; }
        .status-Half-Day { background: #fff3cd; color: #856404; border-color: #ffeeba; }
        .status-Leave { background: #f8d7da; color: #721c24; border-color: #f5c6cb; }
        .status-Holiday { background: #d1ecf1; color: #0c5460; border-color: #bee5eb; }
        .status-Absent { background: #f8d7da; color: #721c24; border-color: #f5c6cb; }

        /* --- 🆕 NEW: INLINE TIME EXCEPTION STYLES --- */
        
        /* Wrapper to keep time and badge together */
        .time-cell-wrapper {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 6px; /* Reduced from 8px */
        }
        
        .main-time {
            font-weight: 500;
            font-size: 0.8rem; /* Reduced from 0.85rem */
            white-space: nowrap;
        }

        /* Base style for the new inline badges */
        .time-exception-badge {
            font-weight: 600;
            font-size: 0.65rem; /* Reduced from 0.7rem */
            padding: 1px 5px; /* Reduced from 2px 7px */
            border-radius: 8px; /* Slightly smaller */
            letter-spacing: 0.2px;
            white-space: nowrap;
        }
        
        /* Subtle "light" variants */
        .exception-late { 
            background: #fdf5f5;
            color: #d9534f;
        }
        .exception-early-arrival { 
            background: #f4f9fc; 
            color: #3498db; 
        }
        .exception-early { 
            background: #fefaf3; 
            color: #f0ad4e; 
        }
        .exception-overtime {
            background: #f6fbf6;
            color: #5cb85c;
        }
        
    </style>
    """
    
    # Helper function to handle missing data gracefully
    def _get_val(row, col, default_val="-"):
        val = row.get(col)
        return val if pd.notna(val) and val != "" else default_val

    # Start table HTML
    table_html = '<div style="overflow-x: auto;"><table class="daily-report-table"><thead><tr>'
    
    # Table Headers (Updated)
    headers = ['Designation','Employee Name',  'Check In', 'Check Out', 'Status', 'Notes']
    for header in headers:
        table_html += f'<th>{header}</th>'
    table_html += '</tr></thead><tbody>'
    
    # Table Rows
    for index, row in df_display.iterrows():
        table_html += '<tr>'
        
        # Designation
        table_html += f'<td>{_get_val(row, "designation")}</td>'
        
        # Employee Name
        table_html += f'<td>{_get_val(row, "Employee Name")}</td>'
        
        # --- 🆕 MERGED Check In Column ---
        check_in_time = _get_val(row, "Check In")
        late_val = _get_val(row, "Late Arrival", "")
        early_arrival_val = _get_val(row, "Early Arrival", "")
        
        table_html += '<td><div class="time-cell-wrapper">'
        table_html += f'<span class="main-time">{check_in_time}</span>'
        
        # Add exception badge *inline*
        if late_val:
            table_html += f'<span class="time-exception-badge exception-late">Late: {late_val}</span>'
        elif early_arrival_val:
            table_html += f'<span class="time-exception-badge exception-early-arrival">Early: {early_arrival_val}</span>'
            
        table_html += '</div></td>'
        
        # --- 🆕 MERGED Check Out Column ---
        check_out_time = _get_val(row, "Check Out")
        early_val = _get_val(row, "Early Exit", "")
        overtime_val = _get_val(row, "Overtime", "")

        table_html += '<td><div class="time-cell-wrapper">'
        table_html += f'<span class="main-time">{check_out_time}</span>'

        # Add exception badge *inline*
        if early_val:
            table_html += f'<span class="time-exception-badge exception-early">Early: {early_val}</span>'
        elif overtime_val:
            table_html += f'<span class="time-exception-badge exception-overtime">Overtime: {overtime_val}</span>'

        table_html += '</div></td>'
        
        # Status
        status_val = _get_val(row, "Status", "N/A")
        if status_val != "N/A":
            status_class = status_val.replace(" ", "-") # e.g., "Half Day" -> "Half-Day"
            table_html += f'<td><span class="status-badge status-{status_class}">{status_val}</span></td>'
        else:
            table_html += '<td>-</td>'
        
        # Notes
        table_html += f'<td>{_get_val(row, "Notes")}</td>'
        
        table_html += '</tr>'
        
    table_html += '</tbody></table></div>'
    
    # Combine CSS and HTML and render
    st.markdown(table_css + table_html, unsafe_allow_html=True)

def render_day_card(day_date, attendance_dict, is_current_month, holidays=None):
    """Render a single day card"""
    if not is_current_month:
        st.markdown('<div class="day-card day-card-empty"></div>', unsafe_allow_html=True)
        return
    
    day_name = calendar.day_abbr[day_date.weekday()]
    
    is_holiday = holidays and day_date in holidays
    holiday_name = holidays.get(day_date, '') if holidays else ''
    
    css_class = "day-card-empty"
    summary_html = "<div class='status-badge'>📅 No Record</div>"

    if day_date.day in attendance_dict:
        data = attendance_dict[day_date.day]
        status = data['status']
        
        if status == 'Holiday': css_class = 'day-card-holiday'
        elif status == 'Leave': css_class = 'day-card-leave'
        elif status == 'Half Day': css_class = 'day-card-half-day'
        elif status == 'Absent': css_class = 'day-card-absent'
        elif status == 'Present': css_class = 'day-card-present'

        summary_lines = []
        
        if is_holiday:
            summary_lines.append(f"<div class='status-badge'><strong>🏖️ {holiday_name}</strong></div>")
        elif status == 'Leave':
            summary_lines.append(f"<div class='status-badge'><strong>❌ Leave</strong></div>")
        elif status == 'Half Day':
            summary_lines.append(f"<div class='status-badge'><strong>🕐 Half Day</strong></div>")
        
        if data['status'] in ['Present', 'Half Day']:
            check_in_str = data['check_in'].strftime('%I:%M %p') if data['check_in'] else '-'
            check_out_str = data['check_out'].strftime('%I:%M %p') if data['check_out'] else '-'
            
            time_html = f"""
            <div class="time-container">
                <div class="time-block">
                    <span class="time-label">Check In</span>
                    <span class="time-value">{check_in_str}</span>
                </div>
                <div class="time-block">
                    <span class="time-label">Check Out</span>
                    <span class="time-value">{check_out_str}</span>
                </div>
            </div>
            """
            summary_lines.append(time_html)

            exceptions = []
            if data.get('is_early_arrival'):
                diff = calculate_time_diff_for_cards(data['check_in'], SCHEDULED_IN, 'early_arrival')
                exceptions.append(f'<span class="exception exception-early-in-bg">🌅 Early In {diff}</span>')
            if data.get('is_late'):
                diff = calculate_time_diff_for_cards(data['check_in'], SCHEDULED_IN, 'late')
                exceptions.append(f'<span class="exception exception-late-in-bg">⏰ Late In {diff}</span>')
            if data.get('is_early'):
                diff = calculate_time_diff_for_cards(data['check_out'], SCHEDULED_OUT, 'early')
                exceptions.append(f'<span class="exception exception-early-out-bg">🏃 Early Out {diff}</span>')
            if data.get('is_overtime'):
                diff = calculate_time_diff_for_cards(data['check_out'], SCHEDULED_OUT, 'overtime')
                exceptions.append(f'<span class="exception exception-overtime-bg">🌙 Overtime +{diff}</span>')

            if exceptions:
                summary_lines.append('<div class="exception-container">' + "".join(exceptions) + '</div>')
            elif status == 'Present':
                 summary_lines.append("<div class='status-badge'>✅ On Time</div>")

        if data['notes']:
            summary_lines.append(f"<div style='font-size: 0.68em; color: #555; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'>📝 {data['notes'][:28]}...</div>")
        
        summary_html = "".join(summary_lines)
    elif is_holiday:
        summary_html = f"<div class='status-badge'><strong>🏖️ {holiday_name}</strong></div>"
        css_class = "day-card-holiday"

    card_html = f"""
    <div class="day-card-container">
        <div class="day-card {css_class}">
            <div class="day-header">
                <div class="day-number">{day_date.day}</div>
                <div class="day-name">{day_name}</div>
            </div>
            <div class="day-summary">{summary_html}</div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def create_modern_calendar(year, month, attendance_data,selected_emp):
    """Create a modern calendar view using Streamlit columns"""
    inject_custom_css()
    
    # Create attendance dictionary
    attendance_dict = {}
    for row in attendance_data:
        att_date, check_in, check_out, status, notes, is_late, is_early, is_overtime, is_early_arrival = row
        
        # Convert timedelta to time if needed
        if check_in and isinstance(check_in, timedelta):
            total_seconds = int(check_in.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            check_in = dt_time(hours, minutes)
        
        if check_out and isinstance(check_out, timedelta):
            total_seconds = int(check_out.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            check_out = dt_time(hours, minutes)
        
        attendance_dict[att_date.day] = {
            'check_in': check_in,
            'check_out': check_out,
            'status': status,
            'notes': notes,
            'is_late': bool(is_late),
            'is_early': bool(is_early),
            'is_overtime': bool(is_overtime),
            'is_early_arrival': bool(is_early_arrival)
        }

    selected_emp = re.split(r'\s*\(', selected_emp)[0].strip()
    
    # Display month header
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 0.3rem; border-radius: 12px; margin-bottom: 1.2rem; 
                    text-align: center; font-weight: 700; font-size: 1.5rem;
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);">
            📅 {calendar.month_name[month]} {year} ({selected_emp})
        </div>
    """, unsafe_allow_html=True)
    
    # Legend
    st.markdown("""
        <div style="display: flex; flex-wrap: wrap; gap: 12px; margin: 1.2rem 0; padding: 1.2rem; 
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                    border-radius: 12px; justify-content: center; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; font-weight: 500;">
                <div style="width: 24px; height: 24px; border-radius: 6px; background: linear-gradient(135deg, #D4EDDA, #C3E6CB); border: 2px solid #28a745;"></div>
                <span>Present</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; font-weight: 500;">
                <div style="width: 24px; height: 24px; border-radius: 6px; background: linear-gradient(135deg, #FFE5D0, #FFDCC5); border: 2px solid #fd7e14;"></div>
                <span>Late</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; font-weight: 500;">
                <div style="width: 24px; height: 24px; border-radius: 6px; background: linear-gradient(135deg, #F8E6FF, #F0D9FF); border: 2px solid #e83e8c;"></div>
                <span>Early Out</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; font-weight: 500;">
                <div style="width: 24px; height: 24px; border-radius: 6px; background: linear-gradient(135deg, #e0f7ff, #c7eeff); border: 2px solid #3498db;"></div>
                <span>Early In</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; font-weight: 500;">
                <div style="width: 24px; height: 24px; border-radius: 6px; background: linear-gradient(135deg, #FFF3CD, #FFEAA7); border: 2px solid #ffc107;"></div>
                <span>Half Day</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; font-weight: 500;">
                <div style="width: 24px; height: 24px; border-radius: 6px; background: linear-gradient(135deg, #E2D9F3, #D6C9EB); border: 2px solid #6f42c1;"></div>
                <span>Holiday</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; font-weight: 500;">
                <div style="width: 24px; height: 24px; border-radius: 6px; background: linear-gradient(135deg, #F8D7DA, #F5C6CB); border: 2px solid #dc3545;"></div>
                <span>Leave</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; font-weight: 500;">
                <div style="width: 24px; height: 24px; border-radius: 6px; background: linear-gradient(135deg, #d4f4dd, #b8e6c4); border: 2px solid #27ae60;"></div>
                <span>Overtime</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Day headers
    header_cols = st.columns(6)
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    for i, day in enumerate(days):
        with header_cols[i]:
            st.markdown(f'<div class="header-card">{day}</div>', unsafe_allow_html=True)
    
    # Calendar grid
    cal = calendar.Calendar()
    for week in cal.monthdatescalendar(year, month):
        cols = st.columns(6)
        for i, day_date in enumerate(week[:-1]):
            with cols[i]:
                is_current_month = (day_date.month == month)
                render_day_card(day_date, attendance_dict, is_current_month)

def render_mini_day_card(day_date, attendance_dict, is_current_month):
    """Render a mini day card for yearly view"""
    if not is_current_month:
        st.markdown('<div style="height: 40px; background: transparent;"></div>', unsafe_allow_html=True)
        return
    
    day_key = day_date.strftime("%Y-%m-%d")
    
    if day_key in attendance_dict:
        data = attendance_dict[day_key]
        status_class, _ = determine_day_status(
            data['status'], 
            data['check_in'], 
            data['check_out']
        )
        css_class = status_class
    else:
        css_class = "day-card-empty"
    
    card_html = f"""
    <div style="padding: 8px; border-radius: 6px; text-align: center; font-size: 0.85rem; 
                height: 40px; display: flex; align-items: center; justify-content: center;
                font-weight: 500;" class="{css_class}">
        {day_date.day}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def create_mini_month_calendar(year, month, attendance_dict):
    """Create a mini calendar for yearly view using Streamlit columns"""
    st.markdown(f"""
        <div style="text-align: center; font-weight: bold; color: #667eea; margin-bottom: 0.5rem; font-size: 1rem;">
            {calendar.month_name[month]}
        </div>
    """, unsafe_allow_html=True)
    
    # Day headers
    header_cols = st.columns(6)
    days = ['M', 'T', 'W', 'T', 'F', 'S']
    for i, day in enumerate(days):
        with header_cols[i]:
            st.markdown(f'<div style="text-align: center; font-size: 0.7rem; font-weight: 600; color: #666; margin-bottom: 4px;">{day}</div>', unsafe_allow_html=True)
    
    # Calendar grid
    cal = calendar.Calendar()
    for week in cal.monthdatescalendar(year, month):
        cols = st.columns(6)
        for i, day_date in enumerate(week[:-1]):
            with cols[i]:
                is_current_month = (day_date.month == month)
                render_mini_day_card(day_date, attendance_dict, is_current_month)

# --- Analytics Functions ---
@st.cache_data(ttl=600)
def get_holidays(_conn, year):
    """Fetch all holidays for a given year."""
    try:
        with _conn.session as s:
            result = s.execute(text("""
                SELECT holiday_date FROM holidays WHERE YEAR(holiday_date) = :year
            """), {"year": year})
            return {row[0] for row in result.fetchall()}
    except Exception as e:
        st.error(f"Error fetching holidays: {e}")
        return set()

@st.cache_data(ttl=600)
def get_analytics_data(_conn, year, month=None):
    """Fetch all attendance data for analytics, for active employees."""
    try:
        with _conn.session as s:
            query = """
                SELECT 
                    e.employee_id,
                    e.employee_name,
                    e.designation,
                    a.attendance_date,
                    a.check_in_time,
                    a.check_out_time,
                    a.status
                FROM employees e
                JOIN attendance a ON e.employee_id = a.employee_id
                WHERE e.employment_status = 'Active' AND YEAR(a.attendance_date) = :year
            """
            params = {"year": year}
            if month and month != "All":
                query += " AND MONTH(a.attendance_date) = :month"
                params["month"] = month
            
            query += " ORDER BY e.employee_id, a.attendance_date"
            
            # Use st.connection's connection for pandas
            df = pd.read_sql(text(query), s.connection(), params=params)
            return df
    except Exception as e:
        st.error(f"Error fetching analytics data: {e}")
        return pd.DataFrame()

def time_to_total_minutes(t):
    """Convert time object to total minutes from midnight."""
    if t is None or pd.isna(t):
        return None
    return t.hour * 60 + t.minute

def calculate_longest_streak(present_dates, all_work_days):
    """Calculate the longest streak of consecutive work days an employee was present."""
    if not present_dates or not all_work_days:
        return 0
    
    present_set = set(present_dates)
    sorted_work_days = sorted(list(all_work_days))
    
    max_streak = 0
    current_streak = 0
    
    for day in sorted_work_days:
        if day.date() in present_set:
            current_streak += 1
        else:
            max_streak = max(max_streak, current_streak)
            current_streak = 0
            
    max_streak = max(max_streak, current_streak)
    return max_streak


# Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Mark Attendance", "👤 Individual View", "📊 Daily Report", "📊 Analytics", "➕ Add Employee"])


###################################################################################################################################
##################################--------------- Tab 1 ----------------------------##################################
###################################################################################################################################

# TAB 1: Mark Employee Attendance
with tab1:
    st.subheader("Mark Employee Attendance")
    
    # Date selector
    selected_date = st.date_input("Attendance Date", value=date.today(), key="mark_attendance_date")
    
    # Fetch employees
    employees = get_all_employees(conn)
    if not employees:
        st.warning("No employees found. Please add employees first.")
        st.stop()
    
    # Fetch existing attendance for the selected date
    try:
        with conn.session as s:
            result = s.execute(text("""
                SELECT 
                    employee_id,
                    check_in_time,
                    check_out_time,
                    status,
                    COALESCE(notes, '') AS notes
                FROM attendance 
                WHERE attendance_date = :att_date
            """), {"att_date": selected_date})
            existing_attendance = {row[0]: row[1:] for row in result.fetchall()}
    except Exception as e:
        st.error(f"Error fetching attendance: {e}")
        existing_attendance = {}
    
    # Form for marking holiday for all employees
    with st.form(key="holiday_form", border=False):

        with st.popover("🎉 Mark Holiday for All Employees", width=500):
            holiday_name = st.text_input("Holiday Name", placeholder="e.g., Christmas Day")
            holiday_submitted = st.form_submit_button("🎉 Mark Holiday Today", width='stretch', type="primary")
            
            if holiday_submitted:
                if not holiday_name.strip():
                    st.error("Holiday name is required.")
                    st.toast("Error: Holiday name required", icon="🚨")
                else:
                    success_count = 0
                    for emp in employees:
                        emp_id, emp_name, dept = emp
                        # Skip if already marked as Holiday with the same name
                        if emp_id in existing_attendance and existing_attendance[emp_id][2] == "Holiday" and existing_attendance[emp_id][3] == holiday_name:
                            continue
                        if mark_attendance(
                            conn,
                            emp_id,
                            selected_date,
                            None,  # No check-in
                            None,  # No check-out
                            "Holiday",
                            holiday_name
                        ):
                            success_count += 1
                    if success_count > 0:
                        st.success(f"✅ Holiday '{holiday_name}' marked for {success_count} employee(s) on {selected_date}")
                        st.toast(f"Holiday marked for {success_count} employee(s)", icon="🎉")
                    else:
                        st.info("No changes to save. Holiday already marked for all employees.")

    # Form for all employees
    with st.form(key="bulk_attendance_form"):
        # Dictionary to store form data
        attendance_data = {}
        
        # Custom CSS for compact layout, headers, and highlighted employee names in errors
        st.markdown("""
            <style>
            .employee-row {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 8px;
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            .employee-name {
                width: 200px;
                font-weight: bold;
            }
            .status-select {
                width: 100px;
            }
            .time-input {
                width: 80px;
            }
            .notes-input {
                width: 150px;
            }
            .header-row {
                display: flex;
                gap: 8px;
                padding: 8px;
                font-weight: bold;
                border-bottom: 2px solid #ccc;
                margin-bottom: 8px;
            }
            .header {
                text-align: left;
            }
            .highlight-name {
                font-weight: bold;
                color: #ff4b4b;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Determine layout: 1 or 2 columns based on employee count
        num_employees = len(employees)
        if num_employees > 10:
            col_left, col_right = st.columns(2)
            mid_point = (num_employees + 1) // 2
            left_employees = employees[:mid_point]
            right_employees = employees[mid_point:]
            employee_groups = [(col_left, left_employees), (col_right, right_employees)]
        else:
            employee_groups = [(st.container(), employees)]

        column_size = [1, 0.8, 0.8, 1]  # Width ratios for status, check-in, check-out, notes
        
        # Headers for each column
        for col, emp_list in employee_groups:
            with col:
                c1, c2, c3, c4 = st.columns(column_size)
                with c1:
                    st.write("###### Employee Status")
                with c2:
                    st.write("###### Check-In")
                with c3:
                    st.write("###### Check-Out")
                with c4:
                    st.write("###### Notes")
        
        # Create rows for each employee
        for col, emp_list in employee_groups:
            with col:
                for emp in emp_list:
                    emp_id, emp_name, dept = emp
                    emp_display = f"{emp_name}"
                    
                    # Load existing or default values
                    existing = existing_attendance.get(emp_id, (None, None, None, ""))
                    
                    # Convert check-in/check-out times to string format (e.g., "9:30 AM")
                    check_in = existing[0]
                    check_out = existing[1]
                    if check_in and isinstance(check_in, timedelta):
                        total_sec = int(check_in.total_seconds())
                        hours = total_sec // 3600
                        minutes = (total_sec % 3600) // 60
                        check_in = datetime.strftime(datetime(1, 1, 1, hours, minutes), "%I:%M %p").lstrip("0")
                    else:
                        check_in = ""
                    
                    if check_out and isinstance(check_out, timedelta):
                        total_sec = int(check_out.total_seconds())
                        hours = total_sec // 3600
                        minutes = (total_sec % 3600) // 60
                        check_out = datetime.strftime(datetime(1, 1, 1, hours, minutes), "%I:%M %p").lstrip("0")
                    else:
                        check_out = ""
                    
                    default_status = existing[2] if existing[2] in ["Present", "Half Day", "Leave", "Holiday"] else "Present"
                    default_notes = existing[3]
                    
                    # Employee row
                    with st.container():
                        st.markdown(f'<div class="employee-row">', unsafe_allow_html=True)
                        
                        # Employee name (non-editable)
                        st.markdown(f'<div class="employee-name">{emp_display}</div>', unsafe_allow_html=True)
                        st.space(1)
                        
                        # Input fields
                        col1, col2, col3, col4 = st.columns(column_size)
                        with col1:
                            status = st.selectbox(
                                "Status",
                                ["Present", "Half Day", "Leave", "Holiday"],
                                index=["Present", "Half Day", "Leave", "Holiday"].index(default_status),
                                key=f"status_{emp_id}_{selected_date}",
                                label_visibility="collapsed"
                            )
                        
                        with col2:
                            check_in_input = st.text_input(
                                "Check-In",
                                value=check_in,
                                disabled=status in ["Leave", "Holiday"],
                                key=f"check_in_{emp_id}_{selected_date}",
                                placeholder="e.g. 9:30 AM",
                                label_visibility="collapsed"
                            )
                        
                        with col3:
                            check_out_input = st.text_input(
                                "Check-Out",
                                value=check_out,
                                disabled=status in ["Leave", "Holiday"],
                                key=f"check_out_{emp_id}_{selected_date}",
                                placeholder="e.g. 6:00 PM",
                                label_visibility="collapsed"
                            )
                        
                        with col4:
                            notes = st.text_input(
                                "Notes",
                                value=default_notes,
                                key=f"notes_{emp_id}_{selected_date}",
                                placeholder="Optional notes",
                                label_visibility="collapsed"
                            )
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Validate and convert AM/PM time to 24-hour format for saving
                        check_in_time = None
                        check_out_time = None
                        if status not in ["Leave", "Holiday"]:
                            try:
                                if check_in_input.strip():
                                    # Validate time format (e.g., "9:30 AM", "12:00 PM")
                                    check_in_time = datetime.strptime(check_in_input.strip(), "%I:%M %p").strftime("%H:%M:%S")
                            except ValueError:
                                check_in_time = None
                                if check_in_input.strip():
                                    st.warning(f"Invalid Check-In time format for {emp_name}. Use format like '9:30 AM'.")
                            
                            try:
                                if check_out_input.strip():
                                    check_out_time = datetime.strptime(check_out_input.strip(), "%I:%M %p").strftime("%H:%M:%S")
                            except ValueError:
                                check_out_time = None
                                if check_out_input.strip():
                                    st.warning(f"Invalid Check-Out time format for {emp_name}. Use format like '6:00 PM'.")
                        
                        # Store data for submission
                        attendance_data[emp_id] = {
                            "check_in": check_in_time,
                            "check_out": check_out_time,
                            "status": status,
                            "notes": notes,
                            "emp_name": emp_name  # Store name for error reporting
                        }
        
        # Single Save button for all employees, inside the form
        submitted = st.form_submit_button("💾 Save All Attendance", width='stretch', type="primary")
        if submitted:
            success_count = 0
            invalid_employees = []
            for emp_id, data in attendance_data.items():
                # Validate Check-In and Check-Out for Present or Half Day
                if data["status"] in ["Present", "Half Day"]:
                    if not data["check_in"] or not data["check_out"]:
                        invalid_employees.append(f'<span class="highlight-name">{data["emp_name"]}</span>')
                        continue
                
                # Save if status is Present/Half Day or has notes, or is Leave/Holiday
                if data["status"] in ["Present", "Half Day"] or data["notes"].strip() or data["status"] in ["Leave", "Holiday"]:
                    if mark_attendance(
                        conn,
                        emp_id,
                        selected_date,
                        data["check_in"],
                        data["check_out"],
                        data["status"],
                        data["notes"]
                    ):
                        success_count += 1
            
            if invalid_employees:
                st.markdown(
                    f"""
                    <div style="background-color: #ffebee; color: #c62828; padding: 10px; border-radius: 5px; border-left: 4px solid #f44336;">
                        <strong>Error:</strong> Check-In and Check-Out times are required for {', '.join(invalid_employees)} with status 'Present' or 'Half Day'.
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                st.toast("Error: Check-In and Check-Out times required", icon="🚨")
            if success_count > 0:
                st.space(1)
                st.success(f"✅ {success_count} attendance record(s) saved for {selected_date}")
            elif not invalid_employees:
                st.info("No changes to save.")


# --- HELPER FUNCTION TO RENDER YEARLY VIEW ---
def display_yearly_calendars(year, attendance_data):
    """
    Renders 12 monthly calendars in a 2x6 grid for the yearly view.
    Includes indicators for late arrival, early exit, and overtime.
    """
    
    # CSS for the calendar
    calendar_css = """
    <style>
    .year-view-container {
        padding: 10px;
    }
    .calendar-month {
        background-color: #ffffff;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        padding: 15px;
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
    }
    .calendar-month h5 {
        text-align: center;
        color: #010e1a;
        font-weight: 600;
        margin-bottom: 15px;
    }
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 5px;
    }
    
    /* --- IMPROVED: Subtle Colored Header UI --- */
    .calendar-header {
        text-align: center;
        font-weight: 600;
        font-size: 0.8em;
        color: #f9fafb;
        padding: 8px 0;
        text-transform: uppercase;
        letter-spacing: 1px;
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border-radius: 6px;
        margin-bottom: 8px;
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.05);
    }


    
    .calendar-day {
        text-align: center;
        font-size: 0.9em;
        height: 50px;
        padding: 4px 2px;
        border-radius: 4px;
        position: relative;
        background-color: #f4f4f4;
        color: #aaa;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    
    .day-number {
        font-weight: 600;
        font-size: 1em;
        line-height: 1;
    }
    .calendar-day.valid-day {
        background-color: #e9ecef;
        color: #333;
        cursor: help;
    }
    .calendar-day.Present {
        background-color: #d4edda;
        color: #155724;
        font-weight: bold;
    }
    .calendar-day.Leave {
        background-color: #f8d7da;
        color: #721c24;
    }
    .calendar-day.Half {
        background: linear-gradient(135deg, #d4edda 50%, #fff3cd 50%);
        color: #333;
        font-weight: bold;
    }
    .calendar-day.Holiday {
        background-color: #d1ecf1;
        color: #0c5460;
    }
    
    /* --- IMPROVED: Text-based Exception Indicators --- */
    .exception-indicators {
        display: flex;
        gap: 2px;
        font-size: 0.65em;
        font-weight: 600;
        margin-top: 2px;
        line-height: 1;
    }
    
    .exception-tag {
        padding: 1px 3px;
        border-radius: 2px;
        color: white;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    .tag-late {
        background-color: #ed5721;
    }
    
    .tag-early {
        background-color: #5bc0de;
    }
    
    .tag-early-arrival {
        background-color: #3498db;
    }
    
    .tag-overtime {
        background-color: #28a745;
    }

    /* Tooltip styling */
    .calendar-day[title]:hover::after {
        content: attr(title);
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        white-space: pre-wrap;
        background-color: #333;
        color: white;
        padding: 8px;
        border-radius: 5px;
        z-index: 100;
        font-size: 0.85em;
        line-height: 1.4;
        min-width: 180px;
        text-align: left;
    }
    </style>
    """
    st.markdown(calendar_css, unsafe_allow_html=True)
    
    # Get day abbreviations
    week_headers = [day for day in calendar.day_abbr][:-1]

    # Create a 2-column layout (2x6 grid)
    col1, col2 = st.columns(2)
    
    for month_num in range(1, 13):
        month_name = calendar.month_name[month_num]
        month_calendar = calendar.monthcalendar(year, month_num)
        
        # Start HTML for the month
        html = f'<div class="calendar-month"><h5>{month_name} {year}</h5>'
        html += '<div class="calendar-grid">'
        
        # Add week headers
        for header in week_headers:
            html += f'<div class="calendar-header">{header}</div>'
            
        # Add days
        for week in month_calendar:
            for day in week[:-1]:
                if day == 0:
                    html += '<div class="calendar-day"></div>' # Empty cell
                else:
                    date_key = f"{year}-{month_num:02d}-{day:02d}"
                    day_data = attendance_data.get(date_key)
                    
                    status_class = "valid-day" # Default for days with no record
                    tooltip = f"{date_key}\nStatus: N/A" # Default tooltip
                    indicators_html = ""
                    
                    if day_data:
                        status = day_data['status']
                        if status == "Half Day":
                            status_class = "Half"
                        else:
                            status_class = status # "Present", "Leave", "Holiday"
                        
                        # --- IMPROVED: Build text-based indicators ---
                        indicators = []
                        if day_data.get('is_early_arrival', False):
                            indicators.append('<span class="exception-tag tag-early-arrival">Early</span>')
                        if day_data.get('is_late', False):
                            indicators.append('<span class="exception-tag tag-late">Late</span>')
                        if day_data.get('is_early', False):
                            indicators.append('<span class="exception-tag tag-early">Eearly Exit</span>')
                        if day_data.get('is_overtime', False):
                            indicators.append('<span class="exception-tag tag-overtime">Overtime</span>')
                        
                        if indicators:
                            indicators_html = f'<div class="exception-indicators">{"".join(indicators)}</div>'
                        
                        # Build tooltip with exceptions
                        tooltip = f"Date: {date_key}\nStatus: {status}"
                        if status in ["Present", "Half Day"]:
                            check_in = day_data['check_in'].strftime('%I:%M %p') if day_data['check_in'] else "N/A"
                            check_out = day_data['check_out'].strftime('%I:%M %p') if day_data['check_out'] else "N/A"
                            tooltip += f"\nCheck-In: {check_in}\nCheck-Out: {check_out}"
                            
                            # Add exception notes to tooltip
                            if day_data.get('is_early_arrival', False):
                                tooltip += "\n🌅 Early Arrival"
                            if day_data.get('is_late', False):
                                tooltip += "\n🔴 Late Arrival"
                            if day_data.get('is_early', False):
                                tooltip += "\n🔵 Early Exit"
                            if day_data.get('is_overtime', False):
                                tooltip += "\n🟢 Overtime"
                                
                        if day_data['notes']:
                            tooltip += f"\nNotes: {day_data['notes']}"
                            
                    html += f'<div class="calendar-day {status_class}" title="{tooltip}"><span class="day-number">{day}</span>{indicators_html}</div>'
                    
        html += '</div></div>' # Close grid and month
        
        # Add to the correct column
        if month_num <= 6:
            with col1:
                st.markdown(html, unsafe_allow_html=True)
        else:
            with col2:
                st.markdown(html, unsafe_allow_html=True)


###################################################################################################################################
##################################--------------- Tab 2 ----------------------------##################################
###################################################################################################################################


# --- TAB 2: Individual Employee View ---
with tab2:
    st.subheader("Individual Employee Attendance")

    col1, col2, col3, col4 = st.columns([0.5, 1, 1, 1])

    with col1:
        view_type = st.segmented_control("View Type", ["Monthly", "Yearly"], default= "Monthly")

    with col2:
        employees = get_all_employees(conn)
        if not employees:
            st.warning("No employees found.")
            st.stop()
        employee_options = {f"{emp[1]} ({emp[2]})": emp[0] for emp in employees}
        selected_emp = st.selectbox("Select Employee", list(employee_options.keys()), key="ind_emp")
        selected_emp_id = employee_options[selected_emp]

    # Fetch available years for the selected employee
    available_years = get_employee_available_years(conn, selected_emp_id)

    selected_year = None
    selected_month = None
    attendance_data = []

    with col3:
        if available_years:
            # Default to the most recent year
            default_year_index = 0
            selected_year = st.selectbox(
                "Year",
                available_years,
                index=default_year_index,
                key="ind_year"
            )
        else:
            st.warning("No attendance records available for this employee.")
            st.selectbox("Year", [], disabled=True)
            st.stop()

    with col4:
        if view_type == "Monthly" and selected_year:
            # Fetch available months for the selected year
            available_months = get_available_months_for_year(conn, selected_emp_id, selected_year)
            if available_months:
                # Default to the most recent month
                default_month_index = 0
                selected_month = st.selectbox(
                    "Month",
                    available_months,
                    index=default_month_index,
                    format_func=lambda x: calendar.month_name[x],
                    key=f"ind_month_for_year_{selected_year}"
                )
            else:
                st.selectbox("Month", [], disabled=True)
        else:  # Yearly or no year selected
            selected_month = None
            st.selectbox("Month", [], disabled=True, label_visibility="visible")

    st.markdown("---")

    if selected_emp_id:
        if view_type == "Monthly" and selected_month and selected_year:
            # --- MONTHLY VIEW ---
            attendance_data = get_employee_monthly_attendance(conn, selected_emp_id, selected_year, selected_month)
            
            if attendance_data:
                # Create DataFrame
                df = pd.DataFrame(attendance_data,
                                columns=['Date', 'Check In', 'Check Out', 'Status', 'Notes',
                                         'Is Late', 'Is Early', 'Is Overtime', 'Is Early Arrival'])
                
                # Calculate statistics
                present_days = len([row for row in attendance_data if row[3] == 'Present'])
                half_days = len([row for row in attendance_data if row[3] == 'Half Day'])
                leave_days = len([row for row in attendance_data if row[3] == 'Leave'])
                month_holiday = len([row for row in attendance_data if row[3] == 'Holiday'])
                late_arrivals = sum(row[5] for row in attendance_data if row[5] == 1)
                early_exits = sum(row[6] for row in attendance_data if row[6] == 1)
                overtime_days = sum(row[7] for row in attendance_data if row[7] == 1)
                early_arrivals = sum(row[8] for row in attendance_data if row[8] == 1)
                working_days = get_month_working_days(conn, selected_year, selected_month)

                #----Attendance Rate Calculate -------#

                # 1. Calculate the numerator (days the employee actually attended)
                days_attended = present_days + (half_days * 0.5)
                # 3. Calculate the final rate
                attendance_rate = (days_attended / working_days * 100) if working_days > 0 else 0

                #----Punctuality Rate Calculate -------#


                # 1. Calculate total days employee was at work
                total_days_attended = present_days + half_days

                # 2. Calculate days they were punctual (no late arrival or early exit)
                total_punctual_days = total_days_attended - late_arrivals - early_exits

                # 3. Calculate the rate
                punctuality_score = (total_punctual_days / total_days_attended * 100) if total_days_attended > 0 else 0
                
                
                # Calculate average check-in and check-out times
                check_in_times = [row[1] for row in attendance_data if row[1] is not None]
                check_out_times = [row[2] for row in attendance_data if row[2] is not None]

                avg_check_in = None
                if check_in_times:
                    try:
                        # Convert timedelta to seconds
                        seconds = []
                        for t in check_in_times:
                            if isinstance(t, timedelta):
                                total_seconds = t.total_seconds()
                                seconds.append(total_seconds)
                            elif isinstance(t, dt_time):
                                seconds.append(t.hour * 3600 + t.minute * 60 + t.second)
                        if seconds:
                            avg_seconds = sum(seconds) / len(seconds)
                            avg_check_in = f"{int(avg_seconds // 3600):02d}:{int((avg_seconds % 3600) // 60):02d}"
                        else:
                            avg_check_in = 'N/A'
                    except Exception as e:
                        st.error(f"Error calculating average check-in time: {e}")
                        avg_check_in = 'N/A'

                avg_check_out = None
                if check_out_times:
                    try:
                        # Convert timedelta to seconds
                        seconds = []
                        for t in check_out_times:
                            if isinstance(t, timedelta):
                                total_seconds = t.total_seconds()
                                seconds.append(total_seconds)
                            elif isinstance(t, dt_time):
                                seconds.append(t.hour * 3600 + t.minute * 60 + t.second)
                        if seconds:
                            avg_seconds = sum(seconds) / len(seconds)
                            avg_check_out = f"{int(avg_seconds // 3600):02d}:{int((avg_seconds % 3600) // 60):02d}"
                        else:
                            avg_check_out = 'N/A'
                    except Exception as e:
                        st.error(f"Error calculating average check-out time: {e}")
                        avg_check_out = 'N/A'
                
                col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

                with col1:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #28a745;">{attendance_rate:.1f}%</div>
                        <div class="stat-label">Attendance Rate</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #6f42c1;">{punctuality_score:.1f}%</div>
                        <div class="stat-label">Punctuality Rate</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col3:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ffc107;">{working_days}</div>
                        <div class="stat-label">Working Days</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col4:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #28a745;">{present_days}</div>
                        <div class="stat-label">Present</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col5:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #dc3545;">{leave_days}</div>
                        <div class="stat-label">Leaves</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col6:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ffc107;">{half_days}</div>
                        <div class="stat-label">Half Days</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col7:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ed5721;">{late_arrivals}</div>
                        <div class="stat-label">Late</div>
                    </div>
                    """, unsafe_allow_html=True)

                col1, col2, col3, col4, col5, col6 = st.columns(6)

                with col1:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #3498db;">{avg_check_in or 'N/A'}</div>
                        <div class="stat-label">Avg Check-In</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #3498db;">{avg_check_out or 'N/A'}</div>
                        <div class="stat-label">Avg Check-Out</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col3:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ffc107;">{month_holiday}</div>
                        <div class="stat-label">Holidays</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col4:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #28a745;">{overtime_days}</div>
                        <div class="stat-label">Overtime</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col5:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #3498db;">{early_arrivals}</div>
                        <div class="stat-label">Early Arrivals</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col6:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #5bc0de;">{early_exits}</div>
                        <div class="stat-label">Early Exits</div>
                    </div>
                    """, unsafe_allow_html=True)
                

                with st.expander("View Analytics"):

                    col1,col2 = st.columns([0.4,1])


                    with col2:
                
                        # New: Trend Graphs for Check-In and Check-Out Times
                        if check_in_times or check_out_times:
                            # Prepare data for plotting
                            trend_data = {
                                'Date': [row[0] for row in attendance_data],
                                'Check-In': [
                                    (f"{int(row[1].total_seconds() // 3600):02d}:{int((row[1].total_seconds() % 3600) // 60):02d}"
                                    if isinstance(row[1], timedelta)
                                    else row[1].strftime('%H:%M') if isinstance(row[1], dt_time)
                                    else None)
                                    for row in attendance_data
                                ],
                                'Check-Out': [
                                    (f"{int(row[2].total_seconds() // 3600):02d}:{int((row[2].total_seconds() % 3600) // 60):02d}"
                                    if isinstance(row[2], timedelta)
                                    else row[2].strftime('%H:%M') if isinstance(row[2], dt_time)
                                    else None)
                                    for row in attendance_data
                                ]
                            }
                            trend_df = pd.DataFrame(trend_data)
                            
                            # Convert times to numeric values for plotting
                            def time_to_float(t):
                                if pd.isna(t) or t is None:
                                    return None
                                try:
                                    # Parse HH:MM string to hours
                                    hours, minutes = map(int, t.split(':'))
                                    return hours + minutes / 60.0
                                except:
                                    return None
                            
                            trend_df['Check-In Numeric'] = trend_df['Check-In'].apply(time_to_float)
                            trend_df['Check-Out Numeric'] = trend_df['Check-Out'].apply(time_to_float)

                            
                            # Create line chart
                            fig = px.line(
                                trend_df,
                                x='Date',
                                y=['Check-In Numeric', 'Check-Out Numeric'],
                                labels={'value': 'Time', 'variable': 'Type'},
                                title='Check-In and Check-Out Time Trends'
                            )
                            
                            # Update legend names
                            fig.for_each_trace(lambda t: t.update(
                                name='Check-In' if t.name == 'Check-In Numeric' else 'Check-Out'
                            ))
                            
                            # Customize y-axis to show time format
                            fig.update_yaxes(
                                tickvals=[6, 8, 10, 12, 14, 16, 18, 20, 22],
                                ticktext=['06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00']
                            )
                        
                            
                            # Assign customdata and hovertemplate to each trace individually
                            for trace in fig.data:
                                if trace.name == 'Check-In':
                                    trace.customdata = trend_df['Check-In']
                                    trace.hovertemplate = 'Date: %{x}<br>Time: %{customdata}<extra></extra>'
                                elif trace.name == 'Check-Out':
                                    trace.customdata = trend_df['Check-Out']
                                    trace.hovertemplate = 'Date: %{x}<br>Time: %{customdata}<extra></extra>'
                            
                            st.plotly_chart(fig, use_container_width=True)
                    
                    with col1:
                        # Pie Chart for Attendance Overview
                        fig = go.Figure(data=[go.Pie(
                            labels=['Present', 'Half Day', 'Leave','Late Arrival', 'Early Arrival', 'Early Exit', 'Overtime'],
                            values=[present_days, half_days, leave_days, late_arrivals, early_arrivals, early_exits, overtime_days],
                            hole=.4,
                            marker_colors=['#28a745', '#ffc107', '#dc3545', '#ed5721', '#3498db', '#5bc0de', '#6f42c1']
                        )])
                        fig.update_layout(
                            title=f"Attendance Overview - {selected_year}",
                            height=400
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    
                create_modern_calendar(selected_year, selected_month, attendance_data, selected_emp)
                
                st.markdown("---")
                
            else:
                month_display_name = "the selected month"
                if isinstance(selected_month, int) and 1 <= selected_month <= 12:
                    month_display_name = calendar.month_name[selected_month]
                elif selected_month is None:
                    month_display_name = "the selected month (no month available)"
                else:
                    month_display_name = str(selected_month) # Fallback for unexpected types

                st.info(f"No attendance records found for {month_display_name} {selected_year}")
        
        elif view_type == "Yearly" and selected_year:
            
            # --- YEARLY VIEW LOGIC ---

            # Fetch full year data ONCE
            year_data = get_employee_full_year_attendance(conn, selected_emp_id, selected_year)
            
            # Initialize counters and attendance dictionary
            total = 0
            present = 0
            half = 0
            leave = 0
            holiday = 0
            late_arrivals = 0
            early_exits = 0
            overtime_days = 0
            early_arrivals = 0
            attendance_dict = {}
            check_in_times = []
            check_out_times = []
            
            if year_data:
                # Process all data in one loop
                for row in year_data:
                    total += 1
                    att_date, check_in, check_out, status, notes = row
                    
                    # Handle timedelta (no conversion to dt_time needed for averages and graph)
                    if check_in and isinstance(check_in, timedelta):
                        check_in_times.append(check_in)
                    if check_out and isinstance(check_out, timedelta):
                        check_out_times.append(check_out)
                    
                    # Convert timedelta to dt_time for existing exception logic
                    if check_in and isinstance(check_in, timedelta):
                        total_seconds = int(check_in.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        check_in = dt_time(hours, minutes)
                    
                    if check_out and isinstance(check_out, timedelta):
                        total_seconds = int(check_out.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        check_out = dt_time(hours, minutes)
                    
                    # Count primary stats
                    if status == 'Present': present += 1
                    elif status == 'Half Day': half += 1
                    elif status == 'Leave': leave += 1
                    elif status == 'Holiday': holiday += 1
                    
                    # Calculate and count exceptions
                    is_late = False
                    is_early = False
                    is_overtime = False
                    is_early_arrival = False
                    
                    if status in ["Present", "Half Day"]:
                        if check_in and check_in < EARLY_ARRIVAL_THRESHOLD:
                            is_early_arrival = True
                            early_arrivals += 1
                        elif check_in and check_in > LATE_THRESHOLD:
                            is_late = True
                            late_arrivals += 1
                        if check_out and check_out < SCHEDULED_OUT:
                            is_early = True
                            early_exits += 1
                        if check_out and check_out > OVERTIME_THRESHOLD:
                            is_overtime = True
                            overtime_days += 1
                    
                    # Build the dictionary for the calendar
                    date_key = att_date.strftime("%Y-%m-%d")
                    attendance_dict[date_key] = {
                        'check_in': check_in,
                        'check_out': check_out,
                        'status': status,
                        'notes': notes,
                        'is_late': is_late,
                        'is_early': is_early,
                        'is_overtime': is_overtime,
                        'is_early_arrival': is_early_arrival
                    }
            
            # Total Working Days
            working_days = get_year_working_days(conn, selected_year)

            #----Attendance Rate Calculate (Yearly) -------#
            days_attended = present + (half * 0.5)

            # 2. Calculate the final rate using the correct denominator from your function
            attendance_rate = (days_attended / working_days * 100) if working_days > 0 else 0

            #----Punctuality Rate Calculate (Yearly) -------#

            # 1. Calculate total days employee was at work
            total_days_attended = present + half

            # 2. Calculate days they were punctual (no late arrival or early exit)
            total_punctual_days = total_days_attended - late_arrivals - early_exits

            # 3. Calculate the rate
            punctuality_score = (total_punctual_days / total_days_attended * 100) if total_days_attended > 0 else 0
            
            # Average Check-In and Check-Out Times
            avg_check_in = None
            if check_in_times:
                try:
                    seconds = [t.total_seconds() for t in check_in_times if isinstance(t, timedelta)]
                    if seconds:
                        avg_seconds = sum(seconds) / len(seconds)
                        avg_check_in = f"{int(avg_seconds // 3600):02d}:{int((avg_seconds % 3600) // 60):02d}"
                    else:
                        avg_check_in = 'N/A'
                except Exception as e:
                    st.error(f"Error calculating average check-in time: {e}")
                    avg_check_in = 'N/A'
            
            avg_check_out = None
            if check_out_times:
                try:
                    seconds = [t.total_seconds() for t in check_out_times if isinstance(t, timedelta)]
                    if seconds:
                        avg_seconds = sum(seconds) / len(seconds)
                        avg_check_out = f"{int(avg_seconds // 3600):02d}:{int((avg_seconds % 3600) // 60):02d}"
                    else:
                        avg_check_out = 'N/A'
                except Exception as e:
                    st.error(f"Error calculating average check-out time: {e}")
                    avg_check_out = 'N/A'
            
            
            # Render components if data exists
            if total > 0:
                # Updated 12-column stat cards to include new metrics
                col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

                with col1:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #28a745;">{attendance_rate:.1f}%</div>
                        <div class="stat-label">Attendance Rate</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #6f42c1;">{punctuality_score:.1f}%</div>
                        <div class="stat-label">Punctuality Rate</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col3:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ffc107;">{working_days}</div>
                        <div class="stat-label">Working Days</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col4:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #28a745;">{present}</div>
                        <div class="stat-label">Present</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col5:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #dc3545;">{leave}</div>
                        <div class="stat-label">Leaves</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col6:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ffc107;">{half}</div>
                        <div class="stat-label">Half Days</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col7:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ed5721;">{late_arrivals}</div>
                        <div class="stat-label">Late</div>
                    </div>
                    """, unsafe_allow_html=True)

                col8, col9, col10, col11, col12, col13 = st.columns(6)

                with col8:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #3498db;">{avg_check_in or 'N/A'}</div>
                        <div class="stat-label">Avg Check-In</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col9:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #3498db;">{avg_check_out or 'N/A'}</div>
                        <div class="stat-label">Avg Check-Out</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col10:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #17a2b8;">{holiday}</div>
                        <div class="stat-label">Holidays</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col11:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #28a745;">{overtime_days}</div>
                        <div class="stat-label">Overtime</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col12:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #3498db;">{early_arrivals}</div>
                        <div class="stat-label">Early Arrivals</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col13:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #5bc0de;">{early_exits}</div>
                        <div class="stat-label">Early Exits</div>
                    </div>
                    """, unsafe_allow_html=True)

                with st.expander("View Analytics"):

                    col1,col2 = st.columns([0.4,1])


                    with col2:
                
                        # Trend Graphs for Check-In and Check-Out Times
                        if check_in_times or check_out_times:
                            trend_data = {
                                'Date': [row[0] for row in year_data],
                                'Check-In': [
                                    (f"{int(row[1].total_seconds() // 3600):02d}:{int((row[1].total_seconds() % 3600) // 60):02d}"
                                    if isinstance(row[1], timedelta)
                                    else row[1].strftime('%H:%M') if isinstance(row[1], dt_time)
                                    else None)
                                    for row in year_data
                                ],
                                'Check-Out': [
                                    (f"{int(row[2].total_seconds() // 3600):02d}:{int((row[2].total_seconds() % 3600) // 60):02d}"
                                    if isinstance(row[2], timedelta)
                                    else row[2].strftime('%H:%M') if isinstance(row[2], dt_time)
                                    else None)
                                    for row in year_data
                                ]
                            }
                            trend_df = pd.DataFrame(trend_data)

                            
                            # Convert times to numeric values for plotting
                            def time_to_float(t):
                                if pd.isna(t) or t is None:
                                    return None
                                try:
                                    hours, minutes = map(int, t.split(':'))
                                    return hours + minutes / 60.0
                                except:
                                    return None
                            
                            trend_df['Check-In Numeric'] = trend_df['Check-In'].apply(time_to_float)
                            trend_df['Check-Out Numeric'] = trend_df['Check-Out'].apply(time_to_float)
                            
                            # Create line chart
                            fig = px.line(
                                trend_df,
                                x='Date',
                                y=['Check-In Numeric', 'Check-Out Numeric'],
                                labels={'value': 'Time', 'variable': 'Type'},
                                title=f'Check-In and Check-Out Time Trends - {selected_year}'
                            )
                            
                            # Update legend names
                            fig.for_each_trace(lambda t: t.update(
                                name='Check-In' if t.name == 'Check-In Numeric' else 'Check-Out'
                            ))
                            
                            # Customize y-axis to show time format
                            fig.update_yaxes(
                                tickvals=[6, 8, 10, 12, 14, 16, 18, 20, 22],
                                ticktext=['06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00']
                            )
                            
                            # Assign customdata and hovertemplate to each trace
                            for trace in fig.data:
                                if trace.name == 'Check-In':
                                    trace.customdata = trend_df['Check-In']
                                    trace.hovertemplate = 'Date: %{x}<br>Time: %{customdata}<extra></extra>'
                                elif trace.name == 'Check-Out':
                                    trace.customdata = trend_df['Check-Out']
                                    trace.hovertemplate = 'Date: %{x}<br>Time: %{customdata}<extra></extra>'
                            
                            st.plotly_chart(fig, use_container_width=True)
                    

                    with col1:
                        # Pie Chart for Attendance Overview
                        fig = go.Figure(data=[go.Pie(
                            labels=['Present', 'Half Day', 'Leave', 'Holiday', 'Late Arrival', 'Early Arrival', 'Early Exit', 'Overtime'],
                            values=[present, half, leave, holiday, late_arrivals, early_arrivals, early_exits, overtime_days],
                            hole=.4,
                            marker_colors=['#28a745', '#ffc107', '#dc3545', '#17a2b8', '#ed5721', '#3498db', '#5bc0de', '#6f42c1']
                        )])
                        fig.update_layout(
                            title=f"Attendance Overview - {selected_year}",
                            height=400
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                st.markdown(f"### 📅 {selected_year} at a Glance")
                
                # Call the calendar function with the dictionary we built
                display_yearly_calendars(selected_year, attendance_dict)
            
            else:
                st.info(f"No attendance records found for {selected_year}")


###################################################################################################################################
##################################------------------ Tab 3 ----------------------------###########################################
###################################################################################################################################


# TAB 3: Daily Report
with tab3:
    st.subheader("Daily Attendance Report")
    
    report_date = st.date_input("Select Date", value=date.today(), key="report_date")
    
    daily_data = get_daily_attendance(conn, report_date)
    
    if daily_data:
        df_daily = pd.DataFrame(daily_data, 
                               columns=['Employee Name', 'designation', 'Check In', 'Check Out', 
                                        'Status', 'Notes', 'Is Late', 'Is Early', 'Is Overtime', 'Is Early Arrival'])
        
        # Standard work times
        scheduled_in_time = dt_time(9, 30)  # 9:30 AM
        scheduled_out_time = dt_time(18, 0)  # 6:00 PM
        
        # Function to calculate time difference in minutes
        def calculate_time_diff(time_str, reference_time, diff_type):
            """
            Calculate time difference and return formatted string
            diff_type: 'late', 'early', 'overtime', or 'early_arrival'
            """
            if pd.isna(time_str) or time_str == '-' or time_str == '' or time_str is None:
                return ''
            
            try:
                # Parse the time string
                if isinstance(time_str, str):
                    actual_time = pd.to_datetime(time_str).time()
                else:
                    actual_time = time_str
                
                # Convert to datetime for calculation
                ref_datetime = datetime.combine(date.today(), reference_time)
                actual_datetime = datetime.combine(date.today(), actual_time)
                
                # Calculate difference in minutes
                diff = (actual_datetime - ref_datetime).total_seconds() / 60
                
                if diff_type == 'late' and diff > 0:
                    hours = int(diff // 60)
                    mins = int(diff % 60)
                    if hours > 0:
                        return f"🔴 +{hours}h {mins}m"
                    else:
                        return f"🔴 +{mins}m"

                elif diff_type == 'early_arrival' and diff < 0:
                    diff = abs(diff)
                    hours = int(diff // 60)
                    mins = int(diff % 60)
                    if hours > 0:
                        return f"🌅 -{hours}h {mins}m"
                    else:
                        return f"🌅 -{mins}m"
                        
                elif diff_type == 'early' and diff < 0:
                    diff = abs(diff)
                    hours = int(diff // 60)
                    mins = int(diff % 60)
                    if hours > 0:
                        return f"🟡 -{hours}h {mins}m"
                    else:
                        return f"🟡 -{mins}m"
                        
                elif diff_type == 'overtime' and diff > 0:
                    hours = int(diff // 60)
                    mins = int(diff % 60)
                    if hours > 0:
                        return f"🟢 +{hours}h {mins}m"
                    else:
                        return f"🟢 +{mins}m"
                
                return ''
            except Exception as e:
                return ''
        
        # Convert time to AM/PM format
        def format_time_ampm(time_str):
            if pd.isna(time_str) or time_str == '' or time_str is None or time_str == '-':
                return '-'
            try:
                if isinstance(time_str, str):
                    time_obj = pd.to_datetime(time_str).strftime('%I:%M %p')
                else:
                    time_obj = time_str.strftime('%I:%M %p')
                return time_obj
            except:
                return str(time_str)
        
        # Create display columns with time differences
        df_display = df_daily.copy()
        
        # Format times
        df_display['Check In'] = df_display['Check In'].apply(format_time_ampm)
        df_display['Check Out'] = df_display['Check Out'].apply(format_time_ampm)
        
        # Calculate time differences using original time data
        df_display['Late Arrival'] = df_daily.apply(
            lambda row: calculate_time_diff(row['Check In'], scheduled_in_time, 'late') 
            if row['Is Late'] == 1 else '', 
            axis=1
        )

        df_display['Early Arrival'] = df_daily.apply(
            lambda row: calculate_time_diff(row['Check In'], scheduled_in_time, 'early_arrival') 
            if row['Is Early Arrival'] == 1 else '', 
            axis=1
        )
        
        df_display['Early Exit'] = df_daily.apply(
            lambda row: calculate_time_diff(row['Check Out'], scheduled_out_time, 'early') 
            if row['Is Early'] == 1 else '', 
            axis=1
        )
        
        df_display['Overtime'] = df_daily.apply(
            lambda row: calculate_time_diff(row['Check Out'], scheduled_out_time, 'overtime') 
            if row['Is Overtime'] == 1 else '', 
            axis=1
        )
        
        # Statistics
        total_employees = len(daily_data)
        present_count = len([row for row in daily_data if row[4] == 'Present'])
        leave_count = len([row for row in daily_data if row[4] == 'Leave'])
        half_day_count = len([row for row in daily_data if row[4] == 'Half Day'])
        late_count = sum(row[6] for row in daily_data if row[6] == 1)
        early_exit_count = sum(row[7] for row in daily_data if row[7] == 1)
        overtime_count = sum(row[8] for row in daily_data if row[8] == 1)
        early_arrival_count = sum(row[9] for row in daily_data if row[9] == 1)
        
        # Display statistics in 8 columns
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #6f42c1;">{total_employees}</div>
                <div class="stat-label">Total Employees</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #28a745;">{present_count}</div>
                <div class="stat-label">Present</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #dc3545;">{leave_count}</div>
                <div class="stat-label">Leave</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #ffc107;">{half_day_count}</div>
                <div class="stat-label">Half Days</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #ed5721;">{late_count}</div>
                <div class="stat-label">Late</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col6:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #3498db;">{early_arrival_count}</div>
                <div class="stat-label">Early Arrivals</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col7:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #5bc0de;">{early_exit_count}</div>
                <div class="stat-label">Early Exits</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col8:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #28a745;">{overtime_count}</div>
                <div class="stat-label">Overtime</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Display styled dataframe
        render_daily_report_table(df_display)
        
    else:
        st.info("No attendance records found for this date.")



###################################################################################################################################
##################################--------------- Tab 4 ----------------------------##################################
###################################################################################################################################


with tab4:
    st.markdown("""
        <style>
    
        
        /* Summary Stats - Horizontal */
        .stats-container {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.8rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: white;
            padding: 1.25rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            border-left: 3px solid;
            transition: all 0.2s ease;
            margin-bottom: 1rem;
        }
    
        
        .stat-card.employees { border-left-color: #667eea; }
        .stat-card.attendance { border-left-color: #51cf66; }
        .stat-card.ontime { border-left-color: #4dabf7; }
        .stat-card.late { border-left-color: #ff6b6b; }
        
        .stat-label {
            color: #868e96;
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }
        
        .stat-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #212529;
            line-height: 1;
        }
        
        /* Section Headers */
        .section-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin: 2rem 0 1rem 0;
            padding-bottom: 0.75rem;
            border-bottom: 2px solid #e9ecef;
        }
        
        .section-icon {
            font-size: 1.5rem;
        }
        
        .section-title {
            font-size: 1.3rem;
            font-weight: 700;
            color: #212529;
            margin: 0;
        }
        
        .section-subtitle {
            color: #868e96;
            font-size: 0.85rem;
            margin-left: auto;
        }
        
        /* Card Headers */
        .card-header-box {
            padding: 1rem 1.25rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            border-radius: 12px 12px 0 0;
            margin-bottom: 0.5rem;
        }
        
        .card-header-box.late { background: linear-gradient(135deg, #fff5f5 0%, #ffe3e3 100%); }
        .card-header-box.ontime { background: linear-gradient(135deg, #f4fcf7 0%, #d3f9e3 100%); }
        .card-header-box.score { background: linear-gradient(135deg, #f0f9ff 0%, #d0ebff 100%); }
        .card-header-box.leave { background: linear-gradient(135deg, #fff9db 0%, #ffec99 100%); }
        .card-header-box.work { background: linear-gradient(135deg, #f3f0ff 0%, #e5dbff 100%); }
        .card-header-box.early { background: linear-gradient(135deg, #e6fcf5 0%, #c3fae8 100%); }
        .card-header-box.overtime { background: linear-gradient(135deg, #fff5f5 0%, #ffe3e3 100%); }
        .card-header-box.consistent { background: linear-gradient(135deg, #e7f5ff 0%, #d0ebff 100%); }
        
        .card-icon {
            font-size: 1.5rem;
            line-height: 1;
        }
        
        .card-title-text {
            font-size: 1.05rem;
            font-weight: 700;
            color: #212529;
            margin: 0;
            flex: 1;
        }
        
        .card-count {
            font-size: 0.8rem;
            color: #868e96;
            font-weight: 600;
        }
        
        /* Streamlit DataFrame Styling */
        .stDataFrame {
            border: 1px solid #e9ecef;
            border-radius: 0 0 12px 12px;
            overflow: hidden;
        }

        
        /* Smooth Animations */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        </style>
    """, unsafe_allow_html=True)

    # Filters
    col1, col2, col3, col4, col5 = st.columns([0.5, 1, 1, 1, 1], gap="small")

    with col1:
        view_type = st.segmented_control("View Type", ["Yearly", "Monthly"], key="team_view_type_no", default="Monthly")

    with col2:
        # Fetch available years
        available_years = get_all_available_years(conn)
        if not available_years:
            st.warning("No attendance records available.")
            st.selectbox("Year", [], disabled=True)
            st.stop()
        # Default to the most recent year
        default_year_index = 0
        year = st.selectbox(
            "Year",
            available_years,
            index=default_year_index,
            key="team_year"
        )

    with col3:
        month = None
        if view_type == "Monthly" and year:
            # Fetch available months for the selected year
            available_months = get_all_available_months_for_year(conn, year)
            if available_months:
                # Default to the most recent month
                default_month_index = 0
                month = st.selectbox(
                    "Month",
                    available_months,
                    index=default_month_index,
                    format_func=lambda x: calendar.month_name[x],
                    key=f"team_month_for_year_{year}"
                )
            else:
                st.selectbox("Month", [], disabled=True)
        else:  # Yearly or no year selected
            st.selectbox("Month", [], disabled=True, label_visibility="visible", key= "ehfbwifbwlifb")
            
    st.markdown("")
    
    # Fetch data
    from collections import defaultdict
    team_data = get_all_employees_attendance(conn, year, month)
    
    if team_data:
        # Process metrics (same logic)
        employee_metrics = defaultdict(lambda: {
            'name': '', 'designation': '', 'late_arrivals': 0, 'on_time_arrivals': 0,
            'present_days': 0, 'leave_days': 0, 'half_days': 0, 'work_days': 0,
            'early_check_ins': 0, 'overtime_days': 0, 'early_exits': 0, 'max_consecutive_present': 0,
            'holidays': 0
        })
        
        current_employee = None
        current_streak = 0
        last_date = None
        
        for row in team_data:
            if len(row) < 7:
                continue
            emp_id, emp_name, designation, att_date, check_in, check_out, status = row[0], row[1], row[2], row[3], row[4], row[5], row[6]
            
            if not att_date:
                employee_metrics[emp_id]['name'] = emp_name
                employee_metrics[emp_id]['designation'] = designation
                continue
            
            metrics = employee_metrics[emp_id]
            metrics['name'] = emp_name
            metrics['designation'] = designation
            
            if status == 'Present':
                metrics['present_days'] += 1
                metrics['work_days'] += 1
            elif status == 'Half Day':
                metrics['half_days'] += 1
                metrics['work_days'] += 1
            elif status == 'Leave':
                metrics['leave_days'] += 1
            elif status == 'Holiday':
                metrics['holidays'] += 1
            
            check_in_dt = None
            if check_in and isinstance(check_in, timedelta):
                total_seconds = int(check_in.total_seconds())
                hours, minutes = total_seconds // 3600, (total_seconds % 3600) // 60
                try:
                    check_in_dt = dt_time(hours, minutes)
                except ValueError:
                    continue
            
            check_out_dt = None
            if check_out and isinstance(check_out, timedelta):
                total_seconds = int(check_out.total_seconds())
                hours, minutes = total_seconds // 3600, (total_seconds % 3600) // 60
                try:
                    check_out_dt = dt_time(hours, minutes)
                except ValueError:
                    continue
            
            if status in ['Present', 'Half Day']:
                if check_in_dt:
                    if check_in_dt > LATE_THRESHOLD:
                        metrics['late_arrivals'] += 1
                    if check_in_dt <= SCHEDULED_IN:
                        metrics['on_time_arrivals'] += 1
                    if check_in_dt < EARLY_ARRIVAL_THRESHOLD:
                        metrics['early_check_ins'] += 1
                if check_out_dt:
                    if check_out_dt < SCHEDULED_OUT:
                        metrics['early_exits'] += 1
                    if check_out_dt > OVERTIME_THRESHOLD:
                        metrics['overtime_days'] += 1
            
            if emp_id != current_employee or not last_date or att_date != last_date + timedelta(days=1):
                current_streak = 0
            if status == 'Present':
                current_streak += 1
                metrics['max_consecutive_present'] = max(metrics['max_consecutive_present'], current_streak)
            else:
                current_streak = 0
            current_employee = emp_id
            last_date = att_date
        
        working_days = get_month_working_days(conn, year, month) if month else get_year_working_days(conn, year)
        leaderboard_data = []
        
        for emp_id, metrics in employee_metrics.items():
            total_work_days = metrics['work_days']
            attendance_score = (metrics['present_days'] / working_days * 100) if working_days > 0 else 0
            early_on_time_rate = (metrics['on_time_arrivals'] / total_work_days * 100) if total_work_days > 0 else 0
            
            leaderboard_data.append({
                'Employee ID': emp_id, 'Name': metrics['name'], 'Designation': metrics['designation'],
                'Late Arrivals': metrics['late_arrivals'], 'On-Time Arrivals': metrics['on_time_arrivals'],
                'Attendance Score (%)': attendance_score, 'Leave Days': metrics['leave_days'],
                'Work Days (No Leaves)': metrics['work_days'], 'Early Check-Ins': metrics['early_check_ins'],
                'Overtime Days': metrics['overtime_days'], 'Early/On-Time Rate (%)': early_on_time_rate,
                'Total Working Days': working_days
            })
        
        df = pd.DataFrame(leaderboard_data)
        if df.empty:
            st.info("No attendance data for the selected period.")
            st.stop()
        
        total_present_days = sum(m['present_days'] for m in employee_metrics.values())
        total_half_days = sum(m['half_days'] for m in employee_metrics.values())
        total_leave_days = sum(m['leave_days'] for m in employee_metrics.values())
        total_late_arrivals = sum(m['late_arrivals'] for m in employee_metrics.values())
        total_early_exits = sum(m['early_exits'] for m in employee_metrics.values())
        total_overtime_days = sum(m['overtime_days'] for m in employee_metrics.values())
        total_early_arrivals = sum(m['early_check_ins'] for m in employee_metrics.values())
        total_holidays = sum(m.get('holidays', 0) for m in employee_metrics.values())

        # --- Corrected Team Punctuality Score (Percentage-Based) ---
        # Numerator: Total days attended by anyone MINUS total infractions
        total_days_attended_team = total_present_days + total_half_days
        total_punctual_days_team = total_days_attended_team - total_late_arrivals - total_early_exits
        # Denominator: Total days attended by anyone
        team_punctuality_score = (total_punctual_days_team / total_days_attended_team * 100) if total_days_attended_team > 0 else 0

        # --- Corrected Team Attendance Rate ---
        # Numerator: Total days attended (Half days as 0.5)
        total_days_attended_weighted = total_present_days + (total_half_days * 0.5)
        # Denominator: Total possible work days * number of employees
        total_possible_work_days = working_days * len(employee_metrics) 
        team_attendance_rate = (total_days_attended_weighted / total_possible_work_days * 100) if total_possible_work_days > 0 else 0

        # Average Check-in/Check-out
        all_check_ins = []
        all_check_outs = []
        for row in team_data:
            if len(row) >= 6:
                check_in, check_out = row[4], row[5]
                if check_in and isinstance(check_in, timedelta):
                    all_check_ins.append(check_in)
                if check_out and isinstance(check_out, timedelta):
                    all_check_outs.append(check_out)

        avg_check_in_str = 'N/A'
        if all_check_ins:
            avg_seconds = sum(t.total_seconds() for t in all_check_ins) / len(all_check_ins)
            avg_check_in_str = f"{int(avg_seconds // 3600):02d}:{int((avg_seconds % 3600) // 60):02d}"

        avg_check_out_str = 'N/A'
        if all_check_outs:
            avg_seconds = sum(t.total_seconds() for t in all_check_outs) / len(all_check_outs)
            avg_check_out_str = f"{int(avg_seconds // 3600):02d}:{int((avg_seconds % 3600) // 60):02d}"

        if view_type == "Monthly":
            col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
            with col1:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #28a745;">{team_attendance_rate:.1f}%</div>
                    <div class="stat-label">Attendance Rate</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #6f42c1;">{team_punctuality_score:.1f}%</div>
                    <div class="stat-label">Punctuality Rate</div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #ffc107;">{working_days}</div>
                    <div class="stat-label">Working Days</div>
                </div>
                """, unsafe_allow_html=True)
            with col4:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #28a745;">{total_present_days}</div>
                    <div class="stat-label">Present</div>
                </div>
                """, unsafe_allow_html=True)
            with col5:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #dc3545;">{total_leave_days}</div>
                    <div class="stat-label">Leaves</div>
                </div>
                """, unsafe_allow_html=True)
            with col6:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #ffc107;">{total_half_days}</div>
                    <div class="stat-label">Half Days</div>
                </div>
                """, unsafe_allow_html=True)
            with col7:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #ed5721;">{total_late_arrivals}</div>
                    <div class="stat-label">Late</div>
                </div>
                """, unsafe_allow_html=True)

            col8, col9, col10, col11, col12, col13 = st.columns(6)
            with col8:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #3498db;">{avg_check_in_str}</div>
                    <div class="stat-label">Avg Check-In</div>
                </div>
                """, unsafe_allow_html=True)
            with col9:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #3498db;">{avg_check_out_str}</div>
                    <div class="stat-label">Avg Check-Out</div>
                </div>
                """, unsafe_allow_html=True)
            with col10:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #6f42c1;">{len(employee_metrics)}</div>
                    <div class="stat-label">Holidays</div>
                </div>
                """, unsafe_allow_html=True)
            with col11:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #28a745;">{total_overtime_days}</div>
                    <div class="stat-label">Overtime</div>
                </div>
                """, unsafe_allow_html=True)
            with col12:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #3498db;">{total_early_arrivals}</div>
                    <div class="stat-label">Early Arrivals</div>
                </div>
                """, unsafe_allow_html=True)
            with col13:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #5bc0de;">{total_early_exits}</div>
                    <div class="stat-label">Early Exits</div>
                </div>
                """, unsafe_allow_html=True)

        elif view_type == "Yearly":
            col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
            with col1:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #28a745;">{team_attendance_rate:.1f}%</div>
                    <div class="stat-label">Attendance Rate</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #6f42c1;">{team_punctuality_score:.1f}</div>
                    <div class="stat-label">Punctuality Rate</div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #ffc107;">{working_days}</div>
                    <div class="stat-label">Working Days</div>
                </div>
                """, unsafe_allow_html=True)
            with col4:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #28a745;">{total_present_days}</div>
                    <div class="stat-label">Present</div>
                </div>
                """, unsafe_allow_html=True)
            with col5:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #dc3545;">{total_leave_days}</div>
                    <div class="stat-label">Leaves</div>
                </div>
                """, unsafe_allow_html=True)
            with col6:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #ffc107;">{total_half_days}</div>
                    <div class="stat-label">Half Days</div>
                </div>
                """, unsafe_allow_html=True)
            with col7:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #ed5721;">{total_late_arrivals}</div>
                    <div class="stat-label">Late</div>
                </div>
                """, unsafe_allow_html=True)

            col8, col9, col10, col11, col12, col13, col14 = st.columns(7)
            with col8:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #3498db;">{avg_check_in_str}</div>
                    <div class="stat-label">Avg Check-In</div>
                </div>
                """, unsafe_allow_html=True)
            with col9:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #3498db;">{avg_check_out_str}</div>
                    <div class="stat-label">Avg Check-Out</div>
                </div>
                """, unsafe_allow_html=True)
            with col10:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #17a2b8;">{total_holidays}</div>
                    <div class="stat-label">Holidays</div>
                </div>
                """, unsafe_allow_html=True)
            with col11:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #28a745;">{total_overtime_days}</div>
                    <div class="stat-label">Overtime</div>
                </div>
                """, unsafe_allow_html=True)
            with col12:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #3498db;">{total_early_arrivals}</div>
                    <div class="stat-label">Early Arrivals</div>
                </div>
                """, unsafe_allow_html=True)
            with col13:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #5bc0de;">{total_early_exits}</div>
                    <div class="stat-label">Early Exits</div>
                </div>
                """, unsafe_allow_html=True)
            with col14:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value" style="color: #6f42c1;">{len(employee_metrics)}</div>
                    <div class="stat-label">Total Employees</div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Helper function to display leaderboard with Streamlit dataframe
        def display_leaderboard(title, icon, header_class, data_df, columns_to_show, limit=10):
            st.markdown(f"""
                <div class="card-header-box {header_class}">
                    <span class="card-icon">{icon}</span>
                    <span class="card-title-text">{title}</span>
                    <span class="card-count">Top {limit}</span>
                </div>
            """, unsafe_allow_html=True)
            
            # Prepare display dataframe
            display_df = data_df.head(limit)[columns_to_show].copy()
            display_df.insert(0, 'Rank', range(1, len(display_df) + 1))
            
            # Format percentage columns
            for col in display_df.columns:
                if '(%)' in col:
                    display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}%")
            
            st.dataframe(
                display_df,
                width='stretch',
                hide_index=True,
                height=400
            )
        
        # Punctuality Section
        st.markdown("""
            <div class="section-header">
                <span class="section-icon">⏰</span>
                <h2 class="section-title">Punctuality Metrics</h2>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            display_leaderboard(
                "Most On-Time Arrivals", "🟢", "ontime",
                df.nlargest(10, 'On-Time Arrivals'),
                ['Name', 'Designation', 'On-Time Arrivals', 'Total Working Days']
            )
        with col2:
            display_leaderboard(
                "Most Late Arrivals", "🔴", "late",
                df.nlargest(10, 'Late Arrivals'),
                ['Name', 'Designation', 'Late Arrivals', 'Total Working Days']
            )
        
        # Performance Section
        st.markdown("""
            <div class="section-header">
                <span class="section-icon">📊</span>
                <h2 class="section-title">Performance & Attendance</h2>
                <span class="section-subtitle">Overall attendance quality</span>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            display_leaderboard(
                "Best Attendance Score", "📈", "score",
                df.nlargest(10, 'Attendance Score (%)'),
                ['Name', 'Designation', 'Attendance Score (%)', 'Total Working Days']
            )
        with col2:
            display_leaderboard(
                "Most Consistent Early/On-Time", "⭐", "consistent",
                df.nlargest(10, 'Early/On-Time Rate (%)'),
                ['Name', 'Designation', 'Early/On-Time Rate (%)', 'Total Working Days']
            )
        
        # Dedication Section
        st.markdown("""
            <div class="section-header">
                <span class="section-icon">💼</span>
                <h2 class="section-title">Work Dedication</h2>
                <span class="section-subtitle">Extra effort and commitment</span>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            display_leaderboard(
                "Most Work Days", "💪", "work",
                df.nlargest(10, 'Work Days (No Leaves)'),
                ['Name', 'Designation', 'Work Days (No Leaves)', 'Total Working Days']
            )
        with col2:
            display_leaderboard(
                "Most Early Check-Ins", "🌅", "early",
                df.nlargest(10, 'Early Check-Ins'),
                ['Name', 'Designation', 'Early Check-Ins', 'Total Working Days']
            )
        
        # Additional Metrics
        st.markdown("""
            <div class="section-header">
                <span class="section-icon">📋</span>
                <h2 class="section-title">Additional Insights</h2>
                <span class="section-subtitle">Leave and overtime patterns</span>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            display_leaderboard(
                "Most Leave Days", "🏖️", "leave",
                df.nlargest(10, 'Leave Days'),
                ['Name', 'Designation', 'Leave Days', 'Total Working Days']
            )
        with col2:
            display_leaderboard(
                "Most Overtime Days", "🌙", "overtime",
                df.nlargest(10, 'Overtime Days'),
                ['Name', 'Designation', 'Overtime Days', 'Total Working Days']
            )
        
    else:
        st.info("No attendance records found for the selected period.")



###################################################################################################################################
##################################--------------- Tab 5 ----------------------------##################################
###################################################################################################################################

# TAB 4: Manage Employees

with tab5:
    st.subheader("Employee Management")

    col1, col2 = st.columns([2, 1])

    with col2:
        st.markdown("##### Add New Employee")
        with st.form("add_employee_form", border=True):
            emp_code = st.text_input("Employee Code*")
            emp_name = st.text_input("Employee Name*")
            emp_email = st.text_input("Employee Email*")
            emp_dept = st.text_input("Designation")
            submitted = st.form_submit_button("➕ Add Employee", width='stretch', type="primary")

            if submitted:
                if emp_name and emp_email and emp_code:
                    try:
                        with conn.session as s:
                            s.execute(text("""
                                INSERT INTO employees (employee_code, employee_name, employee_email, designation)
                                VALUES (:code, :name, :email, :dept)
                            """), {"code": emp_code, "name": emp_name, "email": emp_email, "dept": emp_dept})
                            s.commit()
                        st.success(f"✅ Employee '{emp_name}' added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding employee: {e}")
                else:
                    st.warning("Please fill in all required fields (Code, Name, and Email)")

    with col1:
        all_employees = get_all_employees_with_status(conn)
        if all_employees:
            df = pd.DataFrame(all_employees, columns=['employee_id', 'employee_code', 'employee_name', 'designation', 'employment_status'])
            
            active_count = (df['employment_status'] == 'Active').sum()
            inactive_count = (df['employment_status'] == 'Inactive').sum()
            
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                st.metric("Total Employees", f"{active_count + inactive_count}")
            with m_col2:
                st.metric("Active", f"{active_count}")
            with m_col3:
                st.metric("Inactive", f"{inactive_count}")
            st.markdown("---")

            edit_mode = st.checkbox("Edit Employees")
            if edit_mode:
                st.info("You are in edit mode. Modify the table below and click 'Save Changes'.")
                edited_df = st.data_editor(
                    df,
                    width='stretch',
                    hide_index=True,
                    column_config={
                        "employee_id": None, # Hide employee_id
                        "employee_code": st.column_config.TextColumn("Employee Code", disabled=True),
                        "employee_name": "Name",
                        "designation": "Designation",
                        "employment_status": st.column_config.SelectboxColumn(
                            "Status",
                            options=["Active", "Inactive"],
                            required=True,
                        )
                    },
                    key="employee_editor",
                    height=1000
                )
                if st.button("Save Changes", type="primary"):
                    # Compare original df with edited df to find changes
                    original_df = df.set_index('employee_id')
                    edited_df_indexed = edited_df.set_index('employee_id')
                    # Find rows where any column has changed
                    changed_rows_mask = (original_df != edited_df_indexed).any(axis=1)
                    if not changed_rows_mask.any():
                        st.info("No changes to save.")
                    else:
                        update_count = 0
                        for emp_id in original_df[changed_rows_mask].index:
                            details = edited_df_indexed.loc[emp_id].to_dict()
                            if update_employee(conn, emp_id, details):
                                update_count += 1
                        if update_count > 0:
                            st.success(f"Successfully updated {update_count} employee(s).")
                            st.rerun()
            else:
                def style_status(row):
                    if row.employment_status == 'Active':
                        return ['background-color: #d4edda; color: #155724;'] * len(row)
                    elif row.employment_status == 'Inactive':
                        return ['background-color: #f8d7da; color: #721c24;'] * len(row)
                    return [''] * len(row)

                df_display = df[['employee_code', 'employee_name', 'designation', 'employment_status']]
                st.dataframe(
                    df_display.style.apply(style_status, axis=1),
                    width='stretch',
                    hide_index=True,
                    column_config={
                        "employee_code": "Employee Code",
                        "employee_name": "Name",
                        "designation": "Designation",
                        "employment_status": "Status"
                    },
                    height=1000
                )
        else:
            st.info("No employees in the system yet.")

