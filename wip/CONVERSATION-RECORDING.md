# Conversation Recording & Replay

## Overview

The refactored CLI (`reckie-cli-refactored.py`) now supports **conversation recording** and **replay** functionality. This allows you to:

1. Record all user inputs and system responses during a conversation
2. Save conversations to structured JSON log files
3. List and select from previously recorded conversations
4. Replay conversations step-by-step to test system behavior

## Features

### 📹 Recording Mode

**What it does**: Captures the complete conversation flow between user and system.

**What is logged**:
- User inputs (initial prompt, feedback, answers)
- System responses (document previews, questions, actions)
- Metadata (timestamps, action types, workflow state)
- Conversation metadata (IDs, document type, start/end times)

**Output**: JSON file in `conversation-logs/` directory

### 🎬 Replay Mode

**What it does**: Replays user inputs from a recorded conversation one step at a time.

**How it works**:
1. Select a conversation log from the list
2. System loads all user inputs from the log
3. Each user input is displayed in a panel
4. Press ENTER to execute that input and see system response
5. Continue through all steps

**Use cases**:
- Testing LLM response consistency
- Debugging workflow issues
- Demonstrating conversation flows
- Regression testing after code changes

## Usage

### Starting the CLI

```bash
python reckie-cli-refactored.py
```

### Main Menu Options

```
What would you like to do?
  1. Create document
  2. Create document (with recording)
  3. Replay conversation from log
  4. Chat (free-form)
  5. Exit
```

**Note**: Option 3 (Replay) only appears if conversation logs exist.

### Recording a Conversation

1. Select **"2. Create document (with recording)"**
2. Choose document type (e.g., Vision Document)
3. CLI displays: `🔴 Recording conversation to: vision_document_20251003_151102.json`
4. Proceed with normal workflow (create document, provide feedback, etc.)
5. When workflow completes: `💾 Conversation saved to: conversation-logs/vision_document_20251003_151102.json`

### Replaying a Conversation

1. Select **"3. Replay conversation from log"**
2. CLI shows list of available logs:

```
Available conversation logs:

  1. vision_document_20251003_151102
     Document type: vision_document
     Started: 2025-10-03T15:11:02.255184
     Entries: 4 (~2 user inputs)

  0. Cancel
```

3. Select a log by number
4. CLI displays: `🎬 Starting replay mode`
5. For each user input:
   - See the input in a highlighted panel
   - Press ENTER to execute
   - View the system response
   - Continue to next step

6. When complete: `✅ Replay completed`

## Log File Format

Conversation logs are saved as JSON in `conversation-logs/` directory.

### File Naming

Format: `{document_type}_{timestamp}.json`

Example: `vision_document_20251003_151102.json`

### JSON Structure

```json
{
  "log_id": "vision_document_20251003_151102",
  "conversation_id": "d1f41d39-ba5d-4dbc-a5c9-1a29fcd3c8aa",
  "user_id": "69a94d8a-663d-4f31-bda9-db2eaaa693ca",
  "document_type": "vision_document",
  "started_at": "2025-10-03T15:11:02.255184",
  "ended_at": "2025-10-03T15:11:02.255273",
  "entries": [
    {
      "timestamp": "2025-10-03T15:11:02.255243",
      "entry_type": "user_input",
      "content": "Create a vision document for a job search app",
      "metadata": {
        "step": "initial_input"
      }
    },
    {
      "timestamp": "2025-10-03T15:11:02.255253",
      "entry_type": "system_response",
      "content": "Vision document created with sections...",
      "metadata": {
        "action": "create-document",
        "duration": 2.45
      }
    },
    {
      "timestamp": "2025-10-03T15:11:02.255260",
      "entry_type": "user_input",
      "content": "Add more detail to the features section",
      "metadata": {
        "action": "provide_feedback"
      }
    },
    {
      "timestamp": "2025-10-03T15:11:02.255267",
      "entry_type": "system_response",
      "content": "Updated vision document with detailed features...",
      "metadata": {
        "action": "update-document",
        "duration": 3.12
      }
    }
  ]
}
```

### Fields Explained

**Root Level**:
- `log_id`: Unique identifier for this log
- `conversation_id`: UUID of the conversation
- `user_id`: UUID of the user
- `document_type`: Type of document (e.g., "vision_document")
- `started_at`: ISO timestamp when recording started
- `ended_at`: ISO timestamp when recording stopped
- `entries`: Array of conversation entries

