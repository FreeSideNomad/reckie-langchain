"""Unit tests for ConversationMetric model."""

import uuid

from src.database.models.conversation_metric import ConversationMetric


class TestConversationMetric:
    """Test suite for ConversationMetric model."""

    def test_create_metric(self):
        """Test creating a conversation metric."""
        conversation_id = uuid.uuid4()
        correlation_id = uuid.uuid4()

        metric = ConversationMetric(
            conversation_id=conversation_id,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model="gpt-4-turbo",
            correlation_id=correlation_id,
            duration_ms=1500,
            error_occurred=False,
        )

        assert metric.conversation_id == conversation_id
        assert metric.prompt_tokens == 100
        assert metric.completion_tokens == 50
        assert metric.total_tokens == 150
        assert metric.model == "gpt-4-turbo"
        assert metric.correlation_id == correlation_id
        assert metric.duration_ms == 1500
        assert metric.error_occurred is False
        assert metric.error_message is None

    def test_create_metric_with_error(self):
        """Test creating a metric with error details."""
        conversation_id = uuid.uuid4()

        metric = ConversationMetric(
            conversation_id=conversation_id,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            model="gpt-4-turbo",
            error_occurred=True,
            error_message="Rate limit exceeded",
        )

        assert metric.error_occurred is True
        assert metric.error_message == "Rate limit exceeded"
        assert metric.has_error is True

    def test_has_error_property(self):
        """Test has_error property."""
        metric = ConversationMetric(
            conversation_id=uuid.uuid4(),
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model="gpt-4-turbo",
            error_occurred=False,
        )

        assert metric.has_error is False

        metric.error_occurred = True
        assert metric.has_error is True

    def test_to_dict(self):
        """Test to_dict conversion."""
        conversation_id = uuid.uuid4()
        correlation_id = uuid.uuid4()

        metric = ConversationMetric(
            conversation_id=conversation_id,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model="gpt-4-turbo",
            correlation_id=correlation_id,
            duration_ms=1500,
            error_occurred=False,
        )

        metric_dict = metric.to_dict()

        assert metric_dict["conversation_id"] == str(conversation_id)
        assert metric_dict["prompt_tokens"] == 100
        assert metric_dict["completion_tokens"] == 50
        assert metric_dict["total_tokens"] == 150
        assert metric_dict["model"] == "gpt-4-turbo"
        assert metric_dict["correlation_id"] == str(correlation_id)
        assert metric_dict["duration_ms"] == 1500
        assert metric_dict["error_occurred"] is False

    def test_repr(self):
        """Test string representation."""
        conversation_id = uuid.uuid4()

        metric = ConversationMetric(
            conversation_id=conversation_id,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model="gpt-4-turbo",
        )

        repr_str = repr(metric)

        assert "ConversationMetric" in repr_str
        assert str(conversation_id) in repr_str
        assert "gpt-4-turbo" in repr_str
        assert "150" in repr_str
