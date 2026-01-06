import streamlit as st
import pandas as pd
from sqlalchemy import text
import time
import json
from auth import validate_token
from constants import connect_db, log_activity, initialize_click_and_session_id

st.set_page_config(page_title="Extra & Deleted Books", page_icon="🗑️", layout="wide")

# Logo
logo = "logo/logo_black.png"
small_logo = "logo/favicon_white.ico"
st.logo(logo, size="large", icon_image=small_logo)

# Auth
validate_token()
initialize_click_and_session_id()

user_role = st.session_state.get("role", "Unknown")
# Allow admins and main app users
if user_role != 'admin' and st.session_state.get("app") != 'main':
    st.error("⚠️ Access Denied.")
    st.stop()

st.markdown("""
    <style>
        .main > div { padding-top: 0px !important; }
        .block-container { padding-top: 28px !important; }
    </style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([9, 1],vertical_alignment="bottom")

with col1:
    st.write("## 🗑️ Extra & Deleted Books Manager")
with col2:
    if st.button("🔄 Refresh", key="refresh_operations", type="tertiary", use_container_width=True):
        st.cache_data.clear()


conn = connect_db()

# --- Data Fetching Functions ---

def fetch_rewritten_books():
    """Fetch archived operations from extra_books table."""
    try:
        query = """
        SELECT 
            id, book_id, title, date, reason, rewritten_at, book_pages,
            writing_start, writing_end, writing_by,
            proofreading_start, proofreading_end, proofreading_by,
            formatting_start, formatting_end, formatting_by
        FROM extra_books
        ORDER BY rewritten_at DESC
        """
        return conn.query(query, ttl=0)
    except Exception:
        return pd.DataFrame()

def fetch_cancelled_books():
    """Fetch deleted books from deleted_books table."""
    query = """
    SELECT 
        book_id, title, date, cancellation_reason,
        writing_start, writing_end, writing_by,
        proofreading_start, proofreading_end, proofreading_by,
        formatting_start, formatting_end, formatting_by,
        cover_start, cover_end, cover_by,
        authors_json, deleted_at
    FROM deleted_books
    ORDER BY deleted_at DESC, date DESC
    """
    return conn.query(query, ttl=0)

# --- Action Functions ---

def reenroll_book(extra_book_id, source_data, target_book_id):
    """Transfer details from extra_books to a target active book and move original to deleted_books."""
    try:
        from datetime import datetime, date
        from decimal import Decimal
        import json

        with conn.session as s:
            # 1. Check if target book exists
            res = s.execute(text("SELECT title FROM books WHERE book_id = :id"), {"id": target_book_id}).fetchone()
            if not res:
                return False, f"Target Book ID {target_book_id} not found."
            
            target_title = res[0]

            # 2. Update target book
            s.execute(text("""
                UPDATE books SET
                    writing_start = :ws, writing_end = :we, writing_by = :wb,
                    proofreading_start = :ps, proofreading_end = :pe, proofreading_by = :pb,
                    formatting_start = :fs, formatting_end = :fe, formatting_by = :fb,
                    book_pages = :bp
                WHERE book_id = :target_id
            """), {
                "ws": source_data['writing_start'], "we": source_data['writing_end'], "wb": source_data['writing_by'],
                "ps": source_data['proofreading_start'], "pe": source_data['proofreading_end'], "pb": source_data['proofreading_by'],
                "fs": source_data['formatting_start'], "fe": source_data['formatting_end'], "fb": source_data['formatting_by'],
                "bp": source_data['book_pages'],
                "target_id": target_book_id
            })

            # 3. Move original book to deleted_books
            book_id = source_data['book_id']
            # Fetch Authors
            authors_rows = s.execute(text("SELECT * FROM book_authors WHERE book_id = :book_id"), {"book_id": book_id}).mappings().all()
            authors_list = [dict(row) for row in authors_rows]
            
            def json_serial(obj):
                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                if isinstance(obj, Decimal):
                    return float(obj)
                raise TypeError (f"Type {type(obj)} not serializable")
            
            authors_json_str = json.dumps(authors_list, default=json_serial)

            # Insert into deleted_books (using existing info in books table, assuming it's soft deleted there)
            # Need to ensure cancellation reason is present. If it's in extra_books, we might want to use that.
            # But the row in books should have is_cancelled=2.
            # We'll use the query similar to app.py but with deleted_at = NOW()
            
            # First, ensure cancellation_reason is set in books (if not already) using extra_books reason
            reason = source_data['reason']
            s.execute(text("UPDATE books SET cancellation_reason = :reason WHERE book_id = :book_id"), {"reason": reason, "book_id": book_id})

            # Check if already in deleted_books
            exists = s.execute(text("SELECT 1 FROM deleted_books WHERE book_id = :book_id"), {"book_id": book_id}).fetchone()

            if not exists:
                s.execute(text("""
                    INSERT INTO deleted_books
                    SELECT b.*, :authors, NOW()
                    FROM books b
                    WHERE b.book_id = :book_id
                """), {"book_id": book_id, "authors": authors_json_str})
            
            # 4. Delete from book_authors
            s.execute(text("DELETE FROM book_authors WHERE book_id = :book_id"), {"book_id": book_id})

            # 5. Clear Books Data (Soft Delete) - Consistent with app.py logic
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
            """), {"reason": reason, "book_id": book_id})

            # 6. Delete from extra_books
            s.execute(text("DELETE FROM extra_books WHERE id = :id"), {"id": extra_book_id})
            
            s.commit()
            
        return True, f"Successfully transferred details to '{target_title}' and moved original to deleted books."
    except Exception as e:
        return False, f"Error reenrolling: {str(e)}"

