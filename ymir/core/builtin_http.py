"""
Built-in HTTP client and server functionality for Ymir.

Uses aiohttp for async HTTP operations.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger("ymir.http")


class Request:
    """HTTP Request object."""

    def __init__(self, method: str, path: str, headers: Dict[str, str], body: str, query_params: Dict[str, str]):
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body
        self.query_params = query_params

    def json(self) -> Any:
        """Parse request body as JSON."""
        try:
            return json.loads(self.body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in request body: {e}")

    def __repr__(self) -> str:
        return f"Request(method={self.method}, path={self.path})"


class Response:
    """HTTP Response object."""

    def __init__(self, status: int = 200, body: str = "", headers: Optional[Dict[str, str]] = None):
        self.status = status
        self.body = body
        self.headers = headers or {}

    @classmethod
    def json(cls, data: Any, status: int = 200):
        """Create a JSON response."""
        return cls(status=status, body=json.dumps(data), headers={"Content-Type": "application/json"})

    def __repr__(self) -> str:
        return f"Response(status={self.status}, body_len={len(self.body)})"


class HTTPClient:
    """Async HTTP client using aiohttp."""

    def __init__(self):
        self.session = None

    async def ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None:
            try:
                import aiohttp

                self.session = aiohttp.ClientSession()
            except ImportError:
                raise ImportError("aiohttp is required for HTTP client functionality")

    async def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> Tuple[int, str, Dict[str, str]]:
        """
        Perform HTTP GET request.

        Args:
            url: The URL to request
            headers: Optional headers dict

        Returns:
            Tuple of (status_code, body, response_headers)
        """
        await self.ensure_session()
        logger.info(f"HTTP GET {url}")

        try:
            async with self.session.get(url, headers=headers or {}) as response:
                body = await response.text()
                response_headers = dict(response.headers)
                logger.debug(f"HTTP GET {url} -> {response.status}")
                return response.status, body, response_headers
        except Exception as e:
            logger.error(f"HTTP GET {url} failed: {e}")
            raise

    async def post(
        self,
        url: str,
        data: Optional[str] = None,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, str, Dict[str, str]]:
        """
        Perform HTTP POST request.

        Args:
            url: The URL to request
            data: Optional string data to send
            json_data: Optional JSON data to send
            headers: Optional headers dict

        Returns:
            Tuple of (status_code, body, response_headers)
        """
        await self.ensure_session()
        logger.info(f"HTTP POST {url}")

        kwargs = {"headers": headers or {}}
        if json_data is not None:
            kwargs["json"] = json_data
        elif data is not None:
            kwargs["data"] = data

        try:
            async with self.session.post(url, **kwargs) as response:
                body = await response.text()
                response_headers = dict(response.headers)
                logger.debug(f"HTTP POST {url} -> {response.status}")
                return response.status, body, response_headers
        except Exception as e:
            logger.error(f"HTTP POST {url} failed: {e}")
            raise

    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None


class HTTPServer:
    """Async HTTP server using aiohttp."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.routes: Dict[Tuple[str, str], Callable] = {}  # (method, path) -> handler
        self.app = None
        self.runner = None
        self.site = None

    def route(self, path: str, handler: Callable, method: str = "GET"):
        """
        Register a route handler.

        Args:
            path: The URL path
            handler: Function to handle requests (takes Request, returns Response)
            method: HTTP method (GET, POST, etc.)
        """
        key = (method.upper(), path)
        self.routes[key] = handler
        logger.info(f"Registered route: {method} {path}")

    async def _handle_request(self, aiohttp_request):
        """Internal handler that converts aiohttp request to Ymir Request."""
        try:
            import aiohttp
        except ImportError:
            raise ImportError("aiohttp is required for HTTP server functionality")

        method = aiohttp_request.method
        path = aiohttp_request.path
        headers = dict(aiohttp_request.headers)
        body = await aiohttp_request.text()
        query_params = dict(aiohttp_request.query)

        # Create Ymir Request object
        request = Request(method, path, headers, body, query_params)

        # Find matching route
        key = (method, path)
        if key in self.routes:
            handler = self.routes[key]
            try:
                # Call the handler
                response = handler(request)

                # If handler returns a simple value, wrap it in a Response
                if not isinstance(response, Response):
                    response = Response(200, str(response))

                # Convert Ymir Response to aiohttp response
                return aiohttp.web.Response(status=response.status, text=response.body, headers=response.headers)
            except Exception as e:
                logger.error(f"Error in handler for {method} {path}: {e}")
                return aiohttp.web.Response(status=500, text=f"Internal Server Error: {str(e)}")
        else:
            logger.warning(f"No route found for {method} {path}")
            return aiohttp.web.Response(status=404, text="Not Found")

    async def start(self):
        """Start the HTTP server."""
        try:
            import aiohttp.web
        except ImportError:
            raise ImportError("aiohttp is required for HTTP server functionality")

        logger.info(f"Starting HTTP server on {self.host}:{self.port}")

        # Create aiohttp application
        self.app = aiohttp.web.Application()

        # Register all routes
        for (method, path), handler in self.routes.items():
            self.app.router.add_route(method, path, self._handle_request)

        # Setup and start runner
        self.runner = aiohttp.web.AppRunner(self.app)
        await self.runner.setup()
        self.site = aiohttp.web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        logger.info(f"HTTP server running on http://{self.host}:{self.port}")

    async def stop(self):
        """Stop the HTTP server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("HTTP server stopped")

    def run(self):
        """Run the server (blocking)."""
        asyncio.run(self._run_server())

    async def _run_server(self):
        """Internal method to run the server."""
        await self.start()
        try:
            # Keep running forever
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.stop()


# Global HTTP client instance
_http_client: Optional[HTTPClient] = None


def get_http_client() -> HTTPClient:
    """Get or create the global HTTP client."""
    global _http_client
    if _http_client is None:
        _http_client = HTTPClient()
    return _http_client
