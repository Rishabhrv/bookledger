import streamlit as st
from constants import log_activity
from constants import connect_db
import re
import uuid
import pandas as pd
from urllib.parse import urlencode, quote
from constants import get_page_url
from urllib.parse import urlencode
from sqlalchemy import text
from auth import validate_token
from datetime import datetime


st.set_page_config(layout="wide", page_title="AGPH Books", initial_sidebar_state="collapsed")

logo = "logo/logo_black.png"
fevicon = "logo/favicon_black.ico"
small_logo = "logo/favicon_white.ico"

st.logo(logo,
size = "large",
icon_image = small_logo
)

validate_token()

user_role = st.session_state.get("role", None)
user_id = st.session_state.get("user_id",0)
user_app = st.session_state.get("app", None)
user_name = st.session_state.get("username", "Unknown")
user_access = st.session_state.get("access", None)[0]
token = st.session_state.token


if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Access control check
if not (user_role == 'user' and user_access == 'Full Access' and user_app == 'sales'):
    st.error("⚠️ Access Denied: You don't have permission to access this page.")
    st.stop()


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


conn = connect_db()


if "activity_logged" not in st.session_state:
    log_activity(
                conn,
                st.session_state.user_id,
                st.session_state.username,
                st.session_state.session_id,
                "logged in",
                "App: Sales"
            )
    st.session_state.activity_logged = True


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
            
        .month-header {
            font-size: 16px;
            font-weight: bold;
            color: #333;
            padding: 3px 10px;
            border-left: 3px solid #f54242; /* Blue side border */
            display: inline-block;
        }
        .popover-button {
            background-color: #007bff;
            color: white;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 12px;
        }
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
        .cell-container {
            display: flex;
            flex-direction: column;
            gap: 4px;
            line-height: 1.4;
        }
        .title-line {
            font-weight: 500;
            font-size: 14px;
        }
        .authors-line {
            font-size: 11px;
            color: #4b5563;
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
        .sidebar .sidebar-content {
            background-color: #f8f9fa;
        }
        .compact-table { font-size: 12px; border-collapse: collapse; width: 100%; }
        .compact-table th, .compact-table td { border: 1px solid #e0e0e0; padding: 5px 7px; text-align: left; }
        .compact-table th { background-color: #dfe6ed; font-weight: 600; color: #2c3e50; }
        .compact-table tr:nth-child(even) { background-color: #f8fafc; }
        .section-title { margin-top: 10px; margin-bottom: 5px; font-size: 16px; color: #2c3e50; font-weight: 600; }
                    
        .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; font-size: 12px; }
        .info-box { padding: 5px; border-radius: 6px; background-color: #f1f5f9; }
        .info-label { font-weight: 600; color: #2c3e50; display: inline-block; margin-right: 4px; }
        .book-title { font-size: 18px; color: #2c3e50; font-weight: 700; margin-bottom: 8px; }
            
        .status-badge-red {
        background-color: #FFEBEE;
        color: #F44336;
        padding: 5px 17px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
        font-size: 20px;
        margin-bottom: 15px;
    }
    .badge-count {
        background-color: rgba(255, 255, 255, 0.9);
        color: inherit;
        padding: 2px 6px;
        border-radius: 10px;
        margin-left: 6px;
        font-size: 14px;
        font-weight: normal;
    }
    .table-header {
        font-weight: bold;
        font-size: 14px;
        color: #333;
        padding: 8px;
        border-bottom: 2px solid #ddd;
        margin-bottom: 10px;
    }
    .table-row {
        padding: 7px 5px;
        background-color: #ffffff;
        font-size: 13px; 
        margin-bottom: 5px;
        margin-top: 5px;    
    }
    .table-row:hover {
        background-color: #f1f1f1; 
    }
    .container-spacing {
        margin-bottom: 30px;
    }
    .pill-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
        text-align: center;
        min-width: 80px;
    }
    .publisher-Penguin { background-color: #fff3e0; color: #ef6c00; }
    .publisher-HarperCollins { background-color: #e6f3ff; color: #0052cc; }
    .publisher-Macmillan { background-color: #f0e6ff; color: #6200ea; }
    .publisher-RandomHouse { background-color: #e6ffe6; color: #2e7d32; }
    .publisher-default { background-color: #f5f5f5; color: #616161; }
                
    .date-pill {
        display: inline-block;
        padding: 2px 5px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 500;
        background-color: #e0f7fa;
        color: #006064;
        margin-left: 3px;
    }
    .author-type-double { background-color: #e6f3ff; color: #0052cc; }
    .author-type-triple { background-color: #f0e6ff; color: #6200ea; }
    .author-type-multiple { background-color: #f5f5f5; color:#616161; }
    .position-occupied { background-color: #e6ffe6; color: #2e7d32; }
    .position-vacant { background-color: #ffe6e6; color: #d32f2f; }
    .position-na { background-color: #f5f5f5; color: #616161; }
            
    /* override Streamlit’s reset */
    .stMarkdown .publisher-pill {
        border-radius: 12px !important;
        padding: 3px 8px !important;
        display: inline-flex !important;
        align-items: center !important;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def fetch_all_book_authors(book_ids, _conn):
    if not book_ids:  # Handle empty book_ids
        return pd.DataFrame(columns=[
            'id', 'book_id', 'author_id', 'name', 'email', 'phone', 'author_position',
            'welcome_mail_sent', 'corresponding_agent', 'publishing_consultant',
            'photo_recive', 'id_proof_recive', 'author_details_sent',
            'cover_agreement_sent', 'agreement_received', 'digital_book_sent',
            'printing_confirmation', 'delivery_address', 'delivery_charge',
            'number_of_books', 'total_amount', 'emi1', 'emi2', 'emi3',
            'emi1_date', 'emi2_date', 'emi3_date', 'delivery_date',
            'tracking_id', 'delivery_vendor', 'emi1_payment_mode',
            'emi2_payment_mode', 'emi3_payment_mode', 'emi1_transaction_id',
            'emi2_transaction_id', 'emi3_transaction_id'
        ])
    query = """
    SELECT ba.id, ba.book_id, ba.author_id, a.name, a.email, a.phone, 
           ba.author_position, ba.welcome_mail_sent, ba.corresponding_agent, 
           ba.publishing_consultant, ba.photo_recive, ba.id_proof_recive, 
           ba.author_details_sent, ba.cover_agreement_sent, ba.agreement_received, 
           ba.digital_book_sent, ba.printing_confirmation, ba.delivery_address, 
           ba.delivery_charge, ba.number_of_books, ba.total_amount, ba.emi1, 
           ba.emi2, ba.emi3, ba.emi1_date, ba.emi2_date, ba.emi3_date,
           ba.delivery_date, ba.tracking_id, ba.delivery_vendor,
           ba.emi1_payment_mode, ba.emi2_payment_mode, ba.emi3_payment_mode,
           ba.emi1_transaction_id, ba.emi2_transaction_id, ba.emi3_transaction_id
    FROM book_authors ba
    JOIN authors a ON ba.author_id = a.author_id
    WHERE ba.book_id IN :book_ids
    """
    try:
        return _conn.query(query, params={'book_ids': tuple(book_ids)}, show_spinner=False)
    except Exception as e:
        st.error(f"Error fetching book authors: {e}")
        return pd.DataFrame(columns=[
            'id', 'book_id', 'author_id', 'name', 'email', 'phone', 'author_position',
            'welcome_mail_sent', 'corresponding_agent', 'publishing_consultant',
            'photo_recive', 'id_proof_recive', 'author_details_sent',
            'cover_agreement_sent', 'agreement_received', 'digital_book_sent',
            'printing_confirmation', 'delivery_address', 'delivery_charge',
            'number_of_books', 'total_amount', 'emi1', 'emi2', 'emi3',
            'emi1_date', 'emi2_date', 'emi3_date', 'delivery_date',
            'tracking_id', 'delivery_vendor', 'emi1_payment_mode',
            'emi2_payment_mode', 'emi3_payment_mode', 'emi1_transaction_id',
            'emi2_transaction_id', 'emi3_transaction_id'
        ])


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


# Author type-specific styles
AUTHOR_TYPE_STYLES = {
    "Single": {"color": "#15803d", "background": "#e5fff3"},  # Teal with light teal background
    "Double": {"color": "#15803d", "background": "#e5fff3"},  # Purple with light purple background
    "Triple": {"color": "#15803d", "background": "#e5fff3"},  # Amber with light amber background
    "Multiple": {"color": "#15803d", "background": "#e5fff3"}  # Red with light red background
}

PUBLISHER_STYLES = {
    "Cipher": {"color": "#ffffff", "background": "#9178e3"},
    "AG Volumes": {"color": "#ffffff", "background": "#2b1a70"},
    "AG Classics": {"color": "#ffffff", "background": "#d81b60"},
    "AG Kids": {"color": "#ffffff", "background": "#f57c00"},
    "NEET/JEE": {"color": "#ffffff", "background": "#0288d1"}
}

# Updated base badge style
BASE_BADGE_STYLE = {
    "display": "inline-block",
    "padding": "4px 12px",
    "border-radius": "12px",
    "font-size": "11px",
    "font-weight": "500",
    "text-align": "center",
    "min-width": "80px",
}

def generate_badge(content, color, background, extra_styles=None): 
    styles = {**BASE_BADGE_STYLE, "color": color, "background-color": background}
    if extra_styles:
        styles.update(extra_styles)
    style_str = "; ".join(f"{k}: {v}" for k, v in styles.items())
    return f'<span style="{style_str}">{content}</span>'


def get_payment_status(row):
    # Ensure numeric conversion to avoid string comparison errors
    total = float(row.get('total_amount', 0) or 0)
    emi1 = float(row.get('emi1', 0) or 0)
    emi2 = float(row.get('emi2', 0) or 0)
    emi3 = float(row.get('emi3', 0) or 0)
    amount_paid = emi1 + emi2 + emi3

    # Logic for determining status
    if total <= 0:
        return generate_badge("Pending Payment", "#b91c1c", "#fee2e2")
    elif amount_paid >= total:
        return generate_badge("Paid", "#166534", "#e5fff3")
    elif 0 < amount_paid < total:
        return generate_badge("Partial", "#854d0e", "#fff7ed")
    else:
        return generate_badge("Pending Payment", "#854d0e", "#fee2e2")


def fetch_book_details(book_id, conn):
    query = f"""
    SELECT title, date, apply_isbn, isbn, is_single_author, isbn_receive_date , tags, subject, num_copies, 
    syllabus_path, is_thesis_to_book, print_status,is_publish_only, publisher, price
    FROM books
    WHERE book_id = '{book_id}'
    """
    return conn.query(query,show_spinner = False)

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

@st.dialog("Manage Book Price and Author Payments", width="large", on_dismiss="rerun")
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
            emi1 = int(row.get('emi1', 0) or 0)
            emi2 = int(row.get('emi2', 0) or 0)
            emi3 = int(row.get('emi3', 0) or 0)
            amount_paid = emi1 + emi2 + emi3
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
                        payment_modes = ["Cash", "UPI", "Bank Deposit"]
                        
                        # Determine visibility for progressive EMI display
                        show_emi2 = emi1 > 0
                        show_emi3 = emi1 > 0 and emi2 > 0

                        # EMI 1 (always shown)
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
                        emi1_txn_id = ""
                        if emi1_mode in ["UPI", "Bank Deposit"]:
                            emi1_txn_id = st.text_input(
                                "Transaction ID",
                                value=emi1_transaction_id,
                                key=f"emi1_txn_{row['id']}",
                                placeholder="Enter Transaction ID"
                            )

                        # EMI 2 (shown only if EMI 1 is saved)
                        if show_emi2:
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
                            emi2_txn_id = ""
                            if emi2_mode in ["UPI", "Bank Deposit"]:
                                emi2_txn_id = st.text_input(
                                    "Transaction ID",
                                    value=emi2_transaction_id,
                                    key=f"emi2_txn_{row['id']}",
                                    placeholder="Enter Transaction ID"
                                )
                        else:
                            emi2_str = str(emi2) if emi2 > 0 else ""
                            emi2_date_new = pd.to_datetime(emi2_date) if emi2_date else None
                            emi2_mode = emi2_payment_mode
                            emi2_txn_id = emi2_transaction_id

                        # EMI 3 (shown only if EMI 1 and 2 are saved)
                        if show_emi3:
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
                            emi3_txn_id = ""
                            if emi3_mode in ["UPI", "Bank Deposit"]:
                                emi3_txn_id = st.text_input(
                                    "Transaction ID",
                                    value=emi3_transaction_id,
                                    key=f"emi3_txn_{row['id']}",
                                    placeholder="Enter Transaction ID"
                                )
                        else:
                            emi3_str = str(emi3) if emi3 > 0 else ""
                            emi3_date_new = pd.to_datetime(emi3_date) if emi3_date else None
                            emi3_mode = emi3_payment_mode
                            emi3_txn_id = emi3_transaction_id

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
                                import time
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
                                    st.toast(f"Payment updated for {row['name']}", icon="✔️", duration="long")
                                    st.cache_data.clear()

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

@st.dialog("Book Details", width="large")
def show_book_details(book_id, book_row, authors_df, printeditions_df):
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

    # Book Title and Archive Toggle

    st.markdown(f"<div class='book-title'>{book_row['title']} (ID: {book_id})</div>", unsafe_allow_html=True)
    # Book Info in Compact Grid Layout
    st.markdown("<div class='info-grid'>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"<div class='info-box'><span class='info-label'>Publisher:</span>{book_row['publisher']}</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='info-box'><span class='info-label'>Enrolled:</span>{enrolled_date.strftime('%d %b %Y') if enrolled_date else 'N/A'}</div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='info-box'><span class='info-label'>Since:</span>{days_since_enrolled} days</div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='info-box'><span class='info-label'>Authors:</span>{author_count}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Author Checklists (Full Sequence)
    st.markdown("<h4 class='section-title'>Author Checklist</h4>", unsafe_allow_html=True)
    book_authors_df = authors_df[authors_df['book_id'] == book_id]
    if not book_authors_df.empty:
        checklist_columns = [
            'welcome_mail_sent', 'author_details_sent', 'photo_recive',
            'apply_isbn_not_applied', 'isbn_not_received',
            'cover_agreement_sent', 'digital_book_sent', 'id_proof_recive',
            'agreement_received', 'printing_confirmation'
        ]
        checklist_labels = [
            'Welcome', 'Details', 'Photo', 'ISBN Apply', 'ISBN Recv',
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
            <tr><th>ID</th><th>Name</th><th>Consultant</th><th>Pos</th>
        """
        for label in checklist_labels:
            table_html += f"<th>{label}</th>"
        table_html += "</tr>"
        
        for _, author in book_authors_df.iterrows():
            table_html += f"<tr><td>{author['author_id']}</td><td>{author['name']}</td><td>{author['publishing_consultant']}</td><td>{author['author_position']}</td>"
            for col, label in zip(checklist_columns, checklist_labels):
                if col in ['apply_isbn_not_applied', 'isbn_not_received']:
                    # Handle book-level ISBN fields
                    if col == 'apply_isbn_not_applied':
                        status = '✅' if book_row.get('apply_isbn', 0) == 1 else '❌'
                    else:  # isbn_not_received
                        status = '✅' if pd.notnull(book_row.get('isbn')) and book_row.get('apply_isbn', 0) == 1 else '❌'
                else:
                    # Handle author-level fields
                    status = '✅' if author[col] else '❌'
                table_html += f"<td>{status}</td>"
            table_html += "</tr>"
        table_html += "</table>"
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("No authors found for this book.")

    # Operations and Print Editions in two columns
    col_ops, col_print = st.columns(2)

    # Operations Status
    with col_ops:
        st.markdown("<h4 class='section-title'>Operations Status</h4>", unsafe_allow_html=True)
        operations = [
            ('Writing', 'writing_start', 'writing_end'),
            ('Proofreading', 'proofreading_start', 'proofreading_end'),
            ('Formatting', 'formatting_start', 'formatting_end'),
            ('Cover Design', 'cover_start', 'cover_end')
        ]
        # Check if book is publish-only or thesis-to-book
        is_publish_only = book_row.get('is_publish_only', 0) == 1
        is_thesis_to_book = book_row.get('is_thesis_to_book', 0) == 1
        
        table_html = "<table class='compact-table'><tr><th>Operation</th><th>Status</th></tr>"
        for op_name, start_field, end_field in operations:
            if op_name == 'Writing' and (is_publish_only or is_thesis_to_book):
                status = '📖 Publish Only' if is_publish_only else '📚 Thesis to Book'
            else:
                start = book_row[start_field]
                end = book_row[end_field]
                if pd.notnull(start) and pd.notnull(end):
                    status = '✅ Done'
                elif pd.notnull(start):
                    status = '⏳ Active'
                else:
                    status = '❌ Pending'
            table_html += f"<tr><td>{op_name}</td><td>{status}</td></tr>"
        table_html += "</table>"
        st.markdown(table_html, unsafe_allow_html=True)

    # Print Editions
    with col_print:
        st.markdown("<h4 class='section-title'>Print Editions</h4>", unsafe_allow_html=True)
        conn = connect_db()
        book_print_details_df = fetch_print_details(book_id, conn)
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
        else:
            book_printeditions_df = printeditions_df[printeditions_df['book_id'] == book_id]
            if not book_printeditions_df.empty:
                table_html = "<table class='compact-table'><tr><th>Print ID</th><th>Status</th></tr>"
                for _, row in book_printeditions_df.iterrows():
                    table_html += f"<tr><td>{row['print_id']}</td><td>{row['status']}</td></tr>"
                table_html += "</table>"
                st.markdown(table_html, unsafe_allow_html=True)
            else:
                st.info("No print editions found.")

# Function to update book_authors table
def update_book_authors(id, updates, conn):
    set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
    query = f"UPDATE book_authors SET {set_clause} WHERE id = :id"
    params = updates.copy()
    params["id"] = int(id)
    with conn.session as session:
        session.execute(text(query), params)
        session.commit()

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

# Filter functions
def filter_books(df, query):
    if not query or not query.strip():
        return df
    query = query.strip().lower()
    
    if query.startswith('@'):
        author_query = query[1:]
        author_book_ids_query = """
            SELECT DISTINCT ba.book_id
            FROM book_authors ba
            JOIN authors a ON ba.author_id = a.author_id
            WHERE LOWER(a.name) LIKE :author_query
        """
        author_book_ids = conn.query(
            author_book_ids_query,
            params={"author_query": f"%{author_query}%"},
            show_spinner=False
        )
        matching_book_ids = author_book_ids['book_id'].tolist()
        return df[df['book_id'].isin(matching_book_ids)]
    
    elif query.startswith('#'):
        phone_query = query[1:]
        if re.match(r'^[\d\s-]{7,15}$', phone_query):
            phone_book_ids_query = """
                SELECT DISTINCT ba.book_id
                FROM book_authors ba
                JOIN authors a ON ba.author_id = a.author_id
                WHERE LOWER(a.phone) LIKE :phone_query
            """
            phone_book_ids = conn.query(
                phone_book_ids_query,
                params={"phone_query": f"%{phone_query}%"},
                show_spinner=False
            )
            matching_book_ids = phone_book_ids['book_id'].tolist()
            return df[df['book_id'].isin(matching_book_ids)]
        return df[df['book_id'].isna()]
    
    elif query.startswith('!'):
        email_query = query[1:]
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email_query):
            email_book_ids_query = """
                SELECT DISTINCT ba.book_id
                FROM book_authors ba
                JOIN authors a ON ba.author_id = a.author_id
                WHERE LOWER(a.email) LIKE :email_query
            """
            email_book_ids = conn.query(
                email_book_ids_query,
                params={"email_query": f"%{email_query}%"},
                show_spinner=False
            )
            matching_book_ids = email_book_ids['book_id'].tolist()
            return df[df['book_id'].isin(matching_book_ids)]
        return df[df['book_id'].isna()]
    
    elif query.isdigit():
        if 1 <= len(query) <= 4:
            return df[df['book_id'].astype(str) == query]
    
    elif re.match(r'^\d{3}-\d{2}-\d{5,7}-\d{1,2}-\d$', query):
        return df[df['isbn'].astype(str) == query]
    
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', query):
        try:
            pd.to_datetime(query)
            return df[df['date'].astype(str) == query]
        except ValueError:
            return df[df['book_id'].isna()]
    
    return df[df['title'].str.lower().str.contains(query, na=False)]

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


# Query to get author count per book
author_count_query = """
    SELECT book_id, COUNT(author_id) as author_count
    FROM book_authors
    GROUP BY book_id
"""
author_counts = conn.query(author_count_query,show_spinner = False)
# Convert to dictionary for easy lookup
author_count_dict = dict(zip(author_counts['book_id'], author_counts['author_count']))

# Fetch books filtered by publishing_consultant
query = """
    SELECT 
    b.book_id, 
    b.title, 
    b.date,
    b.writing_start,
    b.writing_end,
    b.proofreading_start,
    b.proofreading_end,
    b.formatting_start,
    b.formatting_end,
    b.cover_start,
    b.cover_end,
    b.publisher,
    b.is_thesis_to_book,
    b.author_type,
    b.is_publish_only,
    b.apply_isbn,
    b.isbn,
    b.price,
    -- Aggregate EMI values to avoid duplicates
    MAX(ba.total_amount) as total_amount,
    MAX(ba.emi1) as emi1,
    MAX(ba.emi2) as emi2,
    MAX(ba.emi3) as emi3,
    ba.publishing_consultant
FROM books b
INNER JOIN book_authors ba ON b.book_id = ba.book_id
WHERE ba.publishing_consultant = :user_name
GROUP BY 
    b.book_id, b.title, b.date, b.writing_start, b.writing_end,
    b.proofreading_start, b.proofreading_end, b.formatting_start, b.formatting_end,
    b.cover_start, b.cover_end, b.publisher, b.is_thesis_to_book, b.author_type,
    b.is_publish_only, b.apply_isbn, b.isbn, b.price, ba.publishing_consultant
ORDER BY b.date DESC
"""


try:
    books = conn.query(query, params={"user_name": user_name}, show_spinner=False)
    book_ids = books['book_id'].tolist()
    authors_data = fetch_all_book_authors(book_ids, conn)
    printeditions_data = fetch_all_printeditions(book_ids, conn)
    
    if books.empty:
        st.info(f"No books found for publishing consultant: {user_name}")
        st.stop()
        
except Exception as e:
    st.error(f"Error fetching books: {e}")
    st.stop()

# Header layout
c1,c2, c3 = st.columns([10,30,3], vertical_alignment="bottom")

with c1:
    st.markdown("## 📚 AGPH Books")
    
with c2:
    st.caption(f":material/account_circle: Welcome! {user_name} ({user_role})")

with c3:
    if st.button(":material/refresh: Refresh", key="refresh_books", type="tertiary"):
        st.cache_data.clear()

# Search bar and filters
srcol1, srcol2, scrol3= st.columns([5, 3, 1,], gap="small")
with srcol1:
    search_query = st.text_input(
        "🔎 Search Books",
        "",
        placeholder="Search by ID, title, ISBN, date, or @authorname, !authoremail, #authorphone..",
        key="search_bar",
        label_visibility="collapsed"
    )
    if search_query and search_query.lower() in ["yogesh sharma", "rishabh vyas"]:
        st.balloons()
        st.toast(f"Hello {user_name}!😄", icon="🎉", duration="long")
    
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

with srcol2:
    # Popover for filtering
    with st.popover("Filter by Date, Status, Publisher, Subject", width="stretch"):
        # Extract unique publishers, years, and author types from the dataset
        unique_publishers = sorted(books['publisher'].dropna().unique())
        books['date'] = pd.to_datetime(books['date'])
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
        if 'publish_only_filter' not in st.session_state:
            st.session_state.publish_only_filter = None
        if 'thesis_to_book_filter' not in st.session_state:
            st.session_state.thesis_to_book_filter = None
        if 'clear_filters_trigger' not in st.session_state:
            st.session_state.clear_filters_trigger = 0

        # Reset button at the top
        if st.button(":material/restart_alt: Reset Filters", key="clear_filters", help="Clear all filters", width="stretch", type="secondary"):
            st.session_state.year_filter = None
            st.session_state.month_filter = None
            st.session_state.start_date_filter = None
            st.session_state.end_date_filter = None
            st.session_state.status_filter = None
            st.session_state.publisher_filter = None
            st.session_state.isbn_filter = None
            st.session_state.author_type_filter = None
            st.session_state.publish_only_filter = None
            st.session_state.thesis_to_book_filter = None
            st.session_state.clear_filters_trigger += 1
            st.rerun()

        # Tabs for filter categories
        tabs = st.tabs(["Status", "Author Type", "Publisher", "Date"])

        # Date tab
        with tabs[3]:
            year_options = [str(year) for year in unique_years]
            selected_year = st.pills(
                "Year:",
                options=year_options,
                key=f"year_pills_{st.session_state.clear_filters_trigger}",
                label_visibility='visible'
            )
            if selected_year:
                st.session_state.year_filter = int(selected_year)
            elif selected_year is None:
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
                    "Month:",
                    options=month_options,
                    key=f"month_pills_{st.session_state.clear_filters_trigger}",
                    label_visibility='visible'
                )
                if selected_month:
                    st.session_state.month_filter = next(
                        (num for num, name in month_names.items() if name == selected_month),
                        None
                    )
                elif selected_month is None:
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

        # Status tab
        with tabs[0]:
            status_options = ["Delivered", "On Going","Pending Payment"]
            selected_status = st.pills(
                "Book Status:",
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

        # Publisher tab
        with tabs[2]:
            publisher_options = unique_publishers
            selected_publisher = st.pills(
                "Publisher:",
                options=publisher_options,
                key=f"publisher_pills_{st.session_state.clear_filters_trigger}",
                label_visibility='visible'
            )
            st.session_state.publisher_filter = selected_publisher

        # Author Type tab
        with tabs[1]:
            # Author type filter
            author_type_options = ["Single", "Double", "Triple", "Multiple"]
            selected_author_type = st.pills(
                "Author Type:",
                options=author_type_options,
                key=f"author_type_pills_{st.session_state.clear_filters_trigger}",
                label_visibility='visible'
            )
            st.session_state.author_type_filter = selected_author_type

            # Book Type filters
            with st.container():
                col1, col2, col3 = st.columns([1,1,0.9], gap="small")
                with col1:
                    # Publish Only filter
                    publish_only_options = ["Publish Only"]
                    selected_publish_only = st.pills(
                        "Book Type:",
                        options=publish_only_options,
                        key=f"publish_only_pills_{st.session_state.clear_filters_trigger}",
                        label_visibility='visible'
                    )
                    st.session_state.publish_only_filter = selected_publish_only
                with col2:
                    # Thesis to Book filter
                    thesis_to_book_options = ["Thesis to Book"]
                    selected_thesis_to_book = st.pills(
                        "Thesis Type:",
                        options=thesis_to_book_options,
                        key=f"thesis_to_book_pills_{st.session_state.clear_filters_trigger}",
                        label_visibility='visible'
                    )
                    st.session_state.thesis_to_book_filter = selected_thesis_to_book

    # Apply filters
    filtered_books = filter_books(books, search_query)
    applied_filters = []

    # Apply publisher filter
    if st.session_state.publisher_filter:
        filtered_books = filtered_books[filtered_books['publisher'] == st.session_state.publisher_filter]
        applied_filters.append(f"Publisher={st.session_state.publisher_filter}")

    # Apply publish only filter
    if st.session_state.publish_only_filter:
        filtered_books = filtered_books[filtered_books['is_publish_only'] == 1]
        applied_filters.append(f"Publish Type={st.session_state.publish_only_filter}")

    # Apply thesis to book filter
    if st.session_state.thesis_to_book_filter:
        filtered_books = filtered_books[filtered_books['is_thesis_to_book'] == 1]
        applied_filters.append(f"Thesis Type={st.session_state.thesis_to_book_filter}")

    # Apply date filters
    if st.session_state.year_filter or st.session_state.month_filter or st.session_state.start_date_filter or st.session_state.end_date_filter:
        filtered_books = filter_books_by_date(
            filtered_books,
            None,
            st.session_state.month_filter,
            st.session_state.year_filter,
            st.session_state.start_date_filter,
            st.session_state.end_date_filter
        )
        if st.session_state.year_filter:
            applied_filters.append(f"Year={st.session_state.year_filter}")
        if st.session_state.month_filter:
            month_names = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
            applied_filters.append(f"Month={month_names.get(st.session_state.month_filter)}")
        if st.session_state.start_date_filter:
            applied_filters.append(f"Start Date={st.session_state.start_date_filter}")
        if st.session_state.end_date_filter:
            applied_filters.append(f"End Date={st.session_state.end_date_filter}")

    # Apply ISBN filter
    if st.session_state.isbn_filter:
        if st.session_state.isbn_filter == "Not Applied":
            filtered_books = filtered_books[filtered_books['isbn'].isna() & (filtered_books['apply_isbn'] == 0)]
        elif st.session_state.isbn_filter == "Not Received":
            filtered_books = filtered_books[filtered_books['isbn'].isna() & (filtered_books['apply_isbn'] == 1)]
        applied_filters.append(f"ISBN={st.session_state.isbn_filter}")

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
        applied_filters.append(f"Status={st.session_state.status_filter}")

    # Apply author type filter
    if st.session_state.author_type_filter:
        filtered_books = filtered_books[filtered_books['author_type'] == st.session_state.author_type_filter]
        applied_filters.append(f"Author Type={st.session_state.author_type_filter}")

if applied_filters:
    st.success(f"Applied Filters: {', '.join(applied_filters)}")

with scrol3:
    with st.popover("More", width="stretch", help="More Options"):
        click_id = str(uuid.uuid4())
        query_params = {
            "click_id": click_id,
            "session_id": st.session_state.session_id
        }
        full_url = get_page_url("tasks", token) + f"&{urlencode(query_params, quote_via=quote)}"
        st.link_button(
            label="🕒 Timesheet",
            url=full_url,
            type="tertiary",
            width="content"
        )

        full_url = get_page_url("prints", token) + f"&{urlencode(query_params, quote_via=quote)}"
        st.link_button(
            label="💬 Message",
            url=full_url,
            type="tertiary",
            width="content"
        )
        full_url = get_page_url("author_positions", token) + f"&{urlencode(query_params, quote_via=quote)}"
        st.link_button(
            label="📚 Open Positions",
            url=full_url,
            type="tertiary",
            width="content"
        )


# Pagination
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1
page_size = 40
total_books = len(filtered_books)
total_pages = max(1, (total_books + page_size - 1) // page_size)
st.session_state.current_page = max(1, min(st.session_state.current_page, total_pages))
start_idx = (st.session_state.current_page - 1) * page_size
end_idx = min(start_idx + page_size, total_books)
paginated_books = filtered_books.iloc[start_idx:end_idx]

# Table rendering
column_size = [0.5, 3.8, 1, 1, 1, 1, 1]
with st.container(border=False):
    if paginated_books.empty:
        st.error("No books available.")
    else:
        if applied_filters or search_query:
            st.warning(f"Showing {start_idx + 1}-{min(end_idx, len(filtered_books))} of {len(filtered_books)} books")

        book_ids = paginated_books['book_id'].tolist()
        authors_df = fetch_all_book_authors(book_ids, conn)
        printeditions_df = fetch_all_printeditions(book_ids, conn)
        author_names_dict = fetch_all_author_names(book_ids, conn)
        authors_grouped = {book_id: group for book_id, group in authors_df.groupby('book_id')}

        grouped_books = paginated_books.groupby(pd.Grouper(key='date', freq='ME'))
        reversed_grouped_books = reversed(list(grouped_books))

        for month, monthly_books in reversed_grouped_books:
            monthly_books = monthly_books.sort_values(by='date', ascending=False)
            num_books = len(monthly_books)
            st.markdown(f'<div class="month-header">{month.strftime("%B %Y")} ({num_books} books)</div>', unsafe_allow_html=True)

            for _, row in monthly_books.iterrows():
                st.markdown('<div class="data-row">', unsafe_allow_html=True)
                authors_display = author_names_dict.get(row['book_id'], "No authors")
                col1, col2, col3, col4, col5, col6, col7 = st.columns(column_size, vertical_alignment="center")

                with col1:
                    st.write(row['book_id'])
                with col2:
                    author_count = author_count_dict.get(row['book_id'], 0)
                    author_badge = get_author_badge(row.get('author_type', 'Multiple'), author_count)
                    publish_badge = get_publish_badge(row.get('is_publish_only', 0))
                    thesis_to_book_badge = get_thesis_to_book_badge(row.get('is_thesis_to_book', 0))
                    checklist_display = get_author_checklist_pill(row['book_id'], row, authors_grouped)
                    authors_display = author_names_dict.get(row['book_id'], "No authors found")

                    html_content = f"""
                    <div class="cell-container">
                        <div class="title-line">
                            {row['title']} {publish_badge}{thesis_to_book_badge}{author_badge}
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
                    # Publisher pill using pill-badge class
                    publisher_class = {
                        'AGPH': 'publisher-Penguin',
                        'Cipher': 'publisher-HarperCollins',
                        'AG Volumes': 'publisher-Macmillan',
                        'AG Classics': 'publisher-RandomHouse'
                    }.get(row['publisher'], 'publisher-default')
                    st.markdown(f'<div class="pill-badge {publisher_class}">{row["publisher"]}</div>',unsafe_allow_html=True)
                with col5:
                    st.markdown(get_isbn_display(row["book_id"], row["isbn"], row["apply_isbn"]), unsafe_allow_html=True)
                with col6:
                    st.markdown(get_payment_status(row), unsafe_allow_html=True)
                with col7:
                    btn_col1, btn_col2 = st.columns([1, 1], vertical_alignment="bottom")
                    with btn_col1:
                        publisher = row.get('publisher', '')
                        if publisher not in ["AG Kids", "NEET/JEE"] or user_role == "admin":
                            if st.button(":material/currency_rupee:", key=f"price_btn_{row['book_id']}", help="Edit Payments"):
                                manage_price_dialog(row['book_id'], conn)
                        else:
                            st.button(":material/currency_rupee:", key=f"price_btn_{row['book_id']}", help="Price management disabled for this publisher", disabled=True)
                    with btn_col2:
                        if st.button(":material/info:", key=f"details_{row['book_id']}", help="View Details"):
                            show_book_details(row['book_id'], row, authors_data, printeditions_data)
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            f"<div style='text-align: center; margin-bottom: 10px;'>"
            f"Showing <span style='font-weight: bold; color: #362f2f;'>{start_idx + 1}</span>-"
            f"<span style='font-weight: bold; color: #362f2f;'>{end_idx}</span> of "
            f"<span style='font-weight: bold; color: #362f2f;'>{total_books}</span> books"
            f"</div>",
            unsafe_allow_html=True
        )

        if total_pages > 1:
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