#!/usr/bin/env python3
"""
Reckie CLI - Tech Spike for LLM Interaction

Interactive CLI with persistent prompt, status line, action handlers, and PostgreSQL conversation state.
"""

import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from langchain_core.messages import SystemMessage, HumanMessage

from src.services.conversation_chain_service import ConversationChainService

# Configure logging (INFO only, no DEBUG)
LOG_FILE = "reckie-cli.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE)
    ]
)
logger = logging.getLogger(__name__)

# Rich console for colorful output
console = Console()

# Load configuration
CONFIG_FILE = "reckie-cli-config.json"


def load_config():
    """Load configuration from JSON file."""
    if not Path(CONFIG_FILE).exists():
        console.print(f"[red]❌ Config file not found: {CONFIG_FILE}[/red]")
        sys.exit(1)

    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def build_system_prompt(doc_type_config: dict) -> str:
    """
    Build system prompt from document type configuration.

    Combines base prompt, workflow instructions, and action definitions.
    """
    parts = []

    # Base system prompt
    base_prompt = doc_type_config.get("base_system_prompt", "")
    if base_prompt:
        parts.append(base_prompt)

    # Workflow instructions
    instructions = doc_type_config.get("workflow_instructions", [])
    if instructions:
        parts.append("\n## Workflow Instructions:")
        for instruction in instructions:
            parts.append(instruction)

    # Available actions
    actions = doc_type_config.get("available_actions", {})
    if actions:
        parts.append("\n## Available Actions:")
        for action_name, action_def in actions.items():
            when_to_use = action_def.get("when_to_use", "")
            format_example = json.dumps(action_def.get("format", {}), indent=2)
            notes = action_def.get("notes", "")

            parts.append(f"\n### Action: {action_name}")
            parts.append(f"**When to use**: {when_to_use}")
            parts.append(f"**Response format**:\n```json\n{format_example}\n```")
            if notes:
                parts.append(f"**Notes**: {notes}")

    # Final reminder with STRONG markdown formatting requirements
    parts.append("\n## CRITICAL REQUIREMENTS")
    parts.append("- You MUST respond with valid JSON only")
    parts.append("- Choose the appropriate action based on user input")
    parts.append("- Follow the exact format specified for each action")
    parts.append("\n## MARKDOWN FORMATTING - ABSOLUTELY CRITICAL")
    parts.append("- **NEVER** use escaped newlines (\\n) in the content field")
    parts.append("- **ALWAYS** use actual line breaks in your JSON content")
    parts.append("- The content field MUST contain properly formatted markdown with real newlines")
    parts.append("- **DO NOT** write content as a single line with \\n escape sequences")
    parts.append("- Format markdown with proper spacing: blank lines between sections, proper heading hierarchy")
    parts.append("- Example of CORRECT formatting:")
    parts.append('  ```json\n  {\n    "action": "create-document",\n    "content": "# Heading\\n\\nParagraph text.\\n\\n## Section\\n\\nMore content."\n  }\n  ```')
    parts.append("- If you return improperly formatted markdown, you will be asked to reformat it")

    return "\n".join(parts)


def create_document_handler(action_params: dict, content: str, config: dict, save_now: bool = False) -> str:
    """
    Handle create-document action.

    Creates a new markdown file with the given content.

    Args:
        action_params: Action parameters including file-name
        content: Document content
        config: CLI configuration
        save_now: If True, save immediately; if False, just prepare (for review loop)

    Returns:
        File path where document will be/was saved
    """
    file_name = action_params.get("file-name", "document.md")

    # Get output directory from config
    output_dir = Path(config.get("output_directory", "reckie-docs"))

    # Create directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Full path to file
    file_path = output_dir / file_name

    if save_now:
        logger.info(f"Creating document: {file_path}")
        console.print(f"\n[green]📄 Creating document: {file_name}[/green]")

        # Write content to file
        try:
            file_path.write_text(content)
            logger.info(f"Document created successfully: {file_path}")
            console.print(f"[green]✅ Document created: {file_path.absolute()}[/green]\n")
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            console.print(f"[red]❌ Error creating document: {e}[/red]\n")

    return str(file_path)


