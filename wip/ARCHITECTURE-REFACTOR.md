# Architecture Refactoring - Clean Separation of Concerns

## Problem

The original `reckie-cli.py` had mixed concerns:
- ❌ UI logic (prompts, display) mixed with business logic
- ❌ Templating and LLM prompts embedded in UI code
- ❌ Workflow orchestration tangled with presentation
- ❌ Hard to test, hard to extend, hard to reuse

## Solution

Implemented **Clean Architecture** with 3 distinct layers:

```
┌─────────────────────────────────────────┐
│         UI Layer (Presentation)         │
│    CLIPresenter - Rich Console UI      │
│    - Display documents                  │
│    - Collect user input                 │
│    - Show errors/questions              │
└───────────────┬─────────────────────────┘
                │ WorkflowResponse
                ▼
┌─────────────────────────────────────────┐
│      Service Layer (Business Logic)     │
│  DocumentWorkflowService - Orchestrator │
│    - Parse LLM responses                │
│    - Determine workflow flow            │
│    - Trigger feature decomposition      │
│    - Maintain conversation state        │
└───────────────┬─────────────────────────┘
                │ LangChain Messages
                ▼
┌─────────────────────────────────────────┐
│      Data Layer (Persistence)           │
│   ConversationChainService - LLM + DB   │
│    - LangChain integration              │
│    - PostgreSQL persistence             │
│    - Custom chat history                │
└─────────────────────────────────────────┘
```

## New File Structure

```
src/
├── services/
│   ├── document_workflow_service.py     # NEW: Business logic layer
│   ├── conversation_chain_service.py    # Existing: Data layer
│   └── custom_chat_history.py           # Existing: Database integration
└── ui/
    ├── __init__.py                       # NEW: UI module
    └── cli_presenter.py                  # NEW: Presentation layer

reckie-cli-refactored.py                  # NEW: Clean CLI entry point
reckie-cli.py                             # OLD: Legacy (keep for reference)
```

## Layer Responsibilities

### 1. UI Layer (`src/ui/cli_presenter.py`)

**Purpose**: Handle ALL user interaction and display

**Responsibilities**:
- Display markdown previews
- Show questions and collect answers
- Request feedback from users
- Save files to disk
- Display errors with recovery options
- NO business logic
- NO LLM communication

**Key Methods**:
```python
class CLIPresenter:
    def handle_response(self, response: WorkflowResponse) -> dict:
        """Route response to appropriate handler"""

    def _show_document_preview(self, response: WorkflowResponse):
        """Display markdown in rich panel"""

    def _ask_questions(self, response: WorkflowResponse) -> dict:
        """Collect answers from user"""

    def _request_feedback(self, response: WorkflowResponse) -> dict:
        """Show doc and ask: accept or feedback?"""

    def _save_document(self, response: WorkflowResponse) -> dict:
        """Write file to disk"""

    def _show_error(self, response: WorkflowResponse) -> dict:
        """Display error with recovery options"""
```

**Input**: `WorkflowResponse` from service
**Output**: `dict` with user's decision/input

---

### 2. Service Layer (`src/services/document_workflow_service.py`)

**Purpose**: Orchestrate workflow and business logic

**Responsibilities**:
- Send messages to LLM
- Parse LLM responses (JSON extraction)
- Determine what UI should do next
- Trigger feature decomposition when appropriate
- Manage workflow state (pre/post decomposition)
- Build context-aware prompts
- NO user interaction
- NO file I/O (except through data layer)

**Key Methods**:
```python
class DocumentWorkflowService:
    def send_user_input(self, user_input: str) -> WorkflowResponse:
        """Process user input, get LLM response, return UI action"""

    def handle_user_acceptance(self) -> WorkflowResponse:
        """Handle doc acceptance, decide if decomposition needed"""

    def trigger_feature_decomposition(self, vision: str) -> WorkflowResponse:
        """Replace system prompt and trigger decomposition"""

    def handle_user_feedback(self, feedback: str) -> WorkflowResponse:
        """Build feedback prompt with context"""

    def handle_question_answers(self, answers: dict) -> WorkflowResponse:
        """Format answers and send to LLM"""
```

**Input**: User messages, feedback, answers (strings/dicts)
**Output**: `WorkflowResponse` (action + data for UI)

---

### 3. Data Layer (`src/services/conversation_chain_service.py`)

**Purpose**: Handle LLM and database persistence

**Responsibilities**:
- LangChain integration
- OpenAI API calls
- PostgreSQL message storage
- Custom chat history implementation
- NO workflow logic
- NO UI logic

**Key Methods**:
```python
class ConversationChainService:
    def create_chain(self, conversation_id, user_id, document_id) -> ConversationChain:
        """Create LangChain chain with PostgreSQL memory"""

    async def stream_response(self, conversation_id, user_message) -> AsyncIterator[str]:
        """Stream LLM response token by token"""

    def get_conversation_history(self, conversation_id) -> list[dict]:
        """Retrieve conversation history from DB"""
```

