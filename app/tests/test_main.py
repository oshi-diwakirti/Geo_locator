import pytest

@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test public root endpoint"""
    response = await client.get("/health", follow_redirects=True)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_secure_endpoint_unauthorized(client):
    """Test protected endpoint without token"""
    response = await client.get("/secure-data")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"
