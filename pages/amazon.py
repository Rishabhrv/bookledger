

import requests
import os
from datetime import datetime, timedelta, date, time as dt_time
import requests, urllib.parse
import streamlit as st
import time
from constants import log_activity, initialize_click_and_session_id, connect_db
from auth import validate_token
from collections import defaultdict
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Set page configuration
st.set_page_config(
    layout="wide",  # Set layout to wide mode
    initial_sidebar_state="expanded",
    page_title="AGPH Books",
    page_icon="📚"
)

validate_token()
initialize_click_and_session_id()

user_role = st.session_state.get("role", None)
user_app = st.session_state.get("app", None)
user_access = st.session_state.get("access", None)
session_id = st.session_state.session_id
click_id = st.session_state.get("click_id", None)


if user_role != "admin":
    st.error("You do not have permission to access this page.")
    st.stop()


# Connect to MySQL
conn = connect_db()


# Initialize logged_click_ids if not present
if "logged_click_ids" not in st.session_state:
    st.session_state.logged_click_ids = set()

# Log navigation if click_id is present and not already logged
if click_id and click_id not in st.session_state.logged_click_ids:
    try:
        log_activity(
            conn,
            st.session_state.user_id,
            st.session_state.username,
            st.session_state.session_id,
            "navigated to page",
            f"Page: Activity Log"
        )
        st.session_state.logged_click_ids.add(click_id)
    except Exception as e:
        st.error(f"Error logging navigation: {str(e)}")

LWA_APP_ID  = st.secrets["amazon"]["LWA_APP_ID"]
LWA_CLIENT_SECRET  = st.secrets["amazon"]["LWA_CLIENT_SECRET"]
REFRESH_TOKEN  = st.secrets["amazon"]["REFRESH_TOKEN"]
ENDPOINT = "https://sellingpartnerapi-eu.amazon.com"
MARKETPLACE_ID = 'A21TJRUUN4KGV'  # India

def get_lwa_access_token():
    """Get or refresh LWA access token with caching"""
    if 'access_token' in st.session_state and 'token_expiry' in st.session_state:
        if datetime.now() < st.session_state.token_expiry:
            return st.session_state.access_token

    response = requests.post(
        "https://api.amazon.com/auth/o2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
            "client_id": LWA_APP_ID,
            "client_secret": LWA_CLIENT_SECRET
        }
    )

    if response.status_code != 200:
        st.error('Unable to load access_token.')
        return None

    access_token = response.json()['access_token']
    st.session_state.access_token = access_token
    st.session_state.token_expiry = datetime.now() + timedelta(minutes=55)
    
    return access_token


def fetch_orders(access_token, start_date, end_date, order_statuses=None):
    """Fetch orders with pagination"""
    if order_statuses is None:
        order_statuses = "Shipped,Unshipped,PartiallyShipped"
    
    created_after = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    created_before = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    request_params = {
        "MarketplaceIds": MARKETPLACE_ID,
        "CreatedAfter": created_after,
    }
    
    if end_date.date() < datetime.now().date():
        request_params["CreatedBefore"] = created_before
    
    if order_statuses:
        request_params["OrderStatuses"] = order_statuses
    
    orders_url = f"{ENDPOINT}/orders/v0/orders"
    next_token = None
    all_orders = []
    
    while True:
        params = request_params.copy()
        if next_token:
            params['NextToken'] = next_token
        
        url_with_params = f"{orders_url}?{urllib.parse.urlencode(params)}"
        response = requests.get(
            url_with_params,
            headers={"x-amz-access-token": access_token}
        )
        
        if response.status_code != 200:
            st.error(f"Error fetching orders: {response.status_code}")
            break
        
        orders_data = response.json()
        
        if 'payload' in orders_data and 'Orders' in orders_data['payload']:
            all_orders.extend(orders_data['payload']['Orders'])
            next_token = orders_data['payload'].get('NextToken')
            if not next_token:
                break
            time.sleep(0.6)
        else:
            break
    
    return all_orders


