import streamlit as st
import pandas as pd
from sqlalchemy import text
import datetime
import calendar

# --- Custom CSS for Calendar UI ---
# This CSS will be injected into the page to style the HTML calendar
CALENDAR_CSS = """
<style>
    .calendar-container {
        font-family: 'Arial', sans-serif;
        width: 100%;
    }
    .calendar-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px;
        background-color: #f4f4f4;
        border-radius: 8px 8px 0 0;
    }
    .calendar-header h3 {
        margin: 0;
    }
    .calendar-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed; /* Ensures even column widths */
    }
    .calendar-table th, .calendar-table td {
        border: 1px solid #ddd;
        text-align: center;
        height: 100px; /* Taller cells for content */
        vertical-align: top;
        padding: 6px;
        box-sizing: border-box;
    }
    .calendar-table th {
        background-color: #f9f9f9;
        font-size: 0.9em;
        padding: 10px 6px;
        height: auto;
    }
    .calendar-day {
        font-size: 0.9em;
        text-align: left;
    }
    .day-number {
        font-weight: bold;
        font-size: 1.1em;
        color: #333;
    }
    .day-content {
        margin-top: 5px;
        font-size: 0.85em;
    }
    .day-content .status-present {
        color: #28a745;
        font-weight: bold;
    }
    .day-content .status-half-day {
        color: #ffc107;
        font-weight: bold;
    }
    .day-content .status-absent {
        color: #dc3545;
        font-weight: bold;
    }
    .day-content .time {
        color: #6c757d;
    }
    .not-in-month {
        background-color: #fdfdfd;
        color: #ccc;
    }
    .today {
        background-color: #e6f7ff;
    }
</style>
"""

# --- Database Connection ---
# Using the connection function you provided
def connect_db():
    try:
        @st.cache_resource
        def get_connection():
            return st.connection('mysql', type='sql')
        conn = get_connection()
        return conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        return None

# --- Database Functions ---

def get_all_employees(conn):
    """Fetch all employees for select boxes."""
    try:
        df = conn.query("SELECT employee_id, name FROM employees ORDER BY name", ttl=600)
        return df
    except Exception as e:
        st.error(f"Error fetching employees: {e}")
        return pd.DataFrame(columns=["employee_id", "name"])

def log_attendance(conn, employee_id, date, in_time, out_time):
    """Insert or update an attendance record."""
    try:
        # Use ON DUPLICATE KEY UPDATE to handle existing records (upsert)
        query = text("""
            INSERT INTO attendance (employee_id, attendance_date, in_time, out_time)
            VALUES (:emp_id, :date, :in, :out)
            ON DUPLICATE KEY UPDATE
                in_time = :in,
                out_time = :out;
        """)
        with conn.session as s:
            s.execute(query, {
                "emp_id": employee_id,
                "date": date,
                "in": in_time,
                "out": out_time
            })
            s.commit()
        return True
    except Exception as e:
        st.error(f"Error logging attendance: {e}")
        return False

def get_employee_attendance_month(conn, employee_id, year, month):
    """Fetch attendance data for a specific employee and month."""
    try:
        query = text("""
            SELECT attendance_date, in_time, out_time
            FROM attendance
            WHERE employee_id = :emp_id
              AND YEAR(attendance_date) = :year
              AND MONTH(attendance_date) = :month
            ORDER BY attendance_date;
        """)
        df = conn.query(query, params={"emp_id": employee_id, "year": year, "month": month}, ttl=60)
        return df
    except Exception as e:
        st.error(f"Error fetching monthly attendance: {e}")
        return pd.DataFrame(columns=["attendance_date", "in_time", "out_time"])

def get_employee_attendance_year(conn, employee_id, year):
    """Fetch attendance data for a specific employee and year for summary."""
    try:
        query = text("""
            SELECT attendance_date, in_time, out_time
            FROM attendance
            WHERE employee_id = :emp_id
              AND YEAR(attendance_date) = :year
            ORDER BY attendance_date;
        """)
        df = conn.query(query, params={"emp_id": employee_id, "year": year}, ttl=60)
        return df
    except Exception as e:
        st.error(f"Error fetching yearly attendance: {e}")
        return pd.DataFrame(columns=["attendance_date", "in_time", "out_time"])

def get_daily_attendance(conn, date):
    """Fetch all employee attendance for a specific date."""
    try:
        query = text("""
            SELECT
                e.name,
                a.in_time,
                a.out_time,
                a.attendance_date
            FROM employees e
            LEFT JOIN attendance a
              ON e.employee_id = a.employee_id AND a.attendance_date = :date
            ORDER BY e.name;
        """)
        df = conn.query(query, params={"date": date}, ttl=60)
        return df
    except Exception as e:
        st.error(f"Error fetching daily attendance: {e}")
        return pd.DataFrame(columns=["name", "in_time", "out_time", "attendance_date"])

