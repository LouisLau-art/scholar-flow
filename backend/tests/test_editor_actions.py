"""
Editor Command Center Security Tests
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

# 确保测试目录可访问
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestEditorAPI:
    """校验历史测试端点已从生产路由中移除。"""

    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/v1/editor/test/pipeline"),
            ("GET", "/api/v1/editor/test/available-reviewers"),
            ("POST", "/api/v1/editor/test/decision"),
        ],
    )
    def test_legacy_test_endpoints_removed(self, client: TestClient, method: str, path: str):
        response = client.request(method, path, json={"manuscript_id": "dummy", "decision": "accept"})
        assert response.status_code == 404
