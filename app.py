import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import date
import time
import re
import os
import datetime
import time
import logging
from logging.handlers import RotatingFileHandler
from auth import validate_token
from constants import ACCESS_TO_BUTTON
import uuid
from urllib.parse import urlencode
from constants import log_activity
from constants import connect_db
from constants import clean_old_logs

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import io
import os


####################################################################################################################
##################################--------------- Logs ----------------------------#################################
####################################################################################################################

start_time = time.time()

# Custom filter to exclude watchdog logs
class NoWatchdogFilter(logging.Filter):
    def filter(self, record):
        return not record.name.startswith('watchdog')

# Configure logging
logger = logging.getLogger('streamlit_app')
logger.setLevel(logging.DEBUG)

# Remove any existing handlers to avoid duplicate logs
logger.handlers = []

# Create a rotating file handler (max 1MB, keep 3 backups)
handler = RotatingFileHandler('streamlit.log', maxBytes=1_000_000, backupCount=3)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
handler.addFilter(NoWatchdogFilter())
logger.addHandler(handler)

########################################################################################################################
##################################--------------- Page Config ----------------------------#############################
#######################################################################################################################


# Set page configuration
st.set_page_config(
    menu_items={
        'About': None,
        'Get Help': None,
        'Report a bug': None
    },
    layout="wide",  # Set layout to wide mode
    initial_sidebar_state="collapsed",
    page_title="AGPH Books",
    page_icon="📚"
)

logo = "logo/logo_black.png"
fevicon = "logo/favicon_black.ico"
small_logo = "logo/favicon_white.ico"

st.logo(logo,
size = "large",
icon_image = small_logo
)


########################################################################################################################
##################################--------------- Token Validation ----------------------------######################
#######################################################################################################################

chek_time = time.time()
validate_token()
total_chek_time = time.time() - chek_time


user_role = st.session_state.get("role", "Unknown")
user_app = st.session_state.get("app", "Unknown")
user_access = st.session_state.get("access", [])
user_id = st.session_state.get("user_id", "Unknown")
user_name = st.session_state.get("username", "Unknown")
token = st.session_state.token
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


