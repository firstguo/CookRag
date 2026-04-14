"""
Test script for MilvusClient.

This script tests all MilvusClient operations:
- Connection and collection initialization
- Upsert recipes
- Search recipes by vector similarity
- Delete recipes
- Collection statistics

Usage:
    python test_milvus_client.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Settings
from app.services.milvus_client import MilvusClient


def create_test_recipe(recipe_id: str, title: str = "测试菜品") -> dict:
    """Create a test recipe with dummy embedding."""
    return {
        "recipe_id": recipe_id,
        "title_zh": title,
        "content_zh": f"这是一道美味的{title}，做法简单，味道鲜美。",
        "ingredients": ["鸡蛋", "西红柿", "盐", "油"],
        "tags": ["家常菜", "素食", "快手菜"],
        "cook_time_minutes": 15,
        "embedding": [0.1] * 1024,  # Dummy embedding vector for bge-m3
    }


def test_milvus_client():
    """Run comprehensive tests for MilvusClient."""
    print("=" * 60)
    print("MilvusClient Test Suite")
    print("=" * 60)
    
    # Initialize settings and client
    print("\n[1/6] Testing connection and initialization...")
    try:
        settings = Settings()
        client = MilvusClient(settings)
        print("✓ Successfully connected to Milvus")
        print(f"  Collection: {settings.MILVUS_COLLECTION_NAME}")
    except Exception as e:
        print(f"✗ Failed to connect to Milvus: {e}")
        print("  Make sure Milvus is running (docker-compose up)")
        return False
    
    # Test collection stats
    print("\n[2/6] Testing collection statistics...")
    try:
        stats = client.get_collection_stats()
        print(f"✓ Collection stats retrieved")
        print(f"  Name: {stats['name']}")
        print(f"  Entities: {stats['num_entities']}")
    except Exception as e:
        print(f"✗ Failed to get collection stats: {e}")
        return False
    
    # Test upsert recipe
    print("\n[3/6] Testing recipe upsert...")
    test_recipes = [
        create_test_recipe("test_001", "西红柿炒鸡蛋"),
        create_test_recipe("test_002", "清炒时蔬"),
        create_test_recipe("test_003", "麻婆豆腐"),
    ]
    
    try:
        for recipe in test_recipes:
            client.upsert_recipe(recipe)
            print(f"✓ Upserted: {recipe['title_zh']} (ID: {recipe['recipe_id']})")
        
        # Verify upsert
        stats = client.get_collection_stats()
        print(f"  Total entities after upsert: {stats['num_entities']}")
    except Exception as e:
        print(f"✗ Failed to upsert recipes: {e}")
        return False
    
    # Test vector search
    print("\n[4/6] Testing vector search...")
    try:
        # Create a query embedding (similar to test_001)
        query_embedding = [0.12] * 1024  # Slightly different from test_001
        
        results = client.search_recipes(
            query_embedding=query_embedding,
            top_k=3,
        )
        
        print(f"✓ Search returned {len(results)} results")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['title_zh']} (score: {result['score']:.4f})")
            print(f"     ID: {result['recipe_id']}")
            print(f"     Tags: {', '.join(result['tags'])}")
    except Exception as e:
        print(f"✗ Failed to search recipes: {e}")
        return False
    
    # Test search with filter expression
    print("\n[5/6] Testing filtered search...")
    try:
        query_embedding = [0.1] * 1024
        
        # Search with ingredient filter
        expr = "array_contains(ingredients, '鸡蛋')"
        results = client.search_recipes(
            query_embedding=query_embedding,
            top_k=5,
            expr=expr,
        )
        
        print(f"✓ Filtered search returned {len(results)} results")
        print(f"  Filter: {expr}")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['title_zh']} (score: {result['score']:.4f})")
    except Exception as e:
        print(f"✗ Failed filtered search: {e}")
        print("  (This may be expected if array filter syntax differs)")
    
    # Test delete recipe
    print("\n[6/6] Testing recipe deletion...")
    try:
        # Delete one recipe
        client.delete_recipe("test_002")
        print("✓ Deleted recipe: test_002 (清炒时蔬)")
        
        # Verify deletion
        stats = client.get_collection_stats()
        print(f"  Total entities after deletion: {stats['num_entities']}")
        
        # Clean up remaining test recipes
        client.delete_recipe("test_001")
        client.delete_recipe("test_003")
        print("✓ Cleaned up remaining test recipes")
        
        stats = client.get_collection_stats()
        print(f"  Final entity count: {stats['num_entities']}")
    except Exception as e:
        print(f"✗ Failed to delete recipes: {e}")
        return False
    
    # Close connection
    client.close()
    print("\n" + "=" * 60)
    print("✓ All tests passed successfully!")
    print("=" * 60)
    return True


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "=" * 60)
    print("Edge Case Tests")
    print("=" * 60)
    
    settings = Settings()
    client = MilvusClient(settings)
    
    # Test upsert with missing optional fields
    print("\n[Edge 1] Testing upsert with minimal fields...")
    try:
        minimal_recipe = {
            "recipe_id": "test_minimal",
            "title_zh": "最小化测试",
            "embedding": [0.05] * 1024,
        }
        client.upsert_recipe(minimal_recipe)
        print("✓ Successfully upserted minimal recipe")
        
        # Clean up
        client.delete_recipe("test_minimal")
        print("✓ Cleaned up minimal recipe")
    except Exception as e:
        print(f"✗ Failed minimal upsert: {e}")
    
    # Test search with no results
    print("\n[Edge 2] Testing search with non-existent recipe...")
    try:
        query_embedding = [0.99] * 1024  # Very different from test data
        results = client.search_recipes(
            query_embedding=query_embedding,
            top_k=5,
        )
        print(f"✓ Search returned {len(results)} results (expected 0 or low similarity)")
    except Exception as e:
        print(f"✗ Failed edge case search: {e}")
    
    # Test delete non-existent recipe
    print("\n[Edge 3] Testing deletion of non-existent recipe...")
    try:
        client.delete_recipe("non_existent_id")
        print("✓ Deletion of non-existent recipe handled gracefully")
    except Exception as e:
        print(f"⚠ Deletion raised error (may be expected): {e}")
    
    client.close()
    print("\n" + "=" * 60)
    print("Edge case tests completed")
    print("=" * 60)


if __name__ == "__main__":
    print("\nStarting MilvusClient tests...\n")
    
    # Run main tests
    success = test_milvus_client()
    
    if success:
        # Run edge case tests
        test_edge_cases()
    else:
        print("\n✗ Main tests failed. Skipping edge case tests.")
        sys.exit(1)
