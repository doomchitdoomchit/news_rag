# News RAG System

This project is a News Aggregation and Retrieval-Augmented Generation (RAG) system that crawls news from the Korean Economic Daily (Hankyung), stores them in a vector database, and provides intelligent answers to user queries using Google Gemini and LangGraph.

## 📌 Features

### 1. News Crawling
-   **Source**: [Korean Economic Daily (Market Insight)](https://www.hankyung.com/mr)
-   **Mechanism**: Automated crawling using `BeautifulSoup4`.
-   **Data**: Extracts Title, Content, URL, and Author.
-   **Scheduling**: Runs automatically every day at **8:00 AM KST** using `APScheduler`.

### 2. RAG System (Retrieval-Augmented Generation)
-   **Agentic Workflow**: Built with `LangGraph` to orchestrate retrieval and generation.
-   **LLM**: Google Gemini 2.5 Pro.
-   **Embeddings**: Google Generative AI Embeddings (`text-embedding-004`).
-   **Vector Store**: `ChromaDB` (via `LangChain` integration) for semantic search.
-   **Process**:
    1.  **Retrieve**: Searches relevant news articles based on user query.
    2.  **Grade**: Evaluates relevance of retrieved documents.
    3.  **Generate**: Synthesizes answers using pertinent context.

### 3. Backend API
-   **Framework**: `FastAPI` (Python).
-   **Endpoints**:
    -   `POST /news/crawl`: Manual trigger for news crawling.
    -   `POST /rag/search`: Query the RAG agent for answers.

## 🛠️ Tech Stack

-   **Language**: Python 3.12+
-   **Web Framework**: FastAPI
-   **LLM Framework**: LangChain, LangGraph
-   **Vector DB**: ChromaDB
-   **Database**: SQLite (SQLAlchemy)
-   **Scheduler**: APScheduler
-   **Crawling**: BeautifulSoup4, Requests
-   **Package Manager**: `uv`

## 🚀 Installation & Setup

### 1. Prerequisites
-   Python 3.12 or higher
-   `uv` (fast Python package installer)

### 2. Clone Repository
```bash
git clone <repository-url>
cd news_RAG
```

### 3. Install Dependencies
This project uses `uv` for dependency management.
```bash
uv sync
```
Or manually with pip (if requirements.txt exists):
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the root directory and add your API keys:
```ini
DATABASE_URL=sqlite:///./news.db
CHROMA_DB_PATH=./chroma_db
GOOGLE_API_KEY=your_google_api_key_here
```

### 5. Run the Server
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 📖 Usage

### Swagger UI
Access the interactive API documentation at: http://localhost:8000/docs

### Example Queries

**Crawl News:**
```bash
curl -X POST "http://localhost:8000/news/crawl"
```

**Search:**
```bash
curl -X POST "http://localhost:8000/rag/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "Samsung Electronics recent stock trends"}'
```

## 📂 Project Structure
```
news_RAG/
├── app/
│   ├── routers/        # API Routes (news, rag)
│   ├── crawler.py      # News crawling logic
│   ├── database.py     # DB & VectorStore setup
│   ├── indexing.py     # ChromaDB indexing logic
│   ├── models.py       # SQLAlchemy models
│   ├── rag_graph.py    # LangGraph agent definition
│   └── scheduler.py    # APScheduler config
├── main.py             # App entry point
├── pyproject.toml      # Dependencies
└── .env                # Environment variables
```
