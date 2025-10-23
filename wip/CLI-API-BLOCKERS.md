# CLI MVP - API Blockers and Missing User Stories

**Status**: Analysis Complete
**Date**: 2025-10-02
**Reviewer**: Claude Code

---

## Executive Summary

The CLI MVP (Feature F7) requires **7 new API endpoints** and **2 major service enhancements** to support its functionality. These are critical blockers that must be implemented before the CLI can function.

**Total New User Stories Needed**: 9
**Estimated Story Points**: 18 SP
**Critical Path**: Document Type API (blocks all CLI create workflows)

---

## Current API Coverage Analysis

### ✅ Existing Endpoints (Available)

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/v1/documents` | GET | List documents with filters | ✅ Available |
| `/api/v1/documents` | POST | Create document | ✅ Available |
| `/api/v1/documents/{id}` | GET | Get single document | ✅ Available |
| `/api/v1/documents/{id}` | PUT | Update document | ✅ Available |
| `/api/v1/documents/{id}` | DELETE | Delete document | ✅ Available |
| `/api/v1/documents/{id}/ancestors` | GET | Get ancestor documents | ✅ Available |
| `/api/v1/documents/{id}/descendants` | GET | Get descendant documents | ✅ Available |
| `/api/v1/documents/{id}/breadcrumb` | GET | Get breadcrumb trail | ✅ Available |
| `/api/v1/documents/{id}/context` | GET | Get parent context for RAG | ✅ Available |
| `/api/v1/documents/{id}/mark-descendants` | POST | Trigger ripple effect | ✅ Available |

### ❌ Missing Endpoints (Blockers)

| Endpoint | Method | Purpose | Blocker For | Priority |
|----------|--------|---------|-------------|----------|
| `/api/v1/document-types` | GET | List all document types | Epic F7-E3 (Create) | **P0** |
| `/api/v1/document-types/{type_name}` | GET | Get document type config | Epic F7-E3 (Create) | **P0** |
| `/api/v1/workflows/start` | POST | Start interactive workflow | Epic F7-E4 (Workflows) | **P0** |
| `/api/v1/workflows/{id}/respond` | POST | Send user answer | Epic F7-E4 (Workflows) | **P0** |
| `/api/v1/workflows/{id}/next` | GET | Get next action | Epic F7-E4 (Workflows) | **P0** |
| `/api/v1/workflows/{id}/finish` | POST | Finish workflow early | Epic F7-E4 (Workflows) | P1 |

**Note**: Document types are static JSONB configurations (no POST/PUT/DELETE endpoints needed for MVP)

---

## Blocker #1: Document Type Management API (**CRITICAL**)

### Impact

**Blocks**:
- Epic F7-E3: Create Document (cannot list available types)
- Epic F7-E4: Interactive Workflows (needs type configuration)

**Current State**:
- Database table exists: `document_types`
- Service layer exists: `src/services/document_type_service.py` (from Epic F2-E1)
- **API layer missing**: No REST endpoints

### Required User Stories

#### US-F2-E1-S2: Document Type REST API Endpoints

**Story Points**: 3 SP
**Priority**: P0 (CLI MVP Blocker)
**Epic**: F2-E1 (Configuration Service & API)

**Description**:
As a **CLI user**, I need REST API endpoints to fetch document type configurations so that I can see available document types and their requirements when creating documents.

**Acceptance Criteria**:
- [ ] `GET /api/v1/document-types` - List all document types
  - Query params: None (return all types)
  - Response: Array of document types with full configuration
  - Includes: type_name, display_name, description, system_prompt, workflow_steps, parent_types, allowed_personas, config
- [ ] `GET /api/v1/document-types/{type_name}` - Get single document type
  - Path param: type_name (e.g., "feature_document")
  - Response: Full document type configuration
  - Error: 404 if not found
- [ ] Response includes all fields needed for CLI filtering:
  - `single_instance` (bool) - Can only exist once (e.g., Vision)
  - `requires_parent` (bool) - Must have parent document
  - `allowed_parent_types` (array) - Valid parent types
  - `has_interactive_workflow` (bool) - Starts workflow after creation
  - `required_fields` (array) - Fields to prompt for

**Technical Notes**:
```python
# src/api/v1/routes/document_types.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.api.dependencies import get_db
from src.services.document_type_service import DocumentTypeService

