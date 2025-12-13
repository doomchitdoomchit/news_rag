import sys
import os
from sqlalchemy import text
from app.database import SessionLocal, engine

def reset_database():
    """
    Resets the database by clearing all data from tables.
    Handles both SQLite (DELETE) and Postgres (TRUNCATE).
    """
    session = SessionLocal()
    try:
        # Order matters for foreign keys
        tables = ['article_author', 'authors', 'articles']
        print("Resetting database...")
        
        # Check if using SQLite
        # This is a basic check. Can be improved if needed.
        is_sqlite = 'sqlite' in str(engine.url)
        
        for table in tables:
            print(f"Clearing table: {table}")
            if is_sqlite:
                # SQLite doesn't support TRUNCATE standardly
                session.execute(text(f"DELETE FROM {table}"))
                try:
                    # Reset autoincrement counter in SQLite
                    session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'"))
                except Exception:
                    pass 
            else:
                # Postgres/others
                session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
                
        session.commit()
        print("Database reset successfully.")
        
    except Exception as e:
        print(f"Error resetting database: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    reset_database()
