## Part 9: AI Analyst Service (Advanced AI Integration)

### Learning Objectives

By the end of Part 9, you will understand:

1. **LangChain Framework** - Building LLM applications with chains
2. **RAG (Retrieval-Augmented Generation)** - Combining vector search with LLMs
3. **HuggingFace Integration** - Using open-source LLMs
4. **Sentiment Analysis** - Analyzing news with AI
5. **Vector Stores** - Redis as a vector database
6. **Embeddings** - Converting text to vectors
7. **Prompt Engineering** - Crafting effective prompts

---

### 9.1 Understanding RAG and LLMs

#### What is RAG?

**RAG = Retrieval-Augmented Generation**

**Problem with base LLMs:**
```
User: "What is Max Pain in DeltaStream?"
LLM: "I don't have information about DeltaStream. Max Pain generally refers to..."
```

LLMs have knowledge cutoff dates and don't know your specific data.

**RAG Solution:**

```
┌──────────┐      ┌─────────────┐      ┌─────────┐      ┌──────┐
│  Query   │─────▶│ Vector      │─────▶│ Top-K   │─────▶│ LLM  │
│          │      │ Search      │      │ Docs    │      │      │
└──────────┘      └─────────────┘      └─────────┘      └──────┘
                         │                    │              │
                         │                    │              ▼
                  ┌──────────────┐     ┌──────────────┐  Answer
                  │ Vector Store │     │ Context from │  with your
                  │ (Your Docs)  │     │ your docs    │  data!
                  └──────────────┘     └──────────────┘
```

**How RAG works:**

1. **Index documents**: Convert docs to embeddings, store in vector DB
2. **User asks question**: Convert question to embedding
3. **Vector search**: Find similar documents (k-NN search)
4. **Inject context**: Add retrieved docs to LLM prompt
5. **LLM generates answer**: Using your data as context

**Example:**

```python
# Without RAG
llm("What is Max Pain in DeltaStream?")
# → "I don't know about DeltaStream"

# With RAG
docs = vector_store.similarity_search("Max Pain DeltaStream")
# → Retrieved: "Max Pain in DeltaStream is calculated as the strike where..."

llm(f"Context: {docs}\n\nQuestion: What is Max Pain?")
# → "Based on DeltaStream documentation, Max Pain is..."
```

---

### 9.2 Building the AI Analyst Service

#### Dependencies

`requirements.txt`:
```txt
flask==3.0.0
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
```

**Key dependencies:**
- `langchain`: LLM application framework
- `huggingface_hub`: Access HuggingFace models
- `transformers`: Model loading and inference
- `sentence-transformers`: Text embeddings
- `feedparser`: Parse RSS news feeds

---

#### Part 9.2.1: Service Setup

```python
#!/usr/bin/env python3
"""
AI Analyst Service

Provides:
1. Market Pulse - Automated market summaries
2. Sentiment Analysis - News sentiment with LLM
3. Trade Assistant - RAG chatbot for Q&A
"""

import os
import structlog
import feedparser
from flask import Flask, jsonify, request
from flask_cors import CORS

# LangChain imports
from langchain.llms import HuggingFaceHub
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Redis
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, RetrievalQA
from langchain.docstore.document import Document

# Configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'ai-analyst')
PORT = int(os.getenv('PORT', '8006'))
ANALYTICS_SERVICE_URL = os.getenv('ANALYTICS_SERVICE_URL', 'http://analytics:8004')
HUGGINGFACE_API_TOKEN = os.getenv('HUGGINGFACE_API_TOKEN', '')

app = Flask(__name__)
CORS(app)
```

**HuggingFace API Token:**

```bash
# Sign up at https://huggingface.co/
# Get token from https://huggingface.co/settings/tokens
# Add to .env:
HUGGINGFACE_API_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx
```

---

#### Part 9.2.2: Feature 1 - Market Pulse (LLM Summarization)

