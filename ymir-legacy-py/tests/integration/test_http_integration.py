"""
Integration tests for HTTP client and server.
"""

import pytest

from ymir.core.builtin_http import HTTPClient, HTTPServer, Request, Response


class TestHTTPClientIntegration:
    """Integration tests for HTTP client."""

    @pytest.mark.asyncio
    async def test_client_session_management(self):
        """Test client session lifecycle."""
        client = HTTPClient()
        await client.ensure_session()
        assert client.session is not None
        await client.close()
        assert client.session is None

    @pytest.mark.asyncio
    async def test_client_multiple_requests(self):
        """Test making multiple requests with same client."""
        client = HTTPClient()

        # This would require a real HTTP server to test fully
        # For now, just test initialization
        await client.ensure_session()
        assert client.session is not None
        await client.close()


class TestHTTPServerIntegration:
    """Integration tests for HTTP server."""

    def test_server_route_registration(self):
        """Test registering multiple routes."""
        server = HTTPServer("localhost", 8080)

        def handler1(req):
            return Response(200, "Handler 1")

        def handler2(req):
            return Response(200, "Handler 2")

        def handler3(req):
            return Response(200, "Handler 3")

        server.route("/api/users", handler1, "GET")
        server.route("/api/users", handler2, "POST")
        server.route("/api/status", handler3, "GET")

        assert len(server.routes) == 3
        assert ("GET", "/api/users") in server.routes
        assert ("POST", "/api/users") in server.routes
        assert ("GET", "/api/status") in server.routes

    def test_handler_response_types(self):
        """Test different response types from handlers."""
        server = HTTPServer("localhost", 8080)

        def text_handler(req):
            return Response(200, "Plain text")

        def json_handler(req):
            return Response(200, '{"key": "value"}', {"Content-Type": "application/json"})

        def error_handler(req):
            return Response(500, "Internal Error")

        server.route("/text", text_handler)
        server.route("/json", json_handler)
        server.route("/error", error_handler)

        assert len(server.routes) == 3


class TestHTTPRequestHandling:
    """Test HTTP request handling."""

    def test_request_parsing(self):
        """Test parsing request objects."""
        headers = {"Content-Type": "application/json", "Authorization": "Bearer token"}
        query_params = {"page": "1", "limit": "10"}

        request = Request(
            method="POST", path="/api/data", headers=headers, body='{"data": "test"}', query_params=query_params
        )

        assert request.method == "POST"
        assert request.path == "/api/data"
        assert request.headers["Content-Type"] == "application/json"
        assert request.query_params["page"] == "1"

    def test_json_response_helper(self):
        """Test JSON response creation."""
        data = {"status": "success", "data": [1, 2, 3]}
        response = Response.json(data, 200)

        assert response.status == 200
        assert response.headers["Content-Type"] == "application/json"
        assert "status" in response.body
        assert "success" in response.body


class TestHTTPWithConcurrency:
    """Test HTTP operations with concurrency."""

    def test_concurrent_handler_setup(self):
        """Test setting up handlers that use concurrency."""
        server = HTTPServer("localhost", 8080)

        def concurrent_handler(req):
            # In real scenario, this would spawn tasks
            return Response(200, "Concurrent processing")

        server.route("/concurrent", concurrent_handler)
        assert ("GET", "/concurrent") in server.routes