---

## Data Flow

### Example: User Accepts Document

```
1. UI Layer (CLIPresenter):
   User clicks "1. Accept this version"
   ↓
   Returns: {"action": "accept_document"}

2. CLI Main Loop:
   Receives UI result
   ↓
   Calls: workflow_service.handle_user_acceptance()

3. Service Layer (DocumentWorkflowService):
   Checks if decomposition needed
   ↓
   Returns: WorkflowResponse(
     action=SAVE_DOCUMENT,
     data={"file_path": "...", "trigger_decomposition": True}
   )

4. CLI Main Loop:
   Receives WorkflowResponse
   ↓
   Calls: presenter.handle_response(response)

5. UI Layer (CLIPresenter):
   Saves file to disk
   Shows: "✅ Document saved!"
   Shows: "🔍 Starting feature decomposition..."
   ↓
   Returns: {"action": "trigger_decomposition", "content": "..."}

6. CLI Main Loop:
   Receives trigger signal
   ↓
   Calls: workflow_service.trigger_feature_decomposition(content)

7. Service Layer:
   Replaces system prompt
   Sends decomposition request to LLM
   ↓
   Returns: WorkflowResponse(action=REQUEST_FEEDBACK, data={"content": "..."})

8. Back to UI Layer:
   Shows feature breakdown table
   Asks: "Accept or provide feedback?"
```

---

## Key Abstractions

### WorkflowResponse

**Purpose**: Structured communication from service to UI

```python
@dataclass
class WorkflowResponse:
    action: WorkflowAction  # What UI should do
    data: dict              # Data needed by UI
    metadata: dict          # Optional extra info

    # Convenience properties
    @property
    def document_content(self) -> Optional[str]:
        """Get document markdown"""

    @property
    def questions(self) -> Optional[list]:
        """Get questions for user"""
```

**Actions**:
- `SHOW_DOCUMENT_PREVIEW` → Display markdown
- `ASK_QUESTIONS` → Collect answers
- `REQUEST_FEEDBACK` → Show doc, ask accept/feedback
- `SAVE_DOCUMENT` → Write to disk
- `SHOW_ERROR` → Display error with recovery
- `EXIT_WORKFLOW` → End conversation

---

### WorkflowAction Enum

```python
class WorkflowAction(Enum):
    SHOW_DOCUMENT_PREVIEW = "show_document_preview"
    ASK_QUESTIONS = "ask_questions"
    REQUEST_FEEDBACK = "request_feedback"
    SAVE_DOCUMENT = "save_document"
    SHOW_ERROR = "show_error"
    EXIT_WORKFLOW = "exit_workflow"
```

**Why Enum?**
- Type safety
- Clear contract between layers
- Easy to extend
- Self-documenting

---

### FeedbackPhase Enum

```python
class FeedbackPhase(Enum):
    PRE_DECOMPOSITION = "pre_decomposition"
    POST_DECOMPOSITION = "post_decomposition"
```

**Purpose**: Service tracks whether features have been added

- `PRE_DECOMPOSITION`: Normal document refinement
- `POST_DECOMPOSITION`: Feature refinement only (no re-decomposition)

---

## Benefits

### 1. **Testability**

**Before**:
```python
# Can't test without mocking Rich console, LLM, user input
def test_workflow():
    # Hard to test mixed UI/business logic
```

**After**:
```python
# Test service layer independently
def test_document_acceptance():
    service = DocumentWorkflowService(...)
    response = service.handle_user_acceptance()
    assert response.action == WorkflowAction.SAVE_DOCUMENT
    assert response.data["trigger_decomposition"] == True

# Test UI layer independently
def test_presenter_displays_error():
    presenter = CLIPresenter(console=mock_console)
    response = WorkflowResponse(
        action=WorkflowAction.SHOW_ERROR,
        data={"error_message": "Test error"}
    )
    result = presenter.handle_response(response)
    assert "retry" in result["action"]
```

### 2. **Reusability**

**Service layer** can be reused in:
- Web API (FastAPI)
- Desktop app (PyQt)
- Mobile app backend
- Batch processing scripts

**UI layer** is independent:
- Swap Rich console for Streamlit
- Add web interface
- Create API endpoints

### 3. **Maintainability**

**Clear responsibilities**:
- Bug in display? → Check `CLIPresenter`
- Bug in workflow logic? → Check `DocumentWorkflowService`
- Bug in LLM calls? → Check `ConversationChainService`

**Easy to extend**:
- Add new action? → Add to `WorkflowAction` enum
- New document type? → Add to service, UI stays same
- New output format? → Add new presenter

### 4. **Type Safety**

