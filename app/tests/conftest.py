import os
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

# Mark the environment as test
os.environ["ENVIRONMENT"] = "TEST"

@pytest_asyncio.fixture
async def client():
    """Provides async test client for FastAPI"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
