import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
import io
from auth import validate_token
from constants import log_activity
from constants import connect_db

logo = "logo/logo_black.png"
fevicon = "logo/favicon_black.ico"
small_logo = "logo/favicon_white.ico"

st.set_page_config(page_title='Pending Work', page_icon="⏳", layout="wide")

st.logo(logo,
size = "large",
icon_image = small_logo
)

validate_token()

user_role = st.session_state.get("role", None)
user_app = st.session_state.get("app", None)
user_access = st.session_state.get("access", None)


if user_role != 'admin' and not (
    user_role == 'user' and 
    user_app == 'main' and 
    'Pending Work' in user_access 
):
    st.error("⚠️ Access Denied: You don't have permission to access this page.")
    st.stop()

st.cache_data.clear()

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


# Custom CSS
st.markdown("""
<style>
.status-badge-red {
        background-color: #FFEBEE;
        color: #F44336;
        padding: 3px 18px;
        border-radius: 8px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
        font-size: 20px;
        margin-bottom: 16px;
    }
    .badge-count {
        background-color: rgba(255, 255, 255, 0.9);
        color: inherit;
        padding: 2px 9px;
        border-radius: 10px;
        margin-left: 6px;
        font-size: 14px;
        font-weight: normal;
    }
.author-pill {
    background-color: #E3F2FD;
    color: #1E88E5;
    padding: 2px 5px;
    border-radius: 13px;
    font-size: 11px;
    margin-left: 7px;
    display: inline-block;
}
.table-header {
    font-weight: bold;
    font-size: 14.5px;
    color: #333;
    padding: 7px 10px;
    border-bottom: 2px solid #ddd;
}
.table-row {
    padding: 1px 9px;
    background-color: #ffffff;
    font-size: 14px; 
    margin-bottom: 20px;
    margin-top: 20px;    
}

.days-badge-green {
    background-color: #E8F5E9;
    color: #2E7D32;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 100px; /* Adjust as needed */
    text-align: center;
    white-space: nowrap;
}
.days-badge-yellow {
    background-color: #FFFDE7;
    color: #FBC02D;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 100px; /* Adjust as needed */
    text-align: center;
    white-space: nowrap;

}
.days-badge-orange {
    background-color: #FFF3E0;
    color: #F57C00;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 100px; /* Adjust as needed */
    text-align: center;
    white-space: nowrap;
}
.days-badge-red {
    background-color: #ffe6e6;
    color: #d32f2f;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 100px; /* Adjust as needed */
    text-align: center;
    white-space: nowrap;
}
.stuck-reason-welcome-mail-pending {
    background-color: #D9E6FF;
    color: #2B579A;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    text-align: center;
    min-width: 190px;
    white-space: nowrap;
}
            
.stuck-reason-isbn-not-applied {
    background-color: #E6ECEF;
    color: #374957;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    text-align: center;
    min-width: 190px;
    white-space: nowrap;
}
            
.stuck-reason-isbn-not-received {
    background-color: #D9E6FF;
    color: #2B579A;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    text-align: center;
    min-width: 190px;
    white-space: nowrap;
}
.stuck-reason-cover-agreement-pending {
    background-color: #F0E1FF;
    color: #5C2D91;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 190px;
    text-align: center;
    white-space: nowrap;
}
.stuck-reason-waiting-for-author-details {
    background-color: #DDF4E8;
    color: #1A6642;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 190px;
    text-align: center;
    white-space: nowrap;
}
.stuck-reason-waiting-for-photo {
    background-color: #FFE8D6;
    color: #B35600;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 190px;
    text-align: center;
    white-space: nowrap;
}
.stuck-reason-waiting-for-id-proof {
    background-color: #E0F7FA;
    color: #00838F;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 190px;
    text-align: center;
    white-space: nowrap;
}
.stuck-reason-waiting-for-agreement {
    background-color: #E3E7FF;
    color: #2E3A9B;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 190px;
    text-align: center;
    white-space: nowrap;
}
.stuck-reason-waiting-for-digital-proof {
    background-color: #D6F0F5;
    color: #005B66;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 190px;
    text-align: center;
    white-space: nowrap;
}
.stuck-reason-waiting-for-print-confirmation {
    background-color: #E8F3D8;
    color: #355E1F;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 190px;
    text-align: center;
    white-space: nowrap;
}
.stuck-reason-writing-pending {
    background-color: #FFF3D6;
    color: #B38700;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 190px;
    text-align: center;
    white-space: nowrap;
}
.stuck-reason-proofreading-pending {
    background-color: #E8DAFF;
    color: #4B2A8C;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 190px;
    text-align: center;
    white-space: nowrap;
}
.stuck-reason-formatting-pending {
    background-color: #DBEAFF;
    color: #1F5EAA;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 190px;
    text-align: center;
    white-space: nowrap;
}
.stuck-reason-cover-design-pending {
    background-color: #FFD6E0;
    color: #9B1B4C;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 190px;
    text-align: center;
    white-space: nowrap;
}
.stuck-reason-in-printing {
    background-color: #E0F2E3;
    color: #2A6B3A;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 190px;
    text-align: center;
    white-space: nowrap;
}
.stuck-reason-not-dispatched-yet {
    background-color: #FFF0D1;
    color: #B37700;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 190px;
    text-align: center;
    white-space: nowrap;
}
.stuck-reason-waiting-for-print {
    background-color: #E6ECEF;
    color: #374957;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 190px;
    text-align: center;
    white-space: nowrap;
}
.stuck-reason-not-started {
    background-color: #ECE9E6;
    color: #40352F;
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 190px;
    text-align: center;
    white-space: nowrap;
}
                      
.pill-badge {
    padding: 6px 8px;
    border-radius: 12px;
    font-size: 12px;
    display: inline-block;
    min-width: 100px; /* Adjust as needed */
    text-align: center;
    white-space: nowrap;
}
            
.publisher-Penguin { background-color: #fff3e0; color: #ef6c00; }
.publisher-HarperCollins { background-color: #e6f3ff; color: #0052cc; }
.publisher-Macmillan { background-color: #f0e6ff; color: #6200ea; }
.publisher-RandomHouse { background-color: #e6ffe6; color: #2e7d32; }
.publisher-default { background-color: #f5f5f5; color: #616161; }

.compact-table { font-size: 12px; border-collapse: collapse; width: 100%; }
.compact-table th, .compact-table td { border: 1px solid #e0e0e0; padding: 5px 7px; text-align: left; }
.compact-table th { background-color: #dfe6ed; font-weight: 600; color: #2c3e50; }
.compact-table tr:nth-child(even) { background-color: #f8fafc; }
.section-title { margin-top: 10px; margin-bottom: 5px; font-size: 16px; color: #2c3e50; font-weight: 600; }
            
.info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; font-size: 12px; }
.info-box { padding: 5px; border-radius: 6px; background-color: #f1f5f9; }
.info-label { font-weight: 600; color: #2c3e50; display: inline-block; margin-right: 4px; }
.book-title { font-size: 18px; color: #2c3e50; font-weight: 700; margin-bottom: 8px; }

</style>
""", unsafe_allow_html=True)

