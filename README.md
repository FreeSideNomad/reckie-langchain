# LangChain Document Management System

An AI-powered hierarchical document management system that enables business analysts, product owners, QA leads, and DDD designers to collaboratively create and manage business documentation through conversational AI interfaces.

## Project Status

**Phase:** Planning Complete ✅
**Implementation:** Not Started
**Documents Created:** 14 planning documents

## Quick Links

- [Vision Document](./vision.md) - Overall system vision with 23 features
- [Planning Summary](./PLANNING_SUMMARY.md) - Complete planning breakdown
- [Features Summary](./features-summary.md) - Index of all 23 features
- [Document Prompts](./config/document_prompts.yaml) - System prompts for all 9 document types

## What Is This System?

This system helps teams create comprehensive software project documentation through AI-guided conversations. Key capabilities:

- **9 Document Types:** Research reports, business context, vision, features, epics, user stories, DDD designs, testing strategy, and test plans
- **Hierarchical Relationships:** Documents link together (Vision → Features → Epics → User Stories)
- **AI Guidance:** GPT-4 asks 3-5 clarifying questions per turn to build each document
- **Context-Aware:** AI has full context of parent documents using RAG (vector search)
- **Persona-Based:** Different roles (BA, PO, QA, DDD Designer) work on different document types
- **Ripple Effects:** Changes to parent documents flag children for review
- **Conversational Interface:** Web UI with chat panels for each document

## Document Hierarchy

```
Research Report ──┐
                  ├──> Vision Document ──> Features ──> Epics ──> User Stories
Business Context ─┘                            │
                                               └──> Test Plan
Testing Strategy (references Vision)
DDD Design (references Features)
```

## Technology Stack

### Core
- **LangChain** - AI orchestration framework
- **OpenAI GPT-4** - Large language model for conversations
- **PostgreSQL 15+** - Database with pgvector extension
- **pgvector** - Vector embeddings for RAG
- **SQLAlchemy 2.x** - Python ORM
- **Alembic** - Database migrations

### Web Framework
- **FastAPI** - Python web framework
- **Jinja2** - Template engine (server-side rendering)
- **GitHub Primer CSS** - Styling

### Development
- **Docker Compose** - Local development orchestration
- **pytest** - Testing framework
- **Pydantic** - Data validation

## Project Structure

```
langchain-demo/
├── README.md                          # This file
├── PLANNING_SUMMARY.md                # Complete planning summary
├── vision.md                          # Vision document
├── features-summary.md                # Feature index
│
├── Feature Documents (4 of 23 created)
├── feature-f1-database-vector-store.md
├── feature-f2-document-type-configuration.md
├── feature-f3-langchain-integration.md
├── feature-f6-vision-workflow.md
│
├── Epic Documents (3 created)
├── epic-f1-e1-docker-postgresql-setup.md
├── epic-f1-e2-database-schema-design.md
├── epic-f1-e3-database-migrations.md
│
├── User Story Documents (3 created)
├── user-story-f1-e1-s1-docker-compose.md
├── user-story-f1-e1-s2-pgvector-extension.md
├── user-story-f1-e1-s3-environment-config.md
│
├── Configuration
└── config/
    └── document_prompts.yaml          # System prompts for all 9 document types
```

## Planning Documents Created

This repository contains a complete planning breakdown:

### 1. Vision Document (vision.md)
- Vision statement and objectives
- 23 features across 6 phases
- Success metrics and timeline
- 16-20 week implementation plan

### 2. Feature Documents (4 of 23)
- **F1:** Database & Vector Store Setup
- **F2:** Document Type Configuration System
- **F3:** LangChain Integration & Prompt Management
- **F6:** Vision Document Workflow

Each feature includes:
- Business value and dependencies
- Detailed acceptance criteria
- Technical design
- User stories outline
- Non-functional requirements
- Testing strategy
- Risk mitigation

### 3. Epic Documents (3 created for Feature F1)
- **F1-E1:** Docker & PostgreSQL Setup (5 story points)
- **F1-E2:** Database Schema Design (8 story points)
- **F1-E3:** Database Migrations with Alembic (5 story points)

Each epic includes:
- Detailed acceptance criteria
- User story list
- Technical design
- Definition of done
- Testing checklist

### 4. User Story Documents (3 created for Epic F1-E1)
- **F1-E1-S1:** Docker Compose File Creation (2 story points)
- **F1-E1-S2:** pgvector Extension Installation (1 story point)
- **F1-E1-S3:** Environment Configuration (1 story point)

Each user story includes:
- User story format ("As a... I want... So that...")
- Detailed acceptance criteria
- Complete implementation details
- Testing checklist
- Definition of done
- Sub-task breakdown

### 5. Document Prompt Templates (config/document_prompts.yaml)
System prompts for all 9 document types:
1. Research Report - Business analyst, research methodology
2. Business Context - BA/PO, Canadian banking domain
3. Vision Document - Product owner, strategic direction
4. Feature Document - Product owner, feature elaboration
5. Epic Document - Product owner, epic breakdown
6. User Story - Product owner, implementation details
7. DDD Design - DDD designer, domain modeling
8. Testing Strategy - QA lead, quality approach
9. Test Plan - QA lead, feature testing

Each prompt includes:
- Role and context
- Conversation flow (step-by-step)
- Workflow steps definition
- Parent document types
- Allowed personas
- Domain model YAML template

