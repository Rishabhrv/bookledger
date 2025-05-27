import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.parser import parse
from sqlalchemy.sql import text

# --- Database Connection ---
@st.cache_resource
def connect_db():
    try:
        return st.connection('mysql', type='sql')
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

# --- Main App ---
def main():
    st.title("Update Books ISBN Receive Date")
    
    # File upload
    uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx", "xls"])
    
    if uploaded_file is not None:
        try:
            # Read Excel file
            df = pd.read_excel(uploaded_file)
            
            # Validate required columns
            required_columns = ['Book Title', 'Publication Date']
            if not all(col in df.columns for col in required_columns):
                st.error("Excel file must contain 'Book Title' and 'Publication Date' columns")
                return
            
            # Clean and prepare data
            df = df[required_columns].dropna()  # Remove rows with missing values
            df['Book Title'] = df['Book Title'].str.strip().str.lower().str.replace('&', 'and')
            total_books = len(df)  # Metric: Total books in file
            df['Publication Date'] = pd.to_datetime(df['Publication Date'], errors='coerce')
            invalid_date_titles = df[df['Publication Date'].isna()]['Book Title'].tolist()  # Metric: Invalid dates
            df = df.dropna(subset=['Publication Date'])  # Drop rows with invalid dates
            st.write("Preview of uploaded data:")
            st.dataframe(df.head(20))
            
            # Connect to database
            conn = connect_db()
            
            # Check database titles
            with conn.connect() as connection:
                db_titles = pd.read_sql_query("SELECT title FROM books", connection)['title'].str.strip().str.lower().tolist()
                excel_titles = df['Book Title'].tolist()
                non_existent_titles = [title for title in excel_titles if title not in db_titles]  # Metric: Titles not in DB
            
            # Count total rows and initialize progress
            total_rows = len(df)
            progress_bar = st.progress(0)
            updated_rows = 0  # Metric: Books updated
            unmatched_titles = []  # Metric: Unmatched titles during update
            
            # Update books table
            with conn.connect() as connection:
                for index, row in df.iterrows():
                    title = row['Book Title']
                    pub_date = row['Publication Date'].date()
                    
                    # SQL query to update isbn_receive_date
                    query = text("""
                    UPDATE books
                    SET isbn_receive_date = :pub_date
                    WHERE LOWER(TRIM(title)) = :title
                    """)
                    result = connection.execute(query, {"pub_date": pub_date, "title": title})
                    
                    # Check if any row was updated
                    if result.rowcount > 0:
                        updated_rows += result.rowcount
                    else:
                        unmatched_titles.append(title)
                    
                    # Update progress
                    progress = (index + 1) / total_rows
                    progress_bar.progress(min(progress, 1.0))
                
                # Commit changes
                connection.commit()
            
            # Display metrics
            st.subheader("Processing Summary")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Books in File", total_books)
            col2.metric("Books Updated", updated_rows)
            col3.metric("Titles Not Matched", len(unmatched_titles))
            col4.metric("Invalid Date Formats", len(invalid_date_titles))

            # Display detailed warnings as DataFrames
            if unmatched_titles:
                st.warning("The following titles did not match any records in the books table:")
                unmatched_df = pd.DataFrame(unmatched_titles, columns=["Title"])
                st.dataframe(unmatched_df, use_container_width=True)
            if non_existent_titles:
                st.warning("The following titles from Excel do not exist in the database:")
                non_existent_df = pd.DataFrame(non_existent_titles, columns=["Title"])
                st.dataframe(non_existent_df, use_container_width=True)
            if invalid_date_titles:
                st.warning("The following titles had invalid date formats and were skipped:")
                invalid_date_df = pd.DataFrame(invalid_date_titles, columns=["Title"])
                st.dataframe(invalid_date_df, use_container_width=True)

            # Display sample of updated data
            st.write("Sample of updated books:")
            sample_query = """
            SELECT title, isbn_receive_date
            FROM books
            WHERE isbn_receive_date IS NOT NULL
            LIMIT 20
            """
            with conn.connect() as connection:
                sample_df = pd.read_sql_query(sample_query, connection)
            st.dataframe(sample_df)
            
        except Exception as e:
            st.error(f"An error occurred: {e}")
    
    else:
        st.info("Please upload an Excel file to proceed.")

if __name__ == "__main__":
    main()