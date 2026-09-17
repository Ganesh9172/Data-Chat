import os
import sys
from dotenv import load_dotenv

# Ensure root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

from backend.database import init_db, get_stats

def main():
    print("=" * 60)
    print("FIREBIRD AI — JSON FILE STORAGE INITIALIZATION")
    print("=" * 60)
    
    try:
        print("\n1. Initializing JSON file storage in data/...")
        init_db()
        print("JSON storage initialized successfully!")
        
        print("\n2. Current JSON storage stats:")
        stats = get_stats()
        for k, v in stats.items():
            print(f"  - {k}: {v}")
            
        print("\nJSON storage initialization complete.")
    except Exception as e:
        print(f"\n[ERROR] JSON storage initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
