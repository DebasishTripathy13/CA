# API Specification - AWS Certificate Decision Assistant

## API Overview

**Base URL:** `https://api.cert-assistant.example.com/v1`  
**Protocol:** HTTPS only  
**Authentication:** JWT Bearer Token (from SSO)  
**Content-Type:** `application/json`  
**API Style:** RESTful  

## Authentication

All API endpoints (except health check) require authentication via JWT token obtained from SSO login.

### Authentication Header

```http
Authorization: Bearer <jwt_token>
```

### Error Responses

All endpoints return consistent error format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {},
    "timestamp": "2024-01-15T10:30:00Z",
    "trace_id": "uuid-trace-id"
  }
}
```

**Common Error Codes:**
- `401` - Unauthorized (missing or invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error

---

## Endpoints

### 1. Authentication

#### POST /auth/login

Initiate SSO login flow.

**Request:**
```http
POST /auth/login
Content-Type: application/json

{
  "provider": "azure_ad",
  "redirect_uri": "https://app.cert-assistant.example.com/callback"
}
```

**Response:**
```json
{
  "authorization_url": "https://login.microsoftonline.com/...",
  "state": "random-state-token"
}
```

#### POST /auth/callback

Complete SSO authentication and receive JWT token.

**Request:**
```http
POST /auth/callback
Content-Type: application/json

{
  "code": "authorization-code",
  "state": "random-state-token"
}
```

**Response:**
```json
{
  "access_token": "jwt-token",
  "refresh_token": "refresh-token",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "John Doe",
    "role": "user"
  }
}
```

#### POST /auth/refresh

Refresh expired access token.

**Request:**
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "refresh-token"
}
```

**Response:**
```json
{
  "access_token": "new-jwt-token",
  "expires_in": 3600
}
```

#### POST /auth/logout

Logout and invalidate tokens.

**Request:**
```http
POST /auth/logout
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

---

### 2. Users

#### GET /users/me

Get current user profile.

**Request:**
```http
GET /users/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "display_name": "John Doe",
  "department": "IT",
  "role": "user",
  "last_login_at": "2024-01-15T10:00:00Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### PATCH /users/me

Update current user profile.

**Request:**
```http
PATCH /users/me
Authorization: Bearer <token>
Content-Type: application/json

{
  "display_name": "John A. Doe",
  "department": "Engineering"
}
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "John A. Doe",
  "department": "Engineering",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

### 3. Recommendation Engine

#### POST /recommendations/evaluate

Submit questionnaire answers and get CA recommendation.

**Request:**
```http
POST /recommendations/evaluate
Authorization: Bearer <token>
Content-Type: application/json

{
  "service_type": "web_server",
  "publicly_accessible": "yes",
  "expected_lifespan": "1_to_2_years",
  "browser_trust_required": "yes",
  "environment_type": "production",
  "certificate_count": "single",
  "domain_type": "wildcard",
  "criticality_level": "high",
  "compliance_requirements": ["PCI_DSS", "SOC2"],
  "key_size_preference": "RSA_2048",
  "renewal_preference": "automatic"
}
```

**Response:**
```json
{
  "recommendation": {
    "ca_type": "public",
    "confidence": 0.95,
    "reason": "Public CA is recommended because the service requires browser trust and is publicly accessible.",
    "public_ca_options": [
      {
        "name": "DigiCert",
        "url": "https://www.digicert.com",
        "features": ["EV certificates", "Wildcard support", "24/7 support"]
      },
      {
        "name": "Let's Encrypt",
        "url": "https://letsencrypt.org",
        "features": ["Free", "Automated renewal", "90-day validity"]
      }
    ]
  },
  "allow_override": true,
  "questionnaire_id": "uuid"
}
```

**Alternative Response (Internal CA):**
```json
{
  "recommendation": {
    "ca_type": "internal",
    "confidence": 0.88,
    "reason": "Internal CA is recommended for internal-only services without browser trust requirement.",
    "next_steps": "Proceed to certificate request form"
  },
  "allow_override": true,
  "questionnaire_id": "uuid"
}
```

---

### 4. Certificate Requests

#### POST /requests

Create a new certificate request.

**Request:**
```http
POST /requests
Authorization: Bearer <token>
Content-Type: application/json

