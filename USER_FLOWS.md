# User Flows - AWS Certificate Decision Assistant

## Overview

This document details the user journeys through the AWS Certificate Decision Assistant system, covering all major use cases from initial login through certificate lifecycle management.

---

## 1. New User Onboarding Flow

### Flow Diagram
```
Start → SSO Login → First-Time Setup → Dashboard → End
```

### Detailed Steps

1. **User Accesses Application**
   - User navigates to `https://cert-assistant.example.com`
   - System detects no active session
   - Redirect to SSO login page

2. **SSO Authentication**
   - User authenticates with corporate credentials
   - IdP validates credentials and returns SAML assertion/OAuth token
   - System validates assertion/token
   - Creates user record (JIT provisioning)
   - Generates JWT session token

3. **First-Time Setup (Optional)**
   - Welcome screen with quick tour
   - Profile confirmation (name, department, email)
   - Preference settings (notification preferences)
   - Brief tutorial on how to request certificates

4. **Dashboard Display**
   - Show personalized dashboard
   - Quick start guide for first-time users
   - Highlight "Request Certificate" button

### User Interactions
- **Input:** Username/password at IdP
- **Decision:** Accept/decline notification preferences
- **Output:** Access to main dashboard

---

## 2. Certificate Request Flow (Standard Path)

### Flow Diagram
```
Dashboard → Recommendation Engine → Fill Request Form → Review → Submit → 
Approval → Certificate Issued → Download → Complete
```

### Detailed Steps

#### Step 1: Initiate Request
- User clicks "New Certificate Request" from dashboard
- System displays recommendation questionnaire

#### Step 2: Recommendation Engine
**Questions (11 total):**

1. **Service Type**
   - Radio buttons: Web server, Database, API, Email, VPN, Code signing, Other
   - User selects: "Web server"

2. **Public Accessibility**
   - Radio buttons: Yes, No, Hybrid
   - User selects: "Yes"

3. **Certificate Lifespan**
   - Dropdown: <90 days, 90-365 days, 1-2 years, >2 years
   - User selects: "1-2 years"

4. **Browser Trust Required**
   - Radio buttons: Yes, No, Partial
   - User selects: "Yes"

5. **Environment**
   - Radio buttons: Production, Development, Testing, Sandbox
   - User selects: "Production"

6. **Certificate Count**
   - Radio buttons: Single, Multiple (2-10), Bulk (>10)
   - User selects: "Single"

7. **Domain Type**
   - Radio buttons: Single domain, Wildcard, Multi-domain (SAN)
   - User selects: "Single domain"

8. **Criticality Level**
   - Radio buttons: Critical, High, Medium, Low
   - User selects: "High"

9. **Compliance Requirements**
   - Checkboxes: PCI DSS, HIPAA, SOC 2, ISO 27001, None
   - User selects: "PCI DSS, SOC 2"

10. **Key Size Preference**
    - Dropdown: RSA 2048, RSA 4096, ECC P-256, ECC P-384
    - User selects: "RSA 2048"

11. **Renewal Preference**
    - Radio buttons: Automatic, Manual, Notification only
    - User selects: "Notification only"

**System Processing:**
- Evaluates responses against decision tree
- Calculates recommendation score
- Determines: Public CA vs Internal CA

**Recommendation Display:**
```
┌─────────────────────────────────────────────────┐
│ Recommendation: Public CA                       │
│                                                  │
│ Based on your responses, a Public CA is         │
│ recommended because:                             │
│ - Service is publicly accessible                │
│ - Browser trust is required                     │
│ - Production environment                         │
│                                                  │
│ Suggested Public CAs:                            │
│ • DigiCert (link)                               │
│ • Let's Encrypt (link)                          │
│                                                  │
│ [Continue with Public CA] [Use Internal CA]     │
└─────────────────────────────────────────────────┘
```

**User Decision:**
- Option A: Click "Continue with Public CA" → Redirect to external CA portal → End flow
- Option B: Click "Use Internal CA" → Show justification form → Continue to Step 3

#### Step 3: Fill Certificate Request Form (Internal CA)

**Form Fields:**

