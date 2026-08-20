# Ymir HTTP Server Guide

> **SUPERSEDED.** This document describes the frozen Python implementation in
> `/ymir-legacy-py/`, and contains claims that have since been disproved by direct
> execution. It is kept for history. The normative definition of Ymir is
> [`/docs/spec/`](spec/), and the migration plan is [`/PLAN.md`](../PLAN.md).

Ymir provides a built-in HTTP server based on aiohttp, making it easy to create web APIs and services.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Server Creation](#server-creation)
3. [Request and Response](#request-and-response)
4. [Routing](#routing)
5. [Examples](#examples)

## Quick Start

```ymr
module simple_server

import stdlib.server

func handle_hello(request: Request) -> Response {
    return Response(200, "Hello, World!")
}

func main() {
    server = HTTPServer("0.0.0.0", 8080)
    server.route("/hello", handle_hello)
    server.run()
}
```

## Server Creation

### HTTPServer Constructor

```ymr
server = HTTPServer(host: string, port: int)
```

**Parameters:**
- `host`: The host to bind to (e.g., "0.0.0.0", "localhost")
- `port`: The port number to listen on

**Example:**
```ymr
# Listen on all interfaces, port 8080
server = HTTPServer("0.0.0.0", 8080)

# Listen on localhost only, port 3000
server = HTTPServer("127.0.0.1", 3000)
```

## Request and Response

### Request Object

The `Request` object contains information about the incoming HTTP request:

```ymr
class Request {
    method: string       # HTTP method (GET, POST, etc.)
    path: string        # Request path
    headers: map[string]string  # HTTP headers
    body: string        # Request body
    query_params: map[string]string  # Query parameters
}
```

**Methods:**
- `request.json()`: Parse body as JSON

**Example:**
```ymr
func handle_request(request: Request) -> Response {
    method = request.method
    path = request.path
    body = request.body
    
    print("Received " + method + " request to " + path)
    return Response(200, "OK")
}
```

### Response Object

The `Response` object represents the HTTP response:

```ymr
Response(status: int, body: string, headers: map[string]string)
```

**Parameters:**
- `status`: HTTP status code (200, 404, 500, etc.)
- `body`: Response body as a string
- `headers`: Optional HTTP headers (default: empty)

**Example:**
```ymr
# Simple text response
return Response(200, "Hello!")

# JSON response
json_body = '{"message": "Success", "data": [1, 2, 3]}'
return Response(200, json_body, {"Content-Type": "application/json"})

# HTML response
html = "<h1>Welcome</h1><p>Hello from Ymir!</p>"
return Response(200, html, {"Content-Type": "text/html"})

# Error response
return Response(404, "Not Found")
```

### JSON Response Helper

```ymr
Response.json(data: any, status: int)
```

Creates a JSON response with proper content type:

```ymr
data = {"name": "Ymir", "version": "0.1.0"}
return Response.json(data, 200)
```

## Routing

### Registering Routes

```ymr
server.route(path: string, handler: func, method: string)
```

**Parameters:**
- `path`: URL path to match
- `handler`: Function that handles the request
- `method`: HTTP method (default: "GET")

**Example:**
```ymr
server.route("/", handle_root, "GET")
server.route("/api/users", handle_users, "GET")
server.route("/api/users", create_user, "POST")
```

### Handler Function Signature

Handlers must accept a `Request` parameter and return a `Response`:

```ymr
func my_handler(request: Request) -> Response {
    # Handle request
    return Response(200, "OK")
}
```

## Examples

### Example 1: Simple API

```ymr
module simple_api

import stdlib.server

func handle_health(request: Request) -> Response {
    return Response(200, "OK")
}

func handle_version(request: Request) -> Response {
    json = '{"version": "1.0.0", "status": "running"}'
    return Response(200, json, {"Content-Type": "application/json"})
}

func main() {
    server = HTTPServer("0.0.0.0", 8080)
    server.route("/health", handle_health)
    server.route("/version", handle_version)
    
    print("API server running on http://0.0.0.0:8080")
    server.run()
}
```

### Example 2: Echo Server

```ymr
module echo_server

import stdlib.server

func handle_echo(request: Request) -> Response {
    body = request.body
    
    if body == "" {
        return Response(400, "No content to echo")
    }
    
    response_body = "Echo: " + body
    return Response(200, response_body)
}

func main() {
    server = HTTPServer("localhost", 3000)
    server.route("/echo", handle_echo, "POST")
    
    print("Echo server running on http://localhost:3000")
    print("Send POST requests to /echo")
    server.run()
}
```

### Example 3: RESTful API

```ymr
module rest_api

import stdlib.server

# In-memory storage
var users: array[string] = []

func handle_get_users(request: Request) -> Response {
    # Return list of users as JSON
    json = '{"users": ' + str(users) + '}'
    return Response(200, json, {"Content-Type": "application/json"})
}

func handle_create_user(request: Request) -> Response {
    # Parse request body (simplified)
    username = request.body
    
    if username == "" {
        return Response(400, "Username required")
    }
    
    # Add user
    users = users.append(username)
    
    response = '{"message": "User created", "username": "' + username + '"}'
    return Response(201, response, {"Content-Type": "application/json"})
}

func handle_root(request: Request) -> Response {
    html = "<h1>User API</h1><p>GET /users - List users</p><p>POST /users - Create user</p>"
    return Response(200, html, {"Content-Type": "text/html"})
}

func main() {
    server = HTTPServer("0.0.0.0", 8080)
    
    server.route("/", handle_root, "GET")
    server.route("/users", handle_get_users, "GET")
    server.route("/users", handle_create_user, "POST")
    
    print("REST API running on http://0.0.0.0:8080")
    print("Try: GET http://0.0.0.0:8080/users")
    server.run()
}
```

### Example 4: Server with Concurrency

Combine HTTP server with concurrent tasks:

```ymr
module concurrent_server

import stdlib.server

func background_worker(id: int, ch: any) {
    var i: int = 0
    while i < 5 {
        print("Background worker " + str(id) + " working...")
        ch <- i
        i = i + 1
    }
}

func handle_status(request: Request) -> Response {
    return Response(200, "Server is running with background tasks")
}

func main() {
    # Start background workers
    ch = make_channel(10)
    spawn background_worker(1, ch)
    spawn background_worker(2, ch)
    
    # Start HTTP server
    server = HTTPServer("0.0.0.0", 8080)
    server.route("/status", handle_status)
    
    print("Server with background tasks running on http://0.0.0.0:8080")
    server.run()
}
```

## HTTP Client

Ymir also provides HTTP client functionality:

```ymr
import stdlib.http

# GET request
status, body, headers = http_get("https://api.example.com/data")
print("Status: " + str(status))
print("Body: " + body)

# POST request with JSON
json_data = {"key": "value"}
status, body, headers = http_post("https://api.example.com/data", nil, json_data)
```

## Implementation Details

### Backend

- Built on `aiohttp` for async I/O
- Non-blocking request handling
- Automatic connection management

### Performance

- Handles multiple concurrent connections
- Efficient routing
- Low memory overhead

## Best Practices

### 1. Error Handling

Always handle errors in your handlers:

```ymr
func safe_handler(request: Request) -> Response {
    try {
        # Handle request
        result = process(request)
        return Response(200, result)
    } except Exception as e {
        print("Error: " + str(e))
        return Response(500, "Internal Server Error")
    }
}
```

### 2. Input Validation

Validate all input data:

```ymr
func handle_user(request: Request) -> Response {
    username = request.body
    
    if username == "" {
        return Response(400, "Username is required")
    }
    
    if len(username) > 50 {
        return Response(400, "Username too long")
    }
    
    # Process valid username
    return Response(200, "OK")
}
```

### 3. Use Appropriate Status Codes

- 200: OK
- 201: Created
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

### 4. Set Content-Type Headers

Always specify the content type:

```ymr
# JSON
return Response(200, json_data, {"Content-Type": "application/json"})

# HTML
return Response(200, html, {"Content-Type": "text/html"})

# Plain text
return Response(200, text, {"Content-Type": "text/plain"})
```

## Future Enhancements

Planned features for future releases:

- Middleware support
- Path parameters (e.g., `/users/:id`)
- Static file serving
- WebSocket support
- Request parsing helpers
- Authentication middleware
- CORS support

## See Also

- [Concurrency Guide](concurrency.md)
- [Syntax Guidelines](syntax_guidelines.md)
- [Matrix Operations](matrix_operations.md)

