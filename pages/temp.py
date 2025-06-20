import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text

# Database connection
@st.cache_resource
def connect_db():
    try:
        def get_connection():
            return st.connection('ijisem', type='sql')
        conn = get_connection()
        return conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

# Function to convert date from DD/MM/YYYY to YYYY-MM-DD or return None
def convert_date(date_str):
    if date_str and isinstance(date_str, str):
        try:
            return datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')
        except ValueError:
            return None
    return None

# Function to process Excel file and insert into database
def import_excel_to_db(file):
    try:
        # Read Excel file
        df = pd.read_excel(file, dtype=str)  # Read as strings to handle mixed types
        df = df.fillna('')  # Replace NaN with empty string

        # Connect to database
        conn = connect_db()
        session = conn.session

        # Process each row
        for _, row in df.iterrows():
            # Step 1: Handle authors
            author_data = []
            for i in range(1, 6):  # Up to 5 authors
                author_name = row.get(f'Author {i}', '')
                email = row.get(f'Email {i}', '')
                affiliation = row.get(f'Affiliation {i}', '')
                if author_name:  # Only process if author name exists
                    author_data.append({
                        'name': author_name,
                        'email': email if email else None,
                        'affiliation': affiliation if affiliation else None
                    })

            # Insert authors and get their IDs
            author_ids = []
            for author in author_data:
                # Check if author email already exists
                result = session.execute(
                    text("SELECT author_id FROM authors WHERE email = :email"),
                    {"email": author['email']}
                ).first()
                if result:
                    author_ids.append(result[0])
                else:
                    # Insert new author
                    session.execute(
                        text("""
                        INSERT INTO authors (name, email, affiliation)
                        VALUES (:name, :email, :affiliation)
                        """),
                        {
                            "name": author['name'],
                            "email": author['email'],
                            "affiliation": author['affiliation']
                        }
                    )
                    # Get last inserted ID
                    result = session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                    author_ids.append(result)

            # Step 2: Prepare paper data
            paper_data = {
                'paper_id': row['Paper ID'],
                'paper_title': row['Paper Title'],
                'receiving_date': convert_date(row['Receiving Date']),
                'corrosponding_email': row['Corresponding Email'] if row['Corresponding Email'] else None,
                'corrosponding_phone': row['Contact No.'] if row['Contact No.'] else None,
                'paper_source': row['Paper Source'] if row['Paper Source'] in ['Google', 'Justdial', 'Indiamart', 'Website', 'WhatsApp', 'College Visit', 'Office Visit', 'Social Media', 'Call', 'Ads'] else None,
                'writing_by': row['Writing By'] if row['Writing By'] else None,
                'writing_date': convert_date(row['Writing Date']),
                'reviewer_name': row['Reviewer Name'] if row['Reviewer Name'] else None,
                'review_done': 1 if row['Review Process'] == 'TRUE' else 0,
                'review_date': convert_date(row['Review Date']),
                'plagiarism': row['Plagiarism'] if row['Plagiarism'] else None,
                'ai_plagiarism': row['AI'] if row['AI'] else None,
                'acceptance': row['Acceptance'] if row['Acceptance'] in ['Accepted', 'Rejected', 'Pending', 'In Review'] else 'Pending',
                'payment_amount': float(row['Payment']) if row['Payment'] else None,
                'formatting_by': row['Format By'] if row['Format By'] else None,
                'formatting_date': convert_date(row['Formatting Date']),
                'volume': int(row['Volume']) if row['Volume'] else None,
                'issue': row['Issue'] if row['Issue'] else None,
                'paper_url': row['Paper URL'] if row['Paper URL'] else None,
                'paper_doi': row['DOI'] if row['DOI'] else None,
                'paper_uploading_date': convert_date(row['Paper Uploading Date'])
            }

            # Step 3: Insert paper
            session.execute(
                text("""
                INSERT INTO papers (
                    paper_id, paper_title, receiving_date, corrosponding_email, corrosponding_phone,
                    paper_source, volume, issue, publishing_type, writing_by, writing_date,
                    formatting_by, formatting_date, reviewer_name, review_done, review_date,
                    plagiarism, ai_plagiarism, acceptance, payment_amount, payment_date,
                    paper_uploading_date, paper_url, paper_doi
                ) VALUES (:paper_id, :paper_title, :receiving_date, :corrosponding_email, :corrosponding_phone,
                          :paper_source, :volume, :issue, :publishing_type, :writing_by, :writing_date,
                          :formatting_by, :formatting_date, :reviewer_name, :review_done, :review_date,
                          :plagiarism, :ai_plagiarism, :acceptance, :payment_amount, :payment_date,
                          :paper_uploading_date, :paper_url, :paper_doi)
                """),
                {
                    "paper_id": paper_data['paper_id'],
                    "paper_title": paper_data['paper_title'],
                    "receiving_date": paper_data['receiving_date'],
                    "corrosponding_email": paper_data['corrosponding_email'],
                    "corrosponding_phone": paper_data['corrosponding_phone'],
                    "paper_source": paper_data['paper_source'],
                    "volume": paper_data['volume'],
                    "issue": paper_data['issue'],
                    "publishing_type": None,  # Not in Excel
                    "writing_by": paper_data['writing_by'],
                    "writing_date": paper_data['writing_date'],
                    "formatting_by": paper_data['formatting_by'],
                    "formatting_date": paper_data['formatting_date'],
                    "reviewer_name": paper_data['reviewer_name'],
                    "review_done": paper_data['review_done'],
                    "review_date": paper_data['review_date'],
                    "plagiarism": paper_data['plagiarism'],
                    "ai_plagiarism": paper_data['ai_plagiarism'],
                    "acceptance": paper_data['acceptance'],
                    "payment_amount": paper_data['payment_amount'],
                    "payment_date": None,  # Not in Excel
                    "paper_uploading_date": paper_data['paper_uploading_date'],
                    "paper_url": paper_data['paper_url'],
                    "paper_doi": paper_data['paper_doi']
                }
            )

            # Step 4: Insert paper-author relationships
            for position, author_id in enumerate(author_ids, 1):
                session.execute(
                    text("""
                    INSERT INTO paper_authors (paper_id, author_id, author_position)
                    VALUES (:paper_id, :author_id, :author_position)
                    """),
                    {
                        "paper_id": paper_data['paper_id'],
                        "author_id": author_id,
                        "author_position": position
                    }
                )

        # Commit transaction
        session.commit()
        st.success("Data imported successfully!")
    except Exception as e:
        session.rollback()
        st.error(f"Error importing data: {e}")
    finally:
        session.close()

# Streamlit UI
st.title("Import Excel to IJISEM Database")
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    if st.button("Import Data"):
        import_excel_to_db(uploaded_file)