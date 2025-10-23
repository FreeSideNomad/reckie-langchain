# Recording & Markdown Validation Improvements

## Issues Fixed

### 1. ✅ Question/Answer Recording
**Problem**: Questions and answers were not being logged during recording, making it impossible to replay them.

**Solution**:
- Updated `question_handler()` to accept `conv_logger` and `is_recording` parameters
- Log each question as a system response with metadata
- Log each answer as user input with metadata
- Updated `execute_action()` to pass logger to question handler

**What's Logged**:
```json
{
  "timestamp": "2025-10-03T15:30:00.123456",
  "entry_type": "system_response",
  "content": "What are the main business goals?",
  "metadata": {
    "action": "question",
    "question_id": "q1",
    "question_index": 1
  }
}
{
  "timestamp": "2025-10-03T15:30:15.789012",
  "entry_type": "user_input",
  "content": "Increase user engagement and retention",
  "metadata": {
    "action": "answer_question",
    "question_id": "q1",
    "question_index": 1
  }
}
```

### 2. ✅ Markdown Validation with 3-Attempt Retry
**Problem**: LLM still returns improperly formatted markdown with escaped newlines (`\n`) instead of actual line breaks.

**Solution**:
- Added `has_escaped_newlines()` function to detect formatting issues
- Added `validate_and_fix_markdown()` function with 3-attempt retry logic
- Validate markdown **BEFORE** displaying to user
- Automatically request reformatting if issues detected
- Stop after 3 attempts to prevent endless loop

**How It Works**:
1. LLM returns response
2. Parse JSON
3. **Validate markdown** (NEW step)
   - Check for escaped newlines
   - If found: send reformatting request to LLM
   - Retry up to 3 times
   - If still broken after 3 attempts: show warning and display as-is
4. Display validated content to user

**Example Flow**:
```
LLM Response 1: "Vision Document\n\n## Introduction\n..." (escaped newlines)
↓
Validation detects issue
↓
Send reformat request: "CRITICAL: Use actual line breaks, not \n"
↓
LLM Response 2: Still has escaped newlines
↓
Retry (attempt 2/3)
↓
LLM Response 3: Properly formatted! ✅
↓
Show to user
```

### 3. ✅ Strengthened System Prompt
**Problem**: LLM needs stronger instructions about markdown formatting.

**Solution**: Added CRITICAL REQUIREMENTS section to system prompt:

```
## MARKDOWN FORMATTING - ABSOLUTELY CRITICAL
- **NEVER** use escaped newlines (\n) in the content field
- **ALWAYS** use actual line breaks in your JSON content
- The content field MUST contain properly formatted markdown with real newlines
- **DO NOT** write content as a single line with \n escape sequences
- Format markdown with proper spacing: blank lines between sections, proper heading hierarchy
- Example of CORRECT formatting:
  {
    "action": "create-document",
    "content": "# Heading\n\nParagraph text.\n\n## Section\n\nMore content."
  }
- If you return improperly formatted markdown, you will be asked to reformat it
```

## Code Changes

### Modified Functions

1. **`question_handler()`** (`reckie-cli.py:173`)
   - Added `conv_logger` and `is_recording` parameters
   - Log each question as system response
   - Log each answer as user input

2. **`execute_action()`** (`reckie-cli.py:399`)
   - Added `conv_logger` and `is_recording` parameters
   - Pass to question handler

3. **`build_system_prompt()`** (`reckie-cli.py:55`)
   - Added CRITICAL REQUIREMENTS section
   - Added MARKDOWN FORMATTING section with strong language

### New Functions

1. **`has_escaped_newlines(content: str) -> bool`** (`reckie-cli.py:343`)
   - Detects literal `\n` strings in content
   - Detects long content on 1-3 lines (indicates escaped newlines)

2. **`validate_and_fix_markdown(chain, content, action, max_attempts=3) -> str`** (`reckie-cli.py:365`)
   - Validates markdown formatting
   - Auto-requests reformatting if issues found
   - Retries up to 3 times
   - Returns validated content

### Updated Call Sites

1. **Main workflow loop** (`reckie-cli.py:933-937`)
   ```python
   # Validate and fix markdown formatting BEFORE displaying
   if content and action in ("create-document", "update-document"):
       content = validate_and_fix_markdown(chain, content, action, max_attempts=3)
       response_data["content"] = content
   ```

2. **execute_action calls** (`reckie-cli.py:855, 892`)
   ```python
   execute_action(
       response_data, config, save_document=False,
       conv_logger=conv_logger, is_recording=is_recording
   )
   ```

## Testing

### Test Question Recording

1. Run CLI with recording enabled
2. LLM asks questions
3. Answer questions
4. Check log file - should contain:
   - Each question as `system_response`
   - Each answer as `user_input`
   - Metadata with `question_id` and `question_index`

### Test Markdown Validation

1. If LLM returns escaped newlines:
   - CLI shows: `⚠️ Detected formatting issues. Requesting proper markdown formatting (attempt 1/3)...`
   - Auto-sends reformat request
   - Retries up to 3 times
   - Shows properly formatted markdown

2. If LLM returns proper markdown:
   - No reformatting needed
   - Shows content immediately

### Test 3-Attempt Limit

1. If LLM fails to format properly after 3 attempts:
   - Shows: `❌ Could not properly format markdown after 3 attempts. Showing content as-is.`
   - Displays the content anyway (prevents endless loop)

## Benefits

### Question Recording
- ✅ Complete conversation replay including Q&A
- ✅ Can test question-based workflows
- ✅ Full audit trail of all user interactions

### Markdown Validation
- ✅ Auto-fixes formatting issues before showing to user
- ✅ Prevents displaying broken markdown
- ✅ 3-attempt limit prevents infinite loops
- ✅ Stronger system prompt reduces formatting issues

### User Experience
- ✅ Always see properly formatted markdown
- ✅ No manual reformatting needed
- ✅ Transparent auto-correction (shows attempt count)
- ✅ Graceful degradation (shows content after 3 failed attempts)

## Example Logs

### Question/Answer Recording
```json
{
  "log_id": "vision_document_20251003_153000",
  "entries": [
    {
      "timestamp": "2025-10-03T15:30:00.123456",
      "entry_type": "user_input",
      "content": "Create a vision document",
      "metadata": {"step": "initial_input"}
    },
    {
      "timestamp": "2025-10-03T15:30:05.789012",
      "entry_type": "system_response",
      "content": "What are the main business goals?",
      "metadata": {
        "action": "question",
        "question_id": "q1",
        "question_index": 1
      }
    },
    {
      "timestamp": "2025-10-03T15:30:15.456789",
      "entry_type": "user_input",
      "content": "Increase engagement and retention",
      "metadata": {
        "action": "answer_question",
        "question_id": "q1",
        "question_index": 1
      }
    }
  ]
}
```

## Summary

✅ **Fixed**: Question/Answer recording for complete replay
✅ **Fixed**: Markdown validation with 3-attempt auto-correction
✅ **Improved**: System prompt with CRITICAL markdown requirements
✅ **Added**: Automatic formatting detection and correction
✅ **Protected**: Against endless loops with 3-attempt limit

All changes maintain backward compatibility. Recording works for all conversation types, and markdown validation only activates when needed.

---

**Updated**: 2025-10-03
**Status**: Complete ✅
