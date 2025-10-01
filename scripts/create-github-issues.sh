#!/bin/bash
# Script to create GitHub issues for Features, Epics, and User Stories
# Based on planning documentation in wiki/

set -e

echo "Creating GitHub issues from planning documentation..."
echo ""

# Feature F1: Database & Vector Store Setup
echo "Creating Feature F1..."
gh issue create \
  --title "[Feature F1] Database & Vector Store Setup" \
  --label "feature,P0,phase-1" \
  --body "## Feature Overview

**Feature ID:** F1
**Name:** Database & Vector Store Setup
**Priority:** P0 (Blocker)
**Sequence:** 1
**Phase:** Phase 1: Core Infrastructure
**Parent:** [Vision Document](https://github.com/FreeSideNomad/reckie-langchain/wiki/vision)

## Description

Establish the foundational data infrastructure for the system using PostgreSQL with pgvector extension. This includes designing and implementing the database schema for storing documents (markdown + YAML), document relationships (parent-child hierarchy), vector embeddings for RAG, conversation sessions, and document versioning. The setup must support local development via Docker Compose and be production-ready with migration support.

## Business Value

- **Foundation:** Enables all other features to store and retrieve data
- **Scalability:** PostgreSQL handles enterprise-scale document volumes
- **Intelligence:** pgvector enables semantic search and RAG capabilities
- **Developer Experience:** Docker Compose simplifies local development setup
- **Data Integrity:** Proper schema design with constraints and indexes

## Dependencies

**Upstream:** None (foundational feature)

**Downstream:**
- F2: Document Type Configuration System
- F3: LangChain Integration
- F17: RAG-Powered Context Retrieval
- F19: Document Versioning

## Acceptance Criteria

### AC1: Docker Compose Setup
- [ ] Docker Compose file with PostgreSQL 15+ service
- [ ] pgvector extension installed and enabled
- [ ] Environment variables for database credentials
- [ ] Volume mounts for data persistence
- [ ] Health checks configured
- [ ] README with setup instructions

### AC2: Database Schema Design
- [ ] **documents** table with all required fields
- [ ] **document_relationships** table
- [ ] **document_embeddings** table with vector(1536)
- [ ] **conversations** table
- [ ] **document_types** table
- [ ] **users** table
- [ ] Indexes on foreign keys and frequently queried fields
- [ ] Constraints: NOT NULL, foreign keys, unique constraints

### AC3: Database Migrations
- [ ] Alembic configured for migrations
- [ ] Initial migration script creating all tables
- [ ] Migration script for pgvector extension
- [ ] Downgrade migrations for rollback

### AC4: Versioning Support
- [ ] version column in documents table
- [ ] **document_versions** table
- [ ] Trigger or application logic to create version on update

### AC5: SQLAlchemy ORM Models
- [ ] All models defined with proper relationships
- [ ] Proper type hints and validations

### AC6: Connection Pooling & Configuration
- [ ] SQLAlchemy engine configuration
- [ ] Connection pooling configured
- [ ] Environment-based configuration

## Epics

- [ ] #TBD Epic F1-E1: Docker & PostgreSQL Setup (5 SP)
- [ ] #TBD Epic F1-E2: Database Schema Design (8 SP)
- [ ] #TBD Epic F1-E3: Database Migrations (5 SP)

## Technical Design

**Technology Stack:**
- PostgreSQL 15+
- pgvector extension
- SQLAlchemy 2.x ORM
- Alembic migrations
- Docker Compose

**Estimated Story Points:** 18

**Reference:** [Feature F1 Documentation](https://github.com/FreeSideNomad/reckie-langchain/wiki/feature-f1-database-vector-store)"

echo "✓ Created Feature F1"
echo ""

# Wait for issue to be created and get issue number
sleep 2
FEATURE_F1=$(gh issue list --label "feature" --limit 1 --json number --jq '.[0].number')
echo "Feature F1 issue number: #$FEATURE_F1"
echo ""

# Epic F1-E1: Docker & PostgreSQL Setup
echo "Creating Epic F1-E1..."
gh issue create \
  --title "[Epic F1-E1] Docker & PostgreSQL Setup" \
  --label "epic,P0,sprint-1" \
  --body "## Epic Overview

**Epic ID:** F1-E1
**Name:** Docker & PostgreSQL Setup
**Parent Feature:** #${FEATURE_F1} (F1: Database & Vector Store Setup)
**Priority:** P0 (Blocker)
**Sprint:** Sprint 1
**Story Points:** 5

## Description

Set up local development environment using Docker Compose with PostgreSQL 15+ and pgvector extension. Create configuration files, environment templates, initialization scripts, and documentation for developers to quickly spin up the database locally. Ensure health checks, data persistence via volumes, and proper networking for FastAPI application to connect.

## Business Value

- **Developer Productivity:** One-command database setup (\`docker-compose up\`)
- **Consistency:** All developers use identical database configuration
- **Onboarding:** New team members can start in minutes
- **CI/CD Foundation:** Same Docker setup usable in testing/staging

## Acceptance Criteria

### AC1: Docker Compose File
- [ ] \`docker-compose.yml\` in project root
- [ ] PostgreSQL 15+ service defined
- [ ] Container name: \`langchain-demo-postgres\`
- [ ] Port mapping: 5432:5432
- [ ] Volume mount for data persistence
- [ ] Environment variables loaded from \`.env\` file
- [ ] Network: \`langchain-network\` (bridge)

### AC2: PostgreSQL Configuration
- [ ] Database name: \`langchain_docs\` (configurable)
- [ ] User/password from environment variables
- [ ] UTF-8 encoding
- [ ] Timezone: UTC
- [ ] Logging enabled

### AC3: pgvector Extension
- [ ] PostgreSQL image with pgvector support (pgvector/pgvector:pg15)
- [ ] Extension installation script in \`scripts/init_db.sql\`
- [ ] Script executed on container initialization

### AC4: Environment Configuration
- [ ] \`.env.example\` file with template variables
- [ ] \`.env\` file gitignored
- [ ] README instructions to copy \`.env.example\` to \`.env\`

### AC5: Health Checks
- [ ] Healthcheck defined in docker-compose.yml
- [ ] Container reports healthy status within 30 seconds

### AC6: Initialization Script
- [ ] \`scripts/init_db.sh\` for custom initialization
- [ ] Creates extensions
- [ ] Idempotent (can run multiple times safely)

### AC7: Documentation
- [ ] README.md section: \"Local Development Setup\"
- [ ] Step-by-step instructions
- [ ] Troubleshooting section

### AC8: Testing
- [ ] \`docker-compose up\` starts successfully
- [ ] PostgreSQL container healthy within 30s
- [ ] Can connect via psql from host
- [ ] pgvector extension verified installed
- [ ] Data persists after restart

## User Stories

- [ ] #TBD US-F1-E1-S1: Docker Compose File Creation (2 SP)
- [ ] #TBD US-F1-E1-S2: pgvector Extension Installation (1 SP)
- [ ] #TBD US-F1-E1-S3: Environment Configuration (1 SP)
- [ ] #TBD US-F1-E1-S4: Health Checks Configuration (1 SP)
- [ ] #TBD US-F1-E1-S5: Setup Documentation (1 SP)

## Dependencies

**Blocked By:** None (foundational)

**Blocks:**
- Epic F1-E2: Database Schema Design
- Epic F1-E3: Database Migrations

## Testing Strategy

### Manual Testing
- [ ] Run \`docker-compose up -d\`
- [ ] Verify container status
- [ ] Connect via psql
- [ ] Check extensions
- [ ] Test data persistence

### Automated Testing
- [ ] CI pipeline: Docker Compose starts successfully
- [ ] Health check passes within 30 seconds

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All user stories completed
- [ ] Documentation reviewed and clear
- [ ] Manual testing passed
- [ ] Code reviewed
- [ ] No blockers for dependent epics

**Estimated Effort:** 8-12 hours

**Reference:** [Epic F1-E1 Documentation](https://github.com/FreeSideNomad/reckie-langchain/wiki/epic-f1-e1-docker-postgresql-setup)"

echo "✓ Created Epic F1-E1"
echo ""

# Wait and get epic number
sleep 2
EPIC_F1_E1=$(gh issue list --label "epic" --limit 1 --json number --jq '.[0].number')
echo "Epic F1-E1 issue number: #$EPIC_F1_E1"
echo ""

# User Story F1-E1-S1: Docker Compose File Creation
echo "Creating User Story F1-E1-S1..."
gh issue create \
  --title "[US-F1-E1-S1] Docker Compose File Creation" \
  --label "user-story,sprint-1" \
  --assignee "@me" \
  --body "## User Story

**Story ID:** F1-E1-S1

As a developer
I want a docker-compose.yml file with PostgreSQL configuration
So that I can start the database with one command (\`docker-compose up\`)

## Parent Context

**Epic:** #${EPIC_F1_E1} (F1-E1: Docker & PostgreSQL Setup)
**Feature:** #${FEATURE_F1} (F1: Database & Vector Store Setup)
**Vision:** [AI-Powered Hierarchical Document Management System](https://github.com/FreeSideNomad/reckie-langchain/wiki/vision)

**Story Points:** 2
**Sprint:** Sprint 1
**Estimated Hours:** 2-3 hours

## Acceptance Criteria

### AC1: Docker Compose File Exists
- [ ] File \`docker-compose.yml\` created in project root
- [ ] Valid YAML syntax
- [ ] Version: \`3.8\` or higher

### AC2: PostgreSQL Service Configured
- [ ] Service name: \`postgres\`
- [ ] Image: \`pgvector/pgvector:pg15\`
- [ ] Container name: \`langchain-demo-postgres\`

### AC3: Port Mapping
- [ ] Host port \`5432\` mapped to container port \`5432\`
- [ ] Port configurable via environment variable (default 5432)

### AC4: Environment Variables
- [ ] \`POSTGRES_USER\` loaded from \`.env\`
- [ ] \`POSTGRES_PASSWORD\` loaded from \`.env\`
- [ ] \`POSTGRES_DB\` loaded from \`.env\`
- [ ] \`PGDATA\` set to \`/var/lib/postgresql/data/pgdata\`

### AC5: Volume Mounts
- [ ] Data volume: \`./postgres_data:/var/lib/postgresql/data\`
- [ ] Init script volume: \`./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql\`

### AC6: Network Configuration
- [ ] Network \`langchain-network\` defined
- [ ] Network driver: \`bridge\`
- [ ] Postgres service attached to network

### AC7: Health Check
- [ ] Health check command: \`pg_isready -U \${POSTGRES_USER} -d \${POSTGRES_DB}\`
- [ ] Interval: 10 seconds
- [ ] Timeout: 5 seconds
- [ ] Retries: 5

### AC8: Restart Policy
- [ ] Restart policy: \`unless-stopped\`

## Testing Checklist

### Manual Testing
- [ ] Run \`docker-compose up -d\`
- [ ] Verify container started: \`docker ps | grep langchain-demo-postgres\`
- [ ] Check container status: \`docker-compose ps\` (should show \"healthy\")
- [ ] Verify network: \`docker network ls | grep langchain-network\`
- [ ] Check logs: \`docker-compose logs postgres\` (no errors)
- [ ] Stop containers: \`docker-compose down\`
- [ ] Restart: \`docker-compose up -d\` (should work identically)

### Integration Testing
- [ ] Container becomes healthy within 30 seconds
- [ ] Environment variables correctly passed to container
- [ ] Volume mount successful (data directory created)
- [ ] Network accessible from host machine

## Definition of Done

- [ ] docker-compose.yml file created and committed
- [ ] File passes YAML linting
- [ ] All acceptance criteria met
- [ ] Manual testing completed successfully
- [ ] Code reviewed by peer
- [ ] Documentation updated (if needed)

## Sub-Tasks

- [ ] Create \`docker-compose.yml\` file in project root
- [ ] Define \`postgres\` service with all required fields
- [ ] Configure environment variables with defaults
- [ ] Set up volume mounts
- [ ] Define network
- [ ] Add health check configuration
- [ ] Test \`docker-compose up\`
- [ ] Verify health check passes
- [ ] Test \`docker-compose down\`
- [ ] Update \`.gitignore\` to exclude \`postgres_data/\`
- [ ] Commit and push changes

## Dependencies

**Blocked By:** None (first story in epic)

**Blocks:**
- US-F1-E1-S2: pgvector Extension Installation
- US-F1-E1-S3: Environment Configuration

**Estimated Effort:** 2-3 hours

**Reference:** [User Story F1-E1-S1 Documentation](https://github.com/FreeSideNomad/reckie-langchain/wiki/user-story-f1-e1-s1-docker-compose)"

echo "✓ Created User Story F1-E1-S1"
echo ""

sleep 2
US_F1_E1_S1=$(gh issue list --label "user-story" --limit 1 --json number --jq '.[0].number')
echo "User Story F1-E1-S1 issue number: #$US_F1_E1_S1"
echo ""

echo "================================"
echo "Issues created successfully!"
echo "================================"
echo "Feature F1: #$FEATURE_F1"
echo "Epic F1-E1: #$EPIC_F1_E1"
echo "User Story F1-E1-S1: #$US_F1_E1_S1"
echo ""
echo "View all issues: gh issue list"
