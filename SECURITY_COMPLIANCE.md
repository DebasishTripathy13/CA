# Security and Compliance - AWS Certificate Decision Assistant

## Security Architecture Overview

The AWS Certificate Decision Assistant implements a comprehensive security strategy following defense-in-depth principles, AWS Well-Architected Framework security pillar, and industry best practices.

## 1. Identity and Access Management (IAM)

### 1.1 Authentication

#### Single Sign-On (SSO)
- **Protocol:** SAML 2.0 and OAuth 2.0/OIDC
- **Supported IdPs:**
  - Azure Active Directory
  - Okta
  - AWS SSO
  - ADFS
  - Generic SAML 2.0 providers

#### Implementation
```yaml
SSO Flow:
1. User accesses application → Redirect to IdP
2. User authenticates with IdP → IdP validates credentials
3. IdP generates SAML assertion/OAuth token
4. Application validates assertion/token
5. Application creates JWT session token
6. JWT token used for subsequent API calls
```

#### JWT Token Structure
```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user-uuid",
    "email": "user@example.com",
    "name": "John Doe",
    "role": "user",
    "iat": 1642261200,
    "exp": 1642264800,
    "iss": "cert-assistant.example.com",
    "aud": "cert-assistant-api"
  }
}
```

#### Token Security
- **Algorithm:** RS256 (RSA Signature with SHA-256)
- **Expiration:** 1 hour
- **Refresh Token:** 7 days (sliding window)
- **Storage:** HTTP-only, Secure, SameSite cookies
- **Rotation:** On each refresh
- **Revocation:** Token blacklist in Redis (for logout)

### 1.2 Authorization

#### Role-Based Access Control (RBAC)

**Roles:**

| Role | Permissions | Use Case |
|------|-------------|----------|
| **user** | - Create/view own requests<br>- Download own certificates<br>- Request revocation | Standard end users |
| **approver** | - All user permissions<br>- Approve/reject requests<br>- View pending approvals | Certificate approvers/managers |
| **admin** | - All approver permissions<br>- View all requests/certificates<br>- Manage system config<br>- View audit logs | System administrators |
| **auditor** | - Read-only access to audit logs<br>- Export audit reports<br>- View all certificates (no modification) | Compliance/security team |

#### Permission Matrix

| Resource | Create | Read | Update | Delete | Approve | Download |
|----------|--------|------|--------|--------|---------|----------|
| **Own Requests** | ✓ user | ✓ user | ✓ user | ✓ user | - | - |
| **All Requests** | - | ✓ admin | ✓ admin | ✓ admin | ✓ approver | - |
| **Own Certificates** | - | ✓ user | - | - | - | ✓ user |
| **All Certificates** | - | ✓ admin/auditor | - | - | - | ✓ admin |
| **Audit Logs** | - | ✓ admin/auditor | - | - | - | ✓ admin/auditor |
| **System Config** | - | ✓ admin | ✓ admin | - | - | - |

#### Attribute-Based Access Control (ABAC)

Additional access controls based on attributes:
- **Department-based:** Users can only see requests from their department (optional)
- **Environment-based:** Restrict production certificates to specific users
- **Time-based:** Restrict access to business hours (configurable)

### 1.3 AWS IAM Policies

#### Application Service Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:PutObjectAcl"
      ],
      "Resource": "arn:aws:s3:::cert-assistant-*/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:Encrypt",
        "kms:GenerateDataKey"
      ],
      "Resource": "arn:aws:kms:*:*:key/*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "s3.us-east-1.amazonaws.com"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage"
      ],
      "Resource": "arn:aws:sqs:*:*:cert-assistant-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:cert-assistant/*"
    }
  ]
}
```

---

## 2. Data Security

### 2.1 Encryption at Rest

#### Database (RDS)
- **Method:** AWS RDS encryption with KMS
- **Algorithm:** AES-256
- **Key Management:** AWS KMS Customer Managed Key (CMK)
- **Key Rotation:** Automatic annual rotation
- **Scope:** Entire database, automated backups, snapshots, read replicas

#### S3 Buckets
- **Method:** Server-Side Encryption with KMS (SSE-KMS)
- **Algorithm:** AES-256
- **Key Management:** Dedicated CMK per bucket type
- **Key Rotation:** Enabled

**Bucket Encryption Configuration:**
```yaml
Certificates Bucket:
  - Encryption: SSE-KMS
  - KMS Key: cert-assistant-certificates-key
  - Versioning: Enabled
  - MFA Delete: Enabled

