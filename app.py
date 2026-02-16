import streamlit as st
import pandas as pd
from sqlalchemy import text
import datetime
from datetime import date
import time
import re
import io
import os
import pytz
import random
import uuid
from urllib.parse import urlencode, quote
import logging
from logging.handlers import RotatingFileHandler
from auth import validate_token
from constants import ACCESS_TO_BUTTON,log_activity, connect_db, connect_ijisem_db, connect_ict_db, clean_old_logs, get_page_url, VALID_SUBJECTS, get_ready_to_print_books, get_reprint_eligible_books,get_total_unread_count, check_ready_to_print
from auth import VALID_APPS
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from PIL import Image as PILImage
import requests
import ollama
import difflib
from decimal import Decimal

####################################################################################################################
##################################--------------- Logs ----------------------------#################################
####################################################################################################################

start_time = time.time()
from datetime import datetime
# Get current time in Indian Standard Time
ist = pytz.timezone('Asia/Kolkata')
ist_time = datetime.now(ist)

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

validate_token()

user_role = st.session_state.get("role", "Unknown")
user_app = st.session_state.get("app", "Unknown")
user_access = st.session_state.get("access", [])
user_id = st.session_state.get("user_id", "Unknown")
user_name = st.session_state.get("username", "Unknown")
start_date = st.session_state.get("start_date", None)
level = st.session_state.get("level", "Unknown")
report_to = st.session_state.get("report_to", "Unknown")
token = st.session_state.token
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