def fetch_order_items_batch(access_token, order_ids, progress_callback=None):
    """Fetch items for multiple orders with rate limiting"""
    all_items = []
    
    for idx, order_id in enumerate(order_ids):
        if progress_callback:
            progress_callback(idx + 1, len(order_ids))
        
        time.sleep(0.6)
        
        items_url = f"{ENDPOINT}/orders/v0/orders/{order_id}/orderItems"
        items_response = requests.get(
            items_url,
            headers={"x-amz-access-token": access_token}
        )
        
        if items_response.status_code == 200:
            items_data = items_response.json()
            if 'payload' in items_data and 'OrderItems' in items_data['payload']:
                for item in items_data['payload']['OrderItems']:
                    item['AmazonOrderId'] = order_id
                    all_items.append(item)
    
    return all_items


def calculate_metrics(orders, items):
    """Calculate comprehensive metrics from orders and items"""
    metrics = {
        'total_orders': len(orders),
        'total_revenue': 0,
        'total_units': 0,
        'total_items': len(items),
        'avg_order_value': 0,
        'canceled_orders': 0,
        'returned_units': 0,
        'orders_by_status': defaultdict(int),
        'daily_orders': defaultdict(int),
        'daily_revenue': defaultdict(float),
        'top_products': defaultdict(lambda: {'name': '', 'quantity': 0, 'revenue': 0}),
        'orders_by_channel': defaultdict(int),
        'hourly_orders': defaultdict(int),
        'day_of_week_orders': defaultdict(int),
        'fulfillment_times': [],
        'order_sizes': defaultdict(int),
        'unique_customers': set(),
        'repeat_customers': 0,
        'fulfillment_method': defaultdict(int),
        # New Financial Metrics
        'revenue_breakdown': {
            'product_sales': 0.0,
            'tax': 0.0,
            'shipping': 0.0,
            'discount': 0.0
        },
        # New Geo Metrics
        'geo_distribution': {
            'states': defaultdict(int),
            'cities': defaultdict(int)
        }
    }
    
    for order in orders:
        # Revenue calculation
        if 'OrderTotal' in order and 'Amount' in order['OrderTotal']:
            revenue = float(order['OrderTotal']['Amount'])
            metrics['total_revenue'] += revenue
            
            order_date = order['PurchaseDate'][:10]
            metrics['daily_revenue'][order_date] += revenue
        
        # Orders by status
        status = order.get('OrderStatus', 'Unknown')
        metrics['orders_by_status'][status] += 1
        
        if status == 'Canceled':
            metrics['canceled_orders'] += 1
        
        # Daily orders
        order_date = order['PurchaseDate'][:10]
        metrics['daily_orders'][order_date] += 1
        
        # Hourly pattern
        try:
            order_datetime = datetime.strptime(order['PurchaseDate'], '%Y-%m-%dT%H:%M:%SZ')
            metrics['hourly_orders'][order_datetime.hour] += 1
            metrics['day_of_week_orders'][order_datetime.strftime('%A')] += 1
        except:
            pass
        
        # Orders by channel
        channel = order.get('SalesChannel', 'Unknown')
        metrics['orders_by_channel'][channel] += 1
        
        # Fulfillment method
        fulfillment = order.get('FulfillmentChannel', 'Unknown')
        metrics['fulfillment_method'][fulfillment] += 1
        
        # Customer tracking
        buyer_email = order.get('BuyerEmail', '')
        if buyer_email:
            if buyer_email in metrics['unique_customers']:
                metrics['repeat_customers'] += 1
            metrics['unique_customers'].add(buyer_email)
        
        # Order size (number of items)
        num_items = order.get('NumberOfItemsShipped', 0) + order.get('NumberOfItemsUnshipped', 0)
        metrics['order_sizes'][num_items] += 1
        
        # Fulfillment time
        if 'LastUpdateDate' in order and status == 'Shipped':
            try:
                purchase = datetime.strptime(order['PurchaseDate'], '%Y-%m-%dT%H:%M:%SZ')
                last_update = datetime.strptime(order['LastUpdateDate'], '%Y-%m-%dT%H:%M:%SZ')
                fulfillment_hours = (last_update - purchase).total_seconds() / 3600
                if fulfillment_hours > 0:
                    metrics['fulfillment_times'].append(fulfillment_hours)
            except:
                pass

        # Geo Distribution
        if 'ShippingAddress' in order:
            addr = order['ShippingAddress']
            state = addr.get('StateOrRegion', 'Unknown')
            city = addr.get('City', 'Unknown')
            if state and state != 'Unknown':
                metrics['geo_distribution']['states'][state] += 1
            if city and city != 'Unknown':
                metrics['geo_distribution']['cities'][city] += 1
    
    # Calculate from items
    for item in items:
        qty = item.get('QuantityOrdered', 0)
        metrics['total_units'] += qty
        
        qty_shipped = item.get('QuantityShipped', 0)
        if qty_shipped < qty:
            metrics['returned_units'] += (qty - qty_shipped)
        
        # Product analytics
        sku = item.get('SellerSKU', 'Unknown')
        product_name = item.get('Title', 'Unknown Product')
        metrics['top_products'][sku]['name'] = product_name
        metrics['top_products'][sku]['quantity'] += qty
        
        if 'ItemPrice' in item and 'Amount' in item['ItemPrice']:
            item_revenue = float(item['ItemPrice']['Amount'])
            metrics['top_products'][sku]['revenue'] += item_revenue
            metrics['revenue_breakdown']['product_sales'] += item_revenue
            
        if 'ItemTax' in item and 'Amount' in item['ItemTax']:
            metrics['revenue_breakdown']['tax'] += float(item['ItemTax']['Amount'])
            
        if 'ShippingPrice' in item and 'Amount' in item['ShippingPrice']:
            metrics['revenue_breakdown']['shipping'] += float(item['ShippingPrice']['Amount'])
            
        if 'PromotionDiscount' in item and 'Amount' in item['PromotionDiscount']:
            metrics['revenue_breakdown']['discount'] += float(item['PromotionDiscount']['Amount'])
    
    # Average order value
    if metrics['total_orders'] > 0:
        metrics['avg_order_value'] = metrics['total_revenue'] / metrics['total_orders']

    # Average Selling Price
    if metrics['total_units'] > 0:
        metrics['avg_selling_price'] = metrics['revenue_breakdown']['product_sales'] / metrics['total_units']
    else:
        metrics['avg_selling_price'] = 0
    
    # Average fulfillment time
    if metrics['fulfillment_times']:
        metrics['avg_fulfillment_hours'] = sum(metrics['fulfillment_times']) / len(metrics['fulfillment_times'])
    else:
        metrics['avg_fulfillment_hours'] = 0
    
    # Customer metrics
    metrics['total_customers'] = len(metrics['unique_customers'])
    if metrics['total_customers'] > 0:
        metrics['repeat_customer_rate'] = (metrics['repeat_customers'] / metrics['total_orders']) * 100
    else:
        metrics['repeat_customer_rate'] = 0
    
    return metrics