```python
@app.route('/api/ai/pulse', methods=['GET'])
def get_market_pulse():
    """Generates market summary using LLM."""
    product = request.args.get('product', 'NIFTY')
    
    # 1. Fetch data from Analytics Service
    analytics = fetch_analytics_data(product)
    
    # 2. Check for API token
    if not HUGGINGFACE_API_TOKEN:
        return jsonify({
            "product": product,
            "analysis": "AI Analysis Unavailable (Missing HUGGINGFACE_API_TOKEN).",
            "data": analytics
        })

    try:
        # 3. Initialize LLM
        llm = HuggingFaceHub(
            repo_id="google/flan-t5-large", 
            model_kwargs={"temperature": 0.5, "max_length": 256},
            huggingfacehub_api_token=HUGGINGFACE_API_TOKEN
        )
        
        # 4. Construct prompt
        template = """
        Analyze the following option market data for {product}:
        Put-Call Ratio (OI): {pcr}
        Put-Call Ratio (Volume): {pcr_vol}
        
        Provide a concise market sentiment summary (Bullish, Bearish, or Neutral) and explain why based on the PCR.
        """
        prompt = PromptTemplate(template=template, input_variables=["product", "pcr", "pcr_vol"])
        chain = LLMChain(prompt=prompt, llm=llm)
        
        # 5. Run chain
        summary = chain.run({
            "product": product, 
            "pcr": analytics.get('pcr', 'N/A'),
            "pcr_vol": analytics.get('pcr_vol', 'N/A')
        })
        
        return jsonify({
            "product": product,
            "analysis": summary.strip(),
            "data": analytics
        })
        
    except Exception as e:
        logger.error("market_pulse_error", error=str(e))
        return jsonify({"error": "Failed to generate AI analysis"}), 500


def fetch_analytics_data(product):
    """Fetch PCR and other metrics from Analytics Service."""
    try:
        import requests
        data = {}
        
        # Get PCR trend
        pcr_resp = requests.get(f"{ANALYTICS_SERVICE_URL}/pcr/{product}")
        if pcr_resp.status_code == 200:
            pcr_data = pcr_resp.json().get('pcr_trend', [{}])[0]
            data['pcr'] = pcr_data.get('pcr_oi', 'N/A')
            data['pcr_vol'] = pcr_data.get('pcr_volume', 'N/A')
        
        return data
    except Exception as e:
        logger.error("fetch_analytics_error", error=str(e))
        return {}
```

**LangChain components explained:**

**1. LLM (Language Model):**
```python
llm = HuggingFaceHub(
    repo_id="google/flan-t5-large",  # Model name
    model_kwargs={"temperature": 0.5, "max_length": 256}
)
```

**Temperature:**
- `0.0`: Deterministic (always same output)
- `0.5`: Balanced (some creativity)
- `1.0`: Creative (more random)

**2. Prompt Template:**
```python
template = "Analyze data for {product}: PCR={pcr}"
prompt = PromptTemplate(template=template, input_variables=["product", "pcr"])
```

Variables in `{braces}` are filled at runtime.

**3. Chain:**
```python
chain = LLMChain(prompt=prompt, llm=llm)
result = chain.run({"product": "NIFTY", "pcr": 1.2})
```

Chain = Prompt + LLM execution.

**Request flow:**

```
Client                 AI Analyst           Analytics          HuggingFace
  │                        │                    │                   │
  ├─GET /api/ai/pulse─────▶│                    │                   │
  │                        ├──GET /pcr/NIFTY───▶│                   │
  │                        │◀────{pcr: 1.2}─────┤                   │
  │                        │                    │                   │
  │                        ├──────LLM inference─────────────────────▶│
  │                        │   "Analyze PCR 1.2 for NIFTY..."        │
  │                        │◀──"Bullish sentiment (PCR > 1)..."─────┤
  │◀────{analysis: "..."}──┤                    │                   │
```

---

#### Part 9.2.3: Feature 2 - Sentiment Analysis

