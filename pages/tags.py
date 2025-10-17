# import streamlit as st
# import warnings 
# import pandas as pd
# import os
# from sqlalchemy import text
# warnings.simplefilter('ignore')
# import os
# import datetime
# import altair as alt
# from auth import validate_token
# from constants import log_activity
# from constants import connect_db
# import uuid
# from datetime import datetime, timezone, timedelta, time
# from time import sleep
# from sqlalchemy.sql import text
# from constants import get_page_url


# # Set page configuration
# st.set_page_config(
#     layout="wide",  # Set layout to wide mode
#     initial_sidebar_state="collapsed",
#     page_icon="chart_with_upwards_trend",  
#      page_title="Content Dashboard",
# )

# # Inject CSS to remove the menu (optional)
# hide_menu_style = """
#     <style>
#     #MainMenu {visibility: hidden;}
#     footer {visibility: hidden;}
#     </style>
# """

# st.markdown(hide_menu_style, unsafe_allow_html=True)

# st.markdown("""
#     <style>
            
#         /* Remove Streamlit's default top padding */
#         .main > div {
#             padding-top: 0px !important;
#         }
#         /* Ensure the first element has minimal spacing */
#         .block-container {
#             padding-top: 28px !important;  /* Small padding for breathing room */
#         }
#             """, unsafe_allow_html=True)

# logo = "logo/logo_black.png"
# fevicon = "logo/favicon_black.ico"
# small_logo = "logo/favicon_white.ico"

# st.logo(logo,
# size = "large",
# icon_image = small_logo
# )

# # Run validation
# validate_token()

# role_user = st.session_state.get("role", "Unknown")
# user_app = st.session_state.get("app", "Unknown")
# user_name = st.session_state.get("username", "Unknown")
# user_access = st.session_state.get("access", [])
# token = st.session_state.token
# # if "session_id" not in st.session_state:
# #     st.session_state.session_id = str(uuid.uuid4())


# # role_user = 'admin'
# # user_app = 'main'
# # user_name = 'Akash'
# # user_access = ['DatadashBoard','Advance' 'Search','Team Dashboard']

# #st.write(f"### Welcome {user_name}!")
# # st.write(f"**Role:** {role_user}")
# # st.write(f"**App:** {user_app}")
# # st.write(f"**Access:** {user_access}")


# section_labels = {
#     "Writing Section": "writer",
#     "Proofreading Section": "proofreader",
#     "Formatting Section": "formatter",
#     "Cover Design Section": "cover_designer"
# }


# # Admin or allowed users get role selector pills
# if role_user == "admin" or (role_user == "user" and user_app == "main" and "Team Dashboard" in user_access):
#     selected = st.segmented_control(
#         "Select Section", 
#         list(section_labels.keys()),
#         default="Writing Section",
#         key="section_selector",
#         label_visibility='collapsed'
#     )
#     if selected is None:
#         st.error("Please select a section to proceed.")
#         st.stop()
#     #st.session_state.access = [selected]  # Store as list to match user format
#     user_role = section_labels[selected]



# elif role_user == "user" and user_app == "operations":
#     # Set user_role from their first access item
#     user_role = user_access[0] if user_access else ""

# else:
#     # Access Denied
#     st.error("You don't have permission to access this page.")
#     st.stop()

# st.cache_data.clear()

# # Connect to MySQL
# conn = connect_db()

# # if user_app == 'operations':
# #     if "activity_logged" not in st.session_state:
# #         log_activity(
# #                     conn,
# #                     st.session_state.user_id,
# #                     st.session_state.username,
# #                     st.session_state.session_id,
# #                     "logged in",
# #                     f"App: {st.session_state.app}, Access: {st.session_state.access[0]}"
# #                 )
# #         st.session_state.activity_logged = True


# # if user_app == 'main':
# #     # Initialize session state from query parameters
# #     query_params = st.query_params
# #     click_id = query_params.get("click_id", [None])
# #     session_id = query_params.get("session_id", [None])

# #     # Set session_id in session state
# #     st.session_state.session_id = session_id

# #     # Initialize logged_click_ids if not present
# #     if "logged_click_ids" not in st.session_state:
# #         st.session_state.logged_click_ids = set()

# #     # Log navigation if click_id is present and not already logged
# #     if click_id and click_id not in st.session_state.logged_click_ids:
# #         try:
# #             log_activity(
# #                 conn,
# #                 st.session_state.user_id,
# #                 st.session_state.username,
# #                 st.session_state.session_id,
# #                 "navigated to page",
# #                 f"Page: Team Dashboard"
# #             )
# #             st.session_state.logged_click_ids.add(click_id)
# #         except Exception as e:
# #             st.error(f"Error logging navigation: {str(e)}")


# # Initialize session state
# if "logged_click_ids" not in st.session_state:
#     st.session_state.logged_click_ids = set()
# if "activity_logged" not in st.session_state:
#     st.session_state.activity_logged = False

# # Determine session_id based on access method
# user_app = st.session_state.get("app", "operations")
# if user_app == "main":
#     query_params = st.query_params
#     session_id = query_params.get("session_id", [None])
#     click_id = query_params.get("click_id", [None])
#     if not session_id:
#         st.error("Session not initialized. Please access this page from the main dashboard.")
#         st.stop()
#     st.session_state.session_id = session_id
# else:
#     if "session_id" not in st.session_state:
#         st.session_state.session_id = str(uuid.uuid4())
#     click_id = None

# # Ensure user_id and username are set
# if not all(key in st.session_state for key in ["user_id", "username"]):
#     st.error("Session not initialized. Please log in again.")
#     st.stop()

# # Log login for direct access (operations)
# if user_app == "operations" and not st.session_state.activity_logged:
#     try:
#         log_activity(
#             conn,
#             st.session_state.user_id,
#             st.session_state.username,
#             st.session_state.session_id,
#             "logged in",
#             f"App: {user_app}, Access: {st.session_state.get('access', ['direct'])[0]}"
#         )
#         st.session_state.activity_logged = True
#     except Exception as e:
#         st.error(f"Error logging login: {str(e)}")

# # Log page access if coming from main page and click_id is new
# if user_app == "main" and click_id and click_id not in st.session_state.logged_click_ids:
#     try:
#         log_activity(
#             conn,
#             st.session_state.user_id,
#             st.session_state.username,
#             st.session_state.session_id,
#             "navigated to page",
#             f"Page: team_dashboard"
#         )
#         st.session_state.logged_click_ids.add(click_id)
#     except Exception as e:
#         st.error(f"Error logging navigation: {str(e)}")


# # --- Updated CSS ---
# st.markdown("""
#     <style>
#     .header-row {
#         padding-bottom: 5px;
#         margin-bottom: 10px;
#     }
#     .header {
#         font-weight: bold;
#         font-size: 14px; 
#     }
#     .header-line {
#         border-bottom: 1px solid #ddd;
#         margin-top: -10px;
#     }
#     .pill {
#         padding: 2px 6px;
#         border-radius: 10px;
#         font-size: 12px;
#         display: inline-block;
#         margin-right: 4px;
#     }
#     .since-enrolled {
#         background-color: #FFF3E0;
#         color: #FF9800;
#         padding: 1px 4px;
#         border-radius: 8px;
#         font-size: 11px;
#     }
#     .section-start-not {
#         background-color: #F5F5F5;
#         color: #757575;
#     }
#     .section-start-date {
#         background-color: #FFF3E0;
#         color: #FF9800;
#     }
#     .worker-by-not {
#         background-color: #F5F5F5;
#         color: #757575;
#     }
#     /* Worker-specific colors (softer tones, reusable for all sections) */
#     .worker-by-0 { background-color: #E3F2FD; color: #1976D2; } /* Blue */
#     .worker-by-1 { background-color: #FCE4EC; color: #D81B60; } /* Pink */
#     .worker-by-2 { background-color: #E0F7FA; color: #006064; } /* Cyan */
#     .worker-by-3 { background-color: #F1F8E9; color: #558B2F; } /* Light Green */
#     .worker-by-4 { background-color: #FFF3E0; color: #EF6C00; } /* Orange */
#     .worker-by-5 { background-color: #F3E5F5; color: #8E24AA; } /* Purple */
#     .worker-by-6 { background-color: #FFFDE7; color: #F9A825; } /* Yellow */
#     .worker-by-7 { background-color: #EFEBE9; color: #5D4037; } /* Brown */
#     .worker-by-8 { background-color: #E0E0E0; color: #424242; } /* Grey */
#     .worker-by-9 { background-color: #E8EAF6; color: #283593; } /* Indigo */
#     .status-pending {
#         background-color: #FFEBEE;
#         color: #F44336;
#         font-weight: bold;
#     }
#     .apply-isbn-yes {
#     background-color: #C8E6C9; /* Light green */
#     color: #2E7D32; /* Dark green text */
#     }
#     .apply-isbn-no {
#         background-color: #E0E0E0; /* Light gray */
#         color: #616161; /* Dark gray text */
#     }
#     .status-running {
#         background-color: #FFFDE7;
#         color: #F9A825;
#         font-weight: bold;
#     }
    
#     /* Standardized badge colors for Pending (red) and Running (yellow) */
#     .status-badge-red {
#         background-color: #FFEBEE;
#         color: #F44336;
#         padding: 4px 8px;
#         border-radius: 12px;
#         font-weight: bold;
#         display: inline-flex;
#         align-items: center;
#     }
#     .status-badge-yellow {
#         background-color: #FFF3E0; /* soft orange background */
#         color: #FB8C00;           /* vibrant orange text */
#         padding: 4px 8px;
#         border-radius: 12px;
#         font-weight: bold;
#         display: inline-flex;
#         align-items: center;
#     }
#     .status-badge-orange {
#         background-color: #FFEFE6; /* light peachy orange */
#         color: #E65100;           /* deep burnt orange */
#         padding: 4px 8px;
#         border-radius: 12px;
#         font-weight: bold;
#         display: inline-flex;
#         align-items: center;
#     }

#     .badge-count {
#         background-color: rgba(255, 255, 255, 0.9);
#         color: inherit;
#         padding: 2px 6px;
#         border-radius: 10px;
#         margin-left: 6px;
#         font-size: 12px;
#         font-weight: normal;
#     }
#     /* ... existing styles ... */
#     .status-completed {
#         background-color: #E8F5E9;
#         color: #4CAF50;
#         font-weight: bold;
#     }
#     .status-correction {
#         background-color: #FFEBEE;
#         color: #F44336;
#         font-weight: bold;
#     }
#     .on-hold {
#         background-color: #FFEBEE;
#         color: #F44336;
#         font-weight: bold;
#     }
#     .status-badge-green {
#         background-color: #E8F5E9;
#         color: #4CAF50;
#         padding: 4px 8px;
#         border-radius: 12px;
#         font-weight: bold;
#         display: inline-flex;
#         align-items: center;
#     }
            
#     .publish-only-badge {
#         background-color: #e0f7fa;
#         color: #00695c;
#         padding: 2px 8px;
#         border-radius: 12px;
#         font-size: 10px;
#         margin-left: 5px;
#     }
            
#     .thesis-to-book-badge {
#         background-color: #e0f7fa;
#         color: #00695c;
#         padding: 2px 8px;
#         border-radius: 12px;
#         font-size: 10px;
#         margin-left: 5px;
#     }
            
#     .dialog-header {
#             font-size: 20px;
#             color: #4CAF50;
#             margin-bottom: 10px;
#             font-weight: bold;
#         }
#         .info-label {
#             font-weight: bold;
#             color: #333;
#             margin-top: 10px;
#             margin-bottom: 5px;
#         }
#         .info-value {
#             padding: 5px 10px;
#             border-radius: 5px;
#             background-color: #F5F5F5;
#             display: inline-block;
#         }
#         table {
#             width: 100%;
#             border-collapse: collapse;
#             margin-bottom: 20px;
#         }
#         th {
#             background-color: #4CAF50;
#             color: white;
#             padding: 10px;
#             text-align: left;
#             font-weight: bold;
#         }
#         td {
#             padding: 10px;
#             border-bottom: 1px solid #E0E0E0;
#         }
#         .pill-yes {
#             background-color: #C8E6C9;
#             color: #2E7D32;
#             padding: 2px 8px;
#             border-radius: 12px;
#             font-size: 12px;
#         }
#         .pill-no {
#             background-color: #E0E0E0;
#             color: #616161;
#             padding: 2px 8px;
#             border-radius: 12px;
#             font-size: 12px;
#         }
#         .close-button {
#             margin-top: 20px;
#             width: 100%;
#         }
#             /* Timeline styles */
#         .timeline {
#             position: relative;
#             padding-left: 40px;
#             margin: 0;
#             font-family: Arial, sans-serif;
#             font-size: 14px;
#             line-height: 1.5;
#         }
#         .timeline::before {
#             content: '';
#             position: absolute;
#             top: 0;
#             bottom: 0;
#             left: 15px;
#             width: 2px;
#             background: #4CAF50;
#         }
#         .timeline-item {
#             position: relative;
#             margin-bottom: 6px;
#             padding-left: 20px;
#         }
#         .timeline-item::before {
#             content: '';
#             position: absolute;
#             left: -25px;
#             top: 5px;
#             width: 10px;
#             height: 10px;
#             background: #fff;
#             border: 2px solid #4CAF50;
#             border-radius: 50%;
#         }
#         .timeline-time {
#             font-weight: bold;
#             color: #333;
#             display: inline-block;
#             min-width: 140px;
#         }
#         .timeline-event {
#             color: #555;
#         }
#         .timeline-notes {
#             color: #777;
#             font-style: italic;
#             font-size: 12px;
#             display: block;
#             margin-top: 2px;
#         }
        
#         /* Other element styles */
#         .field-label {
#             font-weight: bold;
#             margin-bottom: 5px;
#         }
#         .changed {
#             background-color: #FFF3E0;
#             padding: 2px 6px;
#             border-radius: 4px;
#         }
#     </style>
# """, unsafe_allow_html=True)

# def fetch_books(months_back: int = 4, section: str = "writing") -> pd.DataFrame:
#     conn = connect_db()
#     cutoff_date = datetime.now().date() - timedelta(days=30 * months_back)
#     cutoff_date_str = cutoff_date.strftime('%Y-%m-%d')
    
#     section_columns = {
#         "writing": {
#             "base": [
#                 "writing_by AS 'Writing By'", 
#                 "writing_start AS 'Writing Start'", 
#                 "writing_end AS 'Writing End'",
#                 "book_pages AS 'Number of Book Pages'",
#                 "syllabus_path AS 'Syllabus Path'",
#                 "book_note AS 'book_note'"
#             ],
#             "extra": [],
#             "publish_filter": "AND b.is_publish_only = 0 AND b.is_thesis_to_book = 0"
#         },
#         "proofreading": {
#             "base": [
#                 "proofreading_by AS 'Proofreading By'", 
#                 "proofreading_start AS 'Proofreading Start'", 
#                 "proofreading_end AS 'Proofreading End'",
#                 "b.is_publish_only AS 'is_publish_only'",
#                 "b.is_thesis_to_book AS 'is_thesis_to_book'",
#                 "book_note AS 'book_note'"
#             ],
#             "extra": [
#                 "writing_end AS 'Writing End'", 
#                 "writing_by AS 'Writing By'",
#                 "book_pages AS 'Number of Book Pages'"
#             ],
#             "publish_filter": ""
#         },
#         "formatting": {
#             "base": [
#                 "formatting_by AS 'Formatting By'", 
#                 "formatting_start AS 'Formatting Start'", 
#                 "formatting_end AS 'Formatting End'",
#                 "book_pages AS 'Number of Book Pages'",
#                 "book_note AS 'book_note'"
#             ],
#             "extra": ["proofreading_end AS 'Proofreading End'"],
#             "publish_filter": ""
#         },
#         "cover": {
#             "base": [
#                 "cover_by AS 'Cover By'", 
#                 "cover_start AS 'Cover Start'", 
#                 "cover_end AS 'Cover End'",
#                 "apply_isbn AS 'Apply ISBN'", 
#                 "isbn AS 'ISBN'",
#                 "book_note AS 'book_note'"
#             ],
#             "extra": [
#                 "formatting_end AS 'Formatting End'",
#                 "(SELECT MIN(ba.photo_recive) FROM book_authors ba WHERE ba.book_id = b.book_id) AS 'All Photos Received'",
#                 "(SELECT MIN(ba.author_details_sent) FROM book_authors ba WHERE ba.book_id = b.book_id) AS 'All Details Sent'"
#             ],
#             "publish_filter": ""
#         }
#     }
#     config = section_columns.get(section, section_columns["writing"])
#     columns = config["base"] + config["extra"]
#     columns_str = ", ".join(columns)
#     publish_filter = config["publish_filter"]
    
#     if section == "cover":
#         query = f"""
#             SELECT 
#                 b.book_id AS 'Book ID',
#                 b.title AS 'Title',
#                 b.date AS 'Date',
#                 {columns_str},
#                 b.is_publish_only AS 'Is Publish Only',
#                 b.is_thesis_to_book AS 'Is Thesis to Book',
#                 h.hold_start AS 'hold_start',
#                 h.resume_time AS 'resume_time',
#                 GROUP_CONCAT(CONCAT(a.name, ' (Pos: ', ba.author_position, ', Photo: ', ba.photo_recive, ', Sent: ', ba.author_details_sent, ')') SEPARATOR ', ') AS 'Author Details'
#             FROM books b
#             LEFT JOIN book_authors ba ON b.book_id = ba.book_id
#             LEFT JOIN authors a ON ba.author_id = a.author_id
#             LEFT JOIN holds h ON b.book_id = h.book_id AND h.section = '{section}'
#             WHERE b.date >= '{cutoff_date_str}'
#             {publish_filter}
#             GROUP BY b.book_id, b.title, b.date, {', '.join(c.split(' AS ')[0] for c in columns)}, b.is_publish_only, b.is_thesis_to_book, h.hold_start, h.resume_time
#             ORDER BY b.date DESC
#         """
#     else:
#         query = f"""
#             SELECT 
#                 b.book_id AS 'Book ID',
#                 b.title AS 'Title',
#                 b.date AS 'Date',
#                 {columns_str},
#                 b.is_publish_only AS 'Is Publish Only',
#                 b.is_thesis_to_book AS 'Is Thesis to Book',
#                 h.hold_start AS 'hold_start',
#                 h.resume_time AS 'resume_time',
#                 h.reason AS 'hold_reason'
#             FROM books b
#             LEFT JOIN holds h ON b.book_id = h.book_id AND h.section = '{section}'
#             WHERE b.date >= '{cutoff_date_str}'
#             {publish_filter}
#             ORDER BY b.date DESC
#         """
    
#     df = conn.query(query, show_spinner=False)
#     df['Date'] = pd.to_datetime(df['Date']).dt.date
#     df['hold_start'] = pd.to_datetime(df['hold_start'])
#     df['resume_time'] = pd.to_datetime(df['resume_time'])
#     return df

# def fetch_author_details(book_id):
#     conn = connect_db()
#     query = f"""
#         SELECT
#             ba.author_id AS 'Author ID', 
#             a.name AS 'Author Name',
#             ba.author_position AS 'Position',
#             ba.photo_recive AS 'Photo Received',
#             ba.author_details_sent AS 'Details Sent'
#         FROM book_authors ba
#         JOIN authors a ON ba.author_id = a.author_id
#         WHERE ba.book_id = {book_id}
#     """
#     df = conn.query(query, show_spinner=False)
#     return df

# def fetch_holds(section: str) -> pd.DataFrame:
#     conn = connect_db()
#     query = """
#         SELECT 
#             book_id,
#             section,
#             hold_start,
#             resume_time
#         FROM holds
#         WHERE section = :section
#     """
#     holds_df = conn.query(query, params={"section": section}, show_spinner=False)
#     holds_df['hold_start'] = pd.to_datetime(holds_df['hold_start'])
#     holds_df['resume_time'] = pd.to_datetime(holds_df['resume_time'])
#     return holds_df

# #on_hold_books = fetch_hold_books()


