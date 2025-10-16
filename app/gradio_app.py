"""Gradio web interface for FinPulse."""

import gradio as gr

def generate_report(ticker, filing_scope, query):
    """Generate financial report based on inputs."""
    # TODO: Implement report generation functionality
    return f"""
    # FinPulse Report - Skeleton Implementation
    
    **Ticker:** {ticker}
    **Scope:** {filing_scope}
    **Query:** {query}
    
    ⚠️ This is a skeleton implementation. Please implement the core functionality.
    
    Report generation functionality needs to be implemented.
    """

def main():
    """Main Gradio app."""
    
    with gr.Blocks(title="FinPulse - Financial Report Generator") as app:
        gr.Markdown("# 📊 FinPulse - AI-Powered Financial Reports")
        gr.Markdown("*Generate intelligent financial analysis from SEC filings*")
        
        with gr.Row():
            with gr.Column():
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
                
                generate_btn = gr.Button("🚀 Generate Report", variant="primary")
            
            with gr.Column():
                report_output = gr.Markdown(
                    value="""
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
                    """
                )
        
        generate_btn.click(
            fn=generate_report,
            inputs=[ticker_input, filing_scope, query_input],
            outputs=report_output
        )
    
    return app

if __name__ == "__main__":
    app = main()
    app.launch()