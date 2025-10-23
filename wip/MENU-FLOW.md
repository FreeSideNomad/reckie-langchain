# Menu Flow - Conversation Recording & Replay

## Initial Menu (No Logs)

When you first open the application (no recorded logs yet):

```
╭────────────────────────────────────────────────╮
│ Reckie CLI                                     │
│ Model: gpt-4o                                  │
│ State: PostgreSQL Persistence                  │
│ Type your prompts below. Press Ctrl+C to exit. │
╰────────────────────────────────────────────────╯


What would you like to do?
  1. Create document
  2. Chat (free-form)
  3. Exit

> Select option [1/2/3]:
```

## Initial Menu (With Logs)

Once you have recorded at least one conversation:

```
╭────────────────────────────────────────────────╮
│ Reckie CLI                                     │
│ Model: gpt-4o                                  │
│ State: PostgreSQL Persistence                  │
│ Type your prompts below. Press Ctrl+C to exit. │
╰────────────────────────────────────────────────╯


What would you like to do?
  1. Create document
  2. Replay conversation from log
  3. Chat (free-form)
  4. Exit

> Select option [1/2/3/4]:
```

## Recording Menu (Option 1: Create Document)

When you select "Create document", you'll be asked about recording:

```
Do you want to record this conversation?
  1. Yes - Record conversation
  2. No - Don't record

> Select option [1/2]:
```

### If You Select "Yes - Record conversation":

```
🔴 Recording conversation to: vision_document_20251003_151500.json

Select document type:
  1. Vision Document

> Select document type [1]:
```

The conversation proceeds normally, and all inputs/responses are logged.

At the end:

```
💾 Conversation saved to: conversation-logs/vision_document_20251003_151500.json
```

### If You Select "No - Don't record":

The conversation proceeds normally without recording.

## Replay Menu (Option 2: Replay Conversation)

When you select "Replay conversation from log":

```
Available conversation logs:

  1. vision_document_20251003_151500
     Document type: vision_document
     Started: 2025-10-03T15:15:00.123456
     Entries: 6 (~3 user inputs)

  2. vision_document_20251003_142300
     Document type: vision_document
     Started: 2025-10-03T14:23:00.789012
     Entries: 8 (~4 user inputs)

  0. Cancel

> Select log to replay [0/1/2]:
```

### After Selecting a Log:

```
✅ Loaded log: vision_document_20251003_151500
Document type: vision_document
Total entries: 6

Found 3 user inputs to replay

🎬 Starting replay mode

Press ENTER to execute each user input


Step 1/3
╭─────────────────────────────────────────────────────╮
│ User Input (from log)                               │
├─────────────────────────────────────────────────────┤
│ Create a job search application that aggregates     │
│ jobs from multiple sources                          │
╰─────────────────────────────────────────────────────╯

Press ENTER to execute this input:
```

You press ENTER, and the system executes that input:

```
⏳ Replaying step 1/3...

╭─────────────────────────────────────────────────────╮
│ System Response                                     │
├─────────────────────────────────────────────────────┤
│ [Markdown preview of generated document]            │
╰─────────────────────────────────────────────────────╯


Step 2/3
╭─────────────────────────────────────────────────────╮
│ User Input (from log)                               │
├─────────────────────────────────────────────────────┤
│ Add more detail about user authentication and       │
│ profile management                                  │
╰─────────────────────────────────────────────────────╯

Press ENTER to execute this input:
```

This continues for all user inputs in the log.

At the end:

```
✅ Replay completed
```

## Complete Workflow Example

### Recording a Conversation