**Structured responses** instead of tuples:

**Before**:
```python
continue_workflow, question_answers, document_path = execute_action(...)
# What does each value mean? Hard to remember!
```

**After**:
```python
response = workflow_service.send_user_input(user_input)
# response.action is clear
# response.document_content is explicit
# response.questions is typed
```

---

## Migration Path

### Phase 1: Side-by-side (Current)
- Keep `reckie-cli.py` (legacy)
- Add `reckie-cli-refactored.py` (new)
- Both work, compare behavior

### Phase 2: Testing
- Test refactored version extensively
- Verify feature parity
- Add unit tests for service layer

### Phase 3: Cutover
- Rename `reckie-cli.py` → `reckie-cli-legacy.py`
- Rename `reckie-cli-refactored.py` → `reckie-cli.py`
- Remove legacy after validation period

---

## Testing Strategy

### Unit Tests (Service Layer)

```python
# tests/unit/test_workflow_service.py
def test_should_trigger_decomposition():
    service = DocumentWorkflowService(
        document_type="vision_document",
        ...
    )
    service.current_content = "# Vision\n\nSome content"
    assert service._should_trigger_decomposition() == True

    service.current_content = "# Vision\n\n## Feature Breakdown\n..."
    assert service._should_trigger_decomposition() == False
```

### Integration Tests (Service + LLM)

```python
# tests/integration/test_workflow_integration.py
def test_send_user_input_creates_document(mock_llm):
    service = DocumentWorkflowService(...)
    response = service.send_user_input("Create a vision doc")

    assert response.action == WorkflowAction.REQUEST_FEEDBACK
    assert "# Vision" in response.document_content
```

### E2E Tests (Full Stack)

```python
# tests/e2e/test_cli_workflow.py
def test_full_vision_to_features_flow(test_db):
    # Simulate full user journey
    # Assert document saved with features
```

---

## Future Enhancements

### 1. **Streaming Responses**

```python
class DocumentWorkflowService:
    async def send_user_input_streaming(self, user_input: str) -> AsyncIterator[WorkflowResponse]:
        """Stream responses as they come in"""
        async for chunk in self.conv_service.stream_response(...):
            yield WorkflowResponse(
                action=WorkflowAction.SHOW_DOCUMENT_PREVIEW,
                data={"content": chunk, "is_partial": True}
            )
```

### 2. **Web API Layer**

```python
# api/routes/documents.py
@app.post("/api/documents/create")
async def create_document(request: CreateDocumentRequest):
    service = DocumentWorkflowService(...)
    response = service.send_user_input(request.user_input)

    return WorkflowResponseSchema.from_workflow_response(response)
```

### 3. **Event-Driven Architecture**

```python
class DocumentWorkflowService:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    def handle_user_acceptance(self):
        # Emit event
        self.event_bus.emit("document.accepted", {...})

        if self._should_trigger_decomposition():
            self.event_bus.emit("decomposition.triggered", {...})
```

---

## Comparison: Before vs After

### Before (Mixed Concerns)

```python
# 800 lines of tangled UI + business logic
def chat():
    # UI code
    console.print("What would you like to do?")
    choice = Prompt.ask(...)

    # Business logic
    if choice == "1":
        response = chain.predict(input=user_prompt)

        # More UI
        console.print(Markdown(response))

        # More business logic
        if "## Feature Breakdown" not in content:
            chain.memory.clear()
            # ...

        # More UI
        user_choice = Prompt.ask(...)
```

### After (Clean Separation)

```python
# Service layer (business logic only)
class DocumentWorkflowService:
    def send_user_input(self, input: str) -> WorkflowResponse:
        response = self.chain.predict(input=input)
        parsed = self._parse_llm_response(response)
        return self._determine_ui_action(parsed)

# UI layer (presentation only)
class CLIPresenter:
    def handle_response(self, response: WorkflowResponse) -> dict:
        if response.action == WorkflowAction.REQUEST_FEEDBACK:
            return self._request_feedback(response)

# CLI (orchestration only)
def main():
    service = DocumentWorkflowService(...)
    presenter = CLIPresenter(...)

    response = service.send_user_input(user_input)
    ui_result = presenter.handle_response(response)
```

---

## Summary

✅ **Clean Architecture** implemented
✅ **3-layer separation**: UI → Service → Data
✅ **Type-safe** communication via `WorkflowResponse`
✅ **Testable** components
✅ **Reusable** service layer
✅ **Maintainable** codebase
✅ **Extensible** design

**New files**:
- `src/services/document_workflow_service.py` - Business logic
- `src/ui/cli_presenter.py` - Presentation layer
- `reckie-cli-refactored.py` - Clean entry point

**Next steps**:
1. Test refactored version
2. Add unit tests for service layer
3. Validate feature parity
4. Replace legacy CLI
