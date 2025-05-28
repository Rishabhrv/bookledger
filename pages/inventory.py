import streamlit as st
import pandas as pd
import plotly.express as px
import time
from auth import validate_token
from sqlalchemy import text


logo = "logo/logo_black.png"
fevicon = "logo/favicon_black.ico"
small_logo = "logo/favicon_white.ico"

st.set_page_config(page_title='AGPH Inventory', page_icon="📦📦", layout="wide")

st.logo(logo,
size = "large",
icon_image = small_logo
)

validate_token()

user_role = st.session_state.get("role", None)
user_app = st.session_state.get("app", None)
user_access = st.session_state.get("access", None)


if user_role != 'admin' and not (
    user_role == 'user' and 
    user_app == 'main' and 
    'Inventory' in user_access 
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
            """, unsafe_allow_html=True)

# CSS styles
st.markdown("""
    <style>
    .status-badge-red {
        background-color: #FFEBEE;
        color: #F44336;
        padding: 2px 17px;
        border-radius: 12px;
        font-weight: bold;
        display: inline-flex;
        align-items: center;
        font-size: 20px;
        margin-bottom: 10px;
    }
    .badge-count {
        background-color: rgba(255, 255, 255, 0.9);
        color: inherit;
        padding: 2px 6px;
        border-radius: 10px;
        margin-left: 6px;
        font-size: 14px;
        font-weight: normal;
    }
    .table-header {
        font-weight: bold;
        font-size: 14px;
        color: #333;
        padding: 8px;
        border-bottom: 2px solid #ddd;
        margin-bottom:10px;
    }
    .table-row {
        padding: 7px 5px;
        background-color: #ffffff;
        font-size: 13px; 
        margin-bottom: 5px;
        margin-top: 5px;    
    }
    .table-row:hover {
        background-color: #f1f1f1; 
    }
    .low-stock {
        background-color: #FFEBEE !important;
    }
    .low-stock:hover {
        background-color: #FFCDD2 !important;
    }
    .container-spacing {
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# Database connection
def connect_db():
    try:
        @st.cache_resource
        def get_connection():
            return st.connection('mysql', type='sql')
        conn = get_connection()
        return conn
    except Exception as e:
        st.error(f"Error connecting to MySQL: {e}")
        st.stop()

@st.cache_data
def fetch_data():
    conn = connect_db()
    query = """
    SELECT
        b.book_id,
        b.title,
        i.rack_number,
        COALESCE(
            (SELECT SUM(ba.number_of_books) 
             FROM book_authors ba 
             WHERE ba.book_id = b.book_id), 
            0
        ) AS books_sent_to_authors,
        i.website_sales,
        i.amazon_sales,
        i.flipkart_sales,
        i.direct_sales,
        COALESCE(
            (SELECT SUM(bd.copies_in_batch) 
             FROM BatchDetails bd 
             JOIN PrintEditions pe ON bd.print_id = pe.print_id 
             WHERE pe.book_id = b.book_id), 
            0
        ) AS total_printed_books,
        (SELECT MAX(pb.print_receive_date) 
         FROM PrintBatches pb 
         JOIN BatchDetails bd ON pb.batch_id = bd.batch_id 
         JOIN PrintEditions pe ON bd.print_id = pe.print_id 
         WHERE pe.book_id = b.book_id) AS deliver_date
    FROM books b
    JOIN inventory i ON b.book_id = i.book_id
    WHERE b.print_status = 1
    """
    df = conn.query(query, show_spinner=False)
    return df

st.markdown("""
        <style>
        .print-run-table {
            font-size: 11px;
            border-radius: 5px;
            overflow-x: auto;
            margin-bottom: 8px;
        }

        .print-run-table-header,
        .print-run-table-row {
            display: grid;
            grid-template-columns: 0.5fr 0.6fr 0.6fr 1fr 1fr 0.8fr 0.8fr 1.5fr 1fr;
            padding: 4px 6px;
            align-items: center;
            box-sizing: border-box;
            min-width: 100%;
        }

        .print-run-table-header {
            background-color: #f1f3f5;
            font-weight: 600;
            font-size: 12px;
            color: #2c3e50;
            border-bottom: 1px solid #dcdcdc;
            border-radius: 5px 5px 0 0;
        }

        .print-run-table-row {
            border-bottom: 1px solid #e0e0e0;
            background-color: #fff;
        }

        .print-run-table-row:last-child {
            border-bottom: none;
        }

        .print-run-table-row:hover {
            background-color: #f9f9f9;
        }

        .status-received, .status-sent, .status-pending {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            text-align: center;
            font-size: 10px;
            color: #fff;
            min-width: 60px;
        }

        .status-received { background-color: #27ae60; }
        .status-sent { background-color: #e67e22; }
        .status-pending { background-color: #7f8c8d; }
            
        .value-green { color: #2ecc71; }
        .value-orange { color: #f39c12; }
        .value-red { color: #e74c3c; }
        </style>
    """, unsafe_allow_html=True)

# Header
col1, col2, col3 = st.columns([8, 0.7, 1], vertical_alignment="bottom")
with col1:
    st.markdown("## 📦 Inventory")
with col2:
    if st.button(":material/refresh: Refresh", key="refresh", type="tertiary"):
        st.cache_data.clear()
with col3:
    if st.button(":material/arrow_back: Go Back", key="back_button", type="tertiary", use_container_width=True):
        st.switch_page('app.py')


# Initialize reset trigger
if "reset_trigger" not in st.session_state:
    st.session_state["reset_trigger"] = False

# Fetch data
df = fetch_data()

# Calculate In Stock
df['in_stock'] = (
    df['total_printed_books'] - 
    df['books_sent_to_authors'] - 
    df['website_sales'] - 
    df['amazon_sales'] - 
    df['flipkart_sales'] - 
    df['direct_sales']
)

# Rename columns for display
df = df.rename(columns={
    'rack_number': 'Cell No.',
    'book_id': 'Book ID',
    'title': 'Book Title',
    'deliver_date': 'Deliver Date',
    'total_printed_books': 'Total Prints',
    'books_sent_to_authors': 'Author Copies',
    'website_sales': 'AGPH Store',
    'amazon_sales': 'Amazon',
    'flipkart_sales': 'Filpkart',
    'direct_sales': 'Direct',
    'in_stock': 'In Stock'
})

# Dialog for updating sales and links
@st.dialog("Update Book Details", width="large")
def update_book_details(book_id, current_data):
    st.markdown(f"### (ID: {book_id}) {current_data['Book Title']} ")

    # Fetch current links from books table
    conn = connect_db()
    link_query = """
    SELECT agph_link, amazon_link, flipkart_link, google_link
    FROM books
    WHERE book_id = :book_id
    """
    try:
        with conn.session as session:
            link_data = session.execute(text(link_query), {"book_id": book_id}).fetchone()
            current_links = {
                'agph_link': link_data[0] if link_data and link_data[0] else '',
                'amazon_link': link_data[1] if link_data and link_data[1] else '',
                'flipkart_link': link_data[2] if link_data and link_data[2] else '',
                'google_link': link_data[3] if link_data and link_data[3] else ''
            }
    except Exception as e:
        st.error(f"Failed to fetch book links: {str(e)}")
        return

    tab1, tab2, tab3 = st.tabs(['Sales', 'Links', 'PrintEditions'])

    with tab1:
        # Sales inputs
        st.markdown("#### Sales Numbers and Cell No.")
        col1, col2 = st.columns(2)
        with col1:
            website_sales = st.number_input("AGPH Store Sales", min_value=0, value=int(current_data['AGPH Store']), step=1)
            amazon_sales = st.number_input("Amazon Sales", min_value=0, value=int(current_data['Amazon']), step=1)
        with col2:
            flipkart_sales = st.number_input("Filpkart Sales", min_value=0, value=int(current_data['Filpkart']), step=1)
            direct_sales = st.number_input("Direct Sales", min_value=0, value=int(current_data['Direct']), step=1)
        rack_number = st.text_input("Cell No.", value=str(current_data['Cell No.']) if pd.notnull(current_data['Cell No.']) else '')

    with tab3:
        # Fetch print editions data with batch details
        st.markdown("#### Existing Print Editions")
        print_editions_query = """
            SELECT 
                pe.print_id, 
                pe.copies_planned, 
                pe.print_cost, 
                pe.print_color, 
                pe.binding, 
                pe.book_size, 
                pe.edition_number, 
                pe.status,
                pe.color_pages,
                bd.batch_id,
                pb.batch_name
            FROM 
                PrintEditions pe
            LEFT JOIN 
                BatchDetails bd ON pe.print_id = bd.print_id
            LEFT JOIN 
                PrintBatches pb ON bd.batch_id = pb.batch_id
            WHERE 
                pe.book_id = :book_id
            ORDER BY 
                pe.edition_number DESC
        """
        try:
            with conn.session as session:
                print_editions_data = session.execute(text(print_editions_query), {"book_id": book_id}).fetchall()
                print_editions_df = pd.DataFrame(print_editions_data, columns=[
                    'print_id', 'copies_planned', 'print_cost', 'print_color', 'binding', 
                    'book_size', 'edition_number', 'status', 'color_pages', 'batch_id', 'batch_name'
                ])
        except Exception as e:
            st.error(f"Failed to fetch print editions: {str(e)}")
            print_editions_df = pd.DataFrame()

        if not print_editions_df.empty:
            st.markdown('<div class="print-run-table">', unsafe_allow_html=True)
            st.markdown("""
                <div class="print-run-table-header">
                    <div>ID</div>
                    <div>Copies</div>
                    <div>Cost</div>
                    <div>Color</div>
                    <div>Binding</div>
                    <div>Size</div>
                    <div>Edition</div>
                    <div>Batch</div>
                    <div>Status</div>
                </div>
            """, unsafe_allow_html=True)
            
            for idx, row in print_editions_df.iterrows():
                status_badge = {
                    'Pending': "<span style='background-color: #fff3e0; color: #f57c00; padding: 3px 6px; border-radius: 4px; font-size: 12px;'>Pending</span>",
                    'In Printing': "<span style='background-color: #e3f2fd; color: #1976d2; padding: 3px 6px; border-radius: 4px; font-size: 12px;'>In Printing</span>",
                    'Received': "<span style='background-color: #e6ffe6; color: green; padding: 3px 6px; border-radius: 4px; font-size: 12px;'>Received</span>"
                }.get(row['status'], row['status'])
                batch_info = f"{row['batch_name']} (ID: {row['batch_id']})" if row['batch_id'] else "Not Assigned"
                
                st.markdown(f"""
                    <div class="print-run-table-row">
                        <div>{row['print_id']}</div>
                        <div>{int(row['copies_planned'])}</div>
                        <div>{row['print_cost'] or 'N/A'}</div>
                        <div>{row['print_color']}</div>
                        <div>{row['binding']}</div>
                        <div>{row['book_size']}</div>
                        <div>{row['edition_number']}</div>
                        <div>{batch_info}</div>
                        <div>{status_badge}</div>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No print editions found. Add a new print edition below.")

        with st.expander("Add New Print Edition", expanded=False):
            # Add new PrintEdition
            st.markdown("#### Add New Print Edition")
            col1, col2, col3, col4, col5 = st.columns([1, 0.6, 1.2, 1.2, 0.7])
            with col1:
                new_num_copies = st.number_input("Copies", min_value=0, step=1, value=0, key=f"new_num_copies_{book_id}")
            with col2:
                print_cost = st.text_input("Cost", key=f"print_cost_{book_id}")
            with col3:
                print_color = st.selectbox("Color", options=["Black & White", "Full Color"], key=f"print_color_{book_id}")
            with col4:
                binding = st.selectbox("Binding", options=["Paperback", "Hardcover"], key=f"binding_{book_id}")
            with col5:
                book_size = st.selectbox("Size", options=["6x9", "8.5x11"], key=f"book_size_{book_id}")
            
            # Conditional input for color pages
            new_color_pages = None
            if print_color == "Full Color":
                new_color_pages = st.number_input("Number of Color Pages", min_value=0, step=1, value=0, key=f"new_color_pages_{book_id}")

    with tab2:
        # Link inputs
        st.markdown("#### Book Links")
        agph_link = st.text_input("AGPH Store Link", value=current_links['agph_link'])
        amazon_link = st.text_input("Amazon Link", value=current_links['amazon_link'])
        flipkart_link = st.text_input("Filpkart Link", value=current_links['flipkart_link'])
        google_link = st.text_input("Google Link", value=current_links['google_link'])

    if st.button("Save"):
        with st.spinner('Saving...'):
            time.sleep(1)
            try:
                # Validate inputs
                if new_num_copies > 0:
                    if print_cost:
                        try:
                            float(print_cost)
                        except ValueError:
                            st.error("Print cost must be a valid number or empty.")
                            return
                    if print_color == "Full Color" and (new_color_pages is None or new_color_pages <= 0):
                        st.error("Number of Color Pages must be greater than 0 for Full Color.")
                        return

                with conn.session as session:
                    # Update inventory table (sales and rack_number)
                    session.execute(text("""
                        UPDATE inventory
                        SET website_sales = :website_sales, amazon_sales = :amazon_sales, 
                            flipkart_sales = :flipkart_sales, direct_sales = :direct_sales,
                            rack_number = :rack_number
                        WHERE book_id = :book_id
                    """), {
                        "website_sales": website_sales,
                        "amazon_sales": amazon_sales,
                        "flipkart_sales": flipkart_sales,
                        "direct_sales": direct_sales,
                        "rack_number": rack_number,
                        "book_id": book_id
                    })

                    # Update books table (links)
                    session.execute(text("""
                        UPDATE books
                        SET agph_link = :agph_link, amazon_link = :amazon_link, 
                            flipkart_link = :flipkart_link, google_link = :google_link
                        WHERE book_id = :book_id
                    """), {
                        "agph_link": agph_link,
                        "amazon_link": amazon_link,
                        "flipkart_link": flipkart_link,
                        "google_link": google_link,
                        "book_id": book_id
                    })

                    # Create new PrintEdition if copies > 0
                    if new_num_copies > 0:
                        result = session.execute(
                            text("SELECT COALESCE(MAX(edition_number), 0) + 1 AS next_edition FROM PrintEditions WHERE book_id = :book_id"),
                            {"book_id": book_id}
                        )
                        edition_number = result.fetchone()[0]
                        session.execute(
                            text("""
                                INSERT INTO PrintEditions (book_id, edition_number, copies_planned, 
                                    print_cost, print_color, binding, book_size, status, color_pages)
                                VALUES (:book_id, :edition_number, :copies_planned, 
                                    :print_cost, :print_color, :binding, :book_size, 'Pending', :color_pages)
                            """),
                            {
                                "book_id": book_id,
                                "edition_number": edition_number,
                                "copies_planned": new_num_copies,
                                "print_cost": float(print_cost) if print_cost else None,
                                "print_color": print_color,
                                "binding": binding,
                                "book_size": book_size,
                                "color_pages": new_color_pages if print_color == "Full Color" else None
                            }
                        )

                    # Commit changes
                    session.commit()

                # Clear cache and refresh data
                fetch_data.clear()
                st.success("Details and Print Edition (if added) Saved Successfully!")
                time.sleep(2)
                st.rerun()  # Refresh the app

            except Exception as e:
                st.error(f"Failed to save changes: {str(e)}")


@st.dialog("Inventory Visualizations", width="large")
def show_charts():
    # # Cell No. Occupancy Chart
    # st.markdown("### Cell No. Occupancy")
    # cell_df = df.groupby('Cell No.').size().reset_index(name='Count')
    # cell_df['Cell No.'] = cell_df['Cell No.'].astype(str).replace('nan', 'Unknown').fillna('Unknown')
    # st.write("Contents of cell_df:")
    # st.write(cell_df)

    # if not cell_df.empty:
    #     fig_cell = px.bar(cell_df, x='Cell No.', y='Count', color_discrete_sequence=['#F44336'],
    #                       title='Books per Cell', labels={'Count': 'Number of Books'})
    #     st.plotly_chart(fig_cell, use_container_width=True)
    # else:
    #     st.write("No Cell No. data available to display.")

    # # In Stock Distribution Chart
    # st.markdown("### In Stock Distribution")
    # bins = [0, 1, 3, 6, float('inf')]
    # labels = ['0', '1-2', '3-5', '6+']
    # chart_df = df.copy()
    # chart_df['Stock Range'] = pd.cut(chart_df['In Stock'], bins=bins, labels=labels, include_lowest=True, right=False)
    # stock_counts = chart_df.groupby('Stock Range', observed=True).size().reset_index(name='Count')

    # if not stock_counts.empty and stock_counts['Count'].sum() > 0:
    #     fig_stock = px.bar(stock_counts, x='Stock Range', y='Count', color_discrete_sequence=['#FF6B6B'],
    #                        title='Distribution of In Stock Books', labels={'Count': 'Number of Books'})
    #     st.plotly_chart(fig_stock, use_container_width=True)
    # else:
    #     st.write("No In Stock data available to display.")

    # # Sales Breakdown Pie Chart
    # st.markdown("### Sales Breakdown")
    # sales_data = df[['AGPH Store', 'Amazon', 'Filpkart', 'Direct']].sum().reset_index()
    # sales_data.columns = ['Channel', 'Sales']

    # if sales_data['Sales'].sum() > 0:
    #     fig_sales = px.pie(sales_data, values='Sales', names='Channel', title='Sales by Channel',
    #                        color='Channel', color_discrete_sequence=['#F44336', '#FF6B6B', '#FFCDD2', '#FFEBEE'])
    #     fig_sales.update_traces(textinfo='percent+label')
    #     st.plotly_chart(fig_sales, use_container_width=True)
    # else:
    #     st.write("No sales data available to display.")
    st.write("Comming Soon 😊")


import streamlit as st
import pandas as pd

# Initialize session state for filters and pagination
if 'search_term' not in st.session_state:
    st.session_state['search_term'] = ''
if 'cell_nos' not in st.session_state:
    st.session_state['cell_nos'] = []
if 'out_of_stock' not in st.session_state:
    st.session_state['out_of_stock'] = False
if 'stock_condition' not in st.session_state:
    st.session_state['stock_condition'] = 'Greater than'
if 'stock_value' not in st.session_state:
    st.session_state['stock_value'] = 0
if 'sort_column' not in st.session_state:
    st.session_state['sort_column'] = 'Book ID'
if 'sort_order' not in st.session_state:
    st.session_state['sort_order'] = 'Descending'
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 1
if 'reset_trigger' not in st.session_state:
    st.session_state['reset_trigger'] = False

# Callback functions for widget changes
def update_search_term():
    st.session_state['search_term'] = st.session_state['search_term_widget']
    st.session_state['current_page'] = 1

def update_cell_nos():
    st.session_state['cell_nos'] = st.session_state['cell_nos_widget']
    st.session_state['current_page'] = 1

def update_out_of_stock():
    st.session_state['out_of_stock'] = st.session_state['out_of_stock_widget']
    st.session_state['current_page'] = 1

def update_stock_condition():
    st.session_state['stock_condition'] = st.session_state['stock_condition_widget']
    st.session_state['current_page'] = 1

def update_stock_value():
    st.session_state['stock_value'] = st.session_state['stock_value_widget']
    st.session_state['current_page'] = 1

def update_sort_column():
    st.session_state['sort_column'] = st.session_state['sort_column_widget']
    st.session_state['current_page'] = 1

def update_sort_order():
    st.session_state['sort_order'] = st.session_state['sort_order_widget']
    st.session_state['current_page'] = 1

# Search and Cell No. filter layout
filcol1, filcol2, filcol3, filcol4, filcol5 = st.columns([1.3, 3.5, 3, 0.6, 1.5], vertical_alignment="center")

with filcol2:
    st.text_input(
        "🔍 Search",
        placeholder="Search by Book ID or Book Title",
        value=st.session_state['search_term'],
        key="search_term_widget",
        label_visibility="collapsed",
        on_change=update_search_term
    )
with filcol5:
    st.multiselect(
        "🗄️ Filter by Cell",
        options=df['Cell No.'].unique(),
        key="cell_nos_widget",
        label_visibility="collapsed",
        placeholder="Filter by Cell",
        on_change=update_cell_nos
    )

with filcol4:
    if st.button("📉", key="show_visualizations", type="secondary", use_container_width=True):
        show_charts()

with filcol3:
    with st.popover("More Filters & Sort", use_container_width=True):
        st.checkbox(
            "Show Out of Stock Books",
            value=st.session_state['out_of_stock'],
            key="out_of_stock_widget",
            on_change=update_out_of_stock
        )
        st.selectbox(
            "Stock Filter",
            ["Greater than", "Equal to", "Less than"],
            index=["Greater than", "Equal to", "Less than"].index(st.session_state['stock_condition']),
            key="stock_condition_widget",
            on_change=update_stock_condition
        )
        max_stock = int(df['In Stock'].max()) if not df['In Stock'].empty else 0
        st.number_input(
            "Stock Value",
            min_value=0,
            max_value=max_stock,
            value=st.session_state['stock_value'],
            key="stock_value_widget",
            on_change=update_stock_value
        )
        st.selectbox(
            "Sort by",
            options=df.columns,
            index=list(df.columns).index(st.session_state['sort_column']) if st.session_state['sort_column'] in df.columns else 2,
            key="sort_column_widget",
            on_change=update_sort_column
        )
        st.radio(
            "Sort Order",
            ["Ascending", "Descending"],
            index=["Descending", "Ascending"].index(st.session_state['sort_order']),
            horizontal=True,
            key="sort_order_widget",
            on_change=update_sort_order
        )
        col1, col2 = st.columns([2.5, 1.2])
        with col1:
            if st.button(":material/restart_alt: Reset", key="reset_filters", type="tertiary"):
                st.session_state['search_term'] = ''
                st.session_state['cell_nos'] = []
                st.session_state['out_of_stock'] = False
                st.session_state['stock_condition'] = 'Greater than'
                st.session_state['stock_value'] = 0
                st.session_state['sort_column'] = 'Book Title'
                st.session_state['sort_order'] = 'Ascending'
                st.session_state['current_page'] = 1
                st.session_state['reset_trigger'] = True
                st.rerun()
        with col2:
            # Export filtered table as CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=":material/vertical_align_bottom: Export CSV",
                data=csv,
                file_name="inventory_export.csv",
                mime="text/csv",
                key="export_table",
                type="tertiary"
            )

# Clear reset trigger after applying defaults
if st.session_state["reset_trigger"]:
    st.session_state["reset_trigger"] = False

# Apply filters
filtered_df = df.copy()
if st.session_state['search_term']:
    filtered_df = filtered_df[
        filtered_df['Book Title'].str.contains(st.session_state['search_term'], case=False, na=False) |
        filtered_df['Book ID'].astype(str).str.contains(st.session_state['search_term'], case=False, na=False)
    ]
if st.session_state['cell_nos']:
    filtered_df = filtered_df[filtered_df['Cell No.'].isin(st.session_state['cell_nos'])]
if st.session_state['out_of_stock']:
    filtered_df = filtered_df[filtered_df['In Stock'] == 0]
elif st.session_state['stock_condition'] == "Equal to":
    filtered_df = filtered_df[filtered_df['In Stock'] == st.session_state['stock_value']]
elif st.session_state['stock_condition'] == "Greater than":
    filtered_df = filtered_df[filtered_df['In Stock'] > st.session_state['stock_value']]
elif st.session_state['stock_condition'] == "Less than":
    filtered_df = filtered_df[filtered_df['In Stock'] < st.session_state['stock_value']]

with filcol1:
    # Display book count
    st.markdown(f'<div class="status-badge-red">All Books <span class="badge-count">{len(filtered_df)}</span></div>', unsafe_allow_html=True)

# Sort functionality
sort_ascending = st.session_state['sort_order'] == "Ascending"
filtered_df = filtered_df.sort_values(by=st.session_state['sort_column'], ascending=sort_ascending)

# Custom table with pagination
if not filtered_df.empty:
    # Define column widths (updated to include Action column)
    column_widths = [0.8, 3, 0.8, 1.1, 1, 1.2, 1, 0.55, 0.55, 0.77, 0.5]

    # Pagination setup
    books_per_page = 50
    total_books = len(filtered_df)
    total_pages = (total_books + books_per_page - 1) // books_per_page  # Ceiling division

    # Clamp current_page to valid range
    if total_pages > 0:
        st.session_state['current_page'] = max(1, min(st.session_state['current_page'], total_pages))
    else:
        st.session_state['current_page'] = 1

    # Calculate the start and end indices for the current page
    start_idx = (st.session_state['current_page'] - 1) * books_per_page
    end_idx = min(start_idx + books_per_page, total_books)
    page_df = filtered_df.iloc[start_idx:end_idx]

    # Display the table
    with st.container(border=True):
        cols = st.columns(column_widths)
        cols[0].markdown('<div class="table-header">Book ID</div>', unsafe_allow_html=True)
        cols[1].markdown('<div class="table-header">Book Title</div>', unsafe_allow_html=True)
        cols[2].markdown('<div class="table-header">Cell</div>', unsafe_allow_html=True)
        cols[3].markdown('<div class="table-header">Deliver Date</div>', unsafe_allow_html=True)
        cols[4].markdown('<div class="table-header">Prints</div>', unsafe_allow_html=True)
        cols[5].markdown('<div class="table-header">To Authors</div>', unsafe_allow_html=True)
        cols[6].markdown('<div class="table-header">AGPH</div>', unsafe_allow_html=True)
        cols[7].markdown('<div class="table-header">Amazon</div>', unsafe_allow_html=True)
        cols[8].markdown('<div class="table-header">Filpkart</div>', unsafe_allow_html=True)
        cols[9].markdown('<div class="table-header">Stock</div>', unsafe_allow_html=True)
        cols[10].markdown('<div class="table-header">Action</div>', unsafe_allow_html=True)

        for _, row in page_df.iterrows():
            cols = st.columns(column_widths, vertical_alignment="center")
            deliver_date = row['Deliver Date'].strftime('%Y-%m-%d') if pd.notnull(row['Deliver Date']) else ''
            # Apply low stock highlight
            row_class = 'table-row low-stock' if row['In Stock'] < 2 else 'table-row'
            cols[0].markdown(f'<div class="{row_class}">{row["Book ID"]}</div>', unsafe_allow_html=True)
            cols[1].markdown(f'<div class="{row_class}">{row["Book Title"]}</div>', unsafe_allow_html=True)
            cols[2].markdown(f'<div class="{row_class}">{row["Cell No."]}</div>', unsafe_allow_html=True)
            cols[3].markdown(f'<div class="{row_class}">{deliver_date}</div>', unsafe_allow_html=True)
            cols[4].markdown(f'<div class="{row_class}">{int(row["Total Prints"])}</div>', unsafe_allow_html=True)
            cols[5].markdown(f'<div class="{row_class}">{int(row["Author Copies"])}</div>', unsafe_allow_html=True)
            cols[6].markdown(f'<div class="{row_class}">{int(row["AGPH Store"])}</div>', unsafe_allow_html=True)
            cols[7].markdown(f'<div class="{row_class}">{int(row["Amazon"])}</div>', unsafe_allow_html=True)
            cols[8].markdown(f'<div class="{row_class}">{int(row["Filpkart"])}</div>', unsafe_allow_html=True)
            cols[9].markdown(f'<div class="{row_class}">{int(row["In Stock"])}</div>', unsafe_allow_html=True)
            if cols[10].button(":material/manufacturing:", key=f"action_{row['Book ID']}"):
                st.session_state['update_dialog'] = True
                update_book_details(row['Book ID'], row)

    # Display "Showing X-Y of Z books"
    st.markdown(f"<div style='text-align: center; margin-top: 10px;'>Showing {start_idx + 1}-{end_idx} of {total_books} books</div>", unsafe_allow_html=True)

    # Page navigation (at bottom)
    col1, col2, col3, col4, col5, col6 = st.columns([1, 2, 4, 1, 1, 1], vertical_alignment="center")
    with col1:
        if st.button("First", disabled=(st.session_state['current_page'] == 1)):
            st.session_state['current_page'] = 1
    with col2:
        if st.button("Previous", disabled=(st.session_state['current_page'] == 1)):
            st.session_state['current_page'] -= 1
    with col3:
        st.markdown(f"<div style='text-align: center;'>Page {st.session_state['current_page']} of {total_pages}</div>", unsafe_allow_html=True)
    with col4:
        if st.button("Next", disabled=(st.session_state['current_page'] == total_pages)):
            st.session_state['current_page'] += 1
    with col5:
        if st.button("Last", disabled=(st.session_state['current_page'] == total_pages)):
            st.session_state['current_page'] = total_pages
    with col6:
        page_options = list(range(1, total_pages + 1)) if total_pages > 0 else [1]
        current_index = min(st.session_state['current_page'] - 1, len(page_options) - 1)
        selected_page = st.selectbox(
            "Go to page:",
            page_options,
            index=current_index,
            key="page_selector"
        )
        if selected_page != st.session_state['current_page']:
            st.session_state['current_page'] = selected_page

else:
    st.info("No books match the current filters.")

st.markdown('<div class="container-spacing"></div>', unsafe_allow_html=True)