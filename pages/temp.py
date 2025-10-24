import streamlit as st
import pandas as pd
from datetime import timedelta, datetime

# Database connection
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

# Calculate duration in a human-readable format
def calculate_duration(start, end):
    if pd.isna(start) or pd.isna(end):
        return "N/A"
    delta = end - start
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

# Calculate active work time considering office hours and excluding Sundays
def calculate_active_time(start, end, holds_df, section):
    if pd.isna(start) or pd.isna(end):
        return "Not Started"
    
    # Office hours: Monday to Saturday, 9:30 AM to 6:00 PM
    office_start_hour = 9.5  # 9:30 AM
    office_end_hour = 18.0   # 6:00 PM
    office_hours_per_day = office_end_hour - office_start_hour  # 8.5 hours
    
    # Initialize total work time
    current = start
    total_work_seconds = 0
    
    while current < end:
        # Skip Sundays
        if current.weekday() == 6:  # Sunday
            current = current.replace(hour=0, minute=0, second=0) + timedelta(days=1)
            continue
            
        # Determine work period for the day
        day_start = current.replace(hour=int(office_start_hour), minute=int((office_start_hour % 1) * 60))
        day_end = current.replace(hour=int(office_end_hour), minute=0)
        
        # Adjust if current time is before or after office hours
        if current < day_start:
            current = day_start
        if current >= day_end:
            current = current.replace(hour=0, minute=0, second=0) + timedelta(days=1)
            continue
            
        # Find end of work period for current day
        work_end = min(end, day_end)
        
        # Check for holds within this period
        section_holds = holds_df[holds_df['section'] == section]
        hold_seconds = 0
        for _, hold in section_holds.iterrows():
            if pd.notna(hold['hold_start']) and pd.notna(hold['resume_time']):
                hold_start = max(hold['hold_start'], current)
                hold_end = min(hold['resume_time'], work_end)
                if hold_start < hold_end:
                    # Only count hold time within office hours
                    hold_time = hold_end - hold_start
                    hold_seconds += hold_time.total_seconds()
        
        # Calculate active work time for this period
        period_seconds = (work_end - current).total_seconds() - hold_seconds
        if period_seconds > 0:
            total_work_seconds += period_seconds
        
        # Move to next day
        current = current.replace(hour=0, minute=0, second=0) + timedelta(days=1)
    
    # Convert total seconds to human-readable format
    days = total_work_seconds // (office_hours_per_day * 3600)
    remaining_seconds = total_work_seconds % (office_hours_per_day * 3600)
    hours = remaining_seconds // 3600
    minutes = (remaining_seconds % 3600) // 60
    if days > 0:
        return f"{int(days)}d {int(hours)}h {int(minutes)}m"
    elif hours > 0:
        return f"{int(hours)}h {int(minutes)}m"
    else:
        return f"{int(minutes)}m"

# Format timestamp to DD/MM/YYYY HH:MM AM/PM
def format_timestamp(ts):
    if pd.isna(ts):
        return "N/A"
    date_part = ts.strftime("%d/%m/%Y")
    time_part = ts.strftime("%I:%M %p")
    return f'<span class="date-part">{date_part}</span> | <span class="time-part">{time_part}</span>'

# Get emoji for section
def get_section_emoji(section):
    section_emojis = {
        'writing': '✍️',
        'proofreading': '🔍',
        'formatting': '📄',
        'cover': '🎨',
        'correction': '✏️',
        'hold': '⏸️'
    }
    return section_emojis.get(section.lower(), '⚙️')