# @st.dialog("Author Details", width='medium')
# def show_author_details_dialog(book_id):
#     # Fetch book details (title and ISBN)
#     conn = connect_db()
#     book_query = f"SELECT title, isbn FROM books WHERE book_id = {book_id}"
#     book_data = conn.query(book_query, show_spinner=False)
#     book_title = book_data.iloc[0]['title'] if not book_data.empty else "Unknown Title"
#     isbn = book_data.iloc[0]['isbn'] if not book_data.empty and pd.notnull(book_data.iloc[0]['isbn']) else "Not Assigned"

#     # Fetch author details
#     author_details_df = fetch_author_details(book_id)

#     # Header
#     st.markdown(f'<div class="dialog-header">Book ID: {book_id} - {book_title}</div>', unsafe_allow_html=True)

#     # ISBN Display
#     st.markdown('<div class="info-label">ISBN</div>', unsafe_allow_html=True)
#     st.markdown(f'<span class="info-value">{isbn}</span>', unsafe_allow_html=True)

#     # Author Details Table
#     if not author_details_df.empty:
#         # Prepare HTML table
#         table_html = '<table><tr><th>Author ID</th><th>Author Name</th><th>Position</th><th>Photo Received</th><th>Details Received</th></tr>'
#         for _, row in author_details_df.iterrows():
#             photo_class = "pill-yes" if row["Photo Received"] else "pill-no"
#             details_class = "pill-yes" if row["Details Sent"] else "pill-no"
#             table_html += (
#                 f'<tr>'
#                 f'<td>{row["Author ID"]}</td>'
#                 f'<td>{row["Author Name"]}</td>'
#                 f'<td>{row["Position"]}</td>'
#                 f'<td><span class="{photo_class}">{"Yes" if row["Photo Received"] else "No"}</span></td>'
#                 f'<td><span class="{details_class}">{"Yes" if row["Details Sent"] else "No"}</span></td>'
#                 f'</tr>'
#             )
#         table_html += '</table>'
#         st.markdown(table_html, unsafe_allow_html=True)
#     else:
#         st.warning("No author details available.")

# # --- Reusable Month Selector ---
# def render_month_selector(books_df):
#     unique_months = sorted(books_df['Date'].apply(lambda x: x.strftime('%B %Y')).unique(), 
#                           key=lambda x: datetime.strptime(x, '%B %Y'), reverse=False)
#     default_month = unique_months[-1]  # Most recent month
#     selected_month = st.pills("Select Month", unique_months, default=default_month, 
#                              key=f"month_selector_{st.session_state.get('section', 'writing')}", 
#                              label_visibility='collapsed')
#     return selected_month



# def calculate_working_duration(start_date, end_date, hold_periods=None):
#     """Calculate duration in working hours (09:30–18:00, Mon–Sat) between two timestamps,
#        excluding hold periods. Returns (total_days, remaining_hours) where 1 day = 8.5 hours, hours rounded."""
    
#     if pd.isna(start_date) or pd.isna(end_date):
#         return (0, 0)
#     if start_date >= end_date:
#         return (0, 0)
    
#     # Working day limits
#     work_start = time(9, 30)
#     work_end = time(18, 0)
#     work_day_hours = 8.5

#     total_minutes = 0
#     current = start_date

#     # Process hold periods
#     if hold_periods is None:
#         hold_periods = []
#     # Filter valid hold periods and ensure they are within start_date and end_date
#     valid_hold_periods = []
#     for hold_start, hold_end in hold_periods:
#         if pd.isna(hold_start) or (hold_end is not None and pd.isna(hold_end)):
#             continue
#         hold_start = max(hold_start, start_date) if pd.notnull(hold_start) else start_date
#         hold_end = min(hold_end, end_date) if pd.notnull(hold_end) else end_date
#         if hold_start < hold_end:
#             valid_hold_periods.append((hold_start, hold_end))

#     while current.date() <= end_date.date():
#         # Skip Sundays
#         if current.weekday() != 6:
#             day_start = datetime.combine(current.date(), work_start)
#             day_end = datetime.combine(current.date(), work_end)

#             actual_start = max(day_start, start_date)
#             actual_end = min(day_end, end_date)

#             if actual_start < actual_end:
#                 day_minutes = (actual_end - actual_start).total_seconds() / 60
#                 for hold_start, hold_end in valid_hold_periods:
#                     hold_start_in_day = max(hold_start, actual_start)
#                     hold_end_in_day = min(hold_end, actual_end)
#                     if hold_start_in_day < hold_end_in_day:
#                         hold_duration = (hold_end_in_day - hold_start_in_day).total_seconds() / 60
#                         day_minutes -= hold_duration
#                 if day_minutes > 0:
#                     total_minutes += day_minutes

#         current += timedelta(days=1)
#         current = current.replace(hour=0, minute=0, second=0, microsecond=0)

#     total_hours = total_minutes / 60.0
#     total_days = int(total_hours // work_day_hours)
#     remaining_hours = int(round(total_hours % work_day_hours))

#     return (total_days, remaining_hours)

# def render_worker_completion_graph(books_df, selected_month, section, holds_df=None):
#     """Render a graph and table showing completed books for a given section and month, with hold time excluded from time taken and hold time in the last column."""
    
    
#     # Convert selected_month to year and month for filtering
#     selected_month_dt = datetime.strptime(selected_month, '%B %Y')
#     target_period = pd.Timestamp(selected_month_dt).to_period('M')

#     # Filter books where {section}_by and {section}_end are not null, and {section}_end is in the selected month
#     end_col = f'{section.capitalize()} End'
#     by_col = f'{section.capitalize()} By'
#     start_col = f'{section.capitalize()} Start'
#     completed_books = books_df[
#         books_df[by_col].notnull() &
#         books_df[end_col].notnull() &
#         (books_df[end_col].dt.to_period('M') == target_period)
#     ]

#     if completed_books.empty:
#         st.warning(f"No books assigned and completed in {selected_month} for {section.capitalize()}.")
#         return

#     # Get unique workers for dropdown, add 'All' as default
#     workers = ['All'] + sorted(completed_books[by_col].unique().tolist())
    
#     # Create two columns for graph and table
#     col1, col2 = st.columns([1.3, 1], gap="medium", vertical_alignment="center")

#     with col1:
#         selected_worker = st.selectbox(
#             "",
#             workers,
#             index=0,  # Default to 'All'
#             key=f"{section}_worker_select",
#             label_visibility="collapsed"
#         )

#         # Filter data based on selected worker
#         if selected_worker != 'All':
#             completed_books = completed_books[completed_books[by_col] == selected_worker]
        
#         if completed_books.empty:
#             st.warning(f"No books completed by {selected_worker} in {selected_month} for {section.capitalize()}.")
#             return

#         # Create table for book details
#         st.write(f"##### {section.capitalize()} Completed in {selected_month} by {selected_worker}")
#         display_columns = ['Book ID', 'Title', f'{section.capitalize()} By', 'Time Taken', 'Start Date', 'Start Time', 'End Date', 'End Time', 'Hold Time'] if 'Title' in books_df.columns else ['Book ID', f'{section.capitalize()} By', 'Time Taken', 'Start Date', 'Start Time', 'End Date', 'End Time', 'Hold Time']

#         # Calculate time taken (excluding hold periods)
#         completed_books = completed_books.copy()  # Avoid modifying original dataframe
#         completed_books['Time Taken'] = completed_books.apply(
#             lambda row: calculate_working_duration(
#                 row[start_col],
#                 row[end_col],
#                 [(h['hold_start'], h['resume_time'] or row[end_col]) for _, h in holds_df[(holds_df['book_id'] == row['Book ID']) & (holds_df['section'] == section)].iterrows()] if holds_df is not None and not holds_df[(holds_df['book_id'] == row['Book ID']) & (holds_df['section'] == section)].empty else []
#             ),
#             axis=1
#         )
#         completed_books['Time Taken'] = completed_books['Time Taken'].apply(
#             lambda x: f"{x[0]}d {x[1]}h"
#         )

#         def calculate_total_hold_time(row, holds_df, end_col, section):
#             """
#             Calculate total hold time for a book in calendar days and hours.
#             Returns (total_days, remaining_hours) where 1 day = 24 hours.
#             """
#             if holds_df is None or holds_df.empty:
#                 return (0, 0)
            
#             # Filter hold periods for this book and section
#             book_holds = holds_df[(holds_df['book_id'] == row['Book ID']) & (holds_df['section'] == section)]
#             if book_holds.empty:
#                 return (0, 0)
            
#             total_minutes = 0
#             hold_periods = [
#                 (h['hold_start'], h['resume_time'] if pd.notnull(h['resume_time']) else row[end_col])
#                 for _, h in book_holds.iterrows()
#             ]
            
#             for hold_start, hold_end in hold_periods:
#                 if pd.isna(hold_start) or pd.isna(hold_end) or hold_start >= hold_end:
#                     continue
#                 # Calculate duration in calendar days (total time, not working hours)
#                 duration = (hold_end - hold_start).total_seconds() / 60
#                 total_minutes += duration
            
#             # Convert total minutes to days and hours (1 day = 24 hours)
#             total_hours = total_minutes / 60.0
#             total_days = int(total_hours // 24)
#             remaining_hours = int(round(total_hours % 24))
#             return (total_days, remaining_hours)

#         completed_books['Hold Time'] = completed_books.apply(
#             lambda row: calculate_total_hold_time(row, holds_df, end_col, section),
#             axis=1
#         )
#         completed_books['Hold Time'] = completed_books['Hold Time'].apply(
#             lambda x: f"{x[0]}d {x[1]}h" if x != (0, 0) else "0d 0h"
#         )

#         # Split Start and End into Date and Time with AM/PM format
#         completed_books['Start Date'] = completed_books[start_col].dt.strftime('%Y-%m-%d')
#         completed_books['Start Time'] = completed_books[start_col].dt.strftime('%I:%M %p')
#         completed_books['End Date'] = completed_books[end_col].dt.strftime('%Y-%m-%d')
#         completed_books['End Time'] = completed_books[end_col].dt.strftime('%I:%M %p')
        
#         st.dataframe(
#             completed_books[display_columns].rename(columns={f'{section.capitalize()} By': 'Team Member'}),
#             hide_index=True,
#             width="stretch"
#         )

#     with col2:
#         # Group by worker for the bar chart
#         worker_counts = completed_books.groupby(by_col).size().reset_index(name='Book Count')
#         if selected_worker != 'All':
#             worker_counts = worker_counts[worker_counts[by_col] == selected_worker]
        
#         if worker_counts.empty:
#             st.warning(f"No books completed by {selected_worker} in {selected_month} for {section.capitalize()}.")
#             return

#         worker_counts = worker_counts.sort_values('Book Count', ascending=False)

#         # Create Altair horizontal bar chart
#         max_count = int(worker_counts['Book Count'].max())
#         tick_values = list(range(max_count + 1))

#         bar = alt.Chart(worker_counts).mark_bar(size=31).encode(
#             x=alt.X('Book Count:Q', title='Number of Books Completed', axis=alt.Axis(values=tick_values, grid=True, gridOpacity=0.3)),
#             y=alt.Y(f'{by_col}:N', title='Team Member', sort='-x'),
#             color=alt.Color(f'{by_col}:N', scale=alt.Scale(scheme='darkgreen'), legend=None),
#             tooltip=[f'{by_col}:N', 'Book Count:Q']
#         )

#         # Add text labels at the end of the bars
#         text = bar.mark_text(
#             align='left',
#             baseline='middle',
#             dx=4,
#             color='black',
#             fontSize=10
#         ).encode(
#             text='Book Count:Q'
#         )

#         # Combine bar and text
#         chart = (bar + text).properties(
#             title="",
#             width='container',
#             height=300
#         ).configure_title(
#             fontSize=10,
#             anchor='start',
#             offset=10
#         ).configure_axis(
#             labelFontSize=14
#         )

#         # Display chart
#         st.write(f"##### {section.capitalize()} Completed in {selected_month} by {selected_worker}")
#         st.altair_chart(chart, use_container_width=True)


# from urllib.parse import urlencode, quote

# def render_metrics(books_df, selected_month, section, user_role, holds_df=None):
#     # Convert selected_month (e.g., "April 2025") to date range
#     selected_month_dt = datetime.strptime(selected_month, '%B %Y')
#     month_start = selected_month_dt.replace(day=1).date()
#     month_end = (selected_month_dt.replace(day=1) + timedelta(days=31)).replace(day=1).date() - timedelta(days=1)

#     # Filter books based on enrollment Date for metrics
#     filtered_books_metrics = books_df[(books_df['Date'] >= month_start) & (books_df['Date'] <= month_end)]

#     total_books = len(filtered_books_metrics)
    
#     # Completion and pending logic for all sections
#     completed_books = len(filtered_books_metrics[
#         filtered_books_metrics[f'{section.capitalize()} End'].notnull() & 
#         (filtered_books_metrics[f'{section.capitalize()} End'] != '0000-00-00 00:00:00')
#     ])
#     if section == "cover":
#         pending_books = len(filtered_books_metrics[
#             filtered_books_metrics['Cover Start'].isnull() | 
#             (filtered_books_metrics['Cover Start'] == '0000-00-00 00:00:00')
#         ])
#     else:
#         pending_books = len(filtered_books_metrics[
#             filtered_books_metrics[f'{section.capitalize()} Start'].isnull() | 
#             (filtered_books_metrics[f'{section.capitalize()} Start'] == '0000-00-00 00:00:00')
#         ])

#     # Render UI
#     col1, col2, col3 = st.columns([8, 1, 1], vertical_alignment="bottom")
#     with col1:
#         st.subheader(f"Metrics of {selected_month}")
#         st.caption(f"Welcome {st.session_state.username}!")
#     with col2:
#         if st.button(":material/refresh: Refresh", key=f"refresh_{section}", type="tertiary"):
#             st.cache_data.clear()
#     with col3:
#         if st.session_state.role == "user":
#             click_id = str(uuid.uuid4())
#             query_params = {
#                 "click_id": click_id,
#                 "session_id": st.session_state.session_id
#             }
#             tasks_url = get_page_url('tasks', token) + f"&{urlencode(query_params, quote_via=quote)}"
#             st.link_button(
#                 ":material/checklist: Tasks",
#                 url=tasks_url,
#                 type="tertiary"
#             )

#     # Metrics rendering
#     if section == "writing":
#         # Previous month total books
#         prev_month_dt = selected_month_dt - timedelta(days=31)
#         prev_month_start = prev_month_dt.replace(day=1).date()
#         prev_month_end = (prev_month_dt.replace(day=1) + timedelta(days=31)).replace(day=1).date() - timedelta(days=1)
#         prev_total_books = len(books_df[(books_df['Date'] >= prev_month_start) & (books_df['Date'] <= prev_month_end)])

#         # Worker-specific metrics
#         target_period = pd.Timestamp(selected_month_dt).to_period('M')
#         prev_period = pd.Timestamp(prev_month_dt).to_period('M')

#         # Filter completed books for current month
#         completed_current = books_df[
#             books_df['Writing By'].notnull() &
#             books_df['Writing End'].notnull() &
#             (books_df['Writing End'] != '0000-00-00 00:00:00') &
#             (books_df['Writing End'].dt.to_period('M') == target_period)
#         ]
#         current_worker_counts = completed_current.groupby('Writing By').size().reset_index(name='Book Count')

#         # Filter completed books for previous month
#         completed_prev = books_df[
#             books_df['Writing By'].notnull() &
#             books_df['Writing End'].notnull() &
#             (books_df['Writing End'] != '0000-00-00 00:00:00') &
#             (books_df['Writing End'].dt.to_period('M') == prev_period)
#         ]
#         prev_worker_counts = completed_prev.groupby('Writing By').size().reset_index(name='Prev Book Count')

#         # Merge counts, fill missing values with 0
#         worker_counts = current_worker_counts.merge(prev_worker_counts, on='Writing By', how='outer').fillna(0)
#         worker_counts['Book Count'] = worker_counts['Book Count'].astype(int)
#         worker_counts['Prev Book Count'] = worker_counts['Prev Book Count'].astype(int)
#         worker_num = len(worker_counts['Writing By']) + 1 
        
#         with st.container(border=True):
#             # Create list of all metrics
#             metrics = [
#                 {"label": f"Books in {selected_month}", "value": total_books, "delta": f"{prev_total_books} Last Month"},
#             ]
#             for _, row in worker_counts.iterrows():
#                 metrics.append({
#                     "label": row['Writing By'],
#                     "value": row['Book Count'],
#                     "delta": f"{row['Prev Book Count']} Last Month"
#                 })

#             # Render metrics in a grid
#             cols = st.columns(worker_num)
#             for idx, metric in enumerate(metrics):
#                 col_idx = idx % worker_num
#                 if col_idx == 0 and idx > 0:
#                     cols = st.columns(worker_num)  # Start a new row
#                 with cols[col_idx]:
#                     # Extract numeric delta value for comparison (remove " (Prev Month)" and convert to int)
#                     try:
#                         delta_value = int(metric["delta"].split(" ")[0])
#                         delta_color = "inverse" if delta_value <= 3 else "normal"  # Red for <= 3, Green for > 3
#                     except ValueError:
#                         delta_color = "normal"  # Default to normal if delta isn't numeric
#                     st.metric(
#                         label=metric["label"],
#                         value=metric["value"],
#                         delta=metric["delta"],
#                         delta_color=delta_color
#                     )
#     else:
#         # Original layout for non-writing sections
#         col1, col2, col3 = st.columns(3, border=True)
#         with col1:
#             st.metric(f"Books in {selected_month}", total_books)
#         with col2:
#             st.metric(f"{section.capitalize()} Done in {selected_month}", completed_books)
#         with col3:
#             st.metric(f"Pending in {selected_month}", pending_books)

#     # Render worker completion graph for non-Cover sections in an expander using full books_df
#     if section != "cover":
#         with st.expander(f"Show Completion Graph and Table for {section.capitalize()}, {selected_month}"):
#             render_worker_completion_graph(books_df, selected_month, section, holds_df=holds_df)
    
#     return filtered_books_metrics

# # Helper function to fetch unique names (assumed to exist or can be added)
# def fetch_unique_names(column_name, conn):
#     query = f"SELECT DISTINCT {column_name} FROM books WHERE {column_name} IS NOT NULL"
#     result = conn.query(query, show_spinner=False)
#     return sorted(result[column_name].tolist())

# # --- Helper Functions ---
# def get_status(start, end, current_date, is_in_correction=False):
#     if is_in_correction:
#         return "In Correction", None
#     if pd.isna(start) or start == '0000-00-00 00:00:00':
#         return "Pending", None
#     if pd.notna(start) and start != '0000-00-00 00:00:00' and pd.isna(end):
#         start_date = start.date() if isinstance(start, pd.Timestamp) else pd.to_datetime(start).date()
#         days = (current_date - start_date).days
#         return "Running", days
#     return "Completed", None

# def get_days_since_enrolled(enroll_date, current_date):
#     if pd.notnull(enroll_date):
#         date_enrolled = enroll_date if isinstance(enroll_date, datetime) else pd.to_datetime(enroll_date).date()
#         return (current_date - date_enrolled).days
#     return None


# def fetch_book_details(book_id, conn):
#     query = f"SELECT title, book_note FROM books WHERE book_id = {book_id}"
#     return conn.query(query, show_spinner=False)


# @st.dialog("Rate User", width='medium')
# def rate_user_dialog(book_id, conn):
#     # Fetch book title
#     book_details = fetch_book_details(book_id, conn)
#     if not book_details.empty:
#         book_title = book_details.iloc[0]['title']
#         st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
#     else:
#         st.markdown(f"### Rate User for Book ID: {book_id}")
#         st.warning("Book title not found.")
    
#     sentiment_mapping = ["one", "two", "three", "four", "five"]
#     selected = st.feedback("stars")
#     if selected is not None:
#         st.markdown(f"You selected {sentiment_mapping[selected]} star(s).")


# @st.dialog("Correction Details", width='medium')
# def correction_dialog(book_id, conn, section):
#     # IST timezone
#     IST = timezone(timedelta(hours=5, minutes=30))
    
#     # Map section to display name and database columns
#     section_config = {
#         "writing": {"display": "Writing", "by": "writing_by", "start": "writing_start", "end": "writing_end"},
#         "proofreading": {"display": "Proofreading", "by": "proofreading_by", "start": "proofreading_start", "end": "proofreading_end"},
#         "formatting": {"display": "Formatting", "by": "formatting_by", "start": "formatting_start", "end": "formatting_end"},
#         "cover": {"display": "Cover Page", "by": "cover_by", "start": "cover_start", "end": "cover_end"}
#     }
    
