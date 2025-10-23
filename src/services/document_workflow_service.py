"""Document workflow orchestration service.

Separates business logic from UI presentation.
Handles conversation flow, document creation, and feature decomposition.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID

from langchain.schema import SystemMessage

from src.services.conversation_chain_service import ConversationChainService


class WorkflowAction(Enum):
    """Actions the UI should perform based on service response."""
    SHOW_DOCUMENT_PREVIEW = "show_document_preview"
    ASK_QUESTIONS = "ask_questions"
    REQUEST_FEEDBACK = "request_feedback"
    SAVE_DOCUMENT = "save_document"
    SHOW_ERROR = "show_error"
    EXIT_WORKFLOW = "exit_workflow"


class FeedbackPhase(Enum):
    """Phase of the feedback loop."""
    PRE_DECOMPOSITION = "pre_decomposition"  # Normal document refinement
    POST_DECOMPOSITION = "post_decomposition"  # Feature refinement only


@dataclass
class WorkflowResponse:
    """Structured response from workflow service to UI."""
    action: WorkflowAction
    data: dict
    metadata: Optional[dict] = None

    @property
    def document_content(self) -> Optional[str]:
        """Get document content if available."""
        return self.data.get("content")

    @property
    def questions(self) -> Optional[list]:
        """Get questions if available."""
        return self.data.get("questions")

    @property
    def error_message(self) -> Optional[str]:
        """Get error message if available."""
        return self.data.get("error_message")

    @property
    def file_path(self) -> Optional[str]:
        """Get file path if available."""
        return self.data.get("file_path")


class DocumentWorkflowService:
    """Orchestrates document creation workflow.

    Responsibilities:
    - Manage conversation flow with LLM
    - Parse LLM responses
    - Determine next UI action
    - Handle feature decomposition triggers
    - Maintain workflow state
    """

    def __init__(
        self,
        conversation_id: UUID,
        user_id: UUID,
        document_id: UUID,
        document_type: str,
        system_prompt: str,
        model: str = "gpt-4o",
        db_url: Optional[str] = None
    ):
        """Initialize workflow service.

        Args:
            conversation_id: Unique conversation ID
            user_id: User UUID
            document_id: Document UUID
            document_type: Type of document (e.g., "vision_document")
            system_prompt: Initial system prompt for LLM
            model: OpenAI model name
            db_url: Database connection string
        """
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.document_id = document_id
        self.document_type = document_type
        self.model = model
        self.db_url = db_url

        # Initialize conversation service
        self.conv_service = ConversationChainService(
            model=model,
            temperature=0.7
        )

        # Create chain with initial system prompt
        self.chain = self.conv_service.create_chain(
            conversation_id=conversation_id,
            user_id=user_id,
            document_id=document_id,
            connection_string=db_url
        )

        # Add system prompt
        self.chain.memory.chat_memory.add_message(SystemMessage(content=system_prompt))  # type: ignore[attr-defined]

        # Workflow state
        self.current_content: Optional[str] = None
        self.current_action: Optional[str] = None
        self.current_action_params: Optional[dict] = None
        self.feedback_phase = FeedbackPhase.PRE_DECOMPOSITION
        self.decomposition_triggered = False

    def send_user_input(self, user_input: str) -> WorkflowResponse:
        """Send user input to LLM and return structured response.

        Args:
            user_input: User's message/prompt

        Returns:
            WorkflowResponse with action and data for UI
        """
        try:
            # Send to LLM
            response = self.chain.predict(input=user_input)

            # Parse response
            parsed = self._parse_llm_response(response)

            if parsed is None:
                # Failed to parse - return error
                return WorkflowResponse(
                    action=WorkflowAction.SHOW_ERROR,
                    data={
                        "error_message": "Could not parse LLM response",
                        "raw_response": response[:2000]
                    }
                )

            # Extract action and content
            llm_action = parsed.get("action")
            content = parsed.get("content", "")
            action_params = parsed.get("action-params", {})

            # Validate markdown formatting if content is present
            if content and llm_action in ("create-document", "update-document"):
                if self._has_escaped_newlines(content):
                    # Content has \n instead of actual newlines - ask LLM to fix
                    return self._request_markdown_reformatting(content)

            # Store current state
            self.current_action = llm_action
            self.current_content = content
            self.current_action_params = action_params

            # Determine UI action based on LLM action
            return self._determine_ui_action(parsed)

        except Exception as e:
            return WorkflowResponse(
                action=WorkflowAction.SHOW_ERROR,
                data={
                    "error_message": f"Workflow error: {str(e)}",
                    "exception_type": type(e).__name__
                }
            )

    def handle_user_acceptance(self) -> WorkflowResponse:
        """Handle user accepting the document.

        Returns:
            WorkflowResponse indicating next action (save or decompose)
        """
        # First, save the document
        file_path = self._get_file_path()

        # Check if we should trigger feature decomposition
        if self._should_trigger_decomposition():
            # Mark as triggered
            self.decomposition_triggered = True
            self.feedback_phase = FeedbackPhase.POST_DECOMPOSITION

            return WorkflowResponse(
                action=WorkflowAction.SAVE_DOCUMENT,
                data={
                    "file_path": file_path,
                    "content": self.current_content,
                    "trigger_decomposition": True
                }
            )
        else:
            # Just save and exit
            return WorkflowResponse(
                action=WorkflowAction.SAVE_DOCUMENT,
                data={
                    "file_path": file_path,
                    "content": self.current_content,
                    "trigger_decomposition": False
                },
                metadata={"exit_after_save": True}
            )

    def trigger_feature_decomposition(self, vision_content: str) -> WorkflowResponse:
        """Trigger feature decomposition for vision document.

        Args:
            vision_content: Current vision document content

        Returns:
            WorkflowResponse to show decomposition in progress
        """
        # Build decomposition prompt
        decomposition_prompt = self._build_feature_decomposition_prompt(vision_content)

        # Replace system message
        self.chain.memory.chat_memory.clear()  # type: ignore[attr-defined]
        self.chain.memory.chat_memory.add_message(  # type: ignore[attr-defined]
            SystemMessage(content=decomposition_prompt)
        )

        # Send decomposition request
        decomposition_input = "Please analyze the vision document and create a Feature Breakdown table with 10-15 features."

        return self.send_user_input(decomposition_input)

    def handle_user_feedback(self, feedback: str) -> WorkflowResponse:
        """Handle user feedback for document refinement.

        Args:
            feedback: User's feedback text

        Returns:
            WorkflowResponse with refined document
        """
        # Build feedback prompt with context
        feedback_prompt = self._build_feedback_prompt(feedback)

        # Send to LLM
        return self.send_user_input(feedback_prompt)

    def handle_question_answers(self, answers: dict) -> WorkflowResponse:
        """Handle answers to LLM questions.

        Args:
            answers: Dict of question_id -> answer

        Returns:
            WorkflowResponse with updated document
        """
        # Format answers
        answer_text = "\n".join([
            f"{q_id}: {answer}"
            for q_id, answer in answers.items()
        ])

        # Send to LLM
        return self.send_user_input(
            f"Here are my answers:\n{answer_text}\n\n"
            f"Please update the document with this information."
        )

    def _parse_llm_response(self, response_text: str) -> Optional[dict]:
        """Parse LLM response as JSON.

        Args:
            response_text: Raw LLM response

        Returns:
            Parsed JSON dict or None if parsing failed
        """
        import json

        # Try to extract JSON from code block
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            json_text = response_text[start:end].strip()
        else:
            json_text = response_text.strip()

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            return None

    def _determine_ui_action(self, parsed_response: dict) -> WorkflowResponse:
        """Determine what the UI should do based on LLM response.

        Args:
            parsed_response: Parsed LLM JSON response

        Returns:
            WorkflowResponse with UI action
        """
        llm_action = parsed_response.get("action")
        content = parsed_response.get("content", "")

        if llm_action == "question":
            # LLM wants to ask questions
            questions = parsed_response.get("questions", [])
            return WorkflowResponse(
                action=WorkflowAction.ASK_QUESTIONS,
                data={"questions": questions}
            )

        elif llm_action in ("create-document", "update-document"):
            # LLM created/updated document - show preview and ask for feedback
            return WorkflowResponse(
                action=WorkflowAction.REQUEST_FEEDBACK,
                data={
                    "content": content,
                    "action_type": llm_action,
                    "feedback_phase": self.feedback_phase.value
                }
            )

        elif llm_action == "complete":
            # Workflow complete
            message = parsed_response.get("message", "Workflow complete!")
            return WorkflowResponse(
                action=WorkflowAction.EXIT_WORKFLOW,
                data={"message": message}
            )

        else:
            # Unknown action
            return WorkflowResponse(
                action=WorkflowAction.SHOW_ERROR,
                data={
                    "error_message": f"Unknown action: {llm_action}",
                    "parsed_response": parsed_response
                }
            )

    def _should_trigger_decomposition(self) -> bool:
        """Check if feature decomposition should be triggered.

        Returns:
            True if decomposition should run
        """
        return (
            self.document_type == "vision_document"
            and not self.decomposition_triggered
            and self.current_content is not None
            and "## Feature Breakdown" not in self.current_content
        )

    def _get_file_path(self) -> str:
        """Get file path for current document.

        Returns:
            File path string
        """
        if self.current_action_params:
            file_name = self.current_action_params.get("file-name", "document.md")
        else:
            file_name = "document.md"

        return f"reckie-docs/{file_name}"

    def _build_feedback_prompt(self, feedback: str) -> str:
        """Build feedback prompt with document context.

        Args:
            feedback: User's feedback

        Returns:
            Formatted prompt for LLM
        """
        if self.feedback_phase == FeedbackPhase.POST_DECOMPOSITION:
            # Post-decomposition: refinement only
            return f"""Current document version (with Feature Breakdown):

