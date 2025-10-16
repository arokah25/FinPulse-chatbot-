"""RAG indexer for chunking, embedding, and retrieving financial document text."""

import logging
import os
from pathlib import Path
from typing import List, Tuple

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class DocumentIndexer:
    """Indexes documents for retrieval-augmented generation."""
    
    def __init__(self, chroma_dir: str = None, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize the document indexer.
        
        Args:
            chroma_dir: Directory to store ChromaDB data
            model_name: Name of the sentence transformer model to use
        """
        self.chroma_dir = chroma_dir or os.getenv("CHROMA_DIR", "data/cache/chroma")
        self.model_name = model_name
        
        # Initialize ChromaDB
        Path(self.chroma_dir).mkdir(parents=True, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_dir)
        self.collection = self.chroma_client.get_or_create_collection(
            name="financial_documents",
            metadata={"description": "Financial filing documents"}
        )
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {model_name}")
        self.embedding_model = SentenceTransformer(model_name)
    
    def chunk_text(self, text: str, chunk_size: int = 1500, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum size of each chunk in characters
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings within the last 200 characters
                search_start = max(start + chunk_size - 200, start)
                for i in range(end - 1, search_start - 1, -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            
        return chunks
    
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
        
        all_chunks = []
        all_metadata = []
        all_urls = []
        
        for i, (text, url) in enumerate(documents):
            chunks = self.chunk_text(text)
            
            for j, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_urls.append(url)
                
                chunk_metadata = {
                    "document_id": i,
                    "chunk_id": j,
                    "url": url,
                    "chunk_length": len(chunk)
                }
                
                if metadata and i < len(metadata):
                    chunk_metadata.update(metadata[i])
                
                all_metadata.append(chunk_metadata)
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = self.embedding_model.encode(all_chunks).tolist()
        
        # Add to ChromaDB
        ids = [f"doc_{i}_chunk_{j}" for i in range(len(documents)) for j in range(len(self.chunk_text(documents[i][0])))]
        
        self.collection.add(
            embeddings=embeddings,
            documents=all_chunks,
            metadatas=all_metadata,
            ids=ids
        )
        
        logger.info(f"Successfully indexed {len(all_chunks)} chunks")
    
    def retrieve(self, query: str, k: int = 5) -> List[Tuple[str, str, float]]:
        """Retrieve relevant document chunks for a query.
        
        Args:
            query: Search query
            k: Number of chunks to retrieve
            
        Returns:
            List of (chunk_text, url, similarity_score) tuples
        """
        logger.info(f"Retrieving top {k} chunks for query: {query[:100]}...")
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).tolist()
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=k
        )
        
        if not results['documents'] or not results['documents'][0]:
            logger.warning("No results found for query")
            return []
        
        # Format results
        chunks = []
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            url = metadata.get('url', '')
            similarity = 1 - distance  # Convert distance to similarity
            chunks.append((doc, url, similarity))
        
        logger.info(f"Retrieved {len(chunks)} chunks")
        return chunks
    
    def clear_index(self):
        """Clear all indexed documents."""
        logger.info("Clearing document index")
        self.chroma_client.delete_collection("financial_documents")
        self.collection = self.chroma_client.create_collection(
            name="financial_documents",
            metadata={"description": "Financial filing documents"}
        )
    
    def get_collection_stats(self) -> dict:
        """Get statistics about the indexed collection.
        
        Returns:
            Dictionary with collection statistics
        """
        count = self.collection.count()
        return {
            "total_chunks": count,
            "model_name": self.model_name,
            "chroma_dir": self.chroma_dir
        }