# Base URL for your app
BASE_URL  = st.secrets["general"]["BASE_URL"]
SYLLABUS_UPLOAD_DIR = st.secrets["general"]["SYLLABUS_UPLOAD_DIR"]
AUTHOR_PHOTO_UPLOAD_DIR = st.secrets["general"]["AUTHOR_PHOTO_UPLOAD_DIR"]
CORRECTION_FIL_DIR = st.secrets["general"]["CORRECTION_FIL_DIR"]
EMAIL_ADDRESS = st.secrets["export_email"]["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["export_email"]["EMAIL_PASSWORD"]
GMAIL_SMTP_SERVER = st.secrets["email_servers"]["GMAIL_SMTP_SERVER"]
GMAIL_SMTP_PORT = st.secrets["email_servers"]["GMAIL_SMTP_PORT"]
HOSTINGER_SMTP_SERVER = st.secrets["email_servers"]["HOSTINGER_SMTP_SERVER"]
HOSTINGER_SMTP_PORT = st.secrets["email_servers"]["HOSTINGER_SMTP_PORT"]
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
            padding-top: 0px !important;  /* Small padding for breathing room */
        }
            
        .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; font-size: 12px; }
        .info-box { padding: 5px; border-radius: 6px; background-color: #f1f5f9; }
        .info-label { font-weight: 600; color: #2c3e50; display: inline-block; margin-right: 4px; }
        .book-title { font-size: 18px; color: #2c3e50; font-weight: 700; margin-bottom: 8px; }
        .section-title { margin-top: 10px; margin-bottom: 5px; font-size: 16px; color: #2c3e50; font-weight: 600; }
            
        [data-testid="stElementToolbar"] {display: none;}
        </style>
            
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:FILL@0" rel="stylesheet" />
            """, unsafe_allow_html=True)

st.cache_data.clear()


########################################################################################################################
##################################--------------- Database Connection ----------------------------######################
#######################################################################################################################

# Connect to MySQL
conn = connect_db()
ijisem_conn = connect_ijisem_db()
ict_conn = connect_ict_db()

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
    clean_old_logs(conn)
    st.session_state.cleanup_done = True


########################################################################################################################
##################################--------------- Button Configuration ----------------------------######################
#######################################################################################################################


# Button configuration
BUTTON_CONFIG = {
    "advance_search": {
        "label": "Advance Search",
        "icon": "🔍",
        "page_path": "adsearch",
        "permission": "advance_search",
        "type": "new_tab",
    },
    "messages": {
        "label": "Message",
        "icon": "💬",
        "page_path": "/",
        "permission": "messages",
        "type": "new_tab",
    },
    "amazon": {
        "label": "Amazon",
        "icon": "📦",
        "page_path": "amazon",
        "permission": "amazon",
        "type": "new_tab",
        "admin_only": True,
    },

    "team_dashboard": {
        "label": "Operations",
        "icon": "📈",
        "page_path": "team_dashboard",
        "permission": "team_dashboard",
        "type": "new_tab",
    },
    "payments": {
        "label": "Payments",
        "icon": "💰",
        "page_path": "payments",
        "permission": None, # Admin only via admin_only flag
        "type": "new_tab",
        "admin_only": True,
    },
    "pending_books": {
        "label": "Pending Work",
        "icon": "⚠️",
        "page_path": "pending_books",
        "permission": "pending_books",
        "type": "new_tab",
    },
    "tasks": {
        "label": "Tasks",
        "icon": "🕒",
        "page_path": "tasks",
        "permission": "tasks",
        "type": "new_tab",
    },
    "attendance": {
        "label": "Attendance Log",
        "icon": "🔔",
        "page_path": "attendance",
        "permission": "attendance",
        "type": "new_tab",
    },
    "dashboard": {
        "label": "Dashboard",
        "icon": "📊",
        "page_path": "dashboard",
        "permission": "datadashoard",
        "type": "new_tab",
    },
    "IJISEM": {
        "label": "IJISEM",
        "icon": "🧾",
        "page_path": "ijisem",
        "permission": "ijisem",
        "type": "new_tab",
    },
    "academic_guru": {
        "label": "Academic Guru",
        "icon": "🎓",
        "page_path": "academic_guru",
        "permission": "academic_guru",
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
    "sales_track": {
        "label": "Sales Tracking",
        "icon": "📈",
        "page_path": "sales_track",
        "permission": "sales_track",
        "type": "new_tab",
    },
    "author_positions": {
        "label": "Open Positions",
        "icon": "📚",
        "page_path": "author_positions",
        "permission": "open_author_positions",
        "type": "new_tab",
    },
    "extra_books": {
        "label": "Extra/Deleted Books",
        "icon": "🗑️",
        "page_path": "extra_books",
        "permission": "extra_books",
        "type": "new_tab",
    },
    "edit_authors": {
        "label": "Edit Authors",
        "icon": "✏️",
        "permission": "edit_author_detail",
        "type": "call_function",
        "function": lambda conn: edit_author_detail(conn),
    },
    "activity_log": {
        "label": "Activity Log",
        "icon": "🕵🏻",
        "page_path": "activity_log",
        "permission": None,
        "type": "new_tab",
        "admin_only": True,
    },

    "settings": {
        "label": "Settings",
        "icon": "⚙️",
        "permission": None,
        "type": "call_function",
        "function": lambda conn: settings_dialog(conn),
        "admin_only": True,
    },
}


first_print_books = get_ready_to_print_books(conn)
reprint_books = get_reprint_eligible_books(conn)
total_unread = get_total_unread_count(ict_conn, st.session_state.user_id)


# Helper to update button labels with counts
def update_button_counts(conn):
    try:
        # 1. Extra Books (Rewritten in extra_books) + Deleted Books (in deleted_books)
        extra_count_query = """
            SELECT 
                (SELECT COUNT(*) FROM extra_books) as total_count
        """
        extra_count = conn.query(extra_count_query, ttl=0, show_spinner = False).iloc[0]["total_count"]
        if "extra_books" in BUTTON_CONFIG and extra_count > 0:
            BUTTON_CONFIG["extra_books"]["label"] += f" 🔴 ({extra_count})"

        # 2. Pending Work
        pending_count = conn.query("SELECT COUNT(*) AS count FROM books WHERE deliver = 0 AND is_archived = 0 AND is_cancelled = 0", ttl=0, show_spinner = False).iloc[0]["count"]
        if "pending_books" in BUTTON_CONFIG and pending_count > 0:
            BUTTON_CONFIG["pending_books"]["label"] += f" 🔴 ({pending_count})"

        # 3. Operations (Pending Writing)
        ops_count = conn.query("SELECT COUNT(*) AS count FROM books WHERE writing_start IS NULL AND is_publish_only = 0 AND is_thesis_to_book = 0 AND is_cancelled = 0", ttl=0,show_spinner = False).iloc[0]["count"]
        if "team_dashboard" in BUTTON_CONFIG and ops_count > 0:
            BUTTON_CONFIG["team_dashboard"]["label"] += f" 🔴 ({ops_count})"

        # 3.1 Payments (Pending Approval)
        if "payments" in BUTTON_CONFIG:
            pay_count = conn.query("SELECT COUNT(*) AS count FROM author_payments WHERE status = 'Pending'", ttl=0, show_spinner=False).iloc[0]["count"]
            if pay_count > 0:
                BUTTON_CONFIG["payments"]["label"] += f" 🔴 ({pay_count})"

        # 4. Open Positions
        open_pos_query = """
        SELECT SUM(
            CASE 
                WHEN author_type = 'Double' THEN GREATEST(0, 2 - cnt)
                WHEN author_type = 'Triple' THEN GREATEST(0, 3 - cnt)
                WHEN author_type = 'Multiple' THEN GREATEST(0, 4 - cnt)
                ELSE 0
            END
        ) as count
        FROM (
            SELECT b.author_type, COUNT(ba.author_id) as cnt
            FROM books b
            LEFT JOIN book_authors ba ON b.book_id = ba.book_id
            WHERE b.author_type IN ('Double', 'Triple', 'Multiple') AND b.is_cancelled = 0
            GROUP BY b.book_id, b.author_type
        ) as sub
        """
        open_pos_res = conn.query(open_pos_query, ttl=0, show_spinner = False)
        open_pos_count = int(open_pos_res.iloc[0]["count"]) if not open_pos_res.empty and pd.notna(open_pos_res.iloc[0]["count"]) else 0
        if "author_positions" in BUTTON_CONFIG and open_pos_count > 0:
            BUTTON_CONFIG["author_positions"]["label"] += f" 🔴 ({open_pos_count})"
        
        # 5. Print Management
        first_print_count = len(first_print_books)
        reprint_count = len(reprint_books)
        total_print = first_print_count + reprint_count
        if "print_management" in BUTTON_CONFIG and total_print > 0:
            BUTTON_CONFIG["print_management"]["label"] += f" 🔴 ({total_print})"

        # 6. Messages
        if "messages" in BUTTON_CONFIG and total_unread > 0:
            BUTTON_CONFIG["messages"]["label"] += f" 🔴 ({total_unread})"
            if "unread_toast_shown" not in st.session_state:
                st.toast(f"You have {total_unread} unread messages!", icon="💬", duration="infinite")
                st.session_state.unread_toast_shown = True

    except Exception:
        pass

update_button_counts(conn)

########################################################################################################################
##################################--------------- Main App Started ----------------------------######################
#######################################################################################################################


# Fetch books from the database
query = "SELECT book_id, title, date, isbn, apply_isbn, isbn_receive_date, deliver, price, is_single_author, syllabus_path, " \
"is_publish_only, is_thesis_to_book, publisher, author_type, writing_start, writing_end, " \
"proofreading_start, proofreading_end, formatting_start, formatting_end, cover_start, cover_end," \
"writing_by, proofreading_by, formatting_by, cover_by, tags, subject, agph_link, amazon_link, flipkart_link, google_link, images, correction_status FROM books WHERE is_cancelled = 0"

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
    SELECT title, date, apply_isbn, isbn, is_single_author, isbn_receive_date , tags, subject, num_copies, 
    syllabus_path, is_thesis_to_book, print_status,is_publish_only, publisher, price, writing_start, is_cancelled, cancellation_reason, correction_status
    FROM books
    WHERE book_id = '{book_id}'
    """
    return conn.query(query,show_spinner = False)

# Convert 'date' column to datetime objects if it's not already
if not pd.api.types.is_datetime64_any_dtype(books['date']):
    books['date'] = pd.to_datetime(books['date'])


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



@st.cache_data
def fetch_all_book_authors(book_ids, _conn):
    if not book_ids:  # Handle empty book_ids
        return pd.DataFrame(columns=[
            'id', 'book_id', 'author_id', 'name', 'email', 'phone', 'city', 'state', 'author_position',
            'welcome_mail_sent', 'corresponding_agent', 'publishing_consultant',
            'photo_recive', 'id_proof_recive', 'author_details_sent',
            'cover_agreement_sent', 'agreement_received', 'digital_book_sent',
            'printing_confirmation', 'delivery_address', 'delivery_charge',
            'number_of_books', 'total_amount', 'delivery_date',
            'tracking_id', 'delivery_vendor', 'amount_paid'
        ])
    query = """
    SELECT ba.id, ba.book_id, ba.author_id, a.name, a.email, a.phone, a.city, a.state,
           ba.author_position, ba.welcome_mail_sent, ba.corresponding_agent, 
           ba.publishing_consultant, ba.photo_recive, ba.id_proof_recive, 
           ba.author_details_sent, ba.cover_agreement_sent, ba.agreement_received, 
           ba.digital_book_sent, ba.printing_confirmation, ba.delivery_address, 
           ba.delivery_charge, ba.number_of_books, ba.total_amount,
           ba.delivery_date, ba.tracking_id, ba.delivery_vendor,
           COALESCE((SELECT SUM(amount) FROM author_payments WHERE book_author_id = ba.id AND status = 'Approved'), 0) as amount_paid
    FROM book_authors ba
    JOIN authors a ON ba.author_id = a.author_id
    WHERE ba.book_id IN :book_ids
    """
    try:
        return _conn.query(query, params={'book_ids': tuple(book_ids)}, show_spinner=False)
    except Exception as e:
        st.error(f"Error fetching book authors: {e}")
        return pd.DataFrame(columns=[
            'id', 'book_id', 'author_id', 'name', 'email', 'phone', 'city', 'state', 'author_position',
            'welcome_mail_sent', 'corresponding_agent', 'publishing_consultant',
            'photo_recive', 'id_proof_recive', 'author_details_sent',
            'cover_agreement_sent', 'agreement_received', 'digital_book_sent',
            'printing_confirmation', 'delivery_address', 'delivery_charge',
            'number_of_books', 'total_amount', 'delivery_date',
            'tracking_id', 'delivery_vendor', 'amount_paid'
        ])

# New function to fetch detailed print information for a specific book_id
def fetch_print_details(book_id, conn):
    query = """
    SELECT pe.book_id, pe.print_id, bd.batch_id, pe.copies_planned, pb.print_sent_date, pb.print_receive_date, pb.status
    FROM PrintEditions pe
    LEFT JOIN BatchDetails bd ON pe.print_id = bd.print_id
    LEFT JOIN PrintBatches pb ON bd.batch_id = pb.batch_id
    WHERE pe.book_id = :book_id
    """
    return conn.query(query, params={'book_id': book_id}, show_spinner=False)

@st.cache_data
def fetch_all_printeditions(book_ids, _conn):
    if not book_ids:  # Handle empty book_ids
        return pd.DataFrame(columns=['book_id', 'print_id', 'status'])
    query = """
    SELECT book_id, print_id, status
    FROM PrintEditions
    WHERE book_id IN :book_ids
    """
    try:
        return _conn.query(query, params={'book_ids': tuple(book_ids)}, show_spinner=False)
    except Exception as e:
        st.error(f"Error fetching print editions: {e}")
        return pd.DataFrame(columns=['book_id', 'print_id', 'status'])

@st.cache_data
def fetch_all_author_names(book_ids, _conn):
    """Fetch author names for multiple book_ids, formatted with Material Icons, returning a dictionary."""
    if not book_ids:  # Handle empty book_ids
        return {}
    try:
        with _conn.session as session:
            query = text("""
                SELECT pa.book_id, a.name
                FROM authors a
                JOIN book_authors pa ON a.author_id = pa.author_id
                WHERE pa.book_id IN :book_ids
                ORDER BY pa.book_id, pa.author_position IS NULL, pa.author_position ASC
            """)
            results = session.execute(query, {'book_ids': tuple(book_ids)}).fetchall()
            # Group by book_id and format names with Material Icons
            author_dict = {}
            current_book_id = None
            current_authors = []
            for row in results:
                book_id, name = row.book_id, row.name
                if book_id != current_book_id:
                    if current_book_id is not None:
                        author_dict[current_book_id] = ", ".join(
                            f"""<span class="material-symbols-rounded" style="vertical-align: middle; font-size:12px;">person</span> {name}"""
                            for name in current_authors
                        ) if current_authors else "No authors"
                    current_book_id = book_id
                    current_authors = [name]
                else:
                    current_authors.append(name)
            # Handle the last group
            if current_book_id is not None:
                author_dict[current_book_id] = ", ".join(
                    f"""<span class="material-symbols-rounded" style="vertical-align: middle; font-size:12px;">person</span> {name}"""
                    for name in current_authors
                ) if current_authors else "No authors"
            return author_dict
    except Exception as e:
        st.error(f"Error fetching author names: {e}")
        return {book_id: f"Database error: {str(e)}" for book_id in book_ids}

@st.cache_data
def fetch_active_corrections(book_ids, _conn):
    if not book_ids:
        return pd.DataFrame(columns=['book_id', 'section', 'worker'])
    query = """
    SELECT book_id, section, worker
    FROM corrections
    WHERE book_id IN :book_ids AND correction_end IS NULL
    """
    try:
        return _conn.query(query, params={'book_ids': tuple(book_ids)}, show_spinner=False)
    except Exception as e:
        st.error(f"Error fetching active corrections: {e}")
        return pd.DataFrame(columns=['book_id', 'section', 'worker'])

# ------------------------------------------------------------------
# 1.  Harmonised palette  (light bg → dark text)
# ------------------------------------------------------------------
PALETTE = {
    "grey":  {"bg": "#f1f3f4", "text": "#5f6368", "dot": "#80868b"},
    "blue":  {"bg": "#e8f0fe", "text": "#1967d2", "dot": "#1967d2"},
    "green": {"bg": "#e6f4ea", "text": "#137333", "dot": "#137333"},
    "amber": {"bg": "#fef7e0", "text": "#b06000", "dot": "#f29900"},
    "teal":  {"bg": "#e0f2f1", "text": "#00796b", "dot": "#00796b"},
    "purple":{"bg": "#f3e5f5", "text": "#8e24aa", "dot": "#8e24aa"},
}

# ------------------------------------------------------------------
# 2.  Emoji map  (one icon per semantic state)
# ------------------------------------------------------------------
EMOJI = {
    "writing":      "✍️",
    "proofreading": "🔍",
    "formatting":   "📄",
    "cover":        "🎨",
    "print":        "🖨️",
    "dispatch":     "📦",
    "live":         "🌐",
    "links":        "🔗",
    "ready":        "📚",
    "complete":     "✅",
}

# ------------------------------------------------------------------
# 3.  Base pill CSS (unchanged mechanics)
# ------------------------------------------------------------------
PILL_CSS = (
    "padding:7px 8px;"
    "border-radius:10px;"
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
    "display:flex;flex-direction:column;align-items:flex-start;"
    "border:1px solid {border};"
    "box-shadow:0 2px 4px rgba(0,0,0,.06);"
    "line-height:1.5;gap:4px;min-width:120px;width:fit-content;"
    "transition:transform .15s;"
    "{{}}"
)

# ------------------------------------------------------------------
# 4.  Re-usable pill builder
# ------------------------------------------------------------------
def pill(text: str, colour_key: str, emoji_key: str = "") -> str:
    """
    Build a single pill.
    colour_key must be a key in PALETTE.
    emoji_key  must be a key in EMOJI (or "" for no icon).
    """
    col  = PALETTE[colour_key]
    icon = EMOJI.get(emoji_key, "")
    return (
        f'<div style="{PILL_CSS.format(border=col["bg"])}">'
        f'<span style="color:{col["text"]};font-size:11.5px;font-weight:500;">'
        f"{icon}{text}"
        f"</span></div>"
    )


def get_status_pill(book_id, row, authors_grouped, printeditions_grouped, corrections_grouped):
    # ---------- shortcuts ----------
    is_publish_only   = row.get("is_publish_only", 0) == 1
    is_thesis_to_book = row.get("is_thesis_to_book", 0) == 1
    skip_writing      = is_publish_only or is_thesis_to_book
    correction_status = row.get("correction_status", "None")

    # ---------- operations status ----------
    operations = [
        ("writing",      "Writing",       "Writing Complete",      "blue"),
        ("proofreading", "Proofreading",  "Proofreading Complete", "blue"),
        ("formatting",   "Formatting",    "Formatting Complete",   "blue"),
        ("cover",        "Cover Design",  "Cover Complete",        "blue"),
    ]

    # Filter out writing stage if skip_writing is True
    if skip_writing:
        operations = [op for op in operations if op[0] != "writing"]

    ops_status, ops_colour, ops_emoji = "⏳Not Started", "grey", ""
    name_map = {s: f"{s}_by" for s, _, _, _ in operations}
    completed_stages = []
    current_stage = None

    for stage, in_prog, done, col_key in operations:
        start_f, end_f = f"{stage}_start", f"{stage}_end"
        started = pd.notnull(row.get(start_f))
        ended = pd.notnull(row.get(end_f))

        if ended:
            completed_stages.append(stage)
        elif started:
            current_stage = (in_prog, done, col_key, stage, row.get(name_map[stage], "Unknown") or "Unknown")
            break  # Stop at the first in-progress stage

    # Determine status based on current stage or completed stages
    required_stages = [s for s, _, _, _ in operations]
    if len(completed_stages) == len(required_stages):
        # Initial Operations Complete - Check for Corrections
        if correction_status and correction_status != "None":
            active_corr = corrections_grouped.get(book_id, pd.DataFrame())
            if not active_corr.empty:
                # Show active task in correction cycle
                task = active_corr.iloc[0]
                ops_status = f"Correction: {task['section'].capitalize()} by {task['worker']}"
                ops_colour = "amber"
                ops_emoji = task['section'].lower()
            else:
                # Pending start of correction stage
                ops_status = f"Correction: Pending in {correction_status}"
                ops_colour = "blue"
                ops_emoji = correction_status.lower()
        else:
            ops_status, ops_colour, ops_emoji = "Operations Complete", "green", "complete"
    elif current_stage:
        in_prog, _, col_key, stage, name = current_stage
        ops_status, ops_colour, ops_emoji = f"{in_prog} by {name}", col_key, stage
    elif completed_stages:
        # Show the last completed stage
        last_stage = completed_stages[-1]
        for stage, _, done, col_key in operations:
            if stage == last_stage:
                ops_status, ops_colour, ops_emoji = done, "green", "complete"
                break

    # ---------- author checklist (INTERNAL ONLY) ----------
    checklist_fields = [
        ("welcome_mail_sent",    "Welcome Mail",        "amber"),
        ("cover_agreement_sent", "Cover / Agreement",   "amber"),
        ("author_details_sent",  "Author Details",      "amber"),
        ("photo_recive",         "Photo",               "amber"),
        ("id_proof_recive",      "ID Proof",            "amber"),
        ("agreement_received",   "Agreement",           "amber"),
        ("digital_book_sent",    "Digital Proof",       "amber"),
        ("printing_confirmation","Print Confirmation",  "amber"),
    ]

    def _author_checklist_complete() -> bool:
        book_authors = authors_grouped.get(book_id, pd.DataFrame())
        if book_authors.empty:
            return True
        for _, author in book_authors.iterrows():
            for field, _, _ in checklist_fields:
                if not author[field]:
                    return False
        return True

    author_ok = _author_checklist_complete()

    # ---------- ISBN check ----------
    _isbn_raw = row.get('isbn')
    isbn_ok = bool(_isbn_raw and str(_isbn_raw).strip() not in ("", "None"))

    # ---------- early exits ----------
    if row.get("deliver") == 1:
        links = ["flipkart_link", "agph_link", "amazon_link", "images"]
        # normalise the field content
        def _ok(f):
            v = str(row.get(f, "")).strip()
            return v and v not in ("[]", "null", "None")

        all_good = all(_ok(f) for f in links)
        return pill("Book Live" if all_good else "Online Links Pending",
                    "green" if all_good else "amber",
                    "live" if all_good else "links")

    prints = printeditions_grouped.get(book_id, pd.DataFrame())
    if not prints.empty:
        latest = prints.sort_values("print_id", ascending=False).iloc[0]
        if latest["status"] == "Received":
            return pill("Ready For Dispatch", "green", "dispatch")
        if latest["status"] == "In Printing":
            return pill("In Printing", "amber", "print")

    # ---------- ready-for-print gate ----------
    if ops_status == "Operations Complete":
        if author_ok and isbn_ok:
            return pill("Ready For Print", "green", "ready")
        else:
            # stay on “Operations Complete” – do NOT reveal checklist
            return pill("Operations Complete", "green", "complete")

    # ---------- default ----------
    return pill(ops_status, ops_colour, ops_emoji)
    

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

        server = smtplib.SMTP(GMAIL_SMTP_SERVER, GMAIL_SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

def send_otp_email(to_email, otp):
    try:
        email_addr = st.secrets["ag_volumes_mail"]["EMAIL_ADDRESS"]
        email_pass = st.secrets["ag_volumes_mail"]["EMAIL_PASSWORD"]
        
        msg = MIMEMultipart()
        msg["From"] = email_addr
        msg["To"] = to_email
        msg["Subject"] = "Admin Password Change OTP"
        
        body = f"Your OTP for changing the admin password is: {otp}\nThis OTP is valid for 10 minutes."
        msg.attach(MIMEText(body, "plain"))
        
        # Use GMAIL_SMTP_SERVER and GMAIL_SMTP_PORT as they are standard for Gmail, or use what's in secrets if appropriate.
        # Based on existing send_email, it uses GMAIL_SMTP_SERVER and GMAIL_SMTP_PORT.
        server = smtplib.SMTP(st.secrets["email_servers"]["GMAIL_SMTP_SERVER"], st.secrets["email_servers"]["GMAIL_SMTP_PORT"])
        server.starttls()
        server.login(email_addr, email_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Failed to send OTP email: {e}")
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


def fetch_tags(conn):

    try:
        # Fetch and process tags
        with conn.session as s:
            tag_query = text("SELECT tags FROM books WHERE tags IS NOT NULL AND tags != ''")
            all_tags = s.execute(tag_query).fetchall()
            
            unique_tags = set()
            for row in all_tags[:5]:
                if row[0] and isinstance(row[0], str):
                    try:
                        tags = json.loads(row[0])  # Parse JSON array
                        unique_tags.update(tags)
                    except json.JSONDecodeError:
                        st.error(f"Invalid JSON in tags: {row[0]} -> Skipped")
                else:
                    st.error(f"Raw tag: {row[0]} -> Skipped (invalid or empty)")
            
            # Collect unique tags from all rows
            for row in all_tags:
                if row[0] and isinstance(row[0], str):
                    try:
                        tags = json.loads(row[0])
                        unique_tags.update(tags)
                    except json.JSONDecodeError:
                        st.write(f"Invalid JSON in tags: {row[0]} -> Skipped")
            
            # Convert to sorted list
            sorted_tags = sorted(unique_tags)

            return sorted_tags
    except Exception as e:
        st.error(f"Error fetching tags: {e}")
        return []


###################################################################################################################################
##################################--------------- Manage Users ----------------------------##################################
###################################################################################################################################


@st.dialog("Settings", width="large", on_dismiss='rerun')
def settings_dialog(conn):
    # Check if user is admin
    if st.session_state.get("role", None) != "admin":
        st.error("❌ Access Denied: Only admins can access settings.")
        return

    # Initialize session state (from manage_users)
    if "show_passwords" not in st.session_state:
        st.session_state.show_passwords = False
    if "confirm_delete_user_id" not in st.session_state:
        st.session_state.confirm_delete_user_id = None
    if "show_passwords_prev" not in st.session_state:
        st.session_state.show_passwords_prev = st.session_state.show_passwords
    if "selected_user_for_edit" not in st.session_state:
        st.session_state.selected_user_for_edit = None

    settings_tab1, settings_tab2 = st.tabs(["👥 Manage Users", "📤 Export Data"])

    with settings_tab1:
            # Check if user is admin
            if st.session_state.get("role", None) != "admin":
                st.error("❌ Access Denied: Only admins can manage users.")
                return

            # Initialize session state
            if "show_passwords" not in st.session_state:
                st.session_state.show_passwords = False
            if "confirm_delete_user_id" not in st.session_state:
                st.session_state.confirm_delete_user_id = None
            if "show_passwords_prev" not in st.session_state:
                st.session_state.show_passwords_prev = st.session_state.show_passwords
            if "selected_user_for_edit" not in st.session_state:
                st.session_state.selected_user_for_edit = None

            # Fetch unique publishing consultants
            try:
                with conn.session as s:
                    publishing_consultants = s.execute(
                        text("SELECT DISTINCT publishing_consultant FROM book_authors WHERE publishing_consultant IS NOT NULL AND publishing_consultant != '' ORDER BY publishing_consultant")
                    ).fetchall()
                    publishing_consultant_names = [pc[0] for pc in publishing_consultants]
            except Exception as e:
                st.error(f"❌ Error fetching publishing consultants: {str(e)}")
                publishing_consultant_names = []

            # Database cleanup
            try:
                with conn.session as s:
                    for correct_access in ACCESS_TO_BUTTON.keys():
                        s.execute(
                            text("""
                                UPDATE user_app_access 
                                SET access_type = :correct_access 
                                WHERE LOWER(access_type) = LOWER(:correct_access)
                                AND access_type != :correct_access
                            """),
                            {"correct_access": correct_access}
                        )
                    s.commit()
            except Exception as e:
                st.error(f"❌ Database error during cleanup: {str(e)}")
                return

            # Fetch all users
            try:
                with conn.session as s:
                    users = s.execute(
                        text("""
                            SELECT u.id, u.username, u.email, u.associate_id, u.designation, u.password, u.role, 
                                   GROUP_CONCAT(uaa.app) as apps, GROUP_CONCAT(uaa.access_type) as access_types,
                                   GROUP_CONCAT(uaa.level) as levels, MIN(uaa.start_date) as start_date,
                                   GROUP_CONCAT(DISTINCT 
                                       CASE WHEN uaa.app = 'tasks' AND uaa.level IN ('worker', 'both') AND uaa.report_to IS NOT NULL 
                                            THEN (SELECT username FROM userss WHERE id = uaa.report_to) 
                                            ELSE NULL END
                                   ) as report_to
                            FROM userss u
                            LEFT JOIN user_app_access uaa ON u.id = uaa.user_id
                            GROUP BY u.id, u.username, u.email, u.associate_id, u.designation, u.password, u.role
                            ORDER BY u.username
                        """)
                    ).fetchall()
            except Exception as e:
                st.error(f"❌ Database error while fetching users: {str(e)}")
                return
    
            # App configurations
            app_display_names = list(VALID_APPS.keys())
            app_db_values = {display: db_value for display, db_value in VALID_APPS.items()}
            FULL_ACCESS_APPS = ["IJISEM", "Tasks", "Sales"]
            LEVEL_SUPPORT_APPS = ["IJISEM", "Tasks", "Operations", "Sales"]

            # Create 3 tabs
            col_nav, col_content = st.columns([0.5, 5])
            with col_nav:
                selected_user_tab = st.radio("Manage Users", ["Users", "Edit User", "Add User"], label_visibility="collapsed")

            with col_content:
                if selected_user_tab == "Users":
                    st.write("### Users Overview")
                    if not users:
                        st.error("❌ No users found in database.")
                    else:
                        show_passwords = st.checkbox(
                            "🔓 Show Passwords",
                            value=st.session_state.show_passwords,
                            key="toggle_passwords",
                            help="Check to reveal all passwords in the table"
                        )
                        if show_passwords:
                            st.toast("⚠️ Warning: Passwords are visible. Ensure you are in a secure environment.", icon="⚠️")

                        if show_passwords != st.session_state.show_passwords_prev:
                            try:
                                log_activity(
                                    conn, st.session_state.user_id, st.session_state.username,
                                    st.session_state.session_id, "toggled checkbox",
                                    f"Show Passwords changed to '{show_passwords}'"
                                )
                                st.session_state.show_passwords = show_passwords
                                st.session_state.show_passwords_prev = show_passwords
                            except Exception as e:
                                st.error(f"❌ Error logging activity: {str(e)}")

                        user_data = [{
                            "ID": user.id, "Username": user.username, "Email": user.email or "",
                            "Associate ID": user.associate_id or "", "Designation": user.designation or "",
                            "Password": user.password if st.session_state.show_passwords else "••••••••",
                            "Real_Password": user.password, "Role": user.role.capitalize() if user.role else "",
                            "Apps": user.apps or "", "Access Types": user.access_types or "",
                            "Levels": user.levels or "", "Reports To": user.report_to or "",
                            "Start Date": user.start_date
                        } for user in users]
            
                        df = pd.DataFrame(user_data)
                        st.data_editor(
                            df, width="stretch", hide_index=True,
                            disabled=["ID", "Username", "Email", "Associate ID", "Designation", 
                                     "Password", "Real_Password", "Role", "Apps", "Access Types", 
                                     "Levels", "Reports To", "Start Date"],
                            column_config={
                                "ID": st.column_config.NumberColumn("ID", disabled=True),
                                "Password": st.column_config.TextColumn("Password"),
                                "Real_Password": None,
                                "Role": st.column_config.SelectboxColumn("Role", options=["Admin", "User"]),
                                "Start Date": st.column_config.DateColumn("Start Date")
                            },
                            column_order=["ID", "Username", "Email", "Password", "Associate ID", "Designation", 
                                         "Role", "Apps", "Access Types", "Levels", "Reports To", 
                                         "Start Date"],
                            num_rows="fixed", key="user_table"
                        )

                elif selected_user_tab == "Edit User":

                    tab_col1, _ = st.columns([2,1])

                    with tab_col1:
                        st.write("### ✏️ Edit Existing User")
                        if not users:
                            st.error("❌ No users found in database.")
                            st.stop()

                        with st.container(border=True):
                            user_dict = {f"{user.username} (ID: {user.id})": user for user in users}
                            selected_user_key = st.selectbox(
                                "Select User to Edit", 
                                options=list(user_dict.keys()), 
                                key="edit_user_select",
                                format_func=lambda x: x
                            )
                            selected_user = user_dict[selected_user_key]

                            # Reset OTP state if user changes
                            if "last_selected_user_id" not in st.session_state or st.session_state.last_selected_user_id != selected_user.id:
                                st.session_state.last_selected_user_id = selected_user.id
                                st.session_state.admin_otp_verified = False
                                st.session_state.admin_otp_sent = False
                                if "admin_otp" in st.session_state: 
                                    del st.session_state.admin_otp

                        with st.container(border=True):
                
                            if selected_user.id == 1:
                                st.warning("⚠️ Primary admin (ID: 1) - Limited editing capabilities.")
                                
                                if not st.session_state.get("admin_otp_verified", False):
                                    st.info("🔒 Identity verification required to change admin password.")

                                    if st.button("📧 Send OTP to Admin", key="send_admin_otp_btn", use_container_width=True):
                                        otp = str(random.randint(100000, 999999))
                                        st.session_state.admin_otp = otp
                                        if send_otp_email(selected_user.email, otp):
                                            st.session_state.admin_otp_sent = True
                                            log_activity(
                                                conn, st.session_state.user_id, st.session_state.username,
                                                st.session_state.session_id, "sent otp",
                                                f"OTP sent to admin email: {selected_user.email}"
                                            )
                                            st.success(f"OTP sent to {selected_user.email}")
                                        else:
                                            st.error("Failed to send OTP.")
                                    
                                    if st.session_state.get("admin_otp_sent"):
                                        entered_otp = st.text_input("Enter OTP", key="admin_otp_input", label_visibility="collapsed", placeholder="Enter OTP")

                                        if st.button("✅ Verify OTP", key="verify_admin_otp_btn", use_container_width=True):
                                            if entered_otp == st.session_state.get("admin_otp"):
                                                st.session_state.admin_otp_verified = True
                                                log_activity(
                                                    conn, st.session_state.user_id, st.session_state.username,
                                                    st.session_state.session_id, "verified otp",
                                                    "Admin identity verified via OTP"
                                                )
                                                st.success("Verified!")
                                            else:
                                                log_activity(
                                                    conn, st.session_state.user_id, st.session_state.username,
                                                    st.session_state.session_id, "otp verification failed",
                                                    f"Invalid OTP entered: {entered_otp}"
                                                )
                                                st.error("Invalid OTP")

                            # Check if current user is Sales app user
                            try:
                                with conn.session as s:
                                    uaa = s.execute(
                                        text("SELECT app, access_type, level, report_to, start_date FROM user_app_access WHERE user_id = :user_id"),
                                        {"user_id": selected_user.id}
                                    ).fetchone()
                                    is_sales_user = uaa and uaa.app and uaa.app.lower() == 'sales'
                                    current_app_db = uaa.app if uaa else None
                                    current_access_type = uaa.access_type if uaa else None
                                    current_level = uaa.level if uaa else None
                                    current_report_to = uaa.report_to if uaa else None
                                    current_start_date = uaa.start_date if uaa else None
                            except:
                                is_sales_user = False
                                current_app_db = None
                                current_access_type = None
                                current_level = None
                                current_report_to = None
                                current_start_date = None

                            current_app_display = next((display for display, db_val in app_db_values.items() if db_val == current_app_db), "Main")

                            # Basic Information Section
                            st.subheader("👤 Basic Information")
                            col1, col2 = st.columns(2)
                            with col1:
                                # Identity check for admin
                                is_admin_verified = True
                                if selected_user.id == 1 and not st.session_state.get("admin_otp_verified", False):
                                    is_admin_verified = False

                                if is_sales_user and publishing_consultant_names:
                                    st.text_input(
                                        "Username", value=selected_user.username, disabled=True,
                                        help="💡 Sales users must use publishing consultant names. Contact admin to change."
                                    )
                                    new_username = selected_user.username
                                    st.info(f"👤 Publishing Consultant: **{new_username}**")
                                else:
                                    new_username = st.text_input(
                                        "Username", value=selected_user.username,
                                        key=f"edit_username_{selected_user.id}",
                                        disabled=not is_admin_verified
                                    )
                    
                                new_email = st.text_input(
                                    "Email", value=selected_user.email or "",
                                    key=f"edit_email_{selected_user.id}",
                                    disabled=not is_admin_verified
                                )
                
                            with col2:
                                # Disable password change for admin if not verified
                                new_password = st.text_input(
                                    "Password", value="", type="password",
                                    key=f"edit_password_{selected_user.id}",
                                    placeholder="Leave empty to keep current" if is_admin_verified else "Verify identity to change",
                                    disabled=not is_admin_verified
                                )
                    
                                current_role = selected_user.role.capitalize() if selected_user.role in ["admin", "user"] else "User"
                                if selected_user.id == 1:
                                    st.selectbox("Role", options=["Admin"], disabled=True, key=f"edit_role_{selected_user.id}")
                                    new_role = "Admin"
                                else:
                                    new_role = st.selectbox(
                                        "Role", options=["Admin", "User"],
                                        index=["Admin", "User"].index(current_role),
                                        key=f"edit_role_{selected_user.id}"
                                    )

                            # Application and Access Section
                            st.write("---")
                            st.subheader("🔧 Application & Access")
                            col_app1, col_app2 = st.columns([0.5,2])
                            with col_app1:
                                if new_role == "Admin":
                                    st.selectbox("Application", options=["Main"], disabled=True, key=f"edit_app_admin_{selected_user.id}")
                                    new_app = "Main"
                                else:
                                    new_app = st.selectbox(
                                        "Application", options=app_display_names,
                                        format_func=lambda x: x.capitalize(),
                                        index=app_display_names.index(current_app_display) if current_app_display in app_display_names else 0,
                                        key=f"edit_app_select_{selected_user.id}"
                                    )

                            with col_app2:
                                access_options = (
                                    list(ACCESS_TO_BUTTON.keys()) if new_app == "Main"
                                    else ["writer", "proofreader", "formatter", "cover_designer"] if new_app == "Operations"
                                    else ["Full Access"] if new_app in FULL_ACCESS_APPS else []
                                )
                    
                                current_access = current_access_type.split(",") if current_access_type else []
                                current_access = [acc.strip() for acc in current_access if acc.strip() in access_options]
                    
                                if new_app == "Main":
                                    new_access_type = st.multiselect(
                                        "Access Permissions", options=access_options,
                                        default=current_access, key=f"edit_access_type_{selected_user.id}",
                                        disabled=selected_user.id == 1
                                    )
                                elif new_app in FULL_ACCESS_APPS:
                                    default_access = current_access_type if current_access_type in access_options else "Full Access"
                                    new_access_type = st.selectbox(
                                        "Access Permissions", options=access_options,
                                        index=access_options.index(default_access) if default_access in access_options else 0,
                                        key=f"edit_access_type_full_{selected_user.id}",
                                        disabled=selected_user.id == 1
                                    )
                                else:
                                    default_access = current_access_type if current_access_type in access_options else (access_options[0] if access_options else "")
                                    new_access_type = st.selectbox(
                                        "Access Permissions", options=access_options,
                                        index=access_options.index(default_access) if default_access in access_options else 0,
                                        key=f"edit_access_type_ops_{selected_user.id}",
                                        disabled=selected_user.id == 1
                                    )

                            # Additional Information
                            st.write("---")
                            st.subheader("📋 Additional Information")
                            col_add1, col_add2 = st.columns(2)
                            with col_add1:
                                new_associate_id = st.text_input(
                                    "Associate ID", value=selected_user.associate_id or "",
                                    key=f"edit_associate_id_{selected_user.id}"
                                )
                            with col_add2:
                                new_designation = st.text_input(
                                    "Designation", value=selected_user.designation or "",
                                    key=f"edit_designation_{selected_user.id}"
                                )

                            # Level and Reports To
                            show_level_report = new_app in LEVEL_SUPPORT_APPS or (new_app == "Main" and isinstance(new_access_type, list) and new_access_type and "Tasks" in new_access_type)
                            if show_level_report:
                                st.write("---")
                                col_level1, col_level2 = st.columns(2)
                                with col_level1:
                                    current_level_display = "Worker" if current_level == "worker" else "Reporting Manager" if current_level == "reporting_manager" else "Both"
                                    new_level_display = st.selectbox(
                                        "Access Level", options=["Worker", "Reporting Manager", "Both"],
                                        index=["Worker", "Reporting Manager", "Both"].index(current_level_display) if current_level_display in ["Worker", "Reporting Manager", "Both"] else 0,
                                        key=f"edit_level_{selected_user.id}",
                                        disabled=selected_user.id == 1
                                    )
                                    new_level = new_level_display.lower().replace(" ", "_")
                    
                                with col_level2:
                                    if new_level in ["worker", "both"]:
                                        report_to_options = ["None"] + [f"{user.username} (ID: {user.id})" for user in users]
                                        current_report_to_display = "None"
                                        if current_report_to:
                                            try:
                                                with conn.session as s:
                                                    report_user = s.execute(
                                                        text("SELECT username FROM userss WHERE id = :id"),
                                                        {"id": current_report_to}
                                                    ).fetchone()
                                                    if report_user:
                                                        current_report_to_display = f"{report_user[0]} (ID: {current_report_to})"
                                            except:
                                                pass
                            
                                        new_report_to_display = st.selectbox(
                                            "Reports To", options=report_to_options,
                                            index=report_to_options.index(current_report_to_display),
                                            key=f"edit_report_to_{selected_user.id}",
                                            disabled=selected_user.id == 1
                                        )
                                        new_report_to = new_report_to_display.split(" (ID: ")[1][:-1] if " (ID: " in new_report_to_display else None
                                    else:
                                        new_report_to = None
                                        st.selectbox("Reports To", options=["None"], disabled=True, key=f"edit_report_to_disabled_{selected_user.id}")
                            else:
                                new_level = None
                                new_report_to = None

                            # Start Date
                            new_start_date = st.date_input(
                                "Start Date", value=current_start_date,
                                key=f"edit_start_date_{selected_user.id}",
                                disabled=new_app != "Main" or selected_user.id == 1
                            )

                            # Action Buttons
                            st.write("---")
                            col_btn1, col_btn2 = st.columns([3, 1])
                            with col_btn1:
                                if st.button("💾 Save Changes", key=f"save_edit_{selected_user.id}", type="primary", width='stretch'):
                                    if new_email and not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
                                        st.error("❌ Invalid email format.")
                                    else:
                                        try:
                                            with st.spinner("Saving changes..."):
                                                with conn.session as s:
                                                    # Update users table
                                                    s.execute(
                                                        text("""
                                                            UPDATE userss SET username = :username, email = :email,
                                                            associate_id = :associate_id, designation = :designation,
                                                            password = :password, role = :role WHERE id = :id
                                                        """),
                                                        {
                                                            "username": new_username,
                                                            "email": new_email or None,
                                                            "associate_id": new_associate_id or None,
                                                            "designation": new_designation or None,
                                                            "password": new_password if new_password else selected_user.password,
                                                            "role": new_role.lower(),
                                                            "id": selected_user.id
                                                        }
                                                    )
                                        
                                                    # Update user_app_access
                                                    s.execute(text("DELETE FROM user_app_access WHERE user_id = :user_id"), {"user_id": selected_user.id})
                                        
                                                    if new_role != "Admin" and new_app:
                                                        db_app_value = app_db_values.get(new_app, new_app.lower())
                                                        access_value = (
                                                            ",".join(new_access_type) if new_app == "Main" and isinstance(new_access_type, list) and new_access_type
                                                            else new_access_type if new_app in FULL_ACCESS_APPS + ["Operations"] and new_access_type
                                                            else None
                                                        )
                                                        s.execute(
                                                            text("""
                                                                INSERT INTO user_app_access (user_id, app, access_type, level, report_to, start_date)
                                                                VALUES (:user_id, :app, :access_type, :level, :report_to, :start_date)
                                                            """),
                                                            {
                                                                "user_id": selected_user.id, "app": db_app_value,
                                                                "access_type": access_value, "level": new_level,
                                                                "report_to": new_report_to, "start_date": new_start_date
                                                            }
                                                        )
                                                    s.commit()
                                    
                                                log_activity(
                                                    conn, st.session_state.user_id, st.session_state.username,
                                                    st.session_state.session_id, "updated user",
                                                    f"User ID: {selected_user.id}, Username: {new_username}"
                                                )
                                                st.success("✅ User Updated Successfully!")
                                                st.rerun()
                                        except Exception as e:
                                            error_message = str(e).lower()
                                            if "duplicate entry" in error_message and "'username'" in error_message:
                                                st.error("❌ Username already exists.")
                                            else:
                                                st.error(f"❌ Database error: {str(e)}")

                            with col_btn2:
                                if selected_user.id != 1:
                                    if st.button("🗑️ Delete", key=f"delete_{selected_user.id}", type="secondary"):
                                        st.session_state.confirm_delete_user_id = selected_user.id

                            if st.session_state.confirm_delete_user_id == selected_user.id:
                                st.warning(f"⚠️ Are you sure you want to delete {selected_user.username}?")
                                col_confirm1, col_confirm2 = st.columns(2)
                                with col_confirm1:
                                    if st.button("❌ Cancel", key=f"cancel_delete_{selected_user.id}"):
                                        st.session_state.confirm_delete_user_id = None
                                with col_confirm2:
                                    if st.button("🗑️ Confirm Delete", key=f"confirm_delete_{selected_user.id}", type="secondary"):
                                        try:
                                            with st.spinner("Deleting user..."):
                                                with conn.session as s:
                                                    s.execute(text("DELETE FROM user_app_access WHERE user_id = :id"), {"id": selected_user.id})
                                                    s.execute(text("DELETE FROM userss WHERE id = :id"), {"id": selected_user.id})
                                                    s.commit()
                                                log_activity(
                                                    conn, st.session_state.user_id, st.session_state.username,
                                                    st.session_state.session_id, "deleted user",
                                                    f"User ID: {selected_user.id}, Username: {selected_user.username}"
                                                )
                                                st.success("✅ User Deleted Successfully!")
                                                st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Database error: {str(e)}")
                                        st.session_state.confirm_delete_user_id = None

                elif selected_user_tab == "Add User":

                    tab3_col1, _ = st.columns([2,1])

                    with tab3_col1:
                        st.write("### ➕ Add New User")
                        with st.container(border=True):
                            # Role and Application Selection
                            st.subheader("🔧 Role & Application")
                            col_role1, col_role2 = st.columns(2)
                            with col_role1:
                                new_role = st.selectbox(
                                    "Role", options=["Admin", "User"],
                                    format_func=lambda x: x.capitalize(),
                                    key="add_role"
                                )
                
                            with col_role2:
                                if new_role == "Admin":
                                    st.selectbox("Application", options=["Main"], disabled=True, key="add_app_admin")
                                    new_app = "Main"
                                else:
                                    new_app = st.selectbox(
                                        "Application", options=app_display_names,
                                        format_func=lambda x: x.capitalize(),
                                        key="add_app_select"
                                    )

                            # Username Section
                            st.write("---")
                            st.subheader("👤 Username")
                            if new_role == "Admin":
                                new_username = st.text_input("Username", key="add_username_admin", placeholder="Admin username")
                            elif new_app == "Sales" and publishing_consultant_names:
                                st.info("💡 Sales users must use publishing consultant names for data integrity")
                                selected_consultant = st.selectbox(
                                    "Select Publishing Consultant",
                                    options=publishing_consultant_names,
                                    key="add_publishing_consultant",
                                    help="Username will be automatically set to the selected consultant name"
                                )
                                new_username = selected_consultant
                                st.success(f"✅ Username: **{new_username}**")
                            else:
                                new_username = st.text_input("Username", key="add_username", placeholder="Enter username")

                            # Contact Information
                            st.write("---")
                            st.subheader("📧 Contact Information")
                            col_contact1, col_contact2 = st.columns(2)
                            with col_contact1:
                                new_email = st.text_input("Email", key="add_email", placeholder="Enter email")
                            with col_contact2:
                                new_password = st.text_input("Password", type="password", key="add_password", placeholder="Enter password")

                            # Additional Information
                            st.write("---")
                            st.subheader("📋 Additional Information")
                            col_add1, col_add2 = st.columns(2)
                            with col_add1:
                                new_associate_id = st.text_input("Associate ID", key="add_associate_id", placeholder="Enter associate ID")
                            with col_add2:
                                new_designation = st.text_input("Designation", key="add_designation", placeholder="Enter designation")

                            # Access Permissions
                            if new_role != "Admin":
                                st.write("---")
                                st.subheader("🔐 Access Permissions")
                                with st.container(border=True):
                                    access_options = (
                                        list(ACCESS_TO_BUTTON.keys()) if new_app == "Main"
                                        else ["writer", "proofreader", "formatter", "cover_designer"] if new_app == "Operations"
                                        else ["Full Access"] if new_app in FULL_ACCESS_APPS else []
                                    )
                        
                                    if new_app == "Main":
                                        new_access_type = st.multiselect(
                                            "Access Permissions", options=access_options, default=[],
                                            key="add_access_type_select"
                                        )
                                    elif new_app in FULL_ACCESS_APPS:
                                        new_access_type = st.selectbox(
                                            "Access Permissions", options=access_options, index=0,
                                            key=f"add_access_type_full_{new_app.lower()}",
                                            help=f"{new_app} users have full access by default"
                                        )
                                    else:
                                        new_access_type = st.selectbox(
                                            "Access Permissions", options=access_options,
                                            key="add_access_type_operations"
                                        )

                                    # Level and Reports To
                                    show_level_report = new_app in LEVEL_SUPPORT_APPS or (new_app == "Main" and isinstance(new_access_type, list) and new_access_type and "Tasks" in new_access_type)
                                    if show_level_report:
                                        col_level1, col_level2 = st.columns(2)
                                        with col_level1:
                                            new_level_display = st.selectbox(
                                                "Access Level", options=["Worker", "Reporting Manager", "Both"],
                                                key="add_level_select"
                                            )
                                            new_level = new_level_display.lower().replace(" ", "_")
                                        with col_level2:
                                            if new_level in ["worker", "both"]:
                                                report_to_options = [f"{user.username} (ID: {user.id})" for user in users]
                                                new_report_to_display = st.selectbox(
                                                    "Reports To", options=["None"] + report_to_options,
                                                    key="add_report_to_select"
                                                )
                                                new_report_to = new_report_to_display.split(" (ID: ")[1][:-1] if new_report_to_display != "None" else None
                                            else:
                                                new_report_to = None
                                                st.selectbox("Reports To", options=["None"], disabled=True, key="add_report_to_disabled")
                                    else:
                                        new_level = None
                                        new_report_to = None

                            # Start Date
                            if new_app == "Main":
                                new_start_date = st.date_input("Start Date", key="add_start_date")
                            else:
                                new_start_date = None

                            # Add Button
                            if st.button("➕ Add User", key="add_user_btn", type="primary", width='stretch'):
                                if not new_username or not new_password:
                                    st.error("❌ Username and password are required.")
                                elif new_email and not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
                                    st.error("❌ Invalid email format.")
                                elif new_role != "Admin" and not new_app:
                                    st.error("❌ Application selection is required.")
                                elif new_app == "Sales" and not publishing_consultant_names:
                                    st.error("❌ No publishing consultants available.")
                                else:
                                    try:
                                        with st.spinner("Adding user..."):
                                            with conn.session as s:
                                                s.execute(
                                                    text("""
                                                        INSERT INTO userss (username, email, associate_id, designation, password, role)
                                                        VALUES (:username, :email, :associate_id, :designation, :password, :role)
                                                    """),
                                                    {
                                                        "username": new_username, "email": new_email or None,
                                                        "associate_id": new_associate_id or None,
                                                        "designation": new_designation or None,
                                                        "password": new_password, "role": new_role.lower()
                                                    }
                                                )
                                                new_user_id = s.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]
                                    
                                                if new_role != "Admin" and new_app:
                                                    db_app_value = app_db_values.get(new_app, new_app.lower())
                                                    access_value = (
                                                        ",".join(new_access_type) if new_app == "Main" and isinstance(new_access_type, list) and new_access_type
                                                        else new_access_type if new_app in FULL_ACCESS_APPS + ["Operations"] and new_access_type
                                                        else None
                                                    )
                                                    s.execute(
                                                        text("""
                                                            INSERT INTO user_app_access (user_id, app, access_type, level, report_to, start_date)
                                                            VALUES (:user_id, :app, :access_type, :level, :report_to, :start_date)
                                                        """),
                                                        {
                                                            "user_id": new_user_id, "app": db_app_value,
                                                            "access_type": access_value, "level": new_level,
                                                            "report_to": new_report_to, "start_date": new_start_date
                                                        }
                                                    )
                                                s.commit()
                                
                                            log_activity(
                                                conn, st.session_state.user_id, st.session_state.username,
                                                st.session_state.session_id, "added user",
                                                f"User ID: {new_user_id}, Username: {new_username}, Role: {new_role}, App: {new_app}"
                                            )
                                            st.success("✅ User Added Successfully!")
                                            st.rerun()
                                    except Exception as e:
                                        error_message = str(e).lower()
                                        if "duplicate entry" in error_message:
                                            if "'username'" in error_message:
                                                st.error("❌ Username already exists.")
                                            elif "'email'" in error_message:
                                                st.error("❌ Email already exists.")
                                            else:
                                                st.error(f"❌ Duplicate entry: {str(e)}")
                                        else:
                                            st.error(f"❌ Database error: {str(e)}")

        


        ###################################################################################################################################
        ##################################--------------- Export Data in PDF/Excel ----------------------------##################################
        ###################################################################################################################################




    with settings_tab2:

        def export_data():
                st.write(" ### Export Filtered Books as Excel")
                
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
                    
                    if st.button("Export to Excel", key="export_button", type="primary"):
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
                                log_activity(
                                    conn, st.session_state.user_id, st.session_state.username,
                                    st.session_state.session_id, "exported excel",
                                    f"Database: {database}, Options: {', '.join(export_options)}"
                                )
                                st.success(f"Data exported successfully and sent to Admin Email: {ADMIN_EMAIL}. Included: {', '.join(export_options)}")
                                st.toast(f"Data exported successfully and sent to Admin Email: {ADMIN_EMAIL}. Included: {', '.join(export_options)}", icon="✔️", duration="long")
                                st.balloons()
                            else:
                                st.error("Failed to send export email")



        def export_filtered_books_pdf(conn):
            st.write("### Export Filtered Books as PDF")

            global_col1, global_col2 = st.columns([0.9,1.5], gap="small")

            with global_col1:
                with st.container(border=True):
                    # Publisher filter (Radio button at the top)
                    publishers = conn.query("SELECT DISTINCT publisher FROM books WHERE publisher IS NOT NULL").publisher.tolist()
                    selected_publisher = st.radio("Publisher", ["All"] + publishers, index=0, key="filter_publisher", horizontal=True)
                    
                    # Delivery Status, Author Type, and Subject filters (side-by-side selectboxes)
                    col1, col2 = st.columns([1, 1], gap="small")
                    
                    with col1:
                        delivery_status = st.selectbox("Delivery Status", ["All", "Delivered", "Ongoing"], index=0, key="filter_delivery_status")
                    
                    with col2:
                        author_types = ["All", "Single", "Double", "Triple", "Multiple"]
                        selected_author_type = st.selectbox("Author Type", author_types, index=0, key="filter_author_type")
                    
                    # Subject filter
                    selected_subject = st.selectbox("Subject", ["All"] + VALID_SUBJECTS, index=0, key="filter_subject")
                    
                    # Tags filter (multiselect below)
                    sorted_tags = fetch_tags(conn)
                    selected_tags = st.multiselect("Tags", sorted_tags, help="Select tags to filter books", key="filter_tags")
                    
                    # Build query with filters, joining book_authors and authors to get author names and positions
                    query = """
                    SELECT b.images, b.title, b.isbn, b.book_mrp, b.publisher,
                        GROUP_CONCAT(CONCAT(a.name, ' (', ba.author_position, ')')) AS authors
                    FROM books b
                    LEFT JOIN book_authors ba ON b.book_id = ba.book_id
                    LEFT JOIN authors a ON ba.author_id = a.author_id
                    WHERE 1=1
                    """
                    params = {}
                    if selected_publisher != "All":
                        query += " AND b.publisher = :publisher"
                        params["publisher"] = selected_publisher
                    if delivery_status != "All":
                        query += " AND b.deliver = :deliver"
                        params["deliver"] = 1 if delivery_status == "Delivered" else 0
                    if selected_tags:
                        query += " AND (" + " OR ".join(["b.tags LIKE :tag" + str(i) for i in range(len(selected_tags))]) + ")"
                        for i, tag in enumerate(selected_tags):
                            params[f"tag{i}"] = f"%{tag}%"
                    if selected_author_type != "All":
                        query += " AND b.author_type = :author_type"
                        params["author_type"] = selected_author_type
                    if selected_subject != "All":
                        query += " AND b.subject = :subject"
                        params["subject"] = selected_subject
                    
                    query += " GROUP BY b.book_id, b.publisher, b.images, b.title, b.isbn, b.book_mrp"
                    
                    # Fetch filtered data for preview
                    df = conn.query(query, params=params)

                button_col1, button_col2 = st.columns([3.9,1.9], gap="small")   

                with button_col1:
                    # Export button
                    if st.button("Export to PDF", key="export_pdf_button", type="primary", disabled=df.empty):
                        with st.spinner("Generating PDF (This may take while)..."):
                            # Generate PDF using reportlab
                            pdf_output = io.BytesIO()
                            doc = SimpleDocTemplate(pdf_output, pagesize=A4, rightMargin=2.5*cm, leftMargin=2.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
                            elements = []
                            
                            # Styles
                            styles = getSampleStyleSheet()
                            title_style = ParagraphStyle(name='Title', fontName='Helvetica-Bold', fontSize=14, spaceAfter=8)
                            normal_style = ParagraphStyle(name='Normal', fontName='Helvetica', fontSize=8, spaceAfter=4, wordWrap='CJK')
                            summary_style = ParagraphStyle(name='Summary', fontName='Helvetica-Oblique', fontSize=8, spaceAfter=6)
                            
                            # Add title
                            elements.append(Paragraph("Exported Books Report", title_style))
                            elements.append(Spacer(1, 8))
                            elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d')}", normal_style))
                            elements.append(Spacer(1, 8))
                            
                            # Add summary
                            book_count = len(df)
                            publisher_text = selected_publisher if selected_publisher != "All" else "All Publishers"
                            tags_text = ", ".join(selected_tags) if selected_tags else "None"
                            subject_text = selected_subject if selected_subject != "All" else "All Subjects"
                            elements.append(Paragraph(f"Publisher: {publisher_text}", summary_style))
                            elements.append(Paragraph(f"Subject: {subject_text}", summary_style))
                            elements.append(Paragraph(f"Tags: {tags_text}", summary_style))
                            elements.append(Paragraph(f"Number of Books: {book_count}", summary_style))
                            elements.append(Spacer(1, 8))
                            
                            # Table data
                            table_data = [["Image", "Title", "Authors", "ISBN", "MRP", "Publisher"]]
                            for idx, row in df.iterrows():
                                image_url = row['images'] if pd.notna(row['images']) else ''
                                title = row['title'] if pd.notna(row['title']) else ''
                                authors = row['authors'] if pd.notna(row['authors']) else 'No Authors'
                                isbn = row['isbn'] if pd.notna(row['isbn']) else ''
                                mrp = str(row['book_mrp']) if pd.notna(row['book_mrp']) else ''
                                publisher_ = str(row['publisher']) if pd.notna(row['publisher']) else ''
                                
                                # Handle image (fetch from URL and compress/resize)
                                image_element = Paragraph("No Image", normal_style)
                                if image_url and image_url.startswith(('http://', 'https://')):
                                    try:
                                        response = requests.get(image_url, stream=True, timeout=5)
                                        if response.status_code == 200:
                                            # Load image with PIL
                                            pil_image = PILImage.open(io.BytesIO(response.content))
                                            # Resize to 100x150 pixels for compactness
                                            pil_image.thumbnail((100, 150), PILImage.Resampling.LANCZOS)
                                            # Save compressed to BytesIO as JPEG
                                            img_buffer = io.BytesIO()
                                            pil_image.convert('RGB').save(img_buffer, format='JPEG', quality=70, optimize=True)
                                            img_buffer.seek(0)
                                            # Load into reportlab Image
                                            image_element = Image(img_buffer, width=3*cm, height=4*cm)
                                    except Exception:
                                        pass
                                        
                                table_data.append([
                                    image_element,
                                    Paragraph(title, normal_style),
                                    Paragraph(authors, normal_style),
                                    Paragraph(isbn, normal_style),
                                    Paragraph(mrp, normal_style),
                                    Paragraph(publisher_, normal_style)
                                ])
                            
                            # Create table with modern styling
                            table = Table(table_data, colWidths=[3*cm, 4.5*cm, 5.5*cm, 2.7*cm, 1.5*cm, 1.5*cm])
                            table.setStyle(TableStyle([
                                # Header
                                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),  # Dark slate blue header
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0, 0), (-1, 0), 9),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                                ('TOPPADDING', (0, 0), (-1, 0), 6),
                                # Body
                                ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Center image
                                ('ALIGN', (1, 1), (-1, -1), 'LEFT'),   # Left-align text for readability
                                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
                                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                                ('FONTSIZE', (0, 1), (-1, -1), 8),
                                # Alternate row colors (clean and minimal)
                                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [
                                    colors.HexColor('#FFFFFF'),  # White
                                    colors.HexColor('#F7F9FB')   # Very light gray
                                ]),
                                # Grid & borders
                                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#D3D8E0')),  # Subtle gray grid
                                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#A0A8B3')),   # Clean outer border
                                # Padding for compactness
                                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                                ('TOPPADDING', (0, 1), (-1, -1), 3),
                            ]))
                            
                            elements.append(table)
                            
                            # Build PDF
                            try:
                                doc.build(elements)
                            except Exception as e:
                                st.error(f"Failed to generate PDF: {str(e)}")
                                st.toast(f"Failed to generate PDF: {str(e)}", icon="❌", duration="long")
                                return
                            
                            # Send email
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"Filtered_Books_{timestamp}.pdf"
                            subject = f"Filtered Books PDF Export"
                            body = f"Please find attached the filtered books report from the MIS database.\nFilters applied: Publisher={selected_publisher}, Delivery Status={delivery_status}, Subject={selected_subject}, Tags={', '.join(selected_tags) or 'None'}, Author Type={selected_author_type}"
                            
                            if send_email(subject, body, pdf_output.getvalue(), filename):
                                log_activity(
                                    conn, st.session_state.user_id, st.session_state.username,
                                    st.session_state.session_id, "exported pdf",
                                    f"Publisher: {selected_publisher}, Subject: {selected_subject}, Status: {delivery_status}"
                                )
                                st.success(f"PDF exported successfully and sent to Admin Email: {ADMIN_EMAIL}")
                                st.toast(f"PDF exported successfully and sent to Admin Email: {ADMIN_EMAIL}", icon="✔️", duration="long")
                                st.balloons()
                            else:
                                st.error("Failed to send export email")
                                st.toast("Failed to send export email", icon="❌", duration="long")

                with button_col2:
                    st.markdown(f"**Total Books: <span style='color:red;'>{len(df)}</span>**", unsafe_allow_html=True)
                
            with global_col2:
                # Display preview of filtered data
                if df.empty:
                    st.warning("No books match the selected filters.")
                else:
                    st.dataframe(
                        df[['images', 'title', 'authors', 'isbn', 'book_mrp', 'publisher']],
                        column_config={
                            "images": st.column_config.ImageColumn("Image"),
                            "title": "Book Title",
                            "authors": "Authors",
                            "isbn": "ISBN",
                            "book_mrp": st.column_config.NumberColumn("MRP", format="₹%.2f"),
                            "publisher": "Publisher",
                        },
                        width="stretch",
                        hide_index=True,
                    )

        col_exp_nav, col_exp_content = st.columns([0.7, 5])
        with col_exp_nav:
            selected_export_tab = st.radio("Export Data", ["Export as PDF", "Export as Excel"], label_visibility="collapsed")

        with col_exp_content:
            if selected_export_tab == "Export as PDF":
                export_filtered_books_pdf(conn)
            elif selected_export_tab == "Export as Excel":
                col1, _ = st.columns(2)
                with col1:
                    export_data()

###################################################################################################################################
##################################--------------- Edit Auhtor Details ----------------------------##################################
###################################################################################################################################


# Dialog for managing authors
@st.dialog("Manage Authors", width="medium", on_dismiss = 'rerun')
def edit_author_detail(conn):
    # Ensure columns exist
    try:
        with conn.session as s:
            s.execute(text("SELECT about_author, author_photo, city, state FROM authors LIMIT 1"))
    except Exception:
        # Columns likely missing, add them
        try:
            with conn.session as s:
                try:
                    s.execute(text("ALTER TABLE authors ADD COLUMN about_author TEXT"))
                except Exception:
                    pass
                try:
                    s.execute(text("ALTER TABLE authors ADD COLUMN author_photo TEXT"))
                except Exception:
                    pass
                try:
                    s.execute(text("ALTER TABLE authors ADD COLUMN city VARCHAR(255)"))
                except Exception:
                    pass
                try:
                    s.execute(text("ALTER TABLE authors ADD COLUMN state VARCHAR(255)"))
                except Exception:
                    pass
                s.commit()
        except Exception as e:
             st.error(f"Error updating database schema: {e}")

    # Fetch all authors from database
    with conn.session as s:
        authors = s.execute(
            text("SELECT author_id, name, email, phone, about_author, author_photo, city, state FROM authors ORDER BY name")
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
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            new_email = st.text_input(
                "Email",
                value=selected_author.email if selected_author.email is not None else "",
                key=f"email_{selected_author.author_id}"
            )
        with col_e2:
            new_phone = st.text_input(
                "Phone",
                value=selected_author.phone if selected_author.phone is not None else "",
                key=f"phone_{selected_author.author_id}"
            )
        
        col_e3, col_e4 = st.columns(2)
        with col_e3:
            new_city = st.text_input(
                "City",
                value=selected_author.city if selected_author.city is not None else "",
                key=f"city_{selected_author.author_id}"
            )
        with col_e4:
            new_state = st.text_input(
                "State",
                value=selected_author.state if selected_author.state is not None else "",
                key=f"state_{selected_author.author_id}"
            )
        
        # New Fields
        new_about_author = st.text_area(
            "About The Author",
            value=selected_author.about_author if selected_author.about_author is not None else "",
            key=f"about_{selected_author.author_id}",
            height=200
        )
        
        current_photo = selected_author.author_photo if selected_author.author_photo is not None else None
        uploaded_photo = st.file_uploader("Upload Author Photo", type=['jpg', 'png', 'jpeg'], key=f"photo_{selected_author.author_id}")

        if current_photo:
            st.success(f"Current Photo Available")
            if os.path.exists(current_photo):
                with open(current_photo, "rb") as file:
                    st.download_button(
                        label="⬇️ Download Current Photo",
                        data=file,
                        file_name=os.path.basename(current_photo),
                        mime="image/jpeg",
                         key=f"dl_{selected_author.author_id}"
                    )
            else:
                 st.warning("⚠️ Photo file record exists but file not found on server.")

        btn_col1, btn_col2 = st.columns([3, 1])

        with btn_col1:
            with st.container():
                if st.button("Save Changes", 
                            key=f"save_{selected_author.author_id}", 
                            type="primary",
                            width="stretch"):
                    with st.spinner("Saving changes..."):
                        import time
                        time.sleep(1)
                        # Track changes for logging
                        changes = []
                        if new_name != selected_author.name:
                            changes.append(f"Name changed from '{selected_author.name}' to '{new_name}'")
                        if new_email != (selected_author.email or ''):
                            changes.append(f"Email changed from '{selected_author.email or ''}' to '{new_email}'")
                        if new_phone != (selected_author.phone or ''):
                            changes.append(f"Phone changed from '{selected_author.phone or ''}' to '{new_phone}'")
                        if new_city != (selected_author.city or ''):
                            changes.append(f"City changed from '{selected_author.city or ''}' to '{new_city}'")
                        if new_state != (selected_author.state or ''):
                            changes.append(f"State changed from '{selected_author.state or ''}' to '{new_state}'")
                        if new_about_author != (selected_author.about_author or ''):
                             changes.append("Updated About Author")
                        
                       # Handle Photo Upload
                        photo_path = current_photo
                        if uploaded_photo:
                            try:
                                file_extension = os.path.splitext(uploaded_photo.name)[1]
                                # Use author name and ID for filename
                                author_name_clean = selected_author.name.replace(" ", "_").replace("/", "_").replace("\\", "_")
                                unique_filename = f"{author_name_clean}_{selected_author.author_id}{file_extension}"
                                save_path = os.path.join(AUTHOR_PHOTO_UPLOAD_DIR, unique_filename)
                                
                                if not os.path.exists(AUTHOR_PHOTO_UPLOAD_DIR):
                                    os.makedirs(AUTHOR_PHOTO_UPLOAD_DIR)
                                    
                                with open(save_path, "wb") as f:
                                    f.write(uploaded_photo.getbuffer())
                                
                                photo_path = save_path
                                changes.append("Updated Author Photo")
                            except Exception as e:
                                st.error(f"Failed to upload photo: {e}")
                                st.stop()

                        try:
                            with conn.session as s:
                                s.execute(
                                    text("""
                                        UPDATE authors 
                                        SET name = :name, 
                                            email = :email, 
                                            phone = :phone,
                                            city = :city,
                                            state = :state,
                                            about_author = :about_author,
                                            author_photo = :author_photo
                                        WHERE author_id = :author_id
                                    """),
                                    {
                                        "name": new_name,
                                        "email": new_email if new_email else None,
                                        "phone": new_phone if new_phone else None,
                                        "city": new_city if new_city else None,
                                        "state": new_state if new_state else None,
                                        "about_author": new_about_author if new_about_author else None,
                                        "author_photo": photo_path,
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
                            st.toast("Author Updated Successfully!", icon="✔️")
                        except Exception as e:
                            st.error(f"Failed to save changes: {str(e)}")
                            st.toast(f"Failed to save changes: {str(e)}", icon="❌", duration="long")

        with btn_col2:
            delete_key = f"delete_{selected_author.author_id}"
            if "confirm_delete" not in st.session_state:
                st.session_state["confirm_delete"] = False

            if st.button("🗑️", 
                        key=delete_key, 
                        type="secondary",
                        help=f"Delete {selected_author.name}",
                        width="stretch"):
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
                        import time
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
                            st.toast("Author Deleted Successfully!", icon="✔️", duration="long")
                            st.session_state["confirm_delete"] = False
                        except Exception as e:
                            st.error(f"Failed to delete author: {str(e)}")
                            st.toast(f"Failed to delete author: {str(e)}", icon="❌", duration="long")


###################################################################################################################################
##################################--------------- Add New Book & Auhtor ----------------------------##################################
###################################################################################################################################


# Predefined list of educational subjects
VALID_SUBJECTS = [
    "Mathematics", "Physics", "Chemistry", "Biology", "Computer Science",
    "History", "Geography", "Literature", "Economics", "Business Studies",
    "Political Science", "Sociology", "Psychology", "Engineering", "Medicine",
    "Education", "General Science", "Management", "Marketing", "Medical", "Self Help", 
    "Physical Education", "Commerce", "Law", "Social Science"
]

def find_closest_subject(suggested_subject):
    """Map suggested subject to the closest predefined subject."""
    if not suggested_subject:
        return "General Science"
    
    # Normalize and find closest match
    suggested_subject = suggested_subject.strip().lower()
    valid_subjects_lower = [s.lower() for s in VALID_SUBJECTS]
    
    # Exact match
    if suggested_subject in valid_subjects_lower:
        return VALID_SUBJECTS[valid_subjects_lower.index(suggested_subject)]
    
    # Find closest match using difflib
    closest = difflib.get_close_matches(suggested_subject, valid_subjects_lower, n=1, cutoff=0.6)
    if closest:
        return VALID_SUBJECTS[valid_subjects_lower.index(closest[0])]
    
    # Fallback
    return "General Science"

def generate_subject_with_ollama(book_title):
    """Generate a single concise subject using the Ollama gemma3:1b model."""
    try:
        prompt = f"""
        You are a book categorization assistant. Based on the book title, suggest a single, concise subject that best describes the book's educational content. The subject must be one of the following: {', '.join(VALID_SUBJECTS)}. Return only the subject name with no additional text or formatting.

        Book Title: {book_title}

        Example output: Physics
        """
        response = ollama.generate(model="gemma3:1b", prompt=prompt)
        raw_response = response['response'].strip()
        
        # Clean and map to valid subject
        subject = find_closest_subject(raw_response)
        
        if subject == "General Science" and raw_response and raw_response.lower() not in [s.lower() for s in VALID_SUBJECTS]:
            st.warning(f"No valid subject generated for '{book_title}'. Using fallback: General Science")
        
        return subject
    except Exception as e:
        st.error(f"Error generating subject for '{book_title}' with gemma3:1b: {str(e)}")
        return "General Science"  # Fallback on error

def generate_tags_with_ollama(book_title):
    """Generate tags using the Ollama gemma3:1b model and clean the output."""
    try:
        prompt = f"""
        You are a book tagging assistant for a book management system. 
        Based only on the given book title, generate exactly 3 to 4 concise and highly relevant tags. 

        Rules:
        - Tags must be single words or short phrases (max 2 words). 
        - Do not add filler or generic tags like 'book', 'novel', 'story', 'interesting', 'popular'.
        - Only return a comma-separated list with exactly 3 to 4 tags, no extra text.

        Book Title: {book_title}

        Example output: Social Security,AI,Machine Learning,Tourism,Management
        """
        response = ollama.generate(model="gemma3:1b", prompt=prompt)
        raw_response = response['response'].strip()
        
        # Clean the output to extract only comma-separated tags
        if raw_response.startswith("here are the tags") or "*" in raw_response or "-" in raw_response:
            lines = raw_response.split("\n")
            tags = []
            for line in lines:
                line = line.strip()
                if line.startswith("*") or line.startswith("-"):
                    tags.append(line.lstrip("*- ").strip())
                elif "," in line:
                    tags.extend([tag.strip() for tag in line.split(",") if tag.strip()])
        else:
            tags = [tag.strip() for tag in raw_response.split(",") if tag.strip()]
        
        # Ensure 3 to 4 tags: trim or pad with fallbacks
        tags = list(dict.fromkeys([tag.lower() for tag in tags if tag]))  # Remove duplicates and lowercase
        if len(tags) > 4:
            tags = tags[:4]  # Take first 4
        elif len(tags) < 3:
            # Fallback tags if insufficient
            fallback_tags = ["general", "education", "literature", "academic"]
            tags.extend(fallback_tags[:4 - len(tags)])  # Pad to 3 or 4
        
        if not tags:
            st.warning(f"No valid tags generated by gemma3:1b for '{book_title}'.")
            return []
        
        return tags
    except Exception as e:
        st.error(f"Failed to generate tags with gemma3:1b for '{book_title}': {str(e)}")
        return []
    

agph_email = st.secrets["agph_mail"]["EMAIL_ADDRESS"]
cipher_email = st.secrets["cipher_mail"]["EMAIL_ADDRESS"]
ag_volumes_email = st.secrets["ag_volumes_mail"]["EMAIL_ADDRESS"]


# Updated Configuration with specific SMTP settings per publisher
PUBLISHER_CONFIG = {
    "AGPH": {
        "name": "AG Publishing House", 
        "email": agph_email, 
        "secret_section": "agph_mail",
        "smtp_server": GMAIL_SMTP_SERVER,
        "smtp_port": GMAIL_SMTP_PORT
    },
    "Cipher": {
        "name": "Cipher Publishing", 
        "email": cipher_email, 
        "secret_section": "cipher_mail",
        "smtp_server": HOSTINGER_SMTP_SERVER,
        "smtp_port": HOSTINGER_SMTP_PORT
    },
    "AG Volumes": {
        "name": "AG Volumes", 
        "email": ag_volumes_email, 
        "secret_section": "ag_volumes_mail",
        "smtp_server": GMAIL_SMTP_SERVER,
        "smtp_port": GMAIL_SMTP_PORT
    },
}

def send_welcome_email(to_email, author_name, author_phone, book_title, book_id, author_id, author_position, publisher="AGPH"):
    """
    Sends a formatted HTML welcome email.
    Dynamically switches between SMTP_SSL (Port 465) and STARTTLS (Port 587).
    Returns: (bool, str) -> (Success Status, Sender Email Address)
    """
    if not to_email:
        return False, None
    
    # 1. Load Configuration
    config = PUBLISHER_CONFIG.get(publisher, PUBLISHER_CONFIG.get("AGPH"))
    if not config:
        st.error(f"Configuration for publisher '{publisher}' not found.")
        return False, None

    pub_name = config.get("name")
    pub_email = config.get("email")
    secret_section = config.get("secret_section")
    
    # Get specific server details, default to Gmail/587 if missing
    smtp_server = config.get("smtp_server", "smtp.gmail.com")
    smtp_port = config.get("smtp_port", 587)

    try:
        # 2. Load Credentials
        if secret_section in st.secrets:
            secrets_source = st.secrets[secret_section]
            email_address = secrets_source["EMAIL_ADDRESS"]
            email_password = secrets_source["EMAIL_PASSWORD"]
        else:
            st.error(f"Secrets section '{secret_section}' not found.")
            return False, None

        # 3. Construct Email
        msg = MIMEMultipart("alternative")
        msg['From'] = email_address
        msg['To'] = to_email
        msg['Subject'] = f"Publication Confirmation - {book_title} | {pub_name}"

        # HTML Body (Professional solid color header - deep blue)
        html_body = f"""
        <html>
          <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #2c3e50; max-width: 700px; margin: 0 auto; padding: 20px;">
            
            <div style="background-color: #1e4976; padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 24px; font-weight: 600; letter-spacing: 0.5px;">{pub_name}</h1>
                <p style="color: #b8d4f1; margin: 8px 0 0 0; font-size: 14px;">Publication Confirmation</p>
            </div>

            <div style="background-color: #ffffff; padding: 35px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px;">
                <p style="margin-top: 0;">Dear <strong>{author_name}</strong>,</p>
                
                <p>Thank you for choosing {pub_name}. We are pleased to confirm receipt of your publication request for "<strong>{book_title}</strong>".</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-left: 4px solid #1e4976; margin: 25px 0; border-radius: 4px;">
                    <p style="margin: 0; font-size: 15px;"><strong>Timeline:</strong> Publication process takes 30-45 days, with an additional 10-12 days for printing and delivery.</p>
                </div>

                <h3 style="color: #1e4976; margin-top: 30px; margin-bottom: 15px; font-size: 18px; border-bottom: 2px solid #e8f5e9; padding-bottom: 8px;">Submission Details</h3>
                
                <!-- Compact Table -->
                <table style="border-collapse: collapse; width: 100%; max-width: 420px; margin-bottom: 25px; font-size: 13px;">
                    <tr style="background-color: #f5f5f5;">
                        <td style="padding: 6px 10px; border: 1px solid #e0e0e0; font-weight: 600; width: 35%;">Book Title</td>
                        <td style="padding: 6px 10px; border: 1px solid #e0e0e0;">{book_title}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 10px; border: 1px solid #e0e0e0; font-weight: 600;">Book ID</td>
                        <td style="padding: 6px 10px; border: 1px solid #e0e0e0;">{book_id}</td>
                    </tr>
                    <tr style="background-color: #f5f5f5;">
                        <td style="padding: 6px 10px; border: 1px solid #e0e0e0; font-weight: 600;">Author Name</td>
                        <td style="padding: 6px 10px; border: 1px solid #e0e0e0;">{author_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 10px; border: 1px solid #e0e0e0; font-weight: 600;">Author Email</td>
                        <td style="padding: 6px 10px; border: 1px solid #e0e0e0;">{to_email}</td>
                    </tr>
                    <tr style="background-color: #f5f5f5;">
                        <td style="padding: 6px 10px; border: 1px solid #e0e0e0; font-weight: 600;">Author Phone</td>
                        <td style="padding: 6px 10px; border: 1px solid #e0e0e0;">{author_phone}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 10px; border: 1px solid #e0e0e0; font-weight: 600;">Author ID</td>
                        <td style="padding: 6px 10px; border: 1px solid #e0e0e0;">{author_id}</td>
                    </tr>
                    <tr style="background-color: #f5f5f5;">
                        <td style="padding: 6px 10px; border: 1px solid #e0e0e0; font-weight: 600;">Author Position</td>
                        <td style="padding: 6px 10px; border: 1px solid #e0e0e0;">{author_position}</td>
                    </tr>
                </table>

                <h3 style="color: #1e4976; margin-top: 30px; margin-bottom: 15px; font-size: 18px; border-bottom: 2px solid #e3f2fd; padding-bottom: 8px;">Required Documentation</h3>
                <p style="margin-bottom: 12px;">Please provide the following within <strong>24 hours</strong> by replying to this email:</p>
                <ol style="margin: 0; padding-left: 20px; line-height: 1.8;">
                    <li><strong>Author Profile:</strong> 100-150 words maximum</li>
                    <li><strong>Passport Size Photo:</strong> High-resolution image suitable for cover page</li>
                    <li><strong>ID Proof:</strong> Aadhar Card or PAN Card copy</li>
                    <li><strong>Full Name with Prefix:</strong> Include appropriate title (Dr., Prof., Mr., Ms., etc.)</li>
                    <li><strong>Payment Receipt:</strong> Digital copy</li>
                    <li><strong>Delivery Address:</strong> Complete address with pincode for author copy delivery</li>
                </ol>

                <div style="background-color: #fff8e1; border-left: 4px solid #f57c00; padding: 18px; margin: 25px 0; border-radius: 4px;">
                    <h4 style="margin: 0 0 12px 0; color: #e65100; font-size: 16px;">⚠️ Critical: ISBN Application Details</h4>
                    <p style="margin-bottom: 10px; font-size: 14px;">Please verify the following information carefully before submission:</p>
                    <ul style="margin: 10px 0; padding-left: 20px; font-size: 14px; line-height: 1.7;">
                        <li>Complete author name with correct prefix (Dr., Prof., Mr., Ms., etc.)</li>
                        <li>Professional designation</li>
                        <li>Exact formatting including spacing, punctuation, and capitalization</li>
                    </ul>
                </div>

                <div style="background-color: #e3f2fd; padding: 15px; border-radius: 4px; margin: 25px 0;">
                    <p style="margin: 0; font-size: 14px;">📧 <strong>Communication:</strong> All future updates regarding your publication will be sent to this email address. Please check regularly until publication is complete.</p>
                </div>

                <hr style="border: 0; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                
                <p style="font-size: 14px; color: #666;">For any queries or assistance, please contact us at:<br>
                <a href="mailto:{pub_email}" style="color: #1e4976; text-decoration: none; font-weight: 600;">{pub_email}</a></p>
                
                <p style="margin-bottom: 0; margin-top: 25px;">Best regards,<br>
                <strong style="color: #1e4976;">Team {pub_name}</strong></p>
            </div>
            <div style="text-align: center; padding: 20px; font-size: 12px; color: #999;">
                <p style="margin: 0;">© 2025 {pub_name}. All rights reserved.</p>
            </div>
          </body>
        </html>
        """
        msg.attach(MIMEText(html_body, 'html'))

        # 4. Connect to Server (Logic Branch for SSL vs TLS)
        # Port 465 = SSL (Hostinger), Port 587 = TLS (Gmail)
        
        if smtp_port == 465:
            # SSL Connection (Hostinger)
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(email_address, email_password)
                server.send_message(msg)
        else:
            # TLS Connection (Gmail)
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_address, email_password)
                server.send_message(msg)
            
        return True, email_address

    except Exception as e:
        st.error(f"Failed to send email to {to_email} via {publisher}: {str(e)}")
        return False, None

@st.dialog("Add New Book", width="large", on_dismiss = 'rerun')
def add_book_dialog(conn):
    # --- Helper Function to Ensure Backward Compatibility ---
    def ensure_author_fields(author):
        default_author = {
            "name": "",
            "email": "",
            "phone": "",
            "city": "",
            "state": "",
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

    def book_details_section(publisher, conn):
        with st.container(border=True):
            st.markdown("<h5 style='color: #4CAF50;'>Book Details</h5>", unsafe_allow_html=True)
            col1, col2 = st.columns([2, 0.6])
            book_title = col1.text_input("Book Title", placeholder="Enter Book Title..", key="book_title")
            book_date = col2.date_input("Date", value=date.today(), key="book_date")

            toggles_enabled = publisher in ["AGPH", "Cipher", "AG Volumes", "AG Classics"]

            col3, col4 = st.columns([3, 2], vertical_alignment="bottom")

            with col3:
                author_type = st.radio(
                    "Author Type",
                    ["Multiple", "Single", "Double", "Triple"],
                    key="author_type_radio",
                    horizontal=True,
                    disabled=not toggles_enabled
                )

            with col4:
                book_mode = st.segmented_control(
                    "Book Type",
                    options=["Publish Only", "Thesis to Book"],
                    key="book_mode_segment",
                    disabled=not toggles_enabled
                )

            if not toggles_enabled:
                st.warning("Author Type and Book Mode options are disabled for AG Kids and NEET/JEE publishers.")

            # Tags and subject will be generated at save time, no UI input
            return {
                "title": book_title,
                "date": book_date,
                "author_type": author_type if toggles_enabled else "Multiple",
                "is_publish_only": (book_mode == "Publish Only") if (book_mode and toggles_enabled) else False,
                "is_thesis_to_book": (book_mode == "Thesis to Book") if (book_mode and toggles_enabled) else False,
                "publisher": publisher,
                "tags": [],  # Placeholder, tags will be generated on save
                "subject": ""  # Placeholder, subject will be generated on save
            }


    def syllabus_upload_section(is_publish_only: bool, is_thesis_to_book: bool, toggles_enabled: bool):

        with st.container(border=True):

            st.markdown("<h5 style='color: #4CAF50;'>Book Syllabus</h5>", unsafe_allow_html=True)
            
            syllabus_file = None
            if not is_publish_only and not is_thesis_to_book and toggles_enabled:
                syllabus_file = st.file_uploader(
                    "Upload Book Syllabus",
                    type=["pdf", "docx", "jpg", "jpeg", "png"],
                    key="syllabus_upload",
                    help="Upload the book syllabus as a PDF, DOCX, or image file.",
                    label_visibility="collapsed"
                )
            else:
                if is_publish_only:
                    st.info("Syllabus upload is disabled for Publish Only books.")
                elif is_thesis_to_book:
                    st.info("Syllabus upload is disabled for Thesis to Book conversions.")
                else: # not toggles_enabled
                    st.info("Syllabus upload is disabled for AG Kids and NEET/JEE publishers.")
        
        return syllabus_file


    def book_note_section():

        with st.popover("Book Note", width="stretch"):

            with st.container(border=False):
                st.markdown("<h5 style='color: #4CAF50;'>Book Note</h5>", unsafe_allow_html=True)
                
                book_note = st.text_area(
                    "Book Note or Instructions",
                    key="book_note",
                    help="Enter any additional notes or instructions for the book (optional, max 1000 characters)",
                    max_chars=1000,
                    placeholder="Enter notes or special instructions for the book here...",
                    height=50,
                    label_visibility="collapsed"
                )
        
        return book_note


    def author_details_section(conn, author_type, publisher):
        author_section_disabled = publisher in ["AG Kids", "NEET/JEE"]

        if "authors" not in st.session_state:
            st.session_state.authors = [
                {"name": "", "email": "", "phone": "", "city": "", "state": "", "author_id": None, "author_position": f"{i+1}{'st' if i == 0 else 'nd' if i == 1 else 'rd' if i == 2 else 'th'}", "corresponding_agent": "", "publishing_consultant": ""}
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
                    st.toast(f"Error fetching agents/consultants: {e}", icon="❌", duration="long")
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
                            # --- Existing Author: Read-Only View ---
                            selected_author_id = int(selected_author.split('(ID: ')[1][:-1])
                            selected_author_details = next((a for a in all_authors if a.author_id == selected_author_id), None)
                            
                            if selected_author_details:
                                # Update session state with existing details
                                st.session_state.authors[i]["name"] = selected_author_details.name
                                st.session_state.authors[i]["email"] = selected_author_details.email
                                st.session_state.authors[i]["phone"] = selected_author_details.phone
                                st.session_state.authors[i]["author_id"] = selected_author_details.author_id

                                # Display Read-Only Details
                                st.markdown(f"""
                                    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 14px;">
                                        <strong>👤 Name:</strong> {selected_author_details.name}<br>
                                        <strong>📧 Email:</strong> {selected_author_details.email}<br>
                                        <strong>📱 Phone:</strong> {selected_author_details.phone}
                                    </div>
                                """, unsafe_allow_html=True)
                        
                        elif selected_author == "Add New Author" and not disabled:
                            # --- New Author: Editable Fields ---
                            st.session_state.authors[i]["author_id"] = None
                            
                            col1, col2 = st.columns(2)
                            st.session_state.authors[i]["name"] = col1.text_input(f"Author Name {i+1}", st.session_state.authors[i]["name"], key=f"name_{i}", placeholder="Enter Author name..", disabled=disabled)
                            # Placeholder for alignment if needed, or just let 'Position' take the next slot below or beside if layout allows.
                            # In original code, Position was col2. Let's keep Position editable for everyone.

                        # --- Common Editable Fields (Position, Agent, Consultant) ---
                        
                        # Calculate available positions for both cases
                        available_positions = ["1st", "2nd", "3rd", "4th"]
                        taken_positions = [a["author_position"] for a in st.session_state.authors if a != st.session_state.authors[i]]
                        available_positions = [p for p in available_positions if p not in taken_positions or p == st.session_state.authors[i]["author_position"]]

                        if selected_author != "Add New Author" and not disabled:
                             # For existing authors, we need a place for Position.
                             st.session_state.authors[i]["author_position"] = st.selectbox(
                                f"Position {i+1}",
                                available_positions,
                                index=available_positions.index(st.session_state.authors[i]["author_position"]) if st.session_state.authors[i]["author_position"] in available_positions else 0,
                                key=f"author_position_{i}",
                                disabled=disabled
                            )
                        elif selected_author == "Add New Author" and not disabled:
                             # For new authors, Position was in col2 next to Name.
                             st.session_state.authors[i]["author_position"] = col2.selectbox(
                                f"Position {i+1}",
                                available_positions,
                                index=available_positions.index(st.session_state.authors[i]["author_position"]) if st.session_state.authors[i]["author_position"] in available_positions else 0,
                                key=f"author_position_{i}",
                                disabled=disabled
                            )

                        if selected_author == "Add New Author" and not disabled:
                            col3, col4 = st.columns(2)
                            st.session_state.authors[i]["phone"] = col3.text_input(f"Phone {i+1}", st.session_state.authors[i]["phone"], key=f"phone_{i}", placeholder="Enter phone..", disabled=disabled)
                            st.session_state.authors[i]["email"] = col4.text_input(f"Email {i+1}", st.session_state.authors[i]["email"], key=f"email_{i}", placeholder="Enter email..", disabled=disabled)
                            
                            col_c1, col_c2 = st.columns(2)
                            st.session_state.authors[i]["city"] = col_c1.text_input(f"City {i+1}", st.session_state.authors[i]["city"], key=f"city_{i}", placeholder="Enter city..", disabled=disabled)
                            st.session_state.authors[i]["state"] = col_c2.text_input(f"State {i+1}", st.session_state.authors[i]["state"], key=f"state_{i}", placeholder="Enter state..", disabled=disabled)
                        
                        col5, col6 = st.columns(2)

                        selected_agent = col5.selectbox(
                            f"Corresponding Author/Agent {i+1}",
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
        
        # Validation for Book Details
        if not book_data["title"]:
            errors.append("Book title is required.")
        if not book_data["date"]:
            errors.append("Book date is required.")
        if not book_data["publisher"]:
            errors.append("Publisher is required.")
            
        # Validation for Authors (Publisher-specific)
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
        col1, col2 = st.columns([1.1, 1])
        with col1:
            publisher = publisher_section()
            book_data = book_details_section(publisher, conn)
            syllabus_file = syllabus_upload_section(
                book_data["is_publish_only"],
                book_data["is_thesis_to_book"],
                publisher in ["AGPH", "Cipher", "AG Volumes", "AG Classics"]
            )
            book_data["syllabus_file"] = syllabus_file
            book_note = book_note_section()
            book_data["book_note"] = book_note
        with col2:
            author_data = author_details_section(conn, book_data["author_type"], publisher)
            
            send_welcome = st.checkbox("Send welcome email to authors", 
                                       value=False, 
                                       key="send_welcome_chk", 
                                       disabled=True,
                                       help="Feature coming soon.")

    # Save, Clear, and Cancel Buttons
    col1, col2 = st.columns([7, 1])
    with col1:
        if st.button("Save", key="dialog_save", type="primary"):
            errors = validate_form(book_data, author_data, book_data["author_type"], publisher)
            if errors:
                st.error("\n".join(errors), icon="🚨")
            else:
                with st.status("Processing Book...", expanded=True) as status:
                    try:
                        # Generate tags and subject
                        if book_data["title"]:
                            st.write("🤖 Generating AI Tags & Subject...")
                            book_data["tags"] = generate_tags_with_ollama(book_data["title"])
                            book_data["subject"] = generate_subject_with_ollama(book_data["title"])
                        
                        st.write("💾 Saving Book Details...")
                        with conn.session as s:
                            # Handle syllabus file upload
                            syllabus_path = None
                            if book_data["syllabus_file"] and not book_data["is_publish_only"] and not book_data["is_thesis_to_book"]:
                                file_extension = os.path.splitext(book_data["syllabus_file"].name)[1]
                                unique_filename = f"syllabus_{book_data['title'].replace(' ', '_')}_{int(time.time())}{file_extension}"
                                syllabus_path_temp = os.path.join(SYLLABUS_UPLOAD_DIR, unique_filename)
                                if not os.access(SYLLABUS_UPLOAD_DIR, os.W_OK):
                                    st.error(f"No write permission for {SYLLABUS_UPLOAD_DIR}.")
                                    raise PermissionError(f"Cannot write to {SYLLABUS_UPLOAD_DIR}")
                                try:
                                    with open(syllabus_path_temp, "wb") as f:
                                        f.write(book_data["syllabus_file"].getbuffer())
                                    syllabus_path = syllabus_path_temp
                                except Exception as e:
                                    st.error(f"Failed to save syllabus file: {str(e)}")
                                    st.toast(f"Failed to save syllabus file: {str(e)}", icon="❌", duration="long")
                                    raise
                            
                            # Convert tags list to JSON
                            tags_json = json.dumps(book_data["tags"]) if book_data["tags"] else None

                            # Insert book with book note, tags, and subject
                            s.execute(text("""
                                INSERT INTO books (title, date, author_type, is_publish_only, is_thesis_to_book, publisher, syllabus_path, book_note, tags, subject)
                                VALUES (:title, :date, :author_type, :is_publish_only, :is_thesis_to_book, :publisher, :syllabus_path, :book_note, :tags, :subject)
                            """), params={
                                "title": book_data["title"],
                                "date": book_data["date"],
                                "author_type": book_data["author_type"],
                                "is_publish_only": book_data["is_publish_only"],
                                "is_thesis_to_book": book_data["is_thesis_to_book"],
                                "publisher": book_data["publisher"],
                                "syllabus_path": syllabus_path,
                                "book_note": book_data["book_note"],
                                "tags": tags_json,
                                "subject": book_data["subject"]
                            })
                            book_id = s.execute(text("SELECT LAST_INSERT_ID();")).scalar()

                            # Process active authors
                            st.write("👥 Linking Authors...")
                            active_authors = [a for a in author_data if is_author_active(a)]
                            if publisher not in ["AG Kids", "NEET/JEE"]:
                                for author in active_authors:
                                    if author["author_id"]:
                                        author_id_to_link = author["author_id"]
                                    else:
                                        s.execute(text("""
                                            INSERT INTO authors (name, email, phone, city, state)
                                            VALUES (:name, :email, :phone, :city, :state)
                                            ON DUPLICATE KEY UPDATE name=name
                                        """), params={
                                            "name": author["name"], 
                                            "email": author["email"], 
                                            "phone": author["phone"],
                                            "city": author["city"],
                                            "state": author["state"]
                                        })
                                        author_id_to_link = s.execute(text("SELECT LAST_INSERT_ID();")).scalar()
                                        author["author_id"] = author_id_to_link
                                    
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

                            if send_welcome and publisher not in ["AG Kids", "NEET/JEE"]:
                                st.write("📧 Sending Welcome Emails...")
                                for author in active_authors:
                                    if author.get("email") and author.get("author_id"):
                                        st.write(f"⏳Sending email to {author['name']}...")
                                        email_status = "Failed"
                                        
                                        email_success, sender_email = send_welcome_email(author["email"], author["name"], author["phone"], book_data["title"], book_id, author["author_id"], author["author_position"], publisher)
                                        if email_success:
                                            email_status = "Success"
                                            s.execute(text("""
                                                UPDATE book_authors 
                                                SET welcome_mail_sent = 1 
                                                WHERE book_id = :book_id AND author_id = :author_id
                                            """), {"book_id": book_id, "author_id": author["author_id"]})
                                            st.write(f"✅ Sent to {author['name']}")
                                        else:
                                            email_status = "Failed"
                                            st.write(f"❌ Failed to send to {author['name']}")

                                        # Log activity
                                        log_activity(
                                            conn,
                                            st.session_state.user_id,
                                            st.session_state.username,
                                            st.session_state.session_id,
                                            "sent welcome email",
                                            f"To: {author['name']} ({author['email']}), Book ID: {book_id}, Status: {email_status}"
                                        )
                                        
                                        # Insert into email_history
                                        try:
                                            s.execute(text("""
                                                INSERT INTO email_history (timestamp, recipient, sender_email, status, book_id, book_title, triggered_by, details)
                                                VALUES (:timestamp, :recipient, :sender_email, :status, :book_id, :book_title, :triggered_by, :details)
                                            """), {
                                                "timestamp": ist_time.strftime('%Y-%m-%d %H:%M:%S'),
                                                "recipient": author["email"],
                                                "sender_email": sender_email,
                                                "status": email_status,
                                                "book_id": book_id,
                                                "book_title": book_data["title"],   
                                                "triggered_by": st.session_state.username,
                                                "details": f"Author: {author['name']}, Position: {author['author_position']}"
                                            })
                                        except Exception as e:
                                            st.error(f"Failed to log email history: {str(e)}")
                                            
                                s.commit()

                            # Log save action
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "added book",
                                f"Book ID: {book_id}, Publisher: {book_data['publisher']}, Author Type: {book_data['author_type']}, Is Publish Only: {book_data['is_publish_only']}, Is Thesis to Book: {book_data['is_thesis_to_book']}, Book Note: {book_data['book_note'][:50] + '...' if book_data['book_note'] else 'None'}, Tags: {tags_json}, Subject: {book_data['subject']}"
                            )

                            status.update(label="✅ Book Added Successfully!", state="complete", expanded=False)

                            st.success(
                                        f"Book saved successfully! "
                                        f"Tags: {', '.join(book_data['tags'])}  "
                                        f"Subject: {book_data['subject']}",
                                        icon="✔️"
                                    )
                            st.toast(f"Book saved successfully with subject {book_data['subject']}!", icon="✔️", duration="long")
                        
                            st.session_state.authors = [
                                {"name": "", "email": "", "phone": "", "author_id": None, "author_position": f"{i+1}{'st' if i == 0 else 'nd' if i == 1 else 'rd' if i == 2 else 'th'}", "corresponding_agent": "", "publishing_consultant": ""}
                                for i in range(4)
                            ]
                    except Exception as db_error:
                        s.rollback()
                        status.update(label="❌ Error Occurred", state="error", expanded=True)
                        st.error(f"Database error: {db_error}")
                        st.toast(f"Database error: {db_error}", icon="❌", duration="long")

    with col2:
        if st.button("Cancel", key="dialog_cancel", type="secondary"):
            st.session_state.authors = [
                {"name": "", "email": "", "phone": "", "author_id": None, "author_position": f"{i+1}{'st' if i == 0 else 'nd' if i == 1 else 'rd' if i == 2 else 'th'}", "corresponding_agent": "", "publishing_consultant": ""}
                for i in range(4)
            ]
            st.session_state["new_book_tags"] = []  # Reset tags on cancel
            st.rerun()



###################################################################################################################################
##################################--------------- Edit ISBN Dialog ----------------------------##################################
###################################################################################################################################


# Inject the hover style once
st.markdown("""
    <style>
    .subject-pill {
        color:#ea580c; 
        background: linear-gradient(90deg, #fff0e6, #fff7ed);
        font-size: 14px;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 16px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        border: 1px solid #f0b88a; 
        box-shadow: 0 2px 4px rgba(234, 88, 12, 0.15);
        margin-right: 10px;
        transition: all 0.2s ease-in-out;
    }
    .subject-pill:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 8px rgba(234, 88, 12, 0.25);
        cursor: default;
    }
    .tags-pill {
        display: inline-block;
        vertical-align: middle;
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

def get_book_image_url(conn, book_id):
    """Fetch the image URL for a given book_id from the database"""
    try:
        with conn.session as s:
            result = s.execute(
                text("SELECT images FROM books WHERE book_id = :book_id"),
                {"book_id": book_id}
            )
            row = result.fetchone()
            if row and row[0]:
                return row[0]
            else:
                return None
    except Exception as e:
        st.error(f"Error fetching book image: {e}")
        return None


from datetime import datetime
@st.dialog("Manage Book Details", width="large", on_dismiss='rerun')
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
    current_is_thesis_to_book = book_details.iloc[0].get('is_thesis_to_book', 0) == 1
    current_publisher = book_details.iloc[0].get('publisher', '')
    current_isbn_receive_date = book_details.iloc[0].get('isbn_receive_date', None)
    current_tags = book_details.iloc[0].get('tags', '')
    current_subject = book_details.iloc[0].get('subject', 'N/A')  # Fetch subject, default to 'N/A' if not present
    try:
        current_tags_list = json.loads(current_tags) if current_tags else []
    except json.JSONDecodeError:
        current_tags_list = []

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
    
    # Initialize session state for toggles and publisher
    if f"is_publish_only_{book_id}" not in st.session_state:
        st.session_state[f"is_publish_only_{book_id}"] = current_is_publish_only
    if f"is_thesis_to_book_{book_id}" not in st.session_state:
        st.session_state[f"is_thesis_to_book_{book_id}"] = current_is_thesis_to_book
    if f"tags_{book_id}" not in st.session_state:
        st.session_state[f"tags_{book_id}"] = current_tags_list
    if f"subject_{book_id}" not in st.session_state:
        st.session_state[f"subject_{book_id}"] = current_subject
    # Initialize publisher session state with current_publisher
    if f"publisher_{book_id}" not in st.session_state:
        st.session_state[f"publisher_{book_id}"] = current_publisher if current_publisher in ["AGPH", "Cipher", "AG Volumes", "AG Classics", "AG Kids", "NEET/JEE"] else "AGPH"

    # Initialize PREVIOUS state for logging immediate actions (Subject, Tags, Publisher)
    if f"subject_{book_id}_prev" not in st.session_state:
        st.session_state[f"subject_{book_id}_prev"] = st.session_state[f"subject_{book_id}"]
    if f"tags_{book_id}_prev" not in st.session_state:
        st.session_state[f"tags_{book_id}_prev"] = st.session_state[f"tags_{book_id}"]
    if f"publisher_{book_id}_prev" not in st.session_state:
        st.session_state[f"publisher_{book_id}_prev"] = st.session_state[f"publisher_{book_id}"]


    def syllabus_upload_section(is_publish_only, is_thesis_to_book, toggles_enabled, book_id):

        st.markdown("<h5 style='color: #4CAF50;'>Book Syllabus</h5>", unsafe_allow_html=True)
        syllabus_file = None
        
        # Check if the file uploader should be enabled
        if not is_publish_only and not is_thesis_to_book and toggles_enabled:
            syllabus_file = st.file_uploader(
                "Upload Book Syllabus",
                type=["pdf", "docx", "jpg", "jpeg", "png"],
                key=f"syllabus_upload_{book_id}",
                help="Upload the book syllabus as a PDF, DOCX, or image file.",
                label_visibility="collapsed"
            )
        else:
            # Display a message explaining why the upload is disabled
            if is_publish_only:
                st.info("Syllabus upload is disabled for Publish Only books.")
            elif is_thesis_to_book:
                st.info("Syllabus upload is disabled for Thesis to Book conversions.")
            else: # not toggles_enabled
                st.info("Syllabus upload is disabled for AG Kids and NEET/JEE publishers.")
        
        return syllabus_file


    def publisher_selection_section():
        publisher_options = ["AGPH", "Cipher", "AG Volumes", "AG Classics", "AG Kids", "NEET/JEE"]
        # Ensure the current publisher is in the options, default to AGPH if not
        default_publisher = st.session_state[f"publisher_{book_id}"] if st.session_state[f"publisher_{book_id}"] in publisher_options else "AGPH"
        # Find the index of the current publisher for the radio button
        default_index = publisher_options.index(default_publisher)
        selected_publisher = st.radio(
            "Select Publisher",
            options=publisher_options,
            index=default_index,
            key=f"publisher_radio_{book_id}",
            horizontal=True ,
            label_visibility="collapsed"
        )
        # Update session state with the selected publisher
        st.session_state[f"publisher_{book_id}"] = selected_publisher

        # Log Publisher Change
        if st.session_state[f"publisher_{book_id}"] != st.session_state[f"publisher_{book_id}_prev"]:
            log_activity(
                conn,
                st.session_state.user_id,
                st.session_state.username,
                st.session_state.session_id,
                "changed publisher",
                f"Book ID: {book_id}, Publisher changed to '{selected_publisher}'"
            )
            st.session_state[f"publisher_{book_id}_prev"] = selected_publisher
    

    def book_note_section(current_book_note, book_id):
        st.markdown("<h5 style='color: #4CAF50;'>Book Note</h5>", unsafe_allow_html=True)
        book_note = st.text_area(
            "Book Note or Instructions",
            value=current_book_note if current_book_note else "",
            key=f"book_note_{book_id}",
            help="Enter any additional notes or instructions for the book (optional, max 1000 characters)",
            max_chars=1000,
            placeholder="Enter notes or special instructions for the book here...",
            height=50
        )
        return book_note


    st.markdown(f"### {book_id} - {current_title}{publisher_badge}", unsafe_allow_html=True)
    publisher = current_publisher

    dialog_col1, dialog_col2 = st.columns([1.4,1])

    with dialog_col1:
        # Main container
        with st.container():
            # Book Details Section
            st.markdown("<h5 style='color: #4CAF50;'>Book Details</h5>", unsafe_allow_html=True)
            with st.container(border=True):
                
                # Get book image URL
                image_url = get_book_image_url(conn, book_id)
                
                if image_url:
                    # Layout with image
                    publisher_selection_section()
                    col1, col2 = st.columns([1, 3])  # Adjusted column ratio for image and inputs
                    with col1:
                        st.image(image_url, width=140)
                    with col2:
                        new_title = st.text_input(
                            "Book Title",
                            value=current_title,
                            key=f"title_{book_id}"
                        )
                        # Place remaining inputs below title
                        new_date = st.date_input(
                            "Book Date",
                            value=current_date if current_date else datetime.today(),
                            key=f"date_{book_id}",
                            width = 250
                        )
                        toggles_enabled = current_publisher in ["AGPH", "Cipher", "AG Volumes", "AG Classics"]
                        
                        col3, col4 = st.columns([2, 4])
                        with col3:
                            # Callback to handle Publish Only toggle
                            def on_publish_only_change():
                                if st.session_state[f"is_publish_only_{book_id}"]:
                                    st.session_state[f"is_thesis_to_book_{book_id}"] = False

                            new_is_publish_only = st.toggle(
                                "Publish Only?",
                                value=st.session_state[f"is_publish_only_{book_id}"],
                                key=f"is_publish_only_{book_id}",
                                disabled=not toggles_enabled,
                                on_change=on_publish_only_change
                            )
                        with col4:
                            # Callback to handle Thesis to Book toggle
                            def on_thesis_to_book_change():
                                if st.session_state[f"is_thesis_to_book_{book_id}"]:
                                    st.session_state[f"is_publish_only_{book_id}"] = False

                            new_is_thesis_to_book = st.toggle(
                                "Thesis to Book?",
                                value=st.session_state[f"is_thesis_to_book_{book_id}"],
                                key=f"is_thesis_to_book_{book_id}",
                                disabled=not toggles_enabled,
                                on_change=on_thesis_to_book_change
                            )
                        if not toggles_enabled:
                            st.warning("Publish Only and Thesis to Book options are disabled for AG Kids and NEET/JEE publishers.")
                else:
                    publisher_selection_section()
                    # Original layout without image
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        new_title = st.text_input(
                            "Book Title",
                            value=current_title,
                            key=f"title_{book_id}"
                        )
                    with col2:
                        new_date = st.date_input(
                            "Book Date",
                            value=current_date if current_date else datetime.today(),
                            key=f"date_{book_id}"
                        )
                    toggles_enabled = current_publisher in ["AGPH", "Cipher", "AG Volumes", "AG Classics"]
                    col3, col4 = st.columns([1, 3])
                    with col3:
                        # Callback to handle Publish Only toggle
                        def on_publish_only_change():
                            if st.session_state[f"is_publish_only_{book_id}"]:
                                st.session_state[f"is_thesis_to_book_{book_id}"] = False

                        new_is_publish_only = st.toggle(
                            "Publish Only?",
                            value=st.session_state[f"is_publish_only_{book_id}"],
                            key=f"is_publish_only_{book_id}",
                            help="Enable this to mark the book as publish only (disables writing operations)",
                            disabled=not toggles_enabled,
                            on_change=on_publish_only_change
                        )
                    with col4:
                        # Callback to handle Thesis to Book toggle
                        def on_thesis_to_book_change():
                            if st.session_state[f"is_thesis_to_book_{book_id}"]:
                                st.session_state[f"is_publish_only_{book_id}"] = False

                        new_is_thesis_to_book = st.toggle(
                            "Thesis to Book?",
                            value=st.session_state[f"is_thesis_to_book_{book_id}"],
                            key=f"is_thesis_to_book_{book_id}",
                            help="Enable this to mark the book as a thesis-to-book conversion",
                            disabled=not toggles_enabled,
                            on_change=on_thesis_to_book_change
                        )
                    if not toggles_enabled:
                        st.warning("Publish Only and Thesis to Book options are disabled for AG Kids and NEET/JEE publishers.")
                
                st.markdown('</div>', unsafe_allow_html=True)

            

            # Display subject and tags side by side
            badge_markdown = ""
            if st.session_state[f"tags_{book_id}"]:
                # Create a copy of colors list to ensure unique selection
                available_colors = ["red", "orange", "yellow", "blue", "green", "violet", "primary"]
                for tag in st.session_state[f"tags_{book_id}"]:
                    # Select a random color and remove it from available colors
                    if available_colors:
                        color = random.choice(available_colors)
                        available_colors.remove(color)
                    else:
                        # Fallback to random choice if we run out of colors
                        color = random.choice(["red", "orange", "yellow", "blue", "green", "violet", "primary"])
                    badge_markdown += f":{color}-badge[#{tag}] "
            else:
                badge_markdown = "None"

            # Display subject and tags side by side
            badge_markdown = ""
            if st.session_state[f"tags_{book_id}"]:
                # Create a copy of colors list to ensure unique selection
                available_colors = ["red", "orange", "yellow", "blue", "green", "violet", "primary"]
                for tag in st.session_state[f"tags_{book_id}"]:
                    # Select a random color and remove it from available colors
                    if available_colors:
                        color = random.choice(available_colors)
                        available_colors.remove(color)
                    else:
                        # Fallback to random choice if we run out of colors
                        color = random.choice(["red", "orange", "yellow", "blue", "green", "violet", "primary"])
                    badge_markdown += f":{color}-badge[#{tag}] "
            else:
                badge_markdown = "None"

            # Render pills
            st.markdown(
                f"""
                <span class="subject-pill">🔭 {current_subject}</span>
                <span class="tags-pill">{badge_markdown}</span>
                """,
                unsafe_allow_html=True
            )
    
        with st.expander("Manage Subject & Tags", expanded=False):
            # Manage Subject
            st.markdown("<h5 style='color: #4CAF50;'>Manage Subjet</h5>", unsafe_allow_html=True)

            available_subjects = VALID_SUBJECTS  # Assume this function fetches all unique subjects
            if current_subject and current_subject not in available_subjects:
                available_subjects.append(current_subject)
            
            # Use st.pills for subject selection
            selected_subject = st.pills(
                "Select Subject",
                options=available_subjects,
                default=current_subject,
                key=f"manage_subject_{book_id}",
                help="Select a subject for the book or clear to remove",
                label_visibility="collapsed"
            )
            st.session_state[f"subject_{book_id}"] = selected_subject if selected_subject else ''

            # Log Subject Change
            if st.session_state[f"subject_{book_id}"] != st.session_state[f"subject_{book_id}_prev"]:
                log_activity(
                    conn,
                    st.session_state.user_id,
                    st.session_state.username,
                    st.session_state.session_id,
                    "changed subject",
                    f"Book ID: {book_id}, Subject changed to '{selected_subject}'"
                )
                st.session_state[f"subject_{book_id}_prev"] = st.session_state[f"subject_{book_id}"]

            st.markdown("<h5 style='color: #4CAF50;'>Manage Tags</h5>", unsafe_allow_html=True)

            # Fetch all unique tags and their counts from the database
            sorted_tags = fetch_tags(conn)
            
            # Add any new tags from session state that aren't in the database yet
            for tag in st.session_state[f"tags_{book_id}"]:
                if tag and tag not in sorted_tags:
                    sorted_tags.append(tag)
            
            # Multiselect for adding/removing tags
            st.session_state[f"tags_{book_id}"] = st.multiselect(
                "Manage Tags",
                options=sorted_tags,
                default=st.session_state[f"tags_{book_id}"],
                key=f"manage_tags_{book_id}",
                accept_new_options=True,
                max_selections=10,
                help="Select or deselect tags for the book, or type to add new tags",
                label_visibility="collapsed",
            )

            # Log Tags Change
            if st.session_state[f"tags_{book_id}"] != st.session_state[f"tags_{book_id}_prev"]:
                new_tags_str = ", ".join(st.session_state[f"tags_{book_id}"])
                log_activity(
                    conn,
                    st.session_state.user_id,
                    st.session_state.username,
                    st.session_state.session_id,
                    "updated tags",
                    f"Book ID: {book_id}, Tags updated: {new_tags_str}"
                )
                st.session_state[f"tags_{book_id}_prev"] = st.session_state[f"tags_{book_id}"]

        # Fetch current syllabus and book note for the book
        with conn.session as s:
            result = s.execute(text("SELECT syllabus_path, book_note FROM books WHERE book_id = :book_id"), {"book_id": book_id}).fetchone()
            current_syllabus_path = result[0] if result else None
            current_book_note = result[1] if result else None

        with st.expander("Syllabus & Book Note", expanded=False):
            # Add syllabus and book note section
            syllabus_file = syllabus_upload_section(
                new_is_publish_only,
                new_is_thesis_to_book,
                publisher in ["AGPH", "Cipher", "AG Volumes", "AG Classics"],
                current_syllabus_path
            )
            book_note = book_note_section(current_book_note, book_id)


    with dialog_col2:    
        # ISBN Details Section
        st.markdown("<h5 style='color: #4CAF50;'>ISBN Details</h5>", unsafe_allow_html=True)
        apply_isbn = bool(current_apply_isbn)
        receive_isbn = bool(pd.notna(current_isbn))
        if not has_open_author_position(conn, book_id):
            with st.container(border=True):
                apply_isbn = st.checkbox(
                    "ISBN Applied?",
                    value=apply_isbn,
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
                    col3, col4 = st.columns([1,0.7])
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
                            "ISBN Receive Date",
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
        
        st.markdown("<h5 style='color: #4CAF50;'>Associated Authors</h5>", unsafe_allow_html=True)
        with st.expander("Authors", expanded=True):
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

        
        # -------------------- CANCEL BOOK FEATURE --------------------
        #st.markdown("<h5 style='color: #D32F2F;'>Danger Zone</h5>", unsafe_allow_html=True)

        with st.popover("🚫 Cancel Book", width="stretch"):
            # Fetch latest status
            current_book_details = fetch_book_details(book_id, conn)
            if not current_book_details.empty:
                writing_start_val = current_book_details.iloc[0].get('writing_start')
            else:
                writing_start_val = None
            
            # Check digital_book_sent status
            authors_df = fetch_book_authors(book_id, conn)
            digital_sent_count = 0
            if not authors_df.empty and 'digital_book_sent' in authors_df.columns:
                digital_sent_count = authors_df['digital_book_sent'].sum()
            
            if digital_sent_count > 0:
                st.error(f"❌ Cannot cancel the book once digital book has been sent to author(s).")
            else:
                st.caption("Cancel this book if it is no longer needed or the author has withdrawn.")
                cancel_reason = st.text_area(
                    "Reason for Cancellation (Required)", 
                    key=f"cancel_reason_{book_id}",
                    placeholder="e.g. Author withdrew, Duplicate entry, etc."
                )
                
                if st.button("🗑️ Confirm Cancel", key=f"confirm_cancel_{book_id}", type="primary"):
                    if not cancel_reason.strip():
                        st.error("Please provide a reason for cancellation.")
                    else:
                        with st.spinner("Cancelling book..."):
                            time.sleep(5)
                            # Determine target status

                            has_writing = pd.notna(writing_start_val)
                            
                            try:
                                with conn.session as s:
                                    if has_writing:
                                        # Archive to extra_books
                                        s.execute(text("""
                                            INSERT INTO extra_books (
                                                book_id, title, date, reason,
                                                writing_start, writing_end, writing_by,
                                                proofreading_start, proofreading_end, proofreading_by,
                                                formatting_start, formatting_end, formatting_by,
                                                book_pages
                                            )
                                            SELECT 
                                                book_id, title, date, :reason,
                                                writing_start, writing_end, writing_by,
                                                proofreading_start, proofreading_end, proofreading_by,
                                                formatting_start, formatting_end, formatting_by,
                                                book_pages
                                            FROM books
                                            WHERE book_id = :book_id
                                        """), {"book_id": book_id, "reason": cancel_reason})
                                        
                                        # Set as deleted and clear operations in original book
                                        s.execute(text("""
                                            UPDATE books SET 
                                                is_cancelled = 2, 
                                                cancellation_reason = :reason,
                                                writing_start = NULL, writing_end = NULL, writing_by = NULL,
                                                proofreading_start = NULL, proofreading_end = NULL, proofreading_by = NULL,
                                                formatting_start = NULL, formatting_end = NULL, formatting_by = NULL,
                                                cover_start = NULL, cover_end = NULL, cover_by = NULL,
                                                book_pages = 0
                                            WHERE book_id = :book_id
                                        """), {"status": 2, "reason": cancel_reason, "book_id": book_id})
                                        
                                        status_label = "Extra Books (Archived)"
                                    else:
                                        # 1. Fetch Authors
                                        authors_rows = s.execute(text("SELECT * FROM book_authors WHERE book_id = :book_id"), {"book_id": book_id}).mappings().all()
                                        authors_list = [dict(row) for row in authors_rows]
                                        # Handle date serialization
                                        def json_serial(obj):
                                            if isinstance(obj, (datetime, date)):
                                                return obj.isoformat()
                                            if isinstance(obj, Decimal):
                                                return float(obj)
                                            raise TypeError (f"Type {type(obj)} not serializable")
                                        
                                        authors_json_str = json.dumps(authors_list, default=json_serial)
                                        
                                        # 2. Update reason in books (so it copies correctly)
                                        s.execute(text("UPDATE books SET cancellation_reason = :reason WHERE book_id = :book_id"), {"reason": cancel_reason, "book_id": book_id})

                                        # 3. Insert into deleted_books
                                        s.execute(text("""
                                            INSERT INTO deleted_books
                                            SELECT b.*, :authors, NOW()
                                            FROM books b
                                            WHERE b.book_id = :book_id
                                        """), {"book_id": book_id, "authors": authors_json_str})
                                        
                                        # 4. Delete Authors
                                        s.execute(text("DELETE FROM book_authors WHERE book_id = :book_id"), {"book_id": book_id})
                                        
                                        # 5. Clear Books Data (Soft Delete)
                                        s.execute(text("""
                                            UPDATE books SET 
                                                is_cancelled = 2, 
                                                cancellation_reason = :reason,
                                                isbn = NULL,
                                                isbn_receive_date = NULL,
                                                writing_start = NULL, writing_end = NULL, writing_by = NULL,
                                                proofreading_start = NULL, proofreading_end = NULL, proofreading_by = NULL,
                                                formatting_start = NULL, formatting_end = NULL, formatting_by = NULL,
                                                cover_start = NULL, cover_end = NULL, cover_by = NULL,
                                                book_pages = 0
                                            WHERE book_id = :book_id
                                        """), {"reason": cancel_reason, "book_id": book_id})
                                        
                                        status_label = "Deleted Books"
                                        
                                    s.commit()
                                
                                log_activity(
                                    conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id,
                                    "cancelled book", f"Book ID: {book_id}, Status: {status_label}, Reason: {cancel_reason}"
                                )
                                st.success(f"Book moved to {status_label}.")
                            except Exception as e:
                                st.error(f"Error cancelling book: {e}")
        

    # Save Button
    if st.button("Save Changes", key=f"save_isbn_{book_id}", type="secondary"):
        with st.spinner("Saving changes..."):
            with conn.session as s:
                try:
                    # Handle syllabus file upload
                    syllabus_path = current_syllabus_path
                    if syllabus_file and not new_is_publish_only and not new_is_thesis_to_book and st.session_state[f"publisher_{book_id}"] in ["AGPH", "Cipher", "AG Volumes", "AG Classics"]:
                        file_extension = os.path.splitext(syllabus_file.name)[1]
                        unique_filename = f"syllabus_{new_title.replace(' ', '_')}_{int(time.time())}{file_extension}"
                        syllabus_path_temp = os.path.join(SYLLABUS_UPLOAD_DIR, unique_filename)
                        if not os.access(SYLLABUS_UPLOAD_DIR, os.W_OK):
                            st.error(f"No write permission for {SYLLABUS_UPLOAD_DIR}.")
                            raise PermissionError(f"Cannot write to {SYLLABUS_UPLOAD_DIR}")
                        try:
                            with open(syllabus_path_temp, "wb") as f:
                                f.write(syllabus_file.getbuffer())
                            syllabus_path = syllabus_path_temp
                        except Exception as e:
                            st.error(f"Failed to save syllabus file: {str(e)}")
                            st.toast(f"Failed to save syllabus file: {str(e)}", icon="❌", duration="long")
                            raise

                    # Convert tags list to JSON string for database
                    new_tags_json = json.dumps(st.session_state[f"tags_{book_id}"]) if st.session_state[f"tags_{book_id}"] else '[]'

                    # Track changes for logging
                    changes = []
                    if new_title != current_title:
                        changes.append(f"Updated title from '{current_title}' to '{new_title}'")
                    if new_date != current_date:
                        changes.append(f"Updated date from '{current_date}' to '{new_date}'")
                    if new_is_publish_only != current_is_publish_only:
                        changes.append(f"Updated is_publish_only to '{new_is_publish_only}'")
                    if new_is_thesis_to_book != current_is_thesis_to_book:
                        changes.append(f"Updated is_thesis_to_book to '{new_is_thesis_to_book}'")
                    if apply_isbn != bool(current_apply_isbn):
                        changes.append(f"Updated ISBN Applied to '{apply_isbn}'")
                    if receive_isbn != bool(pd.notna(current_isbn)):
                        changes.append(f"Updated ISBN Received to '{receive_isbn}'")
                    if apply_isbn and receive_isbn and new_isbn != current_isbn:
                        changes.append(f"Updated ISBN to '{new_isbn}'")
                    if apply_isbn and receive_isbn and isbn_receive_date != current_isbn_receive_date:
                        changes.append(f"Updated ISBN Receive Date to '{isbn_receive_date}'")
                    if syllabus_path != current_syllabus_path:
                        changes.append(f"Updated syllabus file to '{syllabus_path}'")
                    if book_note != current_book_note:
                        changes.append(f"Updated book note to '{book_note[:50] + '...' if book_note else 'None'}'")
                    if new_tags_json != current_tags:
                        changes.append(f"Updated tags to '{new_tags_json}'")
                    if st.session_state[f"subject_{book_id}"] != current_subject:
                        changes.append(f"Updated subject to '{st.session_state[f'subject_{book_id}']}'")
                    if st.session_state[f"publisher_{book_id}"] != current_publisher:
                        changes.append(f"Updated publisher to '{st.session_state[f'publisher_{book_id}']}'")

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
                                    is_publish_only = :is_publish_only,
                                    is_thesis_to_book = :is_thesis_to_book,
                                    syllabus_path = :syllabus_path,
                                    book_note = :book_note,
                                    tags = :tags,
                                    subject = :subject,
                                    publisher = :publisher
                                WHERE book_id = :book_id
                            """),
                            {
                                "apply_isbn": 1, 
                                "isbn": new_isbn, 
                                "isbn_receive_date": isbn_receive_date, 
                                "title": new_title, 
                                "date": new_date,
                                "is_publish_only": 1 if new_is_publish_only else 0,
                                "is_thesis_to_book": 1 if new_is_thesis_to_book else 0,
                                "syllabus_path": syllabus_path,
                                "book_note": book_note,
                                "tags": new_tags_json,
                                "subject": st.session_state[f"subject_{book_id}"],
                                "publisher": st.session_state[f"publisher_{book_id}"],
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
                                    is_publish_only = :is_publish_only,
                                    is_thesis_to_book = :is_thesis_to_book,
                                    syllabus_path = :syllabus_path,
                                    book_note = :book_note,
                                    tags = :tags,
                                    subject = :subject,
                                    publisher = :publisher
                                WHERE book_id = :book_id
                            """),
                            {
                                "apply_isbn": 1, 
                                "title": new_title, 
                                "date": new_date,
                                "is_publish_only": 1 if new_is_publish_only else 0,
                                "is_thesis_to_book": 1 if new_is_thesis_to_book else 0,
                                "syllabus_path": syllabus_path,
                                "book_note": book_note,
                                "tags": new_tags_json,
                                "subject": st.session_state[f"subject_{book_id}"],
                                "publisher": st.session_state[f"publisher_{book_id}"],
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
                                    is_publish_only = :is_publish_only,
                                    is_thesis_to_book = :is_thesis_to_book,
                                    syllabus_path = :syllabus_path,
                                    book_note = :book_note,
                                    tags = :tags,
                                    subject = :subject,
                                    publisher = :publisher
                                WHERE book_id = :book_id
                            """),
                            {
                                "apply_isbn": 0, 
                                "title": new_title, 
                                "date": new_date,
                                "is_publish_only": 1 if new_is_publish_only else 0,
                                "is_thesis_to_book": 1 if new_is_thesis_to_book else 0,
                                "syllabus_path": syllabus_path,
                                "book_note": book_note,
                                "tags": new_tags_json,
                                "subject": st.session_state[f"subject_{book_id}"],
                                "publisher": st.session_state[f"publisher_{book_id}"],
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
                    st.toast("Book details updated successfully!", icon="✅", duration="long")
                except Exception as db_error:
                    s.rollback()
                    st.error(f"Database error: {db_error}")
                    st.toast(f"Database error: {db_error}", icon="❌", duration="long")


###################################################################################################################################
##################################--------------- Edit Price Dialog ----------------------------##################################
###################################################################################################################################


@st.dialog("Manage Book Price and Author Payments", width="large", on_dismiss="ignore")
def manage_price_dialog(book_id, conn):
    # Fetch book details for title and price
    book_details = fetch_book_details(book_id, conn)
    book_title = book_details.iloc[0]['title'] if not book_details.empty else "Unknown Title"
    current_price = book_details.iloc[0]['price'] if not book_details.empty else None
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
            amount_paid = float(row.get('amount_paid', 0) or 0)
            agent = row.get('publishing_consultant', 'Unknown Agent')

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
                status_text = f"₹0/₹{total_amount}" if total_amount > 0 else "N/A"
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

    glob_col1, glob_col2 = st.columns([2.2,1])

    with glob_col2:
 
        with st.container(border=True):
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
                if st.button("Save Price", key=f"save_price_{book_id}"):
                    with st.spinner("Saving..."):
                        import time
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
                            
                            log_activity(
                                conn,
                                st.session_state.user_id,
                                st.session_state.username,
                                st.session_state.session_id,
                                "updated book price",
                                f"Book: {book_title} ({book_id}), New Price: ₹{price}"
                            )
                            
                            st.toast("Book Price Updated Successfully", icon="✔️", duration="long")
                            st.cache_data.clear()
                        except ValueError:
                            st.error("Please enter a valid whole number", icon="🚨")
    
    with glob_col1:
        with st.container(border=True):
            # Section 2: Author Payments with Tabs
            st.markdown("<h5 style='color: #4CAF50;'>Author Payments</h5>", unsafe_allow_html=True)
            if not book_authors.empty:
                total_author_amounts = 0
                updated_authors = []

                # Create tabs for each author
                tab_titles = [f"{row['name']} (ID: {row['author_id']})" for _, row in book_authors.iterrows()]
                tabs = st.tabs(tab_titles)

                for tab, (_, row) in zip(tabs, book_authors.iterrows()):
                    with tab:
                        ba_id = row['id']
                        total_amount = int(row.get('total_amount', 0) or 0)
                        remark_val = row.get('remark', '') or ""
                        
                        # Calculate amount paid from the new table
                        amount_paid = float(row.get('amount_paid', 0) or 0)
                        
                        # Payment status
                        if amount_paid >= total_amount and total_amount > 0:
                            status = '<span class="payment-status status-paid">Fully Paid</span>'
                        elif amount_paid > 0:
                            status = '<span class="payment-status status-partial">Partially Paid</span>'
                        else:
                            status = '<span class="payment-status status-pending">Pending</span>'
                        st.markdown(f"**Payment Status:** {status}", unsafe_allow_html=True)

                        # --- Section: Author Metadata ---
                        col_m1, col_m2 = st.columns([1, 2])
                        with col_m1:
                            new_total_str = st.text_input(
                                "Total Amount Due (₹)",
                                value=str(total_amount) if total_amount > 0 else "",
                                key=f"total_{ba_id}",
                                placeholder="Enter whole amount"
                            )
                        with col_m2:
                            new_remark = st.text_input(
                                "Payment Remark",
                                value=remark_val,
                                key=f"remark_{ba_id}",
                                placeholder="General notes about author payment..."
                            )
                        
                        if st.button("Update Total & Remark", key=f"update_meta_{ba_id}"):
                            try:
                                nt = int(new_total_str) if new_total_str.strip() else 0
                                update_book_authors(ba_id, {"total_amount": nt, "remark": new_remark}, conn)
                                log_activity(
                                    conn,
                                    st.session_state.user_id,
                                    st.session_state.username,
                                    st.session_state.session_id,
                                    "updated author total & remark",
                                    f"Book: {book_title} ({book_id}), Author: {row['name']} (ID: {row['author_id']}), Total: ₹{nt}, Remark: {new_remark}"
                                )
                                st.success("Updated successfully!")
                                st.rerun()
                            except ValueError:
                                st.error("Invalid amount")

                        st.write("---")

                        # --- Section: Payment History ---
                        st.markdown("##### 🧾 Payment History")
                        history_query = "SELECT * FROM author_payments WHERE book_author_id = :ba_id ORDER BY payment_date DESC"
                        history = conn.query(history_query, params={"ba_id": ba_id}, ttl=0, show_spinner=False)
                        
                        if not history.empty:
                            for _, p in history.iterrows():
                                hcol1, hcol2, hcol3, hcol4, hcol5, hcol6 = st.columns([1, 1, 1, 1, 1, 0.4])
                                with hcol1:
                                    st.write(f"₹{p['amount']}")
                                with hcol2:
                                    st.write(p['payment_date'].strftime('%d %b %Y') if p['payment_date'] else "-")
                                with hcol3:
                                    st.write(f"**{p['payment_mode']}**")
                                with hcol4:
                                    st.write(f"ID: {p['transaction_id']}" if p['transaction_id'] else "-")
                                with hcol5:
                                    status = p.get('status', 'Pending')
                                    status_color = "green" if status == 'Approved' else "red" if status == 'Rejected' else "orange"
                                    st.markdown(f"<span style='color:{status_color}'>{status}</span>", unsafe_allow_html=True)
                                    if status == 'Rejected' and p.get('rejection_reason'):
                                        st.caption(f"Reason: {p['rejection_reason']}")
                                with hcol6:
                                    if st.button(":material/delete:", key=f"del_pay_{p['id']}", help="Delete this payment"):
                                        with conn.session as s:
                                            s.execute(text("DELETE FROM author_payments WHERE id = :pid"), {"pid": p['id']})
                                            s.commit()
                                        log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "deleted payment", f"Book: {book_title} ({book_id}), Author: {row['name']} (ID: {row['author_id']}), Amount: ₹{p['amount']} ({p['payment_mode']})")
                                        st.rerun()
                        else:
                            st.info("No individual payment records found.")

                        st.write("---")
                        
                        # --- Section: Add New Payment ---
                        st.markdown("##### ➕ Add New Payment")
                        payment_modes = ["Cash", "UPI", "Bank Deposit"]
                        acol1, acol2, acol3 = st.columns([1, 1, 1])
                        with acol1:
                            add_amt = st.text_input("Amount (₹)", key=f"add_amt_{ba_id}", placeholder="0")
                        with acol2:
                            add_date = st.date_input("Date", value=datetime.now(), key=f"add_date_{ba_id}")
                        with acol3:
                            add_mode = st.selectbox("Mode", payment_modes, key=f"add_mode_{ba_id}")
                        
                        add_txn = ""
                        if add_mode in ["UPI", "Bank Deposit"]:
                            add_txn = st.text_input("Transaction ID", key=f"add_txn_{ba_id}", placeholder="Ref No.")
                        
                        add_rem = st.text_input("Payment Specific Note", key=f"add_rem_{ba_id}", placeholder="e.g. Received via WhatsApp")

                        if st.button("➕ Register Payment", key=f"btn_add_{ba_id}", type="primary", use_container_width=True):
                            try:
                                amt = float(add_amt) if add_amt.strip() else 0
                                if amt <= 0:
                                    st.error("Enter a valid amount")
                                else:
                                    # Determine status based on role
                                    is_admin = st.session_state.get("role") == "admin"
                                    initial_status = 'Approved' if is_admin else 'Pending'
                                    
                                    with conn.session as s:
                                        s.execute(text("""
                                            INSERT INTO author_payments (book_author_id, amount, payment_date, payment_mode, transaction_id, remark, status, created_by, requested_by, approved_by, approved_at)
                                            VALUES (:ba_id, :amt, :date, :mode, :txn, :remark, :status, :created_by, :requested_by, :approved_by, :approved_at)
                                        """), {
                                            "ba_id": ba_id, 
                                            "amt": amt, 
                                            "date": add_date, 
                                            "mode": add_mode, 
                                            "txn": add_txn, 
                                            "remark": add_rem,
                                            "status": initial_status,
                                            "created_by": st.session_state.get("user_id"),
                                            "requested_by": st.session_state.get("username", "Unknown"),
                                            "approved_by": st.session_state.get("username") if is_admin else None,
                                            "approved_at": datetime.now() if is_admin else None
                                        })
                                        s.commit()
                                    
                                        log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "added payment", f"Book: {book_title} ({book_id}), Author: {row['name']} (ID: {row['author_id']}), Amount: ₹{amt}, Mode: {add_mode}, Status: {initial_status}")
                                    
                                    if is_admin:
                                        st.success("Payment registered and approved!")
                                    else:
                                        st.success("Payment registered! Waiting for Admin Approval.")
                                    st.rerun()
                            except ValueError:
                                st.error("Invalid amount")

                        remaining = total_amount - amount_paid
                        st.markdown(f"<div style='text-align:right;'><span style='color:green'>**Total Paid:** ₹{amount_paid}</span> | <span style='color:red'>**Remaining:** ₹{remaining}</span></div>", unsafe_allow_html=True)





###################################################################################################################################
##################################--------------- Edit Auhtor Dialog ----------------------------##################################
###################################################################################################################################



# Function to fetch book_author details along with author details for a given book_id
def fetch_book_authors(book_id, conn):
    query = f"""
    SELECT ba.id, ba.book_id, ba.author_id, a.name, a.email, a.phone, a.about_author, a.author_photo, a.city, a.state,
           ba.author_position, ba.welcome_mail_sent, ba.corresponding_agent, 
           ba.publishing_consultant, ba.photo_recive, ba.id_proof_recive, 
           ba.author_details_sent, ba.cover_agreement_sent, ba.agreement_received, 
           ba.digital_book_sent, 
           ba.printing_confirmation, ba.delivery_address, ba.delivery_charge, 
           ba.number_of_books, ba.total_amount, 
           ba.delivery_date, ba.tracking_id, ba.delivery_vendor,
           ba.remark,
           COALESCE((SELECT SUM(amount) FROM author_payments WHERE book_author_id = ba.id AND status = 'Approved'), 0) as amount_paid
    FROM book_authors ba
    JOIN authors a ON ba.author_id = a.author_id
    WHERE ba.book_id = '{book_id}'
    """
    return conn.query(query, show_spinner = False)

def insert_author(conn, name, email, phone, city=None, state=None):
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
                    INSERT INTO authors (name, email, phone, city, state)
                    VALUES (:name, :email, :phone, :city, :state)
                """),
                params={"name": name, "email": email, "phone": phone, "city": city, "state": state}
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
        st.toast(f"Error inserting author: {e}", icon="❌", duration="long")
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
         "corresponding_agent": "", "publishing_consultant": "", "city": "", "state": ""}
        for _ in range(slots)
    ]

def initialize_new_editors(slots):
    return [
        {"name": "", "email": "", "phone": "", "city": "", "state": "", "author_id": None, "author_position": None}
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
            SELECT ce.author_id, ce.author_position, a.name, a.email, a.phone, a.city, a.state,
                   ce.corresponding_agent, ce.publishing_consultant
            FROM chapter_editors ce
            JOIN authors a ON ce.author_id = a.author_id
            WHERE ce.chapter_id = :chapter_id
            ORDER BY ce.author_position
        """)
        result = s.execute(query, {"chapter_id": chapter_id}).fetchall()
        return pd.DataFrame(result, columns=[
            'author_id', 'author_position', 'name', 'email', 'phone', 'city', 'state',
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
# Updated dialog for editing author details with improved UI
@st.dialog("Edit Author Details", width='large', on_dismiss = 'rerun')
def edit_author_dialog(book_id, conn):

    # Fetch book details for title, is_single_author, num_copies, and print_status
    book_details = fetch_book_details(book_id, conn)
    if book_details.empty:
        st.markdown(f"### Authors for Book ID: {book_id}")
        st.error("❌ Book details not found.")
        st.toast("Book details not found.", icon="❌", duration="long")
        if st.button("Close"):
            st.rerun()
        return

    book_title = book_details.iloc[0]['title']
    is_single_author = book_details.iloc[0]['is_single_author']
    num_copies = book_details.iloc[0]['num_copies']
    print_status = book_details.iloc[0]['print_status']
    publisher = book_details.iloc[0]['publisher']
    correction_status = book_details.iloc[0].get('correction_status', 'None')

    # Check if book is currently in a correction cycle
    with conn.session as s:
        active_task = s.execute(
            text("SELECT section FROM corrections WHERE book_id = :book_id AND correction_end IS NULL LIMIT 1"),
            {"book_id": book_id}
        ).fetchone()
    
    is_in_correction = (correction_status is not None and correction_status != 'None') or active_task is not None
    
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
                st.toast("Can't Change Author Type", icon="❌", duration="long")
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
                        st.toast(f"Author type changed to {selected_author_type}", icon="✔️", duration="long")
                        log_activity(
                            conn,
                            st.session_state.user_id,
                            st.session_state.username,
                            st.session_state.session_id,
                            "changed author type",
                            f"Book ID: {book_id}, New Author Type: {selected_author_type}"
                        )

                except Exception as e:
                    st.error(f"❌ Error updating author type: {e}")
                    st.toast(f"Error updating author type: {e}", icon="❌", duration="long")
                    return

        available_slots = max_authors_allowed - existing_author_count
        if available_slots <= 0:
            st.warning(f"⚠️ Maximum number of authors ({max_authors_allowed}) reached for {selected_author_type} author type.")
            if st.button("Close"):
                st.rerun()
            return

        if existing_author_count == 0:
            st.warning(f"⚠️ No authors found for Book ID: {book_id}")

        # Initialize session state for new authors
        if "new_authors" not in st.session_state or len(st.session_state.new_authors) != available_slots:
            st.session_state.new_authors = initialize_new_authors(available_slots)

        def validate_author(author, existing_positions, existing_author_ids, all_new_authors, index, author_type):
            """Validate an author's details."""
            if not author["name"]:
                return False, "Author name is required."
            if not author["email"] or not validate_email(author["email"]):
                return False, "Invalid email format."
            if not author["phone"] or not validate_phone(author["phone"]):
                return False, "Invalid phone number format."
            if not author["author_position"]:
                return False, "Author position is required."
            if not author["publishing_consultant"]:
                return False, "Publishing consultant is required."

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

        cols = st.columns(2)

        # Iterate through available slots and assign each expander to a column
        for i in range(available_slots):
            with cols[i % 2]:
                with st.expander(f"New Author {i+1}", expanded=True):
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
                        # --- Existing Author: Read-Only View ---
                        selected_author_id = int(selected_author.split('(ID: ')[1][:-1])
                        selected_author_details = next((a for a in all_authors if a.author_id == selected_author_id), None)
                        if selected_author_details:
                            # Update session state
                            st.session_state.new_authors[i].update({
                                "name": selected_author_details.name,
                                "email": selected_author_details.email,
                                "phone": selected_author_details.phone,
                                "author_id": selected_author_details.author_id
                            })
                            
                            # Display Read-Only Details
                            st.markdown(f"""
                                <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 14px;">
                                    <strong>👤 Name:</strong> {selected_author_details.name}<br>
                                    <strong>📧 Email:</strong> {selected_author_details.email}<br>
                                    <strong>📱 Phone:</strong> {selected_author_details.phone}
                                </div>
                            """, unsafe_allow_html=True)

                    elif selected_author == "Add New Author" and not disabled:
                        # --- New Author: Editable Fields ---
                        st.session_state.new_authors[i]["author_id"] = None
                        
                        col1, col2 = st.columns(2)
                        st.session_state.new_authors[i]["name"] = col1.text_input(
                            f"Author Name {i+1}", st.session_state.new_authors[i]["name"], key=f"new_name_{i}",
                            disabled=disabled
                        )

                    # --- Common Editable Fields (Position) ---
                    available_positions = [pos for pos in ["1st", "2nd", "3rd", "4th"] if pos not in 
                                        (existing_positions + [a["author_position"] for j, a in enumerate(st.session_state.new_authors) if j != i and a["author_position"]])]
                    
                    if selected_author != "Add New Author" and not disabled:
                        # For existing authors, we need a place for Position.
                        st.session_state.new_authors[i]["author_position"] = st.selectbox(
                            f"Position {i+1}",
                            available_positions,
                            key=f"new_author_position_{i}",
                            disabled=disabled or not available_positions
                        ) if available_positions else st.error("❌ No available positions left.")
                    
                    elif selected_author == "Add New Author" and not disabled:
                        # For new authors, Position logic from before (likely col2)
                        st.session_state.new_authors[i]["author_position"] = col2.selectbox(
                            f"Position {i+1}",
                            available_positions,
                            key=f"new_author_position_{i}",
                            disabled=disabled or not available_positions
                        ) if available_positions else st.error("❌ No available positions left.")

                    if selected_author == "Add New Author" and not disabled:
                        col3, col4 = st.columns(2)
                        st.session_state.new_authors[i]["phone"] = col3.text_input(
                            f"Phone {i+1}", st.session_state.new_authors[i]["phone"], key=f"new_phone_{i}",
                            disabled=disabled
                        )
                        st.session_state.new_authors[i]["email"] = col4.text_input(
                            f"Email {i+1}", st.session_state.new_authors[i]["email"], key=f"new_email_{i}",
                            disabled=disabled
                        )

                        col_city, col_state = st.columns(2)
                        st.session_state.new_authors[i]["city"] = col_city.text_input(
                            f"City {i+1}", st.session_state.new_authors[i]["city"], key=f"new_city_{i}",
                            disabled=disabled
                        )
                        st.session_state.new_authors[i]["state"] = col_state.text_input(
                            f"State {i+1}", st.session_state.new_authors[i]["state"], key=f"new_state_{i}",
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

        # Add or Cancel buttons (outside the column layout to maintain original placement)
        col1, col2 = st.columns([7, 1])
        with col1:
            send_welcome = st.checkbox("Send welcome email to new authors", 
                                       value=False, 
                                       key="send_welcome_new_author",
                                       disabled=True)
            if st.button("Add Authors to Book", key="add_authors_to_book", type="primary"):
                errors = []
                for i, author in enumerate(st.session_state.new_authors):
                    if author["name"]:
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
                                if author["name"]:
                                    author_id_to_link = author["author_id"]
                                    if not author_id_to_link:  # New author
                                        author_id_to_link = insert_author(conn, author["name"], author["email"], author["phone"], author["city"], author["state"])
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
                                        "email": author["email"],
                                        "phone": author["phone"],
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

                            # Send Welcome Emails
                            if send_welcome and publisher not in ["AG Kids", "NEET/JEE"]:
                                st.write("📧 Sending Welcome Emails...")
                                with conn.session as s:
                                    for author in added_authors:
                                        if author.get("email") and author.get("author_id"):
                                            email_status = "Failed"
                                            
                                            email_success, sender_email = send_welcome_email(author["email"], author["name"], author["phone"], book_title, book_id, author["author_id"], author["author_position"], publisher)
                                            if email_success:
                                                email_status = "Success"
                                                s.execute(text("""
                                                    UPDATE book_authors 
                                                    SET welcome_mail_sent = 1 
                                                    WHERE book_id = :book_id AND author_id = :author_id
                                                """), {"book_id": book_id, "author_id": author["author_id"]})
                                                s.commit()
                                                st.success(f"✅ Sent to {author['name']}")
                                            else:
                                                email_status = "Failed"
                                                st.error(f"❌ Failed to send to {author['name']}")

                                            # Log activity
                                            log_activity(
                                                conn,
                                                st.session_state.user_id,
                                                st.session_state.username,
                                                st.session_state.session_id,
                                                "sent welcome email",
                                                f"To: {author['name']} ({author['email']}), Book ID: {book_id}, Status: {email_status}"
                                            )
                                            
                                            # Insert into email_history
                                            try:
                                                s.execute(text("""
                                                    INSERT INTO email_history (timestamp, recipient, sender_email, status, book_id, book_title, triggered_by, details)
                                                    VALUES (:timestamp, :recipient, :sender_email, :status, :book_id, :book_title, :triggered_by, :details)
                                                """), {
                                                    "timestamp": ist_time.strftime('%Y-%m-%d %H:%M:%S'),
                                                    "recipient": author["email"],
                                                    "sender_email": sender_email,
                                                    "status": email_status,
                                                    "book_id": book_id,
                                                    "book_title": book_title,   
                                                    "triggered_by": st.session_state.username,
                                                    "details": f"Author: {author['name']}, Position: {author['author_position']}"
                                                })
                                            except Exception as e:
                                                st.error(f"Failed to log email history: {str(e)}")
                                    s.commit()
                            st.cache_data.clear()
                            st.success("✔️ New authors added successfully!")
                            st.toast("New authors added successfully!", icon="✔️", duration="long")
                            del st.session_state.new_authors
                        else:
                            st.error("❌ No authors were added due to errors.")
                    except Exception as e:
                        st.error(f"❌ Error adding authors: {e}")
                        st.toast(f"Error adding authors: {e}", icon="❌", duration="long")

        with col2:
            if st.button("Cancel", key="cancel_add_authors", type="secondary"):
                del st.session_state.new_authors
                st.rerun()
        return

    # Initialize session state for expander states and previous checkbox states
    if 'expander_states' not in st.session_state:
        st.session_state.expander_states = {}
    if 'checkbox_states' not in st.session_state:
        st.session_state.checkbox_states = {}

    tab1, tab2 = st.tabs(["Existing Authors", "Add New"])
    with tab1:
        num_authors = len(book_authors)
        num_columns = min(2, 2)  
        cols = st.columns(num_columns)
        # Iterate through authors and assign each to a column
        for idx, (_, row) in enumerate(book_authors.iterrows()):
            author_id = row['author_id']
            author_position = row['author_position']
            # Use session state to track whether this author's expander is open
            expander_key = f"expander_{author_id}"
            if expander_key not in st.session_state.expander_states:
                st.session_state.expander_states[expander_key] = True  # Default to collapsed
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
            # Place each author expander in a column (cycle through columns if more authors than columns)
            with cols[idx % num_columns]:
                with st.expander(f"📖 {row['name']} (ID: {author_id}) Position: {author_position}", expanded=st.session_state.expander_states[expander_key]):
                    # Display author details
                    with st.container():

                        # col1, col2 = st.columns([1,1.2])
                        # with col1:
                        #         if row['author_photo']:
                        #             st.image(row['author_photo'],width = 100)
                        #         else:
                                    
                        #             uploaded_photo = st.file_uploader("Upload Author Photo", type=['jpg', 'png', 'jpeg'], key=f"photo_{row['id']}")
                                         
                        # with col2:
                        #     st.markdown(f"**📌 Author ID:** {row['author_id']}")
                        #     st.markdown(f"**👤 Name:** {row['name']}")
                        #     st.markdown(f"**📧 Email:** {row['email'] or 'N/A'}")
                        #     st.markdown(f"**📞 Phone:** {row['phone'] or 'N/A'}")

                        # if row['author_photo']:
                        #     col1, col2 = st.columns([1, 2])

                        #     with col1:
                        #         st.image(row['author_photo'],width = 100)

                        #     with col2:
                        #         st.markdown(f"**📌 Author ID:** {row['author_id']}")
                        #         st.markdown(f"**👤 Name:** {row['name']}")
                        #         st.markdown(f"**📧 Email:** {row['email'] or 'N/A'}")
                        #         st.markdown(f"**📞 Phone:** {row['phone'] or 'N/A'}")

                        # else:
                        #     col1, col2 = st.columns(2)
                        #     with col1:
                        #         st.markdown(f"**📌 Author ID:** {row['author_id']}")
                        #         st.markdown(f"**👤 Name:** {row['name']}")
                        #     with col2:
                        #         st.markdown(f"**📧 Email:** {row['email'] or 'N/A'}")
                        #         st.markdown(f"**📞 Phone:** {row['phone'] or 'N/A'}")


                        if row['author_photo']:

                            col1, col2, col3 = st.columns([0.3,0.6,1], gap="small")

                            with col1:
                                st.image(row['author_photo'],width = 100)
                            
                            with col2:
                                st.markdown(f"**📌 Author ID:** {row['author_id']}")
                                st.markdown(f"**📞 Phone:** {row['phone'] or 'N/A'}")
                                
                            with col3:
                                st.markdown(f"**👤 Name:** {row['name']}")
                                st.markdown(f"**📧 Email:** {row['email'] or 'N/A'}")

                        else:
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**📌 Author ID:** {row['author_id']}")
                                st.markdown(f"**👤 Name:** {row['name']}")
                            with col2:
                                st.markdown(f"**📧 Email:** {row['email'] or 'N/A'}")
                                st.markdown(f"**📞 Phone:** {row['phone'] or 'N/A'}")                  

                        # Tabs for organizing fields
                        tab_titles = ["Checklists", "Basic Info", "Corrections", "Delivery"]
                        tab_objects = st.tabs(tab_titles)
                    
                        # Checklists tab (no form, no save button)
                        with tab_objects[0]:
                            # Payment status logic
                            total = float(row.get('total_amount', 0) or 0)
                            paid = float(row.get('amount_paid', 0) or 0)
                            if total <= 0:
                                p_status_html = '<div style="background-color:#f1f3f4; color:#5f6368; padding:4px; border-radius:5px; text-align:center; font-weight:bold; font-size:13px; margin-bottom:10px;">⚪ Payment Status: Pending</div>'
                            elif paid >= total:
                                p_status_html = '<div style="background-color:#e6f4ea; color:#137333; padding:4px; border-radius:5px; text-align:center; font-weight:bold; font-size:13px; margin-bottom:10px;">✅ Payment Status: Paid</div>'
                            elif paid > 0:
                                p_status_html = '<div style="background-color:#fef7e0; color:#b06000; padding:4px; border-radius:5px; text-align:center; font-weight:bold; font-size:13px; margin-bottom:10px;">🟠 Payment Status: Partially Paid</div>'
                            else:
                                p_status_html = '<div style="background-color:#fce8e6; color:#c5221f; padding:4px; border-radius:5px; text-align:center; font-weight:bold; font-size:13px; margin-bottom:10px;">🔴 Payment Status: Unpaid</div>'
                            
                            st.markdown(p_status_html, unsafe_allow_html=True)
                            
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
                                    update_book_authors(row['id'], {'welcome_mail_sent': int(updates_checklist['welcome_mail_sent'])}, conn)
                                
                                # Author Details Received - Display only, no auto-sync on dialog open
                                updates_checklist['author_details_sent'] = st.checkbox(
                                    "📥 Author Details Received",
                                    value=bool(row['author_details_sent']),
                                    help="Check if the author's details have been received.",
                                    key=f"author_details_sent_{row['id']}",
                                    disabled=False
                                )
                                
                                # Photo Received - Display only, no auto-sync on dialog open
                                updates_checklist['photo_recive'] = st.checkbox(
                                    "📷 Photo Received",
                                    value=bool(row['photo_recive']),
                                    help="Check if the author's photo has been received.",
                                    key=f"photo_recive_{row['id']}",
                                    disabled=False
                                )
                                
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
                                    help="Check if the digital book has been sent. (Disabled during active correction cycle)" if is_in_correction else "Check if the digital book has been sent.",
                                    key=f"digital_book_sent_{row['id']}",
                                    disabled=is_in_correction
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
                                    updates['publishing_consultant'] = st.text_input(
                                        "Publishing Consultant",
                                        value=row['publishing_consultant'] or "",
                                        help="Enter the name of the publishing consultant.",
                                        key=f"publishing_consultant_{row['id']}"
                                    )

                                    updates['corresponding_agent'] = st.text_input(
                                        "Corresponding Author/Agent",
                                        value=row['corresponding_agent'] or "",
                                        help="Enter the name of the corresponding agent.",
                                        key=f"corresponding_agent_{row['id']}"
                                    )

                            
                                # New Fields for Author Table (collected separately as they belong to authors table)
                                author_updates = {}
                                col_city, col_state = st.columns(2)
                                with col_city:
                                    author_updates['city'] = st.text_input(
                                        "City",
                                        value=row['city'] if row['city'] is not None else "",
                                        key=f"city_{row['id']}"
                                    )
                                with col_state:
                                    author_updates['state'] = st.text_input(
                                        "State",
                                        value=row['state'] if row['state'] is not None else "",
                                        key=f"state_{row['id']}"
                                    )

                                author_updates['about_author'] = st.text_area(
                                    "About The Author",
                                    value=row['about_author'] if row['about_author'] is not None else "",
                                    key=f"about_{row['id']}",
                                    height=200
                                )
                                updates['delivery_address'] = st.text_area(
                                    "Delivery Address",
                                    value=row['delivery_address'] or "",
                                    height=100,
                                    help="Enter the delivery address.",
                                    key=f"delivery_address_{row['id']}"
                                )

                                current_photo = row['author_photo'] if row['author_photo'] is not None else None
                                uploaded_photo = st.file_uploader("Upload Author Photo", type=['jpg', 'png', 'jpeg'], key=f"photo_{row['id']}")
                                if current_photo:
                                    if os.path.exists(current_photo):
                                        with open(current_photo, "rb") as file:
                                            st.download_button(
                                                label="⬇️ Download Photo",
                                                data=file,
                                                file_name=os.path.basename(current_photo),
                                                mime="image/jpeg",
                                                key=f"dl_{row['id']}"
                                            )
                                    else:
                                        st.caption("⚠️ File record exists but file missing.")
                            
                            # Tab 3: Delivery
                            with tab_objects[3]:
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
                                if st.form_submit_button("💾 Save Changes", width="stretch", type="primary"):
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
                                
                                    # Handle Author Table Updates
                                    author_changes = []
                                    photo_path = current_photo
                                
                                    if uploaded_photo:
                                        try:
                                            import time
                                            file_extension = os.path.splitext(uploaded_photo.name)[1]
                                            # Use author name and ID for filename
                                            author_name_clean = row['name'].replace(" ", "_").replace("/", "_").replace("\\", "_")
                                            unique_filename = f"{author_name_clean}_{author_id}{file_extension}"
                                            save_path = os.path.join(AUTHOR_PHOTO_UPLOAD_DIR, unique_filename)
                                            
                                            if not os.path.exists(AUTHOR_PHOTO_UPLOAD_DIR):
                                                os.makedirs(AUTHOR_PHOTO_UPLOAD_DIR)
                                                
                                            with open(save_path, "wb") as f:
                                                f.write(uploaded_photo.getbuffer())
                                            
                                            photo_path = save_path
                                            author_updates['author_photo'] = photo_path
                                            author_changes.append("Updated Author Photo")
                                        except Exception as e:
                                            st.error(f"Failed to upload photo: {e}")
                                
                                    if author_updates.get('about_author') != row['about_author']:
                                        author_changes.append("Updated About Author")

                                    if author_updates.get('city') != row['city']:
                                        author_changes.append("Updated City")
                                    
                                    if author_updates.get('state') != row['state']:
                                        author_changes.append("Updated State")
                                        
                                    # Determine if auto-checkboxes need to be updated (separate from main changes)
                                    auto_check_author_details = False
                                    auto_check_photo = False
                                    
                                    # Check if about_author has content after save
                                    has_about = bool(author_updates.get('about_author') and str(author_updates.get('about_author')).strip())
                                    if has_about and not bool(row['author_details_sent']):
                                        # Only set to 1 if it's currently not checked
                                        updates['author_details_sent'] = 1
                                        auto_check_author_details = True
                                
                                    # Check if photo was uploaded
                                    has_photo_file = bool(photo_path and str(photo_path).strip())
                                    if has_photo_file and not bool(row['photo_recive']):
                                        # Only set to 1 if it's currently not checked
                                        updates['photo_recive'] = 1
                                        auto_check_photo = True
                                        
                                    try:
                                        with st.spinner("Saving changes..."):
                                            import time
                                            time.sleep(1)
                                        
                                            # Update book_authors table
                                            update_book_authors(row['id'], updates, conn)
                                        
                                            # Update authors table if needed
                                            if author_changes:
                                                with conn.session as s:
                                                    update_query = "UPDATE authors SET about_author = :about_author, city = :city, state = :state"
                                                    params = {
                                                        "about_author": author_updates['about_author'], 
                                                        "city": author_updates['city'],
                                                        "state": author_updates['state'],
                                                        "author_id": author_id
                                                    }
                                                
                                                    if 'author_photo' in author_updates:
                                                        update_query += ", author_photo = :author_photo"
                                                        params["author_photo"] = author_updates['author_photo']
                                                
                                                    update_query += " WHERE author_id = :author_id"
                                                    s.execute(text(update_query), params)
                                                    s.commit()
                                                
                                                changes.extend(author_changes)
                                            
                                            # Log main save action (without auto-checkbox changes)
                                            if changes:
                                                log_activity(
                                                    conn,
                                                    st.session_state.user_id,
                                                    st.session_state.username,
                                                    st.session_state.session_id,
                                                    "updated author details",
                                                    f"Book ID: {book_id}, Author ID: {author_id}, {', '.join(changes)}"
                                                )
                                            
                                            # Log auto-checkbox updates separately
                                            if auto_check_author_details:
                                                log_activity(
                                                    conn,
                                                    st.session_state.user_id,
                                                    st.session_state.username,
                                                    st.session_state.session_id,
                                                    "updated checklist",
                                                    f"Book ID: {book_id}, Author ID: {author_id}, Author Details Received changed to 'True'"
                                                )
                                            
                                            if auto_check_photo:
                                                log_activity(
                                                    conn,
                                                    st.session_state.user_id,
                                                    st.session_state.username,
                                                    st.session_state.session_id,
                                                    "updated checklist",
                                                    f"Book ID: {book_id}, Author ID: {author_id}, Photo Received changed to 'True'"
                                                )
                                            
                                            st.cache_data.clear()
                                            st.success(f"✔️ Updated details for {row['name']} (Author ID: {author_id})")
                                            st.toast(f"Updated details for {row['name']} (Author ID: {author_id})", icon="✔️", duration="long")
                                    except Exception as e:
                                        st.error(f"❌ Error updating author details: {e}")
                                        st.toast("Error updating author details", icon="❌", duration="long")
                            with col_remove:
                                confirmation_key = f"confirm_remove_{row['id']}"
                                if confirmation_key not in st.session_state:
                                    st.session_state[confirmation_key] = False
                                if st.form_submit_button("🗑️", width="stretch", type="secondary", help=f"Remove {row['name']} from this book"):
                                    st.session_state[confirmation_key] = True
                        # Confirmation form for removal
                        if st.session_state[confirmation_key]:
                            with st.form(f"confirm_form_{row['id']}", border=False):
                                st.warning(f"Are you sure you want to remove {row['name']} (Author ID: {row['author_id']}) from Book ID: {book_id}?")
                                col_confirm, col_cancel = st.columns(2)
                                with col_confirm:
                                    if st.form_submit_button("Yes, Remove", width="stretch", type="primary"):
                                        try:
                                            with st.spinner("Removing author..."):
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
                                                st.toast(f"Removed {row['name']} (Author ID: {author_id}) from this book", icon="✔️", duration="long")
                                                st.session_state[confirmation_key] = False
                                        except Exception as e:
                                            st.error(f"❌ Error removing author: {e}")
                                            st.toast(f"Error removing author:", icon="❌", duration="long")
                                with col_cancel:
                                    if st.form_submit_button("Cancel", width="stretch"):
                                        st.session_state[confirmation_key] = False

                        # Corrections Tab
                        with tab_objects[2]:
                            st.markdown("#### 📝 Author Corrections")

                            # Fetch all team correction tasks for status mapping
                            try:
                                with conn.session as s:
                                    team_tasks = s.execute(
                                        text("SELECT * FROM corrections WHERE book_id = :book_id"),
                                        {"book_id": book_id}
                                    ).fetchall()
                                
                                # Display existing corrections
                                with conn.session as s:
                                    author_corrections = s.execute(
                                        text("SELECT ac.*, COALESCE(a.name, 'Internal Team') as author_name FROM author_corrections ac LEFT JOIN authors a ON ac.author_id = a.author_id WHERE ac.book_id = :book_id AND (ac.author_id = :author_id OR ac.author_id IS NULL) ORDER BY ac.created_at DESC"),
                                        {"book_id": book_id, "author_id": author_id}
                                    ).fetchall()
                                
                                if author_corrections:
                                    for corr in author_corrections:
                                        # Determine status for this specific round
                                        r_num = getattr(corr, 'round_number', 1)
                                        round_tasks = [t for t in team_tasks if t.round_number == r_num]
                                        active_task_for_round = next((t for t in round_tasks if t.correction_end is None), None)
                                        
                                        if active_task_for_round:
                                            status_text = f"🚀 {active_task_for_round.section.capitalize()}"
                                            status_color = "#e65100" # Orange
                                            badge_bg = "#fff3e0"
                                        elif round_tasks:
                                            if correction_status == 'None' or correction_status is None:
                                                status_text = "✅ Completed"
                                                status_color = "#2e7d32" # Green
                                                badge_bg = "#e8f5e9"
                                            else:
                                                status_text = f"⏳ {correction_status}"
                                                status_color = "#1967d2" # Blue
                                                badge_bg = "#e8f0fe"
                                        else:
                                            status_text = "🕒 Wait for Team"
                                            status_color = "#666666" # Grey
                                            badge_bg = "#f5f5f5"

                                        with st.container(border=True):
                                            # Header row with Round and Status Badge
                                            h_col1, h_col2 = st.columns([1, 1])
                                            with h_col1:
                                                st.markdown(f"**🔄 Round {r_num}**")
                                            with h_col2:
                                                st.markdown(
                                                    f'<div style="text-align:right;">'
                                                    f'<span style="background-color:{badge_bg}; color:{status_color}; '
                                                    f'padding:2px 8px; border-radius:10px; font-size:12px; font-weight:bold; '
                                                    f'border:1px solid {status_color}44;">{status_text}</span>'
                                                    f'</div>', 
                                                    unsafe_allow_html=True
                                                )
                                            
                                            st.write("") # Spacer
                                            
                                            # Content Section
                                            st.markdown(f"**📝 Request Details**")
                                            st.info(f"**From:** {corr.author_name}  \n{corr.correction_text}" if corr.correction_text else f"**From:** {corr.author_name}  \n*No text provided*")
                                            
                                            # Footer with date and file
                                            f_col1, f_col2 = st.columns([2, 1], vertical_alignment="center")
                                            with f_col1:
                                                st.caption(f"📅 Requested on: {corr.created_at.strftime('%d %b %Y, %I:%M %p') if hasattr(corr.created_at, 'strftime') else corr.created_at}")
                                            
                                            with f_col2:
                                                if corr.correction_file:
                                                    if os.path.exists(corr.correction_file):
                                                        with open(corr.correction_file, "rb") as f:
                                                            st.download_button(
                                                                label="⬇️ Download File",
                                                                data=f,
                                                                file_name=os.path.basename(corr.correction_file),
                                                                key=f"dl_corr_{corr.id}",
                                                                use_container_width=True,
                                                                type="secondary"
                                                            )
                                                    else:
                                                        st.caption("⚠️ File missing")
                                            
                                            # Mini Timeline for this round if tasks exist
                                            if round_tasks:
                                                with st.expander("🛠️ Round Progress", expanded=False):
                                                    for t in sorted(round_tasks, key=lambda x: x.correction_start):
                                                        done = t.correction_end is not None
                                                        t_status = "✅" if done else "⏳"
                                                        st.markdown(f"<small>{t_status} **{t.section.capitalize()}**: {t.worker}</small>", unsafe_allow_html=True)
                                else:
                                    st.info("No corrections found.")
                            except Exception as e:
                                st.error(f"Error fetching corrections: {e}")

                            st.write("---")
                            st.markdown("##### ➕ Add New Correction")
                            
                            if not row['digital_book_sent']:
                                st.warning("The book has not be sent to the author yet. Please send the digital book before adding corrections.")
                            else:
                                if active_task:
                                    st.warning(f"⚠️ A correction is currently in progress by the **{active_task.section.capitalize()}** team. Please wait for them to finish before adding another request.")
                                else:
                                    with st.form(key=f"add_correction_form_{row['id']}", border=False):
                                        correction_text = st.text_area("Correction Details", key=f"corr_text_{row['id']}")
                                        correction_file = st.file_uploader("Upload File", key=f"corr_file_{row['id']}")
                                        
                                        if st.form_submit_button("Submit Correction", type="primary"):
                                            if not correction_text and not correction_file:
                                                st.error("Please provide text or a file.")
                                            else:
                                                try:
                                                    with st.spinner("Adding correction..."):
                                                        import time
                                                        time.sleep(2)
                                                        file_path = None
                                                        if correction_file:
                                                            # Define upload dir
                                                            if not os.path.exists(CORRECTION_FIL_DIR):
                                                                os.makedirs(CORRECTION_FIL_DIR)
                                                            
                                                            # Save file
                                                            file_ext = os.path.splitext(correction_file.name)[1]
                                                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                                            filename = f"corrections_{book_id}_{book_title}_{timestamp}{file_ext}"
                                                            file_path = os.path.join(CORRECTION_FIL_DIR, filename)
                                                            
                                                            with open(file_path, "wb") as f:
                                                                f.write(correction_file.getbuffer())
                                                        
                                                        # Insert DB
                                                        with conn.session as s:
                                                            # Determine Round Number
                                                            book_info = s.execute(
                                                                text("SELECT correction_status FROM books WHERE book_id = :book_id"),
                                                                {"book_id": book_id}
                                                            ).fetchone()
                                                            
                                                            # Get max round from author_corrections to ensure consistency
                                                            max_round_res = s.execute(
                                                                text("SELECT COALESCE(MAX(round_number), 0) FROM author_corrections WHERE book_id = :book_id"),
                                                                {"book_id": book_id}
                                                            ).scalar()
                                                            
                                                            status = book_info.correction_status if book_info else 'None'
                                                            
                                                            # If starting a new cycle (Status is None), the round will be incremented
                                                            if status == 'None' or status is None:
                                                                current_round = max_round_res + 1
                                                            else:
                                                                current_round = max_round_res

                                                            s.execute(
                                                                text("""
                                                                    INSERT INTO author_corrections (book_id, author_id, correction_text, correction_file, round_number)
                                                                    VALUES (:book_id, :author_id, :correction_text, :correction_file, :round_number)
                                                                """),
                                                                {
                                                                    "book_id": book_id,
                                                                    "author_id": author_id,
                                                                    "correction_text": correction_text,
                                                                    "correction_file": file_path,
                                                                    "round_number": current_round
                                                                }
                                                            )
                                                            
                                                            # Uncheck digital_book_sent for ALL authors of this book
                                                            s.execute(
                                                                text("UPDATE book_authors SET digital_book_sent = 0 WHERE book_id = :book_id"),
                                                                {"book_id": book_id}
                                                            )
                                                            
                                                            # Trigger Correction Lifecycle
                                                            # If not currently in a correction cycle (status is None), start new cycle (Writing)
                                                            # If already in a cycle (Writing/Proofreading/Formatting), just leave it (new tasks added to current cycle)
                                                            s.execute(
                                                                text("""
                                                                    UPDATE books 
                                                                    SET correction_status = CASE 
                                                                            WHEN correction_status = 'None' THEN 'Writing' 
                                                                            ELSE correction_status 
                                                                        END
                                                                    WHERE book_id = :book_id
                                                                """),
                                                                {"book_id": book_id}
                                                            )
                                                            
                                                            s.commit()

                                                        # Log the correction
                                                        log_activity(
                                                            conn,
                                                            st.session_state.user_id,
                                                            st.session_state.username,
                                                            st.session_state.session_id,
                                                            "added correction",
                                                            f"Book ID: {book_id}, Author ID: {author_id}, File: {os.path.basename(file_path) if file_path else 'None'}"
                                                        )

                                                        # Log the mass uncheck
                                                        log_activity(
                                                            conn,
                                                            st.session_state.user_id,
                                                            st.session_state.username,
                                                            st.session_state.session_id,
                                                            "updated checklist",
                                                            f"Book ID: {book_id}, Reset Digital Book Sent to 'False' for all authors due to new correction"
                                                        )
                                                        
                                                        st.success("✅ Correction added successfully! Digital Book status reset for all authors.")
                                                        st.rerun()
                                                except Exception as e:
                                                    st.error(f"Error adding correction: {e}")

    with tab2:
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
                            "city": editor['city'],
                            "state": editor['state'],
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
                            "city": "",
                            "state": "",
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
                                                "city": selected_editor_details.city,
                                                "state": selected_editor_details.state,
                                                "author_id": selected_editor_id
                                            })
                                            
                                            # Display Read-Only Details
                                            st.markdown(f"""
                                                <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 14px;">
                                                    <strong>👤 Name:</strong> {selected_editor_details.name}<br>
                                                    <strong>📧 Email:</strong> {selected_editor_details.email}<br>
                                                    <strong>📱 Phone:</strong> {selected_editor_details.phone}<br>
                                                    <strong>🏙️ City:</strong> {selected_editor_details.city or 'N/A'}<br>
                                                    <strong>🗺️ State:</strong> {selected_editor_details.state or 'N/A'}
                                                </div>
                                            """, unsafe_allow_html=True)
                                            
                                    elif selected_editor == "Select Existing Editor":
                                        editor["author_id"] = None
                                        editor.update({
                                            "name": "",
                                            "email": "",
                                            "phone": "",
                                            "corresponding_agent": "",
                                            "publishing_consultant": ""
                                        })

                                    available_positions = ["1st", "2nd", "3rd", "4th"]
                                    current_positions = [e["author_position"] for k, e in enumerate(edit_data["editors"]) if k != j and e["author_position"]]
                                    available_positions = [p for p in available_positions if p not in current_positions]

                                    if editor["author_id"]:
                                         # Read-Only Mode (Display Position Only)
                                         editor["author_position"] = st.selectbox(
                                            "Position",
                                            available_positions,
                                            index=available_positions.index(editor["author_position"]) if editor["author_position"] in available_positions else 0,
                                            key=f"edit_chapter_{chapter_id}_editor_position_{j}"
                                        )
                                    else:
                                        # Editable Mode
                                        col1, col2 = st.columns(2)
                                        editor["name"] = col1.text_input(
                                            "Name",
                                            value=editor["name"],
                                            key=f"edit_chapter_{chapter_id}_editor_name_{j}"
                                        )
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

                                        col_c1, col_c2 = st.columns(2)
                                        editor["city"] = col_c1.text_input(
                                            "City",
                                            value=editor["city"],
                                            key=f"edit_chapter_{chapter_id}_editor_city_{j}"
                                        )
                                        editor["state"] = col_c2.text_input(
                                            "State",
                                            value=editor["state"],
                                            key=f"edit_chapter_{chapter_id}_editor_state_{j}"
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
                                        import time
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
                                                                    INSERT INTO authors (name, email, phone, city, state)
                                                                    VALUES (:name, :email, :phone, :city, :state)
                                                                """),
                                                                {
                                                                    "name": editor["name"],
                                                                    "email": editor["email"] or None,
                                                                    "phone": editor["phone"] or None,
                                                                    "city": editor["city"] or None,
                                                                    "state": editor["state"] or None
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
                                                st.toast("Chapter updated successfully!", icon="✔️", duration="long")
                                                st.cache_data.clear()
                                            except Exception as e:
                                                st.error(f"❌ Error updating chapter: {e}")
                                                st.toast(f"Error updating chapter: {e}", icon="❌", duration="long")
                                                with conn.session as s:
                                                    s.rollback()

                            with col_delete:
                                if st.button("Delete Chapter", key=f"delete_chapter_{chapter_id}"):
                                    with st.spinner("Deleting chapter..."):
                                        import time
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
                                            st.toast("Chapter deleted successfully!", icon="✔️", duration="long")
                                            st.cache_data.clear()
                                        except Exception as e:
                                            st.error(f"❌ Error deleting chapter: {e}")
                                            st.toast(f"Error deleting chapter: {e}", icon="❌", duration="long")
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
                                    "city": "",
                                    "state": "",
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
                        "name": "", "email": "", "phone": "", "city": "", "state": "", "author_id": None, "author_position": None,
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
                                            "city": selected_editor_details.city,
                                            "state": selected_editor_details.state,
                                            "author_id": selected_editor_id,
                                            "corresponding_agent": "",
                                            "publishing_consultant": ""
                                        })
                                        
                                        # Display Read-Only Details
                                        st.markdown(f"""
                                            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 14px;">
                                                <strong>👤 Name:</strong> {selected_editor_details.name}<br>
                                                <strong>📧 Email:</strong> {selected_editor_details.email}<br>
                                                <strong>📱 Phone:</strong> {selected_editor_details.phone}<br>
                                                <strong>🏙️ City:</strong> {selected_editor_details.city or 'N/A'}<br>
                                                <strong>🗺️ State:</strong> {selected_editor_details.state or 'N/A'}
                                            </div>
                                        """, unsafe_allow_html=True)
                                    
                            elif selected_editor == "Add New Editor":
                                editor["author_id"] = None
                                editor.update({
                                    "name": editor.get("name", ""),
                                    "email": editor.get("email", ""),
                                    "phone": editor.get("phone", ""),
                                    "corresponding_agent": editor.get("corresponding_agent", ""),
                                    "publishing_consultant": editor.get("publishing_consultant", "")
                                })

                            available_positions = ["1st", "2nd", "3rd", "4th"]
                            current_positions = [e["author_position"] for k, e in enumerate(chapter["editors"]) if k != j and e["author_position"]]
                            available_positions = [p for p in available_positions if p not in current_positions]

                            if editor["author_id"]:
                                # Read-Only Mode
                                editor["author_position"] = st.selectbox(
                                    "Position",
                                    available_positions,
                                    index=available_positions.index(editor["author_position"]) if editor["author_position"] in available_positions else 0,
                                    key=f"new_chapter_editor_position_{j}"
                                )
                            else:
                                # Editable Mode
                                col1, col2 = st.columns(2)
                                editor["name"] = col1.text_input(
                                    "Name",
                                    editor["name"],
                                    key=f"new_chapter_editor_name_{j}"
                                )
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

                                col_nc1, col_nc2 = st.columns(2)
                                editor["city"] = col_nc1.text_input(
                                    "City",
                                    editor["city"],
                                    key=f"new_chapter_editor_city_{j}"
                                )
                                editor["state"] = col_nc2.text_input(
                                    "State",
                                    editor["state"],
                                    key=f"new_chapter_editor_state_{j}"
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
                            import time
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
                                                        INSERT INTO authors (name, email, phone, city, state)
                                                        VALUES (:name, :email, :phone, :city, :state)
                                                    """),
                                                    {
                                                        "name": editor["name"],
                                                        "email": editor["email"] or None,
                                                        "phone": editor["phone"] or None,
                                                        "city": editor["city"] or None,
                                                        "state": editor["state"] or None
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
                                    st.toast("Chapter and editors added successfully!", icon="✔️", duration="long")
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
                        st.toast("Can't Change Author Type", icon="❌", duration="long")
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
                                st.toast(f"Author type changed to {selected_author_type}", icon="✔️", duration="long")
                                log_activity(
                                    conn,
                                    st.session_state.user_id,
                                    st.session_state.username,
                                    st.session_state.session_id,
                                    "changed author type",
                                    f"Book ID: {book_id}, New Author Type: {selected_author_type}"
                                )
                        except Exception as e:
                            st.error(f"❌ Error updating author type: {e}")
                            st.toast(f"Error updating author type: {e}", icon="❌", duration="long")
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

                cols = st.columns(2)

                # Iterate through available slots and assign each expander to a column
                for i in range(available_slots):
                    with cols[i % num_columns]:
                        with st.expander(f"New Author {i+1}", expanded=True):
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
                                    
                                    # Display Read-Only Details
                                    st.markdown(f"""
                                        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 14px;">
                                            <strong>👤 Name:</strong> {selected_author_details.name}<br>
                                            <strong>📧 Email:</strong> {selected_author_details.email}<br>
                                            <strong>📱 Phone:</strong> {selected_author_details.phone}
                                        </div>
                                    """, unsafe_allow_html=True)

                            elif selected_author == "Add New Author" and not disabled:
                                st.session_state.new_authors[i]["author_id"] = None
                                
                                col1, col2 = st.columns(2)
                                st.session_state.new_authors[i]["name"] = col1.text_input(
                                    f"Author Name {i+1}", st.session_state.new_authors[i]["name"], key=f"new_name_{i}",
                                    disabled=disabled
                                )

                            available_positions = [pos for pos in ["1st", "2nd", "3rd", "4th"] if pos not in 
                                                (existing_positions + [a["author_position"] for j, a in enumerate(st.session_state.new_authors) if j != i and a["author_position"]])]
                            
                            if selected_author != "Add New Author" and not disabled:
                                st.session_state.new_authors[i]["author_position"] = st.selectbox(
                                    f"Position {i+1}",
                                    available_positions,
                                    key=f"new_author_position_{i}",
                                    disabled=disabled or not available_positions
                                ) if available_positions else st.error("❌ No available positions left.")
                            
                            elif selected_author == "Add New Author" and not disabled:
                                st.session_state.new_authors[i]["author_position"] = col2.selectbox(
                                    f"Position {i+1}",
                                    available_positions,
                                    key=f"new_author_position_{i}",
                                    disabled=disabled or not available_positions
                                ) if available_positions else st.error("❌ No available positions left.")

                            if selected_author == "Add New Author" and not disabled:
                                col3, col4 = st.columns(2)
                                st.session_state.new_authors[i]["phone"] = col3.text_input(
                                    f"Phone {i+1}", st.session_state.new_authors[i]["phone"], key=f"new_phone_{i}",
                                    disabled=disabled
                                )
                                st.session_state.new_authors[i]["email"] = col4.text_input(
                                    f"Email {i+1}", st.session_state.new_authors[i]["email"], key=f"new_email_{i}",
                                    disabled=disabled
                                )

                                col_city, col_state = st.columns(2)
                                st.session_state.new_authors[i]["city"] = col_city.text_input(
                                    f"City {i+1}", st.session_state.new_authors[i]["city"], key=f"new_city_{i}",
                                    disabled=disabled
                                )
                                st.session_state.new_authors[i]["state"] = col_state.text_input(
                                    f"State {i+1}", st.session_state.new_authors[i]["state"], key=f"new_state_{i}",
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

                send_welcome_new_authors = st.checkbox("Send welcome email to newly added authors", 
                                                       value=False, 
                                                       key="send_welcome_new_authors_chk", 
                                                       disabled=True,
                                                       help="Feature coming soon.")
                
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
                                                author_id_to_link = insert_author(conn, author["name"], author["email"], author["phone"], author["city"], author["state"])
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
                                            # Store author details for logging and email
                                            added_authors.append({
                                                "author_id": author_id_to_link,
                                                "name": author["name"],
                                                "email": author["email"],
                                                "phone": author["phone"],
                                                "author_position": author["author_position"],
                                                "corresponding_agent": author["corresponding_agent"],
                                                "publishing_consultant": author["publishing_consultant"]
                                            })
                                    s.commit()
                                    
                                    # Send welcome emails if requested
                                    if authors_added and send_welcome_new_authors:
                                        with st.status("Sending Welcome Emails...", expanded=True) as status:
                                            for author in added_authors:
                                                if author.get("email") and author.get("author_id"):
                                                    st.write(f"Sending email to {author['name']}...")
                                                    email_status = "Failed"
                                                    subject_line = f"Publication Confirmation - {book_title}"
                                                    
                                                    email_success, sender_email = send_welcome_email(author["email"], author["name"], author["phone"], book_title, book_id, author["author_id"], author["author_position"], publisher)
                                                    if email_success:
                                                        email_status = "Success"
                                                        s.execute(text("""
                                                            UPDATE book_authors 
                                                            SET welcome_mail_sent = 1 
                                                            WHERE book_id = :book_id AND author_id = :author_id
                                                        """), {"book_id": book_id, "author_id": author["author_id"]})
                                                        st.write(f"✅ Sent to {author['name']}")
                                                    else:
                                                        email_status = "Failed"
                                                        st.write(f"❌ Failed to send to {author['name']}")
                                                    
                                                    # Log activity for email send
                                                    log_activity(
                                                        conn,
                                                        st.session_state.user_id,
                                                        st.session_state.username,
                                                        st.session_state.session_id,
                                                        "sent welcome email",
                                                        f"To: {author['name']} ({author['email']}), Book ID: {book_id}, Status: {email_status}"
                                                    )
                                                    
                                                    # Insert into email_history
                                                    try:
                                                        s.execute(text("""
                                                            INSERT INTO email_history (timestamp, recipient, sender_email, status, book_id, book_title, triggered_by, details)
                                                            VALUES (:timestamp, :recipient, :sender_email, :status, :book_id, :book_title, :triggered_by, :details)
                                                        """), {
                                                            "timestamp": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                            "recipient": author["email"],
                                                            "sender_email": sender_email,
                                                            "status": email_status,
                                                            "book_id": book_id,
                                                            "book_title": book_title,
                                                            "triggered_by": st.session_state.username,
                                                            "details": f"Author: {author['name']}, Position: {author['author_position']}"
                                                        })
                                                    except Exception as e:
                                                        st.error(f"Failed to log email history: {str(e)}")
                                                        
                                            status.update(label="Welcome Emails Processed", state="complete", expanded=False)
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
                                    st.toast("New authors added successfully!", icon="✔️", duration="long")
                                    del st.session_state.new_authors
                                else:
                                    st.error("❌ No authors were added due to errors.")
                            except Exception as e:
                                st.error(f"❌ Error adding authors: {e}")
                                st.toast(f"Error adding authors: {e}", icon="❌", duration="long")

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

def rewrite_book_logic(book_id, reason, conn):
    """Archives current book operations to extra_books and resets them."""
    try:
        with conn.session as s:

            s.execute(text("""
                INSERT INTO extra_books (
                    book_id, title, date, reason,
                    writing_start, writing_end, writing_by,
                    proofreading_start, proofreading_end, proofreading_by,
                    formatting_start, formatting_end, formatting_by,
                    book_pages
                )
                SELECT 
                    book_id, title, date, :reason,
                    writing_start, writing_end, writing_by,
                    proofreading_start, proofreading_end, proofreading_by,
                    formatting_start, formatting_end, formatting_by,
                    book_pages
                FROM books
                WHERE book_id = :book_id
            """), {"book_id": book_id, "reason": reason})

            # 3. Reset details in books table
            s.execute(text("""
                UPDATE books SET
                    writing_start = NULL, writing_end = NULL, writing_by = NULL,
                    proofreading_start = NULL, proofreading_end = NULL, proofreading_by = NULL,
                    formatting_start = NULL, formatting_end = NULL, formatting_by = NULL,
                    book_pages = 0
                WHERE book_id = :book_id
            """), {"book_id": book_id})

            s.commit()
        return True, "Book operations archived and reset successfully!"
    except Exception as e:
        return False, f"Error rewriting book: {str(e)}"

@st.dialog("Edit Operation Details", width='medium', on_dismiss="rerun")
def edit_operation_dialog(book_id, conn):
    # Fetch book details for title, is_publish_only, is_thesis_to_book, and syllabus_path
    book_details = fetch_book_details(book_id, conn)
    is_publish_only = False
    is_thesis_to_book = False
    current_syllabus_path = None
    
    # Fetch operation details EARLY to use for button logic
    query = f"""
        SELECT writing_start, writing_end, writing_by, 
               proofreading_start, proofreading_end, proofreading_by, 
               formatting_start, formatting_end, formatting_by, 
               cover_start, cover_end, cover_by, book_pages,
               about_book, about_book_200
        FROM books WHERE book_id = {book_id}
    """
    book_operations = conn.query(query, show_spinner=False)
    
    if book_operations.empty:
        current_data = {}
        writing_done = False
    else:
        current_data = book_operations.iloc[0].to_dict()
        writing_done = pd.notna(current_data.get('writing_end'))

    # Check for print confirmation
    print_conf_query = "SELECT COUNT(*) as count FROM book_authors WHERE book_id = :book_id AND printing_confirmation = 1"
    print_conf_res = conn.query(print_conf_query, params={"book_id": book_id}, show_spinner=False)
    has_print_conf = print_conf_res.iloc[0]['count'] > 0 if not print_conf_res.empty else False

    if not book_details.empty:
        book_title = book_details.iloc[0]['title']
        is_publish_only = book_details.iloc[0].get('is_publish_only', 0) == 1
        is_thesis_to_book = book_details.iloc[0].get('is_thesis_to_book', 0) == 1
        current_syllabus_path = book_details.iloc[0].get('syllabus_path', None)
        
        col1, col2 = st.columns([5, 2])
        with col1:
            st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
        with col2:
            if st.button("🔄 Refresh", key="refresh_operations", type="tertiary", use_container_width=True):
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

    st.write("")  # Spacer

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

    # --- Tabs Layout ---
    tabs_list = ["✍️ Writing", "🔍 Proofreading", "📏 Formatting", "🎨 Book Cover", "ℹ️ About Book", "🔧 Corrections"]
    op_tabs = st.tabs(tabs_list)

    # ==========================
    # TAB 1: Writing
    # ==========================
    with op_tabs[0]:
        with st.container(border=True):
            if is_publish_only or is_thesis_to_book:
                st.warning("Writing section is disabled (Publish Only / Thesis to Book).")

            # Download link if exists
            if not (is_publish_only or is_thesis_to_book) and current_syllabus_path and os.path.exists(current_syllabus_path):
                with open(current_syllabus_path, "rb") as f:
                    st.download_button(
                        label="Download Current Syllabus",
                        data=f,
                        file_name=os.path.basename(current_syllabus_path),
                        key=f"download_syllabus_{book_id}",
                        use_container_width=True
                    )
            
            with st.form(key=f"writing_form_{book_id}", border=False):
                # Worker selection
                selected_writer = st.selectbox(
                    "Writer",
                    writing_options,
                    index=(writing_options.index(st.session_state[f"writing_by_{book_id}"]) 
                           if f"writing_by_{book_id}" in st.session_state and st.session_state[f"writing_by_{book_id}"] in writing_options else 0),
                    key=f"writing_select_{book_id}",
                    disabled=is_publish_only or is_thesis_to_book
                )
                new_writer = ""
                if selected_writer == "Add New..." and not (is_publish_only or is_thesis_to_book):
                    new_writer = st.text_input(
                        "New Writer Name",
                        key=f"writing_new_input_{book_id}",
                        placeholder="Enter new writer name..."
                    )
                    if new_writer:
                        st.session_state[f"writing_by_{book_id}"] = new_writer
                elif selected_writer != "Select Writer" and not (is_publish_only or is_thesis_to_book):
                    st.session_state[f"writing_by_{book_id}"] = selected_writer

                writing_by = st.session_state[f"writing_by_{book_id}"] if f"writing_by_{book_id}" in st.session_state and st.session_state[f"writing_by_{book_id}"] != "Select Writer" else ""

                # DateTime Inputs
                col_dt1, col_dt2 = st.columns(2)
                with col_dt1:
                    w_start_val = current_data.get('writing_start')
                    if pd.isna(w_start_val): w_start_val = None
                    writing_start_dt = st.datetime_input(
                        "Start",
                        value=w_start_val,
                        key=f"writing_start_dt_{book_id}",
                        disabled=is_publish_only or is_thesis_to_book
                    )
                with col_dt2:
                    w_end_val = current_data.get('writing_end')
                    if pd.isna(w_end_val): w_end_val = None
                    writing_end_dt = st.datetime_input(
                        "End",
                        value=w_end_val,
                        key=f"writing_end_dt_{book_id}",
                        disabled=is_publish_only or is_thesis_to_book
                    )

                book_pages = st.number_input(
                    "Total Book Pages",
                    min_value=0,
                    value=current_data.get('book_pages', 0) if current_data.get('book_pages') is not None else 0,
                    step=1,
                    key=f"book_pages_writing_{book_id}",
                    disabled=is_publish_only or is_thesis_to_book
                )

                # Book Syllabus Section
                if not (is_publish_only or is_thesis_to_book):
                    with st.expander("📂 Book Syllabus", expanded=False):
                        # Syllabus uploader
                        syllabus_file = st.file_uploader(
                            "Upload New Syllabus",
                            type=["pdf", "docx", "jpg", "jpeg", "png"],
                            key=f"syllabus_upload_{book_id}",
                            help="Upload a new syllabus to replace the existing one.",
                            label_visibility="collapsed",
                        )
                        if syllabus_file and current_syllabus_path:
                            st.caption("⚠️ Will replace existing syllabus.")
                        

                        # Download link moved outside form

                

                st.write("") # Spacer
                if st.form_submit_button("💾 Save Writing", width="stretch", disabled=is_publish_only or is_thesis_to_book, type="primary"):
                    with st.spinner("Saving..."):
                        os.makedirs(SYLLABUS_UPLOAD_DIR, exist_ok=True)
                        # Handle syllabus file upload
                        new_syllabus_path = current_syllabus_path
                        if syllabus_file and not (is_publish_only or is_thesis_to_book):
                            file_extension = os.path.splitext(syllabus_file.name)[1]
                            unique_filename = f"syllabus_{book_title.replace(' ', '_')}_{int(time.time())}{file_extension}"
                            new_syllabus_path_temp = os.path.join(SYLLABUS_UPLOAD_DIR, unique_filename)
                            try:
                                with open(new_syllabus_path_temp, "wb") as f:
                                    f.write(syllabus_file.getbuffer())
                                new_syllabus_path = new_syllabus_path_temp
                                if current_syllabus_path and current_syllabus_path != new_syllabus_path and os.path.exists(current_syllabus_path):
                                    try: os.remove(current_syllabus_path)
                                    except OSError: pass
                            except Exception as e:
                                st.error(f"Failed to save syllabus: {str(e)}")
                                raise

                        # Format dates
                        writing_start = writing_start_dt.strftime('%Y-%m-%d %H:%M:%S') if writing_start_dt else None
                        writing_end = writing_end_dt.strftime('%Y-%m-%d %H:%M:%S') if writing_end_dt else None

                        if writing_start and writing_end and writing_start > writing_end:
                            st.error("Start must be before End.")
                        else:
                            updates = {
                                "writing_start": writing_start,
                                "writing_end": writing_end,
                                "writing_by": writing_by if writing_by else None,
                                "book_pages": book_pages,
                                "syllabus_path": new_syllabus_path
                            }
                            update_operation_details(book_id, updates)
                            
                            syllabus_info = f"Syllabus: {os.path.basename(new_syllabus_path)}" if new_syllabus_path else "Syllabus: None"
                            details = (f"Book ID: {book_id}, Writer: {writing_by}, Pages: {book_pages}, {syllabus_info}")
                            log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "updated writing details", details)
                            st.success("Saved!")
                            st.toast("Updated Writing details", icon="✔️")
                            if selected_writer == "Add New..." and new_writer: st.cache_data.clear()

        with st.popover("Rewrite", use_container_width=True, type="tertiary"):
            if is_publish_only or is_thesis_to_book:
                st.error("⚠️ Cannot rewrite 'Publish Only' or 'Thesis to Book' projects.")
            elif not writing_done:
                st.error("⚠️ Writing must be completed before rewriting.")
            elif has_print_conf:
                st.error("⚠️ Cannot rewrite: Print confirmation already received.")
            else:
                st.markdown("### ⚠️ Confirm Rewrite")
                st.info("This will archive current progress to 'Extra Books' and reset operations.")
                rewrite_reason = st.text_area("Reason", placeholder="e.g. Quality issues...", key=f"reason_{book_id}")
                
                if st.button("Confirm", type="primary", key=f"rewrite_confirm_{book_id}", use_container_width=True):
                    if not rewrite_reason.strip():
                        st.error("Please provide a reason.")
                    else:
                        with st.spinner("Resetting book operations and moving to extra books..."):
                            time.sleep(5)
                            success, msg = rewrite_book_logic(book_id, rewrite_reason, conn)
                            if success:
                                st.success("Reset Complete!")
                                log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "rewrote book", f"Book ID: {book_id}, Reason: {rewrite_reason}, Moved to Extra Books")
                            else:
                                st.error(msg)

    # ==========================
    # TAB 2: Formatting
    # ==========================
    with op_tabs[2]:
        with st.container(border=True):
            with st.form(key=f"formatting_form_{book_id}", border=False):
                selected_formatter = st.selectbox(
                    "Formatter",
                    formatting_options,
                    index=(formatting_options.index(st.session_state[f"formatting_by_{book_id}"]) 
                        if f"formatting_by_{book_id}" in st.session_state and st.session_state[f"formatting_by_{book_id}"] in formatting_options else 0),
                    key=f"formatting_select_{book_id}"
                )
                new_formatter = ""
                if selected_formatter == "Add New...":
                    new_formatter = st.text_input("New Formatter Name", key=f"formatting_new_input_{book_id}")
                    if new_formatter: st.session_state[f"formatting_by_{book_id}"] = new_formatter
                elif selected_formatter != "Select Formatter":
                    st.session_state[f"formatting_by_{book_id}"] = selected_formatter

                formatting_by = st.session_state[f"formatting_by_{book_id}"] if f"formatting_by_{book_id}" in st.session_state and st.session_state[f"formatting_by_{book_id}"] != "Select Formatter" else ""

                col_dt1, col_dt2 = st.columns(2)
                with col_dt1:
                    f_start_val = current_data.get('formatting_start')
                    if pd.isna(f_start_val): f_start_val = None
                    formatting_start_dt = st.datetime_input("Start", value=f_start_val, key=f"formatting_start_dt_{book_id}")
                with col_dt2:
                    f_end_val = current_data.get('formatting_end')
                    if pd.isna(f_end_val): f_end_val = None
                    formatting_end_dt = st.datetime_input("End", value=f_end_val, key=f"formatting_end_dt_{book_id}")

                book_pages = st.number_input(
                    "Total Book Pages", min_value=0,
                    value=current_data.get('book_pages', 0) if current_data.get('book_pages') is not None else 0,
                    step=1, key=f"book_pages_formatting_{book_id}"
                )

                st.write("") # Spacer
                if st.form_submit_button("💾 Save Formatting", width="stretch", type="primary"):
                    with st.spinner("Saving..."):
                        formatting_start = formatting_start_dt.strftime('%Y-%m-%d %H:%M:%S') if formatting_start_dt else None
                        formatting_end = formatting_end_dt.strftime('%Y-%m-%d %H:%M:%S') if formatting_end_dt else None

                        if formatting_start and formatting_end and formatting_start > formatting_end:
                            st.error("Start must be before End.")
                        else:
                            updates = {
                                "formatting_start": formatting_start,
                                "formatting_end": formatting_end,
                                "formatting_by": formatting_by if formatting_by else None,
                                "book_pages": book_pages
                            }
                            update_operation_details(book_id, updates)
                            log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "updated formatting details", f"Book ID: {book_id}")
                            st.success("Saved!")
                            st.toast("Updated Formatting details", icon="✔️")
                            if selected_formatter == "Add New..." and new_formatter: st.cache_data.clear()

    # ==========================
    # TAB 3: Proofreading
    # ==========================
    with op_tabs[1]:
        with st.container(border=True):
            with st.form(key=f"proofreading_form_{book_id}", border=False):
                selected_proofreader = st.selectbox(
                    "Proofreader",
                    proofreading_options,
                    index=(proofreading_options.index(st.session_state[f"proofreading_by_{book_id}"]) 
                        if f"proofreading_by_{book_id}" in st.session_state and st.session_state[f"proofreading_by_{book_id}"] in proofreading_options else 0),
                    key=f"proofreading_select_{book_id}"
                )
                new_proofreader = ""
                if selected_proofreader == "Add New...":
                    new_proofreader = st.text_input("New Proofreader Name", key=f"proofreading_new_input_{book_id}")
                    if new_proofreader: st.session_state[f"proofreading_by_{book_id}"] = new_proofreader
                elif selected_proofreader != "Select Proofreader":
                    st.session_state[f"proofreading_by_{book_id}"] = selected_proofreader

                proofreading_by = st.session_state[f"proofreading_by_{book_id}"] if f"proofreading_by_{book_id}" in st.session_state and st.session_state[f"proofreading_by_{book_id}"] != "Select Proofreader" else ""

                col_dt1, col_dt2 = st.columns(2)
                with col_dt1:
                    p_start_val = current_data.get('proofreading_start')
                    if pd.isna(p_start_val): p_start_val = None
                    proofreading_start_dt = st.datetime_input("Start", value=p_start_val, key=f"proofreading_start_dt_{book_id}")
                with col_dt2:
                    p_end_val = current_data.get('proofreading_end')
                    if pd.isna(p_end_val): p_end_val = None
                    proofreading_end_dt = st.datetime_input("End", value=p_end_val, key=f"proofreading_end_dt_{book_id}")

                book_pages = st.number_input(
                    "Total Book Pages", min_value=0,
                    value=current_data.get('book_pages', 0) if current_data.get('book_pages') is not None else 0,
                    step=1, key=f"book_pages_proofreading_{book_id}"
                )

                st.write("") # Spacer
                if st.form_submit_button("💾 Save Proofreading", width="stretch", type="primary"):
                    with st.spinner("Saving..."):
                        proofreading_start = proofreading_start_dt.strftime('%Y-%m-%d %H:%M:%S') if proofreading_start_dt else None
                        proofreading_end = proofreading_end_dt.strftime('%Y-%m-%d %H:%M:%S') if proofreading_end_dt else None

                        if proofreading_start and proofreading_end and proofreading_start > proofreading_end:
                            st.error("Start must be before End.")
                        else:
                            updates = {
                                "proofreading_start": proofreading_start,
                                "proofreading_end": proofreading_end,
                                "proofreading_by": proofreading_by if proofreading_by else None,
                                "book_pages": book_pages
                            }
                            update_operation_details(book_id, updates)
                            log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "updated proofreading details", f"Book ID: {book_id}")
                            st.success("Saved!")
                            st.toast("Updated Proofreading details", icon="✔️")
                            if selected_proofreader == "Add New..." and new_proofreader: st.cache_data.clear()

    # ==========================
    # TAB 4: Cover
    # ==========================
    with op_tabs[3]:
        with st.container(border=True):
            with st.form(key=f"cover_form_{book_id}", border=False):
                selected_cover = st.selectbox(
                    "Cover Designer",
                    cover_options,
                    index=(cover_options.index(st.session_state[f"cover_by_{book_id}"]) 
                        if f"cover_by_{book_id}" in st.session_state and st.session_state[f"cover_by_{book_id}"] in cover_options else 0),
                    key=f"cover_select_{book_id}"
                )
                new_cover_designer = ""
                if selected_cover == "Add New...":
                    new_cover_designer = st.text_input("New Cover Designer Name", key=f"cover_new_input_{book_id}")
                    if new_cover_designer: st.session_state[f"cover_by_{book_id}"] = new_cover_designer
                elif selected_cover != "Select Cover Designer":
                    st.session_state[f"cover_by_{book_id}"] = selected_cover

                cover_by = st.session_state[f"cover_by_{book_id}"] if f"cover_by_{book_id}" in st.session_state and st.session_state[f"cover_by_{book_id}"] != "Select Cover Designer" else ""

                col_dt1, col_dt2 = st.columns(2)
                with col_dt1:
                    c_start_val = current_data.get('cover_start')
                    if pd.isna(c_start_val): c_start_val = None
                    cover_start_dt = st.datetime_input("Start", value=c_start_val, key=f"cover_start_dt_{book_id}")
                with col_dt2:
                    c_end_val = current_data.get('cover_end')
                    if pd.isna(c_end_val): c_end_val = None
                    cover_end_dt = st.datetime_input("End", value=c_end_val, key=f"cover_end_dt_{book_id}")

                st.write("") # Spacer
                if st.form_submit_button("💾 Save Cover", width="stretch", type="primary"):
                    with st.spinner("Saving..."):
                        cover_start = cover_start_dt.strftime('%Y-%m-%d %H:%M:%S') if cover_start_dt else None
                        cover_end = cover_end_dt.strftime('%Y-%m-%d %H:%M:%S') if cover_end_dt else None

                        if cover_start and cover_end and cover_start > cover_end:
                            st.error("Start must be before End.")
                        else:
                            updates = {
                                "cover_start": cover_start,
                                "cover_end": cover_end,
                                "cover_by": cover_by if cover_by else None
                            }
                            update_operation_details(book_id, updates)
                            log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "updated cover details", f"Book ID: {book_id}")
                            st.success("Saved!")
                            st.toast("Updated Cover details", icon="✔️")
                            if selected_cover == "Add New..." and new_cover_designer: st.cache_data.clear()

    # ==========================
    # TAB 5: About Book
    # ==========================
    with op_tabs[4]:
        with st.container(border=True):
            with st.form(key=f"about_book_form_{book_id}", border=False):
                about_book = st.text_area(
                    "About the Book",
                    value=current_data.get('about_book', "") if current_data.get('about_book') else "",
                    height=150,
                    key=f"about_book_input_{book_id}"
                )
                
                about_book_200 = st.text_area(
                    "About the Book (150 Words)",
                    value=current_data.get('about_book_200', "") if current_data.get('about_book_200') else "",
                    height=100,
                    key=f"about_book_200_input_{book_id}"
                )
                
                st.write("") # Spacer
                if st.form_submit_button("💾 Save About Details", width="stretch", type="primary"):
                    with st.spinner("Saving..."):
                        updates = {
                            "about_book": about_book.strip() if about_book else None,
                            "about_book_200": about_book_200.strip() if about_book_200 else None
                        }
                        update_operation_details(book_id, updates)
                        log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "updated about book details", f"Book ID: {book_id}")
                        st.success("Saved!")
                        st.toast("Updated About Book details", icon="✔️")

    # ==========================
    # TAB 6: Corrections
    # ==========================
    with op_tabs[5]:
        st.subheader("🔧 Manage Correction Tasks")
        
        # Fetch all corrections for this book
        corr_query = "SELECT * FROM corrections WHERE book_id = :book_id ORDER BY correction_start DESC"
        corrections = conn.query(corr_query, params={"book_id": book_id}, show_spinner=False)
        
        if corrections.empty:
            st.info("No correction records found for this book.")
        else:
            # Get unique names from corrections table too
            corr_names_res = conn.query("SELECT DISTINCT worker FROM corrections WHERE worker IS NOT NULL AND worker != ''", show_spinner=False)
            corr_names = corr_names_res['worker'].tolist() if not corr_names_res.empty else []
            
            # Get all unique names for assignee options
            all_worker_names = sorted(list(set(writing_names + proofreading_names + formatting_names + cover_names + corr_names)))
            worker_options = ["Select Assignee"] + all_worker_names + ["Add New..."]

            for idx, row in corrections.iterrows():
                with st.container(border=True):
                    c_id = row['correction_id']
                    st.markdown(f"**Section:** `{row['section'].capitalize()}` | **Round:** `{row['round_number']}`")

                    with st.form(key=f"edit_corr_form_{c_id}", border=False):
                        c_col1, c_col2 = st.columns(2)
                        
                        with c_col1:
                            current_worker = row['worker']
                            selected_worker = st.selectbox(
                                "Assignee",
                                worker_options,
                                index=worker_options.index(current_worker) if current_worker in worker_options else 0,
                                key=f"worker_corr_{c_id}"
                            )
                            
                            final_worker = current_worker
                            if selected_worker == "Add New...":
                                new_worker = st.text_input("New Name", key=f"new_worker_corr_{c_id}")
                                if new_worker:
                                    final_worker = new_worker
                            elif selected_worker != "Select Assignee":
                                final_worker = selected_worker
                                
                            round_num = st.number_input("Round", min_value=1, value=int(row['round_number']), key=f"round_corr_{c_id}")

                        with c_col2:
                            start_val = row['correction_start']
                            if pd.isna(start_val):
                                start_val = None
                            start_dt = st.datetime_input("Start Time", value=start_val, key=f"start_corr_{c_id}")

                            end_val = row['correction_end']
                            if pd.isna(end_val):
                                end_val = None
                            end_dt = st.datetime_input("End Time", value=end_val, key=f"end_corr_{c_id}")

                        if st.form_submit_button("💾 Update Record", use_container_width=True, type="primary"):
                            updates = {
                                "worker": final_worker,
                                "round_number": round_num,
                                "correction_start": start_dt.strftime('%Y-%m-%d %H:%M:%S') if start_dt else None,
                                "correction_end": end_dt.strftime('%Y-%m-%d %H:%M:%S') if end_dt else None
                            }
                            update_correction_details(c_id, updates)
                            log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "updated correction record", f"Correction ID: {c_id}, Book ID: {book_id}, Worker: {final_worker}")
                            st.success("Updated!")
                            time.sleep(1)
                            st.rerun()