def calculate_comparison_metrics(current_metrics, previous_metrics):
    """Calculate growth rates between two periods"""
    comparisons = {}
    
    keys_to_compare = ['total_orders', 'total_revenue', 'total_units', 'avg_order_value']
    
    for key in keys_to_compare:
        current = current_metrics.get(key, 0)
        previous = previous_metrics.get(key, 0)
        
        if previous > 0:
            growth = ((current - previous) / previous) * 100
        else:
            growth = 100 if current > 0 else 0
        
        comparisons[key] = {
            'current': current,
            'previous': previous,
            'growth': growth
        }
    
    return comparisons


# Main Dashboard
st.title("📦 Amazon Seller Dashboard Pro")
st.markdown("---")

# Sidebar for filters
with st.sidebar:
    st.header("⚙️ Filters")
    
    # Date range selector
    date_option = st.radio(
        "Select Date Range",
        ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Custom Range"]
    )
    
    if date_option == "Last 7 Days":
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        prev_start = datetime.now() - timedelta(days=14)
        prev_end = datetime.now() - timedelta(days=7)
    elif date_option == "Last 30 Days":
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        prev_start = datetime.now() - timedelta(days=60)
        prev_end = datetime.now() - timedelta(days=30)
    elif date_option == "Last 90 Days":
        start_date = datetime.now() - timedelta(days=90)
        end_date = datetime.now()
        prev_start = datetime.now() - timedelta(days=180)
        prev_end = datetime.now() - timedelta(days=90)
    else:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
            start_date = datetime.combine(start_date, datetime.min.time())
        with col2:
            end_date = st.date_input("End Date", datetime.now())
            end_date = datetime.combine(end_date, datetime.max.time())
        
        # Calculate previous period
        days_diff = (end_date - start_date).days
        prev_end = start_date
        prev_start = start_date - timedelta(days=days_diff)
    
    st.markdown("---")
    
    # Comparison toggle
    show_comparison = st.checkbox("📊 Compare with Previous Period", value=False)
    
    st.markdown("---")
    
    # Order status filter
    status_options = st.multiselect(
        "Order Status",
        ["Shipped", "Unshipped", "PartiallyShipped", "Canceled"],
        default=["Shipped", "Unshipped", "PartiallyShipped"]
    )
    
    order_statuses = ",".join(status_options) if status_options else "Shipped,Unshipped,PartiallyShipped"
    
    st.markdown("---")
    refresh_button = st.button("🔄 Refresh Data", use_container_width=True)

