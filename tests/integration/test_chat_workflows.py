"""Chat workflow test suite with 30 test cases.

Tests conversational AI workflows across multiple scenarios:
- Business Context workflows (10 tests)
- Vision document workflows (7 tests)
- Testing Strategy workflows (6 tests)
- Multi-turn refinement (4 tests)
- Error handling (3 tests)

All tests use mock chat (USE_MOCK_ADAPTERS=true) to avoid API costs.
Fixtures stored in tests/fixtures/mock_adapters/chat.yaml
"""

import os

import pytest

from src.api.dependencies import get_chat_provider


@pytest.fixture
def chat():
    """Get chat provider (mock mode)."""
    # Ensure we're using mocks
    os.environ["USE_MOCK_ADAPTERS"] = "true"
    return get_chat_provider()


# Category 1: Business Context Workflows (10 tests)


def test_business_context_rich_info_turn1(chat):
    """Business Context - Rich info: Initial user input with 5 sentences."""
    messages = [
        {
            "role": "user",
            "content": (
                "I'm working on a commercial banking platform for RBC. "
                "The system handles payment origination..."
            ),
        }
    ]
    response = chat.invoke(messages)
    assert response is not None
    assert hasattr(response, "content")


def test_business_context_rich_info_turn2(chat):
    """Business Context - Rich info: Follow-up question about challenges."""
    messages = [
        {"role": "user", "content": "I'm working on a commercial banking platform..."},
        {"role": "assistant", "content": "Thank you for providing that context..."},
        {"role": "user", "content": "The main challenge is the complex approval workflows..."},
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_business_context_rich_info_turn3(chat):
    """Business Context - Rich info: User approval."""
    messages = [
        {"role": "user", "content": "I'm working on a commercial banking platform..."},
        {"role": "assistant", "content": "Thank you..."},
        {"role": "user", "content": "The main challenge is..."},
        {"role": "assistant", "content": "I understand..."},
        {"role": "user", "content": "looks good"},
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_business_context_sparse_info_turn1(chat):
    """Business Context - Sparse info: Minimal 2-sentence input."""
    messages = [
        {"role": "user", "content": "We're building a banking app. It's for business users."}
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_business_context_sparse_info_turn2(chat):
    """Business Context - Sparse info: Follow-up with partial details."""
    messages = [
        {"role": "user", "content": "We're building a banking app..."},
        {"role": "assistant", "content": "I'd like to ask some questions..."},
        {"role": "user", "content": "It handles payments and reporting. Canadian market."},
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_business_context_sparse_info_turn3(chat):
    """Business Context - Sparse info: More details provided."""
    messages = [
        {"role": "user", "content": "We're building a banking app..."},
        {"role": "assistant", "content": "Questions..."},
        {"role": "user", "content": "Payments and reporting..."},
        {"role": "assistant", "content": "More questions..."},
        {
            "role": "user",
            "content": "Wire transfers, ACH, international. About 500 corporate clients.",
        },
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_business_context_domain_knowledge_turn1(chat):
    """Business Context - Domain knowledge: Construction lending terminology."""
    messages = [
        {
            "role": "user",
            "content": (
                "Commercial lending platform for construction loans. " "Focus on draw schedules..."
            ),
        }
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_business_context_domain_knowledge_turn2(chat):
    """Business Context - Domain knowledge: Compliance requirements."""
    messages = [
        {"role": "user", "content": "Commercial lending platform..."},
        {"role": "assistant", "content": "Domain questions..."},
        {
            "role": "user",
            "content": "Progress payments based on inspection reports. FDIC and state regulations.",
        },
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_business_context_domain_knowledge_approval(chat):
    """Business Context - Domain knowledge: User approval."""
    messages = [
        {"role": "user", "content": "Commercial lending..."},
        {"role": "assistant", "content": "Questions..."},
        {"role": "user", "content": "Progress payments..."},
        {"role": "assistant", "content": "Draft..."},
        {"role": "user", "content": "perfect"},
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_business_context_iterative_refinement(chat):
    """Business Context - Iterative refinement through multiple turns."""
    messages = [
        {"role": "user", "content": "E-commerce platform for B2B sales"},
        {"role": "assistant", "content": "Questions..."},
        {"role": "user", "content": "Focus on bulk ordering and quote management"},
        {"role": "assistant", "content": "More questions..."},
        {"role": "user", "content": "Integration with ERP systems required"},
        {"role": "assistant", "content": "Draft..."},
        {"role": "user", "content": "add section on API integrations"},
        {"role": "assistant", "content": "Updated..."},
        {"role": "user", "content": "approve"},
    ]
    response = chat.invoke(messages)
    assert response is not None


# Category 2: Vision Document Workflows (7 tests)


def test_vision_feature_decomposition_turn1(chat):
    """Vision - Feature decomposition: Initial vision description."""
    messages = [
        {"role": "user", "content": "Build a document management system with AI assistance..."}
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_vision_feature_decomposition_turn2(chat):
    """Vision - Feature decomposition: Persona details."""
    messages = [
        {"role": "user", "content": "Build a document management system..."},
        {"role": "assistant", "content": "Questions..."},
        {
            "role": "user",
            "content": "Multiple personas: Business Analyst, Product Owner, QA Lead...",
        },
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_vision_feature_decomposition_turn3(chat):
    """Vision - Feature decomposition: RAG and hierarchy details."""
    messages = [
        {"role": "user", "content": "Build a document management system..."},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "Multiple personas..."},
        {"role": "assistant", "content": "..."},
        {
            "role": "user",
            "content": "Uses RAG for parent context. Vision → Features → Epics → User Stories.",
        },
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_vision_feature_decomposition_combine_features(chat):
    """Vision - Feature decomposition: User requests to combine features."""
    messages = [
        {"role": "user", "content": "Build a document management system..."},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "Draft with 10 features..."},
        {"role": "user", "content": "Combine feature 3 and 4 into one feature"},
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_vision_no_parent_context_turn1(chat):
    """Vision - No parent context: User starts without Business Context."""
    messages = [{"role": "user", "content": "Create a vision for a payment system"}]
    response = chat.invoke(messages)
    assert response is not None


def test_vision_no_parent_context_proceed(chat):
    """Vision - No parent context: User insists on proceeding."""
    messages = [
        {"role": "user", "content": "Create a vision for a payment system"},
        {"role": "assistant", "content": "Do you have a Business Context?"},
        {"role": "user", "content": "no, start from scratch"},
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_vision_no_parent_context_details(chat):
    """Vision - No parent context: User provides details."""
    messages = [
        {"role": "user", "content": "Create a vision..."},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "no, start from scratch"},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "Real-time payment processing for small businesses..."},
    ]
    response = chat.invoke(messages)
    assert response is not None


# Category 3: Testing Strategy Workflows (6 tests)


def test_testing_strategy_with_research_turn1(chat):
    """Testing Strategy - With research: Initial request."""
    messages = [
        {"role": "user", "content": "Create a testing strategy for the document management system"}
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_testing_strategy_with_research_confirm(chat):
    """Testing Strategy - With research: User confirms research request."""
    messages = [
        {"role": "user", "content": "Create a testing strategy..."},
        {"role": "assistant", "content": "Should I research best practices?"},
        {"role": "user", "content": "yes, research testing pyramid, CI/CD, coverage targets"},
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_testing_strategy_with_research_tech_stack(chat):
    """Testing Strategy - With research: Tech stack details."""
    messages = [
        {"role": "user", "content": "Create a testing strategy..."},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "yes, research..."},
        {"role": "assistant", "content": "Research summary..."},
        {
            "role": "user",
            "content": "Python stack: pytest, GitHub Actions, PostgreSQL with Testcontainers...",
        },
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_testing_strategy_no_research_turn1(chat):
    """Testing Strategy - No research: Experienced user skips research."""
    messages = [
        {"role": "user", "content": "Testing strategy - I don't need research, ask me questions"}
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_testing_strategy_no_research_tech_details(chat):
    """Testing Strategy - No research: Tech stack provided."""
    messages = [
        {"role": "user", "content": "Testing strategy - no research..."},
        {"role": "assistant", "content": "Questions..."},
        {"role": "user", "content": "FastAPI backend, React frontend. API contract testing..."},
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_testing_strategy_no_research_risk_areas(chat):
    """Testing Strategy - No research: High-risk areas identified."""
    messages = [
        {"role": "user", "content": "Testing strategy - no research..."},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "FastAPI backend..."},
        {"role": "assistant", "content": "..."},
        {
            "role": "user",
            "content": "High-risk: payment processing, approval workflows, encryption",
        },
    ]
    response = chat.invoke(messages)
    assert response is not None


# Category 4: Multi-Turn Refinement (4 tests)


def test_feature_refinement_add_oauth(chat):
    """Feature refinement: Add OAuth support."""
    messages = [
        {"role": "user", "content": "Create feature document for user authentication"},
        {"role": "assistant", "content": "Questions..."},
        {"role": "user", "content": "OAuth2 with Google, Microsoft, GitHub"},
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_feature_refinement_add_mfa(chat):
    """Feature refinement: Add MFA requirement."""
    messages = [
        {"role": "user", "content": "Create feature for user authentication"},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "OAuth2..."},
        {"role": "assistant", "content": "Draft..."},
        {"role": "user", "content": "add MFA support"},
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_feature_refinement_epic_breakdown(chat):
    """Feature refinement: Request epic breakdown."""
    messages = [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "Updated with MFA..."},
        {"role": "user", "content": "needs epic breakdown"},
    ]
    response = chat.invoke(messages)
    assert response is not None


def test_feature_refinement_combine_epics(chat):
    """Feature refinement: Combine epics."""
    messages = [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "Epics: OAuth, MFA, SSO, Password..."},
        {"role": "user", "content": "combine OAuth and SSO into one epic"},
    ]
    response = chat.invoke(messages)
    assert response is not None


# Category 5: Edge Cases & Error Handling (3 tests)


def test_edge_case_user_confusion(chat):
    """Edge case: User doesn't know what they want."""
    messages = [{"role": "user", "content": "start"}]
    response = chat.invoke(messages)
    assert response is not None


def test_edge_case_off_topic_then_pivot(chat):
    """Edge case: User goes off-topic then pivots."""
    messages = [{"role": "user", "content": "Create a vision for a space exploration startup"}]
    response = chat.invoke(messages)
    assert response is not None


def test_edge_case_context_switch(chat):
    """Edge case: User changes mind mid-workflow."""
    messages = [
        {"role": "user", "content": "Create Business Context for e-commerce platform"},
        {"role": "assistant", "content": "Questions..."},
        {"role": "user", "content": "actually, I want to do a Vision document instead"},
    ]
    response = chat.invoke(messages)
    assert response is not None