conn = connect_db()

# Initialize session state from query parameters
query_params = st.query_params
click_id = query_params.get("click_id", [None])[0]  # Extract first element, default to None
session_id = query_params.get("session_id", [None])[0]  # Extract first element, default to None

# Set session_id in session state
st.session_state.session_id = session_id

# Initialize logged_click_ids if not present
if "logged_click_ids" not in st.session_state:
    st.session_state.logged_click_ids = set()

# Log navigation if click_id is present, not None, and not already logged
if click_id and click_id != "None" and click_id not in st.session_state.logged_click_ids:
    try:
        log_activity(
            conn,
            st.session_state.user_id,
            st.session_state.username,
            st.session_state.session_id,
            "navigated to page",
            f"Page: Pending Work"
        )
        st.session_state.logged_click_ids.add(click_id)
    except Exception as e:
        st.error(f"Error logging navigation: {str(e)}")

# Function to fetch book_author details for multiple book_ids with author details
def fetch_all_book_authors(book_ids, conn):
    if not book_ids:
        return pd.DataFrame(columns=['book_id', 'author_id', 'author_position', 'welcome_mail_sent', 
                                   'cover_agreement_sent', 'author_details_sent', 'photo_recive', 
                                   'id_proof_recive', 'agreement_received', 'digital_book_sent', 
                                   'printing_confirmation', 'name', 'phone', 'publishing_consultant'])
    query = """
    SELECT ba.book_id, ba.author_id, ba.author_position, ba.welcome_mail_sent, 
           ba.cover_agreement_sent, ba.author_details_sent, ba.photo_recive, 
           ba.id_proof_recive, ba.agreement_received, ba.digital_book_sent, 
           ba.printing_confirmation, a.name, a.phone, ba.publishing_consultant
    FROM book_authors ba
    JOIN authors a ON ba.author_id = a.author_id
    WHERE ba.book_id IN :book_ids
    """
    return conn.query(query, params={'book_ids': tuple(book_ids)}, show_spinner=False)

