import streamlit as st
from constants import log_activity , get_total_unread_count, connect_ict_db, connect_db, get_page_url
import re
import uuid
import pandas as pd
import time
from urllib.parse import urlencode, quote
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
ict_conn = connect_ict_db()


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


total_unread = get_total_unread_count(ict_conn, st.session_state.user_id)

if total_unread > 0:
    if "unread_toast_shown" not in st.session_state:
        st.toast(f"You have {total_unread} unread messages!", icon="💬" , duration="infinite")
        st.session_state.unread_toast_shown = True

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
            'number_of_books', 'total_amount', 'delivery_date',
            'tracking_id', 'delivery_vendor', 'amount_paid'
        ])
    query = """
    SELECT ba.id, ba.book_id, ba.author_id, a.name, a.email, a.phone, 
           ba.author_position, ba.welcome_mail_sent, ba.corresponding_agent, 
           ba.publishing_consultant, ba.photo_recive, ba.id_proof_recive, 
           ba.author_details_sent, ba.cover_agreement_sent, ba.agreement_received, 
           ba.digital_book_sent, ba.printing_confirmation, ba.delivery_address, 
           ba.delivery_charge, ba.number_of_books, ba.total_amount,
           ba.delivery_date, ba.tracking_id, ba.delivery_vendor,
           COALESCE((SELECT SUM(amount) FROM author_payments WHERE book_author_id = ba.id), 0) as amount_paid
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
            'number_of_books', 'total_amount', 'delivery_date',
            'tracking_id', 'delivery_vendor', 'amount_paid'
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
    amount_paid = float(row.get('amount_paid', 0) or 0)
    has_rejected = row.get('has_rejected', 0)

    # Logic for determining status
    if has_rejected == 1:
        return generate_badge("Rejected", "#b91c1c", "#fee2e2")
    elif total <= 0:
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

@st.dialog("Manage Book Payments", width="large")
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
        # --- Grouping Logic ---
        book_authors['agent_clean'] = book_authors['corresponding_agent'].fillna('').str.strip()
        all_agents = set(book_authors[book_authors['agent_clean'] != '']['agent_clean'])
        
        def assign_group(row):
            if row['agent_clean'] != '': return row['agent_clean']
            if row['name'] in all_agents: return row['name']
            return f"INDV_{row['id']}"
            
        book_authors['payment_group'] = book_authors.apply(assign_group, axis=1)
        
        agent_summary = book_authors.groupby('payment_group').agg({
            'total_amount': 'sum',
            'amount_paid': 'sum',
            'publishing_consultant': 'first',
            'name': list
        }).reset_index()

        # Calculate book total paid
        total_book_paid = float(book_authors['amount_paid'].sum())
        total_book_expected = float(current_price) if pd.notna(current_price) else 0.0
        total_book_remaining = total_book_expected - total_book_paid

        # Determine book status color
        if total_book_paid >= total_book_expected and total_book_expected > 0:
            book_status_class, book_badge_text = "status-paid", "Fully Paid"
        elif total_book_paid > 0:
            book_status_class, book_badge_text = "status-partial", "Partially Paid"
        else:
            book_status_class, book_badge_text = "status-pending", "Pending"

        cols = st.columns(len(agent_summary) + 1, gap="small")
        
        with cols[0]:
            html = f"""
                <div class="payment-box {book_status_class}" style="border-left: 5px solid #4CAF50;">
                    <div class="author-name">Total Book Price</div>
                    <div class="payment-text">₹{int(total_book_paid)}/₹{int(total_book_expected)}</div>
                    <div class="status-badge">{book_badge_text}</div>
                    <div class="agent-text">Remaining: ₹{int(total_book_remaining)}</div>
                </div>
            """
            st.markdown(html, unsafe_allow_html=True)

        for i, row in agent_summary.iterrows():
            total_amount = int(row['total_amount'] or 0)
            amount_paid = float(row['amount_paid'] or 0)
            agent_consultant = row['publishing_consultant'] or 'Unknown Agent'
            group_id = row['payment_group']
            
            if group_id.startswith("INDV_"):
                display_name, is_group = row['name'][0], False
            else:
                display_name, is_group = group_id, True
            
            member_names = ", ".join(row['name'])

            if amount_paid >= total_amount and total_amount > 0:
                status_class, badge_text = "status-paid", "Paid"
            elif amount_paid > 0:
                status_class, badge_text = "status-partial", "Partial"
            else:
                status_class, badge_text = "status-pending", "Pending"

            with cols[i+1]:
                group_style = "border-top: 3px solid #3b82f6;" if is_group else ""
                html = f"""
                    <div class="payment-box {status_class}" style="{group_style}" title="Covers: {member_names}">
                        <div class="author-name">{display_name}</div>
                        <div class="payment-text">₹{int(amount_paid)}/₹{total_amount}</div>
                        <div class="status-badge">{badge_text}</div>
                        <div class="agent-text">{agent_consultant}</div>
                    </div>
                """
                st.markdown(html, unsafe_allow_html=True)

    # Section 1: Book Price
    with st.container(border=True):
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
                            conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id,
                            "updated book price", f"Book: {book_title} ({book_id}), New Price: ₹{price}"
                        )
                        st.toast("Book Price Updated Successfully", icon="✔️", duration="long")
                        st.cache_data.clear()
                    except ValueError:
                        st.error("Please enter a valid whole number", icon="🚨")
    
    # Section 2: Author Payments with Tabs
    with st.container(border=True):
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
                                    if status == 'Approved':
                                        status_color = "green"
                                    elif status == 'Rejected':
                                        status_color = "red"
                                    else:
                                        status_color = "orange"
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
                                    
                                    log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "registered payment", f"Book: {book_title} ({book_id}), Author: {row['name']} (ID: {row['author_id']}), Amount: ₹{amt}, Mode: {add_mode}")
                                    st.toast(f"Registered ₹{amt} for {row['name']}", icon="✅")
                                    time.sleep(1)
                                    st.rerun()
                            except ValueError:
                                st.error("Invalid amount")

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
def show_book_details(book_id, book_row, authors_df, printeditions_df, conn):
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
                        source_badge = '<span style="background-color:#F3E5F5; color:#8E24AA; padding:2px 6px; border-radius:8px; font-size:10px; font-weight:bold;">INTERNAL TEAM</span>'
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
                        section_display += ' <span style="background-color:#F3E5F5; color:#8E24AA; padding:1px 4px; border-radius:4px; font-size:9px; font-weight:bold;">INTERNAL</span>'
                        
                    corr_table += f"<tr><td>{section_display}</td><td>{corr['round_number']}</td><td>{corr['worker']}</td><td>{start_str}</td><td>{end_str}</td></tr>"
                corr_table += "</table>"
                st.markdown(corr_table, unsafe_allow_html=True)


    st.markdown("<h4 class='section-title'>Print Editions</h4>", unsafe_allow_html=True)
    conn = connect_db()
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
    -- Aggregate total_amount and amount_paid
    SUM(ba.total_amount) as total_amount,
    COALESCE(SUM(ap_agg.paid), 0) as amount_paid,
    COALESCE(MAX(ap_agg.has_rejected), 0) as has_rejected,
    ba.publishing_consultant
FROM books b
INNER JOIN book_authors ba ON b.book_id = ba.book_id
LEFT JOIN (
    SELECT 
        book_author_id, 
        SUM(CASE WHEN status = 'Approved' THEN amount ELSE 0 END) as paid,
        MAX(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END) as has_rejected
    FROM author_payments
    GROUP BY book_author_id
) ap_agg ON ba.id = ap_agg.book_author_id
WHERE ba.publishing_consultant = :user_name AND b.is_cancelled = 0
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
                SELECT DISTINCT ba.book_id
                FROM book_authors ba
                WHERE ba.total_amount > 0 
                AND COALESCE((SELECT SUM(amount) FROM author_payments WHERE book_author_id = ba.id), 0) < ba.total_amount
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

        full_url = get_page_url("/", token) + f"&{urlencode(query_params, quote_via=quote)}"
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
                            show_book_details(row['book_id'], row, authors_data, printeditions_data, conn)
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