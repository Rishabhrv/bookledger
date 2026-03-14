import streamlit as st
import warnings 
import pandas as pd
import os
import uuid
import altair as alt
from datetime import datetime, timezone, timedelta, time
from time import sleep
from sqlalchemy import text
from auth import validate_token
from constants import (
    log_activity, connect_db, get_page_url, 
    initialize_click_and_session_id, get_total_unread_count, connect_ict_db
)
from urllib.parse import urlencode, quote

warnings.simplefilter('ignore')

# --- Page Configuration ---
st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="chart_with_upwards_trend",  
    page_title="Content Dashboard (V2)",
)

# --- CSS Parity ---
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
        background-color: #FFF3E0;
        color: #FB8C00;
        font-weight: bold;
    }
    .status-hold {
        background-color: #FFEFE6;
        color: #E65100;
        font-weight: bold;
    }
    .on-hold {
        background-color: #FFEFE6;
        color: #E65100;
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
        background-color: #FFF3E0; /* soft orange background */
        color: #FB8C00;           /* vibrant orange text */
        padding: 4px 8px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
    }
    .status-badge-orange {
        background-color: #FFEFE6; /* light peachy orange */
        color: #E65100;           /* deep burnt orange */
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
    .on-hold {
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
            
    .thesis-to-book-badge {
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
            /* Timeline styles */
        .timeline {
            position: relative;
            padding-left: 40px;
            margin: 0;
            font-family: Arial, sans-serif;
            font-size: 14px;
            line-height: 1.5;
        }
        .timeline::before {
            content: '';
            position: absolute;
            top: 0;
            bottom: 0;
            left: 15px;
            width: 2px;
            background: #4CAF50;
        }
        .timeline-item {
            position: relative;
            margin-bottom: 6px;
            padding-left: 20px;
        }
        .timeline-item::before {
            content: '';
            position: absolute;
            left: -25px;
            top: 5px;
            width: 10px;
            height: 10px;
            background: #fff;
            border: 2px solid #4CAF50;
            border-radius: 50%;
        }
        .timeline-time {
            font-weight: bold;
            color: #333;
            display: inline-block;
            min-width: 140px;
        }
        .timeline-event {
            color: #555;
        }
        .timeline-notes {
            color: #777;
            font-style: italic;
            font-size: 12px;
            display: block;
            margin-top: 2px;
        }
        
        /* Other element styles */
        .field-label {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .changed {
            background-color: #FFF3E0;
            padding: 2px 6px;
            border-radius: 4px;
        }

        /* Timeline styles */
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

# --- Authentication ---
validate_token()
role_user = st.session_state.get("role", "Unknown")
user_app = st.session_state.get("app", "Unknown")
user_name = st.session_state.get("username", "Unknown")
user_id = st.session_state.get("user_id", None)
user_access = st.session_state.get("access", [])
token = st.session_state.token

# --- Section Routing ---
SECTION_LABELS = {
    "Writing Section": "writer",
    "Proofreading Section": "proofreader",
    "Formatting Section": "formatter",
    "Cover Design Section": "cover_designer",
    "Correction Hub": "correction_hub",
    "History": "book_timeline"
}

if role_user == "admin" or (role_user == "user" and user_app == "main" and "Team Dashboard" in user_access):
    selected = st.segmented_control("Select Section", list(SECTION_LABELS.keys()), default="Writing Section", key="section_selector", label_visibility='collapsed')
    if not selected: st.stop()
    user_role = SECTION_LABELS[selected]
elif role_user == "user" and user_app == "operations":
    user_role = user_access[0] if user_access else ""
else:
    st.error("Access Denied"); st.stop()

st.cache_data.clear()

# --- Logging & Database ---
conn = connect_db()
ict_conn = connect_ict_db()
initialize_click_and_session_id()
session_id = st.session_state.get("session_id", "Unknown")
click_id = st.session_state.get("click_id", None)

if user_app == "operations" and not st.session_state.get("activity_logged", False):
    log_activity(conn, user_id, user_name, session_id, "logged in", f"App: {user_app}")
    st.session_state.activity_logged = True

if click_id and click_id not in st.session_state.get("logged_click_ids", set()):
    log_activity(conn, user_id, user_name, session_id, "navigated to page", "Team Dashboard V2")
    if "logged_click_ids" not in st.session_state: st.session_state.logged_click_ids = set()
    st.session_state.logged_click_ids.add(click_id)

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
                "syllabus_path AS 'Syllabus Path'",
                "book_note AS 'book_note'"
            ],
            "extra": [],
            "publish_filter": "AND b.is_publish_only = 0 AND b.is_thesis_to_book = 0"
        },
        "proofreading": {
            "base": [
                "proofreading_by AS 'Proofreading By'", 
                "proofreading_start AS 'Proofreading Start'", 
                "proofreading_end AS 'Proofreading End'",
                "b.is_publish_only AS 'is_publish_only'",
                "b.is_thesis_to_book AS 'is_thesis_to_book'",
                "book_note AS 'book_note'"
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
                "book_pages AS 'Number of Book Pages'",
                "book_note AS 'book_note'"
            ],
            "extra": ["proofreading_end AS 'Proofreading End'"],
            "publish_filter": ""
        },
        "cover": {
            "base": [
                "cover_by AS 'Cover By'", 
                "cover_start AS 'Cover Start'", 
                "cover_end AS 'Cover End'", 
                "isbn AS 'ISBN'",
                "book_note AS 'book_note'"
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
                b.is_thesis_to_book AS 'Is Thesis to Book',
                h.hold_start AS 'hold_start',
                h.resume_time AS 'resume_time',
                GROUP_CONCAT(CONCAT(a.name, ' (Pos: ', ba.author_position, ', Photo: ', ba.photo_recive, ', Sent: ', ba.author_details_sent, ')') SEPARATOR ', ') AS 'Author Details'
            FROM books b
            LEFT JOIN book_authors ba ON b.book_id = ba.book_id
            LEFT JOIN authors a ON ba.author_id = a.author_id
            LEFT JOIN holds h ON b.book_id = h.book_id AND h.section = '{section}'
            WHERE b.date >= '{cutoff_date_str}' AND b.is_cancelled = 0
            {publish_filter}
            GROUP BY b.book_id, b.title, b.date, {', '.join(c.split(' AS ')[0] for c in columns)}, b.is_publish_only, b.is_thesis_to_book, h.hold_start, h.resume_time
            ORDER BY b.date DESC
        """
    else:
        query = f"""
            SELECT 
                b.book_id AS 'Book ID',
                b.title AS 'Title',
                b.date AS 'Date',
                {columns_str},
                b.is_publish_only AS 'Is Publish Only',
                b.is_thesis_to_book AS 'Is Thesis to Book',
                h.hold_start AS 'hold_start',
                h.resume_time AS 'resume_time',
                h.reason AS 'hold_reason'
            FROM books b
            LEFT JOIN holds h ON b.book_id = h.book_id AND h.section = '{section}'
            WHERE b.date >= '{cutoff_date_str}' AND b.is_cancelled = 0
            {publish_filter}
            ORDER BY b.date DESC
        """
    
    df = conn.query(query, show_spinner=False)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df['hold_start'] = pd.to_datetime(df['hold_start'])
    df['resume_time'] = pd.to_datetime(df['resume_time'])
    return df

def fetch_correction_books(section: str) -> pd.DataFrame:
    conn = connect_db()
    # Map section slug to DB Enum value
    status_map = {
        "writing": "Writing",
        "proofreading": "Proofreading",
        "formatting": "Formatting",
        "cover": "Cover"
    }
    target_status = status_map.get(section)
    
    if not target_status:
        return pd.DataFrame()

    query = f"""
        SELECT 
            b.book_id AS 'Book ID',
            b.title AS 'Title',
            b.date AS 'Date',
            (SELECT COALESCE(MAX(round_number), 0) FROM author_corrections ac WHERE ac.book_id = b.book_id) AS 'Round',
            b.correction_status AS 'Status',
            (SELECT COUNT(*) FROM corrections c WHERE c.book_id = b.book_id AND c.correction_end IS NULL AND c.section = '{section}') as 'Active Tasks',
            (SELECT MAX(created_at) FROM author_corrections ac WHERE ac.book_id = b.book_id) AS 'Correction Date',
            (SELECT correction_file FROM author_corrections ac WHERE ac.book_id = b.book_id ORDER BY round_number DESC, created_at DESC LIMIT 1) AS 'Correction File',
            (SELECT correction_text FROM author_corrections ac WHERE ac.book_id = b.book_id ORDER BY round_number DESC, created_at DESC LIMIT 1) AS 'Correction Text',
            (SELECT worker FROM corrections c WHERE c.book_id = b.book_id AND c.correction_end IS NULL AND c.section = '{section}' ORDER BY correction_start DESC LIMIT 1) AS 'Correction By',
            (SELECT correction_start FROM corrections c WHERE c.book_id = b.book_id AND c.correction_end IS NULL AND c.section = '{section}' ORDER BY correction_start DESC LIMIT 1) AS 'Correction Start',
            (SELECT is_internal FROM corrections c WHERE c.book_id = b.book_id AND c.correction_end IS NULL AND c.section = '{section}' ORDER BY correction_start DESC LIMIT 1) AS 'is_internal'
        FROM books b
        WHERE (b.correction_status = '{target_status}' OR 
               EXISTS (SELECT 1 FROM corrections c WHERE c.book_id = b.book_id AND c.correction_end IS NULL AND c.section = '{section}'))
          AND b.is_cancelled = 0
        ORDER BY b.date DESC
    """
    return conn.query(query, show_spinner=False)


def fetch_author_details(book_id):
    conn = connect_db()
    query = f"""
        SELECT
            ba.author_id AS 'Author ID', 
            a.name AS 'Author Name',
            ba.author_position AS 'Position',
            ba.photo_recive AS 'Photo Received',
            ba.author_details_sent AS 'Details Sent',
            a.about_author AS 'About Author',
            a.author_photo AS 'Author Photo Path'
        FROM book_authors ba
        JOIN authors a ON ba.author_id = a.author_id
        WHERE ba.book_id = {book_id}
    """
    df = conn.query(query, show_spinner=False)
    return df

def fetch_holds(section: str) -> pd.DataFrame:
    conn = connect_db()
    query = """
        SELECT 
            book_id,
            section,
            hold_start,
            resume_time
        FROM holds
        WHERE section = :section
    """
    holds_df = conn.query(query, params={"section": section}, show_spinner=False)
    holds_df['hold_start'] = pd.to_datetime(holds_df['hold_start'])
    holds_df['resume_time'] = pd.to_datetime(holds_df['resume_time'])
    return holds_df

def fetch_unique_names(column_name, conn):
    query = f"SELECT DISTINCT {column_name} FROM books WHERE {column_name} IS NOT NULL"
    result = conn.query(query, show_spinner=False)
    return sorted(result[column_name].tolist())

def calculate_working_duration(start_date, end_date, hold_periods=None):
    """Calculate duration in working hours (09:30–18:00, Mon–Sat) between two timestamps,
       excluding hold periods. Returns (total_days, remaining_hours, remaining_minutes) where 1 day = 8.5 hours."""
    
    if pd.isna(start_date) or pd.isna(end_date):
        return (0, 0, 0)
    if start_date >= end_date:
        return (0, 0, 0)
    
    # Working day limits
    work_start = time(9, 30)
    work_end = time(18, 0)
    work_day_hours = 8.5

    total_minutes = 0
    current = start_date

    # Process hold periods
    if hold_periods is None:
        hold_periods = []
    # Filter valid hold periods and ensure they are within start_date and end_date
    valid_hold_periods = []
    for hold_start, hold_end in hold_periods:
        if pd.isna(hold_start) or (hold_end is not None and pd.isna(hold_end)):
            continue
        hold_start = max(hold_start, start_date) if pd.notnull(hold_start) else start_date
        hold_end = min(hold_end, end_date) if pd.notnull(hold_end) else end_date
        if hold_start < hold_end:
            valid_hold_periods.append((hold_start, hold_end))

    while current.date() <= end_date.date():
        # Skip Sundays
        if current.weekday() != 6:
            day_start = datetime.combine(current.date(), work_start)
            day_end = datetime.combine(current.date(), work_end)

            actual_start = max(day_start, start_date)
            actual_end = min(day_end, end_date)

            if actual_start < actual_end:
                day_minutes = (actual_end - actual_start).total_seconds() / 60
                for hold_start, hold_end in valid_hold_periods:
                    hold_start_in_day = max(hold_start, actual_start)
                    hold_end_in_day = min(hold_end, actual_end)
                    if hold_start_in_day < hold_end_in_day:
                        hold_duration = (hold_end_in_day - hold_start_in_day).total_seconds() / 60
                        day_minutes -= hold_duration
                if day_minutes > 0:
                    total_minutes += day_minutes

        current += timedelta(days=1)
        current = current.replace(hour=0, minute=0, second=0, microsecond=0)

    total_hours = total_minutes / 60.0
    total_days = int(total_hours // work_day_hours)
    remaining_hours = int((total_hours % work_day_hours))
    remaining_minutes = int(round((total_hours % 1) * 60))
    
    # Handle minute overflow to hours if rounding up
    if remaining_minutes >= 60:
        remaining_minutes -= 60
        remaining_hours += 1
    
    # Handle hour overflow to days
    if remaining_hours >= work_day_hours:
        remaining_hours -= work_day_hours
        total_days += 1

    return (total_days, int(remaining_hours), int(remaining_minutes))

def get_status(start, end, current_date):
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

def fetch_book_details(book_id, conn):
    query = f"SELECT title, book_note, book_pages FROM books WHERE book_id = {book_id}"
    return conn.query(query, show_spinner=False)


def get_hold_periods(holds_df, book_id, section, end_date=None):
    """Helper to extract hold periods for a specific book and section."""
    if holds_df is None or holds_df.empty:
        return []
    relevant = holds_df[(holds_df['book_id'] == book_id) & (holds_df['section'] == section)]
    return [(h['hold_start'], h['resume_time'] or end_date) for _, h in relevant.iterrows()]

# --- UI Components ---
def render_status_badge(row, section, title, is_active, holds_df=None):
    current_date = datetime.now().date()
    book_id = row['Book ID']
    
    # Pre-calculate hold periods if holds_df is provided
    book_holds = get_hold_periods(holds_df, book_id, section)

    if "Hold" in title:
        hs = row.get('hold_start', pd.NaT)
        days = (current_date - hs.date()).days if pd.notnull(hs) else 0
        st.markdown(f'<span class="pill status-hold">On Hold <span class="since-enrolled">{days}d</span></span>', unsafe_allow_html=True)
    else:
        st_date = row[f"{section.capitalize()} Start"]
        en_date = row[f"{section.capitalize()} End"]
        status, _ = get_status(st_date, en_date, current_date)
        
        if status == "Pending":
            enrolled_days = (current_date - (row['Date'] if isinstance(row['Date'], datetime) else pd.to_datetime(row['Date']).date())).days
            st.markdown(f'<span class="pill status-pending">Pending <span class="since-enrolled">{enrolled_days}d</span></span>', unsafe_allow_html=True)
        elif status == "Running":
            # Pass holds to duration calculator
            d, h, m = calculate_working_duration(st_date, datetime.now(), hold_periods=book_holds)
            time_str = f"{d}d" + (f" {h}h" if h > 0 else "")
            st.markdown(f'<span class="pill status-running">Running <span class="since-enrolled">{time_str}</span></span>', unsafe_allow_html=True)
        elif status == "Completed":
            # Pass holds to duration calculator
            d, h, m = calculate_working_duration(st_date, en_date, hold_periods=book_holds)
            time_str = f"{d}d" + (f" {h}h" if h > 0 else "")
            st.markdown(f'<span class="pill status-completed">Completed <span class="since-enrolled">{time_str}</span></span>', unsafe_allow_html=True)

def render_worker_pill(worker, mapping):
    if pd.isnull(worker) or worker == '-': 
        st.markdown('<span class="pill worker-by-not">Not Assigned</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'<span class="pill worker-by-{mapping.get(worker, 0)}">{worker}</span>', unsafe_allow_html=True)

# --- Generic Table Engine ---
def smart_table_engine(df, title, section, role, table_type, config, holds_df=None):
    if df.empty: return
    with st.container(border=True):
        badge = "orange" if "Hold" in title else "yellow" if "Running" in title else "red" if "Pending" in title else "green"
        st.markdown(f"<h5><span class='status-badge-{badge}'>{title} Books <span class='badge-count'>{len(df)}</span></span></h5>", unsafe_allow_html=True)
        
        # Search for completed
        filtered_df = df
        if "Completed" in title:
            search = st.text_input("", placeholder="Search ID or Title", key=f"s_{section}_{table_type}", label_visibility="collapsed")
            if search:
                filtered_df = df[df['Book ID'].astype(str).str.contains(search, case=False) | df['Title'].str.contains(search, case=False)]
        
        cols = config['columns'][table_type]
        sizes = config['sizes'][table_type]
        
        # Header
        st.markdown('<div class="header-row">', unsafe_allow_html=True)
        h_cols = st.columns(sizes)
        for i, c in enumerate(cols): h_cols[i].markdown(f'<span class="header">{c}</span>', unsafe_allow_html=True)
        st.markdown('</div><div class="header-line"></div>', unsafe_allow_html=True)
        
        # Worker Mapping
        worker_cols = [c for c in df.columns if "By" in c]
        worker_map = {w: i % 10 for i, w in enumerate(df[worker_cols[0]].unique()) if pd.notnull(w)} if worker_cols else {}
        
        for _, row in filtered_df.iterrows():
            r_cols = st.columns(sizes, vertical_alignment="center")
            for i, c in enumerate(cols):
                with r_cols[i]:
                    if c == "Book ID": st.write(row['Book ID'])
                    elif c == "Title":
                        t = row['Title']
                        if pd.notnull(row.get('hold_start')): t += ' <span class="history-icon" title="Previously on hold">:material/pause:</span>'
                        if row.get('book_note'): t += f' <span class="note-icon" title="{row["book_note"][:50]}...">:material/forum:</span>'
                        if role == "proofreader":
                            if row.get('Is Publish Only'): t += ' <span class="pill publish-only-badge">Publish only</span>'
                            if row.get('Is Thesis to Book'): t += ' <span class="pill thesis-to-book-badge">Thesis to Book</span>'
                        st.markdown(t, unsafe_allow_html=True)
                    elif c == "Date": st.write(row['Date'].strftime('%Y-%m-%d'))
                    elif c == "Status": render_status_badge(row, section, title, table_type in ["running", "on_hold"], holds_df=holds_df)
                    elif "By" in c: render_worker_pill(row[c], worker_map)
                    elif "End" in c or "Start" in c or "Since" in c:
                        val = row.get(c if c != "Hold Since" else "hold_start")
                        st.write(val.strftime('%Y-%m-%d') if pd.notnull(val) else "-")
                    elif c == "Book Pages": st.write(row['Number of Book Pages'] if row['Number of Book Pages'] else "-")
                    elif c == "ISBN":
                        v = "Yes" if pd.notnull(row.get('ISBN')) and row['ISBN'] else "No"
                        st.markdown(f'<span class="pill apply-isbn-{"yes" if v == "Yes" else "no"}">{v}</span>', unsafe_allow_html=True)
                    elif c in ["Photo", "Details"]:
                        v = "Yes" if row.get(f"All {'Photos' if c == 'Photo' else 'Details'} {'Received' if c == 'Photo' else 'Sent'}") else "No"
                        st.markdown(f'<span class="pill apply-isbn-{"yes" if v == "Yes" else "no"}">{v}</span>', unsafe_allow_html=True)
                    elif c == "Syllabus":
                        p = row.get('Syllabus Path')
                        disabled = pd.isna(p) or not p or not os.path.exists(p)
                        if not disabled:
                            with open(p, "rb") as f:
                                st.download_button(":material/download:", f, os.path.basename(p), key=f"dl_s_{row['Book ID']}_{table_type}", on_click=lambda: log_activity(conn, user_id, user_name, session_id, "downloaded syllabus", f"ID: {row['Book ID']}"))
                        else: st.download_button(":material/download:", "", disabled=True, key=f"dl_s_{row['Book ID']}_{table_type}")
                    elif c == "Rating":
                        if st.button("Rate", key=f"rate_{section}_{row['Book ID']}"):
                            rate_user_dialog(row['Book ID'], conn)
                    elif c == "Action":
                        if table_type in ["running", "on_hold", "pending"]:
                            if st.button("Edit", key=f"btn_{table_type}_{section}_{row['Book ID']}"):
                                edit_section_dialog(row['Book ID'], conn, section)
                        elif table_type == "completed":
                            if st.button("Correction", key=f"corr_{section}_{row['Book ID']}", help="Start an internal correction"):
                                internal_correction_dialog(row['Book ID'], conn, section)
                    elif c == "Details":
                        if st.button("Details", key=f"det_{table_type}_{section}_{row['Book ID']}"): show_author_details_dialog(row['Book ID'])


# --- Section Configurations ---
CONFIG = {
    "writing": {
        "columns": {
            "running": ["Book ID", "Title", "Date", "Status", "Writing Start", "Writing By", "Syllabus", "Action"],
            "on_hold": ["Book ID", "Title", "Date", "Status", "Hold Since", "Writing By", "Syllabus", "Action"],
            "pending": ["Book ID", "Title", "Date", "Status", "Syllabus", "Action"],
            "completed": ["Book ID", "Title", "Date", "Status", "Book Pages", "Writing By", "Writing End", "Action"]
        },
        "sizes": {
            "running": [0.7, 5.2, 1, 1.3, 1.3, 1.2, 1, 1],
            "on_hold": [0.7, 5.2, 1, 1, 1, 1.2, 1, 1],
            "pending": [0.7, 5.5, 1, 1, 0.8, 1],
            "completed": [0.7, 4.5, 1, 1.2, 1, 1, 1, 1]
        }
    },
    "proofreading": {
        "columns": {
            "running": ["Book ID", "Title", "Date", "Status", "Proofreading Start", "Proofreading By", "Action"],
            "on_hold": ["Book ID", "Title", "Date", "Status", "Hold Since", "Proofreading By", "Action"],
            "pending": ["Book ID", "Title", "Date", "Status", "Writing By", "Writing End", "Book Pages", "Action"],
            "completed": ["Book ID", "Title", "Date", "Status", "Proofreading By", "Proofreading End", "Action"]
        },
        "sizes": {
            "running": [0.7, 5, 1, 1.2, 1.6, 1.2, 1],
            "on_hold": [0.7, 5, 1, 1.2, 1, 1.2, 1],
            "pending": [0.8, 5.5, 1, 1.2, 1, 1, 1, 1],
            "completed": [0.7, 4.5, 1, 1.2, 1, 1, 1]
        }
    },
    "formatting": {
        "columns": {
            "running": ["Book ID", "Title", "Date", "Status", "Formatting Start", "Formatting By", "Action"],
            "on_hold": ["Book ID", "Title", "Date", "Status", "Hold Since", "Formatting By", "Action"],
            "pending": ["Book ID", "Title", "Date", "Status", "Proofreading End", "Book Pages", "Action"],
            "completed": ["Book ID", "Title", "Date", "Status", "Formatting By", "Formatting End", "Action"]
        },
        "sizes": {
            "running": [0.7, 5.5, 1, 1, 1.2, 1.2, 1],
            "on_hold": [0.7, 5.5, 1, 1, 1, 1.2, 1],
            "pending": [0.7, 5.5, 1, 1, 1.2, 1, 1],
            "completed": [0.7, 4.5, 1, 1.2, 1, 1, 1]
        }
    },
    "cover": {
        "columns": {
            "running": ["Book ID", "Title", "Date", "Status", "ISBN", "Photo", "Details", "Cover By", "Action", "Details"],
            "on_hold": ["Book ID", "Title", "Date", "Status", "ISBN", "Photo", "Details", "Hold Since", "Cover By", "Action", "Details"],
            "pending": ["Book ID", "Title", "Date", "Status", "ISBN", "Photo", "Details", "Action", "Details"],
            "completed": ["Book ID", "Title", "Date", "Status", "Cover By", "Cover End", "Action"]
        },
        "sizes": {
            "running": [0.8, 5, 1.2, 1.3, 1, 1, 1, 1, 1, 1],
            "on_hold": [0.8, 3, 1.1, 1.2, 1, 1, 1, 1, 1, 1, 1],
            "pending": [0.8, 5.5, 1, 1.2, 1, 1, 1, 0.8, 1],
            "completed": [0.7, 5, 1, 1.3, 1.2, 1.2, 1]
        }
    }
}

# --- Reusable Components from V1 ---

@st.dialog("Author Details", width="large")
def show_author_details_dialog(book_id):
    # Fetch book details (title, ISBN, and about text)
    conn = connect_db()
    book_query = f"SELECT title, isbn, about_book, about_book_200 FROM books WHERE book_id = {book_id}"
    book_data = conn.query(book_query, show_spinner=False)
    
    if not book_data.empty:
        row = book_data.iloc[0]
        book_title = row['title']
        isbn = row['isbn'] if pd.notnull(row['isbn']) else "Not Assigned"
        about_book = row.get('about_book', '')
        about_book_200 = row.get('about_book_200', '')
    else:
        book_title = "Unknown Title"
        isbn = "Not Assigned"
        about_book = ""
        about_book_200 = ""

    # Fetch author details
    author_details_df = fetch_author_details(book_id)

    # Header
    st.markdown(f'<div class="dialog-header">Book ID: {book_id} - {book_title}</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1,4], gap="small") 

    with col2:
        # ISBN Display
        st.markdown('<div class="info-label">ISBN</div>', unsafe_allow_html=True)
        st.markdown(f'<span class="info-value">{isbn}</span>', unsafe_allow_html=True)
    
    with col1:
        # About Book Downloads
        st.markdown('<div class="info-label">Book Descriptions</div>', unsafe_allow_html=True)
    
        has_about_book = bool(about_book and str(about_book).strip())
        has_about_book_200 = bool(about_book_200 and str(about_book_200).strip())

        st.download_button(
            label="⬇️ About Book",
            data=str(about_book) if has_about_book else "",
            file_name=f"about_book_{book_title}_{book_id}.txt",
            mime="text/plain",
            key=f"dl_about_book_{book_title}_{book_id}",
            disabled=not has_about_book,
            help="Download About the Book text" if has_about_book else "No info available"
        )
        
        st.download_button(
            label="⬇️ About Book (150 Words)",
            data=str(about_book_200) if has_about_book_200 else "",
            file_name=f"about_book_200_{book_title}_{book_id}.txt",
            mime="text/plain",
            key=f"dl_about_book_200_{book_title}_{book_id}",
            disabled=not has_about_book_200,
            help="Download About the Book (150 words) text" if has_about_book_200 else "No info available"
        )

    st.write("")

    # Author Details Table
    if not author_details_df.empty:
        # Table Header
        header_cols = st.columns([1, 2, 1, 1.5, 1.5, 1.5, 1.5])
        with header_cols[0]: st.markdown("**ID**")
        with header_cols[1]: st.markdown("**Name**")
        with header_cols[2]: st.markdown("**Pos**")
        with header_cols[3]: st.markdown("**Photo**")
        with header_cols[4]: st.markdown("**Details**")
        with header_cols[5]: st.markdown("**About**")
        with header_cols[6]: st.markdown("**Photo**")
        st.divider()

        for _, row in author_details_df.iterrows():
            cols = st.columns([1, 2, 1, 1.5, 1.5, 1.5, 1.5])
            with cols[0]: st.write(str(row['Author ID']))
            with cols[1]: st.write(row['Author Name'])
            with cols[2]: st.write(row['Position'])
            
            with cols[3]: 
                if row["Photo Received"]:
                    st.markdown('<span class="pill-yes">Yes</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="pill-no">No</span>', unsafe_allow_html=True)
            
            with cols[4]:
                if row["Details Sent"]:
                    st.markdown('<span class="pill-yes">Yes</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="pill-no">No</span>', unsafe_allow_html=True)
            
            with cols[5]:
                about_author = row.get('About Author')
                has_about = bool(about_author and str(about_author).strip())
                st.download_button(
                    label="⬇️ About",
                    data=str(about_author) if has_about else "",
                    file_name=f"about_{row['Author Name'].replace(' ', '_')}.txt" if has_about else "none.txt",
                    mime="text/plain",
                    key=f"dl_about_{row['Author ID']}",
                    help="Download About The Author" if has_about else "No info available",
                    disabled=not has_about,
                    on_click=lambda: log_activity(
                        conn,
                        st.session_state.user_id,
                        st.session_state.username,
                        st.session_state.session_id,
                        "downloaded author file",
                        f"Book ID: {book_id}, Author ID: {row['Author ID']}, Type: About Author"
                    )
                )

            with cols[6]:
                photo_path = row.get('Author Photo Path')
                has_photo = bool(photo_path and os.path.exists(photo_path))
                photo_data = b""
                if has_photo:
                    try:
                        with open(photo_path, "rb") as file:
                            photo_data = file.read()
                    except Exception:
                        has_photo = False
                
                st.download_button(
                    label="⬇️ Photo",
                    data=photo_data,
                    file_name=os.path.basename(photo_path) if has_photo else "none.jpg",
                    mime="image/jpeg",
                    key=f"dl_photo_{row['Author ID']}",
                    help="Download Author Photo" if has_photo else "No photo available",
                    disabled=not has_photo,
                    on_click=lambda: log_activity(
                        conn,
                        st.session_state.user_id,
                        st.session_state.username,
                        st.session_state.session_id,
                        "downloaded author file",
                        f"Book ID: {book_id}, Author ID: {row['Author ID']}, Type: Author Photo"
                    )
                )
            st.divider()
    else:
        st.warning("No author details available.")

def render_month_selector(books_df):
    unique_months = sorted(books_df['Date'].apply(lambda x: x.strftime('%B %Y')).unique(), 
                          key=lambda x: datetime.strptime(x, '%B %Y'), reverse=False)
    default_month = unique_months[-1]  # Most recent month
    selected_month = st.pills("Select Month", unique_months, default=default_month, 
                             key=f"month_selector_{st.session_state.get('section', 'writing')}", 
                             label_visibility='collapsed')
    return selected_month

@st.dialog("Correction Audit", width="large")
def show_correction_audit_dialog(book_id, conn):
    # Fetch book title
    query = f"SELECT title FROM books WHERE book_id = :book_id"
    book_details = conn.query(query, params={"book_id": book_id}, show_spinner=False)
    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        st.markdown(f'<div class="dialog-header">Book ID: {book_id} - {book_title}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f"### Correction Audit for Book ID: {book_id}")

    # 1. Fetch all data
    reqs = conn.query("""
        SELECT ac.*, COALESCE(a.name, 'Internal Team') as author_name 
        FROM author_corrections ac 
        LEFT JOIN authors a ON ac.author_id = a.author_id 
        WHERE ac.book_id = :bid ORDER BY ac.created_at DESC
    """, params={"bid": book_id}, show_spinner=False)
    
    tasks = conn.query("""
        SELECT * FROM corrections WHERE book_id = :bid ORDER BY correction_start DESC
    """, params={"bid": book_id}, show_spinner=False)

    # 2. Identify unique rounds across both tables
    req_rounds = set(reqs['round_number'].unique()) if not reqs.empty else set()
    task_rounds = set(tasks['round_number'].unique()) if not tasks.empty else set()
    all_rounds = sorted(list(req_rounds | task_rounds), reverse=True)

    if not all_rounds:
        st.info("No correction history found for this book.")
        return

    # 3. Iterate through rounds
    for r_num in all_rounds:
        # Determine a summary for the expander label
        r_tasks = tasks[tasks['round_number'] == r_num]
        status_summary = "✅ Completed" if not r_tasks.empty and all(pd.notnull(r_tasks['correction_end'])) else "🚀 In Progress"
        if r_tasks.empty: status_summary = "⏳ Pending Action"
        
        with st.expander(f"🔄 **Round {r_num}** — {status_summary}", expanded=(r_num == all_rounds[0])):
            col_req, col_task = st.columns([1, 1], gap="medium")
            
            with col_req:
                st.markdown("##### 📝 Request Source")
                r_reqs = reqs[reqs['round_number'] == r_num]
                if r_reqs.empty:
                    st.info("No request logged for this round.")
                for _, r in r_reqs.iterrows():
                    is_internal = pd.isnull(r['author_id'])
                    # Visual styling based on source
                    if is_internal:
                        badge_html = '<span style="background-color:#F3E5F5; color:#8E24AA; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:bold; border:1px solid #8E24AA44;">🏢 INTERNAL TEAM</span>'
                        border_color = "#8E24AA"
                    else:
                        badge_html = '<span style="background-color:#E3F2FD; color:#1976D2; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:bold; border:1px solid #1976D244;">👤 AUTHOR REQUEST</span>'
                        border_color = "#1976D2"

                    with st.container(border=True):
                        st.markdown(badge_html, unsafe_allow_html=True)
                        st.caption(f"📅 {r['created_at'].strftime('%d %b %Y, %I:%M %p')}")
                        st.markdown(f"**From:** {r['author_name']}")
                        
                        # Use a colored box for the text to make it stand out
                        st.markdown(f"""
                            <div style="background-color:#f8f9fa; border-left: 4px solid {border_color}; padding: 10px; border-radius: 4px; margin: 10px 0;">
                                {r['correction_text'] or "<i>File only submission</i>"}
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if r['correction_file']:
                            # Using a button or link-like display for files
                            st.markdown(f"📎 **File:** `{os.path.basename(r['correction_file'])}`")

            with col_task:
                st.markdown("##### 🛠️ Team Actions")
                if r_tasks.empty:
                    st.info("No team actions logged yet.")
                
                for _, t in r_tasks.sort_values('correction_start').iterrows():
                    with st.container(border=True):
                        # Action Header with Status Pill
                        status_pill = '<span class="pill status-completed">Done</span>' if pd.notnull(t['correction_end']) else '<span class="pill status-running">Running</span>'
                        
                        internal_badge = ""
                        if t.get('is_internal') == 1:
                            internal_badge = '<span style="background-color:#F3E5F5; color:#8E24AA; padding:1px 6px; border-radius:8px; font-size:10px; font-weight:bold; margin-left:5px;">INTERNAL</span>'
                        
                        st.markdown(f"**{t['section'].capitalize()}** {status_pill}{internal_badge}", unsafe_allow_html=True)
                        
                        t_col1, t_col2 = st.columns(2)
                        with t_col1:
                            st.caption(f"👤 {t['worker']}")
                        with t_col2:
                            st.caption(f"⏱️ Started: {t['correction_start'].strftime('%d %b %Y, %I:%M %p')}")
                            if pd.notnull(t['correction_end']):
                                st.caption(f"🏁 Ended: {t['correction_end'].strftime('%d %b %Y, %I:%M %p')}")
                            if t['notes']:
                                st.markdown(f"<small><b>Note:</b> {t['notes']}</small>", unsafe_allow_html=True)

def render_correction_hub(conn):
    st.subheader("🛠️ Correction Hub")
    st.caption("Overview of all books with current or past correction activity.")

    # 2. Fetch Detailed List
    query = """
        SELECT 
            b.book_id AS `Book ID`,
            b.title AS `Title`,
            b.date AS `Enroll Date`,
            b.correction_status AS `Current Lifecycle`,
            (SELECT COALESCE(MAX(round_number), 0) FROM author_corrections ac WHERE ac.book_id = b.book_id) AS `Total Rounds`,
            (SELECT section FROM corrections c WHERE c.book_id = b.book_id AND c.correction_end IS NULL LIMIT 1) AS `Active Section`,
            (SELECT is_internal FROM corrections c WHERE c.book_id = b.book_id ORDER BY correction_start DESC LIMIT 1) AS `Is Internal`,
            (SELECT MAX(created_at) FROM author_corrections ac WHERE ac.book_id = b.book_id) AS `Last Request`,
            (SELECT GREATEST(COALESCE(MAX(correction_start), '1970-01-01'), COALESCE(MAX(correction_end), '1970-01-01')) FROM corrections c WHERE c.book_id = b.book_id) AS `Last Action`
        FROM books b
        WHERE b.book_id IN (SELECT book_id FROM author_corrections)
           OR b.book_id IN (SELECT book_id FROM corrections)
        ORDER BY GREATEST(COALESCE(`Last Request`, '1970-01-01'), COALESCE(`Last Action`, '1970-01-01')) DESC
    """
    df = conn.query(query, show_spinner=False)

    if df.empty:
        st.info("No correction history found in the system yet.")
        return

    # Search and Filter
    f_col1, f_col2 = st.columns([2, 1])
    with f_col1:
        search = st.text_input("Search by Title or ID", placeholder="Search by Title or ID", key="hub_search", label_visibility='collapsed')
    with f_col2:
        filter_status = st.selectbox("Filter Status", ["All", "Running", "Pending Start", "Completed Cycle"], label_visibility='collapsed')

    filtered_df = df.copy()
    if search:
        filtered_df = filtered_df[
            filtered_df['Title'].str.contains(search, case=False, na=False) |
            filtered_df['Book ID'].astype(str).str.contains(search, case=False, na=False)
        ]
    
    if filter_status == "Running":
        filtered_df = filtered_df[filtered_df['Active Section'].notnull()]
    elif filter_status == "Pending Start":
        filtered_df = filtered_df[(filtered_df['Active Section'].isnull()) & (filtered_df['Current Lifecycle'] != 'None') & (filtered_df['Current Lifecycle'].notnull())]
    elif filter_status == "Completed Cycle":
        filtered_df = filtered_df[(filtered_df['Current Lifecycle'] == 'None') | (filtered_df['Current Lifecycle'].isnull())]

    # Pagination
    items_per_page = 50
    total_pages = max(1, (len(filtered_df) + items_per_page - 1) // items_per_page)

    # Initialize session state
    if 'hub_page' not in st.session_state:
        st.session_state.hub_page = 0

    # Reset page if it exceeds total pages
    if st.session_state.hub_page >= total_pages:
        st.session_state.hub_page = total_pages - 1
    elif total_pages == 0:
        st.session_state.hub_page = 0

    # Slice dataframe
    start_idx = st.session_state.hub_page * items_per_page
    end_idx = start_idx + items_per_page
    paged_df = filtered_df.iloc[start_idx:end_idx]

    # Display Table
    cont = st.container(border=True)
    with cont:
        # Title with Badge
        st.markdown(f"<h5><span class='status-badge-orange'>Correction Audit List <span class='badge-count'>{len(filtered_df)}</span></span></h5>", 
                    unsafe_allow_html=True)
        
        st.markdown('<div class="header-row">', unsafe_allow_html=True)

        # Table Headers
        column_sizes = [0.8, 3, 1.2, 1.2, 1.5, 1]
        h_cols = st.columns(column_sizes)
        headers = ["Book ID", "Book Title", "Latest Round", "Lifecycle", "Current Status", "Action"]
        for i, h in enumerate(headers):
            h_cols[i].markdown(f'<div class="header">{h}</div>', unsafe_allow_html=True)

        st.write("")
        st.markdown('</div><div class="header-line"></div>', unsafe_allow_html=True)

        for _, row in paged_df.iterrows():
            with st.container():
                r_cols = st.columns(column_sizes, vertical_alignment="center")
                
                with r_cols[0]: st.write(int(row['Book ID']))
                with r_cols[1]: st.markdown(f"**{row['Title']}**")
                with r_cols[2]: 
                    round_text = f"<span class='pill worker-by-1'>Round {row['Total Rounds']}</span>"
                    if row.get('Is Internal') == 1:
                        round_text += ' <span class="pill status-on-hold" style="background-color:#F3E5F5; color:#8E24AA; font-weight:bold; font-size:10px;">INTERNAL</span>'
                    st.markdown(round_text, unsafe_allow_html=True)
                
                with r_cols[3]:
                    lc = row['Current Lifecycle']
                    if lc == 'None' or pd.isna(lc):
                        st.markdown("<span class='pill status-completed'>Closed</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span class='pill status-pending'>{lc}</span>", unsafe_allow_html=True)

                with r_cols[4]:
                    if pd.notnull(row['Active Section']):
                        st.markdown(f"<span class='pill status-running'>Running in {row['Active Section'].capitalize()}</span>", unsafe_allow_html=True)
                    elif lc != 'None' and pd.notnull(lc):
                        st.markdown("<span class='pill status-badge-yellow'>Waiting for Start</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span class='pill status-badge-green'>All Processed</span>", unsafe_allow_html=True)

                with r_cols[5]:
                    if st.button("View Details", key=f"hub_view_{row['Book ID']}", use_container_width=True, type="secondary"):
                        show_correction_audit_dialog(row['Book ID'], conn)

    # Pagination controls
    if total_pages > 1:
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns([1, 2, 1, 2], vertical_alignment="center")
        
        with col1:
            if st.session_state.hub_page > 0:
                if st.button("Previous", key="hub_prev_button"):
                    st.session_state.hub_page -= 1
                    st.rerun()
        
        with col2:
            st.write(f"Page {st.session_state.hub_page + 1} of {total_pages}", unsafe_allow_html=True)
        
        with col3:
            if st.session_state.hub_page < total_pages - 1:
                if st.button("Next", key="hub_next_button"):
                    st.session_state.hub_page += 1
                    st.rerun()
        
        with col4:
            page_options = list(range(1, total_pages + 1))
            selected_page = st.selectbox(
                "Go to page",
                options=page_options,
                index=st.session_state.hub_page,
                key="hub_page_selector",
                label_visibility="collapsed"
            )
            if selected_page != st.session_state.hub_page + 1:
                st.session_state.hub_page = selected_page - 1
                st.rerun()

def render_worker_completion_graph(books_df, selected_month, section, holds_df=None):
    """Render a graph and table showing completed books for a given section and month, with hold time excluded from time taken and hold time in the last column."""
    
    
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

        # Create table for book details
        st.write(f"##### {section.capitalize()} Completed in {selected_month} by {selected_worker}")
        display_columns = ['Book ID', 'Title', f'{section.capitalize()} By', 'Time Taken', 'Start Date', 'Start Time', 'End Date', 'End Time', 'Hold Time'] if 'Title' in books_df.columns else ['Book ID', f'{section.capitalize()} By', 'Time Taken', 'Start Date', 'Start Time', 'End Date', 'End Time', 'Hold Time']

        # Calculate time taken (excluding hold periods)
        completed_books = completed_books.copy()  # Avoid modifying original dataframe
        completed_books['Time Taken'] = completed_books.apply(
            lambda row: calculate_working_duration(
                row[start_col],
                row[end_col],
                get_hold_periods(holds_df, row['Book ID'], section, row[end_col])
            ),
            axis=1
        )
        completed_books['Time Taken'] = completed_books['Time Taken'].apply(
            lambda x: f"{x[0]}d {x[1]}h"
        )

        def calculate_total_hold_time(row, holds_df, end_col, section):
            """
            Calculate total hold time for a book in calendar days and hours.
            Returns (total_days, remaining_hours) where 1 day = 24 hours.
            """
            if holds_df is None or holds_df.empty:
                return (0, 0)
            
            # Filter hold periods for this book and section
            book_holds = holds_df[(holds_df['book_id'] == row['Book ID']) & (holds_df['section'] == section)]
            if book_holds.empty:
                return (0, 0)
            
            total_minutes = 0
            hold_periods = [
                (h['hold_start'], h['resume_time'] if pd.notnull(h['resume_time']) else row[end_col])
                for _, h in book_holds.iterrows()
            ]
            
            for hold_start, hold_end in hold_periods:
                if pd.isna(hold_start) or pd.isna(hold_end) or hold_start >= hold_end:
                    continue
                # Calculate duration in calendar days (total time, not working hours)
                duration = (hold_end - hold_start).total_seconds() / 60
                total_minutes += duration
            
            # Convert total minutes to days and hours (1 day = 24 hours)
            total_hours = total_minutes / 60.0
            total_days = int(total_hours // 24)
            remaining_hours = int(round(total_hours % 24))
            return (total_days, remaining_hours)

        completed_books['Hold Time'] = completed_books.apply(
            lambda row: calculate_total_hold_time(row, holds_df, end_col, section),
            axis=1
        )
        completed_books['Hold Time'] = completed_books['Hold Time'].apply(
            lambda x: f"{x[0]}d {x[1]}h" if x != (0, 0) else "0d 0h"
        )

        # Split Start and End into Date and Time with AM/PM format
        completed_books['Start Date'] = completed_books[start_col].dt.strftime('%Y-%m-%d')
        completed_books['Start Time'] = completed_books[start_col].dt.strftime('%I:%M %p')
        completed_books['End Date'] = completed_books[end_col].dt.strftime('%Y-%m-%d')
        completed_books['End Time'] = completed_books[end_col].dt.strftime('%I:%M %p')
        
        st.dataframe(
            completed_books[display_columns].rename(columns={f'{section.capitalize()} By': 'Team Member'}),
            hide_index=True,
            width="stretch"
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

    # # Note for Employees
    st.caption("""
    📝 **Note on Active Time Calculation**
    
    To help you understand how your performance metrics are recorded, here is a brief explanation of how "Active Time" is calculated:
    
    *   **Official Working Hours:** The system only accounts for work performed between **09:30 AM and 06:00 PM**.
    *   **Automatic Exclusions:** **Sundays** and any period where a task is marked as **'On Hold'** are automatically excluded from the total duration.
    *   **Working Day Unit:** In the report above, 1 "Day" is equal to **8.5 hours** of actual work time.
    *   **Calculation Example:** If you begin a task on Monday at 05:00 PM and finish it on Tuesday at 10:00 AM, it is recorded as **1 hour 30 minutes** (1 hour from Monday + 30 minutes from Tuesday).
    """)

def render_metrics(books_df, selected_month, section, user_role, holds_df=None):
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
    col1, col2, col3, col4 = st.columns([8, 1, 1, 1], vertical_alignment="bottom")
    with col1:
        st.subheader(f"Metrics of {selected_month}")
        st.caption(f"Welcome {st.session_state.username}!")
    with col2:
        if st.button(":material/refresh: Refresh", key=f"refresh_{section}", type="tertiary"):
            st.cache_data.clear()
    with col3:
        if role_user == "user" and user_app == "operations":
            click_id = str(uuid.uuid4())
            query_params = {
                "click_id": click_id,
                "session_id": st.session_state.session_id
            }
            tasks_url = get_page_url('tasks', token) + f"&{urlencode(query_params, quote_via=quote)}"
            st.link_button(
                ":material/checklist: Tasks",
                url=tasks_url,
                type="tertiary"
            )
    with col4:
        if role_user == "user" and user_app == "operations":
            click_id = str(uuid.uuid4())
            query_params = {
                "click_id": click_id,
                "session_id": st.session_state.session_id
            }
            tasks_url = get_page_url('/', token) + f"&{urlencode(query_params, quote_via=quote)}"
            st.link_button(
                ":material/chat: Message",
                url=tasks_url,
                type="tertiary",
                disabled=False,
                help="Connect with Team"
            )

    # Metrics rendering
    if section == "writing":
        # Previous month total books
        prev_month_dt = selected_month_dt - timedelta(days=31)
        prev_month_start = prev_month_dt.replace(day=1).date()
        prev_month_end = (prev_month_dt.replace(day=1) + timedelta(days=31)).replace(day=1).date() - timedelta(days=1)
        prev_total_books = len(books_df[(books_df['Date'] >= prev_month_start) & (books_df['Date'] <= prev_month_end)])

        # Worker-specific metrics
        target_period = pd.Timestamp(selected_month_dt).to_period('M')
        prev_period = pd.Timestamp(prev_month_dt).to_period('M')

        # Filter completed books for current month
        completed_current = books_df[
            books_df['Writing By'].notnull() &
            books_df['Writing End'].notnull() &
            (books_df['Writing End'] != '0000-00-00 00:00:00') &
            (books_df['Writing End'].dt.to_period('M') == target_period)
        ]
        current_worker_counts = completed_current.groupby('Writing By').size().reset_index(name='Book Count')

        # Filter completed books for previous month
        completed_prev = books_df[
            books_df['Writing By'].notnull() &
            books_df['Writing End'].notnull() &
            (books_df['Writing End'] != '0000-00-00 00:00:00') &
            (books_df['Writing End'].dt.to_period('M') == prev_period)
        ]
        prev_worker_counts = completed_prev.groupby('Writing By').size().reset_index(name='Prev Book Count')

        # Merge counts, fill missing values with 0
        worker_counts = current_worker_counts.merge(prev_worker_counts, on='Writing By', how='outer').fillna(0)
        worker_counts['Book Count'] = worker_counts['Book Count'].astype(int)
        worker_counts['Prev Book Count'] = worker_counts['Prev Book Count'].astype(int)
        worker_num = len(worker_counts['Writing By']) + 1 
        
        with st.container(border=True):
            # Create list of all metrics
            metrics = [
                {"label": f"Books in {selected_month}", "value": total_books, "delta": f"{prev_total_books} Last Month"},
            ]
            for _, row in worker_counts.iterrows():
                metrics.append({
                    "label": row['Writing By'],
                    "value": row['Book Count'],
                    "delta": f"{row['Prev Book Count']} Last Month"
                })

            # Render metrics in a grid
            cols = st.columns(worker_num)
            for idx, metric in enumerate(metrics):
                col_idx = idx % worker_num
                if col_idx == 0 and idx > 0:
                    cols = st.columns(worker_num)  # Start a new row
                with cols[col_idx]:
                    # Extract numeric delta value for comparison (remove " (Prev Month)" and convert to int)
                    try:
                        delta_value = int(metric["delta"].split(" ")[0])
                        delta_color = "inverse" if delta_value <= 3 else "normal"  # Red for <= 3, Green for > 3
                    except ValueError:
                        delta_color = "normal"  # Default to normal if delta isn't numeric
                    st.metric(
                        label=metric["label"],
                        value=metric["value"],
                        delta=metric["delta"],
                        delta_color=delta_color
                    )
    else:
        # Original layout for non-writing sections
        col1, col2, col3 = st.columns(3, border=True)
        with col1:
            st.metric(f"Books in {selected_month}", total_books)
        with col2:
            st.metric(f"{section.capitalize()} Done in {selected_month}", completed_books)
        with col3:
            st.metric(f"Pending in {selected_month}", pending_books)

    # Render worker completion graph in an expander using full books_df
    with st.expander(f"Show Completion Graph and Table for {section.capitalize()}, {selected_month}"):
        render_worker_completion_graph(books_df, selected_month, section, holds_df=holds_df)
    
    return filtered_books_metrics

@st.dialog("Rate User", width='medium')
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


@st.dialog("Correction Details", width='medium')
def correction_dialog(book_id, conn, section):
    # IST timezone
    IST = timezone(timedelta(hours=5, minutes=30))
    
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

    # Fetch ongoing correction
    query = """
        SELECT correction_id, correction_start, worker, notes, is_internal
        FROM corrections
        WHERE book_id = :book_id AND section = :section AND correction_end IS NULL
        ORDER BY correction_start DESC
        LIMIT 1
    """
    ongoing_correction = conn.query(query, params={"book_id": book_id, "section": section}, show_spinner=False)
    is_ongoing = not ongoing_correction.empty
    
    if is_ongoing:
        correction_id = ongoing_correction.iloc[0]["correction_id"]
        current_start = ongoing_correction.iloc[0]["correction_start"]
        current_worker = ongoing_correction.iloc[0]["worker"]
        is_internal_task = bool(ongoing_correction.iloc[0]["is_internal"])
    else:
        current_start = None
        current_worker = None
        is_internal_task = False

    # Fetch default worker if not ongoing
    if not is_ongoing:
        query = f"SELECT {config['by']} AS worker FROM books WHERE book_id = :book_id"
        book_data = conn.query(query, params={"book_id": book_id}, show_spinner=False)
        default_worker = book_data.iloc[0]["worker"] if not book_data.empty and book_data.iloc[0]["worker"] else "Select Team Member"
    else:
        default_worker = current_worker

    # Fetch hold and resume status from holds table
    hold_query = """
        SELECT hold_start, resume_time, reason
        FROM holds 
        WHERE book_id = :book_id AND section = :section
    """
    hold_data = conn.query(hold_query, params={"book_id": book_id, "section": section}, show_spinner=False)
    hold_start = hold_data.iloc[0]['hold_start'] if not hold_data.empty else None
    resume_time = hold_data.iloc[0]['resume_time'] if not hold_data.empty else None
    hold_reason = hold_data.iloc[0]['reason'] if not hold_data.empty and 'reason' in hold_data.columns else "-"
    is_on_hold = hold_start is not None and resume_time is None

    # Fetch section start and end from books
    query = f"SELECT {config['start']}, {config['end']}, {config['by']} AS worker FROM books WHERE book_id = :book_id"
    section_data = conn.query(query, params={"book_id": book_id}, show_spinner=False)
    section_start = section_data.iloc[0][config['start']] if not section_data.empty else None
    section_end = section_data.iloc[0][config['end']] if not section_data.empty else None
    section_worker = section_data.iloc[0]['worker'] if not section_data.empty and section_data.iloc[0]['worker'] else "-"

    # Collect full history events
    events = []
    if section_start:
        events.append({"Time": section_start, "Event": f"{display_name} Started by {section_worker}", "Notes": "-"})
    if hold_start:
        events.append({"Time": hold_start, "Event": "Placed on Hold", "Notes": hold_reason})
    if resume_time:
        events.append({"Time": resume_time, "Event": "Resumed", "Notes": "-"})

    # Fetch all corrections for history
    query = """
        SELECT correction_start AS Start, correction_end AS End, worker, notes, round_number, is_internal
        FROM corrections
        WHERE book_id = :book_id AND section = :section
        ORDER BY correction_start
    """
    corrections = conn.query(query, params={"book_id": book_id, "section": section}, show_spinner=False)
    for idx, row in corrections.iterrows():
        r_num = row['round_number'] if pd.notnull(row['round_number']) else 1
        internal_flag = " (Internal)" if row['is_internal'] else ""
        events.append({
            "Time": row["Start"],
            "Event": f"Correction Started by {row['worker']} (Round {r_num}){internal_flag}",
            "Notes": row['notes'] if pd.notnull(row['notes']) else "-"
        })
        if pd.notnull(row["End"]):
            events.append({"Time": row["End"], "Event": "Correction Ended", "Notes": "-"})

    if section_end:
        events.append({"Time": section_end, "Event": f"{display_name} Ended", "Notes": "-"})

    # Sort events by time
    events.sort(key=lambda x: x["Time"])

    # Display history in a timeline-like format
    with st.expander(f"Show Full {display_name} History"):
        if events:
            for event in events:
                time_str = event["Time"].strftime('%d %B %Y, %I:%M %p') if pd.notnull(event["Time"]) else "-"
                event_str = event["Event"]
                notes = event["Notes"]
                # Use st.info for a clean, boxed appearance
                if notes != "-":
                    st.info(f"**{time_str}**: {event_str}  \n**Reason**: {notes}")
                else:
                    st.info(f"**{time_str}**: {event_str}")
        else:
            st.info("No history available.")

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

    # Fetch unique names
    names = fetch_unique_names(config["by"], conn)
    options = ["Select Team Member"] + names + ["Add New..."]

    # Initialize session state for new worker
    if f"{section}_correction_new_worker_{book_id}" not in st.session_state:
        st.session_state[f"{section}_correction_new_worker_{book_id}"] = ""

    # Show warning if on hold
    if is_on_hold:
        st.warning(f"⚠️ This section is currently on hold. Placed on hold: {hold_start.strftime('%d %B %Y, %I:%M %p IST')}")

    if not is_ongoing:
        # Pending: Start new correction
        form_title = f"Start New {display_name} Correction"
        st.markdown(f"<h4 style='color:#4CAF50;'>{form_title}</h4>", unsafe_allow_html=True)
        
        selected_worker = st.selectbox(
            "Team Member",
            options,
            index=options.index(default_worker) if default_worker in options else 0,
            key=f"{section}_correction_select_{book_id}",
            label_visibility="collapsed",
            help=f"Select an existing {display_name.lower()} worker or add a new one.",
            disabled=is_on_hold
        )
        
        if selected_worker == "Add New..." and not is_on_hold:
            st.session_state[f"{section}_correction_new_worker_{book_id}"] = st.text_input(
                "New Team Member",
                value=st.session_state[f"{section}_correction_new_worker_{book_id}"],
                key=f"{section}_correction_new_input_{book_id}",
                placeholder=f"Enter new {display_name.lower()} team member name...",
                label_visibility="collapsed"
            )
            if st.session_state[f"{section}_correction_new_worker_{book_id}"].strip():
                worker = st.session_state[f"{section}_correction_new_worker_{book_id}"].strip()
        elif selected_worker != "Select Team Member" and not is_on_hold:
            worker = selected_worker
            st.session_state[f"{section}_correction_new_worker_{book_id}"] = ""
        else:
            worker = None

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if is_on_hold:
                st.button("▶️ Start Correction Now", type="primary", disabled=True, width='stretch')
                st.caption("Resume the section first.")
            elif worker:
                if st.button("▶️ Start Correction Now", type="primary", width='stretch'):
                    with st.spinner(f"Starting {display_name} correction..."):
                        sleep(1)
                        now = datetime.now(IST)
                        
                        # Fetch current correction round
                        round_res = conn.query("SELECT COALESCE(MAX(round_number), 1) as correction_round FROM author_corrections WHERE book_id = :book_id", params={"book_id": book_id}, show_spinner=False)
                        current_round = int(round_res.iloc[0]['correction_round']) if not round_res.empty and pd.notnull(round_res.iloc[0]['correction_round']) else 1

                        updates = {
                            "book_id": book_id,
                            "section": section,
                            "correction_start": now,
                            "worker": worker,
                            "round_number": current_round,
                            "is_internal": 0
                        }
                        insert_fields = ", ".join(updates.keys())
                        insert_placeholders = ", ".join([f":{key}" for key in updates.keys()])
                        with conn.session as s:
                            query = f"""
                                INSERT INTO corrections ({insert_fields})
                                VALUES ({insert_placeholders})
                            """
                            s.execute(text(query), updates)
                            s.commit()
                        details = (
                            f"Book ID: {book_id}, Start: {now}, "
                            f"Worker: {worker or 'None'}"
                        )
                        try:
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                f"started {section} correction",
                                details
                            )
                        except Exception as e:
                            st.error(f"Error logging {display_name.lower()} correction details: {str(e)}")
                        st.success(f"✔️ Started {display_name} correction")
                        st.toast(f"✔️ Started {display_name} correction", icon="✔️", duration="long")
                        st.session_state.pop(f"{section}_correction_new_worker_{book_id}", None)
                        sleep(1)
                        st.rerun()
            else:
                st.button("▶️ Start Correction Now", type="primary", disabled=True, width='stretch')

    else:
        # Ongoing correction
        form_title = f"Ongoing {display_name} Correction"
        if is_internal_task:
            form_title = f"Ongoing {display_name} INTERNAL Correction"
            
        st.markdown(f"<h4 style='color:#4CAF50;'>{form_title}</h4>", unsafe_allow_html=True)
        
        col_start, col_assigned = st.columns(2)
        with col_start:
            st.markdown("**Started At**")
            st.info(current_start.strftime('%d %B %Y, %I:%M %p IST') if current_start else 'None')
        with col_assigned:
            st.markdown("**Assigned To**")
            st.info(current_worker or 'None')

        col_end, col_cancel = st.columns(2)
        with col_end:
            if st.button(f"⏹️ End {display_name} Correction Now", type="primary", width='stretch'):
                with st.spinner(f"Ending {display_name} correction..."):
                    sleep(1)
                    now = datetime.now(IST)
                    with conn.session as s:
                        # 1. End the specific correction task
                        query = f"""
                            UPDATE corrections
                            SET correction_end = :correction_end
                            WHERE correction_id = :correction_id
                        """
                        params = {
                            "correction_end": now,
                            "correction_id": correction_id
                        }
                        s.execute(text(query), params)
                        
                        # 2. Advance Lifecycle State
                        next_status = None
                        if not is_internal_task:
                            if section == 'writing':
                                next_status = 'Proofreading'
                            elif section == 'proofreading':
                                next_status = 'Formatting'
                            elif section == 'formatting':
                                next_status = 'None' # Cycle Closed
                            elif section == 'cover':
                                next_status = 'None' # Cycle Closed
                            
                            if next_status:
                                s.execute(
                                    text("UPDATE books SET correction_status = :status WHERE book_id = :book_id"),
                                    {"status": next_status, "book_id": book_id}
                                )
                        else:
                            # Internal Task: End the cycle immediately for this book
                            next_status = 'None'
                            s.execute(
                                text("UPDATE books SET correction_status = 'None' WHERE book_id = :book_id"),
                                {"book_id": book_id}
                            )

                        s.commit()

                    details = (
                        f"Book ID: {book_id}, End: {now}, Internal: {is_internal_task}"
                    )
                    if next_status:
                         details += f", Advanced to {next_status}"

                    try:
                        log_activity(
                            conn,
                            st.session_state.user_id,
                            st.session_state.username,
                            st.session_state.session_id,
                            f"ended {section} correction",
                            details
                        )
                    except Exception as e:
                        st.error(f"Error logging {display_name.lower()} correction details: {str(e)}")
                    st.success(f"✔️ Ended {display_name} correction")
                    if not is_internal_task:
                        if next_status == 'None':
                             st.success("✅ Correction Cycle Complete!")
                        elif next_status:
                             st.info(f"➡️ Moved to {next_status}")
                    else:
                        st.success("✅ Internal Correction Task Complete!")

                    st.toast(f"Ended {display_name} correction", icon="✔️", duration="long")
                    sleep(1)
                    st.rerun()
        with col_cancel:
            if st.button("Cancel", type="secondary", width='stretch'):
                st.rerun()

@st.dialog("Internal Correction", width='medium')
def internal_correction_dialog(book_id, conn, section):
    # IST timezone
    IST = timezone(timedelta(hours=5, minutes=30))
    
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
    book_details = fetch_book_details(book_id, conn)
    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
    else:
        book_title = "Unknown Title"
        st.markdown(f"### {display_name} Internal Correction for Book ID: {book_id}")

    # Fetch default worker from books table
    query = f"SELECT {config['by']} AS worker FROM books WHERE book_id = :book_id"
    book_data = conn.query(query, params={"book_id": book_id}, show_spinner=False)
    default_worker = book_data.iloc[0]["worker"] if not book_data.empty and book_data.iloc[0]["worker"] else "Select Team Member"

    # Fetch hold status
    hold_query = """
        SELECT hold_start, resume_time, reason
        FROM holds 
        WHERE book_id = :book_id AND section = :section
    """
    hold_data = conn.query(hold_query, params={"book_id": book_id, "section": section}, show_spinner=False)
    hold_start = hold_data.iloc[0]['hold_start'] if not hold_data.empty else None
    resume_time = hold_data.iloc[0]['resume_time'] if not hold_data.empty else None
    hold_reason = hold_data.iloc[0]['reason'] if not hold_data.empty and 'reason' in hold_data.columns else "-"

    # Fetch section start and end from books
    query = f"SELECT {config['start']}, {config['end']}, {config['by']} AS worker FROM books WHERE book_id = :book_id"
    section_data = conn.query(query, params={"book_id": book_id}, show_spinner=False)
    section_start = section_data.iloc[0][config['start']] if not section_data.empty else None
    section_end = section_data.iloc[0][config['end']] if not section_data.empty else None
    section_worker = section_data.iloc[0]['worker'] if not section_data.empty and section_data.iloc[0]['worker'] else "-"

    # Check if digital book has been sent to ANY author
    with conn.session as s:
        digital_sent_res = s.execute(
            text("SELECT COUNT(*) FROM book_authors WHERE book_id = :book_id AND digital_book_sent = 1"),
            {"book_id": book_id}
        ).scalar()
    
    digital_book_sent = digital_sent_res > 0

    # Collect and display history
    events = []
    if section_start:
        events.append({"Time": section_start, "Event": f"{display_name} Started by {section_worker}", "Notes": "-"})
    if hold_start:
        events.append({"Time": hold_start, "Event": "Placed on Hold", "Notes": hold_reason})
    if resume_time:
        events.append({"Time": resume_time, "Event": "Resumed", "Notes": "-"})

    query = """
        SELECT correction_start AS Start, correction_end AS End, worker, notes, round_number, is_internal
        FROM corrections
        WHERE book_id = :book_id AND section = :section
        ORDER BY correction_start
    """
    corrections = conn.query(query, params={"book_id": book_id, "section": section}, show_spinner=False)
    for idx, row in corrections.iterrows():
        r_num = row['round_number'] if pd.notnull(row['round_number']) else 1
        internal_flag = " (Internal)" if row['is_internal'] else ""
        events.append({
            "Time": row["Start"],
            "Event": f"Correction Started by {row['worker']} (Round {r_num}){internal_flag}",
            "Notes": row['notes'] if pd.notnull(row['notes']) else "-"
        })
        if pd.notnull(row["End"]):
            events.append({"Time": row["End"], "Event": "Correction Ended", "Notes": "-"})

    if section_end:
        events.append({"Time": section_end, "Event": f"{display_name} Ended", "Notes": "-"})

    events.sort(key=lambda x: x["Time"])

    with st.expander(f"Show Full {display_name} History"):
        if events:
            for event in events:
                time_str = event["Time"].strftime('%d %B %Y, %I:%M %p') if pd.notnull(event["Time"]) else "-"
                event_str = event["Event"]
                notes = event["Notes"]
                if notes != "-":
                    st.info(f"**{time_str}**: {event_str}  \n**Reason**: {notes}")
                else:
                    st.info(f"**{time_str}**: {event_str}")
        else:
            st.info("No history available.")

    if digital_book_sent:
        st.warning("⚠️ Internal correction is not allowed because the digital copy of the book has already been sent to one or more authors.")
        if st.button("Close", use_container_width=True):
            st.rerun()
        return
    
    st.warning("⚠️ Do not use this for author-requested changes, those must go through the standard author correction workflow. This is strictly for team-driven quality improvements and does not follow the full correction lifecycle (writing → proofreading → formatting); it updates the current correction only.")
    
    # Fetch unique names for the section
    names = fetch_unique_names(config["by"], conn)
    options = ["Select Team Member"] + names + ["Add New..."]

    selected_worker = st.selectbox(
        "Team Member",
        options,
        index=options.index(default_worker) if default_worker in options else 0,
        key=f"internal_corr_worker_select_{book_id}",
    )
    
    worker = None
    if selected_worker == "Add New...":
        worker = st.text_input("New Team Member Name", key=f"internal_corr_new_worker_{book_id}").strip()
    elif selected_worker != "Select Team Member":
        worker = selected_worker

    notes = st.text_area("Correction Notes", placeholder="Describe the internal correction needed...", key=f"internal_corr_notes_{book_id}")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if worker:
            if st.button("▶️ Start Internal Correction", type="primary", width='stretch'):
                with st.spinner(f"Starting internal {display_name} correction..."):
                    sleep(1)
                    now = datetime.now(IST)
                    
                    with conn.session as s:
                        # 1. Determine Round Number
                        book_info = s.execute(
                            text("SELECT correction_status FROM books WHERE book_id = :book_id"),
                            {"book_id": book_id}
                        ).fetchone()
                        
                        max_round_res = s.execute(
                            text("SELECT COALESCE(MAX(round_number), 0) FROM author_corrections WHERE book_id = :book_id"),
                            {"book_id": book_id}
                        ).scalar()
                        
                        status = book_info.correction_status if book_info else 'None'
                        
                        if status == 'None' or status is None:
                            current_round = max_round_res + 1
                        else:
                            current_round = max_round_res

                        # 2. Insert into author_corrections (Internal Request)
                        s.execute(
                            text("""
                                INSERT INTO author_corrections (book_id, author_id, correction_text, round_number)
                                VALUES (:book_id, NULL, :correction_text, :round_number)
                            """),
                            {
                                "book_id": book_id,
                                "correction_text": f"{notes}" if notes else "No details provided",
                                "round_number": current_round
                            }
                        )

                        # 3. Update Book status if starting new cycle
                        if status == 'None' or status is None:
                            s.execute(
                                text("UPDATE books SET correction_status = :status WHERE book_id = :book_id"),
                                {"status": section.capitalize(), "book_id": book_id}
                            )

                        # 4. Insert into corrections table
                        updates = {
                            "book_id": book_id,
                            "section": section,
                            "correction_start": now,
                            "worker": worker,
                            "notes": notes.strip() if notes.strip() else None,
                            "round_number": current_round,
                            "is_internal": 1
                        }
                        insert_fields = ", ".join(updates.keys())
                        insert_placeholders = ", ".join([f":{key}" for key in updates.keys()])
                        
                        query = f"""
                            INSERT INTO corrections ({insert_fields})
                            VALUES ({insert_placeholders})
                        """
                        s.execute(text(query), updates)
                        s.commit()
                    
                    try:
                        log_activity(
                            conn,
                            st.session_state.user_id,
                            st.session_state.username,
                            st.session_state.session_id,
                            f"started internal {section} correction",
                            f"Book ID: {book_id}, Worker: {worker}, Round: {current_round}"
                        )
                    except Exception:
                        pass
                    st.success(f"✔️ Started Internal {display_name} correction (Round {current_round})")
                    st.toast(f"Internal {display_name} correction started", icon="✔️")
                    sleep(1)
                    st.rerun()
        else:
            st.button("▶️ Start Internal Correction", type="primary", disabled=True, width='stretch')

@st.dialog("Edit Details", width='medium')
def edit_section_dialog(book_id, conn, section):
    # IST timezone
    IST = timezone(timedelta(hours=5, minutes=30))
    
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

    # Fetch book title, book note, and current book_pages
    book_details = fetch_book_details(book_id, conn)
    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        book_note = book_details.iloc[0].get('book_note', None)
        current_book_pages = book_details.iloc[0].get('book_pages', 0)
        st.markdown(f"### {book_id} : {book_title}")
        st.markdown("")
        # Display book note only if it exists
        if book_note:
            st.markdown("**Book Note or Instructions**")
            st.info(book_note)
    else:
        book_title = "Unknown Title"
        book_note = None
        current_book_pages = 0
        st.markdown(f"### {display_name} Details for Book ID: {book_id}")
        st.warning("Book title not found.")

    # Fetch hold and resume status from holds table
    hold_query = """
        SELECT hold_start, resume_time, reason 
        FROM holds 
        WHERE book_id = :book_id AND section = :section
    """
    hold_data = conn.query(hold_query, params={"book_id": book_id, "section": section}, show_spinner=False)
    hold_start = hold_data.iloc[0]['hold_start'] if not hold_data.empty else None
    resume_time = hold_data.iloc[0]['resume_time'] if not hold_data.empty else None
    hold_reason = hold_data.iloc[0].get('reason', None) if not hold_data.empty else None
    is_on_hold = hold_start is not None and resume_time is None

    # Check if book is running (any section has start without end)
    running_query = """
        SELECT 
            CASE 
                WHEN writing_start IS NOT NULL AND writing_end IS NULL THEN 1 
                WHEN proofreading_start IS NOT NULL AND proofreading_end IS NULL THEN 1 
                WHEN formatting_start IS NOT NULL AND formatting_start IS NULL THEN 1 
                WHEN cover_start IS NOT NULL AND cover_end IS NULL THEN 1 
                ELSE 0 
            END AS is_running
        FROM books 
        WHERE book_id = :book_id
    """
    running_data = conn.query(running_query, params={"book_id": book_id}, show_spinner=False)
    is_running = running_data.iloc[0]['is_running'] if not running_data.empty else False

    # Book-level hold info (warning and hold start if on hold)
    if is_on_hold:
        st.warning(f"⚠️ This book is currently on hold for {display_name}. Placed on hold: {hold_start.strftime('%d %B %Y, %I:%M %p IST')}")
        if hold_reason:
            st.markdown("**Reason for Hold**")
            st.info(hold_reason)

    # Fetch current section data
    if section == "cover":
        query = """
            SELECT 
                cover_start AS 'Cover Start', 
                cover_end AS 'Cover End', 
                cover_by AS 'Cover By'
            FROM books 
            WHERE book_id = :book_id
        """
    else:
        query = f"""
            SELECT {config['start']}, {config['end']}, {config['by']}, book_pages 
            FROM books 
            WHERE book_id = :book_id
        """
    book_data = conn.query(query, params={"book_id": book_id}, show_spinner=False)
    current_data = book_data.iloc[0].to_dict() if not book_data.empty else {}

    # Get current start, end, worker from data
    current_start_key = "Cover Start" if section == "cover" else config['start']
    current_end_key = "Cover End" if section == "cover" else config['end']
    current_start = current_data.get(current_start_key)
    current_end = current_data.get(current_end_key)
    current_worker = current_data.get(config['by'], "")

    # Determine section status
    pending = current_start is None
    running = current_start is not None and current_end is None
    completed = current_end is not None

    # Fetch unique names for the section
    names = fetch_unique_names(config["by"], conn)
    options = ["Select Team Member"] + names + ["Add New..."]

    # Initialize session state for worker and book_pages (only for pending and completed if needed)
    keys = [f"{section}_new_worker"]
    if section in ["writing", "proofreading", "formatting"]:
        keys.append("book_pages")
    defaults = {
        f"{section}_new_worker": "",
        "book_pages": max(1, current_data.get("book_pages", current_book_pages)) if section in ["writing", "proofreading", "formatting"] else None
    }
    
    for key in keys:
        if f"{key}_{book_id}" not in st.session_state:
            st.session_state[f"{key}_{book_id}"] = defaults[key]

    # Initialize session state for showing hold form
    if f"show_hold_form_{book_id}_{section}" not in st.session_state:
        st.session_state[f"show_hold_form_{book_id}_{section}"] = False

    # Initialize session state for showing end writing form
    if f"show_end_writing_form_{book_id}" not in st.session_state:
        st.session_state[f"show_end_writing_form_{book_id}"] = False

    if pending:
        # For pending: Team member selector, then centered Start button
        selected_worker = st.selectbox(
            f"{display_name} Team Member",
            options,
            index=options.index(current_worker) if current_worker in options else 0,
            key=f"{section}_select_{book_id}",
            help=f"Select an existing {display_name.lower()} worker or add a new one."
        )
        
        # Handle worker selection
        if selected_worker == "Add New...":
            new_worker = st.text_input(
                "New Team Member Name",
                value=st.session_state[f"{section}_new_worker_{book_id}"],
                key=f"{section}_new_input_{book_id}",
                placeholder=f"Enter new {display_name.lower()} team member name..."
            )
            if new_worker.strip():
                selected_worker = new_worker.strip()
                st.session_state[f"{section}_new_worker_{book_id}"] = new_worker.strip()
        worker = selected_worker if selected_worker != "Select Team Member" and selected_worker != "Add New..." else None
        if not worker:
            st.warning("😊 Please select a team member to proceed.")

        # Centered Start button (disable if on hold)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if is_on_hold:
                st.button(f"▶️ Start {display_name} Now", type="primary", disabled=True, width='stretch')
                st.caption("Resume the book first.")
            elif worker:
                if st.button(f"▶️ Start {display_name} Now", type="primary", width='stretch'):
                    with st.spinner(f"Starting {display_name}..."):
                        sleep(1)
                        try:
                            now = datetime.now(IST)
                            updates = {config['start']: now, config['end']: None, config['by']: worker}
                            # Update database
                            with conn.session as s:
                                set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
                                query = f"UPDATE books SET {set_clause} WHERE book_id = :id"
                                params = updates.copy()
                                params["id"] = int(book_id)
                                s.execute(text(query), params)
                                s.commit()
                            # Log the start action
                            details = f"Book ID: {book_id}, Start Time: {now}, By: {worker}"
                            try:
                                log_activity(
                                    conn,
                                    st.session_state.user_id,
                                    st.session_state.username,
                                    st.session_state.session_id,
                                    f"started {section}",
                                    details
                                )
                            except Exception as e:
                                st.warning(f"Warning: {display_name} started but failed to log activity: {str(e)}")
                            st.success(f"✔️ Started {display_name}")
                            st.toast(f"Started {display_name} for Book ID {book_id}", icon="▶️", duration='long')
                            # Clear new worker
                            st.session_state[f"{section}_new_worker_{book_id}"] = ""
                            sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to start {display_name}: {str(e)}")
                            st.toast(f"Error starting {display_name} for Book ID {book_id}", icon="🚫", duration='long')
            else:
                st.button(f"▶️ Start {display_name} Now", type="primary", disabled=True, width='stretch')

    elif running:
        # On hold running layout
        if is_on_hold:
            col_start, col_assigned = st.columns(2)
            with col_start:
                st.markdown("**Started At**")
                st.info(current_start.strftime('%d %B %Y, %I:%M %p IST') if current_start else 'None')
            with col_assigned:
                st.markdown("**Assigned To**")
                st.info(current_worker or 'None')

            # Centered Resume button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("▶️ Resume Book", type="primary", width='stretch'):
                    with st.spinner("Resuming book..."):
                        sleep(1)
                        try:
                            now = datetime.now(IST)
                            updates = {"resume_time": now}
                            with conn.session as s:
                                query = """
                                    UPDATE holds 
                                    SET resume_time = :resume_time 
                                    WHERE book_id = :book_id AND section = :section
                                """
                                params = {"resume_time": now, "book_id": int(book_id), "section": section}
                                s.execute(text(query), params)
                                s.commit()
                            # Log the resume action
                            details = f"Book ID: {book_id}, Resume Time: {now}"
                            try:
                                log_activity(
                                    conn,
                                    st.session_state.user_id,
                                    st.session_state.username,
                                    st.session_state.session_id,
                                    "resumed book",
                                    details
                                )
                            except Exception as e:
                                st.warning(f"Warning: Book resumed but failed to log activity: {str(e)}")
                            st.success("✔️ Book resumed")
                            sleep(2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to resume book: {str(e)}")
                            st.toast(f"Error resuming Book ID {book_id}", icon="🚫", duration='long')
        else:
            # Normal running layout
            col_start, col_assigned = st.columns(2)
            with col_start:
                st.markdown("**Started At**")
                st.info(current_start.strftime('%d %B %Y, %I:%M %p IST') if current_start else 'None')
            with col_assigned:
                st.markdown("**Assigned To**")
                st.info(current_worker or 'None')
            # Show hold and resume info only if the book was ever held
            if hold_start is not None:
                col_hold, col_resume = st.columns(2)
                with col_hold:
                    st.markdown("**Placed on hold**")
                    st.info(hold_start.strftime('%d %B %Y, %I:%M %p IST') if hold_start else 'None')
                with col_resume:
                    st.markdown("**Resumed**")
                    st.info(resume_time.strftime('%d %B %Y, %I:%M %p IST') if resume_time else 'None')

            needs_pages = section in ["writing", "proofreading", "formatting"]
            book_pages = None
            current_pages = current_data.get("book_pages", 0) if needs_pages else None
            if needs_pages:
                st.markdown("**Total Book Pages**")
                book_pages = st.number_input(
                    "Pages",
                    value=st.session_state[f"book_pages_{book_id}"],
                    key=f"book_pages_{book_id}",
                    help="Enter the total number of pages in the book.",
                    label_visibility="collapsed"
                )

            # Initialize session state for hold reason
            if f"hold_reason_{book_id}_{section}" not in st.session_state:
                st.session_state[f"hold_reason_{book_id}_{section}"] = ""

            # End and Hold buttons side by side
            col_end, col_hold = st.columns(2)
            with col_end:
                if section == 'writing':
                    if st.button(f"⏹️ End {display_name} Now", type="primary", width='stretch', key=f"end_writing_btn_{book_id}"):
                        if needs_pages and book_pages < 10:
                            st.error("❌ Enter Book Pages before ending.")
                        else:
                            st.session_state[f"show_end_writing_form_{book_id}"] = True
                else:
                    if st.button(f"⏹️ End {display_name} Now", type="primary", width='stretch', key=f"end_other_btn_{book_id}"):
                        if needs_pages and book_pages < 10:
                            st.error("❌ Enter Book Pages before ending.")
                        else:
                            with st.spinner(f"Ending {display_name}..."):
                                sleep(1)
                                try:
                                    now = datetime.now(IST)
                                    updates = {config['end']: now}
                                    if needs_pages and book_pages is not None and current_pages != book_pages:
                                        updates['book_pages'] = book_pages
                                    # Update database
                                    with conn.session as s:
                                        set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
                                        query = f"UPDATE books SET {set_clause} WHERE book_id = :id"
                                        params = updates.copy()
                                        params["id"] = int(book_id)
                                        s.execute(text(query), params)
                                        s.commit()
                                    # Log the end action
                                    details = f"Book ID: {book_id}, End Time: {now}, By: {current_worker}"
                                    if needs_pages and book_pages is not None:
                                        details += f", Pages: {book_pages}"
                                    try:
                                        log_activity(
                                            conn,
                                            st.session_state.user_id,
                                            st.session_state.username,
                                            st.session_state.session_id,
                                            f"ended {section}",
                                            details
                                        )
                                    except Exception as e:
                                        st.warning(f"Warning: {display_name} started but failed to log activity: {str(e)}")
                                    st.success(f"✔️ Ended {display_name}")
                                    st.toast(f"Ended {display_name} for Book ID {book_id}", icon="⏹️", duration='long')
                                    sleep(2)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Failed to end {display_name}: {str(e)}")
                                    st.toast(f"Error ending {display_name} for Book ID {book_id}", icon="🚫", duration='long')

            with col_hold:
                if st.button("⏸️ Hold Book", type="secondary", width='stretch'):
                    st.session_state[f"show_hold_form_{book_id}_{section}"] = True
            
            if section == 'writing' and st.session_state.get(f"show_end_writing_form_{book_id}", False):
                with st.container(border=True):
                    st.markdown("### Finalize Writing Details")
                    about_book = st.text_area("About the Book", key=f"about_book_{book_id}")
                    about_book_200 = st.text_area("About the Book in 100 Words", key=f"about_book_200_{book_id}")
                    
                    col_conf, col_cancel = st.columns(2)
                    with col_conf:
                        if st.button("✅ Confirm End", type="primary", width="stretch", key=f"confirm_end_writing_{book_id}"):
                            if not about_book.strip() or not about_book_200.strip():
                                st.error("❌ Please fill both 'About the Book' fields.")
                            else:
                                with st.spinner(f"Ending {display_name}..."):
                                    sleep(1)
                                    try:
                                        now = datetime.now(IST)
                                        updates = {config['end']: now}
                                        if needs_pages and book_pages is not None and current_pages != book_pages:
                                            updates['book_pages'] = book_pages
                                        
                                        # Add new fields
                                        updates['about_book'] = about_book.strip()
                                        updates['about_book_200'] = about_book_200.strip()

                                        # Update database
                                        with conn.session as s:
                                            set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
                                            query = f"UPDATE books SET {set_clause} WHERE book_id = :id"
                                            params = updates.copy()
                                            params["id"] = int(book_id)
                                            s.execute(text(query), params)
                                            s.commit()
                                        # Log the end action
                                        details = f"Book ID: {book_id}, End Time: {now}, By: {current_worker}"
                                        if needs_pages and book_pages is not None:
                                            details += f", Pages: {book_pages}"
                                        try:
                                            log_activity(
                                                conn,
                                                st.session_state.user_id,
                                                st.session_state.username,
                                                st.session_state.session_id,
                                                f"ended {section}",
                                                details
                                            )
                                        except Exception as e:
                                            st.warning(f"Warning: {display_name} ended but failed to log activity: {str(e)}")
                                        st.success(f"✔️ Ended {display_name}")
                                        st.toast(f"Ended {display_name} for Book ID {book_id}", icon="⏹️", duration='long')
                                        st.session_state[f"show_end_writing_form_{book_id}"] = False # Reset
                                        sleep(2)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Failed to end {display_name}: {str(e)}")
                                        st.toast(f"Error ending {display_name} for Book ID {book_id}", icon="🚫", duration='long')
                    with col_cancel:
                        if st.button("Cancel", type="secondary", width="stretch", key=f"cancel_end_writing_{book_id}"):
                            st.session_state[f"show_end_writing_form_{book_id}"] = False
                            st.rerun()
            
            # Render hold reason form full-width below buttons
            if st.session_state[f"show_hold_form_{book_id}_{section}"]:
                with st.form(key=f"hold_form_{book_id}_{section}"):
                    st.markdown("**Reason for Hold**")
                    hold_reason = st.text_area(
                        "",
                        value=st.session_state[f"hold_reason_{book_id}_{section}"],
                        placeholder="Enter the reason for placing this book on hold...",
                        help="Provide a brief reason for holding the book (e.g., waiting for author feedback, resource constraints).",
                        key=f"hold_reason_input_{book_id}_{section}",
                        label_visibility="collapsed"
                    )
                    submit_hold = st.form_submit_button("Confirm Hold", type="primary", width='stretch')
                    if submit_hold:
                        if hold_reason.strip():
                            with st.spinner("Holding book..."):
                                sleep(1)
                                try:
                                    now = datetime.now(IST)
                                    with conn.session as s:
                                        query = """
                                            INSERT INTO holds (book_id, section, hold_start, reason)
                                            VALUES (:book_id, :section, :hold_start, :reason)
                                            ON DUPLICATE KEY UPDATE hold_start = :hold_start, reason = :reason, resume_time = NULL
                                        """
                                        params = {
                                            "book_id": int(book_id),
                                            "section": section,
                                            "hold_start": now,
                                            "reason": hold_reason.strip()
                                        }
                                        s.execute(text(query), params)
                                        s.commit()
                                    # Log the hold action
                                    details = f"Book ID: {book_id}, Hold Time: {now}, Reason: {hold_reason.strip()}"
                                    try:
                                        log_activity(
                                            conn,
                                            st.session_state.user_id,
                                            st.session_state.username,
                                            st.session_state.session_id,
                                            "held book",
                                            details
                                        )
                                    except Exception as e:
                                        st.warning(f"Warning: Book held but failed to log activity: {str(e)}")
                                    st.success("✔️ Book held")
                                    st.toast(f"Held Book ID {book_id}", icon="⏸️", duration='long')
                                    # Clear hold reason and hide form
                                    st.session_state[f"hold_reason_{book_id}_{section}"] = ""
                                    st.session_state[f"show_hold_form_{book_id}_{section}"] = False
                                    sleep(2)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Failed to hold book: {str(e)}")
                                    st.toast(f"Error holding Book ID {book_id}", icon="🚫", duration='long')
                        else:
                            st.error("❌ Please provide a reason for holding the book.")

    else:  # completed
        # For completed: Show start, end, worker, pages
        st.markdown("**Started At**")
        st.info(current_start.strftime('%d %B %Y, %I:%M %p IST') if current_start else 'None')
        st.markdown("**Ended At**")
        st.info(current_end.strftime('%d %B %Y, %I:%M %p IST') if current_end else 'None')
        st.markdown(f"**Assigned To**")
        st.info(current_worker or 'None')
        if section in ["writing", "proofreading", "formatting"]:
            current_pages = current_data.get("book_pages", 0)
            st.markdown("**Total Book Pages**")
            st.info(current_pages)

def render_correction_table(correction_books, section, conn):
    count = len(correction_books)
    title = "Active Corrections"
    badge_color = "red"  # Using red to highlight corrections

    cont = st.container(border=True)
    with cont:
        # Title with Badge
        st.markdown(f"<h5><span class='status-badge-{badge_color}'>{title} <span class='badge-count'>{count}</span></span></h5>", 
                    unsafe_allow_html=True)
        
        st.markdown('<div class="header-row">', unsafe_allow_html=True)

        # Columns
        column_sizes = [0.8, 4, 1, 0.8, 1, 1, 0.7, 1]
        col_configs = st.columns(column_sizes)
        
        with col_configs[0]: st.markdown('<div class="header">Book ID</div>', unsafe_allow_html=True)
        with col_configs[1]: st.markdown('<div class="header">Title</div>', unsafe_allow_html=True)
        with col_configs[2]: st.markdown('<div class="header">Date</div>', unsafe_allow_html=True)
        with col_configs[3]: st.markdown('<div class="header">Round</div>', unsafe_allow_html=True)
        with col_configs[4]: st.markdown('<div class="header">Status</div>', unsafe_allow_html=True)
        with col_configs[5]: st.markdown('<div class="header">Correction By</div>', unsafe_allow_html=True)
        with col_configs[6]: st.markdown('<div class="header">File</div>', unsafe_allow_html=True)
        with col_configs[7]: st.markdown('<div class="header">Action</div>', unsafe_allow_html=True)

        st.write("")
        
        st.markdown('</div><div class="header-line"></div>', unsafe_allow_html=True)

        current_date = datetime.now().date()
        
        # Create worker map for consistent coloring
        unique_workers = [w for w in correction_books['Correction By'].unique() if pd.notnull(w) and w != '-']
        worker_map = {worker: idx % 10 for idx, worker in enumerate(unique_workers)}

        for _, row in correction_books.iterrows():
            with st.container():
                col_configs = st.columns(column_sizes, vertical_alignment="center")
                
                with col_configs[0]:
                    st.write(int(row['Book ID']))
                
                with col_configs[1]:
                    st.markdown(f"{row['Title']}")
                
                with col_configs[2]:
                    date_val = row['Date']
                    if isinstance(date_val, (pd.Timestamp, datetime)):
                        date_str = date_val.strftime('%d %B %Y')
                    else:
                        date_str = str(date_val)
                    st.write(date_str)
                
                with col_configs[3]:
                    round_text = f'<span class="pill worker-by-1">Cycle {row["Round"]}</span>'
                    if row.get('is_internal') == 1:
                        round_text += ' <span class="pill status-on-hold" style="background-color:#F3E5F5; color:#8E24AA; font-weight:bold;">Internal</span>'
                    st.markdown(round_text, unsafe_allow_html=True)
                
                with col_configs[4]:
                    active_tasks = row['Active Tasks']
                    if active_tasks > 0:
                        # Running
                        start_time = row['Correction Start']
                        if pd.notnull(start_time):
                            if not isinstance(start_time, (pd.Timestamp, datetime)):
                                start_time = pd.to_datetime(start_time)
                            days = (current_date - start_time.date()).days
                            st.markdown(f'<span class="pill status-running">Running <span class="since-enrolled">{days}d</span></span>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<span class="pill status-running">Running</span>', unsafe_allow_html=True)
                    else:
                        # Pending
                        corr_date = row['Correction Date']
                        if pd.notnull(corr_date):
                            if not isinstance(corr_date, (pd.Timestamp, datetime)):
                                corr_date = pd.to_datetime(corr_date)
                            days = (current_date - corr_date.date()).days
                            st.markdown(f'<span class="pill status-pending">Pending <span class="since-enrolled">{days}d</span></span>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<span class="pill status-pending">Pending</span>', unsafe_allow_html=True)
                
                with col_configs[5]:
                    worker = row.get('Correction By')
                    if pd.notnull(worker) and worker != '-':
                        class_name = f"worker-by-{worker_map.get(worker)}"
                        st.markdown(f'<span class="pill {class_name}">{worker}</span>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span class="pill worker-by-not">Not Assigned</span>', unsafe_allow_html=True)
                
                with col_configs[6]:
                    file_path = row.get('Correction File')
                    corr_text = row.get('Correction Text')
                    has_file = pd.notnull(file_path) and file_path and os.path.exists(file_path)
                    has_text = pd.notnull(corr_text) and str(corr_text).strip() != ""

                    if has_file:
                        with open(file_path, "rb") as file:
                            st.download_button(
                                label=":material/download:",
                                data=file,
                                file_name=os.path.basename(file_path),
                                mime="application/octet-stream",
                                key=f"dl_corr_file_{section}_{row['Book ID']}",
                                help="Download Correction File",
                                on_click=lambda: log_activity(
                                    conn,
                                    st.session_state.user_id,
                                    st.session_state.username,
                                    st.session_state.session_id,
                                    "downloaded correction file",
                                    f"Book ID: {row['Book ID']}, Section: {section}, File: {os.path.basename(file_path)}"
                                )
                            )
                    elif has_text:
                        st.download_button(
                            label=":material/download:",
                            data=str(corr_text),
                            file_name=f"correction_{row['Book ID']}.txt",
                            mime="text/plain",
                            key=f"dl_corr_text_{section}_{row['Book ID']}",
                            help="Download Correction Text (.txt)",
                            on_click=lambda: log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "downloaded correction text",
                                f"Book ID: {row['Book ID']}, Section: {section}, Type: Text Download"
                            )
                        )
                    else:
                        st.download_button(
                            label=":material/download:",
                            data="",
                            file_name="none",
                            key=f"dl_corr_file_{section}_{row['Book ID']}_disabled",
                            disabled=True,
                            help="No file or text available"
                        )

                with col_configs[7]:
                    if st.button("Manage", key=f"manage_corr_{section}_{row['Book ID']}"):
                        correction_dialog(row['Book ID'], conn, section)

# --- Timeline Helpers ---
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

def format_duration(days, hours, minutes):
    """Format duration into a human-readable string."""
    if days > 0: return f"{int(days)}d {int(hours)}h {int(minutes)}m"
    elif hours > 0: return f"{int(hours)}h {int(minutes)}m"
    else: return f"{int(minutes)}m"

def format_timestamp(ts):
    if pd.isna(ts): return "N/A"
    return f'<span class="date-part">{ts.strftime("%d/%m/%Y")}</span> | <span class="time-part">{ts.strftime("%I:%M %p")}</span>'

def get_section_emoji(section):
    return {'writing': '✍️', 'proofreading': '🔍', 'formatting': '📄', 'cover': '🎨', 'correction': '✏️', 'hold': '⏸️'}.get(section.lower(), '⚙️')

# --- Main Logic Execution ---
if user_role in ["writer", "proofreader", "formatter", "cover_designer"] or role_user == "admin":
    current_section = next((k for k, v in SECTION_LABELS.items() if v == user_role), "Writing Section")
    # For admin who might have selected Correction Hub or History, we need to handle that or default to a section
    if selected in ["Correction Hub", "History"]:
        pass # Will be handled in the else block
    else:
        st.session_state['section'] = section_labels = {"Writing Section": "writing", "Proofreading Section": "proofreading", "Formatting Section": "formatting", "Cover Design Section": "cover"}[selected]
        curr_s = st.session_state['section']
        books_df = fetch_books(months_back=4, section=curr_s)
        holds_df = fetch_holds(curr_s)
        
        sel_month = render_month_selector(books_df)
        if sel_month:
            render_metrics(books_df, sel_month, curr_s, user_role, holds_df=holds_df)
            
            # Active Corrections
            correction_books = fetch_correction_books(curr_s)
            if not correction_books.empty:
                render_correction_table(correction_books, curr_s, conn)
            
            not_on_hold = (books_df['hold_start'].isnull() | books_df['resume_time'].notnull())
            on_hold = (books_df['hold_start'].notnull() & books_df['resume_time'].isnull())
            
            col_map = {"writing": "Writing", "proofreading": "Proofreading", "formatting": "Formatting", "cover": "Cover"}
            c_start, c_end = f"{col_map[curr_s]} Start", f"{col_map[curr_s]} End"
            
            smart_table_engine(books_df[books_df[c_start].notnull() & books_df[c_end].isnull() & not_on_hold], f"{curr_s.capitalize()} Running", curr_s, user_role, "running", CONFIG[curr_s], holds_df=holds_df)
            smart_table_engine(books_df[on_hold], f"{curr_s.capitalize()} Hold", curr_s, user_role, "on_hold", CONFIG[curr_s], holds_df=holds_df)
            
            # Pending logic
            if curr_s == "writing": p_cond = books_df[c_start].isnull() & not_on_hold
            elif curr_s == "proofreading": p_cond = ((books_df['Writing End'].notnull()) | (books_df['Is Publish Only'] == 1) | (books_df['Is Thesis to Book'] == 1)) & books_df[c_start].isnull() & not_on_hold
            elif curr_s == "formatting": p_cond = books_df['Proofreading End'].notnull() & books_df[c_start].isnull() & not_on_hold
            else: p_cond = books_df[c_start].isnull() & not_on_hold
            
            smart_table_engine(books_df[p_cond], f"{curr_s.capitalize()} Pending", curr_s, user_role, "pending", CONFIG[curr_s], holds_df=holds_df)
            
            if st.button(f"Show {curr_s.capitalize()} Completed Books", key=f"show_{curr_s}_completed_button"):
                st.session_state[f"show_{curr_s}_completed"] = not st.session_state.get(f"show_{curr_s}_completed", False)
            if st.session_state.get(f"show_{curr_s}_completed"):
                smart_table_engine(books_df[books_df[c_end].notnull() & not_on_hold], f"{curr_s.capitalize()} Completed", curr_s, user_role, "completed", CONFIG[curr_s], holds_df=holds_df)

if role_user != "user" or user_app != "operations":
    if selected == "Correction Hub":
        render_correction_hub(conn)
    elif selected == "History":
        with conn.session as s:
            books_df = conn.query("SELECT book_id, title, date FROM books ORDER BY book_id DESC", ttl=3600)
            s.commit()
        book_options = ['Select a book'] + [f"{row['title']} (ID: {row['book_id']})" for _, row in books_df.iterrows()]
        selected_book = st.selectbox("Select Book", options=book_options, label_visibility="collapsed", placeholder="Select a book...")
        if selected_book != 'Select a book':
            book_id = int(selected_book.split('ID: ')[-1].strip(')'))
            book_data = conn.query("SELECT * FROM books WHERE book_id = :book_id", params={"book_id": book_id}, ttl=3600)
            if not book_data.empty:
                book = book_data.iloc[0]
                st.subheader(f'📖 {book["title"]} (ID: {book_id})', anchor=False, divider="orange")
                corrections_df = conn.query("SELECT * FROM corrections WHERE book_id = :book_id ORDER BY correction_start", params={"book_id": book_id}, ttl=3600)
                requests_df = conn.query("SELECT ac.*, a.name AS author_name FROM author_corrections ac LEFT JOIN authors a ON ac.author_id = a.author_id WHERE ac.book_id = :book_id ORDER BY ac.created_at", params={"book_id": book_id}, ttl=3600)
                holds_df = conn.query("SELECT * FROM holds WHERE book_id = :book_id ORDER BY hold_start", params={"book_id": book_id}, ttl=3600)
                all_dates, events, sections = [], [], ['writing', 'proofreading', 'formatting', 'cover']
                for s_name in sections:
                    s_st, s_en, s_by = f"{s_name}_start", f"{s_name}_end", f"{s_name}_by"
                    if pd.notna(book[s_st]):
                        all_dates.append(book[s_st])
                        events.append({'timestamp': book[s_st], 'section': s_name, 'type': 'start', 'details': f"Assigned to {book[s_by] or 'N/A'}"})
                    if pd.notna(book[s_en]):
                        all_dates.append(book[s_en])
                        # Consolidate: use calculate_working_duration + format_duration
                        if pd.notna(book[s_st]):
                            h_periods = get_hold_periods(holds_df, book_id, s_name, book[s_en])
                            duration = format_duration(*calculate_working_duration(book[s_st], book[s_en], h_periods))
                        else:
                            duration = "Not Started"
                        events.append({'timestamp': book[s_en], 'section': s_name, 'type': 'end', 'details': f"{s_name.capitalize()} phase completed", 'duration': duration})
                for _, req in requests_df.iterrows():
                    if pd.notna(req['created_at']):
                        all_dates.append(req['created_at'])
                        author_name = req['author_name'] if pd.notnull(req['author_name']) else "Internal Team"
                        snippet = (req['correction_text'][:100] + '...') if req['correction_text'] and len(req['correction_text']) > 100 else (req['correction_text'] or "File uploaded")
                        events.append({'timestamp': req['created_at'], 'section': 'correction', 'type': 'correction_request', 'details': f"{'Internal' if pd.isnull(req['author_id']) else 'Author'}: {author_name} | Round {req['round_number']} Request: {snippet}"})
                for _, corr in corrections_df.iterrows():
                    if pd.notna(corr['correction_start']):
                        all_dates.append(corr['correction_start'])
                        label = "[INTERNAL] " if corr.get('is_internal') == 1 else ""
                        events.append({'timestamp': corr['correction_start'], 'section': corr['section'], 'type': 'correction_start', 'details': f"{label}Worker: {corr['worker'] or 'N/A'} (Cycle: {corr['round_number']})"})
                    if pd.notna(corr['correction_end']):
                        all_dates.append(corr['correction_end'])
                        events.append({'timestamp': corr['correction_end'], 'section': corr['section'], 'type': 'correction_end', 'details': f"Correction completed", 'duration': calculate_duration(corr['correction_start'], corr['correction_end'])})
                for _, hld in holds_df.iterrows():
                    if pd.notna(hld['hold_start']):
                        all_dates.append(hld['hold_start'])
                        events.append({'timestamp': hld['hold_start'], 'section': hld['section'], 'type': 'hold_start', 'details': f"Reason: {hld['reason']}"})
                    if pd.notna(hld['resume_time']):
                        all_dates.append(hld['resume_time'])
                        events.append({'timestamp': hld['resume_time'], 'section': hld['section'], 'type': 'hold_end', 'details': f"Resumed work on {hld['section']}", 'duration': calculate_duration(hld['hold_start'], hld['resume_time'])})
                events_df = pd.DataFrame(events)
                if not events_df.empty: events_df = events_df.sort_values('timestamp')
                en_date = book['date']
                total_time = calculate_duration(min(all_dates), max(all_dates)) if all_dates else "Not Started"
                
                # Metrics Calculation using refactored engine
                def get_sec_time(s_name):
                    st_key, en_key = f"{s_name}_start", f"{s_name}_end"
                    if pd.notna(book[st_key]) and pd.notna(book[en_key]):
                        h_periods = get_hold_periods(holds_df, book_id, s_name, book[en_key])
                        return format_duration(*calculate_working_duration(book[st_key], book[en_key], h_periods))
                    return "Not Started"

                w_time = get_sec_time('writing')
                p_time = get_sec_time('proofreading')
                f_time = get_sec_time('formatting')
                c_time = get_sec_time('cover')

                cols = st.columns(6)
                for i, (l, v) in enumerate([("Enrollment", en_date), ("Total", total_time), ("Writing", w_time), ("Proofreading", p_time), ("Formatting", f_time), ("Cover", c_time)]):
                    cols[i].markdown(f'<div class="custom-metric"><div class="custom-metric-label">{l}</div><div class="custom-metric-value">{v}</div></div>', unsafe_allow_html=True)
                with st.expander("##### ⏳ View Full Timeline", expanded=True):
                    if not events_df.empty:
                        for _, e in events_df.iterrows():
                            amap = {'start': f"{get_section_emoji(e['section'])} {e['section'].capitalize()} Started", 'end': f"{get_section_emoji(e['section'])} {e['section'].capitalize()} Completed", 'correction_request': "📩 Correction Request Received", 'correction_start': f"{get_section_emoji('correction')} {e['section'].capitalize()} Correction Started", 'correction_end': f"{get_section_emoji('correction')} {e['section'].capitalize()} Correction Ended", 'hold_start': f"{get_section_emoji('hold')} {e['section'].capitalize()} Paused", 'hold_end': f"{get_section_emoji(e['section'])} {e['section'].capitalize()} Resumed"}
                            det = e['details'] + (f"<span class='duration'>(Duration: {e['duration']})</span>" if e.get('duration') else "")
                            st.markdown(f'<div class="tree-item"><div class="timestamp">{format_timestamp(e["timestamp"])}</div><div class="action">{amap[e["type"]]}</div><div class="details">{det}</div></div>', unsafe_allow_html=True)
                    else: st.info("No events found.")
