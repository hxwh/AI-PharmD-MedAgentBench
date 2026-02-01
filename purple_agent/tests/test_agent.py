"""Tests for Purple Agent."""

import pytest
import httpx


@pytest.mark.asyncio
async def test_agent_card(agent_url):
    """Test that the agent card is accessible."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{agent_url}/.well-known/agent-card.json")
        assert response.status_code == 200
        
        card = response.json()
        assert "name" in card
        assert "description" in card


@pytest.mark.asyncio
async def test_agent_root(agent_url):
    """Test the root endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(agent_url)
        assert response.status_code == 200
