import pytest
import pytest_asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from cryptography.fernet import Fernet

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("OPENAI_API_KEY", "x")
os.environ.setdefault("API_KEY_SALT", "x")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())
os.environ.setdefault("RESEND_API_KEY", "")


@pytest.fixture(autouse=True, scope='function')
def cleanup_summarizer_modules(request):
    """Clean up summarizer module imports to avoid conflicts between test_summarizer.py and test_summarizer_backfill.py"""
    # Before each test, ensure correct import paths
    # Remove any existing summarizer imports that might conflict
    mods_to_clean = [k for k in list(sys.modules.keys()) if k == 'summarizer' or k.startswith('summarizer.')]
    for mod in mods_to_clean:
        del sys.modules[mod]

    backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
    backend_path_abs = os.path.abspath(backend_path)
    sys_path_backup = None

    # Adjust sys.path based on which test is running
    if 'test_summarizer_backfill' in request.node.nodeid:
        # For backfill tests, prefer current dir so local summarizer/ package is found
        sys_path_backup = list(sys.path)
        sys.path[:] = [p for p in sys.path if p != '']
        sys.path.insert(0, '')
    elif 'test_summarizer.py' in request.node.nodeid:
        # For test_summarizer.py tests, ensure backend comes before current dir
        # so that 'from summarizer import ...' finds backend/summarizer.py not local package
        sys_path_backup = list(sys.path)
        # Remove both backend and empty string, then add backend first
        sys.path[:] = [p for p in sys.path if os.path.abspath(p) != backend_path_abs and p != '']
        sys.path.insert(0, backend_path_abs)

    yield

    # Restore sys.path if we modified it
    if sys_path_backup is not None:
        sys.path[:] = sys_path_backup

    # After each test, clean up modules again
    mods_to_clean = [k for k in list(sys.modules.keys()) if k == 'summarizer' or k.startswith('summarizer.')]
    for mod in mods_to_clean:
        del sys.modules[mod]

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from database import Base

TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:54322/postgres"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
