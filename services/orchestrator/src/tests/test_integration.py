"""
Integration Tests for Alice v2 Orchestrator
Tests API endpoints with Guardian integration
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def mock_guardian_healthy():
    """Mock Guardian in healthy state"""
    return {
        "state": "NORMAL",
        "available": True,
        "ram_pct": 45.0,
        "cpu_pct": 25.0,
        "uptime_s": 3600,
    }


@pytest.fixture
def mock_guardian_overloaded():
    """Mock Guardian in overloaded state"""
    return {
        "state": "EMERGENCY",
        "available": False,
        "ram_pct": 95.0,
        "cpu_pct": 85.0,
        "uptime_s": 7200,
    }


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_root_endpoint(self, client):
        """Test root endpoint returns service info"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "Alice v2 Orchestrator"
        assert data["version"] == "1.0.0"
        assert "docs" in data
        assert "health" in data

    @patch("src.services.guardian_client.GuardianClient.get_health")
    def test_health_endpoint_healthy(
        self, mock_get_health, client, mock_guardian_healthy
    ):
        """Test health endpoint when Guardian is healthy"""
        mock_get_health.return_value = mock_guardian_healthy

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "orchestrator"
        assert data["dependencies"]["guardian"] == "NORMAL"

    @patch("src.services.guardian_client.GuardianClient.get_health")
    def test_health_endpoint_guardian_error(self, mock_get_health, client):
        """Test health endpoint when Guardian is unreachable"""
        mock_get_health.side_effect = Exception("Connection failed")

        response = client.get("/health")
        assert response.status_code == 503


class TestChatAPI:
    """Test chat completion API"""

    @patch("src.services.guardian_client.GuardianClient.check_admission")
    @patch("src.services.guardian_client.GuardianClient.get_health")
    @patch("src.services.guardian_client.GuardianClient.get_recommended_model")
    def test_chat_success(
        self,
        mock_get_model,
        mock_get_health,
        mock_check_admission,
        client,
        mock_guardian_healthy,
    ):
        """Test successful chat request"""
        mock_check_admission.return_value = True
        mock_get_health.return_value = mock_guardian_healthy
        mock_get_model.return_value = "micro"

        request_data = {
            "v": "1",
            "session_id": "test_session",
            "message": "Hej Alice!",
            "model": "auto",
        }

        response = client.post("/api/chat", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["v"] == "1"
        assert data["session_id"] == "test_session"
        assert "response" in data
        assert data["model_used"] == "micro"
        assert data["latency_ms"] > 0
        assert "trace_id" in data

    @patch("src.services.guardian_client.GuardianClient.check_admission")
    def test_chat_blocked_by_guardian(self, mock_check_admission, client):
        """Test chat request blocked by Guardian"""
        mock_check_admission.return_value = False

        request_data = {
            "v": "1",
            "session_id": "test_session",
            "message": "Test message",
        }

        response = client.post("/api/chat", json=request_data)
        assert response.status_code == 503

        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "SERVICE_OVERLOADED"

    def test_chat_invalid_request(self, client):
        """Test chat with invalid request format"""
        request_data = {
            "message": "Test",
            # Missing required fields
        }

        response = client.post("/api/chat", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_chat_empty_message(self, client):
        """Test chat with empty message"""
        request_data = {
            "v": "1",
            "session_id": "test_session",
            "message": "",  # Empty message
        }

        response = client.post("/api/chat", json=request_data)
        assert response.status_code == 422  # Validation error


class TestOrchestratorAPI:
    """Test orchestrator ingestion API"""

    @patch("src.services.guardian_client.GuardianClient.check_admission")
    @patch("src.services.guardian_client.GuardianClient.get_health")
    def test_ingest_success(
        self, mock_get_health, mock_check_admission, client, mock_guardian_healthy
    ):
        """Test successful ingestion request"""
        mock_check_admission.return_value = True
        mock_get_health.return_value = mock_guardian_healthy

        request_data = {
            "v": "1",
            "session_id": "test_session",
            "text": "Kan du hjälpa mig med något?",
            "lang": "sv",
        }

        response = client.post("/api/orchestrator/ingest", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["v"] == "1"
        assert data["session_id"] == "test_session"
        assert data["accepted"] == True
        assert data["model"] == "micro"  # Phase 1: always micro
        assert 1 <= data["priority"] <= 10
        assert data["estimated_latency_ms"] > 0

    @patch("src.services.guardian_client.GuardianClient.check_admission")
    @patch("src.services.guardian_client.GuardianClient.get_health")
    def test_ingest_blocked_by_guardian(
        self, mock_get_health, mock_check_admission, client, mock_guardian_overloaded
    ):
        """Test ingestion blocked by Guardian"""
        mock_check_admission.return_value = False
        mock_get_health.return_value = mock_guardian_overloaded

        request_data = {"v": "1", "session_id": "test_session", "text": "Test text"}

        response = client.post("/api/orchestrator/ingest", json=request_data)
        assert response.status_code == 503

    def test_ingest_invalid_version(self, client):
        """Test ingestion with invalid API version"""
        request_data = {
            "v": "2",  # Invalid version
            "session_id": "test_session",
            "text": "Test text",
        }

        response = client.post("/api/orchestrator/ingest", json=request_data)
        assert response.status_code == 422


class TestAPIVersioning:
    """Test API versioning and contract stability"""

    @patch("src.services.guardian_client.GuardianClient.check_admission")
    @patch("src.services.guardian_client.GuardianClient.get_health")
    def test_api_version_consistency(
        self, mock_get_health, mock_check_admission, client, mock_guardian_healthy
    ):
        """Test that all responses include consistent API version"""
        mock_check_admission.return_value = True
        mock_get_health.return_value = mock_guardian_healthy

        # Test chat endpoint
        chat_request = {"v": "1", "session_id": "test", "message": "Test"}

        response = client.post("/api/chat", json=chat_request)
        assert response.status_code == 200
        assert response.json()["v"] == "1"

        # Test ingest endpoint
        ingest_request = {"v": "1", "session_id": "test", "text": "Test"}

        response = client.post("/api/orchestrator/ingest", json=ingest_request)
        assert response.status_code == 200
        assert response.json()["v"] == "1"

    def test_trace_id_propagation(self, client):
        """Test that trace IDs are included in responses"""
        response = client.get("/health")
        assert response.status_code in [200, 503]  # Either healthy or unhealthy
        assert "X-Trace-ID" in response.headers


class TestErrorHandling:
    """Test error handling and response formats"""

    def test_404_endpoint(self, client):
        """Test non-existent endpoint returns 404"""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test wrong HTTP method returns 405"""
        response = client.get("/api/chat")  # Should be POST
        assert response.status_code == 405

    @patch("src.services.guardian_client.GuardianClient.check_admission")
    def test_internal_error_handling(self, mock_check_admission, client):
        """Test internal error handling"""
        mock_check_admission.side_effect = Exception("Unexpected error")

        request_data = {
            "v": "1",
            "session_id": "test_session",
            "message": "Test message",
        }

        response = client.post("/api/chat", json=request_data)
        assert response.status_code == 500

        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "INTERNAL_ERROR"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
