# Tech Spike: CLI LLM Interaction

**Purpose**: Experimental CLI to test LLM interactions with increasing complexity

**File**: `reckie-cli.py` (project root)

---

## Spike Questions & Answers

### 1. LLM Provider & Model
**Q**: Which LLM should we use?
- OpenAI (GPT-4, GPT-3.5)?
- Anthropic Claude (via existing project setup)?
- Other provider?

**A**: GPT-4 (use GPT-4o)

---

### 2. Existing Integration
**Q**: Should we reuse the existing LangChain setup from this project?
- I see `src/services/conversation_chain_service.py` exists
- Or start fresh with a simpler direct API call?

**A**: Direct but through LangChain

---

### 3. CLI Framework
**Q**: What level of interactivity?
- Simple input/output loop (basic `input()`)
- Rich CLI with Click framework (matches Feature F7 design)
- Interactive REPL with history/editing?

**A**: Click framework

---

### 4. Conversation State
**Q**: Should it maintain conversation history?
- Stateless (each prompt independent)
- Stateful session (multi-turn conversation)
- Save/load conversation history?

**A**: Not initially - we will evolve this

---

### 5. Output Formatting
**Q**: How should responses be displayed?
- Plain text
- Markdown rendering (using `rich` library)
- Streaming output (token-by-token)

**A**: Start with plain text

---

### 6. File Location
**Q**: Where should `reckie-cli.py` go?
- Project root (`/Users/igor/code/langchain-demo/reckie-cli.py`)
- `scripts/` directory
- Separate `spike/` or `experimental/` directory?

**A**: Root

---

### 7. Scope for First Iteration
**Q**: What's the minimal first version?
- Just send prompt → get response → display?
- Include basic error handling?
- Any specific prompts/use cases to test?

**A**: Prompt → get response → display

---

## Implementation Plan

### Phase 1: Minimal Viable Spike ✅ COMPLETE
- [x] Click CLI framework
- [x] Single prompt input
- [x] LangChain + GPT-4o integration
- [x] Plain text output
- [x] No conversation history

### Phase 2: Interactive UI & Actions ✅ COMPLETE
- [x] Rich library for colorful UI
- [x] Persistent `>` prompt (like Claude Code)
- [x] Status line with model info and response time
- [x] JSON response parsing
- [x] Action handler framework
- [x] `create-document` action handler
- [x] Config file (`reckie-cli-config.json`)
- [x] System prompts from config
- [x] INFO-level logging only (no DEBUG spam)
- [x] Interactive loop (prompt returns after each response)

### Phase 3: Menu System & Document Management ✅ COMPLETE
- [x] Main menu (Create document / Chat / Exit)
- [x] Document type selection menu
- [x] Initial messages from config
- [x] Output directory (`reckie-docs/`)
- [x] Auto-create output directory
- [x] Document type-specific system prompts
- [x] Free-form chat mode (no system prompt)

### Phase 4: Workflow Engine & PostgreSQL State ✅ COMPLETE
- [x] PostgreSQL conversation persistence via ConversationChainService
- [x] Hybrid workflow configuration (base_system_prompt + workflow_instructions + available_actions)
- [x] Dynamic system prompt generation from config
- [x] Question action with batch Q&A (ask all, answer all, send back)
- [x] Update-document action for iterative refinement
- [x] Complete action for workflow termination
- [x] Workflow loop (create → question → update → complete)
- [x] Conversation state stored in PostgreSQL `message_store` table
- [x] Action-based decision making (LLM decides which action to use)

### Phase 5: Evolution (Future)
- [ ] Add conversation history/memory
- [ ] Streaming output
- [ ] Save/load sessions
- [ ] Multi-turn conversation within same document
- [ ] Error handling & retries
- [ ] Token usage tracking
- [ ] Additional action handlers (update-document, delete-document)
- [ ] Document templates with variable substitution

---

**Created**: 2025-10-03
**Status**: Phase 3 - Complete
**Last Updated**: 2025-10-03
