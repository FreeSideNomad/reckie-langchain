# Feature Decomposition Flow

## Overview

When a user accepts a **Vision Document**, the system automatically triggers **Feature Decomposition** - an AI-powered analysis that breaks down the vision into 10-15 concrete features.

## Workflow

### Phase 1: Vision Document Creation

```
User: Create document → Vision Document
User: [Provides initial vision input]

LLM: Creates initial vision document
User: Provides feedback (optional, iterative)
User: Accepts final version

✅ Vision document saved
```

### Phase 2: Automatic Feature Decomposition

```
🔍 Starting feature decomposition from vision document...

[LLM analyzes vision and creates Feature Breakdown table]

📄 Document Preview (with Feature Breakdown):
┌─────────────────────────────────────────────┐
│ # Vision Document                           │
│                                             │
│ [Original vision content...]                │
│                                             │
│ ## Feature Breakdown                        │
│                                             │
│ | Feature ID | Feature Name | Description | │
│ |------------|--------------|-------------| │
│ | F01 | User Auth | • Secure login...      │ │
│ | F02 | Dashboard | • Real-time metrics... │ │
│ | ...        | ...          | ...         │ │
└─────────────────────────────────────────────┘

📋 Document has been updated with Feature Breakdown.

What would you like to do?
  1. Accept this version (save and exit)
  2. Provide feedback for improvements
```

### Phase 3: Refinement (Post-Decomposition)

After features are added, the user can refine:

- **Feature names**
- **Feature descriptions** (add/remove bullet points)
- **Release classification** (MVP vs R01, R02, etc.)
- **Add/remove features**
- **Modify vision content**

**IMPORTANT**: Feature decomposition runs **ONLY ONCE**. Subsequent feedback loops allow refinement but **do NOT re-trigger decomposition**.

## Feature Breakdown Table Format

```markdown
## Feature Breakdown

| Feature ID | Feature Name | Description | Release |
|------------|--------------|-------------|---------|
| F01 | User Authentication | • Secure login/logout functionality<br>• Password reset capability<br>• Multi-factor authentication<br>• Session management<br>• OAuth integration | MVP |
| F02 | Dashboard | • Real-time metrics display<br>• Customizable widgets<br>• Data visualization<br>• Export capabilities | MVP |
| F03 | Reporting Engine | • Custom report builder<br>• Scheduled reports<br>• PDF/Excel export<br>• Email distribution | R01 |
| F04 | Notification System | • Email notifications<br>• In-app notifications<br>• SMS alerts<br>• Notification preferences | MVP |
| F05 | User Management | • User roles and permissions<br>• Team management<br>• Invitation system<br>• Access control | R01 |
```

### Column Definitions:

1. **Feature ID**: Sequential format `F01`, `F02`, ... `F15`
2. **Feature Name**: Concise, 2-5 words
3. **Description**: 5-10 bullet points using `<br>` tags
4. **Release**: `MVP` or `R01`, `R02`, `R03`, etc.

## Implementation Details

### Trigger Condition

Feature decomposition triggers when:
- ✅ Document type is `vision_document`
- ✅ User accepts the document (chooses option 1)
- ✅ Document does NOT already contain `## Feature Breakdown`

### System Prompt

When decomposition is triggered, the LLM receives:

```
You are an expert product manager performing feature decomposition.

## Current Vision Document:
[Full vision content]

## Your Task:
Analyze and decompose into 10-15 features...
```

See `reckie-cli.py:build_feature_decomposition_prompt()` for full prompt.

### Conversation State

The decomposition phase:

1. **Clears existing conversation history**
   ```python
   chain.memory.chat_memory.clear()
   ```

2. **Replaces system prompt with decomposition prompt**
   ```python
   chain.memory.chat_memory.add_message(
       SystemMessage(content=decomposition_prompt)
   )
   ```

3. **Sends decomposition request**
   ```
   "Please analyze the vision document and create a
    Feature Breakdown table with 10-15 features."
   ```

### Post-Decomposition Refinement

After features are added, feedback prompts include:

```
Please revise the document based on this feedback.
You can modify any section including the Feature Breakdown table,
but do NOT re-run feature decomposition.
```

This prevents the LLM from:
- ❌ Re-analyzing the vision from scratch
- ❌ Regenerating all features
- ❌ Losing user refinements

## Example Session

### Complete Flow

```
$ python reckie-cli.py

What would you like to do?
  1. Create document
  2. Chat (free-form)
  3. Exit

> 1

Select document type:
  1. Vision Document
  2. Feature Document

> 1

💬 Please provide 5-10 sentences containing areas you would
   like to cover in your vision document.

> helpful app for RBC devs. isam sucks, can't run fullstack...

[LLM asks clarifying questions]

📄 Document Preview:
┌─────────────────────────────────────────────┐
│ # Vision Document                           │
│ ## Purpose                                  │
│ Improve developer experience at RBC...      │
└─────────────────────────────────────────────┘

📋 Initial version created.
What would you like to do?
  1. Accept
  2. Provide feedback

> 1

✅ Document accepted and saved!

🔍 Starting feature decomposition from vision document...
Analyzing vision and identifying features...

⏳ Waiting for response...

📄 Document Preview (with Feature Breakdown):
┌─────────────────────────────────────────────┐
│ ## Feature Breakdown                        │
│                                             │
│ | Feature ID | Feature Name | ...           │
│ | F01 | Local Dev Environment | ...         │
│ | F02 | Container Runtime | ...             │
│ | ...                                       │
└─────────────────────────────────────────────┘

📋 Document has been updated with Feature Breakdown.

What would you like to do?
  1. Accept
  2. Provide feedback

> 2

💬 Please provide your feedback
> Change F02 to MVP and add more details about Docker

[LLM refines Feature Breakdown table]

📄 Document Preview (updated):
[Shows refined version]

What would you like to do?
  1. Accept
  2. Provide feedback

> 1

✅ Document accepted and saved!
```

## Database Storage

All iterations (including decomposition) are stored in `conversations` table:

```sql
SELECT
  id,
  user_id,
  document_id,
  jsonb_array_length(history) as message_count,
  history -> -1 -> 'data' -> 'content' as latest_message
FROM conversations
WHERE user_id = '2974bf21-34e3-4857-a86a-c6a6636875fc'
  AND document_id = '081b5e3c-d37e-4e26-92e7-52da464be5ef';
```

### Conversation History Includes:

1. Initial vision creation prompts/responses
2. User refinement feedback
3. Decomposition prompt (system message)
4. Feature breakdown response
5. Post-decomposition refinement feedback

## Configuration

No changes needed to `reckie-cli-config.json`.

Feature decomposition is triggered programmatically based on:
- Document type (`vision_document`)
- Document state (accepted by user)
- Content check (no existing Feature Breakdown)

## Testing

### Manual Test:

1. Run CLI: `python reckie-cli.py`
2. Create Vision Document
3. Provide vision input
4. Accept document when satisfied
5. **Verify**: Feature decomposition triggers automatically
6. **Verify**: Feature Breakdown table appears (10-15 features)
7. Provide feedback to refine features
8. **Verify**: Decomposition does NOT re-run
9. Accept final version

### Automated Test:

```python
# TODO: Create integration test for feature decomposition flow
# tests/integration/test_feature_decomposition.py
```

## Future Enhancements

- [ ] Allow user to specify number of features (default: 10-15)
- [ ] Support epic-level decomposition (F01 → E01, E02, E03)
- [ ] Generate user stories from feature descriptions
- [ ] Export features to GitHub Issues
- [ ] Link features to JIRA/Linear tickets
