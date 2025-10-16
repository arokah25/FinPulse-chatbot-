"""RAG indexer for chunking, embedding, and retrieving financial document text using LangChain."""

import logging
import os
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class DocumentIndexer:
    """Indexes documents for retrieval-augmented generation using LangChain."""
    
    def __init__(self, chroma_dir: str = None, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize the document indexer.
        
        Args:
            chroma_dir: Directory to store ChromaDB data
            model_name: Name of the sentence transformer model to use
        """
        self.chroma_dir = chroma_dir or os.getenv("CHROMA_DIR", "data/cache/chroma")
        self.model_name = model_name
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {model_name}")
        self.embeddings = SentenceTransformerEmbeddings(model_name=model_name)
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Initialize ChromaDB vector store
        Path(self.chroma_dir).mkdir(parents=True, exist_ok=True)
        self.vectorstore = Chroma(
            collection_name="financial_documents",
            embedding_function=self.embeddings,
            persist_directory=self.chroma_dir
        )
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks using LangChain.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        return self.text_splitter.split_text(text)
    
    def index_documents(self, documents: List[Tuple[str, str]], metadata: List[dict] = None):
        """Index documents for retrieval using LangChain.
        
        Args:
            documents: List of (text, url) tuples
            metadata: Optional list of metadata dictionaries
        """
        if not documents:
            logger.warning("No documents to index")
            return
        
        logger.info(f"Indexing {len(documents)} documents")
        
        all_texts = []
        all_metadatas = []
        
        for i, (text, url) in enumerate(documents):
            chunks = self.chunk_text(text)
            
            for j, chunk in enumerate(chunks):
                all_texts.append(chunk)
                
                chunk_metadata = {
                    "document_id": i,
                    "chunk_id": j,
                    "url": url,
                    "chunk_length": len(chunk)
                }
                
                if metadata and i < len(metadata):
                    chunk_metadata.update(metadata[i])
                
                all_metadatas.append(chunk_metadata)
        
        # Add documents to vectorstore
        logger.info(f"Adding {len(all_texts)} chunks to vectorstore...")
        self.vectorstore.add_texts(
            texts=all_texts,
            metadatas=all_metadatas
        )
        
        logger.info(f"Successfully indexed {len(all_texts)} chunks")
    
    def retrieve(self, query: str, k: int = 5) -> List[Tuple[str, str, float]]:
        """Retrieve relevant document chunks for a query using LangChain.
        
        Args:
            query: Search query
            k: Number of chunks to retrieve
            
        Returns:
            List of (chunk_text, url, similarity_score) tuples
        """
        logger.info(f"Retrieving top {k} chunks for query: {query[:100]}...")
        
        # Search vectorstore
        docs = self.vectorstore.similarity_search_with_score(query, k=k)
        
        if not docs:
            logger.warning("No results found for query")
            return []
        
        # Format results
        chunks = []
        for doc, score in docs:
            url = doc.metadata.get('url', '')
            similarity = 1 - score  # Convert distance to similarity
            chunks.append((doc.page_content, url, similarity))
        
        logger.info(f"Retrieved {len(chunks)} chunks")
        return chunks
    
    def clear_index(self):
        """Clear all indexed documents."""
        logger.info("Clearing document index")
        # Recreate vectorstore to clear all data
        self.vectorstore = Chroma(
            collection_name="financial_documents",
            embedding_function=self.embeddings,
            persist_directory=self.chroma_dir
        )
    
    def get_collection_stats(self) -> dict:
        """Get statistics about the indexed collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            # Get collection info
            collection_info = self.vectorstore._collection.count()
            return {
                "total_chunks": collection_info,
                "model_name": self.model_name,
                "chroma_dir": self.chroma_dir
            }
        except Exception:
            return {
                "total_chunks": 0,
                "model_name": self.model_name,
                "chroma_dir": self.chroma_dir
            }