#     config = section_config.get(section, section_config["writing"])
#     display_name = config["display"]

#     # Fetch book title
#     query = f"SELECT title FROM books WHERE book_id = :book_id"
#     book_details = conn.query(query, params={"book_id": book_id}, show_spinner=False)
#     if not book_details.empty:
#         book_title = book_details.iloc[0]['title']
#         st.markdown(f"<h3 style='color:#4CAF50;'>{book_id} : {book_title}</h3>", unsafe_allow_html=True)
#     else:
#         book_title = "Unknown Title"
#         st.markdown(f"### {display_name} Correction Details for Book ID: {book_id}")
#         st.warning("Book title not found.")

#     # Fetch ongoing correction
#     query = """
#         SELECT correction_id, correction_start, worker, notes
#         FROM corrections
#         WHERE book_id = :book_id AND section = :section AND correction_end IS NULL
#         ORDER BY correction_start DESC
#         LIMIT 1
#     """
#     ongoing_correction = conn.query(query, params={"book_id": book_id, "section": section}, show_spinner=False)
#     is_ongoing = not ongoing_correction.empty
    
#     if is_ongoing:
#         correction_id = ongoing_correction.iloc[0]["correction_id"]
#         current_start = ongoing_correction.iloc[0]["correction_start"]
#         current_worker = ongoing_correction.iloc[0]["worker"]
#         current_notes = ongoing_correction.iloc[0]["notes"] or ""
#     else:
#         current_start = None
#         current_worker = None
#         current_notes = ""

#     # Fetch default worker if not ongoing
#     if not is_ongoing:
#         query = f"SELECT {config['by']} AS worker FROM books WHERE book_id = :book_id"
#         book_data = conn.query(query, params={"book_id": book_id}, show_spinner=False)
#         default_worker = book_data.iloc[0]["worker"] if not book_data.empty and book_data.iloc[0]["worker"] else "Select Team Member"
#     else:
#         default_worker = current_worker

#     # Fetch hold and resume status from holds table
#     hold_query = """
#         SELECT hold_start, resume_time, reason
#         FROM holds 
#         WHERE book_id = :book_id AND section = :section
#     """
#     hold_data = conn.query(hold_query, params={"book_id": book_id, "section": section}, show_spinner=False)
#     hold_start = hold_data.iloc[0]['hold_start'] if not hold_data.empty else None
#     resume_time = hold_data.iloc[0]['resume_time'] if not hold_data.empty else None
#     hold_reason = hold_data.iloc[0]['reason'] if not hold_data.empty and 'reason' in hold_data.columns else "-"
#     is_on_hold = hold_start is not None and resume_time is None

#     # Fetch section start and end from books
#     query = f"SELECT {config['start']}, {config['end']}, {config['by']} AS worker FROM books WHERE book_id = :book_id"
#     section_data = conn.query(query, params={"book_id": book_id}, show_spinner=False)
#     section_start = section_data.iloc[0][config['start']] if not section_data.empty else None
#     section_end = section_data.iloc[0][config['end']] if not section_data.empty else None
#     section_worker = section_data.iloc[0]['worker'] if not section_data.empty and section_data.iloc[0]['worker'] else "-"

#     # Collect full history events
#     events = []
#     if section_start:
#         events.append({"Time": section_start, "Event": f"{display_name} Started by {section_worker}", "Notes": "-"})
#     if hold_start:
#         events.append({"Time": hold_start, "Event": "Placed on Hold", "Notes": hold_reason})
#     if resume_time:
#         events.append({"Time": resume_time, "Event": "Resumed", "Notes": "-"})

#     # Fetch all corrections for history
#     query = """
#         SELECT correction_start AS Start, correction_end AS End, worker, notes
#         FROM corrections
#         WHERE book_id = :book_id AND section = :section
#         ORDER BY correction_start
#     """
#     corrections = conn.query(query, params={"book_id": book_id, "section": section}, show_spinner=False)
#     for idx, row in corrections.iterrows():
#         events.append({
#             "Time": row["Start"],
#             "Event": f"Correction Started by {row['worker']}",
#             "Notes": row['notes'] if pd.notnull(row['notes']) else "-"
#         })
#         if pd.notnull(row["End"]):
#             events.append({"Time": row["End"], "Event": "Correction Ended", "Notes": "-"})

#     if section_end:
#         events.append({"Time": section_end, "Event": f"{display_name} Ended", "Notes": "-"})

#     # Sort events by time
#     events.sort(key=lambda x: x["Time"])

#     # Display history in a timeline-like format
#     st.markdown(f'<div class="field-label">Full {display_name} History</div>', unsafe_allow_html=True)
#     if events:
#         for event in events:
#             time_str = event["Time"].strftime('%d %B %Y, %I:%M %p') if pd.notnull(event["Time"]) else "-"
#             event_str = event["Event"]
#             notes = event["Notes"]
#             # Use st.info for a clean, boxed appearance
#             if notes != "-":
#                 st.info(f"**{time_str}**: {event_str}  \n**Reason**: {notes}")
#             else:
#                 st.info(f"**{time_str}**: {event_str}")
#     else:
#         st.info("No history available.")

#     # Custom CSS
#     st.markdown("""
#         <style>
#         .field-label {
#             font-weight: bold;
#             margin-bottom: 5px;
#         }
#         .changed {
#             background-color: #FFF3E0;
#             padding: 2px 6px;
#             border-radius: 4px;
#         }
#         </style>
#     """, unsafe_allow_html=True)

#     # Fetch unique names
#     names = fetch_unique_names(config["by"], conn)
#     options = ["Select Team Member"] + names + ["Add New..."]

#     # Initialize session state for new worker and notes
#     if f"{section}_correction_new_worker_{book_id}" not in st.session_state:
#         st.session_state[f"{section}_correction_new_worker_{book_id}"] = ""
#     if f"{section}_correction_notes_{book_id}" not in st.session_state:
#         st.session_state[f"{section}_correction_notes_{book_id}"] = current_notes

#     # Show warning if on hold
#     if is_on_hold:
#         st.warning(f"⚠️ This section is currently on hold. Placed on hold: {hold_start.strftime('%d %B %Y, %I:%M %p IST')}")

#     if not is_ongoing:
#         # Pending: Start new correction
#         form_title = f"Start New {display_name} Correction"
#         st.markdown(f"<h4 style='color:#4CAF50;'>{form_title}</h4>", unsafe_allow_html=True)
        
#         selected_worker = st.selectbox(
#             "Team Member",
#             options,
#             index=options.index(default_worker) if default_worker in options else 0,
#             key=f"{section}_correction_select_{book_id}",
#             label_visibility="collapsed",
#             help=f"Select an existing {display_name.lower()} worker or add a new one.",
#             disabled=is_on_hold
#         )
        
#         if selected_worker == "Add New..." and not is_on_hold:
#             st.session_state[f"{section}_correction_new_worker_{book_id}"] = st.text_input(
#                 "New Team Member",
#                 value=st.session_state[f"{section}_correction_new_worker_{book_id}"],
#                 key=f"{section}_correction_new_input_{book_id}",
#                 placeholder=f"Enter new {display_name.lower()} team member name...",
#                 label_visibility="collapsed"
#             )
#             if st.session_state[f"{section}_correction_new_worker_{book_id}"].strip():
#                 worker = st.session_state[f"{section}_correction_new_worker_{book_id}"].strip()
#         elif selected_worker != "Select Team Member" and not is_on_hold:
#             worker = selected_worker
#             st.session_state[f"{section}_correction_new_worker_{book_id}"] = ""
#         else:
#             worker = None

#         notes = st.text_area(
#             "Correction Notes",
#             value=st.session_state[f"{section}_correction_notes_{book_id}"],
#             key=f"{section}_correction_notes_{book_id}",
#             placeholder=f"Enter notes about this {display_name.lower()} correction...",
#             label_visibility="collapsed",
#             help=f"Optional notes about the {display_name.lower()} correction",
#             disabled=is_on_hold
#         )

#         col1, col2, col3 = st.columns([1, 2, 1])
#         with col2:
#             if is_on_hold:
#                 st.button("▶️ Start Correction Now", type="primary", disabled=True, use_container_width=True)
#                 st.caption("Resume the section first.")
#             elif worker:
#                 if st.button("▶️ Start Correction Now", type="primary", use_container_width=True):
#                     with st.spinner(f"Starting {display_name} correction..."):
#                         sleep(1)
#                         now = datetime.now(IST)
#                         updates = {
#                             "book_id": book_id,
#                             "section": section,
#                             "correction_start": now,
#                             "worker": worker,
#                             "notes": notes if notes.strip() else None
#                         }
#                         updates = {k: v for k, v in updates.items() if v is not None}
#                         insert_fields = ", ".join(updates.keys())
#                         insert_placeholders = ", ".join([f":{key}" for key in updates.keys()])
#                         with conn.session as s:
#                             query = f"""
#                                 INSERT INTO corrections ({insert_fields})
#                                 VALUES ({insert_placeholders})
#                             """
#                             s.execute(text(query), updates)
#                             s.commit()
#                         details = (
#                             f"Book ID: {book_id}, Start: {now}, "
#                             f"Worker: {worker or 'None'}, Notes: {notes or 'None'}"
#                         )
#                         try:
#                             log_activity(
#                                 conn,
#                                 st.session_state.user_id,
#                                 st.session_state.username,
#                                 st.session_state.session_id,
#                                 f"started {section} correction",
#                                 details
#                             )
#                         except Exception as e:
#                             st.error(f"Error logging {display_name.lower()} correction details: {str(e)}")
#                         st.success(f"✔️ Started {display_name} correction")
#                         st.toast(f"✔️ Started {display_name} correction", icon="✔️", duration="long")
#                         st.session_state.pop(f"{section}_correction_new_worker_{book_id}", None)
#                         st.session_state.pop(f"{section}_correction_notes_{book_id}", None)
#                         sleep(1)
#                         st.rerun()
#             else:
#                 st.button("▶️ Start Correction Now", type="primary", disabled=True, use_container_width=True)

#     else:
#         # Ongoing correction
#         form_title = f"Ongoing {display_name} Correction"
#         st.markdown(f"<h4 style='color:#4CAF50;'>{form_title}</h4>", unsafe_allow_html=True)
        
#         col_start, col_assigned = st.columns(2)
#         with col_start:
#             st.markdown("**Started At**")
#             st.info(current_start.strftime('%d %B %Y, %I:%M %p IST') if current_start else 'None')
#         with col_assigned:
#             st.markdown("**Assigned To**")
#             st.info(current_worker or 'None')

#         st.markdown(f'<div class="field-label">Correction Notes</div>', unsafe_allow_html=True)
#         notes = st.text_area(
#             "Notes",
#             value=st.session_state[f"{section}_correction_notes_{book_id}"],
#             key=f"{section}_correction_notes_{book_id}",
#             placeholder=f"Enter notes about this {display_name.lower()} correction...",
#             label_visibility="collapsed",
#             help=f"Optional notes about the {display_name.lower()} correction"
#         )

#         col_end, col_cancel = st.columns(2)
#         with col_end:
#             if st.button(f"⏹️ End {display_name} Correction Now", type="primary", use_container_width=True):
#                 with st.spinner(f"Ending {display_name} correction..."):
#                     sleep(1)
#                     now = datetime.now(IST)
#                     updates = {
#                         "correction_end": now,
#                         "notes": notes if notes.strip() else None
#                     }
#                     updates = {k: v for k, v in updates.items() if v is not None}
#                     update_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
#                     with conn.session as s:
#                         query = f"""
#                             UPDATE corrections
#                             SET {update_clause}
#                             WHERE correction_id = :correction_id
#                         """
#                         updates["correction_id"] = correction_id
#                         s.execute(text(query), updates)
#                         s.commit()
#                     details = (
#                         f"Book ID: {book_id}, End: {now}, Notes: {notes or 'None'}"
#                     )
#                     try:
#                         log_activity(
#                             conn,
#                             st.session_state.user_id,
#                             st.session_state.username,
#                             st.session_state.session_id,
#                             f"ended {section} correction",
#                             details
#                         )
#                     except Exception as e:
#                         st.error(f"Error logging {display_name.lower()} correction details: {str(e)}")
#                     st.success(f"✔️ Ended {display_name} correction")
#                     st.toast(f"Ended {display_name} correction", icon="✔️", duration="long")
#                     st.session_state.pop(f"{section}_correction_notes_{book_id}", None)
#                     sleep(1)
#                     st.rerun()
#         with col_cancel:
#             if st.button("Cancel", type="secondary", use_container_width=True):
#                 st.session_state.pop(f"{section}_correction_notes_{book_id}", None)
#                 st.rerun()



# @st.dialog("Edit Details", width='medium')
# def edit_section_dialog(book_id, conn, section):
#     # IST timezone
#     IST = timezone(timedelta(hours=5, minutes=30))
    
#     # Map section to display name and database columns
#     section_config = {
#         "writing": {"display": "Writing", "by": "writing_by", "start": "writing_start", "end": "writing_end"},
#         "proofreading": {"display": "Proofreading", "by": "proofreading_by", "start": "proofreading_start", "end": "proofreading_end"},
#         "formatting": {"display": "Formatting", "by": "formatting_by", "start": "formatting_start", "end": "formatting_end"},
#         "cover": {
#             "display": "Cover Page",
#             "by": "cover_by",
#             "start": "cover_start",
#             "end": "cover_end"
#         }
#     }
    
#     config = section_config.get(section, section_config["writing"])
#     display_name = config["display"]

#     # Fetch book title, book note, and current book_pages
#     book_details = fetch_book_details(book_id, conn)
#     if not book_details.empty:
#         book_title = book_details.iloc[0]['title']
#         book_note = book_details.iloc[0].get('book_note', None)
#         current_book_pages = book_details.iloc[0].get('book_pages', 0)
#         st.markdown(f"### {book_id} : {book_title}")
#         st.markdown("")
#         # Display book note only if it exists
#         if book_note:
#             st.markdown("**Book Note or Instructions**")
#             st.info(book_note)
#     else:
#         book_title = "Unknown Title"
#         book_note = None
#         current_book_pages = 0
#         st.markdown(f"### {display_name} Details for Book ID: {book_id}")
#         st.warning("Book title not found.")

#     # Fetch hold and resume status from holds table
#     hold_query = """
#         SELECT hold_start, resume_time, reason 
#         FROM holds 
#         WHERE book_id = :book_id AND section = :section
#     """
#     hold_data = conn.query(hold_query, params={"book_id": book_id, "section": section}, show_spinner=False)
#     hold_start = hold_data.iloc[0]['hold_start'] if not hold_data.empty else None
#     resume_time = hold_data.iloc[0]['resume_time'] if not hold_data.empty else None
#     hold_reason = hold_data.iloc[0].get('reason', None) if not hold_data.empty else None
#     is_on_hold = hold_start is not None and resume_time is None

#     # Check if book is running (any section has start without end)
#     running_query = """
#         SELECT 
#             CASE 
#                 WHEN writing_start IS NOT NULL AND writing_end IS NULL THEN 1 
#                 WHEN proofreading_start IS NOT NULL AND proofreading_end IS NULL THEN 1 
#                 WHEN formatting_start IS NOT NULL AND formatting_start IS NULL THEN 1 
#                 WHEN cover_start IS NOT NULL AND cover_end IS NULL THEN 1 
#                 ELSE 0 
#             END AS is_running
#         FROM books 
#         WHERE book_id = :book_id
#     """
#     running_data = conn.query(running_query, params={"book_id": book_id}, show_spinner=False)
#     is_running = running_data.iloc[0]['is_running'] if not running_data.empty else False

#     # Book-level hold info (warning and hold start if on hold)
#     if is_on_hold:
#         st.warning(f"⚠️ This book is currently on hold for {display_name}. Placed on hold: {hold_start.strftime('%d %B %Y, %I:%M %p IST')}")
#         if hold_reason:
#             st.markdown("**Reason for Hold**")
#             st.info(hold_reason)

#     # Fetch current section data
#     if section == "cover":
#         query = """
#             SELECT 
#                 cover_start AS 'Cover Start', 
#                 cover_end AS 'Cover End', 
#                 cover_by AS 'Cover By'
#             FROM books 
#             WHERE book_id = :book_id
#         """
#     else:
#         query = f"""
#             SELECT {config['start']}, {config['end']}, {config['by']}, book_pages 
#             FROM books 
#             WHERE book_id = :book_id
#         """
#     book_data = conn.query(query, params={"book_id": book_id}, show_spinner=False)
#     current_data = book_data.iloc[0].to_dict() if not book_data.empty else {}

#     # Get current start, end, worker from data
#     current_start_key = "Cover Start" if section == "cover" else config['start']
#     current_end_key = "Cover End" if section == "cover" else config['end']
#     current_start = current_data.get(current_start_key)
#     current_end = current_data.get(current_end_key)
#     current_worker = current_data.get(config['by'], "")

#     # Determine section status
#     pending = current_start is None
#     running = current_start is not None and current_end is None
#     completed = current_end is not None

#     # Fetch unique names for the section
#     names = fetch_unique_names(config["by"], conn)
#     options = ["Select Team Member"] + names + ["Add New..."]

#     # Initialize session state for worker and book_pages (only for pending and completed if needed)
#     keys = [f"{section}_new_worker"]
#     if section in ["writing", "proofreading", "formatting"]:
#         keys.append("book_pages")
#     defaults = {
#         f"{section}_new_worker": "",
#         "book_pages": max(1, current_data.get("book_pages", current_book_pages)) if section in ["writing", "proofreading", "formatting"] else None
#     }
    
#     for key in keys:
#         if f"{key}_{book_id}" not in st.session_state:
#             st.session_state[f"{key}_{book_id}"] = defaults[key]

#     # Initialize session state for showing hold form
#     if f"show_hold_form_{book_id}_{section}" not in st.session_state:
#         st.session_state[f"show_hold_form_{book_id}_{section}"] = False

#     if pending:
#         # For pending: Team member selector, then centered Start button
#         selected_worker = st.selectbox(
#             f"{display_name} Team Member",
#             options,
#             index=options.index(current_worker) if current_worker in options else 0,
#             key=f"{section}_select_{book_id}",
#             help=f"Select an existing {display_name.lower()} worker or add a new one."
#         )
        
#         # Handle worker selection
#         if selected_worker == "Add New...":
#             new_worker = st.text_input(
#                 "New Team Member Name",
#                 value=st.session_state[f"{section}_new_worker_{book_id}"],
#                 key=f"{section}_new_input_{book_id}",
#                 placeholder=f"Enter new {display_name.lower()} team member name..."
#             )
#             if new_worker.strip():
#                 selected_worker = new_worker.strip()
#                 st.session_state[f"{section}_new_worker_{book_id}"] = new_worker.strip()
#         worker = selected_worker if selected_worker != "Select Team Member" and selected_worker != "Add New..." else None
#         if not worker:
#             st.warning("😊 Please select a team member to proceed.")

#         # Centered Start button (disable if on hold)
#         col1, col2, col3 = st.columns([1, 2, 1])
#         with col2:
#             if is_on_hold:
#                 st.button(f"▶️ Start {display_name} Now", type="primary", disabled=True, use_container_width=True)
#                 st.caption("Resume the book first.")
#             elif worker:
#                 if st.button(f"▶️ Start {display_name} Now", type="primary", use_container_width=True):
#                     with st.spinner(f"Starting {display_name}..."):
#                         sleep(1)
#                         try:
#                             now = datetime.now(IST)
#                             updates = {config['start']: now, config['end']: None, config['by']: worker}
#                             # Update database
#                             with conn.session as s:
#                                 set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
#                                 query = f"UPDATE books SET {set_clause} WHERE book_id = :id"
#                                 params = updates.copy()
#                                 params["id"] = int(book_id)
#                                 s.execute(text(query), params)
#                                 s.commit()
#                             # Log the start action
#                             details = f"Book ID: {book_id}, Start Time: {now}, By: {worker}"
#                             try:
#                                 log_activity(
#                                     conn,
#                                     st.session_state.user_id,
#                                     st.session_state.username,
#                                     st.session_state.session_id,
#                                     f"started {section}",
#                                     details
#                                 )
#                             except Exception as e:
#                                 st.warning(f"Warning: {display_name} started but failed to log activity: {str(e)}")
#                             st.success(f"✔️ Started {display_name}")
#                             st.toast(f"Started {display_name} for Book ID {book_id}", icon="▶️", duration='long')
#                             # Clear new worker
#                             st.session_state[f"{section}_new_worker_{book_id}"] = ""
#                             sleep(1)
#                             st.rerun()
#                         except Exception as e:
#                             st.error(f"❌ Failed to start {display_name}: {str(e)}")
#                             st.toast(f"Error starting {display_name} for Book ID {book_id}", icon="🚫", duration='long')
#             else:
#                 st.button(f"▶️ Start {display_name} Now", type="primary", disabled=True, use_container_width=True)