# Function to fetch print editions for multiple book_ids (restored original)
def fetch_all_printeditions(book_ids, conn):
    if not book_ids:
        return pd.DataFrame(columns=['book_id', 'print_id', 'status'])
    query = """
    SELECT book_id, print_id, status
    FROM PrintEditions
    WHERE book_id IN :book_ids
    """
    return conn.query(query, params={'book_ids': tuple(book_ids)}, show_spinner=False)

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

# Function to determine stuck reason
def get_stuck_reason(book_id, book_row, authors_df, printeditions_df):
    book_authors_df = authors_df[authors_df['book_id'] == book_id]
    book_printeditions_df = printeditions_df[printeditions_df['book_id'] == book_id]

    # Define the checklist sequence
    checklist_sequence = [
        ("welcome_mail_sent", "Welcome Mail Pending"),
        ("author_details_sent", "Waiting for Author Details"),
        ("photo_recive", "Waiting for Photo"),
        ("apply_isbn_not_applied", "ISBN Not Applied"),
        ("isbn_not_received", "ISBN Not Received"),
        ("cover_agreement_sent", "Cover/Agreement Pending"),
        ("writing", "Writing Pending", "writing_start", "writing_end"),
        ("proofreading", "Proofreading Pending", "proofreading_start", "proofreading_end"),
        ("formatting", "Formatting Pending", "formatting_start", "formatting_end"),
        ("cover", "Cover Design Pending", "cover_start", "cover_end"),
        ("digital_book_sent", "Waiting for Digital Proof"),
        ("id_proof_recive", "Waiting for ID Proof"),
        ("agreement_received", "Waiting for Agreement"),
        ("printing_confirmation", "Waiting for Print Confirmation")
    ]

    # Exclude "writing" step if is_publish_only or is_thesis_to_book is 1
    is_publish_only = book_row.get('is_publish_only', 0) == 1
    is_thesis_to_book = book_row.get('is_thesis_to_book', 0) == 1
    if is_publish_only or is_thesis_to_book:
        checklist_sequence = [item for item in checklist_sequence if item[0] != "writing"]

    # Check print editions status
    if not book_printeditions_df.empty:
        latest_print = book_printeditions_df.sort_values(by='print_id', ascending=False).iloc[0]
        if latest_print['status'] == "In Printing":
            return "In Printing"
        elif latest_print['status'] == "Received":
            return "Not Dispatched Yet"

    # Check author checklist and operations
    if not book_authors_df.empty:
        for field, label, *date_fields in checklist_sequence:
            if len(date_fields) == 2:  # Operations with start/end dates
                start_field, end_field = date_fields
                if book_row[start_field] is not None and pd.notnull(book_row[start_field]):
                    if book_row[end_field] is None or pd.isnull(book_row[end_field]):
                        return label
                else:
                    return label
            else:  # Checklist items
                if field == "apply_isbn_not_applied":
                    if book_row.get('apply_isbn', 0) == 0:
                        return label
                elif field == "isbn_not_received":
                    if book_row.get('apply_isbn', 0) == 1 and (book_row.get('isbn') is None or pd.isnull(book_row.get('isbn'))):
                        return label
                else:
                    if not book_authors_df[field].all():
                        return label

    # Check if ready for print
    if (not book_authors_df.empty and 
        all(book_authors_df[field].all() for field, _, *date_fields in checklist_sequence if len(date_fields) == 0 and field not in ["apply_isbn_not_applied", "isbn_not_received"]) and
        all(book_row[end_field] is not None and pd.notnull(book_row[end_field]) 
            for _, _, *date_fields in checklist_sequence if len(date_fields) == 2)):
        return "Waiting for Print"

    return "Not Started"