## Implementation Roadmap

### Phase 1: Core Infrastructure (Weeks 1-3)
**Status:** Ready to start
- [ ] F1: Database & Vector Store Setup
  - [x] Epic F1-E1: Docker & PostgreSQL (user stories ready)
  - [ ] Epic F1-E2: Database Schema Design
  - [ ] Epic F1-E3: Database Migrations
- [ ] F2: Document Type Configuration System
- [ ] F3: LangChain Integration

### Phase 2: Document Workflows (Weeks 4-7)
- [ ] F4: Research Report Workflow
- [ ] F5: Business Context Workflow
- [ ] F6: Vision Document Workflow
- [ ] F7: Feature Document Workflow
- [ ] F8: Epic Document Workflow
- [ ] F9: User Story Document Workflow

### Phase 3: Specialized Personas (Weeks 8-10)
- [ ] F10: DDD Design Workflow
- [ ] F11: Testing Strategy Workflow
- [ ] F12: Test Plan Workflow

### Phase 4: User Interface (Weeks 11-13)
- [ ] F13: FastAPI + Jinja2 Web Application
- [ ] F14: Document Chat Interface
- [ ] F15: Document Navigation & Hierarchy Viewer
- [ ] F16: Persona Selector

### Phase 5: Advanced Features (Weeks 14-16)
- [ ] F17: RAG-Powered Context Retrieval
- [ ] F18: Ripple Effect Change Propagation
- [ ] F19: Document Versioning
- [ ] F20: Multi-User Support (future)

### Phase 6: Optimization (Week 17+)
- [ ] F21: Performance Optimization
- [ ] F22: Admin Configuration UI
- [ ] F23: Export & Reporting

## Getting Started (Future)

### Prerequisites
- Docker Desktop (Mac/Windows) or Docker Engine (Linux)
- Python 3.11+
- OpenAI API key
- Git

### Installation (Not Yet Implemented)

```bash
# Clone repository
git clone <repository-url>
cd langchain-demo

# Copy environment template
cp .env.example .env

# Edit .env and add:
# - OPENAI_API_KEY=your-key-here
# - POSTGRES_PASSWORD=strong-password

# Start PostgreSQL
docker-compose up -d

# Install Python dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start application
uvicorn src.main:app --reload

# Open browser
open http://localhost:8000
```

## Environment Variables

See `.env.example` (to be created) for all configuration options.

Required:
- `OPENAI_API_KEY` - OpenAI API key for GPT-4 and embeddings
- `POSTGRES_PASSWORD` - Database password
- `SECRET_KEY` - Application secret key

Optional (with defaults):
- `POSTGRES_USER` - Database user (default: langchain_user)
- `POSTGRES_DB` - Database name (default: langchain_docs)
- `POSTGRES_PORT` - Database port (default: 5432)
- `DATABASE_URL` - Full PostgreSQL connection string

## Project Estimates

- **Total Features:** 23
- **Estimated Epics:** 50-60
- **Estimated User Stories:** 200-300
- **Estimated Story Points:** 300-400
- **Estimated Duration:** 16-20 weeks (4-5 months)
- **Team Size:** 2-4 developers

## Key Features Demonstrated in Planning

This planning exercise demonstrates the very system we're building:

1. **Hierarchical Decomposition:** Vision → Features → Epics → User Stories
2. **Parent Context Preservation:** Each document references its parents
3. **Markdown + YAML:** Human-readable markdown with structured YAML domain models
4. **Detailed Documentation:** Complete specs at every level
5. **Conversational Prompts:** System prompts define AI conversation flow
6. **Workflow Steps:** Each document type has defined workflow stages
7. **Persona Mapping:** Different roles work on different document types

## Example Workflow (How the System Works)

### Creating a Vision Document

1. **User:** "Create a vision document for payment processing platform"
2. **AI:** Loads parent Research Report and Business Context documents
3. **AI:** Asks 3-5 questions about vision statement, objectives, users, metrics
4. **User:** Responds to questions
5. **AI:** Updates vision document markdown incrementally
6. **Repeat:** Steps 3-5 until vision is complete
7. **AI:** Derives feature list from vision
8. **AI:** Asks 3-5 questions to refine feature list
9. **User:** Approves feature list
10. **AI:** Creates 10 separate feature documents
11. **System:** Marks vision document as "complete"

### Parent Context in Action

When working on a **User Story**, the AI has full context:
- Epic (parent)
- Feature (grandparent)
- Vision (great-grandparent)
- DDD Design (related document)

This context is injected into the AI prompt using RAG (vector search) to ensure consistency and traceability.

## Success Metrics (from Vision)

- **Documentation Speed:** 60% reduction in time to create document hierarchy
- **Context Preservation:** 100% traceability from user stories to vision
- **User Satisfaction:** 4.5/5 rating from each persona
- **AI Quality:** < 5 turns per document to reach user approval
- **Change Impact:** 80% accuracy identifying affected child documents

## Contributing (Future)

This project is in the planning phase. Implementation has not started.

Once implementation begins:
1. Pick a user story from the backlog
2. Create a feature branch
3. Implement according to acceptance criteria
4. Write tests (see story's testing checklist)
5. Submit pull request

## License

TBD

## Contact

TBD

---

**Status:** ✅ Planning Complete | ⏳ Implementation Pending
**Next Action:** Implement US-F1-E1-S1 (Docker Compose File Creation)
