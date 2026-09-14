import os
import re
import math
import hashlib
import numpy as np
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5").strip()
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").strip()

_openai_client = None
_fastembed_model = None

def get_fastembed_model():
    """
    Returns a cached instance of the local FastEmbed model.
    Runs locally on CPU with zero external API calls or token limits.
    """
    global _fastembed_model
    if _fastembed_model is None:
        try:
            from fastembed import TextEmbedding
            model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5").strip()
            # If still set to OpenAI model name or empty, use BAAI/bge-small-en-v1.5
            if not model_name or "text-embedding" in model_name:
                model_name = "BAAI/bge-small-en-v1.5"
            _fastembed_model = TextEmbedding(model_name=model_name)
        except Exception as e:
            print(f"[Embeddings] Failed to initialize FastEmbed model: {e}")
            _fastembed_model = None
    return _fastembed_model

def get_openai_client():
    global _openai_client
    api_key = os.getenv("AI_API_KEY", "").strip()
    if not api_key or api_key in ("your_api_key", "your_api_key_here"):
        return None
    
    base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").strip()
    # Groq does not have embedding endpoints; use local FastEmbed model
    if "groq.com" in base_url.lower():
        return None

    if _openai_client is None:
        try:
            import httpx
            from openai import OpenAI
            http_client = httpx.Client(headers={"Accept-Encoding": "gzip, deflate"}, timeout=15.0)
            _openai_client = OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
        except Exception as e:
            print(f"[Embeddings] Failed to initialize OpenAI client: {e}")
            return None
    return _openai_client

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", 
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", 
    "by", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from", 
    "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him", 
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "me", "more", 
    "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", 
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so", 
    "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then", 
    "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up", 
    "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", 
    "why", "with", "would", "you", "your", "yours", "yourself", "yourselves"
}

def _fallback_embedding(text: str, dim: int = 384) -> np.ndarray:
    """
    Deterministic normalized stopword-filtered token and subword hash vector.
    Ensures safe retrieval fallback if ML models cannot be loaded.
    """
    vec = np.zeros(dim, dtype=np.float32)
    raw_tokens = re.findall(r"[a-z0-9]+", text.lower())
    tokens = [t for t in raw_tokens if t not in STOP_WORDS and len(t) > 1]
    if not tokens:
        tokens = raw_tokens
    if not tokens:
        return vec
    
    for token in tokens:
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16)
        vec[h % dim] += 2.0
        if len(token) >= 3:
            for i in range(len(token) - 2):
                sub = token[i:i+3]
                sub_h = int(hashlib.sha256(sub.encode("utf-8")).hexdigest()[:8], 16)
                vec[sub_h % dim] += 0.8
                
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec

def get_embedding(text: str) -> np.ndarray:
    """
    Returns a 1D float32 numpy array normalized embedding for text.
    Prioritizes local FastEmbed (BAAI/bge-small-en-v1.5), then OpenAI API if available, then fallback hash.
    """
    cleaned = text.replace("\n", " ").strip()
    if not cleaned:
        cleaned = "empty"
        
    # 1. Try local FastEmbed model
    model = get_fastembed_model()
    if model is not None:
        try:
            vec = list(model.embed([cleaned]))[0]
            vec = np.array(vec, dtype=np.float32)
            norm = np.linalg.norm(vec)
            return vec / norm if norm > 0 else vec
        except Exception as e:
            print(f"[Embeddings] FastEmbed error ({e}), trying fallback")

    # 2. Try OpenAI API if configured with a compatible endpoint
    client = get_openai_client()
    if client:
        try:
            emb_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small").strip()
            response = client.embeddings.create(input=[cleaned], model=emb_model)
            vec = np.array(response.data[0].embedding, dtype=np.float32)
            norm = np.linalg.norm(vec)
            return vec / norm if norm > 0 else vec
        except Exception as e:
            print(f"[Embeddings] OpenAI API failed ({e}), using fallback vectorizer.")
            
    return _fallback_embedding(cleaned)

def get_embeddings_batch(texts: List[str]) -> List[np.ndarray]:
    """
    Generates normalized embeddings for a batch of strings.
    """
    if not texts:
        return []
        
    cleaned_texts = [t.replace("\n", " ").strip() or "empty" for t in texts]

    # 1. Try local FastEmbed model
    model = get_fastembed_model()
    if model is not None:
        try:
            raw_vecs = list(model.embed(cleaned_texts))
            vectors = []
            for v in raw_vecs:
                vec = np.array(v, dtype=np.float32)
                norm = np.linalg.norm(vec)
                vectors.append(vec / norm if norm > 0 else vec)
            return vectors
        except Exception as e:
            print(f"[Embeddings] FastEmbed batch error ({e}), trying fallback")

    # 2. Try OpenAI API if configured with a compatible endpoint
    client = get_openai_client()
    if client:
        try:
            emb_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small").strip()
            response = client.embeddings.create(input=cleaned_texts, model=emb_model)
            vectors = []
            for item in response.data:
                vec = np.array(item.embedding, dtype=np.float32)
                norm = np.linalg.norm(vec)
                vectors.append(vec / norm if norm > 0 else vec)
            return vectors
        except Exception as e:
            print(f"[Embeddings] Batch API call failed ({e}), using fallback vectorizer.")
            
    return [_fallback_embedding(t) for t in cleaned_texts]

def vector_to_bytes(vec: np.ndarray) -> bytes:
    return vec.astype(np.float32).tobytes()

def bytes_to_vector(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)