{
  "common_name": "app.example.com",
  "organization": "Example Corp",
  "organizational_unit": "Engineering",
  "locality": "Seattle",
  "state_province": "WA",
  "country": "US",
  "email_address": "admin@example.com",
  "subject_alternative_names": ["www.example.com", "api.example.com"],
  "certificate_type": "web_server",
  "key_algorithm": "RSA_2048",
  "validity_period_days": 365,
  "csr_type": "generated",
  "csr_content": "-----BEGIN CERTIFICATE REQUEST-----\n...",
  "business_justification": "SSL certificate for new production web application",
  "department": "Engineering",
  "cost_center": "CC-1234",
  "project_code": "PROJ-567",
  "approver_email": "manager@example.com",
  "questionnaire_id": "uuid",
  "override_requested": false
}
```

**Response:**
```json
{
  "id": "uuid",
  "request_number": "REQ-20240115-00001",
  "status": "draft",
  "common_name": "app.example.com",
  "certificate_type": "web_server",
  "created_at": "2024-01-15T10:30:00Z",
  "estimated_issuance_time": "2-3 business days"
}
```

#### GET /requests

List certificate requests (paginated).

**Request:**
```http
GET /requests?page=1&per_page=20&status=pending_approval&sort=created_at&order=desc
Authorization: Bearer <token>
```

**Query Parameters:**
- `page` (integer): Page number (default: 1)
- `per_page` (integer): Results per page (default: 20, max: 100)
- `status` (string): Filter by status
- `sort` (string): Sort field (created_at, updated_at, common_name)
- `order` (string): Sort order (asc, desc)
- `search` (string): Search by common name or request number

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "request_number": "REQ-20240115-00001",
      "common_name": "app.example.com",
      "certificate_type": "web_server",
      "status": "pending_approval",
      "created_at": "2024-01-15T10:00:00Z",
      "submitted_at": "2024-01-15T10:30:00Z",
      "approver": {
        "email": "manager@example.com",
        "name": "Jane Smith"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 45,
    "total_pages": 3
  }
}
```

#### GET /requests/{id}

Get details of a specific request.

**Request:**
```http
GET /requests/uuid
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "uuid",
  "request_number": "REQ-20240115-00001",
  "common_name": "app.example.com",
  "organization": "Example Corp",
  "organizational_unit": "Engineering",
  "locality": "Seattle",
  "state_province": "WA",
  "country": "US",
  "email_address": "admin@example.com",
  "subject_alternative_names": ["www.example.com", "api.example.com"],
  "certificate_type": "web_server",
  "key_algorithm": "RSA_2048",
  "validity_period_days": 365,
  "csr_type": "generated",
  "business_justification": "SSL certificate for new production web application",
  "department": "Engineering",
  "status": "pending_approval",
  "submitted_at": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "requester": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "John Doe"
  },
  "approver": {
    "id": "uuid",
    "email": "manager@example.com",
    "display_name": "Jane Smith"
  },
  "recommendation": {
    "ca_type": "internal",
    "override_requested": false
  }
}
```

#### PATCH /requests/{id}

Update a draft request.

**Request:**
```http
PATCH /requests/uuid
Authorization: Bearer <token>
Content-Type: application/json

{
  "common_name": "app2.example.com",
  "business_justification": "Updated justification"
}
```

**Response:**
```json
{
  "id": "uuid",
  "request_number": "REQ-20240115-00001",
  "common_name": "app2.example.com",
  "status": "draft",
  "updated_at": "2024-01-15T11:00:00Z"
}
```

#### POST /requests/{id}/submit

Submit a draft request for approval.

**Request:**
```http
POST /requests/uuid/submit
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "uuid",
  "request_number": "REQ-20240115-00001",
  "status": "pending_approval",
  "submitted_at": "2024-01-15T11:00:00Z",
  "approver": {
    "email": "manager@example.com",
    "name": "Jane Smith"
  }
}
```

#### DELETE /requests/{id}

Cancel a request (only draft or pending approval).

**Request:**
```http
DELETE /requests/uuid
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Request cancelled successfully",
  "request_number": "REQ-20240115-00001"
}
```

#### GET /requests/{id}/csr

Download CSR for a request.

**Request:**
```http
GET /requests/uuid/csr
Authorization: Bearer <token>
```

**Response:**
```
-----BEGIN CERTIFICATE REQUEST-----
MIICvDCCAaQCAQAwdzELMAkGA1UEBhMCVVMxCzAJBgNVBAgMAldBMRAwDgYDVQQH
...
-----END CERTIFICATE REQUEST-----
```

---

### 5. Approvals

#### GET /approvals

List pending approvals (approvers only).

