"""Streamlit web interface for FinPulse."""

import logging
import sys
from pathlib import Path

import streamlit as st
import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from report.generator import ReportGenerator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="FinPulse - Financial Report Generator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def get_report_generator():
    """Get cached report generator instance."""
    return ReportGenerator()

def format_kpi_value(value: float) -> str:
    """Format KPI values for display."""
    if abs(value) >= 1e9:
        return f"${value/1e9:.2f}B"
    elif abs(value) >= 1e6:
        return f"${value/1e6:.2f}M"
    elif abs(value) >= 1e3:
        return f"${value/1e3:.2f}K"
    else:
        return f"${value:.2f}"

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
        
        # Initialize generator
        try:
            with st.spinner("Initializing FinPulse..."):
                generator = get_report_generator()
            
            # Generate report
            with st.spinner(f"Generating {filing_scope} report for {ticker}..."):
                result = generator.generate_report(
                    ticker=ticker,
                    form_type=filing_scope,
                    query=query
                )
            
            # Display results
            st.success(f"✅ Report generated successfully!")
            
            # Company info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Company", result.get('entityName', 'Unknown'))
            with col2:
                st.metric("CIK", result['cik'])
            with col3:
                st.metric("Filings Analyzed", result['filings_analyzed'])
            
            # KPI metrics
            st.subheader("📈 Key Financial Metrics")
            
            if result['kpis']:
                # Create KPI table
                kpi_data = []
                for kpi_name, kpi_info in result['kpis'].items():
                    kpi_data.append({
                        'Metric': kpi_name,
                        'Value': format_kpi_value(kpi_info.get('value', 0)),
                        'Period': kpi_info.get('period', 'Unknown'),
                        'Filing': kpi_info.get('form', 'Unknown'),
                        'Filed': kpi_info.get('filed', 'Unknown')
                    })
                
                kpi_df = pd.DataFrame(kpi_data)
                st.dataframe(kpi_df, use_container_width=True)
                
                # KPI visualization
                if len(result['kpis']) >= 2:
                    st.subheader("📊 KPI Overview")
                    
                    # Create a simple bar chart for numeric KPIs
                    numeric_kpis = []
                    kpi_names = []
                    
                    for kpi_name, kpi_info in result['kpis'].items():
                        value = kpi_info.get('value', 0)
                        if abs(value) > 0:  # Only include non-zero values
                            numeric_kpis.append(abs(value))
                            kpi_names.append(kpi_name)
                    
                    if numeric_kpis:
                        chart_df = pd.DataFrame({
                            'KPI': kpi_names,
                            'Value (Absolute)': numeric_kpis
                        })
                        st.bar_chart(chart_df.set_index('KPI'))
            else:
                st.warning("No KPI data available for this company")
            
            # Financial analysis
            st.subheader("🤖 AI Financial Analysis")
            st.markdown(result['narrative'])
            
            # Sources
            if result['sources']:
                st.subheader("📚 Sources")
                
                for i, (doc, url, score) in enumerate(result['sources'], 1):
                    with st.expander(f"Source {i} (Relevance: {score:.3f})"):
                        st.markdown(f"**URL:** [{url}]({url})")
                        st.markdown(f"**Content Preview:**")
                        st.text(doc[:500] + "..." if len(doc) > 500 else doc)
            
            # Disclaimer
            st.markdown("---")
            st.warning("""
            ⚠️ **Disclaimer:** This analysis is for informational purposes only. 
            Not intended as investment advice. Please consult a financial advisor 
            before making investment decisions.
            """)
            
        except Exception as e:
            st.error(f"❌ Error generating report: {str(e)}")
            logger.error(f"Report generation failed: {e}")
    
    else:
        # Welcome message
        st.markdown("""
        ## Welcome to FinPulse! 🚀
        
        FinPulse uses AI to analyze SEC filings and generate intelligent financial reports. 
        Simply enter a company ticker symbol and select the type of filing you'd like to analyze.
        
        ### Features:
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
