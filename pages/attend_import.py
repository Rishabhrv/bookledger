import streamlit as st
import pandas as pd
from sqlalchemy import text

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


import pandas as pd

def parse_datetime(dt_str):
    """Parse datetime string from CSV"""
    if pd.isna(dt_str) or str(dt_str).strip() == '':
        return None
    
    try:
        dt_str = str(dt_str).strip()
        dt = pd.to_datetime(dt_str, dayfirst=True)
        return dt
    except Exception as e:
        print(f"Error parsing date: '{dt_str}'. Error: {e}")
        return None

def get_or_create_employee(conn, emp_code, emp_name, designation):
    """Get employee_id or create new employee"""
    with conn.session as s:
        # Check if employee exists
        result = s.execute(
            text("SELECT employee_id FROM employees WHERE employee_code = :code"),
            {"code": str(emp_code).strip()}
        )
        row = result.fetchone()
        
        if row:
            return row[0]
        
        # Create new employee
        s.execute(
            text("""
                INSERT INTO employees (employee_code, employee_name, designation)
                VALUES (:code, :name, :designation)
            """),
            {
                "code": str(emp_code).strip(),
                "name": str(emp_name).strip(),
                "designation": str(designation).strip() if pd.notna(designation) else None
            }
        )
        s.commit()
        
        # Get the new employee_id
        result = s.execute(
            text("SELECT employee_id FROM employees WHERE employee_code = :code"),
            {"code": str(emp_code).strip()}
        )
        return result.fetchone()[0]

def insert_attendance_record(conn, employee_id, att_date, check_in, check_out, status):
    """Insert or update attendance record"""
    with conn.session as s:
        try:
            # Map CSV status to DB status
            status_mapping = {
                'Present': 'Present',
                'Half Day': 'Half Day',
                'Leave': 'Leave',
                'Absent': 'Leave',
                'Holiday': 'Holiday'
            }
            
            db_status = status_mapping.get(status, 'Present')
            
            # Prepare time values
            check_in_time = check_in.time() if check_in else None
            check_out_time = check_out.time() if check_out else None
            
            # Try to insert, update on duplicate
            s.execute(
                text("""
                    INSERT INTO attendance 
                    (employee_id, attendance_date, check_in_time, check_out_time, status)
                    VALUES (:emp_id, :att_date, :check_in, :check_out, :status)
                    ON DUPLICATE KEY UPDATE
                    check_in_time = :check_in,
                    check_out_time = :check_out,
                    status = :status
                """),
                {
                    "emp_id": employee_id,
                    "att_date": att_date.date(),
                    "check_in": check_in_time,
                    "check_out": check_out_time,
                    "status": db_status
                }
            )
            s.commit()
            return True
        except Exception as e:
            st.error(f"Error inserting attendance: {e}")
            return False

def insert_holiday(conn, holiday_date, holiday_name):
    """Insert holiday record"""
    with conn.session as s:
        try:
            s.execute(
                text("""
                    INSERT IGNORE INTO holidays (holiday_date, holiday_name)
                    VALUES (:date, :name)
                """),
                {
                    "date": holiday_date.date(),
                    "name": holiday_name
                }
            )
            s.commit()
            return True
        except Exception as e:
            st.error(f"Error inserting holiday: {e}")
            return False

