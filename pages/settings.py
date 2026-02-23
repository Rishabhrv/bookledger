import streamlit as st
import pandas as pd
from sqlalchemy import text
import datetime
import re
import io
import random
from auth import validate_token
from constants import ACCESS_TO_BUTTON,log_activity, connect_db, connect_ijisem_db, initialize_click_and_session_id, VALID_SUBJECTS, fetch_tags
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


logo = "logo/logo_black.png"
fevicon = "logo/favicon_black.ico"
small_logo = "logo/favicon_white.ico"

st.set_page_config(page_title='Settings', page_icon="⚙️", layout="wide",initial_sidebar_state=200)


st.logo(logo,
size = "large",
icon_image = small_logo
)

validate_token()
initialize_click_and_session_id()

user_role = st.session_state.get("role", None)
user_app = st.session_state.get("app", None)
user_access = st.session_state.get("access", None)
session_id = st.session_state.session_id
click_id = st.session_state.get("click_id", None)

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


if user_role != "admin":
    st.error("You do not have permission to access this page.")
    st.stop()

st.markdown("""
    <style>
    .data-row {
        margin-bottom: 0px;
        font-size: 14px;
        color: #212529;
        padding: 12px 0;
        transition: background-color 0.2s ease;
    }
    .data-row:hover {
        background-color: #f8f9fa;
    }
    .user-name {
        font-weight: 600;
        color: #333;
        font-size: 16px;
    }
    .user-sub {
        font-size: 12px;
        color: #666;
        margin-top: 2px;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .app-badge {
        font-size: 11px;
        font-weight: 600;
        padding: 2px 10px;
        border-radius: 12px;
        display: inline-block;
        margin-bottom: 4px;
        letter-spacing: 0.3px;
        text-transform: uppercase;
        color: white;
    }
    .app-main { background-color: #ff922b; }
    .app-operations { background-color: #51cf66; }
    .app-ijisem { background-color: #cc5de8; }
    .app-tasks { background-color: #339af0;}
    .app-sales { background-color: #f06595; }
    .access-badge {
        font-size: 11px;
        font-weight: 500;
        color: #495057;
        background-color: #f1f3f5;
        border: 1px solid #dee2e6;
        padding: 2px 8px;
        border-radius: 10px;
        display: inline-block;
        margin-bottom: 3px;
        margin-right: 3px;
    }
    .role-badge {
        font-size: 11px;
        font-weight: 600;
        padding: 2px 10px;
        border-radius: 20px;
        display: inline-flex;
        align-items: center;
        vertical-align: middle;
    }
    .role-admin {
        background-color: #f3f0ff;
        color: #6741d9;
        border: 1px solid #d0bfff;
    }
    .role-user {
        background-color: #ebfbee;
        color: #2b8a3e;
        border: 1px solid #b2f2bb;
    }
    .table-header {
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        color: #6c757d;
        padding: 10px 0;
        border-bottom: 2px solid #dee2e6;
        margin-bottom: 10px;
    }
    .row-divider {
        border-top: 1px solid #e9ecef;
        margin: 0;
        padding: 0;
    }
    code {
        color: #e83e8c;
        word-break: break-word;
    }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:FILL@1" rel="stylesheet" />
""", unsafe_allow_html=True)

st.cache_data.clear()

# Connect to MySQL
conn = connect_db()
ijisem_conn = connect_ijisem_db()

