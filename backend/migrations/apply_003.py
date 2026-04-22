#!/usr/bin/env python3
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from config import settings

SQL = open(os.path.join(os.path.dirname(__file__), "003_auth_fields.sql"), encoding="utf-8").read()

async def main():
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text(SQL))
    finally:
        await engine.dispose()
    print("Migration 003 applied.")

asyncio.run(main())
