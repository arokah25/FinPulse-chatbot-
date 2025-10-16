"""Tests for SEC EDGAR client functionality."""

import json
import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

# Add src to path for imports
import sys
from pathlib import Path as PathLib
sys.path.insert(0, str(PathLib(__file__).parent.parent / "src"))

from finpulse.ingest.edgar import EdgarClient


class TestEdgarClient:
    """Test cases for EdgarClient."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = EdgarClient(cache_dir="test_cache")
    
    def teardown_method(self):
        """Clean up after tests."""
        # Clean up test cache if it exists
        import shutil
        if Path("test_cache").exists():
            shutil.rmtree("test_cache")
    
    @patch('requests.get')
    def test_ticker_to_cik_success(self, mock_get):
        """Test successful ticker to CIK conversion."""
        # Mock response for ticker mapping
        mock_response = Mock()
        mock_response.json.return_value = {
            "0": {"ticker": "AAPL", "cik_str": "0000320193"},
            "1": {"ticker": "MSFT", "cik_str": "0000789019"}
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        cik = self.client.ticker_to_cik("AAPL")
        assert cik == "0000320193"
        
        cik = self.client.ticker_to_cik("MSFT")
        assert cik == "0000789019"
        
        # Test case insensitive
        cik = self.client.ticker_to_cik("aapl")
        assert cik == "0000320193"
    
    def test_ticker_to_cik_not_found(self):
        """Test ticker not found scenario."""
        # Mock empty ticker mapping
        with patch.object(self.client, '_get_tickers_mapping', return_value={}):
            cik = self.client.ticker_to_cik("INVALID")
            assert cik is None
    
    @patch('requests.get')
    def test_get_company_facts_success(self, mock_get):
        """Test successful company facts retrieval."""
        # Mock response for company facts
        mock_response = Mock()
        mock_response.json.return_value = {
            "entityName": "Apple Inc.",
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [{"val": 89498000000, "end": "2024-09-28", "form": "10-Q"}]
                        }
                    }
                }
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        facts = self.client.get_company_facts("0000320193")
        
        assert facts["entityName"] == "Apple Inc."
        assert "facts" in facts
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_get_company_facts_failure(self, mock_get):
        """Test company facts retrieval failure."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_get.return_value = mock_response
        
        with pytest.raises(Exception, match="API Error"):
            self.client.get_company_facts("0000320193")
    
    def test_extract_kpis_with_data(self):
        """Test KPI extraction with valid data."""
        company_facts = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [{"val": 89498000000, "end": "2024-09-28", "form": "10-Q", "filed": "2024-10-31"}]
                        }
                    },
                    "NetIncomeLoss": {
                        "units": {
                            "USD": [{"val": 22956000000, "end": "2024-09-28", "form": "10-Q", "filed": "2024-10-31"}]
                        }
                    },
                    "EarningsPerShareDiluted": {
                        "units": {
                            "USD/shares": [{"val": 1.53, "end": "2024-09-28", "form": "10-Q", "filed": "2024-10-31"}]
                        }
                    }
                }
            }
        }
        
        kpis = self.client.extract_kpis(company_facts)
        
        assert "Revenues" in kpis
        assert "NetIncomeLoss" in kpis
        assert "EarningsPerShareDiluted" in kpis
        
        assert kpis["Revenues"]["value"] == 89498000000
        assert kpis["NetIncomeLoss"]["value"] == 22956000000
        assert kpis["EarningsPerShareDiluted"]["value"] == 1.53
    
    def test_extract_kpis_no_data(self):
        """Test KPI extraction with no data."""
        company_facts = {"facts": {"us-gaap": {}}}
        
        kpis = self.client.extract_kpis(company_facts)
        
        assert len(kpis) == 0
    
    def test_extract_kpis_missing_facts(self):
        """Test KPI extraction with missing facts structure."""
        company_facts = {}
        
        kpis = self.client.extract_kpis(company_facts)
        
        assert len(kpis) == 0
    
    @patch('requests.get')
    def test_get_latest_filings_success(self, mock_get):
        """Test successful latest filings retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "filings": {
                "recent": {
                    "form": ["10-Q", "10-Q", "8-K"],
                    "filingDate": ["2024-10-31", "2024-07-31", "2024-09-15"],
                    "reportDate": ["2024-09-28", "2024-06-29", "2024-09-15"],
                    "accessionNumber": ["0000320193-24-000123", "0000320193-24-000098", "0000320193-24-000111"],
                    "primaryDocument": ["aapl-20240928.htm", "aapl-20240629.htm", "aapl-20240915.htm"]
                }
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        filings = self.client.get_latest_filings("0000320193", "10-Q", limit=2)
        
        assert len(filings) == 2
        assert all(filing["form"] == "10-Q" for filing in filings)
        assert filings[0]["filingDate"] == "2024-10-31"
        assert filings[0]["accessionNumber"] == "0000320193-24-000123"
    
    @patch('requests.get')
    def test_get_filing_text_success(self, mock_get):
        """Test successful filing text retrieval."""
        mock_response = Mock()
        mock_response.text = "This is a sample filing text content..."
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        text = self.client.get_filing_text("0000320193-24-000123", "aapl-20240928.htm")
        
        assert "sample filing text content" in text
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_get_filing_text_failure(self, mock_get):
        """Test filing text retrieval failure."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("Network Error")
        mock_get.return_value = mock_response
        
        with pytest.raises(Exception, match="Network Error"):
            self.client.get_filing_text("0000320193-24-000123", "aapl-20240928.htm")
    
    def test_cached_ticker_mapping(self):
        """Test that ticker mapping is cached properly."""
        # Create a mock cache file
        cache_data = {
            "0": {"ticker": "AAPL", "cik_str": "0000320193"},
            "1": {"ticker": "MSFT", "cik_str": "0000789019"}
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(cache_data))):
            with patch("pathlib.Path.exists", return_value=True):
                cik = self.client.ticker_to_cik("AAPL")
                assert cik == "0000320193"