def update_document_handler(action_params: dict, content: str, config: dict, save_now: bool = False) -> str:
    """Handle update-document action.

    Args:
        action_params: Action parameters including file-name
        content: Document content
        config: CLI configuration
        save_now: If True, save immediately; if False, just prepare (for review loop)

    Returns:
        File path where document will be/was saved
    """
    file_name = action_params.get("file-name", "document.md")
    output_dir = Path(config.get("output_directory", "reckie-docs"))
    file_path = output_dir / file_name

    if save_now:
        logger.info(f"Updating document: {file_path}")
        console.print(f"\n[yellow]📝 Updating document: {file_name}[/yellow]")

        try:
            file_path.write_text(content)
            logger.info(f"Document updated successfully: {file_path}")
            console.print(f"[green]✅ Document updated: {file_path.absolute()}[/green]\n")
        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            console.print(f"[red]❌ Error updating document: {e}[/red]\n")

    return str(file_path)


def question_handler(questions: list) -> dict:
    """
    Handle question action - collect answers from user.

    Args:
        questions: List of questions to ask

    Returns:
        Dict mapping question_id to answer
    """
    logger.info(f"Asking {len(questions)} questions")
    console.print(f"\n[cyan]📋 Please answer the following questions:[/cyan]\n")

    answers = {}

    for idx, question in enumerate(questions, 1):
        question_id = question.get("question_id", f"q{idx}")
        question_text = question.get("question_text", "")
        question_type = question.get("type", "text")
        required = question.get("required", True)
        skip_allowed = question.get("skip_allowed", True)

        console.print(f"[bold cyan]Question {idx}/{len(questions)}:[/bold cyan] {question_text}")

        if question_type == "choice":
            options = question.get("options", [])
            for opt_idx, option in enumerate(options, 1):
                console.print(f"  {opt_idx}. {option}")

            if skip_allowed:
                console.print("  [dim](or type 'skip' to skip)[/dim]")

            answer = Prompt.ask(f"\n[cyan]>[/cyan] Your answer", console=console)

            if answer.lower() == "skip" and skip_allowed:
                logger.info(f"Question {question_id} skipped")
                console.print("[dim]Skipped[/dim]\n")
                continue

            # Validate choice
            try:
                choice_idx = int(answer) - 1
                if 0 <= choice_idx < len(options):
                    answers[question_id] = options[choice_idx]
                else:
                    console.print("[red]Invalid choice. Skipping question.[/red]\n")
                    continue
            except ValueError:
                answers[question_id] = answer  # Allow free text

        else:  # text type
            if skip_allowed:
                console.print("  [dim](or type 'skip' to skip)[/dim]")

            answer = Prompt.ask(f"\n[cyan]>[/cyan] Your answer", console=console)

            if answer.lower() == "skip" and skip_allowed:
                logger.info(f"Question {question_id} skipped")
                console.print("[dim]Skipped[/dim]\n")
                continue

            if not answer.strip() and required:
                console.print("[yellow]This question is required. Please provide an answer.[/yellow]")
                answer = Prompt.ask(f"[cyan]>[/cyan] Your answer", console=console)

            answers[question_id] = answer

        logger.info(f"Question {question_id} answered: {answer[:50]}...")
        console.print()

    return answers


def complete_handler(message: str, config: dict) -> None:  # noqa: ARG001
    """Handle complete action - workflow finished."""
    logger.info("Workflow completed")
    console.print(f"\n[green bold]✅ {message}[/green bold]\n")


def build_feature_decomposition_prompt(vision_content: str) -> str:
    """
    Build system prompt for feature decomposition from vision document.

    Args:
        vision_content: Full markdown content of the vision document

    Returns:
        System prompt for feature decomposition
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


ACTION_HANDLERS = {
    "create-document": create_document_handler,
    "update-document": update_document_handler,
    "question": question_handler,
    "complete": complete_handler,
}


def has_escaped_newlines(content: str) -> bool:
    """Check if content has escaped newlines instead of actual newlines.

    Args:
        content: Document content to check

    Returns:
        True if content has \\n escape sequences
    """
    # Check for literal \\n strings (escaped newlines)
    if "\\n" in content:
        return True

    # Check if content is mostly on one line with \\n visible
    lines = content.split("\n")
    if len(lines) <= 3 and len(content) > 200:
        # Long content but only 1-3 lines = likely has \\n instead of newlines
        return True

    return False


def validate_and_fix_markdown(
    chain,
    conversation_id: UUID,
    content: str,
    action: str,
    max_attempts: int = 3
) -> str:
    """Validate markdown and auto-reformat if needed (with retry limit).

    Args:
        chain: LangChain RunnableWithMessageHistory
        conversation_id: Conversation UUID for session config
        content: Content to validate
        action: Action type (create-document, update-document)
        max_attempts: Maximum reformatting attempts

    Returns:
        Properly formatted markdown content
    """
    attempt = 0
    current_content = content

    while attempt < max_attempts:
        if not has_escaped_newlines(current_content):
            # Content is properly formatted
            return current_content

        attempt += 1
        logger.warning(f"Detected escaped newlines in content - attempting reformat (attempt {attempt}/{max_attempts})")
        console.print(f"\n[yellow]⚠️  Detected formatting issues. Requesting proper markdown formatting (attempt {attempt}/{max_attempts})...[/yellow]\n")

        # Send reformatting request
        reformat_prompt = f"""The previous response contained escaped newlines (\\n) instead of proper line breaks.

