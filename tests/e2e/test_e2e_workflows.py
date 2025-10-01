"""E2E workflow tests for critical user journeys.

Tests the most important end-to-end scenarios with full PostgreSQL + pgvector stack.
Following Testing Pyramid: ~10 E2E tests covering critical paths only.
"""

import time
import uuid

from src.database.models.document import Document
from src.database.models.document_type import DocumentType
from src.database.models.user import User


class TestE2EDocumentHierarchy:
    """E2E tests for document hierarchy workflows."""

    def test_e2e_create_document_hierarchy(self, api_client, test_db):
        """
        E2E: Create full hierarchy and verify all relationships.

        Critical path covering:
        - Document creation via API
        - Relationship creation
        - Breadcrumb generation
        - Parent context aggregation
        """
        # Setup: Create user and document types
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            username="testuser",
            password_hash="hash",
            role="user",
        )
        vision_type = DocumentType(
            type_name="vision_document",
            system_prompt="Vision prompt",
            workflow_steps=[],
            parent_types=[],
            allowed_personas=["user"],
            config={},
        )
        feature_type = DocumentType(
            type_name="feature_document",
            system_prompt="Feature prompt",
            workflow_steps=[],
            parent_types=["vision_document"],
            allowed_personas=["user"],
            config={},
        )
        test_db.add(user)
        test_db.add(vision_type)
        test_db.add(feature_type)
        test_db.commit()

        # Act: Create Vision via API
        vision_response = api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "vision_document",
                "title": "Product Vision 2024",
                "content_markdown": "Our vision is to revolutionize document management.",
            },
        )
        assert vision_response.status_code == 201
        vision_id = vision_response.json()["id"]

        # Act: Create Feature under Vision
        feature_response = api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "feature_document",
                "title": "User Authentication",
                "content_markdown": "This feature provides secure authentication.",
            },
        )
        assert feature_response.status_code == 201
        feature_id = feature_response.json()["id"]

        # Act: Create relationship via API
        rel_response = api_client.post(
            "/api/v1/relationships/",
            json={"parent_id": vision_id, "child_id": feature_id},
        )
        assert rel_response.status_code == 201

        # Assert: Verify breadcrumb via API
        breadcrumb_response = api_client.get(
            f"/api/v1/relationships/documents/{feature_id}/breadcrumb"
        )
        assert breadcrumb_response.status_code == 200
        breadcrumb_string = breadcrumb_response.json()["breadcrumb_string"]
        assert "Product Vision 2024" in breadcrumb_string
        assert "User Authentication" in breadcrumb_string

        # Assert: Verify parent context (for RAG)
        context_response = api_client.get(f"/api/v1/relationships/documents/{feature_id}/context")
        assert context_response.status_code == 200
        context = context_response.json()["context"]
        assert "revolutionize document management" in context

    def test_e2e_ripple_effect_propagation(self, api_client, test_db):
        """
        E2E: Update parent, verify descendants marked for review.

        Tests ripple effect: when parent changes, all descendants
        are automatically flagged for review.
        """
        # Setup: Create hierarchy
        user = User(
            id=uuid.uuid4(),
            email="test2@example.com",
            username="testuser2",
            password_hash="hash",
            role="user",
        )
        doc_type = DocumentType(
            type_name="test_type",
            system_prompt="Test",
            workflow_steps=[],
            parent_types=["test_type"],
            allowed_personas=["user"],
            config={},
        )
        test_db.add(user)
        test_db.add(doc_type)
        test_db.commit()

        # Create parent document
        parent_response = api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "test_type",
                "title": "Parent Document",
                "content_markdown": "Original content",
            },
        )
        parent_id = parent_response.json()["id"]

        # Create child document
        child_response = api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "test_type",
                "title": "Child Document",
                "content_markdown": "Child content",
            },
        )
        child_id = child_response.json()["id"]

        # Create relationship
        api_client.post(
            "/api/v1/relationships/",
            json={"parent_id": parent_id, "child_id": child_id},
        )

        # Act: Update parent document
        update_response = api_client.put(
            f"/api/v1/documents/{parent_id}",
            json={"content_markdown": "UPDATED content - major change!"},
        )
        assert update_response.status_code == 200

        # Act: Mark descendants for review
        mark_response = api_client.post(
            f"/api/v1/relationships/documents/{parent_id}/mark-descendants"
        )
        assert mark_response.status_code == 200

        # Assert: Child document should be marked
        child_doc = test_db.query(Document).filter(Document.id == uuid.UUID(child_id)).first()
        assert child_doc is not None
        assert child_doc.metadata.get("needs_review") is True

    def test_e2e_breadcrumb_navigation(self, api_client, test_db):
        """
        E2E: Deep hierarchy breadcrumb generation.

        Tests breadcrumb performance and correctness
        with deep document hierarchy (5 levels).
        """
        # Setup
        user = User(
            id=uuid.uuid4(),
            email="test3@example.com",
            username="testuser3",
            password_hash="hash",
            role="user",
        )
        doc_type = DocumentType(
            type_name="test_type",
            system_prompt="Test",
            workflow_steps=[],
            parent_types=["test_type"],
            allowed_personas=["user"],
            config={},
        )
        test_db.add(user)
        test_db.add(doc_type)
        test_db.commit()

        # Create 5-level hierarchy
        doc_ids = []
        for i in range(5):
            doc_response = api_client.post(
                "/api/v1/documents/",
                json={
                    "user_id": str(user.id),
                    "document_type": "test_type",
                    "title": f"Level {i+1} Document",
                    "content_markdown": f"Content at level {i+1}",
                },
            )
            doc_ids.append(doc_response.json()["id"])

            # Create relationship (except for first doc)
            if i > 0:
                api_client.post(
                    "/api/v1/relationships/",
                    json={"parent_id": doc_ids[i - 1], "child_id": doc_ids[i]},
                )

        # Act: Get breadcrumb for deepest document
        start_time = time.time()
        breadcrumb_response = api_client.get(
            f"/api/v1/relationships/documents/{doc_ids[-1]}/breadcrumb"
        )
        elapsed_ms = (time.time() - start_time) * 1000

        # Assert: Breadcrumb correct and performant
        assert breadcrumb_response.status_code == 200
        breadcrumb_string = breadcrumb_response.json()["breadcrumb_string"]
        assert "Level 1 Document" in breadcrumb_string
        assert "Level 5 Document" in breadcrumb_string
        assert elapsed_ms < 50, f"Breadcrumb took {elapsed_ms}ms, expected < 50ms"