def restore_book(book_id, title):
    """Restore a cancelled book to active status."""
    try:
        with conn.session as s:
            # 1. Fetch authors_json
            res = s.execute(text("SELECT authors_json FROM deleted_books WHERE book_id = :book_id"), {"book_id": book_id}).fetchone()
            if not res:
                return False, "Book not found in Deleted Books."
            
            authors_json = res[0]
            
            # 2. Restore Books Data (Partial update from deleted_books)
            s.execute(text("""
                UPDATE books b
                JOIN deleted_books db ON b.book_id = db.book_id
                SET 
                    b.is_cancelled = 0,
                    b.cancellation_reason = NULL,
                    b.isbn = db.isbn,
                    b.isbn_receive_date = db.isbn_receive_date,
                    b.title = db.title,
                    b.date = db.date,
                    b.price = db.price,
                    b.publisher = db.publisher,
                    b.author_type = db.author_type,
                    b.writing_start = db.writing_start,
                    b.writing_end = db.writing_end,
                    b.writing_by = db.writing_by,
                    b.proofreading_start = db.proofreading_start,
                    b.proofreading_end = db.proofreading_end,
                    b.proofreading_by = db.proofreading_by,
                    b.formatting_start = db.formatting_start,
                    b.formatting_end = db.formatting_end,
                    b.formatting_by = db.formatting_by,
                    b.cover_start = db.cover_start,
                    b.cover_end = db.cover_end,
                    b.cover_by = db.cover_by,
                    b.book_pages = db.book_pages,
                    b.tags = db.tags,
                    b.subject = db.subject,
                    b.images = db.images
                WHERE b.book_id = :book_id
            """), {"book_id": book_id})

            # 3. Restore Authors
            if authors_json:
                authors_list = json.loads(authors_json)
                if authors_list:
                    for author in authors_list:
                         keys = list(author.keys())
                         cols = ", ".join(keys)
                         vals = ", ".join([f":{k}" for k in keys])
                         stmt = text(f"INSERT INTO book_authors ({cols}) VALUES ({vals})")
                         s.execute(stmt, author)
            
            # 4. Delete from deleted_books
            s.execute(text("DELETE FROM deleted_books WHERE book_id = :book_id"), {"book_id": book_id})
            
            s.commit()
        return True, f"✅ Book '{title}' restored successfully."
    except Exception as e:
        return False, f"Error restoring book: {e}"

