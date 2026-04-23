#!/usr/bin/env python3
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from config import settings

SQL_FILE = os.path.join(os.path.dirname(__file__), "003_auth_fields.sql")

async def main():
    sql = open(SQL_FILE, encoding="utf-8").read()
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as conn:
            for stmt in statements:
                await conn.execute(text(stmt))
    finally:
        await engine.dispose()
    print("Migration 003 applied.")

asyncio.run(main())