#     elif running:
#         # On hold running layout
#         if is_on_hold:
#             col_start, col_assigned = st.columns(2)
#             with col_start:
#                 st.markdown("**Started At**")
#                 st.info(current_start.strftime('%d %B %Y, %I:%M %p IST') if current_start else 'None')
#             with col_assigned:
#                 st.markdown("**Assigned To**")
#                 st.info(current_worker or 'None')

#             # Centered Resume button
#             col1, col2, col3 = st.columns([1, 2, 1])
#             with col2:
#                 if st.button("▶️ Resume Book", type="primary", use_container_width=True):
#                     with st.spinner("Resuming book..."):
#                         sleep(1)
#                         try:
#                             now = datetime.now(IST)
#                             updates = {"resume_time": now}
#                             with conn.session as s:
#                                 query = """
#                                     UPDATE holds 
#                                     SET resume_time = :resume_time 
#                                     WHERE book_id = :book_id AND section = :section
#                                 """
#                                 params = {"resume_time": now, "book_id": int(book_id), "section": section}
#                                 s.execute(text(query), params)
#                                 s.commit()
#                             # Log the resume action
#                             details = f"Book ID: {book_id}, Resume Time: {now}"
#                             try:
#                                 log_activity(
#                                     conn,
#                                     st.session_state.user_id,
#                                     st.session_state.username,
#                                     st.session_state.session_id,
#                                     "resumed book",
#                                     details
#                                 )
#                             except Exception as e:
#                                 st.warning(f"Warning: Book resumed but failed to log activity: {str(e)}")
#                             st.success("✔️ Book resumed")
#                             sleep(2)
#                             st.rerun()
#                         except Exception as e:
#                             st.error(f"❌ Failed to resume book: {str(e)}")
#                             st.toast(f"Error resuming Book ID {book_id}", icon="🚫", duration='long')
#         else:
#             # Normal running layout
#             col_start, col_assigned = st.columns(2)
#             with col_start:
#                 st.markdown("**Started At**")
#                 st.info(current_start.strftime('%d %B %Y, %I:%M %p IST') if current_start else 'None')
#             with col_assigned:
#                 st.markdown("**Assigned To**")
#                 st.info(current_worker or 'None')
#             # Show hold and resume info only if the book was ever held
#             if hold_start is not None:
#                 col_hold, col_resume = st.columns(2)
#                 with col_hold:
#                     st.markdown("**Placed on hold**")
#                     st.info(hold_start.strftime('%d %B %Y, %I:%M %p IST') if hold_start else 'None')
#                 with col_resume:
#                     st.markdown("**Resumed**")
#                     st.info(resume_time.strftime('%d %B %Y, %I:%M %p IST') if resume_time else 'None')

#             needs_pages = section in ["writing", "proofreading", "formatting"]
#             book_pages = None
#             current_pages = current_data.get("book_pages", 0) if needs_pages else None
#             if needs_pages:
#                 st.markdown("**Total Book Pages**")
#                 book_pages = st.number_input(
#                     "Pages",
#                     value=st.session_state[f"book_pages_{book_id}"],
#                     key=f"book_pages_{book_id}",
#                     help="Enter the total number of pages in the book.",
#                     label_visibility="collapsed"
#                 )

#             # Initialize session state for hold reason
#             if f"hold_reason_{book_id}_{section}" not in st.session_state:
#                 st.session_state[f"hold_reason_{book_id}_{section}"] = ""

#             # End and Hold buttons side by side
#             col_end, col_hold = st.columns(2)
#             with col_end:
#                 if st.button(f"⏹️ End {display_name} Now", type="primary", use_container_width=True):
#                     if needs_pages and book_pages < 10:
#                         st.error("❌ Enter Book Pages before ending.")
#                     else:
#                         with st.spinner(f"Ending {display_name}..."):
#                             sleep(1)
#                             try:
#                                 now = datetime.now(IST)
#                                 updates = {config['end']: now}
#                                 if needs_pages and book_pages is not None and current_pages != book_pages:
#                                     updates['book_pages'] = book_pages
#                                 # Update database
#                                 with conn.session as s:
#                                     set_clause = ", ".join([f"{key} = :{key}" for key in updates.keys()])
#                                     query = f"UPDATE books SET {set_clause} WHERE book_id = :id"
#                                     params = updates.copy()
#                                     params["id"] = int(book_id)
#                                     s.execute(text(query), params)
#                                     s.commit()
#                                 # Log the end action
#                                 details = f"Book ID: {book_id}, End Time: {now}, By: {current_worker}"
#                                 if needs_pages and book_pages is not None:
#                                     details += f", Pages: {book_pages}"
#                                 try:
#                                     log_activity(
#                                         conn,
#                                         st.session_state.user_id,
#                                         st.session_state.username,
#                                         st.session_state.session_id,
#                                         f"ended {section}",
#                                         details
#                                     )
#                                 except Exception as e:
#                                     st.warning(f"Warning: {display_name} ended but failed to log activity: {str(e)}")
#                                 st.success(f"✔️ Ended {display_name}")
#                                 st.toast(f"Ended {display_name} for Book ID {book_id}", icon="⏹️", duration='long')
#                                 sleep(2)
#                                 st.rerun()
#                             except Exception as e:
#                                 st.error(f"❌ Failed to end {display_name}: {str(e)}")
#                                 st.toast(f"Error ending {display_name} for Book ID {book_id}", icon="🚫", duration='long')

#             with col_hold:
#                 if st.button("⏸️ Hold Book", type="secondary", use_container_width=True):
#                     st.session_state[f"show_hold_form_{book_id}_{section}"] = True
            
#             # Render hold reason form full-width below buttons
#             if st.session_state[f"show_hold_form_{book_id}_{section}"]:
#                 with st.form(key=f"hold_form_{book_id}_{section}"):
#                     st.markdown("**Reason for Hold**")
#                     hold_reason = st.text_area(
#                         "",
#                         value=st.session_state[f"hold_reason_{book_id}_{section}"],
#                         placeholder="Enter the reason for placing this book on hold...",
#                         help="Provide a brief reason for holding the book (e.g., waiting for author feedback, resource constraints).",
#                         key=f"hold_reason_input_{book_id}_{section}",
#                         label_visibility="collapsed"
#                     )
#                     submit_hold = st.form_submit_button("Confirm Hold", type="primary", use_container_width=True)
#                     if submit_hold:
#                         if hold_reason.strip():
#                             with st.spinner("Holding book..."):
#                                 sleep(1)
#                                 try:
#                                     now = datetime.now(IST)
#                                     with conn.session as s:
#                                         query = """
#                                             INSERT INTO holds (book_id, section, hold_start, reason)
#                                             VALUES (:book_id, :section, :hold_start, :reason)
#                                             ON DUPLICATE KEY UPDATE hold_start = :hold_start, reason = :reason, resume_time = NULL
#                                         """
#                                         params = {
#                                             "book_id": int(book_id),
#                                             "section": section,
#                                             "hold_start": now,
#                                             "reason": hold_reason.strip()
#                                         }
#                                         s.execute(text(query), params)
#                                         s.commit()
#                                     # Log the hold action
#                                     details = f"Book ID: {book_id}, Hold Time: {now}, Reason: {hold_reason.strip()}"
#                                     try:
#                                         log_activity(
#                                             conn,
#                                             st.session_state.user_id,
#                                             st.session_state.username,
#                                             st.session_state.session_id,
#                                             "held book",
#                                             details
#                                         )
#                                     except Exception as e:
#                                         st.warning(f"Warning: Book held but failed to log activity: {str(e)}")
#                                     st.success("✔️ Book held")
#                                     st.toast(f"Held Book ID {book_id}", icon="⏸️", duration='long')
#                                     # Clear hold reason and hide form
#                                     st.session_state[f"hold_reason_{book_id}_{section}"] = ""
#                                     st.session_state[f"show_hold_form_{book_id}_{section}"] = False
#                                     sleep(2)
#                                     st.rerun()
#                                 except Exception as e:
#                                     st.error(f"❌ Failed to hold book: {str(e)}")
#                                     st.toast(f"Error holding Book ID {book_id}", icon="🚫", duration='long')
#                         else:
#                             st.error("❌ Please provide a reason for holding the book.")

#     else:  # completed
#         # For completed: Show start, end, worker, pages
#         st.markdown("**Started At**")
#         st.info(current_start.strftime('%d %B %Y, %I:%M %p IST') if current_start else 'None')
#         st.markdown("**Ended At**")
#         st.info(current_end.strftime('%d %B %Y, %I:%M %p IST') if current_end else 'None')
#         st.markdown(f"**Assigned To**")
#         st.info(current_worker or 'None')
#         if section in ["writing", "proofreading", "formatting"]:
#             current_pages = current_data.get("book_pages", 0)
#             st.markdown("**Total Book Pages**")
#             st.info(current_pages)


# def render_table(books_df, title, column_sizes, color, section, role, is_running=False):
#     if books_df.empty:
#         st.warning(f"No {title.lower()} books available from the last 3 months.")
#         return
    
#     cont = st.container(border=True)
#     with cont:
#         # Custom CSS for search bar and icons
#         st.markdown("""
#             <style>
#             .note-icon {
#                 font-size: 1em;
#                 color: #666;
#                 margin-left: 0.5rem;
#                 cursor: default;
#             }
#             .note-icon:hover {
#                 color: #333;
#             }
#             /* New style for history icons */
#             .history-icon {
#                 font-size: 1em;
#                 color: #8a6d3b;
#                 margin-left: 0.5rem;
#                 cursor: help;
#             }
#             </style>
#         """, unsafe_allow_html=True)

#         # Search bar for Completed table
#         filtered_df = books_df
#         if "Completed" in title:
#             with st.container():
#                 search_term = st.text_input(
#                     "",
#                     placeholder="Search by Book ID or Title",
#                     key=f"search_{section}_{title}",
#                     label_visibility="collapsed",
#                 )
#                 if search_term:
#                     filtered_df = books_df[
#                         books_df['Book ID'].astype(str).str.contains(search_term, case=False, na=False) |
#                         books_df['Title'].str.contains(search_term, case=False, na=False)
#                     ]

#         # Update count based on filtered DataFrame
#         count = len(filtered_df)
#         if count == 0 and "Completed" in title and search_term:
#             st.warning(f"No books match the search term '{search_term}' in {title.lower()} books.")
#             return

#         if "Hold" in title:
#             badge_color = 'orange'
#         elif "Running" in title:
#             badge_color = 'yellow'
#         elif "Pending" in title:
#             badge_color = 'red'
#         else:
#             badge_color = 'green'
#         st.markdown(f"<h5><span class='status-badge-{badge_color}'>{title} Books <span class='badge-count'>{count}</span></span></h5>", 
#                     unsafe_allow_html=True)
#         st.markdown('<div class="header-row">', unsafe_allow_html=True)
        
#         # Base columns
#         columns = ["Book ID", "Title", "Date", "Status"]
#         # Role-specific additional columns
#         if role == "proofreader":
#             columns.append("Writing By")
#             if not is_running:
#                 columns.append("Writing End")
#             if "Pending" in title or "Completed" in title:
#                 columns.append("Book Pages")
#             if "Pending" in title and section != "proofreading":
#                 columns.append("Rating")
#         elif role == "formatter":
#             if not is_running:
#                 columns.append("Proofreading End")
#             if "Pending" in title or "Completed" in title:
#                 columns.append("Book Pages")
#         elif role == "cover_designer":
#             if "Pending" in title or is_running:
#                 columns.extend(["Apply ISBN", "Photo", "Details"])
#         elif role == "writer":
#             if "Completed" in title:
#                 columns.append("Book Pages")
#             if "Pending" in title:
#                 columns.append("Syllabus")
#         # Adjust columns based on table type
#         is_active = is_running or ("Hold" in title)
#         if is_active:
#             if role == "cover_designer":
#                 if "Hold" in title:
#                     columns.extend(["Hold Since", "Cover By", "Action", "Details"])
#                 else:
#                     columns.extend(["Cover By", "Action", "Details"])
#             elif role == "proofreader":
#                 if "Hold" in title:
#                     columns.extend(["Hold Since", "Proofreading By", "Action"])
#                 else:
#                     columns.extend(["Proofreading Start", "Proofreading By", "Action"])
#             elif role == "writer":
#                 if "Hold" in title:
#                     columns.extend(["Hold Since", "Writing By", "Syllabus", "Action"])
#                 else:
#                     columns.extend(["Writing Start", "Writing By", "Syllabus", "Action"])
#             else:
#                 if "Hold" in title:
#                     columns.extend(["Hold Since", f"{section.capitalize()} By", "Action"])
#                 else:
#                     columns.extend([f"{section.capitalize()} Start", f"{section.capitalize()} By", "Action"])
#         elif "Pending" in title:
#             if role == "cover_designer":
#                 columns.extend(["Action", "Details"])
#             else:
#                 columns.append("Action")
#         elif "Completed" in title:
#             columns.extend([f"{section.capitalize()} By", f"{section.capitalize()} End", "Correction"])
        
#         # Validate column sizes
#         if len(column_sizes) < len(columns):
#             st.error(f"Column size mismatch in {title}: {len(columns)} columns but only {len(column_sizes)} sizes provided.")
#             return
        
#         col_configs = st.columns(column_sizes[:len(columns)])
#         for i, col in enumerate(columns):
#             with col_configs[i]:
#                 st.markdown(f'<span class="header">{col}</span>', unsafe_allow_html=True)
#         st.markdown('</div><div class="header-line"></div>', unsafe_allow_html=True)

#         # Fetch metadata for books in the current view
#         book_ids = tuple(filtered_df['Book ID'].tolist())
#         correction_book_ids = set() # For ONGOING corrections
#         correction_history_ids = set() # For ANY past correction

#         if book_ids:
#             # Fetch ongoing corrections for 'Running' table status pill
#             if is_running:
#                 query_ongoing = """
#                     SELECT book_id
#                     FROM corrections
#                     WHERE section = :section AND correction_end IS NULL AND book_id IN :book_ids
#                 """
#                 with conn.session as s:
#                     ongoing_corrections = s.execute(text(query_ongoing), {"section": section, "book_ids": book_ids}).fetchall()
#                     correction_book_ids = set(row.book_id for row in ongoing_corrections)
            
#             # Fetch all correction history for the new icon indicator
#             query_history = """
#                 SELECT DISTINCT book_id FROM corrections
#                 WHERE section = :section AND book_id IN :book_ids
#             """
#             with conn.session as s:
#                 history_results = s.execute(text(query_history), {"section": section, "book_ids": book_ids}).fetchall()
#                 correction_history_ids = {row.book_id for row in history_results}

#         current_date = datetime.now().date()
#         # Worker maps
#         if user_role == role:
#             unique_workers = [w for w in filtered_df[f'{section.capitalize()} By'].unique() if pd.notnull(w)]
#             worker_map = {worker: idx % 10 for idx, worker in enumerate(unique_workers)}
#             if role == "proofreader":
#                 unique_writing_workers = [w for w in filtered_df['Writing By'].unique() if pd.notnull(w)]
#                 writing_worker_map = {worker: idx % 10 for idx, worker in enumerate(unique_writing_workers)}
#             else:
#                 writing_worker_map = None
#         else:
#             worker_map = None
#             writing_worker_map = None

#         skip_start = "Hold" in title
#         for _, row in filtered_df.iterrows():
#             col_configs = st.columns(column_sizes[:len(columns)])
#             col_idx = 0
            
#             with col_configs[col_idx]:
#                 st.write(row['Book ID'])
#             col_idx += 1
#             with col_configs[col_idx]:
#                 title_text = row['Title']

#                 # Add indicators for hold and correction history
#                 # Check for hold history (assuming 'hold_start' column indicates this)
#                 if 'hold_start' in row and pd.notnull(row['hold_start']) and str(row['hold_start']) != '0000-00-00 00:00:00':
#                     title_text += ' <span class="history-icon" title="This book has been on hold before">:material/pause:</span>'
#                 # Check for correction history from our fetched set
#                 if row['Book ID'] in correction_history_ids:
#                     title_text += ' <span class="history-icon" title="This book has had corrections before">:material/build:</span>'
                
#                 if role == "proofreader":
#                     if pd.notnull(row.get('is_publish_only')) and row['is_publish_only'] == 1:
#                         title_text += ' <span class="pill publish-only-badge">Publish only</span>'
#                     elif pd.notnull(row.get('is_thesis_to_book')) and row['is_thesis_to_book'] == 1:
#                         title_text += ' <span class="pill thesis-to-book-badge">Thesis to Book</span>'
#                 if 'book_note' in row and pd.notnull(row['book_note']) and row['book_note'].strip():
#                     note_snippet = row['book_note'][:50] + ('...' if len(row['book_note']) > 50 else '')
#                     title_text += f' <span class="note-icon" title="{note_snippet}">:material/forum:</span>'
#                 st.markdown(title_text, unsafe_allow_html=True)
#             col_idx += 1
#             with col_configs[col_idx]:
#                 st.write(row['Date'].strftime('%Y-%m-%d') if pd.notnull(row['Date']) else "-")
#             col_idx += 1
#             with col_configs[col_idx]:
#                 if "Hold" in title:
#                     hold_start = row.get('hold_start', pd.NaT)
#                     if pd.notnull(hold_start) and str(hold_start) != '0000-00-00 00:00:00':
#                         hold_days = (current_date - hold_start.date()).days
#                         status_html = f'<span class="pill on-hold">On Hold {hold_days}d</span>'
#                     else:
#                         status_html = '<span class="pill pending">Pending</span>'
#                 else:
#                     is_in_correction = row['Book ID'] in correction_book_ids and is_running
#                     status, days = get_status(row[f'{section.capitalize()} Start'], row[f'{section.capitalize()} End'], current_date, is_in_correction)
#                     days_since = get_days_since_enrolled(row['Date'], current_date)
#                     status_html = f'<span class="pill status-{"correction" if is_in_correction else "pending" if status == "Pending" else "running" if status == "Running" else "completed"}">{status}'
#                     if days is not None and status == "Running":
#                         duration = calculate_working_duration(row[f'{section.capitalize()} Start'], datetime.now())
#                         if duration:
#                             days, hours = duration
#                             duration_str = f"{days}d" if hours == 0 else f"{days}d {hours}h"
#                             status_html += f' {duration_str}'
#                     elif "Completed" in title:
#                         start_date = row[f'{section.capitalize()} Start']
#                         end_date = row[f'{section.capitalize()} End']
#                         if pd.notnull(start_date) and pd.notnull(end_date) and start_date != '0000-00-00 00:00:00' and end_date != '0000-00-00 00:00:00':
#                             duration = calculate_working_duration(start_date, end_date)
#                             if duration:
#                                 days, hours = duration
#                                 duration_str = f"{days}d" if hours == 0 else f"{days}d {hours}h"
#                                 status_html += f' ({duration_str})'
#                             else:
#                                 status_html += ' (-)'
#                         else:
#                             status_html += ' (-)'
#                     elif not is_running and days_since is not None:
#                         status_html += f'<span class="since-enrolled">{days_since}d</span>'
#                     status_html += '</span>'
#                 st.markdown(status_html, unsafe_allow_html=True)
#             col_idx += 1
            