**Certificate Details:**
- Common Name (CN): `app.example.com` *
- Organization (O): `Example Corp` *
- Organizational Unit (OU): `Engineering`
- Locality (L): `Seattle`
- State/Province (ST): `Washington`
- Country (C): `US` * (dropdown)
- Email Address: `admin@example.com` *

**Subject Alternative Names (SANs):**
- + Add SAN button
- Input fields for additional domains
- Example: `www.example.com`, `api.example.com`

**Certificate Type:**
- Dropdown: Web server, Email, Code signing, VPN, Database, User authentication, Other
- Pre-filled from recommendation: "Web server"

**Key Algorithm:**
- Radio buttons: RSA 2048, RSA 4096, ECC P-256, ECC P-384
- Pre-filled: "RSA 2048"

**Validity Period:**
- Radio buttons: 90 days, 1 year, 2 years
- Selected: "1 year"

**CSR Generation:**
- Radio buttons: Generate CSR in portal, Upload existing CSR
- User selects: "Generate CSR in portal"

**If "Generate CSR":**
```
┌─────────────────────────────────────────────────┐
│ Generate Certificate Signing Request            │
│                                                  │
│ Your browser will generate a CSR and private    │
│ key securely using Web Crypto API.              │
│                                                  │
│ [Generate CSR]                                   │
│                                                  │
│ ⚠️  Important: Download your private key now!   │
│    You will NOT be able to retrieve it later.   │
│                                                  │
│ CSR Preview:                                     │
│ -----BEGIN CERTIFICATE REQUEST-----              │
│ MIICvDCCAaQCAQAwdzELMAkGA1UE...              │
│ -----END CERTIFICATE REQUEST-----                │
│                                                  │
│ [Download Private Key] [Copy CSR]               │
└─────────────────────────────────────────────────┘
```

**If "Upload CSR":**
```
┌─────────────────────────────────────────────────┐
│ Upload Certificate Signing Request              │
│                                                  │
│ [Choose File] or drag and drop                  │
│                                                  │
│ Or paste CSR text:                               │
│ ┌─────────────────────────────────────────────┐ │
│ │ -----BEGIN CERTIFICATE REQUEST-----         │ │
│ │ ...                                         │ │
│ │ -----END CERTIFICATE REQUEST-----           │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ CSR Details (auto-extracted):                    │
│ • Common Name: app.example.com                  │
│ • Organization: Example Corp                    │
│ • Key Size: RSA 2048                            │
│                                                  │
│ ✓ CSR validated successfully                    │
└─────────────────────────────────────────────────┘
```

**Business Justification:**
- Text area (min 50 characters): *
- "SSL certificate for new customer-facing web application"

**Additional Information:**
- Department: `Engineering`
- Cost Center: `CC-1234`
- Project Code: `PROJ-567`
- Additional Notes: (optional)

**Approver Selection:**
- Autocomplete field: Search by name or email
- Selected: `Jane Smith (jane.smith@example.com)`

#### Step 4: Review Request

```
┌─────────────────────────────────────────────────────────┐
│ Review Certificate Request                              │
│                                                          │
│ Request Details:                                         │
│ • Common Name: app.example.com                          │
│ • Organization: Example Corp                            │
│ • SANs: www.example.com, api.example.com               │
│ • Key Algorithm: RSA 2048                               │
│ • Validity: 1 year                                      │
│ • Approver: Jane Smith                                  │
│                                                          │
│ Business Justification:                                  │
│ SSL certificate for new customer-facing web application │
│                                                          │
│ Estimated Issuance Time: 2-3 business days              │
│                                                          │
│ [Edit] [Cancel] [Submit Request]                        │
└─────────────────────────────────────────────────────────┘
```

#### Step 5: Submit Request

**Confirmation Dialog:**
```
┌─────────────────────────────────────────────────┐
│ Confirm Submission                               │
│                                                  │
│ Are you sure you want to submit this request?   │
│                                                  │
│ Once submitted:                                  │
│ • Your approver will be notified                │
│ • You cannot edit the request                   │
│ • You will receive status updates via email     │
│                                                  │
│ [Cancel] [Confirm]                               │
└─────────────────────────────────────────────────┘
```

