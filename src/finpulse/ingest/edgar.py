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
        # if cache file exists -> load it
        if self.tickers_file.exists():
            logger.info("Loading cached ticker mapping")
            try:
                #open file at self.tickers_file for reading
                with open(self.tickers_file, 'r') as f:
                    #read entire file and pare it as JSON into phyton object
                    #if file contains JSON object -> data will be dictionary
                    data = json.load(f)
                    return {item['ticker']: item['cik_str'] for item in data.values()}
            except Exception as e:
                logger.warning(f"Failed to load cached tickers: {e}")
        
        # Fallback to hardcoded common tickers
        logger.info("Using hardcoded ticker mapping for common companies")
        #dictionary: tickers & CIKs
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
        
       # write the fallback mappting to disk for next time
        try:
            with open(self.tickers_file, 'w') as f:
                json.dump(common_tickers, f)
        except Exception as e:
            logger.warning(f"Failed to cache tickers: {e}")
        #return mapping either way
        return common_tickers
    
    def ticker_to_cik(self, ticker: str) -> Optional[str]:
        """Convert ticker symbol to CIK number.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            
        Returns:
            CIK number as string, or None if not found
        """
        #Upper cases ticker -> Mapping keys are upper case
        ticker = ticker.upper()
        #calls helper that returns mapping (i.e. dictionaly of ticker -> CIK)
        tickers_map = self._get_tickers_mapping()
        #look up the ticker in the dictionary & retunr the CIK string if exists
        #if it dfoes not exist -> return None
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
            #HTTP GET request to SEC API -> asking the server for ressources
            #asnwer from server: (OK or error) + content (HTML, JSON; image...)
            #if server doesnt repsond within 30 sec -> raise error
            #headers: key/value metadata: we set 1. user-agent (short string for identifaction)
            #2. Accept-Encoding: gzip (we can handle compressed responses)
            response = requests.get(url, headers=HEADERS, timeout=30)
            #rais error if HTTP status != 2xx (2xx=success)
            response.raise_for_status()
            #parse JSON response into Python dictionary and return it
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch company facts for CIK {cik}: {e}")
            raise
    #extract kpis from company facts and create a dictionary of kpis
    #input company facts: comes from self.edgar_client.get_company_facts(cik)
    def extract_kpis(self, company_facts: Dict) -> Dict[str, float]:
        """Extract key financial KPIs from company facts.
        
        Args:
            company_facts: Company facts data from SEC API
            
        Returns:
            Dictionary of KPI names to latest values
        """
        #initzialize container with APIs
        kpis = {}
        #validates input structure, i.e. check if 'facts' & 'us-gaap' keys exist
        if 'facts' not in company_facts or 'us-gaap' not in company_facts['facts']:
            logger.warning("No US-GAAP facts found in company data")
            return kpis
        
        us_gaap = company_facts['facts']['us-gaap']
        
        # Define KPI mappings (what should be pulled)
        kpi_mappings = {
            'Revenues': 'Revenues',
            'NetIncomeLoss': 'NetIncomeLoss', 
            'EarningsPerShareDiluted': 'EarningsPerShareDiluted',
            'CashAndCashEquivalentsAtCarryingValue': 'CashAndCashEquivalentsAtCarryingValue',
            'LongTermDebtNoncurrent': 'LongTermDebtNoncurrent'
        }
        
        # iterate oeach KPI that should be extracted
        for kpi_name, sec_name in kpi_mappings.items():
            #only contiue if that concept exists for this company
            #sec_name = key used to fetch that concept's data from SEC facts. e.g. us_gaap['Revenues']
            if sec_name in us_gaap:
                units = us_gaap[sec_name].get('units', {})
                
                # unit for KPIs: USD, except for EPS which is USD/shares
                preferred_unit = 'USD' if kpi_name != 'EarningsPerShareDiluted' else 'USD/shares'
                
                # Filter for 10-Q filings only
                #helper function
                def get_latest_10q_data(unit_data):
                    #if unit_data is None or []
                    if not unit_data:
                        return None
                    
                    # Filter for 10-Q filings only
                    #lsit comprehension: builds new list by scanning every item in unit_data
                    #safeöy tries to read "form" key from the dictioanry; empty string if its missing
                    q10_data = [item for item in unit_data if item.get('form', '').startswith('10-Q')] #retursn false for 10-K
                    #last elemeent because "company_facts" lists are chronologically ordered from oldest->newest
                    
                    # Apply date filtering (last 24 months)
                    from datetime import datetime, timedelta
                    cutoff_date = datetime.now() - timedelta(days=730)  # ~24 months ago
                    
                    recent_q10_data = []
                    for item in q10_data:
                        end_date_str = item.get('end', '')
                        if end_date_str:
                            try:
                                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                                if end_date >= cutoff_date:
                                    recent_q10_data.append(item)
                            except ValueError:
                                continue
                    
                    # Return the most recent one
                    return recent_q10_data[-1] if recent_q10_data else None
                
                #if preferred unit exists in units -> grab that facts for revenues (or USD/shares facts for EPS)
                #pass it to helper, keeps only 10-Q facts, returns most recent one
                if preferred_unit in units:
                    latest_data = get_latest_10q_data(units[preferred_unit])
                #fallbakc 1: tries USD series, all the values reported in USD for that concept
                elif 'USD' in units:
                    latest_data = get_latest_10q_data(units['USD'])
                #Fallback 2: if neither preferred nor USD exists, try USD/shares (for EPS)
                elif 'USD/shares' in units:
                    latest_data = get_latest_10q_data(units['USD/shares'])
                else:
                    # Take the first available unit and filter for 10-Q
                    # I.e. if no USD or USD/shares, just take whatever is there
                    first_unit = list(units.keys())[0] if units else None
                    latest_data = get_latest_10q_data(units[first_unit]) if first_unit else None
                

                if latest_data:
                    #store key KPI data into output dictionary
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
                        
                        # Filter for recent quarters (last 24 months to ensure we get 3 quarters)
                        from datetime import datetime, timedelta
                        cutoff_date = datetime.now() - timedelta(days=730)  # ~24 months ago
                        
                        recent_q10_data = []
                        for item in q10_data:
                            end_date_str = item.get('end', '')
                            if end_date_str:
                                try:
                                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                                    if end_date >= cutoff_date:
                                        recent_q10_data.append(item)
                                except ValueError:
                                    continue
                        
                        # Get the most recent quarters
                        recent_q10_data.sort(key=lambda x: x.get('end', ''), reverse=True)
                        
                        for item in recent_q10_data[:limit]:
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
    
    def extract_revenue_from_filing_text(self, filing_text: str, report_date: str) -> float:
        """Extract revenue from filing text using regex patterns.
        
        Args:
            filing_text: The text content of the filing
            report_date: The report date for this filing
            
        Returns:
            Revenue value in dollars, or 0 if not found
        """
        # Filter for recent quarters (last 24 months to ensure we get 3 quarters)
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=730)  # ~24 months ago
        
        try:
            filing_date = datetime.strptime(report_date, '%Y-%m-%d')
            if filing_date < cutoff_date:
                logger.info(f"Filing date {report_date} is too old, skipping text extraction")
                return 0
        except ValueError:
            logger.warning(f"Could not parse filing date: {report_date}")
            # Continue anyway if date parsing fails
        import re
        
        # Look for revenue patterns in the text
        revenue_patterns = [
            # Apple-style: "Total net sales $94,036" (in millions) - more specific
            r'Total net sales[:\s]*\$?\s*([0-9,]+\.?[0-9]*)\s*$',
            # Look for the specific table format Apple uses with better number matching
            r'Total net sales[:\s]*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)',
            # Simple fallback: any large number after "Total net sales"
            r'Total net sales.*?([0-9]{2,3}(?:,[0-9]{3})+)',
            # More general patterns
            r'net sales[:\s]*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*billion',
            r'total revenue[:\s]*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*billion',
            r'revenue[:\s]*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*billion',
            # Also try millions
            r'net sales[:\s]*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*million',
            r'total revenue[:\s]*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*million',
            r'revenue[:\s]*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*million'
        ]
        
        for pattern in revenue_patterns:
            matches = re.findall(pattern, filing_text, re.IGNORECASE | re.MULTILINE)
            if matches:
                logger.info(f"Found revenue match with pattern: {pattern}")
                logger.info(f"Matches: {matches}")
                # Take the first match (usually the most recent quarter)
                revenue_str = matches[0].replace(',', '')
                try:
                    revenue_value = float(revenue_str)
                    if 'million' in pattern or 'Total net sales' in pattern:
                        result = revenue_value * 1e6  # Convert millions to dollars
                        logger.info(f"Extracted revenue: ${revenue_value}M = ${result/1e9:.2f}B")
                        return result
                    else:
                        result = revenue_value * 1e9  # Convert billions to dollars
                        logger.info(f"Extracted revenue: ${revenue_value}B = ${result/1e9:.2f}B")
                        return result
                except ValueError:
                    logger.warning(f"Could not parse revenue value: {revenue_str}")
                    continue
        
        return 0
    
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