#             # Role-specific columns
#             if role == "proofreader":
#                 with col_configs[col_idx]:
#                     writing_by = row['Writing By']
#                     value = writing_by if pd.notnull(writing_by) and writing_by else "-"
#                     if writing_worker_map and value != "-":
#                         writing_idx = writing_worker_map.get(writing_by)
#                         class_name = f"worker-by-{writing_idx}" if writing_idx is not None else "worker-by-not"
#                         st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                     else:
#                         st.markdown(f'<span>{value}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 if "Writing End" in columns:
#                     with col_configs[col_idx]:
#                         writing_end = row['Writing End']
#                         value = writing_end.strftime('%Y-%m-%d') if not pd.isna(writing_end) and writing_end != '0000-00-00 00:00:00' else "-"
#                         st.markdown(f'<span>{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                 if "Book Pages" in columns:
#                     with col_configs[col_idx]:
#                         book_pages = row['Number of Book Pages']
#                         value = str(book_pages) if pd.notnull(book_pages) and book_pages != 0 else "-"
#                         st.markdown(f'<span>{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                 if "Rating" in columns and not is_running and section != "proofreading":
#                     with col_configs[col_idx]:
#                         if st.button("Rate", key=f"rate_{section}_{row['Book ID']}"):
#                             rate_user_dialog(row['Book ID'], conn)
#                     col_idx += 1
#             elif role == "formatter":
#                 if "Proofreading End" in columns:
#                     with col_configs[col_idx]:
#                         proofreading_end = row['Proofreading End']
#                         value = proofreading_end.strftime('%Y-%m-%d') if not pd.isna(proofreading_end) and proofreading_end != '0000-00-00 00:00:00' else "-"
#                         st.markdown(f'<span>{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                 if "Pending" in title or "Completed" in title:
#                     with col_configs[col_idx]:
#                         book_pages = row['Number of Book Pages']
#                         value = str(book_pages) if pd.notnull(book_pages) and book_pages != 0 else "-"
#                         st.markdown(f'<span>{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#             elif role == "cover_designer":
#                 if "Apply ISBN" in columns:
#                     with col_configs[col_idx]:
#                         apply_isbn = row['Apply ISBN']
#                         value = "Yes" if pd.notnull(apply_isbn) and apply_isbn else "No"
#                         class_name = "pill apply-isbn-yes" if value == "Yes" else "pill apply-isbn-no"
#                         st.markdown(f'<span class="{class_name}">{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                 if "Photo" in columns:
#                     with col_configs[col_idx]:
#                         photo_received = row['All Photos Received']
#                         value = "Yes" if pd.notnull(photo_received) and photo_received else "No"
#                         class_name = "pill apply-isbn-yes" if value == "Yes" else "pill apply-isbn-no"
#                         st.markdown(f'<span class="{class_name}">{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                 if "Details" in columns:
#                     with col_configs[col_idx]:
#                         details_sent = row['All Details Sent']
#                         value = "Yes" if pd.notnull(details_sent) and details_sent else "No"
#                         class_name = "pill apply-isbn-yes" if value == "Yes" else "pill apply-isbn-no"
#                         st.markdown(f'<span class="{class_name}">{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#             elif role == "writer":
#                 if "Book Pages" in columns:
#                     with col_configs[col_idx]:
#                         book_pages = row['Number of Book Pages']
#                         value = str(book_pages) if pd.notnull(book_pages) and book_pages != 0 else "-"
#                         st.markdown(f'<span>{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                 if "Syllabus" in columns and not is_running:
#                     with col_configs[col_idx]:
#                         syllabus_path = row['Syllabus Path']
#                         disabled = pd.isna(syllabus_path) or not syllabus_path or not os.path.exists(syllabus_path)
#                         if not disabled:
#                             with open(syllabus_path, "rb") as file:
#                                 st.download_button(
#                                     label=":material/download:",
#                                     data=file,
#                                     file_name=syllabus_path.split("/")[-1],
#                                     mime="application/pdf",
#                                     key=f"download_syllabus_{section}_{row['Book ID']}",
#                                     disabled=disabled,
#                                     help="Download Syllabus"
#                                 )
#                         else:
#                             st.download_button(
#                                 label=":material/download:",
#                                 data="",
#                                 file_name="no_syllabus.pdf",
#                                 mime="application/pdf",
#                                 key=f"download_syllabus_{section}_{row['Book ID']}",
#                                 disabled=disabled,
#                                 help="No Syllabus Available"
#                             )
#                     col_idx += 1
            
#             # Active-specific columns (Running or On Hold)
#             if is_active and user_role == role:
#                 if "Hold" in title:
#                     # Render Hold Since column for all roles
#                     with col_configs[col_idx]:
#                         hold_start = row.get('hold_start', pd.NaT)
#                         value = hold_start.strftime('%Y-%m-%d') if pd.notnull(hold_start) and str(hold_start) != '0000-00-00 00:00:00' else "-"
#                         st.write(value)
#                     col_idx += 1
#                 if role == "cover_designer":
#                     with col_configs[col_idx]:
#                         worker = row['Cover By']
#                         value = worker if pd.notnull(worker) else "Not Assigned"
#                         class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                         st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                     with col_configs[col_idx]:
#                         is_in_correction = row['Book ID'] in correction_book_ids
#                         if is_in_correction:
#                             if st.button("Edit", key=f"edit_correction_{section}_{row['Book ID']}", help="Edit ongoing correction details"):
#                                 correction_dialog(row['Book ID'], conn, section)
#                         else:
#                             if st.button("Edit", key=f"edit_main_{section}_{row['Book ID']}", help="Edit main process details"):
#                                 edit_section_dialog(row['Book ID'], conn, section)
#                     col_idx += 1
#                     with col_configs[col_idx]:
#                         if st.button("Details", key=f"details_{section}_{row['Book ID']}"):
#                             show_author_details_dialog(row['Book ID'])
#                 elif role == "proofreader":
#                     if not skip_start:
#                         with col_configs[col_idx]:
#                             start = row['Proofreading Start']
#                             if pd.notnull(start) and start != '0000-00-00 00:00:00':
#                                 st.markdown(f'<span class="pill section-start-date">{start.strftime("%d %B %Y")}</span>', unsafe_allow_html=True)
#                             else:
#                                 st.markdown(f'<span class="pill section-start-not">Not started</span>', unsafe_allow_html=True)
#                         col_idx += 1
#                     with col_configs[col_idx]:
#                         worker = row['Proofreading By']
#                         value = worker if pd.notnull(worker) else "Not Assigned"
#                         class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                         st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                     with col_configs[col_idx]:
#                         is_in_correction = row['Book ID'] in correction_book_ids
#                         if is_in_correction:
#                             if st.button("Edit", key=f"edit_correction_{section}_{row['Book ID']}", help="Edit ongoing correction details"):
#                                 correction_dialog(row['Book ID'], conn, section)
#                         else:
#                             if st.button("Edit", key=f"edit_main_{section}_{row['Book ID']}", help="Edit main process details"):
#                                 edit_section_dialog(row['Book ID'], conn, section)
#                 elif role == "writer":
#                     if not skip_start:
#                         with col_configs[col_idx]:
#                             start = row['Writing Start']
#                             if pd.notnull(start) and start != '0000-00-00 00:00:00':
#                                 st.markdown(f'<span class="pill section-start-date">{start.strftime("%d %B %Y")}</span>', unsafe_allow_html=True)
#                             else:
#                                 st.markdown(f'<span class="pill section-start-not">Not started</span>', unsafe_allow_html=True)
#                         col_idx += 1
#                     with col_configs[col_idx]:
#                         worker = row['Writing By']
#                         value = worker if pd.notnull(worker) else "Not Assigned"
#                         class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                         st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                     with col_configs[col_idx]:
#                         syllabus_path = row['Syllabus Path']
#                         disabled = pd.isna(syllabus_path) or not syllabus_path or not os.path.exists(syllabus_path)
#                         if not disabled:
#                             with open(syllabus_path, "rb") as file:
#                                 st.download_button(
#                                     label=":material/download:",
#                                     data=file,
#                                     file_name=syllabus_path.split("/")[-1],
#                                     mime="application/pdf",
#                                     key=f"download_syllabus_{section}_{row['Book ID']}_running",
#                                     disabled=disabled
#                                 )
#                         else:
#                             st.download_button(
#                                 label=":material/download:",
#                                 data="",
#                                 file_name="no_syllabus.pdf",
#                                 mime="application/pdf",
#                                 key=f"download_syllabus_{section}_{row['Book ID']}_running",
#                                 disabled=disabled
#                             )
#                     col_idx += 1
#                     with col_configs[col_idx]:
#                         is_in_correction = row['Book ID'] in correction_book_ids
#                         if is_in_correction:
#                             if st.button("Edit", key=f"edit_correction_{section}_{row['Book ID']}", help="Edit ongoing correction details"):
#                                 correction_dialog(row['Book ID'], conn, section)
#                         else:
#                             if st.button("Edit", key=f"edit_main_{section}_{row['Book ID']}", help="Edit main process details"):
#                                 edit_section_dialog(row['Book ID'], conn, section)
#                 else:
#                     if not skip_start:
#                         with col_configs[col_idx]:
#                             start = row[f'{section.capitalize()} Start']
#                             if pd.notnull(start) and start != '0000-00-00 00:00:00':
#                                 st.markdown(f'<span class="pill section-start-date">{start.strftime("%d %B %Y")}</span>', unsafe_allow_html=True)
#                             else:
#                                 st.markdown(f'<span class="pill section-start-not">Not started</span>', unsafe_allow_html=True)
#                         col_idx += 1
#                     with col_configs[col_idx]:
#                         worker = row[f'{section.capitalize()} By']
#                         value = worker if pd.notnull(worker) else "Not Assigned"
#                         class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                         st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                     with col_configs[col_idx]:
#                         is_in_correction = row['Book ID'] in correction_book_ids
#                         if is_in_correction:
#                             if st.button("Edit", key=f"edit_correction_{section}_{row['Book ID']}", help="Edit ongoing correction details"):
#                                 correction_dialog(row['Book ID'], conn, section)
#                         else:
#                             if st.button("Edit", key=f"edit_main_{section}_{row['Book ID']}", help="Edit main process details"):
#                                 edit_section_dialog(row['Book ID'], conn, section)
#             # Pending-specific column
#             elif "Pending" in title and user_role == role:
#                 if role == "cover_designer":
#                     with col_configs[col_idx]:
#                         if st.button("Edit", key=f"edit_{section}_{row['Book ID']}"):
#                             edit_section_dialog(row['Book ID'], conn, section)
#                     col_idx += 1
#                     with col_configs[col_idx]:
#                         if st.button("Details", key=f"details_{section}_{row['Book ID']}"):
#                             show_author_details_dialog(row['Book ID'])
#                 else:
#                     with col_configs[col_idx]:
#                         if st.button("Edit", key=f"edit_{section}_{row['Book ID']}"):
#                             edit_section_dialog(row['Book ID'], conn, section)
#             # Completed-specific columns
#             elif "Completed" in title:
#                 if role == "proofreader":
#                     with col_configs[col_idx]:
#                         worker = row['Proofreading By']
#                         value = worker if pd.notnull(worker) else "-"
#                         class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                         st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                 elif role == "formatter":
#                     with col_configs[col_idx]:
#                         worker = row['Formatting By']
#                         value = worker if pd.notnull(worker) else "-"
#                         class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                         st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                 elif role == "cover_designer":
#                     with col_configs[col_idx]:
#                         worker = row['Cover By']
#                         value = worker if pd.notnull(worker) else "-"
#                         class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                         st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                 elif role == "writer":
#                     with col_configs[col_idx]:
#                         worker = row['Writing By']
#                         value = worker if pd.notnull(worker) else "-"
#                         class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                         st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                 with col_configs[col_idx]:
#                     end_date = row[f'{section.capitalize()} End']
#                     value = end_date.strftime('%Y-%m-%d') if not pd.isna(end_date) and end_date != '0000-00-00 00:00:00' else "-"
#                     st.markdown(f'<span>{value}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     if st.button("Edit", key=f"correction_{section}_{row['Book ID']}"):
#                         correction_dialog(row['Book ID'], conn, section)



# def render_writing_table(books_df, title, column_sizes, conn, user_role):
#     if books_df.empty:
#         st.warning(f"No {title.lower()} books available from the last 3 months.")
#         return
    
#     cont = st.container(border=True)
#     with cont:
#         st.markdown("""
#             <style>
#             .note-icon {
#                 font-size: 1em;
#                 color: #666;
#                 margin-left: 0.5rem;
#                 cursor: default;
#             }
#             .note-icon:hover {
#                 color: #333;
#             }
#             .history-icon {
#                 font-size: 1em;
#                 color: #8a6d3b;
#                 margin-left: 0.5rem;
#                 cursor: help;
#             }
#             </style>
#         """, unsafe_allow_html=True)

#         filtered_df = books_df
#         if "Completed" in title:
#             with st.container():
#                 search_term = st.text_input(
#                     "",
#                     placeholder="Search by Book ID or Title",
#                     key=f"search_writing_{title}",
#                     label_visibility="collapsed",
#                 )
#                 if search_term:
#                     filtered_df = books_df[
#                         books_df['Book ID'].astype(str).str.contains(search_term, case=False, na=False) |
#                         books_df['Title'].str.contains(search_term, case=False, na=False)
#                     ]

#         count = len(filtered_df)
#         if count == 0 and "Completed" in title and search_term:
#             st.warning(f"No books match the search term '{search_term}' in {title.lower()} books.")
#             return

#         badge_color = 'orange' if "Hold" in title else 'yellow' if "Running" in title else 'red' if "Pending" in title else 'green'
#         st.markdown(f"<h5><span class='status-badge-{badge_color}'>{title} Books <span class='badge-count'>{count}</span></span></h5>", 
#                     unsafe_allow_html=True)
#         st.markdown('<div class="header-row">', unsafe_allow_html=True)

#         columns = ["Book ID", "Title", "Date", "Status"]
#         is_active = "Running" in title or "Hold" in title
#         if "Completed" in title:
#             columns.extend(["Book Pages", "Writing By", "Writing End", "Correction"])
#         elif "Pending" in title:
#             columns.extend(["Syllabus", "Action"])
#         elif is_active:
#             if "Hold" in title:
#                 columns.extend(["Hold Since", "Writing By", "Syllabus", "Action"])
#             else:
#                 columns.extend(["Writing Start", "Writing By", "Syllabus", "Action"])

#         if len(column_sizes) < len(columns):
#             st.error(f"Column size mismatch in {title}: {len(columns)} columns but only {len(column_sizes)} sizes provided.")
#             return

#         col_configs = st.columns(column_sizes[:len(columns)])
#         for i, col in enumerate(columns):
#             with col_configs[i]:
#                 st.markdown(f'<span class="header">{col}</span>', unsafe_allow_html=True)
#         st.markdown('</div><div class="header-line"></div>', unsafe_allow_html=True)

#         book_ids = tuple(filtered_df['Book ID'].tolist())
#         correction_book_ids = set()
#         correction_history_ids = set()
#         if book_ids:
#             if is_active:
#                 query_ongoing = """
#                     SELECT book_id
#                     FROM corrections
#                     WHERE section = 'writing' AND correction_end IS NULL AND book_id IN :book_ids
#                 """
#                 with conn.session as s:
#                     ongoing_corrections = s.execute(text(query_ongoing), {"book_ids": book_ids}).fetchall()
#                     correction_book_ids = set(row.book_id for row in ongoing_corrections)
            
#             query_history = """
#                 SELECT DISTINCT book_id FROM corrections
#                 WHERE section = 'writing' AND book_id IN :book_ids
#             """
#             with conn.session as s:
#                 history_results = s.execute(text(query_history), {"book_ids": book_ids}).fetchall()
#                 correction_history_ids = {row.book_id for row in history_results}

#         unique_workers = [w for w in filtered_df['Writing By'].unique() if pd.notnull(w)]
#         worker_map = {worker: idx % 10 for idx, worker in enumerate(unique_workers)} if user_role == "writer" else None

#         current_date = datetime.now().date()
#         for _, row in filtered_df.iterrows():
#             col_configs = st.columns(column_sizes[:len(columns)])
#             col_idx = 0

#             with col_configs[col_idx]:
#                 st.write(row['Book ID'])
#             col_idx += 1
#             with col_configs[col_idx]:
#                 title_text = row['Title']
#                 if 'hold_start' in row and pd.notnull(row['hold_start']) and str(row['hold_start']) != '0000-00-00 00:00:00':
#                     title_text += ' <span class="history-icon" title="This book has been on hold before">:material/pause:</span>'
#                 if row['Book ID'] in correction_history_ids:
#                     title_text += ' <span class="history-icon" title="This book has had corrections before">:material/build:</span>'
#                 if 'book_note' in row and pd.notnull(row['book_note']) and row['book_note'].strip():
#                     note_snippet = row['book_note'][:50] + ('...' if len(row['book_note']) > 50 else '')
#                     title_text += f' <span class="note-icon" title="{note_snippet}">:material/forum:</span>'
#                 st.markdown(title_text, unsafe_allow_html=True)
#             col_idx += 1
#             with col_configs[col_idx]:
#                 st.write(row['Date'].strftime('%Y-%m-%d') if pd.notnull(row['Date']) else "-")
#             col_idx += 1
#             with col_configs[col_idx]:
#                 if "Hold" in title:
#                     hold_start = row.get('hold_start', pd.NaT)
#                     status_html = f'<span class="pill on-hold">On Hold {(current_date - hold_start.date()).days}d</span>' if pd.notnull(hold_start) and str(hold_start) != '0000-00-00 00:00:00' else '<span class="pill pending">Pending</span>'
#                 else:
#                     is_in_correction = row['Book ID'] in correction_book_ids and is_active
#                     status, days = get_status(row['Writing Start'], row['Writing End'], current_date, is_in_correction)
#                     days_since = get_days_since_enrolled(row['Date'], current_date)
#                     status_html = f'<span class="pill status-{"correction" if is_in_correction else "pending" if status == "Pending" else "running" if status == "Running" else "completed"}">{status}'
#                     if days is not None and status == "Running":
#                         duration = calculate_working_duration(row['Writing Start'], datetime.now())
#                         if duration:
#                             days, hours = duration
#                             status_html += f' {days}d' if hours == 0 else f' {days}d {hours}h'
#                     elif "Completed" in title:
#                         duration = calculate_working_duration(row['Writing Start'], row['Writing End']) if pd.notnull(row['Writing Start']) and pd.notnull(row['Writing End']) and row['Writing Start'] != '0000-00-00 00:00:00' and row['Writing End'] != '0000-00-00 00:00:00' else None
#                         status_html += f' ({days}d {hours}h)' if duration else ' (-)'
#                     elif not is_active and days_since is not None:
#                         status_html += f'<span class="since-enrolled">{days_since}d</span>'
#                     status_html += '</span>'
#                 st.markdown(status_html, unsafe_allow_html=True)
#             col_idx += 1