router = APIRouter(prefix="/document-types", tags=["document-types"])

@router.get("/")
def list_document_types(db: Session = Depends(get_db)):
    """List all document types."""
    service = DocumentTypeService(db)
    types = service.list_types()
    return types

@router.get("/{type_name}")
def get_document_type(type_name: str, db: Session = Depends(get_db)):
    """Get document type by name."""
    service = DocumentTypeService(db)
    doc_type = service.get_type(type_name)
    if not doc_type:
        raise HTTPException(status_code=404, detail=f"Document type '{type_name}' not found")
    return doc_type
```

**Depends On**: US-F2-E1-S1 (DocumentTypeService Core CRUD) - Already implemented

**Blocks**: Epic F7-E3 (Create Document), Epic F7-E4 (Interactive Workflows)

---

## Blocker #2: Interactive Workflow API (**CRITICAL**)

### Impact

**Blocks**:
- Epic F7-E4: Interactive Workflows (core CLI feature)

**Current State**:
- Conversation service exists: `src/services/conversation_chain_service.py`
- WebSocket chat endpoint exists: `/api/v1/chat/ws/{conversation_id}`
- **Structured protocol API missing**: No REST endpoints for structured workflow

### Required User Stories

#### US-F3-E1-S3: Workflow Orchestration API (Structured Protocol)

**Story Points**: 5 SP
**Priority**: P0 (CLI MVP Blocker)
**Epic**: F3-E1 (OpenAI Conversation Chain)

**Description**:
As a **CLI user**, I need REST API endpoints that implement the structured workflow protocol so that I can have interactive document creation sessions with question/answer flows.

**Acceptance Criteria**:
- [ ] `POST /api/v1/workflows/start` - Start new workflow session
  - Request body: `{ "document_id": UUID, "user_email": str }`
  - Response: `WorkflowResponse` with first action (usually `prompt_user`)
  - Creates new conversation session with LangChain
  - Returns `conversation_id` for subsequent calls
- [ ] `POST /api/v1/workflows/{conversation_id}/respond` - Send user answer
  - Path param: `conversation_id` (UUID)
  - Request body: `{ "question_id": str, "answer": str }` OR `{ "question_id": str, "command": "skip" }`
  - Response: `WorkflowResponse` with next action
  - Processes user answer through LangChain
  - Determines next action (prompt_user, update_content, complete, error)
- [ ] `GET /api/v1/workflows/{conversation_id}/next` - Get next action
  - Path param: `conversation_id` (UUID)
  - Response: `WorkflowResponse` with next action
  - Used after `update_content` (auto_continue)
- [ ] `POST /api/v1/workflows/{conversation_id}/finish` - Finish workflow early
  - Path param: `conversation_id` (UUID)
  - Request body: `{ "reason": "user_exit", "last_question_id": str }`
  - Response: `CompleteAction` with summary
  - Saves current state, marks workflow as paused
- [ ] Implement `WorkflowResponse` protocol (see `wiki/cli-api-protocol.md`):
  - Base structure: `{ "action": str, "data": dict, "conversation_id": UUID, "document_id": UUID }`
  - Action types: `prompt_user`, `update_content`, `complete`, `error`
- [ ] Integration with document creation:
  - After document created, workflow automatically started
  - Workflow updates document content via `DocumentService`
  - Document version incremented on each update

**Technical Notes**:
```python
# src/api/v1/routes/workflows.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.api.dependencies import get_db
from src.services.workflow_orchestration_service import WorkflowOrchestrationService

router = APIRouter(prefix="/workflows", tags=["workflows"])

