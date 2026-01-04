# Part 9: AI Analyst Service - LangChain & RAG

AI can transform raw market data into actionable insights. This chapter covers building an AI analyst using LangChain for market summaries, sentiment analysis, and a RAG-powered chatbot.

---

## 9.1 Understanding AI for Finance

### The Problem with Base LLMs

**Scenario:**
```
User: "What is Max Pain in DeltaStream?"
GPT-4: "I don't have information about DeltaStream specifically. 
        Max Pain generally refers to the strike price where..."
```

**Why LLMs fail:**
- ❌ Knowledge cutoff dates (trained on data until X date)
- ❌ Don't know your specific application
- ❌ Can't access real-time data
- ❌ Hallucinate when uncertain

### The RAG Solution

**RAG = Retrieval-Augmented Generation**

```
┌──────────┐      ┌─────────────┐      ┌─────────┐      ┌──────┐
│  Query   │─────▶│ Vector      │─────▶│ Top-K   │─────▶│ LLM  │
│          │      │ Search      │      │ Docs    │      │  +   │
└──────────┘      └─────────────┘      └─────────┘      │Context│
                         │                    │         └──────┘
                         │                    │             │
                  ┌──────────────┐     ┌──────────────┐   ▼
                  │ Vector Store │     │ Retrieve     │ Answer
                  │ (Your Docs)  │     │ relevant     │ with your
                  └──────────────┘     │ chunks       │ data!
                                       └──────────────┘
```

**How RAG Works:**

1. **Index Phase** (One-time):
   - Convert documentation to embeddings (vectors)
   - Store in vector database (Redis, Pinecone, etc.)

2. **Query Phase** (Every request):
   - User asks question → Convert to embedding
   - Search vector DB for similar documents (k-NN)
   - Inject retrieved docs into LLM prompt
   - LLM generates answer using your data

**Example:**

**Without RAG:**
```python
llm("What is Max Pain in DeltaStream?")
# → "I don't have information about DeltaStream"
```

**With RAG:**
```python
# 1. Retrieve relevant docs
docs = vector_store.similarity_search("Max Pain DeltaStream")
# → "Max Pain in DeltaStream is calculated as the strike where 
#     option writers face maximum loss..."

# 2. Inject into prompt
context = docs[0].page_content
llm(f"Context: {context}\n\nQuestion: What is Max Pain?")
# → "Based on DeltaStream documentation, Max Pain is the strike price
#     where the maximum number of options expire worthless..."
```

---

## 9.2 Project Setup

### Step 9.1: Create Directory Structure

**Action:** Create the AI analyst service:

```bash
mkdir -p services/ai-analyst
cd services/ai-analyst
```

### Step 9.2: Create Requirements File

**Action:** Create `requirements.txt`:

```txt
Flask==3.0.0
flask-cors==4.0.0
structlog==24.1.0
requests==2.31.0
langchain==0.1.0
langchain-community==0.0.10
huggingface_hub==0.20.0
transformers==4.36.0
torch==2.1.2 --index-url https://download.pytorch.org/whl/cpu
sentence-transformers==2.2.2
feedparser==6.0.10
redis==5.0.1
```

**Breaking Down Dependencies:**

**LangChain Ecosystem:**
```txt
langchain==0.1.0           # Core framework
langchain-community==0.0.10 # Community integrations
```
- `langchain`: Main library (chains, prompts, agents)
- `langchain-community`: Integrations (HuggingFace, Redis, etc.)

**HuggingFace Stack:**
```txt
huggingface_hub==0.20.0    # API client
transformers==4.36.0        # Model loading
sentence-transformers==2.2.2 # Embeddings
torch==2.1.2               # ML framework
```
- `huggingface_hub`: Access models via API
- `transformers`: Load and run models locally
- `sentence-transformers`: Specialized for embeddings
- `torch`: Required by transformers (CPU-only version)

**Other:**
```txt
feedparser==6.0.10  # Parse RSS news feeds
redis==5.0.1        # Vector storage
```

---

## 9.3 Building Feature 1: Market Pulse

