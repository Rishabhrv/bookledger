import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
from sqlalchemy import text

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .timeline-container {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 5px solid #1f77b4;
    }
    .operation-card {
        background: white;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid;
    }
    .writing { border-left-color: #ff6b6b; }
    .proofreading { border-left-color: #4ecdc4; }
    .formatting { border-left-color: #45b7d1; }
    .cover { border-left-color: #96ceb4; }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 8px;
        margin: 5px;
        text-align: center;
    }
    .status-active { color: #28a745; font-weight: bold; }
    .status-paused { color: #ffc107; font-weight: bold; }
    .status-completed { color: #17a2b8; font-weight: bold; }
    .employee-selector {
        background: #e9ecef;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    .timeline-event {
        display: flex;
        align-items: center;
        margin: 8px 0;
        padding: 8px;
        background: white;
        border-radius: 5px;
        border-left: 4px solid;
    }
</style>
""", unsafe_allow_html=True)

def connect_db():
    try:
        @st.cache_resource
        def get_connection():
            return st.connection('mysql', type='sql')
        conn = get_connection()
        return conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

def get_employees(conn):
    """Get all employees from books table"""
    try:
        query = """
        SELECT DISTINCT writing_by as employee_id
        FROM books WHERE writing_by IS NOT NULL AND writing_by != ''
        UNION
        SELECT DISTINCT proofreading_by as employee_id
        FROM books WHERE proofreading_by IS NOT NULL AND proofreading_by != ''
        UNION
        SELECT DISTINCT formatting_by as employee_id
        FROM books WHERE formatting_by IS NOT NULL AND formatting_by != ''
        UNION
        SELECT DISTINCT cover_by as employee_id
        FROM books WHERE cover_by IS NOT NULL AND cover_by != ''
        """
        result = conn.query(query, ttl=3600)
        
        # Since we don't have a users table, we'll use the employee_id as name
        employees = []
        for _, row in result.iterrows():
            employee_id = row['employee_id']
            # Check if it's numeric or string name
            if isinstance(employee_id, (int, float)) or (isinstance(employee_id, str) and employee_id.isdigit()):
                employees.append({'employee_id': employee_id, 'employee_name': f"Employee {employee_id}"})
            else:
                employees.append({'employee_id': employee_id, 'employee_name': employee_id})
        
        return pd.DataFrame(employees)
    except Exception as e:
        st.error(f"Error fetching employees: {e}")
        return pd.DataFrame()

def get_employee_books(conn, employee_id, month=None):
    """Get books for a specific employee"""
    try:
        if month is None:
            month = datetime.datetime.now().replace(day=1)
        
        next_month = month.replace(day=28) + timedelta(days=4)
        next_month = next_month.replace(day=1)
        
        query = """
        SELECT book_id, title, writing_start, writing_end, 
               proofreading_start, proofreading_end, formatting_start, formatting_end,
               cover_start, cover_end, writing_by, proofreading_by, formatting_by, cover_by
        FROM books 
        WHERE (writing_by = :emp_id OR proofreading_by = :emp_id OR 
               formatting_by = :emp_id OR cover_by = :emp_id)
        AND (COALESCE(writing_start, proofreading_start, formatting_start, cover_start) >= :month_start 
             OR COALESCE(writing_end, proofreading_end, formatting_end, cover_end) >= :month_start)
        """
        result = conn.query(query, params={"emp_id": employee_id, "month_start": month}, ttl=3600)
        return result
    except Exception as e:
        st.error(f"Error fetching employee books: {e}")
        return pd.DataFrame()

def get_book_timeline(conn, book_id):
    """Get complete timeline for a book"""
    try:
        # Get book basic info
        book_query = """
        SELECT * FROM books WHERE book_id = :book_id
        """
        book_info = conn.query(book_query, params={"book_id": book_id}, ttl=3600)
        
        if book_info.empty:
            return None, None, None
        
        # Get corrections
        corrections_query = """
        SELECT * FROM corrections WHERE book_id = :book_id ORDER BY correction_start
        """
        corrections = conn.query(corrections_query, params={"book_id": book_id}, ttl=3600)
        
        # Get holds
        holds_query = """
        SELECT * FROM holds WHERE book_id = :book_id ORDER BY hold_start
        """
        holds = conn.query(holds_query, params={"book_id": book_id}, ttl=3600)
        
        return book_info.iloc[0], corrections, holds
    except Exception as e:
        st.error(f"Error fetching book timeline: {e}")
        return None, None, None

def calculate_operation_timeline(operation_data, corrections, holds, operation_type):
    """Calculate detailed timeline for an operation"""
    timeline = []
    
    start_time = operation_data.get('start')
    if start_time and not pd.isna(start_time):
        # Add start event
        timeline.append({
            'type': 'start',
            'time': start_time,
            'description': f'{operation_type.title()} started'
        })
        
        # Add hold events for this operation
        operation_holds = holds[holds['section'] == operation_type] if not holds.empty else pd.DataFrame()
        for _, hold in operation_holds.iterrows():
            hold_start = hold.get('hold_start')
            resume_time = hold.get('resume_time')
            reason = hold.get('reason', 'No reason provided')
            
            if hold_start and not pd.isna(hold_start):
                timeline.append({
                    'type': 'hold',
                    'time': hold_start,
                    'description': f'{operation_type.title()} paused: {reason}'
                })
            
            if resume_time and not pd.isna(resume_time):
                timeline.append({
                    'type': 'resume',
                    'time': resume_time,
                    'description': f'{operation_type.title()} resumed'
                })
        
        # Add correction events for this operation
        operation_corrections = corrections[corrections['section'] == operation_type] if not corrections.empty else pd.DataFrame()
        for _, correction in operation_corrections.iterrows():
            correction_start = correction.get('correction_start')
            correction_end = correction.get('correction_end')
            
            if correction_start and not pd.isna(correction_start):
                timeline.append({
                    'type': 'correction_start',
                    'time': correction_start,
                    'description': f'{operation_type.title()} correction started'
                })
            
            if correction_end and not pd.isna(correction_end):
                timeline.append({
                    'type': 'correction_end',
                    'time': correction_end,
                    'description': f'{operation_type.title()} correction completed'
                })
        
        # Add end event if available
        end_time = operation_data.get('end')
        if end_time and not pd.isna(end_time):
            timeline.append({
                'type': 'end',
                'time': end_time,
                'description': f'{operation_type.title()} completed'
            })
    
    # Sort timeline by time
    timeline.sort(key=lambda x: x['time'] if x['time'] else datetime.datetime.min)
    return timeline

def calculate_operation_metrics(timeline, operation_type):
    """Calculate metrics for an operation"""
    metrics = {}
    
    if not timeline:
        return metrics
    
    start_time = None
    end_time = None
    total_pause_time = timedelta(0)
    last_pause_start = None
    
    for event in timeline:
        if event['type'] == 'start':
            start_time = event['time']
        elif event['type'] == 'end':
            end_time = event['time']
        elif event['type'] == 'hold' and last_pause_start is None:
            last_pause_start = event['time']
        elif event['type'] == 'resume' and last_pause_start:
            total_pause_time += (event['time'] - last_pause_start)
            last_pause_start = None
    
    # If still paused, calculate until now
    if last_pause_start:
        total_pause_time += (datetime.datetime.now() - last_pause_start)
    
    if start_time:
        if end_time:
            total_time = end_time - start_time
            effective_time = total_time - total_pause_time
            metrics['status'] = 'Completed'
            metrics['total_time'] = format_timedelta(total_time)
            metrics['effective_time'] = format_timedelta(effective_time)
        else:
            total_time = datetime.datetime.now() - start_time
            effective_time = total_time - total_pause_time
            metrics['status'] = 'In Progress'
            metrics['total_time'] = format_timedelta(total_time)
            metrics['effective_time'] = format_timedelta(effective_time)
        
        metrics['pause_time'] = format_timedelta(total_pause_time)
        if total_time.total_seconds() > 0:
            metrics['efficiency'] = (effective_time.total_seconds() / total_time.total_seconds() * 100)
        else:
            metrics['efficiency'] = 0
    
    return metrics

def format_timedelta(td):
    """Format timedelta to readable string"""
    if td is None:
        return "N/A"
    
    total_seconds = int(td.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def display_operation_timeline(operation_data, corrections, holds, operation_type, employee_name):
    """Display timeline for a specific operation"""
    start_time = operation_data.get('start')
    if not start_time or pd.isna(start_time):
        return
    
    with st.container():
        st.markdown(f'<div class="operation-card {operation_type}">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"{operation_type.title()} - {employee_name}")
        with col2:
            end_time = operation_data.get('end')
            if end_time and not pd.isna(end_time):
                status = "Completed"
                status_class = "completed"
            else:
                status = "In Progress"
                status_class = "active"
            st.markdown(f'<p class="status-{status_class}">{status}</p>', unsafe_allow_html=True)
        
        # Calculate timeline and metrics
        timeline = calculate_operation_timeline(operation_data, corrections, holds, operation_type)
        metrics = calculate_operation_metrics(timeline, operation_type)
        
        # Display metrics
        if metrics:
            metric_cols = st.columns(4)
            with metric_cols[0]:
                st.metric("Total Time", metrics.get('total_time', 'N/A'))
            with metric_cols[1]:
                st.metric("Effective Time", metrics.get('effective_time', 'N/A'))
            with metric_cols[2]:
                st.metric("Pause Time", metrics.get('pause_time', 'N/A'))
            with metric_cols[3]:
                if 'efficiency' in metrics:
                    st.metric("Efficiency", f"{metrics['efficiency']:.1f}%")
        
        # Display timeline
        st.write("### Timeline")
        for event in timeline:
            event_time = event['time']
            if event_time:
                time_str = event_time.strftime("%Y-%m-%d %H:%M")
            else:
                time_str = "N/A"
            
            col1, col2 = st.columns([1, 4])
            with col1:
                st.write(time_str)
            with col2:
                icon = "🟢" if event['type'] == 'start' else "🔴" if event['type'] == 'end' else "⏸️" if event['type'] == 'hold' else "▶️" if event['type'] == 'resume' else "🔧"
                st.write(f"{icon} {event['description']}")
        
        st.markdown('</div>', unsafe_allow_html=True)

def main():
    st.markdown('<div class="main-header">📚 Employee Productivity Tracker</div>', unsafe_allow_html=True)
    
    conn = connect_db()
    
    # Employee selection
    st.markdown('<div class="employee-selector">', unsafe_allow_html=True)
    employees_df = get_employees(conn)
    
    if employees_df.empty:
        st.warning("No employees found in the database.")
        return
    
    # Create display names for dropdown
    employee_options = []
    employee_mapping = {}
    
    for _, row in employees_df.iterrows():
        employee_id = row['employee_id']
        employee_name = row['employee_name']
        
        # Handle both string and numeric IDs
        display_name = f"{employee_name}"
        employee_options.append(display_name)
        employee_mapping[display_name] = employee_id
    
    selected_employee_display = st.selectbox("Select Employee:", employee_options)
    
    if selected_employee_display:
        employee_id = employee_mapping[selected_employee_display]
        employee_name = selected_employee_display
        
        # Month selection
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month
        selected_month = st.date_input("Select Month:", 
                                     datetime.date(current_year, current_month, 1),
                                     key="month_selector")
        
        month_start = datetime.datetime(selected_month.year, selected_month.month, 1)
        
        # Get employee books for selected month
        books_df = get_employee_books(conn, employee_id, month_start)
        
        if books_df.empty:
            st.info(f"No books found for {employee_name} in {selected_month.strftime('%B %Y')}")
        else:
            st.success(f"Found {len(books_df)} books for {employee_name} in {selected_month.strftime('%B %Y')}")
            
            # Book selection
            book_options = [f"{row['title']} (ID: {row['book_id']})" for _, row in books_df.iterrows()]
            selected_book = st.selectbox("Select Book:", book_options)
            
            if selected_book:
                book_id = int(selected_book.split("(ID: ")[1].replace(")", ""))
                book_title = selected_book.split(" (ID:")[0]
                
                # Get book timeline
                book_info, corrections, holds = get_book_timeline(conn, book_id)
                
                if book_info is not None:
                    st.markdown(f'<div class="timeline-container">', unsafe_allow_html=True)
                    st.header(f"📖 {book_title} - Complete Timeline")
                    
                    # Display all operations for this employee
                    operations = [
                        ('writing', 'Writing', book_info.get('writing_by')),
                        ('proofreading', 'Proofreading', book_info.get('proofreading_by')),
                        ('formatting', 'Formatting', book_info.get('formatting_by')),
                        ('cover', 'Cover Design', book_info.get('cover_by'))
                    ]
                    
                    operation_found = False
                    for op_type, op_name, op_employee_id in operations:
                        # Compare employee IDs (handling both string and numeric)
                        if str(op_employee_id) == str(employee_id):
                            operation_found = True
                            operation_data = {
                                'start': book_info.get(f'{op_type}_start'),
                                'end': book_info.get(f'{op_type}_end')
                            }
                            display_operation_timeline(operation_data, corrections, holds, op_type, employee_name)
                    
                    if not operation_found:
                        st.info(f"{employee_name} is not assigned to any operations for this book.")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Overall book metrics
                    st.subheader("📊 Overall Book Metrics")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        total_operations = sum(1 for op_type, _, op_emp in operations if str(op_emp) == str(employee_id))
                        st.metric("Operations Involved", total_operations)
                    
                    with col2:
                        completed_ops = sum(1 for op_type, _, op_emp in operations 
                                          if str(op_emp) == str(employee_id) and 
                                          book_info.get(f'{op_type}_end') is not None and 
                                          not pd.isna(book_info.get(f'{op_type}_end')))
                        st.metric("Completed Operations", completed_ops)
                    
                    with col3:
                        writing_start = book_info.get('writing_start')
                        writing_end = book_info.get('writing_end')
                        if not writing_start or pd.isna(writing_start):
                            writing_progress = 0
                        elif not writing_end or pd.isna(writing_end):
                            writing_progress = 50
                        else:
                            writing_progress = 100
                        st.metric("Writing Progress", f"{writing_progress}%")
                    
                    with col4:
                        current_ops = []
                        for op_type, op_name, op_emp in operations:
                            if str(op_emp) == str(employee_id):
                                op_start = book_info.get(f'{op_type}_start')
                                op_end = book_info.get(f'{op_type}_end')
                                if (op_start is not None and not pd.isna(op_start)) and (op_end is None or pd.isna(op_end)):
                                    current_ops.append(op_name)
                        st.metric("Current Operations", ", ".join(current_ops) if current_ops else "None")
                
                else:
                    st.error("Book information not found.")
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()