import os
import sys
from dotenv import load_dotenv

# Ensure root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

from backend.database import init_db, get_stats, get_engine

def main():
    print("=" * 60)
    print("FIREBIRD AI — MICROSOFT SQL SERVER INITIALIZATION")
    print("=" * 60)
    
    db_url = os.getenv("DATABASE_URL", "")
    print(f"Target DATABASE_URL: {db_url}")
    
    try:
        print("\n1. Connecting to Microsoft SQL Server...")
        engine = get_engine()
        print("Connected successfully to SQL Server engine!")
        
        print("\n2. Initializing SQL Server tables...")
        init_db()
        print("Tables initialized successfully!")
        
        print("\n3. Current SQL Server stats:")
        stats = get_stats()
        for k, v in stats.items():
            print(f"  - {k}: {v}")
            
        print("\nDatabase initialization complete.")
    except Exception as e:
        print(f"\n[ERROR] Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
