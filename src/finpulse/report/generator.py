"""
Main Orchestrator - The Brain
Coordinates all other components
Runs the complete pipeline: fetch data → process documents → generate AI analysis
Manages caching and error handling
Returns final report with KPIs and narrative
"""

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
    
    def __init__(self, cache_dir: str = "data/cache", documents_dir: str = None):
        
        """Initialize the report generator.
        
        Args:
            cache_dir: Directory for caching data
            documents_dir: Directory for document storage
        """
        self.cache_dir = cache_dir #DELETE
        self.documents_dir = documents_dir or os.getenv("DOCUMENTS_DIR", f"{cache_dir}/documents")
        
        # Initialize components
        #edgar client
        #self.edgar_client = EdgarClient(cache_dir)
        #REDUCED: deactivated caching function
        self.edgar_client = EdgarClient()

        #rag
        self.rag_indexer = DocumentIndexer(self.documents_dir)
        
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
            #get latest 3 quarterly filings
            filings = self.edgar_client.get_latest_filings(cik, form_type, limit=3)
            
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
            

    #----------------------------------------Adam-----------------------------------------------------------
            # Step 5: Check if we need to rebuild the index
            #The index is the searchable collection of document chunks stored in self.documents (a list of dicts)
            #purpose: avoid re-downloading and re-chunking the same company's filings every time the report is generated
            cache_key = f"{ticker}_{form_type}_{cik}"
            if cache_key not in self.processed_cache:
                logger.info("Building document index...")
                self._build_document_index(ticker, cik, filings)
                self.processed_cache[cache_key] = True
            
            # Step 6: Retrieve relevant document chunks
            logger.info(f"Retrieving documents for query: {query}")
            #here we retrieve the relevant document chunks from the index based on the user's query
            retrieved_docs = self.rag_indexer.retrieve(query, k=5)
            
            # Fallback sources: We provide raw SEC API URLs as "sources" so the LLM still has something to reference, even if it can't cite specific chunks
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
            

            # Final output of the entire RAG pipeline
            # everything the user needs in one structured response 
            return {
                'ticker': ticker,
                'cik': cik,
                'form_type': form_type,
                'kpis': kpis,
                'kpi_table': kpi_table,
                'narrative': narrative, #gemeni's response
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
            filings: List of filing data, format is a list of dicts with keys: accessionNumber, primaryDocument, filingDate, reportDate
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
                #for each file, we create a tuple of the filing text and the filing url
                #documents is thus a list of tuples of (filing text, filing url)
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
            #this is where we chunk the filings and index them
            #output is a list of dictionaries, each representing a chunk
            self.rag_indexer.index_documents(documents, metadata)
        else:
            logger.warning("No documents to index")
    

 #----------------------------------------Adam-----------------------------------------------------------
