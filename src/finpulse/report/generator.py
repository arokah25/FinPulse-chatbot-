"""Report generator that orchestrates the entire FinPulse pipeline."""

import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv

from finpulse.ingest.edgar import EdgarClient
from finpulse.llm.gemini import GeminiClient
from finpulse.rag.indexer import DocumentIndexer
from finpulse.utils.dates import get_most_recent_period

# Load environment variables
load_dotenv()
# 
logger = logging.getLogger(__name__)

class ReportGenerator:
    """Orchestrates the complete financial report generation pipeline."""
    
    def __init__(self, cache_dir: str = "data/cache", chroma_dir: str = None):
        """Initialize the report generator.
        
        Args:
            cache_dir: Directory for caching data
            chroma_dir: Directory for ChromaDB storage
        """
        self.cache_dir = cache_dir
        self.chroma_dir = chroma_dir or os.getenv("CHROMA_DIR", f"{cache_dir}/chroma")
        
        # Initialize components
        self.edgar_client = EdgarClient(cache_dir)
        self.rag_indexer = DocumentIndexer(self.chroma_dir)
        
        # Initialize Gemini client with error handling
        try:
            self.gemini_client = GeminiClient()
            logger.info("Gemini client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise
        
        # Cache for processed tickers
        self.processed_cache = {}
    
    def generate_report(self, ticker: str, form_type: str = "10-Q", query: str = "latest quarterly performance") -> Dict:
        """Generate a complete financial report for a company.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            form_type: Type of filing to analyze ('10-Q' only)
            query: Query for document retrieval
            
        Returns:
            Dictionary containing KPIs and generated narrative
        """
        logger.info(f"Generating report for {ticker} ({form_type})")
        
        try:
            # Step 1: Resolve ticker to CIK
            cik = self.edgar_client.ticker_to_cik(ticker)
            if not cik:
                raise ValueError(f"Could not find CIK for ticker: {ticker}")
            
            logger.info(f"Found CIK {cik} for ticker {ticker}")
            
            # Step 2: Get company facts and extract KPIs
            logger.info("Fetching company financial facts...")
            company_facts = self.edgar_client.get_company_facts(cik)
            kpis = self.edgar_client.extract_kpis(company_facts)
            
            if not kpis:
                logger.warning(f"No KPIs found for {ticker}")
            
            # Step 3: Get latest filings
            logger.info(f"Fetching latest {form_type} filings...")
            filings = self.edgar_client.get_latest_filings(cik, form_type, limit=3)
            
            # Step 4: Get quarterly revenue (XBRL first, then text fallback)
            logger.info("Getting quarterly revenue from XBRL API...")
            quarterly_revenues = self.edgar_client.get_quarterly_revenue_from_xbrl(cik, limit=3)
            
            # If no XBRL revenue data, try extracting from filing text
            if not quarterly_revenues and filings:
                logger.info("No XBRL revenue data found, trying text extraction...")
                for filing in filings[:3]:  # Try last 3 filings
                    try:
                        filing_text = self.edgar_client.get_filing_text(
                            filing['accessionNumber'], 
                            filing['primaryDocument'], 
                            cik
                        )
                        report_date = filing.get('reportDate', 'Unknown')
                        revenue_value = self.edgar_client.extract_revenue_from_filing_text(filing_text, report_date)
                        if revenue_value > 0:
                            quarterly_revenues[report_date] = revenue_value
                            logger.info(f"Found revenue from text: ${revenue_value/1e9:.2f}B for {report_date}")
                    except Exception as e:
                        logger.warning(f"Failed to extract revenue from filing text: {e}")
                        continue
            
            # Add quarterly revenue data to KPIs
            if quarterly_revenues:
                # Calculate 9-month revenue (sum of last 3 quarters)
                total_9_month_revenue = sum(quarterly_revenues.values())
                if total_9_month_revenue > 0:
                    kpis['Revenue_9_Months'] = {
                        'value': total_9_month_revenue,
                        'period': f"Last {len(quarterly_revenues)} quarters ({', '.join(sorted(quarterly_revenues.keys()))})",
                        'form': '10-Q',
                        'filed': 'From SEC XBRL data and filing text'
                    }
                    logger.info(f"Added {len(quarterly_revenues)}-quarter revenue: ${total_9_month_revenue/1e9:.2f}B")

            # Build sources from filings for display
            def helper_build_url_from_filings(cik: str, accession_number: str, primary_document: str) -> str:
                acc = accession_number.replace("-", "")
                return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{primary_document}"
            
            display_sources = []
            for f in filings:
                url = helper_build_url_from_filings(cik, f['accessionNumber'], f['primaryDocument'])    
                label = f"{f['form']} filed {f['filingDate']}"
                display_sources.append((label, url, 1.0))

            sources = display_sources


            
            if not filings:
                raise ValueError(f"No {form_type} filings found for {ticker}")
            
            # Step 5: Check if we need to rebuild the index
            cache_key = f"{ticker}_{form_type}_{cik}"
            if cache_key not in self.processed_cache:
                logger.info("Building document index...")
                self._build_document_index(ticker, cik, filings)
                self.processed_cache[cache_key] = True
            
            # Step 6: Retrieve relevant documents
            logger.info(f"Retrieving documents for query: {query}")
            retrieved_docs = self.rag_indexer.retrieve(query, k=5)
            
            # Add fallback sources if no documents were retrieved
            if not retrieved_docs:
                logger.info("No documents retrieved, adding fallback sources")
                fallback_sources = [
                    (f"SEC EDGAR company facts data for {ticker}", f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json", 0.8),
                    (f"SEC EDGAR submissions for {ticker}", f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json", 0.7)
                ]
                retrieved_docs = fallback_sources
            
            # Step 6: Generate summary with Gemini
            logger.info("Generating financial summary...")
            narrative = self.gemini_client.summarize(kpis, retrieved_docs, user_query=query)
            
            # Step 7: Generate KPI table
            kpi_table = self.gemini_client.generate_kpi_table(kpis)
            


            return {
                'ticker': ticker,
                'cik': cik,
                'form_type': form_type,
                'kpis': kpis,
                'kpi_table': kpi_table,
                'narrative': narrative,
                'sources': sources,
                'filings_analyzed': len(filings),
                'query': query,
                'entityName': company_facts.get('entityName', 'Unknown')
            }
            
        except Exception as e:
            logger.error(f"Failed to generate report for {ticker}: {e}")
            raise
    
    def _build_document_index(self, ticker: str, cik: str, filings: List[Dict]):
        """Build the document index for a company's filings.
        
        Args:
            ticker: Stock ticker symbol
            cik: Company CIK number
            filings: List of filing data
        """
        documents = []
        metadata = []
        
        for filing in filings:
            try:
                accession_number = filing['accessionNumber']
                primary_document = filing['primaryDocument']
                filing_date = filing['filingDate']
                report_date = filing['reportDate']
                
                logger.info(f"Fetching filing: {primary_document}")
                
                # Fetch the filing text
                filing_text = self.edgar_client.get_filing_text(accession_number, primary_document, cik)
                
                # Convert accession number to URL format (remove dashes)
                accession_clean = accession_number.replace('-', '')

                # Create URL for this filing
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{primary_document}"
                documents.append((filing_text, filing_url))
                metadata.append({
                    'ticker': ticker,
                    'cik': cik,
                    'filing_date': filing_date,
                    'report_date': report_date,
                    'form': filing.get('form', 'Unknown'),
                    'accession_number': accession_number
                })
                
            except Exception as e:
                logger.error(f"Failed to process filing {filing.get('primaryDocument', 'Unknown')}: {e}")
                continue
        
        if documents:
            logger.info(f"Indexing {len(documents)} documents")
            self.rag_indexer.index_documents(documents, metadata)
        else:
            logger.warning("No documents to index")
    
    def get_company_info(self, ticker: str) -> Dict:
        """Get basic company information.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with company information
        """
        cik = self.edgar_client.ticker_to_cik(ticker)
        if not cik:
            return {'error': f'Could not find CIK for ticker: {ticker}'}
        
        # Get company facts for basic info
        company_facts = self.edgar_client.get_company_facts(cik)
        
        return {
            'ticker': ticker,
            'cik': cik,
            'entityName': company_facts.get('entityName', 'Unknown'),
            'sic': company_facts.get('sic', 'Unknown'),
            'sicDescription': company_facts.get('sicDescription', 'Unknown'),
            'stateOfIncorporation': company_facts.get('stateOfIncorporation', 'Unknown')
        }
    
    def list_available_filings(self, ticker: str, form_type: str = "10-Q") -> List[Dict]:
        """List available filings for a company.
        
        Args:
            ticker: Stock ticker symbol
            form_type: Type of filing to list
            
        Returns:
            List of filing information dictionaries
        """
        cik = self.edgar_client.ticker_to_cik(ticker)
        if not cik:
            return []
        
        filings = self.edgar_client.get_latest_filings(cik, form_type, limit=10)
        
        return [
            {
                'form': filing['form'],
                'filingDate': filing['filingDate'],
                'reportDate': filing['reportDate'],
                'accessionNumber': filing['accessionNumber'],
                'primaryDocument': filing['primaryDocument']
            }
            for filing in filings
        ]
    
    def clear_cache(self, ticker: str = None):
        """Clear cached data for a specific ticker or all data.
        
        Args:
            ticker: Specific ticker to clear, or None to clear all
        """
        if ticker:
            # Clear specific ticker cache
            keys_to_remove = [key for key in self.processed_cache.keys() if key.startswith(ticker)]
            for key in keys_to_remove:
                del self.processed_cache[key]
            logger.info(f"Cleared cache for {ticker}")
        else:
            # Clear all cache
            self.processed_cache.clear()
            self.rag_indexer.clear_index()
            logger.info("Cleared all cached data")