```python
@app.route('/api/ai/sentiment', methods=['GET'])
def get_sentiment():
    """Analyzes news sentiment using LLM."""
    try:
        # 1. Fetch news headlines
        news_url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^NSEI&region=IN"
        feed = feedparser.parse(news_url, agent="Mozilla/5.0 (DeltaStreamAI/1.0)")
        
        headlines = [entry.title for entry in feed.entries[:5]]
        if not headlines:
            headlines = ["Market stable.", "Traders await RBI decision."]
            
        # 2. Analyze with LLM
        if not HUGGINGFACE_API_TOKEN:
             return jsonify({
                "sentiment": "Neutral (Token Missing)", 
                "headlines": headlines
            })
            
        llm = HuggingFaceHub(
            repo_id="google/flan-t5-large", 
            model_kwargs={"temperature": 0.1, "max_length": 64},
            huggingface_api_token=HUGGINGFACE_API_TOKEN
        )
        
        template = """
        Classify the overall sentiment of these news headlines as Bullish, Bearish, or Neutral:
        {headlines}
        
        Sentiment:
        """
        prompt = PromptTemplate(template=template, input_variables=["headlines"])
        chain = LLMChain(prompt=prompt, llm=llm)
        
        sentiment = chain.run({"headlines": "\n".join(headlines)})
        
        return jsonify({
            "sentiment": sentiment.strip(),
            "headlines": headlines
        })
        
    except Exception as e:
        logger.error("sentiment_error", error=str(e))
        return jsonify({"error": str(e)}), 500
```

**RSS Feed parsing:**

```python
feed = feedparser.parse(news_url)
headlines = [entry.title for entry in feed.entries[:5]]
```

**Example output:**
```python
[
  "Nifty hits all-time high on strong FII inflows",
  "Banking stocks surge 3% on rate cut expectations",
  "IT sector faces headwinds from recession fears"
]
```

**Why temperature=0.1 for sentiment?**

Sentiment classification needs consistency:
- Same headlines → same sentiment
- Low temperature (0.1) = deterministic
- High temperature → "Bullish" one time, "Neutral" next time

---

#### Part 9.2.4: Feature 3 - RAG Chatbot

```python
# Global RAG chain
rag_chain = None

def init_rag():
    """Initialize RAG system."""
    global rag_chain
    if rag_chain: return
    
    try:
        if not HUGGINGFACE_API_TOKEN: return
        
        # 1. Create embeddings model
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # 2. Load documents
        docs_path = "/app/project_docs"
        docs = []
        
        target_files = ["README.md", "TUTORIAL.md"]
        
        for filename in target_files:
            file_path = os.path.join(docs_path, filename)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Chunk by paragraphs
                    chunks = content.split('\n\n')
                    for chunk in chunks:
                        if len(chunk.strip()) > 50:
                            docs.append(Document(
                                page_content=chunk.strip(),
                                metadata={"source": filename}
                            ))
                logger.info("ingested_file", filename=filename)
        
        if not docs:
            # Fallback knowledge
            docs = [
                Document(page_content="DeltaStream is an option analytics platform."),
                Document(page_content="Max Pain is the strike where most contracts expire worthless.")
            ]
        
        # 3. Create vector store (Redis)
        rds = Redis.from_documents(
            docs, 
            embeddings, 
            redis_url="redis://redis:6379",  
            index_name="finance_docs"
        )
        
        # 4. Initialize LLM
        llm = HuggingFaceHub(
            repo_id="google/flan-t5-large", 
            model_kwargs={"temperature": 0.1},
            huggingfacehub_api_token=HUGGINGFACE_API_TOKEN
        )
        
        # 5. Create RAG chain
        rag_chain = RetrievalQA.from_chain_type(
            llm=llm, 
            chain_type="stuff",  # "stuff" = inject all docs in prompt
            retriever=rds.as_retriever()
        )
        
        logger.info("rag_initialized", num_docs=len(docs))
        
    except Exception as e:
        logger.error("rag_init_error", error=str(e))


@app.route('/api/ai/chat', methods=['POST'])
def chat():
    """RAG chatbot endpoint."""
    try:
        if not HUGGINGFACE_API_TOKEN:
             return jsonify({"answer": "Error: HUGGINGFACE_API_TOKEN not set."})

        # Lazy init RAG
        if not rag_chain:
            init_rag()
            
        query = request.json.get('query', '')
        if not query:
            return jsonify({"error": "Query required"}), 400
            
        if rag_chain:
            answer = rag_chain.run(query)
        else:
            answer = "RAG System failed to initialize."
            
        return jsonify({"answer": answer})
        
    except Exception as e:
        logger.error("chat_error", error=str(e))
        return jsonify({"error": str(e)}), 500
```

**RAG chain breakdown:**

**1. Embeddings:**
```python
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
```

Converts text → 384-dimensional vector:
```python
"What is Max Pain?" → [0.23, -0.15, 0.67, ..., 0.91]  # 384 numbers
```

**2. Document chunking:**
```python
chunks = content.split('\n\n')  # Split on paragraphs
```

