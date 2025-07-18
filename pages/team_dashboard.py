import streamlit as st
import warnings 
import pandas as pd
import os
from sqlalchemy import text
warnings.simplefilter('ignore')
import os
import datetime
import altair as alt
from auth import validate_token
from constants import log_activity
from constants import connect_db
import uuid


# Set page configuration
st.set_page_config(
    layout="wide",  # Set layout to wide mode
    initial_sidebar_state="collapsed",
    page_icon="chart_with_upwards_trend",  
     page_title="Content Dashboard",
)

# Inject CSS to remove the menu (optional)
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
"""

st.markdown(hide_menu_style, unsafe_allow_html=True)

st.markdown("""
    <style>
            
        /* Remove Streamlit's default top padding */
        .main > div {
            padding-top: 0px !important;
        }
        /* Ensure the first element has minimal spacing */
        .block-container {
            padding-top: 28px !important;  /* Small padding for breathing room */
        }
            """, unsafe_allow_html=True)

logo = "logo/logo_black.png"
fevicon = "logo/favicon_black.ico"
small_logo = "logo/favicon_white.ico"

st.logo(logo,
size = "large",
icon_image = small_logo
)

# Run validation
validate_token()

role_user = st.session_state.get("role", "Unknown")
user_app = st.session_state.get("app", "Unknown")
user_name = st.session_state.get("username", "Unknown")
user_access = st.session_state.get("access", [])
# if "session_id" not in st.session_state:
#     st.session_state.session_id = str(uuid.uuid4())


# role_user = 'admin'
# user_app = 'main'
# user_name = 'Akash'
# user_access = ['DatadashBoard','Advance' 'Search','Team Dashboard']

#st.write(f"### Welcome {user_name}!")
# st.write(f"**Role:** {role_user}")
# st.write(f"**App:** {user_app}")
# st.write(f"**Access:** {user_access}")


section_labels = {
    "Writing Section": "writer",
    "Proofreading Section": "proofreader",
    "Formatting Section": "formatter",
    "Cover Design Section": "cover_designer"
}


# Admin or allowed users get role selector pills
if role_user == "admin" or (role_user == "user" and user_app == "main" and "Team Dashboard" in user_access):
    selected = st.segmented_control(
        "Select Section", 
        list(section_labels.keys()),
        default="Writing Section",
        key="section_selector",
        label_visibility='collapsed'
    )
    #st.session_state.access = [selected]  # Store as list to match user format
    user_role = section_labels[selected]

elif role_user == "user" and user_app == "operations":
    # Set user_role from their first access item
    user_role = user_access[0] if user_access else ""

else:
    # Access Denied
    st.error("You don't have permission to access this page.")
    st.stop()

st.cache_data.clear()

# Connect to MySQL
conn = connect_db()

# if user_app == 'operations':
#     if "activity_logged" not in st.session_state:
#         log_activity(
#                     conn,
#                     st.session_state.user_id,
#                     st.session_state.username,
#                     st.session_state.session_id,
#                     "logged in",
#                     f"App: {st.session_state.app}, Access: {st.session_state.access[0]}"
#                 )
#         st.session_state.activity_logged = True


# if user_app == 'main':
#     # Initialize session state from query parameters
#     query_params = st.query_params
#     click_id = query_params.get("click_id", [None])
#     session_id = query_params.get("session_id", [None])

#     # Set session_id in session state
#     st.session_state.session_id = session_id

#     # Initialize logged_click_ids if not present
#     if "logged_click_ids" not in st.session_state:
#         st.session_state.logged_click_ids = set()

#     # Log navigation if click_id is present and not already logged
#     if click_id and click_id not in st.session_state.logged_click_ids:
#         try:
#             log_activity(
#                 conn,
#                 st.session_state.user_id,
#                 st.session_state.username,
#                 st.session_state.session_id,
#                 "navigated to page",
#                 f"Page: Team Dashboard"
#             )
#             st.session_state.logged_click_ids.add(click_id)
#         except Exception as e:
#             st.error(f"Error logging navigation: {str(e)}")


# Initialize session state
if "logged_click_ids" not in st.session_state:
    st.session_state.logged_click_ids = set()
if "activity_logged" not in st.session_state:
    st.session_state.activity_logged = False

# Determine session_id based on access method
user_app = st.session_state.get("app", "operations")
if user_app == "main":
    query_params = st.query_params
    session_id = query_params.get("session_id", [None])
    click_id = query_params.get("click_id", [None])
    if not session_id:
        st.error("Session not initialized. Please access this page from the main dashboard.")
        st.stop()
    st.session_state.session_id = session_id
else:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    click_id = None

# Ensure user_id and username are set
if not all(key in st.session_state for key in ["user_id", "username"]):
    st.error("Session not initialized. Please log in again.")
    st.stop()

# Log login for direct access (operations)
if user_app == "operations" and not st.session_state.activity_logged:
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
if user_app == "main" and click_id and click_id not in st.session_state.logged_click_ids:
    try:
        log_activity(
            conn,
            st.session_state.user_id,
            st.session_state.username,
            st.session_state.session_id,
            "navigated to page",
            f"Page: team_dashboard"
        )
        st.session_state.logged_click_ids.add(click_id)
    except Exception as e:
        st.error(f"Error logging navigation: {str(e)}")


# --- Updated CSS ---
st.markdown("""
    <style>
    .header-row {
        padding-bottom: 5px;
        margin-bottom: 10px;
    }
    .header {
        font-weight: bold;
        font-size: 14px; 
    }
    .header-line {
        border-bottom: 1px solid #ddd;
        margin-top: -10px;
    }
    .pill {
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 12px;
        display: inline-block;
        margin-right: 4px;
    }
    .since-enrolled {
        background-color: #FFF3E0;
        color: #FF9800;
        padding: 1px 4px;
        border-radius: 8px;
        font-size: 11px;
    }
    .section-start-not {
        background-color: #F5F5F5;
        color: #757575;
    }
    .section-start-date {
        background-color: #FFF3E0;
        color: #FF9800;
    }
    .worker-by-not {
        background-color: #F5F5F5;
        color: #757575;
    }
    /* Worker-specific colors (softer tones, reusable for all sections) */
    .worker-by-0 { background-color: #E3F2FD; color: #1976D2; } /* Blue */
    .worker-by-1 { background-color: #FCE4EC; color: #D81B60; } /* Pink */
    .worker-by-2 { background-color: #E0F7FA; color: #006064; } /* Cyan */
    .worker-by-3 { background-color: #F1F8E9; color: #558B2F; } /* Light Green */
    .worker-by-4 { background-color: #FFF3E0; color: #EF6C00; } /* Orange */
    .worker-by-5 { background-color: #F3E5F5; color: #8E24AA; } /* Purple */
    .worker-by-6 { background-color: #FFFDE7; color: #F9A825; } /* Yellow */
    .worker-by-7 { background-color: #EFEBE9; color: #5D4037; } /* Brown */
    .worker-by-8 { background-color: #E0E0E0; color: #424242; } /* Grey */
    .worker-by-9 { background-color: #E8EAF6; color: #283593; } /* Indigo */
    .status-pending {
        background-color: #FFEBEE;
        color: #F44336;
        font-weight: bold;
    }
    .apply-isbn-yes {
    background-color: #C8E6C9; /* Light green */
    color: #2E7D32; /* Dark green text */
    }
    .apply-isbn-no {
        background-color: #E0E0E0; /* Light gray */
        color: #616161; /* Dark gray text */
    }
    .status-running {
        background-color: #FFFDE7;
        color: #F9A825;
        font-weight: bold;
    }
    /* Standardized badge colors for Pending (red) and Running (yellow) */
    .status-badge-red {
        background-color: #FFEBEE;
        color: #F44336;
        padding: 4px 8px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
    }
    .status-badge-yellow {
        background-color: #FFFDE7;
        color: #F9A825;
        padding: 4px 8px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
    }
    .badge-count {
        background-color: rgba(255, 255, 255, 0.9);
        color: inherit;
        padding: 2px 6px;
        border-radius: 10px;
        margin-left: 6px;
        font-size: 12px;
        font-weight: normal;
    }
    /* ... existing styles ... */
    .status-completed {
        background-color: #E8F5E9;
        color: #4CAF50;
        font-weight: bold;
    }
    .status-correction {
        background-color: #FFEBEE;
        color: #F44336;
        font-weight: bold;
    }
    .status-badge-green {
        background-color: #E8F5E9;
        color: #4CAF50;
        padding: 4px 8px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
    }
            
    .publish-only-badge {
        background-color: #e0f7fa;
        color: #00695c;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 10px;
        margin-left: 5px;
    }
            
    .dialog-header {
            font-size: 20px;
            color: #4CAF50;
            margin-bottom: 10px;
            font-weight: bold;
        }
        .info-label {
            font-weight: bold;
            color: #333;
            margin-top: 10px;
            margin-bottom: 5px;
        }
        .info-value {
            padding: 5px 10px;
            border-radius: 5px;
            background-color: #F5F5F5;
            display: inline-block;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        th {
            background-color: #4CAF50;
            color: white;
            padding: 10px;
            text-align: left;
            font-weight: bold;
        }
        td {
            padding: 10px;
            border-bottom: 1px solid #E0E0E0;
        }
        .pill-yes {
            background-color: #C8E6C9;
            color: #2E7D32;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
        }
        .pill-no {
            background-color: #E0E0E0;
            color: #616161;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
        }
        .close-button {
            margin-top: 20px;
            width: 100%;
        }
    </style>
""", unsafe_allow_html=True)

def fetch_books(months_back: int = 4, section: str = "writing") -> pd.DataFrame:
    conn = connect_db()
    cutoff_date = datetime.now().date() - timedelta(days=30 * months_back)
    cutoff_date_str = cutoff_date.strftime('%Y-%m-%d')
    
    section_columns = {
        "writing": {
            "base": [
                "writing_by AS 'Writing By'", 
                "writing_start AS 'Writing Start'", 
                "writing_end AS 'Writing End'",
                "book_pages AS 'Number of Book Pages'",
                "syllabus_path AS 'Syllabus Path'"
            ],
            "extra": [],
            "publish_filter": "AND is_publish_only = 0"
        },
        "proofreading": {
            "base": [
                "proofreading_by AS 'Proofreading By'", 
                "proofreading_start AS 'Proofreading Start'", 
                "proofreading_end AS 'Proofreading End'",
                "is_publish_only AS 'is_publish_only'"
            ],
            "extra": [
                "writing_end AS 'Writing End'", 
                "writing_by AS 'Writing By'",
                "book_pages AS 'Number of Book Pages'"
              
            ],
            "publish_filter": ""
        },
        "formatting": {
            "base": [
                "formatting_by AS 'Formatting By'", 
                "formatting_start AS 'Formatting Start'", 
                "formatting_end AS 'Formatting End'",
                "book_pages AS 'Number of Book Pages'"
            ],
            "extra": ["proofreading_end AS 'Proofreading End'"],
            "publish_filter": ""
        },
        "cover": {
            "base": [
                "cover_by AS 'Cover By'", 
                "cover_start AS 'Cover Start'", 
                "cover_end AS 'Cover End'", 
                "apply_isbn AS 'Apply ISBN'", 
                "isbn AS 'ISBN'"
            ],
            "extra": [
                "formatting_end AS 'Formatting End'",
                "(SELECT MIN(ba.photo_recive) FROM book_authors ba WHERE ba.book_id = b.book_id) AS 'All Photos Received'",
                "(SELECT MIN(ba.author_details_sent) FROM book_authors ba WHERE ba.book_id = b.book_id) AS 'All Details Sent'"
            ],
            "publish_filter": ""
        }
    }
    config = section_columns.get(section, section_columns["writing"])
    columns = config["base"] + config["extra"]
    columns_str = ", ".join(columns)
    publish_filter = config["publish_filter"]
    
    if section == "cover":
        query = f"""
            SELECT 
                b.book_id AS 'Book ID',
                b.title AS 'Title',
                b.date AS 'Date',
                {columns_str},
                b.is_publish_only AS 'Is Publish Only',
                GROUP_CONCAT(CONCAT(a.name, ' (Pos: ', ba.author_position, ', Photo: ', ba.photo_recive, ', Sent: ', ba.author_details_sent, ')') SEPARATOR ', ') AS 'Author Details'
            FROM books b
            LEFT JOIN book_authors ba ON b.book_id = ba.book_id
            LEFT JOIN authors a ON ba.author_id = a.author_id
            WHERE b.date >= '{cutoff_date_str}'
            {publish_filter}
            GROUP BY b.book_id, b.title, b.date, b.cover_by, b.cover_start, b.cover_end, b.apply_isbn, b.isbn, b.is_publish_only
            ORDER BY b.date DESC
        """
    else:
        query = f"""
            SELECT 
                book_id AS 'Book ID',
                title AS 'Title',
                date AS 'Date',
                {columns_str},
                is_publish_only AS 'Is Publish Only'
            FROM books 
            WHERE date >= '{cutoff_date_str}'
            {publish_filter}
            ORDER BY date DESC
        """
    
    df = conn.query(query, show_spinner=False)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    return df

def fetch_author_details(book_id):
    conn = connect_db()
    query = f"""
        SELECT
            ba.author_id AS 'Author ID', 
            a.name AS 'Author Name',
            ba.author_position AS 'Position',
            ba.photo_recive AS 'Photo Received',
            ba.author_details_sent AS 'Details Sent'
        FROM book_authors ba
        JOIN authors a ON ba.author_id = a.author_id
        WHERE ba.book_id = {book_id}
    """
    df = conn.query(query, show_spinner=False)
    return df


@st.dialog("Author Details", width='large')
def show_author_details_dialog(book_id):
    # Fetch book details (title and ISBN)
    conn = connect_db()
    book_query = f"SELECT title, isbn FROM books WHERE book_id = {book_id}"
    book_data = conn.query(book_query, show_spinner=False)
    book_title = book_data.iloc[0]['title'] if not book_data.empty else "Unknown Title"
    isbn = book_data.iloc[0]['isbn'] if not book_data.empty and pd.notnull(book_data.iloc[0]['isbn']) else "Not Assigned"

    # Fetch author details
    author_details_df = fetch_author_details(book_id)

    # Header
    st.markdown(f'<div class="dialog-header">Book ID: {book_id} - {book_title}</div>', unsafe_allow_html=True)

    # ISBN Display
    st.markdown('<div class="info-label">ISBN</div>', unsafe_allow_html=True)
    st.markdown(f'<span class="info-value">{isbn}</span>', unsafe_allow_html=True)

    # Author Details Table
    if not author_details_df.empty:
        # Prepare HTML table
        table_html = '<table><tr><th>Author ID</th><th>Author Name</th><th>Position</th><th>Photo Received</th><th>Details Received</th></tr>'
        for _, row in author_details_df.iterrows():
            photo_class = "pill-yes" if row["Photo Received"] else "pill-no"
            details_class = "pill-yes" if row["Details Sent"] else "pill-no"
            table_html += (
                f'<tr>'
                f'<td>{row["Author ID"]}</td>'
                f'<td>{row["Author Name"]}</td>'
                f'<td>{row["Position"]}</td>'
                f'<td><span class="{photo_class}">{"Yes" if row["Photo Received"] else "No"}</span></td>'
                f'<td><span class="{details_class}">{"Yes" if row["Details Sent"] else "No"}</span></td>'
                f'</tr>'
            )
        table_html += '</table>'
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.warning("No author details available.")

# --- Reusable Month Selector ---
def render_month_selector(books_df):
    unique_months = sorted(books_df['Date'].apply(lambda x: x.strftime('%B %Y')).unique(), 
                          key=lambda x: datetime.strptime(x, '%B %Y'), reverse=False)
    default_month = unique_months[-1]  # Most recent month
    selected_month = st.pills("Select Month", unique_months, default=default_month, 
                             key=f"month_selector_{st.session_state.get('section', 'writing')}", 
                             label_visibility='collapsed')
    return selected_month

from datetime import datetime, timedelta

def format_duration(duration):
    """Convert a timedelta to a human-readable string like '8 Hours' or '1 Day 2 Hours'."""
    total_seconds = int(duration.total_seconds())
    if total_seconds < 0:
        return "Invalid duration"
    
    days = total_seconds // (24 * 3600)
    hours = (total_seconds % (24 * 3600)) // 3600
    
    if days > 0 and hours > 0:
        return f"{days} Day{'s' if days != 1 else ''} {hours} Hour{'s' if hours != 1 else ''}"
    elif days > 0:
        return f"{days} Day{'s' if days != 1 else ''}"
    elif hours > 0:
        return f"{hours} Hour{'s' if hours != 1 else ''}"
    else:
        return "Less than an hour"

def render_worker_completion_graph(books_df, selected_month, section):
    # Convert selected_month to year and month for filtering
    selected_month_dt = datetime.strptime(selected_month, '%B %Y')
    target_period = pd.Timestamp(selected_month_dt).to_period('M')

    # Filter books where {section}_by and {section}_end are not null, and {section}_end is in the selected month
    end_col = f'{section.capitalize()} End'
    by_col = f'{section.capitalize()} By'
    start_col = f'{section.capitalize()} Start'
    completed_books = books_df[
        books_df[by_col].notnull() &
        books_df[end_col].notnull() &
        (books_df[end_col].dt.to_period('M') == target_period)
    ]

    if completed_books.empty:
        st.warning(f"No books assigned and completed in {selected_month} for {section.capitalize()}.")
        return

    # Get unique workers for dropdown, add 'All' as default
    workers = ['All'] + sorted(completed_books[by_col].unique().tolist())
    
    # Create two columns for graph and table
    col1, col2 = st.columns([1.3, 1], gap="medium", vertical_alignment="center")

    with col1:
        selected_worker = st.selectbox(
            "",
            workers,
            index=0,  # Default to 'All'
            key=f"{section}_worker_select",
            label_visibility="collapsed"
        )

        # Filter data based on selected worker
        if selected_worker != 'All':
            completed_books = completed_books[completed_books[by_col] == selected_worker]
        
        if completed_books.empty:
            st.warning(f"No books completed by {selected_worker} in {selected_month} for {section.capitalize()}.")
            return

        # Create table for book details using st.dataframe
        st.write(f"##### {section.capitalize()} Completed in {selected_month} by {selected_worker}")
        section_columns = [f'{section.capitalize()} By', f'{section.capitalize()} Start', f'{section.capitalize()} End']
        display_columns = ['Title'] + section_columns if 'Title' in books_df.columns else section_columns
        
        # Calculate time taken and split dates/times
        completed_books = completed_books.copy()  # Avoid modifying original dataframe
        completed_books['Time Taken'] = completed_books[end_col] - completed_books[start_col]
        completed_books['Time Taken'] = completed_books['Time Taken'].apply(format_duration)
        
        # Split Start and End into Date and Time with AM/PM format
        completed_books['Start Date'] = completed_books[start_col].dt.strftime('%Y-%m-%d')
        completed_books['Start Time'] = completed_books[start_col].dt.strftime('%I:%M %p')
        completed_books['End Date'] = completed_books[end_col].dt.strftime('%Y-%m-%d')
        completed_books['End Time'] = completed_books[end_col].dt.strftime('%I:%M %p')
        
        # Reorder columns to include Time Taken and split date/time
        display_columns = ['Title', 'Date', f'{section.capitalize()} By', 'Start Date', 'Start Time', 'End Date', 'End Time', 'Time Taken'] if 'Title' in books_df.columns else [f'{section.capitalize()} By', 'Start Date', 'Start Time', 'End Date', 'End Time', 'Time Taken']
        
        st.dataframe(
            completed_books[display_columns].rename(columns={
                f'{section.capitalize()} By': 'Team Member'
            }),
            hide_index=True,
            use_container_width=True
        )

    with col2:
        # Group by worker for the bar chart
        worker_counts = completed_books.groupby(by_col).size().reset_index(name='Book Count')
        if selected_worker != 'All':
            worker_counts = worker_counts[worker_counts[by_col] == selected_worker]
        
        if worker_counts.empty:
            st.warning(f"No books completed by {selected_worker} in {selected_month} for {section.capitalize()}.")
            return

        worker_counts = worker_counts.sort_values('Book Count', ascending=False)

        # Create Altair horizontal bar chart
        max_count = int(worker_counts['Book Count'].max())
        tick_values = list(range(max_count + 1))

        bar = alt.Chart(worker_counts).mark_bar(size=31).encode(
            x=alt.X('Book Count:Q', title='Number of Books Completed', axis=alt.Axis(values=tick_values, grid=True, gridOpacity=0.3)),
            y=alt.Y(f'{by_col}:N', title='Team Member', sort='-x'),
            color=alt.Color(f'{by_col}:N', scale=alt.Scale(scheme='darkgreen'), legend=None),
            tooltip=[f'{by_col}:N', 'Book Count:Q']
        )

        # Add text labels at the end of the bars
        text = bar.mark_text(
            align='left',
            baseline='middle',
            dx=4,
            color='black',
            fontSize=10
        ).encode(
            text='Book Count:Q'
        )

        # Combine bar and text
        chart = (bar + text).properties(
            title="",
            width='container',
            height=300
        ).configure_title(
            fontSize=10,
            anchor='start',
            offset=10
        ).configure_axis(
            labelFontSize=14
        )

        # Display chart
        st.write(f"##### {section.capitalize()} Completed in {selected_month} by {selected_worker}")
        st.altair_chart(chart, use_container_width=True)

    

def render_metrics(books_df, selected_month, section, user_role):
    # Convert selected_month (e.g., "April 2025") to date range
    selected_month_dt = datetime.strptime(selected_month, '%B %Y')
    month_start = selected_month_dt.replace(day=1).date()
    month_end = (selected_month_dt.replace(day=1) + timedelta(days=31)).replace(day=1).date() - timedelta(days=1)

    # Filter books based on enrollment Date for metrics
    filtered_books_metrics = books_df[(books_df['Date'] >= month_start) & (books_df['Date'] <= month_end)]

    total_books = len(filtered_books_metrics)
    
    # Completion and pending logic for all sections
    completed_books = len(filtered_books_metrics[
        filtered_books_metrics[f'{section.capitalize()} End'].notnull() & 
        (filtered_books_metrics[f'{section.capitalize()} End'] != '0000-00-00 00:00:00')
    ])
    if section == "cover":
        pending_books = len(filtered_books_metrics[
            filtered_books_metrics['Cover Start'].isnull() | 
            (filtered_books_metrics['Cover Start'] == '0000-00-00 00:00:00')
        ])
    else:
        pending_books = len(filtered_books_metrics[
            filtered_books_metrics[f'{section.capitalize()} Start'].isnull() | 
            (filtered_books_metrics[f'{section.capitalize()} Start'] == '0000-00-00 00:00:00')
        ])

    # Render UI
    col1, col2, col3 = st.columns([10, 1, 1], vertical_alignment="bottom")
    with col1:
        st.subheader(f"Metrics of {selected_month}")
        st.caption(f"Welcome {user_name}!")
    with col2:
        if st.button(":material/refresh: Refresh", key=f"refresh_{section}", type="tertiary"):
            st.cache_data.clear()

    # Go Back Button - Same Access as Pills
    if role_user == "admin" or (role_user == "user" and user_app == "main" and "Team Dashboard" in user_access):
        with col3:
            if st.button(":material/arrow_back: Go Back", key="back_button", type="tertiary", use_container_width=True):
                st.switch_page('app.py')

    col1, col2, col3 = st.columns(3, border=True)
    with col1:
        st.metric(f"Books in {selected_month}", total_books)
    with col2:
        st.metric(f"{section.capitalize()} Done in {selected_month}", completed_books)
    with col3:
        st.metric(f"Pending in {selected_month}", pending_books)
    
    # Render worker completion graph for non-Cover sections in an expander using full books_df
    if section != "cover":
        with st.expander(f"Show Completion Graph and Table for {section.capitalize()}, {selected_month}"):
            render_worker_completion_graph(books_df, selected_month, section)
    
    return filtered_books_metrics

# Helper function to fetch unique names (assumed to exist or can be added)
def fetch_unique_names(column_name, conn):
    query = f"SELECT DISTINCT {column_name} FROM books WHERE {column_name} IS NOT NULL"
    result = conn.query(query, show_spinner=False)
    return sorted(result[column_name].tolist())

# --- Helper Functions ---
def get_status(start, end, current_date, is_in_correction=False):
    if is_in_correction:
        return "In Correction", None
    if pd.isna(start) or start == '0000-00-00 00:00:00':
        return "Pending", None
    if pd.notna(start) and start != '0000-00-00 00:00:00' and pd.isna(end):
        start_date = start.date() if isinstance(start, pd.Timestamp) else pd.to_datetime(start).date()
        days = (current_date - start_date).days
        return "Running", days
    return "Completed", None

def get_days_since_enrolled(enroll_date, current_date):
    if pd.notnull(enroll_date):
        date_enrolled = enroll_date if isinstance(enroll_date, datetime) else pd.to_datetime(enroll_date).date()
        return (current_date - date_enrolled).days
    return None

def get_worker_by(start, worker_by, worker_map=None):
    if pd.notnull(start) and start != '0000-00-00 00:00:00':
        worker = worker_by if pd.notnull(worker_by) else "Unknown Worker"
        if worker_map and worker in worker_map:
            return worker, worker_map[worker]
        return worker, None
    return "Not Assigned", None


def fetch_book_details(book_id, conn):
    query = f"SELECT title FROM books WHERE book_id = {book_id}"
    return conn.query(query, show_spinner=False)


from time import sleep
from sqlalchemy.sql import text

@st.dialog("Rate User", width='large')
def rate_user_dialog(book_id, conn):
    # Fetch book title
    book_details = fetch_book_details(book_id, conn)
    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
    else:
        st.markdown(f"### Rate User for Book ID: {book_id}")
        st.warning("Book title not found.")
    
    sentiment_mapping = ["one", "two", "three", "four", "five"]
    selected = st.feedback("stars")
    if selected is not None:
        st.markdown(f"You selected {sentiment_mapping[selected]} star(s).")


@st.dialog("Correction Details", width='large')
def correction_dialog(book_id, conn, section):
    # Map section to display name and database columns
    section_config = {
        "writing": {"display": "Writing", "by": "writing_by", "start": "writing_start", "end": "writing_end"},
        "proofreading": {"display": "Proofreading", "by": "proofreading_by", "start": "proofreading_start", "end": "proofreading_end"},
        "formatting": {"display": "Formatting", "by": "formatting_by", "start": "formatting_start", "end": "formatting_end"},
        "cover": {"display": "Cover Page", "by": "cover_by", "start": "cover_start", "end": "cover_end"}
    }
    
    config = section_config.get(section, section_config["writing"])
    display_name = config["display"]

    # Fetch book title
    query = f"SELECT title FROM books WHERE book_id = :book_id"
    book_details = conn.query(query, params={"book_id": book_id}, show_spinner=False)
    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
    else:
        book_title = "Unknown Title"
        st.markdown(f"### {display_name} Correction Details for Book ID: {book_id}")
        st.warning("Book title not found.")

    # Fetch current worker (default for new corrections)
    query = f"SELECT {config['by']} AS worker FROM books WHERE book_id = :book_id"
    book_data = conn.query(query, params={"book_id": book_id}, show_spinner=False)
    default_worker = book_data.iloc[0]["worker"] if not book_data.empty and book_data.iloc[0]["worker"] else None

    # Fetch most recent correction
    query = """
        SELECT correction_id, correction_start, correction_end, worker, notes
        FROM corrections
        WHERE book_id = :book_id AND section = :section
        ORDER BY correction_start DESC
        LIMIT 1
    """
    recent_correction = conn.query(query, params={"book_id": book_id, "section": section}, show_spinner=False)
    
    # Determine if editing an ongoing correction
    is_ongoing = not recent_correction.empty and pd.isna(recent_correction.iloc[0]["correction_end"])
    correction_id = recent_correction.iloc[0]["correction_id"] if is_ongoing else None
    default_start = recent_correction.iloc[0]["correction_start"] if is_ongoing else None
    default_worker = recent_correction.iloc[0]["worker"] if is_ongoing else default_worker
    default_notes = recent_correction.iloc[0]["notes"] if is_ongoing and recent_correction.iloc[0]["notes"] else ""

    # Initialize session state
    worker_keys = [f"{section}_correction_worker", f"{section}_correction_new_worker"]
    date_keys = [
        f"{section}_correction_start_date",
        f"{section}_correction_start_time",
        f"{section}_correction_end_date",
        f"{section}_correction_end_time",
        f"{section}_correction_notes"
    ]
    worker_defaults = {
        f"{section}_correction_worker": default_worker if default_worker else "Select Team Member",
        f"{section}_correction_new_worker": ""
    }
    date_defaults = {
        f"{section}_correction_start_date": default_start.date() if default_start else datetime.now().date(),
        f"{section}_correction_start_time": default_start.time() if default_start else datetime.now().time(),
        f"{section}_correction_end_date": None,
        f"{section}_correction_end_time": None,
        f"{section}_correction_notes": default_notes
    }
    for key in worker_keys:
        if f"{key}_{book_id}" not in st.session_state:
            st.session_state[f"{key}_{book_id}"] = worker_defaults[key]
    for key in date_keys:
        if f"{key}_{book_id}" not in st.session_state:
            st.session_state[f"{key}_{book_id}"] = date_defaults[key]

    # Fetch unique names for the section
    def fetch_unique_names(column, conn):
        query = f"SELECT DISTINCT {column} FROM books WHERE {column} IS NOT NULL"
        result = conn.query(query, show_spinner=False)
        return sorted([row[column] for row in result.to_dict('records') if row[column]])
    
    names = fetch_unique_names(config["by"], conn)
    options = ["Select Team Member"] + names + ["Add New..."]

    # Custom CSS
    st.markdown("""
        <style>
        .field-label {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .changed {
            background-color: #FFF3E0;
            padding: 2px 6px;
            border-radius: 4px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Display correction history
    st.markdown(f'<div class="field-label">{display_name} Correction History</div>', unsafe_allow_html=True)
    query = """
        SELECT correction_id, correction_start, correction_end, worker, notes
        FROM corrections
        WHERE book_id = :book_id AND section = :section
        ORDER BY correction_start DESC
    """
    history_data = conn.query(query, params={"book_id": book_id, "section": section}, show_spinner=False)
    if not history_data.empty:
        history_df = history_data.rename(columns={
            "correction_id": "ID",
            "correction_start": "Start",
            "correction_end": "End",
            "worker": "Worker",
            "notes": "Notes"
        })
        history_df["Start"] = history_df["Start"].apply(lambda x: x.strftime('%Y-%m-%d %H:%M') if pd.notnull(x) else "-")
        history_df["End"] = history_df["End"].apply(lambda x: x.strftime('%Y-%m-%d %H:%M') if pd.notnull(x) else "-")
        history_df["Notes"] = history_df["Notes"].apply(lambda x: x if pd.notnull(x) else "-")
        st.dataframe(history_df, use_container_width=True, hide_index=True)
    else:
        st.info("No correction history available.")

    # Form header
    form_title = "Edit Ongoing Correction" if is_ongoing else f"Add New {display_name} Correction"
    st.markdown(f"<h4 style='color:#4CAF50;'>{form_title}</h4>", unsafe_allow_html=True)

    # Form for adding/updating correction
    with st.form(key=f"correction_form_{book_id}_{section}", border=False):
        st.markdown(f'<div class="field-label">{display_name} Team Member</div>', unsafe_allow_html=True)
        disabled = is_ongoing
        selected_worker = st.selectbox(
            "Team Member",
            options,
            index=options.index(st.session_state[f"{section}_correction_worker_{book_id}"]) if st.session_state[f"{section}_correction_worker_{book_id}"] in options else 0,
            key=f"{section}_correction_select_{book_id}",
            label_visibility="collapsed",
            help=f"Select an existing {display_name.lower()} worker or add a new one.",
            disabled=disabled
        )
        
        if selected_worker == "Add New..." and not disabled:
            st.session_state[f"{section}_correction_new_worker_{book_id}"] = st.text_input(
                "New Team Member",
                value=st.session_state[f"{section}_correction_new_worker_{book_id}"],
                key=f"{section}_correction_new_input_{book_id}",
                placeholder=f"Enter new {display_name.lower()} team member name...",
                label_visibility="collapsed"
            )
            if st.session_state[f"{section}_correction_new_worker_{book_id}"].strip():
                st.session_state[f"{section}_correction_worker_{book_id}"] = st.session_state[f"{section}_correction_new_worker_{book_id}"].strip()
        elif selected_worker != "Select Team Member" and not disabled:
            st.session_state[f"{section}_correction_worker_{book_id}"] = selected_worker
            st.session_state[f"{section}_correction_new_worker_{book_id}"] = ""
        elif not disabled:
            st.session_state[f"{section}_correction_worker_{book_id}"] = None
            st.session_state[f"{section}_correction_new_worker_{book_id}"] = ""

        worker = st.session_state[f"{section}_correction_worker_{book_id}"]
        if disabled:
            worker = default_worker

        col1, col2 = st.columns(2, gap="medium")
        with col1:
            st.markdown(f'<div class="field-label">Correction Start Date & Time</div>', unsafe_allow_html=True)
            start_date = st.date_input(
                "Start Date",
                value=st.session_state[f"{section}_correction_start_date_{book_id}"],
                key=f"{section}_correction_start_date_{book_id}",
                label_visibility="collapsed",
                help=f"When {display_name.lower()} correction began",
                disabled=disabled
            )
            start_time = st.time_input(
                "Start Time",
                value=st.session_state[f"{section}_correction_start_time_{book_id}"],
                key=f"{section}_correction_start_time_{book_id}",
                label_visibility="collapsed",
                disabled=disabled
            )
        with col2:
            st.markdown(f'<div class="field-label">Correction End Date & Time</div>', unsafe_allow_html=True)
            end_date = st.date_input(
                "End Date",
                value=st.session_state[f"{section}_correction_end_date_{book_id}"],
                key=f"{section}_correction_end_date_{book_id}",
                label_visibility="collapsed",
                help=f"When {display_name.lower()} correction was completed (leave blank if ongoing)"
            )
            end_time = st.time_input(
                "End Time",
                value=st.session_state[f"{section}_correction_end_time_{book_id}"],
                key=f"{section}_correction_end_time_{book_id}",
                label_visibility="collapsed"
            )

        st.markdown(f'<div class="field-label">Correction Notes</div>', unsafe_allow_html=True)
        notes = st.text_area(
            "Notes",
            value=st.session_state[f"{section}_correction_notes_{book_id}"],
            key=f"{section}_correction_notes_{book_id}",
            placeholder=f"Enter notes about this {display_name.lower()} correction...",
            label_visibility="collapsed",
            help=f"Optional notes about the {display_name.lower()} correction"
        )

        col_save, col_cancel = st.columns([1, 1])
        with col_save:
            submit = st.form_submit_button("💾 Save and Close", use_container_width=True)
        with col_cancel:
            cancel = st.form_submit_button("Cancel", use_container_width=True, type="secondary")

        if submit:
            if not worker:
                st.error("Please select or add a team member.")
                return
            if not start_date or not start_time:
                st.error("Please provide a start date and time.")
                return
            start = datetime.combine(start_date, start_time)
            end = datetime.combine(end_date, end_time) if end_date and end_time else None
            if start and end and start > end:
                st.error("Start must be before End.")
                return
            with st.spinner(f"Saving {display_name} correction details..."):
                sleep(2)
                updates = {
                    "book_id": book_id,
                    "section": section,
                    "correction_start": start,
                    "correction_end": end,
                    "worker": worker,
                    "notes": notes if notes.strip() else None
                }
                updates = {k: v for k, v in updates.items() if v is not None}
                insert_fields = ", ".join(updates.keys())
                insert_placeholders = ", ".join([f":{key}" for key in updates.keys()])
                
                with conn.session as s:
                    if is_ongoing:
                        # Update existing ongoing correction
                        update_clause = ", ".join([f"{key} = :{key}" for key in updates.keys() if key != "book_id" and key != "section"])
                        query = f"""
                            UPDATE corrections
                            SET {update_clause}
                            WHERE correction_id = :correction_id
                        """
                        updates["correction_id"] = correction_id
                        action = "updated"
                    else:
                        # Insert new correction
                        query = f"""
                            INSERT INTO corrections ({insert_fields})
                            VALUES ({insert_placeholders})
                        """
                        action = "added"
                    
                    s.execute(text(query), updates)
                    s.commit()
                
                # Log the form submission
                details = (
                    f"Book ID: {book_id}, {display_name} Team Member: {worker or 'None'}, "
                    f"Start: {start or 'None'}, End: {end or 'None'}, Notes: {notes or 'None'}"
                )
                try:
                    log_activity(
                        conn,
                        st.session_state.user_id,
                        st.session_state.username,
                        st.session_state.session_id,
                        f"{action} {section} correction",
                        details
                    )
                except Exception as e:
                    st.error(f"Error logging {display_name.lower()} correction details: {str(e)}")
                
                st.success(f"✔️ {action.capitalize()} {display_name} correction")
                for key in worker_keys + date_keys:
                    st.session_state.pop(f"{key}_{book_id}", None)
                sleep(1)
                st.rerun()

        elif cancel:
            for key in worker_keys + date_keys:
                st.session_state.pop(f"{key}_{book_id}", None)
            st.rerun()


@st.dialog("Edit Section Details", width='large')
def edit_section_dialog(book_id, conn, section):
    # Map section to display name and database columns
    section_config = {
        "writing": {"display": "Writing", "by": "writing_by", "start": "writing_start", "end": "writing_end"},
        "proofreading": {"display": "Proofreading", "by": "proofreading_by", "start": "proofreading_start", "end": "proofreading_end"},
        "formatting": {"display": "Formatting", "by": "formatting_by", "start": "formatting_start", "end": "formatting_end"},
        "cover": {
            "display": "Cover Page",
            "by": "cover_by",
            "start": "cover_start",
            "end": "cover_end"
        }
    }
    
    config = section_config.get(section, section_config["writing"])
    display_name = config["display"]

    # Fetch book title and current book_pages
    book_details = fetch_book_details(book_id, conn)
    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        current_book_pages = book_details.iloc[0].get('book_pages', 0)
        st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
    else:
        book_title = "Unknown Title"
        current_book_pages = 0
        st.markdown(f"### {display_name} Details for Book ID: {book_id}")
        st.warning("Book title not found.")

    # Fetch current section data
    if section == "cover":
        query = f"""
            SELECT 
                cover_start AS 'Cover Start', 
                cover_end AS 'Cover End', 
                cover_by AS 'Cover By'
            FROM books 
            WHERE book_id = {book_id}
        """
    else:
        query = f"SELECT {config['start']}, {config['end']}, {config['by']}, book_pages FROM books WHERE book_id = {book_id}"
    book_data = conn.query(query, show_spinner=False)
    current_data = book_data.iloc[0].to_dict() if not book_data.empty else {}

    # Fetch unique names for the section
    names = fetch_unique_names(config["by"], conn)
    options = ["Select Team Member"] + names + ["Add New..."]

    # Initialize session state
    keys = [
        f"{section}_by",
        f"{section}_new_worker",
        f"{section}_start_date", f"{section}_start_time",
        f"{section}_end_date", f"{section}_end_time"
    ]
    if section in ["writing", "proofreading", "formatting"]:
        keys.append(f"book_pages")
    defaults = {
        f"{section}_by": current_data.get(config["by"], ""),
        f"{section}_new_worker": "",
        f"{section}_start_date": current_data.get("Cover Start" if section == "cover" else config["start"], None),
        f"{section}_start_time": current_data.get("Cover Start" if section == "cover" else config["start"], None),
        f"{section}_end_date": current_data.get("Cover End" if section == "cover" else config["end"], None),
        f"{section}_end_time": current_data.get("Cover End" if section == "cover" else config["end"], None),
        f"book_pages": current_data.get("book_pages", current_book_pages) if section in ["writing", "proofreading", "formatting"] else None
    }
    
    for key in keys:
        if f"{key}_{book_id}" not in st.session_state:
            st.session_state[f"{key}_{book_id}"] = defaults[key]
    
    # Custom CSS
    st.markdown("""
        <style>
        .field-label {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .changed {
            background-color: #FFF3E0;
            padding: 2px 6px;
            border-radius: 4px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Worker selection (outside the form)
    st.markdown(f'<div class="field-label">{display_name} Team Member</div>', unsafe_allow_html=True)
    selected_worker = st.selectbox(
        "Team Member",
        options,
        index=options.index(st.session_state[f"{section}_by_{book_id}"]) if st.session_state[f"{section}_by_{book_id}"] in names else 0,
        key=f"{section}_select_{book_id}",
        label_visibility="collapsed",
        help=f"Select an existing {display_name.lower()} worker or add a new one."
    )
    
    # Handle worker selection
    if selected_worker == "Add New...":
        st.session_state[f"{section}_new_worker_{book_id}"] = st.text_input(
            "New Team Member",
            value=st.session_state[f"{section}_new_worker_{book_id}"],
            key=f"{section}_new_input_{book_id}",
            placeholder=f"Enter new {display_name.lower()} team Member name...",
            label_visibility="collapsed"
        )
        if st.session_state[f"{section}_new_worker_{book_id}"].strip():
            st.session_state[f"{section}_by_{book_id}"] = st.session_state[f"{section}_new_worker_{book_id}"].strip()
    elif selected_worker != "Select Team Member":
        st.session_state[f"{section}_by_{book_id}"] = selected_worker
        st.session_state[f"{section}_new_worker_{book_id}"] = ""
    else:
        st.session_state[f"{section}_by_{book_id}"] = None
        st.session_state[f"{section}_new_worker_{book_id}"] = ""

    worker = st.session_state[f"{section}_by_{book_id}"]

    # Form for date, time, and book pages inputs
    with st.form(key=f"{section}_form_{book_id}", border=False):
        # Date and Time Inputs
        col1, col2 = st.columns(2, gap="medium")
        with col1:
            st.markdown(f'<div class="field-label">Start Date & Time</div>', unsafe_allow_html=True)
            start_date = st.date_input(
                "Start Date",
                value=st.session_state[f"{section}_start_date_{book_id}"],
                key=f"{section}_start_date_{book_id}",
                label_visibility="collapsed",
                help=f"When {display_name.lower()} began"
            )
            start_time = st.time_input(
                "Start Time",
                value=st.session_state[f"{section}_start_time_{book_id}"],
                key=f"{section}_start_time_{book_id}",
                label_visibility="collapsed"
            )
        with col2:
            st.markdown(f'<div class="field-label">End Date & Time</div>', unsafe_allow_html=True)
            end_date = st.date_input(
                "End Date",
                value=st.session_state[f"{section}_end_date_{book_id}"],
                key=f"{section}_end_date_{book_id}",
                label_visibility="collapsed",
                help=f"When {display_name.lower()} was completed (leave blank if ongoing)"
            )
            end_time = st.time_input(
                "End Time",
                value=st.session_state[f"{section}_end_time_{book_id}"],
                key=f"{section}_end_time_{book_id}",
                label_visibility="collapsed"
            )
        start = f"{start_date} {start_time}" if start_date and start_time else None
        end = f"{end_date} {end_time}" if end_date and end_time else None

        # Add Total Book Pages field for writing, proofreading, and formatting
        if section in ["writing", "proofreading", "formatting"]:
            st.markdown('<div class="field-label">Total Book Pages</div>', unsafe_allow_html=True)
            book_pages = st.number_input(
                "Total Book Pages",
                min_value=0,
                value=st.session_state[f"book_pages_{book_id}"],
                key=f"book_pages_{book_id}",
                label_visibility="collapsed",
                help="Enter the total number of pages in the book"
            )

        col_save, col_cancel = st.columns([1, 1])
        with col_save:
            submit = st.form_submit_button("💾 Save and Close", use_container_width=True)
        with col_cancel:
            cancel = st.form_submit_button("Cancel", use_container_width=True, type="secondary")

        if submit:
            if start and end and start > end:
                st.error("Start must be before End.")
            else:
                with st.spinner(f"Saving {display_name} details..."):
                    sleep(2)
                    updates = {
                        config["start"]: start,
                        config["end"]: end,
                        config["by"]: worker
                    }
                    if section in ["writing", "proofreading", "formatting"]:
                        updates["book_pages"] = book_pages
                    # Remove None values from updates
                    updates = {k: v for k, v in updates.items() if v is not None}
                    with conn.session as s:
                        set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
                        query = f"UPDATE books SET {set_clause} WHERE book_id = :id"
                        params = updates.copy()
                        params["id"] = int(book_id)
                        s.execute(text(query), params)
                        s.commit()
                    
                    # Log the form submission
                    details = (
                        f"Book ID: {book_id}, {display_name} Team Member: {worker or 'None'}, "
                        f"Start: {start or 'None'}, End: {end or 'None'}"
                    )
                    if section in ["writing", "proofreading", "formatting"]:
                        details += f", Pages: {book_pages}"
                    try:
                        log_activity(
                            conn,
                            st.session_state.user_id,
                            st.session_state.username,
                            st.session_state.session_id,
                            f"updated {section} details",
                            details
                        )
                    except Exception as e:
                        st.error(f"Error logging {display_name.lower()} details: {str(e)}")
                    
                    st.success(f"✔️ Updated {display_name} details")
                    # Clear new worker input after saving
                    st.session_state[f"{section}_new_worker_{book_id}"] = ""
                    sleep(1)
                    st.rerun()

        elif cancel:
            for key in keys:
                st.session_state.pop(f"{key}_{book_id}", None)
            st.rerun()


def render_table(books_df, title, column_sizes, color, section, role, is_running=False):
    if books_df.empty:
        st.warning(f"No {title.lower()} books available from the last 3 months.")
        return
    
    cont = st.container(border=True)
    with cont:
        count = len(books_df)
        badge_color = 'yellow' if "Running" in title else 'red' if "Pending" in title else 'green'
        st.markdown(f"<h5><span class='status-badge-{badge_color}'>{title} Books <span class='badge-count'>{count}</span></span></h5>", 
                    unsafe_allow_html=True)
        st.markdown('<div class="header-row">', unsafe_allow_html=True)
        
        # Base columns
        columns = ["Book ID", "Title", "Date", "Status"]
        # Role-specific additional columns
        if role == "proofreader":
            columns.append("Writing By")
            if not is_running:
                columns.append("Writing End")
            if "Pending" in title or "Completed" in title:
                columns.append("Book Pages")
            if "Pending" in title:
                columns.append("Rating")
        elif role == "formatter":
            if not is_running:
                columns.append("Proofreading End")
            if "Pending" in title or "Completed" in title:
                columns.append("Book Pages")
        elif role == "cover_designer":
            if "Pending" in title or is_running:
                columns.extend(["Apply ISBN", "Photo", "Details"])
        elif role == "writer":
            if "Completed" in title:
                columns.append("Book Pages")
            if "Pending" in title:
                columns.append("Syllabus")
        # Adjust columns based on table type
        if is_running:
            if role == "cover_designer":
                columns.extend(["Cover By", "Action", "Details"])
            elif role == "proofreader":
                columns.extend(["Proofreading Start", "Proofreading By", "Rating", "Action"])
            elif role == "writer":
                columns.extend(["Writing Start", "Writing By", "Syllabus", "Action"])
            else:
                columns.extend([f"{section.capitalize()} Start", f"{section.capitalize()} By", "Action"])
        elif "Pending" in title:
            if role == "cover_designer":
                columns.extend(["Action", "Details"])
            else:
                columns.append("Action")
        elif "Completed" in title:
            columns.extend([f"{section.capitalize()} By", f"{section.capitalize()} End", "Correction"])
        
        # Validate column sizes
        if len(column_sizes) < len(columns):
            st.error(f"Column size mismatch in {title}: {len(columns)} columns but only {len(column_sizes)} sizes provided.")
            return
        
        col_configs = st.columns(column_sizes[:len(columns)])
        for i, col in enumerate(columns):
            with col_configs[i]:
                st.markdown(f'<span class="header">{col}</span>', unsafe_allow_html=True)
        st.markdown('</div><div class="header-line"></div>', unsafe_allow_html=True)

        # Fetch ongoing corrections for running table
        book_ids = tuple(books_df['Book ID'].tolist())
        if book_ids and is_running:
            query = """
                SELECT book_id
                FROM corrections
                WHERE section = :section AND correction_end IS NULL AND book_id IN :book_ids
            """
            with conn.session as s:
                ongoing_corrections = s.execute(text(query), {"section": section, "book_ids": book_ids}).fetchall()
                correction_book_ids = set(row.book_id for row in ongoing_corrections)
        else:
            correction_book_ids = set()

        current_date = datetime.now().date()
        # Worker maps
        if user_role == role:
            unique_workers = [w for w in books_df[f'{section.capitalize()} By'].unique() if pd.notnull(w)]
            worker_map = {worker: idx % 10 for idx, worker in enumerate(unique_workers)}
            if role == "proofreader":
                unique_writing_workers = [w for w in books_df['Writing By'].unique() if pd.notnull(w)]
                writing_worker_map = {worker: idx % 10 for idx, worker in enumerate(unique_writing_workers)}
            else:
                writing_worker_map = None
        else:
            worker_map = None
            writing_worker_map = None

        for _, row in books_df.iterrows():
            col_configs = st.columns(column_sizes[:len(columns)])
            col_idx = 0
            
            with col_configs[col_idx]:
                st.write(row['Book ID'])
            col_idx += 1
            with col_configs[col_idx]:
                title_text = row['Title']
                if role == "proofreader" and pd.notnull(row.get('is_publish_only')) and row['is_publish_only'] == 1:
                    title_text += ' <span class="pill publish-only-badge">Publish only</span>'
                st.markdown(title_text, unsafe_allow_html=True)
            col_idx += 1
            with col_configs[col_idx]:
                st.write(row['Date'].strftime('%Y-%m-%d') if pd.notnull(row['Date']) else "-")
            col_idx += 1
            with col_configs[col_idx]:
                is_in_correction = row['Book ID'] in correction_book_ids and is_running
                status, days = get_status(row[f'{section.capitalize()} Start'], row[f'{section.capitalize()} End'], current_date, is_in_correction)
                days_since = get_days_since_enrolled(row['Date'], current_date)
                status_html = f'<span class="pill status-{"correction" if is_in_correction else "pending" if status == "Pending" else "running" if status == "Running" else "completed"}">{status}'
                if days is not None and status == "Running":
                    status_html += f' {days}d'
                elif "Completed" in title:
                    start_date = row[f'{section.capitalize()} Start']
                    end_date = row[f'{section.capitalize()} End']
                    if pd.notnull(start_date) and pd.notnull(end_date) and start_date != '0000-00-00 00:00:00' and end_date != '0000-00-00 00:00:00':
                        duration = end_date - start_date
                        total_hours = duration.total_seconds() / 3600
                        if total_hours >= 24:
                            duration_days = duration.days
                            duration_hours = round(total_hours % 24)
                            duration_str = f"{duration_days}d" if duration_hours == 0 else f"{duration_days}d {duration_hours}h"
                        else:
                            duration_hours = round(total_hours)
                            duration_str = f"{duration_hours}h"
                        status_html += f' ({duration_str})'
                    else:
                        status_html += ' (-)'
                elif not is_running and days_since is not None:
                    status_html += f'<span class="since-enrolled">{days_since}d</span>'
                status_html += '</span>'
                st.markdown(status_html, unsafe_allow_html=True)
            col_idx += 1
            
            # Role-specific columns
            if role == "proofreader":
                with col_configs[col_idx]:
                    writing_by = row['Writing By']
                    value = writing_by if pd.notnull(writing_by) and writing_by else "-"
                    if writing_worker_map and value != "-":
                        writing_idx = writing_worker_map.get(writing_by)
                        class_name = f"worker-by-{writing_idx}" if writing_idx is not None else "worker-by-not"
                        st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span>{value}</span>', unsafe_allow_html=True)
                col_idx += 1
                if "Writing End" in columns:
                    with col_configs[col_idx]:
                        writing_end = row['Writing End']
                        value = writing_end.strftime('%Y-%m-%d') if not pd.isna(writing_end) and writing_end != '0000-00-00 00:00:00' else "-"
                        st.markdown(f'<span>{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                if "Book Pages" in columns:
                    with col_configs[col_idx]:
                        book_pages = row['Number of Book Pages']
                        value = str(book_pages) if pd.notnull(book_pages) and book_pages != 0 else "-"
                        st.markdown(f'<span>{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                if "Rating" in columns and not is_running:
                    with col_configs[col_idx]:
                        if st.button("Rate", key=f"rate_{section}_{row['Book ID']}"):
                            rate_user_dialog(row['Book ID'], conn)
                    col_idx += 1
            elif role == "formatter":
                if "Proofreading End" in columns:
                    with col_configs[col_idx]:
                        proofreading_end = row['Proofreading End']
                        value = proofreading_end.strftime('%Y-%m-%d') if not pd.isna(proofreading_end) and proofreading_end != '0000-00-00 00:00:00' else "-"
                        st.markdown(f'<span>{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                if "Pending" in title or "Completed" in title:
                    with col_configs[col_idx]:
                        book_pages = row['Number of Book Pages']
                        value = str(book_pages) if pd.notnull(book_pages) and book_pages != 0 else "-"
                        st.markdown(f'<span>{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
            elif role == "cover_designer":
                if "Apply ISBN" in columns:
                    with col_configs[col_idx]:
                        apply_isbn = row['Apply ISBN']
                        value = "Yes" if pd.notnull(apply_isbn) and apply_isbn else "No"
                        class_name = "pill apply-isbn-yes" if value == "Yes" else "pill apply-isbn-no"
                        st.markdown(f'<span class="{class_name}">{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                if "Photo" in columns:
                    with col_configs[col_idx]:
                        photo_received = row['All Photos Received']
                        value = "Yes" if pd.notnull(photo_received) and photo_received else "No"
                        class_name = "pill apply-isbn-yes" if value == "Yes" else "pill apply-isbn-no"
                        st.markdown(f'<span class="{class_name}">{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                if "Details" in columns:
                    with col_configs[col_idx]:
                        details_sent = row['All Details Sent']
                        value = "Yes" if pd.notnull(details_sent) and details_sent else "No"
                        class_name = "pill apply-isbn-yes" if value == "Yes" else "pill apply-isbn-no"
                        st.markdown(f'<span class="{class_name}">{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
            elif role == "writer":
                if "Book Pages" in columns:
                    with col_configs[col_idx]:
                        book_pages = row['Number of Book Pages']
                        value = str(book_pages) if pd.notnull(book_pages) and book_pages != 0 else "-"
                        st.markdown(f'<span>{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                if "Syllabus" in columns and not is_running:
                    with col_configs[col_idx]:
                        syllabus_path = row['Syllabus Path']
                        disabled = pd.isna(syllabus_path) or not syllabus_path or not os.path.exists(syllabus_path)
                        if not disabled:
                            with open(syllabus_path, "rb") as file:
                                st.download_button(
                                    label=":material/download:",
                                    data=file,
                                    file_name=syllabus_path.split("/")[-1],
                                    mime="application/pdf",
                                    key=f"download_syllabus_{section}_{row['Book ID']}",
                                    disabled=disabled,
                                    help="Download Syllabus"
                                )
                        else:
                            st.download_button(
                                label=":material/download:",
                                data="",
                                file_name="no_syllabus.pdf",
                                mime="application/pdf",
                                key=f"download_syllabus_{section}_{row['Book ID']}",
                                disabled=disabled,
                                help="No Syllabus Available"
                            )
                    col_idx += 1
            
            # Running-specific columns
            if is_running and user_role == role:
                if role == "cover_designer":
                    with col_configs[col_idx]:
                        worker = row['Cover By']
                        value = worker if pd.notnull(worker) else "Not Assigned"
                        class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
                        st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                    with col_configs[col_idx]:
                        is_in_correction = row['Book ID'] in correction_book_ids
                        if is_in_correction:
                            if st.button("Edit", key=f"edit_correction_{section}_{row['Book ID']}", help="Edit ongoing correction details"):
                                correction_dialog(row['Book ID'], conn, section)
                        else:
                            if st.button("Edit", key=f"edit_main_{section}_{row['Book ID']}", help="Edit main process details"):
                                edit_section_dialog(row['Book ID'], conn, section)
                    col_idx += 1
                    with col_configs[col_idx]:
                        if st.button("Details", key=f"details_{section}_{row['Book ID']}"):
                            show_author_details_dialog(row['Book ID'])
                elif role == "proofreader":
                    with col_configs[col_idx]:
                        start = row['Proofreading Start']
                        if pd.notnull(start) and start != '0000-00-00 00:00:00':
                            st.markdown(f'<span class="pill section-start-date">{start.strftime("%d %B %Y")}</span>', unsafe_allow_html=True)
                        else:
                            st.markdown('<span class="pill section-start-not">Not started</span>', unsafe_allow_html=True)
                    col_idx += 1
                    with col_configs[col_idx]:
                        worker = row['Proofreading By']
                        value = worker if pd.notnull(worker) else "Not Assigned"
                        class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
                        st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                    with col_configs[col_idx]:
                        if st.button("Rate", key=f"rate_{section}_{row['Book ID']}"):
                            rate_user_dialog(row['Book ID'], conn)
                    col_idx += 1
                    with col_configs[col_idx]:
                        is_in_correction = row['Book ID'] in correction_book_ids
                        if is_in_correction:
                            if st.button("Edit", key=f"edit_correction_{section}_{row['Book ID']}", help="Edit ongoing correction details"):
                                correction_dialog(row['Book ID'], conn, section)
                        else:
                            if st.button("Edit", key=f"edit_main_{section}_{row['Book ID']}", help="Edit main process details"):
                                edit_section_dialog(row['Book ID'], conn, section)
                elif role == "writer":
                    with col_configs[col_idx]:
                        start = row['Writing Start']
                        if pd.notnull(start) and start != '0000-00-00 00:00:00':
                            st.markdown(f'<span class="pill section-start-date">{start.strftime("%d %B %Y")}</span>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<span class="pill section-start-not">Not started</span>', unsafe_allow_html=True)
                    col_idx += 1
                    with col_configs[col_idx]:
                        worker = row['Writing By']
                        value = worker if pd.notnull(worker) else "Not Assigned"
                        class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
                        st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                    with col_configs[col_idx]:
                        syllabus_path = row['Syllabus Path']
                        disabled = pd.isna(syllabus_path) or not syllabus_path or not os.path.exists(syllabus_path)
                        if not disabled:
                            with open(syllabus_path, "rb") as file:
                                st.download_button(
                                    label=":material/download:",
                                    data=file,
                                    file_name=syllabus_path.split("/")[-1],
                                    mime="application/pdf",
                                    key=f"download_syllabus_{section}_{row['Book ID']}_running",
                                    disabled=disabled
                                )
                        else:
                            st.download_button(
                                label=":material/download:",
                                data="",
                                file_name="no_syllabus.pdf",
                                mime="application/pdf",
                                key=f"download_syllabus_{section}_{row['Book ID']}_running",
                                disabled=disabled
                            )
                    col_idx += 1
                    with col_configs[col_idx]:
                        is_in_correction = row['Book ID'] in correction_book_ids
                        if is_in_correction:
                            if st.button("Edit", key=f"edit_correction_{section}_{row['Book ID']}", help="Edit ongoing correction details"):
                                correction_dialog(row['Book ID'], conn, section)
                        else:
                            if st.button("Edit", key=f"edit_main_{section}_{row['Book ID']}", help="Edit main process details"):
                                edit_section_dialog(row['Book ID'], conn, section)
                else:
                    with col_configs[col_idx]:
                        start = row[f'{section.capitalize()} Start']
                        if pd.notnull(start) and start != '0000-00-00 00:00:00':
                            st.markdown(f'<span class="pill section-start-date">{start.strftime("%d %B %Y")}</span>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<span class="pill section-start-not">Not started</span>', unsafe_allow_html=True)
                    col_idx += 1
                    with col_configs[col_idx]:
                        worker = row[f'{section.capitalize()} By']
                        value = worker if pd.notnull(worker) else "Not Assigned"
                        class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
                        st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                    with col_configs[col_idx]:
                        is_in_correction = row['Book ID'] in correction_book_ids
                        if is_in_correction:
                            if st.button("Edit", key=f"edit_correction_{section}_{row['Book ID']}", help="Edit ongoing correction details"):
                                correction_dialog(row['Book ID'], conn, section)
                        else:
                            if st.button("Edit", key=f"edit_main_{section}_{row['Book ID']}", help="Edit main process details"):
                                edit_section_dialog(row['Book ID'], conn, section)
            # Pending-specific column
            elif "Pending" in title and user_role == role:
                if role == "cover_designer":
                    with col_configs[col_idx]:
                        if st.button("Edit", key=f"edit_{section}_{row['Book ID']}"):
                            edit_section_dialog(row['Book ID'], conn, section)
                    col_idx += 1
                    with col_configs[col_idx]:
                        if st.button("Details", key=f"details_{section}_{row['Book ID']}"):
                            show_author_details_dialog(row['Book ID'])
                else:
                    with col_configs[col_idx]:
                        if st.button("Edit", key=f"edit_{section}_{row['Book ID']}"):
                            edit_section_dialog(row['Book ID'], conn, section)
            # Completed-specific columns
            elif "Completed" in title:
                if role == "proofreader":
                    with col_configs[col_idx]:
                        worker = row['Proofreading By']
                        value = worker if pd.notnull(worker) else "-"
                        class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
                        st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                elif role == "formatter":
                    with col_configs[col_idx]:
                        worker = row['Formatting By']
                        value = worker if pd.notnull(worker) else "-"
                        class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
                        st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                elif role == "cover_designer":
                    with col_configs[col_idx]:
                        worker = row['Cover By']
                        value = worker if pd.notnull(worker) else "-"
                        class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
                        st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                elif role == "writer":
                    with col_configs[col_idx]:
                        worker = row['Writing By']
                        value = worker if pd.notnull(worker) else "-"
                        class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
                        st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                with col_configs[col_idx]:
                    end_date = row[f'{section.capitalize()} End']
                    value = end_date.strftime('%Y-%m-%d') if not pd.isna(end_date) and end_date != '0000-00-00 00:00:00' else "-"
                    st.markdown(f'<span>{value}</span>', unsafe_allow_html=True)
                col_idx += 1
                with col_configs[col_idx]:
                    if st.button("Edit", key=f"correction_{section}_{row['Book ID']}"):
                        correction_dialog(row['Book ID'], conn, section)

# --- Section Configuration ---
sections = {
    "writing": {"role": "writer", "color": "unused"},
    "proofreading": {"role": "proofreader", "color": "unused"},
    "formatting": {"role": "formatter", "color": "unused"},
    "cover": {"role": "cover_designer", "color": "unused"}
}

for section, config in sections.items():
    if user_role == config["role"] or user_role == "admin":
        st.session_state['section'] = section
        books_df = fetch_books(months_back=4, section=section)
        
        # Fetch books with ongoing corrections
        query = """
            SELECT DISTINCT book_id
            FROM corrections
            WHERE section = :section AND correction_end IS NULL
        """
        ongoing_corrections = conn.query(query, params={"section": section}, show_spinner=False)
        ongoing_correction_ids = set(ongoing_corrections["book_id"].tolist())
        
        if section == "writing":
            running_books = books_df[
                (books_df['Writing Start'].notnull() & books_df['Writing End'].isnull()) |
                (books_df['Book ID'].isin(ongoing_correction_ids))
            ]
            pending_books = books_df[
                (books_df['Writing Start'].isnull()) &
                (books_df['Is Publish Only'] != 1) &
                (~books_df['Book ID'].isin(ongoing_correction_ids))
            ]
            completed_books = books_df[
                (books_df['Writing End'].notnull()) &
                (~books_df['Book ID'].isin(ongoing_correction_ids))
            ]
        elif section == "proofreading":
            running_books = books_df[
                (books_df['Proofreading Start'].notnull() & books_df['Proofreading End'].isnull()) |
                (books_df['Book ID'].isin(ongoing_correction_ids))
            ]
            pending_books = books_df[
                ((books_df['Writing End'].notnull()) | (books_df['Is Publish Only'] == 1)) &
                (books_df['Proofreading Start'].isnull()) &
                (~books_df['Book ID'].isin(ongoing_correction_ids))
            ]
            completed_books = books_df[
                (books_df['Proofreading End'].notnull()) &
                (~books_df['Book ID'].isin(ongoing_correction_ids))
            ]
        elif section == "formatting":
            running_books = books_df[
                (books_df['Formatting Start'].notnull() & books_df['Formatting End'].isnull()) |
                (books_df['Book ID'].isin(ongoing_correction_ids))
            ]
            pending_books = books_df[
                (books_df['Proofreading End'].notnull()) &
                (books_df['Formatting Start'].isnull()) &
                (~books_df['Book ID'].isin(ongoing_correction_ids))
            ]
            completed_books = books_df[
                (books_df['Formatting End'].notnull()) &
                (~books_df['Book ID'].isin(ongoing_correction_ids))
            ]
        elif section == "cover":
            running_books = books_df[
                (books_df['Cover Start'].notnull() & books_df['Cover End'].isnull()) |
                (books_df['Book ID'].isin(ongoing_correction_ids))
            ]
            pending_books = books_df[
                (books_df['Cover Start'].isnull()) &
                (~books_df['Book ID'].isin(ongoing_correction_ids))
            ]
            completed_books = books_df[
                (books_df['Cover End'].notnull()) &
                (~books_df['Book ID'].isin(ongoing_correction_ids))
            ]

        # Sort Pending table by Date (oldest first)
        pending_books = pending_books.sort_values(by='Date', ascending=True)

        # Column sizes (from your previous code)
        if section == "writing":
            column_sizes_running = [0.7, 5.2, 1, 1.2, 1.2, 1.2, 1, 1]
            column_sizes_pending = [0.7, 5.5, 1, 1, 0.8, 1]
            column_sizes_completed = [0.7, 5, 1, 1.3, 1, 1, 1, 1]
        elif section == "proofreading":
            column_sizes_running = [0.8, 5.5, 1, 1.2, 1, 1.2, 1.2, 1, 1]
            column_sizes_pending = [0.8, 5.5, 1, 1.2, 1, 1, 1, 0.8, 0.8]
            column_sizes_completed = [0.7, 3, 1, 1.3, 1.1, 1, 1, 1, 1, 1]
        elif section == "formatting":
            column_sizes_running = [0.7, 5.5, 1, 1, 1.2, 1.2, 1]
            column_sizes_pending = [0.7, 5.5, 1, 1, 1.2, 1, 1]
            column_sizes_completed = [0.7, 3, 1, 1.3, 1.2, 1, 1, 1, 1]
        elif section == "cover":
            column_sizes_running = [0.8, 5, 1.2, 1.2, 1, 1, 1, 1, 1, 1]
            column_sizes_pending = [0.8, 5.5, 1, 1.2, 1, 1, 1, 0.8, 1]
            column_sizes_completed = [0.7, 5.5, 1, 1.5, 1.3, 1.3, 1, 1]

        # Initialize session state for completed table visibility
        if f"show_{section}_completed" not in st.session_state:
            st.session_state[f"show_{section}_completed"] = False

        selected_month = render_month_selector(books_df)
        render_metrics(books_df, selected_month, section, role_user)
        render_table(running_books, f"{section.capitalize()} Running", column_sizes_running, config["color"], section, config["role"], is_running=True)
        render_table(pending_books, f"{section.capitalize()} Pending", column_sizes_pending, config["color"], section, config["role"], is_running=False)
        
        # Show completed table toggle
        if st.button(f"Show {section.capitalize()} Completed Books", key=f"show_{section}_completed_button"):
            st.session_state[f"show_{section}_completed"] = not st.session_state[f"show_{section}_completed"]
        
        if st.session_state[f"show_{section}_completed"]:
            render_table(completed_books, f"{section.capitalize()} Completed", column_sizes_completed, config["color"], section, config["role"], is_running=False)