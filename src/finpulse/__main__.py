"""Main entry point for FinPulse CLI."""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from src.finpulse.report.generator import ReportGenerator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="FinPulse - AI-powered financial report chatbot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m finpulse --ticker AAPL --scope 10Q
  python -m finpulse --ticker MSFT --scope 10K
  python -m finpulse --ticker GOOGL --scope 10Q --query "revenue growth and profitability"
        """
    )
    
    parser.add_argument(
        '--ticker',
        required=True,
        help='Stock ticker symbol (e.g., AAPL, MSFT)'
    )
    
    parser.add_argument(
        '--scope',
        choices=['10K', '10Q'],
        default='10Q',
        help='Filing type to analyze (default: 10Q)'
    )
    
    parser.add_argument(
        '--query',
        default='latest quarterly performance',
        help='Query for document retrieval (default: "latest quarterly performance")'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize report generator
        logger.info("Initializing FinPulse report generator...")
        generator = ReportGenerator()
        
        # Generate report
        logger.info(f"Generating {args.scope} report for {args.ticker}")
        result = generator.generate_report(
            ticker=args.ticker.upper(),
            form_type=args.scope,
            query=args.query
        )
        
        # Print results
        print("\n" + "="*60)
        print(f"FINANCIAL REPORT: {result['ticker']} ({result['form_type']})")
        print("="*60)
        
        print(f"\nCompany: {result.get('entityName', 'Unknown')}")
        print(f"CIK: {result['cik']}")
        print(f"Filings Analyzed: {result['filings_analyzed']}")
        print(f"Query: {result['query']}")
        
        print("\n" + "-"*40)
        print("KEY FINANCIAL METRICS")
        print("-"*40)
        
        if result['kpis']:
            for kpi_name, kpi_data in result['kpis'].items():
                value = kpi_data.get('value', 0)
                period = kpi_data.get('period', 'Unknown')
                form = kpi_data.get('form', 'Unknown')
                
                # Format large numbers
                if abs(value) >= 1e9:
                    formatted_value = f"${value/1e9:.2f}B"
                elif abs(value) >= 1e6:
                    formatted_value = f"${value/1e6:.2f}M"
                elif abs(value) >= 1e3:
                    formatted_value = f"${value/1e3:.2f}K"
                else:
                    formatted_value = f"${value:.2f}"
                
                print(f"{kpi_name:30} {formatted_value:>15} ({period})")
        else:
            print("No KPI data available")
        
        print("\n" + "-"*40)
        print("FINANCIAL ANALYSIS")
        print("-"*40)
        print(result['narrative'])
        
        if result['sources']:
            print("\n" + "-"*40)
            print("SOURCES")
            print("-"*40)
            for i, (doc, url, score) in enumerate(result['sources'], 1):
                print(f"[S{i}] {url} (relevance: {score:.3f})")
        
        print("\n" + "="*60)
        print("DISCLAIMER: This analysis is for informational purposes only.")
        print("Not intended as investment advice. Please consult a financial advisor.")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
