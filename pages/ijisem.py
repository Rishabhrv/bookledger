import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime
from auth import validate_token
import altair as alt
from time import sleep
from constants import log_activity
from constants import connect_db
import uuid

########################################################################################################################
##################################--------------- Page Config ----------------------------#############################
#######################################################################################################################

logo = "logo/ijisem.png"
fevicon = "logo/ijisem.png"
small_logo = "logo/ijisem.png"

st.set_page_config(page_title='IJISEM', page_icon='🧾', layout="wide")

st.logo(logo,
size = "large",
icon_image = small_logo

)
########################################################################################################################
##################################--------------- Token Validation ----------------------------######################
#######################################################################################################################


# Run validation
validate_token()

user_role = st.session_state.get("role", None)
user_app = st.session_state.get("app", None)
user_access = st.session_state.get("access", None)
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


if user_role != 'admin' and not (
    (user_role == 'user' and user_app == 'main' and 'IJISEM' in user_access) or 
    (user_role == 'user' and user_app == 'ijisem' and 'Full Access' in user_access)
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
            padding-top: 8px !important;  /* Small padding for breathing room */
        }
            <style>
            """, unsafe_allow_html=True)

########################################################################################################################
##################################--------------- CSS Style ----------------------------######################
#######################################################################################################################

# CSS styles
st.markdown("""
    <style>
    .data-row {
        margin-bottom: 0px; /* Remove margin to avoid gaps */
        font-size: 14px; /* Smaller font size */
        color: #212529;
        padding: 8px 0; /* Vertical padding for readability */
        transition: background-color 0.2s ease;
    }
        
    .author-names {
        font-size: 12px;
        color: #555; 
        margin-bottom: 3px; /* Space between author names */
    }

    .month-header {
        font-size: 15px;
        font-weight: 600;
        color: #2c3e50;
        padding: 5px 12px;
        border-left: 4px solid #e74c3c;
        margin: 20px 0 15px;
        border-radius: 4px;
    }

    .table-header {
        font-size: 14px;
        font-weight: 600;
        color: #2c3e50;
        padding: 8px 0;
        border-bottom: 2px solid #cbd1d6; /* Header bottom border */
    }

    .row-divider {
        border-top: 1px solid #e9ecef; /* Single horizontal border between rows */
        margin: 0;
        padding: 0;
    }
            
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85em;
        font-weight: 500;
        text-align: center;
        min-width: 80px;
        }
            
    .badge-completed {
        background-color: #e6ffe6;
        color: #2e7d32;
    }
    .badge-pending {
        background-color: #FFEBEE;
        color: #F44336;
    }
    .badge-accepted {
        background-color: #E3F2FD;
        color: #1565C0;
    }
    .badge-rejected {
        background-color: #FFEBEE;
        color: #C62828;
    }
    .badge-in-review {
        background-color: #EDE7F6;
        color: #4527A0;
    }
    .badge-excess-plagiarism {
        background-color: #fff3e0;
        color: #e65100;
    }
    .badge-paid {
        background-color: #fff3e0;
        color: #ef6c00;
    }
    .badge-due {
        background-color: #ffede5;
        color: #d84315;

        border-radius: 12px;
        font-size: 0.85em;
        font-weight: 500;
        text-align: center;
        min-width: 80px;
    }
    .small-pill {
        display: inline-block;
        padding: 1px 6px;
        border-radius: 10px;
        font-size: 0.8em;
        margin-left: 6px;
        line-height: 1.2;
    }
    .pill-publishing {
        background-color: #fff3e0;
        color: #ef6c00;
    }
    .pill-writing-publishing {
        background-color: #fff3e0;
        color: #ef6c00;
    }
    .pill-published {
        background-color: #e6ffe6;
        color: #2e7d32;
    }
    .pill-not-published {
        background-color: #f8d7da;
        color: #721c24;
    }
    .tick::before {
        content: "✔ ";
        color: #155724;
    }
    .cross::before {
        content: "✖ ";
        color: #721c24;
    }
      
    </style>
            
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:FILL@1" rel="stylesheet" />
""", unsafe_allow_html=True)

########################################################################################################################
##################################--------------- Database Connection ----------------------------######################
#######################################################################################################################


# Database connection
@st.cache_resource
def connect_db_ijisem():
    try:
        def get_connection():
            return st.connection('ijisem', type='sql')
        conn = get_connection()
        return conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

conn_main = connect_db()
conn = connect_db_ijisem()


if user_app == 'ijisem':
    if "activity_logged" not in st.session_state:
        log_activity(
                    conn_main,
                    st.session_state.user_id,
                    st.session_state.username,
                    st.session_state.session_id,
                    "logged in",
                    f"App: {st.session_state.app}"
                )
        st.session_state.activity_logged = True

if user_app == 'main':
    # Initialize session state from query parameters
    query_params = st.query_params
    click_id = query_params.get("click_id", [None])
    session_id = query_params.get("session_id", [None])

    # Set session_id in session state
    st.session_state.session_id = session_id

    # Initialize logged_click_ids if not present
    if "logged_click_ids" not in st.session_state:
        st.session_state.logged_click_ids = set()

    # Log navigation if click_id is present and not already logged
    if click_id and click_id not in st.session_state.logged_click_ids:
        try:
            log_activity(
                conn_main,
                st.session_state.user_id,
                st.session_state.username,
                st.session_state.session_id,
                "navigated to page",
                f"Page: IJISEM"
            )
            st.session_state.logged_click_ids.add(click_id)
        except Exception as e:
            st.error(f"Error logging navigation: {str(e)}")


########################################################################################################################
##################################--------------- Helping Functions ----------------------------######################
#######################################################################################################################

def fetch_papers(conn):
    try:
        query = """
            SELECT 
                p.paper_id,
                p.paper_title,
                p.receiving_date,
                p.acceptance,
                p.payment_amount,
                p.payment_date,
                p.ai_plagiarism,
                p.plagiarism,
                p.review_done,
                p.publishing_type,
                p.paper_uploading_date,
                p.formatting_date,
                p.writing_date,
                p.emi_1_amount,
                p.emi_2_amount,
                p.emi_3_amount,
                p.volume,
                p.issue
            FROM papers p
            ORDER BY p.receiving_date DESC
        """
        df = conn.query(query, show_spinner=False)
        # Convert receiving_date to datetime
        df['receiving_date'] = pd.to_datetime(df['receiving_date'])
        df['paper_uploading_date'] = pd.to_datetime(df['paper_uploading_date'])
        df['payment_date'] = pd.to_datetime(df['payment_date'])
        return df
    except Exception as e:
        st.error(f"Error fetching papers: {e}")
        return pd.DataFrame()

def fetch_author_names(paper_id, conn):
    """Fetch author names for a paper, formatted with Material Icons."""
    # Validate conn
    if not hasattr(conn, 'session'):
        return "Database error: Invalid connection"
    
    try:
        with conn.session as session:
            query = text("""
                SELECT a.name
                FROM authors a
                JOIN paper_authors pa ON a.author_id = pa.author_id
                WHERE pa.paper_id = :paper_id
                ORDER BY pa.author_position IS NULL, pa.author_position ASC
            """)
            results = session.execute(query, {'paper_id': paper_id}).fetchall()
            author_names = [result.name for result in results]
            if author_names:
                return ", ".join(
                    f"""<span class="material-symbols-rounded" style="vertical-align: middle; font-size:12px;">person</span> {name}"""
                    for name in author_names
                )
            return "No authors"
    except Exception as e:
        return f"Database error: {str(e)}"

def format_date(date):
    return date.strftime('%Y-%m-%d') if pd.notnull(date) else 'N/A'

def format_review(review_done):
    return 'Completed' if review_done else 'Pending'

def format_payment(row, emi_data=None):
    
    # If row is a single value (e.g., payment_amount), treat it as such
    if isinstance(row, (int, float)):
        payment_amount = row
        # Use emi_data if provided, otherwise assume no EMI payments
        if emi_data is None:
            emi_data = {"emi_1_amount": 0, "emi_2_amount": 0, "emi_3_amount": 0}
    elif isinstance(row, (dict, pd.Series)):
        # Convert to dict if row is a Series
        row = row.to_dict() if isinstance(row, pd.Series) else row
        payment_amount = row.get("payment_amount", 0)
        emi_data = {
            "emi_1_amount": row.get("emi_1_amount", 0),
            "emi_2_amount": row.get("emi_2_amount", 0),
            "emi_3_amount": row.get("emi_3_amount", 0)
        }
    else:
        return "Invalid row format"

    # Check if payment_amount is valid
    if pd.notnull(payment_amount) and payment_amount > 0:
        total_paid = sum(
            amount for amount in [
                emi_data.get("emi_1_amount", 0),
                emi_data.get("emi_2_amount", 0),
                emi_data.get("emi_3_amount", 0)
            ] if pd.notnull(amount)
        )
        
        if total_paid >= payment_amount:
            return "No dues"
        else:
            remaining = payment_amount - total_paid
            return f"₹{int(remaining)} Due"
    return "Pending"


def format_status(status, status_type):
    if status_type == "review":
        badge_class = "badge-completed" if status == "Completed" else "badge-pending"
    elif status_type == "acceptance":
        issue_mapping = {
            "Accepted": "badge-accepted",
            "Rejected": "badge-rejected",
            "Pending": "badge-pending",
            "In Review": "badge-in-review",
            "Excess Plagiarism": "badge-excess-plagiarism",
            "Excess AI": "badge-excess-plagiarism",
            "Technical Incorrect": "badge-excess-plagiarism",
            "Grammatical Incorrect": "badge-excess-plagiarism",
            "References Incorrect": "badge-excess-plagiarism"
        }
        badge_class = issue_mapping.get(status, "badge-pending")
    else:  # payment or unknown
        if status == "No dues":
            badge_class = "badge-paid"
        elif status == "Pending" or status == "Invalid row format":
            badge_class = "badge-pending"
        else:  # Due amount
            badge_class = "badge-due"

    return f'<span class="badge {badge_class}">{status}</span>'

########################################################################################################################
##################################--------------- Add New Paper ----------------------------######################
#######################################################################################################################


@st.dialog("Add New Paper", width="large")
def add_paper_dialog(conn):
    with st.container(border=True):
        # Publication ID and Title in one row
        col1, col2 = st.columns([0.7, 2])
        with col1:
            publication_id = st.text_input("Publication ID", value="", placeholder="Unique ID", key="publication_id")
        with col2:
            paper_title = st.text_input("Paper Title", value="", placeholder="Enter title", key="paper_title")

        # Receiving Date and Paper Source in one row
        col3, col4 = st.columns(2)
        with col3:
            receiving_date = st.date_input(
                "Receiving Date",
                value=datetime.now(),
                key="receiving_date"
            )
        with col4:
            paper_source = st.selectbox(
                "Paper Source",
                options=["Google", "Justdial", "Indiamart", 
                         "Website", "WhatsApp", "College Visit",
                         "Office Visit", "Social Media", "Call", "Ads"],
                index=0,
                placeholder="Select source",
                key="paper_source"
            )

        # Volume and Issue in one row
        col5, col6 = st.columns(2)
        with col5:
            volume = st.number_input(
                "Volume",
                min_value=0,
                step=1,
                value=0,
                format="%d",
                key="volume"
            )
        with col6:
            issue = st.text_input("Issue", value="", placeholder="Enter issue", key="issue")

        # Publishing Type with st.pills
        publishing_type = st.radio(
            "Publishing Type",
            options=["Publishing Only", "Writing + Publishing"],
            horizontal=True,
        )

        if st.button("Add Paper", key="add_paper", use_container_width=True):
            # Validate required fields
            if not paper_title or not publishing_type:
                st.error("Paper Title and Publishing Type are required.")
                return

            try:
                with conn.session as session:
                    query = text("""
                        INSERT INTO papers (
                            publication_id, paper_title, receiving_date, paper_source, 
                            volume, issue, publishing_type
                        )
                        VALUES (
                            :publication_id, :paper_title, :receiving_date, :paper_source, 
                            :volume, :issue, :publishing_type
                        )
                    """)
                    session.execute(query, {
                        'publication_id': publication_id if publication_id else None,
                        'paper_title': paper_title,
                        'receiving_date': receiving_date,
                        'paper_source': paper_source if paper_source else None,
                        'volume': volume if volume > 0 else None,
                        'issue': issue if issue else None,
                        'publishing_type': publishing_type
                    })
                    session.commit()
                st.success("Paper added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding paper: {e}")


########################################################################################################################
##################################--------------- Edit Author Data ----------------------------######################
#######################################################################################################################


@st.dialog("Edit or Delete Author")
def edit_delete_author_dialog(conn):
    # Fetch all authors for the dropdown
    try:
        with conn.session as session:
            query = text("SELECT author_id, name FROM authors ORDER BY name")
            authors = session.execute(query).fetchall()
            author_options = {f"{row.name} (ID: {row.author_id})": row.author_id for row in authors}
    except Exception as e:
        st.error(f"Error fetching authors: {e}")
        return

    if not author_options:
        st.warning("No authors found in the database.")
        return

    with st.container(border=True):
        # Author selection dropdown
        selected_author = st.selectbox(
            "Select Author",
            options=list(author_options.keys()),
            key="selected_author"
        )
        author_id = author_options[selected_author]

        # Fetch selected author's details
        try:
            with conn.session as session:
                query = text("""
                    SELECT name, email, phone, affiliation 
                    FROM authors 
                    WHERE author_id = :author_id
                """)
                author = session.execute(query, {'author_id': author_id}).fetchone()
                if not author:
                    st.error("Author not found.")
                    return
        except Exception as e:
            st.error(f"Error fetching author details: {e}")
            return

        # Input fields for editing
        name = st.text_input("Name", value=author.name, placeholder="Enter name", key="author_name")
        email = st.text_input("Email", value=author.email or "", placeholder="Enter email", key="author_email")
        phone = st.text_input("Phone", value=author.phone or "", placeholder="Enter phone", key="author_phone")
        affiliation = st.text_input(
            "Affiliation", 
            value=author.affiliation or "", 
            placeholder="Enter affiliation", 
            key="author_affiliation"
        )

        # Create columns for buttons
        col1, col2 = st.columns(2)
        
        with col1:
            save_clicked = st.button("Save Changes", key="save_author", use_container_width=True)
            
        with col2:
            delete_clicked = st.button("Delete Author", key="delete_author", use_container_width=True)

        # Handle Save functionality
        if save_clicked:
            # Validate required fields
            if not name:
                st.error("Name is required.")
                return

            # Check for duplicate email (excluding current author)
            if email:
                try:
                    with conn.session as session:
                        query = text("""
                            SELECT COUNT(*) 
                            FROM authors 
                            WHERE email = :email AND author_id != :author_id
                        """)
                        result = session.execute(query, {'email': email, 'author_id': author_id}).scalar()
                        if result > 0:
                            st.error("Email already exists. Please use a unique email.")
                            return
                except Exception as e:
                    st.error(f"Error checking email: {e}")
                    return

            # Update author details
            try:
                with conn.session as session:
                    query = text("""
                        UPDATE authors 
                        SET name = :name, email = :email, phone = :phone, affiliation = :affiliation
                        WHERE author_id = :author_id
                    """)
                    session.execute(query, {
                        'name': name,
                        'email': email if email else None,
                        'phone': phone if phone else None,
                        'affiliation': affiliation if affiliation else None,
                        'author_id': author_id
                    })
                    session.commit()
                st.success("Author details updated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating author: {e}")
                return

        # Handle Delete functionality
        if delete_clicked:
            # Fetch associated papers
            try:
                with conn.session as session:
                    query = text("""
                        SELECT p.paper_id, p.paper_title
                        FROM papers p
                        JOIN paper_authors pa ON p.paper_id = pa.paper_id
                        WHERE pa.author_id = :author_id
                    """)
                    papers = session.execute(query, {'author_id': author_id}).fetchall()
                    
                    if papers:
                        st.warning("This author is associated with the following papers:")
                        for paper in papers:
                            st.write(f"- {paper.paper_title} (ID: {paper.paper_id})")
                        
                        # Confirmation for deletion
                        confirm_delete = st.checkbox("Confirm deletion (this will remove the author from all associated papers)")
                        if confirm_delete:
                            if st.button("Proceed with Deletion", key="confirm_delete"):
                                try:
                                    # Delete from paper_authors first
                                    query = text("DELETE FROM paper_authors WHERE author_id = :author_id")
                                    session.execute(query, {'author_id': author_id})
                                    
                                    # Delete from authors
                                    query = text("DELETE FROM authors WHERE author_id = :author_id")
                                    session.execute(query, {'author_id': author_id})
                                    
                                    session.commit()
                                    st.success("Author deleted successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting author: {e}")
                    else:
                        # No associated papers, proceed with deletion
                        if st.checkbox("Confirm deletion (no associated papers found)"):
                            if st.button("Proceed with Deletion", key="confirm_delete"):
                                try:
                                    # Delete from authors
                                    query = text("DELETE FROM authors WHERE author_id = :author_id")
                                    session.execute(query, {'author_id': author_id})
                                    session.commit()
                                    st.success("Author deleted successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting author: {e}")
            except Exception as e:
                st.error(f"Error fetching associated papers: {e}")


########################################################################################################################
##################################--------------- Edit Payment Details ----------------------------######################
#######################################################################################################################


@st.dialog("Update Payment")
def payment_dialog(paper_id, conn):

    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"<h3 style='color:#4CAF50;'>Paper ID: {paper_id}</h3>", 
                    unsafe_allow_html=True)
    with col2:
        if st.button(":material/refresh: Refresh", key="refresh_price", type="tertiary"):
            st.cache_data.clear()

    # Initialize session state for EMI visibility specific to paper_id
    show_emi_2_key = f"show_emi_2_{paper_id}"
    show_emi_3_key = f"show_emi_3_{paper_id}"
    if show_emi_2_key not in st.session_state:
        st.session_state[show_emi_2_key] = False
    if show_emi_3_key not in st.session_state:
        st.session_state[show_emi_3_key] = False

    # Fetch current payment data for the paper
    try:
        with conn.session as session:
            query = text("""
                SELECT payment_amount, emi_1_amount, emi_1_date, 
                       emi_2_amount, emi_2_date, emi_3_amount, emi_3_date 
                FROM papers WHERE paper_id = :paper_id
            """)
            result = session.execute(query, {'paper_id': paper_id}).fetchone()
            current_payment_amount = result.payment_amount if result else 0
            emi_1_amount = result.emi_1_amount if result and result.emi_1_amount else 0
            emi_1_date = result.emi_1_date if result and result.emi_1_date else None
            emi_2_amount = result.emi_2_amount if result and result.emi_2_amount else 0
            emi_2_date = result.emi_2_date if result and result.emi_2_date else None
            emi_3_amount = result.emi_3_amount if result and result.emi_3_amount else 0
            emi_3_date = result.emi_3_date if result and result.emi_3_date else None
    except Exception as e:
        st.error(f"Error fetching payment data: {e}")
        current_payment_amount = 0
        emi_1_amount = emi_2_amount = emi_3_amount = 0
        emi_1_date = emi_2_date = emi_3_date = None

    # Initialize session state based on existing EMI data
    if emi_1_amount > 0:
        st.session_state[show_emi_2_key] = True
    if emi_2_amount > 0:
        st.session_state[show_emi_3_key] = True

    # Input fields for total payment and EMI details
    payment_amount = st.number_input(
        "Total Payment Amount (₹)",
        min_value=0,
        step=1,
        format="%d",
        value=int(current_payment_amount) if current_payment_amount else 0,
        key=f"total_payment_{paper_id}"
    )

    st.subheader("EMI Details")
    col1, col2 = st.columns(2)
    
    with col1:
        emi_1_amount = st.number_input(
            "EMI 1 Amount (₹)",
            min_value=0,
            step=1,
            format="%d",
            value=int(emi_1_amount),
            key=f"emi_1_amount_{paper_id}"
        )
        if st.session_state[show_emi_2_key]:
            emi_2_amount = st.number_input(
                "EMI 2 Amount (₹)",
                min_value=0,
                step=1,
                format="%d",
                value=int(emi_2_amount),
                key=f"emi_2_amount_{paper_id}"
            )
        else:
            emi_2_amount = 0
        if st.session_state[show_emi_3_key]:
            emi_3_amount = st.number_input(
                "EMI 3 Amount (₹)",
                min_value=0,
                step=1,
                format="%d",
                value=int(emi_3_amount),
                key=f"emi_3_amount_{paper_id}"
            )
        else:
            emi_3_amount = 0
    
    with col2:
        emi_1_date = st.date_input(
            "EMI 1 Date",
            value=emi_1_date,
            key=f"emi_1_date_{paper_id}",
            min_value=None
        )
        if st.session_state[show_emi_2_key]:
            emi_2_date = st.date_input(
                "EMI 2 Date",
                value=emi_2_date,
                key=f"emi_2_date_{paper_id}",
                min_value=None
            )
        else:
            emi_2_date = None
        if st.session_state[show_emi_3_key]:
            emi_3_date = st.date_input(
                "EMI 3 Date",
                value=emi_3_date,
                key=f"emi_3_date_{paper_id}",
                min_value=None
            )
        else:
            emi_3_date = None

    # Validate EMI amounts and dates
    total_emi = emi_1_amount + emi_2_amount + emi_3_amount
    if total_emi > payment_amount and payment_amount > 0:
        st.warning("Sum of EMI amounts cannot exceed Total Payment Amount")

    # Check if dates are provided for non-zero EMI amounts
    date_errors = []
    if emi_1_amount > 0 and emi_1_date is None:
        date_errors.append("EMI 1 Date is required when EMI 1 Amount is provided")
    if emi_2_amount > 0 and emi_2_date is None:
        date_errors.append("EMI 2 Date is required when EMI 2 Amount is provided")
    if emi_3_amount > 0 and emi_3_date is None:
        date_errors.append("EMI 3 Date is required when EMI 3 Amount is provided")

    if st.button("Submit Payment", key=f"submit_payment_{paper_id}"):
        # Prevent saving if EMI sum exceeds total payment
        if total_emi > payment_amount and payment_amount > 0:
            st.error("Sum of EMI amounts cannot exceed Total Payment Amount. Please adjust EMI amounts.")
            return

        # Prevent saving if any non-zero EMI amount lacks a date
        if date_errors:
            st.error("Please provide date.")
            return

        try:
            with st.spinner("Updating payment details..."):
                sleep(1)
                with conn.session as session:
                    query = text("""
                        UPDATE papers 
                        SET payment_amount = :payment_amount,
                            emi_1_amount = :emi_1_amount,
                            emi_1_date = :emi_1_date,
                            emi_2_amount = :emi_2_amount,
                            emi_2_date = :emi_2_date,
                            emi_3_amount = :emi_3_amount,
                            emi_3_date = :emi_3_date
                        WHERE paper_id = :paper_id
                    """)
                    session.execute(query, {
                        'payment_amount': payment_amount,
                        'emi_1_amount': emi_1_amount,
                        'emi_1_date': emi_1_date,
                        'emi_2_amount': emi_2_amount,
                        'emi_2_date': emi_2_date,
                        'emi_3_amount': emi_3_amount,
                        'emi_3_date': emi_3_date,
                        'paper_id': paper_id
                    })
                    session.commit()
                st.success("Payment details updated successfully!")

                # Update session state for EMI visibility
                if emi_1_amount > 0:
                    st.session_state[show_emi_2_key] = True
                if emi_2_amount > 0:
                    st.session_state[show_emi_3_key] = True

                #st.rerun()
        except Exception as e:
            st.error(f"Error updating payment: {e}")


########################################################################################################################
##################################--------------- Edit Paper Basic Details ----------------------------######################
#######################################################################################################################


@st.dialog("✏️ Edit Paper Details", width="large")
def edit_paper_dialog(paper_id, conn):
    # Initialize session state for deletion confirmation
    if 'confirm_delete' not in st.session_state:
        st.session_state.confirm_delete = False

    # Fetch current paper data
    try:
        with conn.session as session:
            result = session.execute(text("""
                SELECT paper_id, paper_title, publication_id, paper_source, receiving_date, volume, issue 
                FROM papers 
                WHERE paper_id = :paper_id
            """), {'paper_id': paper_id}).fetchone()

            current_paper_id = result.paper_id if result else ""
            current_paper_publication_id = result.publication_id if result else ""
            current_paper_title = result.paper_title if result else ""
            current_paper_source = result.paper_source if result else "Google"
            current_receiving_date = result.receiving_date if result else datetime.now()
            current_volume = result.volume if result else ""
            current_issue = result.issue if result else ""

    except Exception as e:
        st.error(f"❌ Error fetching paper data: {e}")
        current_paper_id = current_paper_title = current_volume = current_issue = ""
        current_paper_source = "Google"
        current_receiving_date = datetime.now()

    # Header
    col1, col2 = st.columns([8, 1])
    with col1:
        st.markdown(
            f"<h4 style='color:#4CAF50; margin-bottom: 5px;'>{current_paper_id} : {current_paper_title}</h4>",
            unsafe_allow_html=True
        )
    with col2:
        if st.button(":material/refresh: Refresh", key="refresh_price", type="tertiary"):
            st.cache_data.clear()

    st.markdown("---")

    # Source options
    source_options = [
        "Google", "Justdial", "Indiamart", "Website", "WhatsApp",
        "College Visit", "Office Visit", "Social Media", "Call", "Ads"
    ]

    # Form Inputs in columns
    col1, col2 = st.columns(2)
    with col1:
        new_paper_publication_id = st.text_input("📑 Publication ID", value=current_paper_publication_id)
        paper_source = st.selectbox(
            "📌 Paper Source",
            options=source_options,
            index=source_options.index(current_paper_source) if current_paper_source in source_options else 0,
            key="paper_source_1"
        )
        volume = st.text_input("📚 Volume", value=current_volume)
    with col2:
        paper_title = st.text_input("📝 Paper Title", value=current_paper_title)
        receiving_date = st.date_input("📅 Receiving Date", value=current_receiving_date)
        issue = st.text_input("🧾 Issue", value=current_issue)

    # Create columns for buttons
    col1, col2 = st.columns(2)
    
    with col1:
        # Submit button
        if st.button("✅ Submit Changes"):
            try:
                with conn.session as session:
                    session.execute(text("""
                        UPDATE papers 
                        SET publication_id = :new_paper_publication_id,
                            paper_title = :paper_title,
                            paper_source = :paper_source,
                            receiving_date = :receiving_date,
                            volume = :volume,
                            issue = :issue
                        WHERE paper_id = :paper_id
                    """), {
                        'new_paper_publication_id': new_paper_publication_id,
                        'paper_title': paper_title,
                        'paper_source': paper_source,
                        'receiving_date': receiving_date,
                        'volume': volume,
                        'issue': issue,
                        'paper_id': paper_id
                    })
                    session.commit()
                st.success("✅ Paper details updated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error updating paper: {e}")

    with col2:
        # Delete button (only visible to admins)
        if user_role == 'admin':
            if st.button("🗑️ Delete Paper", key="delete_paper"):
                st.session_state.confirm_delete = True

            if st.session_state.confirm_delete:
                st.warning("Are you sure you want to delete this paper? This action cannot be undone.")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("Proceed with Deletion", key="confirm_delete_paper"):
                        try:
                            with conn.session as session:
                                # Delete from paper_authors first
                                result = session.execute(text("""
                                    DELETE FROM paper_authors 
                                    WHERE paper_id = :paper_id
                                """), {'paper_id': paper_id})
                                deleted_authors = result.rowcount
                                
                                # Delete from papers
                                result = session.execute(text("""
                                    DELETE FROM papers 
                                    WHERE paper_id = :paper_id
                                """), {'paper_id': paper_id})
                                deleted_papers = result.rowcount
                                
                                session.commit()
                            st.success(f"✅ Paper deleted successfully! (Removed {deleted_authors} author associations and {deleted_papers} paper record)")
                            st.session_state.confirm_delete = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error deleting paper: {e}")
                            st.session_state.confirm_delete = False
                with col_cancel:
                    if st.button("Cancel", key="cancel_delete"):
                        st.session_state.confirm_delete = False
                        st.rerun()


########################################################################################################################
##################################--------------- Edit Author Details ----------------------------######################
########################################################################################################################


@st.dialog("Edit Author Details", width="large")
def edit_author_dialog(paper_id, conn):
    # --- Custom CSS for Compact and Modern Styling ---
    st.markdown(
        """
        <style>
        .author-card { 
            background-color: #ffffff; 
            border: 1px solid #e0e0e0; 
            border-radius: 8px; 
            padding: 12px; 
            margin-bottom: 12px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
        }
        .author-grid { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 10px; 
            font-size: 13px; 
        }
        .author-grid div { 
            display: flex; 
            align-items: center; 
        }
        .author-grid strong { 
            width: 80px; 
            color: #424242; 
        }
        .checklist-container { 
            display: flex; 
            flex-wrap: wrap; 
            gap: 10px; 
            margin-top: 10px; 
        }
        .checklist-container .stCheckbox { 
            margin-right: 20px; 
            margin-bottom: 5px; 
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # --- Fetch Paper Title and Publishing Type ---
    try:
        with conn.session as session:
            query = text("SELECT paper_title, publishing_type FROM papers WHERE paper_id = :paper_id")
            result = session.execute(query, {'paper_id': paper_id}).fetchone()
            paper_title = result.paper_title if result else "Unknown Title"
            publishing_type = result.publishing_type if result else None
    except Exception as e:
        st.error(f"Error fetching paper data: {e}")
        paper_title = "Unknown Title"
        publishing_type = None

    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(f"<h3 style='color:#4CAF50;'>{paper_id} : {paper_title}</h3>", 
                    unsafe_allow_html=True)
    with col2:
        if st.button(":material/refresh: Refresh", key="refresh_price", type="tertiary"):
            st.cache_data.clear()

    # --- Fetch All Authors ---
    try:
        with conn.session as session:
            query = text("""
                SELECT a.author_id, a.name, a.email, a.phone, a.affiliation, pa.author_position,
                       pa.written_paper_confirmation_received, pa.paper_receiving_confirmation_sent,
                       pa.paper_review_confirmation_sent, pa.certificate_ready, pa.certificate_sent,
                       pa.publishing_confirmation_sent
                FROM authors a
                JOIN paper_authors pa ON a.author_id = pa.author_id
                WHERE pa.paper_id = :paper_id
                ORDER BY pa.author_position IS NULL, pa.author_position ASC
            """)
            results = session.execute(query, {'paper_id': paper_id}).fetchall()
            authors = [
                {
                    'author_id': row.author_id,
                    'name': row.name or "N/A",
                    'email': row.email or "N/A",
                    'phone': row.phone or "N/A",
                    'affiliation': row.affiliation or "N/A",
                    'author_position': row.author_position or None,
                    'written_paper_confirmation_received': row.written_paper_confirmation_received or False,
                    'paper_receiving_confirmation_sent': row.paper_receiving_confirmation_sent or False,
                    'paper_review_confirmation_sent': row.paper_review_confirmation_sent or False,
                    'certificate_ready': row.certificate_ready or False,
                    'certificate_sent': row.certificate_sent or False,
                    'publishing_confirmation_sent': row.publishing_confirmation_sent or False
                }
                for row in results
            ]
    except Exception as e:
        st.error(f"Error fetching author data: {e}")
        authors = []

    if not authors:
        st.info("No authors assigned to this paper yet.", icon="ℹ️")
    else:
        with st.container():
            for author in authors:
                with st.container():
                    if author['author_position'] == 1:
                        with st.expander(f"{author['name']} (ID: {author['author_id']})", expanded=True):
                            st.markdown(
                                f"""
                                <div class="author-card">
                                    <div class="author-grid">
                                        <div><strong>Name:</strong> {author['name']}</div>
                                        <div><strong>Email:</strong> {author['email']}</div>
                                        <div><strong>Phone:</strong> {author['phone']}</div>
                                        <div><strong>Position:</strong> {author['author_position'] or 'None'}</div>
                                        <div style="grid-column: span 2;"><strong>Affiliation:</strong> {author['affiliation']}</div>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                            with st.form(key=f"checklist_form_{author['author_id']}", border=False):
                                checklist_values = {}
                                
                                # Prepare a list of checkbox labels and keys based on publishing type
                                checklist_items = []

                                if publishing_type == "Writing + Publishing":
                                    checklist_items.append(("Written Paper Confirmation Received", 'written_paper_confirmation_received'))

                                elif publishing_type == "Publishing Only":
                                    checklist_items.append(("Paper Receiving Confirmation Sent", 'paper_receiving_confirmation_sent'))

                                checklist_items += [
                                    ("Paper Review Confirmation Sent", 'paper_review_confirmation_sent'),
                                    ("Certificate Ready", 'certificate_ready'),
                                    ("Certificate Sent", 'certificate_sent'),
                                    ("Publishing Confirmation Sent", 'publishing_confirmation_sent')
                                ]

                                # Render checkboxes in rows of 2 columns
                                for i in range(0, len(checklist_items), 2):
                                    cols = st.columns(2, gap="small", vertical_alignment="top")
                                    for j in range(2):
                                        if i + j < len(checklist_items):
                                            label, key = checklist_items[i + j]
                                            db_value = author.get(key, False)
                                            checklist_values[key] = cols[j].checkbox(
                                                label, value=db_value, key=f"{key}_{author['author_id']}"
                                            )

                                # Submit Button
                                if st.form_submit_button("Update", type="primary", use_container_width=False):
                                    try:
                                        with conn.session as session:
                                            query = text("""
                                                UPDATE paper_authors
                                                SET written_paper_confirmation_received = :written_paper_confirmation_received,
                                                    paper_receiving_confirmation_sent = :paper_receiving_confirmation_sent,
                                                    paper_review_confirmation_sent = :paper_review_confirmation_sent,
                                                    certificate_ready = :certificate_ready,
                                                    certificate_sent = :certificate_sent,
                                                    publishing_confirmation_sent = :publishing_confirmation_sent
                                                WHERE paper_id = :paper_id AND author_id = :author_id
                                            """)
                                            session.execute(query, {
                                                'written_paper_confirmation_received': checklist_values.get('written_paper_confirmation_received', False),
                                                'paper_receiving_confirmation_sent': checklist_values.get('paper_receiving_confirmation_sent', False),
                                                'paper_review_confirmation_sent': checklist_values.get('paper_review_confirmation_sent', False),
                                                'certificate_ready': checklist_values.get('certificate_ready', False),
                                                'certificate_sent': checklist_values.get('certificate_sent', False),
                                                'publishing_confirmation_sent': checklist_values.get('publishing_confirmation_sent', False),
                                                'paper_id': paper_id,
                                                'author_id': author['author_id']
                                            })
                                            session.commit()
                                        st.success("Checklist updated!", icon="✅")
                                    except Exception as e:
                                        st.error(f"Error updating checklist: {e}")

                    else:
                        st.markdown(
                            f"""
                            <div class="author-card">
                                <strong style="font-size:14px;color:#2e7d32;">
                                    {author['name']} (ID: {author['author_id']})
                                </strong>
                                <div class="author-grid">
                                    <div><strong>Name:</strong> {author['name']}</div>
                                    <div><strong>Email:</strong> {author['email']}</div>
                                    <div><strong>Phone:</strong> {author['phone']}</div>
                                    <div><strong>Position:</strong> {author['author_position'] or 'None'}</div>
                                    <div style="grid-column: span 2;"><strong>Affiliation:</strong> {author['affiliation']}</div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

    # --- Helper Function: Check for Duplicate Author Position ---
    def is_author_position_duplicate(paper_id, author_position, exclude_author_id=None):
        try:
            with conn.session as session:
                query = text("""
                    SELECT COUNT(*)
                    FROM paper_authors
                    WHERE paper_id = :paper_id
                    AND author_position = :author_position
                    AND (:exclude_author_id IS NULL OR author_id != :exclude_author_id)
                """)
                result = session.execute(query, {
                    'paper_id': paper_id,
                    'author_position': author_position,
                    'exclude_author_id': exclude_author_id
                }).scalar()
                return result > 0
        except Exception as e:
            st.error(f"Error checking author position: {e}")
            return False

    # --- Helper Function: Fetch All Author Names for Selectbox Search ---
    def get_author_suggestions():
        try:
            with conn.session as session:
                query = text("SELECT author_id, name, email, phone, affiliation FROM authors ORDER BY name")
                results = session.execute(query).fetchall()
                return [
                    {
                        'author_id': row.author_id,
                        'name': row.name,
                        'email': row.email or "",
                        'phone': row.phone or "",
                        'affiliation': row.affiliation or ""
                    }
                    for row in results
                ]
        except Exception as e:
            st.error(f"Error fetching authors: {e}")
            return []

    # --- Add New Author Section ---
    st.write("### Add New Author")
    with st.container():
        with st.expander("Add Author", expanded=False):
            # Store form state in session_state to manage reset
            if 'author_form_reset' not in st.session_state:
                st.session_state.author_form_reset = False
                
            author_suggestions = get_author_suggestions()
            # Modified to show author ID in selectbox
            author_names = [""] + [f"{author['name']} (ID: {author['author_id']})" for author in author_suggestions]
            selected_author_name = st.selectbox(
                "Search Author by Name",
                options=author_names,
                index=0,
                placeholder="Select or type to search",
                key="author_search"
            )

            selected_author = None
            if selected_author_name:
                # Extract name from format "Name (ID: X)"
                name_part = selected_author_name.split(' (ID:')[0]
                selected_author = next((a for a in author_suggestions if a['name'] == name_part), None)

            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(
                    "Author Name",
                    value=selected_author['name'] if selected_author else "",
                    key=f"new_name_{st.session_state.get('author_form_reset', False)}",
                    placeholder="Enter author name"
                )
                email = st.text_input(
                    "Author Email",
                    value=selected_author['email'] if selected_author else "",
                    key=f"new_email_{st.session_state.get('author_form_reset', False)}",
                    placeholder="Enter email address"
                )
            with col2:
                phone = st.text_input(
                    "Author Phone",
                    value=selected_author['phone'] if selected_author else "",
                    key=f"new_phone_{st.session_state.get('author_form_reset', False)}",
                    placeholder="Enter phone number"
                )
                author_position = st.number_input(
                    "Author Position",
                    min_value=1,
                    step=1,
                    value=1,
                    format="%d",
                    key=f"new_position_{st.session_state.get('author_form_reset', False)}"
                )
            affiliation = st.text_area(
                "Author Affiliation",
                value=selected_author['affiliation'] if selected_author else "",
                key=f"new_affiliation_{st.session_state.get('author_form_reset', False)}",
                placeholder="Enter affiliation"
            )

            if st.button("Add Author", key="add_author", type="primary", use_container_width=True):
                if not name:
                    st.error("Name is required.")
                    return
                if is_author_position_duplicate(paper_id, author_position):
                    st.error("This author position is already taken for this paper.")
                    return

                try:
                    with conn.session as session:
                        if selected_author:
                            # Update existing author if fields changed
                            author_query = text("""
                                UPDATE authors 
                                SET name = :name, email = :email, phone = :phone, affiliation = :affiliation
                                WHERE author_id = :author_id
                            """)
                            session.execute(author_query, {
                                'name': name,
                                'email': email if email else None,
                                'phone': phone if phone else None,
                                'affiliation': affiliation if affiliation else None,
                                'author_id': selected_author['author_id']
                            })

                            # Check if author is already linked to paper
                            check_duplicate_paper_author_query = text("""
                                SELECT COUNT(*) FROM paper_authors
                                WHERE paper_id = :paper_id AND author_id = :author_id
                            """)
                            if session.execute(check_duplicate_paper_author_query, {
                                'paper_id': paper_id,
                                'author_id': selected_author['author_id']
                            }).scalar() > 0:
                                st.error("This author is already linked to this paper.")
                                return
                            
                            # Add to paper_authors
                            paper_author_query = text("""
                                INSERT INTO paper_authors (paper_id, author_id, author_position)
                                VALUES (:paper_id, :author_id, :author_position)
                            """)
                            session.execute(paper_author_query, {
                                'paper_id': paper_id,
                                'author_id': selected_author['author_id'],
                                'author_position': author_position
                            })
                            session.commit()
                            st.success("Existing author updated and added to paper!", icon="✅")
                        else:
                            # Create new author
                            author_query = text("""
                                INSERT INTO authors (name, email, phone, affiliation)
                                VALUES (:name, :email, :phone, :affiliation)
                            """)
                            result = session.execute(author_query, {
                                'name': name,
                                'email': email if email else None,
                                'phone': phone if phone else None,
                                'affiliation': affiliation if affiliation else None
                            })
                            session.flush()
                            new_author_id = session.execute(text("SELECT LAST_INSERT_ID()")).scalar()

                            # Add to paper_authors
                            paper_author_query = text("""
                                INSERT INTO paper_authors (paper_id, author_id, author_position)
                                VALUES (:paper_id, :author_id, :author_position)
                            """)
                            session.execute(paper_author_query, {
                                'paper_id': paper_id,
                                'author_id': new_author_id,
                                'author_position': author_position
                            })
                            session.commit()
                            st.success("New author added!", icon="✅")
                        
                        # Reset form
                        st.session_state.author_form_reset = not st.session_state.author_form_reset
                        st.rerun()

                except Exception as e:
                    st.error(f"Error adding author: {e}")

paper_status = ['Accepted','Rejected','Pending','In Review','Excess Plagiarism',
                'Excess AI','Technical Incorrect','Grammatical Incorrect','References Incorrect']


########################################################################################################################
##################################--------------- Edit Paper Status ----------------------------######################
#######################################################################################################################

@st.dialog("Edit Paper Status")
def edit_paper_status_dialog(paper_id, conn):
    # Fetch current paper data
    try:
        with conn.session as session:
            query = text("""
                SELECT 
                    writing_by, writing_date,
                    reviewer_name, review_date, plagiarism, ai_plagiarism, acceptance,
                    formatting_by, formatting_date,
                    paper_uploading_date, paper_doi, paper_url,
                    publishing_type
                FROM papers
                WHERE paper_id = :paper_id
            """)
            result = session.execute(query, {'paper_id': paper_id}).fetchone()
            current_writing_by = result.writing_by or "" if result else ""
            current_writing_date = result.writing_date if result else None
            current_reviewer_name = result.reviewer_name or "" if result else ""
            current_review_date = result.review_date if result else None
            current_plagiarism = result.plagiarism or "" if result else ""
            current_ai_plagiarism = result.ai_plagiarism or "" if result else ""
            current_acceptance = result.acceptance or "Pending" if result else "Pending"
            current_formatting_by = result.formatting_by or "" if result else ""
            current_formatting_date = result.formatting_date if result else None
            current_paper_uploading_date = result.paper_uploading_date if result else None
            current_paper_doi = result.paper_doi or "" if result else ""
            current_paper_url = result.paper_url or "" if result else ""
            current_publishing_type = result.publishing_type or "" if result else ""
    except Exception as e:
        st.error(f"Error fetching paper data: {e}")
        current_writing_by = ""
        current_writing_date = None
        current_reviewer_name = ""
        current_review_date = None
        current_plagiarism = ""
        current_ai_plagiarism = ""
        current_acceptance = "Pending"
        current_formatting_by = ""
        current_formatting_date = None
        current_paper_uploading_date = None
        current_paper_doi = ""
        current_paper_url = ""
        current_publishing_type = ""

    # Define tabs, excluding Writing if publishing_type is "Publishing"
    tab_names = ["Review", "Formatting", "Publish"]
    if current_publishing_type != "Publishing Only":
        tab_names.insert(0, "Writing")
    tabs = st.tabs(tab_names)

    # Writing Section (if not hidden)
    if current_publishing_type != "Publishing Only":
        with tabs[tab_names.index("Writing")]:
            writing_by = st.text_input("Written By", value=current_writing_by, key="writing_by")
            writing_date = st.date_input(
                "Writing Date",
                value=current_writing_date if current_writing_date else datetime.now(),
                key="writing_date"
            )
            if st.button("Update Writing Details", key="update_writing"):
                try:
                    with conn.session as session:
                        query = text("""
                            UPDATE papers 
                            SET writing_by = :writing_by,
                                writing_date = :writing_date
                            WHERE paper_id = :paper_id
                        """)
                        session.execute(query, {
                            'writing_by': writing_by,
                            'writing_date': writing_date,
                            'paper_id': paper_id
                        })
                        session.commit()
                    st.success("Writing details updated successfully!")
                except Exception as e:
                    st.error(f"Error updating writing details: {e}")

    # Review Section
    with tabs[tab_names.index("Review")]:
        reviewer_name = st.text_input("Reviewer Name", value=current_reviewer_name, key="reviewer_name")
        review_date = st.date_input(
            "Review Date",
            value=current_review_date if current_review_date else datetime.now(),
            key="review_date"
        )
        plagiarism = st.text_input("Plagiarism (%)", value=current_plagiarism, key="plagiarism")
        ai_plagiarism = st.text_input("AI Plagiarism (%)", value=current_ai_plagiarism, key="ai_plagiarism")
        acceptance = st.selectbox(
            "Acceptance Status",
            options=paper_status,
            index = paper_status.index(current_acceptance) if current_acceptance in paper_status else 2,
            key="acceptance"
        )
        if st.button("Update Review Details", key="update_review"):
            try:
                with conn.session as session:
                    query = text("""
                        UPDATE papers 
                        SET reviewer_name = :reviewer_name,
                            review_date = :review_date,
                            plagiarism = :plagiarism,
                            ai_plagiarism = :ai_plagiarism,
                            acceptance = :acceptance,
                            review_done = 1
                        WHERE paper_id = :paper_id
                    """)
                    session.execute(query, {
                        'reviewer_name': reviewer_name,
                        'review_date': review_date,
                        'plagiarism': plagiarism,
                        'ai_plagiarism': ai_plagiarism,
                        'acceptance': acceptance,
                        'paper_id': paper_id
                    })
                    session.commit()
                st.success("Review details updated successfully!")
                st.rerun()  # Refresh the page to reflect changes
            except Exception as e:
                st.error(f"Error updating review details: {e}")

    # Formatting Section
    with tabs[tab_names.index("Formatting")]:
        formatting_by = st.text_input("Formatted By", value=current_formatting_by, key="formatting_by")
        formatting_date = st.date_input(
            "Formatting Date",
            value=current_formatting_date if current_formatting_date else datetime.now(),
            key="formatting_date"
        )
        if st.button("Update Formatting Details", key="update_formatting"):
            try:
                with conn.session as session:
                    query = text("""
                        UPDATE papers 
                        SET formatting_by = :formatting_by,
                            formatting_date = :formatting_date
                        WHERE paper_id = :paper_id
                    """)
                    session.execute(query, {
                        'formatting_by': formatting_by,
                        'formatting_date': formatting_date,
                        'paper_id': paper_id
                    })
                    session.commit()
                st.success("Formatting details updated successfully!")
                st.rerun()  # Refresh the page to reflect changes
            except Exception as e:
                st.error(f"Error updating formatting details: {e}")

    # Publish Section
    with tabs[tab_names.index("Publish")]:
        paper_uploading_date = st.date_input(
            "Publish/Uploading Date",
            value=current_paper_uploading_date if current_paper_uploading_date else datetime.now(),
            key="paper_uploading_date"
        )
        paper_doi = st.text_input("Paper DOI", value=current_paper_doi, key="paper_doi")
        paper_url = st.text_input("Paper URL", value=current_paper_url, key="paper_url")
        if st.button("Update Publish Details", key="update_publish"):
            try:
                with conn.session as session:
                    query = text("""
                        UPDATE papers 
                        SET paper_uploading_date = :paper_uploading_date,
                            paper_doi = :paper_doi,
                            paper_url = :paper_url
                        WHERE paper_id = :paper_id
                    """)
                    session.execute(query, {
                        'paper_uploading_date': paper_uploading_date,
                        'paper_doi': paper_doi,
                        'paper_url': paper_url,
                        'paper_id': paper_id
                    })
                    session.commit()
                st.success("Publish details updated successfully!")
            except Exception as e:
                st.error(f"Error updating publish details: {e}")


########################################################################################################################
##################################--------------- Metric Expander ----------------------------######################
#######################################################################################################################

def metrics(df):
    with st.expander("📊 Metrics", expanded=False):
        col1, col2, col3, col4, col5, col6 = st.columns(6, gap="small")
        with col1:
            st.metric("Total Papers", len(df), delta=None, help="Total number of papers in the database.")
        with col2:
            st.metric("Total Published", len(df[df['paper_uploading_date'].notnull()]), 
                      delta=f"-{len(df[df['paper_uploading_date'].isnull()])} Not Published")
        with col3:
            st.metric("Accepted Papers", len(df[df['acceptance'] == 'Accepted']), 
                      delta=f"-{len(df[df['acceptance'] == 'Rejected'])} Rejected")
        with col4:
            st.metric("Review Pending", len(df[df['review_done'].isnull()]), 
                      delta=f"{len(df[df['review_done'].notnull()])} Done")
        with col5:
            st.metric("Formatting Pending", len(df[df['formatting_date'].isnull()]), 
                      delta=f"{len(df[df['formatting_date'].notnull()])} Done")
        with col6:
            st.metric("Payment Pending", len(df[df['payment_date'].isnull()]), 
                      delta=f"{len(df[df['payment_date'].notnull()])} Received")
        
        month_order = [
            "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"
        ]
        # Extract the latest year from receiving_date
        # Safely get the latest year
        latest_year = None
        if not df.empty and df['receiving_date'].notna().any():
            latest_year = int(df['receiving_date'].dt.year.max())
        
        # Monthly counts line chart
        monthly_counts = df.groupby(df['receiving_date'].dt.month).agg({
            'paper_id': 'nunique',
        }).reset_index()
        
        # Rename columns for clarity
        monthly_counts['Month'] = monthly_counts['receiving_date'].apply(lambda x: pd.to_datetime(f"{latest_year}-{int(x)}-01").strftime('%B'))
        monthly_counts = monthly_counts.rename(columns={'paper_id': 'Total Paper'})
        
        line_chart = alt.Chart(monthly_counts).mark_line(point=True).encode(
            x=alt.X('Month', title='Month', sort=month_order),
            y=alt.Y('Total Paper', title='Total Count'),
            color=alt.value("#5499de")  # Color for Total Papers line
        ).properties(
            width=600,
            height=400
        )
        # Add text labels on data points
        total_papers_charts = line_chart.mark_text(
            align='center',
            baseline='bottom',
            dy=-10
        ).encode(
            text='Total Paper:Q'
        )
        
        st.write(f"##### Total Papers in {latest_year}")
        #st.caption("Total Papers each month")
        st.altair_chart((line_chart + total_papers_charts), use_container_width=True)


########################################################################################################################
##################################--------------- All Filters Function ----------------------------######################
#######################################################################################################################


def all_filters(df):
    # Initialize session state for filters if it doesn't exist
    if 'filters' not in st.session_state:
        st.session_state.filters = {
            'year': None, 'month': None, 'pending_payment': False,
            'pending_review': False, 'acceptance': None, 'publishing_type': None,
            'volume': None, 'issue': None
        }

    # Callback function to reset filters
    def reset_all_filters():
        st.session_state.filters = {
            'year': None, 'month': None, 'pending_payment': False,
            'pending_review': False, 'acceptance': None, 'publishing_type': None,
            'volume': None, 'issue': None
        }
        st.session_state.search_input = ""
        st.session_state.year_pills = None
        st.session_state.month_pills = None
        st.session_state.payment_pills = None
        st.session_state.review_pills = None
        st.session_state.acceptance_pills = None
        st.session_state.publishing_pills = None
        st.session_state.volume_select = None
        st.session_state.issue_select = None
        if 'page' in st.session_state:
            st.session_state.page = 0

    # UI and Filter Logic
    col1, col2, col3 = st.columns([5, 3, 1], vertical_alignment="center")
    with col1:
        search_query = st.text_input(
            "Search by Paper ID or Title",
            placeholder="Search by Paper ID or Title",
            label_visibility="collapsed",
            key="search_input"
        )

    with col2:
        with st.popover("Filters & More", use_container_width=True):
            st.button(":material/cached: Reset Filters", key="reset_filters_button", 
                      on_click=reset_all_filters, use_container_width=True)
            
            # Organize filters into tabs
            tab1, tab2, tab3, tab4 = st.tabs(["Status", "Date", "Volume/Issue", "Edit Author"])

            with tab4:
                if st.button("Edit Author Details", key="edit_author", use_container_width=True):
                    edit_delete_author_dialog(conn)
            
            with tab2:
                # Date Filters
                years = sorted(df['receiving_date'].dt.year.dropna().astype(int).unique(), reverse=True)
                selected_year = st.pills("Filter by Year", options=[str(y) for y in years], key="year_pills")
                st.session_state.filters['year'] = selected_year

                if selected_year:
                    months = sorted(df[df['receiving_date'].dt.year == int(selected_year)]['receiving_date'].dt.strftime('%B').unique())
                    selected_month = st.pills("Filter by Month", options=months, key="month_pills")
                    st.session_state.filters['month'] = selected_month
                else:
                    st.session_state.filters['month'] = None

            with tab1:
                # Status Filters
                pending_payment = st.pills("Filter by Payment Status", options=["Pending Payment"], key="payment_pills")
                st.session_state.filters['pending_payment'] = bool(pending_payment)

                pending_review = st.pills("Filter by Review Status", options=["Pending Review"], key="review_pills")
                st.session_state.filters['pending_review'] = bool(pending_review)
                
                acceptance_options = ['Accepted', 'Rejected', 'Pending', 'In Review', 
                                    'Excess Plagiarism', 'Excess AI', 'Technical Incorrect', 
                                    'Grammatical Incorrect', 'References Incorrect']
                selected_acceptance = st.pills("Filter by Acceptance", options=acceptance_options, key="acceptance_pills")
                st.session_state.filters['acceptance'] = selected_acceptance

                publishing_types = ['Publishing Only', 'Writing + Publishing']
                selected_publishing_type = st.pills("Filter by Publishing Type", options=publishing_types, 
                                                    key="publishing_pills")
                st.session_state.filters['publishing_type'] = selected_publishing_type
            
            with tab3:
                # Volume and Issue Filters without Form
                volumes = sorted(df['volume'].dropna().astype(float).astype(int).unique())
                volume_options = [str(int(v)) for v in volumes]
                selected_volume = st.selectbox("Select Volume", options=[""] + volume_options, key="volume_select")
                
                # Populate issues based on selected volume
                issues = []
                if selected_volume:
                    try:
                        selected_volume_int = int(selected_volume)
                        issues = sorted(df[df['volume'].apply(lambda x: int(float(x)) if pd.notnull(x) else False) == selected_volume_int]['issue'].dropna().astype(str).unique())
                    except (ValueError, TypeError):
                        issues = []
                else:
                    issues = sorted(df['issue'].dropna().astype(str).unique())
                
                # Reset issue selection if volume changes
                if 'prev_volume' not in st.session_state:
                    st.session_state.prev_volume = None
                
                if selected_volume != st.session_state.prev_volume:
                    st.session_state.issue_select = None
                    st.session_state.filters['issue'] = None
                    st.session_state.prev_volume = selected_volume
                
                selected_issue = st.selectbox("Select Issue", options=[""] + issues, key="issue_select")
                
                # Update filters only if changed
                if st.session_state.filters['volume'] != selected_volume:
                    st.session_state.filters['volume'] = selected_volume if selected_volume else None
                    st.session_state.filters['issue'] = None  # Reset issue when volume changes
                    #st.rerun()
                elif st.session_state.filters['issue'] != selected_issue:
                    st.session_state.filters['issue'] = selected_issue if selected_issue else None
                    #st.rerun()

    with col3:
        if st.button(":material/add: Add Paper", key="add_paper_button", use_container_width=True):
            add_paper_dialog(conn)

    def apply_filters(df, search_query, filters):
        filtered_df = df.copy()
        applied_filters = False

        # Search filter
        if search_query:
            filtered_df = filtered_df[
                (filtered_df['paper_id'].astype(str).str.contains(search_query, case=False, na=False)) |
                (filtered_df['paper_title'].str.contains(search_query, case=False, na=False))
            ]
            applied_filters = True

        # Year filter
        if filters['year']:
            filtered_df = filtered_df[filtered_df['receiving_date'].dt.year == int(filters['year'])]
            applied_filters = True

        # Month filter
        if filters['month'] and filters['year']:
            filtered_df = filtered_df[filtered_df['receiving_date'].dt.strftime('%B') == filters['month']]
            applied_filters = True

        # Pending Payment filter
        if filters['pending_payment']:
            filtered_df = filtered_df[
                (filtered_df['emi_1_amount'].fillna(0) + 
                 filtered_df['emi_2_amount'].fillna(0) + 
                 filtered_df['emi_3_amount'].fillna(0)) < filtered_df['payment_amount'].fillna(0)
            ]
            applied_filters = True

        # Pending Review filter
        if filters['pending_review']:
            filtered_df = filtered_df[filtered_df['review_done'] == False]
            applied_filters = True

        # Acceptance filter
        if filters['acceptance']:
            filtered_df = filtered_df[filtered_df['acceptance'] == filters['acceptance']]
            applied_filters = True

        # Publishing Type filter
        if filters['publishing_type']:
            filtered_df = filtered_df[filtered_df['publishing_type'] == filters['publishing_type']]
            applied_filters = True

        # Volume filter
        if filters['volume']:
            try:
                filtered_df = filtered_df[filtered_df['volume'].apply(lambda x: int(float(x)) if pd.notnull(x) else False) == int(filters['volume'])]
                applied_filters = True
            except (ValueError, TypeError) as e:
                st.write(f"Debug: Volume filter skipped due to error: {str(e)}")

        # Issue filter
        if filters['issue']:
            try:
                filtered_df = filtered_df[filtered_df['issue'].astype(str) == str(filters['issue'])]
                applied_filters = True
                
            except (ValueError, TypeError) as e:
                st.write(f"Debug: Issue filter skipped due to error: {str(e)}")

        return filtered_df, applied_filters

    # Apply filters
    filtered_df, applied_filters = apply_filters(df, search_query, st.session_state.filters)

    # Display info message if no papers match the filters
    if filtered_df.empty and applied_filters:
        st.warning("No papers match the applied filter.")

    return filtered_df, applied_filters

# def all_filters(df):
#     # Initialize session state for filters if it doesn't exist
#     if 'filters' not in st.session_state:
#         st.session_state.filters = {
#             'year': None, 'month': None, 'pending_payment': False,
#             'pending_review': False, 'acceptance': None, 'publishing_type': None,
#             'volume': None, 'issue': None
#         }

#     # Callback function to reset filters
#     def reset_all_filters():
#         st.session_state.filters = {
#             'year': None, 'month': None, 'pending_payment': False,
#             'pending_review': False, 'acceptance': None, 'publishing_type': None,
#             'volume': None, 'issue': None
#         }
#         st.session_state.search_input = ""
#         st.session_state.year_pills = None
#         st.session_state.month_pills = None
#         st.session_state.payment_pills = None
#         st.session_state.review_pills = None
#         st.session_state.acceptance_pills = None
#         st.session_state.publishing_pills = None
#         st.session_state.volume_select = None
#         st.session_state.issue_select = None
#         if 'page' in st.session_state:
#             st.session_state.page = 0

#     # UI and Filter Logic
#     col1, col2, col3 = st.columns([5, 3, 1], vertical_alignment="center")
#     with col1:
#         search_query = st.text_input(
#             "Search by Paper ID or Title",
#             placeholder="Search by Paper ID or Title",
#             label_visibility="collapsed",
#             key="search_input"
#         )

#     with col2:
#         with st.popover("Filters & More", use_container_width=True):
#             st.button(":material/cached: Reset Filters", key="reset_filters_button", 
#                       on_click=reset_all_filters, use_container_width=True)
            
#             # Organize filters into tabs
#             tab1, tab2, tab3, tab4 = st.tabs(["Status", "Date", "Volume/Issue", "Edit Author"])

#             with tab4:
#                 if st.button("Edit Author Details", key="edit_author", use_container_width=True):
#                     edit_delete_author_dialog(conn)
            
#             with tab2:
#                 # Date Filters
#                 years = sorted(df['receiving_date'].dt.year.dropna().astype(int).unique(), reverse=True)
#                 selected_year = st.pills("Filter by Year", options=[str(y) for y in years], key="year_pills")
#                 st.session_state.filters['year'] = selected_year

#                 if selected_year:
#                     months = sorted(df[df['receiving_date'].dt.year == int(selected_year)]['receiving_date'].dt.strftime('%B').unique())
#                     selected_month = st.pills("Filter by Month", options=months, key="month_pills")
#                     st.session_state.filters['month'] = selected_month
#                 else:
#                     st.session_state.filters['month'] = None

#             with tab1:
#                 # Status Filters
#                 pending_payment = st.pills("Filter by Payment Status", options=["Pending Payment"], key="payment_pills")
#                 st.session_state.filters['pending_payment'] = bool(pending_payment)

#                 pending_review = st.pills("Filter by Review Status", options=["Pending Review"], key="review_pills")
#                 st.session_state.filters['pending_review'] = bool(pending_review)
                
#                 acceptance_options = ['Accepted', 'Rejected', 'Pending', 'In Review', 'Excess Plagiarism', 
#                                     'Excess AI', 'Technical Incorrect', 'Grammatical Incorrect', 'References Incorrect']
#                 selected_acceptance = st.pills("Filter by Acceptance", options=acceptance_options, key="acceptance_pills")
#                 st.session_state.filters['acceptance'] = selected_acceptance

#                 publishing_types = ['Publishing', 'Writing + Publishing']
#                 selected_publishing_type = st.pills("Filter by Publishing Type", options=publishing_types, 
#                                                     key="publishing_pills")
#                 st.session_state.filters['publishing_type'] = selected_publishing_type
            
#             with tab3:
#                 # Volume and Issue Filters
#                 volumes = sorted(pd.to_numeric(df['volume'], errors='coerce').dropna().astype(int).unique())
#                 volume_options = [str(v) for v in volumes]
#                 selected_volume = st.selectbox("Select Volume", options=[""] + volume_options, key="volume_select")
                
#                 # Populate issues based on selected volume
#                 issues = []
#                 if selected_volume:
#                     try:
#                         selected_volume_int = int(selected_volume)
#                         issues = sorted(pd.to_numeric(df[df['volume'].apply(lambda x: int(float(x)) if pd.notnull(x) and pd.to_numeric(x, errors='coerce').notnull() else False) == selected_volume_int]['issue'], errors='coerce').dropna().astype(str).unique())
#                     except (ValueError, TypeError):
#                         issues = []
#                         st.warning("No valid issues found for the selected volume.")
#                 else:
#                     issues = sorted(pd.to_numeric(df['issue'], errors='coerce').dropna().astype(str).unique())
                
#                 # Reset issue selection if volume changes
#                 if 'prev_volume' not in st.session_state:
#                     st.session_state.prev_volume = None
                
#                 if selected_volume != st.session_state.prev_volume:
#                     st.session_state.issue_select = None
#                     st.session_state.filters['issue'] = None
#                     st.session_state.prev_volume = selected_volume
                
#                 selected_issue = st.selectbox("Select Issue", options=[""] + issues, key="issue_select")
                
#                 # Update filters only if changed
#                 if st.session_state.filters['volume'] != selected_volume:
#                     st.session_state.filters['volume'] = selected_volume if selected_volume else None
#                     st.session_state.filters['issue'] = None  # Reset issue when volume changes
#                 elif st.session_state.filters['issue'] != selected_issue:
#                     st.session_state.filters['issue'] = selected_issue if selected_issue else None

#     with col3:
#         if st.button(":material/add: Add Paper", key="add_paper_button", use_container_width=True):
#             add_paper_dialog(conn)

#     def apply_filters(df, search_query, filters):
#         filtered_df = df.copy()
#         applied_filters = False

#         # Search filter
#         if search_query:
#             filtered_df = filtered_df[
#                 (filtered_df['paper_id'].astype(str).str.contains(search_query, case=False, na=False)) |
#                 (filtered_df['paper_title'].str.contains(search_query, case=False, na=False))
#             ]
#             if filtered_df.empty:
#                 st.warning("No papers match the search query.")
#             applied_filters = True

#         # Year filter
#         if filters['year']:
#             filtered_df = filtered_df[filtered_df['receiving_date'].dt.year == int(filters['year'])]
#             if filtered_df.empty:
#                 st.warning(f"No papers found for year {filters['year']}.")
#             applied_filters = True

#         # Month filter
#         if filters['month'] and filters['year']:
#             filtered_df = filtered_df[filtered_df['receiving_date'].dt.strftime('%B') == filters['month']]
#             if filtered_df.empty:
#                 st.warning(f"No papers found for month {filters['month']} in {filters['year']}.")
#             applied_filters = True

#         # Pending Payment filter
#         if filters['pending_payment']:
#             filtered_df = filtered_df[
#                 (filtered_df['emi_1_amount'].fillna(0) + 
#                  filtered_df['emi_2_amount'].fillna(0) + 
#                  filtered_df['emi_3_amount'].fillna(0)) < filtered_df['payment_amount'].fillna(0)
#             ]
#             if filtered_df.empty:
#                 st.warning("No papers with pending payments.")
#             applied_filters = True

#         # Pending Review filter
#         if filters['pending_review']:
#             filtered_df = filtered_df[filtered_df['review_done'] == False]
#             if filtered_df.empty:
#                 st.warning("No papers pending review.")
#             applied_filters = True

#         # Acceptance filter
#         if filters['acceptance']:
#             if 'acceptance' in filtered_df.columns:
#                 filtered_df = filtered_df[filtered_df['acceptance'] == filters['acceptance']]
#                 if filtered_df.empty:
#                     st.warning(f"No papers found with acceptance status '{filters['acceptance']}'.")
#                 applied_filters = True
#             else:
#                 st.error("Acceptance column not found in the DataFrame.")

#         # Publishing Type filter
#         if filters['publishing_type']:
#             if 'publishing_type' in filtered_df.columns:
#                 filtered_df = filtered_df[filtered_df['publishing_type'] == filters['publishing_type']]
#                 if filtered_df.empty:
#                     st.warning(f"No papers found with publishing type '{filters['publishing_type']}'.")
#                 applied_filters = True
#             else:
#                 st.error("Publishing type column not found in the DataFrame.")

#         # Volume filter
#         if filters['volume']:
#             try:
#                 filtered_df['volume_numeric'] = pd.to_numeric(filtered_df['volume'], errors='coerce')
#                 filtered_df = filtered_df[filtered_df['volume_numeric'] == int(filters['volume'])]
#                 filtered_df = filtered_df.drop(columns=['volume_numeric'])
#                 if filtered_df.empty:
#                     st.warning(f"No papers found for volume {filters['volume']}.")
#                 applied_filters = True
#             except (ValueError, TypeError) as e:
#                 st.error(f"Volume filter error: {str(e)}")

#         # Issue filter
#         if filters['issue']:
#             try:
#                 filtered_df['issue_numeric'] = pd.to_numeric(filtered_df['issue'], errors='coerce')
#                 filtered_df = filtered_df[filtered_df['issue_numeric'].astype(str) == str(filters['issue'])]
#                 filtered_df = filtered_df.drop(columns=['issue_numeric'])
#                 if filtered_df.empty:
#                     st.warning(f"No papers found for issue {filters['issue']}.")
#                 applied_filters = True
#             except (ValueError, TypeError) as e:
#                 st.error(f"Issue filter error: {str(e)}")

#         return filtered_df, applied_filters

#     # Apply filters
#     filtered_df, applied_filters = apply_filters(df, search_query, st.session_state.filters)

#     return filtered_df, applied_filters



########################################################################################################################
##################################--------------- Table Code ----------------------------######################
#######################################################################################################################



def render_table(df, page, items_per_page, conn, applied_filters=False):
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    paginated_papers = df.iloc[start_idx:end_idx]

    # Define column sizes for rows and headers
    column_size = [0.8, 5.8, 1.1, 1, 1, 1, 2.5]

    with st.container(border=True):
        if paginated_papers.empty:
            st.error("No papers available.")
        else:
            # Display paper count only if filters are applied
            if applied_filters:
                st.warning(f"Showing {start_idx + 1}-{min(end_idx, len(df))} of {len(df)} papers")

            # Table Header
            col1, col2, col3, col4, col5, col6, col7 = st.columns(column_size, vertical_alignment="center")
            with col1:
                st.markdown('<div class="table-header">Paper ID</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="table-header">Paper Title</div>', unsafe_allow_html=True)
            with col3:
                st.markdown('<div class="table-header">Receiving Date</div>', unsafe_allow_html=True)
            with col4:
                st.markdown('<div class="table-header">Review</div>', unsafe_allow_html=True)
            with col5:
                st.markdown('<div class="table-header">Acceptance</div>', unsafe_allow_html=True)
            with col6:
                st.markdown('<div class="table-header">Payment</div>', unsafe_allow_html=True)
            with col7:
                st.markdown('<div class="table-header">Actions</div>', unsafe_allow_html=True)

            # Group by month
            paginated_papers['month_year'] = paginated_papers['receiving_date'].apply(
                lambda x: x.strftime('%B %Y') if pd.notnull(x) else 'Unknown'
            )
            grouped_papers = paginated_papers.groupby(pd.Grouper(key='receiving_date', freq='ME'))
            reversed_grouped_papers = reversed(list(grouped_papers))

            # Table Body
            for month, monthly_papers in reversed_grouped_papers:
                monthly_papers = monthly_papers.sort_values(by='receiving_date', ascending=False)
                num_papers = len(monthly_papers)
                # Fetch publish count for the month
                publish_count = monthly_papers['paper_uploading_date'].notnull().sum()
                st.markdown(
                    f'<div class="month-header">{month.strftime("%B %Y")} ({num_papers} Papers, {publish_count} Published)</div>',
                    unsafe_allow_html=True
                )

                # Track first row in each month to avoid border above it
                first_row = True
                for _, row in monthly_papers.iterrows():
                    # Add divider before each row except the first in the month
                    if not first_row:
                        st.markdown('<div class="row-divider"></div>', unsafe_allow_html=True)
                    first_row = False

                    # Get author names
                    authors_display = fetch_author_names(row['paper_id'], conn)

                    # Get plagiarism and ai_plagiarism values with symbols
                    plagiarism_value = row['plagiarism'] if pd.notnull(row['plagiarism']) else 'N/A'
                    plagiarism_display = (
                        f'<span style="font-weight: 500; color: #e09f36;">'
                        f'<span class="material-symbols-rounded" style="vertical-align: middle; font-size:12px;">plagiarism</span> '
                        f'Plag: {plagiarism_value}%'
                        f'</span>'
                    )
                
                    # Combine author names with plagiarism values
                    authors_with_plagiarism = (
                        f"{authors_display} | {plagiarism_display}"
                    )

                    # Determine publishing type badge
                    pub_type = row['publishing_type']
                    badge_class = "pill-writing-publishing" if pub_type == 'Writing + Publishing' else ""
                    pub_badge = f'<span class="small-pill {badge_class}">{pub_type}</span>' if pub_type == 'Writing + Publishing' else ''

                    writing_badge = ''
                    if pub_type == 'Writing + Publishing':
                        writing_status = "Writing Done" if pd.notnull(row['writing_date']) else "Writing Pending"
                        writing_class = "pill-published tick" if writing_status == "Writing Done" else "pill-not-published cross"
                        writing_badge = f'<span class="small-pill {writing_class}">{writing_status}</span>'

                    # Determine publication status
                    pub_status = "Published" if pd.notnull(row['paper_uploading_date']) else "Not Published"
                    status_class = "pill-published tick" if pub_status == "Published" else "pill-not-published cross"
                    status_badge = f'<span class="small-pill {status_class}">{pub_status}</span>'

                    # Data row
                    col1, col2, col3, col4, col5, col6, col7 = st.columns(column_size, vertical_alignment="center")
                    with col1:
                        st.write(int(row["paper_id"]))
                    with col2:
                        st.markdown(f'<div class="data-row">{row["paper_title"]} {pub_badge} {writing_badge} {status_badge}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="author-names">{authors_with_plagiarism}</div>', unsafe_allow_html=True)
                    with col3:
                        st.markdown(f'<div class="data-row">{format_date(row["receiving_date"])}</div>', unsafe_allow_html=True)
                    with col4:
                        st.markdown(f'<div class="data-row">{format_status(format_review(row["review_done"]), "review")}</div>', unsafe_allow_html=True)
                    with col5:
                        st.markdown(f'<div class="data-row">{format_status(row["acceptance"], "acceptance")}</div>', unsafe_allow_html=True)
                    with col6:
                        st.markdown(f'<div class="data-row">{format_status(format_payment(row), "payment")}</div>', unsafe_allow_html=True)
                    with col7:
                        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1, 1, 1, 1], vertical_alignment="center", gap="small")
                        with btn_col1:
                            if st.button(":material/receipt_long:", key=f"view_{row['paper_id']}", help="Edit Paper Details"):
                                edit_paper_dialog(row['paper_id'], conn)
                        with btn_col2:
                            if st.button(":material/groups:", key=f"pay_{row['paper_id']}", help="Edit Author Details"):
                                edit_author_dialog(row['paper_id'], conn) 
                        with btn_col3:
                            if st.button(":material/currency_rupee:", key=f"vol_{row['paper_id']}", help="Edit Payment Details"):
                                payment_dialog(row['paper_id'], conn)
                        with btn_col4:
                            if st.button(":material/edit_note:", key=f"edit_{row['paper_id']}", help="Edit Review Details"):
                                edit_paper_status_dialog(row['paper_id'], conn)

