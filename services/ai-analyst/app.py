#!/usr/bin/env python3
"""
AI Analyst Service

Provides:
1. Market Pulse (Automated Summaries)
2. Sentiment Analysis (FinBERT)
3. Trade Assistant (RAG Chatbot)
"""

import os
import structlog
import feedparser
from flask import Flask, jsonify, request
from flask_cors import CORS

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

# LangChain / RAG Imports
from langchain.llms import HuggingFaceHub
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Redis
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, RetrievalQA
from langchain.docstore.document import Document

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': SERVICE_NAME}), 200


def fetch_analytics_data(product):
    """Fetch key metrics from Analytics Service."""
    try:
        data = {}
        # 1. Get PCR
        pcr_resp = requests.get(f"{ANALYTICS_SERVICE_URL}/pcr/{product}")
        if pcr_resp.status_code == 200:
            pcr_data = pcr_resp.json().get('latest', [{}])[0]
            data['pcr'] = pcr_data.get('pcr_oi', 'N/A')
            data['pcr_vol'] = pcr_data.get('pcr_volume', 'N/A')
        
        # 2. Get Max Pain (requires expiry, need to fetch expiries first or just try near date)
        # Simplified: fetching Max Pain with 'current' or first available expiry would be better
        # For now, we'll skip Max Pain complexities or mock a call if we had the date.
        
        return data
    except Exception as e:
        logger.error("fetch_analytics_error", error=str(e))
        return {}

# --- Feature 1: Market Pulse ---
@app.route('/api/ai/pulse', methods=['GET'])
def get_market_pulse():
    """Generates a market summary using LLM."""
    product = request.args.get('product', 'NIFTY')
    
    # 1. Fetch Data
    analytics = fetch_analytics_data(product)
    
    # 2. Check for API Token
    if not HUGGINGFACE_API_TOKEN:
        return jsonify({
            "product": product,
            "analysis": "AI Analysis Unavailable (Missing HUGGINGFACE_API_TOKEN).",
            "data": analytics,
            "note": "Please configure HUGGINGFACE_API_TOKEN in docker-compose.yml"
        })

    try:
        # 3. Initialize LLM
        llm = HuggingFaceHub(
            repo_id="google/flan-t5-large", 
            model_kwargs={"temperature": 0.5, "max_length": 256},
            huggingfacehub_api_token=HUGGINGFACE_API_TOKEN
        )
        
        # 4. Construct Prompt
        template = """
        Analyze the following option market data for {product}:
        Put-Call Ratio (OI): {pcr}
        Put-Call Ratio (Volume): {pcr_vol}
        
        Provide a concise market sentiment summary (Bullish, Bearish, or Neutral) and explain why based on the PCR.
        """
        prompt = PromptTemplate(template=template, input_variables=["product", "pcr", "pcr_vol"])
        chain = LLMChain(prompt=prompt, llm=llm)
        
        # 5. Run Chain
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
        return jsonify({"error": "Failed to generate AI analysis", "details": str(e)}), 500



# --- Feature 2: Sentiment Analysis ---
@app.route('/api/ai/sentiment', methods=['GET'])
def get_sentiment():
    """Analyzes news sentiment using LLM."""
    try:
        # 1. Fetch News (Mock RSS for robustness or Real URL)
        # Using a reliable financial feed or fallback
        news_url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^NSEI,^NSEBANK&region=IN&lang=en-IN"
        # feedparser handles User-Agent automatically but sometimes explicit headers help
        feed = feedparser.parse(news_url, agent="Mozilla/5.0 (compatible; DeltaStreamAI/1.0)")
        
        headlines = [entry.title for entry in feed.entries[:5]]
        if not headlines:
            headlines = ["Market seems stable today.", "Traders awaiting RBI decision.", "Global cues are neutral."]
            
        # 2. Analyze with LLM (reuse FLAN-T5)
        if not HUGGINGFACE_API_TOKEN:
             return jsonify({
                "sentiment": "Neutral (Token Missing)", 
                "headlines": headlines,
                "summary": "Please configure HuggingFace Token."
            })
            
        llm = HuggingFaceHub(
            repo_id="google/flan-t5-large", 
            model_kwargs={"temperature": 0.1, "max_length": 64},
            huggingfacehub_api_token=HUGGINGFACE_API_TOKEN
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

# --- Feature 3: Trade Assistant (RAG) ---
# Global RAG Chain (lazy init)
rag_chain = None

def init_rag():
    """Initialize RAG system (Vector Store + Chain)."""
    global rag_chain
    if rag_chain: return
    
    try:
        if not HUGGINGFACE_API_TOKEN: return
        
        # 1. Embeddings
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # 2. Docs (Knowledge Base)
        # Load from mounted /app/project_docs
        docs_path = "/app/project_docs"
        docs = []
        
        # Files to ingest
        target_files = ["TUTORIAL.md", "README.md", "interview-concepts.md"]
        
        for filename in target_files:
            file_path = os.path.join(docs_path, filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Simple chunking by splitting on double newlines
                        chunks = content.split('\n\n')
                        for chunk in chunks:
                            if len(chunk.strip()) > 50:  # Ignore small empty chunks
                                docs.append(Document(
                                    page_content=chunk.strip(),
                                    metadata={"source": filename}
                                ))
                    logger.info("ingested_file", filename=filename)
                except Exception as e:
                    logger.error("file_ingest_error", filename=filename, error=str(e))
        
        if not docs:
            # Fallback if no docs found
            logger.warning("no_docs_found_using_fallback")
            texts = [
                "DeltaStream is an option analytics platform.",
                "Max Pain is the strike price where the most open option contracts expire worthless."
            ]
            docs = [Document(page_content=t) for t in texts]
        
        # 3. Vector Store (Redis)
        # Using redis url from env
        rds = Redis.from_documents(
            docs, 
            embeddings, 
            redis_url="redis://redis:6379",  
            index_name="finance_docs"
        )
        
        # 4. LLM
        llm = HuggingFaceHub(
            repo_id="google/flan-t5-large", 
            model_kwargs={"temperature": 0.1},
            huggingfacehub_api_token=HUGGINGFACE_API_TOKEN
        )
        
        # 5. Chain
        rag_chain = RetrievalQA.from_chain_type(
            llm=llm, 
            chain_type="stuff", 
            retriever=rds.as_retriever()
        )
        logger.info("rag_initialized")
        
    except Exception as e:
        logger.error("rag_init_error", error=str(e))


@app.route('/api/ai/chat', methods=['POST'])
def chat():
    """RAG Chatbot endpoint."""
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
            answer = "RAG System failed to initialize (check logs/redis)."
            
        return jsonify({"answer": answer})
        
    except Exception as e:
        logger.error("chat_error", error=str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    logger.info("ai_analyst_starting", port=PORT)
    app.run(host='0.0.0.0', port=PORT, debug=True)