CRITICAL: You MUST return properly formatted markdown with ACTUAL line breaks, not \\n escape sequences.

Please reformat the following content as proper markdown:

{current_content[:500]}...

Return the FULL document content with proper markdown formatting, using the same action format ({action}).

IMPORTANT:
- Use actual line breaks in your JSON response, NOT \\n escape sequences
- The content field must have real newlines, not the literal string "\\n"
- Format as readable markdown with proper spacing"""

        try:
            # Use invoke with session config for RunnableWithMessageHistory
            config = {"configurable": {"session_id": str(conversation_id)}}
            response_msg = chain.invoke({"input": reformat_prompt}, config=config)

            # Extract string content from AIMessage
            response = response_msg.content if hasattr(response_msg, 'content') else str(response_msg)
            parsed = parse_llm_response(response)

            if parsed and parsed.get("content"):
                current_content = parsed.get("content", "")
            else:
                logger.error("Failed to parse reformatted response")
                break

        except Exception as e:
            logger.error(f"Error during reformatting: {e}")
            break

    if attempt >= max_attempts:
        logger.error(f"Failed to properly format markdown after {max_attempts} attempts")
        console.print(f"\n[red]❌ Could not properly format markdown after {max_attempts} attempts. Showing content as-is.[/red]\n")

    return current_content


def parse_llm_response(response_text: str) -> Optional[dict]:
    """
    Parse LLM response as JSON.

    Extracts JSON from code blocks if present.
    """
    logger.info("Parsing LLM response")

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
        parsed = json.loads(json_text)
        logger.info(f"Parsed JSON action: {parsed.get('action', 'unknown')}")
        return parsed
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.debug(f"Failed JSON text (first 500 chars): {json_text[:500]}")

        # Try to fix common JSON issues
        # Issue 1: Content with unescaped newlines
        try:
            # Try to find and parse just the outer structure
            if json_text.startswith("{") and '"action"' in json_text:
                # Extract action and other metadata manually
                import re
                action_match = re.search(r'"action"\s*:\s*"([^"]+)"', json_text)
                if action_match:
                    logger.info(f"Extracted action from malformed JSON: {action_match.group(1)}")

                    # For update-document, try to extract content between quotes
                    if "update-document" in json_text or "create-document" in json_text:
                        content_match = re.search(
                            r'"content"\s*:\s*"(.*)"(?:\s*\}|\s*,)',
                            json_text,
                            re.DOTALL
                        )
                        if content_match:
                            # Found content, but it's likely truncated
                            logger.warning("JSON parsing failed but found partial content")

        except Exception as fallback_error:
            logger.error(f"Fallback parsing also failed: {fallback_error}")

        return None


def execute_action(
    response_data: dict,
    config: dict,
    save_document: bool = False
) -> tuple[bool, Optional[dict], Optional[str]]:
    """
    Execute action based on LLM response.

    Args:
        response_data: Parsed LLM response
        config: CLI configuration
        save_document: If True, save document immediately; if False, prepare for review

    Returns:
        Tuple of (continue_workflow, question_answers, document_file_path)
    """
    action = response_data.get("action")

    if not action:
        logger.warning("No action found in response")
        console.print("[yellow]⚠️  No action specified in response[/yellow]")
        return (True, None, None)

    if action == "question":
        # Handle questions
        questions = response_data.get("questions", [])
        if not questions:
            logger.warning("Question action has no questions")
            console.print("[yellow]⚠️  No questions provided[/yellow]")
            return (True, None, None)

        answers = question_handler(questions)
        return (True, answers, None)  # Continue workflow with answers

    elif action == "create-document":
        action_params = response_data.get("action-params", {})
        content = response_data.get("content", "")
        file_path = create_document_handler(action_params, content, config, save_now=save_document)
        return (True, None, file_path)

    elif action == "update-document":
        action_params = response_data.get("action-params", {})
        content = response_data.get("content", "")
        file_path = update_document_handler(action_params, content, config, save_now=save_document)
        return (True, None, file_path)

    elif action == "complete":
        message = response_data.get("message", "Workflow complete!")
        complete_handler(message, config)
        return (False, None, None)  # End workflow

    else:
        logger.warning(f"Unknown action: {action}")
        console.print(f"[yellow]⚠️  Unknown action: {action}[/yellow]")
        return (True, None, None)




def show_main_menu() -> str:
    """Show main menu and return selected action."""
    console.print("\n[bold cyan]What would you like to do?[/bold cyan]")
    console.print("  [cyan]1[/cyan]. Create document")
    console.print("  [cyan]2[/cyan]. Exit")

    choice = Prompt.ask("\n[cyan]>[/cyan] Select option", choices=["1", "2"])

    if choice == "1":
        return "create-document"
    else:  # choice == "2"
        return "exit"




def select_document_type(config: dict) -> tuple[str, dict]:
    """
    Show document type menu and return selected type with its config.

    Returns:
        Tuple of (type_key, type_config)
    """
    doc_types = config.get("document_types", {})

    console.print("\n[bold cyan]Select document type:[/bold cyan]")

    # Build menu
    type_keys = list(doc_types.keys())
    for idx, type_key in enumerate(type_keys, 1):
        display_name = doc_types[type_key].get("display_name", type_key.replace("_", " ").title())
        console.print(f"  [cyan]{idx}[/cyan]. {display_name}")

    # Get choice
    max_choice = len(type_keys)
    choices = [str(i) for i in range(1, max_choice + 1)]
    choice = Prompt.ask(
        f"\n[cyan]>[/cyan] Select document type",
        choices=choices
    )

    # Return selected type
    selected_key = type_keys[int(choice) - 1]
    selected_config = doc_types[selected_key]

    logger.info(f"Selected document type: {selected_key}")
    return selected_key, selected_config


@click.command()
@click.option(
    "--model",
    default="gpt-4o",
    help="OpenAI model to use (default: gpt-4o)",
)
@click.option(
    "--db-url",
    default=None,
    help="PostgreSQL database URL (defaults to DATABASE_URL env var)",
)
def chat(model: str, db_url: Optional[str]):
    """
    Interactive CLI for LLM chat with action handling and PostgreSQL state.

    Features:
    - Persistent > prompt
    - Colorful status line
    - Action handlers (create-document, question, update-document, complete)
    - JSON response parsing
    - PostgreSQL conversation history via LangChain
    """
    logger.info("=" * 80)
    logger.info("🚀 Reckie CLI Started")
    logger.info(f"Model: {model}")
    logger.info("=" * 80)

    # Load config
    config = load_config()

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print("[red]❌ OPENAI_API_KEY environment variable not set[/red]")
        logger.error("OPENAI_API_KEY not found")
        sys.exit(1)

    logger.info("✅ OPENAI_API_KEY found")

    # Check database URL
    if db_url is None:
        db_url = os.getenv("DATABASE_URL")

    if not db_url:
        console.print("[yellow]⚠️  DATABASE_URL not set - conversations will not persist across restarts[/yellow]")
        logger.warning("DATABASE_URL not found - no persistence")

    # Welcome message
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]Reckie CLI[/bold cyan]\n"
        f"Model: [yellow]{model}[/yellow]\n"
        f"State: [{'green]PostgreSQL Persistence' if db_url else 'yellow]In-Memory Only'}[/]\n"
        f"Type your prompts below. Press Ctrl+C to exit.",
        border_style="cyan"
    ))
    console.print()

    # Main interaction loop
    while True:
        try:
            # Show main menu
            action = show_main_menu()

            if action == "exit":
                console.print("\n[yellow]👋 Goodbye![/yellow]")
                logger.info("User selected exit")
                break

            # Create new conversation session
            conversation_id = uuid4()

            # TODO: Get from auth/login system - using real user UUID for now
            # This should be the logged-in user's actual UUID
            user_id = UUID("2974bf21-34e3-4857-a86a-c6a6636875fc")

            # TODO: Get from document creation flow - using real document UUID for now
            # This should be the document being edited
            document_id = UUID("081b5e3c-d37e-4e26-92e7-52da464be5ef")

            logger.info(f"New conversation session: {conversation_id}")
            logger.info(f"User ID: {user_id}, Document ID: {document_id}")

            # Handle create-document action
            if action == "create-document":
                # Select document type
                doc_type_key, doc_type_config = select_document_type(config)

                # Build system prompt from config
                system_prompt = build_system_prompt(doc_type_config)
                logger.info(f"System prompt built ({len(system_prompt)} chars)")

                # Show initial message
                initial_msg = doc_type_config.get("initial_message", "")
                if initial_msg:
                    console.print(f"\n[cyan]💬 {initial_msg}[/cyan]\n")
                    logger.info(f"Initial message: {initial_msg}")

                # Get user input
                user_prompt = Prompt.ask("[cyan]>[/cyan]", console=console)

                if not user_prompt.strip():
                    continue

                # Initialize conversation service with PostgreSQL
                conv_service = ConversationChainService(
                    model=model,
                    temperature=0.7
                )

                # Create conversation chain with system prompt
                chain = conv_service.create_chain(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    document_id=document_id,
                    connection_string=db_url,
                    system_prompt=system_prompt
                )

                # Workflow loop
                workflow_active = True
                current_input = user_prompt

                while workflow_active:
                    # Show status while processing
                    with console.status(
                        f"[bold blue]⏳ Waiting for response from {model}...[/bold blue]",
                        spinner="dots"
                    ):
                        logger.info(f"Sending to LLM: {current_input[:100]}...")

                        start_time = datetime.now()
                        try:
                            # Use invoke with session config for RunnableWithMessageHistory
                            config = {"configurable": {"session_id": str(conversation_id)}}
                            response_msg = chain.invoke({"input": current_input}, config=config)

                            # Extract string content from AIMessage
                            response = response_msg.content if hasattr(response_msg, 'content') else str(response_msg)
                            duration = (datetime.now() - start_time).total_seconds()
                        except Exception as llm_error:
                            duration = (datetime.now() - start_time).total_seconds()
                            logger.error(f"LLM error after {duration:.2f}s: {llm_error}")

                            # Show user-friendly error
                            console.print(f"\n[red]❌ LLM Error: {str(llm_error)}[/red]")
                            console.print("[yellow]This is usually a temporary API issue. Your conversation history is saved.[/yellow]")
                            console.print(f"[dim]Conversation ID: {conversation_id}[/dim]\n")

                            # Exit workflow but don't crash
                            workflow_active = False
                            break

                    logger.info(f"Response time: {duration:.2f}s")

                    # Parse response
                    response_data = parse_llm_response(response)

                    if response_data:
                        # Get content and action
                        content = response_data.get("content", "")
                        action = response_data.get("action", "")

                        # Validate and fix markdown formatting BEFORE displaying
                        if content and action in ("create-document", "update-document"):
                            content = validate_and_fix_markdown(chain, conversation_id, content, action, max_attempts=3)
                            # Update response_data with validated content
                            response_data["content"] = content

                        # Display validated markdown content
                        if content:
                            console.print()
                            console.print(Panel(
                                Markdown(content),
                                title="[bold green]Document Preview[/bold green]",
                                border_style="green"
                            ))
                            console.print()

                        # Execute action (don't save yet - wait for user approval)
                        continue_workflow, question_answers, document_path = execute_action(
                            response_data, config, save_document=False
                        )

                        if not continue_workflow:
                            workflow_active = False
                            break

                        # If questions were answered, send answers back to LLM
                        if question_answers:
                            # Format answers as user message
                            answer_text = "\n".join([
                                f"{q_id}: {answer}"
                                for q_id, answer in question_answers.items()
                            ])
                            current_input = f"Here are my answers:\n{answer_text}\n\nPlease update the document with this information."
                            logger.info(f"Sending answers back to LLM")
                        # If document was created/updated, ask for user feedback
                        elif action in ("create-document", "update-document") and content:
                            console.print("[cyan]📋 Initial version of the document has been created based on your input.[/cyan]\n")
                            console.print("[bold cyan]What would you like to do?[/bold cyan]")
                            console.print("  [green]1[/green]. Accept this version (save and exit)")
                            console.print("  [yellow]2[/yellow]. Provide feedback for improvements")
                            console.print()

                            user_choice = Prompt.ask(
                                "[cyan]>[/cyan] Your choice",
                                choices=["1", "2"],
                                console=console
                            )

                            if user_choice == "1":
                                # Accept - save document
                                logger.info("User accepted document version")

                                # Now actually save the document
                                execute_action(response_data, config, save_document=True)

                                console.print("\n[green]✅ Document accepted and saved![/green]\n")

                                # For vision documents, trigger feature decomposition
                                if doc_type_key == "vision_document" and "## Feature Breakdown" not in content:
                                    console.print("[cyan]🔍 Starting feature decomposition from vision document...[/cyan]\n")
                                    logger.info("Triggering feature decomposition")

                                    # Build feature decomposition prompt
                                    decomposition_prompt = build_feature_decomposition_prompt(content)

                                    # Send decomposition request to LLM
                                    current_input = "Please analyze the vision document and create a Feature Breakdown table with 10-15 features."

                                    # Clear chat history and recreate chain with decomposition prompt
                                    chat_history = conv_service.get_chat_history(conversation_id)
                                    chat_history.clear()

                                    # Recreate chain with decomposition system prompt
                                    chain = conv_service.create_chain(
                                        conversation_id=conversation_id,
                                        user_id=user_id,
                                        document_id=document_id,
                                        connection_string=db_url,
                                        system_prompt=decomposition_prompt
                                    )

                                    # Continue workflow for decomposition
                                    logger.info("Feature decomposition initiated")
                                    console.print("[dim]Analyzing vision and identifying features...[/dim]\n")
                                else:
                                    # Not a vision doc or already has features - exit
                                    workflow_active = False
                            else:
                                # Provide feedback - continue loop
                                logger.info("User wants to provide feedback")
                                feedback = Prompt.ask(
                                    "\n[cyan]💬 Please provide your feedback[/cyan]\n[cyan]>[/cyan]",
                                    console=console
                                )

                                # Check if this is post-decomposition feedback
                                has_features = "## Feature Breakdown" in content

                                if has_features:
                                    # Post-decomposition: refinement only
                                    current_input = f"""Current document version (with Feature Breakdown):

