"""Gemini LLM integration for financial report generation."""

import logging
import os
from typing import Dict, List, Tuple

import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class GeminiClient:
    """Client for Google Gemini LLM."""
    
    def __init__(self, api_key: str = None):
        """Initialize the Gemini client.
        
        Args:
            api_key: Google AI API key. If None, reads from GEMINI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=self.api_key)
        # Use the correct model name with full path
        self.model = genai.GenerativeModel('models/gemini-2.0-flash')
    
    def summarize(self, kpis: Dict[str, Dict], sources: List[Tuple[str, str, float]], user_query: str = "latest quarterly performance") -> str:
        """Generate a financial summary using KPIs and retrieved sources.
        
        Args:
            kpis: Dictionary of KPI data with values, periods, etc.
            sources: List of (chunk_text, url, similarity) tuples from retrieval
            user_query: The specific question or query from the user
            
        Returns:
            Generated financial summary with inline citations
        """
        logger.info("Generating financial summary with Gemini")
        
        # Prepare KPI summary
        kpi_summary = "Key Financial Metrics:\n"
        for kpi_name, kpi_data in kpis.items():
            value = kpi_data.get('value', 0)
            period = kpi_data.get('period', 'Unknown')
            form = kpi_data.get('form', 'Unknown')
            kpi_summary += f"- {kpi_name}: {value:,.2f} (as of {period}, {form})\n"
        
        # Prepare source context with citations
        source_context = "Relevant Financial Information:\n"
        source_citations = []
        
        # Add retrieved sources if available
        for i, (chunk, url, similarity) in enumerate(sources, 1):
            citation_key = f"[S{i}]"
            source_citations.append((citation_key, url))
            source_context += f"{citation_key} {chunk[:500]}...\n\n"
        
        # Add fallback sources if no documents were retrieved
        if not sources:
            source_context += "[S1] Analysis based on SEC EDGAR company facts and financial metrics.\n"
            source_context += "[S2] Data sourced from official SEC filings and company submissions.\n"
            source_citations.append(("[S1]", "https://www.sec.gov/edgar/sec-api-documentation"))
            source_citations.append(("[S2]", "https://www.sec.gov/edgar"))
        
        # Create the prompt
        prompt = f"""
You are a financial analyst writing a response to a specific investor question. Use the following information to directly address the user's query with inline citations.

USER'S QUESTION: "{user_query}"

{kpi_summary}

{source_context}

Requirements:
1. DIRECTLY ANSWER the user's specific question in 5-7 sentences
2. Include inline citations like [S1], [S2] when referencing specific information
3. Use the exact KPI values provided to support your analysis
4. Be objective and factual, but address the specific concern/query
5. If the question is about investment decisions, provide analysis but include appropriate disclaimers
6. Focus on information relevant to answering the user's specific question

Financial Analysis Response:
"""
        
        try:
            response = self.model.generate_content(prompt)
            summary = response.text.strip()
            logger.info("Successfully generated financial summary with Gemini")
            
            # Add source URLs at the end
            if source_citations:
                summary += "\n\n**Sources:**\n"
                for citation_key, url in source_citations:
                    summary += f"- {citation_key}: {url}\n"
            
            logger.info("Successfully generated financial summary")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate summary with Gemini: {e}")
            
            # Fallback summary
            fallback = f"Analysis for query: '{user_query}'\n\n"
            fallback += f"Based on {len(kpis)} key metrics and {len(sources)} relevant documents. "
            fallback += "Key metrics include revenue, net income, and cash position. "
            fallback += f"\n\n⚠️ **Note**: AI analysis unavailable due to API error: {str(e)[:100]}..."
            fallback += "Please refer to the source documents for detailed analysis."
            return fallback
    
    def generate_kpi_table(self, kpis: Dict[str, Dict]) -> str:
        """Generate a formatted KPI table.
        
        Args:
            kpis: Dictionary of KPI data
            
        Returns:
            Formatted markdown table
        """
        if not kpis:
            return "No KPI data available."
        
        table = "| Metric | Value | Period | Filing |\n"
        table += "|--------|-------|--------|--------|\n"
        
        for kpi_name, kpi_data in kpis.items():
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
            
            table += f"| {kpi_name} | {formatted_value} | {period} | {form} |\n"
        
        return table