#             if "Completed" in title:
#                 with col_configs[col_idx]:
#                     book_pages = row['Number of Book Pages']
#                     st.markdown(f'<span>{str(book_pages) if pd.notnull(book_pages) and book_pages != 0 else "-"}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     worker = row['Writing By']
#                     value = worker if pd.notnull(worker) else "-"
#                     class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                     st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     end_date = row['Writing End']
#                     st.markdown(f'<span>{end_date.strftime("%Y-%m-%d") if pd.notnull(end_date) and end_date != "0000-00-00 00:00:00" else "-"}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     if st.button("Edit", key=f"correction_writing_{row['Book ID']}"):
#                         correction_dialog(row['Book ID'], conn, "writing")
#             elif "Pending" in title:
#                 with col_configs[col_idx]:
#                     syllabus_path = row['Syllabus Path']
#                     disabled = pd.isna(syllabus_path) or not syllabus_path or not os.path.exists(syllabus_path)
#                     st.download_button(
#                         label=":material/download:",
#                         data=open(syllabus_path, "rb") if not disabled else "",
#                         file_name=syllabus_path.split("/")[-1] if not disabled else "no_syllabus.pdf",
#                         mime="application/pdf",
#                         key=f"download_syllabus_writing_{row['Book ID']}",
#                         disabled=disabled,
#                         help="Download Syllabus" if not disabled else "No Syllabus Available"
#                     )
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     if st.button("Edit", key=f"edit_writing_{row['Book ID']}"):
#                         edit_section_dialog(row['Book ID'], conn, "writing")
#             elif is_active:
#                 if "Hold" in title:
#                     with col_configs[col_idx]:
#                         hold_start = row.get('hold_start', pd.NaT)
#                         st.write(hold_start.strftime('%Y-%m-%d') if pd.notnull(hold_start) and str(hold_start) != '0000-00-00 00:00:00' else "-")
#                     col_idx += 1
#                 else:
#                     with col_configs[col_idx]:
#                         start = row['Writing Start']
#                         st.markdown(f'<span class="pill section-start-date">{start.strftime("%d %B %Y")}</span>' if pd.notnull(start) and start != '0000-00-00 00:00:00' else '<span class="pill section-start-not">Not started</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                 with col_configs[col_idx]:
#                     worker = row['Writing By']
#                     value = worker if pd.notnull(worker) else "Not Assigned"
#                     class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                     st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     syllabus_path = row['Syllabus Path']
#                     disabled = pd.isna(syllabus_path) or not syllabus_path or not os.path.exists(syllabus_path)
#                     st.download_button(
#                         label=":material/download:",
#                         data=open(syllabus_path, "rb") if not disabled else "",
#                         file_name=syllabus_path.split("/")[-1] if not disabled else "no_syllabus.pdf",
#                         mime="application/pdf",
#                         key=f"download_syllabus_writing_{row['Book ID']}_running",
#                         disabled=disabled,
#                         help="Download Syllabus" if not disabled else "No Syllabus Available"
#                     )
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     is_in_correction = row['Book ID'] in correction_book_ids
#                     if is_in_correction:
#                         if st.button("Edit", key=f"edit_correction_writing_{row['Book ID']}", help="Edit ongoing correction details"):
#                             correction_dialog(row['Book ID'], conn, "writing")
#                     else:
#                         if st.button("Edit", key=f"edit_main_writing_{row['Book ID']}", help="Edit main process details"):
#                             edit_section_dialog(row['Book ID'], conn, "writing")


# def render_proofreading_table(books_df, title, column_sizes, conn, user_role):
#     if books_df.empty:
#         st.warning(f"No {title.lower()} books available from the last 3 months.")
#         return
    
#     cont = st.container(border=True)
#     with cont:
#         st.markdown("""
#             <style>
#             .note-icon {
#                 font-size: 1em;
#                 color: #666;
#                 margin-left: 0.5rem;
#                 cursor: default;
#             }
#             .note-icon:hover {
#                 color: #333;
#             }
#             .history-icon {
#                 font-size: 1em;
#                 color: #8a6d3b;
#                 margin-left: 0.5rem;
#                 cursor: help;
#             }
#             </style>
#         """, unsafe_allow_html=True)

#         filtered_df = books_df
#         if "Completed" in title:
#             with st.container():
#                 search_term = st.text_input(
#                     "",
#                     placeholder="Search by Book ID or Title",
#                     key=f"search_proofreading_{title}",
#                     label_visibility="collapsed",
#                 )
#                 if search_term:
#                     filtered_df = books_df[
#                         books_df['Book ID'].astype(str).str.contains(search_term, case=False, na=False) |
#                         books_df['Title'].str.contains(search_term, case=False, na=False)
#                     ]

#         count = len(filtered_df)
#         if count == 0 and "Completed" in title and search_term:
#             st.warning(f"No books match the search term '{search_term}' in {title.lower()} books.")
#             return

#         badge_color = 'orange' if "Hold" in title else 'yellow' if "Running" in title else 'red' if "Pending" in title else 'green'
#         st.markdown(f"<h5><span class='status-badge-{badge_color}'>{title} Books <span class='badge-count'>{count}</span></span></h5>", 
#                     unsafe_allow_html=True)
#         st.markdown('<div class="header-row">', unsafe_allow_html=True)

#         columns = ["Book ID", "Title", "Date", "Status", "Writing By"]
#         is_active = "Running" in title or "Hold" in title
#         if is_active:
#             if "Hold" in title:
#                 columns.extend(["Hold Since", "Proofreading By", "Action"])
#             else:
#                 columns.extend(["Proofreading Start", "Proofreading By", "Action"])
#         elif "Pending" in title:
#             columns.extend(["Book Pages", "Rating", "Action"])
#         elif "Completed" in title:
#             columns.extend(["Writing End", "Book Pages", "Proofreading By", "Proofreading End", "Correction"])

#         if len(column_sizes) < len(columns):
#             st.error(f"Column size mismatch in {title}: {len(columns)} columns but only {len(column_sizes)} sizes provided.")
#             return

#         col_configs = st.columns(column_sizes[:len(columns)])
#         for i, col in enumerate(columns):
#             with col_configs[i]:
#                 st.markdown(f'<span class="header">{col}</span>', unsafe_allow_html=True)
#         st.markdown('</div><div class="header-line"></div>', unsafe_allow_html=True)

#         book_ids = tuple(filtered_df['Book ID'].tolist())
#         correction_book_ids = set()
#         correction_history_ids = set()
#         if book_ids:
#             if is_active:
#                 query_ongoing = """
#                     SELECT book_id
#                     FROM corrections
#                     WHERE section = 'proofreading' AND correction_end IS NULL AND book_id IN :book_ids
#                 """
#                 with conn.session as s:
#                     ongoing_corrections = s.execute(text(query_ongoing), {"book_ids": book_ids}).fetchall()
#                     correction_book_ids = set(row.book_id for row in ongoing_corrections)
            
#             query_history = """
#                 SELECT DISTINCT book_id FROM corrections
#                 WHERE section = 'proofreading' AND book_id IN :book_ids
#             """
#             with conn.session as s:
#                 history_results = s.execute(text(query_history), {"book_ids": book_ids}).fetchall()
#                 correction_history_ids = {row.book_id for row in history_results}

#         unique_workers = [w for w in filtered_df['Proofreading By'].unique() if pd.notnull(w)]
#         worker_map = {worker: idx % 10 for idx, worker in enumerate(unique_workers)} if user_role == "proofreader" else None
#         unique_writing_workers = [w for w in filtered_df['Writing By'].unique() if pd.notnull(w)]
#         writing_worker_map = {worker: idx % 10 for idx, worker in enumerate(unique_writing_workers)} if user_role == "proofreader" else None

#         current_date = datetime.now().date()
#         for _, row in filtered_df.iterrows():
#             col_configs = st.columns(column_sizes[:len(columns)])
#             col_idx = 0

#             with col_configs[col_idx]:
#                 st.write(row['Book ID'])
#             col_idx += 1
#             with col_configs[col_idx]:
#                 title_text = row['Title']
#                 if 'hold_start' in row and pd.notnull(row['hold_start']) and str(row['hold_start']) != '0000-00-00 00:00:00':
#                     title_text += ' <span class="history-icon" title="This book has been on hold before">:material/pause:</span>'
#                 if row['Book ID'] in correction_history_ids:
#                     title_text += ' <span class="history-icon" title="This book has had corrections before">:material/build:</span>'
#                 if pd.notnull(row.get('is_publish_only')) and row['is_publish_only'] == 1:
#                     title_text += ' <span class="pill publish-only-badge">Publish only</span>'
#                 elif pd.notnull(row.get('is_thesis_to_book')) and row['is_thesis_to_book'] == 1:
#                     title_text += ' <span class="pill thesis-to-book-badge">Thesis to Book</span>'
#                 if 'book_note' in row and pd.notnull(row['book_note']) and row['book_note'].strip():
#                     note_snippet = row['book_note'][:50] + ('...' if len(row['book_note']) > 50 else '')
#                     title_text += f' <span class="note-icon" title="{note_snippet}">:material/forum:</span>'
#                 st.markdown(title_text, unsafe_allow_html=True)
#             col_idx += 1
#             with col_configs[col_idx]:
#                 st.write(row['Date'].strftime('%Y-%m-%d') if pd.notnull(row['Date']) else "-")
#             col_idx += 1
#             with col_configs[col_idx]:
#                 if "Hold" in title:
#                     hold_start = row.get('hold_start', pd.NaT)
#                     status_html = f'<span class="pill on-hold">On Hold {(current_date - hold_start.date()).days}d</span>' if pd.notnull(hold_start) and str(hold_start) != '0000-00-00 00:00:00' else '<span class="pill pending">Pending</span>'
#                 else:
#                     is_in_correction = row['Book ID'] in correction_book_ids and is_active
#                     status, days = get_status(row['Proofreading Start'], row['Proofreading End'], current_date, is_in_correction)
#                     days_since = get_days_since_enrolled(row['Date'], current_date)
#                     status_html = f'<span class="pill status-{"correction" if is_in_correction else "pending" if status == "Pending" else "running" if status == "Running" else "completed"}">{status}'
#                     if days is not None and status == "Running":
#                         duration = calculate_working_duration(row['Proofreading Start'], datetime.now())
#                         if duration:
#                             days, hours = duration
#                             status_html += f' {days}d' if hours == 0 else f' {days}d {hours}h'
#                     elif "Completed" in title:
#                         duration = calculate_working_duration(row['Proofreading Start'], row['Proofreading End']) if pd.notnull(row['Proofreading Start']) and pd.notnull(row['Proofreading End']) and row['Proofreading Start'] != '0000-00-00 00:00:00' and row['Proofreading End'] != '0000-00-00 00:00:00' else None
#                         status_html += f' ({days}d {hours}h)' if duration else ' (-)'
#                     elif not is_active and days_since is not None:
#                         status_html += f'<span class="since-enrolled">{days_since}d</span>'
#                     status_html += '</span>'
#                 st.markdown(status_html, unsafe_allow_html=True)
#             col_idx += 1
#             with col_configs[col_idx]:
#                 writing_by = row['Writing By']
#                 value = writing_by if pd.notnull(writing_by) else "-"
#                 class_name = f"worker-by-{writing_worker_map.get(writing_by)}" if writing_worker_map and value != "-" else "worker-by-not"
#                 st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#             col_idx += 1

#             if is_active:
#                 if "Hold" in title:
#                     with col_configs[col_idx]:
#                         hold_start = row.get('hold_start', pd.NaT)
#                         st.write(hold_start.strftime('%Y-%m-%d') if pd.notnull(hold_start) and str(hold_start) != '0000-00-00 00:00:00' else "-")
#                     col_idx += 1
#                 else:
#                     with col_configs[col_idx]:
#                         start = row['Proofreading Start']
#                         st.markdown(f'<span class="pill section-start-date">{start.strftime("%d %B %Y")}</span>' if pd.notnull(start) and start != '0000-00-00 00:00:00' else '<span class="pill section-start-not">Not started</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                 with col_configs[col_idx]:
#                     worker = row['Proofreading By']
#                     value = worker if pd.notnull(worker) else "Not Assigned"
#                     class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                     st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     is_in_correction = row['Book ID'] in correction_book_ids
#                     if is_in_correction:
#                         if st.button("Edit", key=f"edit_correction_proofreading_{row['Book ID']}", help="Edit ongoing correction details"):
#                             correction_dialog(row['Book ID'], conn, "proofreading")
#                     else:
#                         if st.button("Edit", key=f"edit_main_proofreading_{row['Book ID']}", help="Edit main process details"):
#                             edit_section_dialog(row['Book ID'], conn, "proofreading")
#             elif "Pending" in title:
#                 with col_configs[col_idx]:
#                     book_pages = row['Number of Book Pages']
#                     st.markdown(f'<span>{str(book_pages) if pd.notnull(book_pages) and book_pages != 0 else "-"}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     if st.button("Rate", key=f"rate_proofreading_{row['Book ID']}"):
#                         rate_user_dialog(row['Book ID'], conn)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     if st.button("Edit", key=f"edit_proofreading_{row['Book ID']}"):
#                         edit_section_dialog(row['Book ID'], conn, "proofreading")
#             elif "Completed" in title:
#                 with col_configs[col_idx]:
#                     writing_end = row['Writing End']
#                     st.markdown(f'<span>{writing_end.strftime("%Y-%m-%d") if pd.notnull(writing_end) and writing_end != "0000-00-00 00:00:00" else "-"}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     book_pages = row['Number of Book Pages']
#                     st.markdown(f'<span>{str(book_pages) if pd.notnull(book_pages) and book_pages != 0 else "-"}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     worker = row['Proofreading By']
#                     value = worker if pd.notnull(worker) else "-"
#                     class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                     st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     end_date = row['Proofreading End']
#                     st.markdown(f'<span>{end_date.strftime("%Y-%m-%d") if pd.notnull(end_date) and end_date != "0000-00-00 00:00:00" else "-"}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     if st.button("Edit", key=f"correction_proofreading_{row['Book ID']}"):
#                         correction_dialog(row['Book ID'], conn, "proofreading")



# def render_formatting_table(books_df, title, column_sizes, conn, user_role):
#     if books_df.empty:
#         st.warning(f"No {title.lower()} books available from the last 3 months.")
#         return
    
#     cont = st.container(border=True)
#     with cont:
#         st.markdown("""
#             <style>
#             .note-icon {
#                 font-size: 1em;
#                 color: #666;
#                 margin-left: 0.5rem;
#                 cursor: default;
#             }
#             .note-icon:hover {
#                 color: #333;
#             }
#             .history-icon {
#                 font-size: 1em;
#                 color: #8a6d3b;
#                 margin-left: 0.5rem;
#                 cursor: help;
#             }
#             </style>
#         """, unsafe_allow_html=True)

#         filtered_df = books_df
#         if "Completed" in title:
#             with st.container():
#                 search_term = st.text_input(
#                     "",
#                     placeholder="Search by Book ID or Title",
#                     key=f"search_formatting_{title}",
#                     label_visibility="collapsed",
#                 )
#                 if search_term:
#                     filtered_df = books_df[
#                         books_df['Book ID'].astype(str).str.contains(search_term, case=False, na=False) |
#                         books_df['Title'].str.contains(search_term, case=False, na=False)
#                     ]

#         count = len(filtered_df)
#         if count == 0 and "Completed" in title and search_term:
#             st.warning(f"No books match the search term '{search_term}' in {title.lower()} books.")
#             return

#         badge_color = 'orange' if "Hold" in title else 'yellow' if "Running" in title else 'red' if "Pending" in title else 'green'
#         st.markdown(f"<h5><span class='status-badge-{badge_color}'>{title} Books <span class='badge-count'>{count}</span></span></h5>", 
#                     unsafe_allow_html=True)
#         st.markdown('<div class="header-row">', unsafe_allow_html=True)

#         columns = ["Book ID", "Title", "Date", "Status"]
#         is_active = "Running" in title or "Hold" in title
#         if is_active:
#             if "Hold" in title:
#                 columns.extend(["Hold Since", "Formatting By", "Action"])
#             else:
#                 columns.extend(["Formatting Start", "Formatting By", "Action"])
#         elif "Pending" in title:
#             columns.extend(["Book Pages", "Action"])
#         elif "Completed" in title:
#             columns.extend(["Proofreading End", "Book Pages", "Formatting By", "Formatting End", "Correction"])

#         if len(column_sizes) < len(columns):
#             st.error(f"Column size mismatch in {title}: {len(columns)} columns but only {len(column_sizes)} sizes provided.")
#             return

#         col_configs = st.columns(column_sizes[:len(columns)])
#         for i, col in enumerate(columns):
#             with col_configs[i]:
#                 st.markdown(f'<span class="header">{col}</span>', unsafe_allow_html=True)
#         st.markdown('</div><div class="header-line"></div>', unsafe_allow_html=True)

#         book_ids = tuple(filtered_df['Book ID'].tolist())
#         correction_book_ids = set()
#         correction_history_ids = set()
#         if book_ids:
#             if is_active:
#                 query_ongoing = """
#                     SELECT book_id
#                     FROM corrections
#                     WHERE section = 'formatting' AND correction_end IS NULL AND book_id IN :book_ids
#                 """
#                 with conn.session as s:
#                     ongoing_corrections = s.execute(text(query_ongoing), {"book_ids": book_ids}).fetchall()
#                     correction_book_ids = set(row.book_id for row in ongoing_corrections)
            
#             query_history = """
#                 SELECT DISTINCT book_id FROM corrections
#                 WHERE section = 'formatting' AND book_id IN :book_ids
#             """
#             with conn.session as s:
#                 history_results = s.execute(text(query_history), {"book_ids": book_ids}).fetchall()
#                 correction_history_ids = {row.book_id for row in history_results}

#         unique_workers = [w for w in filtered_df['Formatting By'].unique() if pd.notnull(w)]
#         worker_map = {worker: idx % 10 for idx, worker in enumerate(unique_workers)} if user_role == "formatter" else None

#         current_date = datetime.now().date()
#         for _, row in filtered_df.iterrows():
#             col_configs = st.columns(column_sizes[:len(columns)])
#             col_idx = 0

#             with col_configs[col_idx]:
#                 st.write(row['Book ID'])
#             col_idx += 1
#             with col_configs[col_idx]:
#                 title_text = row['Title']
#                 if 'hold_start' in row and pd.notnull(row['hold_start']) and str(row['hold_start']) != '0000-00-00 00:00:00':
#                     title_text += ' <span class="history-icon" title="This book has been on hold before">:material/pause:</span>'
#                 if row['Book ID'] in correction_history_ids:
#                     title_text += ' <span class="history-icon" title="This book has had corrections before">:material/build:</span>'
#                 if 'book_note' in row and pd.notnull(row['book_note']) and row['book_note'].strip():
#                     note_snippet = row['book_note'][:50] + ('...' if len(row['book_note']) > 50 else '')
#                     title_text += f' <span class="note-icon" title="{note_snippet}">:material/forum:</span>'
#                 st.markdown(title_text, unsafe_allow_html=True)
#             col_idx += 1
#             with col_configs[col_idx]:
#                 st.write(row['Date'].strftime('%Y-%m-%d') if pd.notnull(row['Date']) else "-")
#             col_idx += 1
#             with col_configs[col_idx]:
#                 if "Hold" in title:
#                     hold_start = row.get('hold_start', pd.NaT)
#                     status_html = f'<span class="pill on-hold">On Hold {(current_date - hold_start.date()).days}d</span>' if pd.notnull(hold_start) and str(hold_start) != '0000-00-00 00:00:00' else '<span class="pill pending">Pending</span>'
#                 else:
#                     is_in_correction = row['Book ID'] in correction_book_ids and is_active
#                     status, days = get_status(row['Formatting Start'], row['Formatting End'], current_date, is_in_correction)
#                     days_since = get_days_since_enrolled(row['Date'], current_date)
#                     status_html = f'<span class="pill status-{"correction" if is_in_correction else "pending" if status == "Pending" else "running" if status == "Running" else "completed"}">{status}'
#                     if days is not None and status == "Running":
#                         duration = calculate_working_duration(row['Formatting Start'], datetime.now())
#                         if duration:
#                             days, hours = duration
#                             status_html += f' {days}d' if hours == 0 else f' {days}d {hours}h'
#                     elif "Completed" in title:
#                         duration = calculate_working_duration(row['Formatting Start'], row['Formatting End']) if pd.notnull(row['Formatting Start']) and pd.notnull(row['Formatting End']) and row['Formatting Start'] != '0000-00-00 00:00:00' and row['Formatting End'] != '0000-00-00 00:00:00' else None
#                         status_html += f' ({days}d {hours}h)' if duration else ' (-)'
#                     elif not is_active and days_since is not None:
#                         status_html += f'<span class="since-enrolled">{days_since}d</span>'
#                     status_html += '</span>'
#                 st.markdown(status_html, unsafe_allow_html=True)
#             col_idx += 1

