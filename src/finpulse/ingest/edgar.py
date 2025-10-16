"""SEC EDGAR API client for fetching company filings and financial data."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Constants
USER_AGENT = os.getenv("FINPULSE_USER_AGENT", "FinPulse/1.0 (team@example.com)")
SEC_BASE_URL = "https://data.sec.gov"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Encoding": "gzip"
}

class EdgarClient:
    """Client for interacting with SEC EDGAR API."""
    
    def __init__(self, cache_dir: str = "data/cache"):
        """Initialize the EDGAR client.
        
        Args:
            cache_dir: Directory to cache downloaded data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.tickers_file = self.cache_dir / "company_tickers.json"
        
    def _get_tickers_mapping(self) -> Dict[str, str]:
        """Load ticker to CIK mapping, downloading if not cached.
        
        Returns:
            Dictionary mapping ticker symbols to CIK numbers
        """
        if self.tickers_file.exists():
            logger.info("Loading cached ticker mapping")
            with open(self.tickers_file, 'r') as f:
                data = json.load(f)
                return {item['ticker']: item['cik_str'] for item in data.values()}
        
        logger.info("Downloading company tickers from SEC")
        url = f"{SEC_BASE_URL}/files/company_tickers.json"
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            # Cache the response
            with open(self.tickers_file, 'w') as f:
                json.dump(response.json(), f)
            
            data = response.json()
            return {item['ticker']: item['cik_str'] for item in data.values()}
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch ticker mapping: {e}")
            raise
    
    def ticker_to_cik(self, ticker: str) -> Optional[str]:
        """Convert ticker symbol to CIK number.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            
        Returns:
            CIK number as string, or None if not found
        """
        ticker = ticker.upper()
        tickers_map = self._get_tickers_mapping()
        return tickers_map.get(ticker)
    
    def get_company_facts(self, cik: str) -> Dict:
        """Fetch company facts (financial data) for a given CIK.
        
        Args:
            cik: Company CIK number
            
        Returns:
            Dictionary containing company financial facts
        """
        url = f"{SEC_BASE_URL}/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json"
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch company facts for CIK {cik}: {e}")
            raise
    
    def extract_kpis(self, company_facts: Dict) -> Dict[str, float]:
        """Extract key financial KPIs from company facts.
        
        Args:
            company_facts: Company facts data from SEC API
            
        Returns:
            Dictionary of KPI names to latest values
        """
        kpis = {}
        
        if 'facts' not in company_facts or 'us-gaap' not in company_facts['facts']:
            logger.warning("No US-GAAP facts found in company data")
            return kpis
        
        us_gaap = company_facts['facts']['us-gaap']
        
        # Define KPI mappings
        kpi_mappings = {
            'Revenues': 'Revenues',
            'NetIncomeLoss': 'NetIncomeLoss', 
            'EarningsPerShareDiluted': 'EarningsPerShareDiluted',
            'CashAndCashEquivalentsAtCarryingValue': 'CashAndCashEquivalentsAtCarryingValue',
            'LongTermDebtNoncurrent': 'LongTermDebtNoncurrent'
        }
        
        for kpi_name, sec_name in kpi_mappings.items():
            if sec_name in us_gaap:
                units = us_gaap[sec_name].get('units', {})
                
                # Prefer USD values, fall back to shares for EPS
                preferred_unit = 'USD' if kpi_name != 'EarningsPerShareDiluted' else 'USD/shares'
                if preferred_unit in units:
                    latest_data = units[preferred_unit][-1] if units[preferred_unit] else None
                elif 'USD' in units:
                    latest_data = units['USD'][-1] if units['USD'] else None
                elif 'USD/shares' in units:
                    latest_data = units['USD/shares'][-1] if units['USD/shares'] else None
                else:
                    # Take the first available unit
                    first_unit = list(units.keys())[0] if units else None
                    latest_data = units[first_unit][-1] if first_unit and units[first_unit] else None
                
                if latest_data:
                    kpis[kpi_name] = {
                        'value': latest_data['val'],
                        'period': latest_data.get('end', ''),
                        'form': latest_data.get('form', ''),
                        'filed': latest_data.get('filed', '')
                    }
        
        return kpis
    
    def get_latest_filings(self, cik: str, form_type: str = "10-K", limit: int = 10) -> List[Dict]:
        """Get latest filings for a company.
        
        Args:
            cik: Company CIK number
            form_type: Type of filing (10-K, 10-Q, etc.)
            limit: Maximum number of filings to return
            
        Returns:
            List of filing dictionaries
        """
        url = f"{SEC_BASE_URL}/submissions/CIK{cik.zfill(10)}.json"
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            filings = []
            for filing in data.get('filings', {}).get('recent', {}).get('form', []):
                if form_type in filing:
                    # Find the index of this filing
                    idx = data['filings']['recent']['form'].index(filing)
                    filing_data = {
                        'form': filing,
                        'filingDate': data['filings']['recent']['filingDate'][idx],
                        'reportDate': data['filings']['recent']['reportDate'][idx],
                        'accessionNumber': data['filings']['recent']['accessionNumber'][idx],
                        'primaryDocument': data['filings']['recent']['primaryDocument'][idx]
                    }
                    filings.append(filing_data)
                    
                    if len(filings) >= limit:
                        break
            
            return filings
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch filings for CIK {cik}: {e}")
            raise
    
    def get_filing_text(self, accession_number: str, primary_document: str) -> str:
        """Fetch the text content of a filing.
        
        Args:
            accession_number: SEC accession number
            primary_document: Primary document filename
            
        Returns:
            Filing text content
        """
        # Convert accession number to URL format (remove dashes)
        accession_clean = accession_number.replace('-', '')
        
        url = f"{SEC_BASE_URL}/Archives/edgar/data/{accession_clean[:10]}/{accession_number}/{primary_document}"
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=60)
            response.raise_for_status()
            return response.text
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch filing text: {e}")
            raise