### Step 9.3: Create Base Application

**Action:** Create `app.py` with imports and setup:

```python
#!/usr/bin/env python3
"""
AI Analyst Service

Provides:
1. Market Pulse - Automated market summaries using LLM
2. Sentiment Analysis - News sentiment with AI
3. Trade Assistant - RAG chatbot for Q&A
"""

import os
import json
import structlog
import feedparser
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

# LangChain imports
from langchain.llms import HuggingFaceHub
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Redis as RedisVectorStore
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, RetrievalQA
from langchain.docstore.document import Document

# Structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# Configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'ai-analyst')
PORT = int(os.getenv('PORT', '8006'))
ANALYTICS_SERVICE_URL = os.getenv('ANALYTICS_SERVICE_URL', 'http://analytics:8004')
HUGGINGFACE_API_TOKEN = os.getenv('HUGGINGFACE_API_TOKEN', '')
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')

# Initialize Flask
app = Flask(__name__)
CORS(app)
```

**Getting HuggingFace Token:**

1. Sign up at https://huggingface.co/
2. Go to https://huggingface.co/settings/tokens
3. Create new token (read access)
4. Add to `.env`:
```bash
HUGGINGFACE_API_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxx
```

---

### Step 9.4: Add Helper to Fetch Analytics Data

**Action:** Add function to get market data:

```python
def fetch_analytics_data(product):
    """Fetch PCR and metrics from Analytics Service."""
    try:
        data = {}
        
        # Get PCR trend
        pcr_resp = requests.get(
            f"{ANALYTICS_SERVICE_URL}/pcr/{product}",
            timeout=5
        )
        
        if pcr_resp.status_code == 200:
            pcr_json = pcr_resp.json()
            latest = pcr_json.get('latest', {})
            data['pcr_oi'] = latest.get('pcr_oi', 'N/A')
            data['pcr_volume'] = latest.get('pcr_volume', 'N/A')
        
        return data
        
    except Exception as e:
        logger.error("fetch_analytics_error", error=str(e))
        return {'pcr_oi': 'N/A', 'pcr_volume': 'N/A'}
```

**Breaking Down HTTP Request:**

**Timeout:**
```python
requests.get(url, timeout=5)
```
- Max 5 seconds to respond
- Without timeout: Hangs indefinitely if Analytics down
- Raises `requests.Timeout` exception on timeout

---

### Step 9.5: Implement Market Pulse Endpoint

**Action:** Add LLM-powered market summary:

```python
@app.route('/api/ai/pulse', methods=['GET'])
def get_market_pulse():
    """Generate market summary using LLM."""
    product = request.args.get('product', 'NIFTY')
    
    # 1. Fetch market data
    analytics = fetch_analytics_data(product)
    
    # 2. Check for API token
    if not HUGGINGFACE_API_TOKEN:
        return jsonify({
            "product": product,
            "analysis": "AI unavailable (Missing HUGGINGFACE_API_TOKEN)",
            "data": analytics
        }), 200
    
    try:
        # 3. Initialize LLM
        llm = HuggingFaceHub(
            repo_id="google/flan-t5-large",
            model_kwargs={"temperature": 0.5, "max_length": 256},
            huggingfacehub_api_token=HUGGINGFACE_API_TOKEN
        )
        
        # 4. Create prompt template
        template = """You are a financial analyst for an options trading platform.

Analyze the following option market data for {product}:
- Put-Call Ratio (Open Interest): {pcr_oi}
- Put-Call Ratio (Volume): {pcr_vol}

Provide a concise market sentiment summary (2-3 sentences):
1. State if sentiment is Bullish, Bearish, or Neutral
2. Explain why based on the PCR values
3. Mention what traders should watch

Analysis:"""
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["product", "pcr_oi", "pcr_vol"]
        )
        
        # 5. Create chain
        chain = LLMChain(prompt=prompt, llm=llm)
        
        # 6. Run chain
        summary = chain.run({
            "product": product,
            "pcr_oi": analytics.get('pcr_oi', 'N/A'),
            "pcr_vol": analytics.get('pcr_volume', 'N/A')
        })
        
        return jsonify({
            "product": product,
            "analysis": summary.strip(),
            "data": analytics
        }), 200
        
    except Exception as e:
        logger.error("market_pulse_error", error=str(e), exc_info=True)
        return jsonify({
            "error": "Failed to generate AI analysis",
            "data": analytics
        }), 500
```

