import streamlit as st
import pandas as pd
import json
from sqlalchemy.sql import text

def connect_db():
    try:
        @st.cache_resource
        def get_connection():
            return st.connection('mysql', type='sql')
        return get_connection()
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

st.title("Book Tags Importer")

# Ensure tags column is JSON (or TEXT if JSON type is unavailable)
conn = connect_db()
with conn.session as s:
    s.execute(text("""
        ALTER TABLE books 
        ADD COLUMN IF NOT EXISTS tags JSON
    """))
    s.commit()

# File uploader
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "xls"])

if uploaded_file is not None:
    if st.button("Import Tags"):
        try:
            df = pd.read_excel(uploaded_file)
            if 'title' not in df.columns or 'tags' not in df.columns:
                st.error("Excel file must contain 'title' and 'tags' columns.")
            else:
                updated_count = 0
                errors = []
                
                for index, row in df.iterrows():
                    title = str(row['title']).strip()
                    # Convert comma-separated tags to JSON array
                    tags = [tag.strip() for tag in str(row['tags']).split(',') if tag.strip()]
                    tags_json = json.dumps(tags)  # e.g., ["AI", "Robotics"]
                    
                    # Check if title exists
                    with conn.session as s:
                        result = s.execute(
                            text("SELECT COUNT(*) FROM books WHERE TRIM(title) = :title"),
                            {"title": title}
                        )
                        count = result.fetchone()[0]
                        
                        if count > 0:
                            # Update tags as JSON
                            update_result = s.execute(
                                text("UPDATE books SET tags = :tags WHERE TRIM(title) = :title"),
                                {"tags": tags_json, "title": title}
                            )
                            s.commit()
                            updated_count += update_result.rowcount
                        else:
                            errors.append(f"Title '{title}' not found in database.")
                
                st.success(f"Successfully updated tags for {updated_count} books.")
                if errors:
                    st.error("Errors encountered:")
                    for err in errors:
                        st.write(err)
        
        except Exception as e:
            st.error(f"An error occurred: {e}")
else:
    st.info("Please upload an Excel file to proceed.")