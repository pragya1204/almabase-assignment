import os
import google.genai as genai
from typing import List, Dict
from dotenv import load_dotenv
from services.auth_service import supabase # Reusing our initialized Supabase client

load_dotenv()

# Initialize Google Gemini API client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY in .env file.")

client=genai.Client(api_key=GEMINI_API_KEY)

class RAGService:
    """Handles document indexing and retrieval using Gemini Embeddings and pgvector."""
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Splits a document into smaller chunks for better retrieval accuracy."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    @staticmethod
    def get_embeddings(text: str, task_type: str = "retrieval_document") -> List[float]:
        """Generates embeddings using Gemini API."""
        response = client.models.embed_content(
            model="gemini-embedding-001", 
            contents=text,
        )
        return response.embeddings[0].values

    @staticmethod
    def store_embedding(doc_id: str, chunk: str, embedding: List[float], chunk_index: int):
        """Saves vectors in pgvector via Supabase client."""
        data = {
            "reference_document_id": doc_id,
            "chunk_text": chunk,
            "embedding": embedding,
            "chunk_index": chunk_index
        }
        supabase.table("document_embeddings").insert(data).execute()

    @staticmethod
    def index_document(doc_id: str, content: str):
        """Chunks reference documents, gets embeddings, and stores them."""
        chunks = RAGService.chunk_text(content)
        for i, chunk in enumerate(chunks):
            # Skip empty chunks
            if not chunk.strip():
                continue
            embedding = RAGService.get_embeddings(chunk)
            RAGService.store_embedding(doc_id, chunk, embedding, i)

    @staticmethod
    def retrieve_relevant_content(question: str, top_k: int = 3, threshold: float = 0.6) -> List[Dict]:
        """
        Retrieves relevant content using pgvector similarity search.
        Threshold determines when to return 'Not found in references.'
        """
        # Generate embedding for the question query
        query_embedding = RAGService.get_embeddings(question)

        # Call our Supabase RPC function (match_documents)
        response = supabase.rpc(
            'match_documents',
            {
                'query_embedding': query_embedding, 
                'match_threshold': threshold, 
                'match_count': top_k
            }
        ).execute()

        # Returns a list of dicts: [{'id': ..., 'reference_document_id': ..., 'chunk_text': ..., 'similarity': ...}]
        return response.data