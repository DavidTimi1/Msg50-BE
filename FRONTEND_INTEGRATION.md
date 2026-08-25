# MSG50 E2EE Chat - Frontend Integration & Postman Testing Guide

This guide provides everything the frontend development team needs to integrate with the **MSG50 E2EE Chat Backend**, including authentication flows, Postman setup, REST API reference, rate limits, and WebSocket real-time frame specifications.

> [!TIP]
> For full non-HTTP / WebSocket frame specifications, E2EE key envelope details, and real-time protocol flows, refer to **[`WEBSOCKET_PROTOCOL.md`](file:///c:/codes/django/msg50-be/WEBSOCKET_PROTOCOL.md)**.

---

## 1. Authentication & Cookie Setup

The backend relies on **HttpOnly, Secure, SameSite** cookies for authentication to protect against XSS attacks.

### Authentication Cookies
- **`access_token`**: Short-lived JWT access token (Valid for 3 days).
- **`refresh_token`**: Long-lived JWT refresh token (Valid for 7 days).

> [!NOTE]
> **Cross-Origin Requests**: Ensure your frontend HTTP client (e.g. `axios`, `fetch`) includes credentials in cross-origin requests:
> - Fetch: `{ credentials: 'include' }`
> - Axios: `axios.defaults.withCredentials = true;`

---

## 2. Postman Testing Setup

1. **Import OpenAPI Schema**:
   - Open Postman -> Click **Import**.
   - Select **Link** -> Paste: `http://localhost:8000/api/schema/`.
   - Postman will automatically generate a complete request collection with endpoints, request schemas, parameters, and status codes.

2. **Cookie Jar**:
   - In Postman, add `localhost` to the Cookie Jar so login responses automatically attach `access_token` and `refresh_token` to subsequent requests.

---

## 3. REST API Endpoints Overview

Base API URL: `/api/v2/`

### Authentication
| Endpoint | Method | Rate Limit | Description |
| :--- | :--- | :--- | :--- |
| `/api/v2/auth/register` | `POST` | `5/min` | Register new user (`username`, `email`, `password`) |
| `/api/v2/auth/login` | `POST` | `5/min` | Authenticate username/password (sets HttpOnly cookies) |
| `/api/v2/auth/refresh` | `POST` | `5/min` | Refresh `access_token` using `refresh_token` cookie |
| `/api/v2/auth/verify` | `POST` | `5/min` | Verify if active `access_token` cookie is valid |
| `/api/v2/auth/guest` | `POST` | `5/min` | Create anonymous guest session |

### User & Key Management
| Endpoint | Method | Rate Limit | Description |
| :--- | :--- | :--- | :--- |
| `/api/v2/user/<username>` | `GET` | `1000/day` | Get user profile details (`me` for logged in user) |
| `/api/v2/user/public-key/` | `GET` | `100/min` | Fetch public keys by `?username=u1&username=u2` |
| `/api/v2/user/public-key/` | `POST` | `100/min` | Set or update logged-in user's public key |
| `/api/v2/user/profile-edit` | `POST` | `20/min` | Update profile picture (`dp`) or `bio` |
| `/api/v2/user/settings` | `GET`/`POST`| `1000/day` | Read or update `profile_data` preferences JSON |
| `/api/v2/user/search` | `GET` | `1000/day` | Search users by username query (`?q=<query>`) |

### Encrypted Media
| Endpoint | Method | Rate Limit | Description |
| :--- | :--- | :--- | :--- |
| `/api/v2/media/upload/` | `POST` | `20/min` | Upload encrypted media file & recipient access list |
| `/api/v2/media/<uuid>` | `GET` | `1000/day` | Download encrypted binary blob (or `?metadata=true`) |

### System & Feedback
| Endpoint | Method | Rate Limit | Description |
| :--- | :--- | :--- | :--- |
| `/api/v2/healthz` | `GET` | None | Service health status check |
| `/api/v2/feedback/<project>`| `POST` | `10/hour` | Submit public feedback |

---

## 4. WebSocket Real-Time Protocol Overview

*(Detailed protocol specifications: **[`WEBSOCKET_PROTOCOL.md`](file:///c:/codes/django/msg50-be/WEBSOCKET_PROTOCOL.md)**)*.

- **Endpoint**: `ws://localhost:8000/ws/chat/`
- **Authentication**: Authenticates automatically during handshake using the `access_token` HttpOnly cookie.

### Key Actions Summary
- `ready`: Flush queued offline messages.
- `new-message`: Send single-recipient encrypted message.
- `broadcast`: Send multi-recipient group message with key map.
- `status-ack`: Send delivery/read status receipt (`d` or `r`).
- `typing`: Send typing indicator state (`isTyping: true/false`).
- `ping`: Keepalive heartbeat (receives `pong`).

---

## 5. Swagger UI & Interactive Documentation

Once the backend is running, open your browser to:
- **Interactive Swagger UI**: `http://localhost:8000/api/schema/swagger-ui/`
- **ReDoc Documentation**: `http://localhost:8000/api/schema/redoc/`
- **Raw OpenAPI 3 Schema**: `http://localhost:8000/api/schema/`