**Request:**
```http
GET /approvals?status=pending&page=1&per_page=20
Authorization: Bearer <token>
```

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "request": {
        "id": "uuid",
        "request_number": "REQ-20240115-00001",
        "common_name": "app.example.com",
        "certificate_type": "web_server"
      },
      "requester": {
        "email": "user@example.com",
        "display_name": "John Doe"
      },
      "status": "pending",
      "created_at": "2024-01-15T10:30:00Z",
      "pending_hours": 2
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 5,
    "total_pages": 1
  }
}
```

#### POST /approvals/{id}/approve

Approve a certificate request.

**Request:**
```http
POST /approvals/uuid/approve
Authorization: Bearer <token>
Content-Type: application/json

{
  "comments": "Approved for production deployment"
}
```

**Response:**
```json
{
  "id": "uuid",
  "status": "approved",
  "decision": "approve",
  "comments": "Approved for production deployment",
  "decided_at": "2024-01-15T12:00:00Z",
  "request": {
    "id": "uuid",
    "request_number": "REQ-20240115-00001",
    "status": "approved"
  }
}
```

#### POST /approvals/{id}/reject

Reject a certificate request.

**Request:**
```http
POST /approvals/uuid/reject
Authorization: Bearer <token>
Content-Type: application/json

{
  "comments": "Insufficient business justification. Please provide more details."
}
```

**Response:**
```json
{
  "id": "uuid",
  "status": "rejected",
  "decision": "reject",
  "comments": "Insufficient business justification. Please provide more details.",
  "decided_at": "2024-01-15T12:00:00Z",
  "request": {
    "id": "uuid",
    "request_number": "REQ-20240115-00001",
    "status": "rejected"
  }
}
```

#### POST /approvals/{id}/delegate

Delegate approval to another approver.

**Request:**
```http
POST /approvals/uuid/delegate
Authorization: Bearer <token>
Content-Type: application/json

{
  "delegate_to_email": "other.manager@example.com",
  "delegation_reason": "Out of office this week"
}
```

**Response:**
```json
{
  "id": "uuid",
  "status": "delegated",
  "delegated_to": {
    "email": "other.manager@example.com",
    "display_name": "Mike Johnson"
  },
  "delegation_reason": "Out of office this week"
}
```

---

### 6. Certificates

#### GET /certificates

List certificates for the current user.

**Request:**
```http
GET /certificates?status=active&page=1&per_page=20&expiring_days=30
Authorization: Bearer <token>
```

**Query Parameters:**
- `status` (string): Filter by status (active, revoked, expired)
- `expiring_days` (integer): Show certificates expiring within N days
- `page`, `per_page`: Pagination

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "serial_number": "1A2B3C4D5E6F",
      "common_name": "app.example.com",
      "subject_dn": "CN=app.example.com, O=Example Corp, C=US",
      "issuer_dn": "CN=Internal CA, O=Example Corp, C=US",
      "valid_from": "2024-01-15T00:00:00Z",
      "valid_to": "2025-01-15T00:00:00Z",
      "status": "active",
      "days_until_expiry": 365,
      "expiry_status": "valid",
      "key_algorithm": "RSA_2048",
      "request_number": "REQ-20240115-00001",
      "issued_at": "2024-01-15T14:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 8,
    "total_pages": 1
  }
}
```

#### GET /certificates/{id}

Get details of a specific certificate.

**Request:**
```http
GET /certificates/uuid
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "uuid",
  "serial_number": "1A2B3C4D5E6F",
  "thumbprint_sha256": "abc123...",
  "common_name": "app.example.com",
  "subject_dn": "CN=app.example.com, O=Example Corp, C=US",
  "issuer_dn": "CN=Internal CA, O=Example Corp, C=US",
  "subject_alternative_names": ["www.example.com", "api.example.com"],
  "valid_from": "2024-01-15T00:00:00Z",
  "valid_to": "2025-01-15T00:00:00Z",
  "status": "active",
  "key_algorithm": "RSA_2048",
  "key_size": 2048,
  "signature_algorithm": "SHA256withRSA",
  "download_count": 3,
  "first_downloaded_at": "2024-01-15T14:05:00Z",
  "last_downloaded_at": "2024-01-15T16:00:00Z",
  "request": {
    "id": "uuid",
    "request_number": "REQ-20240115-00001"
  },
  "owner": {
    "email": "user@example.com",
    "display_name": "John Doe"
  }
}
```

#### GET /certificates/{id}/download

Download certificate file.

**Request:**
```http
GET /certificates/uuid/download?format=pem&include_chain=true
Authorization: Bearer <token>
```