Private Keys Bucket:
  - Encryption: SSE-KMS
  - KMS Key: cert-assistant-keys-key (separate key)
  - Versioning: Enabled
  - MFA Delete: Enabled
  - Object Lock: Compliance mode (prevent deletion)

Audit Logs Bucket:
  - Encryption: SSE-KMS
  - KMS Key: cert-assistant-audit-key
  - Versioning: Enabled
  - Object Lock: Governance mode
```

#### Private Key Encryption
For private keys generated by the system:
```
1. Generate RSA/ECC key pair in backend
2. Encrypt private key with AES-256-GCM
3. Encryption key derived from:
   - User-provided password (PBKDF2, 100,000 iterations)
   - OR AWS KMS data key
4. Store encrypted key in S3
5. Never store decryption password
```

### 2.2 Encryption in Transit

#### TLS Configuration
- **Protocol:** TLS 1.2 minimum, TLS 1.3 preferred
- **Cipher Suites:**
  ```
  TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
  TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
  TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256
  ```
- **Certificate:** AWS ACM managed certificate
- **HSTS:** Enabled (max-age=31536000; includeSubDomains; preload)

#### Database Connections
- **RDS:** SSL/TLS required
- **Certificate Verification:** Enabled
- **Connection String:**
  ```
  postgres://user:pass@rds.amazonaws.com:5432/db?sslmode=require&sslrootcert=/path/to/rds-ca-bundle.pem
  ```

#### ADCS Communication
- **VPN/Direct Connect:** Encrypted tunnel to on-premise
- **API Calls:** HTTPS only
- **Mutual TLS:** Optional (certificate-based authentication)

### 2.3 Secrets Management

#### AWS Secrets Manager
All sensitive credentials stored in Secrets Manager:
```yaml
Secrets:
  - cert-assistant/database/credentials
    - username
    - password
    - host
    - port
    
  - cert-assistant/adcs/api-key
    - api_key
    - endpoint
    
  - cert-assistant/jwt/signing-key
    - private_key (RS256)
    - public_key
    
  - cert-assistant/oauth/client-secret
    - client_id
    - client_secret
```

**Features:**
- **Automatic Rotation:** Database credentials rotate every 90 days
- **Versioning:** Keep previous versions for rollback
- **Access Logging:** CloudTrail logs all access
- **Least Privilege:** Only application role can retrieve

---

## 3. Application Security

### 3.1 Input Validation

#### Server-Side Validation
All user inputs are validated on the server:

```javascript
// Example validation rules
const requestSchema = {
  common_name: {
    type: 'string',
    maxLength: 255,
    pattern: /^[a-zA-Z0-9\-\.\*]+$/,
    required: true
  },
  email_address: {
    type: 'string',
    format: 'email',
    maxLength: 255,
    required: true
  },
  country: {
    type: 'string',
    length: 2,
    pattern: /^[A-Z]{2}$/,
    required: true
  },
  business_justification: {
    type: 'string',
    minLength: 50,
    maxLength: 5000,
    required: true
  }
};
```

#### CSR Validation
```javascript
// Validate uploaded CSR
function validateCSR(csrContent) {
  // 1. Parse CSR (PEM/DER format)
  // 2. Verify signature
  // 3. Check key size (min 2048 for RSA)
  // 4. Validate subject DN fields
  // 5. Check for malicious content
  // 6. Ensure no weak algorithms (MD5, SHA1)
}
```

#### File Upload Security
- **Allowed Formats:** .csr, .pem, .txt
- **Max File Size:** 10 KB
- **Content-Type Validation:** Enforce correct MIME type
- **Virus Scanning:** Integrate with ClamAV or AWS S3 malware detection
- **Storage:** Temporary files in `/tmp` with auto-cleanup

### 3.2 SQL Injection Prevention

- **Parameterized Queries:** All database queries use prepared statements
- **ORM:** Use Sequelize (Node.js) or SQLAlchemy (Python) with parameterization
- **Input Sanitization:** Escape special characters
- **Least Privilege:** Database user has minimal required permissions

**Example:**
```javascript
// SAFE - Parameterized query
const requests = await db.query(
  'SELECT * FROM certificate_requests WHERE user_id = $1',
  [userId]
);

