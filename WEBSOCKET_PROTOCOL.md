# MSG50 E2EE Chat - Complete WebSocket Protocol & Non-HTTP Specification

This document serves as the authoritative reference for real-time WebSocket communication and End-to-End Encryption (E2EE) protocols in the **MSG50 Chat Application**.

---

## 1. Connection & Handshake Architecture

### WebSocket URL
```
ws://<hostname>:8000/ws/chat/
```
*(Use `wss://` in production).*

### Authentication Protocol
WebSocket connections authenticate during the **HTTP Upgrade Handshake**:
- Browsers automatically send the HttpOnly `access_token` cookie in the request headers.
- `TokenAuthMiddleware` verifies the JWT `access_token` and attaches the user object to the connection scope.
- **Unauthorized Handshake**: If `access_token` is missing or invalid, the server closes the socket connection with error code `400 ("User is not authenticated")`.

---

## 2. Connection Lifecycle & Heartbeat

### Connection Lifecycle Sequence
```
Client                          Server
  | --- HTTP Upgrade Request ---> | (Authenticates access_token cookie)
  | <--- 101 Switching Protocols -| (Connection accepted)
  |                               |
  | --- { "action": "ready" } --->| (Flushes queued offline messages)
  | <--- [Queued Messages Frame] -|
  |                               |
  | --- { "type": "ping" } ------>| (Interval: Every 25 seconds)
  | <--- { "type": "pong" } ------|
```

---

## 3. Client-to-Server Event Dictionary

All client frames are JSON strings sent via `socket.send(JSON.stringify(payload))`.

### A. Flush Queued Messages (`action: "ready"`)
Sent immediately after `onopen` to request delivery of any messages stored while offline.
```json
{
  "action": "ready"
}
```

### B. Heartbeat Ping (`type: "ping"`)
Sent every 25 seconds to keep the TCP connection active and verify socket state.
```json
{
  "type": "ping"
}
```

### C. Direct Encrypted Message (`action: "new-message"`)
Sends an encrypted payload to a single recipient.
```json
{
  "action": "new-message",
  "receiverID": "b3e2a149-1234-4567-89ab-cdef01234567",
  "id": "client-message-uuid-v4",
  "data": {
    "iv": "base64-12-byte-aes-gcm-iv",
    "encryptedData": "base64-aes-gcm-ciphertext",
    "key": "base64-rsa-encrypted-symmetric-key",
    "file": {
      "src": "media-access-uuid",
      "metadata": { "name": "document.pdf", "size": 102400 }
    }
  }
}
```

### D. Multi-Recipient Broadcast (`action: "broadcast"`)
Sends **1 WebSocket frame** for multi-recipient group or broadcast chats. The server fans out individual frames to each recipient via Redis.
```json
{
  "action": "broadcast",
  "id": "client-message-uuid-v4",
  "data": {
    "iv": "base64-12-byte-aes-gcm-iv",
    "encryptedData": "base64-aes-gcm-ciphertext",
    "file": {
      "src": "media-access-uuid",
      "metadata": { "name": "image.png", "size": 51200 }
    }
  },
  "keys": {
    "recipient-uuid-1": "base64-rsa-encrypted-key-for-user-1",
    "recipient-uuid-2": "base64-rsa-encrypted-key-for-user-2"
  }
}
```

### E. Status ACK Receipt (`action: "status-ack"`)
Informs the server/sender of a message status transition (`"d"` = Delivered, `"r"` = Read).
```json
{
  "action": "status-ack",
  "receiverID": "sender-user-uuid",
  "id": "target-message-uuid",
  "status": "r"
}
```

### F. Typing State Relay (`action: "typing"`)
Sends real-time typing state to the target user.
```json
{
  "action": "typing",
  "receiverID": "target-user-uuid",
  "isTyping": true
}
```

---

## 4. Server-to-Client Event Dictionary

### A. Heartbeat Pong (`type: "pong"`)
Server response to client ping frame.
```json
{
  "type": "pong"
}
```

### B. Incoming Message Frame (`type: "new-message"`)
Delivered to recipient when a new message is received.
```json
{
  "type": "new-message",
  "data": {
    "id": "client-message-uuid",
    "data": {
      "iv": "base64-12-byte-aes-gcm-iv",
      "encryptedData": "base64-aes-gcm-ciphertext",
      "key": "base64-rsa-encrypted-symmetric-key",
      "file": {
        "src": "media-access-uuid",
        "metadata": { "name": "document.pdf", "size": 102400 }
      }
    }
  }
}
```

### C. Status Change Event (`type: "status-change"`)
Pushed to sender when recipient receives or reads a message.
```json
{
  "type": "status-change",
  "data": {
    "action": "status",
    "message_id": "target-message-uuid",
    "data": {
      "status": "r",
      "senderID": "recipient-user-uuid"
    }
  }
}
```

### D. Typing Status Relay (`type: "typing-status"`)
Pushed to user when their chat partner is typing.
```json
{
  "type": "typing-status",
  "senderID": "partner-user-uuid",
  "isTyping": true
}
```

---

## 5. End-to-End Encryption (E2EE) Hybrid Cryptographic Architecture

MSG50 uses a **Hybrid Encryption Model** combining **RSA-OAEP (2048-bit)** and **AES-GCM (256-bit)**:

```
[Sender Device]
  1. Generate random AES-256 key (symmetricKey)
  2. Encrypt message body with AES-GCM (produces encryptedData + iv)
  3. Fetch recipient's RSA Public Key from GET /api/v2/user/public-key/
  4. Encrypt symmetricKey using RSA-OAEP (produces encryptedKey)
  5. Send { iv, encryptedData, key: encryptedKey } via WebSocket

[Recipient Device]
  1. Receive { iv, encryptedData, key: encryptedKey } frame via WebSocket
  2. Retrieve user's RSA Private Key from IndexedDB
  3. Decrypt encryptedKey with RSA-OAEP (recovers symmetricKey)
  4. Decrypt encryptedData with AES-GCM (recovers plaintext message)
```

---

## 6. Encrypted Media Attachment Workflow

1. **Client-Side Media Encryption**:
   - Generate AES-256 symmetric key.
   - Encrypt binary file buffer using `AES-GCM` (produces `encryptedFileData` and `iv`).
2. **HTTP Media Upload**:
   - Upload encrypted binary blob to `POST /api/v2/media/upload/` with metadata containing allowed recipient UUIDs.
   - Receive response: `{ "src": "<media_uuid>" }`.
3. **WebSocket Reference Relay**:
   - Attach `{ "src": "<media_uuid>", "metadata": { ... } }` inside the WebSocket message payload.
4. **Recipient Media Retrieval**:
   - Recipient fetches binary payload from `GET /api/v2/media/<media_uuid>`.
   - Decrypts binary stream using the decrypted `symmetricKey`.