**Query Parameters:**
- `format` (string): File format (pem, der, pkcs12) - default: pem
- `include_chain` (boolean): Include certificate chain - default: true

**Response:**
```
Content-Type: application/x-pem-file
Content-Disposition: attachment; filename="app.example.com.pem"

-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKJ...
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
[Intermediate CA certificate]
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
[Root CA certificate]
-----END CERTIFICATE-----
```

#### GET /certificates/{id}/private-key

Download private key (if generated by system, one-time download).

**Request:**
```http
GET /certificates/uuid/private-key?password=encryption-password
Authorization: Bearer <token>
```

**Response:**
```
Content-Type: application/x-pem-file
Content-Disposition: attachment; filename="app.example.com.key"

-----BEGIN ENCRYPTED PRIVATE KEY-----
MIIFHDBOBgkqhkiG9w0BBQ0wQT...
-----END ENCRYPTED PRIVATE KEY-----
```

**Error Response (already downloaded):**
```json
{
  "error": {
    "code": "PRIVATE_KEY_ALREADY_DOWNLOADED",
    "message": "Private key was already downloaded and cannot be retrieved again for security reasons"
  }
}
```

#### POST /certificates/{id}/revoke

Request certificate revocation.

**Request:**
```http
POST /certificates/uuid/revoke
Authorization: Bearer <token>
Content-Type: application/json

{
  "reason_code": "key_compromise",
  "reason_text": "Private key was exposed in public repository"
}
```

**Reason Codes:**
- `unspecified`
- `key_compromise`
- `ca_compromise`
- `affiliation_changed`
- `superseded`
- `cessation_of_operation`
- `certificate_hold`

**Response:**
```json
{
  "id": "uuid",
  "certificate_id": "uuid",
  "reason_code": "key_compromise",
  "reason_text": "Private key was exposed in public repository",
  "status": "pending_approval",
  "revoked_at": "2024-01-15T15:00:00Z"
}
```

---

### 7. Dashboard & Statistics

#### GET /dashboard

Get dashboard summary for current user.

**Request:**
```http
GET /dashboard
Authorization: Bearer <token>
```

**Response:**
```json
{
  "summary": {
    "total_requests": 15,
    "pending_requests": 3,
    "active_certificates": 8,
    "expiring_soon": 2,
    "pending_approvals": 5
  },
  "recent_requests": [
    {
      "id": "uuid",
      "request_number": "REQ-20240115-00001",
      "common_name": "app.example.com",
      "status": "issued",
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "expiring_certificates": [
    {
      "id": "uuid",
      "common_name": "old.example.com",
      "valid_to": "2024-02-15T00:00:00Z",
      "days_until_expiry": 30
    }
  ]
}
```

#### GET /statistics (Admin only)

Get system-wide statistics.

**Request:**
```http
GET /statistics?period=30d
Authorization: Bearer <token>
```

**Response:**
```json
{
  "period": "30d",
  "requests": {
    "total": 150,
    "by_status": {
      "issued": 120,
      "pending_approval": 15,
      "rejected": 10,
      "failed": 5
    },
    "by_type": {
      "web_server": 100,
      "email": 30,
      "vpn": 20
    }
  },
  "certificates": {
    "total_active": 450,
    "expiring_30_days": 25,
    "expiring_60_days": 45,
    "revoked": 12
  },
  "approvals": {
    "average_approval_time_hours": 8.5,
    "pending_count": 15
  },
  "performance": {
    "average_issuance_time_minutes": 45,
    "success_rate": 0.96
  }
}
```

---

### 8. Audit Logs

#### GET /audit-logs (Admin/Auditor only)

Search audit logs.

**Request:**
```http
GET /audit-logs?event_type=certificate_downloaded&from=2024-01-01&to=2024-01-31&page=1&per_page=50
Authorization: Bearer <token>
```

**Query Parameters:**
- `event_type` (string): Filter by event type
- `event_category` (string): Filter by category
- `user_email` (string): Filter by user
- `result` (string): Filter by result (success, failure)
- `from` (date): Start date (ISO 8601)
- `to` (date): End date (ISO 8601)
- `page`, `per_page`: Pagination

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "event_type": "certificate_downloaded",
      "event_category": "certificate",
      "severity": "info",
      "user_email": "user@example.com",
      "ip_address": "192.168.1.100",
      "resource_type": "certificate",
      "resource_identifier": "1A2B3C4D5E6F",
      "action": "download",
      "result": "success",
      "timestamp": "2024-01-15T14:05:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 1234,
    "total_pages": 25
  }
}
```

#### POST /audit-logs/export (Admin/Auditor only)

Export audit logs to CSV.

**Request:**
```http
POST /audit-logs/export
Authorization: Bearer <token>
Content-Type: application/json