// UNSAFE - Never do this
const requests = await db.query(
  `SELECT * FROM certificate_requests WHERE user_id = '${userId}'`
);
```

### 3.3 Cross-Site Scripting (XSS) Prevention

#### Output Encoding
- **React/Angular:** Automatic escaping of interpolated values
- **API Responses:** JSON encoding (no HTML)
- **Error Messages:** Sanitize before displaying

#### Content Security Policy (CSP)
```http
Content-Security-Policy: 
  default-src 'self'; 
  script-src 'self' 'unsafe-inline' https://cdn.example.com; 
  style-src 'self' 'unsafe-inline'; 
  img-src 'self' data: https:; 
  font-src 'self' https://fonts.gstatic.com; 
  connect-src 'self' https://api.cert-assistant.example.com; 
  frame-ancestors 'none';
```

### 3.4 Cross-Site Request Forgery (CSRF) Prevention

- **Token-Based:** Generate CSRF token on login
- **Validation:** Verify token on all state-changing requests
- **SameSite Cookies:** `SameSite=Strict` for session cookies
- **Custom Header:** Require `X-Requested-With: XMLHttpRequest`

### 3.5 Rate Limiting

**Implementation:** Redis-based rate limiter

```yaml
Rate Limits:
  Authentication:
    - 10 requests per minute per IP
    - 5 failed login attempts → 15-minute lockout
  
  API Endpoints:
    - 100 requests per minute per user
    - 1000 requests per hour per user
  
  Certificate Download:
    - 10 downloads per hour per user
    - 100 downloads per day per user
  
  File Upload:
    - 5 uploads per minute per user
```

**Response Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 85
X-RateLimit-Reset: 1642264800
Retry-After: 60
```

### 3.6 Dependency Security

#### Vulnerability Scanning
- **Tools:** npm audit, Snyk, Dependabot
- **Frequency:** Daily automated scans
- **Action:** Automatic PR for security updates
- **Policy:** Patch critical vulnerabilities within 48 hours

#### Software Composition Analysis (SCA)
```yaml
Allowed Licenses:
  - MIT
  - Apache-2.0
  - BSD-3-Clause
  - ISC

Prohibited Licenses:
  - GPL-3.0 (copyleft)
  - AGPL-3.0
```

---

## 4. Network Security

### 4.1 VPC Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ VPC (10.0.0.0/16)                                           │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Public Subnets (DMZ)                                    │ │
│ │ - Internet Gateway                                      │ │
│ │ - Application Load Balancer (ALB)                       │ │
│ │ - NAT Gateway                                           │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Private Subnets (Application Tier)                     │ │
│ │ - ECS Fargate Tasks                                     │ │
│ │ - Lambda Functions                                      │ │
│ │ - No direct internet access                             │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Private Subnets (Data Tier)                            │ │
│ │ - RDS Database (Multi-AZ)                               │ │
│ │ - ElastiCache (Redis)                                   │ │
│ │ - No internet access                                    │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ VPC Endpoints (PrivateLink):                                │
│ - S3, Secrets Manager, SQS, KMS, CloudWatch                │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Security Groups