# Base URL for your app
BASE_URL  = st.secrets["general"]["BASE_URL"]
UPLOAD_DIR = st.secrets["general"]["UPLOAD_DIR"]
EMAIL_ADDRESS = st.secrets["general"]["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["general"]["EMAIL_PASSWORD"]
SMTP_SERVER = st.secrets["general"]["SMTP_SERVER"]
SMTP_PORT = st.secrets["general"]["SMTP_PORT"]
ADMIN_EMAIL = st.secrets["general"]["ADMIN_EMAIL"]

########################################################################################################################
##################################--------------- Configure Functions ----------------------------######################
#######################################################################################################################

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
        </style>
            
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:FILL@0" rel="stylesheet" />
            """, unsafe_allow_html=True)


# Button configuration
BUTTON_CONFIG = {
    "advance_search": {
        "label": "Advance Search",
        "icon": "🔍",
        "page_path": "adsearch",
        "permission": "advance_search",
        "type": "new_tab",
    },
    "IJISEM": {
        "label": "IJISEM",
        "icon": "🧾",
        "page_path": "ijisem",
        "permission": "ijisem",
        "type": "new_tab",
    },
    "dashboard": {
        "label": "Dashboard",
        "icon": "📊",
        "page_path": "dashboard",
        "permission": "datadashoard",
        "type": "new_tab",
    },
    "team_dashboard": {
        "label": "Operations",
        "icon": "📈",
        "page_path": "team_dashboard",
        "permission": "team_dashboard",
        "type": "new_tab",
    },
    "pending_books": {
        "label": "Pending Work",
        "icon": "⚠️",
        "page_path": "pending_books",
        "permission": "pending_books",
        "type": "new_tab",
    },
    "print_management": {
        "label": "Manage Prints",
        "icon": "🖨️",
        "page_path": "prints",
        "permission": "print_management",
        "type": "new_tab",
    },
    "inventory": {
        "label": "Inventory",
        "icon": "📦",
        "page_path": "inventory",
        "permission": "inventory",
        "type": "new_tab",
    },
    "author_positions": {
        "label": "Open Positions",
        "icon": "📚",
        "page_path": "author_positions",
        "permission": "open_author_positions",
        "type": "new_tab",
    },
    "edit_authors": {
        "label": "Edit Authors",
        "icon": "✏️",
        "permission": "edit_author_detail",
        "type": "call_function",
        "function": lambda conn: edit_author_detail(conn),
    },
    "user_access": {
        "label": "User Access",
        "icon": "👥",
        "permission": None,
        "type": "call_function",
        "function": lambda conn: manage_users(conn),
        "admin_only": True,
    },
    "activity_log": {
        "label": "Activity Log",
        "icon": "🕵🏻",
        "page_path": "activity_log",
        "permission": None,
        "type": "new_tab",
        "admin_only": True,
    }
}

st.cache_data.clear()


########################################################################################################################
##################################--------------- Database Connection ----------------------------######################
#######################################################################################################################

# Connect to MySQL
conn = connect_db()

# Database connection
@st.cache_resource
def connect_ijisem_db():
    try:
        def get_connection():
            return st.connection('ijisem', type='sql')
        connect_ijisem_db_conn = get_connection()
        return connect_ijisem_db_conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

ijisem_conn = connect_ijisem_db()


########################################################################################################################
##################################--------------- Activity Log ----------------------------######################
#######################################################################################################################

if "activity_logged" not in st.session_state:
    log_activity(
                conn,
                st.session_state.user_id,
                st.session_state.username,
                st.session_state.session_id,
                "logged in",
                f"App: {st.session_state.app}"
            )
    st.session_state.activity_logged = True

if "cleanup_done" not in st.session_state:
    st.session_state.cleanup_done = False

# Run log cleanup on app startup (once per session)
if not st.session_state.cleanup_done:
    clean_old_logs(conn, days_to_keep=30)
    st.session_state.cleanup_done = True

########################################################################################################################
##################################--------------- Main App Started ----------------------------######################
#######################################################################################################################


# Fetch books from the database
query = "SELECT book_id, title, date, isbn, apply_isbn, deliver, price, is_single_author, syllabus_path, " \
"is_publish_only, publisher, author_type, writing_start, writing_end, " \
"proofreading_start, proofreading_end, formatting_start, formatting_end, cover_start, cover_end FROM books"
books = conn.query(query,show_spinner = False)

# Apply date range filtering
if user_role == "user" and user_app == "main":
    start_date = st.session_state.get("start_date")
    if start_date:
        try:
            # Convert inputs to pd.Timestamp for consistency
            if isinstance(start_date, str):
                start_date = pd.to_datetime(start_date)
            elif isinstance(start_date, date):
                start_date = pd.Timestamp(start_date)
            # Ensure books['date'] is datetime64[ns]
            books['date'] = pd.to_datetime(books['date'])
            books = books[books['date'] >= start_date]
        except Exception as e:
            st.error(f"Error applying date filter: {e}")
            books = books.iloc[0:0]  # Empty DataFrame on error
    else:
        st.warning("⚠️ Problem in Date. Contact Admin for Valid date.")
        st.stop()
elif user_role != "admin":
    books = books.iloc[0:0]  # No data for invalid roles or user with app!='main'


########################################################################################################################
##################################--------------- Helping Functions ----------------------------######################
#######################################################################################################################

# Function to fetch book details (title, is_single_author, num_copies, print_status)

def fetch_book_details(book_id, conn):
    query = f"""
    SELECT title, date, apply_isbn, isbn, is_single_author, isbn_receive_date , num_copies, syllabus_path, print_status,is_publish_only, publisher
    FROM books
    WHERE book_id = '{book_id}'
    """
    return conn.query(query,show_spinner = False)

# Convert 'date' column to datetime objects if it's not already
if not pd.api.types.is_datetime64_any_dtype(books['date']):
    books['date'] = pd.to_datetime(books['date'])

def get_page_url(page_path, token):
    """Generate a URL with the token as a query parameter."""
    return f"{BASE_URL}/{page_path}?token={token}"

def get_isbn_display(book_id, isbn, apply_isbn):
    if has_open_author_position(conn, book_id):
        return f"<span style='color:#4b5563; background-color:#f3f4f6; font-size:12px; font-weight:501; padding:3px 8px; border-radius:12px; display:inline-flex; align-items:center; box-shadow:0 1px 2px rgba(0,0,0,0.05);'>Not Applicable</span>"
    if pd.notna(isbn):
        return f"<span style='color:#15803d; background-color:#ecfdf5; font-size:12px; font-weight:501; padding:3px 8px; border-radius:12px; display:inline-flex; align-items:center; box-shadow:0 1px 2px rgba(0,0,0,0.05);'>{isbn}</span>"
    elif apply_isbn == 0:
        return f"<span style='color:#dc2626; background-color:#fef2f2; font-size:12px; font-weight:501; padding:3px 8px; border-radius:12px; display:inline-flex; align-items:center; box-shadow:0 1px 2px rgba(0,0,0,0.05);'>Not Applied</span>"
    elif apply_isbn == 1:
        return f"<span style='color:#1e40af; background-color:#eff6ff; font-size:12px; font-weight:501; padding:3px 8px; border-radius:12px; display:inline-flex; align-items:center; box-shadow:0 1px 2px rgba(0,0,0,0.05);'>Not Received</span>"
    return f"<span style='color:#1f2937; background-color:#f3f4f6; font-size:12px; font-weight:501; padding:3px 8px; border-radius:12px; display:inline-flex; align-items:center; box-shadow:0 1px 2px rgba(0,0,0,0.05);'>-</span>"


# Function to check if a button is allowed for the user's role and access
def is_button_allowed(button_name, debug=False):
    user_role = st.session_state.get("role", "Unknown")
    user_access = st.session_state.get("access", [])  # Expecting a list like ['isbn', 'payment', 'authors']
    
    # Special case for admin-only buttons
    if button_name == "manage_users":
        return user_role == "admin"
    
    # Debug output (optional)
    if debug:
        st.write(f"Debug: role={user_role}, access={user_access}, button={button_name}")
    
    # Admins have access to all buttons
    if user_role == "admin":
        return True
    # Invalid or unset role gets no access
    if user_role != "user":
        return False
    
    # For 'user' role, check if the button corresponds to an access value
    allowed_buttons = [ACCESS_TO_BUTTON.get(access) for access in user_access if access in ACCESS_TO_BUTTON]
    if debug:
        st.write(f"Debug: allowed_buttons={allowed_buttons}")
    return button_name in allowed_buttons

def has_open_author_position(conn, book_id):
    query = """
    WITH author_counts AS (
        SELECT 
            b.book_id,
            b.title,
            b.date,
            b.author_type,
            b.publisher,
            COUNT(ba.author_id) as author_count,
            MAX(CASE WHEN ba.author_position = '1st' THEN 'Booked' ELSE NULL END) as position_1,
            MAX(CASE WHEN ba.author_position = '2nd' THEN 'Booked' ELSE NULL END) as position_2,
            MAX(CASE WHEN ba.author_position = '3rd' THEN 'Booked' ELSE NULL END) as position_3,
            MAX(CASE WHEN ba.author_position = '4th' THEN 'Booked' ELSE NULL END) as position_4
        FROM books b
        LEFT JOIN book_authors ba ON b.book_id = ba.book_id
        WHERE b.author_type IN ('Double', 'Triple', 'Multiple')
        GROUP BY b.book_id, b.title, b.date, b.author_type, b.publisher
        HAVING 
            (b.author_type = 'Double' AND COUNT(ba.author_id) < 2) OR
            (b.author_type = 'Triple' AND COUNT(ba.author_id) < 3) OR
            (b.author_type = 'Multiple' AND COUNT(ba.author_id) < 4)
    )
    SELECT 
        book_id,
        title,
        date,
        author_type,
        publisher,
        COALESCE(position_1, 'Vacant') as position_1,
        CASE 
            WHEN author_type IN ('Double', 'Triple', 'Multiple') THEN COALESCE(position_2, 'Vacant')
            ELSE 'N/A'
        END as position_2,
        CASE 
            WHEN author_type IN ('Triple', 'Multiple') THEN COALESCE(position_3, 'Vacant')
            ELSE 'N/A'
        END as position_3,
        CASE 
            WHEN author_type = 'Multiple' THEN COALESCE(position_4, 'Vacant')
            ELSE 'N/A'
        END as position_4
    FROM author_counts;
    """
    df = conn.query(query)
    return book_id in df['book_id'].values


# Function to fetch book_author details for multiple book_ids
def fetch_all_book_authors(book_ids, conn):
    if not book_ids:  # Handle empty book_ids
        return pd.DataFrame()
    query = """
    SELECT ba.id, ba.book_id, ba.author_id, a.name, a.email, a.phone, 
           ba.author_position, ba.welcome_mail_sent, ba.corresponding_agent, 
           ba.publishing_consultant, ba.photo_recive, ba.id_proof_recive, 
           ba.author_details_sent, ba.cover_agreement_sent, ba.agreement_received, 
           ba.digital_book_sent, 
           ba.printing_confirmation, ba.delivery_address, ba.delivery_charge, 
           ba.number_of_books, ba.total_amount, ba.emi1, ba.emi2, ba.emi3,
           ba.emi1_date, ba.emi2_date, ba.emi3_date,
           ba.delivery_date, ba.tracking_id, ba.delivery_vendor,
           ba.emi1_payment_mode, ba.emi2_payment_mode, ba.emi3_payment_mode,
           ba.emi1_transaction_id, ba.emi2_transaction_id, ba.emi3_transaction_id
    FROM book_authors ba
    JOIN authors a ON ba.author_id = a.author_id
    WHERE ba.book_id IN :book_ids
    """
    return conn.query(query, params={'book_ids': tuple(book_ids)}, show_spinner=False)


def fetch_all_printeditions(book_ids, conn):
    if not book_ids:  # Handle empty book_ids
        return pd.DataFrame(columns=['book_id', 'print_id', 'status'])
    
    # SQL query to fetch print editions
    query = """
    SELECT book_id, print_id, status
    FROM printeditions
    WHERE book_id IN :book_ids
    """
    
    try:
        # Execute query using Streamlit's MySQL connection
        printeditions_df = conn.query(query, params={'book_ids': tuple(book_ids)}, show_spinner=False)
        return printeditions_df
    except Exception as e:
        print(f"Error fetching print editions: {e}")
        return pd.DataFrame(columns=['book_id', 'print_id', 'status'])


def get_status_pill(book_id, row, authors_grouped, printeditions_grouped):
    # Base pill style with modern design and vertical stacking
    pill_style = (
        "padding: 6px 12px; "
        "border-radius: 10px; "
        "background: linear-gradient(145deg, #ffffff, #f1f5f9); "
        "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; "
        "display: flex; "
        "flex-direction: column; "
        "align-items: flex-start; "
        "border: 1px solid #e2e8f0; "
        "box-shadow: 0 2px 4px rgba(0,0,0,0.06); "
        "line-height: 1.5; "
        "gap: 4px; "
        "min-width: 120px; "
        "width: 10px; "
        "transition: all 0.2s;"
    )

    # Define status configurations
    operations_sequence = [
        ("writing", "In Writing", "Writing Complete", "#6b7280", "#dbeafe"),  # Blue shades
        ("proofreading", "In Proofreading", "Proofreading Complete", "#6b7280", "#ede9fe"),  # Purple shades
        ("formatting", "In Formatting", "Formatting Complete", "#6b7280", "#fef3c7"),  # Amber shades
        ("cover", "In Cover Design", "Operations Done", "#6b7280", "#ccfbf1")  # Teal shades
    ]

    checklist_sequence = [
        ("welcome_mail_sent", "Welcome Mail", "#dc2626", "#15803d"),  # Red to Green
        ("cover_agreement_sent", "Cover/Agreement", "#dc2626", "#15803d"),
        ("author_details_sent", "Author Details", "#dc2626", "#15803d"),
        ("photo_recive", "Photo", "#dc2626", "#15803d"),
        ("id_proof_recive", "ID Proof", "#dc2626", "#15803d"),
        ("agreement_received", "Agreement", "#dc2626", "#15803d"),
        ("digital_book_sent", "Digital Proof", "#dc2626", "#15803d"),
        ("printing_confirmation", "Print Confirmation", "#dc2626", "#15803d")
    ]

    # Check post-printing statuses
    if row.get('deliver', 0) == 1:
        return (
            f"<div style='{pill_style}'>"
            f"<span style='color: #15803d; font-size: 13.5px; font-weight: 600; display: block;'>Delivered ✓</span>"
            f"</div>"
        )

    # Check print editions
    book_printeditions = printeditions_grouped.get(book_id, pd.DataFrame())
    if not book_printeditions.empty:
        latest_print = book_printeditions.sort_values(by='print_id', ascending=False).iloc[0]
        if latest_print['status'] == "Received":
            return (
                f"<div style='{pill_style}'>"
                f"<span style='color: #15803d; font-size: 13.5px; font-weight: 600; display: block;'>Ready For Dispatch ✓</span>"
                f"</div>"
            )
        elif latest_print['status'] == "In Printing":
            return (
                f"<div style='{pill_style}'>"
                f"<span style='color: #b45309; font-size: 13.5px; font-weight: 600; display: block;'>In Printing</span>"
                f"</div>"
            )

    # Check operations status
    operations_status = "Not Started"
    operations_color = "#6b7280"
    operations_checkmark = ""
    for stage, in_progress, complete, color, _ in operations_sequence:
        start_field = f"{stage}_start"
        end_field = f"{stage}_end"
        if row.get(start_field) is not None and pd.notnull(row.get(start_field)):
            if row.get(end_field) is None or pd.isnull(row.get(end_field)):
                operations_status = in_progress
                operations_color = color
            else:
                operations_status = complete
                operations_color = "#6b7280"
                operations_checkmark = " ✓"
            break

    # Check author checklist
    checklist_status = "No Authors"
    checklist_color = "#6b7280"
    book_authors = authors_grouped.get(book_id, pd.DataFrame())
    if not book_authors.empty:
        earliest_pending_index = len(checklist_sequence)
        earliest_pending_step = None
        for _, author in book_authors.iterrows():
            for idx, (field, label, pending_color, _) in enumerate(checklist_sequence):
                if not author[field]:
                    if idx < earliest_pending_index:
                        earliest_pending_index = idx
                        earliest_pending_step = label
                    break
        if earliest_pending_index < len(checklist_sequence):
            checklist_status = earliest_pending_step
            checklist_color = checklist_sequence[earliest_pending_index][2]
        else:
            checklist_status = "Checklist Complete"
            checklist_color = "#15803d"

    # Check if ready for print
    if (checklist_status == "Checklist Complete" and
            row.get('formatting_end') is not None and pd.notnull(row.get('formatting_end')) and
            row.get('cover_end') is not None and pd.notnull(row.get('cover_end'))):
        return (
            f"<div style='{pill_style}'>"
            f"<span style='color: #15803d; font-size: 13.5px; font-weight: 600; display: block;'>Ready For Print ✓</span>"
            f"</div>"
        )

    # Combine checklist and operations status vertically
    x_mark = "" if checklist_status in ["Checklist Complete", "No Authors"] else " ✗"
    primary_style = f"color: {checklist_color}; font-size: 13.5px; font-weight: 600; display: block;"
    secondary_style = f"color: {operations_color}; font-size: 11px; font-weight: 450; display: block;"
    return (
        f"<div style='{pill_style}'>"
        f"<span style='{primary_style}'>{checklist_status}{x_mark}</span>"
        f"<span style='{secondary_style}'>{operations_status}{operations_checkmark}</span>"
        f"</div>"
    )

def fetch_author_names(book_id, conn):
    """Fetch author names for a paper, formatted with Material Icons."""
    # Validate conn
    if not hasattr(conn, 'session'):
        return "Database error: Invalid connection"
    
    try:
        with conn.session as session:
            query = text("""
                SELECT a.name
                FROM authors a
                JOIN book_authors pa ON a.author_id = pa.author_id
                WHERE pa.book_id = :book_id
                ORDER BY pa.author_position IS NULL, pa.author_position ASC
            """)
            results = session.execute(query, {'book_id': book_id}).fetchall()
            author_names = [result.name for result in results]
            if author_names:
                return ", ".join(
                    f"""<span class="material-symbols-rounded" style="vertical-align: middle; font-size:12px;">person</span> {name}"""
                    for name in author_names
                )
            return "No authors"
    except Exception as e:
        return f"Database error: {str(e)}"
    

def send_email(subject, body, attachment_data, filename):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = ADMIN_EMAIL
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment_data)

        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename={filename}'
        )
        msg.attach(part)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

def get_all_ijisem_data(conn):
    # Fetch papers
    papers_query = "SELECT * FROM papers"
    papers_df = conn.query(papers_query)
    
    # Fetch authors
    authors_query = "SELECT * FROM authors"
    authors_df = conn.query(authors_query)
    
    # Fetch paper_authors
    paper_authors_query = "SELECT * FROM paper_authors"
    paper_authors_df = conn.query(paper_authors_query)
    
    # Merge data
    merged_df = paper_authors_df.merge(papers_df, on='paper_id', how='left')
    merged_df = merged_df.merge(authors_df, on='author_id', how='left')
    
    # Pivot authors to have Author 1 Name))^    author_pivot = merged_df.pivot_table(
    author_pivot = merged_df.pivot_table(
        index=['paper_id', 'paper_title'],
        columns='author_position',
        values=['name', 'email', 'phone', 'affiliation'],
        aggfunc='first'
    ).reset_index()
    
    # Flatten the multi-level column names
    author_pivot.columns = [
        f'{col[0]}_{col[1]}' if col[1] else col[0] 
        for col in author_pivot.columns
    ]
    
    # Rename columns to desired format
    renamed_columns = {'paper_id': 'paper_id', 'paper_title': 'paper_title'}
    for col in author_pivot.columns:
        if col not in ['paper_id', 'paper_title']:
            field, position = col.rsplit('_', 1)
            renamed_columns[col] = f'Author {position} {field.capitalize()}'
    
    author_pivot.rename(columns=renamed_columns, inplace=True)
    
    # Merge back with paper details
    final_df = papers_df.merge(
        author_pivot[['paper_id'] + [col for col in author_pivot.columns if col.startswith('Author')]], 
        on='paper_id', 
        how='left'
    )
    
    return final_df

def get_all_booktracker_data(conn):
    # Fetch books
    books_query = "SELECT * FROM books"
    books_df = conn.query(books_query)
    
    # Fetch authors
    authors_query = "SELECT * FROM authors"
    authors_df = conn.query(authors_query)
    
    # Fetch book_authors
    book_authors_query = "SELECT * FROM book_authors"
    book_authors_df = conn.query(book_authors_query)
    
    # Fetch inventory
    inventory_query = "SELECT * FROM inventory"
    inventory_df = conn.query(inventory_query)
    
    # Merge data
    merged_df = book_authors_df.merge(books_df, on='book_id', how='left')
    merged_df = merged_df.merge(authors_df, on='author_id', how='left')
    merged_df = merged_df.merge(inventory_df, on='book_id', how='left')
    
    # Pivot authors to have Author 1 Name, Author 1 Email, etc.
    author_pivot = merged_df.pivot_table(
        index=['book_id', 'title'],
        columns='author_position',
        values=['name', 'email', 'phone'],
        aggfunc='first'
    ).reset_index()
    
    # Flatten the multi-level column names
    author_pivot.columns = [
        f'{col[0]}_{col[1]}' if col[1] else col[0] 
        for col in author_pivot.columns
    ]
    
    # Rename columns to desired format
    renamed_columns = {'book_id': 'book_id', 'title': 'title'}
    for col in author_pivot.columns:
        if col not in ['book_id', 'title']:
            field, position = col.rsplit('_', 1)
            renamed_columns[col] = f'Author {position} {field.capitalize()}'
    
    author_pivot.rename(columns=renamed_columns, inplace=True)
    
    # Merge back with book details and inventory
    final_df = books_df.merge(
        author_pivot[['book_id'] + [col for col in author_pivot.columns if col.startswith('Author')]], 
        on='book_id',
        how='left'
    ).merge(
        inventory_df,
        on='book_id',
        how='left'
    )
    
    return final_df

def export_data():
    st.header("Export Data")
    
    with st.container(border=True):
        col1, col2 = st.columns([1,1], gap="small")
        with col1:
            st.subheader("Database Selection")
            database = st.radio(
                "Select Database",
                ["MIS", "IJISEM"],
                index=0,
                horizontal=True
            )
        
        with col2:
            st.subheader("Export Options")
            if database == "MIS":
                export_all = st.checkbox("All Data Export", value=True)
                export_authors = st.checkbox("Only Author Data")
                export_books = st.checkbox("Only Book Data")
                export_inventory = st.checkbox("Only Inventory Data")
                
                export_options = []
                if export_all:
                    export_options.append("All Data Export")
                if export_authors:
                    export_options.append("Only Author Data")
                if export_books:
                    export_options.append("Only Book Data")
                if export_inventory:
                    export_options.append("Only Inventory Data")
            else:
                export_all = st.checkbox("All Data Export", value=True)
                export_authors = st.checkbox("Only Author Data")
                export_papers = st.checkbox("Only Papers Data")
                
                export_options = []
                if export_all:
                    export_options.append("All Data Export")
                if export_authors:
                    export_options.append("Only Author Data")
                if export_papers:
                    export_options.append("Only Papers Data")
        
        if st.button("Export"):
            if not export_options:
                st.error("Please select at least one export option")
                return
                
            with st.spinner("Generating export..."):
                dfs = []
                if database == "IJISEM":
                    for option in export_options:
                        if option == "All Data Export":
                            df = get_all_ijisem_data(ijisem_conn)
                            dfs.append(('All_Data', df))
                        elif option == "Only Author Data":
                            df = ijisem_conn.query("SELECT * FROM authors")
                            dfs.append(('Authors', df))
                        else:  # Only Papers Data
                            df = ijisem_conn.query("SELECT * FROM papers")
                            dfs.append(('Papers', df))
                else:  # booktracker
                    for option in export_options:
                        if option == "All Data Export":
                            df = get_all_booktracker_data(conn)
                            dfs.append(('All_Data', df))
                        elif option == "Only Author Data":
                            df = conn.query("SELECT * FROM authors")
                            dfs.append(('Authors', df))
                        elif option == "Only Book Data":
                            df = conn.query("SELECT * FROM books")
                            dfs.append(('Books', df))
                        else:  # Inventory Data Export
                            df = conn.query("SELECT * FROM inventory")
                            dfs.append(('Inventory', df))
                
                # Create Excel file in memory
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    for sheet_name, df in dfs:
                        df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                
                # Get current timestamp for filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{database}_export_{timestamp}.xlsx"
                
                # Send email
                subject = f"{database} Data Export - {', '.join(export_options)}"
                body = f"Please find attached the exported data from {database} database.\nExport types: {', '.join(export_options)}"
                
                if send_email(subject, body, output.getvalue(), filename):
                    st.success(f"Data exported successfully and sent to Admin Email: {ADMIN_EMAIL}. Included: {', '.join(export_options)}")
                    st.balloons()
                else:
                    st.error("Failed to send export email")


###################################################################################################################################
##################################--------------- Manage Users ----------------------------##################################
###################################################################################################################################

@st.dialog("Manage Users", width="large")
def manage_users(conn):
    # Check if user is admin
    if st.session_state.get("role", None) != "admin":
        st.error("❌ Access Denied: Only admins can manage users.")
        return

    # Initialize session state for show_passwords and confirm_delete_user_id
    if "show_passwords" not in st.session_state:
        st.session_state.show_passwords = False
    if "confirm_delete_user_id" not in st.session_state:
        st.session_state.confirm_delete_user_id = None
    # Track previous show_passwords state for logging
    if "show_passwords_prev" not in st.session_state:
        st.session_state.show_passwords_prev = st.session_state.show_passwords

    # Fetch all users from database
    with conn.session as s:
        users = s.execute(
            text("SELECT id, username, email, password, role, app, access, start_date FROM users ORDER BY username")
        ).fetchall()
    
    # Tabs for user management
    tab1, tab2, tab3, tab4 = st.tabs(["View Users", "Edit Users", "Add New User", "Export Data"])

    # Tab 1: View Users
    with tab1:
        if not users:
            st.error("❌ No users found in database.")
        else:
            st.markdown("### Users Overview", unsafe_allow_html=True)
            # Show Password checkbox with logging
            show_passwords = st.checkbox(
                "Show Passwords",
                value=st.session_state.show_passwords,
                key="toggle_passwords",
                help="Check to reveal all passwords in the table"
            )
            # Log checkbox toggle
            if show_passwords != st.session_state.show_passwords_prev:
                log_activity(
                    conn,
                    st.session_state.user_id,
                    st.session_state.username,
                    st.session_state.session_id,
                    "toggled checkbox",
                    f"Show Passwords changed to '{show_passwords}'"
                )
                st.session_state.show_passwords = show_passwords
                st.session_state.show_passwords_prev = show_passwords

            # Prepare data for st.data_editor
            user_data = [
                {
                    "ID": user.id,
                    "Username": user.username,
                    "Email": user.email or "",
                    "Password": user.password if st.session_state.show_passwords else "••••••••",
                    "Real_Password": user.password,  # Hidden column
                    "Role": user.role,
                    "App": user.app or "",
                    "Access": user.access or "",
                    "Start Date": user.start_date
                }
                for user in users
            ]
            df = pd.DataFrame(user_data)

            # Display table
            st.data_editor(
                df,
                use_container_width=True,
                hide_index=True,
                disabled=["ID", "Username", "Email", "Password", "Real_Password", "Role", "App", "Access", "Start Date"],
                column_config={
                    "ID": st.column_config.NumberColumn("ID", help="Unique user ID", disabled=True),
                    "Username": st.column_config.TextColumn("Username", help="User's username"),
                    "Email": st.column_config.TextColumn("Email", help="User's email address"),
                    "Password": st.column_config.TextColumn("Password", help="Password (masked by default)"),
                    "Real_Password": None,  # Hide this column
                    "Role": st.column_config.TextColumn("Role", help="User's role"),
                    "App": st.column_config.TextColumn("App", help="User's app assignment"),
                    "Access": st.column_config.TextColumn("Access", help="User's access permissions"),
                    "Start Date": st.column_config.DateColumn("Start Date", help="Data access start date")
                },
                column_order=["ID", "Username", "Email", "Role", "App", "Access", "Start Date", "Password"],
                num_rows="fixed",
                key="user_table"
            )
    
    # Tab 3: Add New User
    with tab3:
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username", key="new_username", placeholder="Enter username")
                new_email = st.text_input("Email", key="new_email", placeholder="Enter email")
            with col2:
                new_password = st.text_input("Password", key="new_password", type="password", placeholder="Enter password")
                new_role = st.selectbox("Role", options=["admin", "user"], key="new_role")

            col3, col4 = st.columns([1,3])
            if new_role == "admin":
                new_app = "main"
                new_access = None
                new_start_date = None
                with col3:
                    st.text_input("App", value=new_app, disabled=True, key="new_app")
                with col4:
                    st.text_input("Access", value="", disabled=True, key="new_access")
                st.date_input("Data From", value=None, disabled=True, key="new_start_date")
            else:
                with col3:
                    new_app = st.selectbox("App", options=["main", "operations", "ijisem"], key="new_app_select")
                with col4:
                    access_options = (
                        list(ACCESS_TO_BUTTON.keys())
                        if new_app == "main"
                        else ["writer", "proofreader", "formatter", "cover_designer"]
                    )
                    if new_app == "main":
                        new_access = st.multiselect(
                            "Access",
                            options=access_options,
                            default=[],
                            key="new_access_select",
                            help="Select one or more access permissions",
                            disabled=new_app != "main"
                        )
                    elif new_app == "ijisem":
                        new_access = st.selectbox(
                            "Access",
                            options=["Full Access"],
                            key="new_access_select_ijisem",
                            help="IJISEM users have full access by default",
                            disabled=new_app != "ijisem"
                        )
                    else:
                        new_access = st.selectbox(
                            "Access",
                            options=access_options,
                            key="new_access_select_operations",
                            help="Select one access permission",
                            disabled=new_app != "operations"
                        )
                new_start_date = st.date_input(
                    "Data From",
                    value=None,
                    key="new_start_date",
                    help="Select data access start date" if new_app == "main" else None,
                    disabled=new_app != "main"
                )

            if st.button("Add User", key="add_user", type="primary", use_container_width=True):
                if not new_username or not new_password:
                    st.error("❌ Username and password are required.")
                elif new_email and not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
                    st.error("❌ Invalid email format.")
                else:
                    access_value = None if new_role == "admin" else (
                        ",".join(new_access) if new_app == "main" and new_access else
                        new_access if new_app in ("operations", "ijisem") and new_access else None
                    )

                    with st.spinner("Adding user..."):
                        with conn.session as s:
                            s.execute(
                                text("""
                                    INSERT INTO users (username, email, password, role, app, access, start_date)
                                    VALUES (:username, :email, :password, :role, :app, :access, :start_date)
                                """),
                                {
                                    "username": new_username,
                                    "email": new_email if new_email else None,
                                    "password": new_password,
                                    "role": new_role,
                                    "app": new_app,
                                    "access": access_value,
                                    "start_date": new_start_date
                                }
                            )
                            new_user_id = s.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]
                            s.commit()
                        # Log the add user action
                        log_activity(
                            conn,
                            st.session_state.user_id,
                            st.session_state.username,
                            st.session_state.session_id,
                            "added user",
                            f"User ID: {new_user_id}, Username: {new_username}, Role: {new_role}, App: {new_app}"
                        )
                        st.success("User Added Successfully!", icon="✔️")
                        st.rerun()

    # Tab 2: Edit Users
    with tab2:
        if not users:
            st.error("❌ No users found in database.")
        else:
            with st.container(border=True):
                st.markdown("### Select User", unsafe_allow_html=True)
                user_dict = {f"{user.username} (ID: {user.id})": user for user in users}
                selected_user_name = st.selectbox("Select User", options=list(user_dict.keys()), key="user_select")
                selected_user = user_dict[selected_user_name]
                st.markdown(f"**ID:** <span style='color: #2196F3'>{selected_user.id}</span>", unsafe_allow_html=True)

            with st.container(border=True):
                st.markdown(f"### Editing: <span style='color: #4CAF50'>{selected_user.username}</span>", unsafe_allow_html=True)
                
                if selected_user.id == 1:
                    st.warning("⚠️ This is the primary admin (ID: 1). Role cannot be changed, and the user cannot be deleted.")

                col1, col2 = st.columns(2)
                with col1:
                    new_username = st.text_input("Username", value=selected_user.username, key=f"username_{selected_user.id}")
                    new_email = st.text_input("Email", value=selected_user.email or "", key=f"email_{selected_user.id}")
                with col2:
                    new_password = st.text_input("Password", value=selected_user.password or "", key=f"password_{selected_user.id}", type="password")
                    valid_roles = ["admin", "user"]
                    current_role = selected_user.role if selected_user.role in valid_roles else "user"
                    if selected_user.role not in valid_roles:
                        st.warning(f"⚠️ Invalid role '{selected_user.role}' detected. Defaulting to 'user'.")
                    if selected_user.id == 1:
                        st.selectbox("Role", options=["admin"], index=0, disabled=True, key=f"role_{selected_user.id}")
                        new_role = "admin"
                    else:
                        new_role = st.selectbox("Role", options=valid_roles, index=valid_roles.index(current_role), key=f"role_{selected_user.id}")

                col3, col4 = st.columns([1,3])
                if new_role == "admin":
                    new_app = "main"
                    new_access = None
                    new_start_date = None
                    with col3:
                        st.text_input("App", value=new_app, disabled=True, key=f"app_{selected_user.id}")
                    with col4:
                        st.text_input("Access", value="", disabled=True, key=f"access_{selected_user.id}")
                    st.date_input("Data From", value=None, disabled=True, key=f"start_date_{selected_user.id}")
                else:
                    with col3:
                        new_app = st.selectbox("App", options=["main", "operations", "ijisem"], index=["main", "operations", "ijisem"].index(selected_user.app) if selected_user.app in ["main", "operations", "ijisem"] else 0, key=f"app_select_{selected_user.id}")
                    with col4:
                        access_options = list(ACCESS_TO_BUTTON.keys()) if new_app == "main" else ["writer", "proofreader", "formatter", "cover_designer"]
                        if new_app == "main":
                            default_access = [access.strip() for access in selected_user.access.split(",") if access.strip() in access_options] if selected_user.access and isinstance(selected_user.access, str) else []
                            new_access = st.multiselect("Access", options=access_options, default=default_access, key=f"access_select_{selected_user.id}", disabled=new_app != "main")
                        elif new_app == "ijisem":
                            new_access = st.selectbox(
                                "Access",
                                options=["Full Access"],
                                index=0 if selected_user.access == "Full Access" else 0,
                                key=f"access_select_ijisem_{selected_user.id}",
                                help="IJISEM users have full access by default",
                                disabled=new_app != "ijisem"
                            )
                        else:
                            default_access = selected_user.access if selected_user.access in access_options else access_options[0]
                            new_access = st.selectbox("Access", options=access_options, index=access_options.index(default_access), key=f"access_select_operations_{selected_user.id}", disabled=new_app != "operations")
                    new_start_date = st.date_input("Data From", value=selected_user.start_date, key=f"start_date_{selected_user.id}", disabled=new_app != "main")

                btn_col1, btn_col2 = st.columns([3, 1])
                with btn_col1:
                    if st.button("Save Changes", key=f"save_{selected_user.id}", type="primary", use_container_width=True):
                        if new_email and not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
                            st.error("❌ Invalid email format.")
                        else:
                            access_value = None if new_role == "admin" else (
                                ",".join(new_access) if new_app == "main" and new_access else
                                new_access if new_app in ["operations", "ijisem"] and new_access else None
                            )
                            # Track changes for logging
                            changes = []
                            if new_username != selected_user.username:
                                changes.append(f"Updated username from '{selected_user.username}' to '{new_username}'")
                            if new_email != (selected_user.email or ""):
                                changes.append(f"Updated email from '{selected_user.email or ''}' to '{new_email}'")
                            if new_password and new_password != selected_user.password:
                                changes.append("Updated password")
                            if new_role != selected_user.role:
                                changes.append(f"Updated role from '{selected_user.role}' to '{new_role}'")
                            if new_app != (selected_user.app or ""):
                                changes.append(f"Updated app from '{selected_user.app or ''}' to '{new_app}'")
                            if new_access != (selected_user.access or None):
                                changes.append(f"Updated access from '{selected_user.access or ''}' to '{access_value or ''}'")
                            if new_start_date != selected_user.start_date:
                                changes.append(f"Updated start_date from '{selected_user.start_date or ''}' to '{new_start_date or ''}'")

                            with st.spinner("Saving changes..."):
                                with conn.session as s:
                                    s.execute(
                                        text("""
                                            UPDATE users 
                                            SET username = :username, email = :email, password = :password,
                                                role = :role, app = :app, access = :access, start_date = :start_date
                                            WHERE id = :id
                                        """),
                                        {
                                            "username": new_username,
                                            "email": new_email if new_email else None,
                                            "password": new_password if new_password else None,
                                            "role": new_role,
                                            "app": new_app,
                                            "access": access_value,
                                            "start_date": new_start_date,
                                            "id": selected_user.id
                                        }
                                    )
                                    s.commit()
                                # Log changes if any
                                if changes:
                                    details = f"User ID: {selected_user.id}, {', '.join(changes)}"
                                    log_activity(
                                        conn,
                                        st.session_state.user_id,
                                        st.session_state.username,
                                        st.session_state.session_id,
                                        "updated user",
                                        details
                                    )
                                st.success("User Updated Successfully!", icon="✔️")
                                st.rerun()

                with btn_col2:
                    if selected_user.id != 1:
                        if st.button("🗑️", key=f"delete_{selected_user.id}", type="secondary", use_container_width=True):
                            st.session_state.confirm_delete_user_id = selected_user.id

                if st.session_state.confirm_delete_user_id == selected_user.id:
                    st.warning(f"Are you sure you want to delete {selected_user.username} (ID: {selected_user.id})?")
                    confirm_col1, confirm_col2 = st.columns([4, 1])
                    with confirm_col1:
                        if st.button("❌ Cancel", key=f"cancel_delete_{selected_user.id}"):
                            st.session_state.confirm_delete_user_id = None
                    with confirm_col2:
                        if st.button("✔️ Confirm", key=f"confirm_delete_{selected_user.id}"):
                            with st.spinner("Deleting user..."):
                                with conn.session as s:
                                    s.execute(text("DELETE FROM users WHERE id = :id"), {"id": selected_user.id})
                                    s.commit()
                                # Log the delete action
                                log_activity(
                                    conn,
                                    st.session_state.user_id,
                                    st.session_state.username,
                                    st.session_state.session_id,
                                    "deleted user",
                                    f"User ID: {selected_user.id}, Username: {selected_user.username}"
                                )
                                st.success("User Deleted Successfully!", icon="✔️")
                                st.session_state.confirm_delete_user_id = None
                                st.rerun()
    
    # Tab 4: Export Data (no logging assumed)
    with tab4:
        export_data()
        
        
###################################################################################################################################
##################################--------------- Edit Auhtor Details ----------------------------##################################
###################################################################################################################################


# Dialog for managing authors
@st.dialog("Manage Authors", width="large")
def edit_author_detail(conn):
    # Fetch all authors from database
    with conn.session as s:
        authors = s.execute(
            text("SELECT author_id, name, email, phone FROM authors ORDER BY name")
        ).fetchall()
    
    if not authors:
        st.error("❌ No authors found in database.")
        return

    # Convert to dictionary for easier handling
    author_dict = {f"{author.name} (ID: {author.author_id})": author for author in authors}
    author_options = list(author_dict.keys())

    st.markdown("### Author List", unsafe_allow_html=True)
    with st.container(border=True):
        # Author selection
        selected_author_name = st.selectbox(
            "Select Author",
            options=author_options,
            key="author_select",
            help="Select an author to edit or delete"
        )
        
        selected_author = author_dict[selected_author_name]
        # Highlight author ID with green color
        st.markdown(
            f"#### Selected ID: <span style='color: #2196F3; font-weight: bold;'>{selected_author.author_id}</span>",
            unsafe_allow_html=True
        )

    # Highlight author name with blue color
    st.markdown(
        f"### Editing: <span style='color: #4CAF50;'>{selected_author.name}</span>",
        unsafe_allow_html=True
    )
    with st.container(border=True):
        # Edit fields with NULL handling
        new_name = st.text_input(
            "Author Name",
            value=selected_author.name,
            key=f"name_{selected_author.author_id}"
        )
        new_email = st.text_input(
            "Email",
            value=selected_author.email if selected_author.email is not None else "",
            key=f"email_{selected_author.author_id}"
        )
        new_phone = st.text_input(
            "Phone",
            value=selected_author.phone if selected_author.phone is not None else "",
            key=f"phone_{selected_author.author_id}"
        )

        btn_col1, btn_col2 = st.columns([3, 1])

        with btn_col1:
            with st.container():
                if st.button("Save Changes", 
                            key=f"save_{selected_author.author_id}", 
                            type="primary",
                            use_container_width=True):
                    with st.spinner("Saving changes..."):
                        time.sleep(1)
                        # Track changes for logging
                        changes = []
                        if new_name != selected_author.name:
                            changes.append(f"Name changed from '{selected_author.name}' to '{new_name}'")
                        if new_email != (selected_author.email or ''):
                            changes.append(f"Email changed from '{selected_author.email or ''}' to '{new_email}'")
                        if new_phone != (selected_author.phone or ''):
                            changes.append(f"Phone changed from '{selected_author.phone or ''}' to '{new_phone}'")
                        
                        try:
                            with conn.session as s:
                                s.execute(
                                    text("""
                                        UPDATE authors 
                                        SET name = :name, 
                                            email = :email, 
                                            phone = :phone 
                                        WHERE author_id = :author_id
                                    """),
                                    {
                                        "name": new_name,
                                        "email": new_email if new_email else None,
                                        "phone": new_phone if new_phone else None,
                                        "author_id": selected_author.author_id
                                    }
                                )
                                s.commit()
                            # Log changes if any
                            if changes:
                                log_activity(
                                    conn,
                                    st.session_state.user_id,
                                    st.session_state.username,
                                    st.session_state.session_id,
                                    "updated author",
                                    f"Author ID: {selected_author.author_id}, {', '.join(changes)}"
                                )
                            st.success("Author Updated Successfully!", icon="✔️")
                        except Exception as e:
                            st.error(f"Failed to save changes: {str(e)}")

        with btn_col2:
            delete_key = f"delete_{selected_author.author_id}"
            if "confirm_delete" not in st.session_state:
                st.session_state["confirm_delete"] = False

            if st.button("🗑️", 
                        key=delete_key, 
                        type="secondary",
                        help=f"Delete {selected_author.name}",
                        use_container_width=True):
                st.session_state["confirm_delete"] = True

        # Move confirmation dialog outside the column layout
        if st.session_state["confirm_delete"]:
            st.warning(f"Are you sure you want to delete {selected_author.name} (ID: {selected_author.author_id})?")

            # Full-width confirmation buttons
            confirm_col1, confirm_col2 = st.columns([4, 1])
            with confirm_col1:
                if st.button("❌ Cancel", key=f"cancel_{delete_key}"):
                    st.session_state["confirm_delete"] = False
            with confirm_col2:
                if st.button("✔️ Confirm", key=f"confirm_{delete_key}"):
                    with st.spinner("Deleting author..."):
                        time.sleep(1)
                        try:
                            with conn.session as s:
                                s.execute(
                                    text("DELETE FROM authors WHERE author_id = :author_id"),
                                    {"author_id": selected_author.author_id}
                                )
                                s.commit()
                            # Log deletion
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "deleted author",
                                f"Author ID: {selected_author.author_id}, Name: {selected_author.name}"
                            )
                            st.success("Author Deleted Successfully!", icon="✔️")
                            st.session_state["confirm_delete"] = False
                            # Refresh the dialog to update author list
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete author: {str(e)}")


###################################################################################################################################
##################################--------------- Add New Book & Auhtor ----------------------------##################################
###################################################################################################################################


@st.dialog("Add Book and Authors", width="large")
def add_book_dialog(conn):
    # --- Helper Function to Ensure Backward Compatibility ---
    def ensure_author_fields(author):
        default_author = {
            "name": "",
            "email": "",
            "phone": "",
            "author_id": None,
            "author_position": "1st",
            "corresponding_agent": "",
            "publishing_consultant": ""
        }
        for key, default_value in default_author.items():
            if key not in author:
                author[key] = default_value
        return author

    # --- UI Components Inside Dialog ---
    def publisher_section():
        with st.container(border=True):
            st.markdown("<h5 style='color: #4CAF50;'>Publisher</h5>", unsafe_allow_html=True)
            publisher = st.radio(
                "Select Publisher",
                ["AGPH", "Cipher", "AG Volumes", "AG Classics", "AG Kids", "NEET/JEE"],
                key="publisher_select",
                horizontal=True,
                label_visibility="collapsed"
            )
            return publisher

    def book_details_section(publisher):
        with st.container(border=True):
            st.markdown("<h5 style='color: #4CAF50;'>Book Details</h5>", unsafe_allow_html=True)
            col1, col2 = st.columns([2,1])
            book_title = col1.text_input("Book Title", placeholder="Enter Book Title..", key="book_title")
            book_date = col2.date_input("Date", value=date.today(), key="book_date")
            
            toggles_enabled = publisher in ["AGPH", "Cipher", "AG Volumes", "AG Classics"]

            col3, col4 = st.columns([4,2], vertical_alignment="bottom")

            with col3:
                author_type = st.radio(
                    "Author Type",
                    ["Multiple", "Single", "Double", "Triple"],
                    key="author_type_select",
                    horizontal=True,
                    help="Select the number of authors for the book. 'Multiple' allows up to 4 authors.",
                    disabled=not toggles_enabled
                )
            with col4:
                is_publish_only = st.toggle(
                    "Publish Only?",
                    value=False,
                    key="publish_only_toggle",
                    help="Enable this to mark the book as publish only.",
                    disabled=not toggles_enabled
                )
            
            if not toggles_enabled:
                st.warning("Author Type and Publish Only options are disabled for AG Kids and NEET/JEE publishers.")
            
            return {
                "title": book_title,
                "date": book_date,
                "author_type": author_type if toggles_enabled else "Multiple",
                "is_publish_only": is_publish_only if toggles_enabled else False,
                "publisher": publisher
            }

    def syllabus_upload_section(is_publish_only, toggles_enabled):
        with st.container(border=True):
            st.markdown("<h5 style='color: #4CAF50;'>Book Syllabus</h5>", unsafe_allow_html=True)
            syllabus_file = None
            if not is_publish_only and toggles_enabled:
                syllabus_file = st.file_uploader(
                    "Upload Book Syllabus",
                    type=["pdf", "docx", "jpg", "jpeg", "png"],
                    key="syllabus_upload",
                    help="Upload the book syllabus as a PDF, DOCX, or image file."
                )
            else:
                if is_publish_only:
                    st.info("Syllabus upload is disabled for Publish Only books.")
                if not toggles_enabled:
                    st.info("Syllabus upload is disabled for AG Kids and NEET/JEE publishers.")
            return syllabus_file

    def author_details_section(conn, author_type, publisher):
        author_section_disabled = publisher in ["AG Kids", "NEET/JEE"]

        if "authors" not in st.session_state:
            st.session_state.authors = [
                {"name": "", "email": "", "phone": "", "author_id": None, "author_position": f"{i+1}{'st' if i == 0 else 'nd' if i == 1 else 'rd' if i == 2 else 'th'}", "corresponding_agent": "", "publishing_consultant": ""}
                for i in range(4)
            ]
        else:
            st.session_state.authors = [ensure_author_fields(author) for author in st.session_state.authors]

        def get_unique_agents_and_consultants(conn):
            with conn.session as s:
                try:
                    agent_query = text("SELECT DISTINCT corresponding_agent FROM book_authors WHERE corresponding_agent IS NOT NULL AND corresponding_agent != '' ORDER BY corresponding_agent")
                    agents = [row[0] for row in s.execute(agent_query).fetchall()]
                    consultant_query = text("SELECT DISTINCT publishing_consultant FROM book_authors WHERE publishing_consultant IS NOT NULL AND publishing_consultant != '' ORDER BY publishing_consultant")
                    consultants = [row[0] for row in s.execute(consultant_query).fetchall()]
                    return agents, consultants
                except Exception as e:
                    st.error(f"Error fetching agents/consultants: {e}")
                    return [], []

        all_authors = get_all_authors(conn)
        author_options = ["Add New Author"] + [f"{a.name} (ID: {a.author_id})" for a in all_authors]
        unique_agents, unique_consultants = get_unique_agents_and_consultants(conn)

        agent_options = ["Select Agent"] + ["Add New..."] + unique_agents 
        consultant_options = ["Select Consultant"] + ["Add New..."] + unique_consultants 

        max_authors = {
            "Single": 1,
            "Double": 2,
            "Triple": 3,
            "Multiple": 4
        }.get(author_type, 4)

        with st.container(border=True):
            st.markdown("<h5 style='color: #4CAF50;'>Author Details</h5>", unsafe_allow_html=True)
            
            if author_section_disabled:
                st.warning("Author details are disabled for AG Kids and NEET/JEE publishers.")
                return st.session_state.authors
            
            tab_titles = [f"Author {i+1}" for i in range(4)]
            tabs = st.tabs(tab_titles)

            for i, tab in enumerate(tabs):
                disabled = i >= max_authors or author_section_disabled
                with tab:
                    if disabled:
                        st.warning(f"Cannot add Author {i+1}. Maximum allowed authors: {max_authors} for {author_type} author type.")
                    else:
                        selected_author = st.selectbox(
                            f"Select Author {i+1}",
                            author_options,
                            key=f"author_select_{i}",
                            help="Select an existing author or 'Add New Author' to enter new details.",
                            disabled=disabled
                        )

                        if selected_author != "Add New Author" and selected_author and not disabled:
                            selected_author_id = int(selected_author.split('(ID: ')[1][:-1])
                            selected_author_details = next((a for a in all_authors if a.author_id == selected_author_id), None)
                            if selected_author_details:
                                st.session_state.authors[i]["name"] = selected_author_details.name
                                st.session_state.authors[i]["email"] = selected_author_details.email
                                st.session_state.authors[i]["phone"] = selected_author_details.phone
                                st.session_state.authors[i]["author_id"] = selected_author_details.author_id
                        elif selected_author == "Add New Author" and not disabled:
                            st.session_state.authors[i]["author_id"] = None

                        col1, col2 = st.columns(2)
                        st.session_state.authors[i]["name"] = col1.text_input(f"Author Name {i+1}", st.session_state.authors[i]["name"], key=f"name_{i}", placeholder="Enter Author name..", disabled=disabled)
                        available_positions = ["1st", "2nd", "3rd", "4th"]
                        taken_positions = [a["author_position"] for a in st.session_state.authors if a != st.session_state.authors[i]]
                        available_positions = [p for p in available_positions if p not in taken_positions or p == st.session_state.authors[i]["author_position"]]
                        st.session_state.authors[i]["author_position"] = col2.selectbox(
                            f"Position {i+1}",
                            available_positions,
                            index=available_positions.index(st.session_state.authors[i]["author_position"]) if st.session_state.authors[i]["author_position"] in available_positions else 0,
                            key=f"author_position_{i}",
                            disabled=disabled
                        )
                        
                        col3, col4 = st.columns(2)
                        st.session_state.authors[i]["phone"] = col3.text_input(f"Phone {i+1}", st.session_state.authors[i]["phone"], key=f"phone_{i}", placeholder="Enter phone..", disabled=disabled)
                        st.session_state.authors[i]["email"] = col4.text_input(f"Email {i+1}", st.session_state.authors[i]["email"], key=f"email_{i}", placeholder="Enter email..", disabled=disabled)
                        
                        col5, col6 = st.columns(2)

                        selected_agent = col5.selectbox(
                            f"Corresponding Agent {i+1}",
                            agent_options,
                            index=agent_options.index(st.session_state.authors[i]["corresponding_agent"]) if st.session_state.authors[i]["corresponding_agent"] in unique_agents else 0,
                            key=f"agent_select_{i}",
                            disabled=disabled
                        )
                        if selected_agent == "Add New..." and not disabled:
                            st.session_state.authors[i]["corresponding_agent"] = col5.text_input(
                                f"New Agent Name {i+1}",
                                value="",
                                key=f"agent_input_{i}",
                                placeholder="Enter new agent name..."
                            )
                        elif selected_agent != "Select Agent" and not disabled:
                            st.session_state.authors[i]["corresponding_agent"] = selected_agent

                        selected_consultant = col6.selectbox(
                            f"Publishing Consultant {i+1}",
                            consultant_options,
                            index=consultant_options.index(st.session_state.authors[i]["publishing_consultant"]) if st.session_state.authors[i]["publishing_consultant"] in unique_consultants else 0,
                            key=f"consultant_select_{i}",
                            disabled=disabled
                        )
                        if selected_consultant == "Add New..." and not disabled:
                            st.session_state.authors[i]["publishing_consultant"] = col6.text_input(
                                f"New Consultant Name {i+1}",
                                value="",
                                key=f"consultant_input_{i}",
                                placeholder="Enter new consultant name..."
                            )
                        elif selected_consultant != "Select Consultant" and not disabled:
                            st.session_state.authors[i]["publishing_consultant"] = selected_consultant

        return st.session_state.authors

    def is_author_active(author):
        return bool(author["name"] or author["email"] or author["phone"] or author["corresponding_agent"] or author["publishing_consultant"])

    def validate_form(book_data, author_data, author_type, publisher):
        errors = []
        if not book_data["title"]:
            errors.append("Book title is required.")
        if not book_data["date"]:
            errors.append("Book date is required.")
        if not book_data["publisher"]:
            errors.append("Publisher is required.")

        if publisher not in ["AG Kids", "NEET/JEE"]:
            active_authors = [a for a in author_data if is_author_active(a)]
            if not active_authors:
                errors.append("At least one author must be provided.")
            max_authors = {"Single": 1, "Double": 2, "Triple": 3, "Multiple": 4}.get(author_type, 4)
            if len(active_authors) > max_authors:
                errors.append(f"Too many authors. {author_type} allows up to {max_authors} authors.")
            existing_author_ids = set()
            for i, author in enumerate(author_data):
                if is_author_active(author):
                    if not author["name"]:
                        errors.append(f"Author {i+1} name is required.")
                    if not author["email"]:
                        errors.append(f"Author {i+1} email is required.")
                    if not author["phone"]:
                        errors.append(f"Author {i+1} phone is required.")
                    if not author["publishing_consultant"]:
                        errors.append(f"Author {i+1} publishing consultant is required.")
                    if author["author_id"]:
                        if author["author_id"] in existing_author_ids:
                            errors.append(f"Author {i+1} (ID: {author['author_id']}) is already added. Please remove duplicates.")
                        existing_author_ids.add(author["author_id"])
            active_positions = [author["author_position"] for author in active_authors]
            if len(active_positions) != len(set(active_positions)):
                errors.append("All active authors must have unique positions.")
        return errors

    # --- Combined Container Inside Dialog ---
    with st.container():
        publisher = publisher_section()
        book_data = book_details_section(publisher)
        author_data = author_details_section(conn, book_data["author_type"], publisher)
        syllabus_file = syllabus_upload_section(book_data["is_publish_only"], publisher in ["AGPH", "Cipher", "AG Volumes", "AG Classics"])
        book_data["syllabus_file"] = syllabus_file

    # --- Save, Clear, and Cancel Buttons ---
    col1, col2 = st.columns([7, 1])
    with col1:
        if st.button("Save", key="dialog_save", type="primary"):
            errors = validate_form(book_data, author_data, book_data["author_type"], publisher)
            if errors:
                st.error("\n".join(errors), icon="🚨")
            else:
                with st.spinner("Saving..."):
                    with conn.session as s:
                        try:
                            # Handle syllabus file upload
                            syllabus_path = None
                            if book_data["syllabus_file"] and not book_data["is_publish_only"]:
                                file_extension = os.path.splitext(book_data["syllabus_file"].name)[1]
                                unique_filename = f"syllabus_{book_data['title'].replace(' ', '_')}_{int(time.time())}{file_extension}"
                                syllabus_path_temp = os.path.join(UPLOAD_DIR, unique_filename)
                                if not os.access(UPLOAD_DIR, os.W_OK):
                                    st.error(f"No write permission for {UPLOAD_DIR}.")
                                    raise PermissionError(f"Cannot write to {UPLOAD_DIR}")
                                try:
                                    with open(syllabus_path_temp, "wb") as f:
                                        f.write(book_data["syllabus_file"].getbuffer())
                                    syllabus_path = syllabus_path_temp
                                except Exception as e:
                                    st.error(f"Failed to save syllabus file: {str(e)}")
                                    raise
                            
                            # Insert book
                            s.execute(text("""
                                INSERT INTO books (title, date, author_type, is_publish_only, publisher, syllabus_path)
                                VALUES (:title, :date, :author_type, :is_publish_only, :publisher, :syllabus_path)
                            """), params={
                                "title": book_data["title"],
                                "date": book_data["date"],
                                "author_type": book_data["author_type"],
                                "is_publish_only": book_data["is_publish_only"],
                                "publisher": book_data["publisher"],
                                "syllabus_path": syllabus_path
                            })
                            book_id = s.execute(text("SELECT LAST_INSERT_ID();")).scalar()

                            # Process active authors
                            active_authors = [a for a in author_data if is_author_active(a)]
                            if publisher not in ["AG Kids", "NEET/JEE"]:
                                for author in active_authors:
                                    if author["author_id"]:
                                        author_id_to_link = author["author_id"]
                                    else:
                                        s.execute(text("""
                                            INSERT INTO authors (name, email, phone)
                                            VALUES (:name, :email, :phone)
                                            ON DUPLICATE KEY UPDATE name=name
                                        """), params={"name": author["name"], "email": author["email"], "phone": author["phone"]})
                                        author_id_to_link = s.execute(text("SELECT LAST_INSERT_ID();")).scalar()

                                    if book_id and author_id_to_link:
                                        s.execute(text("""
                                            INSERT INTO book_authors (book_id, author_id, author_position, corresponding_agent, publishing_consultant)
                                            VALUES (:book_id, :author_id, :author_position, :corresponding_agent, :publishing_consultant)
                                        """), params={
                                            "book_id": book_id,
                                            "author_id": author_id_to_link,
                                            "author_position": author["author_position"],
                                            "corresponding_agent": author["corresponding_agent"],
                                            "publishing_consultant": author["publishing_consultant"]
                                        })
                            s.commit()

                            # Log save action with specified details
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "added book",
                                f"Book ID: {book_id}, Publisher: {book_data['publisher']}, Author Type: {book_data['author_type']}, Is Publish Only: {book_data['is_publish_only']}"
                            )

                            st.success("Book and Authors Saved Successfully!", icon="✔️")
                            st.session_state.authors = [
                                {"name": "", "email": "", "phone": "", "author_id": None, "author_position": f"{i+1}{'st' if i == 0 else 'nd' if i == 1 else 'rd' if i == 2 else 'th'}", "corresponding_agent": "", "publishing_consultant": ""}
                                for i in range(4)
                            ]
                            st.rerun()
                        except Exception as db_error:
                            s.rollback()
                            st.error(f"Database error: {db_error}")

    with col2:
        if st.button("Cancel", key="dialog_cancel", type="secondary"):
            st.session_state.authors = [
                {"name": "", "email": "", "phone": "", "author_id": None, "author_position": f"{i+1}{'st' if i == 0 else 'nd' if i == 1 else 'rd' if i == 2 else 'th'}", "corresponding_agent": "", "publishing_consultant": ""}
                for i in range(4)
            ]
            st.rerun()



###################################################################################################################################
##################################--------------- Edit ISBN Dialog ----------------------------##################################
###################################################################################################################################

from datetime import datetime

@st.dialog("Manage ISBN and Book Title", width="large")
def manage_isbn_dialog(conn, book_id, current_apply_isbn, current_isbn):
    # Fetch current book details
    book_details = fetch_book_details(book_id, conn)
    if book_details.empty:
        st.error("❌ Book not found in database.")
        return
    
    # Extract current values
    current_title = book_details.iloc[0]['title']
    current_date = book_details.iloc[0]['date']
    current_is_publish_only = book_details.iloc[0].get('is_publish_only', 0) == 1
    current_publisher = book_details.iloc[0].get('publisher', '')
    current_isbn_receive_date = book_details.iloc[0].get('isbn_receive_date', None)

    publisher_colors = {
        "AGPH": {"color": "#ffffff", "background": "#e4be17"},
        "Cipher": {"color": "#ffffff", "background": "#8f1b83"},
        "AG Volumes": {"color": "#ffffff", "background": "#2b1a70"},
        "AG Classics": {"color": "#ffffff", "background": "#d81b60"},
        "AG Kids": {"color": "#ffffff", "background": "#f57c00"},
        "NEET/JEE": {"color": "#ffffff", "background": "#0288d1"}
    }
    
    publisher_badge = ""
    if current_publisher in publisher_colors:
        style = publisher_colors[current_publisher]
        publisher_style = f"color: {style['color']}; font-size: 12px; background-color: {style['background']}; padding: 2px 6px; border-radius: 12px; margin-left: 5px;"
        publisher_badge = f'<span style="{publisher_style}">{current_publisher}</span>'

    # Initialize session state for tracking previous values
    if f"apply_isbn_{book_id}_prev" not in st.session_state:
        st.session_state[f"apply_isbn_{book_id}_prev"] = bool(current_apply_isbn)
    if f"receive_isbn_{book_id}_prev" not in st.session_state:
        st.session_state[f"receive_isbn_{book_id}_prev"] = bool(pd.notna(current_isbn))

    # Main container
    with st.container():
        st.markdown(f"### {book_id} - {current_title}{publisher_badge}", unsafe_allow_html=True)

        # Book Details Section
        st.markdown("<h5 style='color: #4CAF50;'>Book Details</h5>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            col1, col2 = st.columns([3, 1])
            with col1:
                new_title = st.text_input(
                    "Book Title",
                    value=current_title,
                    key=f"title_{book_id}",
                    help="Enter the book title"
                )
            with col2:
                new_date = st.date_input(
                    "Book Date",
                    value=current_date if current_date else datetime.today(),
                    key=f"date_{book_id}",
                    help="Select the book date"
                )
            new_is_publish_only = st.toggle(
                "Publish Only?",
                value=current_is_publish_only,
                key=f"is_publish_only_{book_id}",
                help="Enable this to mark the book as publish only (disables writing operations)"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<h5 style='color: #4CAF50;'>Associated Authors</h5>", unsafe_allow_html=True)
        with st.expander("Authors", expanded=False):
            authors_data = fetch_book_authors(book_id, conn)
            if authors_data.empty:
                st.info("No authors associated with this book.")
            else:
                authors_data = authors_data.sort_values(by='author_position')
                with st.container(border=False):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown("#### 👤 Author Name")
                    with col2:
                        st.markdown("#### 🏷️ Position")
                for _, author in authors_data.iterrows():
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"<div style='margin-bottom: 6px;'>➤ {author['name']}</div>", unsafe_allow_html=True)
                    with col2:
                        position = author['author_position'] if pd.notna(author['author_position']) else "Not specified"
                        st.markdown(f"<div style='color: #0288d1; margin-bottom: 6px;'>{position}</div>", unsafe_allow_html=True)

        if not has_open_author_position(conn, book_id):
            # ISBN Details Section
            st.markdown("<h5 style='color: #4CAF50;'>ISBN Details</h5>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown('<div class="info-box">', unsafe_allow_html=True)
                apply_isbn = st.checkbox(
                    "ISBN Applied?",
                    value=bool(current_apply_isbn),
                    key=f"apply_{book_id}",
                    help="Check if ISBN application has been made"
                )
                receive_isbn = st.checkbox(
                    "ISBN Received?",
                    value=bool(pd.notna(current_isbn)),
                    key=f"receive_{book_id}",
                    disabled=not apply_isbn,
                    help="Check if ISBN has been received (requires ISBN Applied)"
                )
                # Log checkbox interactions
                if apply_isbn != st.session_state[f"apply_isbn_{book_id}_prev"]:
                    log_activity(
                        conn,
                        st.session_state.user_id,
                        st.session_state.username,
                        st.session_state.session_id,
                        "toggled checkbox",
                        f"Book ID: {book_id}, ISBN Applied changed to '{apply_isbn}'"
                    )
                    st.session_state[f"apply_isbn_{book_id}_prev"] = apply_isbn
                if receive_isbn != st.session_state[f"receive_isbn_{book_id}_prev"]:
                    log_activity(
                        conn,
                        st.session_state.user_id,
                        st.session_state.username,
                        st.session_state.session_id,
                        "toggled checkbox",
                        f"Book ID: {book_id}, ISBN Received changed to '{receive_isbn}'"
                    )
                    st.session_state[f"receive_isbn_{book_id}_prev"] = receive_isbn

                if apply_isbn and receive_isbn:
                    col3, col4 = st.columns(2)
                    with col3:
                        new_isbn = st.text_input(
                            "ISBN",
                            value=current_isbn if pd.notna(current_isbn) else "",
                            key=f"isbn_input_{book_id}",
                            help="Enter the ISBN number"
                        )
                    with col4:
                        default_date = current_isbn_receive_date if pd.notna(current_isbn_receive_date) else datetime.today()
                        isbn_receive_date = st.date_input(
                            "ISBN Receive / Allotment Date",
                            value=default_date,
                            key=f"date_input_{book_id}",
                            help="Select the date ISBN was received"
                        )
                else:
                    new_isbn = None
                    isbn_receive_date = None
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("This book has open author positions. ISBN management is not applicable.")

        # Save Button
        if st.button("Save Changes", key=f"save_isbn_{book_id}", type="secondary"):
            with st.spinner("Saving changes..."):
                with conn.session as s:
                    try:
                        # Track changes for logging
                        changes = []
                        if new_title != current_title:
                            changes.append(f"Updated title from '{current_title}' to '{new_title}'")
                        if new_date != current_date:
                            changes.append(f"Updated date from '{current_date}' to '{new_date}'")
                        if new_is_publish_only != current_is_publish_only:
                            changes.append(f"Updated is_publish_only to '{new_is_publish_only}'")
                        if apply_isbn != bool(current_apply_isbn):
                            changes.append(f"Updated ISBN Applied to '{apply_isbn}'")
                        if receive_isbn != bool(pd.notna(current_isbn)):
                            changes.append(f"Updated ISBN Received to '{receive_isbn}'")
                        if apply_isbn and receive_isbn and new_isbn != current_isbn:
                            changes.append(f"Updated ISBN to '{new_isbn}'")
                        if apply_isbn and receive_isbn and isbn_receive_date != current_isbn_receive_date:
                            changes.append(f"Updated ISBN Receive Date to '{isbn_receive_date}'")

                        # Update database
                        if apply_isbn and receive_isbn and new_isbn:
                            s.execute(
                                text("""
                                    UPDATE books 
                                    SET apply_isbn = :apply_isbn, 
                                        isbn = :isbn, 
                                        isbn_receive_date = :isbn_receive_date, 
                                        title = :title, 
                                        date = :date,
                                        is_publish_only = :is_publish_only
                                    WHERE book_id = :book_id
                                """),
                                {
                                    "apply_isbn": 1, 
                                    "isbn": new_isbn, 
                                    "isbn_receive_date": isbn_receive_date, 
                                    "title": new_title, 
                                    "date": new_date,
                                    "is_publish_only": 1 if new_is_publish_only else 0,
                                    "book_id": book_id
                                }
                            )
                        elif apply_isbn and not receive_isbn:
                            s.execute(
                                text("""
                                    UPDATE books 
                                    SET apply_isbn = :apply_isbn, 
                                        isbn = NULL, 
                                        isbn_receive_date = NULL, 
                                        title = :title, 
                                        date = :date,
                                        is_publish_only = :is_publish_only
                                    WHERE book_id = :book_id
                                """),
                                {
                                    "apply_isbn": 1, 
                                    "title": new_title, 
                                    "date": new_date,
                                    "is_publish_only": 1 if new_is_publish_only else 0,
                                    "book_id": book_id
                                }
                            )
                        else:
                            s.execute(
                                text("""
                                    UPDATE books 
                                    SET apply_isbn = :apply_isbn, 
                                        isbn = NULL, 
                                        isbn_receive_date = NULL, 
                                        title = :title, 
                                        date = :date,
                                        is_publish_only = :is_publish_only
                                    WHERE book_id = :book_id
                                """),
                                {
                                    "apply_isbn": 0, 
                                    "title": new_title, 
                                    "date": new_date,
                                    "is_publish_only": 1 if new_is_publish_only else 0,
                                    "book_id": book_id
                                }
                            )
                        s.commit()

                        # Log changes if any
                        if changes:
                            details = f"Book ID: {book_id}, {', '.join(changes)}"
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "updated book",
                                details
                            )

                        st.success("Book Details Updated Successfully!", icon="✔️")
                        time.sleep(1)
                        st.rerun()
                    except Exception as db_error:
                        s.rollback()
                        st.error(f"Database error: {db_error}")


###################################################################################################################################
##################################--------------- Edit Price Dialog ----------------------------##################################
###################################################################################################################################


@st.dialog("Manage Book Price and Author Payments", width="large")
def manage_price_dialog(book_id, current_price, conn):
    # Fetch book details for title
    book_details = fetch_book_details(book_id, conn)
    book_title = book_details.iloc[0]['title'] if not book_details.empty else "Unknown Title"
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
    with col2:
        if st.button(":material/refresh: Refresh", key="refresh_price", type="tertiary"):
            st.cache_data.clear()

    # Updated Streamlit-aligned CSS with improved visuals
    st.markdown("""
        <style>
                
        .payment-status {
            font-size: 12px;
            padding: 3px 8px;
            border-radius: 12px;
            margin-left: 10px;
            display: inline-block;
        }
        .status-paid { background-color: #e6ffe6; color: #006600; }
        .status-partial { background-color: #fff3e6; color: #cc6600; }
        .status-pending { background-color: #ffe6e6; color: #cc0000; }
        .payment-box {
            padding: 10px;
            border-radius: 6px;
            margin: 0 4px 8px 0;
            text-align: center;
            font-size: 14px;
            line-height: 1.5;
            border: 1px solid #e0e0e0;
            background-color: #ffffff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: transform 0.2s ease, background-color 0.2s ease;
        }
        .payment-box:hover {
            background-color: #f9f9f9;
            transform: translateY(-2px);
        }
        .status-paid {
            background-color: #f0f9eb;
            border-color: #b7e1a1;
            color: #2e7d32;
        }
        .status-partial {
            background-color: #fff4e6;
            border-color: #ffd8a8;
            color: #e65100;
        }
        .status-pending {
            background-color: #f6f6f6;
            border-color: #d9d9d9;
            color: #666666;
        }
        .author-name {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .payment-text {
            font-size: 14px;
            font-weight: 400;
        }
        .agent-text {
            font-size: 11px;
            color: #888888;
            margin-top: 6px;
            font-style: italic;
        }
        .status-badge {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 10px;
            display: inline-block;
            margin-top: 4px;
        }
        .status-paid .status-badge { background-color: #2e7d32; color: #ffffff; }
        .status-partial .status-badge { background-color: #e65100; color: #ffffff; }
        .status-pending .status-badge { background-color: #666666; color: #ffffff; }
        </style>
    """, unsafe_allow_html=True)

    # Payment Status Overview
    book_authors = fetch_book_authors(book_id, conn)
    
    if book_authors.empty:
        st.warning(f"No authors found for Book ID: {book_id}")
    else:
        cols = st.columns(len(book_authors), gap="small")
        for i, (_, row) in enumerate(book_authors.iterrows()):
            total_amount = int(row.get('total_amount', 0) or 0)
            emi1 = int(row.get('emi1', 0) or 0)
            emi2 = int(row.get('emi2', 0) or 0)
            emi3 = int(row.get('emi3', 0) or 0)
            amount_paid = emi1 + emi2 + emi3
            agent = row.get('corresponding_agent', 'Unknown Agent')

            # Determine payment status
            if amount_paid >= total_amount and total_amount > 0:
                status_class = "status-paid"
                status_text = f"₹{amount_paid}/₹{total_amount}"
                badge_text = "Paid"
            elif amount_paid > 0:
                status_class = "status-partial"
                status_text = f"₹{amount_paid}/₹{total_amount}"
                badge_text = "Partial"
            else:
                status_class = "status-pending"
                status_text = "₹0/₹{total_amount}" if total_amount > 0 else "N/A"
                badge_text = "Pending"

            with cols[i]:
                html = f"""
                    <div class="payment-box {status_class}">
                        <div class="author-name">{row['name']}</div>
                        <div class="payment-text">{status_text}</div>
                        <div class="status-badge">{badge_text}</div>
                        <div class="agent-text">{agent}</div>
                    </div>
                """
                st.markdown(html, unsafe_allow_html=True)

    contrn = st.container(border=True)
    with contrn:
        # Section 1: Book Price
        st.markdown("<h5 style='color: #4CAF50;'>Book Price</h5>", unsafe_allow_html=True)
        col1,col2 = st.columns([1,1], gap="small", vertical_alignment="bottom")
        with col1:
            price_str = st.text_input(
                "Book Price (₹)",
                value=str(int(current_price)) if pd.notna(current_price) else "",
                key=f"price_{book_id}",
                placeholder="Enter whole amount"
            )

        with col2:
            if st.button("Save Book Price", key=f"save_price_{book_id}"):
                with st.spinner("Saving..."):
                    time.sleep(1)
                    try:
                        price = int(price_str) if price_str.strip() else None
                        if price is not None and price < 0:
                            st.error("Price cannot be negative")
                            return
                        with conn.session as s:
                            s.execute(
                                text("UPDATE books SET price = :price WHERE book_id = :book_id"),
                                {"price": price, "book_id": book_id}
                            )
                            s.commit()
                        st.success("Book Price Updated Successfully", icon="✔️")
                    except ValueError:
                        st.error("Please enter a valid whole number", icon="🚨")

    cont = st.container(border=True)
    with cont:
        # Section 2: Author Payments with Tabs
        st.markdown("<h5 style='color: #4CAF50;'>Author Payments</h5>", unsafe_allow_html=True)
        if not book_authors.empty:
            total_author_amounts = 0
            updated_authors = []

            # Create tabs for each author
            tab_titles = [f"{row['name']} (ID: {row['author_id']})" for _, row in book_authors.iterrows()]
            tabs = st.tabs(tab_titles)

            for tab, (_, row) in zip(tabs, book_authors.iterrows()):
                # Inside the `for tab, (_, row) in zip(tabs, book_authors.iterrows()):` loop
                with tab:
                    # Fetch existing payment details
                    total_amount = int(row.get('total_amount', 0) or 0)
                    emi1 = int(row.get('emi1', 0) or 0)
                    emi2 = int(row.get('emi2', 0) or 0)
                    emi3 = int(row.get('emi3', 0) or 0)
                    emi1_date = row.get('emi1_date', None)
                    emi2_date = row.get('emi2_date', None)
                    emi3_date = row.get('emi3_date', None)
                    # New fields for payment mode and transaction ID (now nullable in DB)
                    emi1_payment_mode = row.get('emi1_payment_mode', None)  # Could be None
                    emi2_payment_mode = row.get('emi2_payment_mode', None)  # Could be None
                    emi3_payment_mode = row.get('emi3_payment_mode', None)  # Could be None
                    emi1_transaction_id = row.get('emi1_transaction_id', '')
                    emi2_transaction_id = row.get('emi2_transaction_id', '')
                    emi3_transaction_id = row.get('emi3_transaction_id', '')
                    amount_paid = emi1 + emi2 + emi3

                    # Payment status (unchanged)
                    if amount_paid >= total_amount and total_amount > 0:
                        status = '<span class="payment-status status-paid">Fully Paid</span>'
                    elif amount_paid > 0:
                        status = '<span class="payment-status status-partial">Partially Paid</span>'
                    else:
                        status = '<span class="payment-status status-pending">Pending</span>'
                    st.markdown(f"**Payment Status:** {status}", unsafe_allow_html=True)

                    # Total Amount Due (unchanged)
                    total_str = st.text_input(
                        "Total Amount Due (₹)",
                        value=str(total_amount) if total_amount > 0 else "",
                        key=f"total_{row['id']}",
                        placeholder="Enter whole amount"
                    )

                    # EMI Payments with Dates, Payment Mode, and Transaction ID
                    #st.markdown("#### EMI Details")
                    payment_modes = ["Cash", "UPI", "Bank Deposit"]

                    # EMI 1
                    st.markdown("**EMI 1**")
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        emi1_str = st.text_input(
                            "Amount (₹)",
                            value=str(emi1) if emi1 > 0 else "",
                            key=f"emi1_{row['id']}",
                            placeholder="Enter EMI amount"
                        )
                    with col2:
                        emi1_date_new = st.date_input(
                            "Date",
                            value=pd.to_datetime(emi1_date) if emi1_date else None,
                            key=f"emi1_date_{row['id']}"
                        )
                    with col3:
                        emi1_mode = st.selectbox(
                            "Payment Mode",
                            payment_modes,
                            index=payment_modes.index(emi1_payment_mode) if emi1_payment_mode in payment_modes else 0,
                            key=f"emi1_mode_{row['id']}"
                        )
                    if emi1_mode in ["UPI", "Bank Deposit"]:
                        emi1_txn_id = st.text_input(
                            "Transaction ID",
                            value=emi1_transaction_id,
                            key=f"emi1_txn_{row['id']}",
                            placeholder="Enter Transaction ID"
                        )
                    else:
                        emi1_txn_id = ""

                    # EMI 2
                    st.markdown("**EMI 2**")
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        emi2_str = st.text_input(
                            "Amount (₹)",
                            value=str(emi2) if emi2 > 0 else "",
                            key=f"emi2_{row['id']}",
                            placeholder="Enter EMI amount"
                        )
                    with col2:
                        emi2_date_new = st.date_input(
                            "Date",
                            value=pd.to_datetime(emi2_date) if emi2_date else None,
                            key=f"emi2_date_{row['id']}"
                        )
                    with col3:
                        emi2_mode = st.selectbox(
                            "Payment Mode",
                            payment_modes,
                            index=payment_modes.index(emi2_payment_mode) if emi2_payment_mode in payment_modes else 0,
                            key=f"emi2_mode_{row['id']}"
                        )
                    if emi2_mode in ["UPI", "Bank Deposit"]:
                        emi2_txn_id = st.text_input(
                            "Transaction ID",
                            value=emi2_transaction_id,
                            key=f"emi2_txn_{row['id']}",
                            placeholder="Enter Transaction ID"
                        )
                    else:
                        emi2_txn_id = ""

                    # EMI 3
                    st.markdown("**EMI 3**")
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        emi3_str = st.text_input(
                            "Amount (₹)",
                            value=str(emi3) if emi3 > 0 else "",
                            key=f"emi3_{row['id']}",
                            placeholder="Enter EMI amount"
                        )
                    with col2:
                        emi3_date_new = st.date_input(
                            "Date",
                            value=pd.to_datetime(emi3_date) if emi3_date else None,
                            key=f"emi3_date_{row['id']}"
                        )
                    with col3:
                        emi3_mode = st.selectbox(
                            "Payment Mode",
                            payment_modes,
                            index=payment_modes.index(emi3_payment_mode) if emi3_payment_mode in payment_modes else 0,
                            key=f"emi3_mode_{row['id']}"
                        )
                    if emi3_mode in ["UPI", "Bank Deposit"]:
                        emi3_txn_id = st.text_input(
                            "Transaction ID",
                            value=emi3_transaction_id,
                            key=f"emi3_txn_{row['id']}",
                            placeholder="Enter Transaction ID"
                        )
                    else:
                        emi3_txn_id = ""

                    # Calculate remaining balance
                    try:
                        new_total = int(total_str) if total_str.strip() else 0
                        new_emi1 = int(emi1_str) if emi1_str.strip() else 0
                        new_emi2 = int(emi2_str) if emi2_str.strip() else 0
                        new_emi3 = int(emi3_str) if emi3_str.strip() else 0
                        new_paid = new_emi1 + new_emi2 + new_emi3
                        remaining = new_total - new_paid
                        total_author_amounts += new_total
                        updated_authors.append((row['id'], new_total, new_emi1, new_emi2, new_emi3, 
                                                emi1_date_new, emi2_date_new, emi3_date_new,
                                                emi1_mode, emi2_mode, emi3_mode,
                                                emi1_txn_id, emi2_txn_id, emi3_txn_id))
                    except ValueError:
                        st.error("Please enter valid whole numbers for all fields")
                        return

                    st.markdown(f"<span style='color:green'>**Total Paid:** ₹{new_paid}</span> | <span style='color:red'>**Remaining Balance:** ₹{remaining}</span>", unsafe_allow_html=True)

                    # Save button
                    if st.button("Save Payment", key=f"save_payment_{row['id']}"):
                        with st.spinner("Saving Payment..."):
                            time.sleep(1)
                            if new_paid > new_total:
                                st.error("Total EMI payments cannot exceed total amount")
                            elif new_total < 0 or new_emi1 < 0 or new_emi2 < 0 or new_emi3 < 0:
                                st.error("Amounts cannot be negative")
                            else:
                                book_price = int(price_str) if price_str.strip() else current_price
                                if pd.isna(book_price):
                                    st.error("Please set a book price first")
                                    return
                                if total_author_amounts > book_price:
                                    st.error(f"Total author amounts (₹{total_author_amounts}) cannot exceed book price (₹{book_price})")
                                    return

                                updates = {
                                    "total_amount": new_total,
                                    "emi1": new_emi1,
                                    "emi2": new_emi2,
                                    "emi3": new_emi3,
                                    "emi1_date": emi1_date_new,
                                    "emi2_date": emi2_date_new,
                                    "emi3_date": emi3_date_new,
                                    "emi1_payment_mode": emi1_mode,
                                    "emi2_payment_mode": emi2_mode,
                                    "emi3_payment_mode": emi3_mode,
                                    "emi1_transaction_id": emi1_txn_id,
                                    "emi2_transaction_id": emi2_txn_id,
                                    "emi3_transaction_id": emi3_txn_id
                                }
                                update_book_authors(row['id'], updates, conn)
                                st.success(f"Payment updated for {row['name']}", icon="✔️")
                                st.cache_data.clear()




###################################################################################################################################
##################################--------------- Edit Auhtor Dialog ----------------------------##################################
###################################################################################################################################



# Function to fetch book_author details along with author details for a given book_id
def fetch_book_authors(book_id, conn):
    query = f"""
    SELECT ba.id, ba.book_id, ba.author_id, a.name, a.email, a.phone, 
           ba.author_position, ba.welcome_mail_sent, ba.corresponding_agent, 
           ba.publishing_consultant, ba.photo_recive, ba.id_proof_recive, 
           ba.author_details_sent, ba.cover_agreement_sent, ba.agreement_received, 
           ba.digital_book_sent, 
           ba.printing_confirmation, ba.delivery_address, ba.delivery_charge, 
           ba.number_of_books, ba.total_amount, ba.emi1, ba.emi2, ba.emi3,
           ba.emi1_date, ba.emi2_date, ba.emi3_date,
           ba.delivery_date, ba.tracking_id, ba.delivery_vendor,
           ba.emi1_payment_mode, ba.emi2_payment_mode, ba.emi3_payment_mode,
           ba.emi1_transaction_id, ba.emi2_transaction_id, ba.emi3_transaction_id
    FROM book_authors ba
    JOIN authors a ON ba.author_id = a.author_id
    WHERE ba.book_id = '{book_id}'
    """
    return conn.query(query, show_spinner = False)

def insert_author(conn, name, email, phone):
    """Insert a new author into the database and return the author_id."""
    try:
        # Validate inputs
        if not name:
            raise ValueError("Author name cannot be empty")
        if len(name) > 255:  # Assuming VARCHAR(255) for name
            raise ValueError("Author name exceeds maximum length of 255 characters")
        if not validate_email(email):
            raise ValueError("Invalid email format")
        if len(email) > 255:  # Assuming VARCHAR(255) for email
            raise ValueError("Email exceeds maximum length of 255 characters")
        if not validate_phone(phone):
            raise ValueError("Invalid phone number format or length")

        with conn.session as s:
            # Insert the author
            result = s.execute(
                text("""
                    INSERT INTO authors (name, email, phone)
                    VALUES (:name, :email, :phone)
                """),
                params={"name": name, "email": email, "phone": phone}
            )
            # Check if the insert was successful
            if result.rowcount != 1:
                raise Exception("Failed to insert author: No rows affected")
            
            # Retrieve the author_id using LAST_INSERT_ID()
            author_id = s.execute(text("SELECT LAST_INSERT_ID();")).scalar()
            if not author_id:
                raise Exception("Failed to retrieve author_id after insertion")
            
            # Commit the transaction to ensure the insert is persisted
            s.commit()
            
            # Verify the author_id exists after commit
            result = s.execute(
                text("SELECT author_id FROM authors WHERE author_id = :author_id"),
                params={"author_id": author_id}
            ).fetchone()
            if not result:
                raise Exception(f"Author ID {author_id} not found in authors table after commit")
            
            return author_id
    except Exception as e:
        st.error(f"Error inserting author: {e}")
        return None

# Function to update book_authors table
def update_book_authors(id, updates, conn):
    set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
    query = f"UPDATE book_authors SET {set_clause} WHERE id = :id"
    params = updates.copy()
    params["id"] = int(id)
    with conn.session as session:
        session.execute(text(query), params)
        session.commit()

# Function to delete a book_author entry
def delete_book_author(id, conn):
    query = "DELETE FROM book_authors WHERE id = :id"
    with conn.session as session:
        session.execute(text(query), {"id": int(id)})
        session.commit()

def validate_email(email):
    """Validate email format."""
    email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(email_pattern, email))

def validate_phone(phone):
    """Validate phone number format (basic validation)."""
    phone_pattern = r"^\+?\d{10,15}$"
    return bool(re.match(phone_pattern, phone))

def is_author_complete(author):
    """Check if an author entry is complete (all required fields are filled)."""
    return (
        author["name"] and
        author["email"] and validate_email(author["email"]) and
        author["phone"] and validate_phone(author["phone"]) and
        author["author_position"] and
        author["publishing_consultant"]
    )

def initialize_new_authors(slots):
    """Initialize new author entries."""
    return [
        {"name": "", "email": "", "phone": "", "author_id": None, "author_position": None,
         "corresponding_agent": "", "publishing_consultant": ""}
        for _ in range(slots)
    ]

def initialize_new_editors(slots):
    return [
        {"name": "", "email": "", "phone": "", "author_id": None, "author_position": None}
        for _ in range(slots)
    ]

# New helper functions for chapters and editors
def fetch_chapters(book_id, conn):
    with conn.session as s:
        query = text("""
            SELECT chapter_id, book_id, chapter_title, chapter_number
            FROM chapters
            WHERE book_id = :book_id
            ORDER BY chapter_number
        """)
        result = s.execute(query, {"book_id": book_id}).fetchall()
        return pd.DataFrame(result, columns=['chapter_id', 'book_id', 'chapter_title', 'chapter_number'])

def fetch_chapter_editors(chapter_id, conn):
    with conn.session as s:
        query = text("""
            SELECT ce.author_id, ce.author_position, a.name, a.email, a.phone,
                   ce.corresponding_agent, ce.publishing_consultant
            FROM chapter_editors ce
            JOIN authors a ON ce.author_id = a.author_id
            WHERE ce.chapter_id = :chapter_id
            ORDER BY ce.author_position
        """)
        result = s.execute(query, {"chapter_id": chapter_id}).fetchall()
        return pd.DataFrame(result, columns=[
            'author_id', 'author_position', 'name', 'email', 'phone',
            'corresponding_agent', 'publishing_consultant'
        ])

def validate_editor(editor, existing_positions, existing_editor_ids, all_new_editors, index):
    if not editor["name"]:
        return False, "Editor name is required."
    if not editor["email"]:
        return False, "Email is required."
    if not validate_email(editor["email"]):
        return False, "Invalid email format."
    if not editor["phone"]:
        return False, "Phone number is required."
    if not validate_phone(editor["phone"]):
        return False, "Invalid phone number format (e.g., +919876543210)."
    if not editor["author_position"]:
        return False, "Editor position is required."
    
    if editor["author_position"] in existing_positions:
        return False, f"Position '{editor['author_position']}' is already taken."
    new_positions = [e["author_position"] for i, e in enumerate(all_new_editors) if i != index and e["author_position"]]
    if editor["author_position"] in new_positions:
        return False, f"Position '{editor['author_position']}' is already taken by another new editor."
    
    if editor["author_id"] and editor["author_id"] in existing_editor_ids:
        return False, f"Editor '{editor['name']}' is already linked to this chapter."
    new_editor_ids = [e["author_id"] for i, e in enumerate(all_new_editors) if i != index and e["author_id"]]
    if editor["author_id"] and editor["author_id"] in new_editor_ids:
        return False, f"Editor '{editor['name']}' is already added as a new editor."
    
    return True, ""

def get_all_authors(conn):
    with conn.session as s:
        try:
            query = text("SELECT author_id, name, email, phone FROM authors ORDER BY name")
            authors = s.execute(query).fetchall()
            return authors
        except Exception as e:
            st.error(f"Error fetching authors: {e}")
            return []
        
        # Fetch unique corresponding agents and publishing consultants
def get_unique_agents_and_consultants(conn):
    with conn.session as s:
        try:
            agent_query = text("SELECT DISTINCT corresponding_agent FROM book_authors WHERE corresponding_agent IS NOT NULL AND corresponding_agent != '' ORDER BY corresponding_agent")
            agents = [row[0] for row in s.execute(agent_query).fetchall()]
            
            consultant_query = text("SELECT DISTINCT publishing_consultant FROM book_authors WHERE publishing_consultant IS NOT NULL AND publishing_consultant != '' ORDER BY publishing_consultant")
            consultants = [row[0] for row in s.execute(consultant_query).fetchall()]
            
            return agents, consultants
        except Exception as e:
            st.error(f"Error fetching agents/consultants: {e}")
            return [], []
# Constants
MAX_AUTHORS = 4
MAX_CHAPTERS = 30
MAX_EDITORS_PER_CHAPTER = 2

# Updated dialog for editing author details with improved UI
@st.dialog("Edit Author Details", width='large')
def edit_author_dialog(book_id, conn):
    # Fetch book details for title, is_single_author, num_copies, and print_status
    book_details = fetch_book_details(book_id, conn)
    if book_details.empty:
        st.markdown(f"### Authors for Book ID: {book_id}")
        st.error("❌ Book details not found.")
        if st.button("Close"):
            st.rerun()
        return

    book_title = book_details.iloc[0]['title']
    is_single_author = book_details.iloc[0]['is_single_author']
    num_copies = book_details.iloc[0]['num_copies']
    print_status = book_details.iloc[0]['print_status']
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
    with col2:
        if st.button(":material/refresh: Refresh", key="refresh_author", type="tertiary"):
            st.cache_data.clear()

    # Custom CSS for better aesthetics
    st.markdown("""
        <style>
        .stTabs { padding-bottom: 10px; }
        .info-box { 
            background-color: #f0f2f6; 
            border-radius: 8px; 
            margin-bottom: 10px; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
        }
        .error-box {
            background-color: #ffcccc;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .success-box {
            background-color: #e6ffe6;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Fetch author details
    book_authors = fetch_book_authors(book_id, conn)
    if book_authors.empty:
        st.warning(f"No authors found for Book ID: {book_id}")
        if st.button("Close"):
            st.rerun()
        return

    # Initialize session state for expander states and previous checkbox states
    if 'expander_states' not in st.session_state:
        st.session_state.expander_states = {}
    if 'checkbox_states' not in st.session_state:
        st.session_state.checkbox_states = {}

    for _, row in book_authors.iterrows():
        author_id = row['author_id']
        author_position = row['author_position']
        # Use session state to track whether this author's expander is open
        expander_key = f"expander_{author_id}"
        if expander_key not in st.session_state.expander_states:
            st.session_state.expander_states[expander_key] = False  # Default to collapsed

        # Initialize previous checkbox states for this author
        if author_id not in st.session_state.checkbox_states:
            st.session_state.checkbox_states[author_id] = {
                'welcome_mail_sent': bool(row['welcome_mail_sent']),
                'author_details_sent': bool(row['author_details_sent']),
                'photo_recive': bool(row['photo_recive']),
                'id_proof_recive': bool(row['id_proof_recive']),
                'digital_book_sent': bool(row['digital_book_sent']),
                'cover_agreement_sent': bool(row['cover_agreement_sent']),
                'agreement_received': bool(row['agreement_received']),
                'printing_confirmation': bool(row['printing_confirmation'])
            }

        # Wrap each author in an expander
        with st.expander(f"📖 {row['name']} (ID: {author_id}) Position: {author_position}", expanded=st.session_state.expander_states[expander_key]):
            # Display author details
            with st.container():
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**📌 Author ID:** {row['author_id']}")
                    st.markdown(f"**👤 Name:** {row['name']}")
                with col2:
                    st.markdown(f"**📧 Email:** {row['email'] or 'N/A'}")
                    st.markdown(f"**📞 Phone:** {row['phone'] or 'N/A'}")

                # Tabs for organizing fields
                tab_titles = ["Checklists", "Basic Info", "Delivery"]
                tab_objects = st.tabs(tab_titles)
                
                # Checklists tab (no form, no save button)
                with tab_objects[0]:
                    col5, col6 = st.columns(2)
                    with col5:
                        updates_checklist = {}
                        updates_checklist['welcome_mail_sent'] = st.checkbox(
                            "📧 Welcome Mail Sent",
                            value=bool(row['welcome_mail_sent']),
                            help="Check if the welcome email has been sent.",
                            key=f"welcome_mail_sent_{row['id']}"
                        )
                        if updates_checklist['welcome_mail_sent'] != st.session_state.checkbox_states[author_id]['welcome_mail_sent']:
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "updated checklist",
                                f"Book ID: {book_id}, Author ID: {author_id}, Welcome Mail Sent changed to '{updates_checklist['welcome_mail_sent']}'"
                            )
                            st.session_state.checkbox_states[author_id]['welcome_mail_sent'] = updates_checklist['welcome_mail_sent']
                            # Update database for checklist
                            update_book_authors(row['id'], {'welcome_mail_sent': int(updates_checklist['welcome_mail_sent'])}, conn)

                        updates_checklist['author_details_sent'] = st.checkbox(
                            "📥 Author Details Received",
                            value=bool(row['author_details_sent']),
                            help="Check if the author's details have been sent.",
                            key=f"author_details_sent_{row['id']}"
                        )
                        if updates_checklist['author_details_sent'] != st.session_state.checkbox_states[author_id]['author_details_sent']:
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "updated checklist",
                                f"Book ID: {book_id}, Author ID: {author_id}, Author Details Received changed to '{updates_checklist['author_details_sent']}'"
                            )
                            st.session_state.checkbox_states[author_id]['author_details_sent'] = updates_checklist['author_details_sent']
                            update_book_authors(row['id'], {'author_details_sent': int(updates_checklist['author_details_sent'])}, conn)

                        updates_checklist['photo_recive'] = st.checkbox(
                            "📷 Photo Received",
                            value=bool(row['photo_recive']),
                            help="Check if the author's photo has been received.",
                            key=f"photo_recive_{row['id']}"
                        )
                        if updates_checklist['photo_recive'] != st.session_state.checkbox_states[author_id]['photo_recive']:
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "updated checklist",
                                f"Book ID: {book_id}, Author ID: {author_id}, Photo Received changed to '{updates_checklist['photo_recive']}'"
                            )
                            st.session_state.checkbox_states[author_id]['photo_recive'] = updates_checklist['photo_recive']
                            update_book_authors(row['id'], {'photo_recive': int(updates_checklist['photo_recive'])}, conn)

                        updates_checklist['id_proof_recive'] = st.checkbox(
                            "🆔 ID Proof Received",
                            value=bool(row['id_proof_recive']),
                            help="Check if the author's ID proof has been received.",
                            key=f"id_proof_recive_{row['id']}"
                        )
                        if updates_checklist['id_proof_recive'] != st.session_state.checkbox_states[author_id]['id_proof_recive']:
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "updated checklist",
                                f"Book ID: {book_id}, Author ID: {author_id}, ID Proof Received changed to '{updates_checklist['id_proof_recive']}'"
                            )
                            st.session_state.checkbox_states[author_id]['id_proof_recive'] = updates_checklist['id_proof_recive']
                            update_book_authors(row['id'], {'id_proof_recive': int(updates_checklist['id_proof_recive'])}, conn)

                    with col6:    
                        updates_checklist['digital_book_sent'] = st.checkbox(
                            "📤 Digital Book Sent",
                            value=bool(row['digital_book_sent']),
                            help="Check if the digital book has been sent.",
                            key=f"digital_book_sent_{row['id']}"
                        )
                        if updates_checklist['digital_book_sent'] != st.session_state.checkbox_states[author_id]['digital_book_sent']:
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "updated checklist",
                                f"Book ID: {book_id}, Author ID: {author_id}, Digital Book Sent changed to '{updates_checklist['digital_book_sent']}'"
                            )
                            st.session_state.checkbox_states[author_id]['digital_book_sent'] = updates_checklist['digital_book_sent']
                            update_book_authors(row['id'], {'digital_book_sent': int(updates_checklist['digital_book_sent'])}, conn)

                        updates_checklist['cover_agreement_sent'] = st.checkbox(
                            "📜 Cover Agreement Sent",
                            value=bool(row['cover_agreement_sent']),
                            help="Check if the cover agreement has been sent.",
                            key=f"cover_agreement_sent_{row['id']}"
                        )
                        if updates_checklist['cover_agreement_sent'] != st.session_state.checkbox_states[author_id]['cover_agreement_sent']:
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "updated checklist",
                                f"Book ID: {book_id}, Author ID: {author_id}, Cover Agreement Sent changed to '{updates_checklist['cover_agreement_sent']}'"
                            )
                            st.session_state.checkbox_states[author_id]['cover_agreement_sent'] = updates_checklist['cover_agreement_sent']
                            update_book_authors(row['id'], {'cover_agreement_sent': int(updates_checklist['cover_agreement_sent'])}, conn)

                        updates_checklist['agreement_received'] = st.checkbox(
                            "✍🏻 Agreement Received",
                            value=bool(row['agreement_received']),
                            help="Check if the agreement has been received.",
                            key=f"agreement_received_{row['id']}"
                        )
                        if updates_checklist['agreement_received'] != st.session_state.checkbox_states[author_id]['agreement_received']:
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "updated checklist",
                                f"Book ID: {book_id}, Author ID: {author_id}, Agreement Received changed to '{updates_checklist['agreement_received']}'"
                            )
                            st.session_state.checkbox_states[author_id]['agreement_received'] = updates_checklist['agreement_received']
                            update_book_authors(row['id'], {'agreement_received': int(updates_checklist['agreement_received'])}, conn)

                        updates_checklist['printing_confirmation'] = st.checkbox(
                            "🖨️ Printing Confirmation Received",
                            value=bool(row['printing_confirmation']),
                            help="Check if printing confirmation has been received.",
                            key=f"printing_confirmation_{row['id']}"
                        )
                        if updates_checklist['printing_confirmation'] != st.session_state.checkbox_states[author_id]['printing_confirmation']:
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "updated checklist",
                                f"Book ID: {book_id}, Author ID: {author_id}, Printing Confirmation Received changed to '{updates_checklist['printing_confirmation']}'"
                            )
                            st.session_state.checkbox_states[author_id]['printing_confirmation'] = updates_checklist['printing_confirmation']
                            update_book_authors(row['id'], {'printing_confirmation': int(updates_checklist['printing_confirmation'])}, conn)

                # Form for Basic Info and Delivery tabs
                with st.form(key=f"edit_form_{row['id']}", border=False):
                    updates = {}

                    # Tab 1: Basic Info
                    with tab_objects[1]:
                        col3, col4 = st.columns(2)
                        with col3:
                            existing_positions = [author['author_position'] for _, author in book_authors.iterrows() if author['id'] != row['id']]
                            available_positions = [pos for pos in ["1st", "2nd", "3rd", "4th"] if pos not in existing_positions]
                            updates['author_position'] = st.selectbox(
                                "Author Position",
                                available_positions,
                                index=available_positions.index(row['author_position']) if row['author_position'] in available_positions else 0,
                                help="Select the author's position in the book.",
                                key=f"author_position_{row['id']}"
                            )
                            updates['number_of_books'] = st.number_input(
                                "Number of Books",
                                min_value=0,
                                step=1,
                                value=int(row['number_of_books'] or 0),
                                help="Enter the number of books to deliver.",
                                key=f"number_of_books_{row['id']}"
                            )
                        with col4:
                            updates['corresponding_agent'] = st.text_input(
                                "Corresponding Agent",
                                value=row['corresponding_agent'] or "",
                                help="Enter the name of the corresponding agent.",
                                key=f"corresponding_agent_{row['id']}"
                            )
                            updates['publishing_consultant'] = st.text_input(
                                "Publishing Consultant",
                                value=row['publishing_consultant'] or "",
                                help="Enter the name of the publishing consultant.",
                                key=f"publishing_consultant_{row['id']}"
                            )
                        updates['delivery_address'] = st.text_area(
                            "Delivery Address",
                            value=row['delivery_address'] or "",
                            height=100,
                            help="Enter the delivery address.",
                            key=f"delivery_address_{row['id']}"
                        )

                    # Tab 3: Delivery
                    with tab_objects[2]:
                        if print_status == 0:
                            st.warning("⚠️ Delivery details are disabled because printing status is not confirmed.")
                        else:
                            col7, col8 = st.columns(2)
                            with col7:
                                updates['delivery_date'] = st.date_input(
                                    "Delivery Date",
                                    value=row['delivery_date'],
                                    help="Enter the delivery date.",
                                    key=f"delivery_date_{row['id']}"
                                )
                                updates['tracking_id'] = st.text_input(
                                    "Tracking ID",
                                    value=row['tracking_id'] or "",
                                    help="Enter the tracking ID for the delivery.",
                                    key=f"tracking_id_{row['id']}"
                                )
                            with col8:
                                updates['delivery_charge'] = st.number_input(
                                    "Delivery Charge (₹)",
                                    min_value=0.0,
                                    step=0.01,
                                    value=float(row['delivery_charge'] or 0.0),
                                    help="Enter the delivery charge in INR.",
                                    key=f"delivery_charge_{row['id']}"
                                )
                                updates['delivery_vendor'] = st.text_input(
                                    "Delivery Vendor",
                                    value=row['delivery_vendor'] or "",
                                    help="Enter the name of the delivery vendor.",
                                    key=f"delivery_vendor_{row['id']}"
                                )

                    # Submit and Remove buttons
                    col_submit, col_remove = st.columns([8, 1])
                    with col_submit:
                        if st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary"):
                            # Convert boolean values to integers for database
                            for key in updates:
                                if isinstance(updates[key], bool):
                                    updates[key] = int(updates[key])

                            # Track changes for logging
                            changes = []
                            original_row = row.to_dict()
                            for key, value in updates.items():
                                original_value = original_row.get(key)
                                if key == 'delivery_date' and original_value:
                                    original_value = pd.Timestamp(original_value).date()
                                if value != original_value:
                                    changes.append(f"{key.replace('_', ' ').title()} changed from '{original_value}' to '{value}'")

                            try:
                                with st.spinner("Saving changes..."):
                                    import time
                                    time.sleep(1)
                                    update_book_authors(row['id'], updates, conn)
                                    # Log save action
                                    if changes:
                                        log_activity(
                                            conn,
                                            st.session_state.user_id,
                                            st.session_state.username,
                                            st.session_state.session_id,
                                            "updated author details",
                                            f"Book ID: {book_id}, Author ID: {author_id}, {', '.join(changes)}"
                                        )
                                    st.cache_data.clear()
                                    st.success(f"✔️ Updated details for {row['name']} (Author ID: {author_id})")
                            except Exception as e:
                                st.error(f"❌ Error updating author details: {e}")

                    with col_remove:
                        confirmation_key = f"confirm_remove_{row['id']}"
                        if confirmation_key not in st.session_state:
                            st.session_state[confirmation_key] = False

                        if st.form_submit_button("🗑️", use_container_width=True, type="secondary", help=f"Remove {row['name']} from this book"):
                            st.session_state[confirmation_key] = True

                # Confirmation form for removal
                if st.session_state[confirmation_key]:
                    with st.form(f"confirm_form_{row['id']}", border=False):
                        st.warning(f"Are you sure you want to remove {row['name']} (Author ID: {row['author_id']}) from Book ID: {book_id}?")
                        col_confirm, col_cancel = st.columns(2)
                        with col_confirm:
                            if st.form_submit_button("Yes, Remove", use_container_width=True, type="primary"):
                                try:
                                    with st.spinner("Removing author..."):
                                        import time
                                        time.sleep(1)
                                        delete_book_author(row['id'], conn)
                                        # Log remove action
                                        log_activity(
                                            conn,
                                            st.session_state.user_id,
                                            st.session_state.username,
                                            st.session_state.session_id,
                                            "removed author",
                                            f"Book ID: {book_id}, Author ID: {author_id}, Name: {row['name']}"
                                        )
                                        st.cache_data.clear()
                                        st.success(f"✔️ Removed {row['name']} (Author ID: {author_id}) from this book")
                                        st.session_state[confirmation_key] = False
                                except Exception as e:
                                    st.error(f"❌ Error removing author: {e}")
                        with col_cancel:
                            if st.form_submit_button("Cancel", use_container_width=True):
                                st.session_state[confirmation_key] = False

    
    publisher = book_details['publisher'].iloc[0] if 'publisher' in book_details else None

    import time  # For spinner delay

    # Assumed helper function (adjusted for fix)
    def is_editor_complete(editor):
        # Allow editor with at least name and position for existing chapters
        return bool(editor.get("name") and editor.get("author_position"))

    if publisher == "AG Volumes":
        chapters = fetch_chapters(book_id, conn)
        existing_chapter_count = len(chapters)

        if existing_chapter_count >= MAX_CHAPTERS:
            st.warning("⚠️ This book already has the maximum number of chapters (30). No more chapters can be added.")
        else:
            # Initialize or refresh session state for editing existing chapters
            if "edit_chapters" not in st.session_state:
                st.session_state.edit_chapters = {}
            
            # Sync edit_chapters with current chapters, forcing initialization to avoid KeyError
            MAX_EDITORS_PER_CHAPTER = 4
            for _, chapter in chapters.iterrows():
                chapter_id = chapter['chapter_id']
                # Always initialize or update to ensure "editors" key exists
                editors = [
                    {
                        "author_id": editor['author_id'],
                        "author_position": editor['author_position'],
                        "name": editor['name'],
                        "email": editor['email'],
                        "phone": editor['phone'],
                        "corresponding_agent": editor['corresponding_agent'] or "",
                        "publishing_consultant": editor['publishing_consultant'] or ""
                    }
                    for _, editor in fetch_chapter_editors(chapter['chapter_id'], conn).iterrows()
                ]
                # Ensure four editor slots
                while len(editors) < MAX_EDITORS_PER_CHAPTER:
                    editors.append({
                        "author_id": None,
                        "author_position": None,
                        "name": "",
                        "email": "",
                        "phone": "",
                        "corresponding_agent": "",
                        "publishing_consultant": ""
                    })
                st.session_state.edit_chapters[chapter_id] = {
                    "chapter_title": chapter['chapter_title'],
                    "chapter_number": str(chapter['chapter_number']),
                    "editors": editors
                }

            # Display existing chapters in expanders
            if existing_chapter_count > 0:
                st.markdown(f"#### Existing Chapters ({existing_chapter_count})")
                for _, chapter in chapters.iterrows():
                    chapter_id = chapter['chapter_id']
                    edit_data = st.session_state.edit_chapters[chapter_id]
                    with st.expander(f"Chapter {edit_data['chapter_number']}: {edit_data['chapter_title'] or 'Untitled'}", expanded=False):
                        edit_data["chapter_title"] = st.text_input(
                            "Chapter Title",
                            value=edit_data["chapter_title"],
                            key=f"edit_chapter_title_{chapter_id}",
                            placeholder="Enter chapter title..."
                        )

                        # Fixed tab labels to "Editor" for consistency
                        editor_tabs = st.tabs(["Writer 1", "Writer 2", "Writer 3", "Writer 4"])
                        for j, editor_tab in enumerate(editor_tabs):
                            with editor_tab:
                                editor = edit_data["editors"][j]
                                all_authors = get_all_authors(conn)
                                author_options = ["Select Existing Editor"] + [f"{a.name} (ID: {a.author_id})" for a in all_authors]
                                selected_editor = st.selectbox(
                                    "Select Writer",  # Changed from "Select Writer"
                                    author_options,
                                    index=author_options.index(f"{editor['name']} (ID: {editor['author_id']})") if editor['author_id'] and f"{editor['name']} (ID: {editor['author_id']})" in author_options else 0,
                                    key=f"edit_chapter_{chapter_id}_editor_select_{j}"
                                )

                                if selected_editor != "Select Existing Editor" and selected_editor:
                                    selected_editor_id = int(selected_editor.split('(ID: ')[1][:-1])
                                    selected_editor_details = next((a for a in all_authors if a.author_id == selected_editor_id), None)
                                    if selected_editor_details:
                                        editor.update({
                                            "name": selected_editor_details.name,
                                            "email": selected_editor_details.email,
                                            "phone": selected_editor_details.phone,
                                            "author_id": selected_editor_id
                                        })
                                elif selected_editor == "Select Existing Editor":
                                    editor["author_id"] = None
                                    editor.update({
                                        "name": "",
                                        "email": "",
                                        "phone": "",
                                        "corresponding_agent": "",
                                        "publishing_consultant": ""
                                    })

                                col1, col2 = st.columns(2)
                                editor["name"] = col1.text_input(
                                    "Name",
                                    value=editor["name"],
                                    key=f"edit_chapter_{chapter_id}_editor_name_{j}"
                                )
                                available_positions = ["1st", "2nd", "3rd", "4th"]
                                current_positions = [e["author_position"] for k, e in enumerate(edit_data["editors"]) if k != j and e["author_position"]]
                                available_positions = [p for p in available_positions if p not in current_positions]
                                editor["author_position"] = col2.selectbox(
                                    "Position",
                                    available_positions,
                                    index=available_positions.index(editor["author_position"]) if editor["author_position"] in available_positions else 0,
                                    key=f"edit_chapter_{chapter_id}_editor_position_{j}"
                                )

                                col3, col4 = st.columns(2)
                                editor["email"] = col3.text_input(
                                    "Email",
                                    value=editor["email"],
                                    key=f"edit_chapter_{chapter_id}_editor_email_{j}"
                                )
                                editor["phone"] = col4.text_input(
                                    "Phone",
                                    value=editor["phone"],
                                    key=f"edit_chapter_{chapter_id}_editor_phone_{j}"
                                )

                                col5, col6 = st.columns(2)
                                unique_agents, unique_consultants = get_unique_agents_and_consultants(conn)
                                agent_options = ["Select Agent"] + unique_agents + ["Add New..."]
                                agent_index = agent_options.index(editor["corresponding_agent"]) if editor["corresponding_agent"] in unique_agents else 0
                                selected_agent = col5.selectbox(
                                    "Corresponding Agent",
                                    agent_options,
                                    index=agent_index,
                                    key=f"edit_chapter_{chapter_id}_editor_agent_{j}"
                                )
                                if selected_agent == "Add New...":
                                    editor["corresponding_agent"] = col5.text_input(
                                        "New Agent Name",
                                        value=editor["corresponding_agent"],
                                        key=f"edit_chapter_{chapter_id}_editor_agent_input_{j}"
                                    )
                                elif selected_agent != "Select Agent":
                                    editor["corresponding_agent"] = selected_agent
                                else:
                                    editor["corresponding_agent"] = ""

                                consultant_options = ["Select Consultant"] + unique_consultants + ["Add New..."]
                                consultant_index = consultant_options.index(editor["publishing_consultant"]) if editor["publishing_consultant"] in unique_consultants else 0
                                selected_consultant = col6.selectbox(
                                    "Publishing Consultant",
                                    consultant_options,
                                    index=consultant_index,
                                    key=f"edit_chapter_{chapter_id}_editor_consultant_{j}"
                                )
                                if selected_consultant == "Add New...":
                                    editor["publishing_consultant"] = col6.text_input(
                                        "New Consultant Name",
                                        value=editor["publishing_consultant"],
                                        key=f"edit_chapter_{chapter_id}_editor_consultant_input_{j}"
                                    )
                                elif selected_consultant != "Select Consultant":
                                    editor["publishing_consultant"] = selected_consultant
                                else:
                                    editor["publishing_consultant"] = ""

                            # Ensure editor data is updated in session state
                            edit_data["editors"][j] = editor

                        col_save, col_delete = st.columns([3, 1])
                        with col_save:
                            if st.button("Save Chapter", key=f"save_chapter_{chapter_id}"):
                                with st.spinner("Saving chapter..."):
                                    time.sleep(1)  # 2-second delay for UX
                                    errors = []
                                    if not edit_data["chapter_title"]:
                                        errors.append("Chapter title is required.")

                                    active_editors = [e for e in edit_data["editors"] if is_editor_complete(e)]
                                    if not active_editors:
                                        errors.append("At least one editor is required with name and position.")
                                    else:
                                        existing_editor_ids = []
                                        for j, editor in enumerate(active_editors):
                                            is_valid, error = validate_editor(editor, [], existing_editor_ids, edit_data["editors"], j)
                                            if not is_valid:
                                                errors.append(f"Editor {j+1}: {error}")
                                            else:
                                                existing_editor_ids.append(editor["author_id"] or editor["name"])

                                    if errors:
                                        for error in errors:
                                            st.error(f"❌ {error}")
                                    else:
                                        try:
                                            with conn.session as s:
                                                s.begin()
                                                # Update chapter (keep chapter_number unchanged)
                                                s.execute(
                                                    text("""
                                                        UPDATE chapters
                                                        SET chapter_title = :chapter_title
                                                        WHERE chapter_id = :chapter_id
                                                    """),
                                                    {
                                                        "chapter_id": chapter_id,
                                                        "chapter_title": edit_data["chapter_title"]
                                                    }
                                                )
                                                # Delete existing editors
                                                s.execute(
                                                    text("DELETE FROM chapter_editors WHERE chapter_id = :chapter_id"),
                                                    {"chapter_id": chapter_id}
                                                )
                                                # Insert updated editors
                                                for editor in active_editors:
                                                    editor_id = editor["author_id"]
                                                    if not editor_id:
                                                        # Insert new author if needed
                                                        s.execute(
                                                            text("""
                                                                INSERT INTO authors (name, email, phone)
                                                                VALUES (:name, :email, :phone)
                                                            """),
                                                            {
                                                                "name": editor["name"],
                                                                "email": editor["email"] or None,
                                                                "phone": editor["phone"] or None
                                                            }
                                                        )
                                                        editor_id = s.execute(text("SELECT LAST_INSERT_ID();")).scalar()
                                                        if not editor_id:
                                                            raise Exception("Failed to retrieve author_id.")
                                                    s.execute(
                                                        text("""
                                                            INSERT INTO chapter_editors (chapter_id, author_id, author_position, corresponding_agent, publishing_consultant)
                                                            VALUES (:chapter_id, :author_id, :author_position, :corresponding_agent, :publishing_consultant)
                                                        """),
                                                        {
                                                            "chapter_id": chapter_id,
                                                            "author_id": editor_id,
                                                            "author_position": editor["author_position"],
                                                            "corresponding_agent": editor["corresponding_agent"] or None,
                                                            "publishing_consultant": editor["publishing_consultant"] or None
                                                        }
                                                    )
                                                s.commit()
                                            st.success("✔️ Chapter updated successfully!")
                                            st.cache_data.clear()
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Error updating chapter: {e}")
                                            with conn.session as s:
                                                s.rollback()

                        with col_delete:
                            if st.button("Delete Chapter", key=f"delete_chapter_{chapter_id}"):
                                with st.spinner("Deleting chapter..."):
                                    time.sleep(1)  # 2-second delay for UX
                                    try:
                                        with conn.session as s:
                                            s.begin()
                                            s.execute(
                                                text("DELETE FROM chapter_editors WHERE chapter_id = :chapter_id"),
                                                {"chapter_id": chapter_id}
                                            )
                                            s.execute(
                                                text("DELETE FROM chapters WHERE chapter_id = :chapter_id"),
                                                {"chapter_id": chapter_id}
                                            )
                                            s.commit()
                                        del st.session_state.edit_chapters[chapter_id]
                                        st.success("✔️ Chapter deleted successfully!")
                                        st.cache_data.clear()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Error deleting chapter: {e}")
                                        with conn.session as s:
                                            s.rollback()

            # New chapter form
            st.markdown("#### Add New Chapter")
            # Calculate smallest available chapter number
            existing_numbers = sorted([int(c["chapter_number"]) for _, c in chapters.iterrows()])
            next_number = 1
            for num in existing_numbers:
                if num != next_number:
                    break
                next_number += 1
            
            # Initialize new_chapters with exactly four editors
            if "new_chapters" not in st.session_state:
                st.session_state.new_chapters = [
                    {
                        "chapter_title": "",
                        "chapter_number": str(next_number),
                        "editors": [
                            {
                                "author_id": None,
                                "author_position": None,
                                "name": "",
                                "email": "",
                                "phone": "",
                                "corresponding_agent": "",
                                "publishing_consultant": ""
                            }
                            for _ in range(MAX_EDITORS_PER_CHAPTER)
                        ]
                    }
                ]

            # Ensure new_chapters always has four editors
            def ensure_editor_fields(editor):
                default_editor = {
                    "name": "", "email": "", "phone": "", "author_id": None, "author_position": None,
                    "corresponding_agent": "", "publishing_consultant": ""
                }
                for key, default_value in default_editor.items():
                    if key not in editor:
                        editor[key] = default_value
                return editor

            # Force four editors in new_chapters
            for chapter in st.session_state.new_chapters:
                chapter["editors"] = [
                    ensure_editor_fields(e) for e in chapter["editors"]
                ]
                while len(chapter["editors"]) < MAX_EDITORS_PER_CHAPTER:
                    chapter["editors"].append({
                        "author_id": None,
                        "author_position": None,
                        "name": "",
                        "email": "",
                        "phone": "",
                        "corresponding_agent": "",
                        "publishing_consultant": ""
                    })
                if len(chapter["editors"]) > MAX_EDITORS_PER_CHAPTER:
                    chapter["editors"] = chapter["editors"][:MAX_EDITORS_PER_CHAPTER]

            all_authors = get_all_authors(conn)
            author_options = ["Add New Editor"] + [f"{a.name} (ID: {a.author_id})" for a in all_authors]
            unique_agents, unique_consultants = get_unique_agents_and_consultants(conn)
            agent_options = ["Select Agent"] + unique_agents + ["Add New..."]
            consultant_options = ["Select Consultant"] + unique_consultants + ["Add New..."]

            chapter = st.session_state.new_chapters[0]
            with st.expander(f"Chapter {chapter['chapter_number']}: New Chapter", expanded=False):
                chapter["chapter_title"] = st.text_input(
                    "Chapter Title",
                    chapter["chapter_title"],
                    key="new_chapter_title",
                    placeholder="Enter chapter title..."
                )

                # Fixed tab labels to "Editor" for consistency
                editor_tabs = st.tabs(["Writer 1", "Writer 2", "Writer 3", "Writer 4"])
                for j, editor_tab in enumerate(editor_tabs):
                    with editor_tab:
                        editor = chapter["editors"][j]
                        selected_editor = st.selectbox(
                            "Select Writer",  # Changed from "Select Writer"
                            author_options,
                            index=author_options.index(f"{editor['name']} (ID: {editor['author_id']})") if editor['author_id'] and f"{editor['name']} (ID: {editor['author_id']})" in author_options else 0,
                            key=f"new_chapter_editor_select_{j}"
                        )

                        if selected_editor != "Add New Editor" and selected_editor:
                            selected_editor_id = int(selected_editor.split('(ID: ')[1][:-1])
                            selected_editor_details = next((a for a in all_authors if a.author_id == selected_editor_id), None)
                            if selected_editor_details:
                                editor.update({
                                    "name": selected_editor_details.name,
                                    "email": selected_editor_details.email,
                                    "phone": selected_editor_details.phone,
                                    "author_id": selected_editor_id,
                                    "corresponding_agent": "",
                                    "publishing_consultant": ""
                                })
                        elif selected_editor == "Add New Editor":
                            editor["author_id"] = None
                            editor.update({
                                "name": editor.get("name", ""),
                                "email": editor.get("email", ""),
                                "phone": editor.get("phone", ""),
                                "corresponding_agent": editor.get("corresponding_agent", ""),
                                "publishing_consultant": editor.get("publishing_consultant", "")
                            })

                        col1, col2 = st.columns(2)
                        editor["name"] = col1.text_input(
                            "Name",
                            editor["name"],
                            key=f"new_chapter_editor_name_{j}"
                        )
                        available_positions = ["1st", "2nd", "3rd", "4th"]
                        current_positions = [e["author_position"] for k, e in enumerate(chapter["editors"]) if k != j and e["author_position"]]
                        available_positions = [p for p in available_positions if p not in current_positions]
                        editor["author_position"] = col2.selectbox(
                            "Position",
                            available_positions,
                            index=available_positions.index(editor["author_position"]) if editor["author_position"] in available_positions else 0,
                            key=f"new_chapter_editor_position_{j}"
                        )

                        col3, col4 = st.columns(2)
                        editor["email"] = col3.text_input(
                            "Email",
                            editor["email"],
                            key=f"new_chapter_editor_email_{j}"
                        )
                        editor["phone"] = col4.text_input(
                            "Phone",
                            editor["phone"],
                            key=f"new_chapter_editor_phone_{j}"
                        )

                        col5, col6 = st.columns(2)
                        agent_index = 0
                        if editor["corresponding_agent"] and editor["corresponding_agent"] in unique_agents:
                            try:
                                agent_index = agent_options.index(editor["corresponding_agent"])
                            except ValueError:
                                agent_index = 0
                        selected_agent = col5.selectbox(
                            "Corresponding Agent",
                            agent_options,
                            index=agent_index,
                            key=f"new_chapter_editor_agent_{j}"
                        )
                        if selected_agent == "Add New...":
                            editor["corresponding_agent"] = col5.text_input(
                                "New Agent Name",
                                value=editor["corresponding_agent"],
                                key=f"new_chapter_editor_agent_input_{j}"
                            )
                        elif selected_agent != "Select Agent":
                            editor["corresponding_agent"] = selected_agent
                        else:
                            editor["corresponding_agent"] = ""

                        consultant_index = 0
                        if editor["publishing_consultant"] and editor["publishing_consultant"] in unique_consultants:
                            try:
                                consultant_index = consultant_options.index(editor["publishing_consultant"])
                            except ValueError:
                                agent_index = 0
                        selected_consultant = col6.selectbox(
                            "Publishing Consultant",
                            consultant_options,
                            index=consultant_index,
                            key=f"new_chapter_editor_consultant_{j}"
                        )
                        if selected_consultant == "Add New...":
                            editor["publishing_consultant"] = col6.text_input(
                                "New Consultant Name",
                                value=editor["publishing_consultant"],
                                key=f"new_chapter_editor_consultant_input_{j}"
                            )
                        elif selected_consultant != "Select Consultant":
                            editor["publishing_consultant"] = selected_consultant
                        else:
                            editor["publishing_consultant"] = ""

                    # Ensure editor data is updated in session state
                    chapter["editors"][j] = editor

            # Save new chapter
            col_save, col_cancel = st.columns([7, 1])
            with col_save:
                if st.button("Add Chapter and Editors", key="add_chapters", type="primary"):
                    with st.spinner("Saving chapter..."):
                        time.sleep(1)  # 2-second delay for UX
                        errors = []
                        chapter = st.session_state.new_chapters[0]
                        existing_numbers = [int(c["chapter_number"]) for _, c in chapters.iterrows()]
                        if int(chapter["chapter_number"]) in existing_numbers:
                            errors.append(f"Chapter number {chapter['chapter_number']} is already used.")
                        if not chapter["chapter_title"]:
                            errors.append("Chapter: Title is required.")

                        active_editors = [e for e in chapter["editors"] if is_editor_complete(e)]
                        if not active_editors:
                            errors.append("Chapter: At least one editor is required with name and position.")
                        else:
                            existing_editor_ids = []
                            for j, editor in enumerate(active_editors):
                                is_valid, error = validate_editor(editor, [], existing_editor_ids, chapter["editors"], j)
                                if not is_valid:
                                    errors.append(f"Editor {j+1}: {error}")
                                else:
                                    existing_editor_ids.append(editor["author_id"] or editor["name"])

                        if errors:
                            for error in errors:
                                st.error(f"❌ {error}")
                        else:
                            try:
                                with conn.session as s:
                                    s.begin()
                                    s.execute(
                                        text("""
                                            INSERT INTO chapters (book_id, chapter_title, chapter_number)
                                            VALUES (:book_id, :chapter_title, :chapter_number)
                                        """),
                                        {
                                            "book_id": book_id,
                                            "chapter_title": chapter["chapter_title"],
                                            "chapter_number": int(chapter["chapter_number"])
                                        }
                                    )
                                    chapter_id = s.execute(text("SELECT LAST_INSERT_ID();")).scalar()
                                    if not chapter_id:
                                        raise Exception("Failed to retrieve chapter_id.")

                                    for editor in active_editors:
                                        editor_id = editor["author_id"]
                                        if not editor_id:
                                            s.execute(
                                                text("""
                                                    INSERT INTO authors (name, email, phone)
                                                    VALUES (:name, :email, :phone)
                                                """),
                                                {
                                                    "name": editor["name"],
                                                    "email": editor["email"] or None,
                                                    "phone": editor["phone"] or None
                                                }
                                            )
                                            editor_id = s.execute(text("SELECT LAST_INSERT_ID();")).scalar()
                                            if not editor_id:
                                                raise Exception("Failed to retrieve author_id.")

                                        s.execute(
                                            text("""
                                                INSERT INTO chapter_editors (chapter_id, author_id, author_position, corresponding_agent, publishing_consultant)
                                                VALUES (:chapter_id, :author_id, :author_position, :corresponding_agent, :publishing_consultant)
                                            """),
                                            {
                                                "chapter_id": chapter_id,
                                                "author_id": editor_id,
                                                "author_position": editor["author_position"],
                                                "corresponding_agent": editor["corresponding_agent"] or None,
                                                "publishing_consultant": editor["publishing_consultant"] or None
                                            }
                                        )
                                    s.commit()
                                st.success("✔️ Chapter and editors added successfully!")
                                st.cache_data.clear()
                                # Calculate next smallest available number
                                chapters = fetch_chapters(book_id, conn)
                                existing_numbers = sorted([int(c["chapter_number"]) for _, c in chapters.iterrows()])
                                next_number = 1
                                for num in existing_numbers:
                                    if num != next_number:
                                        break
                                    next_number += 1
                                st.session_state.new_chapters = [
                                    {
                                        "chapter_title": "",
                                        "chapter_number": str(next_number),
                                        "editors": [
                                            {
                                                "author_id": None,
                                                "author_position": None,
                                                "name": "",
                                                "email": "",
                                                "phone": "",
                                                "corresponding_agent": "",
                                                "publishing_consultant": ""
                                            }
                                            for _ in range(MAX_EDITORS_PER_CHAPTER)
                                        ]
                                    }
                                ]
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error adding chapter/editors: {e}")
                                with conn.session as s:
                                    s.rollback()

            with col_cancel:
                if st.button("Cancel", key="cancel_chapters"):
                    del st.session_state.new_chapters
                    st.rerun()

    else:
        # Fetch current book details and authors
        book_authors = fetch_book_authors(book_id, conn)
        existing_author_count = len(book_authors)

        # Fetch current author_type from books table
        with conn.session as s:
            result = s.execute(
                text("SELECT author_type FROM books WHERE book_id = :book_id"),
                {"book_id": book_id}
            ).fetchone()
            current_author_type = result[0] if result else "Multiple"

        # Author type selection
        st.markdown("### Change Author Type")
        author_types = ["Single", "Double", "Triple", "Multiple"]
        selected_author_type = st.radio(
            "Author Type",
            author_types,
            index=author_types.index(current_author_type),
            key="author_type_selection",
            horizontal=True,
            label_visibility="collapsed" 
        )

        # Determine max authors based on selected author type
        max_authors_allowed = {
            "Single": 1,
            "Double": 2,
            "Triple": 3,
            "Multiple": 4
        }.get(selected_author_type, 4)

        # Validate author type change
        if selected_author_type != current_author_type:
            if existing_author_count > max_authors_allowed:
                st.error(f"❌ Cannot change to {selected_author_type} author type. Current {existing_author_count} author(s) exceed the limit of {max_authors_allowed}. Please remove excess authors first.")
                if st.button("Revert to Current Type"):
                    st.rerun()
                return
            else:
                # Update author_type in books table
                try:
                    with conn.session as s:
                        s.execute(
                            text("UPDATE books SET author_type = :author_type WHERE book_id = :book_id"),
                            {"author_type": selected_author_type, "book_id": book_id}
                        )
                        s.commit()
                        st.success(f"✔️ Author type changed to {selected_author_type}")
                        log_activity(
                            conn,
                            st.session_state.user_id,
                            st.session_state.username,
                            st.session_state.session_id,
                            "changed author type",
                            f"Book ID: {book_id}, New Author Type: {selected_author_type}"
                        )
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error updating author type: {e}")
                    return

        available_slots = max_authors_allowed - existing_author_count
        if available_slots <= 0:
            st.warning(f"⚠️ Maximum number of authors ({max_authors_allowed}) reached for {selected_author_type} author type.")
            if st.button("Close"): st.rerun()
            return

        if existing_author_count == 0:
            st.warning(f"⚠️ No authors found for Book ID: {book_id}")

        # Initialize session state for new authors
        if "new_authors" not in st.session_state or len(st.session_state.new_authors) != available_slots:
            st.session_state.new_authors = initialize_new_authors(available_slots)

        def validate_author(author, existing_positions, existing_author_ids, all_new_authors, index, author_type):
            """Validate an author's details."""
            if not author["name"]: return False, "Author name is required."
            if not author["email"] or not validate_email(author["email"]): return False, "Invalid email format."
            if not author["phone"] or not validate_phone(author["phone"]): return False, "Invalid phone number format."
            if not author["author_position"]: return False, "Author position is required."
            if not author["publishing_consultant"]: return False, "Publishing consultant is required."

            if author["author_position"] in existing_positions or \
            author["author_position"] in [a["author_position"] for i, a in enumerate(all_new_authors) if i != index and a["author_position"]]:
                return False, f"Position '{author['author_position']}' is already taken."

            if author["author_id"] and author["author_id"] in existing_author_ids + \
            [a["author_id"] for i, a in enumerate(all_new_authors) if i != index and a["author_id"]]:
                return False, f"Author '{author['name']}' (ID: {author['author_id']}) is already linked."

            # Validate number of authors based on author_type
            total_authors = existing_author_count + sum(1 for a in all_new_authors if a["name"])
            max_allowed = {"Single": 1, "Double": 2, "Triple": 3, "Multiple": 4}.get(author_type, 4)
            if total_authors > max_allowed:
                return False, f"Too many authors. {author_type} allows up to {max_allowed} authors."

            return True, ""

        # Render author input forms
        st.markdown(f"### Add Up to {available_slots} New Authors")
        all_authors = get_all_authors(conn)
        author_options = ["Add New Author"] + [f"{a.name} (ID: {a.author_id})" for a in all_authors]
        unique_agents, unique_consultants = get_unique_agents_and_consultants(conn)
        agent_options = ["Select Agent"] + ["Add New..."] + unique_agents
        consultant_options = ["Select Consultant"] + ["Add New..."] + unique_consultants
        existing_positions = [author["author_position"] for _, author in book_authors.iterrows()]
        existing_author_ids = [author["author_id"] for _, author in book_authors.iterrows()]

        for i in range(available_slots):
            with st.expander(f"New Author {i+1}", expanded=False):
                disabled = existing_author_count + i >= max_authors_allowed
                if disabled:
                    st.warning(f"⚠️ Disabled: Maximum {max_authors_allowed} authors reached for {selected_author_type} mode.")

                selected_author = st.selectbox(
                    f"Select Author {i+1}",
                    author_options,
                    key=f"new_author_select_{i}",
                    disabled=disabled
                )

                if selected_author != "Add New Author" and selected_author and not disabled:
                    selected_author_id = int(selected_author.split('(ID: ')[1][:-1])
                    selected_author_details = next((a for a in all_authors if a.author_id == selected_author_id), None)
                    if selected_author_details:
                        st.session_state.new_authors[i].update({
                            "name": selected_author_details.name,
                            "email": selected_author_details.email,
                            "phone": selected_author_details.phone,
                            "author_id": selected_author_details.author_id
                        })
                elif selected_author == "Add New Author" and not disabled:
                    st.session_state.new_authors[i]["author_id"] = None

                col1, col2 = st.columns(2)
                st.session_state.new_authors[i]["name"] = col1.text_input(
                    f"Author Name {i+1}", st.session_state.new_authors[i]["name"], key=f"new_name_{i}",
                    disabled=disabled
                )
                available_positions = [pos for pos in ["1st", "2nd", "3rd", "4th"] if pos not in 
                                    (existing_positions + [a["author_position"] for j, a in enumerate(st.session_state.new_authors) if j != i and a["author_position"]])]
                st.session_state.new_authors[i]["author_position"] = col2.selectbox(
                    f"Position {i+1}",
                    available_positions,
                    key=f"new_author_position_{i}",
                    disabled=disabled or not available_positions
                ) if available_positions else st.error("❌ No available positions left.")

                col3, col4 = st.columns(2)
                st.session_state.new_authors[i]["phone"] = col3.text_input(
                    f"Phone {i+1}", st.session_state.new_authors[i]["phone"], key=f"new_phone_{i}",
                    disabled=disabled
                )
                st.session_state.new_authors[i]["email"] = col4.text_input(
                    f"Email {i+1}", st.session_state.new_authors[i]["email"], key=f"new_email_{i}",
                    disabled=disabled
                )

                col5, col6 = st.columns(2)
                selected_agent = col5.selectbox(
                    f"Corresponding Agent {i+1}",
                    agent_options,
                    index=agent_options.index(st.session_state.new_authors[i]["corresponding_agent"]) if st.session_state.new_authors[i]["corresponding_agent"] in unique_agents else 0,
                    key=f"new_agent_select_{i}",
                    disabled=disabled
                )
                if selected_agent == "Add New..." and not disabled:
                    st.session_state.new_authors[i]["corresponding_agent"] = col5.text_input(
                        f"New Agent Name {i+1}", key=f"new_agent_input_{i}"
                    )
                elif selected_agent != "Select Agent" and not disabled:
                    st.session_state.new_authors[i]["corresponding_agent"] = selected_agent
                else:
                    st.session_state.new_authors[i]["corresponding_agent"] = ""

                selected_consultant = col6.selectbox(
                    f"Publishing Consultant {i+1}",
                    consultant_options,
                    index=consultant_options.index(st.session_state.new_authors[i]["publishing_consultant"]) if st.session_state.new_authors[i]["publishing_consultant"] in unique_consultants else 0,
                    key=f"new_consultant_select_{i}",
                    disabled=disabled
                )
                if selected_consultant == "Add New..." and not disabled:
                    st.session_state.new_authors[i]["publishing_consultant"] = col6.text_input(
                        f"New Consultant Name {i+1}", key=f"new_consultant_input_{i}"
                    )
                elif selected_consultant != "Select Consultant" and not disabled:
                    st.session_state.new_authors[i]["publishing_consultant"] = selected_consultant
                else:
                    st.session_state.new_authors[i]["publishing_consultant"] = ""

        # Add or Cancel buttons
        col1, col2 = st.columns([7, 1])
        with col1:
            if st.button("Add Authors to Book", key="add_authors_to_book", type="primary"):
                errors = []
                for i, author in enumerate(st.session_state.new_authors):
                    if author["name"]:  # Only validate if author has a name
                        is_valid, error_message = validate_author(author, existing_positions, existing_author_ids, 
                                                                st.session_state.new_authors, i, selected_author_type)
                        if not is_valid:
                            errors.append(f"Author {i+1}: {error_message}")
                if errors:
                    for error in errors:
                        st.markdown(f'<div class="error-box">❌ {error}</div>', unsafe_allow_html=True)
                else:
                    try:
                        authors_added = False
                        added_authors = []  # Track added authors for logging
                        with conn.session as s:
                            for author in st.session_state.new_authors:
                                if author["name"]:  # Only process non-empty authors
                                    author_id_to_link = author["author_id"]
                                    if not author_id_to_link:  # New author
                                        author_id_to_link = insert_author(conn, author["name"], author["email"], author["phone"])
                                        if not author_id_to_link:
                                            st.error(f"Failed to insert author {author['name']}")
                                            continue
                                    # Insert into book_authors
                                    s.execute(
                                        text("""
                                            INSERT INTO book_authors (book_id, author_id, author_position, corresponding_agent, publishing_consultant)
                                            VALUES (:book_id, :author_id, :author_position, :corresponding_agent, :publishing_consultant)
                                        """),
                                        params={
                                            "book_id": book_id,
                                            "author_id": author_id_to_link,
                                            "author_position": author["author_position"],
                                            "corresponding_agent": author["corresponding_agent"],
                                            "publishing_consultant": author["publishing_consultant"] or None
                                        }
                                    )
                                    authors_added = True
                                    # Store author details for logging
                                    added_authors.append({
                                        "author_id": author_id_to_link,
                                        "name": author["name"],
                                        "author_position": author["author_position"],
                                        "corresponding_agent": author["corresponding_agent"],
                                        "publishing_consultant": author["publishing_consultant"]
                                    })
                            s.commit()
                        if authors_added:
                            # Log each added author
                            for author in added_authors:
                                log_activity(
                                    conn,
                                    st.session_state.user_id,
                                    st.session_state.username,
                                    st.session_state.session_id,
                                    "added author to book",
                                    f"Book ID: {book_id}, Author ID: {author['author_id']}, Name: {author['name']}, Position: {author['author_position']}, Agent: {author['corresponding_agent'] or 'None'}, Consultant: {author['publishing_consultant'] or 'None'}"
                                )
                            st.cache_data.clear()
                            st.success("✔️ New authors added successfully!")
                            del st.session_state.new_authors
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("❌ No authors were added due to errors.")
                    except Exception as e:
                        st.error(f"❌ Error adding authors: {e}")

        with col2:
            if st.button("Cancel", key="cancel_add_authors", type="secondary"):
                del st.session_state.new_authors
                st.rerun()





###################################################################################################################################
##################################--------------- Edit Operations Dialog ----------------------------##################################
###################################################################################################################################


def fetch_unique_names(column):
    query = f"SELECT DISTINCT {column} AS name FROM books WHERE {column} IS NOT NULL AND {column} != ''"
    return sorted(conn.query(query,show_spinner = False)['name'].tolist())

@st.dialog("Edit Operation Details", width='large')
def edit_operation_dialog(book_id, conn):
    # Fetch book details for title, is_publish_only, and syllabus_path
    book_details = fetch_book_details(book_id, conn)
    is_publish_only = False
    current_syllabus_path = None
    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        is_publish_only = book_details.iloc[0].get('is_publish_only', 0) == 1
        current_syllabus_path = book_details.iloc[0].get('syllabus_path', None)
        col1, col2 = st.columns([6, 1])
        with col1:
            st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
        with col2:
            if st.button(":material/refresh: Refresh", key="refresh_operations", type="tertiary"):
                st.cache_data.clear()
    else:
        st.markdown(f"### Operations for Book ID: {book_id}")
        st.warning("Book title not found.")

    # Streamlit-aligned CSS
    st.markdown("""
        <style>
        .status-box {
            padding: 6px 8px;
            border-radius: 4px;
            margin: 0 4px 4px 0;
            text-align: center;
            font-size: 12px;
            line-height: 1.4;
            border: 1px solid #e6e6e6;
            background-color: #ffffff;
        }
        .status-complete {
            background-color: #f0f9eb;
            border-color: #b7e1a1;
            color: #2e7d32;
        }
        .status-ongoing {
            background-color: #fff4e6;
            border-color: #ffd8a8;
            color: #e65100;
        }
        .status-pending {
            background-color: #f6f6f6;
            border-color: #d9d9d9;
            color: #666666;
        }
        </style>
    """, unsafe_allow_html=True)

    # Fetch operation details
    query = f"""
        SELECT writing_start, writing_end, writing_by, 
               proofreading_start, proofreading_end, proofreading_by, 
               formatting_start, formatting_end, formatting_by, 
               cover_start, cover_end, cover_by, book_pages
        FROM books WHERE book_id = {book_id}
    """
    book_operations = conn.query(query, show_spinner=False)
    
    if book_operations.empty:
        st.warning(f"No operation details found for Book ID: {book_id}")
        current_data = {}
    else:
        current_data = book_operations.iloc[0].to_dict()

    # Initialize session state for all worker fields
    worker_keys = [
        f"writing_by_{book_id}",
        f"proofreading_by_{book_id}",
        f"formatting_by_{book_id}",
        f"cover_by_{book_id}"
    ]
    worker_defaults = [
        current_data.get('writing_by', ""),
        current_data.get('proofreading_by', ""),
        current_data.get('formatting_by', ""),
        current_data.get('cover_by', "")
    ]

    for key, default in zip(worker_keys, worker_defaults):
        if key not in st.session_state:
            st.session_state[key] = default

    # Streamlit-style Status Overview
    cols = st.columns(4, gap="small")
    operations = [
        ("Writing", "writing_start", "writing_end"),
        ("Proofreading", "proofreading_start", "proofreading_end"),
        ("Formatting", "formatting_start", "formatting_end"),
        ("Cover", "cover_start", "cover_end")
    ]

    for i, (op_name, start_field, end_field) in enumerate(operations):
        with cols[i]:
            start = current_data.get(start_field)
            end = current_data.get(end_field)
            if end:
                status_class = "status-complete"
                end_date = str(end).split()[0] if end else ""
                status_text = f"Done<br>{end_date}"
            elif start:
                status_class = "status-ongoing"
                status_text = "Ongoing"
            else:
                status_class = "status-pending"
                status_text = "Pending"
            html = f"""
                <div class="status-box {status_class}">
                    <strong>{op_name}</strong><br>
                    {status_text}
                </div>
            """
            st.markdown(html, unsafe_allow_html=True)

    # Fetch unique names for each role
    writing_names = fetch_unique_names("writing_by")
    proofreading_names = fetch_unique_names("proofreading_by")
    formatting_names = fetch_unique_names("formatting_by")
    cover_names = fetch_unique_names("cover_by")

    # Initialize session state for text inputs
    for key, value in [
        (f"writing_by_{book_id}", current_data.get('writing_by', "")),
        (f"proofreading_by_{book_id}", current_data.get('proofreading_by', "")),
        (f"formatting_by_{book_id}", current_data.get('formatting_by', "")),
        (f"cover_by_{book_id}", current_data.get('cover_by', ""))
    ]:
        if key not in st.session_state:
            st.session_state[key] = value

    # Define options for selectboxes
    writing_options = ["Select Writer"] + writing_names + ["Add New..."]
    proofreading_options = ["Select Proofreader"] + proofreading_names + ["Add New..."]
    formatting_options = ["Select Formatter"] + formatting_names + ["Add New..."]
    cover_options = ["Select Cover Designer"] + cover_names + ["Add New..."]

    # Define tabs
    tab1, tab2, tab3, tab4 = st.tabs(["✍️ Writing", "🔍 Proofreading", "📏 Formatting", "🎨 Book Cover"])

    # Writing Tab
    with tab1:
        if is_publish_only:
            st.warning("Writing section is disabled because this book is in 'Publish Only' mode.")
        
        # Form for input collection
        with st.form(key=f"writing_form_{book_id}", border=False):
            # Worker selection
            selected_writer = st.selectbox(
                "Writer",
                writing_options,
                index=(writing_options.index(st.session_state[f"writing_by_{book_id}"]) 
                       if f"writing_by_{book_id}" in st.session_state and st.session_state[f"writing_by_{book_id}"] in writing_options else 0),
                key=f"writing_select_{book_id}",
                disabled=is_publish_only
            )
            new_writer = ""
            if selected_writer == "Add New..." and not is_publish_only:
                new_writer = st.text_input(
                    "New Writer Name",
                    key=f"writing_new_input_{book_id}",
                    placeholder="Enter new writer name..."
                )
                if new_writer:
                    st.session_state[f"writing_by_{book_id}"] = new_writer
            elif selected_writer != "Select Writer" and not is_publish_only:
                st.session_state[f"writing_by_{book_id}"] = selected_writer

            writing_by = st.session_state[f"writing_by_{book_id}"] if f"writing_by_{book_id}" in st.session_state and st.session_state[f"writing_by_{book_id}"] != "Select Writer" else ""

            col1, col2 = st.columns(2)
            with col1:
                writing_start_date = st.date_input(
                    "Start Date",
                    value=current_data.get('writing_start'),
                    key=f"writing_start_date_{book_id}",
                    disabled=is_publish_only
                )
                writing_start_time = st.time_input(
                    "Start Time",
                    value=current_data.get('writing_start'),
                    key=f"writing_start_time_{book_id}",
                    disabled=is_publish_only
                )
            with col2:
                writing_end_date = st.date_input(
                    "End Date",
                    value=current_data.get('writing_end'),
                    key=f"writing_end_date_{book_id}",
                    disabled=is_publish_only
                )
                writing_end_time = st.time_input(
                    "End Time",
                    value=current_data.get('writing_end'),
                    key=f"writing_end_time_{book_id}",
                    disabled=is_publish_only
                )

            book_pages = st.number_input(
                "Total Book Pages",
                min_value=0,
                value=current_data.get('book_pages', 0) if current_data.get('book_pages') is not None else 0,
                step=1,
                key=f"book_pages_writing_{book_id}",
                disabled=is_publish_only
            )

            # Book Syllabus Section
            st.markdown("<h5 style='color: #4CAF50;'>Book Syllabus</h5>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown('<div class="info-box">', unsafe_allow_html=True)
                # Syllabus uploader
                syllabus_file = None
                if not is_publish_only:
                    syllabus_file = st.file_uploader(
                        "Upload New Syllabus",
                        type=["pdf", "docx", "jpg", "jpeg", "png"],
                        key=f"syllabus_upload_{book_id}",
                        help="Upload a new syllabus to replace the existing one (PDF, DOCX, or image)."
                    )
                    if syllabus_file and current_syllabus_path:
                        st.warning("Uploading a new syllabus will replace the existing one.")
                else:
                    st.info("Syllabus upload is disabled for Publish Only books.")
                st.markdown('</div>', unsafe_allow_html=True)

            # Form submit button
            if st.form_submit_button("💾 Save Writing", use_container_width=True, disabled=is_publish_only):
                with st.spinner("Saving Writing details..."):
                    os.makedirs(UPLOAD_DIR, exist_ok=True)

                    # Handle syllabus file upload
                    new_syllabus_path = current_syllabus_path
                    if syllabus_file and not is_publish_only:
                        file_extension = os.path.splitext(syllabus_file.name)[1]
                        unique_filename = f"syllabus_{book_title.replace(' ', '_')}_{int(time.time())}{file_extension}"
                        new_syllabus_path_temp = os.path.join(UPLOAD_DIR, unique_filename)
                        
                        try:
                            with open(new_syllabus_path_temp, "wb") as f:
                                f.write(syllabus_file.getbuffer())
                            new_syllabus_path = new_syllabus_path_temp
                            
                            if current_syllabus_path and current_syllabus_path != new_syllabus_path and os.path.exists(current_syllabus_path):
                                try:
                                    os.remove(current_syllabus_path)
                                except OSError as e:
                                    st.warning(f"Could not delete old syllabus file: {str(e)}")
                        except Exception as e:
                            st.error(f"Failed to save syllabus file: {str(e)}")
                            raise

                    writing_start = f"{writing_start_date} {writing_start_time}" if writing_start_date and writing_start_time else None
                    writing_end = f"{writing_end_date} {writing_end_time}" if writing_end_date and writing_end_time else None
                    if writing_start and writing_end and writing_start > writing_end:
                        st.error("Start date/time must be before end date/time.")
                    else:
                        updates = {
                            "writing_start": writing_start,
                            "writing_end": writing_end,
                            "writing_by": writing_by if writing_by else None,
                            "book_pages": book_pages,
                            "syllabus_path": new_syllabus_path
                        }
                        update_operation_details(book_id, updates)
                        
                        # Log the form submission
                        syllabus_info = f"Syllabus: {os.path.basename(new_syllabus_path)}" if new_syllabus_path else "Syllabus: None"
                        details = (
                            f"Book ID: {book_id}, Writer: {writing_by or 'None'}, "
                            f"Start: {writing_start or 'None'}, End: {writing_end or 'None'}, "
                            f"Pages: {book_pages}, {syllabus_info}"
                        )
                        try:
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "updated writing details",
                                details
                            )
                        except Exception as e:
                            st.error(f"Error logging writing details: {str(e)}")
                        
                        st.success("✔️ Updated Writing details")
                        if selected_writer == "Add New..." and new_writer:
                            st.cache_data.clear()

        # Syllabus download section
        if current_syllabus_path:
            with st.container(border=True):
                st.markdown('<div class="info-box">', unsafe_allow_html=True)
                st.write(f"**Current Syllabus**: {os.path.basename(current_syllabus_path)}")
                if os.path.exists(current_syllabus_path):
                    with open(current_syllabus_path, "rb") as f:
                        st.download_button(
                            label=":material/download: Download",
                            data=f,
                            file_name=os.path.basename(current_syllabus_path),
                            key=f"download_syllabus_{book_id}"
                        )
                else:
                    st.warning("Current syllabus file not found on server.")
                st.markdown('</div>', unsafe_allow_html=True)

    # Proofreading Tab
    with tab2:
        with st.form(key=f"proofreading_form_{book_id}", border=False):
            # Worker selection
            selected_proofreader = st.selectbox(
                "Proofreader",
                proofreading_options,
                index=(proofreading_options.index(st.session_state[f"proofreading_by_{book_id}"]) 
                    if f"proofreading_by_{book_id}" in st.session_state and st.session_state[f"proofreading_by_{book_id}"] in proofreading_options else 0),
                key=f"proofreading_select_{book_id}"
            )
            new_proofreader = ""
            if selected_proofreader == "Add New...":
                new_proofreader = st.text_input(
                    "New Proofreader Name",
                    key=f"proofreading_new_input_{book_id}",
                    placeholder="Enter new proofreader name..."
                )
                if new_proofreader:
                    st.session_state[f"proofreading_by_{book_id}"] = new_proofreader
            elif selected_proofreader != "Select Proofreader":
                st.session_state[f"proofreading_by_{book_id}"] = selected_proofreader

            proofreading_by = st.session_state[f"proofreading_by_{book_id}"] if f"proofreading_by_{book_id}" in st.session_state and st.session_state[f"proofreading_by_{book_id}"] != "Select Proofreader" else ""

            col1, col2 = st.columns(2)
            with col1:
                proofreading_start_date = st.date_input(
                    "Start Date",
                    value=current_data.get('proofreading_start'),
                    key=f"proofreading_start_date_{book_id}"
                )
                proofreading_start_time = st.time_input(
                    "Start Time",
                    value=current_data.get('proofreading_start'),
                    key=f"proofreading_start_time_{book_id}"
                )
            with col2:
                proofreading_end_date = st.date_input(
                    "End Date",
                    value=current_data.get('proofreading_end'),
                    key=f"proofreading_end_date_{book_id}"
                )
                proofreading_end_time = st.time_input(
                    "End Time",
                    value=current_data.get('proofreading_end'),
                    key=f"proofreading_end_time_{book_id}"
                )

            book_pages = st.number_input(
                "Total Book Pages",
                min_value=0,
                value=current_data.get('book_pages', 0) if current_data.get('book_pages') is not None else 0,
                step=1,
                key=f"book_pages_proofreading_{book_id}"
            )

            if st.form_submit_button("💾 Save Proofreading", use_container_width=True):
                with st.spinner("Saving Proofreading details..."):
                    time.sleep(1)
                    proofreading_start = f"{proofreading_start_date} {proofreading_start_time}" if proofreading_start_date and proofreading_start_time else None
                    proofreading_end = f"{proofreading_end_date} {proofreading_end_time}" if proofreading_end_date and proofreading_end_time else None
                    if proofreading_start and proofreading_end and proofreading_start > proofreading_end:
                        st.error("Start date/time must be before end date/time.")
                    else:
                        updates = {
                            "proofreading_start": proofreading_start,
                            "proofreading_end": proofreading_end,
                            "proofreading_by": proofreading_by if proofreading_by else None,
                            "book_pages": book_pages
                        }
                        update_operation_details(book_id, updates)
                        
                        # Log the form submission
                        details = (
                            f"Book ID: {book_id}, Proofreader: {proofreading_by or 'None'}, "
                            f"Start: {proofreading_start or 'None'}, End: {proofreading_end or 'None'}, "
                            f"Pages: {book_pages}"
                        )
                        try:
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "updated proofreading details",
                                details
                            )
                        except Exception as e:
                            st.error(f"Error logging proofreading details: {str(e)}")
                        
                        st.success("✔️ Updated Proofreading details")
                        if selected_proofreader == "Add New..." and new_proofreader:
                            st.cache_data.clear()

    # Formatting Tab
    with tab3:
        with st.form(key=f"formatting_form_{book_id}", border=False):
            # Worker selection
            selected_formatter = st.selectbox(
                "Formatter",
                formatting_options,
                index=(formatting_options.index(st.session_state[f"formatting_by_{book_id}"]) 
                    if f"formatting_by_{book_id}" in st.session_state and st.session_state[f"formatting_by_{book_id}"] in formatting_options else 0),
                key=f"formatting_select_{book_id}"
            )
            new_formatter = ""
            if selected_formatter == "Add New...":
                new_formatter = st.text_input(
                    "New Formatter Name",
                    key=f"formatting_new_input_{book_id}",
                    placeholder="Enter new formatter name..."
                )
                if new_formatter:
                    st.session_state[f"formatting_by_{book_id}"] = new_formatter
            elif selected_formatter != "Select Formatter":
                st.session_state[f"formatting_by_{book_id}"] = selected_formatter

            formatting_by = st.session_state[f"formatting_by_{book_id}"] if f"formatting_by_{book_id}" in st.session_state and st.session_state[f"formatting_by_{book_id}"] != "Select Formatter" else ""

            col1, col2 = st.columns(2)
            with col1:
                formatting_start_date = st.date_input(
                    "Start Date",
                    value=current_data.get('formatting_start'),
                    key=f"formatting_start_date_{book_id}"
                )
                formatting_start_time = st.time_input(
                    "Start Time",
                    value=current_data.get('formatting_start'),
                    key=f"formatting_start_time_{book_id}"
                )
            with col2:
                formatting_end_date = st.date_input(
                    "End Date",
                    value=current_data.get('formatting_end'),
                    key=f"formatting_end_date_{book_id}"
                )
                formatting_end_time = st.time_input(
                    "End Time",
                    value=current_data.get('formatting_end'),
                    key=f"formatting_end_time_{book_id}"
                )

            book_pages = st.number_input(
                "Total Book Pages",
                min_value=0,
                value=current_data.get('book_pages', 0) if current_data.get('book_pages') is not None else 0,
                step=1,
                key=f"book_pages_formatting_{book_id}"
            )

            if st.form_submit_button("💾 Save Formatting", use_container_width=True):
                with st.spinner("Saving Formatting details..."):
                    time.sleep(1)
                    formatting_start = f"{formatting_start_date} {formatting_start_time}" if formatting_start_date and formatting_start_time else None
                    formatting_end = f"{formatting_end_date} {formatting_end_time}" if formatting_end_date and formatting_end_time else None
                    if formatting_start and formatting_end and formatting_start > formatting_end:
                        st.error("Start date/time must be before end date/time.")
                    else:
                        updates = {
                            "formatting_start": formatting_start,
                            "formatting_end": formatting_end,
                            "formatting_by": formatting_by if formatting_by else None,
                            "book_pages": book_pages
                        }
                        update_operation_details(book_id, updates)
                        
                        # Log the form submission
                        details = (
                            f"Book ID: {book_id}, Formatter: {formatting_by or 'None'}, "
                            f"Start: {formatting_start or 'None'}, End: {formatting_end or 'None'}, "
                            f"Pages: {book_pages}"
                        )
                        try:
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "updated formatting details",
                                details
                            )
                        except Exception as e:
                            st.error(f"Error logging formatting details: {str(e)}")
                        
                        st.success("✔️ Updated Formatting details")
                        if selected_formatter == "Add New..." and new_formatter:
                            st.cache_data.clear()

    # Book Cover Tab
    with tab4:
        with st.form(key=f"cover_form_{book_id}", border=False):
            # Worker selection
            selected_cover = st.selectbox(
                "Cover Designer",
                cover_options,
                index=(cover_options.index(st.session_state[f"cover_by_{book_id}"]) 
                    if f"cover_by_{book_id}" in st.session_state and st.session_state[f"cover_by_{book_id}"] in cover_options else 0),
                key=f"cover_select_{book_id}"
            )
            new_cover_designer = ""
            if selected_cover == "Add New...":
                new_cover_designer = st.text_input(
                    "New Cover Designer Name",
                    key=f"cover_new_input_{book_id}",
                    placeholder="Enter new cover designer name..."
                )
                if new_cover_designer:
                    st.session_state[f"cover_by_{book_id}"] = new_cover_designer
            elif selected_cover != "Select Cover Designer":
                st.session_state[f"cover_by_{book_id}"] = selected_cover

            cover_by = st.session_state[f"cover_by_{book_id}"] if f"cover_by_{book_id}" in st.session_state and st.session_state[f"cover_by_{book_id}"] != "Select Cover Designer" else ""

            st.subheader("Book Cover")
            col1, col2 = st.columns(2)
            with col1:
                cover_start_date = st.date_input(
                    "Start Date",
                    value=current_data.get('cover_start'),
                    key=f"cover_start_date_{book_id}"
                )
                cover_start_time = st.time_input(
                    "Start Time",
                    value=current_data.get('cover_start'),
                    key=f"cover_start_time_{book_id}"
                )
            with col2:
                cover_end_date = st.date_input(
                    "End Date",
                    value=current_data.get('cover_end'),
                    key=f"cover_end_date_{book_id}"
                )
                cover_end_time = st.time_input(
                    "End Time",
                    value=current_data.get('cover_end'),
                    key=f"cover_end_time_{book_id}"
                )

            if st.form_submit_button("💾 Save Cover Details", use_container_width=True):
                with st.spinner("Saving Cover details..."):
                    time.sleep(1)
                    cover_start = f"{cover_start_date} {cover_start_time}" if cover_start_date and cover_start_time else None
                    cover_end = f"{cover_end_date} {cover_end_time}" if cover_end_date and cover_end_time else None
                    if cover_start and cover_end and cover_start > cover_end:
                        st.error("Cover start date/time must be before end date/time.")
                    else:
                        updates = {
                            "cover_start": cover_start,
                            "cover_end": cover_end,
                            "cover_by": cover_by if cover_by else None
                        }
                        update_operation_details(book_id, updates)
                        
                        # Log the form submission
                        details = (
                            f"Book ID: {book_id}, Cover Designer: {cover_by or 'None'}, "
                            f"Start: {cover_start or 'None'}, End: {cover_end or 'None'}"
                        )
                        try:
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "updated cover details",
                                details
                            )
                        except Exception as e:
                            st.error(f"Error logging cover details: {str(e)}")
                        
                        st.success("✔️ Updated Cover details")
                        if selected_cover == "Add New..." and new_cover_designer:
                            st.cache_data.clear()

