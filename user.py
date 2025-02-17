import pandas as pd
import streamlit as st

# Connect to MySQL
conn = st.connection("mysql", type="sql")

# Fetch books from the database
query = "SELECT book_id, title, date, isbn, apply_isbn, deliver FROM books"
books = conn.query(query)

# Convert 'date' column to datetime objects if it's not already
if not pd.api.types.is_datetime64_any_dtype(books['date']):
    books['date'] = pd.to_datetime(books['date'])

# Function to get ISBN display logic
def get_isbn_display(isbn, apply_isbn):
    if pd.notna(isbn):
        return isbn  # If ISBN exists, display it
    elif apply_isbn == 0:
        return "Not Applied"
    elif apply_isbn == 1:
        return "Not Received"
    return "-"

# Function to get status with outlined pill styling
def get_status_pill(deliver_value):
    status = "Delivered" if deliver_value == 1 else "On Going"
    border_color = "#28a745" if deliver_value == 1 else "#ffc107"
    text_color = border_color
    return f'<span style="border: 1px solid {border_color}; color: {text_color}; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold;">{status}</span>'

# Custom CSS for styling
st.markdown(
    """
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" integrity="sha512-9usAa10IRO0HhonpyAIVpjrylPvoDwiPUiKdWk5t3PyolY1cOd4DSE0Ga+ri4AuTroPR5aQvXU9xC6qOPnzFeg==" crossorigin="anonymous" referrerpolicy="no-referrer" />
    <style>
        .book-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 14px;
            border-radius: 10px;
            overflow: hidden;
            background-color: var(--background-color);
            color: var(--text-color);
        }
        .book-table th, .book-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(0, 0, 0, 0.1);
        }
        .book-table th {
            background-color: var(--secondary-background-color);
            color: var(--text-color);
            padding: 7px 12px; 
        }
        .book-table tr:nth-child(even) {
            background-color: var(--secondary-background-color);
        }
        .book-table tr:hover {
            background-color: color-mix(in lch, var(--background-color) 90%, var(--primary-color));
        }
        .action-buttons {
            display: flex;
            gap: 8px;
            justify-content: left;
        }
        .action-btn {
            text-decoration: none;
            padding: 6px;
            border-radius: 5px;
            font-size: 14px;
            font-weight: bold;
            display: inline-flex;
            justify-content: center;
            align-items: center;
            transition: background-color 0.3s ease;
            color: black;
            background-color: var(--primary-color);
            width: 32px;
            height: 32px;
        }
        .action-btn:hover {
            opacity: 0.8;
        }
        .responsive-table {
            overflow-x: auto;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Group books by month
grouped_books = books.groupby(pd.Grouper(key='date', freq='ME'))

# Reverse the order of grouped months
reversed_grouped_books = reversed(list(grouped_books))

# Display books
st.markdown("## 📚 Book List")

if books.empty:
    st.warning("No books available.")
else:
    for month, monthly_books in reversed_grouped_books:
        st.markdown(f"##### {month.strftime('%B %Y')}")  # Month and Year as Header
        table_html = """
        <div class='responsive-table'>
        <table class="book-table">
            <thead>
                <tr>
                    <th>Book ID</th>
                    <th>Title</th>
                    <th>Date</th>
                    <th>ISBN</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
        """
        for _, row in monthly_books.iterrows():
            status_pill = get_status_pill(row["deliver"])
            isbn_display = get_isbn_display(row["isbn"], row["apply_isbn"])
            table_html += f"""
            <tr>
                <td>{row['book_id']}</td>
                <td>{row['title']}</td>
                <td>{row['date'].strftime('%Y-%m-%d')}</td>
                <td>{isbn_display}</td>
                <td>{status_pill}</td>
                <td class="action-buttons">
                    <a href='/view/{row["book_id"]}' class='action-btn view-btn' title="View"><i class="fas fa-eye"></i></a>
                    <a href='/edit/{row["book_id"]}' class='action-btn edit-btn' title="Edit"><i class="fas fa-pencil"></i></a>
                    <a href='/archive/{row["book_id"]}' class='action-btn archive-btn' title="Archive"><i class="fas fa-trash"></i></a>
                </td>
            </tr>
            """
        table_html += "</tbody></table></div>"
        st.html(table_html)