# Display selected date range
st.info(f"📅 Current Period: **{start_date.strftime('%Y-%m-%d')}** to **{end_date.strftime('%Y-%m-%d')}**")
if show_comparison:
    st.info(f"📅 Previous Period: **{prev_start.strftime('%Y-%m-%d')}** to **{prev_end.strftime('%Y-%m-%d')}**")

# Initialize or refresh data
if refresh_button or 'dashboard_data' not in st.session_state:
    with st.spinner('🔐 Authenticating...'):
        access_token = get_lwa_access_token()
    
    if access_token:
        # Fetch current period
        with st.spinner('📥 Fetching current period orders...'):
            orders = fetch_orders(access_token, start_date, end_date, order_statuses)
            st.session_state.orders = orders
        
        # Fetch previous period if comparison enabled
        if show_comparison:
            with st.spinner('📥 Fetching previous period orders...'):
                prev_orders = fetch_orders(access_token, prev_start, prev_end, order_statuses)
                st.session_state.prev_orders = prev_orders
        
        if orders:
            st.success(f"✅ Found {len(orders)} orders in current period")
            
            # Fetch order items for current period
            with st.spinner('📦 Fetching order items...'):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(current, total):
                    progress = current / total
                    progress_bar.progress(progress)
                    status_text.text(f"Processing order {current}/{total}")
                
                order_ids = [order['AmazonOrderId'] for order in orders]
                items = fetch_order_items_batch(access_token, order_ids, update_progress)
                
                progress_bar.empty()
                status_text.empty()
                
                st.session_state.items = items
                st.session_state.dashboard_data = calculate_metrics(orders, items)
                
                # Fetch items for previous period if needed
                if show_comparison and prev_orders:
                    with st.spinner('📦 Fetching previous period items...'):
                        prev_order_ids = [order['AmazonOrderId'] for order in prev_orders]
                        prev_items = fetch_order_items_batch(access_token, prev_order_ids)
                        st.session_state.prev_items = prev_items
                        st.session_state.prev_dashboard_data = calculate_metrics(prev_orders, prev_items)
                
                st.success(f"✅ Fetched {len(items)} items")
        else:
            st.warning("No orders found for the selected period.")
            st.session_state.orders = []
            st.session_state.items = []
            st.session_state.dashboard_data = None