def update_operation_details(book_id, updates):
    """Update operation details in the books table."""
    set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
    query = f"UPDATE books SET {set_clause} WHERE book_id = :id"
    params = updates.copy()
    params["id"] = int(book_id)
    with conn.session as session:
        session.execute(text(query), params)
        session.commit()


###################################################################################################################################
##################################--------------- Edit Inventory Dialog ----------------------------##################################
###################################################################################################################################

# Function to check if all conditions are met for ready_to_print
def check_ready_to_print(book_id, conn):
    query = """
    SELECT CASE 
        WHEN (
            b.writing_complete = 1 
            AND b.proofreading_complete = 1 
            AND b.formatting_complete = 1 
            AND b.cover_page_complete = 1
            AND NOT EXISTS (
                SELECT 1 
                FROM book_authors ba 
                WHERE ba.book_id = :book_id 
                AND (
                    ba.welcome_mail_sent != 1 
                    OR ba.photo_recive != 1 
                    OR ba.id_proof_recive != 1 
                    OR ba.author_details_sent != 1 
                    OR ba.cover_agreement_sent != 1 
                    OR ba.agreement_received != 1 
                    OR ba.digital_book_sent != 1 
                    OR ba.printing_confirmation != 1
                )
            )
        ) THEN 1 
        ELSE 0 
    END AS ready_to_print
    FROM books b
    WHERE b.book_id = :book_id
    """
    result = conn.query(query, params={"book_id": book_id}, ttl=0, show_spinner=False)
    return result.iloc[0]['ready_to_print'] == 1

