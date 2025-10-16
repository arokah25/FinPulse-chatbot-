"""Main entry point for FinPulse CLI."""

import argparse
import logging
import sys

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
    
    # TODO: Implement CLI functionality
    print("FinPulse CLI - Skeleton Implementation")
    print(f"Ticker: {args.ticker}")
    print(f"Scope: {args.scope}")
    print(f"Query: {args.query}")
    print("\n⚠️  This is a skeleton implementation. Please implement the core functionality.")

if __name__ == "__main__":
    main()
