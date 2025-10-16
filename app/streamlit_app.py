"""Streamlit web interface for FinPulse."""

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="FinPulse - Financial Report Generator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main Streamlit app."""
    
    # Header
    st.title("📊 FinPulse - AI-Powered Financial Reports")
    st.markdown("*Generate intelligent financial analysis from SEC filings*")
    
    # Sidebar
    st.sidebar.header("Configuration")
    
    # Input controls
    ticker = st.sidebar.text_input(
        "Company Ticker",
        value="AAPL",
        help="Enter a stock ticker symbol (e.g., AAPL, MSFT, GOOGL)"
    ).upper()
    
    filing_scope = st.sidebar.selectbox(
        "Filing Type",
        options=["10-Q", "10-K"],
        index=0,
        help="10-Q for quarterly reports, 10-K for annual reports"
    )
    
    query = st.sidebar.text_area(
        "Analysis Query",
        value="latest quarterly performance",
        help="Customize what aspects to focus on in the analysis"
    )
    
    # Generate button
    generate_btn = st.sidebar.button("🚀 Generate Report", type="primary")
    
    # Main content area
    if generate_btn:
        if not ticker:
            st.error("Please enter a ticker symbol")
            return
        
        # TODO: Implement report generation functionality
        st.info("⚠️ This is a skeleton implementation. Please implement the core functionality.")
        
        st.write(f"**Ticker:** {ticker}")
        st.write(f"**Scope:** {filing_scope}")
        st.write(f"**Query:** {query}")
        
        st.warning("Report generation functionality needs to be implemented.")
    
    else:
        # Welcome message
        st.markdown("""
        ## Welcome to FinPulse! 🚀
        
        FinPulse uses AI to analyze SEC filings and generate intelligent financial reports. 
        Simply enter a company ticker symbol and select the type of filing you'd like to analyze.
        
        ### Features (To Be Implemented):
        - 📊 **KPI Extraction**: Automatically extracts key financial metrics
        - 🤖 **AI Analysis**: Uses Google Gemini to generate intelligent insights
        - 🔍 **RAG Pipeline**: Retrieves relevant information from SEC filings
        - 📈 **Visualization**: Interactive charts and tables
        
        ### How to use:
        1. Enter a stock ticker symbol (e.g., AAPL, MSFT, GOOGL)
        2. Select filing type (10-Q for quarterly, 10-K for annual)
        3. Optionally customize the analysis query
        4. Click "Generate Report" to start the analysis
        
        ### Example tickers to try:
        - **AAPL** - Apple Inc.
        - **MSFT** - Microsoft Corporation  
        - **GOOGL** - Alphabet Inc.
        - **TSLA** - Tesla Inc.
        - **AMZN** - Amazon.com Inc.
        """)

if __name__ == "__main__":
    main()