def process_csv_file(conn, df):
    """Process CSV file and import data"""
    success_count = 0
    error_count = 0
    skipped_count = 0
    errors = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    total_rows = len(df)
    
    for idx, row in df.iterrows():
        try:
            # Update progress
            progress = (idx + 1) / total_rows
            progress_bar.progress(progress)
            status_text.text(f"Processing row {idx + 1} of {total_rows}")
            
            # Extract data
            emp_code = row.get('Employee Code')
            emp_name = row.get('Employee Name')
            designation = row.get('Designation')
            status = str(row.get('Status', 'Present')).strip()
            in_datetime_str = row.get('In DateTime')
            out_datetime_str = row.get('Out DateTime')
            
            # Skip if essential data is missing
            if pd.isna(emp_code) or pd.isna(emp_name):
                errors.append(f"Row {idx + 1}: Missing employee code or name")
                error_count += 1
                continue
            
            # Skip WeeklyOff entries
            if status == 'WeeklyOff':
                skipped_count += 1
                continue
            
            # Skip Holiday entries
            if status == 'Holiday':
                skipped_count += 1
                continue
            
            # Handle Absent status - import as Leave
            if status == 'Absent':
                # For Absent, we need to get the date from somewhere
                # Try to parse datetime if available, otherwise skip
                in_datetime = parse_datetime(in_datetime_str)
                out_datetime = parse_datetime(out_datetime_str)
                
                att_date = in_datetime if in_datetime else out_datetime
                
                if not att_date:
                    # If no date available for Absent, skip it
                    errors.append(f"Row {idx + 1}: Absent status but no date available")
                    error_count += 1
                    continue
                
                # Get or create employee
                employee_id = get_or_create_employee(conn, emp_code, emp_name, designation)
                
                # Insert as Leave status
                if insert_attendance_record(conn, employee_id, att_date, None, None, 'Leave'):
                    success_count += 1
                else:
                    error_count += 1
                continue
            
            # Parse datetime for Present status
            in_datetime = parse_datetime(in_datetime_str)
            out_datetime = parse_datetime(out_datetime_str)
            
            if not in_datetime and status == 'Present':
                errors.append(f"Row {idx + 1}: Missing check-in time for Present status")
                error_count += 1
                continue
            
            # Get attendance date
            att_date = in_datetime if in_datetime else out_datetime
            if not att_date:
                errors.append(f"Row {idx + 1}: Could not determine attendance date")
                error_count += 1
                continue
            
            # Determine final status based on check-in/out times
            final_status = 'Present'
            
            # Check if Half Day based on check-in time (after 11:00 AM)
            if in_datetime and in_datetime.hour >= 11:
                final_status = 'Half Day'
            
            # Check if Half Day based on check-out time (before 3:00 PM / 15:00)
            if out_datetime and out_datetime.hour < 15:
                final_status = 'Half Day'
            
            # Get or create employee
            employee_id = get_or_create_employee(conn, emp_code, emp_name, designation)
            
            # Insert attendance record
            if insert_attendance_record(conn, employee_id, att_date, in_datetime, out_datetime, final_status):
                success_count += 1
            else:
                error_count += 1
                    
        except Exception as e:
            errors.append(f"Row {idx + 1}: {str(e)}")
            error_count += 1
    
    progress_bar.empty()
    status_text.empty()
    
    return success_count, error_count, skipped_count, errors

def main():
    st.set_page_config(page_title="Attendance CSV Import", page_icon="📊", layout="wide")
    
    st.title("📊 Attendance Data Import")
    st.markdown("Upload a CSV file to import employee attendance records into the database.")
    
    # Initialize database connection
    conn = connect_db()
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])
    
    if uploaded_file is not None:
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
            df = None
            encoding_used = None
            
            for encoding in encodings:
                try:
                    uploaded_file.seek(0)  # Reset file pointer
                    df = pd.read_csv(uploaded_file, encoding=encoding)
                    encoding_used = encoding
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            if df is None:
                st.error("Could not read the CSV file with any standard encoding. Please save your CSV as UTF-8.")
                st.stop()
            
            if encoding_used != 'utf-8':
                st.info(f"ℹ️ File was read using {encoding_used} encoding")
            
            # Display preview
            st.subheader("📄 File Preview")
            st.dataframe(df.head(10), use_container_width=True)
            
            st.info(f"Total rows in file: {len(df)}")
            
            # Import button
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button("🚀 Import Data", type="primary", use_container_width=True):
                    with st.spinner("Processing..."):
                        success, errors, skipped, error_list = process_csv_file(conn, df)
                        
                        # Show results
                        st.success("Import completed!")
                        
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("✅ Success", success)
                        with col_b:
                            st.metric("⚠️ Errors", errors)
                        with col_c:
                            st.metric("⏭️ Skipped (WeeklyOff/Holiday)", skipped)
                        
                        # Show errors if any
                        if error_list:
                            with st.expander("⚠️ View Errors", expanded=True):
                                for error in error_list[:20]:  # Show first 20 errors
                                    st.error(error)
                                if len(error_list) > 20:
                                    st.warning(f"... and {len(error_list) - 20} more errors")
            
            with col2:
                if st.button("🔄 Reload File", use_container_width=True):
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Error reading CSV file: {e}")
            st.info("Please ensure your CSV file matches the required format.")
    
    # Database statistics
    st.divider()
    st.subheader("📊 Database Statistics")
    
    try:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            with conn.session as s:
                result = s.execute(text("SELECT COUNT(*) FROM employees"))
                emp_count = result.fetchone()[0]
                st.metric("Total Employees", emp_count)
        
        with col2:
            with conn.session as s:
                result = s.execute(text("SELECT COUNT(*) FROM attendance"))
                att_count = result.fetchone()[0]
                st.metric("Total Attendance Records", att_count)
        
        with col3:
            with conn.session as s:
                result = s.execute(text("SELECT COUNT(*) FROM holidays"))
                hol_count = result.fetchone()[0]
                st.metric("Total Holidays", hol_count)
                
    except Exception as e:
        st.warning(f"Could not fetch database statistics: {e}")

if __name__ == "__main__":
    main()