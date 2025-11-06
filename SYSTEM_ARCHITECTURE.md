# AWS Certificate Decision Assistant - System Architecture

## Overview

The AWS Certificate Decision Assistant is a web-based platform that helps users determine the appropriate Certificate Authority (CA) for their needs through an intelligent decision tree, and then facilitates the entire certificate lifecycle management process.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  React/Angular SPA                                        │   │
│  │  - Decision Tree UI                                       │   │
│  │  - Certificate Request Forms                              │   │
│  │  - Dashboard & Monitoring                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTPS
┌─────────────────────────────────────────────────────────────────┐
│                     Load Balancer Layer                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Application Load Balancer (ALB)                          │   │
│  │  - SSL/TLS Termination                                    │   │
│  │  - WAF Integration                                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                            │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │  Backend API     │  │  Worker Services │                     │
│  │  (Node.js/Python)│  │  (Async Tasks)   │                     │
│  │  - REST APIs     │  │  - CSR Generation│                     │
│  │  - Auth/AuthZ    │  │  - ADCS Polling  │                     │
│  │  - Business Logic│  │  - Notifications │                     │
│  └──────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
           ↓                    ↓                    ↓
┌────────────────┐  ┌──────────────────┐  ┌───────────────────┐
│  Message Queue │  │   Data Layer     │  │  Storage Layer    │
│  (SQS)         │  │   AWS RDS        │  │   AWS S3          │
│  - Cert Tasks  │  │   PostgreSQL     │  │   - Certificates  │
│  - Notifications│  │   - Users        │  │   - Private Keys  │
│                │  │   - Requests     │  │   - Audit Logs    │
└────────────────┘  │   - Certificates │  └───────────────────┘
                    │   - Audit Logs   │
                    └──────────────────┘
           ↓
┌─────────────────────────────────────────────────────────────────┐
│                  External Integrations                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  ADCS Server │  │  SSO Provider│  │  Notification Service│  │
│  │  (On-Premise)│  │  (SAML/OAuth)│  │  (SES/SNS/Slack)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend Layer (React/Angular)

**Technology Stack:**
- Framework: React 18+ with TypeScript or Angular 15+
- State Management: Redux Toolkit (React) or NgRx (Angular)
- UI Components: Material-UI or Ant Design
- Build Tool: Vite or Webpack
- Hosting: Amazon S3 + CloudFront

**Key Features:**
- Multi-step decision tree questionnaire (11+ questions)
- Certificate request form with CSR generation/upload
- Dashboard for tracking requests
- Admin panel for approvals
- Certificate download interface
- Audit log viewer

**Pages/Routes:**
- `/login` - SSO login page
- `/dashboard` - User dashboard
- `/recommend` - Decision tree questionnaire
- `/request/new` - New certificate request
- `/request/:id` - Request details
- `/certificates` - List of certificates
- `/admin/approvals` - Approval queue (admin only)
- `/admin/audit` - Audit logs (admin only)

### 2. Backend API Layer

**Technology Stack:**
- Runtime: Node.js (Express/NestJS) or Python (FastAPI/Django)
- Language: TypeScript/JavaScript or Python 3.11+
- API Style: RESTful with JSON
- Authentication: JWT tokens from SSO
- Hosting: ECS Fargate or Lambda (API Gateway)

**Core Services:**

#### a. Authentication Service
- SSO integration (SAML 2.0 or OAuth 2.0/OIDC)
- JWT token generation and validation
- Role-based access control (RBAC)
- Session management

#### b. Recommendation Engine Service
- Decision tree logic implementation
- Question flow management
- CA recommendation algorithm
- Justification handling for public CA override

#### c. Certificate Request Service
- Request creation and validation
- CSR generation (using OpenSSL/crypto libraries)
- CSR upload and validation
- Request status tracking

#### d. Approval Workflow Service
- Approval queue management
- Notification to approvers
- Approval/rejection logic
- Escalation handling

#### e. ADCS Integration Service
- Communication with on-premise ADCS
- Certificate request submission
- Status polling
- Certificate retrieval
- Revocation requests

#### f. Certificate Management Service
- Certificate storage (S3)
- Certificate retrieval
- Expiry tracking
- Revocation management

#### g. Audit Service
- Comprehensive event logging
- Compliance reporting
- Audit trail generation

#### h. Notification Service
- Email notifications (SES)
- Slack/Teams integration
- SMS alerts (SNS) for critical events

### 3. Data Layer (AWS RDS)

**Database:** PostgreSQL 15+ or MySQL 8+

**Schema Design:** See DATABASE_SCHEMA.md

**Key Features:**
- Multi-AZ deployment for high availability
- Automated backups (point-in-time recovery)
- Read replicas for scaling
- Encryption at rest (KMS)
- Encryption in transit (SSL/TLS)

