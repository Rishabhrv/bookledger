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

st.title("Book Details Importer")

# Ensure required columns exist in the books table
conn = connect_db()
required_columns = ['weight_kg', 'length_cm', 'width_cm', 'height_cm', 'book_mrp', 'images']
with conn.session as s:
    for column in required_columns:
        result = s.execute(text("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME='books' AND COLUMN_NAME=:col
        """), {"col": column})
        if result.scalar() == 0:
            col_type = "TEXT" if column == "images" else "FLOAT" if column in ["weight_kg", "length_cm", "width_cm", "height_cm"] else "DECIMAL(10,2)"
            s.execute(text(f"ALTER TABLE books ADD COLUMN {column} {col_type}"))
    s.commit()

# File uploader
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "xls"])

if uploaded_file is not None:
    if st.button("Import Book Details"):
        try:
            df = pd.read_excel(uploaded_file)
            required_excel_columns = ['Title', 'Weight (kg)', 'Length (cm)', 'Width (cm)', 'Height (cm)', 'Regular price', 'Images']
            if not all(col in df.columns for col in required_excel_columns):
                st.error("Excel file must contain the following columns: " + ", ".join(required_excel_columns))
            else:
                updated_count = 0
                errors = []
                progress_bar = st.progress(0)
                total_rows = len(df)

                for index, row in df.iterrows():
                    title = str(row['Title']).strip()
                    weight = float(row['Weight (kg)']) if pd.notnull(row['Weight (kg)']) else None
                    length = float(row['Length (cm)']) if pd.notnull(row['Length (cm)']) else None
                    width = float(row['Width (cm)']) if pd.notnull(row['Width (cm)']) else None
                    height = float(row['Height (cm)']) if pd.notnull(row['Height (cm)']) else None
                    price = float(row['Regular price']) if pd.notnull(row['Regular price']) else None
                    images = str(row['Images']).strip() if pd.notnull(row['Images']) else None

                    # Check if title exists
                    with conn.session as s:
                        result = s.execute(
                            text("SELECT COUNT(*) FROM books WHERE TRIM(title) = :title"),
                            {"title": title}
                        )
                        count = result.fetchone()[0]

                        if count > 0:
                            # Update book details
                            update_result = s.execute(
                                text("""
                                    UPDATE books 
                                    SET weight_kg = :weight, 
                                        length_cm = :length, 
                                        width_cm = :width, 
                                        height_cm = :height, 
                                        book_mrp = :price, 
                                        images = :images 
                                    WHERE TRIM(title) = :title
                                """),
                                {
                                    "weight": weight,
                                    "length": length,
                                    "width": width,
                                    "height": height,
                                    "price": price,
                                    "images": images,
                                    "title": title
                                }
                            )
                            s.commit()
                            updated_count += update_result.rowcount
                        else:
                            errors.append(f"Title '{title}' not found in database.")

                    # Update progress bar
                    progress_bar.progress((index + 1) / total_rows)

                st.success(f"Successfully updated details for {updated_count} books.")
                if errors:
                    st.error("Errors encountered:")
                    for err in errors:
                        st.write(err)

        except Exception as e:
            st.error(f"An error occurred: {e}")
else:
    st.info("Please upload an Excel file to proceed.")