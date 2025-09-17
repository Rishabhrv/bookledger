import streamlit as st

from sqlalchemy import text
from datetime import date
import time
import json
import difflib
import os
import ollama
import json

def connect_db():
    try:
        @st.cache_resource
        def get_connection():
            return st.connection('mysql', type='sql')
        return get_connection()
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

conn = connect_db()

UPLOAD_DIR = st.secrets["general"]["UPLOAD_DIR"]


########################################################################################################################
##################################--------------- Book add function ----------------------------######################
#######################################################################################################################


def get_all_authors(conn):
    with conn.session as s:
        try:
            query = text("SELECT author_id, name, email, phone FROM authors ORDER BY name")
            authors = s.execute(query).fetchall()
            return authors
        except Exception as e:
            st.error(f"Error fetching authors: {e}")
            return []

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

    def generate_tags_with_ollama(book_title):
        """Generate tags using the Ollama model and clean the output."""
        try:
            prompt = f"""
        You are a book tagging assistant for a book management system. 
        Based only on the given book title, generate exactly 3 concise and highly relevant tags. 

        Rules:
        - Tags must be single words or short phrases (max 2 words). 
        - Do not add filler or generic tags like 'book', 'novel', 'story', 'interesting', 'popular'.
        - Only return a comma-separated list with exactly 3 tags, no extra text.

        Book Title: {book_title}

        Example output: Social Security,AI,Machine Learning,Tourism,Management
        """
            response = ollama.generate(model="llama3.1:8b", prompt=prompt)
            raw_response = response['response'].strip()
            
            # Clean the output to extract only comma-separated tags
            # Remove any preamble, bullet points, or extra text
            if raw_response.startswith("here are the tags") or "*" in raw_response:
                # Extract tags from lines with bullets or after preamble
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
            
            # Limit to 5 tags, lowercase, and remove duplicates
            tags = list(dict.fromkeys([tag.lower() for tag in tags if tag]))[:5]
            
            if not tags:
                st.warning("No valid tags generated by Ollama.")
                return []
            
            return tags
        except Exception as e:
            st.warning(f"Failed to generate tags with Ollama: {str(e)}")
            return []

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

            # Tags will be generated at save time, no UI input
            return {
                "title": book_title,
                "date": book_date,
                "author_type": author_type if toggles_enabled else "Multiple",
                "is_publish_only": (book_mode == "Publish Only") if (book_mode and toggles_enabled) else False,
                "is_thesis_to_book": (book_mode == "Thesis to Book") if (book_mode and toggles_enabled) else False,
                "publisher": publisher,
                "tags": []  # Placeholder, tags will be generated on save
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

        with st.container(border=True):
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

    # def syllabus_upload_section(is_publish_only, is_thesis_to_book, toggles_enabled):
    #     with st.expander("Syllabus & Book Note", expanded=False):
    #         st.markdown("<h5 style='color: #4CAF50;'>Book Syllabus</h5>", unsafe_allow_html=True)
    #         syllabus_file = None
    #         if not is_publish_only and not is_thesis_to_book and toggles_enabled:
    #             syllabus_file = st.file_uploader(
    #                 "Upload Book Syllabus",
    #                 type=["pdf", "docx", "jpg", "jpeg", "png"],
    #                 key="syllabus_upload",
    #                 help="Upload the book syllabus as a PDF, DOCX, or image file.",
    #                 label_visibility="collapsed"
    #             )
    #         else:
    #             if is_publish_only:
    #                 st.info("Syllabus upload is disabled for Publish Only books.")
    #             if is_thesis_to_book:
    #                 st.info("Syllabus upload is disabled for Thesis to Book conversions.")
    #             if not toggles_enabled:
    #                 st.info("Syllabus upload is disabled for AG Kids and NEET/JEE publishers.")
            
    #         st.markdown("<h5 style='color: #4CAF50;'>Book Note</h5>", unsafe_allow_html=True)
    #         book_note = st.text_area(
    #             "Book Note or Instructions",
    #             key="book_note",
    #             help="Enter any additional notes or instructions for the book (optional, max 1000 characters)",
    #             max_chars=1000,
    #             placeholder="Enter notes or special instructions for the book here..."
    #         )
            
    #         return syllabus_file, book_note

    # def tags_section(conn):
    #     # Initialize session state for tags if not already set
    #     if "new_book_tags" not in st.session_state:
    #         st.session_state["new_book_tags"] = []

    #     # Fetch all unique tags and their counts from the database
    #     with conn.session as s:
    #         tag_query = text("SELECT tags FROM books WHERE tags IS NOT NULL AND tags != ''")
    #         all_tags = s.execute(tag_query).fetchall()
    #         tag_counts = {}
    #         for row in all_tags:
    #             tags = [tag.strip() for tag in row[0].split(',') if tag.strip()]
    #             for tag in tags:
    #                 tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
    #         # Sort tags by count (descending) and then alphabetically
    #         sorted_tags = sorted(tag_counts.keys(), key=lambda x: (-tag_counts[x], x))

    #     # Add any new tags from session state that aren't in the database yet
    #     options = sorted_tags + [tag for tag in st.session_state["new_book_tags"] if tag not in sorted_tags]

    #     with st.container(border=True):
    #         # Tags Section UI
    #         st.markdown("<h5 style='color: #4CAF50;'>Add Tags</h5>", unsafe_allow_html=True)
    #         selected_tags = st.multiselect(
    #             "Add Tags",
    #             options=options,
    #             default=st.session_state["new_book_tags"],
    #             key="new_book_tags",
    #             accept_new_options=True,
    #             max_selections=5,
    #             help="Select existing tags or type to add new tags for the book",
    #             label_visibility="collapsed",
    #             placeholder="Select or add up to 5 tags..."
    #         )

    #     return selected_tags

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
        
        # Validation for Book Details
        if not book_data["title"]:
            errors.append("Book title is required.")
        if not book_data["date"]:
            errors.append("Book date is required.")
        if not book_data["publisher"]:
            errors.append("Publisher is required.")
        
        # Add this new check for tags
        tags = book_data.get("tags", [])
        if len(tags) < 3:
            errors.append("At least 3 tags are required.")
            
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
        with col2:
            author_data = author_details_section(conn, book_data["author_type"], publisher)
            book_note = book_note_section()
            book_data["book_note"] = book_note

    # Save, Clear, and Cancel Buttons
    col1, col2 = st.columns([7, 1])
    with col1:
        if st.button("Save", key="dialog_save", type="primary"):
            with st.spinner("Saving..."):
                # Generate tags when Save is clicked
                if book_data["title"]:
                    book_data["tags"] = generate_tags_with_ollama(
                        book_data["title"])

                errors = validate_form(book_data, author_data, book_data["author_type"], publisher)
                if errors:
                    st.error("\n".join(errors), icon="🚨")
                else:
                    with conn.session as s:
                        try:
                            # Handle syllabus file upload
                            syllabus_path = None
                            if book_data["syllabus_file"] and not book_data["is_publish_only"] and not book_data["is_thesis_to_book"]:
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
                                    st.toast(f"Failed to save syllabus file: {str(e)}", icon="❌", duration="long")
                                    raise
                            
                            # Convert tags list to JSON
                            tags_json = json.dumps(book_data["tags"]) if book_data["tags"] else None

                            # Insert book with book note and tags
                            s.execute(text("""
                                INSERT INTO books (title, date, author_type, is_publish_only, is_thesis_to_book, publisher, syllabus_path, book_note, tags)
                                VALUES (:title, :date, :author_type, :is_publish_only, :is_thesis_to_book, :publisher, :syllabus_path, :book_note, :tags)
                            """), params={
                                "title": book_data["title"],
                                "date": book_data["date"],
                                "author_type": book_data["author_type"],
                                "is_publish_only": book_data["is_publish_only"],
                                "is_thesis_to_book": book_data["is_thesis_to_book"],
                                "publisher": book_data["publisher"],
                                "syllabus_path": syllabus_path,
                                "book_note": book_data["book_note"],
                                "tags": tags_json
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

                            # # Log save action
                            # log_activity(
                            #     conn,
                            #     st.session_state.user_id,
                            #     st.session_state.username,
                            #     st.session_state.session_id,
                            #     "added book",
                            #     f"Book ID: {book_id}, Publisher: {book_data['publisher']}, Author Type: {book_data['author_type']}, Is Publish Only: {book_data['is_publish_only']}, Is Thesis to Book: {book_data['is_thesis_to_book']}, Book Note: {book_data['book_note'][:50] + '...' if book_data['book_note'] else 'None'}, Tags: {tags_json or 'None'}"
                            # )

                            st.success("Book and Authors Saved Successfully!", icon="✔️")
                            st.toast("Book and Authors Saved Successfully!", icon="✔️", duration="long")
                        
                            st.session_state.authors = [
                                {"name": "", "email": "", "phone": "", "author_id": None, "author_position": f"{i+1}{'st' if i == 0 else 'nd' if i == 1 else 'rd' if i == 2 else 'th'}", "corresponding_agent": "", "publishing_consultant": ""}
                                for i in range(4)
                            ]
                            time.sleep(1)
                            st.rerun()
                        except Exception as db_error:
                            s.rollback()
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


if st.button("Add New Book", type="primary"):
    add_book_dialog(conn)


########################################################################################################################
##################################--------------- Tag test ----------------------------######################
#######################################################################################################################


def generate_tags_with_ollama(book_title, model):
    """Generate tags using the specified Ollama model and clean the output."""
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
        # Measure start time
        start_time = time.time()
        
        response = ollama.generate(model=model, prompt=prompt)
        raw_response = response['response'].strip()
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        # Debug: Show raw response and elapsed time
        st.write(f"Debug: Raw Ollama response (model: {model}): {raw_response}")
        st.write(f"Time taken to generate tags: {elapsed_time:.2f} seconds")
        
        # Clean the output to extract only comma-separated tags
        if raw_response.startswith("here are the tags") or "*" in raw_response or "-" in raw_response:
            # Extract tags from lines with bullets or after preamble
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
        
        # Ensure exactly 3 tags: trim or pad with fallbacks
        tags = list(dict.fromkeys([tag.lower() for tag in tags if tag]))  # Remove duplicates and lowercase
        if len(tags) > 3:
            tags = tags[:3]  # Take first 3
        elif len(tags) < 3:
            # Fallback tags if insufficient
            fallback_tags = ["general", "education", "literature"]
            tags.extend(fallback_tags[:3 - len(tags)])  # Pad to exactly 3
        
        if not tags:
            st.warning(f"No valid tags generated by {model}.")
            return [], elapsed_time
        
        return tags, elapsed_time
    except Exception as e:
        st.error(f"Failed to generate tags with {model}: {str(e)}")
        return [], 0.0  # Return empty tags and 0 time on error

# Streamlit UI for testing
st.write("#### Test Tag Generation")

# Input for book title and model selection
col1, col2 = st.columns([2, 1])
book_title = col1.text_input("Book Title", placeholder="Enter Book Title (e.g., The History of Space Exploration)")
model = col2.selectbox("Select Model", ["llama3.1:8b", "gemma3:1b", "smollm:1.7b"], index=1)

if book_title:
    with st.spinner(f"Generating tags with {model}..."):
        tags, elapsed_time = generate_tags_with_ollama(book_title, model)
        if tags:
            st.success(f"Tags generated successfully using {model}!")
            st.write(f"**Tags to be saved**: {tags}")
            st.write(f"**JSON format for database**: {json.dumps(tags)}")
            st.write(f"**Generation time**: {elapsed_time:.2f} seconds")
        else:
            st.warning(f"No tags generated by {model}. Check the debug output above.")


########################################################################################################################
##################################--------------- Generate new tags for whole books ----------------------------######################
#######################################################################################################################



def generate_tags_with_ollama(book_title):
    """Generate exactly 3 concise tags using the Ollama model."""
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
        response = ollama.generate(model="llama3.1:8b", prompt=prompt)
        raw_response = response['response'].strip()
        
        # Debug: Log raw response to console and Streamlit
        st.write(f"Raw Ollama response for '{book_title}': {raw_response}")
        
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
        
        # Ensure exactly 3 tags: trim or pad with fallbacks
        tags = list(dict.fromkeys([tag.lower() for tag in tags if tag]))  # Remove duplicates and lowercase
        if len(tags) > 3:
            tags = tags[:3]  # Take first 3
        elif len(tags) < 3:
            # Fallback tags if insufficient
            fallback_tags = ["general", "book", "literature"]
            tags.extend(fallback_tags[:3 - len(tags)])  # Pad to exactly 3
        
        if not tags:
            st.warning(f"No valid tags generated for '{book_title}'. Using fallback tags.")
            return ["general", "book", "literature"]
        
        return tags
    except Exception as e:
        st.error(f"Error generating tags for '{book_title}': {str(e)}")
        return ["general", "book", "literature"]  # Fallback on error

def update_book_tags(conn):
    """Fetch all books, generate 3 tags for each, and update the tags column."""
    try:
        with conn.session as s:
            # Fetch all books (book_id and title)
            result = s.execute(text("SELECT book_id, title FROM books")).fetchall()
            if not result:
                st.warning("No books found in the database.")
                return 0, []
            
            st.write(f"Found {len(result)} books to process.")
            
            updated_count = 0
            errors = []
            progress_text = "Processing books and generating tags..."
            progress_bar = st.progress(0, text=progress_text)
            total_books = len(result)
            
            for i, (book_id, book_title) in enumerate(result):
                if not book_title:
                    st.warning(f"Skipping book ID {book_id}: No title provided.")
                    errors.append(f"Book ID {book_id}: No title provided.")
                    continue
                
                # Generate exactly 3 tags
                tags = generate_tags_with_ollama(book_title)
                tags_json = json.dumps(tags)
                
                # Update the tags column
                try:
                    update_result = s.execute(
                        text("UPDATE books SET tags = :tags WHERE book_id = :book_id"),
                        {"tags": tags_json, "book_id": book_id}
                    )
                    s.commit()
                    updated_count += update_result.rowcount
                    st.write(f"Updated book ID {book_id} ('{book_title}'): Tags = {tags_json}")
                except Exception as db_error:
                    st.error(f"Database error updating book ID {book_id} ('{book_title}'): {str(db_error)}")
                    s.rollback()
                    errors.append(f"Book ID {book_id} ('{book_title}'): {str(db_error)}")
                    continue
                
                # Update progress bar
                progress_value = min((i + 1) / total_books, 1.0)
                progress_bar.progress(progress_value, text=progress_text)
            
            # Clear progress bar
            progress_bar.empty()
            return updated_count, errors
    
    except Exception as e:
        st.error(f"Error accessing database session: {str(e)}")

        return 0, [str(e)]

# Streamlit UI
st.write("#### Update Book Tags")


# Connect to database
conn = connect_db()

# Ensure tags column exists
try:
    with conn.session as s:
        s.execute(text("""
            ALTER TABLE books 
            ADD COLUMN IF NOT EXISTS tags JSON
        """))
        s.commit()
except Exception as e:
    st.error(f"Error ensuring tags column: {e}")
    st.stop()

# Button to trigger tag update
if st.button("Generate and Save Tags"):
    try:
        # Test Ollama connection
        ollama.generate(model="llama3.1:8b", prompt="test")
        st.write("Ollama server is running.")
        
        # Update tags
        updated_count, errors = update_book_tags(conn)
        
        if updated_count > 0:
            st.success(f"Successfully updated tags for {updated_count} books.")
        else:
            st.warning("No books were updated.")
        
        if errors:
            st.error("Errors encountered during processing:")
            for err in errors:
                st.write(err)
    
    except Exception as e:
        st.error(f"Error: Ollama server not running or inaccessible: {str(e)}")
        st.markdown("Please start the Ollama server with `ollama serve` and ensure 'gemma3:1b' is installed.")


########################################################################################################################
##################################--------------- generate Subject for books ----------------------------######################
#######################################################################################################################


# Predefined list of educational subjects
VALID_SUBJECTS = [
    "Mathematics", "Physics", "Chemistry", "Biology", "Computer Science",
    "History", "Geography", "Literature", "Economics", "Business Studies",
    "Political Science", "Sociology", "Psychology", "Engineering", "Medicine",
    "Education", "General Science", "Management", "Marketing", "Medical", "Self Help", "Physical Education", "Commerce", 
    "Law", "Social Science"
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
    """Generate a single concise subject using the Ollama model."""
    try:
        prompt = f"""
        You are a book categorization assistant. Based on the book title, suggest a single, concise subject that best describes the book's educational content. The subject must be one of the following: {', '.join(VALID_SUBJECTS)}. Return only the subject name with no additional text or formatting.

        Book Title: {book_title}

        Example output: Physics
        """
        response = ollama.generate(model="llama3.1:8b", prompt=prompt)
        raw_response = response['response'].strip()
        
        # Debug: Log raw response to console and Streamlit
        st.write(f"Raw Ollama response for '{book_title}': {raw_response}")
        
        # Clean and map to valid subject
        subject = find_closest_subject(raw_response)
        
        if subject == "General Science" and raw_response and raw_response.lower() not in [s.lower() for s in VALID_SUBJECTS]:
            st.warning(f"No valid subject generated for '{book_title}'. Using fallback: General Science")
        
        return subject
    except Exception as e:
        st.error(f"Error generating subject for '{book_title}': {str(e)}")
        return "General Science"  # Fallback on error

def update_book_subjects(conn):
    """Fetch all books, generate a subject for each, and update the subject column."""
    try:
        with conn.session as s:
            # Fetch all books (id and title)
            result = s.execute(text("SELECT book_id, title FROM books")).fetchall()
            if not result:
                st.warning("No books found in the database.")
                return 0, []
            
            st.write(f"Found {len(result)} books to process.")
            
            updated_count = 0
            errors = []
            progress_text = "Processing books and generating subjects..."
            progress_bar = st.progress(0, text=progress_text)
            total_books = len(result)
            
            for i, (book_id, book_title) in enumerate(result):
                if not book_title:
                    st.warning(f"Skipping book ID {book_id}: No title provided.")
                    errors.append(f"Book ID {book_id}: No title provided.")
                    continue
                
                # Generate subject
                subject = generate_subject_with_ollama(book_title)
                
                # Update the subject column
                try:
                    update_result = s.execute(
                        text("UPDATE books SET subject = :subject WHERE book_id = :book_id"),
                        {"subject": subject, "book_id": book_id}
                    )
                    s.commit()
                    updated_count += update_result.rowcount
                    st.write(f"Updated book ID {book_id} ('{book_title}'): Subject = {subject}")
                except Exception as db_error:
                    st.error(f"Database error updating book ID {book_id} ('{book_title}'): {str(db_error)}")
                    s.rollback()
                    errors.append(f"Book ID {book_id} ('{book_title}'): {str(db_error)}")
                    continue
                
                # Update progress bar
                progress_value = min((i + 1) / total_books, 1.0)
                progress_bar.progress(progress_value, text=progress_text)
            
            # Clear progress bar
            progress_bar.empty()
            return updated_count, errors
    
    except Exception as e:
        st.error(f"Error accessing database session: {str(e)}")
        return 0, [str(e)]

# Streamlit UI
st.write("#### Update Book Subjects")

# Connect to database
conn = connect_db()

# Ensure subject column exists
try:
    with conn.session as s:
        s.execute(text("""
            ALTER TABLE books 
            ADD COLUMN IF NOT EXISTS subject TEXT
        """))
        s.commit()
except Exception as e:
    st.error(f"Error ensuring subject column: {e}")
    st.stop()

# Button to trigger subject update
if st.button("Generate and Save Subjects"):
    with st.spinner("Processing books and generating subjects..."):
        try:
            # Test Ollama connection
            ollama.generate(model="llama3.1:8b", prompt="test")
            st.write("Ollama server is running.")
            
            # Update subjects
            updated_count, errors = update_book_subjects(conn)
            
            if updated_count > 0:
                st.success(f"Successfully updated subjects for {updated_count} books.")
            else:
                st.warning("No books were updated.")
            
            if errors:
                st.error("Errors encountered during processing:")
                for err in errors:
                    st.write(err)
        
        except Exception as e:
            st.error(f"Error: Ollama server not running or inaccessible: {str(e)}")
            st.markdown("Please start the Ollama server with `ollama serve` and ensure 'gemma3:270m' is installed.")