# Function to get detailed print status (missing conditions)
def get_print_status(book_id, conn):
    # Query book conditions
    book_query = """
    SELECT 
        writing_complete,
        proofreading_complete,
        formatting_complete,
        cover_page_complete
    FROM books
    WHERE book_id = :book_id
    """
    book_result = conn.query(book_query, params={"book_id": book_id}, ttl=0, show_spinner=False).iloc[0]
    
    # Query author conditions
    author_query = """
    SELECT 
        author_id,
        welcome_mail_sent,
        photo_recive,
        id_proof_recive,
        author_details_sent,
        cover_agreement_sent,
        agreement_received,
        digital_book_sent,
        printing_confirmation
    FROM book_authors
    WHERE book_id = :book_id
    """
    author_results = conn.query(author_query, params={"book_id": book_id}, ttl=0, show_spinner=False)
    
    # Process book conditions
    status = {
        "book": [],
        "authors": []
    }
    if book_result['writing_complete'] != 1:
        status["book"].append("Writing")
    if book_result['proofreading_complete'] != 1:
        status["book"].append("Proofreading")
    if book_result['formatting_complete'] != 1:
        status["book"].append("Formatting")
    if book_result['cover_page_complete'] != 1:
        status["book"].append("Cover")
    
    # Process author conditions with cleaner names
    condition_names = {
        "welcome_mail_sent": "Welcome Mail",
        "photo_recive": "Photo",
        "id_proof_recive": "ID Proof",
        "author_details_sent": "Details",
        "cover_agreement_sent": "Cover Agreement",
        "agreement_received": "Agreement",
        "digital_book_sent": "Digital Book",
        "printing_confirmation": "Print Confirm"
    }
    for _, row in author_results.iterrows():
        author_missing = []
        for col, name in condition_names.items():
            if row[col] != 1:
                author_missing.append(name)
        if author_missing:
            status["authors"].append({"author_id": row['author_id'], "missing": author_missing})
    
    return status