########################################################################################################################
##################################--------------- Main ----------------------------######################
#######################################################################################################################

def main():
    col1, col2 = st.columns([12, 1], vertical_alignment="bottom")
    with col1:
        st.markdown("##  IJISEM")
    with col2:
        if st.button(":material/refresh: Refresh", key="refresh", type="tertiary"):
            st.cache_data.clear()

    # Connect to database
    conn = connect_db_ijisem()
    if conn is None:
        return  # Error already displayed in connect_db()

    # Fetch data
    df = fetch_papers(conn)
    if df.empty:
        st.warning("No papers found in the database.")
        return

    # Apply filters and get filtered dataframe
    filtered_df, applied_filters = all_filters(df)

    metrics(filtered_df)

    # Pagination
    items_per_page = 50
    total_pages = max(1, (len(filtered_df) + items_per_page - 1) // items_per_page)

    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = 0

    # Reset page if it exceeds total pages
    if st.session_state.page >= total_pages:
        st.session_state.page = total_pages - 1
    elif total_pages == 0:
        st.session_state.page = 0

    # Render table
    render_table(filtered_df, st.session_state.page, items_per_page, conn, applied_filters)

    # Pagination controls
    if total_pages > 1:
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns([1, 2, 1, 2], vertical_alignment="center")
        
        with col1:
            if st.session_state.page > 0:
                if st.button("Previous", key="prev_button"):
                    st.session_state.page -= 1
                    st.rerun()
        
        with col2:
            st.write(f"Page {st.session_state.page + 1} of {total_pages}", unsafe_allow_html=True)
        
        with col3:
            if st.session_state.page < total_pages - 1:
                if st.button("Next", key="next_button"):
                    st.session_state.page += 1
                    st.rerun()
        
        with col4:
            page_options = list(range(1, total_pages + 1))
            selected_page = st.selectbox(
                "Go to page",
                options=page_options,
                index=st.session_state.page,
                key="page_selector",
                label_visibility="collapsed"
            )
            if selected_page != st.session_state.page + 1:
                st.session_state.page = selected_page - 1
                st.rerun()


if __name__ == "__main__":
    main()