**Breaking Down LangChain Components:**

**1. LLM Initialization:**
```python
llm = HuggingFaceHub(
    repo_id="google/flan-t5-large",
    model_kwargs={"temperature": 0.5, "max_length": 256}
)
```

**repo_id:**
- Model identifier on HuggingFace
- `google/flan-t5-large`: 780M parameter model
- Good balance of speed vs quality
- Alternative: `google/flan-t5-xl` (3B params, slower but better)

**temperature:**
- Controls randomness: `0.0` to `2.0`
- `0.0`: Deterministic (always same output)
- `0.5`: Balanced creativity
- `1.0`: More creative/random
- For market analysis: `0.5` is good (some variability, but grounded)

**max_length:**
- Maximum tokens in response
- 256 tokens ≈ 200 words
- Prevents runaway generation

**2. Prompt Template:**
```python
template = "Analyze {product}: PCR={pcr_oi}"
prompt = PromptTemplate(
    template=template,
    input_variables=["product", "pcr_oi"]
)
```

**Why use templates?**
- Reusable prompts
- Type-safe variable injection
- Easier to version/test

**Variables in {braces}:**
- Must match `input_variables` list
- Runtime replacement:
```python
prompt.format(product="NIFTY", pcr_oi=1.25)
# → "Analyze NIFTY: PCR=1.25"
```

**3. LLM Chain:**
```python
chain = LLMChain(prompt=prompt, llm=llm)
result = chain.run({"product": "NIFTY", "pcr_oi": 1.25})
```

**What is a Chain?**
- Combines prompt + LLM execution
- Sequential processing
- Can chain multiple steps (hence "chain")

**Execution flow:**
1. `chain.run({...})` → Fills template
2. Sends to LLM API
3. Returns generated text

**Request Flow Diagram:**
```
Client              AI Analyst         Analytics          HuggingFace
  │                     │                  │                   │
  ├─GET /pulse?NIFTY───▶│                  │                   │
  │                     ├──GET /pcr/NIFTY─▶│                   │
  │                     │◀──{pcr: 1.25}────┤                   │
  │                     │                  │                   │
  │                     ├──Format prompt───┘                   │
  │                     │  "Analyze NIFTY: PCR=1.25..."        │
  │                     │                                       │
  │                     ├──LLM API call─────────────────────────▶│
  │                     │◀──"Neutral sentiment. PCR of 1.25..."─┤
  │                     │                                       │
  │◀──{analysis:"..."}──┤                                       │
```

---

## 9.4 Building Feature 2: Sentiment Analysis

### Step 9.6: Add Sentiment Analysis Endpoint

**Action:** Add news sentiment analyzer:

```python
@app.route('/api/ai/sentiment', methods=['GET'])
def get_sentiment():
    """Analyze news sentiment using LLM."""
    try:
        # 1. Fetch news headlines
        news_url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^NSEI&region=IN"
        feed = feedparser.parse(
            news_url,
            agent="Mozilla/5.0 (DeltaStreamAI/1.0)"
        )
        
        # Extract headlines (limit to 5)
        headlines = [entry.title for entry in feed.entries[:5]]
        
        # Fallback if RSS fails
        if not headlines:
            headlines = [
                "Market trading in consolidation phase.",
                "Traders await RBI policy decision."
            ]
        
        # 2. Check for token
        if not HUGGINGFACE_API_TOKEN:
            return jsonify({
                "sentiment": "Neutral (API token missing)",
                "headlines": headlines,
                "confidence": "N/A"
            }), 200
        
        # 3. Initialize LLM (low temperature for classification)
        llm = HuggingFaceHub(
            repo_id="google/flan-t5-large",
            model_kwargs={"temperature": 0.1, "max_length": 64},
            huggingfacehub_api_token=HUGGINGFACE_API_TOKEN
        )
        
        # 4. Create classification prompt
        template = """Classify the overall market sentiment of these news headlines as one of: Bullish, Bearish, or Neutral.

Headlines:
{headlines}

Overall Sentiment (one word only):"""
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["headlines"]
        )
        
        chain = LLMChain(prompt=prompt, llm=llm)
        
        # 5. Run classification
        sentiment = chain.run({
            "headlines": "\n".join([f"- {h}" for h in headlines])
        })
        
        return jsonify({
            "sentiment": sentiment.strip(),
            "headlines": headlines,
            "analyzed_at": "realtime"
        }), 200
        
    except Exception as e:
        logger.error("sentiment_error", error=str(e), exc_info=True)
        return jsonify({
            "error": str(e),
            "sentiment": "Error"
        }), 500
```

