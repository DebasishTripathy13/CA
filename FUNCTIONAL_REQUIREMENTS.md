# Functional Requirements - AWS Certificate Decision Assistant

## 1. User Authentication & Authorization

### 1.1 Single Sign-On (SSO) Login
**Requirement ID:** FR-AUTH-001  
**Priority:** High  
**Description:** Users must authenticate using enterprise SSO (SAML/OAuth)

**Acceptance Criteria:**
- Support SAML 2.0 and OAuth 2.0/OIDC protocols
- Integration with common IdPs (Azure AD, Okta, ADFS)
- Automatic user provisioning on first login (JIT)
- Session timeout after 8 hours of inactivity
- Secure session management with HTTP-only cookies

### 1.2 Role-Based Access Control
**Requirement ID:** FR-AUTH-002  
**Priority:** High  
**Description:** System must support multiple user roles with different permissions

**Roles:**
1. **End User**
   - View own certificate requests
   - Create new certificate requests
   - Download own certificates
   - Request certificate revocation

2. **Approver**
   - All End User permissions
   - View pending approval requests
   - Approve/reject certificate requests
   - Add approval comments

3. **Administrator**
   - All Approver permissions
   - View all requests and certificates
   - Access audit logs
   - Manage system configuration
   - View system statistics

4. **Auditor**
   - Read-only access to audit logs
   - Export audit reports
   - View all certificates (no modification)

### 1.3 Session Management
**Requirement ID:** FR-AUTH-003  
**Priority:** Medium  
**Description:** Secure session handling and token management

**Acceptance Criteria:**
- JWT tokens with 1-hour expiration
- Refresh token mechanism for extended sessions
- Automatic logout on token expiration
- Single logout (SLO) support
- Session activity logging

## 2. Certificate Authority Recommendation Engine

### 2.1 Multi-Step Decision Tree
**Requirement ID:** FR-REC-001  
**Priority:** High  
**Description:** Interactive questionnaire to recommend appropriate CA type

**Decision Questions (11+ questions):**

1. **What type of service requires the certificate?**
   - Web server (HTTPS)
   - Database server (TLS)
   - API endpoint
   - Email server (S/MIME)
   - Code signing
   - User authentication
   - VPN
   - Other

2. **Will the service be publicly accessible?**
   - Yes, public internet
   - No, internal only
   - Hybrid (both internal and external)

3. **What is the expected lifespan of the certificate?**
   - < 90 days
   - 90 days - 1 year
   - 1-2 years
   - > 2 years

4. **Does the service require browser trust?**
   - Yes, must be trusted by all major browsers
   - No, internal services only
   - Partial (specific client trust)

5. **What is the environment type?**
   - Production
   - Development
   - Testing/Staging
   - Lab/Sandbox

6. **How many certificates do you need?**
   - Single certificate
   - Multiple certificates (2-10)
   - Bulk certificates (>10)

7. **Will this certificate use wildcard or SAN?**
   - Single domain
   - Wildcard (*.example.com)
   - Multi-domain (SAN)

8. **What is the criticality level?**
   - Critical (revenue-impacting)
   - High (important services)
   - Medium (standard services)
   - Low (non-critical)

9. **Compliance requirements?**
   - PCI DSS
   - HIPAA
   - SOC 2
   - ISO 27001
   - None

10. **Certificate key size preference?**
    - RSA 2048
    - RSA 4096
    - ECC P-256
    - ECC P-384

11. **Renewal frequency preference?**
    - Automatic renewal
    - Manual renewal
    - Notification before expiry

**Recommendation Logic:**

| Conditions | Recommendation |
|-----------|----------------|
| Public internet + Browser trust required | **Public CA** |
| Internal only + No browser trust | **Internal CA** |
| Development/Testing environment | **Internal CA** |
| Production + Internal only | **Internal CA** |
| Wildcard + Public | **Public CA** |
| Code signing | **Public CA** |
| VPN/Database (internal) | **Internal CA** |

### 2.2 Recommendation Override
**Requirement ID:** FR-REC-002  
**Priority:** Medium  
**Description:** Allow users to override recommendation with justification

**Acceptance Criteria:**
- Display clear recommendation (Public or Internal CA)
- Provide option to override recommendation
- Require justification text (min 50 characters) for override
- Route override requests to approver
- Log all override requests in audit trail
- Show warning message for overrides