**After Submission:**
```
┌─────────────────────────────────────────────────┐
│ ✓ Request Submitted Successfully                │
│                                                  │
│ Request Number: REQ-20240115-00001              │
│                                                  │
│ Your request has been sent to Jane Smith for    │
│ approval. You will receive email notifications  │
│ on status changes.                               │
│                                                  │
│ [View Request] [Return to Dashboard]            │
└─────────────────────────────────────────────────┘
```

**System Actions:**
- Create request record in database
- Generate unique request number
- Send email to approver
- Send confirmation email to requester
- Create audit log entry
- Update request status to "pending_approval"

---

## 3. Approval Flow (Approver Journey)

### Flow Diagram
```
Email Notification → Login → Approval Queue → Review Request → 
Approve/Reject → Notification Sent → End
```

### Detailed Steps

#### Step 1: Notification
Approver receives email:
```
Subject: Certificate Request Awaiting Your Approval

Hi Jane,

You have a new certificate request awaiting approval:

Request Number: REQ-20240115-00001
Requester: John Doe (john.doe@example.com)
Common Name: app.example.com
Certificate Type: Web server
Submitted: Jan 15, 2024 10:30 AM

View Request: [Link to approval page]

--
AWS Certificate Decision Assistant
```

#### Step 2: Access Approval Queue
- Approver logs in via SSO
- Dashboard shows "Pending Approvals" widget with count
- Click "View All Pending Approvals"

**Approval Queue View:**
```
┌───────────────────────────────────────────────────────────────────┐
│ Pending Approvals (5)                          [Search] [Filter] │
├───────────────────────────────────────────────────────────────────┤
│ Request #      │ Requester  │ Common Name      │ Age  │ Action   │
├───────────────────────────────────────────────────────────────────┤
│ REQ-20240115-01│ John Doe   │ app.example.com  │ 2h   │ [Review] │
│ REQ-20240114-23│ Alice Lee  │ api.example.com  │ 1d   │ [Review] │
│ REQ-20240113-15│ Bob Chen   │ db.example.com   │ 2d⚠️ │ [Review] │
└───────────────────────────────────────────────────────────────────┘
⚠️ = Escalation threshold reached (48 hours)
```

#### Step 3: Review Request Details
Click "Review" on REQ-20240115-00001:

```
┌─────────────────────────────────────────────────────────┐
│ Certificate Request Review                              │
│ REQ-20240115-00001                                      │
├─────────────────────────────────────────────────────────┤
│ Requester Information:                                   │
│ • Name: John Doe                                        │
│ • Email: john.doe@example.com                           │
│ • Department: Engineering                               │
│ • Submitted: Jan 15, 2024 10:30 AM                      │
│                                                          │
│ Certificate Details:                                     │
│ • Common Name: app.example.com                          │
│ • Organization: Example Corp                            │
│ • SANs: www.example.com, api.example.com               │
│ • Key Algorithm: RSA 2048                               │
│ • Validity: 1 year                                      │
│ • Certificate Type: Web server                          │
│                                                          │
│ Business Justification:                                  │
│ SSL certificate for new customer-facing web application │
│                                                          │
│ Project Information:                                     │
│ • Department: Engineering                               │
│ • Cost Center: CC-1234                                  │
│ • Project Code: PROJ-567                                │
│                                                          │
│ CSR Preview: [View CSR]                                 │
│                                                          │
│ Recommendation:                                          │
│ • Recommended CA: Public CA                             │
│ • Override: Using Internal CA (justification required)  │
│                                                          │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Comments (optional):                                 │ │
│ │                                                      │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                          │
│ [Approve] [Reject] [Delegate] [Request More Info]      │
└─────────────────────────────────────────────────────────┘
```

#### Step 4: Approve/Reject Decision

**If Approve:**
```
┌─────────────────────────────────────────────────┐
│ Approve Request                                  │
│                                                  │
│ Comments (optional):                             │
│ ┌─────────────────────────────────────────────┐ │
│ │ Approved for Q1 2024 product launch         │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ [Cancel] [Confirm Approval]                      │
└─────────────────────────────────────────────────┘
```

**If Reject:**
```
┌─────────────────────────────────────────────────┐
│ Reject Request                                   │
│                                                  │
│ Comments (required):                             │
│ ┌─────────────────────────────────────────────┐ │
│ │ Insufficient business justification.        │ │
│ │ Please provide more details about the       │ │
│ │ application and why a certificate is needed.│ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ [Cancel] [Confirm Rejection]                     │
└─────────────────────────────────────────────────┘
```