# --- Display Helpers ---

def get_status_display(start, end, by):
    if pd.notna(end):
        return f"✅ Completed by {by}"
    elif pd.notna(start):
        return f"⏳ In Progress by {by}"
    else:
        return "⚪ Not Started"

def _render_stage_column(label, start, end, by):
    st.caption(label)
    st.write(get_status_display(start, end, by))
    if pd.notna(end):
        try:
            date_str = pd.to_datetime(end).strftime('%d %b %Y')
            st.caption(f"📅 {date_str}")
        except:
            pass

@st.dialog("📚 Re-enroll Archived Book", width="large", on_dismiss="rerun")
def re_enroll_dialog(extra_book_id, source_data):
    st.subheader("🔄 Transfer Progress Data")
    st.caption("Move writing, proofreading, and formatting data from the archived record to an active book.")

    # --- Data Fetching ---
    try:
        # Note: Assuming 'conn' is available in this scope
        active_books_query = "SELECT book_id, title FROM books WHERE is_cancelled = 0 ORDER BY title"
        active_books = conn.query(active_books_query, ttl=0)
        
        # Create a dictionary for mapping (Label -> ID)
        book_options = {f"{row['title']} (ID: {row['book_id']})": row['book_id'] for _, row in active_books.iterrows()}
    except Exception as e:
        st.error(f"Error fetching active books. Please try again. Details: {e}")
        return
    
    # Check if there are active books to select
    if not book_options:
            st.warning("No active books found to re-enroll to.")
            return

    # --- Visual Transfer UI ---
    col_src, col_arrow, col_dest = st.columns([1, 0.2, 1], vertical_alignment="center")

    with col_src:
        with st.container(border=True):
            st.caption("📤 FROM (Archived)")
            st.markdown(f"**{source_data['title']}**")
            st.caption(f"ID: {source_data['book_id']}")
            
            # Show what data is being transferred
            stages = []
            if pd.notna(source_data['writing_start']): stages.append("Writing")
            if pd.notna(source_data['proofreading_start']): stages.append("Proofreading")
            if pd.notna(source_data['formatting_start']): stages.append("Formatting")
            if stages:
                st.caption(f"Includes: {', '.join(stages)}")
            else:
                st.caption("No progress data found.")

    with col_arrow:
        st.markdown("<h2 style='text-align: center; margin: 0; color: #888;'>➔</h2>", unsafe_allow_html=True)

    with col_dest:
        with st.container(border=True):
            st.caption("📥 TO (Active Book)")
            selected_book_label = st.selectbox(
                "Select Target", 
                options=list(book_options.keys()), 
                label_visibility="collapsed"
            )
            target_id = book_options[selected_book_label]
            st.caption(f"Target ID: {target_id}")
            st.write("") # Spacer to match height roughly

    # --- Validation ---
    target_ops = conn.query(
        "SELECT writing_start, proofreading_start FROM books WHERE book_id = :id", 
        params={"id": target_id}, 
        ttl=0
    )
    
    can_reenroll = True
    if not target_ops.empty:
        has_writing = pd.notna(target_ops.iloc[0]['writing_start'])
        has_proofreading = pd.notna(target_ops.iloc[0]['proofreading_start'])
        
        if has_writing or has_proofreading:
            can_reenroll = False
            st.error("❌ Target book already has Writing or Proofreading details. Cannot overwrite.")

    # --- Confirmation Form ---
    st.write("") # Spacing
    with st.form("reenroll_form", border=False):
        if can_reenroll:
            st.info(f"The archived data will be merged into **{selected_book_label}**.")
            st.warning("⚠️ **Warning:** This action is irreversible. The archived record will be deleted and merged.")
        
        confirm_button = st.form_submit_button(
            "✅ Confirm Transfer", 
            type="primary", 
            use_container_width=True,
            disabled=not can_reenroll
        )

    if confirm_button:
        # --- Logic Execution ---
        with st.spinner("🔄 Transferring archived details..."):
            success, msg = reenroll_book(extra_book_id, source_data, target_id)
            
            if success:
                time.sleep(2)
                st.success(f"🎉 Success! {msg}")
                # Log activity
                log_activity(
                    conn, 
                    st.session_state.user_id, 
                    st.session_state.username, 
                    st.session_state.session_id, 
                    "reenrolled book", 
                    f"Archived ID: {extra_book_id} to Book ID: {target_id}"
                )
            else:
                st.error(f"❌ Re-enrollment failed: {msg}")

