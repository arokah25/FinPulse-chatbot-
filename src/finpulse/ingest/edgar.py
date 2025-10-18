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
#SEC_BASE_URL = "https://www.sec.gov"
SEC_ARCHIVES = "https://www.sec.gov"
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
        # Try to load cached mapping first
        if self.tickers_file.exists():
            logger.info("Loading cached ticker mapping")
            try:
                with open(self.tickers_file, 'r') as f:
                    data = json.load(f)
                    return {item['ticker']: item['cik_str'] for item in data.values()}
            except Exception as e:
                logger.warning(f"Failed to load cached tickers: {e}")
        
        # Fallback to hardcoded common tickers
        logger.info("Using hardcoded ticker mapping for common companies")
        common_tickers = {
            'AAPL': '0000320193',  # Apple Inc.
            'MSFT': '0000789019',  # Microsoft Corporation
            'GOOGL': '0001652044', # Alphabet Inc.
            'GOOG': '0001652044',  # Alphabet Inc.
            'AMZN': '0001018724',  # Amazon.com Inc.
            'TSLA': '0001318605',  # Tesla Inc.
            'META': '0001326801',  # Meta Platforms Inc.
            'NVDA': '0001045810',  # NVIDIA Corporation
            'NFLX': '0001065280',  # Netflix Inc.
            'AMD': '0000002488',   # Advanced Micro Devices Inc.
            'INTC': '0000050863',  # Intel Corporation
            'CRM': '0001108524',   # Salesforce Inc.
            'ADBE': '0000796343',  # Adobe Inc.
            'ORCL': '0001341439',  # Oracle Corporation
            'IBM': '0000051143',   # International Business Machines Corp
            'CSCO': '0000858877',  # Cisco Systems Inc.
            'QCOM': '0000804328',  # QUALCOMM Incorporated
            'PYPL': '0001633917',  # PayPal Holdings Inc.
            'UBER': '0001543151',  # Uber Technologies Inc.
            'SNAP': '0001564408',  # Snap Inc.
            'TWTR': '0001418091',  # Twitter Inc. (now X)
            'SQ': '0001512673',    # Block Inc.
            'ROKU': '0001428439',  # Roku Inc.
            'ZM': '0001585521',    # Zoom Video Communications Inc.
            'SPOT': '0001639920',  # Spotify Technology S.A.
            'SHOP': '0001594805',  # Shopify Inc.
            'DOCU': '0001261333',  # DocuSign Inc.
            'OKTA': '0001660134',  # Okta Inc.
            'CRWD': '0001535527',  # CrowdStrike Holdings Inc.
            'PLTR': '0001321655',  # Palantir Technologies Inc.
        }
        
        # Cache the common tickers
        try:
            with open(self.tickers_file, 'w') as f:
                json.dump(common_tickers, f)
        except Exception as e:
            logger.warning(f"Failed to cache tickers: {e}")
        
        return common_tickers
    
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
                
                # Filter for 10-Q filings only
                def get_latest_10q_data(unit_data):
                    if not unit_data:
                        return None
                    # Filter for 10-Q filings and get the most recent one
                    q10_data = [item for item in unit_data if item.get('form', '').startswith('10-Q')]
                    return q10_data[-1] if q10_data else None
                
                if preferred_unit in units:
                    latest_data = get_latest_10q_data(units[preferred_unit])
                elif 'USD' in units:
                    latest_data = get_latest_10q_data(units['USD'])
                elif 'USD/shares' in units:
                    latest_data = get_latest_10q_data(units['USD/shares'])
                else:
                    # Take the first available unit and filter for 10-Q
                    first_unit = list(units.keys())[0] if units else None
                    latest_data = get_latest_10q_data(units[first_unit]) if first_unit else None
                
                if latest_data:
                    kpis[kpi_name] = {
                        'value': latest_data['val'],
                        'period': latest_data.get('end', ''),
                        'form': latest_data.get('form', ''),
                        'filed': latest_data.get('filed', '')
                    }
        
        return kpis
    
    def get_quarterly_revenue_from_xbrl(self, cik: str, limit: int = 3) -> Dict[str, float]:
        """Get quarterly revenue data from SEC XBRL API.
        
        Args:
            cik: Company CIK number
            limit: Number of quarters to get
            
        Returns:
            Dictionary mapping period to revenue values
        """
        quarterly_revenues = {}
        
        try:
            # Get company facts which includes quarterly data
            company_facts = self.get_company_facts(cik)
            
            if 'facts' not in company_facts or 'us-gaap' not in company_facts['facts']:
                logger.warning("No US-GAAP facts found for quarterly revenue")
                return quarterly_revenues
            
            us_gaap = company_facts['facts']['us-gaap']
            
            # Try different revenue field names
            revenue_fields = ['Revenues', 'Revenue', 'SalesRevenueNet', 'NetSales']
            
            for field in revenue_fields:
                if field in us_gaap:
                    units = us_gaap[field].get('units', {})
                    
                    # Look for USD values
                    if 'USD' in units:
                        # Filter for 10-Q filings only
                        q10_data = [item for item in units['USD'] if item.get('form', '').startswith('10-Q')]
                        
                        # Get the most recent quarters
                        q10_data.sort(key=lambda x: x.get('end', ''), reverse=True)
                        
                        for item in q10_data[:limit]:
                            period = item.get('end', 'Unknown')
                            revenue_value = item.get('val', 0)
                            if revenue_value > 0:
                                quarterly_revenues[period] = revenue_value
                        
                        if quarterly_revenues:
                            logger.info(f"Found quarterly revenue data for {len(quarterly_revenues)} quarters")
                            break
            
            return quarterly_revenues
            
        except Exception as e:
            logger.error(f"Failed to get quarterly revenue from XBRL: {e}")
            return quarterly_revenues
    
    #def get_latest_filings(self, cik: str, form_type: str = "10-K", limit: int = 10) -> List[Dict]:
    def get_latest_filings(self, cik: str, form_type: str = "10-Q", limit: int = 10) -> List[Dict]:
        """Get latest filings for a company.
        
        Args:
            cik: Company CIK number
            form_type: Type of filing (10-Q only)
            limit: Maximum number of filings to return
            
        Returns:
            List of filing dictionaries
        """
        #builds URL, and makes sure CIK is 10 digits long inclduing leading zeros
        url = f"{SEC_BASE_URL}/submissions/CIK{cik.zfill(10)}.json"
        
        try:
            #call SEC API
            response = requests.get(url, headers=HEADERS, timeout=30)
            #raise error if request fails
            response.raise_for_status()
            #parses JSON into data
            data = response.json()
            
            #list for results
            filings = []
            #pulls the lsit availabe (10-Q, 8-K, etc...) in forms from JSON
            forms = data.get('filings', {}).get('recent', {}).get('form', [])
            for i, filing in enumerate(forms):
                if filing == form_type:
                    filing_data = {
                        'form': filing,
                        'filingDate': data['filings']['recent']['filingDate'][i],
                        'reportDate': data['filings']['recent']['reportDate'][i],
                        'accessionNumber': data['filings']['recent']['accessionNumber'][i],
                        'primaryDocument': data['filings']['recent']['primaryDocument'][i]
                    }
                    filings.append(filing_data)
                    
                    if len(filings) >= limit:
                        break
            
           # print(f"DEBUG in edgar.py- check data: {data}")

            # filing_data = {
            #         'form': form_type,
            #         'filingDate': data['filings']['recent']['filingDate'][i],
            #         'reportDate': data['filings']['recent']['reportDate'][i],
            #         'accessionNumber': data['filings']['recent']['accessionNumber'][i],
            #         'primaryDocument': data['filings']['recent']['primaryDocument'][i]
            #     }
            # filings.append(filing_data)
                
    
            

            
            return filings
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch filings for CIK {cik}: {e}")
            raise
    
    def get_filing_text(self, accession_number: str, primary_document: str, cik: str = None) -> str:
        """Fetch the text content of a filing.
        
        Args:
            accession_number: SEC accession number
            primary_document: Primary document filename
            cik: Company CIK number (optional, will extract from accession if not provided)
            
        Returns:
            Filing text content
        """
        # Convert accession number to URL format (remove dashes)
        accession_clean = accession_number.replace('-', '')
        
        # Extract CIK from accession number if not provided
        if cik is None:
            cik = accession_clean[:10]
        #print(f"SEC_BASE_URL = {SEC_BASE_URL}")
        # print(f"cik = {cik}")
        # print(f"accession_clean = {accession_clean}")
        # print(f"primary_document = {primary_document}")
        #url = f"{SEC_BASE_URL}/Archives/edgar/data/{cik}/{accession_number}/{primary_document}"
        #url = f"{SEC_BASE_URL}/Archives/edgar/data/{cik}/{accession_clean}/{primary_document}"

        #BUGFIX: we need to use SEC_ARCHIVES here instead of SEC_BASE_URL
        url = f"{SEC_ARCHIVES}/Archives/edgar/data/{cik}/{accession_clean}/{primary_document}"
        #print(f"url CORRECT = {url}")
        try:
            response = requests.get(url, headers=HEADERS, timeout=60)
            response.raise_for_status()
            return response.text
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch filing text: {e}")
            raise