**Breaking Down RSS Parsing:**

**FeedParser:**
```python
feed = feedparser.parse(news_url, agent="Mozilla/5.0 ...")
```
- `agent`: User-Agent header (some sites block default)
- Returns structured object

**Extracting Headlines:**
```python
headlines = [entry.title for entry in feed.entries[:5]]
```
- `feed.entries`: List of news items
- `[:5]`: First 5 items
- List comprehension extracts titles

**Example output:**
```python
[
  "Nifty hits all-time high on strong FII inflows",
  "Banking stocks surge 3% on rate cut expectations",
  "IT sector faces headwinds from recession fears"
]
```

**Why temperature=0.1 for classification?**

**Sentiment is categorical:**
```
Possible outputs: "Bullish", "Bearish", "Neutral"
```

**High temperature (0.8):**
```
Run 1: "Bullish"
Run 2: "Neutral"  ← Same headlines, different result!
Run 3: "Bullish"
```

**Low temperature (0.1):**
```
Run 1: "Bullish"
Run 2: "Bullish"  ← Consistent
Run 3: "Bullish"
```

**Rule:** Classification tasks need low temperature (0.0-0.2)

---

## 9.5 Building Feature 3: RAG Chatbot

### Understanding Embeddings First

**What are embeddings?**

Text → High-dimensional vector (array of numbers)

**Example:**
```python
"What is Max Pain?" → [0.23, -0.15, 0.67, ..., 0.91]
                      ↑ 384 dimensions
```

**Why?**
- Computers can't compare text directly
- Vectors enable mathematical similarity:

```python
embedding1 = [0.5, 0.8, 0.2]  # "max pain"
embedding2 = [0.4, 0.7, 0.3]  # "highest loss"
embedding3 = [-0.9, 0.1, 0.8] # "stock split"

similarity(embedding1, embedding2) = 0.95  ← High! (similar concepts)
similarity(embedding1, embedding3) = 0.12  ← Low (different topics)
```

**Semantic Search:**
```
Query: "How does PCR work?"
Embedding: [0.12, 0.45, 0.78, ...]

Doc 1: "PCR is Put-Call Ratio calculated as..."
Embedding: [0.10, 0.47, 0.76, ...]
Similarity: 0.96 ← Very similar!

Doc 2: "Max Pain calculation involves summing..."
Embedding: [-0.34, 0.89, -0.12, ...]
Similarity: 0.23 ← Not related

→ Return Doc 1
```

---

### Step 9.7: Initialize Embeddings Model

**Action:** Add RAG initialization (top of file, after imports):

```python
# Global RAG components
embeddings_model = None
rag_chain = None

def get_embeddings():
    """Initialize embeddings model (singleton)."""
    global embeddings_model
    
    if embeddings_model is None:
        embeddings_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        logger.info("embeddings_model_initialized")
    
    return embeddings_model
```

**Breaking Down Embeddings Model:**

**Model Choice:**
```python
model_name="sentence-transformers/all-MiniLM-L6-v2"
```
- Lightweight model (22M parameters)
- Fast inference (~10ms per sentence)
- Output: 384-dimensional vectors
- Optimized for semantic similarity