```
> Select option [1/2/3]: 1

Do you want to record this conversation?
  1. Yes - Record conversation
  2. No - Don't record

> Select option [1/2]: 1

🔴 Recording conversation to: vision_document_20251003_153000.json

Select document type:
  1. Vision Document

> Select document type [1]: 1

💬 Please provide input for vision document creation

> Create a project management tool for remote teams

⏳ Waiting for response from gpt-4o...

╭──────────────────────────────────────────────╮
│ Document Preview                             │
├──────────────────────────────────────────────┤
│ [Generated vision document]                  │
╰──────────────────────────────────────────────╯

📋 Initial version of the document has been created based on your input.

What would you like to do?
  1. Accept this version (save and exit)
  2. Provide feedback for improvements

> Your choice [1/2]: 2

💬 Please provide your feedback

> Add more details about collaboration features

⏳ Waiting for response from gpt-4o...

╭──────────────────────────────────────────────╮
│ Document Preview                             │
├──────────────────────────────────────────────┤
│ [Updated vision document]                    │
╰──────────────────────────────────────────────╯

What would you like to do?
  1. Accept this version (save and exit)
  2. Provide feedback for improvements

> Your choice [1/2]: 1

✅ Document accepted and saved!

💾 Conversation saved to: conversation-logs/vision_document_20251003_153000.json
```

### Replaying the Conversation

Next time you open the app:

```
What would you like to do?
  1. Create document
  2. Replay conversation from log
  3. Chat (free-form)
  4. Exit

> Select option [1/2/3/4]: 2

Available conversation logs:

  1. vision_document_20251003_153000
     Document type: vision_document
     Started: 2025-10-03T15:30:00.123456
     Entries: 4 (~2 user inputs)

  0. Cancel

> Select log to replay [0/1]: 1

✅ Loaded log: vision_document_20251003_153000
Document type: vision_document
Total entries: 4

Found 2 user inputs to replay

🎬 Starting replay mode

Press ENTER to execute each user input


Step 1/2
╭─────────────────────────────────────────────────────╮
│ User Input (from log)                               │
├─────────────────────────────────────────────────────┤
│ Create a project management tool for remote teams   │
╰─────────────────────────────────────────────────────╯

Press ENTER to execute this input: [ENTER]

⏳ Replaying step 1/2...

╭──────────────────────────────────────────────╮
│ System Response                              │
├──────────────────────────────────────────────┤
│ [LLM generates new vision document]          │
╰──────────────────────────────────────────────╯


Step 2/2
╭─────────────────────────────────────────────────────╮
│ User Input (from log)                               │
├─────────────────────────────────────────────────────┤
│ Add more details about collaboration features       │
╰─────────────────────────────────────────────────────╯

Press ENTER to execute this input: [ENTER]

⏳ Replaying step 2/2...

╭──────────────────────────────────────────────╮
│ System Response                              │
├──────────────────────────────────────────────┤
│ [LLM generates updated document]             │
╰──────────────────────────────────────────────╯

✅ Replay completed
```

## Key Features

### Recording
- ✅ Asks about recording BEFORE selecting document type
- ✅ Visual indicator (`🔴 Recording conversation to: ...`)
- ✅ Logs all user inputs and system responses
- ✅ Saves to JSON file when conversation ends
- ✅ Confirmation message showing file path

### Replay
- ✅ Only appears if conversation logs exist
- ✅ Shows list with metadata (document type, timestamp, entry count)
- ✅ Step-by-step execution with ENTER key
- ✅ Visual panels showing user input and system response
- ✅ Progress indicator (Step X/Y)
- ✅ Completion message

### User Experience
- ✅ Clear, numbered options
- ✅ Consistent color coding (cyan for prompts, green for success, yellow for warnings)
- ✅ Rich panels for document previews
- ✅ Spinners during LLM processing
- ✅ Status indicators and progress updates

## Log File Location

All conversation logs are stored in:

```
conversation-logs/
├── vision_document_20251003_151500.json
├── vision_document_20251003_153000.json
└── ...
```

## Benefits

1. **Testing**: Replay conversations to verify LLM consistency
2. **Debugging**: Record problematic conversations for analysis
3. **Training**: Show team members how the system works
4. **Regression Testing**: Replay after code changes
5. **Documentation**: Use recorded conversations as examples

---

**Updated**: 2025-10-03
**Status**: Active ✅