#### ALB Security Group
```yaml
Inbound:
  - Port 443 (HTTPS) from 0.0.0.0/0
  - Port 80 (HTTP) from 0.0.0.0/0 → Redirect to 443

Outbound:
  - All traffic to Application SG
```

#### Application Security Group
```yaml
Inbound:
  - Port 8080 from ALB SG only

Outbound:
  - Port 5432 to Database SG (PostgreSQL)
  - Port 6379 to Cache SG (Redis)
  - Port 443 to VPC Endpoints (AWS services)
  - Port 443 to 0.0.0.0/0 (NAT Gateway for external APIs)
```

#### Database Security Group
```yaml
Inbound:
  - Port 5432 from Application SG only

Outbound:
  - None (database doesn't need outbound)
```

### 4.3 Network ACLs

- **Public Subnets:** Allow HTTP/HTTPS inbound, ephemeral ports outbound
- **Private Subnets:** Deny all traffic from internet
- **Stateless:** Must configure both inbound and outbound rules

### 4.4 AWS WAF (Web Application Firewall)

**Attached to:** Application Load Balancer

**Rule Sets:**
1. **AWS Managed Rules:**
   - Core Rule Set (CRS)
   - Known Bad Inputs
   - SQL Injection
   - XSS Prevention
   - Linux/POSIX Operating System Rules

2. **Custom Rules:**
   - **Rate Limiting:** Block IPs with >2000 requests/5 minutes
   - **Geo-Blocking:** Restrict access to allowed countries (optional)
   - **IP Reputation:** Block known malicious IPs
   - **Size Constraints:** Limit request body size to 10 MB

**Actions:**
- Block: Return 403 Forbidden
- Count: Allow but log (for testing rules)
- CAPTCHA: Challenge suspicious requests

---

## 5. Audit and Compliance

### 5.1 Audit Logging

#### What to Log
```yaml
Authentication Events:
  - User login (success/failure)
  - User logout
  - Token refresh
  - Failed authentication attempts
  - Session timeout

Authorization Events:
  - Access denied (403)
  - Role changes
  - Permission changes

Certificate Lifecycle:
  - Request created
  - Request submitted
  - Request approved/rejected
  - Certificate issued
  - Certificate downloaded
  - Certificate revoked
  - Expiry notifications sent

Administrative Actions:
  - Configuration changes
  - User role modifications
  - System maintenance

Security Events:
  - Rate limit violations
  - Suspicious activity
  - Malware detection
  - Security group changes
```

#### Log Format
```json
{
  "timestamp": "2024-01-15T14:30:00.000Z",
  "event_id": "uuid",
  "event_type": "certificate_downloaded",
  "event_category": "certificate",
  "severity": "info",
  "actor": {
    "user_id": "uuid",
    "email": "user@example.com",
    "role": "user",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
  },
  "resource": {
    "type": "certificate",
    "id": "uuid",
    "identifier": "1A2B3C4D5E6F",
    "name": "app.example.com"
  },
  "action": "download",
  "result": "success",
  "metadata": {
    "format": "pem",
    "include_chain": true
  }
}
```

#### Log Storage
- **Short-term (1 year):** RDS database for fast querying
- **Long-term (10 years):** S3 Glacier for compliance
- **Real-time:** CloudWatch Logs for monitoring
- **SIEM Integration:** Export to Splunk/Elastic (optional)

### 5.2 CloudTrail

**AWS API Audit Trail:**
- **Enabled:** All regions
- **Log File Validation:** Enabled (detect tampering)
- **S3 Bucket:** Separate, encrypted, access-logged
- **SNS Notifications:** Alert on specific API calls
- **Integration:** CloudWatch Logs for alarms

