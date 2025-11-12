"""
Tests for Ymir HTTP client and server.
"""

import pytest

from ymir.core.builtin_http import HTTPClient, HTTPServer, Request, Response


class TestRequest:
    """Test Request object."""

    def test_request_creation(self):
        """Test creating a request."""
        req = Request("GET", "/test", {"Content-Type": "text/plain"}, "body", {})
        assert req.method == "GET"
        assert req.path == "/test"
        assert req.body == "body"

    def test_request_json(self):
        """Test JSON parsing."""
        req = Request("POST", "/api", {}, '{"key": "value"}', {})
        data = req.json()
        assert data == {"key": "value"}

    def test_request_json_invalid(self):
        """Test invalid JSON."""
        req = Request("POST", "/api", {}, "not json", {})
        with pytest.raises(ValueError, match="Invalid JSON"):
            req.json()


class TestResponse:
    """Test Response object."""

    def test_response_creation(self):
        """Test creating a response."""
        resp = Response(200, "OK")
        assert resp.status == 200
        assert resp.body == "OK"
        assert resp.headers == {}

    def test_response_with_headers(self):
        """Test response with headers."""
        headers = {"Content-Type": "application/json"}
        resp = Response(200, '{"data": "test"}', headers)
        assert resp.status == 200
        assert resp.headers["Content-Type"] == "application/json"

    def test_response_json_helper(self):
        """Test JSON response helper."""
        data = {"message": "success", "code": 200}
        resp = Response.json(data, 200)
        assert resp.status == 200
        assert resp.headers["Content-Type"] == "application/json"
        assert '"message": "success"' in resp.body


class TestHTTPServer:
    """Test HTTPServer."""

    def test_server_creation(self):
        """Test creating a server."""
        server = HTTPServer("localhost", 8080)
        assert server.host == "localhost"
        assert server.port == 8080
        assert len(server.routes) == 0

    def test_route_registration(self):
        """Test registering routes."""
        server = HTTPServer("localhost", 8080)

        def handler(req):
            return Response(200, "OK")

        server.route("/test", handler, "GET")
        assert ("GET", "/test") in server.routes

    def test_multiple_routes(self):
        """Test registering multiple routes."""
        server = HTTPServer("localhost", 8080)

        def handler1(req):
            return Response(200, "Handler 1")

        def handler2(req):
            return Response(200, "Handler 2")

        server.route("/api/users", handler1, "GET")
        server.route("/api/users", handler2, "POST")

        assert len(server.routes) == 2
        assert ("GET", "/api/users") in server.routes
        assert ("POST", "/api/users") in server.routes


class TestHTTPClient:
    """Test HTTPClient."""

    def test_client_creation(self):
        """Test creating a client."""
        client = HTTPClient()
        assert client.session is None

    @pytest.mark.asyncio
    async def test_ensure_session(self):
        """Test session creation."""
        client = HTTPClient()
        await client.ensure_session()
        assert client.session is not None
        await client.close()