**Alternatives:**
- `all-mpnet-base-v2`: Larger (110M), higher quality, slower
- `multi-qa-mpnet-base-dot-v1`: Optimized for Q&A tasks

**Singleton Pattern:**
```python
if embeddings_model is None:
    embeddings_model = HuggingFaceEmbeddings(...)
```
- Only initialize once
- Reuse for all requests
- Model loading is expensive (~2 seconds)

---

### Step 9.8: Create Document Ingestion Function

**Action:** Add function to load and chunk documents:

```python
def load_documents():
    """Load and chunk project documentation."""
    docs = []
    
    # Path to documentation
    docs_path = "/app/project_docs"
    
    # Target files to ingest
    target_files = ["README.md", "TUTORIAL.md", "API.md"]
    
    for filename in target_files:
        file_path = os.path.join(docs_path, filename)
        
        if not os.path.exists(file_path):
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Chunk by paragraphs (simple strategy)
            chunks = content.split('\n\n')
            
            for chunk in chunks:
                # Skip small chunks
                if len(chunk.strip()) < 50:
                    continue
                
                # Create Document object
                doc = Document(
                    page_content=chunk.strip(),
                    metadata={
                        "source": filename,
                        "length": len(chunk)
                    }
                )
                docs.append(doc)
            
            logger.info("ingested_file", filename=filename, chunks=len(chunks))
        
        except Exception as e:
            logger.error("file_ingest_error", filename=filename, error=str(e))
    
    # Fallback knowledge if no docs
    if not docs:
        docs = [
            Document(
                page_content="DeltaStream is an options trading analytics platform.",
                metadata={"source": "fallback"}
            ),
            Document(
                page_content="Max Pain is the strike price where the most options expire worthless, causing maximum loss to option buyers.",
                metadata={"source": "fallback"}
            ),
            Document(
                page_content="PCR (Put-Call Ratio) is calculated as total put open interest divided by total call open interest.",
                metadata={"source": "fallback"}
            )
        ]
        logger.warning("using_fallback_knowledge")
    
    return docs
```

**Breaking Down Document Processing:**

**Why Chunk?**

**Problem:**
```
README.md: 50,000 characters
LLM context limit: 4,096 tokens (~16,000 characters)
```

**Solution: Chunking**
```
README.md
  ↓ Split on '\n\n'
  ↓
Chunk 1: Introduction (500 chars)
Chunk 2: Installation (800 chars)
Chunk 3: Architecture (1200 chars)
...
```

**Benefits:**
- Each chunk fits in LLM context
- Retrieve only relevant chunks
- More precise answers

**Chunking Strategies:**

**1. Paragraph splitting (simple):**
```python
chunks = content.split('\n\n')
```
- Pros: Fast, preserves natural breaks
- Cons: Variable size, may split mid-thought

**2. Fixed size (better):**
```python
chunk_size = 1000
chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
```
- Pros: Predictable size
- Cons: Splits mid-sentence

**3. Semantic chunking (best, complex):**
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200  # 200 char overlap between chunks
)
chunks = splitter.split_text(content)
```
- Pros: Smart splitting (respects paragraphs, sentences)
- Cons: Slower

**Document Metadata:**
```python
metadata={"source": filename, "length": len(chunk)}
```
- Attached to each chunk
- Used for filtering: "Only search README.md"
- Returned with search results

---

### Step 9.9: Initialize RAG System

**Action:** Add RAG initialization:

```python
def init_rag():
    """Initialize RAG system with vector store and retrieval chain."""
    global rag_chain
    
    # Check if already initialized
    if rag_chain is not None:
        return
    
    # Require API token
    if not HUGGINGFACE_API_TOKEN:
        logger.warning("rag_init_skipped", reason="no_api_token")
        return
    
    try:
        # 1. Get embeddings model
        embeddings = get_embeddings()
        
        # 2. Load documents
        docs = load_documents()
        logger.info("loaded_documents", count=len(docs))
        
        # 3. Create vector store (Redis)
        vector_store = RedisVectorStore.from_documents(
            docs,
            embeddings,
            redis_url=REDIS_URL,
            index_name="deltastream_docs"
        )
        logger.info("vector_store_created", backend="redis")
        
        # 4. Initialize LLM
        llm = HuggingFaceHub(
            repo_id="google/flan-t5-large",
            model_kwargs={"temperature": 0.1, "max_length": 512},
            huggingfacehub_api_token=HUGGINGFACE_API_TOKEN
        )
        
        # 5. Create retrieval chain
        rag_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vector_store.as_retriever(search_kwargs={"k": 3})
        )
        
        logger.info("rag_initialized", num_docs=len(docs))
        
    except Exception as e:
        logger.error("rag_init_error", error=str(e), exc_info=True)