class TestE2ERelationshipValidation:
    """E2E tests for relationship validation."""

    def test_e2e_relationship_validation(self, api_client, test_db):
        """
        E2E: Circular dependency prevention.

        Tests that API correctly prevents circular relationships.
        """
        # Setup
        user = User(
            id=uuid.uuid4(),
            email="test4@example.com",
            username="testuser4",
            password_hash="hash",
            role="user",
        )
        doc_type = DocumentType(
            type_name="test_type",
            system_prompt="Test",
            workflow_steps=[],
            parent_types=["test_type"],
            allowed_personas=["user"],
            config={},
        )
        test_db.add(user)
        test_db.add(doc_type)
        test_db.commit()

        # Create two documents
        doc1_response = api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "test_type",
                "title": "Document 1",
                "content_markdown": "Content 1",
            },
        )
        doc1_id = doc1_response.json()["id"]

        doc2_response = api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "test_type",
                "title": "Document 2",
                "content_markdown": "Content 2",
            },
        )
        doc2_id = doc2_response.json()["id"]

        # Act: Create relationship doc1 -> doc2
        rel1_response = api_client.post(
            "/api/v1/relationships/",
            json={"parent_id": doc1_id, "child_id": doc2_id},
        )
        assert rel1_response.status_code == 201

        # Act: Try to create circular relationship doc2 -> doc1
        rel2_response = api_client.post(
            "/api/v1/relationships/",
            json={"parent_id": doc2_id, "child_id": doc1_id},
        )

        # Assert: Circular relationship rejected
        assert rel2_response.status_code == 400
        assert "circular" in rel2_response.json()["detail"].lower()