@router.post("/start")
async def start_workflow(
    request: WorkflowStartRequest,
    db: Session = Depends(get_db)
):
    """Start interactive workflow for document."""
    service = WorkflowOrchestrationService(db)
    response = await service.start_workflow(
        document_id=request.document_id,
        user_email=request.user_email
    )
    return response  # WorkflowResponse with conversation_id

@router.post("/{conversation_id}/respond")
async def respond_to_workflow(
    conversation_id: UUID,
    request: WorkflowRespondRequest,
    db: Session = Depends(get_db)
):
    """Send user answer to workflow."""
    service = WorkflowOrchestrationService(db)
    response = await service.process_response(
        conversation_id=conversation_id,
        question_id=request.question_id,
        answer=request.answer,
        command=request.command
    )
    return response  # WorkflowResponse with next action
```

**Depends On**:
- Conversation service (exists)
- Document service (exists)
- DocumentType configuration (Blocker #1)

**Blocks**: Epic F7-E4 (Interactive Workflows)

---

#### US-F3-E1-S4: Workflow Orchestration Service Layer

**Story Points**: 5 SP
**Priority**: P0 (CLI MVP Blocker)
**Epic**: F3-E1 (OpenAI Conversation Chain)

**Description**:
As a **backend developer**, I need a workflow orchestration service that bridges LangChain conversations with the structured protocol so that the API can return formatted actions for the CLI.

**Acceptance Criteria**:
- [ ] `WorkflowOrchestrationService` class in `src/services/workflow_orchestration_service.py`
- [ ] Methods:
  - `start_workflow(document_id, user_email) → WorkflowResponse`
  - `process_response(conversation_id, question_id, answer, command) → WorkflowResponse`
  - `get_next_action(conversation_id) → WorkflowResponse`
  - `finish_workflow(conversation_id, reason) → WorkflowResponse`
- [ ] State machine implementation:
  - Track current question/step
  - Determine next action based on LLM response
  - Parse LLM output into structured actions
- [ ] Action generation:
  - `prompt_user`: Extract question from LLM response
  - `update_content`: Generate document content, calculate diff
  - `complete`: Summarize workflow, provide next steps
  - `error`: Handle validation failures, API errors
- [ ] Integration with DocumentType workflow configuration:
  - Load workflow_steps from DocumentType
  - Inject into system prompt
  - Follow configured workflow sequence
- [ ] Document content updates:
  - Call `DocumentService.update_document()` on content changes
  - Increment document version
  - Write to database

**Technical Notes**:
- Reuse `ConversationChainService` for LangChain integration
- Parse LLM responses to extract structured data
- Use prompt engineering to get consistent action formats
- Store workflow state in conversation metadata

**Depends On**:
- US-F3-E1-S3 (API endpoints - can be parallel)
- DocumentTypeService (for workflow configuration)

**Blocks**: US-F3-E1-S3 (API endpoints depend on this service)

---

## Blocker #3: Document List API Enhancement

### Impact

**Blocks**:
- Epic F7-E2: Document Sync (needs children_ids in response)

**Current State**:
- Endpoint exists: `GET /api/v1/documents`
- **Missing field**: `children_ids` not included in response

### Required User Stories

#### US-F1-E5-S4: Enhance Document List Response (children_ids)

**Story Points**: 1 SP
**Priority**: P0 (CLI MVP Blocker)
**Epic**: F1-E5 (Document Relationships & Hierarchy)

**Description**:
As a **CLI user**, I need the document list API to include children_ids so that I can build the local directory hierarchy correctly during sync.

**Acceptance Criteria**:
- [ ] `GET /api/v1/documents` response includes `children_ids` field
- [ ] `children_ids` is an array of UUIDs (child document IDs)
- [ ] Populated from `document_relationships` table (parent_id → child_id)
- [ ] Use RelationshipService to get children efficiently
- [ ] Update `DocumentResponse` Pydantic model to include field

**Technical Notes**:
```python
# src/api/v1/models/document.py

