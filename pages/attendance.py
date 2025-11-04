import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date, time as dt_time
import calendar
from sqlalchemy import text
import plotly.express as px
import plotly.graph_objects as go

# Page Configuration
st.set_page_config(page_title="Attendance Management", page_icon="📅", layout="wide")


# Custom CSS for better UI
st.markdown("""
<style>
    /* Main container styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
    }
    
    .stat-label {
        color: #666;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
    
    /* Modern Calendar styling */
    .calendar-container {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin: 1rem 0;
    }
    
    .calendar-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        text-align: center;
        font-weight: bold;
        font-size: 1.2rem;
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
        background: linear-gradient(135deg, #e8f4fe 0%, #d1e9ff 100%);
        border: 1px solid #4d94e6 !important;
    }

    .status-absent {
        background: linear-gradient(135deg, #fde8e8 0%, #f9d6d6 100%);
        border: 1px solid #e05c5c !important;
    }

    .status-half-day {
        background: linear-gradient(135deg, #fff8e0 0%, #ffefbf 100%);
        border: 1px solid #e6b400 !important;
    }

    .status-leave {
        background: linear-gradient(135deg, #e8f6fa 0%, #d6f0f7 100%);
        border: 1px solid #4db8d1 !important;
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
    
    /* Form styling */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
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

def connect_db():
    """Connect to MySQL database"""
    try:
        @st.cache_resource
        def get_connection():
            return st.connection('attendance', type='sql')
        conn = get_connection()
        return conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()


def init_database(conn):
    """Initialize attendance tables if they don't exist"""
    try:
        with conn.session as s:
            # Create employees table
            s.execute(text("""
                CREATE TABLE IF NOT EXISTS employees (
                    employee_id INT PRIMARY KEY AUTO_INCREMENT,
                    employee_name VARCHAR(100) NOT NULL,
                    employee_email VARCHAR(100) UNIQUE,
                    department VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create attendance table
            s.execute(text("""
                CREATE TABLE IF NOT EXISTS attendance (
                    attendance_id INT PRIMARY KEY AUTO_INCREMENT,
                    employee_id INT NOT NULL,
                    attendance_date DATE NOT NULL,
                    check_in_time TIME,
                    check_out_time TIME,
                    status ENUM('Present', 'Absent', 'Half Day', 'Leave', 'Holiday') DEFAULT 'Absent',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
                    UNIQUE KEY unique_employee_date (employee_id, attendance_date)
                )
            """))
            
            # Create holidays table
            s.execute(text("""
                CREATE TABLE IF NOT EXISTS holidays (
                    holiday_id INT PRIMARY KEY AUTO_INCREMENT,
                    holiday_date DATE NOT NULL UNIQUE,
                    holiday_name VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            s.commit()
    except Exception as e:
        st.error(f"Error initializing database: {e}")

def get_all_employees(conn):
    """Fetch all employees"""
    try:
        with conn.session as s:
            result = s.execute(text("SELECT employee_id, employee_name, department FROM employees ORDER BY employee_name"))
            return result.fetchall()
    except Exception as e:
        st.error(f"Error fetching employees: {e}")
        return []
    
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

def get_employee_monthly_attendance(conn, employee_id, year, month):
    """Get monthly attendance for an employee"""
    try:
        with conn.session as s:
            result = s.execute(text("""
                SELECT attendance_date, check_in_time, check_out_time, status, notes
                FROM attendance
                WHERE employee_id = :emp_id 
                AND YEAR(attendance_date) = :year 
                AND MONTH(attendance_date) = :month
                ORDER BY attendance_date
            """), {"emp_id": employee_id, "year": year, "month": month})
            return result.fetchall()
    except Exception as e:
        st.error(f"Error fetching monthly attendance: {e}")
        return []

def get_employee_yearly_attendance(conn, employee_id, year):
    """Get yearly attendance statistics"""
    try:
        with conn.session as s:
            result = s.execute(text("""
                SELECT 
                    COUNT(*) as total_days,
                    SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present_days,
                    SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent_days,
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

def get_available_years_months(conn, employee_id):
    """Get available years and months from attendance data"""
    try:
        with conn.session as s:
            result = s.execute(text("""
                SELECT DISTINCT YEAR(attendance_date) as year, MONTH(attendance_date) as month
                FROM attendance
                WHERE employee_id = :emp_id
                ORDER BY year DESC, month DESC
            """), {"emp_id": employee_id})
            data = result.fetchall()
            
            years = sorted(list(set([row[0] for row in data])), reverse=True)
            months_by_year = {}
            for year, month in data:
                if year not in months_by_year:
                    months_by_year[year] = []
                months_by_year[year].append(month)
            
            return years, months_by_year
    except Exception as e:
        st.error(f"Error fetching available dates: {e}")
        return [], {}
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

def get_daily_attendance(conn, attendance_date):
    """Get attendance for all employees on a specific date"""
    try:
        with conn.session as s:
            result = s.execute(text("""
                SELECT 
                    e.employee_name,
                    e.department,
                    COALESCE(a.check_in_time, '-') as check_in,
                    COALESCE(a.check_out_time, '-') as check_out,
                    COALESCE(a.status, 'Absent') as status,
                    COALESCE(a.notes, '') as notes
                FROM employees e
                LEFT JOIN attendance a ON e.employee_id = a.employee_id 
                    AND a.attendance_date = :att_date
                ORDER BY e.employee_name
            """), {"att_date": attendance_date})
            return result.fetchall()
    except Exception as e:
        st.error(f"Error fetching daily attendance: {e}")
        return []

def determine_day_status(status, check_in_time, check_out_time):
    """Determine the visual status of a day based on attendance data"""
    if status == 'Holiday':
        return 'status-holiday', '🏖️ Holiday'
    elif status == 'Leave':
        return 'status-leave', '🏝️ Leave'
    elif status == 'Half Day':
        return 'status-half-day', '🕐 Half Day'
    elif status == 'Absent':
        return 'status-absent', '❌ Absent'
    elif status == 'Present':
        # Check for late arrival (after 9:30 AM)
        late_threshold = dt_time(9, 30)
        early_out_threshold = dt_time(17, 0)  # 5:00 PM
        late_checkout_threshold = dt_time(19, 0)  # 7:00 PM
        
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
        
        is_late = check_in_time and check_in_time > late_threshold
        is_early_out = check_out_time and check_out_time < early_out_threshold
        is_late_checkout = check_out_time and check_out_time > late_checkout_threshold
        
        if is_late and is_early_out:
            return 'status-early-out', '⚠️ Late + Early'
        elif is_late:
            return 'status-late', '⏰ Late Arrival'
        elif is_early_out:
            return 'status-early-out', '🏃 Early Exit'
        elif is_late_checkout:
            return 'status-overtime', '🌙 Overtime'
        else:
            return 'status-present', '✅ Present'
    
    return '', ''

def inject_custom_css():
    """Inject custom CSS for calendar styling"""
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
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                transform: translateY(-2px);
                transition: all 0.3s;
            }
            .day-card-present { background-color: #D4EDDA; border-color: #28a745; }
            .day-card-late { background-color: #FFE5D0; border-color: #fd7e14; }
            .day-card-early-out { background-color: #F8E6FF; border-color: #e83e8c; }
            .day-card-half-day { background-color: #FFF3CD; border-color: #ffc107; }
            .day-card-leave { background-color: #D1ECF1; border-color: #17a2b8; }
            .day-card-holiday { background-color: #E2D9F3; border-color: #6f42c1; }
            .day-card-absent { background-color: #F8D7DA; border-color: #dc3545; }
            .day-card-empty { background-color: #FAFAFA; border-style: dashed; }
            .day-number { font-weight: bold; font-size: 1.2em; text-align: left; }
            .day-name { font-size: 0.9em; color: #666; }
            .day-summary { font-size: 0.85em; margin-top: 5px; line-height: 1.3; overflow-y: auto; max-height: 70px; }
            .header-card {
                padding-bottom: 0.75rem;
                font-weight: 600;
                font-size: 0.75rem;
                text-align: center;
                color: #313438;
                margin-bottom: 1rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                border-bottom: 2px solid #d0d2d6;
                background-color: transparent;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 40px;
            }
        </style>
    """, unsafe_allow_html=True)

def render_day_card(day_date, attendance_dict, is_current_month, holidays=None):
    """Render a single day card"""
    if not is_current_month:
        st.markdown('<div class="day-card day-card-empty"></div>', unsafe_allow_html=True)
        return
    
    day_name = calendar.day_abbr[day_date.weekday()]
    
    # Check if it's a holiday
    is_holiday = holidays and day_date in holidays
    holiday_name = holidays.get(day_date, '') if holidays else ''
    
    if day_date.day in attendance_dict:
        data = attendance_dict[day_date.day]
        status_class, status_label = determine_day_status(
            data['status'], 
            data['check_in'], 
            data['check_out']
        )
        
        # Build summary lines
        summary_lines = []
        
        # Show holiday name if it's a holiday
        if is_holiday:
            summary_lines.append(f"<strong>🏖️ {holiday_name}</strong>")
        else:
            summary_lines.append(f"<strong>{status_label}</strong>")
        
        if data['status'] not in ['Holiday', 'Leave', 'Absent']:
            check_in_str = data['check_in'].strftime('%I:%M %p') if data['check_in'] else '-'
            check_out_str = data['check_out'].strftime('%I:%M %p') if data['check_out'] else '-'
            summary_lines.append(f"🕐 In: {check_in_str}")
            summary_lines.append(f"🕔 Out: {check_out_str}")
        
        if data['notes']:
            summary_lines.append(f"📝 {data['notes'][:25]}...")
        
        summary_text = "<br>".join(summary_lines)
        css_class = status_class
    else:
        # Check if it's a holiday even without attendance record
        if is_holiday:
            summary_text = f"<strong>🏖️ {holiday_name}</strong>"
            css_class = "day-card-holiday"
        else:
            summary_text = "📅 No Record"
            css_class = "day-card-empty"
    
    card_html = f"""
    <div class="day-card {css_class}">
        <div>
            <div class="day-number">{day_date.day}</div>
            <div class="day-name">{day_name}</div>
            <div class="day-summary">{summary_text}</div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def create_modern_calendar(year, month, attendance_data):
    """Create a modern calendar view using Streamlit columns"""
    # Inject CSS
    inject_custom_css()
    
    # Create attendance dictionary
    attendance_dict = {}
    for row in attendance_data:
        att_date, check_in, check_out, status, notes = row
        
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
            'notes': notes
        }
    
    # Display month header
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1rem; 
                    text-align: center; font-weight: bold; font-size: 1.3rem;">
            {calendar.month_name[month]} {year}
        </div>
    """, unsafe_allow_html=True)
    
    # Legend
    st.markdown("""
        <div style="display: flex; flex-wrap: wrap; gap: 15px; margin: 1rem 0; padding: 1rem; 
                    background: #f8f9fa; border-radius: 10px; justify-content: center;">
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                <div style="width: 20px; height: 20px; border-radius: 4px; background: #D4EDDA; border: 2px solid #28a745;"></div>
                <span>Present</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                <div style="width: 20px; height: 20px; border-radius: 4px; background: #FFE5D0; border: 2px solid #fd7e14;"></div>
                <span>Late</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                <div style="width: 20px; height: 20px; border-radius: 4px; background: #F8E6FF; border: 2px solid #e83e8c;"></div>
                <span>Early Out</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                <div style="width: 20px; height: 20px; border-radius: 4px; background: #FFF3CD; border: 2px solid #ffc107;"></div>
                <span>Half Day</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                <div style="width: 20px; height: 20px; border-radius: 4px; background: #D1ECF1; border: 2px solid #17a2b8;"></div>
                <span>Leave</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                <div style="width: 20px; height: 20px; border-radius: 4px; background: #E2D9F3; border: 2px solid #6f42c1;"></div>
                <span>Holiday</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                <div style="width: 20px; height: 20px; border-radius: 4px; background: #F8D7DA; border: 2px solid #dc3545;"></div>
                <span>Absent</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Day headers
    header_cols = st.columns(7)
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for i, day in enumerate(days):
        with header_cols[i]:
            st.markdown(f'<div class="header-card">{day}</div>', unsafe_allow_html=True)
    
    # Calendar grid
    cal = calendar.Calendar()
    for week in cal.monthdatescalendar(year, month):
        cols = st.columns(7)
        for i, day_date in enumerate(week):
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
    header_cols = st.columns(7)
    days = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
    for i, day in enumerate(days):
        with header_cols[i]:
            st.markdown(f'<div style="text-align: center; font-size: 0.7rem; font-weight: 600; color: #666; margin-bottom: 4px;">{day}</div>', unsafe_allow_html=True)
    
    # Calendar grid
    cal = calendar.Calendar()
    for week in cal.monthdatescalendar(year, month):
        cols = st.columns(7)
        for i, day_date in enumerate(week):
            with cols[i]:
                is_current_month = (day_date.month == month)
                render_mini_day_card(day_date, attendance_dict, is_current_month)

# Initialize database
conn = connect_db()
init_database(conn)


# Header
st.markdown("""
<div class="main-header">
    <h1>📅 Employee Attendance Management</h1>
    <p>Track and manage employee attendance efficiently</p>
</div>
""", unsafe_allow_html=True)

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["📝 Mark Attendance", "👤 Individual View", "📊 Daily Report", "➕ Add Employee"])

# TAB 1: Mark Attendance
with tab1:
    st.subheader("Mark Employee Attendance")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        employees = get_all_employees(conn)
        if employees:
            employee_options = {f"{emp[1]} ({emp[2]})": emp[0] for emp in employees}
            selected_employee = st.selectbox("Select Employee", list(employee_options.keys()))
            selected_employee_id = employee_options[selected_employee]
        else:
            st.warning("No employees found. Please add employees first.")
            selected_employee_id = None
    
    with col2:
        attendance_date = st.date_input("Attendance Date", value=date.today())
    
    if selected_employee_id:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            check_in_time = st.time_input("Check-In Time", value=datetime.strptime("09:00", "%H:%M").time())
        
        with col2:
            check_out_time = st.time_input("Check-Out Time", value=datetime.strptime("18:00", "%H:%M").time())
        
        with col3:
            status = st.selectbox("Status", ["Present", "Absent", "Half Day", "Leave", "Holiday"])
        
        notes = st.text_area("Notes (Optional)", placeholder="Add any additional notes...")
        
        if st.button("💾 Save Attendance", use_container_width=True):
            if mark_attendance(conn, selected_employee_id, attendance_date, 
                             check_in_time, check_out_time, status, notes):
                st.success(f"✅ Attendance marked successfully for {attendance_date}")
                st.rerun()

# TAB 2: Individual Employee View
with tab2:
    st.subheader("Individual Employee Attendance")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        employees = get_all_employees(conn)
        if employees:
            employee_options = {f"{emp[1]} ({emp[2]})": emp[0] for emp in employees}
            selected_emp = st.selectbox("Select Employee ", list(employee_options.keys()), key="ind_emp")
            selected_emp_id = employee_options[selected_emp]
        else:
            st.warning("No employees found.")
            selected_emp_id = None
    
    with col2:
        view_type = st.radio("View Type", ["Monthly", "Yearly"], horizontal=True)
    
    with col3:
        current_year = datetime.now().year
        selected_year = st.selectbox("Year", range(current_year, current_year - 5, -1))
    
    if selected_emp_id:
        if view_type == "Monthly":
            selected_month = st.selectbox("Month", range(1, 13), 
                                        format_func=lambda x: calendar.month_name[x],
                                        index=datetime.now().month - 1)
            
            # Get monthly attendance
            attendance_data = get_employee_monthly_attendance(conn, selected_emp_id, selected_year, selected_month)
            
            if attendance_data:
                # Create DataFrame
                df = pd.DataFrame(attendance_data, 
                                columns=['Date', 'Check In', 'Check Out', 'Status', 'Notes'])
                
                # Display statistics
                col1, col2, col3, col4 = st.columns(4)
                
                present_days = len([row for row in attendance_data if row[3] == 'Present'])
                absent_days = len([row for row in attendance_data if row[3] == 'Absent'])
                half_days = len([row for row in attendance_data if row[3] == 'Half Day'])
                total_days = len(attendance_data)
                
                with col1:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value">{present_days}</div>
                        <div class="stat-label">Present Days</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #dc3545;">{absent_days}</div>
                        <div class="stat-label">Absent Days</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ffc107;">{half_days}</div>
                        <div class="stat-label">Half Days</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #28a745;">{attendance_rate:.1f}%</div>
                        <div class="stat-label">Attendance Rate</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Modern Calendar view
                st.markdown("### 📅 Calendar View")
                create_modern_calendar(selected_year, selected_month, attendance_data)
                
                st.markdown("---")
                
                # Display table
                st.markdown("### 📋 Detailed Records")
                st.dataframe(df, use_container_width=True, hide_index=True)
                
            else:
                st.info(f"No attendance records found for {calendar.month_name[selected_month]} {selected_year}")
        
        else:  # Yearly view
            yearly_stats = get_employee_yearly_attendance(conn, selected_emp_id, selected_year)
            
            if yearly_stats and yearly_stats[0] > 0:
                total, present, absent, half, leave, holiday = yearly_stats
                
                # Display statistics
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                
                with col1:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value">{total}</div>
                        <div class="stat-label">Total Days</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value">{present}</div>
                        <div class="stat-label">Present</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #dc3545;">{absent}</div>
                        <div class="stat-label">Absent</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ffc107;">{half}</div>
                        <div class="stat-label">Half Days</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col5:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #17a2b8;">{leave}</div>
                        <div class="stat-label">Leaves</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col6:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #6f42c1;">{holiday}</div>
                        <div class="stat-label">Holidays</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Pie chart
                col_chart, col_space = st.columns([2, 1])
                with col_chart:
                    fig = go.Figure(data=[go.Pie(
                        labels=['Present', 'Absent', 'Half Day', 'Leave', 'Holiday'],
                        values=[present, absent, half, leave, holiday],
                        hole=.4,
                        marker_colors=['#28a745', '#dc3545', '#ffc107', '#17a2b8', '#6f42c1']
                    )])
                    fig.update_layout(
                        title=f"Attendance Distribution - {selected_year}",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                
                # Get full year data
                st.markdown("### 📅 Year at a Glance")
                year_data = get_employee_full_year_attendance(conn, selected_emp_id, selected_year)
                
                # Create attendance dictionary for all months
                attendance_dict = {}
                for row in year_data:
                    att_date, check_in, check_out, status, notes = row
                    date_key = att_date.strftime("%Y-%m-%d")
                    attendance_dict[date_key] = {
                        'check_in': check_in,
                        'check_out': check_out,
                        'status': status,
                        'notes': notes
                    }
                
                # Display all 12 months in a grid
                st.markdown("### 📅 Year at a Glance - All Months")
                
                # Inject CSS for mini calendars
                inject_custom_css()
                
                # Create attendance dictionary for all months
                attendance_dict = {}
                for row in year_data:
                    att_date, check_in, check_out, status, notes = row
                    date_key = att_date.strftime("%Y-%m-%d")
                    
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
                    
                    attendance_dict[date_key] = {
                        'check_in': check_in,
                        'check_out': check_out,
                        'status': status,
                        'notes': notes
                    }
                
                # Display months in a 3x4 grid
                for row_idx in range(4):
                    cols = st.columns(3)
                    for col_idx in range(3):
                        month_num = row_idx * 3 + col_idx + 1
                        if month_num <= 12:
                            with cols[col_idx]:
                                with st.container():
                                    st.markdown("""
                                        <div style="background: white; border-radius: 12px; padding: 1rem; 
                                                    box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 1rem;">
                                    """, unsafe_allow_html=True)
                                    create_mini_month_calendar(selected_year, month_num, attendance_dict)
                                    st.markdown("</div>", unsafe_allow_html=True)
                
            else:
                st.info(f"No attendance records found for {selected_year}")

# TAB 3: Daily Report
with tab3:
    st.subheader("Daily Attendance Report")
    
    report_date = st.date_input("Select Date", value=date.today(), key="report_date")
    
    daily_data = get_daily_attendance(conn, report_date)
    
    if daily_data:
        df_daily = pd.DataFrame(daily_data, 
                               columns=['Employee Name', 'Department', 'Check In', 'Check Out', 'Status', 'Notes'])
        
        # Statistics
        total_employees = len(daily_data)
        present_count = len([row for row in daily_data if row[4] == 'Present'])
        absent_count = len([row for row in daily_data if row[4] == 'Absent'])
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{total_employees}</div>
                <div class="stat-label">Total Employees</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{present_count}</div>
                <div class="stat-label">Present</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #dc3545;">{absent_count}</div>
                <div class="stat-label">Absent</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            attendance_pct = (present_count / total_employees * 100) if total_employees > 0 else 0
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color: #28a745;">{attendance_pct:.1f}%</div>
                <div class="stat-label">Attendance %</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Filter by status
        filter_status = st.multiselect("Filter by Status", 
                                      ["Present", "Absent", "Half Day", "Leave", "Holiday"],
                                      default=["Present", "Absent", "Half Day", "Leave", "Holiday"])
        
        df_filtered = df_daily[df_daily['Status'].isin(filter_status)]
        
        # Display table with color coding
        st.dataframe(
            df_filtered.style.applymap(
                lambda x: 'background-color: #d4edda' if x == 'Present' 
                else ('background-color: #f8d7da' if x == 'Absent' 
                else ('background-color: #fff3cd' if x == 'Half Day'
                else ('background-color: #d1ecf1' if x == 'Leave'
                else ('background-color: #e2d9f3' if x == 'Holiday' else '')))),
                subset=['Status']
            ),
            use_container_width=True,
            hide_index=True
        )
        
        # Download button
        csv = df_daily.to_csv(index=False)
        st.download_button(
            label="📥 Download Report (CSV)",
            data=csv,
            file_name=f"attendance_report_{report_date}.csv",
            mime="text/csv"
        )
    else:
        st.info("No attendance records found for this date.")

# TAB 4: Add Employee
with tab4:
    st.subheader("Add New Employee")
    
    with st.form("add_employee_form"):
        emp_name = st.text_input("Employee Name*")
        emp_email = st.text_input("Employee Email*")
        emp_dept = st.text_input("Department")
        
        submitted = st.form_submit_button("➕ Add Employee", use_container_width=True)
        
        if submitted:
            if emp_name and emp_email:
                try:
                    with conn.session as s:
                        s.execute(text("""
                            INSERT INTO employees (employee_name, employee_email, department)
                            VALUES (:name, :email, :dept)
                        """), {"name": emp_name, "email": emp_email, "dept": emp_dept})
                        s.commit()
                    st.success(f"✅ Employee '{emp_name}' added successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding employee: {e}")
            else:
                st.warning("Please fill in all required fields (Name and Email)")
    
    st.markdown("---")
    st.subheader("Existing Employees")
    
    employees = get_all_employees(conn)
    if employees:
        df_employees = pd.DataFrame(employees, columns=['ID', 'Name', 'Department'])
        st.dataframe(df_employees, use_container_width=True, hide_index=True)
    else:
        st.info("No employees in the system yet.")

