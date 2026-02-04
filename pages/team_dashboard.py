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
from constants import log_activity, connect_db, get_page_url, initialize_click_and_session_id, get_total_unread_count, connect_ict_db
import uuid
from datetime import datetime, timezone, timedelta, time
from time import sleep
from sqlalchemy.sql import text
from constants import get_page_url


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
user_id = st.session_state.get("user_id", None)
token = st.session_state.token


section_labels = {
    "Writing Section": "writer",
    "Proofreading Section": "proofreader",
    "Formatting Section": "formatter",
    "Cover Design Section": "cover_designer",
    "Correction Hub": "correction_hub",
    "History": "book_timeline"
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
    if selected is None:
        st.error("Please select a section to proceed.")
        st.stop()
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
ict_conn = connect_ict_db()


# Initialize session state
if "logged_click_ids" not in st.session_state:
    st.session_state.logged_click_ids = set()
if "activity_logged" not in st.session_state:
    st.session_state.activity_logged = False

if user_app == 'main' or role_user == 'admin':
    initialize_click_and_session_id()
else:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

session_id = st.session_state.session_id
click_id = st.session_state.get("click_id", None)

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

if user_app == 'main' or role_user == 'admin':

    # Log navigation if click_id is present and not already logged
    if click_id and click_id not in st.session_state.logged_click_ids:
        try:
            log_activity(
                conn,
                st.session_state.user_id,
                st.session_state.username,
                st.session_state.session_id,
                "navigated to page",
                f"Page: Team Dashboard"
            )
            st.session_state.logged_click_ids.add(click_id)
        except Exception as e:
            st.error(f"Error logging navigation: {str(e)}")

total_unread = get_total_unread_count(ict_conn, st.session_state.user_id)

if user_app == 'operations' and total_unread > 0:

    if "unread_toast_shown" not in st.session_state:
        st.toast(f"You have {total_unread} unread messages!", icon="💬", duration="infinite")
        st.session_state.unread_toast_shown = True

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
                "apply_isbn AS 'Apply ISBN'", 
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
        "formatting": "Formatting"
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
            (SELECT correction_start FROM corrections c WHERE c.book_id = b.book_id AND c.correction_end IS NULL AND c.section = '{section}' ORDER BY correction_start DESC LIMIT 1) AS 'Correction Start'
        FROM books b
        WHERE b.correction_status = '{target_status}' AND b.is_cancelled = 0
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

#on_hold_books = fetch_hold_books()


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

# --- Reusable Month Selector ---
def render_month_selector(books_df):
    unique_months = sorted(books_df['Date'].apply(lambda x: x.strftime('%B %Y')).unique(), 
                          key=lambda x: datetime.strptime(x, '%B %Y'), reverse=False)
    default_month = unique_months[-1]  # Most recent month
    selected_month = st.pills("Select Month", unique_months, default=default_month, 
                             key=f"month_selector_{st.session_state.get('section', 'writing')}", 
                             label_visibility='collapsed')
    return selected_month



def calculate_working_duration(start_date, end_date, hold_periods=None):
    """Calculate duration in working hours (09:30–18:00, Mon–Sat) between two timestamps,
       excluding hold periods. Returns (total_days, remaining_hours) where 1 day = 8.5 hours, hours rounded."""
    
    if pd.isna(start_date) or pd.isna(end_date):
        return (0, 0)
    if start_date >= end_date:
        return (0, 0)
    
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
    remaining_hours = int(round(total_hours % work_day_hours))

    return (total_days, remaining_hours)

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
        SELECT ac.*, a.name as author_name 
        FROM author_corrections ac 
        JOIN authors a ON ac.author_id = a.author_id 
        WHERE ac.book_id = :bid ORDER BY ac.created_at DESC
    """, params={"bid": book_id}, show_spinner=False)
    
    tasks = conn.query("""
        SELECT * FROM corrections WHERE book_id = :bid ORDER BY correction_start DESC
    """, params={"bid": book_id}, show_spinner=False)

    # 2. Identify unique rounds across both tables
    all_rounds = sorted(list(set(reqs['round_number'].tolist()) if not reqs.empty else [] 
                           | set(tasks['round_number'].tolist()) if not tasks.empty else []), reverse=True)

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
                st.markdown("##### 📝 Author Request")
                r_reqs = reqs[reqs['round_number'] == r_num]
                if r_reqs.empty:
                    st.info("No request logged for this round.")
                for _, r in r_reqs.iterrows():
                    with st.container(border=True):
                        st.caption(f"📅 {r['created_at'].strftime('%d %b %Y, %I:%M %p')}")
                        st.markdown(f"**From:** {r['author_name']}")
                        st.write(r['correction_text'] or "*File only submission*")
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
                        st.markdown(f"**{t['section'].capitalize()}** {status_pill}", unsafe_allow_html=True)
                        
                        t_col1, t_col2 = st.columns(2)
                        with t_col1:
                            st.caption(f"👤 {t['worker']}")
                        with t_col2:
                            st.caption(f"⏱️ {t['correction_start'].strftime('%d %b %Y, %I:%M %p')}")
                        
                        if pd.notnull(t['correction_end']):
                            st.caption(f"🏁 Ended: {t['correction_end'].strftime('%d %b %Y, %I:%M %p')}")
                        
                        if t['notes']:
                            st.markdown(f"<small><b>Note:</b> {t['notes']}</small>", unsafe_allow_html=True)

def render_correction_hub(conn):
    st.subheader("🛠️ Correction Central Hub")
    st.caption("Overview of all books with current or past correction activity.")

    # 1. Fetch Summary Metrics
    with conn.session as s:
        # Total unique books with corrections
        total_books_res = s.execute(text("""
            SELECT COUNT(DISTINCT book_id) FROM (
                SELECT book_id FROM author_corrections
                UNION
                SELECT book_id FROM corrections
            ) as combined
        """)).scalar()
        
        # Ongoing corrections (Running)
        ongoing_res = s.execute(text("""
            SELECT COUNT(DISTINCT book_id) FROM corrections WHERE correction_end IS NULL
        """)).scalar()
        
        # Pending correction start (Status != 'None' and no active task)
        pending_res = s.execute(text("""
            SELECT COUNT(*) FROM books 
            WHERE correction_status != 'None' AND correction_status IS NOT NULL
            AND book_id NOT IN (SELECT book_id FROM corrections WHERE correction_end IS NULL)
        """)).scalar()

    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric("Total Books with Corrections", total_books_res or 0)
    with m_col2:
        st.metric("Currently Running", ongoing_res or 0, delta_color="inverse")
    with m_col3:
        st.metric("Pending Team Start", pending_res or 0)

    st.write("---")

    # 2. Fetch Detailed List
    query = """
        SELECT 
            b.book_id AS 'Book ID',
            b.title AS 'Title',
            b.date AS 'Enroll Date',
            b.correction_status AS 'Current Lifecycle',
            (SELECT COALESCE(MAX(round_number), 0) FROM author_corrections ac WHERE ac.book_id = b.book_id) AS 'Total Rounds',
            (SELECT section FROM corrections c WHERE c.book_id = b.book_id AND c.correction_end IS NULL LIMIT 1) AS 'Active Section',
            (SELECT MAX(created_at) FROM author_corrections ac WHERE ac.book_id = b.book_id) AS 'Last Request',
            (SELECT MAX(correction_start) FROM corrections c WHERE c.book_id = b.book_id) AS 'Last Action'
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
        search = st.text_input("Search by Title or ID", placeholder="Type here...", key="hub_search", label_visibility='collapsed')
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

        for _, row in filtered_df.iterrows():
            with st.container():
                r_cols = st.columns(column_sizes, vertical_alignment="center")
                
                with r_cols[0]: st.write(int(row['Book ID']))
                with r_cols[1]: st.markdown(f"**{row['Title']}**")
                with r_cols[2]: st.markdown(f"<span class='pill worker-by-1'>Round {row['Total Rounds']}</span>", unsafe_allow_html=True)
                
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
                [(h['hold_start'], h['resume_time'] or row[end_col]) for _, h in holds_df[(holds_df['book_id'] == row['Book ID']) & (holds_df['section'] == section)].iterrows()] if holds_df is not None and not holds_df[(holds_df['book_id'] == row['Book ID']) & (holds_df['section'] == section)].empty else []
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


from urllib.parse import urlencode, quote

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

    # Render worker completion graph for non-Cover sections in an expander using full books_df
    if section != "cover":
        with st.expander(f"Show Completion Graph and Table for {section.capitalize()}, {selected_month}"):
            render_worker_completion_graph(books_df, selected_month, section, holds_df=holds_df)
    
    return filtered_books_metrics

# Helper function to fetch unique names (assumed to exist or can be added)
def fetch_unique_names(column_name, conn):
    query = f"SELECT DISTINCT {column_name} FROM books WHERE {column_name} IS NOT NULL"
    result = conn.query(query, show_spinner=False)
    return sorted(result[column_name].tolist())

# --- Helper Functions ---
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
    query = f"SELECT title, book_note FROM books WHERE book_id = {book_id}"
    return conn.query(query, show_spinner=False)


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
        SELECT correction_id, correction_start, worker, notes
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
    else:
        current_start = None
        current_worker = None

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
        SELECT correction_start AS Start, correction_end AS End, worker, notes, round_number
        FROM corrections
        WHERE book_id = :book_id AND section = :section
        ORDER BY correction_start
    """
    corrections = conn.query(query, params={"book_id": book_id, "section": section}, show_spinner=False)
    for idx, row in corrections.iterrows():
        r_num = row['round_number'] if pd.notnull(row['round_number']) else 1
        events.append({
            "Time": row["Start"],
            "Event": f"Correction Started by {row['worker']} (Round {r_num})",
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
                            "round_number": current_round
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
                        # Check if this was the last active correction task for this section? 
                        # Actually, the requirement implies the *Lifecycle* moves when the worker says "I'm done".
                        # Assuming one main correction task per section per round usually, or the user explicitly ends the phase.
                        # For simplicity based on prompt: "When they finish... it moves".
                        
                        next_status = None
                        if section == 'writing':
                            next_status = 'Proofreading'
                        elif section == 'proofreading':
                            next_status = 'Formatting'
                        elif section == 'formatting':
                            next_status = 'None' # Cycle Closed
                        
                        if next_status:
                            s.execute(
                                text("UPDATE books SET correction_status = :status WHERE book_id = :book_id"),
                                {"status": next_status, "book_id": book_id}
                            )

                        s.commit()

                    details = (
                        f"Book ID: {book_id}, End: {now}"
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
                    if next_status == 'None':
                         st.success("✅ Correction Cycle Complete!")
                    elif next_status:
                         st.info(f"➡️ Moved to {next_status}")

                    st.toast(f"Ended {display_name} correction", icon="✔️", duration="long")
                    sleep(1)
                    st.rerun()
        with col_cancel:
            if st.button("Cancel", type="secondary", width='stretch'):
                st.rerun()



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
                                        st.warning(f"Warning: {display_name} ended but failed to log activity: {str(e)}")
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
                    about_book_200 = st.text_area("About the Book in 200 Words", key=f"about_book_200_{book_id}")
                    
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
                    st.markdown(f'<span class="pill worker-by-1">Cycle {row["Round"]}</span>', unsafe_allow_html=True)
                
                with col_configs[4]:
                    active_tasks = row['Active Tasks']
                    if active_tasks > 0:
                        # Running
                        start_time = row['Correction Start']
                        if pd.notnull(start_time):
                            if not isinstance(start_time, (pd.Timestamp, datetime)):
                                start_time = pd.to_datetime(start_time)
                            days = (current_date - start_time.date()).days
                            st.markdown(f'<span class="pill status-running">Running ({days}d)</span>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<span class="pill status-running">Running</span>', unsafe_allow_html=True)
                    else:
                        # Pending
                        corr_date = row['Correction Date']
                        if pd.notnull(corr_date):
                            if not isinstance(corr_date, (pd.Timestamp, datetime)):
                                corr_date = pd.to_datetime(corr_date)
                            days = (current_date - corr_date.date()).days
                            st.markdown(f'<span class="pill status-pending">Pending ({days}d)</span>', unsafe_allow_html=True)
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


def render_table(books_df, title, column_sizes, color, section, role, is_running=False):
    if books_df.empty:
        st.warning(f"No {title.lower()} books available from the last 3 months.")
        return
    
    cont = st.container(border=True)
    with cont:
        # Custom CSS for search bar and icons
        st.markdown("""
            <style>
            .note-icon {
                font-size: 1em;
                color: #666;
                margin-left: 0.5rem;
                cursor: default;
            }
            .note-icon:hover {
                color: #333;
            }
            /* New style for history icons */
            .history-icon {
                font-size: 1em;
                color: #8a6d3b;
                margin-left: 0.5rem;
                cursor: help;
            }
            </style>
        """, unsafe_allow_html=True)

        # Search bar for Completed table
        filtered_df = books_df
        if "Completed" in title:
            with st.container():
                search_term = st.text_input(
                    "",
                    placeholder="Search by Book ID or Title",
                    key=f"search_{section}_{title}",
                    label_visibility="collapsed",
                )
                if search_term:
                    filtered_df = books_df[
                        books_df['Book ID'].astype(str).str.contains(search_term, case=False, na=False) |
                        books_df['Title'].str.contains(search_term, case=False, na=False)
                    ]

        # Update count based on filtered DataFrame
        count = len(filtered_df)
        if count == 0 and "Completed" in title and search_term:
            st.warning(f"No books match the search term '{search_term}' in {title.lower()} books.")
            return

        if "Hold" in title:
            badge_color = 'orange'
        elif "Running" in title:
            badge_color = 'yellow'
        elif "Pending" in title:
            badge_color = 'red'
        else:
            badge_color = 'green'
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
            if "Pending" in title and section != "proofreading":
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
        is_active = is_running or ("Hold" in title)
        if is_active:
            if role == "cover_designer":
                if "Hold" in title:
                    columns.extend(["Hold Since", "Cover By", "Action", "Details"])
                else:
                    columns.extend(["Cover By", "Action", "Details"])
            elif role == "proofreader":
                if "Hold" in title:
                    columns.extend(["Hold Since", "Proofreading By", "Action"])
                else:
                    columns.extend(["Proofreading Start", "Proofreading By", "Action"])
            elif role == "writer":
                if "Hold" in title:
                    columns.extend(["Hold Since", "Writing By", "Syllabus", "Action"])
                else:
                    columns.extend(["Writing Start", "Writing By", "Syllabus", "Action"])
            else:
                if "Hold" in title:
                    columns.extend(["Hold Since", f"{section.capitalize()} By", "Action"])
                else:
                    columns.extend([f"{section.capitalize()} Start", f"{section.capitalize()} By", "Action"])
        elif "Pending" in title:
            if role == "cover_designer":
                columns.extend(["Action", "Details"])
            else:
                columns.append("Action")
        elif "Completed" in title:
            columns.extend([f"{section.capitalize()} By", f"{section.capitalize()} End"])
        
        # Validate column sizes
        if len(column_sizes) < len(columns):
            st.error(f"Column size mismatch in {title}: {len(columns)} columns but only {len(column_sizes)} sizes provided.")
            return
        
        col_configs = st.columns(column_sizes[:len(columns)])
        for i, col in enumerate(columns):
            with col_configs[i]:
                st.markdown(f'<span class="header">{col}</span>', unsafe_allow_html=True)
        st.markdown('</div><div class="header-line"></div>', unsafe_allow_html=True)

        current_date = datetime.now().date()
        # Worker maps
        if user_role == role:
            unique_workers = [w for w in filtered_df[f'{section.capitalize()} By'].unique() if pd.notnull(w)]
            worker_map = {worker: idx % 10 for idx, worker in enumerate(unique_workers)}
            if role == "proofreader":
                unique_writing_workers = [w for w in filtered_df['Writing By'].unique() if pd.notnull(w)]
                writing_worker_map = {worker: idx % 10 for idx, worker in enumerate(unique_writing_workers)}
            else:
                writing_worker_map = None
        else:
            worker_map = None
            writing_worker_map = None

        skip_start = "Hold" in title
        for _, row in filtered_df.iterrows():
            col_configs = st.columns(column_sizes[:len(columns)])
            col_idx = 0
            
            with col_configs[col_idx]:
                st.write(row['Book ID'])
            col_idx += 1
            with col_configs[col_idx]:
                title_text = row['Title']

                # Add indicators for hold
                if 'hold_start' in row and pd.notnull(row['hold_start']) and str(row['hold_start']) != '0000-00-00 00:00:00':
                    title_text += ' <span class="history-icon" title="This book has been on hold before">:material/pause:</span>'
                
                if role == "proofreader":
                    if pd.notnull(row.get('is_publish_only')) and row['is_publish_only'] == 1:
                        title_text += ' <span class="pill publish-only-badge">Publish only</span>'
                    elif pd.notnull(row.get('is_thesis_to_book')) and row['is_thesis_to_book'] == 1:
                        title_text += ' <span class="pill thesis-to-book-badge">Thesis to Book</span>'
                if 'book_note' in row and pd.notnull(row['book_note']) and row['book_note'].strip():
                    note_snippet = row['book_note'][:50] + ('...' if len(row['book_note']) > 50 else '')
                    title_text += f' <span class="note-icon" title="{note_snippet}">:material/forum:</span>'
                st.markdown(title_text, unsafe_allow_html=True)
            col_idx += 1
            with col_configs[col_idx]:
                st.write(row['Date'].strftime('%Y-%m-%d') if pd.notnull(row['Date']) else "-")
            col_idx += 1
            with col_configs[col_idx]:
                if "Hold" in title:
                    hold_start = row.get('hold_start', pd.NaT)
                    if pd.notnull(hold_start) and str(hold_start) != '0000-00-00 00:00:00':
                        hold_days = (current_date - hold_start.date()).days
                        status_html = f'<span class="pill on-hold">On Hold {hold_days}d</span>'
                    else:
                        status_html = '<span class="pill pending">Pending</span>'
                else:
                    status, days = get_status(row[f'{section.capitalize()} Start'], row[f'{section.capitalize()} End'], current_date)
                    days_since = get_days_since_enrolled(row['Date'], current_date)
                    status_html = f'<span class="pill status-{"pending" if status == "Pending" else "running" if status == "Running" else "completed"}">{status}'
                    if days is not None and status == "Running":
                        duration = calculate_working_duration(row[f'{section.capitalize()} Start'], datetime.now())
                        if duration:
                            days, hours = duration
                            duration_str = f"{days}d" if hours == 0 else f"{days}d {hours}h"
                            status_html += f' {duration_str}'
                    elif "Completed" in title:
                        start_date = row[f'{section.capitalize()} Start']
                        end_date = row[f'{section.capitalize()} End']
                        if pd.notnull(start_date) and pd.notnull(end_date) and start_date != '0000-00-00 00:00:00' and end_date != '0000-00-00 00:00:00':
                            duration = calculate_working_duration(start_date, end_date)
                            if duration:
                                days, hours = duration
                                duration_str = f"{days}d" if hours == 0 else f"{days}d {hours}h"
                                status_html += f' ({duration_str})'
                            else:
                                status_html += ' (-)'
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
                if "Rating" in columns and not is_running and section != "proofreading":
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
                                    help="Download Syllabus",
                                    on_click=lambda: log_activity(
                                        conn,
                                        st.session_state.user_id,
                                        st.session_state.username,
                                        st.session_state.session_id,
                                        "downloaded syllabus",
                                        f"Book ID: {row['Book ID']}"
                                    )
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
            
            # Active-specific columns (Running or On Hold)
            if is_active and user_role == role:
                if "Hold" in title:
                    # Render Hold Since column for all roles
                    with col_configs[col_idx]:
                        hold_start = row.get('hold_start', pd.NaT)
                        value = hold_start.strftime('%Y-%m-%d') if pd.notnull(hold_start) and str(hold_start) != '0000-00-00 00:00:00' else "-"
                        st.write(value)
                    col_idx += 1
                if role == "cover_designer":
                    with col_configs[col_idx]:
                        worker = row['Cover By']
                        value = worker if pd.notnull(worker) else "Not Assigned"
                        class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
                        st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                    with col_configs[col_idx]:
                        if st.button("Edit", key=f"edit_main_{section}_{row['Book ID']}", help="Edit main process details"):
                            edit_section_dialog(row['Book ID'], conn, section)
                    col_idx += 1
                    with col_configs[col_idx]:
                        if st.button("Details", key=f"details_{section}_{row['Book ID']}"):
                            show_author_details_dialog(row['Book ID'])
                elif role == "proofreader":
                    if not skip_start:
                        with col_configs[col_idx]:
                            start = row['Proofreading Start']
                            if pd.notnull(start) and start != '0000-00-00 00:00:00':
                                st.markdown(f'<span class="pill section-start-date">{start.strftime("%d %B %Y")}</span>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<span class="pill section-start-not">Not started</span>', unsafe_allow_html=True)
                        col_idx += 1
                    with col_configs[col_idx]:
                        worker = row['Proofreading By']
                        value = worker if pd.notnull(worker) else "Not Assigned"
                        class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
                        st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
                    col_idx += 1
                    with col_configs[col_idx]:
                        if st.button("Edit", key=f"edit_main_{section}_{row['Book ID']}", help="Edit main process details"):
                            edit_section_dialog(row['Book ID'], conn, section)
                    col_idx += 1
                elif role == "writer":
                    if not skip_start:
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
                                    disabled=disabled,
                                    on_click=lambda: log_activity(
                                        conn,
                                        st.session_state.user_id,
                                        st.session_state.username,
                                        st.session_state.session_id,
                                        "downloaded syllabus",
                                        f"Book ID: {row['Book ID']}"
                                    )
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
                        if st.button("Edit", key=f"edit_main_{section}_{row['Book ID']}", help="Edit main process details"):
                            edit_section_dialog(row['Book ID'], conn, section)
                    col_idx += 1
                else:
                    if not skip_start:
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
                        if st.button("Edit", key=f"edit_main_{section}_{row['Book ID']}", help="Edit main process details"):
                            edit_section_dialog(row['Book ID'], conn, section)
                    col_idx += 1
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
        holds_df = fetch_holds(section=section)  # Fetch holds_df for the section
        
        not_on_hold_condition = (books_df['hold_start'].isnull() | books_df['resume_time'].notnull())
        
        if section == "writing":
            running_books = books_df[
                (books_df['Writing Start'].notnull() & 
                  books_df['Writing End'].isnull()) &
                not_on_hold_condition
            ]
            on_hold_books = books_df[
                (books_df['hold_start'].notnull() & 
                 books_df['resume_time'].isnull())
            ]
            pending_books = books_df[
                (books_df['Writing Start'].isnull()) &
                (books_df['Is Publish Only'] != 1) &
                (books_df['Is Thesis to Book'] != 1) &
                not_on_hold_condition
            ]
            completed_books = books_df[
                (books_df['Writing End'].notnull()) &
                not_on_hold_condition
            ]
        elif section == "proofreading":
            running_books = books_df[
                (books_df['Proofreading Start'].notnull() & 
                  books_df['Proofreading End'].isnull()) &
                not_on_hold_condition
            ]
            on_hold_books = books_df[
                (books_df['hold_start'].notnull() & 
                 books_df['resume_time'].isnull())
            ]
            pending_books = books_df[
                ((books_df['Writing End'].notnull()) | 
                 (books_df['Is Publish Only'] == 1) | 
                 (books_df['Is Thesis to Book'] == 1)) &
                (books_df['Proofreading Start'].isnull()) &
                not_on_hold_condition
            ]
            completed_books = books_df[
                (books_df['Proofreading End'].notnull()) &
                not_on_hold_condition
            ]
        elif section == "formatting":
            running_books = books_df[
                (books_df['Formatting Start'].notnull() & 
                  books_df['Formatting End'].isnull()) &
                not_on_hold_condition
            ]
            on_hold_books = books_df[
                (books_df['hold_start'].notnull() & 
                 books_df['resume_time'].isnull())
            ]
            pending_books = books_df[
                (books_df['Proofreading End'].notnull()) &
                (books_df['Formatting Start'].isnull()) &
                not_on_hold_condition
            ]
            completed_books = books_df[
                (books_df['Formatting End'].notnull()) &
                not_on_hold_condition
            ]
        elif section == "cover":
            running_books = books_df[
                (books_df['Cover Start'].notnull() & 
                  books_df['Cover End'].isnull()) &
                not_on_hold_condition
            ]
            on_hold_books = books_df[
                (books_df['hold_start'].notnull() & 
                 books_df['resume_time'].isnull())
            ]
            pending_books = books_df[
                (books_df['Cover Start'].isnull()) &
                not_on_hold_condition
            ]
            completed_books = books_df[
                (books_df['Cover End'].notnull()) &
                not_on_hold_condition
            ]

        # Sort tables
        pending_books = pending_books.sort_values(by='Date', ascending=True)
        on_hold_books = on_hold_books.sort_values(by='hold_start', ascending=True)

        # Column sizes
        if section == "writing":
            column_sizes_running = [0.7, 5.2, 1, 1.3, 1.3, 1.2, 1, 1]
            column_sizes_on_hold = [0.7, 5.2, 1, 1, 1, 1.2, 1, 1]
            column_sizes_pending = [0.7, 5.5, 1, 1, 0.8, 1]
            column_sizes_completed = [0.7, 5, 1, 1.3, 1, 1, 1]
        elif section == "proofreading":
            column_sizes_running = [0.7, 5, 1, 1.2, 0.9, 1.6, 1.2, 1]
            column_sizes_on_hold = [0.7, 5, 1, 1.2, 0.9, 1, 1.2, 1]
            column_sizes_pending = [0.8, 5.5, 1, 1.2, 1, 1, 1, 0.8]
            column_sizes_completed = [0.7, 3, 1, 1.3, 1.1, 1, 1, 1, 1]
        elif section == "formatting":
            column_sizes_running = [0.7, 5.5, 1, 1, 1.2, 1.2, 1]
            column_sizes_on_hold = [0.7, 5.5, 1, 1, 1, 1.2, 1]
            column_sizes_pending = [0.7, 5.5, 1, 1, 1.2, 1, 1]
            column_sizes_completed = [0.7, 3, 1, 1.3, 1.2, 1, 1, 1]
        elif section == "cover":
            column_sizes_running = [0.8, 5, 1.2, 1.3, 1, 1, 1, 1, 1, 1]
            column_sizes_on_hold = [0.8, 3, 1.1, 1.2, 1, 1, 1, 1, 1, 1, 1]
            column_sizes_pending = [0.8, 5.5, 1, 1.2, 1, 1, 1, 0.8, 1]
            column_sizes_completed = [0.7, 5.5, 1, 1.5, 1.3, 1.3, 1]

        # Initialize session state for completed table visibility
        if f"show_{section}_completed" not in st.session_state:
            st.session_state[f"show_{section}_completed"] = False

        selected_month = render_month_selector(books_df)
        if selected_month is None:
            st.warning("Please select a month to view metrics.")
            st.stop()
        # Pass holds_df to render_metrics
        render_metrics(books_df, selected_month, section, config["role"], holds_df=holds_df)

        # --- Active Corrections ---
        correction_books = fetch_correction_books(section)
        if not correction_books.empty:
            render_correction_table(correction_books, section, conn)

        render_table(running_books, f"{section.capitalize()} Running", column_sizes_running, config["color"], section, config["role"], is_running=True)
        render_table(on_hold_books, f"{section.capitalize()} Hold", column_sizes_on_hold, config["color"], section, config["role"], is_running=True)
        render_table(pending_books, f"{section.capitalize()} Pending", column_sizes_pending, config["color"], section, config["role"], is_running=False)
        
        # Show completed table toggle
        if st.button(f"Show {section.capitalize()} Completed Books", key=f"show_{section}_completed_button"):
            st.session_state[f"show_{section}_completed"] = not st.session_state[f"show_{section}_completed"]
        
        if st.session_state[f"show_{section}_completed"]:
            render_table(completed_books, f"{section.capitalize()} Completed", column_sizes_completed, config["color"], section, config["role"], is_running=False)


if role_user == "user" and user_app == "operations":
    st.empty()
else:
    if selected == "Correction Hub":
        render_correction_hub(conn)



###################################################################################################################################
##################################--------------- Book Timeline ----------------------------##################################
###################################################################################################################################


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


if role_user == "user" and user_app == "operations":
    st.empty()
else:
    if selected == "History":

        # Fetch all books for selection
        with conn.session as s:
            books_df = conn.query("SELECT book_id, title, date FROM books ORDER BY book_id DESC", ttl=3600)
            s.commit()

        #st.markdown("### ⏳ Book History")

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
                
                # Fetch corrections, requests and holds
                corrections_query = """
                SELECT * FROM corrections WHERE book_id = :book_id ORDER BY correction_start
                """
                requests_query = """
                SELECT ac.*, a.name AS author_name 
                FROM author_corrections ac
                LEFT JOIN authors a ON ac.author_id = a.author_id
                WHERE ac.book_id = :book_id 
                ORDER BY ac.created_at
                """
                holds_query = """
                SELECT * FROM holds WHERE book_id = :book_id ORDER BY hold_start
                """
                corrections_df = conn.query(corrections_query, params={"book_id": book_id}, ttl=3600)
                requests_df = conn.query(requests_query, params={"book_id": book_id}, ttl=3600)
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
                
                # Add correction requests (Author Input)
                for _, req in requests_df.iterrows():
                    if pd.notna(req['created_at']):
                        all_dates.append(req['created_at'])
                        author_name = req['author_name'] if pd.notnull(req['author_name']) else "Unknown Author"
                        text_snippet = (req['correction_text'][:100] + '...') if req['correction_text'] and len(req['correction_text']) > 100 else (req['correction_text'] or "File uploaded")
                        events.append({
                            'timestamp': req['created_at'],
                            'section': 'correction',
                            'type': 'correction_request',
                            'details': f"Author: {author_name} | Round {req['round_number']} Request: {text_snippet}"
                        })

                # Add corrections (Team Action)
                for _, corr in corrections_df.iterrows():
                    if pd.notna(corr['correction_start']):
                        all_dates.append(corr['correction_start'])
                        events.append({
                            'timestamp': corr['correction_start'],
                            'section': corr['section'],
                            'type': 'correction_start',
                            'details': f"Worker: {corr['worker'] if pd.notna(corr['worker']) else 'N/A'} (Cycle: {corr['round_number']})"
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
                enrolment_date = book['date']
                total_time = calculate_duration(min(all_dates), max(all_dates)) if all_dates else "Not Started"
                writing_time = calculate_active_time(book['writing_start'], book['writing_end'], holds_df, 'writing') if pd.notna(book['writing_start']) and pd.notna(book['writing_end']) else "Not Started"
                proofreading_time = calculate_active_time(book['proofreading_start'], book['proofreading_end'], holds_df, 'proofreading') if pd.notna(book['proofreading_start']) and pd.notna(book['proofreading_end']) else "Not Started"
                formatting_time = calculate_active_time(book['formatting_start'], book['formatting_end'], holds_df, 'formatting') if pd.notna(book['formatting_start']) and pd.notna(book['formatting_end']) else "Not Started"
                cover_time = calculate_active_time(book['cover_start'], book['cover_end'], holds_df, 'cover') if pd.notna(book['cover_start']) and pd.notna(book['cover_end']) else "Not Started"
                
                # Display metrics in custom boxes
                cols = st.columns(6)
                with st.container():

                    with cols[0]:
                        st.markdown(f"""
                            <div class="custom-metric">
                                <div class="custom-metric-label">Enrollment Date</div>
                                <div class="custom-metric-value">{enrolment_date}</div>
                            </div>
                        """, unsafe_allow_html=True)
                    with cols[1]:
                        st.markdown(f"""
                            <div class="custom-metric">
                                <div class="custom-metric-label">Total Project Time</div>
                                <div class="custom-metric-value">{total_time}</div>
                            </div>
                        """, unsafe_allow_html=True)
                    with cols[2]:
                        st.markdown(f"""
                            <div class="custom-metric">
                                <div class="custom-metric-label">Writing Time</div>
                                <div class="custom-metric-value">{writing_time}</div>
                            </div>
                        """, unsafe_allow_html=True)
                    with cols[3]:
                        st.markdown(f"""
                            <div class="custom-metric">
                                <div class="custom-metric-label">Proofreading Time</div>
                                <div class="custom-metric-value">{proofreading_time}</div>
                            </div>
                        """, unsafe_allow_html=True)
                    with cols[4]:
                        st.markdown(f"""
                            <div class="custom-metric">
                                <div class="custom-metric-label">Formatting Time</div>
                                <div class="custom-metric-value">{formatting_time}</div>
                            </div>
                        """, unsafe_allow_html=True)
                    with cols[5]:
                        st.markdown(f"""
                            <div class="custom-metric">
                                <div class="custom-metric-label">Cover Time</div>
                                <div class="custom-metric-value">{cover_time}</div>
                            </div>
                        """, unsafe_allow_html=True)

                st.markdown("")    
                
                # Unified Timeline
                with st.expander("##### ⏳ View Full Timeline", expanded=True):
                    with st.container(border=True):
                        if not events_df.empty:
                            for _, event in events_df.iterrows():
                                action_map = {
                                    'start': f"{get_section_emoji(event['section'])} {event['section'].capitalize()} Started",
                                    'end': f"{get_section_emoji(event['section'])} {event['section'].capitalize()} Completed",
                                    'correction_request': f"📩 Correction Request Received",
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

