"""Smoke test: verify TokenRouter responds."""
import os, pytest
from unittest.mock import patch, MagicMock

def test_route_returns_string():
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = "test output"
    with patch("agent.router.get_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = mock_resp
        from agent.router import route, RouteType
        result = route(RouteType.FAST, [{"role": "user", "content": "hello"}])
        assert isinstance(result, str)