**Why chunk?**
- LLMs have context limits (2048-4096 tokens)
- Can't fit entire README in one prompt
- Chunking = retrieve only relevant sections

**3. Vector store (Redis):**
```python
rds = Redis.from_documents(docs, embeddings, redis_url="redis://redis:6379")
```

**How Redis stores vectors:**
```
Key: finance_docs:0
Value: {
  "text": "Max Pain is the strike price where...",
  "embedding": [0.12, 0.45, ...],  # 384 floats
  "metadata": {"source": "README.md"}
}
```

**4. Semantic search:**
```python
retriever = rds.as_retriever()
docs = retriever.get_relevant_documents("What is Max Pain?")
```

**Process:**
1. Convert query to embedding: `[0.15, -0.23, ...]`
2. Calculate similarity (cosine) with all stored vectors
3. Return top-k most similar documents

**Example:**
```
Query: "How does PCR work?"
Embedding: [0.12, 0.45, ...]

Doc 1: "PCR is Put-Call Ratio..."
Embedding: [0.10, 0.47, ...]
Similarity: 0.95 ← High!

Doc 2: "Max Pain calculation..."
Embedding: [-0.34, 0.89, ...]
Similarity: 0.23 ← Low

→ Return Doc 1
```

**5. RetrievalQA chain:**
```python
rag_chain = RetrievalQA.from_chain_type(
    llm=llm, 
    chain_type="stuff",  
    retriever=rds.as_retriever()
)
```

**What "stuff" means:**
- Retrieves k relevant docs
- "Stuffs" them all into LLM prompt
- Alternatives: "map_reduce", "refine"

**Behind the scenes:**
```python
# User query
query = "What is PCR?"

# Retrieval
docs = retriever.get_relevant_documents(query)

# Prompt construction
final_prompt = f"""
Context: {docs[0].page_content}
{docs[1].page_content}

Question: {query}

Answer based on the context above:
"""

# LLM call
answer = llm(final_prompt)
```

---

### 9.3 Docker Setup

`Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Create docs directory (for RAG knowledge base)
RUN mkdir -p /app/project_docs

EXPOSE 8006

CMD ["python", "app.py"]
```

`docker-compose.yml` (add):

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
      - PORT=8006
    volumes:
      - ./docs:/app/project_docs:ro  # Mount docs for RAG
    depends_on:
      - redis
      - analytics
    networks:
      - deltastream-network
    restart: unless-stopped
```

**Volume mount:**
```yaml
volumes:
  - ./docs:/app/project_docs:ro
```

- Mounts `./docs` from host into container at `/app/project_docs`
- `:ro` = read-only
- RAG can read your project documentation

---

### 9.4 Testing the AI Service

#### Test 1: Market Pulse

```bash
curl "http://localhost:8006/api/ai/pulse?product=NIFTY"
```

Expected:
```json
{
  "product": "NIFTY",
  "analysis": "Neutral sentiment. The PCR of 1.15 indicates balanced put and call open interest, suggesting market participants are hedging equally on both sides. Watch for breakout signals.",
  "data": {
    "pcr": 1.15,
    "pcr_vol": 0.98
  }
}
```

---

#### Test 2: Sentiment Analysis

```bash
curl http://localhost:8006/api/ai/sentiment
```

Expected:
```json
{
  "sentiment": "Bullish",
  "headlines": [
    "Nifty hits record high on FII inflows",
    "Banking stocks surge 3%",
    "Retail investors bullish on tech stocks"
  ]
}
```

---

#### Test 3: RAG Chatbot

```bash
curl -X POST http://localhost:8006/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Max Pain?"}'
```

Expected:
```json
{
  "answer": "Based on the documentation, Max Pain is the strike price at which the maximum number of option contracts (both calls and puts) expire worthless, causing the greatest financial loss to option buyers and maximum profit to option sellers."
}
```

---

### 9.5 Production Considerations

#### LLM Alternatives

**HuggingFace (Current):**
- ✅ Free tier available
- ✅ Open-source models
- ❌ Slower inference (API calls)
- ❌ Rate limits

**OpenAI GPT:**
```python
from langchain.llms import OpenAI

llm = OpenAI(
    model="gpt-3.5-turbo",
    temperature=0.5,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)