```

**Breaking Down Vector Store:**

**Redis as Vector Database:**
```python
RedisVectorStore.from_documents(
    docs,
    embeddings,
    redis_url=REDIS_URL,
    index_name="deltastream_docs"
)
```

**What happens internally:**

1. **Embed all documents:**
```python
for doc in docs:
    embedding = embeddings.embed_query(doc.page_content)
    # embedding = [0.12, 0.45, ..., 0.91]  # 384 floats
```

2. **Store in Redis:**
```redis
HSET deltastream_docs:0 
  "text" "Max Pain is the strike where..." 
  "embedding" "[0.12, 0.45, ...]"
  "metadata" "{\"source\":\"README.md\"}"

HSET deltastream_docs:1
  "text" "PCR is calculated as..."
  "embedding" "[0.34, -0.21, ...]"
  "metadata" "{\"source\":\"README.md\"}"
```

3. **Create index:**
```redis
FT.CREATE deltastream_docs_idx 
  ON HASH PREFIX 1 deltastream_docs: 
  SCHEMA embedding VECTOR FLAT 6 DIM 384 DISTANCE_METRIC COSINE
```

**Retriever Configuration:**
```python
retriever = vector_store.as_retriever(search_kwargs={"k": 3})
```
- `k=3`: Return top 3 most similar documents
- More k = more context, but longer prompts
- Typical range: 3-10

**RetrievalQA Chain:**
```python
rag_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever
)
```

**chain_type="stuff":**
- Stuffs all retrieved docs into one prompt
- Simple, works well for k=3-5
- Alternatives:
  - `"map_reduce"`: Summarize each doc separately, then combine
  - `"refine"`: Iteratively refine answer with each doc

**How "stuff" works:**

```python
# User query
query = "What is PCR?"

# 1. Retriever finds relevant docs
docs = retriever.get_relevant_documents(query)
# → [doc1, doc2, doc3]

# 2. Construct prompt
prompt = f"""Use the following context to answer the question.

Context:
{docs[0].page_content}

{docs[1].page_content}

{docs[2].page_content}

Question: {query}

Answer:"""

# 3. LLM generates answer
answer = llm(prompt)
```

---

### Step 9.10: Add Chat Endpoint

**Action:** Add RAG chatbot API:

```python
@app.route('/api/ai/chat', methods=['POST'])
def chat():
    """RAG chatbot for Q&A on documentation."""
    try:
        # Check token
        if not HUGGINGFACE_API_TOKEN:
            return jsonify({
                "answer": "Error: HUGGINGFACE_API_TOKEN not configured."
            }), 503
        
        # Lazy init RAG
        if rag_chain is None:
            init_rag()
        
        # Get query
        query = request.json.get('query', '')
        if not query:
            return jsonify({"error": "Query required"}), 400
        
        # Safety check
        if len(query) > 500:
            return jsonify({"error": "Query too long (max 500 chars)"}), 400
        
        # Run RAG chain
        if rag_chain:
            answer = rag_chain.run(query)
        else:
            answer = "RAG system failed to initialize. Check logs."
        
        return jsonify({
            "query": query,
            "answer": answer.strip()
        }), 200
        
    except Exception as e:
        logger.error("chat_error", error=str(e), exc_info=True)
        return jsonify({
            "error": "Internal error during chat"
        }), 500