@st.dialog("Confirm Restore", width="small", on_dismiss="rerun")
def restore_book_dialog(book_id, title):
    st.warning(f"Are you sure you want to restore '{title}'?")
    st.caption("This will move the book back to the active books list.")
    
    if st.button("Confirm Restore", type="primary", use_container_width=True):
        with st.spinner("Restoring..."):
            success, msg = restore_book(book_id, title)
            if success:
                time.sleep(5)
                st.success(msg)
                log_activity(conn, st.session_state.user_id, st.session_state.username, st.session_state.session_id, "restored book", f"Book ID: {book_id}")
            else:
                st.error(msg)

# --- Data Fetching ---
rewritten_books = fetch_rewritten_books()
deleted_books = fetch_cancelled_books()

# --- Tabs ---
tab1, tab2 = st.tabs([f"📚 Extra Books ({len(rewritten_books)})", f"🗑️ Deleted Books ({len(deleted_books)})"])

# ================= TAB 1: EXTRA BOOKS =================
with tab1:
    st.info("Contains **Rewritten Archives** and **Cancelled Projects** with writing progress.")
    
    # 1. Rewritten Archives
    #st.subheader("🗄️ Rewritten Archives")
    
    if rewritten_books.empty:
        st.caption("No rewritten archives found.")
    else:
        for _, row in rewritten_books.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1.5])
                with c1:
                    st.markdown(f"#### {row['title']}")
                    # Format dates safely
                    enrollment_date = row['date'].strftime('%d %b %Y') if pd.notna(row.get('date')) else "Unknown"
                    archived_date = row['rewritten_at'].strftime('%d %b %Y %H:%M') if pd.notna(row.get('rewritten_at')) else "Unknown"
                    
                    st.caption(f"**Book ID:** {row['book_id']} | **Enrolled:** {enrollment_date} | **Archived:** {archived_date} | **Pages:** {int(row['book_pages']) if pd.notna(row['book_pages']) else 'N/A'}")
                    if pd.notna(row['reason']):
                        st.markdown(f"**Reason:** :red[{row['reason']}]")
                with c2:
                    if st.button("♻️ Re-enroll", key=f"btn_re_{row['id']}", use_container_width=True, type="primary"):
                        re_enroll_dialog(row['id'], row)
                
                st.divider()
                dc1, dc2, dc3 = st.columns(3)
                with dc1: _render_stage_column("Writing", row['writing_start'], row['writing_end'], row['writing_by'])
                with dc2: _render_stage_column("Proofreading", row['proofreading_start'], row['proofreading_end'], row['proofreading_by'])
                with dc3: _render_stage_column("Formatting", row['formatting_start'], row['formatting_end'], row['formatting_by'])
            st.write("")  # Spacer

    

# ================= TAB 2: DELETED BOOKS =================
with tab2:
    st.info("Contains books cancelled **without** any writing progress.")
    
    if deleted_books.empty:
        st.write("No deleted books found.")
    else:
        for _, row in deleted_books.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"#### {row['title']}")
                    st.caption(f"**ID:** {row['book_id']} | **Date:** {row['date']}")
                    if pd.notna(row.get('date')):
                        st.caption(f"**Enrolled At:** {row['date']}")
                    if pd.notna(row.get('deleted_at')):
                        st.caption(f"**Deleted At:** {row['deleted_at']}")
                    st.markdown(f"**Cancellation Reason:** :red[{row['cancellation_reason']}]")
                with c2:
                     if st.button("♻️ Restore", key=f"res_del_{row['book_id']}", type="primary", use_container_width=True):
                         restore_book_dialog(row['book_id'], row['title'])