class TestE2EPerformance:
    """E2E tests for performance baselines."""

    def test_e2e_parent_context_aggregation(self, api_client, test_db):
        """
        E2E: RAG context retrieval performance.

        Tests that parent context aggregation completes < 300ms.
        """
        # Setup
        user = User(
            id=uuid.uuid4(),
            email="test5@example.com",
            username="testuser5",
            password_hash="hash",
            role="user",
        )
        doc_type = DocumentType(
            type_name="test_type",
            system_prompt="Test",
            workflow_steps=[],
            parent_types=["test_type"],
            allowed_personas=["user"],
            config={},
        )
        test_db.add(user)
        test_db.add(doc_type)
        test_db.commit()

        # Create hierarchy with multiple parents
        doc_ids = []
        for i in range(3):
            doc_response = api_client.post(
                "/api/v1/documents/",
                json={
                    "user_id": str(user.id),
                    "document_type": "test_type",
                    "title": f"Document {i+1}",
                    "content_markdown": f"Content {i+1}: " + ("x" * 500),
                },
            )
            doc_ids.append(doc_response.json()["id"])

            if i > 0:
                api_client.post(
                    "/api/v1/relationships/",
                    json={"parent_id": doc_ids[i - 1], "child_id": doc_ids[i]},
                )

        # Act: Get parent context
        start_time = time.time()
        context_response = api_client.get(f"/api/v1/relationships/documents/{doc_ids[-1]}/context")
        elapsed_ms = (time.time() - start_time) * 1000

        # Assert: Context retrieved and performant
        assert context_response.status_code == 200
        context = context_response.json()["context"]
        assert "Content 1" in context
        assert "Content 2" in context
        assert elapsed_ms < 300, f"Context aggregation took {elapsed_ms}ms, expected < 300ms"

    def test_e2e_large_document_performance(self, api_client, test_db):
        """
        E2E: Performance baseline for large documents.

        Tests document creation with large content < 100ms.
        """
        # Setup
        user = User(
            id=uuid.uuid4(),
            email="test6@example.com",
            username="testuser6",
            password_hash="hash",
            role="user",
        )
        doc_type = DocumentType(
            type_name="test_type",
            system_prompt="Test",
            workflow_steps=[],
            parent_types=[],
            allowed_personas=["user"],
            config={},
        )
        test_db.add(user)
        test_db.add(doc_type)
        test_db.commit()

        # Act: Create large document (10KB)
        large_content = "# Large Document\n\n" + ("This is content. " * 500)
        start_time = time.time()
        response = api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "test_type",
                "title": "Large Document",
                "content_markdown": large_content,
            },
        )
        elapsed_ms = (time.time() - start_time) * 1000

        # Assert: Document created and performant
        assert response.status_code == 201
        assert elapsed_ms < 100, f"Document creation took {elapsed_ms}ms, expected < 100ms"


class TestE2ECascadeOperations:
    """E2E tests for cascade operations."""

    def test_e2e_cascade_delete(self, api_client, test_db):
        """
        E2E: Relationship deletion behavior.

        Tests that deleting a document handles relationships correctly.
        """
        # Setup
        user = User(
            id=uuid.uuid4(),
            email="test7@example.com",
            username="testuser7",
            password_hash="hash",
            role="user",
        )
        doc_type = DocumentType(
            type_name="test_type",
            system_prompt="Test",
            workflow_steps=[],
            parent_types=["test_type"],
            allowed_personas=["user"],
            config={},
        )
        test_db.add(user)
        test_db.add(doc_type)
        test_db.commit()

        # Create two documents with relationship
        doc1_response = api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "test_type",
                "title": "Parent Document",
                "content_markdown": "Parent content",
            },
        )
        doc1_id = doc1_response.json()["id"]

        doc2_response = api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "test_type",
                "title": "Child Document",
                "content_markdown": "Child content",
            },
        )
        doc2_id = doc2_response.json()["id"]

        rel_response = api_client.post(
            "/api/v1/relationships/",
            json={"parent_id": doc1_id, "child_id": doc2_id},
        )
        relationship_id = rel_response.json()["id"]

        # Act: Delete parent document
        delete_response = api_client.delete(f"/api/v1/documents/{doc1_id}")
        assert delete_response.status_code == 204

        # Assert: Child document still exists
        child_response = api_client.get(f"/api/v1/documents/{doc2_id}")
        assert child_response.status_code == 200

        # Assert: Relationship may be deleted (depends on cascade rules)
        # For now, just verify operation completed successfully
        rel_check = api_client.get(f"/api/v1/relationships/{relationship_id}")
        # Either 404 (deleted) or 200 (parent_id is null) is acceptable
        assert rel_check.status_code in [200, 404]