EMAIL_ADDRESS = st.secrets["export_email"]["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["export_email"]["EMAIL_PASSWORD"]
GMAIL_SMTP_SERVER = st.secrets["email_servers"]["GMAIL_SMTP_SERVER"]
GMAIL_SMTP_PORT = st.secrets["email_servers"]["GMAIL_SMTP_PORT"]
HOSTINGER_SMTP_SERVER = st.secrets["email_servers"]["HOSTINGER_SMTP_SERVER"]
HOSTINGER_SMTP_PORT = st.secrets["email_servers"]["HOSTINGER_SMTP_PORT"]
ADMIN_EMAIL = st.secrets["general"]["ADMIN_EMAIL"]


# Initialize logged_click_ids if not present
if "logged_click_ids" not in st.session_state:
    st.session_state.logged_click_ids = set()

# Log navigation if click_id is present and not already logged
if click_id and click_id not in st.session_state.logged_click_ids:
    try:
        log_activity(
            conn,
            st.session_state.user_id,
            st.session_state.username,
            st.session_state.session_id,
            "navigated to page",
            f"Page: Activity Log"
        )
        st.session_state.logged_click_ids.add(click_id)
    except Exception as e:
        st.error(f"Error logging navigation: {str(e)}")


# Initialize session state (from manage_users)
if "show_passwords" not in st.session_state:
    st.session_state.show_passwords = False
if "confirm_delete_user_id" not in st.session_state:
    st.session_state.confirm_delete_user_id = None
if "show_passwords_prev" not in st.session_state:
    st.session_state.show_passwords_prev = st.session_state.show_passwords
if "selected_user_for_edit" not in st.session_state:
    st.session_state.selected_user_for_edit = None

st.write("### ⚙️ Settings")

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    main_section = st.radio(
        "Section",
        ["Manage Users", "Export Data"],
        key="settings_main_section"
    )
    if main_section == "Manage Users":
        selected_user_tab = st.radio(
            "User Management",
            ["Users", "Edit User", "Add User", "Responsibilities"],
            key="settings_user_nav"
        )
    else:
        selected_export_tab = st.radio(
            "Export Tools",
            ["Export as PDF", "Export as Excel"],
            key="settings_export_nav"
        )

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

if main_section == "Manage Users":
    

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
        st.stop()

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
                    ORDER BY u.id DESC
                """)
            ).fetchall()
    except Exception as e:
        st.error(f"❌ Database error while fetching users: {str(e)}")
        st.stop() 

    # App configurations
    app_display_names = list(VALID_APPS.keys())
    app_db_values = {display: db_value for display, db_value in VALID_APPS.items()}
    FULL_ACCESS_APPS = ["IJISEM", "Tasks", "Sales"]
    LEVEL_SUPPORT_APPS = ["IJISEM", "Tasks", "Operations", "Sales"]

    col_content = st.container()
    with col_content:
        if selected_user_tab == "Users":
            st.write("### Users Overview")
            if not users:
                st.error("❌ No users found in database.")

            # Table Header
            col_sizes = [0.4, 1.2, 2.0, 0.7, 0.5]
            header_cols = st.columns(col_sizes)
            headers = ["ID", "User Profile", "App Access", "Organization", "Password"]
            for col, header in zip(header_cols, headers):
                col.markdown(f'<div class="table-header">{header}</div>', unsafe_allow_html=True)

            for user in users:
                with st.container():
                    cols = st.columns(col_sizes, vertical_alignment="center")
                    
                    # ID
                    cols[0].markdown(f"<span style='color:#888; font-weight:500'>#{user.id}</span>", unsafe_allow_html=True)
                    
                    # User Profile
                    with cols[1]:
                        st.markdown(f"""
                            <div class="user-name">{user.username}</div>
                            <div class="user-sub">
                                <span class="material-symbols-rounded" style="font-size:14px">mail</span> {user.email or "No Email"}
                            </div>
                            <div class="user-sub">
                                <span class="material-symbols-rounded" style="font-size:14px">badge</span> {user.designation or "No Designation"} | {user.associate_id or "N/A"}
                            </div>
                        """, unsafe_allow_html=True)
                    
                        # App Access
                        with cols[2]:
                            apps_list = user.apps.split(',') if user.apps else []
                            # Create map for class assignment
                            app_class_map = {
                                "main": "app-main",
                                "operations": "app-operations",
                                "ijisem": "app-ijisem",
                                "tasks": "app-tasks",
                                "sales": "app-sales"
                            }
                            apps_html = " ".join([f'<span class="app-badge {app_class_map.get(app.strip().lower(), "")}">{app.strip()}</span>' for app in apps_list])
                            
                            access_list = user.access_types.split(',') if user.access_types else []
                            access_html = " ".join([f'<span class="access-badge">{acc.strip()}</span>' for acc in access_list]) if access_list else '<span style="color:#999; font-size:11px;">None</span>'

                            st.markdown(f"""
                                <div>{apps_html}</div>
                                <div style="margin-top:4px;">{access_html}</div>
                                <div style="font-size:12px; color:#666; margin-top:4px;">
                                    <b>Level:</b> {user.levels or "None"}
                                </div>
                            """, unsafe_allow_html=True)                    
                    # Organization
                    with cols[3]:
                        role_class = "role-admin" if user.role.lower() == "admin" else "role-user"
                        role_html = f'<span class="role-badge {role_class}">{user.role.capitalize()}</span>'
                        report_to_name = user.report_to if user.report_to else "None"
                        st.markdown(f"""
                            <div>{role_html}</div>
                            <div class="user-sub"><b>Reports to:</b> {report_to_name}</div>
                            <div class="user-sub"><b>Joined:</b> {user.start_date or "-"}</div>
                        """, unsafe_allow_html=True)
                    
                    # Password
                    with cols[4]:
                        with st.popover("View"):
                            st.code(user.password, language=None)

                    st.markdown('<div class="row-divider"></div>', unsafe_allow_html=True)

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

        elif selected_user_tab == "Responsibilities":
            # Ensure description and log_actions columns exist
            try:
                with conn.session as s:
                    s.execute(text("SELECT description FROM daily_responsibilities LIMIT 1"))
            except Exception:
                try:
                    with conn.session as s:
                        s.execute(text("ALTER TABLE daily_responsibilities ADD COLUMN description TEXT"))
                        s.commit()
                except Exception as e:
                    st.error(f"Error updating daily_responsibilities schema (description): {e}")

            try:
                with conn.session as s:
                    s.execute(text("SELECT log_actions FROM daily_responsibilities LIMIT 1"))
            except Exception:
                try:
                    with conn.session as s:
                        s.execute(text("ALTER TABLE daily_responsibilities ADD COLUMN log_actions TEXT"))
                        s.commit()
                except Exception as e:
                    st.error(f"Error updating daily_responsibilities schema (log_actions): {e}")

            col1, col2 = st.columns([5,1])
            with col1:
                st.write("### 📋 Manage Daily Responsibilities")
            with col2:
                if st.button(":material/refresh: Refresh", key="refresh_price", type="tertiary"):
                    st.cache_data.clear()
            if not users:
                st.error("❌ No users found in database.")
            else:
                with st.container(border=True):
                    user_dict = {f"{user.username} (ID: {user.id})": user for user in users if user.role != 'admin'}
                    if not user_dict:
                        st.info("No non-admin users found to assign responsibilities.")
                    else:
                        selected_user_key = st.selectbox(
                            "Select Employee", 
                            options=list(user_dict.keys()), 
                            key="resp_user_select"
                        )
                        target_user = user_dict[selected_user_key]
                        target_user_id = target_user.id

                        # Fetch current responsibilities
                        try:
                            resp_df = conn.query("""
                                SELECT dr.id, dr.task_name, dr.description, dr.log_actions, dr.manager_id, u.username as manager_name 
                                FROM daily_responsibilities dr 
                                LEFT JOIN userss u ON dr.manager_id = u.id 
                                WHERE dr.user_id = :uid AND dr.is_active = 1
                            """, params={"uid": target_user_id}, ttl=0)
                            
                            st.write(f"Current Responsibilities for **{target_user.username}**:")
                            if resp_df.empty:
                                st.info("No responsibilities assigned yet.")
                            else:
                                for _, r in resp_df.iterrows():
                                    col_name, col_manager, col_del = st.columns([0.5, 0.35, 0.15])
                                    col_name.write(f"**- {r['task_name']}**")
                                    if r.get('description'):
                                        col_name.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;*<small>{r['description']}</small>*", unsafe_allow_html=True)
                                    
                                    if r.get('log_actions'):
                                        col_name.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;**Logs:** <small>{r['log_actions']}</small>", unsafe_allow_html=True)

                                    manager_display = r['manager_name'] if r['manager_name'] else "Default Manager"
                                    col_manager.write(f"Manager: **{manager_display}**")

                                    if col_del.button("🗑️", key=f"del_resp_{r['id']}", help="Delete Responsibility"):
                                        try:
                                            with conn.session as s:
                                                s.execute(text("UPDATE daily_responsibilities SET is_active = 0 WHERE id = :id"), {"id": r['id']})
                                                s.commit()
                                            st.toast(f"Responsibility '{r['task_name']}' removed.")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error deleting: {e}")
                            
                            st.write("---")
                            # Prepare list of possible managers
                            manager_dict = {f"{u.username} (ID: {u.id})": u for u in users if u.role == 'admin' or (u.levels and ('reporting_manager' in u.levels or 'both' in u.levels))}
                            
                            col_t, col_d, col_m = st.columns([1, 1, 1])
                            new_task = col_t.text_input("Add New Responsibility", key="new_resp_input", placeholder="e.g., Check Amazon Orders")
                            new_desc = col_d.text_input("Description / Guidelines", key="new_resp_desc", placeholder="e.g., Verify all pending orders by 10 AM")
                            
                            # Determine current default manager from user_app_access
                            default_manager_id = None
                            try:
                                with conn.session as s:
                                    uaa = s.execute(text("SELECT report_to FROM user_app_access WHERE user_id = :uid AND app = 'tasks'"), {"uid": target_user_id}).fetchone()
                                    if uaa:
                                        default_manager_id = uaa[0]
                            except:
                                pass

                            manager_options = ["Default Manager"] + list(manager_dict.keys())
                            default_manager_display = "Default Manager"
                            if default_manager_id:
                                for display, u in manager_dict.items():
                                    if u.id == default_manager_id:
                                        default_manager_display = display
                                        break
                            
                            new_manager_key = col_m.selectbox("Manager", options=manager_options, index=manager_options.index(default_manager_display) if default_manager_display in manager_options else 0, key="new_resp_manager")
                            new_manager_id = manager_dict[new_manager_key].id if new_manager_key != "Default Manager" else None

                            # Fetch unique actions from activity_log table
                            try:
                                with conn.session as s:
                                    actions_res = s.execute(text("SELECT DISTINCT action FROM activity_log WHERE action IS NOT NULL AND action != '' ORDER BY action")).fetchall()
                                    db_actions = [row[0] for row in actions_res]
                            except Exception as e:
                                st.error(f"Error fetching activity actions: {e}")
                                db_actions = []

                            new_actions = st.multiselect("Allowed Activity Logs", options=db_actions, key="new_resp_actions")

                            if st.button("➕ Add Responsibility", key="add_resp_btn", type="primary", use_container_width=True):
                                if new_task.strip():
                                    try:
                                        actions_str = ",".join(new_actions) if new_actions else None
                                        with conn.session as s:
                                            s.execute(text("INSERT INTO daily_responsibilities (user_id, task_name, description, manager_id, log_actions) VALUES (:uid, :name, :desc, :mid, :actions)"),
                                                        {"uid": target_user_id, "name": new_task.strip(), "desc": new_desc.strip() if new_desc else None, "mid": new_manager_id, "actions": actions_str})
                                            s.commit()
                                        log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "added responsibility", f"Assigned '{new_task.strip()}' to {target_user.username} (Report to: {new_manager_key})")
                                        st.success("✅ Responsibility added!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error adding: {e}")
                                else:
                                    st.warning("Please enter a task name.")
                        except Exception as e:
                            st.error(f"Error fetching responsibilities: {e}")

    


    ###################################################################################################################################
    ##################################--------------- Export Data in PDF/Excel ----------------------------##################################
    ###################################################################################################################################




if main_section == "Export Data":

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
                
                # --- NEW FILTERS ---
                col_d1, col_d2 = st.columns([1.5, 1], gap="small")
                with col_d1:
                    selected_dates = st.date_input("Date Range", value=[], help="Select start and end date for book registration", key="filter_date_range")
                with col_d2:
                    image_filter = st.selectbox("Image Filter", ["All", "With Image", "Without Image"], index=0, key="filter_image_presence")
                
                # Tags filter (multiselect below)
                sorted_tags = fetch_tags(conn)
                selected_tags = st.multiselect("Tags", sorted_tags, help="Select tags to filter books", key="filter_tags")
                
                # Build query with filters, joining book_authors and authors to get author names and positions
                query = """
                SELECT b.images, b.title, b.isbn, b.book_mrp, b.publisher, b.date,
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
                
                # Image Filter Logic
                if image_filter == "With Image":
                    query += " AND b.images IS NOT NULL AND b.images != ''"
                elif image_filter == "Without Image":
                    query += " AND (b.images IS NULL OR b.images = '')"
                
                # Date Range Logic
                if len(selected_dates) == 2:
                    query += " AND b.date BETWEEN :start_date AND :end_date"
                    params["start_date"] = selected_dates[0]
                    params["end_date"] = selected_dates[1]
                
                query += " GROUP BY b.book_id, b.publisher, b.images, b.title, b.isbn, b.book_mrp, b.date"
                
                # Fetch filtered data for preview
                df = conn.query(query, params=params)
                if not df.empty:
                    df.insert(0, 'Select', True)

        with global_col2:
            # Display preview of filtered data
            if df.empty:
                st.warning("No books match the selected filters.")
                edited_df = df
            else:
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "Select": st.column_config.CheckboxColumn("Select", default=True),
                        "images": st.column_config.ImageColumn("Image"),
                        "title": "Book Title",
                        "authors": "Authors",
                        "isbn": "ISBN",
                        "book_mrp": st.column_config.NumberColumn("MRP", format="₹%.2f"),
                        "publisher": "Publisher",
                        "date": "Registration Date"
                    },
                    width="stretch",
                    hide_index=True,
                    key="pdf_export_editor"
                )

        with global_col1:
            button_col1, button_col2 = st.columns([3.9,1.9], gap="small")   

            with button_col1:
                # Filter for selected books
                selected_df = edited_df[edited_df['Select'] == True] if not edited_df.empty else pd.DataFrame()
                
                # Export button
                if st.button("Export to PDF", key="export_pdf_button", type="primary", disabled=selected_df.empty):
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
                        book_count = len(selected_df)
                        publisher_text = selected_publisher if selected_publisher != "All" else "All Publishers"
                        tags_text = ", ".join(selected_tags) if selected_tags else "None"
                        subject_text = selected_subject if selected_subject != "All" else "All Subjects"
                        date_range_text = f"{selected_dates[0]} to {selected_dates[1]}" if len(selected_dates) == 2 else "All Time"
                        
                        elements.append(Paragraph(f"Publisher: {publisher_text}", summary_style))
                        elements.append(Paragraph(f"Subject: {subject_text}", summary_style))
                        elements.append(Paragraph(f"Date Range: {date_range_text}", summary_style))
                        elements.append(Paragraph(f"Image Filter: {image_filter}", summary_style))
                        elements.append(Paragraph(f"Tags: {tags_text}", summary_style))
                        elements.append(Paragraph(f"Number of Books Selected: {book_count}", summary_style))
                        elements.append(Spacer(1, 8))
                        
                        # Table data
                        table_data = [["Image", "Title", "Authors", "ISBN", "MRP", "Publisher"]]
                        for idx, row in selected_df.iterrows():
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
                                f"Publisher: {selected_publisher}, Subject: {selected_subject}, Status: {delivery_status}, Dates: {date_range_text}, Image Filter: {image_filter}"
                            )
                            st.success(f"PDF exported successfully and sent to Admin Email: {ADMIN_EMAIL}")
                            st.toast(f"PDF exported successfully and sent to Admin Email: {ADMIN_EMAIL}", icon="✔️", duration="long")
                            st.balloons()
                        else:
                            st.error("Failed to send export email")
                            st.toast("Failed to send export email", icon="❌", duration="long")

            with button_col2:
                st.markdown(f"**Total Books: <span style='color:red;'>{len(selected_df)}</span>**", unsafe_allow_html=True)

    col_exp_content = st.container()
    with col_exp_content:
        if selected_export_tab == "Export as PDF":
            export_filtered_books_pdf(conn)
        elif selected_export_tab == "Export as Excel":
            col1, _ = st.columns(2)
            with col1:
                export_data()