def update_operation_details(book_id, updates):
    #Update operation details in the books table.
    set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
    query = f"UPDATE books SET {set_clause} WHERE book_id = :id"
    params = updates.copy()
    params["id"] = int(book_id)
    with conn.session as session:
        session.execute(text(query), params)
        session.commit()

def update_correction_details(correction_id, updates):
    #Update correction details in the corrections table.
    set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
    query = f"UPDATE corrections SET {set_clause} WHERE correction_id = :id"
    params = updates.copy()
    params["id"] = int(correction_id)
    with conn.session as session:
        session.execute(text(query), params)
        session.commit()


###################################################################################################################################
##################################--------------- Edit Inventory Dialog ----------------------------##################################
###################################################################################################################################


# Function to get detailed print status (missing conditions)
def get_print_status(book_id, conn):
    # Query book conditions including is_publish_only and is_thesis_to_book
    book_query = """
    SELECT 
        writing_complete,
        proofreading_complete,
        formatting_complete,
        cover_page_complete,
        is_publish_only,
        is_thesis_to_book
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
    if book_result['is_publish_only'] != 1 and book_result['is_thesis_to_book'] != 1 and book_result['writing_complete'] != 1:
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


@st.dialog("Edit Printing & Inventory", width='large', on_dismiss='rerun')
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
               google_link, agph_link, google_review, book_mrp, images,
               weight_kg, length_cm, width_cm, height_cm
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
            grid-template-columns: 0.5fr 0.7fr 1fr 1fr 0.8fr 1fr 1fr 0.7fr 1fr 1fr;
            gap: 5px;
            padding: 5px 7px;
            align-items: center;
            font-size: 12px;
            box-sizing: border-box;
            min-width: 800px;
        }

        .print-run-table-header {
            background-color: #f1f3f5;
            font-weight: 600;
            font-size: 11px;
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

        st.write("### Existing Print Edition")

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

        st.checkbox(
            label="Ready to Print?",
            value=is_ready_to_print,
            key=f"ready_to_print_{book_id}",
            help="Automatically checked when all conditions are met.",
            disabled=True
        )

        # Fetch print editions data with batch details
        print_editions_query = f"""
            SELECT 
                pe.print_id, 
                pe.copies_planned, 
                pe.print_color, 
                pe.binding, 
                pe.book_size, 
                pe.edition_number, 
                pe.status,
                pe.color_pages,
                pe.page_type,
                pe.cover_type,
                pe.page_number,
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
        with st.container(border = True):
            if not print_editions_data.empty:
                st.markdown('<div class="print-run-table">', unsafe_allow_html=True)
                st.markdown("""
                    <div class="print-run-table-header">
                        <div>ID</div>
                        <div>Copies</div>
                        <div>Color</div>
                        <div>Binding</div>
                        <div>Size</div>
                        <div>Page Type</div>
                        <div>Cover Type</div>
                        <div>Pages</div>
                        <div>Batch</div>
                        <div>Status</div>
                    </div>
                """, unsafe_allow_html=True)
                
                for idx, row in print_editions_data.iterrows():
                    # Determine status badge style
                    if row['status'] == 'Pending':
                        status_badge = "<span style='background-color: #fff3e0; color: #f57c00; padding: 3px 6px; border-radius: 4px; font-size: 11px;'>Pending</span>"
                    elif row['status'] == 'In Printing':
                        status_badge = "<span style='background-color: #e3f2fd; color: #1976d2; padding: 3px 6px; border-radius: 4px; font-size: 11px;'>In Print</span>"
                    else:  # Received
                        status_badge = "<span style='background-color: #e6ffe6; color: green; padding: 3px 6px; border-radius: 4px; font-size: 11px;'>Received</span>"
                    
                    # Format batch information
                    batch_info = f"{row['batch_name']} (ID: {row['batch_id']})" if row['batch_id'] else "Not Assigned"
                    
                    st.markdown(f"""
                        <div class="print-run-table-row">
                            <div>{row['print_id']}</div>
                            <div>{int(row['copies_planned'])}</div>
                            <div>{row['print_color']}</div>
                            <div>{row['binding']}</div>
                            <div>{row['book_size']}</div>
                            <div>{row['page_type'] or '-'}</div>
                            <div>{row['cover_type'] or '-'}</div>
                            <div>{row['page_number'] or '-'}</div>
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
                    
                    # Only allow editing if status is 'Pending'
                    if edit_row['status'] == 'Pending':
                        with st.container():
                            # Compact layout: Use multiple rows for all fields
                            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
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
                                edit_print_color = st.selectbox(
                                    "Color",
                                    options=["Black & White", "Full Color"],
                                    index=["Black & White", "Full Color"].index(edit_row['print_color']),
                                    key=f"edit_print_color_{book_id}_{selected_print_id}",
                                    label_visibility="visible"
                                )
                            with col3:
                                edit_binding = st.selectbox(
                                    "Binding",
                                    options=["Paperback", "Hardcover"],
                                    index=["Paperback", "Hardcover"].index(edit_row['binding']),
                                    key=f"edit_binding_{book_id}_{selected_print_id}",
                                    label_visibility="visible"
                                )
                            with col4:
                                edit_book_size = st.selectbox(
                                    "Size",
                                    options=["6x9", "8.5x11"],
                                    index=["6x9", "8.5x11"].index(edit_row['book_size']) if edit_row['book_size'] in ["6x9", "8.5x11"] else 0,
                                    key=f"edit_book_size_{book_id}_{selected_print_id}",
                                    label_visibility="visible"
                                )

                            col5, col6, col7 = st.columns([1.2, 1.2, 1])
                            with col5:
                                edit_page_type = st.selectbox(
                                    "Page Type",
                                    options=["White 70 GSM", "Natural Shade 70 GSM", "Cream 70 GSM", "Maplitho 80 GSM", "Art Paper 100 GSM"],
                                    index=["White 70 GSM", "Natural Shade 70 GSM", "Cream 70 GSM", "Maplitho 80 GSM", "Art Paper 100 GSM"].index(edit_row['page_type']) if edit_row['page_type'] in ["White 70 GSM", "Natural Shade 70 GSM", "Cream 70 GSM", "Maplitho 80 GSM", "Art Paper 100 GSM"] else 0,
                                    key=f"edit_page_type_{book_id}_{selected_print_id}"
                                )
                            with col6:
                                edit_cover_type = st.selectbox(
                                    "Cover Type",
                                    options=["300 GSM Glossy", "300 GSM Matte", "250 GSM Glossy", "250 GSM Matte"],
                                    index=["300 GSM Glossy", "300 GSM Matte", "250 GSM Glossy", "250 GSM Matte"].index(edit_row['cover_type']) if edit_row['cover_type'] in ["300 GSM Glossy", "300 GSM Matte", "250 GSM Glossy", "250 GSM Matte"] else 0,
                                    key=f"edit_cover_type_{book_id}_{selected_print_id}"
                                )
                            with col7:
                                edit_page_number = st.number_input(
                                    "Total Pages",
                                    min_value=0,
                                    step=1,
                                    value=int(edit_row['page_number']) if pd.notnull(edit_row['page_number']) else 0,
                                    key=f"edit_page_number_{book_id}_{selected_print_id}"
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

                            save_edit = st.button("💾 Save Edited Print Edition", width="stretch", key=f"save_edit_print_{book_id}_{selected_print_id}")

                            if save_edit:
                                with st.spinner("Saving edited print edition..."):
                                    import time
                                    time.sleep(1)
                                    try:
                                        if edit_num_copies <= 0:
                                            st.error("Copies must be greater than 0.")
                                            return
                                        if edit_print_color == "Full Color" and (edit_color_pages is None or edit_color_pages <= 0):
                                            st.error("Number of Color Pages must be greater than 0 for Full Color.")
                                            return

                                        # Track changes for logging
                                        changes = []
                                        if edit_num_copies != int(edit_row['copies_planned']):
                                            changes.append(f"Copies Planned changed from '{int(edit_row['copies_planned'])}' to '{edit_num_copies}'")
                                        if edit_print_color != edit_row['print_color']:
                                            changes.append(f"Print Color changed from '{edit_row['print_color']}' to '{edit_print_color}'")
                                        if edit_binding != edit_row['binding']:
                                            changes.append(f"Binding changed from '{edit_row['binding']}' to '{edit_binding}'")
                                        if edit_book_size != edit_row['book_size']:
                                            changes.append(f"Book Size changed from '{edit_row['book_size']}' to '{edit_book_size}'")
                                        if edit_page_type != edit_row['page_type']:
                                            changes.append(f"Page Type changed from '{edit_row['page_type']}' to '{edit_page_type}'")
                                        if edit_cover_type != edit_row['cover_type']:
                                            changes.append(f"Cover Type changed from '{edit_row['cover_type']}' to '{edit_cover_type}'")
                                        if edit_page_number != edit_row['page_number']:
                                            changes.append(f"Page Number changed from '{edit_row['page_number']}' to '{edit_page_number}'")
                                        if edit_print_color == "Full Color" and edit_color_pages != (int(edit_row['color_pages']) if pd.notnull(edit_row['color_pages']) else 0):
                                            changes.append(f"Color Pages changed from '{int(edit_row['color_pages']) if pd.notnull(edit_row['color_pages']) else 'None'}' to '{edit_color_pages}'")

                                        with conn.session as session:
                                            session.execute(
                                                text("""
                                                    UPDATE PrintEditions 
                                                    SET copies_planned = :copies_planned,
                                                        print_color = :print_color, 
                                                        binding = :binding, 
                                                        book_size = :book_size,
                                                        page_type = :page_type,
                                                        cover_type = :cover_type,
                                                        page_number = :page_number,
                                                        color_pages = :color_pages
                                                    WHERE print_id = :print_id
                                                """),
                                                {
                                                    "print_id": selected_print_id,
                                                    "copies_planned": edit_num_copies,
                                                    "print_color": edit_print_color,
                                                    "binding": edit_binding,
                                                    "book_size": edit_book_size,
                                                    "page_type": edit_page_type,
                                                    "cover_type": edit_cover_type,
                                                    "page_number": edit_page_number,
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
                                        st.toast("Updated Print Edition", icon="✔️", duration="long")
                                        st.cache_data.clear()
                                    except Exception as e:
                                        st.error(f"❌ Error saving print edition: {str(e)}")
                                        st.toast(f"Error saving print edition: {str(e)}", duration="long")

                            # Delete Option
                            if st.button("🗑️ Delete Print Edition", key=f"delete_print_{book_id}_{selected_print_id}", type="tertiary",width="stretch"):
                                with st.spinner("Deleting print edition..."):
                                    import time
                                    time.sleep(3)
                                    try:
                                        with conn.session as session:
                                            session.execute(
                                                text("DELETE FROM PrintEditions WHERE print_id = :print_id"),
                                                {"print_id": selected_print_id}
                                            )
                                            session.commit()
                                        st.success("Print edition deleted successfully!")
                                        st.toast("Print edition deleted!", icon="🗑️")
                                        log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "deleted print edition", f"Print ID: {selected_print_id}")
                                        st.cache_data.clear()
                                    except Exception as e:
                                        st.error(f"Error deleting print edition: {e}")
                                        with conn.session as session:
                                            session.rollback()
                    
                    else:
                        st.info(f"🔒 **Locked**: Print Edition can't be deleted once it is sent to the printer.")
                        st.write(f"**Copies:** {int(edit_row['copies_planned'])} | **Color:** {edit_row['print_color']} | **Binding:** {edit_row['binding']} | **Size:** {edit_row['book_size']}")


        st.write("### Add New Print Edition")

        # 3. Add New Print Edition Expander (only if ready_to_print is True)
        if is_ready_to_print:
            with st.container(border = True):
                with st.container():
                    # Compact layout: Use multiple rows for all fields
                    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
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
                        print_color = st.selectbox(
                            "Color",
                            options=["Black & White", "Full Color"],
                            key=f"print_color_{book_id}",
                            label_visibility="visible"
                        )
                    with col3:
                        binding = st.selectbox(
                            "Binding",
                            options=["Paperback", "Hardcover"],
                            key=f"binding_{book_id}",
                            label_visibility="visible"
                        )
                    with col4:
                        book_size = st.selectbox(
                            "Size",
                            options=["6x9", "8.5x11"],
                            key=f"book_size_{book_id}",
                            label_visibility="visible"
                        )

                    col5, col6, col7 = st.columns([1.2, 1.2, 1])
                    with col5:
                        page_type = st.selectbox(
                            "Page Type",
                            options=["White 70 GSM", "Natural Shade 70 GSM", "Cream 70 GSM", "Maplitho 80 GSM", "Art Paper 100 GSM"],
                            key=f"page_type_{book_id}"
                        )
                    with col6:
                        cover_type = st.selectbox(
                            "Cover Type",
                            options=["300 GSM Glossy", "300 GSM Matte", "250 GSM Glossy", "250 GSM Matte"],
                            key=f"cover_type_{book_id}"
                        )
                    with col7:
                        page_number = st.number_input(
                            "Total Pages",
                            min_value=0,
                            step=1,
                            value=0,
                            key=f"page_number_{book_id}"
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

                    save_new_print = st.button("💾 Save New Print Edition", width="stretch", key=f"save_print_{book_id}")

                    if save_new_print:
                        with st.spinner("Saving new print edition..."):
                            import time
                            time.sleep(1)
                            try:
                                if new_num_copies > 0:
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
                                                    print_color, binding, book_size, status, color_pages, page_type, cover_type, page_number)
                                                VALUES (:book_id, :edition_number, :copies_planned, 
                                                :print_color, :binding, :book_size, 'Pending', :color_pages, :page_type, :cover_type, :page_number)
                                            """),
                                            {
                                                "book_id": book_id,
                                                "edition_number": edition_number,
                                                "copies_planned": new_num_copies,
                                                "print_color": print_color,
                                                "binding": binding,
                                                "book_size": book_size,
                                                "color_pages": color_pages if print_color == "Full Color" else None,
                                                "page_type": page_type,
                                                "cover_type": cover_type,
                                                "page_number": page_number
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
                                            f"Book ID: {book_id}, Print ID: {print_id}, Edition Number: {edition_number}, Copies Planned: {new_num_copies}, Print Color: {print_color}, Binding: {binding}, Book Size: {book_size}, Color Pages: {color_pages if print_color == 'Full Color' else 'None'}, Page Type: {page_type}, Cover Type: {cover_type}, Pages: {page_number}, Status: Pending"
                                        )
                                    st.success("✔️ Added New Print Edition")
                                    st.toast("Added New Print Edition", icon="✔️", duration="long")
                                    st.cache_data.clear()
                                else:
                                    st.warning("Please enter a number of copies greater than 0.")
                            except Exception as e:
                                st.error(f"❌ Error saving new print edition: {str(e)}")
                                st.toast(f"Error saving new print edition: {str(e)}", icon="❌", duration="long")

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

            # Single form for all inputs
            with st.form(key=f"new_inventory_form_{book_id}", border=False):
                inventory_col1, inventory_col2 = st.columns(2)

                with inventory_col1:
                    # Current Inventory Status
                    st.write("#### Current Inventory Status")
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

                    # Pricing Section
                    st.write("#### Pricing & Storage")
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
                    st.write("#### Sales Tracking")
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

                with inventory_col2:
                    # Dimensions and Weight Section
                    st.write("#### Dimensions & Weight")
                    with st.container(border=True):
                        st.markdown('<div class="inventory-box">', unsafe_allow_html=True)
                        col1, col2 = st.columns(2)
                        with col1:
                            weight_kg = st.number_input(
                                "Weight (kg)", 
                                min_value=0.0,
                                step=0.01,
                                value=float(current_data.get('weight_kg', 0.0)) if current_data.get('weight_kg') is not None else 0.0,
                                key=f"weight_kg_{book_id}"
                            )
                            length_cm = st.number_input(
                                "Length (cm)", 
                                min_value=0.0,
                                step=0.01,
                                value=float(current_data.get('length_cm', 0.0)) if current_data.get('length_cm') is not None else 0.0,
                                key=f"length_cm_{book_id}"
                            )
                        with col2:
                            width_cm = st.number_input(
                                "Width (cm)", 
                                min_value=0.0,
                                step=0.01,
                                value=float(current_data.get('width_cm', 0.0)) if current_data.get('width_cm') is not None else 0.0,
                                key=f"width_cm_{book_id}"
                            )
                            height_cm = st.number_input(
                                "Height (cm)", 
                                min_value=0.0,
                                step=0.01,
                                value=float(current_data.get('height_cm', 0.0)) if current_data.get('height_cm') is not None else 0.0,
                                key=f"height_cm_{book_id}"
                            )
                        st.markdown('</div>', unsafe_allow_html=True)

                    # Links and Reviews Section (Collapsible)
                    st.write("#### Links and Reviews")
                    with st.container(border = True):
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
                            image_link = st.text_input(
                                "Image Link", 
                                value=current_data.get('images', ""), 
                                key=f"image_link_{book_id}"
                            )
                            google_review = st.checkbox(
                                "Google Review", 
                                value=bool(current_data.get('google_review', 0)), 
                                key=f"google_review_{book_id}"
                            )
                        st.markdown('</div>', unsafe_allow_html=True)

                # Submit Button (outside of columns but inside form)
                save_inventory = st.form_submit_button(
                    "💾 Save Inventory", 
                    width="stretch",
                    help="Click to save changes to inventory details."
                )

                # Handle form submission
                if save_inventory:
                    with st.spinner("Saving Inventory details..."):
                        import time
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
                                "images": st.session_state[f"image_link_{book_id}"] if st.session_state[f"image_link_{book_id}"] else None,
                                "google_review": 1 if st.session_state[f"google_review_{book_id}"] else 0,
                                "weight_kg": float(st.session_state[f"weight_kg_{book_id}"]) if st.session_state[f"weight_kg_{book_id}"] else None,
                                "length_cm": float(st.session_state[f"length_cm_{book_id}"]) if st.session_state[f"length_cm_{book_id}"] else None,
                                "width_cm": float(st.session_state[f"width_cm_{book_id}"]) if st.session_state[f"width_cm_{book_id}"] else None,
                                "height_cm": float(st.session_state[f"height_cm_{book_id}"]) if st.session_state[f"height_cm_{book_id}"] else None
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
                            st.toast("Updated Inventory details!", icon="✔️", duration="long")
                            st.cache_data.clear()
                        except Exception as e:
                            st.error(f"❌ Error saving inventory details: {str(e)}")
                            st.toast(f"Error saving inventory details: {str(e)}", icon="❌", duration="long")

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
##################################--------------- Book Details ----------------------------##################################
###################################################################################################################################


