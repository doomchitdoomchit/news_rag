import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

# SQL Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./news.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ChromaDB Setup (LangChain)
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")

# Initialize Embeddings
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004", 
    google_api_key=os.getenv('GOOGLE_API_KEY')
)

# Initialize Vector Store
vector_store = Chroma(
    collection_name="news_articles",
    embedding_function=embeddings,
    persist_directory=CHROMA_DB_PATH
)

def get_vector_store():
    return vector_store
