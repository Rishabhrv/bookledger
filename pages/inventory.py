import streamlit as st
import pandas as pd
import plotly.express as px
from auth import validate_token


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
            padding-top: 28px !important;  /* Small padding for breathing room */
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
    font-size: 14.5px;
    color: #333;
    padding: 7px;
    border-bottom: 2px solid #ddd;
}
.table-row {
    padding: 7px 5px;
    background-color: #ffffff;
    font-size: 14px; 
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

# Fetch data
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
             FROM batchdetails bd 
             JOIN printeditions pe ON bd.print_id = pe.print_id 
             WHERE pe.book_id = b.book_id), 
            0
        ) AS total_printed_books,
        (SELECT MAX(pb.print_receive_date) 
         FROM printbatches pb 
         JOIN batchdetails bd ON pb.batch_id = bd.batch_id 
         JOIN printeditions pe ON bd.print_id = pe.print_id 
         WHERE pe.book_id = b.book_id) AS deliver_date
    FROM books b
    JOIN inventory i ON b.book_id = i.book_id
    WHERE b.deliver = 1
    """
    df = conn.query(query)
    return df

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


# Search and Cell No. filter layout
filcol1, filcol2, filcol3, filcol4, filcol5 = st.columns([1.3, 3.5, 3, .6, 1.5], vertical_alignment="center")

with filcol2:
    search_term = st.text_input(
        "🔍 Search",
        placeholder="Search by Book ID or Book Title",
        key="search_term",
        label_visibility="collapsed"
    )
with filcol5:
    cell_nos = st.multiselect(
        "🗄️ Filter by Cell",
        options=df['Cell No.'].unique(),
        key="cell_nos",
        label_visibility="collapsed",
        placeholder="Filter by Cell"
    )

with filcol4:
    if st.button("📉", key="show_visualizations", type="secondary",use_container_width=True):
        show_charts()

with filcol3:
    with st.popover("More Filters & Sort", use_container_width=True):
        out_of_stock = st.checkbox(
            "Show Out of Stock Books Only",
            value=False if st.session_state["reset_trigger"] else st.session_state.get("out_of_stock", False),
            key="out_of_stock"
        )
        stock_condition = st.selectbox(
            "Stock Filter",
            ["Greater than", "Equal to", "Less than"],
            index=0 if st.session_state["reset_trigger"] else st.session_state.get("stock_condition_index", 0),
            key="stock_condition"
        )
        max_stock = int(df['In Stock'].max()) if not df['In Stock'].empty else 0
        stock_value = st.number_input(
            "Stock Value",
            min_value=0,
            max_value=max_stock,
            value=0 if st.session_state["reset_trigger"] else st.session_state.get("stock_value", 0),
            key="stock_value"
        )
        sort_column = st.selectbox(
            "Sort by",
            options=df.columns,
            index=2 if st.session_state["reset_trigger"] else st.session_state.get("sort_column_index", 1),  # Default to Book Title
            key="sort_column"
        )
        sort_order = st.radio(
            "Sort Order",
            ["Ascending", "Descending"],
            index=0 if st.session_state["reset_trigger"] else st.session_state.get("sort_order_index", 0),
            horizontal=True,
            key="sort_order"
        )
        col1, col2 = st.columns([2.5,1.2])
        with col1:
            if st.button(":material/restart_alt: Reset", key="reset_filters",
                type= "tertiary"):
                st.session_state["reset_trigger"] = True
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
                type= "tertiary"
            )

# Clear reset trigger after applying defaults
if st.session_state["reset_trigger"]:
    st.session_state["reset_trigger"] = False

# Apply filters
filtered_df = df.copy()
if search_term:
    filtered_df = filtered_df[
        filtered_df['Book Title'].str.contains(search_term, case=False, na=False) |
        filtered_df['Book ID'].astype(str).str.contains(search_term, case=False, na=False)
    ]
if cell_nos:
    filtered_df = filtered_df[filtered_df['Cell No.'].isin(cell_nos)]
if out_of_stock:
    filtered_df = filtered_df[filtered_df['In Stock'] == 0]
elif stock_condition == "Equal to":
    filtered_df = filtered_df[filtered_df['In Stock'] == stock_value]
elif stock_condition == "Greater than":
    filtered_df = filtered_df[filtered_df['In Stock'] > stock_value]
elif stock_condition == "Less than":
    filtered_df = filtered_df[filtered_df['In Stock'] < stock_value]

with filcol1:
    # Display book count
    st.markdown(f'<div class="status-badge-red">All Books <span class="badge-count">{len(filtered_df)}</span></div>', unsafe_allow_html=True)

# Sort functionality
sort_ascending = sort_order == "Ascending"
filtered_df = filtered_df.sort_values(by=sort_column, ascending=sort_ascending)

# Custom table
if not filtered_df.empty:
    # Define column widths (as provided)
    column_widths = [0.8, 3.5, 0.8, 1.2, 1, 1.2, 1, 0.6, 0.6, 0.6, 0.8]
    
    with st.container(border=True):
        cols = st.columns(column_widths)
        cols[0].markdown('<div class="table-header">Book ID</div>', unsafe_allow_html=True)
        cols[1].markdown('<div class="table-header">Book Title</div>', unsafe_allow_html=True)
        cols[2].markdown('<div class="table-header">Cell No.</div>', unsafe_allow_html=True)
        cols[3].markdown('<div class="table-header">Deliver Date</div>', unsafe_allow_html=True)
        cols[4].markdown('<div class="table-header">Total Prints</div>', unsafe_allow_html=True)
        cols[5].markdown('<div class="table-header">Author Copies</div>', unsafe_allow_html=True)
        cols[6].markdown('<div class="table-header">AGPH Store</div>', unsafe_allow_html=True)
        cols[7].markdown('<div class="table-header">Amazon</div>', unsafe_allow_html=True)
        cols[8].markdown('<div class="table-header">Filpkart</div>', unsafe_allow_html=True)
        cols[9].markdown('<div class="table-header">Direct</div>', unsafe_allow_html=True)
        cols[10].markdown('<div class="table-header">In Stock</div>', unsafe_allow_html=True)

        for _, row in filtered_df.iterrows():
            cols = st.columns(column_widths)
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
            cols[9].markdown(f'<div class="{row_class}">{int(row["Direct"])}</div>', unsafe_allow_html=True)
            cols[10].markdown(f'<div class="{row_class}">{int(row["In Stock"])}</div>', unsafe_allow_html=True)

else:
    st.info("No books match the current filters.")

st.markdown('<div class="container-spacing"></div>', unsafe_allow_html=True)