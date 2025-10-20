"""
Document Processing & Search:
chunking of SEC filings text --> searchable pieces
indexing of searchable pieces
retrieval of relevant document chunks based on user queries
keyword matching with investment-focused synonyms
"""
#Edgar: Downloads SEC filing text (just a string)
#ReportGenerator.build_document_index(): Creates documents list with (text, url) tuples
#DocumentIndexer.index_documents(): Converts those tuples to dictionaries during chunking

import logging
import os
import json
from pathlib import Path #to handle file paths
from typing import List, Tuple

from dotenv import load_dotenv #load environment variables
from langchain.text_splitter import RecursiveCharacterTextSplitter #text splitter to chunk text into smaller pieces

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class DocumentIndexer:
    """Indexes documents for retrieval-augmented generation using LangChain."""
    
    def __init__(self, documents_dir: str = None):
        """Initialize the document indexer.
        
        Args:
            documents_dir: Directory to store document data
        """
        self.documents_dir = documents_dir or os.getenv("DOCUMENTS_DIR", "data/cache/documents") #directory to store documents
        self.documents_file = Path(self.documents_dir) / "documents.json" #file to store documents
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500, #1500 characters per chunk
            chunk_overlap=200, #200 characters overlap between chunks
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""] #separators for chunking (heirarchical chunking ie tried in order paragraphs --> sentences --> words --> characters if individual words > chunk size)
        )
        
        # Initialize document storage
        Path(self.documents_dir).mkdir(parents=True, exist_ok=True) #create directory at data/cache/documents
        self.documents = self._load_documents() #load documents from storage
    
    #CHUNKING flow: SEC filing downloaded as HTML/text (via requests.get() in edgar.py)
    #HTTP response becomes string when you call .text on the response object
    #String passed to chunk_text()
    #String gets chunked using the text splitter
    def chunk_text(self, text: str) -> List[str]:
        """
        Converts long filings into manageable, retrievable units.
        Split text into overlapping chunks using LangChain.
        input: text to chunk
        output: result of langchain splitter = list of text chunks 
        """
        return self.text_splitter.split_text(text)
    
    def _save_documents(self):
        """Documents stored as a list of dictionaries in memory -->
        This helper function saves these documents to storage (documents_dir) in json format
        """
        try:
            with open(self.documents_file, 'w') as f:
                json.dump(self.documents, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save documents: {e}")

    def _load_documents(self) -> List[dict]:
        """Load documents from storage."""
        if self.documents_file.exists(): #
            try:
                with open(self.documents_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load documents: {e}")
        return []

    def index_documents(self, documents: List[Tuple[str, str]], metadata: List[dict] = None):
        """Index documents for retrieval.
        Core “indexing” step—turns raw filings into retrievable chunk records with metadata
        
        Inputs:
            documents: List of (text, url) tuples
            metadata: Optional list of metadata dictionaries

        Output: Documents = chunks stored as a list of dictionaries in memory
        Each dictionary contains:
        - chunk_id: unique identifier for the chunk (includes document index and chunk index)
        - text: text of the chunk
        - url: url of the document
        - document_id: index of the document
        - chunk_length: length of the chunk
        - any metadata such as ticker, cik, filing date, form ("10-Q"), etc.

        EXAMPLE:
        {
        "chunk_id": "0_12",
        "text": "…chunk text…",
        "url": "https://www.sec.gov/Archives/edgar/data/…/…/10q.htm",
        "document_id": 0,
        "chunk_length": 1493,
        "ticker": "AAPL",
        "cik": "0000320193",
        "filing_date": "2025-07-26",
        "report_date": "2025-06-29",
        "form": "10-Q",
        "accession_number": "0000320193-25-000012"
        }
        """
        if not documents:
            logger.warning("No documents to index")
            return
        
        logger.info(f"Indexing {len(documents)} documents")
        
        for i, (text, url) in enumerate(documents):
            chunks = self.chunk_text(text)
            #(j) build a document dict per chunk (i.e. each chunk gets its own dictionary)
            for j, chunk in enumerate(chunks):
                document = {
                    "chunk_id": f"{i}_{j}", #i is document index, j is chunk index
                    "text": chunk, #text of the chunk
                    "url": url, #url of the document
                    "document_id": i, #index of the document
                    "chunk_length": len(chunk) #length of the chunk
                }
                
                if metadata and i < len(metadata):
                    document.update(metadata[i])
                
                self.documents.append(document)
        
        self._save_documents() #saves documents to storage (documents_dir) in json format
        logger.info(f"Successfully indexed {len(self.documents)} chunks")
    
    def retrieve(self, query: str, k: int = 5) -> List[Tuple[str, str, float]]:
        """Retrieve relevant document chunks for a query.
        
        Input:
            query: Search query
            k: Number of chunks to retrieve
            
        Returns:
            List of (chunk_text, url, similarity_score) tuples
        """
        logger.info(f"Retrieving top {k} chunks for query: {query[:100]}...")
        
        if not self.documents:
            logger.warning("No documents indexed")
            return []
        
        # Enhanced keyword-based retrieval with investment focus
        query_lower = query.lower()
        query_words = query_lower.split()
        
        # Add investment-related synonyms and concepts
        investment_keywords = {
            'sell': ['sell', 'divest', 'exit', 'liquidate', 'dispose'],
            'buy': ['buy', 'purchase', 'invest', 'acquire', 'add'],
            'hold': ['hold', 'maintain', 'keep', 'retain'],
            'performance': ['performance', 'results', 'earnings', 'revenue', 'profit'],
            'growth': ['growth', 'increase', 'expansion', 'rise'],
            'decline': ['decline', 'decrease', 'drop', 'fall', 'reduction'],
            'debt': ['debt', 'liabilities', 'borrowing', 'leverage'],
            'cash': ['cash', 'liquidity', 'funds', 'reserves'],
            'risk': ['risk', 'uncertainty', 'volatility', 'exposure'],
            'opportunity': ['opportunity', 'potential', 'upside', 'prospect']
        }
        
        # Expand query with related terms
        expanded_query_words = set(query_words)
        for word in query_words:
            for category, synonyms in investment_keywords.items():
                if word in synonyms:
                    expanded_query_words.update(synonyms)
        
        scored_docs = []
        
        #note self.documents is a list of dictionaries, each representing a chunk
        #stored in documents_dir/documents.json
        #each dictionary contains: chunk_id, text, url, document_id, chunk_length, plus any metadata such as ticker, cik, filing date, form ("10-Q"), etc.
        for doc in self.documents:
            text = doc['text'].lower()
            
            # Calculate score based on expanded query words
            score = 0
            for word in expanded_query_words:
                if word in text:
                    # Give higher weight to exact query words
                    if word in query_words:
                        score += 2
                    else:
                        score += 1
            
            # Boost score for financial sections
            financial_sections = ['financial', 'revenue', 'income', 'cash', 'debt', 'balance', 'statement']
            if any(section in text for section in financial_sections):
                score += 1
            
            if score > 0:
                scored_docs.append((doc, score))
        
        # Sort by score and take top k
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        top_docs = scored_docs[:k]
        
        # Format results
        chunks = []
        for doc, score in top_docs:
            # Normalize score to 0-1 range based on max possible score
            max_possible_score = len(expanded_query_words) * 2 + 1  # +1 for financial section bonus
            similarity = min(score / max_possible_score, 1.0)
            chunks.append((doc['text'], doc['url'], similarity))
        
        logger.info(f"Retrieved {len(chunks)} chunks")
        return chunks
    
    def clear_index(self):
        """
        Clear all indexed documents. 
        (Useful for re-indexing when source data changes or for testing.)
        """
        logger.info("Clearing document index")
        self.documents = []
        self._save_documents()
    
    def get_collection_stats(self) -> dict:
        """Get statistics about the indexed collection of chunks. 
        Helpful for monitoring and sanity checks (e.g., Gradio UI display).
        
        Returns:
            Dictionary with collection statistics
        """
        return {
            "total_chunks": len(self.documents),
            "documents_dir": self.documents_dir
        }

"""
STEPS:
SEC HTML/Text → String (via HTTP download)
String → Chunks (via text splitting)
Chunks → Python Dictionaries (with metadata)
Python Dictionaries → JSON File (via json.dump)
JSON File → Python Dictionaries (via json.load)
Python Dictionaries → Search Results (via keyword matching)
"""