```markdown
{content}
```

User feedback: {feedback}

Please revise the document based on this feedback. You can modify any section including the Feature Breakdown table, but do NOT re-run feature decomposition. Return the updated version using update-document action."""
                                else:
                                    # Pre-decomposition: normal refinement
                                    current_input = f"""Current document version:

```markdown
{content}
```

User feedback: {feedback}

Please revise the document based on this feedback and return the updated version using update-document action."""

                                logger.info(f"Sending feedback to LLM (has_features={has_features}): {feedback[:100]}...")
                        else:
                            # No more actions, exit workflow
                            workflow_active = False
                    else:
                        # Failed to parse JSON - show error and raw response
                        logger.warning(f"Could not parse LLM response as JSON. Response length: {len(response)}")
                        console.print("\n[yellow]⚠️  Could not parse LLM response as valid JSON[/yellow]")
                        console.print("[dim]This usually means the LLM returned malformed JSON or very large content.[/dim]\n")

                        # Show first 2000 chars of response for debugging
                        preview = response[:2000] + "..." if len(response) > 2000 else response
                        console.print(Panel(
                            preview,
                            title="[yellow]Raw Response (preview)[/yellow]",
                            border_style="yellow"
                        ))

                        console.print("\n[cyan]Options:[/cyan]")
                        console.print("  1. Try providing more specific feedback")
                        console.print("  2. Check reckie-cli.log for full response")
                        console.print("  3. Exit and review document manually\n")

                        # Ask user what to do
                        choice = Prompt.ask(
                            "[cyan]>[/cyan] What would you like to do?",
                            choices=["1", "2", "3"],
                            console=console
                        )

                        if choice == "1":
                            # Let user provide more feedback
                            feedback = Prompt.ask(
                                "\n[cyan]💬 Provide more specific feedback[/cyan]\n[cyan]>[/cyan]",
                                console=console
                            )
                            current_input = f"Previous attempt had formatting issues. {feedback}"
                            logger.info(f"User providing feedback after JSON parse error: {feedback[:100]}")
                        elif choice == "2":
                            console.print(f"\n[dim]Check {LOG_FILE} for full response[/dim]\n")
                            workflow_active = False
                        else:
                            workflow_active = False

                # Show status bar
                console.print(
                    f"[dim blue]Model: {model} | Conversation: {conversation_id} | Log: {LOG_FILE}[/dim blue]"
                )
                console.print()

        except KeyboardInterrupt:
            console.print("\n\n[yellow]👋 Goodbye![/yellow]")
            logger.info("User exited (Ctrl+C)")
            break

        except Exception as e:
            console.print(f"\n[red]❌ Error: {e}[/red]\n")
            logger.error(f"Error in main loop: {e}", exc_info=True)

    logger.info("✅ Reckie CLI completed")
    logger.info("=" * 80)


if __name__ == "__main__":
    chat()
