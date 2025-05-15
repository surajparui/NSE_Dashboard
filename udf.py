import streamlit as st
import pandas as pd
from jugaad_data.nse.live import NSELive
from streamlit_autorefresh import st_autorefresh

# Set page configuration
st.set_page_config(page_title="Live NSE Dashboard", layout="wide")

# Auto-refresh every 1000 ms (1 second)
st_autorefresh(interval=1000, key="data_refresh")

# Initialize NSE API
live = NSELive()

def fetch_data(symbol):
    """Fetch both price and market data for a given symbol"""
    try:
        # Get price info for display
        price_data = live.stock_quote(symbol)
        
        # Get trade info for detailed analysis
        trade_data = live.trade_info(symbol)
        
        return price_data, trade_data
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {e}")
        return None, None

def create_trade_dashboard(price_data, trade_data):
    """Create a comprehensive dashboard with all trade information"""
    
    # Extract relevant data
    price_info = price_data.get('priceInfo', {})
    market_data = trade_data.get("marketDeptOrderBook", {})
    
    # 1. Price Info (Transposed)
    price_info_df = pd.DataFrame([{
        'lastPrice': price_info.get('lastPrice', 'N/A'),
        'open': price_info.get('open', 'N/A'),
        'close': price_info.get('close', 'N/A'),
        'high': price_info.get('intraDayHighLow', {}).get('max', 'N/A'),
        'low': price_info.get('intraDayHighLow', {}).get('min', 'N/A'),
        'change': price_info.get('change', 'N/A'),
        'pChange': price_info.get('pChange', 'N/A'),
        'previousClose': price_info.get('previousClose', 'N/A'),
        'vwap': price_info.get('vwap', 'N/A')
    }]).T.rename(columns={0: 'Value'})
    
    # Convert all values to strings to avoid Arrow serialization issues
    price_info_df['Value'] = price_info_df['Value'].astype(str)
    
    # 2. Market Summary (Transposed)
    market_summary = pd.DataFrame([{
        'totalBuyQuantity': market_data.get('totalBuyQuantity', 'N/A'),
        'totalSellQuantity': market_data.get('totalSellQuantity', 'N/A'),
        'lastQuantity': market_data.get('lastQuantity', 'N/A'),
        'totalTradedVolume': market_data.get('totalTradedVolume', 'N/A'),
        'averagePrice': price_info.get('averagePrice', 'N/A'),
        'dayVolume': price_info.get('totalTradedVolume', 'N/A'),
        'marketCap': price_info.get('marketCap', 'N/A')
    }]).T.rename(columns={0: 'Value'})
    
    # Convert all values to strings to avoid Arrow serialization issues
    market_summary['Value'] = market_summary['Value'].astype(str)
    
    # 3. Order Book - Bids and Asks
    if 'bid' in market_data and 'ask' in market_data:
        bids = pd.DataFrame(market_data['bid']).rename(columns={'price': 'Bid Price', 'quantity': 'Bid Quantity'})
        asks = pd.DataFrame(market_data['ask']).rename(columns={'price': 'Ask Price', 'quantity': 'Ask Quantity'})
        order_book = pd.concat([bids.reset_index(drop=True), asks.reset_index(drop=True)], axis=1)
        
        # Convert all values to strings to avoid Arrow serialization issues
        for col in order_book.columns:
            order_book[col] = order_book[col].astype(str)
    else:
        order_book = pd.DataFrame(columns=['Bid Price', 'Bid Quantity', 'Ask Price', 'Ask Quantity'])
    
    # 4. Trade Info details
    if 'tradeInfo' in market_data:
        trade_info_dict = market_data['tradeInfo']
    else:
        trade_info_dict = {}
    
    # Add additional trade info from price data
    price_meta = price_data.get('metadata', {})
    trade_info_dict.update({
        'tradingStatus': price_meta.get('tradingStatus', 'N/A'),
        'industry': price_meta.get('industry', 'N/A'),
        'symbol': price_meta.get('symbol', 'N/A'),
        'listingDate': price_meta.get('listingDate', 'N/A'),
        'isin': price_meta.get('isin', 'N/A')
    })
    
    trade_info = pd.DataFrame([trade_info_dict]).T.rename(columns={0: 'Value'})
    
    # Convert all values to strings to avoid Arrow serialization issues
    trade_info['Value'] = trade_info['Value'].astype(str)
    
    # Combined dashboard
    dashboard = {
        'price_info': price_info_df,
        'market_summary': market_summary,
        'order_book': order_book,
        'trade_info': trade_info
    }
    
    return dashboard, price_info

# App title and description
st.title("📡 NSE Live Dashboard")
st.markdown("Real-time market data from the National Stock Exchange of India")

# User input with default value
col1, col2 = st.columns([3, 1])
with col1:
    symbol = st.text_input("Enter NSE Symbol", "RELIANCE").upper()
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    refresh_button = st.button("🔄 Refresh Data")

# Dynamically update browser tab title
st.markdown(f"""
<script>
    document.title = "NSE Live Dashboard - {symbol}";
</script>
""", unsafe_allow_html=True)

# Create a placeholder for stock price
price_placeholder = st.empty()

# Fetch data and display dashboard
price_data, trade_data = fetch_data(symbol)
if price_data and trade_data:
    # Create dashboard
    dashboard, price_info = create_trade_dashboard(price_data, trade_data)
    
    # Display current price with color based on change
    price_change = price_info.get('pChange', 0)
    if isinstance(price_change, str):
        try:
            price_change = float(price_change)
        except:
            price_change = 0
            
    color = "green" if price_change > 0 else "red" if price_change < 0 else "gray"
    
    with price_placeholder.container():
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <h2 style="margin: 0;">{symbol}</h2>
            <h3 style="margin: 0 0 0 20px; color: {color};">
                ₹{price_info.get('lastPrice', 'N/A')}
                <span style="font-size: 0.8em;">({price_info.get('pChange', 'N/A')}%)</span>
            </h3>
        </div>
        """, unsafe_allow_html=True)
    
    # Display in a 2x2 grid layout
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Price Information")
        st.dataframe(dashboard['price_info'], use_container_width=True)

    with col2:
        st.subheader("📈 Market Summary")
        st.dataframe(dashboard['market_summary'], use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("📉 Order Book (Bids & Asks)")
        st.dataframe(dashboard['order_book'], use_container_width=True)

    with col4:
        st.subheader("🔁 Trade Information")
        st.dataframe(dashboard['trade_info'], use_container_width=True)
    
    # Add a timestamp to show when data was last updated
    st.caption(f"Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.warning(f"No data available for {symbol}. Please check if the symbol is correct.")

# Add some instructions and tips at the bottom
with st.expander("ℹ️ How to use this dashboard"):
    st.markdown("""
    - Enter a valid NSE symbol in the input box (e.g., RELIANCE, INFY, TCS)
    - Data refreshes automatically every second
    - Click the 'Refresh Data' button to force refresh
    - The dashboard shows:
        - Price information including current price, highs/lows and changes
        - Market summary with volume and quantity information
        - Order book with bid and ask prices
        - Detailed trade and company information
    """)