#             if is_active:
#                 if "Hold" in title:
#                     with col_configs[col_idx]:
#                         hold_start = row.get('hold_start', pd.NaT)
#                         st.write(hold_start.strftime('%Y-%m-%d') if pd.notnull(hold_start) and str(hold_start) != '0000-00-00 00:00:00' else "-")
#                     col_idx += 1
#                 else:
#                     with col_configs[col_idx]:
#                         start = row['Formatting Start']
#                         st.markdown(f'<span class="pill section-start-date">{start.strftime("%d %B %Y")}</span>' if pd.notnull(start) and start != '0000-00-00 00:00:00' else '<span class="pill section-start-not">Not started</span>', unsafe_allow_html=True)
#                     col_idx += 1
#                 with col_configs[col_idx]:
#                     worker = row['Formatting By']
#                     value = worker if pd.notnull(worker) else "Not Assigned"
#                     class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                     st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     is_in_correction = row['Book ID'] in correction_book_ids
#                     if is_in_correction:
#                         if st.button("Edit", key=f"edit_correction_formatting_{row['Book ID']}", help="Edit ongoing correction details"):
#                             correction_dialog(row['Book ID'], conn, "formatting")
#                     else:
#                         if st.button("Edit", key=f"edit_main_formatting_{row['Book ID']}", help="Edit main process details"):
#                             edit_section_dialog(row['Book ID'], conn, "formatting")
#             elif "Pending" in title:
#                 with col_configs[col_idx]:
#                     book_pages = row['Number of Book Pages']
#                     st.markdown(f'<span>{str(book_pages) if pd.notnull(book_pages) and book_pages != 0 else "-"}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     if st.button("Edit", key=f"edit_formatting_{row['Book ID']}"):
#                         edit_section_dialog(row['Book ID'], conn, "formatting")
#             elif "Completed" in title:
#                 with col_configs[col_idx]:
#                     proofreading_end = row['Proofreading End']
#                     st.markdown(f'<span>{proofreading_end.strftime("%Y-%m-%d") if pd.notnull(proofreading_end) and proofreading_end != "0000-00-00 00:00:00" else "-"}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     book_pages = row['Number of Book Pages']
#                     st.markdown(f'<span>{str(book_pages) if pd.notnull(book_pages) and book_pages != 0 else "-"}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     worker = row['Formatting By']
#                     value = worker if pd.notnull(worker) else "-"
#                     class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                     st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     end_date = row['Formatting End']
#                     st.markdown(f'<span>{end_date.strftime("%Y-%m-%d") if pd.notnull(end_date) and end_date != "0000-00-00 00:00:00" else "-"}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     if st.button("Edit", key=f"correction_formatting_{row['Book ID']}"):
#                         correction_dialog(row['Book ID'], conn, "formatting")


# def render_cover_design_table(books_df, title, column_sizes, conn, user_role):
#     if books_df.empty:
#         st.warning(f"No {title.lower()} books available from the last 3 months.")
#         return
    
#     cont = st.container(border=True)
#     with cont:
#         st.markdown("""
#             <style>
#             .note-icon {
#                 font-size: 1em;
#                 color: #666;
#                 margin-left: 0.5rem;
#                 cursor: default;
#             }
#             .note-icon:hover {
#                 color: #333;
#             }
#             .history-icon {
#                 font-size: 1em;
#                 color: #8a6d3b;
#                 margin-left: 0.5rem;
#                 cursor: help;
#             }
#             </style>
#         """, unsafe_allow_html=True)

#         filtered_df = books_df
#         if "Completed" in title:
#             with st.container():
#                 search_term = st.text_input(
#                     "",
#                     placeholder="Search by Book ID or Title",
#                     key=f"search_cover_design_{title}",
#                     label_visibility="collapsed",
#                 )
#                 if search_term:
#                     filtered_df = books_df[
#                         books_df['Book ID'].astype(str).str.contains(search_term, case=False, na=False) |
#                         books_df['Title'].str.contains(search_term, case=False, na=False)
#                     ]

#         count = len(filtered_df)
#         if count == 0 and "Completed" in title and search_term:
#             st.warning(f"No books match the search term '{search_term}' in {title.lower()} books.")
#             return

#         badge_color = 'orange' if "Hold" in title else 'yellow' if "Running" in title else 'red' if "Pending" in title else 'green'
#         st.markdown(f"<h5><span class='status-badge-{badge_color}'>{title} Books <span class='badge-count'>{count}</span></span></h5>", 
#                     unsafe_allow_html=True)
#         st.markdown('<div class="header-row">', unsafe_allow_html=True)

#         columns = ["Book ID", "Title", "Date", "Status"]
#         is_active = "Running" in title or "Hold" in title
#         if is_active or "Pending" in title:
#             columns.extend(["Apply ISBN", "Photo", "Details"])
#         if is_active:
#             if "Hold" in title:
#                 columns.extend(["Hold Since", "Cover By", "Action", "Details"])
#             else:
#                 columns.extend(["Cover By", "Action", "Details"])
#         elif "Completed" in title:
#             columns.extend(["Cover By", "Cover End", "Correction"])

#         if len(column_sizes) < len(columns):
#             st.error(f"Column size mismatch in {title}: {len(columns)} columns but only {len(column_sizes)} sizes provided.")
#             return

#         col_configs = st.columns(column_sizes[:len(columns)])
#         for i, col in enumerate(columns):
#             with col_configs[i]:
#                 st.markdown(f'<span class="header">{col}</span>', unsafe_allow_html=True)
#         st.markdown('</div><div class="header-line"></div>', unsafe_allow_html=True)

#         book_ids = tuple(filtered_df['Book ID'].tolist())
#         correction_book_ids = set()
#         correction_history_ids = set()
#         if book_ids:
#             if is_active:
#                 query_ongoing = """
#                     SELECT book_id
#                     FROM corrections
#                     WHERE section = 'cover_design' AND correction_end IS NULL AND book_id IN :book_ids
#                 """
#                 with conn.session as s:
#                     ongoing_corrections = s.execute(text(query_ongoing), {"book_ids": book_ids}).fetchall()
#                     correction_book_ids = set(row.book_id for row in ongoing_corrections)
            
#             query_history = """
#                 SELECT DISTINCT book_id FROM corrections
#                 WHERE section = 'cover_design' AND book_id IN :book_ids
#             """
#             with conn.session as s:
#                 history_results = s.execute(text(query_history), {"book_ids": book_ids}).fetchall()
#                 correction_history_ids = {row.book_id for row in history_results}

#         unique_workers = [w for w in filtered_df['Cover By'].unique() if pd.notnull(w)]
#         worker_map = {worker: idx % 10 for idx, worker in enumerate(unique_workers)} if user_role == "cover_designer" else None

#         current_date = datetime.now().date()
#         for _, row in filtered_df.iterrows():
#             col_configs = st.columns(column_sizes[:len(columns)])
#             col_idx = 0

#             with col_configs[col_idx]:
#                 st.write(row['Book ID'])
#             col_idx += 1
#             with col_configs[col_idx]:
#                 title_text = row['Title']
#                 if 'hold_start' in row and pd.notnull(row['hold_start']) and str(row['hold_start']) != '0000-00-00 00:00:00':
#                     title_text += ' <span class="history-icon" title="This book has been on hold before">:material/pause:</span>'
#                 if row['Book ID'] in correction_history_ids:
#                     title_text += ' <span class="history-icon" title="This book has had corrections before">:material/build:</span>'
#                 if 'book_note' in row and pd.notnull(row['book_note']) and row['book_note'].strip():
#                     note_snippet = row['book_note'][:50] + ('...' if len(row['book_note']) > 50 else '')
#                     title_text += f' <span class="note-icon" title="{note_snippet}">:material/forum:</span>'
#                 st.markdown(title_text, unsafe_allow_html=True)
#             col_idx += 1
#             with col_configs[col_idx]:
#                 st.write(row['Date'].strftime('%Y-%m-%d') if pd.notnull(row['Date']) else "-")
#             col_idx += 1
#             with col_configs[col_idx]:
#                 if "Hold" in title:
#                     hold_start = row.get('hold_start', pd.NaT)
#                     status_html = f'<span class="pill on-hold">On Hold {(current_date - hold_start.date()).days}d</span>' if pd.notnull(hold_start) and str(hold_start) != '0000-00-00 00:00:00' else '<span class="pill pending">Pending</span>'
#                 else:
#                     is_in_correction = row['Book ID'] in correction_book_ids and is_active
#                     status, days = get_status(row['Cover Start'], row['Cover End'], current_date, is_in_correction)
#                     days_since = get_days_since_enrolled(row['Date'], current_date)
#                     status_html = f'<span class="pill status-{"correction" if is_in_correction else "pending" if status == "Pending" else "running" if status == "Running" else "completed"}">{status}'
#                     if days is not None and status == "Running":
#                         duration = calculate_working_duration(row['Cover Start'], datetime.now())
#                         if duration:
#                             days, hours = duration
#                             status_html += f' {days}d' if hours == 0 else f' {days}d {hours}h'
#                     elif "Completed" in title:
#                         duration = calculate_working_duration(row['Cover Start'], row['Cover End']) if pd.notnull(row['Cover Start']) and pd.notnull(row['Cover End']) and row['Cover Start'] != '0000-00-00 00:00:00' and row['Cover End'] != '0000-00-00 00:00:00' else None
#                         status_html += f' ({days}d {hours}h)' if duration else ' (-)'
#                     elif not is_active and days_since is not None:
#                         status_html += f'<span class="since-enrolled">{days_since}d</span>'
#                     status_html += '</span>'
#                 st.markdown(status_html, unsafe_allow_html=True)
#             col_idx += 1

#             if is_active or "Pending" in title:
#                 with col_configs[col_idx]:
#                     apply_isbn = row['Apply ISBN']
#                     value = "Yes" if pd.notnull(apply_isbn) and apply_isbn else "No"
#                     class_name = "pill apply-isbn-yes" if value == "Yes" else "pill apply-isbn-no"
#                     st.markdown(f'<span class="{class_name}">{value}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     photo_received = row['All Photos Received']
#                     value = "Yes" if pd.notnull(photo_received) and photo_received else "No"
#                     class_name = "pill apply-isbn-yes" if value == "Yes" else "pill apply-isbn-no"
#                     st.markdown(f'<span class="{class_name}">{value}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     details_sent = row['All Details Sent']
#                     value = "Yes" if pd.notnull(details_sent) and details_sent else "No"
#                     class_name = "pill apply-isbn-yes" if value == "Yes" else "pill apply-isbn-no"
#                     st.markdown(f'<span class="{class_name}">{value}</span>', unsafe_allow_html=True)
#                 col_idx += 1

#             if is_active:
#                 if "Hold" in title:
#                     with col_configs[col_idx]:
#                         hold_start = row.get('hold_start', pd.NaT)
#                         st.write(hold_start.strftime('%Y-%m-%d') if pd.notnull(hold_start) and str(hold_start) != '0000-00-00 00:00:00' else "-")
#                     col_idx += 1
#                 with col_configs[col_idx]:
#                     worker = row['Cover By']
#                     value = worker if pd.notnull(worker) else "Not Assigned"
#                     class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                     st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     is_in_correction = row['Book ID'] in correction_book_ids
#                     if is_in_correction:
#                         if st.button("Edit", key=f"edit_correction_cover_design_{row['Book ID']}", help="Edit ongoing correction details"):
#                             correction_dialog(row['Book ID'], conn, "cover_design")
#                     else:
#                         if st.button("Edit", key=f"edit_main_cover_design_{row['Book ID']}", help="Edit main process details"):
#                             edit_section_dialog(row['Book ID'], conn, "cover_design")
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     if st.button("Details", key=f"details_cover_design_{row['Book ID']}"):
#                         show_author_details_dialog(row['Book ID'])
#             elif "Pending" in title:
#                 with col_configs[col_idx]:
#                     if st.button("Edit", key=f"edit_cover_design_{row['Book ID']}"):
#                         edit_section_dialog(row['Book ID'], conn, "cover_design")
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     if st.button("Details", key=f"details_cover_design_{row['Book ID']}"):
#                         show_author_details_dialog(row['Book ID'])
#             elif "Completed" in title:
#                 with col_configs[col_idx]:
#                     worker = row['Cover By']
#                     value = worker if pd.notnull(worker) else "-"
#                     class_name = f"worker-by-{worker_map.get(worker)}" if worker_map and pd.notnull(worker) else "worker-by-not"
#                     st.markdown(f'<span class="pill {class_name}">{value}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     end_date = row['Cover End']
#                     st.markdown(f'<span>{end_date.strftime("%Y-%m-%d") if pd.notnull(end_date) and end_date != "0000-00-00 00:00:00" else "-"}</span>', unsafe_allow_html=True)
#                 col_idx += 1
#                 with col_configs[col_idx]:
#                     if st.button("Edit", key=f"correction_cover_design_{row['Book ID']}"):
#                         correction_dialog(row['Book ID'], conn, "cover_design")

# # --- Section Configuration ---
# sections = {
#     "writing": {"role": "writer", "color": "unused"},
#     "proofreading": {"role": "proofreader", "color": "unused"},
#     "formatting": {"role": "formatter", "color": "unused"},
#     "cover": {"role": "cover_designer", "color": "unused"}
# }

# def old_code():
#     for section, config in sections.items():
#         if user_role == config["role"] or user_role == "admin":
#             st.session_state['section'] = section
#             books_df = fetch_books(months_back=4, section=section)
#             holds_df = fetch_holds(section=section)  # Fetch holds_df for the section
            
#             # Fetch books with ongoing corrections
#             query = """
#                 SELECT DISTINCT book_id
#                 FROM corrections
#                 WHERE section = :section AND correction_end IS NULL
#             """
#             ongoing_corrections = conn.query(query, params={"section": section}, show_spinner=False)
#             ongoing_correction_ids = set(ongoing_corrections["book_id"].tolist())
            
#             not_on_hold_condition = (books_df['hold_start'].isnull() | books_df['resume_time'].notnull())
            
#             if section == "writing":
#                 running_books = books_df[
#                     ((books_df['Writing Start'].notnull() & 
#                     books_df['Writing End'].isnull()) |
#                     books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 on_hold_books = books_df[
#                     (books_df['hold_start'].notnull() & 
#                     books_df['resume_time'].isnull())
#                 ]
#                 pending_books = books_df[
#                     (books_df['Writing Start'].isnull()) &
#                     (books_df['Is Publish Only'] != 1) &
#                     (books_df['Is Thesis to Book'] != 1) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 completed_books = books_df[
#                     (books_df['Writing End'].notnull()) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#             elif section == "proofreading":
#                 running_books = books_df[
#                     ((books_df['Proofreading Start'].notnull() & 
#                     books_df['Proofreading End'].isnull()) |
#                     books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 on_hold_books = books_df[
#                     (books_df['hold_start'].notnull() & 
#                     books_df['resume_time'].isnull())
#                 ]
#                 pending_books = books_df[
#                     ((books_df['Writing End'].notnull()) | 
#                     (books_df['Is Publish Only'] == 1) | 
#                     (books_df['Is Thesis to Book'] == 1)) &
#                     (books_df['Proofreading Start'].isnull()) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 completed_books = books_df[
#                     (books_df['Proofreading End'].notnull()) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#             elif section == "formatting":
#                 running_books = books_df[
#                     ((books_df['Formatting Start'].notnull() & 
#                     books_df['Formatting End'].isnull()) |
#                     books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 on_hold_books = books_df[
#                     (books_df['hold_start'].notnull() & 
#                     books_df['resume_time'].isnull())
#                 ]
#                 pending_books = books_df[
#                     (books_df['Proofreading End'].notnull()) &
#                     (books_df['Formatting Start'].isnull()) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 completed_books = books_df[
#                     (books_df['Formatting End'].notnull()) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#             elif section == "cover":
#                 running_books = books_df[
#                     ((books_df['Cover Start'].notnull() & 
#                     books_df['Cover End'].isnull()) |
#                     books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 on_hold_books = books_df[
#                     (books_df['hold_start'].notnull() & 
#                     books_df['resume_time'].isnull())
#                 ]
#                 pending_books = books_df[
#                     (books_df['Cover Start'].isnull()) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 completed_books = books_df[
#                     (books_df['Cover End'].notnull()) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]

#             # Sort tables
#             pending_books = pending_books.sort_values(by='Date', ascending=True)
#             on_hold_books = on_hold_books.sort_values(by='hold_start', ascending=True)

#             # Column sizes
#             if section == "writing":
#                 column_sizes_running = [0.7, 5.2, 1, 1.3, 1.3, 1.2, 1, 1]
#                 column_sizes_on_hold = [0.7, 5.2, 1, 1, 1, 1.2, 1, 1]
#                 column_sizes_pending = [0.7, 5.5, 1, 1, 0.8, 1]
#                 column_sizes_completed = [0.7, 5, 1, 1.3, 1, 1, 1, 1]
#             elif section == "proofreading":
#                 column_sizes_running = [0.7, 5, 1, 1.2, 0.9, 1.6, 1.2, 1]
#                 column_sizes_on_hold = [0.7, 5, 1, 1.2, 0.9, 1, 1.2, 1]
#                 column_sizes_pending = [0.8, 5.5, 1, 1.2, 1, 1, 1, 0.8]
#                 column_sizes_completed = [0.7, 3, 1, 1.3, 1.1, 1, 1, 1, 1, 1]
#             elif section == "formatting":
#                 column_sizes_running = [0.7, 5.5, 1, 1, 1.2, 1.2, 1]
#                 column_sizes_on_hold = [0.7, 5.5, 1, 1, 1, 1.2, 1]
#                 column_sizes_pending = [0.7, 5.5, 1, 1, 1.2, 1, 1]
#                 column_sizes_completed = [0.7, 3, 1, 1.3, 1.2, 1, 1, 1, 1]
#             elif section == "cover":
#                 column_sizes_running = [0.8, 5, 1.2, 1.3, 1, 1, 1, 1, 1, 1]
#                 column_sizes_on_hold = [0.8, 3, 1.1, 1.2, 1, 1, 1, 1, 1, 1, 1]
#                 column_sizes_pending = [0.8, 5.5, 1, 1.2, 1, 1, 1, 0.8, 1]
#                 column_sizes_completed = [0.7, 5.5, 1, 1.5, 1.3, 1.3, 1, 1]

#             # Initialize session state for completed table visibility
#             if f"show_{section}_completed" not in st.session_state:
#                 st.session_state[f"show_{section}_completed"] = False

#             selected_month = render_month_selector(books_df)
#             if selected_month is None:
#                 st.warning("Please select a month to view metrics.")
#                 st.stop()
#             # Pass holds_df to render_metrics
#             render_metrics(books_df, selected_month, section, config["role"], holds_df=holds_df)
#             render_table(running_books, f"{section.capitalize()} Running", column_sizes_running, config["color"], section, config["role"], is_running=True)
#             render_table(on_hold_books, f"{section.capitalize()} Hold", column_sizes_on_hold, config["color"], section, config["role"], is_running=True)
#             render_table(pending_books, f"{section.capitalize()} Pending", column_sizes_pending, config["color"], section, config["role"], is_running=False)
            
#             # Show completed table toggle
#             if st.button(f"Show {section.capitalize()} Completed Books", key=f"show_{section}_completed_button"):
#                 st.session_state[f"show_{section}_completed"] = not st.session_state[f"show_{section}_completed"]
            
#             if st.session_state[f"show_{section}_completed"]:
#                 render_table(completed_books, f"{section.capitalize()} Completed", column_sizes_completed, config["color"], section, config["role"], is_running=False)


# def new_code():
#     for section, config in sections.items():
#         if user_role == config["role"] or user_role == "admin":
#             st.session_state['section'] = section
#             books_df = fetch_books(months_back=4, section=section)
#             holds_df = fetch_holds(section=section)  # Fetch holds_df for the section
            
#             # Fetch books with ongoing corrections
#             query = """
#                 SELECT DISTINCT book_id
#                 FROM corrections
#                 WHERE section = :section AND correction_end IS NULL
#             """
#             ongoing_corrections = conn.query(query, params={"section": section}, show_spinner=False)
#             ongoing_correction_ids = set(ongoing_corrections["book_id"].tolist())
            
#             not_on_hold_condition = (books_df['hold_start'].isnull() | books_df['resume_time'].notnull())
            
