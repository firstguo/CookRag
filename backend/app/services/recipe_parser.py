from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import frontmatter


def slugify(text: str) -> str:
    text = text.strip().lower()
    # Keep ascii alnum and CJK; replace other chars with '-'
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "recipe"


def _normalize_maybe_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        # Accept either comma-separated or a single string.
        s = value.strip()
        if not s:
            return []
        if "," in s:
            return [part.strip() for part in s.split(",") if part.strip()]
        return [s]
    return [str(value).strip()]


def _extract_sections_from_body(body: str) -> Dict[str, str]:
    """Extract sections from markdown based on ## headers."""
    sections = {}
    current_section = "content"
    current_content = []
    
    for line in body.splitlines():
        header_match = re.match(r'^##\s+(.+)$', line.strip())
        if header_match:
            # Save previous section
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            # Start new section
            current_section = header_match.group(1).strip()
            current_content = []
        else:
            current_content.append(line)
    
    # Save last section
    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections


def _extract_ingredients_from_section(ingredients_section: str) -> List[str]:
    """Extract ingredients from the ingredients section."""
    ingredients = []
    for line in ingredients_section.splitlines():
        line = line.strip()
        if not line:
            continue
        # Match list items like "- 大蒜" or "* 大蒜"
        m = re.match(r'^[-*]\s+(.+)$', line)
        if m:
            ingredients.append(m.group(1).strip())
    return ingredients


def _extract_steps_from_section(steps_section: str) -> List[str]:
    """Extract steps from the operations section."""
    steps = []
    for line in steps_section.splitlines():
        line = line.strip()
        if not line:
            continue
        # Match numbered steps like "1. xxx" or "1、xxx"
        m = re.match(r'^\d+[\.、]\s*(.+)$', line)
        if m:
            steps.append(m.group(1).strip())
        # Also match bullet points as fallback
        else:
            m = re.match(r'^[-*]\s+(.+)$', line)
            if m:
                steps.append(m.group(1).strip())
    return steps


def _extract_steps_from_body(body: str) -> List[str]:
    """
    Fallback: parse markdown list items like:
      - xxx
      1. xxx
    """
    steps: List[str] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^[-*]\s+(.+)$", line)
        if m:
            steps.append(m.group(1).strip())
            continue
        m = re.match(r"^\d+\.\s+(.+)$", line)
        if m:
            steps.append(m.group(1).strip())
            continue
    return steps


@dataclass
class ParsedRecipe:
    id: str
    title_zh: str
    ingredients: List[str]
    tags: List[str]
    cook_time_minutes: Optional[int]
    steps: List[str]
    content_zh: str
    raw_body: str


def parse_recipe_markdown(path: Path) -> ParsedRecipe:
    post = frontmatter.load(path)
    fm = post.metadata or {}
    body = post.content or ""

    # Try to get title from frontmatter first
    title = str(fm.get("title") or fm.get("title_zh") or "").strip()
    
    # If no title in frontmatter, extract from markdown
    if not title:
        # Check for title in first line (like "# 红烧茄子的做法")
        first_line_match = re.match(r'^#\s+(.+)$', body.splitlines()[0].strip() if body.splitlines() else "")
        if first_line_match:
            title = first_line_match.group(1).strip()
            # Remove the title suffix like "的做法" if present
            if title.endswith("的做法"):
                title = title[:-3]
        else:
            # Use first non-empty line as best-effort fallback.
            for line in body.splitlines():
                if line.strip():
                    title = line.strip()
                    break
    
    if not title:
        raise ValueError(f"{path}: missing title")

    rid = str(fm.get("id") or hashlib.md5(str(path).encode()).hexdigest()).strip()
    rid = slugify(rid)

    # Extract ingredients
    ingredients = _normalize_maybe_list(fm.get("ingredients"))
    if not ingredients:
        # Try to extract from body sections
        sections = _extract_sections_from_body(body)
        # Look for ingredients section (could be named differently)
        ingredients_section = ""
        for section_name, section_content in sections.items():
            if any(keyword in section_name.lower() for keyword in ['原料', '食材', 'ingredient', '材料']):
                ingredients_section = section_content
                break
        if ingredients_section:
            ingredients = _extract_ingredients_from_section(ingredients_section)

    # Extract tags
    tags = _normalize_maybe_list(fm.get("tags"))
    # If no tags in frontmatter, try to infer from directory structure or content
    if not tags:
        # Could potentially extract from path or other metadata
        pass

    # Extract cook time
    cook_time_minutes: Optional[int] = None
    if fm.get("cook_time_minutes") is not None:
        try:
            cook_time_minutes = int(fm.get("cook_time_minutes"))
        except ValueError:
            cook_time_minutes = None
    elif fm.get("cook_time") is not None:
        try:
            cook_time_minutes = int(fm.get("cook_time"))
        except ValueError:
            cook_time_minutes = None

    # Extract steps
    steps = _normalize_maybe_list(fm.get("steps"))
    if not steps:
        # Try to extract from body sections
        sections = _extract_sections_from_body(body)
        steps_section = ""
        for section_name, section_content in sections.items():
            if any(keyword in section_name.lower() for keyword in ['操作', '步骤', 'step', '做法', '制作']):
                steps_section = section_content
                break
        if steps_section:
            steps = _extract_steps_from_section(steps_section)
        else:
            # Fallback to original method
            steps = _extract_steps_from_body(body)

    # Build embedding text from structured fields; keep it deterministic.
    parts: List[str] = []
    parts.append(f"title: {title}")
    if ingredients:
        parts.append(f"ingredients: {', '.join(ingredients)}")
    if tags:
        parts.append(f"tags: {', '.join(tags)}")
    if steps:
        parts.append("steps:\n" + "\n".join([f"- {s}" for s in steps]))
    content_zh = "\n".join(parts).strip()

    return ParsedRecipe(
        id=rid,
        title_zh=title,
        ingredients=ingredients,
        tags=tags,
        cook_time_minutes=cook_time_minutes,
        steps=steps,
        content_zh=content_zh,
        raw_body=body,
    )


if __name__ == "__main__":
    # Test case using 红烧茄子.md
    from pathlib import Path
    
    test_file = Path(__file__).parent.parent.parent.parent / "recipes" / "vegetable_dish" / "红烧茄子.md"
    
    if test_file.exists():
        print(f"Testing parser with: {test_file}")
        print("=" * 60)
        
        try:
            parsed = parse_recipe_markdown(test_file)
            
            print(f"✓ Recipe ID: {parsed.id}")
            print(f"✓ Title: {parsed.title_zh}")
            print(f"✓ Ingredients count: {len(parsed.ingredients)}")
            print(f"  Ingredients: {parsed.ingredients}")
            print(f"✓ Tags: {parsed.tags}")
            print(f"✓ Cook time: {parsed.cook_time_minutes}")
            print(f"✓ Steps count: {len(parsed.steps)}")
            for i, step in enumerate(parsed.steps[:3], 1):
                print(f"  Step {i}: {step}")
            if len(parsed.steps) > 3:
                print(f"  ... and {len(parsed.steps) - 3} more steps")
            
            print("\n" + "=" * 60)
            print("Generated content for embedding:")
            print("-" * 60)
            print(parsed.content_zh)
            print("=" * 60)
            
        except Exception as e:
            print(f"✗ Error parsing recipe: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"Test file not found: {test_file}")
        print("Please ensure the recipe file exists at the expected path.")
