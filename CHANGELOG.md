# Changelog

All notable changes to the MSG50 End-to-End Encrypted (E2EE) Chat Backend project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.2.0] - 2026-08-25

### Added
- **Multi-Recipient Broadcast (`action: "broadcast"`)**: Enabled 1-frame multi-recipient fan-out over WebSockets using Redis channel layers.
- **WebSocket Protocol Guide (`WEBSOCKET_PROTOCOL.md`)**: Comprehensive documentation covering connection handshake, ping/pong heartbeats, frame schemas, typing indicators, status ACKs, and E2EE hybrid cryptography workflows.
- **Real-Time Typing & Status ACK Relays**: Added `action: "typing"` and `action: "status-ack"` handling to `ChatConsumer`.
- **Heartbeat Handler**: Added `type: "ping"` $\rightarrow$ `{"type": "pong"}` frame responder.

---

## [2.1.0] - 2026-08-24

### Added
- **OpenAPI 3.0 / Swagger Documentation**: Integrated `drf-spectacular` schema generation with Swagger UI (`/api/schema/swagger-ui/`) and ReDoc (`/api/schema/redoc/`).
- **Postman Support**: Schema exported at `/api/schema/` for 1-click Postman collection import.
- **Throttling & Rate Limiting**: Added Redis-backed DRF throttle classes (`AuthRateThrottle`, `MediaUploadRateThrottle`, `PublicKeyRateThrottle`, `FeedbackRateThrottle`) across all sensitive API routes.
- **User Settings Endpoint**: Added `/api/v2/user/settings` (`GET` / `POST`) to retrieve and update user preferences (`profile_data` JSON field).
- **User Discovery Endpoint**: Added `/api/v2/user/search?q=<query>` for finding users by username.
- **Frontend Integration Guide**: Created `FRONTEND_INTEGRATION.md` documenting Postman setup, HttpOnly cookie auth flow, REST endpoints, and WebSocket payload frames.

### Security & Architecture
- **HttpOnly Cookie Standard**: Enforced HttpOnly, Secure, SameSite cookies (`access_token` and `refresh_token`) as the primary authentication mechanism across REST and WebSockets.
- **Redis Resilience**: Hardened `redis_client.py` with `ConnectionPool` timeouts and wrapped all `ChatConsumer` Redis operations in graceful error handling.
- **Memory Optimization**: Removed process-bound `threading.Timer` from `PrefetchLink` model to eliminate memory leaks and multi-instance concurrency issues.

---

## [2.0.0] - 2026-05-17

### Added
- **Redis Channel Layers**: Integrated `channels-redis` for real-time WebSocket message routing and user online presence checking (`user_online:<user_id>`).
- **Containerization**: Added `Dockerfile` and `compose.yaml` for multi-container deployment (App + Postgres + Redis).

### Changed
- **Database Schema**: Added `created_at` timestamp and database index on `receiver_id` in `Message` model for fast offline queue retrieval.

---

## [1.5.0] - 2025-05-12

### Added
- **HttpOnly Cookie Auth**: Added `CookieTokenObtainPairView`, `CookieTokenRefreshView`, and `CookieTokenVerifyView` to store JWT tokens in HttpOnly cookies.
- **Guest Sessions**: Introduced passwordless guest accounts (`is_guest=True`) with automated cleanup command (`delete_aged_guests`).
- **Encrypted Media Model**: Added `Media` model with `access_ids` ManyToMany permissions for encrypted media blob uploads and access control.

---

## [1.0.0] - 2024-11-01

### Added
- **Core Architecture**: Custom `User` model extending `AbstractUser` with UUID primary keys and `public_key` text field.
- **Offline Storage**: Store-and-forward `Message` queue model.
- **Feedback System**: `Feedback` model and admin views with email reply capabilities.
