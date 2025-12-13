from sqlalchemy import Column, Integer, String, DateTime, Table, ForeignKey
from sqlalchemy.orm import declarative_base, relationship # type: ignore
from datetime import datetime

Base = declarative_base()

# Association Table
article_author_association = Table(
    'article_author', Base.metadata,
    Column('article_id', Integer, ForeignKey('articles.id')),
    Column('author_id', Integer, ForeignKey('authors.id'))
)

class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True) # "hk" + data-user
    name = Column(String)
    email = Column(String, nullable=True)
    team = Column(String, nullable=True)
    bf_team = Column(String, nullable=True)

    articles = relationship("Article", secondary=article_author_association, back_populates="authors")

    def __repr__(self):
        return f"<Author(name={self.name}, code={self.code})>"

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    url = Column(String, unique=True, index=True)
    content = Column(String) # Storing content as backup
    recent_write = Column(DateTime) # from HTML attribute 'datetime'
    crawled_at = Column(DateTime, default=datetime.utcnow)

    authors = relationship("Author", secondary=article_author_association, back_populates="articles")

    def __repr__(self):
        return f"<Article(title={self.title}, url={self.url})>"
