#!/usr/bin/env python3
"""Verify the development environment is correctly set up."""

import sys
import subprocess
import asyncio
import asyncpg
import redis
import chromadb
import boto3
from botocore.exceptions import ClientError

async def check_postgres():
    try:
        conn = await asyncpg.connect(
            host="localhost", port=5432,
            user="postgres", password="postgres",
            database="redteam"
        )
        version = await conn.fetchval("SELECT version()")
        await conn.close()
        print(f"✅ PostgreSQL: {version.split(',')[0]}")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL: {e}")
        return False

async def check_redis():
    try:
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
        info = r.info()
        print(f"✅ Redis: {info['redis_version']}")
        return True
    except Exception as e:
        print(f"❌ Redis: {e}")
        return False

async def check_chromadb():
    try:
        client = chromadb.HttpClient(host="localhost", port=8000)
        client.heartbeat()
        print("✅ ChromaDB: Connected")
        return True
    except Exception as e:
        print(f"❌ ChromaDB: {e}")
        return False

async def check_minio():
    try:
        client = boto3.client(
            "s3",
            endpoint_url="http://localhost:9000",
            aws_access_key_id="minioadmin",
            aws_secret_access_key="minioadmin",
            region_name="us-east-1"
        )
        client.head_bucket(Bucket="redteam-artifacts")
        print("✅ MinIO: Connected")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            print("⚠️  MinIO: Bucket not found (will be created)")
            return True
        print(f"❌ MinIO: {e}")
        return False
    except Exception as e:
        print(f"❌ MinIO: {e}")
        return False

def check_python():
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"✅ Python: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python: {version.major}.{version.minor}.{version.micro} (requires 3.11+)")
        return False

def check_docker():
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Docker: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Docker: Not found")
            return False
    except Exception:
        print("❌ Docker: Not found")
        return False

def check_node():
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Node.js: Not found")
            return False
    except Exception:
        print("❌ Node.js: Not found")
        return False

async def main():
    print("🔍 Verifying environment...\n")
    
    checks = [
        ("Python", check_python()),
        ("Docker", check_docker()),
        ("Node.js", check_node()),
        ("PostgreSQL", await check_postgres()),
        ("Redis", await check_redis()),
        ("ChromaDB", await check_chromadb()),
        ("MinIO", await check_minio()),
    ]
    
    print("\n📋 Summary:")
    all_passed = True
    for name, passed in checks:
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ All checks passed! Environment is ready.")
        sys.exit(0)
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())