# Fix for Milvus "Unsupported field type: 0" Error

## Problem
You're encountering this error:
```
pymilvus.exceptions.MilvusException: <MilvusException: (code=Unsupported field type: 0, message=)>
```

## Root Cause
**Version mismatch** between pymilvus client and Milvus server:
- **pymilvus client**: 2.6.2
- **Milvus server**: 2.3.3 (in docker-compose.yml)

The pymilvus 2.6.x client library is not fully compatible with Milvus server 2.3.x, causing schema parsing errors.

## Solution

### Step 1: Downgrade pymilvus
The requirements.txt has been updated to use pymilvus 2.3.3 to match your Milvus server version.

Reinstall the dependencies:
```bash
cd backend
pip install -r requirements.txt
```

Or if using a virtual environment:
```bash
cd backend
source .venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

### Step 2: Recreate the Collection (if needed)
If the collection schema is corrupted, you need to drop and recreate it:

```bash
# From the project root directory
python backend/scripts/recreate_milvus_collection.py
```

This script will:
1. Ask for confirmation (this will delete all data!)
2. Drop the existing collection
3. Recreate it with the correct schema

### Step 3: Re-ingest Your Data
After recreating the collection, you need to re-ingest all recipes:

```bash
# Test with first 10 recipes
python backend/scripts/ingest.py --limit 10

# Ingest all recipes
python backend/scripts/ingest.py
```

### Step 4: Restart Your Backend
```bash
# Stop the backend if running
# Then restart
./start-backend.sh
```

## Verification

Test that the fix works:

```bash
# Test Milvus client
python backend/scripts/test_milvus_client.py
```

You should see all tests pass without the "Unsupported field type: 0" error.

## Alternative: Upgrade Milvus Server

If you want to use pymilvus 2.6.x features, you need to upgrade Milvus server:

1. Edit `docker-compose.yml`:
```yaml
milvus:
  image: milvusdb/milvus:v2.5.0  # or v2.6.0
```

2. Restart Milvus:
```bash
docker-compose down
docker-compose up -d
```

3. Recreate the collection and re-ingest data (schema may have changed between versions)

## Prevention

Always keep pymilvus client version aligned with Milvus server version:
- **Milvus v2.3.x** → **pymilvus v2.3.x**
- **Milvus v2.4.x** → **pymilvus v2.4.x**
- **Milvus v2.5.x** → **pymilvus v2.5.x**

## Current Configuration

After the fix:
- ✅ **pymilvus**: 2.3.3 (in requirements.txt)
- ✅ **Milvus server**: v2.3.3 (in docker-compose.yml)
- ✅ **Versions match**: Compatible