class DocumentResponse(BaseModel):
    id: UUID
    user_id: UUID
    document_type: str
    title: str
    content_markdown: Optional[str]
    version: int
    status: str
    parent_id: Optional[UUID]  # Already exists
    children_ids: List[UUID]  # ADD THIS
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

# src/api/v1/routes/documents.py

@router.get("/")
def list_documents(...) -> DocumentListResponse:
    # Fetch documents
    documents = list(db.execute(query).scalars().all())

    # For each document, get children
    for doc in documents:
        children = relationship_service.get_children(doc.id)
        doc.children_ids = [child.id for child in children]

    return DocumentListResponse(items=documents, ...)
```

**Depends On**: RelationshipService (exists)

**Blocks**: Epic F7-E2 (Document Sync)

---

## Blocker #4: Document Response Enhancement (parent_id)

### Impact

**Blocks**:
- Epic F7-E2: Document Sync (needs parent_id for hierarchy)

**Current State**:
- Endpoint exists: `GET /api/v1/documents`
- **Missing field**: `parent_id` not included in response

### Required User Stories

#### US-F1-E5-S5: Enhance Document Response (parent_id)

**Story Points**: 1 SP
**Priority**: P0 (CLI MVP Blocker)
**Epic**: F1-E5 (Document Relationships & Hierarchy)

**Description**:
As a **CLI user**, I need the document response to include parent_id so that I can determine where to place files in the local directory hierarchy.

**Acceptance Criteria**:
- [ ] `GET /api/v1/documents` response includes `parent_id` field
- [ ] `GET /api/v1/documents/{id}` response includes `parent_id` field
- [ ] `parent_id` is nullable UUID (None for root documents like Vision)
- [ ] Populated from `document_relationships` table (child_id → parent_id)
- [ ] Use RelationshipService to get parent efficiently

**Technical Notes**:
```python
# src/api/v1/routes/documents.py

@router.get("/{document_id}")
def get_document(document_id: UUID, db: Session = Depends(get_db)) -> Document:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get parent relationship
    relationship_service = RelationshipService(db)
    parents = relationship_service.get_parents(document_id)

    # Assuming single parent (hierarchical)
    document.parent_id = parents[0].id if parents else None

    return document
```

**Depends On**: RelationshipService (exists)

**Blocks**: Epic F7-E2 (Document Sync)

---

## Blocker #5: User Email Support (MVP Authentication)

### Impact

**Blocks**:
- Epic F7-E1: CLI Foundation (user identification)
- Epic F7-E2: Document Sync (filter by user)

**Current State**:
- Documents have `user_id` (UUID)
- **Missing**: Email-based lookup for MVP (pre-auth)

### Required User Stories

#### US-F5-E1-S1: User Email Lookup and Creation

**Story Points**: 2 SP
**Priority**: P0 (CLI MVP Blocker)
**Epic**: F5-E1 (User Management)

**Description**:
As a **CLI user**, I need to be identified by email (pre-authentication MVP) so that I can access my documents without JWT tokens.

**Acceptance Criteria**:
- [ ] Enhance `GET /api/v1/documents` to accept `user_email` query param
- [ ] If `user_email` provided:
  - Lookup user by email
  - If not exists, create new user record
  - Filter documents by user_id
- [ ] Enhance `POST /api/v1/documents` to accept `user_email` in body
  - Lookup or create user
  - Set document.user_id from resolved user
- [ ] User table has email field (already exists)
- [ ] Email uniqueness constraint (already exists)

**Technical Notes**:
```python
# src/services/user_service.py

class UserService:
    def get_or_create_by_email(self, email: str) -> User:
        """Get user by email, create if doesn't exist."""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                id=uuid4(),
                name=email.split('@')[0],  # Default name from email
                email=email
            )
            db.add(user)
            db.commit()
        return user

# src/api/v1/routes/documents.py

@router.get("/")
def list_documents(
    user_email: Optional[str] = Query(None),
    ...
):
    if user_email:
        user_service = UserService(db)
        user = user_service.get_or_create_by_email(user_email)
        query = query.where(Document.user_id == user.id)

    # ... rest of query