{
  "from": "2024-01-01",
  "to": "2024-01-31",
  "format": "csv",
  "filters": {
    "event_category": "certificate"
  }
}
```

**Response:**
```json
{
  "export_id": "uuid",
  "status": "processing",
  "download_url": null,
  "estimated_completion": "2024-01-15T15:10:00Z"
}
```

**When complete:**
```json
{
  "export_id": "uuid",
  "status": "completed",
  "download_url": "https://s3.amazonaws.com/exports/audit-log-export-uuid.csv?signature=...",
  "expires_at": "2024-01-15T16:00:00Z"
}
```

---

### 9. System Configuration (Admin only)

#### GET /config

Get all system configuration.

**Request:**
```http
GET /config
Authorization: Bearer <token>
```

**Response:**
```json
{
  "config": [
    {
      "key": "adcs.server.endpoint",
      "value": "https://adcs.internal.example.com",
      "description": "ADCS server endpoint",
      "updated_at": "2024-01-10T00:00:00Z"
    },
    {
      "key": "certificate.default_validity_days",
      "value": "365",
      "description": "Default certificate validity period",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### PATCH /config/{key}

Update a configuration value.

**Request:**
```http
PATCH /config/certificate.default_validity_days
Authorization: Bearer <token>
Content-Type: application/json

{
  "value": "730"
}
```

**Response:**
```json
{
  "key": "certificate.default_validity_days",
  "value": "730",
  "updated_at": "2024-01-15T15:00:00Z"
}
```

---

### 10. Health & Monitoring

#### GET /health

Health check endpoint (no authentication required).

**Request:**
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T15:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "adcs": "healthy",
    "s3": "healthy",
    "sqs": "healthy"
  }
}
```

#### GET /metrics (Admin only)

Prometheus-style metrics.

**Request:**
```http
GET /metrics
Authorization: Bearer <token>
```

**Response:**
```
# HELP api_requests_total Total number of API requests
# TYPE api_requests_total counter
api_requests_total{method="GET",endpoint="/requests",status="200"} 1234
api_requests_total{method="POST",endpoint="/requests",status="201"} 567

# HELP api_request_duration_seconds API request duration
# TYPE api_request_duration_seconds histogram
api_request_duration_seconds_bucket{le="0.1"} 800
api_request_duration_seconds_bucket{le="0.5"} 950
api_request_duration_seconds_bucket{le="1.0"} 990
...
```

---

## Rate Limiting

Rate limits are applied per user and endpoint:

**Limits:**
- Authentication: 10 requests/minute
- General API: 100 requests/minute
- Certificate download: 10 requests/hour
- File upload: 5 requests/minute

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 85
X-RateLimit-Reset: 1642261200
```

**Error Response (429):**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again later.",
    "retry_after": 60
  }
}
```

---

## Pagination

All list endpoints support pagination using these parameters:
- `page` (integer): Page number (default: 1)
- `per_page` (integer): Items per page (default: 20, max: 100)

**Response Format:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5,
    "links": {
      "first": "/requests?page=1",
      "prev": null,
      "next": "/requests?page=2",
      "last": "/requests?page=5"
    }
  }
}
```

---

## Webhooks (Future Enhancement)

Allow external systems to subscribe to events:

**Events:**
- `request.created`
- `request.approved`
- `request.rejected`
- `certificate.issued`
- `certificate.expiring`
- `certificate.revoked`

**Webhook Payload:**
```json
{
  "event": "certificate.issued",
  "timestamp": "2024-01-15T14:00:00Z",
  "data": {
    "certificate_id": "uuid",
    "serial_number": "1A2B3C4D5E6F",
    "common_name": "app.example.com"
  }
}
```

---

## API Versioning

- Current version: `v1`
- Version in URL path: `/v1/...`
- Breaking changes require new version
- Old versions supported for 12 months

---

## Summary

This API specification defines:
- **10 major endpoint groups** covering all functionality
- **50+ API endpoints** for comprehensive operations
- **RESTful design** with consistent patterns
- **JWT authentication** via SSO
- **Pagination, filtering, and sorting** for list endpoints
- **Rate limiting** to prevent abuse
- **Comprehensive error handling** with consistent format
- **Health checks and metrics** for monitoring

The API is designed to support the full certificate lifecycle from recommendation through revocation, with robust security, audit logging, and operational monitoring capabilities.