#### Step 5: Confirmation

**After Approval:**
```
┌─────────────────────────────────────────────────┐
│ ✓ Request Approved                               │
│                                                  │
│ REQ-20240115-00001 has been approved and queued │
│ for certificate issuance.                        │
│                                                  │
│ The requester will be notified and the          │
│ certificate will be issued automatically.        │
│                                                  │
│ [Return to Approval Queue] [Dashboard]          │
└─────────────────────────────────────────────────┘
```

**System Actions:**
- Update request status to "approved"
- Send approval to certificate issuance queue (SQS)
- Send email notification to requester
- Create audit log entry
- Trigger ADCS integration process

---

## 4. Certificate Issuance Flow (Background Process)

### Flow Diagram
```
Approval → Queue → ADCS Submission → Polling → 
Certificate Retrieval → Storage → User Notification
```

### Process Steps

1. **Queue Processing**
   - Worker picks up approved request from SQS queue
   - Validates request data
   - Prepares CSR for ADCS

2. **ADCS Submission**
   - Connect to ADCS server via VPN/Direct Connect
   - Submit CSR using certreq API
   - Receive request ID from ADCS
   - Update request status to "in_progress"

3. **Status Polling**
   - Poll ADCS every 30 seconds for status
   - Check for: Pending, Issued, Failed
   - Max polling duration: 10 minutes
   - Timeout → Retry (3 attempts)

4. **Certificate Retrieval**
   - On "Issued" status, retrieve certificate from ADCS
   - Download full certificate chain (root + intermediates)
   - Validate certificate content
   - Extract metadata (serial number, validity dates)

5. **Storage**
   - Upload certificate to S3 (certificates bucket)
   - Upload chain to S3
   - Encrypt with KMS
   - Store metadata in RDS database
   - Update request status to "issued"

6. **User Notification**
   - Send email with download link
   - Create dashboard notification
   - Schedule expiry monitoring

**Email to Requester:**
```
Subject: Your Certificate Has Been Issued

Hi John,

Great news! Your certificate has been issued successfully.

Request Number: REQ-20240115-00001
Common Name: app.example.com
Serial Number: 1A2B3C4D5E6F
Valid From: Jan 15, 2024
Valid To: Jan 15, 2025

Download your certificate: [Link]

Important: This certificate will expire on Jan 15, 2025. You will 
receive reminders before expiration.

--
AWS Certificate Decision Assistant
```

---

## 5. Certificate Download Flow

### Flow Diagram
```
Dashboard → Certificate List → Select Certificate → 
Download Options → Download → Complete
```

### Detailed Steps

#### Step 1: Navigate to Certificates
- User clicks "My Certificates" from dashboard
- System displays list of user's certificates

**Certificate List View:**
```
┌───────────────────────────────────────────────────────────────────┐
│ My Certificates (8)                         [Search] [Filter]    │
├───────────────────────────────────────────────────────────────────┤
│ Common Name      │ Status  │ Valid To      │ Days Left │ Action  │
├───────────────────────────────────────────────────────────────────┤
│ app.example.com  │ Active  │ Jan 15, 2025  │ 365      │ [View]  │
│ api.example.com  │ Active  │ Dec 1, 2024   │ 320      │ [View]  │
│ old.example.com  │ Active  │ Feb 15, 2024  │ 30⚠️     │ [View]  │
│ test.example.com │ Expired │ Jan 1, 2024   │ -14      │ [View]  │
└───────────────────────────────────────────────────────────────────┘
⚠️ = Expiring soon (< 30 days)
```

#### Step 2: Certificate Details
Click "View" on app.example.com:

```
┌─────────────────────────────────────────────────────────┐
│ Certificate Details                                      │
│ app.example.com                                          │
├─────────────────────────────────────────────────────────┤
│ Status: Active ✓                                         │
│                                                          │
│ Certificate Information:                                 │
│ • Serial Number: 1A2B3C4D5E6F                           │
│ • Thumbprint (SHA-256): abc123...                       │
│ • Common Name: app.example.com                          │
│ • Organization: Example Corp                            │
│ • SANs: www.example.com, api.example.com               │
│                                                          │
│ Validity:                                                │
│ • Valid From: Jan 15, 2024 00:00:00 UTC                 │
│ • Valid To: Jan 15, 2025 00:00:00 UTC                   │
│ • Days Remaining: 365                                    │
│                                                          │
│ Key Information:                                         │
│ • Algorithm: RSA                                         │
│ • Key Size: 2048 bits                                    │
│ • Signature Algorithm: SHA256withRSA                    │
│                                                          │
│ Issuer:                                                  │
│ • CN: Internal CA, O: Example Corp, C: US               │
│                                                          │
│ Request Details:                                         │
│ • Request Number: REQ-20240115-00001                    │
│ • Issued On: Jan 15, 2024 14:30:00 UTC                  │
│ • Downloaded: 3 times                                    │
│                                                          │
│ [Download Certificate] [Revoke Certificate]             │
└─────────────────────────────────────────────────────────┘
```

#### Step 3: Download Options
Click "Download Certificate":

```
┌─────────────────────────────────────────────────┐
│ Download Certificate                             │
│                                                  │
│ Format:                                          │
│ ○ PEM (Base64 encoded)                          │
│ ○ DER (Binary)                                   │
│ ○ PKCS#12 (.pfx/.p12)                           │
│                                                  │
│ Include Certificate Chain:                       │
│ ☑ Include intermediate certificates             │
│ ☑ Include root certificate                       │
│                                                  │
│ Password for PKCS#12 (if selected):              │
│ [________________]                               │
│                                                  │
│ [Cancel] [Download]                              │
└─────────────────────────────────────────────────┘
```

#### Step 4: Download File
- System generates signed S3 URL (15-minute expiration)
- Browser downloads file
- System logs download in audit trail
- Update download counter

**Downloaded Files:**
- `app.example.com.pem` (certificate)
- `app.example.com-chain.pem` (full chain)
- `app.example.com.key` (private key, if generated by system and not yet downloaded)

---

## 6. Certificate Revocation Flow

### Flow Diagram
```
Certificate Details → Request Revocation → Provide Reason → 
Approval (if required) → ADCS Revocation → CRL Update → Complete
```

### Detailed Steps

#### Step 1: Initiate Revocation
From certificate details page, click "Revoke Certificate":

```
┌─────────────────────────────────────────────────┐
│ ⚠️  Revoke Certificate                           │
│                                                  │
│ Warning: Certificate revocation is permanent and │
│ cannot be undone. The certificate will be added │
│ to the Certificate Revocation List (CRL).       │
│                                                  │
│ Are you sure you want to continue?              │
│                                                  │
│ [Cancel] [Continue]                              │
└─────────────────────────────────────────────────┘
```

#### Step 2: Provide Revocation Reason
After clicking "Continue":

```
┌─────────────────────────────────────────────────┐
│ Certificate Revocation Request                   │
│                                                  │
│ Certificate: app.example.com                     │
│ Serial Number: 1A2B3C4D5E6F                     │
│                                                  │
│ Reason for Revocation: *                         │
│ ○ Unspecified                                    │
│ ● Key Compromise                                 │
│ ○ CA Compromise                                  │
│ ○ Affiliation Changed                            │
│ ○ Superseded                                     │
│ ○ Cessation of Operation                         │
│ ○ Certificate Hold                               │
│                                                  │
│ Additional Details: *                            │
│ ┌─────────────────────────────────────────────┐ │
│ │ Private key was accidentally committed to   │ │
│ │ public GitHub repository. Key has been      │ │
│ │ removed but may have been exposed.          │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ [Cancel] [Submit Revocation Request]            │
└─────────────────────────────────────────────────┘
```

#### Step 3: Confirmation & Processing
**Immediate Revocation (for key compromise):**
```
┌─────────────────────────────────────────────────┐
│ ✓ Revocation Request Submitted                   │
│                                                  │
│ Due to the critical nature of this request       │
│ (key compromise), the certificate has been       │
│ immediately revoked.                             │
│                                                  │
│ Revocation ID: REV-20240115-00001               │
│                                                  │
│ The certificate has been:                        │
│ • Added to the CRL                              │
│ • Marked as revoked in OCSP                     │
│ • Disabled for download                         │
│                                                  │
│ Administrator has been notified.                 │
│                                                  │
│ [View Certificate] [Return to Dashboard]        │
└─────────────────────────────────────────────────┘
```