@st.dialog("Book Details", width="large")
def show_book_details(book_id, book_row, authors_df, printeditions_df):
    conn = connect_db()
    # Calculate days since enrolled
    enrolled_date = book_row['date'] if pd.notnull(book_row['date']) else None
    if enrolled_date:
        # Convert both to date objects
        today = datetime.now().date()
        enrolled_date = enrolled_date.date() if hasattr(enrolled_date, 'date') else enrolled_date
        days_since_enrolled = (today - enrolled_date).days
    else:
        days_since_enrolled = "N/A"
    
    # Count authors
    author_count = len(authors_df[authors_df['book_id'] == book_id])

    if book_row.get('deliver', 0) == 0:
        deliver_status = "Undelivered"
    else:
        deliver_status = "Delivered"

    # Book Title and Archive Toggle

    st.markdown(f"<div class='book-title'>{book_row['title']} (ID: {book_id})</div>", unsafe_allow_html=True)
    # Book Info in Compact Grid Layout
    st.markdown("<div class='info-grid'>", unsafe_allow_html=True)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"<div class='info-box'><span class='info-label'>Publisher:</span>{book_row['publisher']}</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='info-box'><span class='info-label'>Enrolled:</span>{enrolled_date.strftime('%d %b %Y') if enrolled_date else 'N/A'}</div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='info-box'><span class='info-label'>Since:</span>{days_since_enrolled} days</div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='info-box'><span class='info-label'>Authors:</span>{author_count}</div>", unsafe_allow_html=True)
    with col5:
        st.markdown(f"<div class='info-box'><span class='info-label'>Status:</span>{deliver_status}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ISBN Status Table
    st.markdown("<h4 class='section-title'>ISBN Status</h4>", unsafe_allow_html=True)
    
    # Determine ISBN Status
    apply_isbn = book_row.get('apply_isbn', 0) == 1
    isbn_val = book_row.get('isbn')
    isbn_received = pd.notnull(isbn_val) and str(isbn_val).strip() != ''
    isbn_date_raw = book_row.get('isbn_receive_date')
    
    if isbn_date_raw and pd.notnull(isbn_date_raw):
        try:
            isbn_date = pd.to_datetime(isbn_date_raw).strftime('%d %b %Y')
        except:
            isbn_date = str(isbn_date_raw)
    else:
        isbn_date = "-"

    isbn_table_html = f"""
    <table class='compact-table'>
        <tr><th>Applied</th><th>Received</th><th>Received Date</th><th>ISBN</th></tr>
        <tr>
            <td>{'✅' if apply_isbn else '❌'}</td>
            <td>{'✅' if isbn_received else '❌'}</td>
            <td>{isbn_date}</td>
            <td>{isbn_val if isbn_received else '-'}</td>
        </tr>
    </table>
    """
    st.markdown(isbn_table_html, unsafe_allow_html=True)

    # Author Checklists (Full Sequence)
    st.markdown("<h4 class='section-title'>Author Checklist</h4>", unsafe_allow_html=True)
    book_authors_df = authors_df[authors_df['book_id'] == book_id]
    if not book_authors_df.empty:
        checklist_columns = [
            'welcome_mail_sent', 'author_details_sent', 'photo_recive',
            'cover_agreement_sent', 'digital_book_sent', 'id_proof_recive',
            'agreement_received', 'printing_confirmation'
        ]
        checklist_labels = [
            'Welcome', 'Details', 'Photo',
            'Cover/Agr', 'Digital', 'ID Proof', 'Agreement', 'Print Conf'
        ]
        
        # Build HTML table for full checklist
        table_html = """
        <style>
            .compact-table {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 12px;
                color: #1f2937;
                border-collapse: collapse;
                width: 100%;
            }
            .compact-table th, .compact-table td {
                padding: 8px 10px;
                text-align: center;
                border-bottom: 1px solid #e2e8f0;
            }
            .compact-table th {
                background: #f1f5f9;
                font-weight: 600;
            }
            .compact-table td {
                color: #4b5563;
            }
        </style>
        <table class='compact-table'>
            <tr><th>ID</th><th>Name</th><th>Consultant</th><th>Pos</th><th>Payment</th>
        """
        for label in checklist_labels:
            table_html += f"<th>{label}</th>"
        table_html += "</tr>"
        
        for _, author in book_authors_df.iterrows():
            # Payment status logic
            total = float(author.get('total_amount', 0) or 0)
            paid = float(author.get('amount_paid', 0) or 0)
            if total <= 0:
                p_status = '<span style="color:#666; font-size:10px;">⚪ Pending</span>'
            elif paid >= total:
                p_status = '<span style="color:#166534; font-size:10px;">✅ Paid</span>'
            elif paid > 0:
                p_status = '<span style="color:#854d0e; font-size:10px;">🟠 Partial</span>'
            else:
                p_status = '<span style="color:#b91c1c; font-size:10px;">🔴 Unpaid</span>'

            table_html += f"<tr><td>{author['author_id']}</td><td>{author['name']}</td><td>{author['publishing_consultant']}</td><td>{author['author_position']}</td><td>{p_status}</td>"
            for col, label in zip(checklist_columns, checklist_labels):
                status = '✅' if author[col] else '❌'
                table_html += f"<td>{status}</td>"
            table_html += "</tr>"
        table_html += "</table>"
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("No authors found for this book.")


    # Operations Status
    st.markdown("<h4 class='section-title'>Operations Status</h4>", unsafe_allow_html=True)
    operations = [
        ('Writing', 'writing_start', 'writing_end', 'writing_by'),
        ('Proofreading', 'proofreading_start', 'proofreading_end', 'proofreading_by'),
        ('Formatting', 'formatting_start', 'formatting_end', 'formatting_by'),
        ('Cover Design', 'cover_start', 'cover_end', 'cover_by')
    ]
    # Check if book is publish-only or thesis-to-book
    is_publish_only = book_row.get('is_publish_only', 0) == 1
    is_thesis_to_book = book_row.get('is_thesis_to_book', 0) == 1
    
    table_html = "<table class='compact-table'><tr><th>Operation</th><th>Start</th><th>End</th><th>By</th><th>Status</th></tr>"
    for op_name, start_field, end_field, by_field in operations:
        by_who = book_row.get(by_field)
        by_who = by_who if pd.notnull(by_who) and str(by_who).strip() != '' else '-'
        
        start_val = book_row.get(start_field)
        end_val = book_row.get(end_field)
        
        start_str = start_val.strftime('%d %b %Y') if pd.notnull(start_val) else '-'
        end_str = end_val.strftime('%d %b %Y') if pd.notnull(end_val) else '-'
        
        if op_name == 'Writing' and (is_publish_only or is_thesis_to_book):
            status = '📖 Publish Only' if is_publish_only else '📚 Thesis to Book'
            by_who = '-'
            start_str = '-'
            end_str = '-'
        else:
            if pd.notnull(start_val) and pd.notnull(end_val):
                status = '✅ Done'
            elif pd.notnull(start_val):
                status = '⏳ Active'
            else:
                status = '❌ Pending'
        table_html += f"<tr><td>{op_name}</td><td>{start_str}</td><td>{end_str}</td><td>{by_who}</td><td>{status}</td></tr>"
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)

    # Correction History
    requests_query = """
    SELECT ac.*, COALESCE(a.name, 'Internal Team') AS author_name 
    FROM author_corrections ac
    LEFT JOIN authors a ON ac.author_id = a.author_id
    WHERE ac.book_id = :book_id 
    ORDER BY ac.created_at DESC
    """
    corrections_query = """
    SELECT * FROM corrections 
    WHERE book_id = :book_id 
    ORDER BY correction_start DESC
    """
    
    requests_df = conn.query(requests_query, params={"book_id": str(book_id)}, show_spinner=False)
    corrections_df = conn.query(corrections_query, params={"book_id": str(book_id)}, show_spinner=False)

    if not requests_df.empty or not corrections_df.empty:
        with st.expander("📝 Correction History", expanded=False):
            if not requests_df.empty:
                st.markdown("**Correction Requests**")
                req_table = "<table class='compact-table'><tr><th>Source</th><th>Round</th><th>Date</th><th>Correction</th></tr>"
                for _, req in requests_df.iterrows():
                    date_str = req['created_at'].strftime('%d %b %Y, %I:%M %p') if pd.notnull(req['created_at']) else '-'
                    text_val = req['correction_text'] if pd.notnull(req['correction_text']) and str(req['correction_text']).strip() != '' else "File uploaded"
                    
                    is_internal = pd.isnull(req['author_id'])
                    if is_internal:
                        source_badge = '<span style="background-color:#F3E5F5; color:#8E24AA; padding:2px 6px; border-radius:8px; font-size:10px; font-weight:bold;">Internal Team</span>'
                    else:
                        source_badge = f'<span style="background-color:#E3F2FD; color:#1976D2; padding:2px 6px; border-radius:8px; font-size:10px; font-weight:bold;">{req["author_name"]}</span>'
                    
                    req_table += f"<tr><td>{source_badge}</td><td>{req['round_number']}</td><td>{date_str}</td><td>{text_val}</td></tr>"
                req_table += "</table>"
                st.markdown(req_table, unsafe_allow_html=True)
            
            if not corrections_df.empty:
                st.markdown("<br>**Team Correction Actions**", unsafe_allow_html=True)
                corr_table = "<table class='compact-table'><tr><th>Section</th><th>Round</th><th>Worker</th><th>Start</th><th>End</th></tr>"
                for _, corr in corrections_df.iterrows():
                    start_str = corr['correction_start'].strftime('%d %b %Y, %I:%M %p') if pd.notnull(corr['correction_start']) else '-'
                    end_str = corr['correction_end'].strftime('%d %b %Y, %I:%M %p') if pd.notnull(corr['correction_end']) else '⏳ Active'
                    
                    section_display = corr['section'].capitalize()
                    if corr.get('is_internal') == 1:
                        section_display += ' <span style="background-color:#F3E5F5; color:#8E24AA; padding:1px 4px; border-radius:4px; font-size:9px; font-weight:bold;">Internal Team</span>'
                        
                    corr_table += f"<tr><td>{section_display}</td><td>{corr['round_number']}</td><td>{corr['worker']}</td><td>{start_str}</td><td>{end_str}</td></tr>"
                corr_table += "</table>"
                st.markdown(corr_table, unsafe_allow_html=True)


    st.markdown("<h4 class='section-title'>Print Editions</h4>", unsafe_allow_html=True)
    book_print_details_df = fetch_print_details(book_id, conn)
    
    # Check for basic print editions if detailed ones are missing
    book_printeditions_df = printeditions_df[printeditions_df['book_id'] == book_id]
    
    has_prints = not book_print_details_df.empty or not book_printeditions_df.empty
    
    if has_prints:
        # Show Print Editions Table
        if not book_print_details_df.empty:
            table_html = "<table class='compact-table'><tr><th>Batch ID</th><th>Copies</th><th>Sent Date</th><th>Receive Date</th><th>Status</th></tr>"
            for _, row in book_print_details_df.iterrows():
                sent_date = row['print_sent_date'].strftime('%d %b %Y') if pd.notnull(row['print_sent_date']) else 'N/A'
                receive_date = row['print_receive_date'].strftime('%d %b %Y') if pd.notnull(row['print_receive_date']) else 'N/A'
                batch_id = row['batch_id'] if pd.notnull(row['batch_id']) else 'N/A'
                copies = row['copies_planned'] if pd.notnull(row['copies_planned']) else 'N/A'
                table_html += f"<tr><td>{batch_id}</td><td>{copies}</td><td>{sent_date}</td><td>{receive_date}</td><td>{row['status']}</td></tr>"
            table_html += "</table>"
            st.markdown(table_html, unsafe_allow_html=True)
        elif not book_printeditions_df.empty:
            table_html = "<table class='compact-table'><tr><th>Print ID</th><th>Status</th></tr>"
            for _, row in book_printeditions_df.iterrows():
                table_html += f"<tr><td>{row['print_id']}</td><td>{row['status']}</td></tr>"
            table_html += "</table>"
            st.markdown(table_html, unsafe_allow_html=True)

        # Author Delivery Table (Only if printed)
        st.markdown("<h4 class='section-title'>Author Delivery</h4>", unsafe_allow_html=True)
        if not book_authors_df.empty:
            table_html = "<table class='compact-table'><tr><th>Author</th><th>Status</th><th>Copies</th><th>Date</th></tr>"
            for _, author in book_authors_df.iterrows():
                delivery_date = author.get('delivery_date')
                if pd.notnull(delivery_date):
                    try:
                        d_date = pd.to_datetime(delivery_date).strftime('%d %b %Y')
                    except:
                        d_date = str(delivery_date)
                    status = "✅ Delivered"
                else:
                    d_date = "-"
                    status = "❌ Pending"
                table_html += f"<tr><td>{author['name']}</td><td>{status}</td><td>{author.get('number_of_books', '❌ Pending')}</td><td>{d_date}</td></tr>"
            table_html += "</table>"
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.info("No authors found.")

    else:
        st.info("Book not printed yet.")

    # Additional Details: Links & Inventory (Only if printed)
    if has_prints:
        st.markdown("---")
        col_links, col_inv = st.columns(2)

        with col_links:
            st.markdown("<h4 class='section-title'>Store Links</h4>", unsafe_allow_html=True)
            links_data = [
                ("Amazon", book_row.get('amazon_link'), "https://img.icons8.com/color/48/000000/amazon.png"),
                ("Flipkart", book_row.get('flipkart_link'), "https://img.icons8.com/?size=100&id=UU2im0hihoyi&format=png&color=000000"),
                ("Google Books", book_row.get('google_link'), "https://img.icons8.com/color/48/000000/google-logo.png"),
                ("AGPH Store", book_row.get('agph_link'), "https://img.icons8.com/fluency/48/shopping-bag.png")
            ]
            
            table_html = "<table class='compact-table'><tr><th>Store</th><th>Link</th></tr>"
            for name, link, icon in links_data:
                if link and str(link).strip() and str(link) != 'None':
                    status = f'<a href="{link}" target="_blank"><img src="{icon}" width="24" height="24" title="{name}"></a>'
                else:
                    status = "❌"
                table_html += f"<tr><td>{name}</td><td>{status}</td></tr>"
            table_html += "</table>"
            st.markdown(table_html, unsafe_allow_html=True)

        with col_inv:
            st.markdown("<h4 class='section-title'>Inventory</h4>", unsafe_allow_html=True)
            try:
                # Total Printed
                total_printed = book_print_details_df[book_print_details_df['status'] == 'Received']['copies_planned'].sum() if not book_print_details_df.empty else 0

                # Fetch inventory sales
                inv_res = conn.query(f"SELECT amazon_sales, flipkart_sales, website_sales, direct_sales FROM inventory WHERE book_id = '{book_id}'", show_spinner=False)
                
                if not inv_res.empty:
                    inv_data = inv_res.iloc[0]
                    amazon = int(inv_data['amazon_sales']) if pd.notnull(inv_data['amazon_sales']) else 0
                    flipkart = int(inv_data['flipkart_sales']) if pd.notnull(inv_data['flipkart_sales']) else 0
                    website = int(inv_data['website_sales']) if pd.notnull(inv_data['website_sales']) else 0
                    direct = int(inv_data['direct_sales']) if pd.notnull(inv_data['direct_sales']) else 0
                else:
                    amazon = flipkart = website = direct = 0
                
                total_sales = amazon + flipkart + website + direct

                # Author Copies
                author_copies = book_authors_df['number_of_books'].fillna(0).astype(int).sum() if not book_authors_df.empty else 0
                
                current_inv = int(total_printed - total_sales - author_copies)
                
                # Inventory Table
                inv_table_html = f"""
                <table class='compact-table'>
                    <tr><th>Category</th><th>Count</th></tr>
                    <tr><td>Total Printed</td><td>{total_printed}</td></tr>
                    <tr><td>Amazon Sales</td><td>{amazon}</td></tr>
                    <tr><td>Flipkart Sales</td><td>{flipkart}</td></tr>
                    <tr><td>Website Sales</td><td>{website}</td></tr>
                    <tr><td>Direct Sales</td><td>{direct}</td></tr>
                    <tr><td>Author Copies</td><td>{author_copies}</td></tr>
                    <tr style='font-weight:bold; background-color:#f8f9fa;'><td>Current Stock</td><td>{current_inv}</td></tr>
                </table>
                """
                st.markdown(inv_table_html, unsafe_allow_html=True)
            
            except Exception as e:
                st.error(f"Error: {str(e)}")



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
            
        /* A container to hold the lines and control spacing in the cell */
        .cell-container {
            display: flex;
            flex-direction: column;
            gap: 4px; /* Controls the tight vertical spacing */
            line-height: 1.4;
        }
        /* Style for the top line (book title + badges) */
        .title-line {
            font-weight: 500;
            font-size: 14px;
        }
        /* Style for the bottom line (author names) */
        .authors-line {
            font-size: 11px;
            color: #4b5563; /* Muted text color */
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

    if search_query and search_query.lower() in ["yogesh sharma", "rishabh vyas"]:
        st.balloons()
        st.toast(f"Hellow {user_name}!😄", icon="🎉", duration="long")


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
    # Callback functions
    def update_tags_filter():
        widget_key = f"tags_multiselect_{st.session_state.clear_filters_trigger}"
        if widget_key in st.session_state:
            st.session_state.tags_filter = st.session_state[widget_key]

    def update_subject_filter():
        widget_key = f"subject_pills_{st.session_state.clear_filters_trigger}"
        if widget_key in st.session_state:
            st.session_state.subject_filter = st.session_state[widget_key]

    def update_consultant_filter():
        widget_key = f"consultant_pills_{st.session_state.clear_filters_trigger}"
        if widget_key in st.session_state:
            st.session_state.consultant_filter = st.session_state[widget_key]

    # Popover for filtering
    with st.popover("🔍 Filters", width="stretch"):
        # Extract unique data
        unique_publishers = sorted(books['publisher'].dropna().unique())
        unique_years = sorted(books['date'].dt.year.unique())
        unique_author_types = sorted(books['author_type'].dropna().unique())

        # Fetch unique tags
        with conn.session as s:
            tag_query = text("SELECT tags FROM books WHERE tags IS NOT NULL AND tags != '' AND tags != '[]'")
            all_tags = s.execute(tag_query).fetchall()
            tag_counts = {}
            for row in all_tags:
                try:
                    tags = json.loads(row[0]) if row[0] else []
                    for tag in tags:
                        if tag:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1
                except json.JSONDecodeError:
                    continue
            unique_tags = sorted(tag_counts.keys(), key=lambda x: (-tag_counts[x], x))

        # Fetch unique consultants
        with conn.session as s:
            consultant_query = text("SELECT DISTINCT publishing_consultant FROM book_authors WHERE publishing_consultant IS NOT NULL AND publishing_consultant != ''")
            unique_consultants = sorted([row[0] for row in s.execute(consultant_query).fetchall()])

        # Initialize session state
        for key, default in [
            ('year_filter', None), ('month_filter', None), ('start_date_filter', None),
            ('end_date_filter', None), ('status_filter', None), ('publisher_filter', None),
            ('isbn_filter', None), ('author_type_filter', None), ('multiple_open_positions_filter', None),
            ('publish_only_filter', None), ('thesis_to_book_filter', None), ('tags_filter', []),
            ('subject_filter', None), ('consultant_filter', None), ('clear_filters_trigger', 0),
            ('active_filter_section', None)
        ]:
            if key not in st.session_state:
                st.session_state[key] = default


            
        if st.button("🔄 Reset Filters", key="clear_filters", width="stretch"):
            for key in ['year_filter', 'month_filter', 'start_date_filter', 'end_date_filter',
                        'status_filter', 'publisher_filter', 'isbn_filter', 'author_type_filter',
                        'multiple_open_positions_filter', 'publish_only_filter', 'thesis_to_book_filter',
                        'subject_filter', 'consultant_filter', 'active_filter_section']:
                st.session_state[key] = None
            st.session_state.tags_filter = []
            st.session_state.clear_filters_trigger += 1
            st.rerun()
        st.write("**Filter By:**")

        # Filter category pills
        filter_categories = [
            "Date", "Publisher", "Book Status", "ISBN Status", 
            "Subject", "Tags", "Consultant", "Author Type", "Book Type"
        ]
        
        selected_filter = st.radio(
            "Select a filter category",
            options=filter_categories,
            key=f"filter_category_{st.session_state.clear_filters_trigger}",
            label_visibility="collapsed",
            index = None
        )
        
        st.session_state.active_filter_section = selected_filter


        # Show selected filter section
        if st.session_state.active_filter_section == "Date":
            st.subheader("📅 Date Filters")
            col_y1, col_y2 = st.columns(2)
            with col_y1:
                year_options = [str(year) for year in unique_years]
                selected_year = st.pills(
                    "Year",
                    options=year_options,
                    key=f"year_pills_{st.session_state.clear_filters_trigger}"
                )
                st.session_state.year_filter = int(selected_year) if selected_year else None

            with col_y2:
                if st.session_state.year_filter:
                    year_books = books[books['date'].dt.year == st.session_state.year_filter]
                    unique_months = sorted(year_books['date'].dt.month.unique())
                    month_names = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                                 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
                    month_options = [month_names[month] for month in unique_months]
                    selected_month = st.pills(
                        "Month",
                        options=month_options,
                        key=f"month_pills_{st.session_state.clear_filters_trigger}"
                    )
                    st.session_state.month_filter = next((num for num, name in month_names.items() if name == selected_month), None) if selected_month else None
                else:
                    st.session_state.month_filter = None
                    st.info("Select a year first", icon="ℹ️")

            st.caption("**Or filter by date range:**")
            col_d1, col_d2 = st.columns(2)
            min_date, max_date = books['date'].min().date(), books['date'].max().date()
            with col_d1:
                st.session_state.start_date_filter = st.date_input(
                    "From", value=st.session_state.start_date_filter,
                    min_value=min_date, max_value=max_date,
                    key=f"start_date_{st.session_state.clear_filters_trigger}"
                )
            with col_d2:
                st.session_state.end_date_filter = st.date_input(
                    "To", value=st.session_state.end_date_filter,
                    min_value=min_date, max_value=max_date,
                    key=f"end_date_{st.session_state.clear_filters_trigger}"
                )
            
            if st.session_state.start_date_filter and st.session_state.end_date_filter:
                if st.session_state.start_date_filter > st.session_state.end_date_filter:
                    st.error("Start date must be before end date")

        elif st.session_state.active_filter_section == "Publisher":
            st.subheader("🏢 Publisher")
            selected_publisher = st.pills(
                "Select Publisher",
                options=unique_publishers,
                key=f"publisher_pills_{st.session_state.clear_filters_trigger}",
                label_visibility="collapsed"
            )
            st.session_state.publisher_filter = selected_publisher

        elif st.session_state.active_filter_section == "Book Status":
            st.subheader("📊 Book Status")
            status_options = ["Delivered", "On Going"]
            if user_role == "admin":
                status_options.append("Pending Payment")
            selected_status = st.pills(
                "Select Status",
                options=status_options,
                key=f"status_pills_{st.session_state.clear_filters_trigger}",
                label_visibility="collapsed"
            )
            st.session_state.status_filter = selected_status

        elif st.session_state.active_filter_section == "ISBN Status":
            st.subheader("📖 ISBN Status")
            selected_isbn = st.pills(
                "Select ISBN Status",
                options=["Not Applied", "Not Received"],
                key=f"isbn_pills_{st.session_state.clear_filters_trigger}",
                label_visibility="collapsed"
            )
            st.session_state.isbn_filter = selected_isbn

        elif st.session_state.active_filter_section == "Subject":
            st.subheader("📚 Subject")
            selected_subject = st.pills(
                "Select Subject",
                options=VALID_SUBJECTS,
                on_change=update_subject_filter,
                key=f"subject_pills_{st.session_state.clear_filters_trigger}",
                label_visibility="collapsed"
            )
            st.session_state.subject_filter = selected_subject

        elif st.session_state.active_filter_section == "Tags":
            st.subheader("🏷️ Tags")
            selected_tags = st.multiselect(
                "Select Tags (max 5)",
                options=unique_tags,
                on_change=update_tags_filter,
                default=st.session_state.tags_filter,
                key=f"tags_multiselect_{st.session_state.clear_filters_trigger}",
                max_selections=5,
                placeholder="Search or select up to 5 tags",
                label_visibility="collapsed"
            )
            st.session_state.tags_filter = selected_tags

        elif st.session_state.active_filter_section == "Consultant":
            st.subheader("👤 Consultant")
            selected_consultant = st.pills(
                "Select Consultant",
                options=unique_consultants,
                on_change=update_consultant_filter,
                key=f"consultant_pills_{st.session_state.clear_filters_trigger}",
                label_visibility="collapsed"
            )
            st.session_state.consultant_filter = selected_consultant

        elif st.session_state.active_filter_section == "Author Type":
            st.subheader("✍️ Author Type")
            selected_author_type = st.pills(
                "Select Author Type",
                options=["Single", "Double", "Triple", "Multiple"],
                key=f"author_type_pills_{st.session_state.clear_filters_trigger}",
                label_visibility="collapsed"
            )
            st.session_state.author_type_filter = selected_author_type

            if selected_author_type == "Multiple":
                st.caption("**Filter Multiple Authors:**")
                selected_multiple_open = st.pills(
                    "Multiple Author Status",
                    options=["Open Positions"],
                    key=f"multiple_open_positions_pills_{st.session_state.clear_filters_trigger}",
                    label_visibility="collapsed"
                )
                st.session_state.multiple_open_positions_filter = "Multiple with Open Positions" if selected_multiple_open else None

        elif st.session_state.active_filter_section == "Book Type":
            st.subheader("📕 Book Type")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                selected_publish_only = st.pills(
                    "Publish Only",
                    options=["Publish Only"],
                    key=f"publish_only_pills_{st.session_state.clear_filters_trigger}"
                )
                st.session_state.publish_only_filter = selected_publish_only

            with col_t2:
                selected_thesis_to_book = st.pills(
                    "Thesis to Book",
                    options=["Thesis to Book"],
                    key=f"thesis_to_book_pills_{st.session_state.clear_filters_trigger}"
                )
                st.session_state.thesis_to_book_filter = selected_thesis_to_book

        # Show active filters summary
        applied_filters = []
        if st.session_state.publisher_filter:
            applied_filters.append(f"Publisher: {st.session_state.publisher_filter}")
        if st.session_state.year_filter:
            applied_filters.append(f"Year: {st.session_state.year_filter}")
        if st.session_state.month_filter:
            month_names = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                         7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
            applied_filters.append(f"Month: {month_names.get(st.session_state.month_filter)}")
        if st.session_state.start_date_filter:
            applied_filters.append(f"From: {st.session_state.start_date_filter}")
        if st.session_state.end_date_filter:
            applied_filters.append(f"To: {st.session_state.end_date_filter}")
        if st.session_state.status_filter:
            applied_filters.append(f"Status: {st.session_state.status_filter}")
        if st.session_state.isbn_filter:
            applied_filters.append(f"ISBN: {st.session_state.isbn_filter}")
        if st.session_state.author_type_filter:
            applied_filters.append(f"Author: {st.session_state.author_type_filter}")
        if st.session_state.multiple_open_positions_filter:
            applied_filters.append("Multiple: Open Positions")
        if st.session_state.publish_only_filter:
            applied_filters.append("Publish Only")
        if st.session_state.thesis_to_book_filter:
            applied_filters.append("Thesis to Book")
        if st.session_state.subject_filter:
            applied_filters.append(f"Subject: {st.session_state.subject_filter}")
        if st.session_state.consultant_filter:
            applied_filters.append(f"Consultant: {st.session_state.consultant_filter}")
        if st.session_state.tags_filter:
            tag_display = ', '.join(st.session_state.tags_filter[:2])
            if len(st.session_state.tags_filter) > 2:
                tag_display += f" +{len(st.session_state.tags_filter) - 2}"
            applied_filters.append(f"Tags: {tag_display}")

        if applied_filters:
            st.success(f"**✓ Active ({len(applied_filters)}):** {' • '.join(applied_filters)}")

            # Apply all filters (same logic as before)
            if st.session_state.publisher_filter:
                filtered_books = filtered_books[filtered_books['publisher'] == st.session_state.publisher_filter]

            if st.session_state.publish_only_filter:
                filtered_books = filtered_books[filtered_books['is_publish_only'] == 1]

            if st.session_state.thesis_to_book_filter:
                filtered_books = filtered_books[filtered_books['is_thesis_to_book'] == 1]

            filtered_books = filter_books_by_date(
                filtered_books, None, st.session_state.month_filter,
                st.session_state.year_filter, st.session_state.start_date_filter,
                st.session_state.end_date_filter
            )

            if st.session_state.isbn_filter:
                if st.session_state.isbn_filter == "Not Applied":
                    filtered_books = filtered_books[filtered_books['isbn'].isna() & (filtered_books['apply_isbn'] == 0)]
                elif st.session_state.isbn_filter == "Not Received":
                    filtered_books = filtered_books[filtered_books['isbn'].isna() & (filtered_books['apply_isbn'] == 1)]

            if st.session_state.status_filter:
                if st.session_state.status_filter == "Pending Payment":
                    pending_payment_query = """
                        SELECT DISTINCT ba.book_id FROM book_authors ba
                        WHERE ba.total_amount > 0 AND 
                        COALESCE((SELECT SUM(amount) FROM author_payments WHERE book_author_id = ba.id AND status = 'Approved'), 0) < ba.total_amount
                    """
                    pending_book_ids = conn.query(pending_payment_query, show_spinner=False)
                    filtered_books = filtered_books[filtered_books['book_id'].isin(pending_book_ids['book_id'].tolist())]
                else:
                    status_mapping = {"Delivered": 1, "On Going": 0}
                    filtered_books = filtered_books[filtered_books['deliver'] == status_mapping[st.session_state.status_filter]]

            if st.session_state.author_type_filter:
                filtered_books = filtered_books[filtered_books['author_type'] == st.session_state.author_type_filter]

            if st.session_state.multiple_open_positions_filter:
                filtered_books = filtered_books[
                    (filtered_books['author_type'] == 'Multiple') &
                    (filtered_books['book_id'].map(author_count_dict) < 4)
                ]

            if st.session_state.tags_filter:
                filtered_books = filtered_books[
                    filtered_books['tags'].apply(
                        lambda x: all(tag in json.loads(x) if x and isinstance(x, str) else [] for tag in st.session_state.tags_filter)
                    )
                ]

            if st.session_state.subject_filter:
                filtered_books = filtered_books[filtered_books['subject'] == st.session_state.subject_filter]

            if st.session_state.consultant_filter:
                consultant_query = "SELECT DISTINCT book_id FROM book_authors WHERE publishing_consultant = :consultant"
                consultant_book_ids = conn.query(consultant_query, params={"consultant": st.session_state.consultant_filter}, show_spinner=False)
                filtered_books = filtered_books[filtered_books['book_id'].isin(consultant_book_ids['book_id'].tolist())]


with srcol4:
    # Add Book button
    if is_button_allowed("add_book_dialog"):
        if st.button(":material/add: Book", type="secondary", help="Add New Book", width="stretch"):
            add_book_dialog(conn)
    else:
        st.button(":material/add: Book", type="secondary", help="Add New Book (Not Authorized)", width="stretch", disabled=True)

with srcol5:
        # Initialize session state for tracking logged click IDs
        if "logged_click_ids" not in st.session_state:
            st.session_state.logged_click_ids = set()

        with st.popover("More", width="stretch", help="More Options"):
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
                            width="content"
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

# Author type-specific styles
AUTHOR_TYPE_STYLES = {
    "Single": {"color": "#15803d", "background": "#e5fff3"},  # Teal with light teal background
    "Double": {"color": "#15803d", "background": "#e5fff3"},  # Purple with light purple background
    "Triple": {"color": "#15803d", "background": "#e5fff3"},  # Amber with light amber background
    "Multiple": {"color": "#15803d", "background": "#e5fff3"}  # Red with light red background
}

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

def get_thesis_to_book_badge(is_thesis_to_book):
    """Generate publish-only badge if applicable."""
    if is_thesis_to_book == 1:
        return generate_badge("Thesis To Book", "#c2410c", "#fff7ed")
    return ""

def get_publisher_badge(publisher):
    """Generate publisher badge if applicable."""
    if publisher in PUBLISHER_STYLES:
        style = PUBLISHER_STYLES[publisher]
        return generate_badge(publisher, style["color"], style["background"])
    return ""


def get_author_checklist_pill(book_id, row, authors_grouped):

    # --- Styles for a more compact look ---

    container_style = (
        "display: flex; "
        "flex-wrap: wrap; "
        "gap: 2px; "
        "padding-top: 1px;"
    )

    # Base style with smaller font and padding
    base_pill_style = (
        "padding: 1px 2px; "          # Reduced padding for a smaller pill
        "border-radius: 12px; "
        "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; "
        "font-size: 10px; "           # Smaller font size
        "font-weight: 500; "
        "display: inline-flex; "
        "align-items: center; "
        "gap: 1px; "

    )

    # Style for 'completed' (green with checkmark)
    complete_style = (
        f"{base_pill_style} "
        "background-color: #ffffff; "
        "color: #166534; "
    )
    
    # NEW: Style for 'pending' (red with cross mark)
    pending_style = (
        f"{base_pill_style} "
        "background-color: #ffffff; "  # Soft red/pink background
        "color: #b91c1c; "             # Darker red text
    )

    # --- Checklist Logic ---

    checklist_sequence = [
        ("welcome_mail_sent", "Welcome"),
        ("cover_agreement_sent", "Cover/Agr"),
        ("author_details_sent", "Details"),
        ("photo_recive", "Photo"),
        ("id_proof_recive", "ID Proof"),
        ("agreement_received", "Agreement"),
        ("digital_book_sent", "Digital"),
        ("printing_confirmation", "Print")
    ]

    book_authors = authors_grouped.get(book_id, pd.DataFrame())
    if book_authors.empty:
        return (
            f"<div style='{container_style}'>"
            f"<span style='font-size: 10px; color: #6b7280; font-style: italic;'>No authors</span>"
            f"</div>"
        )

    html_pills = []
    for field, label in checklist_sequence:
        all_complete = all(author.get(field) for _, author in book_authors.iterrows())

        if all_complete:
            # Checkmark icon ✔ for completed items
            pill_content = f"<span>&#10004;</span><span>{label}</span>"
            style = complete_style
            title = f"{label}: Completed"
        else:
            # NEW: Cross mark icon ✗ for pending items
            pill_content = f"<span>&#10007;</span><span>{label}</span>"
            style = pending_style
            title = f"{label}: Pending"
        
        html_pills.append(f'<div style="{style}" title="{title}">{pill_content}</div>')

    return f"<div style=\"{container_style}\">{''.join(html_pills)}</div>"


#actual icons
price_icon = ":material/currency_rupee:"
isbn_icon = ":material/edit_document:"
author_icon = ":material/manage_accounts:"
ops_icon = ":material/manufacturing:"
delivery_icon = ":material/local_shipping:"
details_icon = ":material/info:"


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
book_idss = paginated_books['book_id'].tolist()
authors_data = fetch_all_book_authors(book_idss, conn)
printeditions_data = fetch_all_printeditions(book_idss, conn)

# Display the table
column_size = [0.5, 3.8, 1, 0.95, 1.3, 2.3]
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
        corrections_df = fetch_active_corrections(book_ids, conn)
        author_names_dict = fetch_all_author_names(book_ids, conn)

        # Preprocess DataFrames to group by book_id
        authors_grouped = {book_id: group for book_id, group in authors_df.groupby('book_id')}
        printeditions_grouped = {book_id: group for book_id, group in printeditions_df.groupby('book_id')}
        corrections_grouped = {book_id: group for book_id, group in corrections_df.groupby('book_id')}

        grouped_books = paginated_books.groupby(pd.Grouper(key='date', freq='ME'))
        reversed_grouped_books = reversed(list(grouped_books))

        for month, monthly_books in reversed_grouped_books:
            monthly_books = monthly_books.sort_values(by='date', ascending=False)
            num_books = len(monthly_books)
            st.markdown(f'<div class="month-header">{month.strftime("%B %Y")} ({num_books} books)</div>', unsafe_allow_html=True)

            for _, row in monthly_books.iterrows():
                st.markdown('<div class="data-row">', unsafe_allow_html=True)
                authors_display = author_names_dict.get(row['book_id'], "No authors")
                col1, col2, col3, col4, col5, col6 = st.columns(column_size, vertical_alignment="center")

                with col1:
                    st.write(row['book_id'])
                with col2:
                    # --- Get all the data for the cell ---
                    author_count = author_count_dict.get(row['book_id'], 0)
                    author_badge = get_author_badge(row.get('author_type', 'Multiple'), author_count)
                    publish_badge = get_publish_badge(row.get('is_publish_only', 0))
                    thesis_to_book_badge = get_thesis_to_book_badge(row.get('is_thesis_to_book', 0))
                    publisher_badge = get_publisher_badge(row.get('publisher', ''))
                    checklist_display = get_author_checklist_pill(row['book_id'], row, authors_grouped)
                    authors_display = author_names_dict.get(row['book_id'], "No authors found")

                    # --- The HTML for each row ---
                    html_content = f"""
                    <div class="cell-container">
                        <div class="title-line">
                            {row['title']} {publish_badge}{thesis_to_book_badge}{publisher_badge}{author_badge}
                        </div>
                        <div class="authors-line">
                            {authors_display}
                        </div>
                        <div>{checklist_display}</div>
                    </div>
                    """

                    st.markdown(html_content, unsafe_allow_html=True)
                with col3:
                    st.write(row['date'].strftime('%Y-%m-%d'))
                with col4:
                    st.markdown(get_isbn_display(row["book_id"], row["isbn"], row["apply_isbn"]), unsafe_allow_html=True)
                with col5:
                    st.markdown(get_status_pill(row["book_id"], row, authors_grouped, printeditions_grouped, corrections_grouped), unsafe_allow_html=True)
                with col6:
                    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5, btn_col6 = st.columns([1, 1, 1, 1, 1, 1], vertical_alignment="bottom")
                    with btn_col1:
                        # ISBN button (manage_isbn_dialog)
                        if is_button_allowed("manage_isbn_dialog"):
                            if st.button(isbn_icon, key=f"isbn_{row['book_id']}", help="Edit Book Details"):
                                manage_isbn_dialog(conn, row['book_id'], row['apply_isbn'], row['isbn'])
                        else:
                            st.button(isbn_icon, key=f"isbn_{row['book_id']}", help="Not Authorised", disabled=True)
                    with btn_col2:
                        # Price button (manage_price_dialog)
                        publisher = row.get('publisher', '')
                        if publisher not in ["AG Kids", "NEET/JEE"] or st.session_state.get("role") == "admin":
                            if is_button_allowed("manage_price_dialog"):
                                if st.button(price_icon, key=f"price_btn_{row['book_id']}", help="Edit Payments"):
                                    manage_price_dialog(row['book_id'],conn)
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
                    with btn_col6:
                         if is_button_allowed("details"):
                            if st.button(details_icon, key=f"details_{row['book_id']}", help="View Details"):
                                show_book_details(row['book_id'], row, authors_data, printeditions_data)
                         else:
                            st.button(details_icon, key=f"details_{row['book_id']}", help="Not Authorised", disabled=True)

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
st.caption(f"**Total Page Load Time:** {total_time:.2f} seconds")
st.caption(f"**Table Rendering Time:** {render_time:.2f} seconds")

