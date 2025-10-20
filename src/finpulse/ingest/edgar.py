"""
SEC API Client & Data Fetcher
Fetches company data from SEC EDGAR API
Converts tickers to CIK numbers
Downloads 10-Q filings and extracts financial metrics (net income, EPS, cash, debt, etc.)
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv

# Load environment variables, needed here: FINPULSE_USER_AGENT
load_dotenv()
logger = logging.getLogger(__name__)

#BUGFIX: make sure env exists for compliance reasons
existence_check = os.getenv("FINPULSE_USER_AGENT", "").strip()
if not existence_check:
    raise RuntimeError("Missing required environmental variable FINPULSE_USER_AGENT. Needed for compliance reasons\n" \
    "Following the structure: FINPULSE_USER_AGENT=\"FinPulse/1.0 (Name; email address)\"")

# Reads .env file -> BUGFIX NECESSARY: abort everything if .env is missing, must comply with SEC.gov's Privacy and Security Policy
USER_AGENT = os.getenv("FINPULSE_USER_AGENT", "FinPulse/1.0 (team@example.com)")


#base domainfor JSON apis
SEC_BASE_URL = "https://data.sec.gov"
#SEC_BASE_URL = "https://www.sec.gov"
#base domain for edgar archives
SEC_ARCHIVES = "https://www.sec.gov"

#default headers sent with every http request
HEADERS = {
    "User-Agent": USER_AGENT, #user agent for compliance
    "Accept-Encoding": "gzip" #accept gzip compression
}

#class defnition for edgar client
#purpose: interact with SEC EDGAR API
class EdgarClient:

#Class methods
    # #helper method for ticker->CIK mapping, returns: dictionary containinger ticker -> CIK number mapping
    # #Note: current implementation is only capable of analyzing companies listed in common_tickers dictionary
    def _get_tickers_mapping(self) -> Dict[str, str]:
        # Use hardcoded common tickers
        logger.info("Using hardcoded ticker mapping for common companies")
        #dictionary: tickers & CIKs
        common_tickers = {
            'AAPL': '0000320193',  # Apple 
            'MSFT': '0000789019',  # Microsoft 
            'GOOGL': '0001652044', # Alphabet 
            'GOOG': '0001652044',  # Alphabet 
            'AMZN': '0001018724',  # Amazon.com 
            'TSLA': '0001318605',  # Tesla 
            'META': '0001326801',  # Meta
            'NVDA': '0001045810',  # NVIDIA 
            'NFLX': '0001065280',  # Netflix I
            'AMD': '0000002488',   # Advanced Micro Devices 
            'INTC': '0000050863',  # Intel 
            'CRM': '0001108524',   # Salesforce 
            'ADBE': '0000796343',  # Adobe 
            'ORCL': '0001341439',  # Oracle 
            'IBM': '0000051143',   # International Business Machines Corp
            'CSCO': '0000858877',  # Cisco Systems 
            'QCOM': '0000804328',  # QUALCOMM Incorporated
            'PYPL': '0001633917',  # PayPal Holdings 
            'UBER': '0001543151',  # Uber Technologies
            'SNAP': '0001564408',  # Snap 
            'TWTR': '0001418091',  # Twitter/X
            'SQ': '0001512673',    # Block 
            'ROKU': '0001428439',  # Roku 
            'ZM': '0001585521',    # Zoom Video Communications 
            'SPOT': '0001639920',  # Spotify Technology
            'SHOP': '0001594805',  # Shopify 
            'DOCU': '0001261333',  # DocuSign 
            'OKTA': '0001660134',  # Okta 
            'CRWD': '0001535527',  # CrowdStrike Holdings
            'PLTR': '0001321655',  # Palantir Technologies
            'ACHR': '0001824502',  # Archer Aviation
        }
        
        return common_tickers
    
    #method that can look up CIK for a given ticker and converts ticker to CIK
    #e.g. input AAPL -> returns CIK number as a string
    def ticker_to_cik(self, ticker: str) -> Optional[str]:
        #Upper cases ticker -> Mapping keys are upper case
        ticker = ticker.upper()
        #calls helper that returns mapping (i.e. dictionaly of ticker -> CIK)
        tickers_map = self._get_tickers_mapping()
        #look up the ticker in the dictionary & retunr the CIK string if exists
        #if it dfoes not exist -> return None
        return tickers_map.get(ticker)
    

    #fetch company facts JOSN for a given CIK
    #input: CIK number as string, output: dictionary containing the company facts
    def get_company_facts(self, cik: str) -> Dict:

        #construct URL
        url = f"{SEC_BASE_URL}/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json"
        
        try:
            #HTTP GET request to SEC API -> asking the server for ressources
            #asnwer from server: (OK or error) + content (HTML, JSON; image...)
            #if server doesnt repsond within 30 sec -> raise error
            #headers: key/value metadata: we set 1. user-agent (short string for identifaction)
            #2. Accept-Encoding: gzip (we can handle compressed responses)
            response = requests.get(url, headers=HEADERS, timeout=30)
            #rais error if HTTP status != 2xx (2xx=success)
            response.raise_for_status() #LEAVE AWAY?
            #parse JSON response into Python dictionary and return it
            company_facts_dict = response.json()
            #return response.json()
            return company_facts_dict
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch company facts for CIK {cik}: {e}")
            raise


    #extract kpis from company facts and create a dictionary of kpis
    #input company facts: comes from self.edgar_client.get_company_facts(cik)


    #derive a small kpi set (key performance indicator) from company facts, input: company facts dicitionary, output: kpi dicitionary
    def extract_kpis(self, company_facts: Dict) -> Dict[str, float]:
        #initzialize container with APIs
        kpis = {}
        #validates input structure, i.e. check if 'facts' & 'us-gaap' keys exist
        if 'facts' not in company_facts or 'us-gaap' not in company_facts['facts']:
            logger.warning("No US-GAAP facts found in company data")
            return kpis
        # US GAAP = U.S. Generally Accepted Accounting Principles
        # contains relevant numbers like net income, EPS, debt, cash,...
        us_gaap = company_facts['facts']['us-gaap']
        
        # Define KPI mappings (what should be pulled)
        kpi_mappings = { #it maps the desired KPI names to SEC concept names
            'NetIncomeLoss': 'NetIncomeLoss', 
            'EarningsPerShareDiluted': 'EarningsPerShareDiluted',
            'CashAndCashEquivalentsAtCarryingValue': 'CashAndCashEquivalentsAtCarryingValue',
            'LongTermDebtNoncurrent': 'LongTermDebtNoncurrent'
        }
        
        # iterate oeach KPI that should be extracted -> unpacks each pair of kpi_mappings into variables kpi_name and sec_name
        for kpi_name, sec_name in kpi_mappings.items():
            #only contiue if that concept (e.g. NetIncomeLoss) exists for this company
            if sec_name in us_gaap:
                units = us_gaap[sec_name].get('units', {})
                
                # unit for KPIs: USD, except for EPS which is USD/shares
                preferred_unit = 'USD' if kpi_name != 'EarningsPerShareDiluted' else 'USD/shares'
                
               
                #helper function within method extract_kpis
                # choose most recent 10-Q datum within last 24 months
                def get_latest_10q_data(unit_data):
                    #if unit_data is None or []
                    if not unit_data:
                        return None
               
                    #keep only 10-Q data
                    q10_data = []
                    for item in unit_data:
                        form = item.get('form', '')
                        if form.startswith('10-Q'):
                            q10_data.append(item)
                    
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
                

                #if preferred unit exists in units -> grab that facts for KPIs (or USD/shares facts for EPS)
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
                
                #if recent 10-Q date found -> store it output directory
                if latest_data:
                    #store key KPI data into output dictionary
                    kpis[kpi_name] = {
                        'value': latest_data['val'],
                        'period': latest_data.get('end', ''),
                        'form': latest_data.get('form', ''),
                        'filed': latest_data.get('filed', '')
                    }
        
        return kpis #return KPI directory -> could be empty due to missing data
    


    
    #method get recents 10-Q filings; input: cik, output list of filing dictionaries
    def get_latest_filings(self, cik: str, form_type: str = "10-Q", limit: int = 10) -> List[Dict]:
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
            #pulls the lsit availabe (10-Q) in forms from JSON
            forms = data.get('filings', {}).get('recent', {}).get('form', []) #returns parallel arrays: i.e. filling_data for 8-K, 10-K, 10-Q,...
            for i, filing in enumerate(forms):
                if filing == form_type: #form_type = 10-Q => anything else (8-K, 10-K,...) is filtered out
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
            

            return filings
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch filings for CIK {cik}: {e}")
            raise


    #method to fetch the text contents of a filing, inputs: accesion_number, primary_document, optional cik; output: filing text content as string
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
        # Use SEC_ARCHIVES for filing text URLs (not SEC_BASE_URL)
        url = f"{SEC_ARCHIVES}/Archives/edgar/data/{cik}/{accession_clean}/{primary_document}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=60)
            response.raise_for_status()
            return response.text
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch filing text: {e}")
            raise