# --- UI & Helper Functions ---

def get_status(in_time, out_time, total_hours=8.0):
    """Determine attendance status based on hours worked."""
    if in_time is None or out_time is None:
        return "Absent", 0.0

    # Convert time objects to datetime objects to calculate duration
    today = datetime.date.today()
    in_dt = datetime.datetime.combine(today, in_time)
    out_dt = datetime.datetime.combine(today, out_time)

    duration = (out_dt - in_dt).total_seconds() / 3600  # Duration in hours

    if duration < 0: # Handle overnight case if out_time is next day (e.g., 9 PM to 5 AM)
        duration += 24

    if duration >= total_hours:
        return "Present", duration
    elif duration >= total_hours / 2:
        return "Half-Day", duration
    elif duration > 0:
        return "Short Leave", duration
    else:
        return "Absent", 0.0

def generate_monthly_calendar(attendance_data, year, month):
    """Generates an HTML string for a calendar view."""
    
    st.html(CALENDAR_CSS) # Inject the CSS
    
    cal = calendar.monthcalendar(year, month)
    month_name = datetime.date(year, month, 1).strftime('%B')
    today = datetime.date.today()

    # Convert data to a dictionary for quick lookup by day
    # We must handle the case where attendance_data['attendance_date'] might be strings
    attendance_dict = {}
    for _, row in attendance_data.iterrows():
        # Ensure date is a date object
        if isinstance(row['attendance_date'], str):
            day = datetime.datetime.strptime(row['attendance_date'], '%Y-%m-%d').date().day
        elif isinstance(row['attendance_date'], datetime.date):
            day = row['attendance_date'].day
        else:
            continue # Skip if format is unexpected
            
        attendance_dict[day] = (row['in_time'], row['out_time'])

    html = f"<div class='calendar-container'>"
    html += f"<div class='calendar-header'><h3>{month_name} {year}</h3></div>"
    html += "<table class='calendar-table'>"
    
    # Add calendar headers
    html += "<tr>"
    for day in calendar.day_abbr:
        html += f"<th>{day}</th>"
    html += "</tr>"

    # Add calendar days
    for week in cal:
        html += "<tr>"
        for day in week:
            cell_class = ""
            content = ""
            if day == 0:
                cell_class = "not-in-month"
                day_str = ""
            else:
                day_str = f"<div class='day-number'>{day}</div>"
                date_obj = datetime.date(year, month, day)
                
                if date_obj == today:
                    cell_class = "today"
                
                if date_obj.weekday() >= 5: # Saturday or Sunday
                    cell_class += " weekend" # You can add CSS for .weekend

                record = attendance_dict.get(day)
                if record:
                    in_time, out_time = record
                    status, hours = get_status(in_time, out_time)
                    
                    in_str = in_time.strftime('%H:%M') if in_time else "N/A"
                    out_str = out_time.strftime('%H:%M') if out_time else "N/A"
                    
                    status_class = f"status-{status.lower().replace(' ', '-')}"
                    
                    content = f"""
                    <div class='day-content'>
                        <div class='{status_class}'>{status}</div>
                        <div class='time'>In: {in_str}</div>
                        <div class='time'>Out: {out_str}</div>
                    </div>
                    """
                elif date_obj <= today:
                     content = "<div class='day-content'><div class='status-absent'>Absent</div></div>"
                
            html += f"<td class='calendar-day {cell_class}'>{day_str}{content}</td>"
        html += "</tr>"

    html += "</table></div>"
    return html

def calculate_yearly_summary(attendance_data, year):
    """Creates a summary DataFrame for the year."""
    summary = []
    
    # Get total days in each month, considering leap years
    days_in_month = {m: calendar.monthrange(year, m)[1] for m in range(1, 13)}

    # Convert dates for easier processing
    attendance_data['date'] = pd.to_datetime(attendance_data['attendance_date'])
    attendance_data['month'] = attendance_data['date'].dt.month
    
    for month in range(1, 13):
        month_name = calendar.month_name[month]
        month_data = attendance_data[attendance_data['month'] == month]
        
        present = 0
        half_day = 0
        
        for _, row in month_data.iterrows():
            status, _ = get_status(row['in_time'], row['out_time'])
            if status == "Present":
                present += 1
            elif status == "Half-Day":
                half_day += 1
        
        # Simple absent calculation (assuming non-working days are not tracked)
        # More complex logic would exclude weekends/holidays
        total_tracked_days = len(month_data)
        
        # A simple summary
        summary.append({
            "Month": month_name,
            "Present Days": present,
            "Half-Days": half_day,
            "Other Tracked": total_tracked_days - present - half_day
        })
        
    return pd.DataFrame(summary)