@st.dialog("Edit Printing & Inventory", width='large')
def edit_inventory_delivery_dialog(book_id, conn):
    # Fetch book details for title
    book_details = fetch_book_details(book_id, conn)
    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        col1, col2 = st.columns([6,1])
        with col1:
            st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
        with col2:
            if st.button(":material/refresh: Refresh", key="refresh_inventory", type="tertiary"):
                st.cache_data.clear()
    else:
        st.markdown(f"### Inventory & Delivery for Book ID: {book_id}")
        st.warning("Book title not found.")

    # Fetch current inventory details
    query = f"""
        SELECT ready_to_print, print_status, amazon_link, flipkart_link, 
               google_link, agph_link, google_review, book_mrp
        FROM books WHERE book_id = {book_id}
    """
    book_data = conn.query(query, show_spinner=False)
    
    if book_data.empty:
        st.warning(f"No inventory details found for Book ID: {book_id}")
        current_data = {}
    else:
        current_data = book_data.iloc[0].to_dict()

    # Define tabs for Printing and Inventory
    tab1, tab2 = st.tabs(["📚 Printing", "📦 Inventory"])


    st.markdown("""
        <style>
        .print-run-table {
            font-size: 11px;
            border-radius: 5px;
            overflow-x: auto;
            margin-bottom: 8px;
        }

        .print-run-table-header,
        .print-run-table-row {
            display: grid;
            grid-template-columns: 0.5fr 0.6fr 0.6fr 1fr 1fr 0.8fr 0.8fr 1.5fr 1fr;
            padding: 4px 6px;
            align-items: center;
            box-sizing: border-box;
            min-width: 100%;
        }

        .print-run-table-header {
            background-color: #f1f3f5;
            font-weight: 600;
            font-size: 12px;
            color: #2c3e50;
            border-bottom: 1px solid #dcdcdc;
            border-radius: 5px 5px 0 0;
        }

        .print-run-table-row {
            border-bottom: 1px solid #e0e0e0;
            background-color: #fff;
        }

        .print-run-table-row:last-child {
            border-bottom: none;
        }

        .print-run-table-row:hover {
            background-color: #f9f9f9;
        }

        .status-received, .status-sent, .status-pending {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            text-align: center;
            font-size: 10px;
            color: #fff;
            min-width: 60px;
        }

        .status-received { background-color: #27ae60; }
        .status-sent { background-color: #e67e22; }
        .status-pending { background-color: #7f8c8d; }
                
        .inventory-summary {
            background-color: #e8f4f8;
            border: 1px solid #b3d4fc;
            border-radius: 5px;

            margin-bottom: 10px;
        }
        .inventory-summary-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        .inventory-summary-item {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            text-align: center;
            font-size: 14px;
            color: #2c3e50;
        }
        .inventory-summary-item strong {
            display: block;
            font-size: 16px;
            font-weight: bold;
        }
        .inventory-summary-item .icon {
            font-size: 24px;
            margin-bottom: 5px;
        }
        .value-green { color: #2ecc71; }
        .value-orange { color: #f39c12; }
        .value-red { color: #e74c3c; }
        </style>
    """, unsafe_allow_html=True)

    # Printing Tab
    with tab1:
        # Check ready_to_print conditions
        is_ready_to_print = check_ready_to_print(book_id, conn)
        
        # Update database if computed ready_to_print differs from current value
        current_ready_to_print = current_data.get('ready_to_print', 0) == 1
        if is_ready_to_print != current_ready_to_print:
            updates = {"ready_to_print": 1 if is_ready_to_print else 0}
            update_inventory_delivery_details(book_id, updates, conn)
            st.cache_data.clear()
            current_data['ready_to_print'] = 1 if is_ready_to_print else 0

        # Get print status
        print_status = get_print_status(book_id, conn)
        missing_book = print_status["book"]
        missing_authors = print_status["authors"]

        # Display checkbox and status
        col1, col2 = st.columns([1, 3], vertical_alignment="center")
        with col1:
            st.checkbox(
                label="Ready to Print?",
                value=is_ready_to_print,
                key=f"ready_to_print_{book_id}",
                help="Automatically checked when all conditions are met.",
                disabled=True
            )
        with col2:
            if is_ready_to_print:
                st.markdown(
                    "<span style='background-color: #e6ffe6; color: green; padding: 3px 6px; border-radius: 4px; font-size: 12px;'>All Set ✓</span>",
                    unsafe_allow_html=True
                )
            else:
                badges = []
                for item in missing_book:
                    badges.append(f"<span style='background-color: #ffe6e6; color: red; padding: 3px 6px; border-radius: 4px; font-size: 12px; margin-right: 5px;'>✗ {item}</span>")
                if missing_authors:
                    count = len(missing_authors)
                    badges.append(f"<span style='background-color: #ffe6e6; color: red; padding: 3px 6px; border-radius: 4px; font-size: 12px; margin-right: 5px;'>✗ {count} Author(s)</span>")
                st.markdown(" ".join(badges), unsafe_allow_html=True)

        # Expander with badge-style missing conditions
        if missing_authors:
            with st.expander("Why Not Ready?", expanded=True):
                for author in missing_authors:
                    author_id = author['author_id']
                    missing_conditions = author['missing']
                    badges = [
                        f"<span style='background-color: #ffe6e6; color: red; padding: 3px 6px; border-radius: 4px; font-size: 12px; margin-right: 5px;'>✗ {condition}</span>"
                        for condition in missing_conditions
                    ]
                    st.markdown(
                        f"<b>Author ID {author_id}:</b> {' '.join(badges)}",
                        unsafe_allow_html=True
                    )

        # Fetch print editions data with batch details
        st.markdown('<div class="section-header">Print Editions</div>', unsafe_allow_html=True)
        print_editions_query = f"""
            SELECT 
                pe.print_id, 
                pe.copies_planned, 
                pe.print_cost, 
                pe.print_color, 
                pe.binding, 
                pe.book_size, 
                pe.edition_number, 
                pe.status,
                pe.color_pages,
                bd.batch_id,
                pb.batch_name
            FROM 
                PrintEditions pe
            LEFT JOIN 
                BatchDetails bd ON pe.print_id = bd.print_id
            LEFT JOIN 
                PrintBatches pb ON bd.batch_id = pb.batch_id
            WHERE 
                pe.book_id = {book_id}
            ORDER BY 
                pe.edition_number DESC
        """
        print_editions_data = conn.query(print_editions_query, show_spinner=False)

        # 1. Print Editions Table Expander
        with st.expander("View Existing Print Editions", expanded=True):
            if not print_editions_data.empty:
                st.markdown('<div class="print-run-table">', unsafe_allow_html=True)
                st.markdown("""
                    <div class="print-run-table-header">
                        <div>ID</div>
                        <div>Copies</div>
                        <div>Cost</div>
                        <div>Color</div>
                        <div>Binding</div>
                        <div>Size</div>
                        <div>Edition</div>
                        <div>Batch</div>
                        <div>Status</div>
                    </div>
                """, unsafe_allow_html=True)
                
                for idx, row in print_editions_data.iterrows():
                    # Determine status badge style
                    if row['status'] == 'Pending':
                        status_badge = "<span style='background-color: #fff3e0; color: #f57c00; padding: 3px 6px; border-radius: 4px; font-size: 12px;'>Pending</span>"
                    elif row['status'] == 'In Printing':
                        status_badge = "<span style='background-color: #e3f2fd; color: #1976d2; padding: 3px 6px; border-radius: 4px; font-size: 12px;'>In Printing</span>"
                    else:  # Received
                        status_badge = "<span style='background-color: #e6ffe6; color: green; padding: 3px 6px; border-radius: 4px; font-size: 12px;'>Received</span>"
                    
                    # Format batch information
                    batch_info = f"{row['batch_name']} (ID: {row['batch_id']})" if row['batch_id'] else "Not Assigned"
                    
                    st.markdown(f"""
                        <div class="print-run-table-row">
                            <div>{row['print_id']}</div>
                            <div>{int(row['copies_planned'])}</div>
                            <div>{row['print_cost'] or 'N/A'}</div>
                            <div>{row['print_color']}</div>
                            <div>{row['binding']}</div>
                            <div>{row['book_size']}</div>
                            <div>{row['edition_number']}</div>
                            <div>{batch_info}</div>
                            <div>{status_badge}</div>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("No print editions found. Add a new print edition below if ready.")

        # 2. Edit Existing Print Edition Expander (only if ready_to_print and data exists)
        if is_ready_to_print and not print_editions_data.empty:
            with st.expander("Edit Existing Print Edition", expanded=False):
                selected_print_id = st.selectbox(
                    "Select Print Edition to Edit",
                    options=print_editions_data['print_id'].tolist(),
                    format_func=lambda x: f"ID {x} - Edition {print_editions_data[print_editions_data['print_id'] == x]['edition_number'].iloc[0]}",
                    key=f"select_print_edition_{book_id}"
                )

                if selected_print_id:
                    edit_row = print_editions_data[print_editions_data['print_id'] == selected_print_id].iloc[0]
                    
                    with st.container():
                        # Compact layout: Use a single row with 5 columns
                        col1, col2, col3, col4, col5 = st.columns([1, 0.6, 1.2, 1.2, 0.7])
                        with col1:
                            edit_num_copies = st.number_input(
                                "Copies",
                                min_value=0,
                                step=1,
                                value=int(edit_row['copies_planned']),
                                key=f"edit_num_copies_{book_id}_{selected_print_id}",
                                label_visibility="visible"
                            )
                        with col2:
                            edit_print_cost = st.text_input(
                                "Cost",
                                value=str(edit_row['print_cost'] or ""),
                                key=f"edit_print_cost_{book_id}_{selected_print_id}",
                                label_visibility="visible"
                            )
                        with col3:
                            edit_print_color = st.selectbox(
                                "Color",
                                options=["Black & White", "Full Color"],
                                index=["Black & White", "Full Color"].index(edit_row['print_color']),
                                key=f"edit_print_color_{book_id}_{selected_print_id}",
                                label_visibility="visible"
                            )
                        with col4:
                            edit_binding = st.selectbox(
                                "Binding",
                                options=["Paperback", "Hardcover"],
                                index=["Paperback", "Hardcover"].index(edit_row['binding']),
                                key=f"edit_binding_{book_id}_{selected_print_id}",
                                label_visibility="visible"
                            )
                        with col5:
                            edit_book_size = st.selectbox(
                                "Size",
                                options=["6x9", "8.5x11"],
                                index=["6x9", "8.5x11"].index(edit_row['book_size']) if edit_row['book_size'] in ["6x9", "8.5x11"] else 0,
                                key=f"edit_book_size_{book_id}_{selected_print_id}",
                                label_visibility="visible"
                            )

                        # Conditional input for color pages
                        edit_color_pages = None
                        if edit_print_color == "Full Color":
                            edit_color_pages = st.number_input(
                                "Number of Color Pages",
                                min_value=0,
                                step=1,
                                value=int(edit_row['color_pages']) if pd.notnull(edit_row['color_pages']) else 0,
                                key=f"edit_color_pages_{book_id}_{selected_print_id}",
                                label_visibility="visible"
                            )

                        save_edit = st.button("💾 Save Edited Print Edition", use_container_width=True, key=f"save_edit_print_{book_id}_{selected_print_id}")

                        if save_edit:
                            with st.spinner("Saving edited print edition..."):
                                time.sleep(1)
                                try:
                                    if edit_num_copies <= 0:
                                        st.error("Copies must be greater than 0.")
                                        return
                                    if edit_print_cost:
                                        try:
                                            float(edit_print_cost)
                                        except ValueError:
                                            st.error("Print cost must be a valid number or empty.")
                                            return
                                    if edit_print_color == "Full Color" and (edit_color_pages is None or edit_color_pages <= 0):
                                        st.error("Number of Color Pages must be greater than 0 for Full Color.")
                                        return

                                    # Track changes for logging
                                    changes = []
                                    if edit_num_copies != int(edit_row['copies_planned']):
                                        changes.append(f"Copies Planned changed from '{int(edit_row['copies_planned'])}' to '{edit_num_copies}'")
                                    if (edit_print_cost and float(edit_print_cost) != edit_row['print_cost']) or (not edit_print_cost and edit_row['print_cost'] is not None):
                                        changes.append(f"Print Cost changed from '{edit_row['print_cost'] or 'None'}' to '{edit_print_cost or 'None'}'")
                                    if edit_print_color != edit_row['print_color']:
                                        changes.append(f"Print Color changed from '{edit_row['print_color']}' to '{edit_print_color}'")
                                    if edit_binding != edit_row['binding']:
                                        changes.append(f"Binding changed from '{edit_row['binding']}' to '{edit_binding}'")
                                    if edit_book_size != edit_row['book_size']:
                                        changes.append(f"Book Size changed from '{edit_row['book_size']}' to '{edit_book_size}'")
                                    if edit_print_color == "Full Color" and edit_color_pages != (int(edit_row['color_pages']) if pd.notnull(edit_row['color_pages']) else 0):
                                        changes.append(f"Color Pages changed from '{int(edit_row['color_pages']) if pd.notnull(edit_row['color_pages']) else 'None'}' to '{edit_color_pages}'")

                                    with conn.session as session:
                                        session.execute(
                                            text("""
                                                UPDATE PrintEditions 
                                                SET copies_planned = :copies_planned, 
                                                    print_cost = :print_cost, 
                                                    print_color = :print_color, 
                                                    binding = :binding, 
                                                    book_size = :book_size,
                                                    color_pages = :color_pages
                                                WHERE print_id = :print_id
                                            """),
                                            {
                                                "print_id": selected_print_id,
                                                "copies_planned": edit_num_copies,
                                                "print_cost": float(edit_print_cost) if edit_print_cost else None,
                                                "print_color": edit_print_color,
                                                "binding": edit_binding,
                                                "book_size": edit_book_size,
                                                "color_pages": edit_color_pages if edit_print_color == "Full Color" else None
                                            }
                                        )
                                        session.commit()
                                    # Log edit action
                                    if changes:
                                        log_activity(
                                            conn,
                                            st.session_state.user_id,
                                            st.session_state.username,
                                            st.session_state.session_id,
                                            "edited print edition",
                                            f"Book ID: {book_id}, Print ID: {selected_print_id}, Edition Number: {edit_row['edition_number']}, {', '.join(changes)}"
                                        )
                                    st.success("✔️ Updated Print Edition")
                                    st.cache_data.clear()
                                except Exception as e:
                                    st.error(f"❌ Error saving print edition: {str(e)}")

        # 3. Add New Print Edition Expander (only if ready_to_print is True)
        if is_ready_to_print:
            with st.expander("Add New Print Edition", expanded=False):
                with st.container():
                    # Compact layout: Use a single row with 5 columns
                    col1, col2, col3, col4, col5 = st.columns([1, 0.6, 1.2, 1.2, 0.7])
                    with col1:
                        new_num_copies = st.number_input(
                            label="Copies",
                            min_value=0,
                            step=1,
                            value=0,
                            key=f"new_num_copies_{book_id}",
                            label_visibility="visible"
                        )
                    with col2:
                        print_cost = st.text_input(
                            "Cost",
                            key=f"print_cost_{book_id}",
                            label_visibility="visible"
                        )
                    with col3:
                        print_color = st.selectbox(
                            "Color",
                            options=["Black & White", "Full Color"],
                            key=f"print_color_{book_id}",
                            label_visibility="visible"
                        )
                    with col4:
                        binding = st.selectbox(
                            "Binding",
                            options=["Paperback", "Hardcover"],
                            key=f"binding_{book_id}",
                            label_visibility="visible"
                        )
                    with col5:
                        book_size = st.selectbox(
                            "Size",
                            options=["6x9", "8.5x11"],
                            key=f"book_size_{book_id}",
                            label_visibility="visible"
                        )

                    # Conditional input for color pages
                    color_pages = None
                    if print_color == "Full Color":
                        color_pages = st.number_input(
                            "Number of Color Pages",
                            min_value=0,
                            step=1,
                            value=0,
                            key=f"color_pages_{book_id}",
                            label_visibility="visible"
                        )

                    save_new_print = st.button("💾 Save New Print Edition", use_container_width=True, key=f"save_print_{book_id}")

                    if save_new_print:
                        with st.spinner("Saving new print edition..."):
                            time.sleep(1)
                            try:
                                if new_num_copies > 0:
                                    if print_cost:
                                        try:
                                            float(print_cost)
                                        except ValueError:
                                            st.error("Print cost must be a valid number or empty.")
                                            return
                                    if print_color == "Full Color" and (color_pages is None or color_pages <= 0):
                                        st.error("Number of Color Pages must be greater than 0 for Full Color.")
                                        return

                                    with conn.session as session:
                                        # Calculate edition_number
                                        result = session.execute(
                                            text("SELECT COALESCE(MAX(edition_number), 0) + 1 AS next_edition FROM PrintEditions WHERE book_id = :book_id"),
                                            {"book_id": book_id}
                                        )
                                        edition_number = result.fetchone()[0]
                                        
                                        # Insert into PrintEditions table with status 'Pending'
                                        session.execute(
                                            text("""
                                                INSERT INTO PrintEditions (book_id, edition_number, copies_planned, 
                                                    print_cost, print_color, binding, book_size, status, color_pages)
                                                VALUES (:book_id, :edition_number, :copies_planned, 
                                                    :print_cost, :print_color, :binding, :book_size, 'Pending', :color_pages)
                                            """),
                                            {
                                                "book_id": book_id,
                                                "edition_number": edition_number,
                                                "copies_planned": new_num_copies,
                                                "print_cost": float(print_cost) if print_cost else None,
                                                "print_color": print_color,
                                                "binding": binding,
                                                "book_size": book_size,
                                                "color_pages": color_pages if print_color == "Full Color" else None
                                            }
                                        )
                                        # Get the newly inserted print_id
                                        print_id = session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                                        session.commit()
                                        # Log add action
                                        log_activity(
                                            conn,
                                            st.session_state.user_id,
                                            st.session_state.username,
                                            st.session_state.session_id,
                                            "added print edition",
                                            f"Book ID: {book_id}, Print ID: {print_id}, Edition Number: {edition_number}, Copies Planned: {new_num_copies}, Print Cost: {print_cost or 'None'}, Print Color: {print_color}, Binding: {binding}, Book Size: {book_size}, Color Pages: {color_pages if print_color == 'Full Color' else 'None'}, Status: Pending"
                                        )
                                    st.success("✔️ Added New Print Edition")
                                    st.cache_data.clear()
                                else:
                                    st.warning("Please enter a number of copies greater than 0.")
                            except Exception as e:
                                st.error(f"❌ Error saving new print edition: {str(e)}")

    # Inventory Tab
    with tab2:
        # Check if print_status is 1
        if not current_data.get('print_status', False):
            st.warning("Inventory details are only available after the book has been printed.")
        else:
            # Fetch total copies printed from PrintEditions where the associated batch is 'Received'
            print_editions_query = f"""
                SELECT pe.copies_planned
                FROM PrintEditions pe
                LEFT JOIN BatchDetails bd ON pe.print_id = bd.print_id
                LEFT JOIN PrintBatches pb ON bd.batch_id = pb.batch_id
                WHERE pe.book_id = :book_id
                AND (pb.status = 'Received' OR pb.batch_id IS NULL)
            """
            print_editions_data = conn.query(print_editions_query, params={"book_id": book_id}, show_spinner=False)
            
            # Calculate total copies printed (only for received batches)
            total_copies_printed = int(print_editions_data['copies_planned'].sum()) if not print_editions_data.empty else 0

            # Fetch existing inventory details
            inventory_query = f"""
                SELECT rack_number, amazon_sales, flipkart_sales, website_sales, direct_sales 
                FROM inventory 
                WHERE book_id = :book_id
            """
            inventory_data = conn.query(inventory_query, params={"book_id": book_id}, show_spinner=False)
            
            inventory_current = inventory_data.iloc[0] if not inventory_data.empty else {
                'rack_number': '', 'amazon_sales': 0, 'flipkart_sales': 0, 'website_sales': 0, 'direct_sales': 0
            }

            # Fetch copies sent to authors from book_authors table
            author_copies_query = f"""
                SELECT SUM(number_of_books) as total_author_copies
                FROM book_authors 
                WHERE book_id = :book_id
            """
            author_copies_data = conn.query(author_copies_query, params={"book_id": book_id}, show_spinner=False)
            copies_sent_to_authors = int(author_copies_data.iloc[0]['total_author_copies'] or 0) if not author_copies_data.empty else 0

            # Calculate total sales and current inventory
            total_sales = int(inventory_current.get('amazon_sales', 0) + 
                            inventory_current.get('flipkart_sales', 0) + 
                            inventory_current.get('website_sales', 0) + 
                            inventory_current.get('direct_sales', 0))
            current_inventory = int(total_copies_printed - total_sales - copies_sent_to_authors)

            # Determine color class for Current Inventory based on thresholds
            if current_inventory <= 10:  # Low inventory threshold
                inventory_color_class = "value-red"
            elif current_inventory <= 50:  # Warning threshold
                inventory_color_class = "value-orange"
            else:  # Healthy inventory
                inventory_color_class = "value-green"

            # Display current inventory status at the top
            st.markdown('<div class="section-header">Inventory Summary</div>', unsafe_allow_html=True)
            st.markdown(f"""
                <div class="inventory-summary-grid">
                    <div class="inventory-summary-item">
                        <div class="icon"></div>
                        <strong>{total_copies_printed}</strong>
                        Total Copies Printed
                    </div>
                    <div class="inventory-summary-item">
                        <div class="icon"></div>
                        <strong>{copies_sent_to_authors}</strong>
                        Copies Sent to Authors
                    </div>
                    <div class="inventory-summary-item">
                        <div class="icon"></div>
                        <strong>{total_sales}</strong>
                        Total Sales
                    </div>
                    <div class="inventory-summary-item">
                        <div class="icon"></div>
                        <strong class="{inventory_color_class}">{current_inventory}</strong>
                        Current Inventory
                    </div>
                </div>
            """, unsafe_allow_html=True)

            with st.form(key=f"new_inventory_form_{book_id}", border=False):
                # Pricing Section
                st.markdown('<div class="section-header">Pricing & Storage</div>', unsafe_allow_html=True)
                with st.container(border=True):
                    st.markdown('<div class="inventory-box">', unsafe_allow_html=True)
                    col1, col2 = st.columns(2)

                    with col1:
                        book_mrp = st.text_input(
                            "Book MRP", 
                            value=str(current_data.get('book_mrp', 0.0)) if current_data.get('book_mrp') is not None else "", 
                            key=f"book_mrp_{book_id}" 
                        )

                    with col2:
                        rack_number = st.text_input(
                            "Rack Number", 
                            value=inventory_current.get('rack_number', ''),
                            key=f"rack_number_{book_id}"
                        )
                    st.markdown('</div>', unsafe_allow_html=True)

                # Sales Tracking Section
                st.markdown('<div class="section-header">Sales Tracking</div>', unsafe_allow_html=True)
                with st.container(border=True):
                    st.markdown('<div class="inventory-box">', unsafe_allow_html=True)
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        amazon_sales = st.number_input(
                            "Amazon Sales", 
                            min_value=0,
                            value=int(inventory_current.get('amazon_sales', 0)),
                            key=f"amazon_sales_{book_id}"
                        )
                    with col2:
                        flipkart_sales = st.number_input(
                            "Flipkart Sales", 
                            min_value=0,
                            value=int(inventory_current.get('flipkart_sales', 0)),
                            key=f"flipkart_sales_{book_id}"
                        )
                    with col3:
                        website_sales = st.number_input(
                            "Website Sales", 
                            min_value=0,
                            value=int(inventory_current.get('website_sales', 0)),
                            key=f"website_sales_{book_id}"
                        )
                    with col4:
                        direct_sales = st.number_input(
                            "Direct Sales", 
                            min_value=0,
                            value=int(inventory_current.get('direct_sales', 0)),
                            key=f"direct_sales_{book_id}"
                        )
                    st.markdown('</div>', unsafe_allow_html=True)

                # Links and Reviews Section (Collapsible)
                st.markdown('<div class="section-header">Links and Reviews</div>', unsafe_allow_html=True)
                with st.expander("Links and Reviews", expanded=False):
                    st.markdown('<div class="inventory-box">', unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        amazon_link = st.text_input(
                            "Amazon Link", 
                            value=current_data.get('amazon_link', ""), 
                            key=f"amazon_link_{book_id}"
                        )
                        flipkart_link = st.text_input(
                            "Flipkart Link", 
                            value=current_data.get('flipkart_link', ""), 
                            key=f"flipkart_link_{book_id}"
                        )
                        google_link = st.text_input(
                            "Google Link", 
                            value=current_data.get('google_link', ""), 
                            key=f"google_link_{book_id}"
                        )
                    with col2:
                        agph_link = st.text_input(
                            "AGPH Link", 
                            value=current_data.get('agph_link', ""), 
                            key=f"agph_link_{book_id}"
                        )
                        google_review = st.text_input(
                            "Google Review", 
                            value=current_data.get('google_review', ""), 
                            key=f"google_review_{book_id}"
                        )
                    st.markdown('</div>', unsafe_allow_html=True)

                # Submit Button
                save_inventory = st.form_submit_button(
                    "💾 Save Inventory", 
                    use_container_width=True,
                    help="Click to save changes to inventory details."
                )

                # Handle form submission
                if save_inventory:
                    with st.spinner("Saving Inventory details..."):
                        time.sleep(1)
                        try:
                            # Track changes for logging
                            changes = []
                            original_book_data = current_data
                            original_inventory_data = inventory_current

                            # Book updates
                            book_updates = {
                                "book_mrp": float(st.session_state[f"book_mrp_{book_id}"]) if st.session_state[f"book_mrp_{book_id}"] else None,
                                "amazon_link": st.session_state[f"amazon_link_{book_id}"] if st.session_state[f"amazon_link_{book_id}"] else None,
                                "flipkart_link": st.session_state[f"flipkart_link_{book_id}"] if st.session_state[f"flipkart_link_{book_id}"] else None,
                                "google_link": st.session_state[f"google_link_{book_id}"] if st.session_state[f"google_link_{book_id}"] else None,
                                "agph_link": st.session_state[f"agph_link_{book_id}"] if st.session_state[f"agph_link_{book_id}"] else None,
                                "google_review": st.session_state[f"google_review_{book_id}"] if st.session_state[f"google_review_{book_id}"] else None
                            }
                            for key, value in book_updates.items():
                                original_value = original_book_data.get(key)
                                if value != original_value:
                                    changes.append(f"{key.replace('_', ' ').title()} changed from '{original_value or 'None'}' to '{value or 'None'}'")

                            # Inventory updates
                            inventory_updates = {
                                "book_id": book_id,
                                "rack_number": st.session_state[f"rack_number_{book_id}"] if st.session_state[f"rack_number_{book_id}"] else None,
                                "amazon_sales": st.session_state[f"amazon_sales_{book_id}"],
                                "flipkart_sales": st.session_state[f"flipkart_sales_{book_id}"],
                                "website_sales": st.session_state[f"website_sales_{book_id}"],
                                "direct_sales": st.session_state[f"direct_sales_{book_id}"]
                            }
                            for key, value in inventory_updates.items():
                                if key != "book_id":
                                    original_value = original_inventory_data.get(key, 0 if key.endswith('_sales') else '')
                                    if value != original_value:
                                        changes.append(f"{key.replace('_', ' ').title()} changed from '{original_value or 'None'}' to '{value or 'None'}'")

                            # Update books table
                            update_inventory_delivery_details(book_id, book_updates, conn)

                            # Update inventory table
                            with conn.session as session:
                                session.execute(
                                    text("""
                                        INSERT INTO inventory (book_id, rack_number, amazon_sales, flipkart_sales, website_sales, direct_sales)
                                        VALUES (:book_id, :rack_number, :amazon_sales, :flipkart_sales, :website_sales, :direct_sales)
                                        ON DUPLICATE KEY UPDATE 
                                            rack_number = VALUES(rack_number),
                                            amazon_sales = VALUES(amazon_sales),
                                            flipkart_sales = VALUES(flipkart_sales),
                                            website_sales = VALUES(website_sales),
                                            direct_sales = VALUES(direct_sales)
                                    """),
                                    inventory_updates
                                )
                                session.commit()

                            # Log save action if changes were made
                            if changes:
                                log_activity(
                                    conn,
                                    st.session_state.user_id,
                                    st.session_state.username,
                                    st.session_state.session_id,
                                    "updated inventory details",
                                    f"Book ID: {book_id}, {', '.join(changes)}"
                                )
                            
                            st.success("✔️ Updated Inventory details!")
                            st.cache_data.clear()
                        except Exception as e:
                            st.error(f"❌ Error saving inventory details: {str(e)}")

def update_inventory_delivery_details(book_id, updates, conn):
    """Update inventory and delivery details in the books table."""
    try:
        set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
        query = f"UPDATE books SET {set_clause} WHERE book_id = :id"
        params = updates.copy()
        params["id"] = int(book_id)  
        with conn.session as session:
            session.execute(text(query), params)
            session.commit()
        st.cache_data.clear()
    except Exception as e:
        st.error(f"❌ Error updating books table: {str(e)}")
        raise



###################################################################################################################################
##################################--------------- Book Table ----------------------------##################################
###################################################################################################################################

# Group books by month (for display purposes only, not for pagination)
grouped_books = books.groupby(pd.Grouper(key='date', freq='ME'))

# Query to get author count per book
author_count_query = """
    SELECT book_id, COUNT(author_id) as author_count
    FROM book_authors
    GROUP BY book_id
"""
author_counts = conn.query(author_count_query,show_spinner = False)
# Convert to dictionary for easy lookup
author_count_dict = dict(zip(author_counts['book_id'], author_counts['author_count']))

# Custom CSS for modern table styling and pagination controls
st.markdown("""
    <style>

        .data-row {
            margin-bottom: 25px;
            border-top: 1px solid #e9ecef;
            font-size: 11px;
            color: #212529;
            margin-top: 0px;
        }
        .month-header {
            font-size: 16px;
            font-weight: 500;
            color: #343a40;
            margin: 0px 0 8px 0;
        }
        .popover-button {
            background-color: #007bff;
            color: white;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 12px;
        }
            
        .month-header {
            font-size: 16px;
            font-weight: bold;
            color: #333;
            padding: 3px 10px;
            border-left: 3px solid #f54242; /* Blue side border */
            display: inline-block;
        }

        /* Pagination Styling */
        .pagination-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-top: 20px;
            gap: 10px;
        }
        .pagination-button {
            background-color: #007bff;
            color: white;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 14px;
            border: none;
            cursor: pointer;
            transition: background-color 0.2s;
        }
            
        .author-names {
            font-size: 12px;
            color: #555; 
            margin-bottom: 0px; /* Space between author names */
        }
        .pagination-button:disabled {
            background-color: #d3d3d3;
            cursor: not-allowed;
        }
        .pagination-button:hover:not(:disabled) {
            background-color: #0056b3;
        }
        .pagination-info {
            font-size: 14px;
            color: #343a40;
        }
    </style>
