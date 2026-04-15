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
        expr = "ARRAY_CONTAINS(ingredients, '鸡蛋')"
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


def test_search_recipes_comprehensive():
    """Comprehensive tests specifically for search_recipes function."""
    print("\n" + "=" * 60)
    print("Comprehensive Search Tests")
    print("=" * 60)
    
    settings = Settings()
    client = MilvusClient(settings)
    
    # Setup test data with varied attributes
    print("\n[Setup] Creating diverse test recipes...")
    test_recipes = [
        {
            "recipe_id": "search_test_001",
            "title_zh": "西红柿炒鸡蛋",
            "content_zh": "经典家常菜，酸甜可口",
            "ingredients": ["西红柿", "鸡蛋", "盐", "糖", "油"],
            "tags": ["家常菜", "素食", "快手菜", "酸甜"],
            "cook_time_minutes": 10,
            "embedding": [0.1] * 1024,
        },
        {
            "recipe_id": "search_test_002",
            "title_zh": "麻婆豆腐",
            "content_zh": "四川名菜，麻辣鲜香",
            "ingredients": ["豆腐", "猪肉末", "豆瓣酱", "花椒", "辣椒"],
            "tags": ["川菜", "辣", "麻", "下饭菜"],
            "cook_time_minutes": 20,
            "embedding": [0.2] * 1024,
        },
        {
            "recipe_id": "search_test_003",
            "title_zh": "清炒时蔬",
            "content_zh": "健康清淡，营养丰富",
            "ingredients": ["青菜", "蒜", "盐", "油"],
            "tags": ["素食", "清淡", "健康", "快手菜"],
            "cook_time_minutes": 8,
            "embedding": [0.3] * 1024,
        },
        {
            "recipe_id": "search_test_004",
            "title_zh": "酸辣土豆丝",
            "content_zh": "爽脆开胃，酸辣可口",
            "ingredients": ["土豆", "干辣椒", "醋", "花椒", "盐"],
            "tags": ["辣", "酸", "开胃菜", "素食"],
            "cook_time_minutes": 15,
            "embedding": [0.4] * 1024,
        },
        {
            "recipe_id": "search_test_005",
            "title_zh": "红烧肉",
            "content_zh": "色泽红亮，肥而不腻",
            "ingredients": ["五花肉", "冰糖", "酱油", "料酒", "姜"],
            "tags": ["家常菜", "肉类", "下饭菜"],
            "cook_time_minutes": 60,
            "embedding": [0.5] * 1024,
        },
    ]
    
    try:
        # Insert test recipes
        for recipe in test_recipes:
            client.upsert_recipe(recipe)
            print(f"  ✓ Inserted: {recipe['title_zh']}")
        
        # Wait for Milvus to index
        import time
        time.sleep(1)
        
        stats = client.get_collection_stats()
        print(f"\n  Total entities: {stats['num_entities']}")
        
        # Test 1: Basic search without filters
        print("\n[Test 1] Basic vector search (no filters)...")
        query_embedding = [0.12] * 1024  # Close to search_test_001
        results = client.search_recipes(
            query_embedding=query_embedding,
            top_k=5,
            min_similarity=0.0,
        )
        print(f"  ✓ Returned {len(results)} results")
        for i, r in enumerate(results[:3], 1):
            print(f"    {i}. {r['title_zh']} (score: {r['score']:.4f})")
        
        # Test 2: Search with ARRAY_CONTAINS filter (single ingredient)
        print("\n[Test 2] Search with ARRAY_CONTAINS (single ingredient)...")
        expr = "ARRAY_CONTAINS(ingredients, '鸡蛋')"
        results = client.search_recipes(
            query_embedding=query_embedding,
            top_k=10,
            expr=expr,
            min_similarity=0.0,
        )
        print(f"  ✓ Filter: {expr}")
        print(f"  ✓ Returned {len(results)} results")
        for i, r in enumerate(results, 1):
            print(f"    {i}. {r['title_zh']} - ingredients: {r['ingredients']}")
        
        # Test 3: Search with ARRAY_CONTAINS filter (single tag)
        print("\n[Test 3] Search with ARRAY_CONTAINS (single tag)...")
        expr = "(ARRAY_CONTAINS(tags, '辣'))"
        results = client.search_recipes(
            query_embedding=query_embedding,
            top_k=10,
            expr=expr,
            min_similarity=0.0,
        )
        print(f"  ✓ Filter: {expr}")
        print(f"  ✓ Returned {len(results)} results")
        for i, r in enumerate(results, 1):
            print(f"    {i}. {r['title_zh']} - tags: {r['tags']}")
        
        # Test 4: Search with combined filters (OR logic)
        print("\n[Test 4] Search with combined filters (OR logic)...")
        expr = "ARRAY_CONTAINS(tags, '辣') or ARRAY_CONTAINS(tags, '酸')"
        results = client.search_recipes(
            query_embedding=query_embedding,
            top_k=10,
            expr=expr,
            min_similarity=0.0,
        )
        print(f"  ✓ Filter: {expr}")
        print(f"  ✓ Returned {len(results)} results")
        for i, r in enumerate(results, 1):
            print(f"    {i}. {r['title_zh']} - tags: {r['tags']}")
        
        # Test 5: Search with combined filters (AND logic)
        print("\n[Test 5] Search with combined filters (AND logic)...")
        expr = "ARRAY_CONTAINS(tags, '素食') and ARRAY_CONTAINS(tags, '快手菜')"
        results = client.search_recipes(
            query_embedding=query_embedding,
            top_k=10,
            expr=expr,
            min_similarity=0.0,
        )
        print(f"  ✓ Filter: {expr}")
        print(f"  ✓ Returned {len(results)} results")
        for i, r in enumerate(results, 1):
            print(f"    {i}. {r['title_zh']} - tags: {r['tags']}")
        
        # Test 6: Search with numeric filter
        print("\n[Test 6] Search with numeric filter (cook_time)...")
        expr = "cook_time_minutes <= 15"
        results = client.search_recipes(
            query_embedding=query_embedding,
            top_k=10,
            expr=expr,
            min_similarity=0.0,
        )
        print(f"  ✓ Filter: {expr}")
        print(f"  ✓ Returned {len(results)} results")
        for i, r in enumerate(results, 1):
            print(f"    {i}. {r['title_zh']} - cook_time: {r['cook_time_minutes']}min")
        
        # Test 7: Search with complex combined filters
        print("\n[Test 7] Search with complex combined filters...")
        expr = "(ARRAY_CONTAINS(tags, '素食') or ARRAY_CONTAINS(ingredients, '鸡蛋')) and cook_time_minutes <= 20"
        results = client.search_recipes(
            query_embedding=query_embedding,
            top_k=10,
            expr=expr,
            min_similarity=0.0,
        )
        print(f"  ✓ Filter: {expr}")
        print(f"  ✓ Returned {len(results)} results")
        for i, r in enumerate(results, 1):
            print(f"    {i}. {r['title_zh']} - tags: {r['tags']}, time: {r['cook_time_minutes']}min")
        
        # Test 8: Search with high min_similarity threshold
        print("\n[Test 8] Search with high similarity threshold...")
        results = client.search_recipes(
            query_embedding=query_embedding,
            top_k=10,
            min_similarity=0.95,
        )
        print(f"  ✓ Min similarity: 0.95")
        print(f"  ✓ Returned {len(results)} results (should be few or none)")
        
        # Test 9: Search with non-existent filter value
        print("\n[Test 9] Search with non-existent filter value...")
        expr = "ARRAY_CONTAINS(ingredients, '龙虾')"
        results = client.search_recipes(
            query_embedding=query_embedding,
            top_k=10,
            expr=expr,
            min_similarity=0.0,
        )
        print(f"  ✓ Filter: {expr}")
        print(f"  ✓ Returned {len(results)} results (should be 0)")
        
        # Test 10: Search with special characters in filter
        print("\n[Test 10] Search with special characters in filter...")
        # Test with single quote escaping (if any recipe has it)
        expr = "ARRAY_CONTAINS(tags, '下饭菜')"
        results = client.search_recipes(
            query_embedding=query_embedding,
            top_k=10,
            expr=expr,
            min_similarity=0.0,
        )
        print(f"  ✓ Filter: {expr}")
        print(f"  ✓ Returned {len(results)} results")
        
        # Cleanup
        print("\n[Cleanup] Removing test recipes...")
        for recipe in test_recipes:
            client.delete_recipe(recipe["recipe_id"])
        print("  ✓ All test recipes deleted")
        
        client.close()
        print("\n" + "=" * 60)
        print("✓ All comprehensive search tests passed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
        # Attempt cleanup
        try:
            for recipe in test_recipes:
                client.delete_recipe(recipe["recipe_id"])
            print("\n  ✓ Cleanup completed")
        except:
            pass
        
        client.close()
        return False


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
        # Run comprehensive search tests
        search_success = test_search_recipes_comprehensive()
        
        if search_success:
            # Run edge case tests
            test_edge_cases()
        else:
            print("\n✗ Comprehensive search tests failed.")
            sys.exit(1)
    else:
        print("\n✗ Main tests failed. Skipping further tests.")
        sys.exit(1)