# --- Main Streamlit Page Function ---

def show_attendance_page():
    """Renders the full attendance management page."""
    
    st.title("Employee Attendance Management")
    
    conn = connect_db()
    if conn is None:
        st.stop()
        
    employee_df = get_all_employees(conn)
    if employee_df.empty:
        st.warning("No employees found in the database. Please add employees first.")
        # Optionally, provide a link or instructions to add employees
        return

    # Create a dictionary for easy lookup
    employee_dict = pd.Series(employee_df.name.values, index=employee_df.employee_id).to_dict()
    employee_options = list(employee_dict.items()) # List of (id, name) tuples

    tab1, tab2, tab3 = st.tabs([
        "📝 Log Attendance",
        "👤 Employee View",
        "📅 Daily View"
    ])

    # --- Tab 1: Log Attendance ---
    with tab1:
        st.subheader("Log or Update Employee Attendance")
        
        # Use format_func to display names while using IDs behind the scenes
        selected_employee = st.selectbox(
            "Select Employee",
            options=employee_options,
            format_func=lambda x: x[1] # x is an (id, name) tuple
        )
        
        attn_date = st.date_input("Select Date", datetime.date.today())
        
        col1, col2 = st.columns(2)
        with col1:
            in_time = st.time_input("In Time", datetime.time(9, 0))
        with col2:
            out_time = st.time_input("Out Time", datetime.time(17, 0))
            
        if st.button("Submit Attendance"):
            if selected_employee:
                emp_id = selected_employee[0] # Get the ID from the tuple
                success = log_attendance(conn, emp_id, attn_date, in_time, out_time)
                if success:
                    st.success(f"Attendance logged for {selected_employee[1]} on {attn_date}!")
                    # Clear cache for relevant queries
                    st.cache_data.clear()
                else:
                    st.error("Failed to log attendance.")

    # --- Tab 2: Employee View (Monthly/Yearly) ---
    with tab2:
        st.subheader("View Individual Employee Attendance")
        
        emp_to_view = st.selectbox(
            "Select Employee to View",
            options=employee_options,
            format_func=lambda x: x[1],
            key="emp_view_select"
        )
        
        if emp_to_view:
            emp_id_to_view = emp_to_view[0]
            emp_name_to_view = emp_to_view[1]
            
            view_type = st.radio("Select View Type", ["Monthly", "Yearly"], horizontal=True, key="view_type")
            
            if view_type == "Monthly":
                # Use a date input to select month and year
                selected_month_date = st.date_input("Select Month", datetime.date.today(), key="month_view")
                year, month = selected_month_date.year, selected_month_date.month
                
                st.markdown(f"#### Attendance for {emp_name_to_view} - {selected_month_date.strftime('%B %Y')}")
                
                # Fetch data
                month_data = get_employee_attendance_month(conn, emp_id_to_view, year, month)
                
                # Generate and display calendar
                calendar_html = generate_monthly_calendar(month_data, year, month)
                st.html(calendar_html)

            else: # Yearly
                selected_year = st.number_input(
                    "Select Year",
                    min_value=2020,
                    max_value=datetime.date.today().year,
                    value=datetime.date.today().year,
                    key="year_view"
                )
                
                st.markdown(f"#### Yearly Summary for {emp_name_to_view} - {selected_year}")
                
                # Fetch data
                year_data = get_employee_attendance_year(conn, emp_id_to_view, selected_year)
                
                if year_data.empty:
                    st.info("No attendance data found for this year.")
                else:
                    summary_df = calculate_yearly_summary(year_data, selected_year)
                    st.dataframe(summary_df, use_container_width=True)

    # --- Tab 3: Daily View (All Employees) ---
    with tab3:
        st.subheader("View All Employee Attendance for a Specific Date")
        
        daily_date = st.date_input("Select Date", datetime.date.today(), key="daily_view")
        
        daily_data = get_daily_attendance(conn, daily_date)
        
        if daily_data.empty:
            st.info(f"No attendance data found for {daily_date}.")
        else:
            # Process data to add status
            processed_data = []
            for _, row in daily_data.iterrows():
                status, hours = get_status(row['in_time'], row['out_time'])
                processed_data.append({
                    "Employee Name": row['name'],
                    "Status": status,
                    "In Time": row['in_time'],
                    "Out Time": row['out_time'],
                    "Hours Worked": f"{hours:.2f}"
                })
            
            final_df = pd.DataFrame(processed_data)
            st.dataframe(final_df, use_container_width=True)

# This allows you to run this file directly for testing
if __name__ == "__main__":
    st.set_page_config(layout="wide")
    show_attendance_page()