@st.dialog("Publishing Process Flow", width="medium")
def show_stuck_reason_sequence(is_publish_only=False):
    # Data definitions remain the same
    author_checklist_items = [
        ("welcome_mail_sent", "Welcome Mail", "📧"),
        ("author_details_sent", "Author Details", "📝"),
        ("photo_recive", "Photo", "📸"),
        ("apply_isbn_not_applied", "ISBN Not Applied", "🔢"),
        ("isbn_not_received", "ISBN Not Received", "🔢"),
        ("cover_agreement_sent", "Cover/Agreement", "📜"),
    ]

    operations_items = [
        ("writing", "Writing", "✍️"),
        ("proofreading", "Proofreading", "🛠️"),
        ("formatting", "Formatting", "🛠️"),
        ("cover", "Cover Design", "🛠️"),
    ]
    if is_publish_only:
        operations_items = [item for item in operations_items if item[0] != "writing"]

    final_steps_items = [
        ("digital_book_sent", "Digital Proof", "📄"),
        ("id_proof_recive", "ID Proof", "🆔"),
        ("agreement_received", "Agreement", "📜"),
        ("printing_confirmation", "Print Confirmation", "🖨️"),
        ("waiting_for_print", "Waiting for Print", "⏳"),
        ("in_printing", "In Printing", "🖨️"),
        ("not_dispatched", "Not Dispatched Yet", "🚚")
    ]

    groups = [
        {"name": "✅ Author Checklist", "items": author_checklist_items, "color": "#3b82f6"},
        {"name": "✏️ Operations", "items": operations_items, "color": "#10b981"},
        {"name": "✔️ Final Steps", "items": final_steps_items, "color": "#f59e0b"}
    ]

    # --- REVISED CSS FOR A VERTICAL LAYOUT ---
    tree_html = """
    <style>
        .flow-container {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 10px;
            border-radius: 8px;
            /* --- KEY CHANGE: Stacks groups vertically --- */
            display: flex;
            flex-direction: column;
            align-items: center; /* Center groups horizontally */
            gap: 1px;           /* Space between groups/connectors */
        }
        .flow-group {
            border: 1px solid #e2e8f0;
            background-color: #ffffff;
            border-radius: 8px;
            padding: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            width: 98%; /* Use most of the container's width */
            max-width: 700px;
        }
        .group-header {
            font-weight: 600;
            font-size: 12px;
            color: white;
            padding: 5px 10px;
            border-radius: 6px;
            margin-bottom: 12px;
            text-align: center;
        }
        .group-items {
            display: flex;
            flex-wrap: wrap;         /* Allows nodes within a group to wrap */
            justify-content: center;
            align-items: center;
            gap: 8px 4px;            /* Vertical and horizontal gap for items */
        }
        .flow-node {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            padding: 5px 8px;
            width: 110px;
            font-size: 11.5px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            min-height: 32px;
            text-align: center;
        }
        .connector {
            color: #94a3b8;
            font-weight: bold;
            text-align: center;
        }
        .h-connector { /* Horizontal connector for inside groups */
            font-size: 16px;
        }
        .v-connector { /* Vertical connector for between groups */
            font-size: 20px;
            line-height: 1;
        }
        .note {
            font-style: italic;
            font-size: 10px;
            color: #64748b;
            text-align: center;
            margin-top: 8px;
            width: 100%;
        }
    </style>
    <div class='flow-container'>
    """

    # --- REVISED HTML GENERATION FOR VERTICAL FLOW ---
    total_groups = len(groups)
    for i, group in enumerate(groups):
        # Create a container for the group
        tree_html += "<div class='flow-group'>"
        tree_html += f"<div class='group-header' style='background: {group['color']}'>{group['name']}</div>"

        # Create a flex container for the nodes to allow wrapping
        tree_html += "<div class='group-items'>"
        total_items = len(group['items'])
        for j, (field, label, icon) in enumerate(group["items"]):
            tree_html += f"<div class='flow-node'>{icon} {label}</div>"
            if j < total_items - 1:
                tree_html += "<div class='connector h-connector'>&rarr;</div>"
        tree_html += "</div></div>"

        # Add a vertical connector between groups
        if i < total_groups - 1:
            tree_html += "<div class='connector v-connector'>&darr;</div>"

    # if is_publish_only:
    #     tree_html += "<div class='note'>📖 Publish-only books skip the Writing step.</div>"
    # tree_html += "</div>"

    # st.markdown(
    #     "<p style='font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, sans-serif; color: #4b5563; font-size: 12 px; text-align: center;'>"
    #     "This flowchart shows the order of steps in the publishing process.</p>",
    #     unsafe_allow_html=True
    # )
    col1, col2 = st.columns([0.11, 1])
    with col2:
        st.caption('This is the order in which stuck reasons are evaluated for books in the publishing process.')

    st.markdown(tree_html, unsafe_allow_html=True)
    st.markdown(
        "<p style='font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, sans-serif; color: #4b5563; font-size: 12 px; text-align: center;'>"
        "</p>",
        unsafe_allow_html=True
    )