```markdown
{self.current_content}
```

User feedback: {feedback}

Please revise the document based on this feedback. You can modify any section including the Feature Breakdown table, but do NOT re-run feature decomposition. Return the updated version using update-document action."""

        else:
            # Pre-decomposition: normal refinement
            return f"""Current document version:

```markdown
{self.current_content}
```

User feedback: {feedback}

Please revise the document based on this feedback and return the updated version using update-document action."""

    def _has_escaped_newlines(self, content: str) -> bool:
        """Check if content has escaped newlines instead of actual newlines.

        Args:
            content: Document content to check

        Returns:
            True if content has \n escape sequences
        """
        # Check for literal \n strings (escaped newlines)
        # These appear when JSON content field has string "\\n" instead of actual newlines
        if "\\n" in content:
            return True

        # Check if content is mostly on one line with \n visible
        lines = content.split("\n")
        if len(lines) <= 3 and len(content) > 200:
            # Long content but only 1-3 lines = likely has \n instead of newlines
            return True

        return False

    def _request_markdown_reformatting(self, malformed_content: str) -> WorkflowResponse:
        """Request LLM to reformat content as proper markdown.

        Args:
            malformed_content: Content with escaped newlines

        Returns:
            WorkflowResponse to trigger reformatting
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Detected escaped newlines in content - requesting reformatting")

        # Send request to reformat
        reformat_prompt = f"""The previous response contained escaped newlines (\\n) instead of proper line breaks.

Please reformat the following content as proper markdown with actual line breaks:

{malformed_content[:500]}...

Return the FULL document content with proper markdown formatting, using the same action format (update-document or create-document).

IMPORTANT: Use actual line breaks in your JSON response, not \\n escape sequences."""

        # Send reformatting request
        logger.info("Sending reformatting request to LLM")
        response = self.chain.predict(input=reformat_prompt)
        parsed = self._parse_llm_response(response)

        if parsed:
            # Extract reformatted content
            llm_action = parsed.get("action")
            content = parsed.get("content", "")
            action_params = parsed.get("action-params", {})

            # Store state
            self.current_action = llm_action
            self.current_content = content
            self.current_action_params = action_params

            # Return UI action
            return self._determine_ui_action(parsed)
        else:
            # Failed to reformat
            return WorkflowResponse(
                action=WorkflowAction.SHOW_ERROR,
                data={
                    "error_message": "Failed to reformat document",
                    "raw_response": response[:2000]
                }
            )

    def _build_feature_decomposition_prompt(self, vision_content: str) -> str:
        """Build feature decomposition system prompt.

        Args:
            vision_content: Vision document content

        Returns:
            System prompt for decomposition
        """
        return f"""You are an expert product manager performing feature decomposition from a vision document.

## Current Vision Document:

{vision_content}

## Your Task:

Analyze the vision document and decompose it into 10-15 high-level features. Add a "Feature Breakdown" section at the END of the document with a table containing:

- **Feature ID**: Format F01, F02, F03, etc.
- **Feature Name**: Clear, concise name (2-5 words)
- **Description**: 5-10 bullet points explaining:
  - What the feature does
  - Why it's needed
  - Key capabilities
  - User benefits
- **Release**: MVP (for initial release) or R01, R02, R03 (for future releases)

## Output Format:

You MUST respond with JSON wrapped in a code block. Use \\n for newlines in the content field:

```json
{{
  "action": "update-document",
  "action-params": {{
    "file-name": "vision.md"
  }},
  "content": "Full vision document with Feature Breakdown table appended.\\nUse \\\\n for line breaks."
}}
```

CRITICAL: Ensure the JSON is valid by properly escaping quotes and newlines in the content field.

## Feature Breakdown Table Format:

```markdown
## Feature Breakdown

| Feature ID | Feature Name | Description | Release |
|------------|--------------|-------------|---------|
| F01 | User Authentication | • Secure login/logout functionality<br>• Password reset capability<br>• Multi-factor authentication<br>• Session management<br>• OAuth integration | MVP |
| F02 | Dashboard | • Real-time metrics display<br>• Customizable widgets<br>• Data visualization<br>• Export capabilities | MVP |
| F03 | Reporting Engine | • Custom report builder<br>• Scheduled reports<br>• PDF/Excel export<br>• Email distribution | R01 |
```

**IMPORTANT**:
- Append the Feature Breakdown section to the EXISTING vision document content
- Do NOT remove or modify existing sections
- Include ALL 10-15 features in the table
- Use `<br>` tags for bullet points in the Description column
- Classify each feature as MVP or future release (R01, R02, etc.)
"""