**Entry Fields**:
- `timestamp`: ISO timestamp of this entry
- `entry_type`: Either "user_input" or "system_response"
- `content`: The actual text content
- `metadata`: Additional context (action type, step, duration, etc.)

## Implementation Details

### ConversationLogger Class

Location: `src/services/conversation_logger.py`

**Key Methods**:

```python
# Start recording
log_id = logger.start_recording(
    conversation_id=uuid4(),
    user_id=uuid4(),
    document_type="vision_document"
)

# Log user input
logger.log_user_input(
    user_input="Create a vision document",
    metadata={"step": "initial_input"}
)

# Log system response
logger.log_system_response(
    response="Document created...",
    metadata={"action": "create-document", "duration": 2.5}
)

# Stop and save recording
log_file = logger.stop_recording()

# List all logs
logs = logger.list_logs()

# Load a specific log
conversation_log = logger.load_log(log_file_path)

# Extract user inputs for replay
user_inputs = logger.get_user_inputs(conversation_log)
```

### Integration Points

**Recording** (reckie-cli-refactored.py):

1. **Start recording** after document type selection:
   ```python
   if is_recording:
       log_id = conv_logger.start_recording(...)
       console.print(f"🔴 Recording conversation to: {log_id}.json")
   ```

2. **Log user inputs** throughout workflow:
   ```python
   if is_recording:
       conv_logger.log_user_input(user_input, metadata={...})
   ```

3. **Log system responses** after LLM calls:
   ```python
   if is_recording:
       conv_logger.log_system_response(
           response=str(response.data),
           metadata={"action": response.action.value, "duration": duration}
       )
   ```

4. **Stop recording** when workflow completes:
   ```python
   if is_recording:
       log_file = conv_logger.stop_recording()
       console.print(f"💾 Conversation saved to: {log_file}")
   ```

**Replay** (reckie-cli-refactored.py):

1. **Select log file**:
   ```python
   log_file_path = select_log_file(conv_logger)
   conversation_log = conv_logger.load_log(log_file_path)
   ```

2. **Extract user inputs**:
   ```python
   user_inputs = conv_logger.get_user_inputs(conversation_log)
   ```

3. **Replay step-by-step**:
   ```python
   for idx, (user_input, metadata) in enumerate(user_inputs, 1):
       console.print(f"Step {idx}/{len(user_inputs)}")
       console.print(Panel(user_input, title="User Input (from log)"))

       Prompt.ask("Press ENTER to execute this input", default="")

       response = workflow_service.send_user_input(user_input)
       presenter.handle_response(response)
   ```

## Benefits

### 1. Testing & Debugging

- **Consistency Testing**: Replay the same inputs to verify LLM responses are consistent
- **Regression Testing**: After code changes, replay conversations to ensure behavior hasn't broken
- **Bug Reproduction**: Record a conversation that triggers a bug, replay to reproduce

### 2. Demonstration & Training

- **Onboarding**: Show new team members how the system works by replaying sample conversations
- **Demos**: Replay well-crafted conversations for stakeholder demos
- **Documentation**: Use recorded conversations as examples in documentation

### 3. Analysis & Improvement

- **Response Time Tracking**: Metadata includes duration for each system response
- **User Behavior Analysis**: See what inputs users provide at each workflow step
- **Prompt Engineering**: Compare responses with different user inputs

## Example Workflow

### Recording a Vision Document Creation

```bash
$ python reckie-cli-refactored.py

What would you like to do?
  1. Create document
  2. Create document (with recording)
  3. Replay conversation from log
  4. Chat (free-form)
  5. Exit

> Select option: 2

Select document type:
  1. Vision Document

> Select document type: 1

🔴 Recording conversation to: vision_document_20251003_151500.json

💬 Please provide input for vision document creation

> Create a job search application that aggregates jobs from multiple sources

⏳ Waiting for response from gpt-4o...

[Document preview shown]

📋 Initial version of the document has been created based on your input.

What would you like to do?
  1. Accept this version (save and exit)
  2. Provide feedback for improvements

> Your choice: 2

💬 Please provide your feedback

> Add more detail about user authentication and profile management

⏳ Waiting for response from gpt-4o...

[Updated document preview shown]

What would you like to do?
  1. Accept this version (save and exit)
  2. Provide feedback for improvements

> Your choice: 1

✅ Document saved: /Users/igor/code/langchain-demo/reckie-docs/vision.md

💾 Conversation saved to: conversation-logs/vision_document_20251003_151500.json
```

### Replaying the Recorded Conversation

