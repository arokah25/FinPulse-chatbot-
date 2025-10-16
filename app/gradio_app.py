"""Gradio web interface for FinPulse."""

import logging
import sys
from pathlib import Path

import gradio as gr
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

# Global variable to cache the report generator
_generator = None

def get_report_generator():
    """Get cached report generator instance."""
    global _generator
    if _generator is None:
        _generator = ReportGenerator()
    return _generator

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

def generate_report(ticker, filing_scope, query, progress=gr.Progress()):
    """Generate financial report based on inputs."""
    if not ticker:
        return "❌ Please enter a ticker symbol", "", ""
    
    try:
        progress(0.1, desc="Initializing FinPulse...")
        generator = get_report_generator()
        
        progress(0.3, desc=f"Generating {filing_scope} report for {ticker}...")
        result = generator.generate_report(
            ticker=ticker.upper(),
            form_type=filing_scope,
            query=query
        )
        
        progress(0.8, desc="Formatting results...")
        
        # Format company info
        company_info = f"""
        **Company:** {result.get('entityName', 'Unknown')}  
        **CIK:** {result['cik']}  
        **Filings Analyzed:** {result['filings_analyzed']}
        """
        
        # Format KPI table
        if result['kpis']:
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
            kpi_table = kpi_df.to_markdown(index=False)
        else:
            kpi_table = "No KPI data available for this company"
        
        # Format analysis with sources
        analysis_text = f"""
        ## 🤖 AI Financial Analysis
        
        {result['narrative']}
        
        ## 📚 Sources
        
        """
        
        if result['sources']:
            for i, (doc, url, score) in enumerate(result['sources'], 1):
                analysis_text += f"""
        **Source {i}** (Relevance: {score:.3f})  
        URL: [{url}]({url})  
        Content Preview: {doc[:300]}...
        
        """
        
        analysis_text += """
        ---
        
        ⚠️ **Disclaimer:** This analysis is for informational purposes only. 
        Not intended as investment advice. Please consult a financial advisor 
        before making investment decisions.
        """
        
        progress(1.0, desc="Report generated successfully!")
        return f"✅ Report generated successfully for {ticker}!", company_info, kpi_table, analysis_text
        
    except Exception as e:
        error_msg = f"❌ Error generating report: {str(e)}"
        logger.error(f"Report generation failed: {e}")
        return error_msg, "", "", ""

def main():
    """Main Gradio app."""
    
    with gr.Blocks(
        title="FinPulse - Financial Report Generator",
        theme=gr.themes.Soft(),
        css="""
        .gradio-container {
            max-width: 1200px !important;
        }
        """
    ) as app:
        gr.Markdown("# 📊 FinPulse - AI-Powered Financial Reports")
        gr.Markdown("*Generate intelligent financial analysis from SEC filings*")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Configuration")
                
                ticker_input = gr.Textbox(
                    label="Company Ticker",
                    placeholder="AAPL",
                    info="Enter a stock ticker symbol (e.g., AAPL, MSFT, GOOGL)",
                    value="AAPL"
                )
                
                filing_scope = gr.Dropdown(
                    choices=["10-Q", "10-K"],
                    label="Filing Type",
                    info="10-Q for quarterly reports, 10-K for annual reports",
                    value="10-Q"
                )
                
                query_input = gr.Textbox(
                    label="Analysis Query",
                    placeholder="latest quarterly performance",
                    info="Customize what aspects to focus on in the analysis",
                    value="latest quarterly performance",
                    lines=3
                )
                
                generate_btn = gr.Button("🚀 Generate Report", variant="primary", size="lg")
            
            with gr.Column(scale=2):
                status_output = gr.Markdown()
                
                with gr.Tabs():
                    with gr.Tab("Company Info"):
                        company_info_output = gr.Markdown()
                    
                    with gr.Tab("KPI Metrics"):
                        kpi_table_output = gr.Markdown()
                    
                    with gr.Tab("Analysis & Sources"):
                        analysis_output = gr.Markdown()
        
        # Welcome message
        welcome_text = """
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
        """
        
        # Initialize with welcome message
        company_info_output.value = welcome_text
        
        # Set up the generate button click handler
        generate_btn.click(
            fn=generate_report,
            inputs=[ticker_input, filing_scope, query_input],
            outputs=[status_output, company_info_output, kpi_table_output, analysis_output],
            show_progress=True
        )
    
    return app

if __name__ == "__main__":
    app = main()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
