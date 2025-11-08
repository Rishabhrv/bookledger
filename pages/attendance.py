import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date, time as dt_time
import calendar
from sqlalchemy import text
import plotly.express as px
import plotly.graph_objects as go

# --- Attendance Logic Constants ---
SCHEDULED_IN = dt_time(9, 30)
SCHEDULED_OUT = dt_time(18, 0)
LATE_THRESHOLD = (datetime.combine(date.min, SCHEDULED_IN) + timedelta(minutes=5)).time()
EARLY_ARRIVAL_THRESHOLD = (datetime.combine(date.min, SCHEDULED_IN) - timedelta(minutes=8)).time()
OVERTIME_THRESHOLD = (datetime.combine(date.min, SCHEDULED_OUT) + timedelta(minutes=10)).time()

# Page Configuration
st.set_page_config(page_title="Attendance Management", page_icon="📅", layout="wide")


# Custom CSS for better UI
st.markdown("""
<style>
    .block-container {
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 100%;
    }
    
    .stat-card {
        background: white;
        padding: 0.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 3px solid #667eea;
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
                    designation VARCHAR(50),
                    employment_status ENUM('Active', 'Inactive') NOT NULL DEFAULT 'Active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Add the column for backward compatibility. Ignore error if it already exists.
            try:
                s.execute(text("ALTER TABLE employees ADD COLUMN employment_status ENUM('Active', 'Inactive') NOT NULL DEFAULT 'Active'"))
                s.commit()
            except Exception:
                s.rollback()  # The column probably already exists.
            
            # Create attendance table
            s.execute(text("""
                CREATE TABLE IF NOT EXISTS attendance (
                    attendance_id INT PRIMARY KEY AUTO_INCREMENT,
                    employee_id INT NOT NULL,
                    attendance_date DATE NOT NULL,
                    check_in_time TIME,
                    check_out_time TIME,
                    status ENUM('Present', 'Half Day', 'Leave', 'Holiday') DEFAULT 'Present',
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
            result = s.execute(text("SELECT employee_id, employee_name, designation, employment_status FROM employees ORDER BY employee_name"))
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
    
# Function to fetch available months and years from attendance table
def get_available_months_years(conn):
    try:
        with conn.session as s:
            result = s.execute(text("""
                SELECT DISTINCT YEAR(attendance_date) as year, MONTH(attendance_date) as month
                FROM attendance
                ORDER BY year DESC, month DESC
            """)).fetchall()
            
            years = sorted(set(row[0] for row in result), reverse=True)
            months = sorted(set(row[1] for row in result))
            return years, months
    except Exception as e:
        st.error(f"Error fetching months and years: {e}")
        return [], []

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

            /* Custom Daily Report Table */
            .daily-report-table {
                width: 100%;
                border-collapse: separate; /* For rounded corners on cells */
                border-spacing: 0 8px; /* Space between rows */
                margin-top: 1.5rem;
            }

            .daily-report-table th {
                background-color: #f0f2f6; /* Light grey header background */
                padding: 12px 15px;
                text-align: left;
                font-weight: 600;
                color: #495057;
                border-bottom: 2px solid #e9ecef;
                position: sticky;
                top: 0;
                z-index: 1;
            }

            .daily-report-table th:first-child {
                border-top-left-radius: 8px;
            }

            .daily-report-table th:last-child {
                border-top-right-radius: 8px;
            }

            .daily-report-table td {
                background-color: #ffffff; /* White cell background */
                padding: 12px 15px;
                border-bottom: 1px solid #e9ecef;
                vertical-align: middle;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05); /* Subtle shadow for rows */
            }

            .daily-report-table tr:last-child td {
                border-bottom: none;
            }

            .daily-report-table tbody tr {
                transition: all 0.2s ease-in-out;
            }

            .daily-report-table tbody tr:hover {
                background-color: #f8f9fa; /* Light hover effect */
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            }

            /* Status Badges - similar to calendar, but for table cells */
            .status-badge {
                display: inline-block;
                padding: 5px 10px;
                border-radius: 20px;
                font-size: 0.85rem;
                font-weight: 600;
                text-align: center;
            }

            .status-Present { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .status-Half-Day { background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
            .status-Leave { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .status-Holiday { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
            .status-Absent { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; } /* Assuming Absent is similar to Leave for styling */

            /* Exception Indicators */
            .exception-indicator {
                font-weight: 600;
                font-size: 0.85rem;
                padding: 3px 6px;
                border-radius: 4px;
                margin-right: 5px;
            }
            .exception-late { background-color: #ffe6e6; color: #d9534f; } /* Red for late */
            .exception-early-arrival { background-color: #e0f7ff; color: #3498db; } /* Blue for early arrival */
            .exception-early { background-color: #fff8e6; color: #f0ad4e; } /* Orange for early exit */
            .exception-overtime { background-color: #e6f9e6; color: #5cb85c; } /* Green for overtime */
        </style>
    """, unsafe_allow_html=True)

def render_daily_report_table(df_display):
    """Renders a custom HTML table for the daily attendance report."""
    
    # Start table HTML
    table_html = '<table class="daily-report-table"><thead><tr>'
    
    # Table Headers
    headers = ['Employee Name', 'Designation', 'Check In', 'Check Out', 'Status', 'Late', 'Early Arrival', 'Early Exit', 'Overtime', 'Notes']
    for header in headers:
        table_html += f'<th>{header}</th>'
    table_html += '</tr></thead><tbody>'
    
    # Table Rows
    for index, row in df_display.iterrows():
        table_html += '<tr>'
        
        # Employee Name
        table_html += f'<td>{row["Employee Name"]}</td>'
        
        # Designation
        table_html += f'<td>{row["designation"]}</td>'
        
        # Check In
        table_html += f'<td>{row["Check In"]}</td>'
        
        # Check Out
        table_html += f'<td>{row["Check Out"]}</td>'
        
        # Status
        status_class = row["Status"].replace(" ", "-") # e.g., "Half Day" -> "Half-Day"
        table_html += f'<td><span class="status-badge status-{status_class}">{row["Status"]}</span></td>'
        
        # Late Arrival
        late_val = row["Late Arrival"]
        if late_val:
            table_html += f'<td><span class="exception-indicator exception-late">{late_val}</span></td>'
        else:
            table_html += '<td>-</td>'

        # Early Arrival
        early_arrival_val = row["Early Arrival"]
        if early_arrival_val:
            table_html += f'<td><span class="exception-indicator exception-early-arrival">{early_arrival_val}</span></td>'
        else:
            table_html += '<td>-</td>'
            
        # Early Exit
        early_val = row["Early Exit"]
        if early_val:
            table_html += f'<td><span class="exception-indicator exception-early">{early_val}</span></td>'
        else:
            table_html += '<td>-</td>'
            
        # Overtime
        overtime_val = row["Overtime"]
        if overtime_val:
            table_html += f'<td><span class="exception-indicator exception-overtime">{overtime_val}</span></td>'
        else:
            table_html += '<td>-</td>'
            
        # Notes
        table_html += f'<td>{row["Notes"]}</td>'
        
        table_html += '</tr>'
        
    table_html += '</tbody></table>'
    
    st.markdown(table_html, unsafe_allow_html=True)

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
            'is_overtime': bool(is_overtime)
        }
    
    # Display month header
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 0.5rem; border-radius: 10px; margin-bottom: 0.8rem; 
                    text-align: center; font-weight: bold; font-size: 1.3rem;">
            {calendar.month_name[month]} {year}
        </div>
    """, unsafe_allow_html=True)
    
    # Legend
    st.markdown("""
        <div style="display: flex; flex-wrap: wrap; gap: 15px; margin: 1rem 0; padding: 1rem; 
                    background: #f8f9fa; border-radius: 10px; justify-content: center;">
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                <div style="width: 20px; height: 20px; border-radius: 4px; background: #D4EDDA; border: 1px solid #28a745;"></div>
                <span>Present</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                <div style="width: 20px; height: 20px; border-radius: 4px; background: #FFE5D0; border: 1px solid #fd7e14;"></div>
                <span>Late</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                <div style="width: 20px; height: 20px; border-radius: 4px; background: #F8E6FF; border: 1px solid #e83e8c;"></div>
                <span>Early Out</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                <div style="width: 20px; height: 20px; border-radius: 4px; background: #e0f7ff; border: 1px solid #3498db;"></div>
                <span>Early Arrival</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                <div style="width: 20px; height: 20px; border-radius: 4px; background: #FFF3CD; border: 1px solid #ffc107;"></div>
                <span>Half Day</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                <div style="width: 20px; height: 20px; border-radius: 4px; background: #E2D9F3; border: 1px solid #6f42c1;"></div>
                <span>Holiday</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                <div style="width: 20px; height: 20px; border-radius: 4px; background: #F8D7DA; border: 1px solid #dc3545;"></div>
                <span>Leave</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem;">
                <div style="width: 20px; height: 20px; border-radius: 4px; background: #e0f0ff; border: 1px solid #4a86e8;"></div>
                <span>Overtime</span>
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


# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["📝 Mark Attendance", "👤 Individual View", "📊 Daily Report", "➕ Add Employee"])


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
            holiday_submitted = st.form_submit_button("🎉 Mark Holiday Today", use_container_width=True, type="primary")
            
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
        submitted = st.form_submit_button("💾 Save All Attendance", use_container_width=True, type="primary")
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
        grid-template-columns: repeat(7, 1fr);
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
    week_headers = [day for day in calendar.day_abbr]

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
            for day in week:
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


# --- TAB 2: Individual Employee View ---
with tab2:
    st.subheader("Individual Employee Attendance")

    available_years, available_months = get_available_months_years(conn) 

    view_type = st.radio("View Type", ["Monthly", "Yearly"], horizontal=True, label_visibility="collapsed")
    
    col1, col2, col3 = st.columns([1,1,1])
    
    with col1:
        employees = get_all_employees(conn)
        if employees:
            employee_options = {f"{emp[1]} ({emp[2]})": emp[0] for emp in employees}
            selected_emp = st.selectbox("Select Employee", list(employee_options.keys()), key="ind_emp")
            selected_emp_id = employee_options[selected_emp]
        else:
            st.warning("No employees found.")
            selected_emp_id = None
            st.stop() # Stop if no employees
    
    with col2:
        if view_type == "Monthly":
            if available_years:
                selected_year = st.selectbox(
                    "Year",
                    available_years,
                    index=0
                )
            else:
                st.warning("No attendance records available.")
                selected_month, selected_year = None, None
        else: # Yearly
            selected_year = st.selectbox(
                "Year",
                available_years if available_years else [datetime.now().year],
                index=0
            )
            selected_month = None # Not used in yearly view

    with col3:
        if view_type == "Monthly":
            if selected_year and available_months:
                selected_month = st.selectbox(
                    "Month",
                    available_months,
                    format_func=lambda x: calendar.month_name[x],
                    index=0
                )
            else:
                selected_month = None
        else: # Yearly
            # Disable month selector in yearly view
            st.selectbox(
                "Month",
                [calendar.month_name[i] for i in range(1, 13)],
                index=0,
                disabled=True
            )

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
                late_arrivals = sum(row[5] for row in attendance_data if row[5] == 1)
                early_exits = sum(row[6] for row in attendance_data if row[6] == 1)
                overtime_days = sum(row[7] for row in attendance_data if row[7] == 1)
                early_arrivals = sum(row[8] for row in attendance_data if row[8] == 1)
                total_days = len(attendance_data)
                
                # Display statistics in 8 columns
                col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
                
                with col2:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value">{present_days}</div>
                        <div class="stat-label">Present Days</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #dc3545;">{leave_days}</div>
                        <div class="stat-label">Leave Days</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ffc107;">{half_days}</div>
                        <div class="stat-label">Half Days</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col1:
                    attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #28a745;">{attendance_rate:.1f}%</div>
                        <div class="stat-label">Attendance Rate</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col5:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ed5721;">{late_arrivals}</div>
                        <div class="stat-label">Late</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col6:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #3498db;">{early_arrivals}</div>
                        <div class="stat-label">Early Arrivals</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col7:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #5bc0de;">{early_exits}</div>
                        <div class="stat-label">Early Exits</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col8:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #28a745;">{overtime_days}</div>
                        <div class="stat-label">Overtime</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")

                
                create_modern_calendar(selected_year, selected_month, attendance_data)
                
                st.markdown("---")
                
            else:
                st.info(f"No attendance records found for {calendar.month_name[selected_month]} {selected_year}")
        
        elif view_type == "Yearly" and selected_year:
            
            # --- YEARLY VIEW LOGIC ---
            
            # 1. Define Standard Times
            SCHEDULED_IN = dt_time(9, 30)
            SCHEDULED_OUT = dt_time(18, 0)

            # 2. Fetch full year data ONCE
            year_data = get_employee_full_year_attendance(conn, selected_emp_id, selected_year)
            
            # 3. Initialize counters and attendance dictionary
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

            if year_data:
                # 4. Process all data in one loop
                for row in year_data:
                    total += 1
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
                    
                    # --- Count primary stats ---
                    if status == 'Present': present += 1
                    elif status == 'Half Day': half += 1
                    elif status == 'Leave': leave += 1
                    elif status == 'Holiday': holiday += 1
                    
                    # --- Calculate and count exceptions ---
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

                    # --- Build the dictionary for the calendar ---
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

            # 5. Render components if data exists
            if total > 0:
                # --- Updated 8-column stat cards ---
                col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
                
                with col1:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value">{present}</div>
                        <div class="stat-label">Present</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #dc3545;">{leave}</div>
                        <div class="stat-label">Leaves</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col3:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ffc107;">{half}</div>
                        <div class="stat-label">Half Days</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #17a2b8;">{holiday}</div>
                        <div class="stat-label">Holidays</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col5:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ed5721;">{late_arrivals}</div>
                        <div class="stat-label">Late</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col6:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #3498db;">{early_arrivals}</div>
                        <div class="stat-label">Early Arrivals</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col7:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #5bc0de;">{early_exits}</div>
                        <div class="stat-label">Early Exits</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col8:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value" style="color: #28a745;">{overtime_days}</div>
                        <div class="stat-label">Overtime</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("---")
                
                # --- IMPROVED: Pie chart with exceptions included ---
                col_chart, col_space = st.columns([2, 1])
                with col_chart:
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
                
                st.markdown("---")
                
                st.markdown(f"### 📅 {selected_year} at a Glance")
                
                # Call the calendar function with the dictionary we built
                display_yearly_calendars(selected_year, attendance_dict)
                
            else:
                st.info(f"No attendance records found for {selected_year}")

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

# TAB 4: Manage Employees
with tab4:
    st.subheader("Add New Employee")
    
    with st.form("add_employee_form"):
        emp_name = st.text_input("Employee Name*")
        emp_email = st.text_input("Employee Email*")
        emp_dept = st.text_input("Designation")
        
        submitted = st.form_submit_button("➕ Add Employee")
        
        if submitted:
            if emp_name and emp_email:
                try:
                    with conn.session as s:
                        s.execute(text("""
                            INSERT INTO employees (employee_name, employee_email, designation)
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
    st.subheader("Manage Employees")
    
    all_employees = get_all_employees_with_status(conn)
    if all_employees:
        # Header
        col1, col2, col3, col4, col5 = st.columns([1, 4, 3, 2, 3])
        col1.write("**ID**")
        col2.write("**Name**")
        col3.write("**Designation**")
        col4.write("**Status**")
        col5.write("**Action**")

        for emp in all_employees:
            emp_id, emp_name, emp_des, emp_status = emp
            col1, col2, col3, col4, col5 = st.columns([1, 4, 3, 2, 3])
            
            with col1:
                st.write(emp_id)
            with col2:
                st.write(emp_name)
            with col3:
                st.write(emp_des)
            with col4:
                if emp_status == 'Active':
                    st.markdown(f'<span style="color:green">{emp_status}</span>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<span style="color:red">{emp_status}</span>', unsafe_allow_html=True)
            with col5:
                new_status = 'Inactive' if emp_status == 'Active' else 'Active'
                button_label = f"Set to {new_status}"
                if st.button(button_label, key=f"status_{emp_id}"):
                    if update_employee_status(conn, emp_id, new_status):
                        st.success(f"Employee {emp_name}'s status updated to {new_status}.")
                        st.rerun()
    else:
        st.info("No employees in the system yet.")

