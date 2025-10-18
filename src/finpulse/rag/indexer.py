"""RAG indexer for chunking, embedding, and retrieving financial document text using LangChain."""

import logging
import os
import json
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class DocumentIndexer:
    """Indexes documents for retrieval-augmented generation using LangChain."""
    
    def __init__(self, chroma_dir: str = None):
        """Initialize the document indexer.
        
        Args:
            chroma_dir: Directory to store document data
        """
        self.chroma_dir = chroma_dir or os.getenv("CHROMA_DIR", "data/cache/chroma")
        self.documents_file = Path(self.chroma_dir) / "documents.json"
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Initialize simple document storage
        Path(self.chroma_dir).mkdir(parents=True, exist_ok=True)
        self.documents = self._load_documents()
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks using LangChain.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        return self.text_splitter.split_text(text)
    
    def _load_documents(self) -> List[dict]:
        """Load documents from storage."""
        if self.documents_file.exists():
            try:
                with open(self.documents_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load documents: {e}")
        return []
    
    def _save_documents(self):
        """Save documents to storage."""
        try:
            with open(self.documents_file, 'w') as f:
                json.dump(self.documents, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save documents: {e}")

    def index_documents(self, documents: List[Tuple[str, str]], metadata: List[dict] = None):
        """Index documents for retrieval.
        
        Args:
            documents: List of (text, url) tuples
            metadata: Optional list of metadata dictionaries
        """
        if not documents:
            logger.warning("No documents to index")
            return
        
        logger.info(f"Indexing {len(documents)} documents")
        
        for i, (text, url) in enumerate(documents):
            chunks = self.chunk_text(text)
            
            for j, chunk in enumerate(chunks):
                document = {
                    "chunk_id": f"{i}_{j}",
                    "text": chunk,
                    "url": url,
                    "document_id": i,
                    "chunk_length": len(chunk)
                }
                
                if metadata and i < len(metadata):
                    document.update(metadata[i])
                
                self.documents.append(document)
        
        self._save_documents()
        logger.info(f"Successfully indexed {len(self.documents)} chunks")
    
    def retrieve(self, query: str, k: int = 5) -> List[Tuple[str, str, float]]:
        """Retrieve relevant document chunks for a query.
        
        Args:
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
        """Clear all indexed documents."""
        logger.info("Clearing document index")
        self.documents = []
        self._save_documents()
    
    def get_collection_stats(self) -> dict:
        """Get statistics about the indexed collection.
        
        Returns:
            Dictionary with collection statistics
        """
        return {
            "total_chunks": len(self.documents),
            "chroma_dir": self.chroma_dir
        }
