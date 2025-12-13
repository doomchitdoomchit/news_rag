from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base # type: ignore
from datetime import datetime

Base = declarative_base()

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    url = Column(String, unique=True, index=True)
    content = Column(String) # Storing content here as backup/cache, though ChromaDB is main for RAG
    author = Column(String, nullable=True)
    crawled_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<News(title={self.title}, url={self.url})>"