#@st.dialog("Book Stuck Reason Summary", width="large")
def show_stuck_reason_summary(books_df, authors_df, printeditions_df):

    # Prepare data for table and export
    today = date.today()
    export_data = []
    stuck_data = []
    for _, book_row in books_df.iterrows():
        book_id = book_row['book_id']
        reason = get_stuck_reason(book_id, book_row, authors_df, printeditions_df)
        
        # Get author count and consultants
        book_authors = authors_df[authors_df['book_id'] == book_id]
        author_count = len(book_authors)
        consultants = ", ".join(book_authors['publishing_consultant'].dropna().unique()) if not book_authors.empty else "N/A"
        
        # Calculate days since enrolled
        enrolled_date = book_row['date'] if pd.notnull(book_row['date']) else None
        days_stuck = (today - enrolled_date).days if enrolled_date else 0
        
        # Data for table
        stuck_data.append({
            'book_id': book_id,
            'reason': reason,
            'author_count': author_count,
            'days_stuck': days_stuck
        })
        
        # Data for export
        export_data.append({
            'Book ID': book_id,
            'Title': book_row['title'],
            'Date': enrolled_date,
            'Since Enrolled': days_stuck,
            'Stuck Reason': reason,
            'Number of Authors': author_count,
            'Publishing Consultants': consultants
        })

    # Aggregate data for table
    stuck_df = pd.DataFrame(stuck_data)
    reason_summary = stuck_df.groupby('reason').agg({
        'book_id': 'count',
        'author_count': 'sum',
        'days_stuck': 'mean'
    }).reset_index()
    reason_summary.columns = ['Reason For Hold', 'Book Count', 'Total Authors', 'Avg Days Stuck']
    reason_summary['Avg Days Stuck'] = reason_summary['Avg Days Stuck'].round(1)

    # Prepare export DataFrame
    export_df = pd.DataFrame(export_data)

    # Create two columns for table and pie chart
    col_table, col_chart = st.columns([1, 1])

    # Display the table in the left column
    with col_table:
        #st.markdown("<h4 class='section-title'>Stuck Reason Summary</h4>", unsafe_allow_html=True)
        if not reason_summary.empty:
            table_html = "<table class='compact-table'><tr><th>Reason For Hold</th><th>Books</th><th>Authors</th><th>Avg Days</th></tr>"
            for _, row in reason_summary.iterrows():
                table_html += f"<tr><td>{row['Reason For Hold']}</td><td>{row['Book Count']}</td><td>{row['Total Authors']}</td><td>{row['Avg Days Stuck']}</td></tr>"
            table_html += "</table>"
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.info("No books found.")

        # Export button
        if not export_df.empty:
            # Generate Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                export_df.to_excel(writer, sheet_name='Stuck_Reason_Details', index=False)
            excel_data = output.getvalue()

            col1, col2 = st.columns([1, 2], gap="small")
            with col1:
                st.download_button(
                    label=":material/download: Export Data to Excel",
                    data=excel_data,
                    file_name=f"stuck_reason_details_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="tertiary",
                    help="Export the detailed stuck reason data to an Excel file."
                )
            with col2:
                if st.button(":material/auto_awesome_motion: Show Stuck Reason Sequence", help="This is the order in which stuck reasons are evaluated for books in the publishing proces", type="tertiary"):
                    show_stuck_reason_sequence(is_publish_only=False)

    # Display the pie chart in the right column
    with col_chart:
        #st.markdown("<h4 class='section-title'>Stuck Reason Distribution</h4>", unsafe_allow_html=True)
        if not reason_summary.empty:
            # Create a pie chart with Plotly
            pie_chart = px.pie(
                reason_summary,
                names='Reason For Hold',
                values='Book Count',
                hole=0.45,
                color_discrete_sequence=px.colors.sequential.Turbo
            )
            # Customize the layout
            pie_chart.update_traces(textinfo='label+value', insidetextorientation='radial')
            pie_chart.update_layout(
                title_text="",  # Set empty string to avoid 'undefined'
                title_font_size=1,  # Minimize the space it takes
                showlegend=False,
                title_x=0.3,
            )
            st.plotly_chart(pie_chart, use_container_width=True)
        else:
            st.info("No data available for pie chart.")