# Display Dashboard
if 'dashboard_data' in st.session_state and st.session_state.dashboard_data:
    metrics = st.session_state.dashboard_data
    
    # Calculate comparisons if available
    if show_comparison and 'prev_dashboard_data' in st.session_state:
        comparisons = calculate_comparison_metrics(metrics, st.session_state.prev_dashboard_data)
    else:
        comparisons = None
    
    # Key Metrics Row
    st.markdown("### 📊 Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if comparisons:
            st.metric(
                "Total Orders",
                f"{metrics['total_orders']:,}",
                f"{comparisons['total_orders']['growth']:+.1f}%",
                help="Total number of orders vs. previous period"
            )
        else:
            st.metric("Total Orders", f"{metrics['total_orders']:,}")
    
    with col2:
        if comparisons:
            st.metric(
                "Total Revenue",
                f"₹{metrics['total_revenue']:,.2f}",
                f"{comparisons['total_revenue']['growth']:+.1f}%",
                help="Total revenue vs. previous period"
            )
        else:
            st.metric("Total Revenue", f"₹{metrics['total_revenue']:,.2f}")
    
    with col3:
        if comparisons:
            st.metric(
                "Units Sold",
                f"{metrics['total_units']:,}",
                f"{comparisons['total_units']['growth']:+.1f}%",
                help="Total units sold vs. previous period"
            )
        else:
            st.metric("Units Sold", f"{metrics['total_units']:,}")
    
    with col4:
        if comparisons:
            st.metric(
                "Avg Order Value",
                f"₹{metrics['avg_order_value']:,.2f}",
                f"{comparisons['avg_order_value']['growth']:+.1f}%",
                help="Average order value vs. previous period"
            )
        else:
            st.metric("Avg Order Value", f"₹{metrics['avg_order_value']:,.2f}")
    
    st.markdown("---")
    
    # Secondary Metrics
    st.markdown("### 🎯 Business Health Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        cancellation_rate = (metrics['canceled_orders'] / metrics['total_orders'] * 100) if metrics['total_orders'] > 0 else 0
        st.metric(
            "Cancellation Rate",
            f"{cancellation_rate:.1f}%",
            f"-{metrics['canceled_orders']} orders",
            delta_color="inverse",
            help="Percentage of canceled orders"
        )
    
    with col2:
        return_rate = (metrics['returned_units'] / metrics['total_units'] * 100) if metrics['total_units'] > 0 else 0
        st.metric(
            "Return Rate",
            f"{return_rate:.1f}%",
            f"-{metrics['returned_units']} units",
            delta_color="inverse",
            help="Percentage of returned/unshipped units"
        )
    
    with col3:
        st.metric(
            "Avg Fulfillment Time",
            f"{metrics['avg_fulfillment_hours']:.1f} hrs",
            help="Average time from order to shipment"
        )
    
    with col4:
        st.metric(
            "Repeat Customer Rate",
            f"{metrics['repeat_customer_rate']:.1f}%",
            f"{metrics['repeat_customers']} repeat orders",
            help="Percentage of orders from repeat customers"
        )
    
    st.markdown("---")

    # NEW SECTION: Financial Breakdown & Unit Economics
    st.markdown("### 💰 Financial Breakdown & Unit Economics")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Revenue Breakdown")
        breakdown = metrics['revenue_breakdown']
        
        # Waterfall Chart
        fig_waterfall = go.Figure(go.Waterfall(
            name = "Revenue Walk",
            orientation = "v",
            measure = ["relative", "relative", "relative", "relative", "total"],
            x = ["Product Sales", "Tax Collected", "Shipping", "Discounts", "Total Collected"],
            textposition = "outside",
            text = [
                f"₹{breakdown['product_sales']:,.0f}",
                f"₹{breakdown['tax']:,.0f}",
                f"₹{breakdown['shipping']:,.0f}",
                f"-₹{breakdown['discount']:,.0f}",
                f"₹{metrics['total_revenue']:,.0f}"
            ],
            y = [
                breakdown['product_sales'],
                breakdown['tax'],
                breakdown['shipping'],
                -breakdown['discount'],
                0 
            ],
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))
        
        fig_waterfall.update_layout(title = "Revenue Components", showlegend = False, height=350)
        st.plotly_chart(fig_waterfall, use_container_width=True)

    with col2:
        st.subheader("Unit Economics (Per Order Averages)")
        
        ue_col1, ue_col2 = st.columns(2)
        with ue_col1:
            st.metric("Avg Selling Price (Unit)", f"₹{metrics['avg_selling_price']:,.2f}")
            st.metric("Avg Tax per Order", f"₹{(breakdown['tax']/metrics['total_orders'] if metrics['total_orders'] else 0):,.2f}")
        with ue_col2:
            st.metric("Avg Shipping Cost (Charged)", f"₹{(breakdown['shipping']/metrics['total_orders'] if metrics['total_orders'] else 0):,.2f}")
            st.metric("Avg Discount", f"₹{(breakdown['discount']/metrics['total_orders'] if metrics['total_orders'] else 0):,.2f}")
            
        st.info(
            "ℹ️ **Note:** These are gross collected amounts. "
            "Net Profit requires deduction of COGS and Amazon Fees (refer to Settlement Reports)."
        )

    st.markdown("---")

    # NEW SECTION: Geographic Distribution
    st.markdown("### 🌍 Geographic Distribution")
    
    geo_col1, geo_col2 = st.columns(2)
    
    with geo_col1:
        if metrics['geo_distribution']['states']:
            st.subheader("Orders by State")
            df_geo = pd.DataFrame([
                {'State': k, 'Orders': v} 
                for k, v in metrics['geo_distribution']['states'].items()
            ])
            df_geo = df_geo.sort_values('Orders', ascending=True).tail(10) # Top 10
            
            fig_geo = px.bar(df_geo, x='Orders', y='State', orientation='h', title="Top 10 States")
            st.plotly_chart(fig_geo, use_container_width=True)
            
    with geo_col2:
        if metrics['geo_distribution']['cities']:
            st.subheader("Orders by City")
            df_city = pd.DataFrame([
                {'City': k, 'Orders': v} 
                for k, v in metrics['geo_distribution']['cities'].items()
            ])
            df_city = df_city.sort_values('Orders', ascending=True).tail(10) # Top 10
            
            fig_city = px.bar(df_city, x='Orders', y='City', orientation='h', title="Top 10 Cities")
            st.plotly_chart(fig_city, use_container_width=True)

    st.markdown("---")
    
    # Charts Row 1
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Daily Orders & Revenue Trend")
        if metrics['daily_orders']:
            df_daily = pd.DataFrame([
                {
                    'Date': date,
                    'Orders': metrics['daily_orders'].get(date, 0),
                    'Revenue': metrics['daily_revenue'].get(date, 0)
                }
                for date in sorted(set(list(metrics['daily_orders'].keys()) + list(metrics['daily_revenue'].keys())))
            ])
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_daily['Date'],
                y=df_daily['Orders'],
                name='Orders',
                yaxis='y',
                marker_color='lightblue'
            ))
            fig.add_trace(go.Scatter(
                x=df_daily['Date'],
                y=df_daily['Revenue'],
                name='Revenue',
                yaxis='y2',
                line=dict(color='orange', width=2)
            ))
            
            fig.update_layout(
                height=350,
                yaxis=dict(title='Orders'),
                yaxis2=dict(title='Revenue (₹)', overlaying='y', side='right'),
                legend=dict(orientation='h', yanchor='bottom', y=1.02),
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### ⏰ Order Patterns")
        
        tab1, tab2 = st.tabs(["Hourly", "Weekly"])
        
        with tab1:
            if metrics['hourly_orders']:
                df_hourly = pd.DataFrame([
                    {'Hour': f"{hour:02d}:00", 'Orders': count}
                    for hour, count in sorted(metrics['hourly_orders'].items())
                ])
                fig = px.bar(df_hourly, x='Hour', y='Orders', color='Orders', color_continuous_scale='Blues')
                fig.update_layout(height=280, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            if metrics['day_of_week_orders']:
                days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                df_weekly = pd.DataFrame([
                    {'Day': day, 'Orders': metrics['day_of_week_orders'].get(day, 0)}
                    for day in days_order
                ])
                fig = px.bar(df_weekly, x='Day', y='Orders', color='Orders', color_continuous_scale='Greens')
                fig.update_layout(height=280, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
    
    # Charts Row 2
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📦 Fulfillment Analysis")
        if metrics['fulfillment_method']:
            df_fulfillment = pd.DataFrame([
                {'Method': method, 'Orders': count}
                for method, count in metrics['fulfillment_method'].items()
            ])
            fig = px.pie(df_fulfillment, values='Orders', names='Method', hole=0.4)
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 📊 Order Status Distribution")
        if metrics['orders_by_status']:
            df_status = pd.DataFrame([
                {'Status': status, 'Count': count}
                for status, count in metrics['orders_by_status'].items()
            ])
            fig = px.bar(df_status, x='Status', y='Count', color='Status')
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Top Products with filtering
    st.markdown("### 🏆 Product Performance")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        product_search = st.text_input("🔍 Search products", placeholder="Enter product name or SKU...")
    with col2:
        sort_by = st.selectbox("Sort by", ["Units Sold", "Revenue"])
    with col3:
        top_n = st.slider("Show top", 10, 50, 20)
    
    if metrics['top_products']:
        top_products_list = [
            {
                'SKU': sku,
                'Product Name': data['name'],
                'Units Sold': data['quantity'],
                'Revenue': data['revenue'],
                'Avg Price': data['revenue'] / data['quantity'] if data['quantity'] > 0 else 0
            }
            for sku, data in metrics['top_products'].items()
        ]
        
        # Apply search filter
        if product_search:
            top_products_list = [
                p for p in top_products_list
                if product_search.lower() in p['Product Name'].lower() or product_search.lower() in p['SKU'].lower()
            ]
        
        # Sort
        if sort_by == "Revenue":
            top_products_list = sorted(top_products_list, key=lambda x: x['Revenue'], reverse=True)
        else:
            top_products_list = sorted(top_products_list, key=lambda x: x['Units Sold'], reverse=True)
        
        # Limit results
        top_products_list = top_products_list[:top_n]
        
        # Format for display
        for p in top_products_list:
            p['Revenue'] = f"₹{p['Revenue']:,.2f}"
            p['Avg Price'] = f"₹{p['Avg Price']:,.2f}"
        
        df_products = pd.DataFrame(top_products_list)
        st.dataframe(df_products, use_container_width=True, height=400)
    
    st.markdown("---")
    
    # Quick Insights
    st.markdown("### 💡 Quick Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🎯 Performance Highlights**")
        
        # Best performing day
        if metrics['day_of_week_orders']:
            best_day = max(metrics['day_of_week_orders'].items(), key=lambda x: x[1])
            st.write(f"• Best day: **{best_day[0]}** ({best_day[1]} orders)")
        
        # Best selling product
        if metrics['top_products']:
            best_product = max(metrics['top_products'].items(), key=lambda x: x[1]['quantity'])
            st.write(f"• Top product: **{best_product[1]['name'][:40]}...** ({best_product[1]['quantity']} units)")
        
        # Peak hour
        if metrics['hourly_orders']:
            peak_hour = max(metrics['hourly_orders'].items(), key=lambda x: x[1])
            st.write(f"• Peak hour: **{peak_hour[0]:02d}:00** ({peak_hour[1]} orders)")
        
        # Customer loyalty
        if metrics['total_customers'] > 0:
            st.write(f"• Unique customers: **{metrics['total_customers']}**")
            avg_orders_per_customer = metrics['total_orders'] / metrics['total_customers']
            st.write(f"• Avg orders per customer: **{avg_orders_per_customer:.2f}**")
    
    with col2:
        st.markdown("**⚠️ Areas to Monitor**")
        
        # Check cancellation rate
        if cancellation_rate > 5:
            st.warning(f"• High cancellation rate: {cancellation_rate:.1f}%")
        else:
            st.success(f"• Cancellation rate is healthy: {cancellation_rate:.1f}%")
        
        # Check return rate
        if return_rate > 10:
            st.warning(f"• High return rate: {return_rate:.1f}%")
        else:
            st.success(f"• Return rate is acceptable: {return_rate:.1f}%")
        
        # Check fulfillment time
        if metrics['avg_fulfillment_hours'] > 48:
            st.warning(f"• Slow fulfillment: {metrics['avg_fulfillment_hours']:.1f} hours")
        elif metrics['avg_fulfillment_hours'] > 0:
            st.success(f"• Good fulfillment time: {metrics['avg_fulfillment_hours']:.1f} hours")
        
        # Growth indicator
        if comparisons and comparisons['total_revenue']['growth'] < -10:
            st.error(f"• Revenue declining: {comparisons['total_revenue']['growth']:.1f}%")
        elif comparisons and comparisons['total_revenue']['growth'] > 10:
            st.success(f"• Strong revenue growth: {comparisons['total_revenue']['growth']:.1f}%")
    
    st.markdown("---")
    
    # Export Options
    st.markdown("### 📥 Export Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export Full Report", use_container_width=True):
            summary = f"""
AMAZON SELLER DASHBOARD - COMPREHENSIVE REPORT
{'='*60}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}

KEY PERFORMANCE INDICATORS
{'-'*60}
Total Orders: {metrics['total_orders']:,}
Total Revenue: ₹{metrics['total_revenue']:,.2f}
Total Units Sold: {metrics['total_units']:,}
Average Order Value: ₹{metrics['avg_order_value']:,.2f}
Avg Selling Price: ₹{metrics['avg_selling_price']:,.2f}

REVENUE BREAKDOWN
{'-'*60}
Product Sales: ₹{metrics['revenue_breakdown']['product_sales']:,.2f}
Tax Collected: ₹{metrics['revenue_breakdown']['tax']:,.2f}
Shipping Charges: ₹{metrics['revenue_breakdown']['shipping']:,.2f}
Discounts: -₹{metrics['revenue_breakdown']['discount']:,.2f}

BUSINESS HEALTH METRICS
{'-'*60}
Cancellation Rate: {cancellation_rate:.2f}%
Return Rate: {return_rate:.2f}%
Avg Fulfillment Time: {metrics['avg_fulfillment_hours']:.1f} hours
Repeat Customer Rate: {metrics['repeat_customer_rate']:.2f}%
Total Unique Customers: {metrics['total_customers']}

ORDER STATUS BREAKDOWN
{'-'*60}
{chr(10).join([f"{status}: {count:,}" for status, count in metrics['orders_by_status'].items()])}

FULFILLMENT METHOD
{'-'*60}
{chr(10).join([f"{method}: {count:,}" for method, count in metrics['fulfillment_method'].items()])}

TOP 10 PRODUCTS
{'-'*60}
{chr(10).join([f"{i+1}. {p['Product Name'][:50]} - {p['Units Sold']} units - {p['Revenue']}" 
              for i, p in enumerate(top_products_list[:10])])}

GROWTH COMPARISON (vs Previous Period)
{'-'*60}
"""
            if comparisons:
                summary += f"""Orders Growth: {comparisons['total_orders']['growth']:+.2f}%
Revenue Growth: {comparisons['total_revenue']['growth']:+.2f}%
Units Growth: {comparisons['total_units']['growth']:+.2f}%
AOV Growth: {comparisons['avg_order_value']['growth']:+.2f}%
"""
            
            st.download_button(
                "Download Full Report",
                summary,
                f"full_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "text/plain"
            )
    
    with col2:
        if st.button("📦 Export Products CSV", use_container_width=True):
            df_export = pd.DataFrame(top_products_list)
            csv = df_export.to_csv(index=False)
            st.download_button(
                "Download Products CSV",
                csv,
                f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv"
            )
    
    with col3:
        if st.button("📋 Export Orders CSV", use_container_width=True):
            df_export = pd.DataFrame([
                {
                    'Order ID': order['AmazonOrderId'],
                    'Purchase Date': order['PurchaseDate'],
                    'Status': order.get('OrderStatus', 'N/A'),
                    'Total Amount': order.get('OrderTotal', {}).get('Amount', 0),
                    'Currency': order.get('OrderTotal', {}).get('CurrencyCode', 'INR'),
                    'Fulfillment': order.get('FulfillmentChannel', 'N/A'),
                    'Items': order.get('NumberOfItemsShipped', 0) + order.get('NumberOfItemsUnshipped', 0),
                }
                for order in st.session_state.orders
            ])
            csv = df_export.to_csv(index=False)
            st.download_button(
                "Download Orders CSV",
                csv,
                f"orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv"
            )

else:
    st.info("👆 Click 'Refresh Data' in the sidebar to load dashboard data")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Amazon Seller Dashboard Pro | "
    "Built with Streamlit | Enhanced Analytics</div>",
    unsafe_allow_html=True
)