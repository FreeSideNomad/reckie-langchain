"""Integration tests for markdown validation in DocumentWorkflowService."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.services.document_workflow_service import (
    DocumentWorkflowService,
    WorkflowAction,
)


class TestMarkdownValidation:
    """Test markdown validation and reformatting."""

    @patch("src.services.document_workflow_service.ConversationChainService")
    def test_has_escaped_newlines_detects_literal_backslash_n(
        self, mock_conv_service_class
    ):
        """Test detection of literal \\n in content."""
        service = self._create_service(mock_conv_service_class)

        # Content with literal \n
        malformed_content = "Vision Document\\n\\n## Introduction\\nThis is content"

        assert service._has_escaped_newlines(malformed_content) is True

    @patch("src.services.document_workflow_service.ConversationChainService")
    def test_has_escaped_newlines_detects_single_line_long_content(
        self, mock_conv_service_class
    ):
        """Test detection of long content on single line."""
        service = self._create_service(mock_conv_service_class)

        # Long content with only 2 lines (should have more breaks)
        malformed_content = "Line 1\n" + ("x" * 300)

        assert service._has_escaped_newlines(malformed_content) is True

    @patch("src.services.document_workflow_service.ConversationChainService")
    def test_has_escaped_newlines_accepts_proper_markdown(
        self, mock_conv_service_class
    ):
        """Test proper markdown passes validation."""
        service = self._create_service(mock_conv_service_class)

        # Proper markdown with actual newlines
        proper_content = """# Vision Document

## Introduction

This is a proper markdown document with actual line breaks.

## Features

- Feature 1
- Feature 2
"""

        assert service._has_escaped_newlines(proper_content) is False

    @patch("src.services.document_workflow_service.ConversationChainService")
    def test_send_user_input_triggers_reformatting_on_escaped_newlines(
        self, mock_conv_service_class
    ):
        """Test that send_user_input triggers reformatting when escapes detected."""
        # Setup service with mocked conversation service
        service = self._create_service(mock_conv_service_class)

        # Mock the chain
        mock_chain = Mock()
        service.chain = mock_chain

        # First response: malformed with escaped newlines
        malformed_response = """{
  "action": "create-document",
  "content": "Vision Document\\\\n\\\\n## Introduction\\\\nThis is content",
  "action-params": {"file-name": "vision.md"}
}"""

        # Second response: properly formatted
        reformatted_response = """{
  "action": "create-document",
  "content": "# Vision Document\\n\\n## Introduction\\n\\nThis is properly formatted content.",
  "action-params": {"file-name": "vision.md"}
}"""

        # Mock chain.predict to return responses in sequence
        mock_chain.predict.side_effect = [malformed_response, reformatted_response]

        # Send user input
        response = service.send_user_input("Create a vision document")

        # Verify reformatting was triggered (predict called twice)
        assert mock_chain.predict.call_count == 2

        # Verify the first call was the original request
        first_call_input = mock_chain.predict.call_args_list[0][1]["input"]
        assert "Create a vision document" in first_call_input

        # Verify the second call was the reformatting request
        second_call_input = mock_chain.predict.call_args_list[1][1]["input"]
        assert "escaped newlines" in second_call_input
        assert "proper markdown" in second_call_input

        # Verify final response has action REQUEST_FEEDBACK
        assert response.action == WorkflowAction.REQUEST_FEEDBACK
        assert response.document_content is not None

    @patch("src.services.document_workflow_service.ConversationChainService")
    def test_send_user_input_skips_reformatting_for_proper_markdown(
        self, mock_conv_service_class
    ):
        """Test that properly formatted markdown doesn't trigger reformatting."""
        # Setup service with mocked conversation service
        service = self._create_service(mock_conv_service_class)

        # Mock the chain
        mock_chain = Mock()
        service.chain = mock_chain

        # Proper response with actual newlines
        proper_response = """{
  "action": "create-document",
  "content": "# Vision Document\\n\\n## Introduction\\n\\nThis is properly formatted.",
  "action-params": {"file-name": "vision.md"}
}"""

        mock_chain.predict.return_value = proper_response

        # Send user input
        response = service.send_user_input("Create a vision document")

        # Verify reformatting was NOT triggered (predict called only once)
        assert mock_chain.predict.call_count == 1

        # Verify response is valid
        assert response.action == WorkflowAction.REQUEST_FEEDBACK
        assert response.document_content is not None

    @patch("src.services.document_workflow_service.ConversationChainService")
    def test_request_markdown_reformatting_includes_context(
        self, mock_conv_service_class
    ):
        """Test that reformatting request includes helpful context."""
        service = self._create_service(mock_conv_service_class)

        # Mock the chain
        service.chain = Mock()
        reformatted_response = """{
  "action": "update-document",
  "content": "# Proper\\n\\nMarkdown",
  "action-params": {"file-name": "test.md"}
}"""
        service.chain.predict.return_value = reformatted_response

        malformed_content = "Test\\\\nContent\\\\n"

        response = service._request_markdown_reformatting(malformed_content)

        # Verify the prompt includes key phrases
        call_args = service.chain.predict.call_args
        prompt = call_args[1]["input"]

        assert "escaped newlines" in prompt
        assert "proper markdown" in prompt
        assert "actual line breaks" in prompt
        assert "IMPORTANT" in prompt

    # Helper methods

    def _create_service(
        self, mock_conv_service_class
    ) -> DocumentWorkflowService:
        """Create a DocumentWorkflowService instance with mocked dependencies."""
        # Mock conversation service
        mock_conv_service = Mock()
        mock_chain = Mock()
        mock_memory = Mock()
        mock_chat_memory = Mock()

        mock_chain.memory = mock_memory
        mock_memory.chat_memory = mock_chat_memory
        mock_conv_service.create_chain.return_value = mock_chain
        mock_conv_service_class.return_value = mock_conv_service

        return DocumentWorkflowService(
            conversation_id=uuid4(),
            user_id=uuid4(),
            document_id=uuid4(),
            document_type="vision_document",
            system_prompt="Test system prompt",
            model="gpt-4o",
            db_url=None  # No database needed for these tests
        )