@st.dialog("Book Pending Work Details", width="large")
def show_book_details(book_id, book_row, authors_df, printeditions_df):
    # Calculate days since enrolled
    enrolled_date = book_row['date'] if pd.notnull(book_row['date']) else None
    days_since_enrolled = (datetime.now().date() - enrolled_date).days if enrolled_date else "N/A"
    
    # Count authors
    author_count = len(authors_df[authors_df['book_id'] == book_id])

    # Book Title
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
                font-size: 11px;
                color: #1f2937;
                border-collapse: collapse;
                width: 100%;
            }
            .compact-table th, .compact-table td tr {
                padding: 4px 6px;
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
            <tr><th>ID</th><th>Name</th><th>Contact</th><th>Consultant</th><th>Pos</th>
        """
        for label in checklist_labels:
            table_html += f"<th>{label}</th>"
        table_html += "</tr>"
        
        for _, author in book_authors_df.iterrows():
            table_html += f"<tr><td>{author['author_id']}</td><td>{author['name']}</td><td>{author['phone']}</td><td>{author['publishing_consultant']}</td><td>{author['author_position']}</td>"
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

# Connect to MySQL
conn = connect_db()

# Fetch books from the database where deliver = 0
query = """
SELECT book_id, title, date, writing_start, writing_end, proofreading_start, 
       proofreading_end, formatting_start, formatting_end, cover_start, cover_end, publisher, is_thesis_to_book ,author_type, is_publish_only,
         apply_isbn, isbn
FROM books
WHERE deliver = 0
"""
books_data = conn.query(query, show_spinner=False)

# Fetch author and print edition data for initial book_ids
book_ids = books_data['book_id'].tolist()
authors_data = fetch_all_book_authors(book_ids, conn)
printeditions_data = fetch_all_printeditions(book_ids, conn)

# Get all possible publishers
all_publishers = books_data['publisher'].unique().tolist()

default_days_filter = 40  # Default days filter value

# Initialize session state with defaults
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'days_filter' not in st.session_state:
    st.session_state.days_filter = default_days_filter
if 'selected_reasons' not in st.session_state:
    st.session_state.selected_reasons = []
if 'selected_publishers' not in st.session_state:
    st.session_state.selected_publishers = []
if 'selected_checklist_reasons' not in st.session_state:
    st.session_state.selected_checklist_reasons = []
if 'selected_operations_reasons' not in st.session_state:
    st.session_state.selected_operations_reasons = []
if 'selected_afterwork_reasons' not in st.session_state:
    st.session_state.selected_afterwork_reasons = []
if 'selected_isbn_reasons' not in st.session_state:
    st.session_state.selected_isbn_reasons = []
if 'sort_by' not in st.session_state:
    st.session_state.sort_by = "Book ID"
if 'sort_order' not in st.session_state:
    st.session_state.sort_order = "Ascending"

# Handle reset via query params
query_params = st.query_params
if "reset" in query_params and query_params["reset"] == "true":
    # Clear query params first
    st.query_params.clear()
    # Use a form or callback to reset widget states
    st.session_state.reset_trigger = True

# Check for reset trigger and reset values
if 'reset_trigger' in st.session_state and st.session_state.reset_trigger:
    st.session_state.search_query = ""
    st.session_state.days_filter = default_days_filter
    st.session_state.selected_reasons = []
    st.session_state.selected_publishers = []
    st.session_state.selected_checklist_reasons = []
    st.session_state.selected_operations_reasons = []
    st.session_state.selected_afterwork_reasons = []
    st.session_state.selected_isbn_reasons = []
    st.session_state.sort_by = "Book ID"
    st.session_state.sort_order = "Ascending"
    st.session_state.reset_trigger = False  # Reset the trigger

# Sync selected_reasons with all filter categories
def sync_selected_reasons():
    st.session_state.selected_reasons = (
        st.session_state.selected_checklist_reasons +
        st.session_state.selected_operations_reasons +
        st.session_state.selected_afterwork_reasons +
        st.session_state.selected_isbn_reasons
    )

# Apply Filters and Sorting
filtered_data = books_data.copy()
# Apply Search
if st.session_state.search_query:
    filtered_data = filtered_data[
        filtered_data['book_id'].astype(str).str.contains(st.session_state.search_query, case=False, na=False) |
        filtered_data['title'].str.contains(st.session_state.search_query, case=False, na=False)
    ]
    if filtered_data.empty:
        filtered_data = pd.DataFrame(columns=books_data.columns)

# Apply Days Filter
if st.session_state.days_filter > 0:
    cutoff_date = date.today() - timedelta(days=st.session_state.days_filter)
    filtered_data = filtered_data[filtered_data['date'].apply(lambda x: pd.to_datetime(x).date() <= cutoff_date if pd.notnull(x) else False)]

# Apply Publisher Filter
if st.session_state.selected_publishers:
    filtered_data = filtered_data[filtered_data['publisher'].isin(st.session_state.selected_publishers)]

# Apply Stuck Reason Filter
if st.session_state.selected_reasons and not filtered_data.empty:
    book_ids = filtered_data['book_id'].tolist()
    authors_data = fetch_all_book_authors(book_ids, conn)
    printeditions_data = fetch_all_printeditions(book_ids, conn)
    filtered_data['stuck_reason'] = filtered_data['book_id'].apply(
        lambda x: get_stuck_reason(x, filtered_data[filtered_data['book_id'] == x].iloc[0], authors_data, printeditions_data)
    )
    filtered_data = filtered_data[filtered_data['stuck_reason'].isin(st.session_state.selected_reasons)]

# Apply Sorting
if not filtered_data.empty:
    book_ids = filtered_data['book_id'].tolist()
    authors_data = fetch_all_book_authors(book_ids, conn)
    printeditions_data = fetch_all_printeditions(book_ids, conn)
    if st.session_state.sort_by == "Book ID":
        filtered_data = filtered_data.sort_values(by='book_id', ascending=(st.session_state.sort_order == "Ascending"))
    elif st.session_state.sort_by == "Date":
        filtered_data = filtered_data.sort_values(by='date', ascending=(st.session_state.sort_order == "Ascending"))
    elif st.session_state.sort_by == "Since Enrolled":
        filtered_data['days_since'] = filtered_data['date'].apply(lambda x: (date.today() - x).days if pd.notnull(x) else float('inf'))
        filtered_data = filtered_data.sort_values(by='days_since', ascending=(st.session_state.sort_order == "Ascending"))
    elif st.session_state.sort_by == "Stuck Reason":
        filtered_data['stuck_reason'] = filtered_data['book_id'].apply(
            lambda x: get_stuck_reason(x, filtered_data[filtered_data['book_id'] == x].iloc[0], authors_data, printeditions_data)
        )
        filtered_data = filtered_data.sort_values(by='stuck_reason', ascending=(st.session_state.sort_order == "Ascending"))

col1, col2, col3 = st.columns([8, 0.7, 1], vertical_alignment="bottom")
with col1:
    st.markdown("### ⏳ AGPH Pending Work")
with col2:
    if st.button(":material/refresh: Refresh", key="refresh", type="tertiary"):
        st.cache_data.clear()
with col3:
    if st.button(":material/arrow_back: Go Back", key="back_button", type="tertiary", use_container_width=True):
        st.switch_page('app.py')

# UI with Popover for Filters and Sorting
with st.container():
    col1, col2, col3 = st.columns([3, 7, 6], vertical_alignment="bottom", gap="small")
    with col1:
        st.markdown(f'<div class="status-badge-red">Overdue Books<span class="badge-count">{len(filtered_data)}</span></div>', unsafe_allow_html=True)
    with col2:
        st.text_input("Search by Book ID or Title", key="search_query", placeholder="Enter Book ID or Title", 
                      label_visibility="collapsed")
    with col3:
        with st.popover("Filters & Sort", use_container_width=True):
            txtcol1, txtcol2, txtcol3 = st.columns([1.5, 2, 1], gap="small", vertical_alignment="bottom")
            with txtcol1:
                st.number_input("Show books older than (days)", min_value=0, value=st.session_state.days_filter, step=1, key="days_filter")
            st.write("###### 📚 Filter by Publisher")
            st.pills("Filter by Publisher",
                    all_publishers,
                    key="selected_publishers",
                    selection_mode="multi",
                    label_visibility="collapsed")
            st.write("###### 📖 Filter by ISBN Status")
            st.pills("ok",
                    ["ISBN Not Applied", "ISBN Not Received"],
                    key="selected_isbn_reasons",
                    selection_mode="multi",
                    label_visibility="collapsed",
                    on_change=sync_selected_reasons)
            st.write("###### ✍️ Filter by Author Checklist")
            st.pills("ok",
                    ["Welcome Mail Pending", "Waiting for Author Details", "Waiting for Photo",
                    "Cover/Agreement Pending", "Waiting for Digital Proof", "Waiting for ID Proof",
                    "Waiting for Agreement", "Waiting for Print Confirmation"],
                    key="selected_checklist_reasons",
                    selection_mode="multi",
                    label_visibility="collapsed",
                    on_change=sync_selected_reasons)
            st.write("###### 🛠️ Filter by Operations")
            st.pills("ok",
                    ["Writing Pending", "Proofreading Pending", "Formatting Pending",
                    "Cover Design Pending"],
                    key="selected_operations_reasons",
                    selection_mode="multi",
                    label_visibility="collapsed",
                    on_change=sync_selected_reasons)
            st.write("###### 🕓 Filter by After Work")
            st.pills("ok",
                    ["Waiting for Print", "In Printing", "Not Dispatched Yet"],
                    key="selected_afterwork_reasons",
                    selection_mode="multi",
                    label_visibility="collapsed",
                    on_change=sync_selected_reasons)
            st.write("###### 🧮 Sort by")
            st.pills("ok",
                    ["Book ID", "Date", "Since Enrolled", "Stuck Reason"],
                    key="sort_by", label_visibility="collapsed")
            st.write("###### 🔁 Sort Order")
            st.radio("ok", ["Ascending", "Descending"],
                    index=0 if st.session_state.sort_order == "Ascending" else 1,
                    horizontal=True, key="sort_order", label_visibility="collapsed")
            with txtcol3:
                if st.button(":material/restart_alt: Reset Filters", use_container_width=True, type="secondary"):
                    st.query_params["reset"] = "true"
                    st.rerun()

with st.expander("⚠️ Pending Books Summary", expanded=False):
    if not filtered_data.empty:
        show_stuck_reason_summary(filtered_data, authors_data, printeditions_data)
    else:
        st.info("No Pending Books Found")

# Display Results
with st.container():
    if not filtered_data.empty:
        column_widths = [0.8, 4.2, 1.5, 1, 1.2, 2.1, 0.6]
        with st.container(border=True):
            cols = st.columns(column_widths, vertical_alignment="bottom")
            cols[0].markdown('<div class="table-header">Book ID</div>', unsafe_allow_html=True)
            cols[1].markdown('<div class="table-header">Book Title</div>', unsafe_allow_html=True)
            cols[2].markdown('<div class="table-header">Date</div>', unsafe_allow_html=True)
            cols[3].markdown('<div class="table-header">Publisher</div>', unsafe_allow_html=True)
            cols[4].markdown('<div class="table-header">Since Enrolled</div>', unsafe_allow_html=True)
            cols[5].markdown('<div class="table-header">Stuck Reason</div>', unsafe_allow_html=True)
            cols[6].markdown('<div class="table-header">Actions</div>', unsafe_allow_html=True)

            for _, book in filtered_data.iterrows():
                book_id = book['book_id']
                stuck_reason = get_stuck_reason(book_id, book, authors_data, printeditions_data)
                author_count = len(authors_data[authors_data['book_id'] == book_id])
                
                # Determine days badge class
                days_since = (date.today() - book["date"]).days if pd.notnull(book["date"]) else None
                if days_since is not None:
                    if days_since <= 30:
                        days_badge_class = "days-badge-green"
                    elif days_since <= 40:
                        days_badge_class = "days-badge-orange"
                    elif days_since <= 50:
                        days_badge_class = "days-badge-orange"
                    else:
                        days_badge_class = "days-badge-red"
                else:
                    days_badge_class = "days-badge-red"

                # Determine stuck reason badge class
                stuck_reason_class = f"stuck-reason-{stuck_reason.lower().replace(' ', '-').replace('/', '-')}"
                
                cols = st.columns(column_widths, vertical_alignment="bottom")
                cols[0].markdown(f'<div class="table-row">{book["book_id"]}</div>', unsafe_allow_html=True)
                cols[1].markdown(f'<div class="table-row">{book["title"]}<span class="author-pill">{book["author_type"]}, {author_count}</span></div>', unsafe_allow_html=True)
                cols[2].markdown(f'<div class="table-row">{book["date"].strftime("%d %B %Y") if pd.notnull(book["date"]) else ""}</div>', unsafe_allow_html=True)
                publisher_class = {
                    'AGPH': 'publisher-Penguin',
                    'Cipher': 'publisher-HarperCollins',
                    'AG Volumes': 'publisher-Macmillan',
                    'AG Classics': 'publisher-RandomHouse'
                }.get(book['publisher'], 'publisher-default')
                cols[3].markdown(f'<div class="table-row"><span class="pill-badge {publisher_class}">{book["publisher"]}</span></div>',unsafe_allow_html=True)
                cols[4].markdown(f'<div class="table-row"><span class="{days_badge_class}">{days_since if days_since is not None else "N/A"} days</span></div>', unsafe_allow_html=True)
                cols[5].markdown(f'<div class="table-row"><span class="{stuck_reason_class}">{stuck_reason}</span></div>', unsafe_allow_html=True)
                with cols[6]:
                    if st.button(":material/visibility:", key=f"action_{book['book_id']}", help="View Details"):
                        show_book_details(book_id, book, authors_data, printeditions_data)
    else:
        st.info("No Pending Books Found")