**System Actions:**
- Submit revocation to ADCS
- Update CRL
- Update OCSP responder
- Update certificate status to "revoked"
- Send notification to admin and user
- Create audit log entry

---

## 7. Certificate Expiry Notification Flow

### Flow Diagram
```
Daily Scan → Identify Expiring Certificates → Generate Notifications → 
Send Emails → User Action (Renew/Ignore)
```

### Notification Schedule

**90 days before expiry:**
```
Subject: Certificate Expiring in 90 Days - app.example.com

Hi John,

This is a reminder that your certificate will expire in 90 days:

Common Name: app.example.com
Serial Number: 1A2B3C4D5E6F
Expires On: Jan 15, 2025

To ensure uninterrupted service, please request a renewal 
certificate before expiration.

[Request Renewal] [View Certificate]

--
AWS Certificate Decision Assistant
```

**30 days before expiry:**
```
Subject: URGENT: Certificate Expiring in 30 Days - app.example.com

Hi John,

⚠️ Your certificate will expire in 30 days:
...
```

**7 days before expiry:**
```
Subject: CRITICAL: Certificate Expiring in 7 Days - app.example.com

Hi John,

🚨 Your certificate will expire in 7 days:
...
```

**Daily reminders for last 7 days**

---

## 8. Admin Dashboard Flow

### Admin-Specific Features

**System Overview:**
```
┌───────────────────────────────────────────────────────────────┐
│ Admin Dashboard                                               │
├───────────────────────────────────────────────────────────────┤
│ System Statistics:                                            │
│ • Total Users: 150                                            │
│ • Active Certificates: 450                                    │
│ • Pending Requests: 23                                        │
│ • Certificates Expiring (30 days): 15                         │
│                                                                │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│ │  Requests   │  │Certificates │  │   Approvals │           │
│ │  This Month │  │   Issued    │  │  Avg Time   │           │
│ │     150     │  │     120     │  │   8.5 hrs   │           │
│ └─────────────┘  └─────────────┘  └─────────────┘           │
│                                                                │
│ Recent Activity:                                               │
│ • Certificate issued: api.example.com (5 min ago)            │
│ • Request approved: db.example.com (15 min ago)              │
│ • Certificate revoked: old.example.com (1 hour ago)          │
│                                                                │
│ Quick Actions:                                                 │
│ [View All Requests] [Audit Logs] [System Config]             │
└───────────────────────────────────────────────────────────────┘
```

**Audit Log Viewer:**
```
┌───────────────────────────────────────────────────────────────────┐
│ Audit Logs                      [Export] [Search] [Filter]       │
├───────────────────────────────────────────────────────────────────┤
│ Timestamp         │ Event          │ User        │ Resource      │
├───────────────────────────────────────────────────────────────────┤
│ Jan 15 14:30:00  │ Cert Downloaded│ john.doe    │ 1A2B3C4D5E6F │
│ Jan 15 14:25:00  │ Cert Issued    │ SYSTEM      │ 1A2B3C4D5E6F │
│ Jan 15 12:00:00  │ Request Approve│ jane.smith  │ REQ-001      │
│ Jan 15 10:30:00  │ Request Created│ john.doe    │ REQ-001      │
│ Jan 15 10:00:00  │ User Login     │ john.doe    │ -            │
└───────────────────────────────────────────────────────────────────┘
```

---

## Summary

This document covers 8 major user flows:
1. **New User Onboarding** - SSO login and first-time setup
2. **Certificate Request** - Complete journey from recommendation to submission
3. **Approval Process** - Approver workflow
4. **Certificate Issuance** - Background automation
5. **Certificate Download** - Retrieving issued certificates
6. **Certificate Revocation** - Emergency revocation workflow
7. **Expiry Notifications** - Automated reminder system
8. **Admin Dashboard** - System administration and monitoring

Each flow is designed for:
- **User-friendly experience** with clear guidance
- **Security** at every step
- **Transparency** with status updates
- **Automation** where possible
- **Audit trail** for compliance
