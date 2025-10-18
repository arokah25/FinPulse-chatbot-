"""Date utility functions for financial data processing."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)

def get_most_recent_period(filing_dates: List[str], max_age_days: int = 365) -> Optional[str]:
    """Get the most recent filing period within the specified age limit.
    
    Args:
        filing_dates: List of filing date strings (YYYY-MM-DD format)
        max_age_days: Maximum age of filing in days
        
    Returns:
        Most recent filing date string, or None if no recent filings
    """
    if not filing_dates:
        return None
    
    # Parse dates and filter by age
    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    valid_dates = []
    
    for date_str in filing_dates:
        try:
            filing_date = datetime.strptime(date_str, "%Y-%m-%d")
            if filing_date >= cutoff_date:
                valid_dates.append(filing_date)
        except ValueError:
            logger.warning(f"Invalid date format: {date_str}")
            continue
    
    if not valid_dates:
        logger.warning(f"No filings found within {max_age_days} days")
        return None
    
    # Return the most recent date
    most_recent = max(valid_dates)
    return most_recent.strftime("%Y-%m-%d")

def is_quarterly_filing(form_type: str) -> bool:
    """Check if a filing type is quarterly.
    
    Args:
        form_type: SEC form type (e.g., '10-Q', '10-K')
        
    Returns:
        True if the form is quarterly, False otherwise
    """
    quarterly_forms = ['10-Q', '10-Q/A', '10-QSB', '10-QSB/A']
    return form_type in quarterly_forms

def is_annual_filing(form_type: str) -> bool:
    """Check if a filing type is annual.
    
    Args:
        form_type: SEC form type (e.g., '10-K', '10-Q')
        
    Returns:
        True if the form is annual, False otherwise
    """
    annual_forms = ['10-K', '10-K/A', '10-KSB', '10-KSB/A', '20-F', '20-F/A']
    return form_type in annual_forms

def get_filing_period_description(form_type: str, report_date: str) -> str:
    """Get a human-readable description of the filing period.
    
    Args:
        form_type: SEC form type
        report_date: Report date string (YYYY-MM-DD)
        
    Returns:
        Human-readable period description
    """
    try:
        report_dt = datetime.strptime(report_date, "%Y-%m-%d")
        year = report_dt.year
        quarter = ((report_dt.month - 1) // 3) + 1
        
        if is_quarterly_filing(form_type):
            return f"Q{quarter} {year}"
        elif is_annual_filing(form_type):
            return f"FY {year}"
        else:
            return f"{year}-{report_dt.strftime('%m-%d')}"
            
    except ValueError:
        return report_date

def get_expected_filing_periods(form_type: str, current_year: int = None) -> List[str]:
    """Get expected filing periods for a given form type.
    
    Args:
        form_type: SEC form type ('10-K' or '10-Q')
        current_year: Year to generate periods for (defaults to current year)
        
    Returns:
        List of expected period descriptions
    """
    if current_year is None:
        current_year = datetime.now().year
    
    if form_type == '10-Q':
        return [f"Q{i} {current_year}" for i in range(1, 5)]
    elif form_type == '10-K':
        return [f"FY {current_year}"]
    else:
        return []

def parse_date_range(date_str: str) -> tuple:
    """Parse a date range string into start and end dates.
    
    Args:
        date_str: Date string in format "YYYY-MM-DD" or "YYYY-MM-DD to YYYY-MM-DD"
        
    Returns:
        Tuple of (start_date, end_date) as datetime objects
    """
    if " to " in date_str:
        start_str, end_str = date_str.split(" to ")
        start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d")
        end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d")
        return start_date, end_date
    else:
        single_date = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return single_date, single_date