```

**Depends On**: User table (exists)

**Blocks**: Epic F7-E1, Epic F7-E2

---

## Non-Blocking Enhancements (Post-MVP)

These are mentioned in the CLI spec but not critical for MVP:

### 1. Document Deletion Cascade
**Epic**: F7-E3 (Create Document) - Post-MVP
**User Story**: Implement cascade delete with user confirmation
**Priority**: P2

### 2. JWT Authentication
**Epic**: F7-E1 (CLI Foundation) - Post-MVP
**User Story**: Replace email-based auth with JWT tokens
**Priority**: P1

### 3. Document Update Endpoint Enhancement
**Epic**: F7-E2 (Document Sync) - Post-MVP
**User Story**: Support push from CLI to API (local changes → remote)
**Priority**: P1

---

## Implementation Order (Critical Path)

To unblock CLI MVP development, implement in this order:

### Phase 1: User & Document Type APIs (5 SP) - **MUST DO FIRST**
1. ✅ **US-F5-E1-S1**: User Email Lookup (2 SP) - Enables user identification
2. ✅ **US-F2-E1-S2**: Document Type REST API (3 SP) - Enables type selection in CLI

**Why First**: CLI cannot start without user identification and document type discovery

### Phase 2: Document Response Enhancements (2 SP) - **MUST DO SECOND**
3. ✅ **US-F1-E5-S4**: Add children_ids to Document Response (1 SP) - Enables hierarchy sync
4. ✅ **US-F1-E5-S5**: Add parent_id to Document Response (1 SP) - Enables hierarchy sync

**Why Second**: CLI sync depends on these fields for directory structure

### Phase 3: Workflow Orchestration (10 SP) - **CAN START IN PARALLEL**
5. ✅ **US-F3-E1-S4**: Workflow Orchestration Service (5 SP) - Core workflow logic
6. ✅ **US-F3-E1-S3**: Workflow API Endpoints (5 SP) - REST interface for workflows

**Why Last**: Interactive workflows can be developed in parallel with CLI E1-E3

---

## Summary of New User Stories

| User Story | Epic | SP | Priority | Blocks CLI Epic | GitHub Issue |
|-----------|------|----|----|-----------------|--------------|
| US-F5-E1-S1: User Email Lookup | F5-E1 | 2 | P0 | F7-E1, F7-E2 | #92 |
| US-F2-E1-S2: Document Type API | F2-E1 | 3 | P0 | F7-E3, F7-E4 | #93 |
| US-F1-E5-S4: Add children_ids | F1-E5 | 1 | P0 | F7-E2 | #94 |
| US-F1-E5-S5: Add parent_id | F1-E5 | 1 | P0 | F7-E2 | #95 |
| US-F3-E1-S4: Workflow Service | F3-E1 | 5 | P0 | F7-E4 | #96 |
| US-F3-E1-S3: Workflow API | F3-E1 | 5 | P0 | F7-E4 | #97 |

**Total**: 6 user stories, 17 SP

**Status**: ✅ All issues created in GitHub

---

## Risk Assessment

### High Risk
- **Workflow Orchestration** (10 SP) - Complex state machine, LLM integration, protocol design
  - Mitigation: Start with simple prompt/response flow, iterate

### Medium Risk
- **Document Type API** (3 SP) - Depends on DocumentTypeService being complete
  - Mitigation: Verify service layer exists and works

### Low Risk
- **User Email Lookup** (2 SP) - Straightforward lookup/create pattern
- **Document Response Enhancements** (2 SP) - Simple field additions

---

## Next Steps

1. **Review this document** with product owner
2. **Create GitHub issues** for all 6 user stories
3. **Assign to epics** (F1-E5, F2-E1, F3-E1, F5-E1)
4. **Prioritize Phase 1** (User + Document Type APIs) - Must complete before CLI work starts
5. **Begin implementation** following critical path order

---

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
