"""
Editor Command Center Tests - T004
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# 确保测试目录可访问
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app

@pytest.fixture
def client():
    return TestClient(app)

class TestEditorAPI:
    """测试编辑相关API接口"""

    def test_get_pipeline(self, client):
        """T001: 测试获取稿件流转状态"""
        response = client.get("/api/v1/editor/test/pipeline")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        assert "pending_quality" in data["data"]
        assert "under_review" in data["data"]
        assert "pending_decision" in data["data"]
        assert "published" in data["data"]

    def test_get_available_reviewers(self, client):
        """T002: 测试获取可用审稿人专家池"""
        response = client.get("/api/v1/editor/test/available-reviewers")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        assert len(data["data"]) > 0

    def test_submit_accept_decision(self, client):
        """T003: 测试提交录用决策"""
        test_manuscript_id = "123e4567-e89b-12d3-a456-426614174000"
        response = client.post(
            "/api/v1/editor/test/decision",
            json={
                "manuscript_id": test_manuscript_id,
                "decision": "accept",
                "comment": "Excellent work!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["decision"] == "accept"
        assert data["data"]["status"] == "published"

    def test_submit_reject_decision(self, client):
        """T003: 测试提交退回决策"""
        test_manuscript_id = "123e4567-e89b-12d3-a456-426614174000"
        response = client.post(
            "/api/v1/editor/test/decision",
            json={
                "manuscript_id": test_manuscript_id,
                "decision": "reject",
                "comment": "Needs more research"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["decision"] == "reject"
        assert data["data"]["status"] == "rejected"

    def test_invalid_decision_type(self, client):
        """T003: 测试无效决策类型"""
        test_manuscript_id = "123e4567-e89b-12d3-a456-426614174000"
        response = client.post(
            "/api/v1/editor/test/decision",
            json={
                "manuscript_id": test_manuscript_id,
                "decision": "invalid",
                "comment": "Some comment"
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