""", unsafe_allow_html=True)

# Function to filter books based on search query
def filter_books(df, query):
    if not query or not query.strip():  # Handle empty or whitespace-only queries
        return df
    
    query = query.strip()  # Remove leading/trailing whitespace
    
    # Author search (starts with @)
    if query.startswith('@'):
        author_query = query[1:].lower()  # Remove @ and convert to lowercase
        # Query to get book_ids associated with the author
        author_book_ids_query = """
            SELECT DISTINCT ba.book_id
            FROM book_authors ba
            JOIN authors a ON ba.author_id = a.author_id
            WHERE LOWER(a.name) LIKE :author_query
        """
        # Fetch book IDs matching the author
        author_book_ids = conn.query(
            author_book_ids_query,
            params={"author_query": f"%{author_query}%"},
            show_spinner=False
        )
        # Filter the original DataFrame using these book IDs
        matching_book_ids = author_book_ids['book_id'].tolist()
        return df[df['book_id'].isin(matching_book_ids)]
    
    # Phone number search (starts with #)
    elif query.startswith('#'):
        phone_query = query[1:].lower()  # Remove # and convert to lowercase
        # Basic phone number validation (digits, optional hyphens/spaces, 7-15 chars)
        if re.match(r'^[\d\s-]{7,15}$', phone_query):
            # Query to get book_ids associated with the author's phone
            phone_book_ids_query = """
                SELECT DISTINCT ba.book_id
                FROM book_authors ba
                JOIN authors a ON ba.author_id = a.author_id
                WHERE LOWER(a.phone) LIKE :phone_query
            """
            # Fetch book IDs matching the phone
            phone_book_ids = conn.query(
                phone_book_ids_query,
                params={"phone_query": f"%{phone_query}%"},
                show_spinner=False
            )
            # Filter the original DataFrame using these book IDs
            matching_book_ids = phone_book_ids['book_id'].tolist()
            return df[df['book_id'].isin(matching_book_ids)]
        else:
            # Invalid phone number format, return empty dataframe
            return df[df['book_id'].isna()]  # Returns empty df
    
    # Email search (starts with !)
    elif query.startswith('!'):
        email_query = query[1:].lower()  # Remove ! and convert to lowercase
        # Basic email validation
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email_query):
            # Query to get book_ids associated with the author's email
            email_book_ids_query = """
                SELECT DISTINCT ba.book_id
                FROM book_authors ba
                JOIN authors a ON ba.author_id = a.author_id
                WHERE LOWER(a.email) LIKE :email_query
            """
            # Fetch book IDs matching the email
            email_book_ids = conn.query(
                email_book_ids_query,
                params={"email_query": f"%{email_query}%"},
                show_spinner=False
            )
            # Filter the original DataFrame using these book IDs
            matching_book_ids = email_book_ids['book_id'].tolist()
            return df[df['book_id'].isin(matching_book_ids)]
        else:
            # Invalid email format, return empty dataframe
            return df[df['book_id'].isna()]  # Returns empty df
    
    # Check if query is a number (for book_id)
    elif query.isdigit():
        query_len = len(query)
        if 1 <= query_len <= 4:  # Book ID (1-4 digits)
            return df[df['book_id'].astype(str) == query]
    
    # Check if query matches ISBN format (e.g., 978-81-970707-9-2)
    elif re.match(r'^\d{3}-\d{2}-\d{5,7}-\d{1,2}-\d$', query):
        # Compare directly with ISBN as stored (with hyphens)
        return df[df['isbn'].astype(str) == query]
    
    # Check if query matches date format (YYYY-MM-DD)
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', query):
        try:
            # Validate date by converting to datetime
            pd.to_datetime(query)
            return df[df['date'].astype(str) == query]
        except ValueError:
            # If date is invalid, return empty dataframe
            return df[df['book_id'].isna()]  # Returns empty df
    
    # Default case: search in title (partial match)
    else:
        query = query.lower()
        return df[df['title'].str.lower().str.contains(query, na=False)]

# Function to filter books based on day, month, year, and date range
def filter_books_by_date(df, day=None, month=None, year=None, start_date=None, end_date=None):
    filtered_df = df.copy()
    if day:
        filtered_df = filtered_df[filtered_df['date'].dt.day == day]
    if month:
        filtered_df = filtered_df[filtered_df['date'].dt.month == month]
    if year:
        filtered_df = filtered_df[filtered_df['date'].dt.year == year]
    if start_date:
        start_date = pd.Timestamp(start_date)
        filtered_df = filtered_df[filtered_df['date'] >= start_date]
    if end_date:
        end_date = pd.Timestamp(end_date)
        filtered_df = filtered_df[filtered_df['date'] <= end_date]
    return filtered_df

c1,c2, c3 = st.columns([10,30,3], vertical_alignment="bottom")

with c1:
    st.markdown("## 📚 AGPH Books")
    
with c2:
    st.caption(f":material/account_circle: Welcome! {user_name} ({user_role})")

with c3:
    if st.button(":material/refresh: Refresh", key="refresh_books", type="tertiary"):
        st.cache_data.clear()

# Search Functionality and Page Size Selection
srcol1, srcol3, srcol4, srcol5 = st.columns([6, 4, 1, 1], gap="small") 

with srcol1:
    # Search bar
    search_query = st.text_input(
        "🔎 Search Books",
        "",
        placeholder="Search by ID, title, ISBN, date, or @authorname, !authoremail, #authorphone..",
        key="search_bar",
        label_visibility="collapsed"
    )

    # Log search query when it changes
    if "prev_search_query" not in st.session_state:
        st.session_state.prev_search_query = ""
    if search_query and search_query != st.session_state.prev_search_query:
        try:
            log_activity(
                conn,
                st.session_state.user_id,
                st.session_state.username,
                st.session_state.session_id,
                "searched",
                f"Search query: {search_query}"
            )
            st.session_state.prev_search_query = search_query
        except Exception as e:
            st.error(f"Error logging search: {str(e)}")

    filtered_books = filter_books(books, search_query)


with srcol3:
    # Popover for filtering

    with st.popover("Filter by Date, Status, Publisher & Author Type", use_container_width=True):
            # Extract unique publishers, years, and author types from the dataset
            unique_publishers = sorted(books['publisher'].dropna().unique())
            unique_years = sorted(books['date'].dt.year.unique())
            unique_author_types = sorted(books['author_type'].dropna().unique())

            # Use session state to manage filter values
            if 'year_filter' not in st.session_state:
                st.session_state.year_filter = None
            if 'month_filter' not in st.session_state:
                st.session_state.month_filter = None
            if 'start_date_filter' not in st.session_state:
                st.session_state.start_date_filter = None
            if 'end_date_filter' not in st.session_state:
                st.session_state.end_date_filter = None
            if 'status_filter' not in st.session_state:
                st.session_state.status_filter = None
            if 'publisher_filter' not in st.session_state:
                st.session_state.publisher_filter = None
            if 'isbn_filter' not in st.session_state:
                st.session_state.isbn_filter = None
            if 'author_type_filter' not in st.session_state:
                st.session_state.author_type_filter = None
            if 'multiple_open_positions_filter' not in st.session_state:
                st.session_state.multiple_open_positions_filter = None
            if 'publish_only_filter' not in st.session_state:
                st.session_state.publish_only_filter = None
            if 'clear_filters_trigger' not in st.session_state:
                st.session_state.clear_filters_trigger = 0

            # Reset button at the top
            if st.button(":material/restart_alt: Reset Filters", key="clear_filters", help="Clear all filters", use_container_width=True, type="secondary"):
                st.session_state.year_filter = None
                st.session_state.month_filter = None
                st.session_state.start_date_filter = None
                st.session_state.end_date_filter = None
                st.session_state.status_filter = None
                st.session_state.publisher_filter = None
                st.session_state.isbn_filter = None
                st.session_state.author_type_filter = None
                st.session_state.multiple_open_positions_filter = None
                st.session_state.publish_only_filter = None
                st.session_state.clear_filters_trigger += 1
                st.rerun()

            # Tabs for filter categories
            tabs = st.tabs(["Status", "Publisher", "Author", "Date"])

            with tabs[3]:
                # Date Filters Expander
                year_options = [str(year) for year in unique_years]
                selected_year = st.pills(
                    "Year:",
                    options=year_options,
                    key=f"year_pills_{st.session_state.clear_filters_trigger}",
                    label_visibility='visible'
                )
                if selected_year:
                    st.session_state.year_filter = int(selected_year)
                elif selected_year is None and "year_pills_callback" not in st.session_state:
                    st.session_state.year_filter = None

                # Month filter
                if st.session_state.year_filter:
                    year_books = books[books['date'].dt.year == st.session_state.year_filter]
                    unique_months = sorted(year_books['date'].dt.month.unique())
                    month_names = {
                        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
                        5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
                        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
                    }
                    month_options = [month_names[month] for month in unique_months]
                    selected_month = st.pills(
                        "Month",
                        options=month_options,
                        key=f"month_pills_{st.session_state.clear_filters_trigger}",
                        label_visibility='visible'
                    )
                    if selected_month:
                        st.session_state.month_filter = next(
                            (num for num, name in month_names.items() if name == selected_month),
                            None
                        )
                    elif selected_month is None and "month_pills_callback" not in st.session_state:
                        st.session_state.month_filter = None
                else:
                    st.session_state.month_filter = None

                st.caption('Filter by Range:')
                # Date range filter
                min_date = books['date'].min().date()
                max_date = books['date'].max().date()
                start_date_key = f"start_date_{st.session_state.clear_filters_trigger}"
                end_date_key = f"end_date_{st.session_state.clear_filters_trigger}"
                st.session_state.start_date_filter = st.date_input(
                    "Start Date",
                    value=st.session_state.start_date_filter,
                    min_value=min_date,
                    max_value=max_date,
                    key=start_date_key,
                    label_visibility="visible"
                )
                st.session_state.end_date_filter = st.date_input(
                    "End Date",
                    value=st.session_state.end_date_filter,
                    min_value=min_date,
                    max_value=max_date,
                    key=end_date_key,
                    label_visibility="visible"
                )
                if st.session_state.start_date_filter and st.session_state.end_date_filter:
                    if st.session_state.start_date_filter > st.session_state.end_date_filter:
                        st.error("Start Date must be before End Date.")
                        st.session_state.start_date_filter = None
                        st.session_state.end_date_filter = None

            # Publisher Filters Expander
            with tabs[1]:
                publisher_options = unique_publishers
                selected_publisher = st.pills(
                    "Publisher:",
                    options=publisher_options,
                    key=f"publisher_pills_{st.session_state.clear_filters_trigger}",
                    label_visibility='visible'
                )
                if selected_publisher:
                    st.session_state.publisher_filter = selected_publisher
                elif selected_publisher is None and "publisher_pills_callback" not in st.session_state:
                    st.session_state.publisher_filter = None

                # Publish Only filter
                publish_only_options = ["Publish Only"]
                selected_publish_only = st.pills(
                    "Publish Type:",
                    options=publish_only_options,
                    key=f"publish_only_pills_{st.session_state.clear_filters_trigger}",
                    label_visibility='visible'
                )
                st.session_state.publish_only_filter = selected_publish_only

            # Status Filters Expander
            with tabs[0]:
                # Status filter
                status_options = ["Delivered", "On Going"]
                if user_role == "admin":
                    status_options.append("Pending Payment")
                selected_status = st.pills(
                    "Status:",
                    options=status_options,
                    key=f"status_pills_{st.session_state.clear_filters_trigger}",
                    label_visibility='visible'
                )
                st.session_state.status_filter = selected_status

                # ISBN filter
                isbn_options = ["Not Applied", "Not Received"]
                selected_isbn = st.pills(
                    "ISBN Status:",
                    options=isbn_options,
                    key=f"isbn_pills_{st.session_state.clear_filters_trigger}",
                    label_visibility='visible'
                )
                st.session_state.isbn_filter = selected_isbn

            # Author Filters Expander
            with tabs[2]:
                # Author type filter
                author_type_options = ["Single", "Double", "Triple", "Multiple"]
                selected_author_type = st.pills(
                    "Author Type:",
                    options=author_type_options,
                    key=f"author_type_pills_{st.session_state.clear_filters_trigger}",
                    label_visibility='visible'
                )
                st.session_state.author_type_filter = selected_author_type

                # Multiple with open positions filter
                multiple_open_positions_options = ["Open Positions"]
                selected_multiple_open_positions = st.pills(
                    "Multiple Authors:",
                    options=multiple_open_positions_options,
                    key=f"multiple_open_positions_pills_{st.session_state.clear_filters_trigger}",
                    label_visibility='visible'
                )
                st.session_state.multiple_open_positions_filter = "Multiple with Open Positions" if selected_multiple_open_positions else None

            # Collect applied filters after all selections
            applied_filters = []
            if st.session_state.publisher_filter:
                applied_filters.append(f"Publisher={st.session_state.publisher_filter}")
            if st.session_state.month_filter:
                applied_filters.append(f"Month={month_names.get(st.session_state.month_filter)}")
            if st.session_state.year_filter:
                applied_filters.append(f"Year={st.session_state.year_filter}")
            if st.session_state.start_date_filter:
                applied_filters.append(f"Start Date={st.session_state.start_date_filter}")
            if st.session_state.end_date_filter:
                applied_filters.append(f"End Date={st.session_state.end_date_filter}")
            if st.session_state.status_filter:
                applied_filters.append(f"Status={st.session_state.status_filter}")
            if st.session_state.isbn_filter:
                applied_filters.append(f"ISBN={st.session_state.isbn_filter}")
            if st.session_state.author_type_filter:
                applied_filters.append(f"Author Type={st.session_state.author_type_filter}")
            if st.session_state.multiple_open_positions_filter:
                applied_filters.append(f"Author Status={st.session_state.multiple_open_positions_filter}")
            if st.session_state.publish_only_filter:
                applied_filters.append(f"Publish Type={st.session_state.publish_only_filter}")

            # Apply filters only if there are any
            if applied_filters:
                # Apply publisher filter
                if st.session_state.publisher_filter:
                    filtered_books = filtered_books[filtered_books['publisher'] == st.session_state.publisher_filter]

                # Apply publish only filter
                if st.session_state.publish_only_filter:
                    filtered_books = filtered_books[filtered_books['is_publish_only'] == 1]

                # Apply date filters
                filtered_books = filter_books_by_date(
                    filtered_books,
                    None,
                    st.session_state.month_filter,
                    st.session_state.year_filter,
                    st.session_state.start_date_filter,
                    st.session_state.end_date_filter
                )

                # Apply ISBN filter
                if st.session_state.isbn_filter:
                    if st.session_state.isbn_filter == "Not Applied":
                        filtered_books = filtered_books[filtered_books['isbn'].isna() & (filtered_books['apply_isbn'] == 0)]
                    elif st.session_state.isbn_filter == "Not Received":
                        filtered_books = filtered_books[filtered_books['isbn'].isna() & (filtered_books['apply_isbn'] == 1)]

                # Apply status filter
                if st.session_state.status_filter:
                    if st.session_state.status_filter == "Pending Payment":
                        pending_payment_query = """
                            SELECT DISTINCT book_id
                            FROM book_authors
                            WHERE total_amount > 0 
                            AND COALESCE(emi1, 0) + COALESCE(emi2, 0) + COALESCE(emi3, 0) < total_amount
                        """
                        pending_book_ids = conn.query(pending_payment_query, show_spinner=False)
                        matching_book_ids = pending_book_ids['book_id'].tolist()
                        filtered_books = filtered_books[filtered_books['book_id'].isin(matching_book_ids)]
                    else:
                        status_mapping = {"Delivered": 1, "On Going": 0}
                        selected_status_value = status_mapping[st.session_state.status_filter]
                        filtered_books = filtered_books[filtered_books['deliver'] == selected_status_value]

                # Apply author type filter
                if st.session_state.author_type_filter:
                    filtered_books = filtered_books[filtered_books['author_type'] == st.session_state.author_type_filter]

                # Apply multiple with open positions filter
                if st.session_state.multiple_open_positions_filter:
                    filtered_books = filtered_books[
                        (filtered_books['author_type'] == 'Multiple') &
                        (filtered_books['book_id'].map(author_count_dict) < 4)
                    ]

                st.success(f"Applied Filters: {', '.join(applied_filters)}")


with srcol4:
    # Add Book button
    if is_button_allowed("add_book_dialog"):
        if st.button(":material/add: Book", type="secondary", help="Add New Book", use_container_width=True):
            add_book_dialog(conn)
    else:
        st.button(":material/add: Book", type="secondary", help="Add New Book (Not Authorized)", use_container_width=True, disabled=True)

with srcol5:
        from urllib.parse import urlencode, quote
        # Initialize session state for tracking logged click IDs
        if "logged_click_ids" not in st.session_state:
            st.session_state.logged_click_ids = set()

        with st.popover("More", use_container_width=True, help="More Options"):
            for key, config in BUTTON_CONFIG.items():
                label_with_icon = f"{config['icon']} {config['label']}"
                permission = config.get('permission')
                admin_only = config.get('admin_only', False)
                
                if admin_only and st.session_state.get("role") != "admin":
                    continue

                if permission is None or is_button_allowed(permission):
                    if config['type'] == "new_tab":
                        # Generate a unique click_id and include only session_id in URL
                        click_id = str(uuid.uuid4())
                        query_params = {
                            "click_id": click_id,
                            "session_id": st.session_state.session_id
                        }
                        full_url = get_page_url(config['page_path'], token) + f"&{urlencode(query_params, quote_via=quote)}"
                        st.link_button(
                            label=label_with_icon,
                            url=full_url,
                            type="tertiary",
                            use_container_width=False
                        )
                    elif config['type'] == "switch_page":
                        if st.button(label_with_icon, key=key, type="tertiary"):
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "navigated to page",
                                f"Page: {config['page_path']}"
                            )
                            st.switch_page(config['page_path'])
                    elif config['type'] == "call_function":
                        if st.button(label_with_icon, key=key, type="tertiary"):
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "opened dialog",
                                f"Function: {config['label']}"
                            )
                            config['function'](conn)
                else:
                    st.button(
                        label=label_with_icon,
                        key=key,
                        type="tertiary",
                        help=f"{config['label']} (Not Authorized)",
                        disabled=True
                    )

# Define base badge styles for consistency
BASE_BADGE_STYLE = {
    "font-size": "10px",
    "font-weight": "500",
    "padding": "3px 8px",
    "border-radius": "12px",
    "display": "inline-flex",
    "align-items": "center",
    "box-shadow": "0 1px 2px rgba(0,0,0,0.05)",
    "margin-left": "5px"
}

# Publisher-specific styles
PUBLISHER_STYLES = {
    "Cipher": {"color": "#ffffff", "background": "#9178e3"},
    "AG Volumes": {"color": "#ffffff", "background": "#2b1a70"},
    "AG Classics": {"color": "#ffffff", "background": "#d81b60"},
    "AG Kids": {"color": "#ffffff", "background": "#f57c00"},
    "NEET/JEE": {"color": "#ffffff", "background": "#0288d1"}
}

# # Author type-specific styles
AUTHOR_TYPE_STYLES = {
    "Single": {"color": "#15803d", "background": "#ecfdf5"},  # Teal with light teal background
    "Double": {"color": "#15803d", "background": "#ecfdf5"},  # Purple with light purple background
    "Triple": {"color": "#15803d", "background": "#ecfdf5"},  # Amber with light amber background
    "Multiple": {"color": "#15803d", "background": "#ecfdf5"}  # Red with light red background
}

# AUTHOR_TYPE_STYLES = {
#     "Single": {"color": "#b45309", "background": "#fef3c7"},  # Teal with light teal background
#     "Double": {"color": "#b45309", "background": "#fef3c7"},  # Purple with light purple background
#     "Triple": {"color": "#b45309", "background": "#fef3c7"},  # Amber with light amber background
#     "Multiple": {"color": "#b45309", "background": "#fef3c7"}  # Red with light red background
# }

def generate_badge(content, color, background, extra_styles=None):
    """Generate HTML for a styled badge."""
    styles = {**BASE_BADGE_STYLE, "color": color, "background-color": background}
    if extra_styles:
        styles.update(extra_styles)
    style_str = "; ".join(f"{k}: {v}" for k, v in styles.items())
    return f'<span style="{style_str}">{content}</span>'

def get_author_badge(author_type, author_count):
    """Generate author type badge with distinct styles."""
    author_type = author_type if author_type in AUTHOR_TYPE_STYLES else "Multiple"
    style = AUTHOR_TYPE_STYLES[author_type]
    content = author_type if author_type != "Multiple" else f"Multiple, {author_count if author_count > 0 else 'Unknown'}"
    return generate_badge(content, style["color"], style["background"])

def get_publish_badge(is_publish_only):
    """Generate publish-only badge if applicable."""
    if is_publish_only == 1:
        return generate_badge("Publish Only", "#c2410c", "#fff7ed")
    return ""

def get_publisher_badge(publisher):
    """Generate publisher badge if applicable."""
    if publisher in PUBLISHER_STYLES:
        style = PUBLISHER_STYLES[publisher]
        return generate_badge(publisher, style["color"], style["background"])
    return ""


#actual icons
price_icon = ":material/currency_rupee:"
isbn_icon = ":material/edit_document:"
author_icon = ":material/manage_accounts:"
ops_icon = ":material/manufacturing:"
delivery_icon = ":material/local_shipping:"


# Pagination Logic
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

# Apply sorting to the filtered books (sort by date in descending order)
filtered_books = filtered_books.sort_values(by='date', ascending=False)

# Apply pagination with fixed page size of 40
page_size = 40
total_books = len(filtered_books)
total_pages = max(1, (total_books + page_size - 1) // page_size)  # Ceiling division
st.session_state.current_page = max(1, min(st.session_state.current_page, total_pages))  # Clamp current page
start_idx = (st.session_state.current_page - 1) * page_size
end_idx = min(start_idx + page_size, total_books)
paginated_books = filtered_books.iloc[start_idx:end_idx]


# Display the table
column_size = [0.5, 3.8, 1, 0.95, 1.2, 2]
render_start = time.time()
# Main rendering loop (partial, focusing on col5)
with st.container(border=False):
    if paginated_books.empty:
        st.error("No books available.")
    else:
        if applied_filters or search_query:
            st.warning(f"Showing {start_idx + 1}-{min(end_idx, len(filtered_books))} of {len(filtered_books)} books")

        book_ids = paginated_books['book_id'].tolist()
        authors_df = fetch_all_book_authors(book_ids, conn)
        printeditions_df = fetch_all_printeditions(book_ids, conn)

        # Preprocess DataFrames to group by book_id
        authors_grouped = {book_id: group for book_id, group in authors_df.groupby('book_id')}
        printeditions_grouped = {book_id: group for book_id, group in printeditions_df.groupby('book_id')}

        grouped_books = paginated_books.groupby(pd.Grouper(key='date', freq='ME'))
        reversed_grouped_books = reversed(list(grouped_books))

        for month, monthly_books in reversed_grouped_books:
            monthly_books = monthly_books.sort_values(by='date', ascending=False)
            num_books = len(monthly_books)
            st.markdown(f'<div class="month-header">{month.strftime("%B %Y")} ({num_books} books)</div>', unsafe_allow_html=True)

            for _, row in monthly_books.iterrows():
                st.markdown('<div class="data-row">', unsafe_allow_html=True)
                authors_display = fetch_author_names(row['book_id'], conn)
                col1, col2, col3, col4, col5, col6 = st.columns(column_size, vertical_alignment="center")

                with col1:
                    st.write(row['book_id'])
                with col2:
                    author_count = author_count_dict.get(row['book_id'], 0)
                    author_badge = get_author_badge(row.get('author_type', 'Multiple'), author_count)
                    publish_badge = get_publish_badge(row.get('is_publish_only', 0))
                    publisher_badge = get_publisher_badge(row.get('publisher', ''))
                    title_with_badges = f"{row['title']} {author_badge}{publish_badge}{publisher_badge}"
                    st.markdown(title_with_badges, unsafe_allow_html=True)
                    st.markdown(f'<div class="author-names">{authors_display}</div>', unsafe_allow_html=True)
                with col3:
                    st.write(row['date'].strftime('%Y-%m-%d'))
                with col4:
                    st.markdown(get_isbn_display(row["book_id"], row["isbn"], row["apply_isbn"]), unsafe_allow_html=True)
                with col5:
                    st.markdown(get_status_pill(row["book_id"], row, authors_grouped, printeditions_grouped), unsafe_allow_html=True)
                with col6:
                    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns([1, 1, 1, 1, 1], vertical_alignment="bottom")
                    with btn_col1:
                        # ISBN button (manage_isbn_dialog)
                        if is_button_allowed("manage_isbn_dialog"):
                            if st.button(isbn_icon, key=f"isbn_{row['book_id']}", help="Edit Book Title & ISBN"):
                                manage_isbn_dialog(conn, row['book_id'], row['apply_isbn'], row['isbn'])
                        else:
                            st.button(isbn_icon, key=f"isbn_{row['book_id']}", help="Not Authorised", disabled=True)
                    with btn_col2:
                        # Price button (manage_price_dialog)
                        publisher = row.get('publisher', '')
                        if publisher not in ["AG Kids", "NEET/JEE"] or st.session_state.get("role") == "admin":
                            if is_button_allowed("manage_price_dialog"):
                                if st.button(price_icon, key=f"price_btn_{row['book_id']}", help="Edit Payments"):
                                    manage_price_dialog(row['book_id'], row['price'], conn)
                            else:
                                st.button(price_icon, key=f"price_btn_{row['book_id']}", help="Not Authorised", disabled=True)
                        else:
                            st.button(price_icon, key=f"price_btn_{row['book_id']}", help="Price management disabled for this publisher", disabled=True)
                    with btn_col3:
                        # Author button (edit_author_dialog)
                        publisher = row.get('publisher', '')
                        if publisher not in ["AG Kids", "NEET/JEE"] or st.session_state.get("role") == "admin":
                            if is_button_allowed("edit_author_dialog"):
                                if st.button(author_icon, key=f"edit_author_{row['book_id']}", help="Edit Authors Details"):
                                    edit_author_dialog(row['book_id'], conn)
                            else:
                                st.button(author_icon, key=f"edit_author_{row['book_id']}", help="Not Authorised", disabled=True)
                        else:
                            st.button(author_icon, key=f"edit_author_{row['book_id']}", help="Author editing disabled for this publisher", disabled=True)
                    with btn_col4:
                        # Operations button (edit_operation_dialog)
                        if is_button_allowed("edit_operation_dialog"):
                            if st.button(ops_icon, key=f"ops_{row['book_id']}", help="Edit Operations"):
                                edit_operation_dialog(row['book_id'], conn)
                        else:
                            st.button(ops_icon, key=f"ops_{row['book_id']}", help="Not Authorised", disabled=True)
                    with btn_col5:
                        # Delivery button (edit_inventory_delivery_dialog)
                        if is_button_allowed("edit_inventory_delivery_dialog"):
                            if st.button(delivery_icon, key=f"delivery_{row['book_id']}", help="Edit Print & Inventory"):
                                edit_inventory_delivery_dialog(row['book_id'], conn)
                        else:
                            st.button(delivery_icon, key=f"delivery_{row['book_id']}", help="Not Authorised", disabled=True)
                    # with st.popover("More Options", use_container_width=True):
                    #     st.write("hello")
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
        

        st.markdown(
            f"<div style='text-align: center; margin-bottom: 10px;'>"
            f"Showing <span style='font-weight: bold; color: #362f2f;'>{start_idx + 1}</span>-"
            f"<span style='font-weight: bold; color: #362f2f;'>{end_idx}</span> of "
            f"<span style='font-weight: bold; color: #362f2f;'>{total_books}</span> books"
            f"</div>",
            unsafe_allow_html=True
        )


        # Pagination Controls (always show since page_size is fixed at 40)
        if total_pages > 1:  # Only show pagination if there are multiple pages
            col1, col2, col3, col4, col5, col6 = st.columns([1, 2, 4, 1, 1, 1], vertical_alignment="center")
            with col1:
                if st.button("First", key="first_page", disabled=(st.session_state.current_page == 1)):
                    st.session_state.current_page = 1
                    st.rerun()
            with col2:
                if st.button("Previous", key="prev_page", disabled=(st.session_state.current_page == 1)):
                    st.session_state.current_page -= 1
                    st.rerun()
            with col3:
                st.markdown(f"<div style='text-align: center;'>Page {st.session_state.current_page} of {total_pages}</div>", unsafe_allow_html=True)
            with col4:
                if st.button("Next", key="next_page", disabled=(st.session_state.current_page == total_pages)):
                    st.session_state.current_page += 1
                    st.rerun()
            with col5:
                if st.button("Last", key="last_page", disabled=(st.session_state.current_page == total_pages)):
                    st.session_state.current_page = total_pages
                    st.rerun()
            with col6:
                page_options = list(range(1, total_pages + 1)) if total_pages > 0 else [1]
                current_index = min(st.session_state.current_page - 1, len(page_options) - 1)
                selected_page = st.selectbox(
                    "Go to page:",
                    page_options,
                    index=current_index,
                    key="page_selector",
                    label_visibility="collapsed"
                )
                if selected_page != st.session_state.current_page:
                    st.session_state.current_page = selected_page
                    st.rerun()
    render_time = time.time() - render_start


# End timing
total_time = time.time() - start_time
st.write(f"**Total Page Load Time:** {total_time:.2f} seconds")
st.write(f"**Table Rendering Time:** {render_time:.2f} seconds")
st.write(f"**Total Authentication Time:** {total_chek_time:.2f} seconds")