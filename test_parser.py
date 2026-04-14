#!/usr/bin/env python3
"""Test script to verify the refactored parse_recipe_markdown function."""

from pathlib import Path
from backend.app.services.recipe_parser import parse_recipe_markdown

# Test with the 红烧茄子.md file
test_file = Path("/Users/firstguo/Project/personal/CookRag/recipes/vegetable_dish/红烧茄子.md")

if test_file.exists():
    print(f"Testing parser with: {test_file}")
    print("=" * 50)
    
    try:
        parsed = parse_recipe_markdown(test_file)
        
        print(f"✓ Recipe ID: {parsed.id}")
        print(f"✓ Title: {parsed.title_zh}")
        print(f"✓ Ingredients count: {len(parsed.ingredients)}")
        print(f"  First 3 ingredients: {parsed.ingredients[:3]}")
        print(f"✓ Steps count: {len(parsed.steps)}")
        print(f"  First step: {parsed.steps[0] if parsed.steps else 'None'}")
        print(f"✓ Content length: {len(parsed.content_zh)} chars")
        print(f"✓ Raw body length: {len(parsed.raw_body)} chars")
        
        print("\n" + "=" * 50)
        print("Parsed content preview:")
        print("-" * 50)
        print(parsed.content_zh[:500] + "..." if len(parsed.content_zh) > 500 else parsed.content_zh)
        
    except Exception as e:
        print(f"✗ Error parsing recipe: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"Test file not found: {test_file}")