### 2.3 External CA Redirect
**Requirement ID:** FR-REC-003  
**Priority:** Medium  
**Description:** For Public CA recommendations, redirect to external CA portal

**Acceptance Criteria:**
- Display list of approved public CAs (DigiCert, Let's Encrypt, etc.)
- Show links to external CA portals
- Display process documentation
- Log redirection in audit trail
- No certificate request creation in system for public CA

## 3. Certificate Request Management

### 3.1 Certificate Request Form
**Requirement ID:** FR-REQ-001  
**Priority:** High  
**Description:** Comprehensive form for certificate request creation

**Required Fields:**
- Certificate type (Web server, Email, Code signing, etc.)
- Common Name (CN)
- Organization (O)
- Organizational Unit (OU)
- Locality (L)
- State/Province (ST)
- Country (C)
- Email address
- Key algorithm (RSA 2048, RSA 4096, ECC P-256, ECC P-384)
- Validity period (90 days, 1 year, 2 years)
- Subject Alternative Names (SANs) - optional
- Business justification
- Approver name/email

**Optional Fields:**
- Department
- Cost center
- Project code
- Additional notes

### 3.2 CSR Generation
**Requirement ID:** FR-REQ-002  
**Priority:** High  
**Description:** In-portal CSR and private key generation

**Acceptance Criteria:**
- Support RSA (2048, 4096) and ECC (P-256, P-384) key types
- Generate private key in browser using Web Crypto API
- Create CSR using crypto library
- Display CSR in PEM format for review
- Validate CSR format and content
- Encrypt private key with user password before storage
- Option to download private key immediately
- Warning: Private key will not be recoverable later

### 3.3 CSR Upload
**Requirement ID:** FR-REQ-003  
**Priority:** High  
**Description:** Support uploading existing CSR

**Acceptance Criteria:**
- File upload (.csr, .pem, .txt formats)
- Paste CSR text directly
- Validate CSR format (PEM/DER)
- Extract and display CSR details (CN, OU, key size, etc.)
- Validate key algorithm meets policy
- Verify CSR signature

### 3.4 Request Review & Submission
**Requirement ID:** FR-REQ-004  
**Priority:** High  
**Description:** Review request details before submission

**Acceptance Criteria:**
- Display all request details in read-only summary
- Show estimated issuance time
- Allow editing before submission
- Confirmation dialog on submit
- Generate unique request ID
- Send confirmation email to requester
- Notify designated approver

### 3.5 Request Status Tracking
**Requirement ID:** FR-REQ-005  
**Priority:** Medium  
**Description:** Track certificate request through lifecycle

**Status Values:**
- **Draft:** Request created but not submitted
- **Pending Approval:** Awaiting approver decision
- **Approved:** Approved, queued for issuance
- **In Progress:** Submitted to ADCS, processing
- **Issued:** Certificate issued successfully
- **Rejected:** Request rejected by approver
- **Failed:** Issuance failed (technical error)
- **Cancelled:** Cancelled by requester or admin
- **Revoked:** Certificate was revoked

**Acceptance Criteria:**
- Real-time status updates
- Status change notifications
- Status history log
- Estimated completion time
- Progress indicator

## 4. Approval Workflow

### 4.1 Approval Queue
**Requirement ID:** FR-APRV-001  
**Priority:** High  
**Description:** Approvers see list of pending requests

**Acceptance Criteria:**
- Display all pending approval requests
- Filter by date, requester, certificate type
- Sort by priority, submission date
- Quick view of request details
- Bulk selection for batch approvals
- SLA indicators (aging requests highlighted)
- Automatic assignment based on rules

### 4.2 Approval/Rejection Actions
**Requirement ID:** FR-APRV-002  
**Priority:** High  
**Description:** Approvers can approve or reject requests

**Acceptance Criteria:**
- Clear approve/reject buttons
- Require approval/rejection comments
- Email notification to requester on decision
- Automatic routing to ADCS on approval
- Request returns to draft on rejection
- Escalation after 48 hours without action
- Re-approval required after modifications

### 4.3 Approval Delegation
**Requirement ID:** FR-APRV-003  
**Priority:** Low  
**Description:** Approvers can delegate to another approver

**Acceptance Criteria:**
- Select alternate approver from directory
- Add delegation note
- Notify delegate via email
- Log delegation in audit trail
- Original approver still has visibility

## 5. ADCS Integration

### 5.1 Certificate Issuance
**Requirement ID:** FR-ADCS-001  
**Priority:** High  
**Description:** Submit approved requests to ADCS for issuance

**Acceptance Criteria:**
- Automatic submission on approval
- Use ADCS API/certreq command
- Handle synchronous and asynchronous issuance
- Poll for status if async (every 30 seconds)
- Timeout after 10 minutes
- Retrieve issued certificate automatically
- Support multiple ADCS servers (load balancing)

### 5.2 Error Handling
**Requirement ID:** FR-ADCS-002  
**Priority:** High  
**Description:** Handle ADCS errors gracefully

**Acceptance Criteria:**
- Retry logic (3 attempts with exponential backoff)
- Categorize errors (temporary, permanent, policy)
- User-friendly error messages
- Notify administrator on repeated failures
- Dead letter queue for failed requests
- Manual intervention option

### 5.3 Certificate Retrieval
**Requirement ID:** FR-ADCS-003  
**Priority:** High  
**Description:** Retrieve issued certificate from ADCS

**Acceptance Criteria:**
- Download certificate in PEM and DER formats
- Include certificate chain (root + intermediates)
- Validate certificate content
- Store in S3 with encryption
- Update request status to "Issued"
- Notify requester with download link

## 6. Certificate Management

### 6.1 Certificate Storage
**Requirement ID:** FR-CERT-001  
**Priority:** High  
**Description:** Secure storage of certificates and keys

**Acceptance Criteria:**
- Store certificates in S3 with KMS encryption
- Store private keys separately (if generated by system)
- Bucket access restricted by IAM roles
- Versioning enabled
- Object lifecycle policies (7-year retention)
- Signed URLs for temporary access (15 minutes)

### 6.2 Certificate Download
**Requirement ID:** FR-CERT-002  
**Priority:** High  
**Description:** Users can download their certificates

**Acceptance Criteria:**
- Download options: PEM, DER, PKCS#12
- Include certificate chain
- Download private key (if generated by system, one-time)
- Generate signed S3 URL
- Log all downloads in audit trail
- Rate limiting (prevent abuse)

### 6.3 Certificate Listing
**Requirement ID:** FR-CERT-003  
**Priority:** Medium  
**Description:** Dashboard to view all user certificates

**Acceptance Criteria:**
- List all certificates for current user
- Display: CN, Issuer, Valid From, Valid To, Status
- Filter by status, expiry date
- Search by common name
- Export to CSV
- Color-coded expiry warnings (red < 30 days)

### 6.4 Certificate Revocation
**Requirement ID:** FR-CERT-004  
**Priority:** High  
**Description:** Users can request certificate revocation

**Acceptance Criteria:**
- Revocation request form
- Reason code selection (key compromise, superseded, etc.)
- Require justification text
- Approval required for revocation (same workflow)
- Submit to ADCS for CRL/OCSP update
- Update certificate status to "Revoked"
- Send confirmation notification
- Prevent download of revoked certificates

## 7. Expiry Monitoring & Notifications

### 7.1 Daily Expiry Scan
**Requirement ID:** FR-EXP-001  
**Priority:** High  
**Description:** Automated daily scan for expiring certificates

**Acceptance Criteria:**
- Scheduled job runs daily at 2 AM UTC
- Query all active certificates
- Identify certificates expiring in 90, 60, 30, 14, 7 days
- Generate notification list
- Send to notification queue

### 7.2 Expiry Notifications
**Requirement ID:** FR-EXP-002  
**Priority:** High  
**Description:** Send reminders for expiring certificates

**Notification Schedule:**
- 90 days before expiry: Initial reminder
- 60 days before expiry: Second reminder
- 30 days before expiry: Urgent reminder
- 14 days before expiry: Critical reminder
- 7 days before expiry: Final reminder
- Daily reminders for last 7 days

**Acceptance Criteria:**
- Email notification to certificate owner
- Include certificate details (CN, expiry date)
- Provide renewal instructions
- Link to create new request
- CC approver and administrator
- Slack/Teams notification (optional)
- Stop notifications after renewal

### 7.3 Expiry Dashboard
**Requirement ID:** FR-EXP-003  
**Priority:** Medium  
**Description:** Visual dashboard for certificate expiry

**Acceptance Criteria:**
- Chart showing expiry timeline
- List of certificates expiring soon
- Color-coded alerts (green > 60 days, yellow 30-60, red < 30)
- Export expiry report
- Admin view shows all certificates
- User view shows own certificates only

## 8. Audit Logging & Compliance

### 8.1 Comprehensive Audit Trail
**Requirement ID:** FR-AUD-001  
**Priority:** High  
**Description:** Log all system actions for compliance

**Logged Events:**
- User login/logout
- Certificate request creation
- Request approval/rejection
- Certificate issuance
- Certificate download
- Certificate revocation
- Configuration changes
- User role changes
- Failed authentication attempts
- System errors

**Log Fields:**
- Timestamp (ISO 8601 UTC)
- Event type
- User ID and name
- IP address
- User agent
- Action performed
- Resource affected (request ID, cert ID)
- Result (success/failure)
- Additional context (JSON payload)

### 8.2 Audit Log Viewer
**Requirement ID:** FR-AUD-002  
**Priority:** Medium  
**Description:** Interface to search and view audit logs

**Acceptance Criteria:**
- Search by date range, user, event type
- Filter by result (success/failure)
- Export to CSV/JSON
- Pagination (100 records per page)
- Detailed view for each event
- Real-time log streaming (admin only)

### 8.3 Compliance Reporting
**Requirement ID:** FR-AUD-003  
**Priority:** Medium  
**Description:** Generate compliance reports

**Report Types:**
1. Certificate Issuance Report (monthly)
2. Revocation Report (on-demand)
3. User Activity Report (on-demand)
4. Approval Metrics Report (monthly)
5. Security Incident Report (as needed)

**Acceptance Criteria:**
- Automated monthly report generation
- Email to compliance team
- Store reports in S3
- 10-year retention policy
- PDF and CSV formats

### 8.4 Audit Log Retention
**Requirement ID:** FR-AUD-004  
**Priority:** High  
**Description:** Long-term retention of audit logs

**Acceptance Criteria:**
- Store in RDS for 1 year (hot storage)
- Archive to S3 after 1 year (cold storage)
- Retain for 10 years minimum
- Immutable logs (write-once)
- Encryption at rest (KMS)
- Access logging for audit logs

## 9. User Interface & Experience

### 9.1 Responsive Design
**Requirement ID:** FR-UI-001  
**Priority:** Medium  
**Description:** Support multiple device types

**Acceptance Criteria:**
- Desktop browsers (Chrome, Firefox, Safari, Edge)
- Tablet support (iPad, Android tablets)
- Mobile responsive (but not primary use case)
- Minimum resolution: 1280x720

### 9.2 Dashboard
**Requirement ID:** FR-UI-002  
**Priority:** High  
**Description:** Personalized user dashboard

**Widgets:**
- My Recent Requests (last 10)
- My Active Certificates
- Expiring Soon (next 30 days)
- Pending Approvals (approvers only)
- Quick Actions (New Request, View Certificates)
- System Announcements

### 9.3 Search & Filter
**Requirement ID:** FR-UI-003  
**Priority:** Medium  
**Description:** Search across requests and certificates

**Acceptance Criteria:**
- Global search bar
- Search by: CN, request ID, certificate serial
- Filter by: status, date range, type
- Auto-suggest as user types
- Save search filters

### 9.4 Accessibility
**Requirement ID:** FR-UI-004  
**Priority:** Medium  
**Description:** WCAG 2.1 AA compliance

**Acceptance Criteria:**
- Keyboard navigation
- Screen reader support
- Color contrast ratios
- Alt text for images
- ARIA labels
- Focus indicators

## 10. Administration

### 10.1 System Configuration
**Requirement ID:** FR-ADM-001  
**Priority:** Medium  
**Description:** Admin panel for system settings

**Configurable Settings:**
- ADCS server endpoints
- Email templates
- Notification settings
- Approval workflow rules
- Certificate validity periods
- Key size policies
- Auto-approval thresholds
- Session timeout

### 10.2 User Management
**Requirement ID:** FR-ADM-002  
**Priority:** Medium  
**Description:** Manage user roles and permissions

**Acceptance Criteria:**
- List all users
- Assign/revoke roles
- Disable user access
- View user activity
- Reset user sessions
- Bulk role assignment

### 10.3 System Statistics
**Requirement ID:** FR-ADM-003  
**Priority:** Low  
**Description:** Metrics and analytics dashboard

**Metrics:**
- Total requests (by status)
- Issuance rate (daily/weekly/monthly)
- Average approval time
- Top requesters
- Certificate types distribution
- Failure rate
- System uptime

## 11. Security Requirements

### 11.1 Authentication Security
**Requirement ID:** FR-SEC-001  
**Priority:** Critical  
**Description:** Secure authentication mechanisms

**Acceptance Criteria:**
- No password storage (SSO only)
- MFA support (via SSO provider)
- Account lockout after 5 failed attempts
- Session fixation prevention
- CSRF token validation
- Secure cookie attributes (HttpOnly, Secure, SameSite)

### 11.2 Data Encryption
**Requirement ID:** FR-SEC-002  
**Priority:** Critical  
**Description:** Encrypt sensitive data

**Acceptance Criteria:**
- TLS 1.2+ for all communications
- KMS encryption for S3 buckets
- RDS encryption at rest
- Private keys encrypted with AES-256
- Secrets in AWS Secrets Manager
- No credentials in code/logs

### 11.3 Input Validation
**Requirement ID:** FR-SEC-003  
**Priority:** Critical  
**Description:** Validate and sanitize all inputs

**Acceptance Criteria:**
- Server-side validation for all inputs
- Parameterized queries (prevent SQL injection)
- Content-Type validation
- File upload restrictions (size, type)
- CSR validation (prevent malicious CSRs)
- XSS prevention (output encoding)

### 11.4 Rate Limiting
**Requirement ID:** FR-SEC-004  
**Priority:** High  
**Description:** Prevent abuse and DoS attacks

**Limits:**
- API: 100 requests/minute per user
- Login: 5 attempts per 15 minutes
- Certificate download: 10 per hour per user
- File upload: 5 per minute per user

## 12. Performance Requirements

### 12.1 Response Time
**Requirement ID:** FR-PERF-001  
**Priority:** High  
**Description:** API and page load performance targets

**Targets:**
- API response time: < 200ms (p95)
- Dashboard load: < 2 seconds
- Search results: < 500ms
- Certificate download: < 3 seconds

### 12.2 Scalability
**Requirement ID:** FR-PERF-002  
**Priority:** High  
**Description:** Support concurrent users

**Targets:**
- Concurrent users: 1000+
- Daily requests: 5000+
- Database connections: Auto-scaling
- Horizontal scaling for API services

### 12.3 Availability
**Requirement ID:** FR-PERF-003  
**Priority:** High  
**Description:** System uptime targets

**Targets:**
- Uptime: 99.5% (4.38 hours downtime/year)
- Planned maintenance: Monthly 2-hour window
- Multi-AZ deployment
- Automated health checks
- Failover time: < 5 minutes

## 13. Integration Requirements

### 13.1 SSO Integration
**Requirement ID:** FR-INT-001  
**Priority:** High  
**Description:** Integrate with enterprise SSO

**Supported Providers:**
- Azure Active Directory (SAML/OIDC)
- Okta (SAML/OIDC)
- ADFS (SAML)
- Generic SAML 2.0 providers

### 13.2 Email Integration
**Requirement ID:** FR-INT-002  
**Priority:** High  
**Description:** Email notifications via AWS SES

**Email Types:**
- Request confirmation
- Approval notifications
- Rejection notifications
- Certificate issued
- Expiry reminders
- Revocation confirmation

### 13.3 Slack/Teams Integration
**Requirement ID:** FR-INT-003  
**Priority:** Low  
**Description:** Optional Slack/Teams notifications

**Acceptance Criteria:**
- Webhook configuration
- Notification templates
- Channel routing
- Enable/disable per user

## 14. Data Migration & Import

### 14.1 Existing Certificate Import
**Requirement ID:** FR-MIG-001  
**Priority:** Medium  
**Description:** Import existing certificates into system

**Acceptance Criteria:**
- Bulk upload via CSV
- Parse certificate files
- Extract metadata (CN, expiry, issuer)
- Validate certificate chain
- Import to database
- Link to existing users (by email)

## Summary

This document defines 60+ functional requirements across 14 major categories:
1. Authentication & Authorization (3)
2. Recommendation Engine (3)
3. Request Management (5)
4. Approval Workflow (3)
5. ADCS Integration (3)
6. Certificate Management (4)
7. Expiry Monitoring (3)
8. Audit & Compliance (4)
9. User Interface (4)
10. Administration (3)
11. Security (4)
12. Performance (3)
13. Integrations (3)
14. Data Migration (1)

Each requirement is prioritized (Critical/High/Medium/Low) and includes detailed acceptance criteria for implementation and testing.