```bash
$ python reckie-cli-refactored.py

What would you like to do?
  1. Create document
  2. Create document (with recording)
  3. Replay conversation from log
  4. Chat (free-form)
  5. Exit

> Select option: 3

Available conversation logs:

  1. vision_document_20251003_151500
     Document type: vision_document
     Started: 2025-10-03T15:15:00.123456
     Entries: 6 (~3 user inputs)

  0. Cancel

> Select log to replay: 1

✅ Loaded log: vision_document_20251003_151500
Found 3 user inputs to replay

🎬 Starting replay mode

Press ENTER to execute each user input


Step 1/3
┌─────────────────────────────────────────┐
│ User Input (from log)                   │
├─────────────────────────────────────────┤
│ Create a job search application that    │
│ aggregates jobs from multiple sources   │
└─────────────────────────────────────────┘

Press ENTER to execute this input: [ENTER]

⏳ Replaying step 1/3...

[System shows document preview]


Step 2/3
┌─────────────────────────────────────────┐
│ User Input (from log)                   │
├─────────────────────────────────────────┤
│ Add more detail about user              │
│ authentication and profile management   │
└─────────────────────────────────────────┘

Press ENTER to execute this input: [ENTER]

⏳ Replaying step 2/3...

[System shows updated document preview]


Step 3/3
[Auto-accepting document (replay mode)]

✅ Replay completed
```

## Testing

Run the test script to verify ConversationLogger functionality:

```bash
python test_conversation_logger.py
```

Expected output:

```
🧪 Testing ConversationLogger

✅ Started recording: vision_document_20251003_151102
✅ Logged user input 1
✅ Logged system response 1
✅ Logged user input 2
✅ Logged system response 2
✅ Saved log to: conversation-logs-test/vision_document_20251003_151102.json

📋 Found 1 log(s):
   - vision_document_20251003_151102 (4 entries)

✅ Loaded log: vision_document_20251003_151102
   Document type: vision_document
   Total entries: 4

👤 Found 2 user inputs:
   1. Create a vision document for a job search app...
      Metadata: {'step': 'initial_input'}
   2. Add more detail to the features section...
      Metadata: {'action': 'provide_feedback'}

✅ All tests passed!
```

## Future Enhancements

### Planned Features

1. **Diff Comparison**
   - Compare system responses between two replay runs
   - Highlight differences in LLM outputs
   - Track response consistency over time

2. **Batch Replay**
   - Replay multiple conversations automatically
   - Generate comparison reports
   - Identify regression patterns

3. **Export Formats**
   - Export logs to CSV for analysis
   - Generate HTML report with conversation flow
   - Export to Markdown for documentation

4. **Filtering & Search**
   - Filter logs by document type
   - Search logs by user input content
   - Filter by date range

5. **Annotations**
   - Add notes to log entries
   - Mark entries as "expected" or "unexpected"
   - Tag logs for categorization

## Troubleshooting

### No logs appear in replay menu

**Issue**: Selected "Replay conversation" but no logs are shown.

**Solution**: Create a conversation with recording first:
1. Select "Create document (with recording)"
2. Complete the workflow
3. Verify log file created in `conversation-logs/` directory

### Log file corrupted or unreadable

**Issue**: Error when loading log file.

**Solution**: Check JSON validity:
```bash
python -m json.tool conversation-logs/your_log_file.json
```

If invalid JSON, the file may have been manually edited or interrupted during save.

### Replay doesn't match original conversation

**Issue**: Replay produces different system responses than original conversation.

**Expected behavior**: LLM responses are non-deterministic. Even with the same inputs, the system may produce slightly different outputs.

**Workaround**: Use lower temperature settings in the LLM for more consistent responses (adjust in `DocumentWorkflowService`).

## Summary

✅ **Recording**: Captures complete conversation flow to JSON
✅ **Replay**: Step-by-step playback of user inputs
✅ **Structured Logs**: Well-formatted JSON with metadata
✅ **Easy Integration**: Minimal code changes to existing workflow
✅ **Testing Support**: Enables regression testing and debugging

**Files**:
- `src/services/conversation_logger.py` - Core logging functionality
- `reckie-cli-refactored.py` - CLI integration
- `conversation-logs/` - Log storage directory
- `test_conversation_logger.py` - Test script

**Next Steps**:
1. Try recording a conversation
2. Replay it to see system behavior
3. Compare responses across multiple replays
4. Use for testing after code changes

---

**Added**: 2025-10-03
**Status**: Active ✅
