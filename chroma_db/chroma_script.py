# rag_tool.py
import os, json, requests
import chromadb
from chromadb.config import Settings
from typing import List
import google.generativeai as genai
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
load_dotenv()

BASE_URL = "http://localhost:3001"

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_board_items():
    url = BASE_URL + "/api/board-items"
    
    response = requests.get(url)
    data = response.json()
    return data

# ----------------------------
# Common embedding helper
# ----------------------------
def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed texts using Gemini embedding model"""
    model = "models/text-embedding-004"
    try:
        res = genai.embed_content(model=model, content=texts)
        
        
        # Handle the response structure correctly
        if "embedding" in res:
            # Single text input - but we might have multiple chunks
            embedding = res["embedding"]
            # If it's a list of lists (multiple embeddings), return as is
            if isinstance(embedding, list) and len(embedding) > 0 and isinstance(embedding[0], list):
                return embedding
            # If it's a single embedding (list of floats), wrap it
            else:
                return [embedding]
        elif "data" in res:
            # Multiple text inputs
            embeddings = [d["embedding"] for d in res["data"]]
            return embeddings
        else:
            # Fallback - try to extract embeddings from the response
            print(f"Unexpected response structure: {list(res.keys())}")
            return []
    except Exception as e:
        print(f"Error in embed_texts: {e}")
        return []

# ----------------------------
# 1️⃣ Build Chroma from text files
# ----------------------------
def build_chroma_from_texts(dir_path: str, persist_dir: str = "./chroma_store"):
    """Load text files, chunk, and store in Chroma vector DB"""
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(name="local_docs")

    splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)

    for fname in os.listdir(dir_path):
        if not fname.endswith(".txt"):
            continue
        fpath = os.path.join(dir_path, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = splitter.split_text(text)
        embeddings = embed_texts(chunks)
        ids = [f"{fname}_{i}" for i in range(len(chunks))]

        collection.add(documents=chunks, embeddings=embeddings, ids=ids)
        # print(f"Stored {len(chunks)} chunks from {fname}")

    # print("✅ Chroma built successfully.")
    return collection


# ----------------------------
# 1.5️⃣ Query from persistent ChromaDB collection
# ----------------------------
def query_chroma_collection(query: str, persist_dir: str = "./chroma_store", collection_name: str = "local_docs", top_k: int = 3):

    try:
        # Connect to the persistent ChromaDB
        client = chromadb.PersistentClient(path=persist_dir)
        collection = client.get_collection(name=collection_name)
        
        # Create custom embedding function for queries
        class CustomEmbeddingFunction:
            def __call__(self, input):
                return embed_texts(input)
            
            def embed_query(self, input, **kwargs):
                embeddings = embed_texts([input])
                result = embeddings[0] if embeddings else []
                return [result]
        
        # Set the embedding function for the collection
        collection._embedding_function = CustomEmbeddingFunction()
        
        # Perform the query
        results = collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        # Extract and return the documents
        if results["documents"] and results["documents"][0]:
            context = "\n".join(results["documents"][0])
            return context
        else:
            return []
            
    except Exception as e:
        print(f"Error querying ChromaDB collection: {e}")
        return []


# ----------------------------
# 2️⃣ RAG from JSON file (no DB)
# ----------------------------
# ---------- Helper: JSON → Markdown ----------
def json_to_markdown(obj: dict, index: int = 0) -> str:
    """
    Convert one JSON object into flat Markdown text.
    - Only a single '# Record {index}' heading.
    - No nested or secondary headings.
    - Nested dicts/lists flattened into simple key paths.
    """
    lines = [f"# Object Record {index + 1}"]

    def flatten(prefix, value):
        if isinstance(value, dict):
            for k, v in value.items():
                new_key = f"{prefix}_{k}" if prefix else k
                flatten(new_key, v)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                new_key = f"{prefix}_{i}" if prefix else f"{prefix}_{i}"
                flatten(new_key, v)
        else:
            key_clean = prefix.replace("_", " ")
            if key_clean == 'id':
                key_clean = 'objectId'
            lines.append(f"**{key_clean}:** {value}")

    flatten("", obj)
    return "\n".join(lines)


# ---------- Main Function ----------
def rag_from_json(json_path: str="", query: str="", top_k: int = 3):
    """
    Load JSON (list of objects), convert each record to Markdown,
    embed chunks in memory, and perform semantic RAG search.
    """
    import hashlib
    import time
    
    # Create in-memory Chroma collection with custom embedding function
    client = chromadb.Client(Settings(anonymized_telemetry=False))
    
    # Create a unique collection name based on JSON path and timestamp
    json_hash = hashlib.md5(json_path.encode()).hexdigest()[:8]
    timestamp = str(int(time.time() * 1000))[-6:]  # Last 6 digits of timestamp
    collection_name = f"temp_json_rag_{json_hash}_{timestamp}"
    
    try:
        # Create a custom embedding function for queries
        class CustomEmbeddingFunction:
            def __call__(self, input):
                return embed_texts(input)
            
            def embed_query(self, input, **kwargs):
                embeddings = embed_texts([input])
                result = embeddings[0] if embeddings else []
                # ChromaDB expects a list of lists even for single query
                return [result]
        
        # Try to delete existing collection if it exists, then create new one
        try:
            client.delete_collection(name=collection_name)
        except:
            pass  # Collection doesn't exist, which is fine
        
        collection = client.create_collection(
            name=collection_name,
            embedding_function=CustomEmbeddingFunction()
        )

        # Load JSON data
        # with open(json_path, "r", encoding="utf-8") as f:
        #     data = json.load(f)
        data = get_board_items()

        # Normalize: list of dicts
        if isinstance(data, dict):
            data = [data]

        # Convert each object to Markdown string
        md_blocks = [json_to_markdown(obj) for obj in data]

        # Chunk each Markdown block
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = []
        for block in md_blocks:
            chunks.extend(splitter.split_text(block))

        # Embed and store in Chroma
        embeddings = embed_texts(chunks)
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        
        # Suppress any output from ChromaDB by redirecting stdout and stderr
        import sys
        import os
        from contextlib import redirect_stdout, redirect_stderr
        
        # Save original stdout and stderr
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        # Redirect to devnull
        with open(os.devnull, 'w') as devnull:
            sys.stdout = devnull
            sys.stderr = devnull
            try:
                collection.add(documents=chunks, embeddings=embeddings, ids=ids)
            finally:
                # Restore original stdout and stderr
                sys.stdout = original_stdout
                sys.stderr = original_stderr

        # Query
        results = collection.query(query_texts=[query], n_results=top_k)
        context = "\n".join(results["documents"][0])

        return context
        
    finally:
        # Clean up: delete the temporary collection
        try:
            client.delete_collection(name=collection_name)
        except:
            pass  # Collection might already be deleted, which is fine



## RUN THIS FOR FIRST TIME TO CREATE VECTOR STORE
collection = build_chroma_from_texts("patient_data", "./chroma_store")
print("✅ Collection built successfully!")
    