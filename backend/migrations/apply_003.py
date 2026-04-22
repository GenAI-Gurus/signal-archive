#!/usr/bin/env python3
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from config import settings

SQL = open(os.path.join(os.path.dirname(__file__), "003_auth_fields.sql")).read()

async def main():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL.split(";"):
            stmt = stmt.strip()
            if stmt:
                await conn.execute(text(stmt))
    print("Migration 003 applied.")

asyncio.run(main())