# Custom CSS for tree-like UI and custom metrics
st.markdown("""
<style>
    .tree-item {
        padding: 8px;
        font-size: 14px;
        border-left: 3px solid #1f77b4;
        margin-left: 20px;
        margin-bottom: 8px;
        display: flex;
        align-items: flex-start;
    }
    .section-node {
        font-size: 16px;
        font-weight: bold;
        color: #333;
        margin-left: 10px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
    }
    .timestamp {
        color: #333;
        font-size: 12px;
        font-weight: bold;
        min-width: 140px;
        margin-right: 10px;
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        line-height: 1.5;
    }
    .timestamp .date-part {
        color: #333;
    }
    .timestamp .time-part {
        color: #1f77b4;
    }
    .action {
        font-weight: bold;
        color: #1f77b4;
        margin-right: 10px;
        min-width: 120px;
        display: inline-block;
    }
    .details {
        color: #333;
        font-size: 13px;
        word-break: break-word;
        background-color: #f8f9fa;
        padding: 6px 10px;
        border-radius: 4px;
        display: inline-block;
        line-height: 1.5;
        flex-grow: 1;
    }
    .duration {
        font-weight: bold;
        color: #5a9c21;
        margin-left: 8px;
    }
    .column-border {
        border-right: 1px solid #e0e0e0;
        padding-right: 20px;
    }
    .custom-metric {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .custom-metric-label {
        font-size: 14px;
        color: #6c757d;
        margin-bottom: 8px;
    }
    .custom-metric-value {
        font-size: 16px;
        font-weight: bold;
        color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database connection
conn = connect_db()

# Fetch all books for selection
with conn.session as s:
    books_df = conn.query("SELECT book_id, title FROM books ORDER BY book_id DESC", ttl=3600)
    s.commit()

st.markdown("### ⏳ Book History")

# Book selection with book_id in label
book_options = ['Select a book'] + [f"{row['title']} (ID: {row['book_id']})" for _, row in books_df.iterrows()]
selected_book = st.selectbox("Select Book", options=book_options, label_visibility="collapsed", placeholder="Select a book...")

if selected_book != 'Select a book':
    # Extract book_id from selected option
    book_id = int(selected_book.split('ID: ')[-1].strip(')'))
    
    # Fetch book details
    book_query = """
    SELECT * FROM books WHERE book_id = :book_id
    """
    book_data = conn.query(book_query, params={"book_id": book_id}, ttl=3600)
    
    if not book_data.empty:
        book = book_data.iloc[0]
        st.markdown("") 
        st.subheader(f'📖 {book["title"]} (ID: {book_id})', anchor=False, divider="orange")
        st.markdown("")  
        
        # Fetch corrections and holds
        corrections_query = """
        SELECT * FROM corrections WHERE book_id = :book_id ORDER BY correction_start
        """
        holds_query = """
        SELECT * FROM holds WHERE book_id = :book_id ORDER BY hold_start
        """
        corrections_df = conn.query(corrections_query, params={"book_id": book_id}, ttl=3600)
        holds_df = conn.query(holds_query, params={"book_id": book_id}, ttl=3600)
        
        # Calculate total book time and active times
        all_dates = []
        events = []
        sections = ['writing', 'proofreading', 'formatting', 'cover']
        
        # Collect all events
        for section in sections:
            start_field = f"{section}_start"
            end_field = f"{section}_end"
            worker_field = f"{section}_by"
            if pd.notna(book[start_field]):
                all_dates.append(book[start_field])
                events.append({
                    'timestamp': book[start_field],
                    'section': section,
                    'type': 'start',
                    'details': f"Assigned to {book[worker_field] if pd.notna(book[worker_field]) else 'N/A'}"
                })
            if pd.notna(book[end_field]):
                all_dates.append(book[end_field])
                duration = calculate_active_time(book[start_field], book[end_field], holds_df, section) if pd.notna(book[start_field]) else "Not Started"
                events.append({
                    'timestamp': book[end_field],
                    'section': section,
                    'type': 'end',
                    'details': f"{section.capitalize()} phase completed",
                    'duration': duration
                })
        
        # Add corrections
        for _, corr in corrections_df.iterrows():
            if pd.notna(corr['correction_start']):
                all_dates.append(corr['correction_start'])
                events.append({
                    'timestamp': corr['correction_start'],
                    'section': corr['section'],
                    'type': 'correction_start',
                    'details': f"Reason: {corr['notes']} | Worker: {corr['worker'] if pd.notna(corr['worker']) else 'N/A'}"
                })
            if pd.notna(corr['correction_end']):
                all_dates.append(corr['correction_end'])
                events.append({
                    'timestamp': corr['correction_end'],
                    'section': corr['section'],
                    'type': 'correction_end',
                    'details': f"Correction completed",
                    'duration': calculate_duration(corr['correction_start'], corr['correction_end']) if pd.notna(corr['correction_end']) else 'Ongoing'
                })
        
        # Add holds
        for _, hold in holds_df.iterrows():
            if pd.notna(hold['hold_start']):
                all_dates.append(hold['hold_start'])
                events.append({
                    'timestamp': hold['hold_start'],
                    'section': hold['section'],
                    'type': 'hold_start',
                    'details': f"Reason: {hold['reason']}"
                })
            if pd.notna(hold['resume_time']):
                all_dates.append(hold['resume_time'])
                duration = calculate_duration(hold['hold_start'], hold['resume_time']) if pd.notna(hold['resume_time']) else 'Ongoing'
                events.append({
                    'timestamp': hold['resume_time'],
                    'section': hold['section'],
                    'type': 'hold_end',
                    'details': f"Resumed work on {hold['section']}",
                    'duration': duration
                })
        
        # Sort events by timestamp
        events_df = pd.DataFrame(events)
        if not events_df.empty:
            events_df = events_df.sort_values('timestamp')
        
        # Calculate times
        total_time = calculate_duration(min(all_dates), max(all_dates)) if all_dates else "Not Started"
        writing_time = calculate_active_time(book['writing_start'], book['writing_end'], holds_df, 'writing') if pd.notna(book['writing_start']) and pd.notna(book['writing_end']) else "Not Started"
        proofreading_time = calculate_active_time(book['proofreading_start'], book['proofreading_end'], holds_df, 'proofreading') if pd.notna(book['proofreading_start']) and pd.notna(book['proofreading_end']) else "Not Started"
        formatting_time = calculate_active_time(book['formatting_start'], book['formatting_end'], holds_df, 'formatting') if pd.notna(book['formatting_start']) and pd.notna(book['formatting_end']) else "Not Started"
        cover_time = calculate_active_time(book['cover_start'], book['cover_end'], holds_df, 'cover') if pd.notna(book['cover_start']) and pd.notna(book['cover_end']) else "Not Started"
        
        # Display metrics in custom boxes
        cols = st.columns(5)
        with st.container():
            with cols[0]:
                st.markdown(f"""
                    <div class="custom-metric">
                        <div class="custom-metric-label">Total Project Time</div>
                        <div class="custom-metric-value">{total_time}</div>
                    </div>
                """, unsafe_allow_html=True)
            with cols[1]:
                st.markdown(f"""
                    <div class="custom-metric">
                        <div class="custom-metric-label">Writing Time (Active)</div>
                        <div class="custom-metric-value">{writing_time}</div>
                    </div>
                """, unsafe_allow_html=True)
            with cols[2]:
                st.markdown(f"""
                    <div class="custom-metric">
                        <div class="custom-metric-label">Proofreading Time (Active)</div>
                        <div class="custom-metric-value">{proofreading_time}</div>
                    </div>
                """, unsafe_allow_html=True)
            with cols[3]:
                st.markdown(f"""
                    <div class="custom-metric">
                        <div class="custom-metric-label">Formatting Time (Active)</div>
                        <div class="custom-metric-value">{formatting_time}</div>
                    </div>
                """, unsafe_allow_html=True)
            with cols[4]:
                st.markdown(f"""
                    <div class="custom-metric">
                        <div class="custom-metric-label">Cover Time (Active)</div>
                        <div class="custom-metric-value">{cover_time}</div>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("")    
        
        # Unified Timeline
        st.markdown("##### ⏳ Timeline")
        with st.container(border=True):
            if not events_df.empty:
                for _, event in events_df.iterrows():
                    action_map = {
                        'start': f"{get_section_emoji(event['section'])} {event['section'].capitalize()} Started",
                        'end': f"{get_section_emoji(event['section'])} {event['section'].capitalize()} Completed",
                        'correction_start': f"{get_section_emoji('correction')} {event['section'].capitalize()} Correction Started",
                        'correction_end': f"{get_section_emoji('correction')} {event['section'].capitalize()} Correction Ended",
                        'hold_start': f"{get_section_emoji('hold')} {event['section'].capitalize()} Paused",
                        'hold_end': f"{get_section_emoji(event['section'])} {event['section'].capitalize()} Resumed"
                    }
                    details = event['details']
                    if event.get('duration') and event['type'] in ['end', 'correction_end', 'hold_end']:
                        details += f"<span class='duration'>(Duration: {event['duration']})</span>"
                    st.markdown(
                        f"""
                        <div class="tree-item">
                            <div class="timestamp">{format_timestamp(event['timestamp'])}</div>
                            <div class="action">{action_map[event['type']]}</div>
                            <div class="details">{details}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.markdown("No events found for this book.")
    else:
        st.info(f"No details found for book: {selected_book}")
else:
    st.info("Please select a book to view its timeline.")