class TestEdgarClientIntegration:
    """Integration tests for EdgarClient."""
    
    @pytest.mark.slow
    @patch('requests.get')
    def test_full_pipeline_mock(self, mock_get):
        """Test the full pipeline with mocked API calls."""
        # Mock ticker mapping response
        ticker_response = Mock()
        ticker_response.json.return_value = {
            "0": {"ticker": "AAPL", "cik_str": "0000320193"}
        }
        ticker_response.raise_for_status.return_value = None
        
        # Mock company facts response
        facts_response = Mock()
        facts_response.json.return_value = {
            "entityName": "Apple Inc.",
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [{"val": 89498000000, "end": "2024-09-28", "form": "10-Q", "filed": "2024-10-31"}]
                        }
                    }
                }
            }
        }
        facts_response.raise_for_status.return_value = None
        
        # Mock filings response
        filings_response = Mock()
        filings_response.json.return_value = {
            "filings": {
                "recent": {
                    "form": ["10-Q"],
                    "filingDate": ["2024-10-31"],
                    "reportDate": ["2024-09-28"],
                    "accessionNumber": ["0000320193-24-000123"],
                    "primaryDocument": ["aapl-20240928.htm"]
                }
            }
        }
        filings_response.raise_for_status.return_value = None
        
        # Mock filing text response
        text_response = Mock()
        text_response.text = "Sample filing content for testing"
        text_response.raise_for_status.return_value = None
        
        # Configure mock to return different responses based on URL
        def mock_get_side_effect(url, **kwargs):
            if "company_tickers.json" in url:
                return ticker_response
            elif "companyfacts" in url:
                return facts_response
            elif "submissions" in url:
                return filings_response
            elif "Archives/edgar" in url:
                return text_response
            else:
                raise Exception(f"Unexpected URL: {url}")
        
        mock_get.side_effect = mock_get_side_effect
        
        client = EdgarClient(cache_dir="test_cache")
        
        # Test the full pipeline
        cik = client.ticker_to_cik("AAPL")
        assert cik == "0000320193"
        
        facts = client.get_company_facts(cik)
        assert facts["entityName"] == "Apple Inc."
        
        kpis = client.extract_kpis(facts)
        assert "Revenues" in kpis
        assert kpis["Revenues"]["value"] == 89498000000
        
        filings = client.get_latest_filings(cik, "10-Q")
        assert len(filings) == 1
        assert filings[0]["form"] == "10-Q"
        
        text = client.get_filing_text(filings[0]["accessionNumber"], filings[0]["primaryDocument"])
        assert "Sample filing content" in text