class TestE2ESearchAndFilters:
    """E2E tests for search and filtering."""

    def test_e2e_search_filters(self, api_client, test_db):
        """
        E2E: Document search with multiple filters.

        Tests search functionality with type, status, and user filters.
        """
        # Setup
        user = User(
            id=uuid.uuid4(),
            email="test8@example.com",
            username="testuser8",
            password_hash="hash",
            role="user",
        )
        doc_type1 = DocumentType(
            type_name="type1",
            system_prompt="Test",
            workflow_steps=[],
            parent_types=[],
            allowed_personas=["user"],
            config={},
        )
        doc_type2 = DocumentType(
            type_name="type2",
            system_prompt="Test",
            workflow_steps=[],
            parent_types=[],
            allowed_personas=["user"],
            config={},
        )
        test_db.add(user)
        test_db.add(doc_type1)
        test_db.add(doc_type2)
        test_db.commit()

        # Create multiple documents
        api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "type1",
                "title": "Doc 1",
                "content_markdown": "Content 1",
                "status": "draft",
            },
        )
        api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "type2",
                "title": "Doc 2",
                "content_markdown": "Content 2",
                "status": "published",
            },
        )
        api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "type1",
                "title": "Doc 3",
                "content_markdown": "Content 3",
                "status": "draft",
            },
        )

        # Act: Search with filters
        search_response = api_client.get("/api/v1/documents/?document_type=type1&status=draft")

        # Assert: Correct documents returned
        assert search_response.status_code == 200
        items = search_response.json()["items"]
        assert len(items) == 2
        assert all(doc["document_type"] == "type1" for doc in items)
        assert all(doc["status"] == "draft" for doc in items)


class TestE2EFullWorkflow:
    """E2E test for complete workflow."""

    def test_e2e_full_workflow(self, api_client, test_db):
        """
        E2E: Vision → Feature → Epic → Story full workflow.

        Tests complete document hierarchy creation and traversal.
        """
        # Setup: Create user and document types
        user = User(
            id=uuid.uuid4(),
            email="workflow@example.com",
            username="workflowuser",
            password_hash="hash",
            role="user",
        )
        vision_type = DocumentType(
            type_name="vision_document",
            system_prompt="Vision",
            workflow_steps=[],
            parent_types=[],
            allowed_personas=["user"],
            config={},
        )
        feature_type = DocumentType(
            type_name="feature_document",
            system_prompt="Feature",
            workflow_steps=[],
            parent_types=["vision_document"],
            allowed_personas=["user"],
            config={},
        )
        epic_type = DocumentType(
            type_name="epic_document",
            system_prompt="Epic",
            workflow_steps=[],
            parent_types=["feature_document"],
            allowed_personas=["user"],
            config={},
        )
        story_type = DocumentType(
            type_name="story_document",
            system_prompt="Story",
            workflow_steps=[],
            parent_types=["epic_document"],
            allowed_personas=["user"],
            config={},
        )
        test_db.add(user)
        test_db.add(vision_type)
        test_db.add(feature_type)
        test_db.add(epic_type)
        test_db.add(story_type)
        test_db.commit()

        # Act: Create Vision
        vision = api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "vision_document",
                "title": "Product Vision",
                "content_markdown": "Our product vision",
            },
        ).json()

        # Act: Create Feature
        feature = api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "feature_document",
                "title": "User Management",
                "content_markdown": "User management feature",
            },
        ).json()

        # Act: Create Epic
        epic = api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "epic_document",
                "title": "Authentication",
                "content_markdown": "Authentication epic",
            },
        ).json()

        # Act: Create Story
        story = api_client.post(
            "/api/v1/documents/",
            json={
                "user_id": str(user.id),
                "document_type": "story_document",
                "title": "Login Page",
                "content_markdown": "Login page story",
            },
        ).json()

        # Act: Create relationships
        api_client.post(
            "/api/v1/relationships/",
            json={"parent_id": vision["id"], "child_id": feature["id"]},
        )
        api_client.post(
            "/api/v1/relationships/",
            json={"parent_id": feature["id"], "child_id": epic["id"]},
        )
        api_client.post(
            "/api/v1/relationships/",
            json={"parent_id": epic["id"], "child_id": story["id"]},
        )

        # Assert: Verify full hierarchy traversal
        ancestors_response = api_client.get(
            f"/api/v1/relationships/documents/{story['id']}/ancestors"
        )
        assert ancestors_response.status_code == 200
        ancestors = ancestors_response.json()["ancestors"]
        assert len(ancestors) == 3  # Epic, Feature, Vision

        # Assert: Verify breadcrumb shows full path
        breadcrumb_response = api_client.get(
            f"/api/v1/relationships/documents/{story['id']}/breadcrumb"
        )
        assert breadcrumb_response.status_code == 200
        breadcrumb_string = breadcrumb_response.json()["breadcrumb_string"]
        assert "Product Vision" in breadcrumb_string
        assert "User Management" in breadcrumb_string
        assert "Authentication" in breadcrumb_string
        assert "Login Page" in breadcrumb_string

        # Assert: Verify descendants from Vision
        descendants_response = api_client.get(
            f"/api/v1/relationships/documents/{vision['id']}/descendants"
        )
        assert descendants_response.status_code == 200
        descendants = descendants_response.json()["descendants"]
        assert len(descendants) == 3  # Feature, Epic, Story