### 4. Storage Layer (AWS S3)

**Buckets:**

1. **Certificates Bucket** (`cert-assistant-certificates-{env}`)
   - Purpose: Store issued certificates
   - Encryption: SSE-KMS
   - Versioning: Enabled
   - Lifecycle: Retain for 7 years (compliance)
   - Access: Private, signed URLs for download

2. **Private Keys Bucket** (`cert-assistant-keys-{env}`)
   - Purpose: Store private keys (if generated by system)
   - Encryption: SSE-KMS with dedicated key
   - Versioning: Enabled
   - Lifecycle: Retain per policy, delete on revocation
   - Access: Highly restricted, audit all access

3. **Audit Logs Bucket** (`cert-assistant-audit-{env}`)
   - Purpose: Long-term audit log storage
   - Encryption: SSE-KMS
   - Versioning: Enabled
   - Lifecycle: Retain for 10 years
   - Access: Read-only for compliance team

### 5. Message Queue Layer (AWS SQS)

**Queues:**

1. **Certificate Processing Queue**
   - Purpose: Async certificate issuance tasks
   - DLQ: Yes, with 3 retry attempts
   - Visibility timeout: 5 minutes

2. **Notification Queue**
   - Purpose: Send email/slack notifications
   - DLQ: Yes
   - Visibility timeout: 1 minute

3. **Expiry Monitoring Queue**
   - Purpose: Daily certificate expiry checks
   - Triggered by: CloudWatch Events/EventBridge
   - Visibility timeout: 10 minutes

### 6. ADCS Integration

**Architecture:**
- VPN/Direct Connect to on-premise network
- VPC Peering or Transit Gateway
- Secure communication over private network
- API wrapper around certreq command
- Status polling mechanism

**Communication Flow:**
1. API sends certificate request to ADCS host
2. ADCS host executes certreq command
3. Poll for status (pending/issued/error)
4. Retrieve certificate on success
5. Handle errors and retry logic

### 7. SSO Integration

**Supported Protocols:**
- SAML 2.0 (Azure AD, Okta, ADFS)
- OAuth 2.0 / OpenID Connect

**Implementation:**
- Identity Provider (IdP) integration
- Service Provider (SP) metadata configuration
- Attribute mapping (email, name, roles)
- Just-in-time (JIT) user provisioning

**User Attributes:**
- Email (unique identifier)
- Display Name
- Department
- Roles (user, approver, admin)

## AWS Services Architecture

### Compute
- **ECS Fargate:** Containerized backend API services
- **Lambda:** Serverless functions for async tasks
- **EC2 (optional):** ADCS integration host if needed

### Networking
- **VPC:** Isolated network environment
- **ALB:** Application load balancing
- **NAT Gateway:** Outbound internet access
- **VPN/Direct Connect:** On-premise connectivity
- **Route 53:** DNS management

### Security
- **IAM:** Fine-grained access control
- **KMS:** Encryption key management
- **Secrets Manager:** Database credentials, API keys
- **WAF:** Web application firewall
- **Security Groups:** Network-level security
- **ACM:** SSL/TLS certificates for ALB

### Monitoring & Logging
- **CloudWatch Logs:** Application logs
- **CloudWatch Metrics:** Performance monitoring
- **CloudWatch Alarms:** Alerting
- **X-Ray:** Distributed tracing
- **CloudTrail:** AWS API audit logs

### Data & Storage
- **RDS:** Relational database
- **S3:** Object storage
- **ElastiCache:** Redis for session/caching
- **DynamoDB (optional):** NoSQL for real-time data

### Messaging
- **SQS:** Message queues
- **SNS:** Pub/sub notifications
- **EventBridge:** Event-driven architecture

### Developer Tools
- **CodePipeline:** CI/CD pipeline
- **CodeBuild:** Build automation
- **CodeDeploy:** Deployment automation
- **ECR:** Container registry

## Deployment Architecture

### Environments
1. **Development** - Single AZ, minimal resources
2. **Staging** - Production-like, single AZ
3. **Production** - Multi-AZ, auto-scaling, high availability

### Regions
- **Primary:** us-east-1 (or preferred region)
- **DR (optional):** us-west-2 for disaster recovery

