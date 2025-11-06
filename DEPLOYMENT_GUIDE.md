# Deployment Guide - AWS Certificate Decision Assistant

## Infrastructure as Code (IaC)

All infrastructure is defined using **Terraform** for reproducibility, version control, and automation.

## AWS Account Structure

### Multi-Account Strategy

```
┌─────────────────────────────────────────────────────┐
│ AWS Organization                                    │
│                                                      │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │  Management      │  │  Security/Audit  │        │
│  │  Account         │  │  Account         │        │
│  └──────────────────┘  └──────────────────┘        │
│                                                      │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │  Development     │  │  Staging         │        │
│  │  Account         │  │  Account         │        │
│  └──────────────────┘  └──────────────────┘        │
│                                                      │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │  Production      │  │  DR (optional)   │        │
│  │  Account         │  │  Account         │        │
│  └──────────────────┘  └──────────────────┘        │
└─────────────────────────────────────────────────────┘
```

### Service Control Policies (SCPs)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Action": [
        "s3:PutBucketPublicAccessBlock",
        "s3:PutAccountPublicAccessBlock"
      ],
      "Resource": "*",
      "Condition": {
        "BoolIfExists": {
          "s3:DisablePublicAccess": "false"
        }
      }
    },
    {
      "Effect": "Deny",
      "Action": "rds:CreateDBInstance",
      "Resource": "*",
      "Condition": {
        "BoolIfExists": {
          "rds:StorageEncrypted": "false"
        }
      }
    }
  ]
}
```

---

## Terraform Structure

```
terraform/
├── modules/
│   ├── networking/          # VPC, subnets, security groups
│   ├── compute/             # ECS, Lambda
│   ├── database/            # RDS
│   ├── storage/             # S3 buckets
│   ├── messaging/           # SQS, SNS
│   ├── security/            # IAM, KMS, Secrets Manager
│   ├── monitoring/          # CloudWatch, alarms
│   └── cdn/                 # CloudFront, ACM
│
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   │   └── ...
│   └── production/
│       └── ...
│
├── backend.tf               # S3 backend for state
└── versions.tf              # Provider versions
```

### Backend Configuration

**backend.tf:**
```hcl
terraform {
  backend "s3" {
    bucket         = "cert-assistant-terraform-state"
    key            = "environments/${var.environment}/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    kms_key_id     = "arn:aws:kms:us-east-1:123456789012:key/..."
    dynamodb_table = "terraform-state-lock"
  }
}
```

---

## Infrastructure Components

### 1. Networking Module

**modules/networking/main.tf:**
```hcl
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.environment}-cert-assistant-vpc"
    Environment = var.environment
  }
}

# Public Subnets (2 AZs)
resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.environment}-public-${count.index + 1}"
    Type = "public"
  }
}

# Private Subnets for Application (2 AZs)
resource "aws_subnet" "private_app" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + 2)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.environment}-private-app-${count.index + 1}"
    Type = "private-app"
  }
}

# Private Subnets for Data (2 AZs)
resource "aws_subnet" "private_data" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + 4)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.environment}-private-data-${count.index + 1}"
    Type = "private-data"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.environment}-igw"
  }
}

# NAT Gateways (one per AZ for HA)
resource "aws_eip" "nat" {
  count  = 2
  domain = "vpc"

  tags = {
    Name = "${var.environment}-nat-eip-${count.index + 1}"
  }
}

resource "aws_nat_gateway" "main" {
  count         = 2
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name = "${var.environment}-nat-${count.index + 1}"
  }
}

# VPC Endpoints
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.${var.region}.s3"
  route_table_ids = concat(
    aws_route_table.private_app[*].id,
    aws_route_table.private_data[*].id
  )

  tags = {
    Name = "${var.environment}-s3-endpoint"
  }
}

resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private_app[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "${var.environment}-secretsmanager-endpoint"
  }
}
```

### 2. Compute Module (ECS Fargate)

**modules/compute/ecs.tf:**
```hcl
resource "aws_ecs_cluster" "main" {
  name = "${var.environment}-cert-assistant"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.environment}-cert-assistant-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = "${var.ecr_repository_url}:${var.image_tag}"
      essential = true

      portMappings = [
        {
          containerPort = 8080
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "NODE_ENV"
          value = var.environment
        },
        {
          name  = "AWS_REGION"
          value = var.region
        }
      ]

      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.database.arn}:connection_string::"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "api"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_service" "api" {
  name            = "${var.environment}-cert-assistant-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8080
  }

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [aws_lb_listener.https]
}

# Auto Scaling
resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "${var.environment}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}
```

### 3. Database Module

**modules/database/rds.tf:**
```hcl
resource "aws_db_subnet_group" "main" {
  name       = "${var.environment}-cert-assistant"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "${var.environment}-db-subnet-group"
  }
}

resource "aws_db_parameter_group" "postgres" {
  name   = "${var.environment}-cert-assistant-postgres15"
  family = "postgres15"

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "ssl"
    value = "1"
  }
}

