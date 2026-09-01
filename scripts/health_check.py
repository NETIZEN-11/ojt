#!/usr/bin/env python3
"""Health check script for production monitoring."""

import sys
import asyncio
import httpx
import asyncpg
import redis
import chromadb
import boto3
from datetime import datetime

async def check_service(name: str, check_func) -> bool:
    try:
        result = await check_func()
        print(f"✅ {name}: OK")
        return True
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False

async def check_api(base_url: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{base_url}/health")
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "healthy":
            raise Exception(f"API not healthy: {data}")

async def check_ready(base_url: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{base_url}/ready")
        if resp.status_code != 200:
            raise Exception(f"Readiness check failed: {resp.status_code}")

async def check_postgres(dsn: str):
    conn = await asyncpg.connect(dsn)
    await conn.execute("SELECT 1")
    await conn.close()

async def check_redis(url: str):
    r = redis.from_url(url)
    r.ping()

async def check_chromadb(host: str, port: int):
    client = chromadb.HttpClient(host=host, port=port)
    client.heartbeat()

async def check_minio(endpoint: str, access_key: str, secret_key: str, bucket: str):
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1"
    )
    client.head_bucket(Bucket=bucket)

async def main():
    import os
    
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    db_dsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/redteam")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    chroma_host = os.getenv("CHROMA_HOST", "localhost")
    chroma_port = int(os.getenv("CHROMA_PORT", "8000"))
    minio_endpoint = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
    minio_access = os.getenv("S3_ACCESS_KEY", "minioadmin")
    minio_secret = os.getenv("S3_SECRET_KEY", "minioadmin")
    minio_bucket = os.getenv("S3_BUCKET", "redteam-artifacts")

    print(f"🏥 Health Check - {datetime.utcnow().isoformat()}")
    print(f"   API Base URL: {base_url}")
    print()

    checks = [
        ("API Health", lambda: check_api(base_url)),
        ("API Readiness", lambda: check_ready(base_url)),
        ("PostgreSQL", lambda: check_postgres(db_dsn)),
        ("Redis", lambda: check_redis(redis_url)),
        ("ChromaDB", lambda: check_chromadb(chroma_host, chroma_port)),
        ("MinIO", lambda: check_minio(minio_endpoint, minio_access, minio_secret, minio_bucket)),
    ]

    results = []
    for name, check_func in checks:
        results.append(await check_service(name, check_func))

    print()
    if all(results):
        print("✅ All health checks passed")
        sys.exit(0)
    else:
        print("❌ Some health checks failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())