```

- ✅ Faster, higher quality
- ✅ Better reasoning
- ❌ Costs money ($0.002/1K tokens)

**Local models (Llama 2):**
```python
from langchain.llms import LlamaCpp

llm = LlamaCpp(
    model_path="./models/llama-2-7b.gguf",
    temperature=0.5
)
```

- ✅ Free, no API limits
- ✅ Privacy (data never leaves server)
- ❌ Requires GPU (or slow CPU inference)
- ❌ Model management overhead

---

#### Vector Store Alternatives

**Redis (Current):**
- ✅ Already in stack
- ✅ Fast in-memory search
- ❌ Limited to simple k-NN

**Pinecone:**
```python
from langchain.vectorstores import Pinecone

vectorstore = Pinecone.from_documents(
    docs,
    embeddings,
    index_name="deltastream"
)
```

- ✅ Managed service
- ✅ Advanced features (metadata filtering, namespaces)
- ❌ Costs money

**Weaviate, Qdrant, Milvus:** Other specialized vector databases.

---

#### Prompt Engineering Tips

**Bad prompt:**
```python
"Tell me about the market"
```

Too vague, no context.

**Good prompt:**
```python
"""
You are a financial analyst for an options trading platform.
Analyze the following data for {product}:
- PCR (OI): {pcr}
- Max Pain: {max_pain}

Provide:
1. Market sentiment (Bullish/Bearish/Neutral)
2. Brief explanation (2-3 sentences)
3. Key levels to watch

Format your response as JSON.
"""
```

**Principles:**
1. **Role definition**: "You are a financial analyst..."
2. **Structured input**: Clearly label data points
3. **Specific output**: Numbered list, JSON format
4. **Constraints**: "2-3 sentences", word limits

---

### Part 9 Complete: What You've Built

You now have an AI-powered analyst that:

✅ **Market Pulse** - LLM-generated market summaries
✅ **Sentiment Analysis** - Real-time news sentiment
✅ **RAG Chatbot** - Q&A on your documentation
✅ **LangChain Integration** - Production LLM framework
✅ **Vector Search** - Semantic document retrieval
✅ **HuggingFace Models** - Open-source LLMs

---

### Key Learnings from Part 9

**1. RAG solves LLM knowledge limitations**
- LLMs don't know your data
- Vector search retrieves relevant context
- Context injection enables accurate answers

**2. LangChain simplifies LLM apps**
- Chains compose prompts + LLMs
- Retrievers handle vector search
- Templates make prompts reusable

**3. Embeddings enable semantic search**
- Text → vectors (all-MiniLM-L6-v2)
- Cosine similarity finds related docs
- Better than keyword search

**4. Prompt engineering matters**
- Clear role, structured input
- Specific output format
- Examples improve quality

**5. Production LLM considerations**
- Cost vs quality (HuggingFace vs OpenAI vs local)
- Latency (API calls vs local inference)
- Privacy (cloud vs on-premise)

---

## 🎉 COMPLETE TUTORIAL - ALL 9 PARTS FINISHED! 🎉

### Final Tutorial Statistics

- **Total Lines**: 9,360+ lines
- **Parts Completed**: All 9 parts
- **Services Built**: 7 complete microservices + AI integration
- **Code Examples**: 180+ detailed snippets
- **Concepts Covered**: 85+ production patterns

### All Services Covered

1. **Feed Generator** - Market data simulation
2. **Worker Enricher** - Celery-based data processing
3. **Storage Service** - MongoDB repository pattern
4. **Auth Service** - JWT authentication
5. **API Gateway** - Request routing
6. **Socket Gateway** - WebSocket real-time streaming
7. **Analytics Service** - Advanced calculations
8. **AI Analyst** - LLM integration with RAG

### Complete Architecture Stack

**Data Layer:**
- MongoDB (persistence)
- Redis (cache, pub/sub, vector store)

**Processing Layer:**
- Celery (async tasks)
- Python workers

**API Layer:**
- REST (Flask)
- WebSocket (Flask-SocketIO)
- GraphQL-ready architecture

**AI Layer:**
- LangChain
- HuggingFace models
- RAG with vector search

**Infrastructure:**
- Docker
- Docker Compose
- Health checks
- Horizontal scaling

This is now **the most comprehensive microservices + AI tutorial** covering everything from basic architecture to advanced AI integration! 🚀

---

