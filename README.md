# MSG50: End-to-End Encrypted (E2EE) Chat Backend

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-5.1-green.svg)](https://www.djangoproject.com/)
[![Docker Compose](https://img.shields.io/badge/docker%20compose-supported-blue.svg)](#docker-compose-setup)
[![API Docs](https://img.shields.io/badge/OpenAPI%203.0-Swagger%20%2F%20ReDoc-orange.svg)](#api-documentation)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MSG50 is a secure, high-performance, real-time messaging backend engineered for **End-to-End Encrypted (E2EE) chat applications**. It acts as a zero-knowledge trust layer, routing encrypted binary files, handling E2EE key mapping exchanges, and managing offline queues without access to the message contents.

**FRONTEND REPOSITORY [HERE](https://github.com/DavidTimi1/Message_50)**

---

## 📖 Related Guides
*   **[Frontend Integration Guide](FRONTEND_INTEGRATION.md)**: Details HTTP REST endpoints, cookie authentication settings, CORS configurations, and Swagger UI parameters.
*   **[WebSocket Protocol Specifications](WEBSOCKET_PROTOCOL.md)**: Documents WebSocket handshake protocols, typing relays, status ACKs, and broadcast key schemas.
*   **[Project Changelog](CHANGELOG.md)**: Chronological catalog of additions, fixes, and release versions.

---

## 🛠️ Core Architectural Highlights

1.  **Zero-Knowledge Hybrid E2EE Routing**: Coordinates symmetric AES-encrypted payloads alongside individual asymmetric RSA-encrypted key maps. The server acts as a message courier without capability to read data packets.
2.  **HttpOnly JWT Session Management**: Protects against Cross-Site Scripting (XSS) token extraction by strictly transmitting JWT access and refresh tokens inside secure, encrypted `HttpOnly`, `SameSite=Lax` cookies.
3.  **Redis-Backed Real-Time Presence & Relays**: Implements distributed, multi-instance user presence checking, real-time status ACKs (Sent, Delivered, Read), typing status relays, and channel layer routing using Redis.
4.  **Resilient Store-and-Forward Queueing**: Stores messages and status adjustments in PostgreSQL when recipients are offline. Automatically flushes queued actions down the active WebSocket connection immediately upon connection handshake.
5.  **Redis-Backed Rate Limiting (Throttling)**: Implements custom throttles across auth routes, media uploads, E2EE public key retrievals, and feedback systems to protect against brute-force attacks.
6.  **Database composite indexing**: Messages table leverages indexing on `(receiver_id, created_at)` to support immediate, low-overhead fetching of offline queues.

---

## 🌐 System Architecture

![System Architecture](docs/assets/system_architecture.png)



---

## 🚀 Getting Started

### Prerequisites
*   Python 3.11, 3.12, or 3.13
*   Docker & Docker Compose (optional, recommended)
*   Redis server (if running locally without Docker)
*   PostgreSQL database (if running locally without Docker)

### Environment Configurations
Create a `.env` file in the root directory. Copy and populate the values from `.env.example`:
```bash
SECRET_KEY='your_production_secret_key'
DEBUG=True
USE_SQLITE=False
DATABASE_URL=postgres://user:password@localhost:5432/chatdb
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://localhost:6379/0
```

---

### Docker Compose Setup (Recommended)
You can launch the entire stack (Django ASGI server + PostgreSQL + Redis) with a single command:
```bash
docker compose up --build
```
This runs the application at `http://localhost:8000`.

---

### Manual Installation (Local Virtual Environment)

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/davidtimi1/msg50-be.git
    cd msg50-be
    ```

2.  **Create and Activate Virtual Environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run Database Migrations**:
    ```bash
    python manage.py migrate
    ```

5.  **Create a Superuser (optional)**:
    ```bash
    python manage.py createsuperuser
    ```

6.  **Start the Local Redis Service** (ensure local redis-server is running on `6379`).

7.  **Start the Development Server**:
    ```bash
    # Run the ASGI app locally with reload enabled
    chmod +x start.sh
    ./start.sh
    ```
    The application will bind to `0.0.0.0:8000`.

---

## 📑 API Documentation

MSG50 exposes interactive OpenAPI 3.0 documentation using `drf-spectacular`.

1.  Start your development server.
2.  Open your browser to:
    *   **Interactive Swagger UI**: `http://localhost:8000/api/schema/swagger-ui/`
    *   **ReDoc UI**: `http://localhost:8000/api/schema/redoc/`
    *   **Raw OpenAPI JSON Scheme**: `http://localhost:8000/api/schema/`

*For full instructions on endpoint request payloads and token refreshes, read the **[Frontend Integration Guide](FRONTEND_INTEGRATION.md)**.*

---

## 🔌 WebSocket Gateway

All real-time actions are managed through a unified WebSocket endpoint:

*   **Endpoint**: `ws://localhost:8000/ws/chat/`
*   **Authentication**: Automated during the WebSocket HTTP handshake by validating HTTP-only cookies (`access_token`).
*   **Heartbeat**: Client must send a `"type": "ping"` packet periodically (e.g. every 25 seconds). The server automatically extends the user's online session TTL in Redis on every ping and responds with a `"type": "pong"` frame.

*For frame schemas, broadcast rules, and status ACK formats, read the **[WebSocket Protocol Guide](WEBSOCKET_PROTOCOL.md)**.*

---

## 🧪 Running Tests

A comprehensive integration and unit test suite is included in `chat/tests.py`, covering authentication, E2EE key mapping APIs, file uploads, and rate limits.

Run tests using Django's test runner:
```bash
python manage.py test
```

---

## ⚠️ Production Configuration Notes

When deploying to production hosts (like Railway, Render, or Kubernetes):
1.  **Redis Protocols**: Modern Redis client libraries (like `redis-py` 5.x+) attempt to run the RESP3 protocol (`HELLO` command) on connection check health. If your production Redis requires a password (e.g. Upstash, Railway Internal), this handshake can trigger authentication errors. The `REDIS_URL` in `settings.py` is configured to append `?protocol=2` to enforce the highly compatible RESP2 connection standard.
2.  **Timeout Limits**: In production, ensure the `socket_timeout` under `CHANNEL_LAYERS` in `settings.py` is set to a value higher than the ASGI long-polling duration (currently set to `30` seconds) to avoid unexpected connection cycling under idle loops.
