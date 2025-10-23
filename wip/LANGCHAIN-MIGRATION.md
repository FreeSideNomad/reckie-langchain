# LangChain Migration: ConversationChain → RunnableWithMessageHistory

## Overview

Migrated from deprecated LangChain classes to modern equivalents, eliminating deprecation warnings.

**Status**: ✅ **Complete**
**Date**: 2025-10-03

---

## Changes Made

### 1. Deprecated Classes Removed

**Before** (Deprecated):
```python
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
```

**After** (Modern):
```python
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
```

### 2. Service Architecture Changes

#### `src/services/conversation_chain_service.py`

**Key Changes**:

1. **Session Management**: Added session configuration storage
   ```python
   self._connection_string: Optional[str] = None
   self._session_configs: dict[str, tuple[UUID, UUID, UUID]] = {}
   ```

2. **Session History Factory**: New method for retrieving session history
   ```python
   def _get_session_history(self, session_id: str) -> BaseChatMessageHistory:
       """Get chat message history for a session."""
       if session_id not in self._session_configs:
           raise ValueError(f"No configuration found for session {session_id}")

       conversation_id, user_id, document_id = self._session_configs[session_id]
       connection_string = self._connection_string or os.getenv("DATABASE_URL", "")

       return ConversationsChatMessageHistory(
           conversation_id=conversation_id,
           user_id=user_id,
           document_id=document_id,
           connection_string=connection_string
       )
   ```

3. **Chain Creation**: Modern prompt template + RunnableWithMessageHistory
   ```python
   # Create prompt template with message history placeholder
   prompt = ChatPromptTemplate.from_messages([
       ("system", "You are a helpful AI assistant."),
       MessagesPlaceholder(variable_name="chat_history"),
       ("human", "{input}"),
   ])

   # Create base runnable (prompt | llm)
   runnable = prompt | llm

   # Wrap with message history
   chain = RunnableWithMessageHistory(
       runnable=runnable,
       get_session_history=self._get_session_history,
       input_messages_key="input",
       history_messages_key="chat_history",
   )
   ```

4. **Streaming**: Updated to use config with session_id
   ```python
   config = {"configurable": {"session_id": session_id}}

   async for chunk in chain.astream({"input": user_message}, config=config):
       if isinstance(chunk, (AIMessage, HumanMessage)):
           if isinstance(chunk.content, str):
               yield chunk.content
   ```

### 3. Custom Chat History (No Changes Required)

**`src/services/custom_chat_history.py`** - No changes needed!

Our custom `ConversationsChatMessageHistory` already inherits from `BaseChatMessageHistory`, which is the modern, supported interface. This class continues to work without any modifications.

### 4. Test Updates

**`tests/unit/test_conversation_chain_service.py`**:

- Updated mocks from `ConversationChain` → `RunnableWithMessageHistory`
- Updated mocks from `PostgresChatMessageHistory` → `ConversationsChatMessageHistory`
- Updated test parameters to include `user_id` and `document_id` (required by new API)
- Updated streaming test to expect `AIMessage` chunks instead of dict responses

**All tests passing** ✅

---

## Benefits

### 1. No More Deprecation Warnings

**Before**:
```
LangChainDeprecationWarning: Please see the migration guide at:
https://python.langchain.com/docs/versions/migrating_memory/
memory = ConversationBufferMemory(...)

LangChainDeprecationWarning: The class `ConversationChain` was deprecated
in LangChain 0.2.7 and will be removed in 1.0.
Use :class:`~langchain_core.runnables.history.RunnableWithMessageHistory` instead.
```

**After**: No warnings! Clean console output.

### 2. Future-Proof

- Uses modern LangChain LCEL (LangChain Expression Language)
- Compatible with LangChain 1.0+
- Follows recommended architecture patterns

### 3. Maintainability

- Explicit session management
- Clear separation of concerns (prompt, LLM, memory)
- Easier to extend and modify

### 4. Flexibility

- Can easily swap out different prompt templates
- Can add multiple prompt messages
- Can use different memory backends

---

## API Compatibility

### Public API (No Breaking Changes)

All public methods maintain the same signatures:

```python
# Still works exactly the same
service = ConversationChainService()
chain = service.create_chain(conversation_id, user_id, document_id)

# Streaming still works
async for token in service.stream_response(
    conversation_id, user_id, document_id, "Hello"
):
    print(token)

# History retrieval still works
history = service.get_conversation_history(
    conversation_id, user_id, document_id
)
```

### Internal Implementation (Changed)

- `ConversationChain` → `RunnableWithMessageHistory`
- `ConversationBufferMemory` → Session-based history management
- Prompt construction now uses `ChatPromptTemplate`

---

## Migration Steps Taken

### Step 1: Update Imports
- ✅ Removed deprecated imports
- ✅ Added modern LangChain core imports

### Step 2: Refactor `create_chain()`
- ✅ Added session configuration storage
- ✅ Created `_get_session_history()` factory method
- ✅ Built prompt template with `ChatPromptTemplate`
- ✅ Created `RunnableWithMessageHistory` wrapper

### Step 3: Update `stream_response()`
- ✅ Added session config to `astream()` call
- ✅ Updated chunk handling for `AIMessage` responses

### Step 4: Update Tests
- ✅ Updated mocks for new classes
- ✅ Updated test assertions
- ✅ Verified all tests pass

### Step 5: Verify No Warnings
- ✅ Created test script (`test_migration.py`)
- ✅ Confirmed no deprecation warnings
- ✅ Verified correct class types

---

## Testing

### Verification Script

Created `test_migration.py` to verify migration:

```bash
python test_migration.py
```

**Output**:
```
✅ Creating ConversationChainService...
   Model: gpt-4-turbo
   Temperature: 0.7
   Max context: 10

✅ Creating chain...
   Chain type: RunnableWithMessageHistory
   Session configs: 1 sessions registered

✅ Service creation successful - no deprecation warnings!
   Migration to RunnableWithMessageHistory complete.
```

### Unit Tests

```bash
pytest tests/unit/test_conversation_chain_service.py -v
```

**Result**: All 8 tests passing ✅

---

## Rollback Plan (If Needed)

If issues arise, rollback is straightforward:

1. Revert `src/services/conversation_chain_service.py` to previous version
2. Revert `tests/unit/test_conversation_chain_service.py` to previous version
3. Re-add deprecation warning suppression

**No database schema changes**, so rollback is safe.

---

## References

- **LangChain Migration Guide**: https://python.langchain.com/docs/versions/migrating_memory/
- **RunnableWithMessageHistory Docs**: https://python.langchain.com/docs/how_to/message_history/
- **LangChain Expression Language**: https://python.langchain.com/docs/concepts/lcel/

---

## Summary

✅ **Successfully migrated** from deprecated `ConversationChain` to modern `RunnableWithMessageHistory`
✅ **No breaking changes** to public API
✅ **All tests passing**
✅ **No deprecation warnings**
✅ **Custom chat history** still works without changes
✅ **Future-proof** for LangChain 1.0+

---

**Author**: Claude Code (LLM Agent)
**Last Updated**: 2025-10-03
