"""
Script to drop and recreate the Milvus collection.
Use this when encountering schema corruption or version mismatch issues.

Usage:
    python backend/scripts/recreate_milvus_collection.py
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from app.config import Settings
from app.services.milvus_client import MilvusClient
from pymilvus import utility


def main():
    print("=" * 60)
    print("Milvus Collection Recreation Script")
    print("=" * 60)
    
    settings = Settings()
    collection_name = settings.MILVUS_COLLECTION_NAME
    
    print(f"\nCollection name: {collection_name}")
    print(f"Milvus server: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
    
    # Check if collection exists
    if not utility.has_collection(collection_name):
        print(f"\n✗ Collection '{collection_name}' does not exist.")
        print("  No action needed. Collection will be created on first use.")
        return
    
    print(f"\n✓ Collection '{collection_name}' exists.")
    
    # Ask for confirmation
    response = input("\n⚠ This will DELETE all data in the collection. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("\n✗ Operation cancelled.")
        return
    
    # Drop collection
    print(f"\n[1/2] Dropping collection '{collection_name}'...")
    try:
        utility.drop_collection(collection_name)
        print(f"✓ Collection dropped successfully.")
    except Exception as e:
        print(f"✗ Failed to drop collection: {e}")
        return
    
    # Verify collection is dropped
    if utility.has_collection(collection_name):
        print(f"✗ Collection still exists after drop!")
        return
    
    print(f"\n[2/2] Recreating collection...")
    try:
        # Create new MilvusClient which will recreate the collection
        client = MilvusClient(settings)
        print(f"✓ Collection recreated successfully.")
        
        # Show stats
        stats = client.get_collection_stats()
        print(f"\nCollection stats:")
        print(f"  Name: {stats['name']}")
        print(f"  Entities: {stats['num_entities']}")
        
        client.close()
        print(f"\n✓ Collection recreation completed successfully!")
        print(f"\n⚠ You need to re-ingest all recipes into the new collection.")
        print(f"  Run: python backend/scripts/ingest.py --limit 10")
        
    except Exception as e:
        print(f"✗ Failed to recreate collection: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