resource "aws_db_instance" "main" {
  identifier     = "${var.environment}-cert-assistant"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.rds.arn

  db_name  = "cert_assistant"
  username = "admin"
  password = random_password.db_password.result

  multi_az               = var.environment == "production" ? true : false
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.postgres.name

  backup_retention_period = var.environment == "production" ? 7 : 3
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  deletion_protection = var.environment == "production" ? true : false
  skip_final_snapshot = var.environment != "production"
  final_snapshot_identifier = "${var.environment}-cert-assistant-final-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  tags = {
    Name        = "${var.environment}-cert-assistant-db"
    Environment = var.environment
  }
}

# Store credentials in Secrets Manager
resource "aws_secretsmanager_secret" "database" {
  name = "${var.environment}/cert-assistant/database"
  
  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "database" {
  secret_id = aws_secretsmanager_secret.database.id
  secret_string = jsonencode({
    username          = aws_db_instance.main.username
    password          = random_password.db_password.result
    host              = aws_db_instance.main.address
    port              = aws_db_instance.main.port
    database          = aws_db_instance.main.db_name
    connection_string = "postgresql://${aws_db_instance.main.username}:${random_password.db_password.result}@${aws_db_instance.main.address}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}?sslmode=require"
  })
}
```

### 4. Storage Module

**modules/storage/s3.tf:**
```hcl
# Certificates Bucket
resource "aws_s3_bucket" "certificates" {
  bucket = "${var.environment}-cert-assistant-certificates-${var.account_id}"

  tags = {
    Name        = "Certificates Storage"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "certificates" {
  bucket = aws_s3_bucket.certificates.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "certificates" {
  bucket = aws_s3_bucket.certificates.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.certificates.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "certificates" {
  bucket = aws_s3_bucket.certificates.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "certificates" {
  bucket = aws_s3_bucket.certificates.id

  rule {
    id     = "archive-old-certificates"
    status = "Enabled"

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    expiration {
      days = 2555  # 7 years
    }
  }
}

# Private Keys Bucket (separate, more restrictive)
resource "aws_s3_bucket" "private_keys" {
  bucket = "${var.environment}-cert-assistant-keys-${var.account_id}"

  tags = {
    Name        = "Private Keys Storage"
    Environment = var.environment
    Sensitive   = "true"
  }
}

resource "aws_s3_bucket_versioning" "private_keys" {
  bucket = aws_s3_bucket.private_keys.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "private_keys" {
  bucket = aws_s3_bucket.private_keys.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.private_keys.arn
    }
  }
}

resource "aws_s3_bucket_logging" "private_keys" {
  bucket = aws_s3_bucket.private_keys.id

  target_bucket = aws_s3_bucket.audit_logs.id
  target_prefix = "s3-access-logs/private-keys/"
}

# Audit Logs Bucket
resource "aws_s3_bucket" "audit_logs" {
  bucket = "${var.environment}-cert-assistant-audit-${var.account_id}"

  tags = {
    Name        = "Audit Logs Storage"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  rule {
    id     = "archive-audit-logs"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 3650  # 10 years
    }
  }
}
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

**.github/workflows/deploy.yml:**
```yaml
name: Deploy to AWS

on:
  push:
    branches:
      - main
      - develop
  pull_request:
    branches:
      - main

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: cert-assistant

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run linter
        run: npm run lint
      
      - name: Run tests
        run: npm test
      
      - name: Run security scan
        run: npm audit --audit-level=high

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
      
      - name: Build, tag, and push image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest

  deploy-dev:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: development
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Update ECS service
        run: |
          aws ecs update-service \
            --cluster dev-cert-assistant \
            --service dev-cert-assistant-api \
            --force-new-deployment

  deploy-prod:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_PROD_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_PROD_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Deploy with blue/green
        run: |
          # Update task definition with new image
          TASK_DEF=$(aws ecs describe-task-definition --task-definition production-cert-assistant-api)
          NEW_TASK_DEF=$(echo $TASK_DEF | jq --arg IMAGE "$ECR_REGISTRY/$ECR_REPOSITORY:${{ github.sha }}" '.taskDefinition | .containerDefinitions[0].image = $IMAGE | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)')
          
          # Register new task definition
          aws ecs register-task-definition --cli-input-json "$NEW_TASK_DEF"
          
          # Update service (blue/green deployment)
          aws ecs update-service \
            --cluster production-cert-assistant \
            --service production-cert-assistant-api \
            --task-definition production-cert-assistant-api \
            --deployment-configuration "maximumPercent=200,minimumHealthyPercent=100"
```

---

## Deployment Procedures

### Initial Infrastructure Deployment

```bash
# 1. Initialize Terraform
cd terraform/environments/production
terraform init

# 2. Review planned changes
terraform plan -out=tfplan

# 3. Apply infrastructure
terraform apply tfplan

# 4. Run database migrations
export DATABASE_URL=$(aws secretsmanager get-secret-value --secret-id production/cert-assistant/database --query SecretString --output text | jq -r .connection_string)
npm run migrate

# 5. Seed initial data (admin user, config)
npm run seed:production
```

### Application Deployment

```bash
# Build and push Docker image
docker build -t cert-assistant:latest .
docker tag cert-assistant:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/cert-assistant:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/cert-assistant:latest

# Update ECS service
aws ecs update-service \
  --cluster production-cert-assistant \
  --service production-cert-assistant-api \
  --force-new-deployment
```

### Database Migrations

```bash
# Using Sequelize (Node.js) or Alembic (Python)

# Generate migration
npm run migrate:generate -- --name add_certificate_table

# Run migrations
npm run migrate:up

# Rollback if needed
npm run migrate:down
```

### Rollback Procedure

```bash
# Rollback to previous task definition
aws ecs update-service \
  --cluster production-cert-assistant \
  --service production-cert-assistant-api \
  --task-definition production-cert-assistant-api:<previous-revision>

# Or rollback infrastructure
cd terraform/environments/production
terraform apply -var="image_tag=<previous-sha>"
```

---

## Monitoring and Observability

### CloudWatch Dashboards

```hcl
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.environment}-cert-assistant"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", { stat = "Average" }],
            [".", "MemoryUtilization", { stat = "Average" }]
          ]
          period = 300
          stat   = "Average"
          region = var.region
          title  = "ECS Performance"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", { stat = "Average" }],
            [".", "DatabaseConnections", { stat = "Sum" }],
            [".", "FreeStorageSpace", { stat = "Average" }]
          ]
          period = 300
          region = var.region
          title  = "RDS Performance"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", { stat = "p95" }],
            [".", "HTTPCode_Target_5XX_Count", { stat = "Sum" }],
            [".", "RequestCount", { stat = "Sum" }]
          ]
          period = 60
          region = var.region
          title  = "ALB Metrics"
        }
      }
    ]
  })
}
```

### Alarms

```hcl
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${var.environment}-cert-assistant-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.api.name
  }
}

resource "aws_cloudwatch_metric_alarm" "api_errors" {
  alarm_name          = "${var.environment}-cert-assistant-api-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = "60"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alert on high 5XX error rate"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

---

## Cost Optimization

### Estimated Monthly Costs (Production)

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| **ECS Fargate** | 2 tasks × 1 vCPU, 2GB RAM | $60 |
| **RDS PostgreSQL** | db.t3.medium, Multi-AZ | $180 |
| **S3** | 100GB storage, 10K requests | $25 |
| **ALB** | 1 ALB, 1M requests | $25 |
| **NAT Gateway** | 2 NAT, 100GB data | $90 |
| **CloudWatch** | Logs, metrics, alarms | $50 |
| **Secrets Manager** | 5 secrets | $2 |
| **KMS** | 3 keys, 10K requests | $3 |
| **Data Transfer** | 100GB outbound | $9 |
| **Total** | | **~$444/month** |

### Cost Optimization Strategies

1. **Right-sizing:**
   - Start with smaller instance types
   - Monitor and adjust based on actual usage
   - Use Auto Scaling to match demand

2. **Reserved Instances:**
   - Purchase RDS Reserved Instances (save 30-60%)
   - 1-year commitment for predictable workloads

3. **S3 Intelligent-Tiering:**
   - Automatically move infrequently accessed data to cheaper tiers
   - Saves 70% on storage costs

4. **Spot Instances:**
   - Use for non-critical worker tasks (certificate processing)
   - Save up to 90% vs On-Demand

5. **CloudWatch Logs Retention:**
   - Set retention policies (7-30 days for operational logs)
   - Archive to S3 for long-term storage

---

## Disaster Recovery

### Backup Strategy

**RDS Automated Backups:**
- Daily automated snapshots
- 7-day retention (production)
- Point-in-time recovery enabled
- Manual snapshots before major changes

**S3 Versioning:**
- Enabled on all buckets
- Cross-region replication (optional, for DR)

**Terraform State:**
- Stored in S3 with versioning
- DynamoDB for state locking
- Regular backups of state file

### DR Testing

**Quarterly DR Drill:**
1. Simulate region failure
2. Restore RDS from snapshot
3. Deploy infrastructure in DR region (if applicable)
4. Verify application functionality
5. Document issues and improvements
6. Update DR runbook

---

## Summary

This deployment guide provides:
- **Infrastructure as Code** with Terraform for all AWS resources
- **Multi-environment** support (dev, staging, production)
- **CI/CD pipeline** with GitHub Actions for automated deployments
- **Monitoring and alerting** with CloudWatch
- **Cost optimization** strategies
- **Disaster recovery** procedures and testing

The infrastructure is designed for:
- High availability (Multi-AZ)
- Scalability (Auto Scaling)
- Security (encryption, least privilege)
- Observability (comprehensive monitoring)
- Cost efficiency (right-sizing, optimization)