**Monitored Events:**
- IAM role/policy changes
- S3 bucket policy changes
- Security group modifications
- KMS key usage
- RDS snapshot creation/deletion
- Secrets Manager access

### 5.3 Compliance Standards

#### SOC 2 Type II

**Controls:**
1. **Security:** Encryption, access control, monitoring
2. **Availability:** Multi-AZ, backups, DR plan
3. **Processing Integrity:** Input validation, error handling
4. **Confidentiality:** Data classification, DLP
5. **Privacy:** GDPR compliance, data retention

#### PCI DSS (if handling payment data)

**Requirements:**
1. **Network Security:** Firewall, segmentation
2. **Encryption:** Data at rest and in transit
3. **Access Control:** RBAC, MFA, least privilege
4. **Monitoring:** Audit logs, SIEM, alerts
5. **Vulnerability Management:** Patching, scanning
6. **Incident Response:** Detection, containment, recovery

#### GDPR

**Compliance Measures:**
1. **Data Minimization:** Only collect necessary data
2. **Right to Access:** Users can export their data
3. **Right to Erasure:** Soft delete with retention policy
4. **Data Portability:** Export in machine-readable format (JSON)
5. **Consent Management:** Explicit consent for data collection
6. **Data Protection Officer (DPO):** Designate contact
7. **Data Breach Notification:** 72-hour disclosure requirement

#### HIPAA (if handling health data)

**Safeguards:**
1. **Administrative:** Policies, procedures, training
2. **Physical:** Data center security (AWS responsibility)
3. **Technical:** Encryption, access control, audit logs
4. **Business Associate Agreement (BAA):** With AWS

### 5.4 Compliance Reporting

**Automated Reports:**
1. **Monthly:**
   - Certificate issuance summary
   - Approval metrics (average time, pending count)
   - Failed authentication attempts
   - Access control changes

2. **Quarterly:**
   - Security incident summary
   - Vulnerability management report
   - Compliance attestation

3. **Annual:**
   - SOC 2 audit preparation
   - Disaster recovery testing results
   - Security awareness training completion

---

## 6. Incident Response

### 6.1 Detection

**Monitoring:**
- **CloudWatch Alarms:** CPU, memory, disk, API errors
- **GuardDuty:** Threat detection (malicious IPs, port scanning)
- **Inspector:** Vulnerability scanning (EC2/ECS)
- **Config:** Resource compliance monitoring
- **Custom Alarms:**
  - Failed login rate > 10/minute
  - Certificate issuance failure rate > 20%
  - Unusual download patterns

### 6.2 Response Playbooks

#### Security Incident Playbook
```yaml
1. Detection:
   - Alert triggered in CloudWatch/GuardDuty
   - Security team notified via PagerDuty

2. Triage:
   - Assess severity (Critical/High/Medium/Low)
   - Determine scope (users affected, data exposed)

3. Containment:
   - Isolate affected resources (security group changes)
   - Revoke compromised credentials
   - Block malicious IPs in WAF

4. Investigation:
   - Review audit logs
   - Analyze CloudTrail events
   - Determine root cause

5. Remediation:
   - Apply security patches
   - Rotate credentials
   - Update firewall rules

6. Recovery:
   - Restore from clean backup if needed
   - Verify system integrity

7. Post-Incident:
   - Document lessons learned
   - Update runbooks
   - Improve detection rules
```

#### Data Breach Response
```yaml
1. Identify:
   - Scope of breach (data types, user count)
   - Breach method (how attacker gained access)

2. Contain:
   - Disable compromised accounts
   - Rotate all credentials
   - Enable additional monitoring

3. Notify:
   - Affected users (within 72 hours for GDPR)
   - Regulators (if required by law)
   - Management and legal team

4. Remediate:
   - Fix vulnerability
   - Enhance security controls
   - Conduct security audit

5. Monitor:
   - Increased monitoring for 90 days
   - Watch for secondary attacks
```

### 6.3 Disaster Recovery