### Multi-AZ Strategy
```
┌─────────────────────────────────────────────────────────┐
│                      VPC (10.0.0.0/16)                  │
│                                                          │
│  ┌──────────────────────┐  ┌──────────────────────┐    │
│  │  Availability Zone A  │  │  Availability Zone B │    │
│  │                       │  │                      │    │
│  │  ┌─────────────────┐ │  │  ┌─────────────────┐│    │
│  │  │ Public Subnet   │ │  │  │ Public Subnet   ││    │
│  │  │ - ALB           │ │  │  │ - ALB           ││    │
│  │  │ - NAT Gateway   │ │  │  │ - NAT Gateway   ││    │
│  │  └─────────────────┘ │  │  └─────────────────┘│    │
│  │                       │  │                      │    │
│  │  ┌─────────────────┐ │  │  ┌─────────────────┐│    │
│  │  │ Private Subnet  │ │  │  │ Private Subnet  ││    │
│  │  │ - ECS Tasks     │ │  │  │ - ECS Tasks     ││    │
│  │  │ - Lambda        │ │  │  │ - Lambda        ││    │
│  │  └─────────────────┘ │  │  └─────────────────┘│    │
│  │                       │  │                      │    │
│  │  ┌─────────────────┐ │  │  ┌─────────────────┐│    │
│  │  │ Data Subnet     │ │  │  │ Data Subnet     ││    │
│  │  │ - RDS Primary   │ │  │  │ - RDS Standby   ││    │
│  │  │ - ElastiCache   │ │  │  │ - ElastiCache   ││    │
│  │  └─────────────────┘ │  │  └─────────────────┘│    │
│  └──────────────────────┘  └──────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Security Architecture

### Defense in Depth

1. **Network Security**
   - VPC isolation
   - Security groups (least privilege)
   - Network ACLs
   - Private subnets for backend
   - WAF for web layer

2. **Application Security**
   - SSO/OAuth authentication
   - JWT token validation
   - Role-based authorization
   - Input validation and sanitization
   - CSRF protection
   - Rate limiting

3. **Data Security**
   - Encryption at rest (KMS)
   - Encryption in transit (TLS 1.2+)
   - Database credential rotation (Secrets Manager)
   - S3 bucket policies (deny public access)
   - Signed URLs for temporary access

4. **Operational Security**
   - Least privilege IAM policies
   - MFA for admin access
   - Audit logging (CloudTrail, application logs)
   - Security scanning (Inspector, GuardDuty)
   - Vulnerability management

5. **Compliance**
   - SOC 2 Type II controls
   - GDPR data handling
   - PCI DSS for sensitive data
   - Audit trail retention (10 years)

## Scalability & Performance

### Auto-Scaling Configuration
- **ECS Services:** Target tracking (CPU/Memory 70%)
- **Database:** Read replicas for read-heavy workload
- **Cache:** ElastiCache for session and frequently accessed data

### Performance Targets
- API response time: < 200ms (p95)
- Certificate issuance: < 5 minutes (end-to-end)
- Dashboard load time: < 2 seconds
- Concurrent users: 1000+ (scalable)

## Disaster Recovery

### Backup Strategy
- **RDS:** Automated daily backups, 7-day retention
- **S3:** Versioning enabled, cross-region replication (optional)
- **Database snapshots:** Weekly manual snapshots, 30-day retention

### Recovery Objectives
- **RTO (Recovery Time Objective):** 1 hour
- **RPO (Recovery Point Objective):** 5 minutes

### DR Plan
1. Monitor health via CloudWatch
2. Automated failover for RDS Multi-AZ
3. Manual failover to DR region if needed
4. Runbook for disaster recovery procedures

## Cost Optimization

### Strategies
- Right-sizing ECS tasks and instances
- S3 Intelligent-Tiering for long-term storage
- Reserved Instances for predictable workloads
- Auto-scaling to match demand
- CloudWatch cost alarms

### Estimated Monthly Cost (Production)
- **Compute (ECS):** $300-500
- **Database (RDS):** $400-600
- **Storage (S3):** $50-100
- **Networking (ALB, NAT):** $100-150
- **Other Services:** $100-200
- **Total:** ~$1000-1550/month

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React/Angular + TypeScript | SPA web application |
| Backend | Node.js/Python | REST API services |
| Database | PostgreSQL/MySQL (RDS) | Relational data storage |
| Cache | Redis (ElastiCache) | Session & data caching |
| Storage | S3 | Certificate & log storage |
| Queue | SQS | Async task processing |
| Auth | SAML/OAuth + JWT | SSO integration |
| Monitoring | CloudWatch + X-Ray | Observability |
| Deployment | ECS Fargate | Container orchestration |
| CI/CD | CodePipeline | Automated deployment |

## Next Steps

Refer to the following documents for detailed specifications:
- `FUNCTIONAL_REQUIREMENTS.md` - Feature specifications
- `DATABASE_SCHEMA.md` - Data model design
- `API_SPECIFICATION.md` - REST API documentation
- `SECURITY_COMPLIANCE.md` - Security controls & compliance
- `DEPLOYMENT_GUIDE.md` - Infrastructure & deployment
- `USER_FLOWS.md` - User journey documentation
