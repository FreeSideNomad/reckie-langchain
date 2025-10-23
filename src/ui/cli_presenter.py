"""CLI presentation layer.

Handles all user interaction and display logic.
Consumes responses from DocumentWorkflowService.
"""

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from src.services.document_workflow_service import WorkflowAction, WorkflowResponse


class CLIPresenter:
    """Handles CLI presentation and user interaction.

    Responsibilities:
    - Display document previews
    - Show questions and collect answers
    - Request feedback from user
    - Display errors
    - Save files to disk
    """

    def __init__(self, console: Optional[Console] = None, output_dir: str = "reckie-docs"):
        """Initialize CLI presenter.

        Args:
            console: Rich console instance
            output_dir: Directory for saving documents
        """
        self.console = console or Console()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def handle_response(self, response: WorkflowResponse) -> Optional[dict]:
        """Handle workflow response and interact with user.

        Args:
            response: WorkflowResponse from service

        Returns:
            Dict with user input/decision, or None if no input needed
        """
        if response.action == WorkflowAction.SHOW_DOCUMENT_PREVIEW:
            return self._show_document_preview(response)

        elif response.action == WorkflowAction.ASK_QUESTIONS:
            return self._ask_questions(response)

        elif response.action == WorkflowAction.REQUEST_FEEDBACK:
            return self._request_feedback(response)

        elif response.action == WorkflowAction.SAVE_DOCUMENT:
            return self._save_document(response)

        elif response.action == WorkflowAction.SHOW_ERROR:
            return self._show_error(response)

        elif response.action == WorkflowAction.EXIT_WORKFLOW:
            return self._exit_workflow(response)

        else:
            self.console.print(f"[red]Unknown action: {response.action}[/red]")
            return None

    def _show_document_preview(self, response: WorkflowResponse) -> None:
        """Display document preview.

        Args:
            response: WorkflowResponse with document content
        """
        content = response.document_content

        if content:
            self.console.print()
            self.console.print(Panel(
                Markdown(content),
                title="[bold green]Document Preview[/bold green]",
                border_style="green"
            ))
            self.console.print()

    def _ask_questions(self, response: WorkflowResponse) -> dict:
        """Ask questions and collect answers.

        Args:
            response: WorkflowResponse with questions

        Returns:
            Dict of question_id -> answer
        """
        questions = response.questions or []

        self.console.print(f"\n[cyan]📋 Please answer the following questions:[/cyan]\n")

        answers = {}

        for idx, question in enumerate(questions, 1):
            question_id = question.get("question_id", f"q{idx}")
            question_text = question.get("question_text", "")
            question_type = question.get("type", "text")
            required = question.get("required", True)
            skip_allowed = question.get("skip_allowed", True)

            self.console.print(f"[bold cyan]Question {idx}/{len(questions)}:[/bold cyan] {question_text}")

            if question_type == "choice":
                options = question.get("options", [])
                for opt_idx, option in enumerate(options, 1):
                    self.console.print(f"  {opt_idx}. {option}")

                if skip_allowed:
                    self.console.print("  [dim](or type 'skip' to skip)[/dim]")

                self.console.print("\n[cyan]>[/cyan] Your answer: ", end="")
                try:
                    answer = input().strip()  # Strip trailing whitespace
                except EOFError:
                    answer = ""

                if answer.lower() == "skip" and skip_allowed:
                    self.console.print("[dim]Skipped[/dim]\n")
                    continue

                # Validate choice
                try:
                    choice_idx = int(answer) - 1
                    if 0 <= choice_idx < len(options):
                        answers[question_id] = options[choice_idx]
                    else:
                        self.console.print("[red]Invalid choice. Skipping question.[/red]\n")
                        continue
                except ValueError:
                    answers[question_id] = answer  # Allow free text

            else:  # text type
                if skip_allowed:
                    self.console.print("  [dim](or type 'skip' to skip)[/dim]")

                self.console.print("\n[cyan]>[/cyan] Your answer: ", end="")
                try:
                    answer = input().strip()  # Strip trailing whitespace
                except EOFError:
                    answer = ""

                if answer.lower() == "skip" and skip_allowed:
                    self.console.print("[dim]Skipped[/dim]\n")
                    continue

                if not answer.strip() and required:
                    self.console.print("[yellow]This question is required. Please provide an answer.[/yellow]")
                    self.console.print("[cyan]>[/cyan] Your answer: ", end="")
                    try:
                        answer = input().strip()  # Strip trailing whitespace
                    except EOFError:
                        answer = ""

                answers[question_id] = answer

            self.console.print()

        return {"action": "answer_questions", "answers": answers}

    def _request_feedback(self, response: WorkflowResponse) -> dict:
        """Show document and request user feedback.

        Args:
            response: WorkflowResponse with document content

        Returns:
            Dict with user decision (accept or provide feedback)
        """
        # Show document preview
        content = response.document_content
        if content:
            self.console.print()
            self.console.print(Panel(
                Markdown(content),
                title="[bold green]Document Preview[/bold green]",
                border_style="green"
            ))
            self.console.print()

        # Ask user for decision
        self.console.print("[cyan]📋 Initial version of the document has been created based on your input.[/cyan]\n")
        self.console.print("[bold cyan]What would you like to do?[/bold cyan]")
        self.console.print("  [green]1[/green]. Accept this version (save and exit)")
        self.console.print("  [yellow]2[/yellow]. Provide feedback for improvements")
        self.console.print()

        user_choice = Prompt.ask(
            "[cyan]>[/cyan] Your choice",
            choices=["1", "2"],
            console=self.console
        )

        if user_choice == "1":
            # User accepted
            return {"action": "accept_document"}
        else:
            # User wants to provide feedback
            self.console.print("\n[cyan]💬 Please provide your feedback[/cyan]")
            self.console.print("[cyan]>[/cyan] ", end="")
            try:
                feedback = input().strip()  # Strip trailing whitespace
            except EOFError:
                feedback = ""
            return {"action": "provide_feedback", "feedback": feedback}

    def _save_document(self, response: WorkflowResponse) -> dict:
        """Save document to disk.

        Args:
            response: WorkflowResponse with file path and content

        Returns:
            Dict indicating success and whether to trigger decomposition
        """
        file_path = Path(response.file_path or "document.md")
        content = response.document_content

        if not content:
            self.console.print("[red]❌ No content to save[/red]")
            return {"action": "save_failed"}

        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            file_path.write_text(content)

            self.console.print(f"\n[green]✅ Document saved: {file_path.absolute()}[/green]\n")

            # Check if decomposition should be triggered
            trigger_decomposition = response.data.get("trigger_decomposition", False)

            if trigger_decomposition:
                self.console.print("[cyan]🔍 Starting feature decomposition from vision document...[/cyan]\n")
                self.console.print("[dim]Analyzing vision and identifying features...[/dim]\n")
                return {"action": "trigger_decomposition", "content": content}
            else:
                # Check if we should exit after save
                exit_after_save = response.metadata and response.metadata.get("exit_after_save", False)
                return {"action": "save_success", "exit": exit_after_save}

        except Exception as e:
            self.console.print(f"[red]❌ Error saving document: {e}[/red]")
            return {"action": "save_failed", "error": str(e)}

    def _show_error(self, response: WorkflowResponse) -> dict:
        """Display error message.

        Args:
            response: WorkflowResponse with error details

        Returns:
            Dict with recovery action
        """
        error_message = response.error_message or "Unknown error"
        raw_response = response.data.get("raw_response")

        self.console.print(f"\n[yellow]⚠️  {error_message}[/yellow]")
        self.console.print("[dim]This usually means the LLM returned malformed JSON or very large content.[/dim]\n")

        if raw_response:
            # Show preview of response
            preview = raw_response[:2000] + "..." if len(raw_response) > 2000 else raw_response
            self.console.print(Panel(
                preview,
                title="[yellow]Raw Response (preview)[/yellow]",
                border_style="yellow"
            ))

        self.console.print("\n[cyan]Options:[/cyan]")
        self.console.print("  1. Try providing more specific feedback")
        self.console.print("  2. Check reckie-cli.log for full response")
        self.console.print("  3. Exit and review document manually\n")

        choice = Prompt.ask(
            "[cyan]>[/cyan] What would you like to do?",
            choices=["1", "2", "3"],
            console=self.console
        )

        if choice == "1":
            self.console.print("\n[cyan]💬 Provide more specific feedback[/cyan]")
            self.console.print("[cyan]>[/cyan] ", end="")
            try:
                feedback = input().strip()  # Strip trailing whitespace
            except EOFError:
                feedback = ""
            return {"action": "retry_with_feedback", "feedback": feedback}
        elif choice == "2":
            self.console.print("\n[dim]Check reckie-cli.log for full response[/dim]\n")
            return {"action": "exit"}
        else:
            return {"action": "exit"}

    def _exit_workflow(self, response: WorkflowResponse) -> dict:
        """Display exit message.

        Args:
            response: WorkflowResponse with completion message

        Returns:
            Dict indicating workflow exit
        """
        message = response.data.get("message", "Workflow complete!")
        self.console.print(f"\n[green bold]✅ {message}[/green bold]\n")
        return {"action": "exit"}

    def show_initial_message(self, message: str) -> None:
        """Show initial workflow message.

        Args:
            message: Message to display
        """
        self.console.print(f"\n[cyan]💬 {message}[/cyan]\n")

    def get_initial_input(self) -> str:
        """Get initial user input with support for multiline paste.

        Returns:
            User's input text (trailing whitespace stripped)
        """
        try:
            # Use input() to support pasting with newlines
            self.console.print("[cyan]>[/cyan] ", end="")
            user_input = input()
            # Strip trailing whitespace (including newlines from paste)
            return user_input.strip()
        except EOFError:
            return ""

    def show_status(self, message: str) -> None:
        """Show status message.

        Args:
            message: Status message
        """
        self.console.print(f"[dim]{message}[/dim]")