**Recovery Objectives:**
- **RTO (Recovery Time Objective):** 1 hour
- **RPO (Recovery Point Objective):** 5 minutes

**DR Plan:**
1. **Multi-AZ Deployment:** Automatic failover for RDS
2. **Backups:**
   - Database: Automated daily backups, 7-day retention
   - S3: Versioning + cross-region replication (optional)
   - Snapshots: Weekly manual snapshots, 30-day retention
3. **Runbooks:** Step-by-step recovery procedures
4. **Testing:** Quarterly DR drills

---

## 7. Secure Development Lifecycle

### 7.1 Code Security

**Practices:**
- **Static Analysis:** SonarQube, ESLint security rules
- **Secret Scanning:** GitGuardian, git-secrets
- **Dependency Scanning:** Snyk, OWASP Dependency-Check
- **Code Review:** Peer review required for all changes
- **Branch Protection:** Require PR approvals, passing CI checks

### 7.2 CI/CD Security

**Pipeline Security:**
```yaml
1. Source Code Scan:
   - Secret detection
   - License compliance
   - SAST (Static Application Security Testing)

2. Build:
   - Dependency vulnerability scan
   - Build in isolated environment
   - Sign artifacts

3. Test:
   - Unit tests
   - Integration tests
   - Security tests (DAST - Dynamic Application Security Testing)

4. Deploy:
   - Deploy to staging first
   - Smoke tests
   - Approval gate for production
   - Blue/green deployment

5. Post-Deploy:
   - Runtime security monitoring
   - Penetration testing (quarterly)
```

---

## 8. Security Monitoring & Alerting

### 8.1 CloudWatch Alarms

```yaml
Critical Alarms:
  - RDS CPU > 80% for 5 minutes
  - RDS storage < 10% free
  - ECS task failures > 5 in 10 minutes
  - ALB 5XX errors > 10 in 5 minutes
  - Failed login attempts > 10 in 1 minute
  - Certificate issuance failure rate > 20%

Warning Alarms:
  - API response time p95 > 500ms
  - Certificate expiring < 7 days
  - Pending approvals > 50
```

### 8.2 Security Dashboards

**CloudWatch Dashboard:**
- API request rate
- Error rate (4XX, 5XX)
- Authentication success/failure rate
- Certificate issuance metrics
- WAF blocked requests
- GuardDuty findings

**Grafana Dashboard:**
- Real-time metrics
- Custom queries
- Anomaly detection
- Historical trends

---

## 9. Third-Party Security

### 9.1 Vendor Assessment

**Criteria:**
- SOC 2 Type II certification
- ISO 27001 compliance
- Regular security audits
- Incident response plan
- Data handling practices

### 9.2 API Security

**External APIs (ADCS, Notification services):**
- API key rotation (90 days)
- IP whitelisting
- TLS mutual authentication
- Rate limiting
- Error handling (no sensitive data in errors)

---

## 10. Security Training

**Requirements:**
- **All Users:** Annual security awareness training
- **Developers:** Secure coding practices (quarterly)
- **Admins:** Incident response training (semi-annual)
- **Approvers:** Data classification and handling (annual)

**Topics:**
- Phishing awareness
- Password hygiene
- Social engineering
- Data classification
- Incident reporting

---

## Summary

This comprehensive security and compliance framework ensures:
- **Defense in Depth:** Multiple layers of security controls
- **Least Privilege:** Minimal access rights for all identities
- **Encryption Everywhere:** Data protected at rest and in transit
- **Comprehensive Audit:** Full visibility into all system activities
- **Compliance Ready:** Meets SOC 2, GDPR, PCI DSS, HIPAA requirements
- **Incident Response:** Prepared to detect, respond, and recover from security events
- **Continuous Improvement:** Regular testing, monitoring, and updates

The system is designed to handle sensitive certificate data with the highest level of security while maintaining usability and operational efficiency.