```

**Lazy Initialization:**
```python
if rag_chain is None:
    init_rag()
```
- Don't initialize on startup (slow)
- Initialize on first request
- Subsequent requests use cached chain

---

### Step 9.11: Add Flask Runner

**Action:** Add main entry point:

```python
if __name__ == '__main__':
    logger.info("ai_analyst_starting", port=PORT)
    app.run(host='0.0.0.0', port=PORT, debug=False)
```

---

## 9.6 Dockerization

### Step 9.12: Create Docker configuration

**Action:** Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download embedding model (cache)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy application
COPY app.py .

# Create docs directory
RUN mkdir -p /app/project_docs

EXPOSE 8006

CMD ["python", "app.py"]
```

**Why pre-download model?**
```dockerfile
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('...')"
```
- Downloads model during build (not runtime)
- Faster startup
- No network dependency on first run

**Action:** Add to `docker-compose.yml`:

```yaml
  ai-analyst:
    build:
      context: ./services/ai-analyst
    container_name: deltastream-ai-analyst
    ports:
      - "8006:8006"
    environment:
      - HUGGINGFACE_API_TOKEN=${HUGGINGFACE_API_TOKEN}
      - ANALYTICS_SERVICE_URL=http://analytics:8004
      - REDIS_URL=redis://redis:6379/0
      - PORT=8006
    volumes:
      - ./docs:/app/project_docs:ro
    depends_on:
      - redis
      - analytics
    networks:
      - deltastream-network
    restart: unless-stopped
```

**Volume Mount:**
```yaml
volumes:
  - ./docs:/app/project_docs:ro
```
- Mounts `./docs` directory into container
- `:ro` = read-only
- RAG can read project documentation

---

## 9.7 Testing

### Step 9.13: Test Market Pulse

**Action:** Test LLM summarization:

```bash
curl "http://localhost:8006/api/ai/pulse?product=NIFTY"
```

**Expected:**
```json
{
  "product": "NIFTY",
  "analysis": "Neutral sentiment. The PCR of 1.15 indicates balanced put and call open interest, suggesting market participants are hedging equally on both sides. Watch for breakout signals above 21800 or support at 21500.",
  "data": {
    "pcr_oi": 1.15,
    "pcr_volume": 0.98
  }
}
```

---

### Step 9.14: Test Sentiment Analysis

**Action:** Test news sentiment:

```bash
curl http://localhost:8006/api/ai/sentiment
```

**Expected:**
```json
{
  "sentiment": "Bullish",
  "headlines": [
    "Nifty hits record high on FII inflows",
    "Banking stocks surge 3% on rate cut hopes",
    "Retail investors bullish on tech stocks"
  ]
}
```

---

### Step 9.15: Test RAG Chatbot

**Action:** Test Q&A:

```bash
curl -X POST http://localhost:8006/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Max Pain?"}'
```

**Expected:**
```json
{
  "query": "What is Max Pain?",
  "answer": "Based on the documentation, Max Pain is the strike price at which the maximum number of option contracts (both calls and puts) expire worthless, causing the greatest financial loss to option buyers and maximum profit to option sellers."
}
```

---

## Summary

You've built an **AI-powered Analyst Service** with:

✅ **Market Pulse** - LLM-generated summaries
✅ **Sentiment Analysis** - News classification
✅ **RAG Chatbot** - Q&A on your docs
✅ **LangChain** - Production LLM framework
✅ **Embeddings** - Semantic text search
✅ **Vector Store** - Redis for similarity search

**Key Learnings:**
- RAG solves LLM knowledge cutoff
- Embeddings enable semantic search
- LangChain chains simplify LLM apps
- Temperature controls randomness
- Chunking fits docs in context windows
- Vector stores enable similarity search

**Production Tips:**
- Use OpenAI GPT for better quality
- Implement caching (same query = cached answer)
- Add rate limiting
- Monitor LLM costs
- Consider local models for privacy

**Next:** Chapter 13 covers the Trade Simulator with order matching!

---