#             if section == "writing":
#                 running_books = books_df[
#                     ((books_df['Writing Start'].notnull() & 
#                     books_df['Writing End'].isnull()) |
#                     books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 on_hold_books = books_df[
#                     (books_df['hold_start'].notnull() & 
#                     books_df['resume_time'].isnull())
#                 ]
#                 pending_books = books_df[
#                     (books_df['Writing Start'].isnull()) &
#                     (books_df['Is Publish Only'] != 1) &
#                     (books_df['Is Thesis to Book'] != 1) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 completed_books = books_df[
#                     (books_df['Writing End'].notnull()) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#             elif section == "proofreading":
#                 running_books = books_df[
#                     ((books_df['Proofreading Start'].notnull() & 
#                     books_df['Proofreading End'].isnull()) |
#                     books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 on_hold_books = books_df[
#                     (books_df['hold_start'].notnull() & 
#                     books_df['resume_time'].isnull())
#                 ]
#                 pending_books = books_df[
#                     ((books_df['Writing End'].notnull()) | 
#                     (books_df['Is Publish Only'] == 1) | 
#                     (books_df['Is Thesis to Book'] == 1)) &
#                     (books_df['Proofreading Start'].isnull()) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 completed_books = books_df[
#                     (books_df['Proofreading End'].notnull()) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#             elif section == "formatting":
#                 running_books = books_df[
#                     ((books_df['Formatting Start'].notnull() & 
#                     books_df['Formatting End'].isnull()) |
#                     books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 on_hold_books = books_df[
#                     (books_df['hold_start'].notnull() & 
#                     books_df['resume_time'].isnull())
#                 ]
#                 pending_books = books_df[
#                     (books_df['Proofreading End'].notnull()) &
#                     (books_df['Formatting Start'].isnull()) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 completed_books = books_df[
#                     (books_df['Formatting End'].notnull()) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#             elif section == "cover":
#                 running_books = books_df[
#                     ((books_df['Cover Start'].notnull() & 
#                     books_df['Cover End'].isnull()) |
#                     books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 on_hold_books = books_df[
#                     (books_df['hold_start'].notnull() & 
#                     books_df['resume_time'].isnull())
#                 ]
#                 pending_books = books_df[
#                     (books_df['Cover Start'].isnull()) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]
#                 completed_books = books_df[
#                     (books_df['Cover End'].notnull()) &
#                     (~books_df['Book ID'].isin(ongoing_correction_ids)) &
#                     not_on_hold_condition
#                 ]

#             # Sort tables
#             pending_books = pending_books.sort_values(by='Date', ascending=True)
#             on_hold_books = on_hold_books.sort_values(by='hold_start', ascending=True)

#             # Column sizes
#             if section == "writing":
#                 column_sizes_running = [0.7, 5.2, 1, 1.3, 1.3, 1.2, 1, 1]
#                 column_sizes_on_hold = [0.7, 5.2, 1, 1, 1, 1.2, 1, 1]
#                 column_sizes_pending = [0.7, 5.5, 1, 1, 0.8, 1]
#                 column_sizes_completed = [0.7, 5, 1, 1.3, 1, 1, 1, 1]
#             elif section == "proofreading":
#                 column_sizes_running = [0.7, 5, 1, 1.2, 0.9, 1.6, 1.2, 1]
#                 column_sizes_on_hold = [0.7, 5, 1, 1.2, 0.9, 1, 1.2, 1]
#                 column_sizes_pending = [0.8, 5.5, 1, 1.2, 1, 1, 1, 0.8]
#                 column_sizes_completed = [0.7, 3, 1, 1.3, 1.1, 1, 1, 1, 1, 1]
#             elif section == "formatting":
#                 column_sizes_running = [0.7, 5.5, 1, 1, 1.2, 1.2, 1]
#                 column_sizes_on_hold = [0.7, 5.5, 1, 1, 1, 1.2, 1]
#                 column_sizes_pending = [0.7, 5.5, 1, 1, 1.2, 1, 1]
#                 column_sizes_completed = [0.7, 3, 1, 1.3, 1.2, 1, 1, 1, 1]
#             elif section == "cover":
#                 column_sizes_running = [0.8, 5, 1.2, 1.3, 1, 1, 1, 1, 1, 1]
#                 column_sizes_on_hold = [0.8, 3, 1.1, 1.2, 1, 1, 1, 1, 1, 1, 1]
#                 column_sizes_pending = [0.8, 5.5, 1, 1.2, 1, 1, 1, 0.8, 1]
#                 column_sizes_completed = [0.7, 5.5, 1, 1.5, 1.3, 1.3, 1, 1]

#             # Initialize session state for completed table visibility
#             if f"show_{section}_completed" not in st.session_state:
#                 st.session_state[f"show_{section}_completed"] = False

#             selected_month = render_month_selector(books_df)
#             if selected_month is None:
#                 st.warning("Please select a month to view metrics.")
#                 st.stop()
#             # Pass holds_df to render_metrics
#             render_metrics(books_df, selected_month, section, config["role"], holds_df=holds_df)

#             # Call the appropriate role-specific render function
#             if section == "writing":
#                 render_writing_table(running_books, f"{section.capitalize()} Running", column_sizes_running, conn, user_role)
#                 render_writing_table(on_hold_books, f"{section.capitalize()} Hold", column_sizes_on_hold, conn, user_role)
#                 render_writing_table(pending_books, f"{section.capitalize()} Pending", column_sizes_pending, conn, user_role)
#                 if st.session_state[f"show_{section}_completed"]:
#                     render_writing_table(completed_books, f"{section.capitalize()} Completed", column_sizes_completed, conn, user_role)
#             elif section == "proofreading":
#                 render_proofreading_table(running_books, f"{section.capitalize()} Running", column_sizes_running, conn, user_role)
#                 render_proofreading_table(on_hold_books, f"{section.capitalize()} Hold", column_sizes_on_hold, conn, user_role)
#                 render_proofreading_table(pending_books, f"{section.capitalize()} Pending", column_sizes_pending, conn, user_role)
#                 if st.session_state[f"show_{section}_completed"]:
#                     render_proofreading_table(completed_books, f"{section.capitalize()} Completed", column_sizes_completed, conn, user_role)
#             elif section == "formatting":
#                 render_formatting_table(running_books, f"{section.capitalize()} Running", column_sizes_running, conn, user_role)
#                 render_formatting_table(on_hold_books, f"{section.capitalize()} Hold", column_sizes_on_hold, conn, user_role)
#                 render_formatting_table(pending_books, f"{section.capitalize()} Pending", column_sizes_pending, conn, user_role)
#                 if st.session_state[f"show_{section}_completed"]:
#                     render_formatting_table(completed_books, f"{section.capitalize()} Completed", column_sizes_completed, conn, user_role)
#             elif section == "cover":
#                 render_cover_design_table(running_books, f"{section.capitalize()} Running", column_sizes_running, conn, user_role)
#                 render_cover_design_table(on_hold_books, f"{section.capitalize()} Hold", column_sizes_on_hold, conn, user_role)
#                 render_cover_design_table(pending_books, f"{section.capitalize()} Pending", column_sizes_pending, conn, user_role)
#                 if st.session_state[f"show_{section}_completed"]:
#                     render_cover_design_table(completed_books, f"{section.capitalize()} Completed", column_sizes_completed, conn, user_role)

#             # Show completed table toggle
#             if st.button(f"Show {section.capitalize()} Completed Books", key=f"show_{section}_completed_button"):
#                 st.session_state[f"show_{section}_completed"] = not st.session_state[f"show_{section}_completed"]

# #old_code()

# new_code()

# timeline_app.py

# timeline_app.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text

# --- 1. PAGE CONFIGURATION & STYLING ---

st.set_page_config(
    page_title="Book Production Timeline",
    page_icon="📚",
    layout="wide"
)

def load_css():
    """Injects custom CSS for styling the timeline and metrics."""
    st.markdown("""
        <style>
            /* Main container for the app */
            .main .block-container {
                padding-top: 2rem;
                padding-left: 2rem;
                padding-right: 2rem;
            }

            /* Sidebar styling */
            [data-testid="stSidebar"] {
                background-color: #f0f2f6;
            }
            
            /* Style for Streamlit's native metric component */
            [data-testid="stMetric"] {
                background-color: #FFFFFF;
                border: 1px solid #dee2e6;
                padding: 1rem;
                border-radius: 8px;
                border-left: 5px solid #0d6efd;
                box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            }

            /* Timeline container */
            .timeline-container {
                border-left: 3px solid #6c757d;
                padding: 1rem 0 1rem 2rem;
                position: relative;
            }

            /* Individual timeline item */
            .timeline-item {
                margin-bottom: 2rem;
                position: relative;
            }

            /* Icon for each timeline item */
            .timeline-item::before {
                content: attr(data-icon);
                position: absolute;
                left: -45px;
                top: 0px;
                font-size: 1.8rem;
                background-color: #ffffff;
                border-radius: 50%;
                width: 35px;
                height: 35px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .timeline-content {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 1rem 1.5rem;
                box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            }

            .timeline-content h4 {
                color: #0d6efd;
                margin-bottom: 0.25rem;
                font-weight: 600;
            }

            .timeline-content p {
                margin-bottom: 0.25rem;
                color: #495057;
            }
            
            .timeline-content .reason {
                font-style: italic;
                color: #6c757d;
                border-left: 3px solid #adb5bd;
                padding-left: 10px;
                margin-top: 5px;
            }

            .stage-header {
                font-size: 2rem;
                font-weight: bold;
                margin-bottom: 1rem;
                color: #343a40;
                border-bottom: 2px solid #0d6efd;
                padding-bottom: 0.5rem;
            }
        </style>
    """, unsafe_allow_html=True)

load_css()

# --- 2. DATABASE CONNECTION & DATA FETCHING ---

def connect_db():
    """Connects to the database using Streamlit's connection management."""
    try:
        @st.cache_resource
        def get_connection():
            return st.connection('mysql', type='sql')
        return get_connection()
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

def get_all_employees(conn):
    """Fetches a unique list of all employees from all relevant roles."""
    query = """
        SELECT DISTINCT employee FROM (
            SELECT writing_by AS employee FROM books WHERE writing_by IS NOT NULL
            UNION
            SELECT proofreading_by AS employee FROM books WHERE proofreading_by IS NOT NULL
            UNION
            SELECT formatting_by AS employee FROM books WHERE formatting_by IS NOT NULL
            UNION
            SELECT cover_by AS employee FROM books WHERE cover_by IS NOT NULL
            UNION
            SELECT worker AS employee FROM corrections WHERE worker IS NOT NULL
        ) AS all_employees
        ORDER BY employee;
    """
    try:
        df = conn.query(query, ttl=3600)
        return df['employee'].tolist()
    except Exception as e:
        st.error(f"Error fetching employees: {e}")
        return []

def get_employee_books_for_month(conn, employee, start_date, end_date):
    """Fetches books an employee has worked on in the current month."""
    query = """
        SELECT book_id, title
        FROM books
        WHERE
            (
                writing_by = :employee OR
                proofreading_by = :employee OR
                formatting_by = :employee OR
                cover_by = :employee OR
                book_id IN (SELECT book_id FROM corrections WHERE worker = :employee)
            )
            AND
            (
                (writing_start BETWEEN :start_date AND :end_date) OR
                (writing_end BETWEEN :start_date AND :end_date) OR
                (proofreading_start BETWEEN :start_date AND :end_date) OR
                (formatting_start BETWEEN :start_date AND :end_date) OR
                (cover_start BETWEEN :start_date AND :end_date)
            )
        ORDER BY title;
    """
    params = {"employee": employee, "start_date": start_date, "end_date": end_date}
    try:
        df = conn.query(query, params=params)
        return df
    except Exception as e:
        st.error(f"Error fetching books for employee: {e}")
        return pd.DataFrame()

def get_book_data(conn, book_id):
    """Fetches all related data for a single book."""
    queries = {
        "details": "SELECT * FROM books WHERE book_id = :book_id",
        "holds": "SELECT * FROM holds WHERE book_id = :book_id ORDER BY hold_start",
        "corrections": "SELECT * FROM corrections WHERE book_id = :book_id ORDER BY correction_start"
    }
    data = {}
    try:
        for key, query in queries.items():
            data[key] = conn.query(query, params={"book_id": book_id}, ttl=60)
    except Exception as e:
        st.error(f"Error fetching book data: {e}")
        return None
    return data

# --- 3. HELPER & CALCULATION FUNCTIONS ---

def format_timedelta(td: timedelta):
    """Formats a timedelta object into a human-readable string."""
    if td is None or td.total_seconds() < 0:
        return "N/A"
    
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
        
    return " ".join(parts) if parts else "0m"

def calculate_stage_metrics(stage_name, details, holds, corrections):
    """Calculates all key metrics for a single production stage."""
    start_time = pd.to_datetime(details[f'{stage_name}_start'].iloc[0])
    end_time = pd.to_datetime(details[f'{stage_name}_end'].iloc[0])
    
    metrics = {
        'total_duration': None,
        'paused_duration': timedelta(0),
        'effective_duration': None,
        'correction_duration': timedelta(0),
        'timeline': []
    }
    
    # Return early if stage hasn't started
    if pd.isna(start_time):
        return None, "Not Started"

    # Add start event to timeline
    metrics['timeline'].append({
        'time': start_time,
        'type': 'Start',
        'icon': '▶️',
        'details': f"{stage_name.capitalize()} process started."
    })

    # Filter holds and corrections for the current stage
    stage_holds = holds[holds['section'] == stage_name]
    stage_corrections = corrections[corrections['section'] == stage_name]

    # Calculate paused time and add hold/resume events to timeline
    for _, row in stage_holds.iterrows():
        hold_start = pd.to_datetime(row['hold_start'])
        resume_time = pd.to_datetime(row['resume_time'])
        if pd.notna(hold_start) and pd.notna(resume_time):
            pause_delta = resume_time - hold_start
            metrics['paused_duration'] += pause_delta
            metrics['timeline'].append({
                'time': hold_start,
                'type': 'Paused',
                'icon': '⏸️',
                'details': f"Paused for: {row.get('reason', 'No reason specified')}. Duration: {format_timedelta(pause_delta)}"
            })
            metrics['timeline'].append({
                'time': resume_time,
                'type': 'Resumed',
                'icon': '🔄',
                'details': "Work resumed."
            })

    # Calculate correction time and add correction events
    for _, row in stage_corrections.iterrows():
        corr_start = pd.to_datetime(row['correction_start'])
        corr_end = pd.to_datetime(row['correction_end'])
        if pd.notna(corr_start) and pd.notna(corr_end):
            corr_delta = corr_end - corr_start
            metrics['correction_duration'] += corr_delta
            metrics['timeline'].append({
                'time': corr_start,
                'type': 'Correction',
                'icon': '✍️',
                'details': f"Correction started by {row['worker']}. Notes: {row.get('notes', 'N/A')}"
            })
            metrics['timeline'].append({
                'time': corr_end,
                'type': 'Correction End',
                'icon': '✅',
                'details': f"Correction finished. Duration: {format_timedelta(corr_delta)}"
            })

    # Check stage status and calculate final metrics
    if pd.isna(end_time):
        status = "In Progress"
        now = pd.to_datetime(datetime.now())
        metrics['total_duration'] = now - start_time
        metrics['effective_duration'] = metrics['total_duration'] - metrics['paused_duration']
    else:
        status = "Completed"
        metrics['total_duration'] = end_time - start_time
        metrics['effective_duration'] = metrics['total_duration'] - metrics['paused_duration']
        metrics['timeline'].append({
            'time': end_time,
            'type': 'End',
            'icon': '🏁',
            'details': f"{stage_name.capitalize()} process finished."
        })

    # Sort timeline chronologically
    metrics['timeline'].sort(key=lambda x: x['time'])
    
    return metrics, status

# --- 4. UI DISPLAY FUNCTIONS ---

def display_timeline(book_data):
    """Renders the complete timeline and metrics for a selected book."""
    if not book_data or book_data['details'].empty:
        st.warning("No data found for this book.")
        return

    details = book_data['details']
    holds = book_data['holds']
    corrections = book_data['corrections']

    st.header(f"Timeline for: *{details['title'].iloc[0]}*")
    st.markdown("---")

    stages = ['writing', 'proofreading', 'formatting', 'cover']
    stage_icons = {'writing': '🖋️', 'proofreading': '🧐', 'formatting': '🎨', 'cover': '🖼️'}
    
    total_effective_time = timedelta(0)

    for stage in stages:
        employee = details[f'{stage}_by'].iloc[0]
        st.markdown(f"<h2 class='stage-header'>{stage_icons[stage]} {stage.capitalize()}</h2>", unsafe_allow_html=True)

        if pd.isna(employee):
            st.info(f"No employee assigned to the {stage} stage yet.")
            st.markdown("<br>", unsafe_allow_html=True)
            continue
            
        st.markdown(f"**Assigned To:** {employee}")

        metrics, status = calculate_stage_metrics(stage, details, holds, corrections)
        
        if not metrics:
            st.info(f"This stage has not started yet.")
            st.markdown("<br>", unsafe_allow_html=True)
            continue

        # Display metric cards using st.metric
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(label="Status", value=status)
        col2.metric(label="Effective Work Time", value=format_timedelta(metrics['effective_duration']))
        col3.metric(label="Time on Hold", value=format_timedelta(metrics['paused_duration']))
        col4.metric(label="Correction Time", value=format_timedelta(metrics['correction_duration']))
        
        # Add to book totals
        if metrics.get('effective_duration'):
            total_effective_time += metrics['effective_duration']
        
        # Display detailed timeline log
        with st.expander("Show Detailed Log"):
            st.write("") # Spacer
            st.markdown('<div class="timeline-container">', unsafe_allow_html=True)
            for event in metrics['timeline']:
                event_time = event['time'].strftime('%d %b %Y, %I:%M %p')
                st.markdown(f"""
                    <div class="timeline-item" data-icon="{event['icon']}">
                        <div class="timeline-content">
                            <h4>{event['type']}</h4>
                            <p><strong>When:</strong> {event_time}</p>
                            <p class="reason">{event['details']}</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)

    # Calculate and display total book time
    book_start = pd.to_datetime(details['writing_start'].iloc[0])
    # Find the last recorded end time across all stages
    final_end_dates = [pd.to_datetime(details[f'{s}_end'].iloc[0]) for s in stages]
    valid_end_dates = [d for d in final_end_dates if pd.notna(d)]
    book_end = max(valid_end_dates) if valid_end_dates else None

    total_book_time = timedelta(0)
    if book_start and book_end:
        total_book_time = book_end - book_start

    st.markdown("---")
    st.header("📖 Book Summary Metrics")
    col1, col2 = st.columns(2)
    col1.metric(label="Total Book Lifecycle", value=format_timedelta(total_book_time))
    col2.metric(label="Total Effective Work Time", value=format_timedelta(total_effective_time))


# --- 5. MAIN APPLICATION LOGIC ---

def main():
    """Main function to run the Streamlit app."""
    st.title("📚 Employee & Book Production Timeline")
    st.markdown("Select an employee to view their work this month, then select a book to see its detailed production history.")

    conn = connect_db()

    # --- Sidebar for Filters ---
    st.sidebar.header("🔍 Filters")
    all_employees = get_all_employees(conn)
    if not all_employees:
        st.sidebar.warning("No employees found in the database.")
        st.info("Please add employee and book data to the database to use this application.")
        return

    selected_employee = st.sidebar.selectbox(
        "Select an Employee",
        options=[""] + all_employees,
        format_func=lambda x: "Select..." if x == "" else x
    )

    if selected_employee:
        today = datetime.today()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # To get the end of the month, go to the first day of the next month and subtract one second
        next_month_start = (start_of_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_of_month = next_month_start - timedelta(seconds=1)

        employee_books_df = get_employee_books_for_month(conn, selected_employee, start_of_month, end_of_month)
        
        if not employee_books_df.empty:
            book_options = dict(zip(employee_books_df['book_id'], employee_books_df['title']))
            
            selected_book_id = st.sidebar.selectbox(
                f"Books worked on by {selected_employee} this month",
                options=[""] + list(book_options.keys()),
                format_func=lambda x: "Select..." if x == "" else book_options.get(x)
            )

            if selected_book_id:
                book_data = get_book_data(conn, selected_book_id)
                display_timeline(book_data)
            else:
                 st.info("Select a book from the sidebar to view its timeline.")
        else:
            st.sidebar.info(f"{selected_employee} has not worked on any books in the current month.")
            st.info(f"No book activity found for {selected_employee} this month.")
    else:
        st.info("Select an employee from the sidebar to begin.")


if __name__ == "__main__":
    main()