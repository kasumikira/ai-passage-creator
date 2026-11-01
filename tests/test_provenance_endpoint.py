import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.deps import require_login
from app.exceptions import BusinessException
from app.routers.provenance import router
from app.routers.article import router as article_router
from app.schemas.user import LoginUserVO


class FakeDatabase:
    async def fetch_one(self, query, values=None):
        if not isinstance(query, str):
            return {"userId": 1}
        if "FROM article WHERE" in query:
            return {"userId": 1} if values["taskId"] == "task-1" else None
        if "FROM material_snapshot" in query:
            if values["taskId"] == "task-1" and values["snapshotId"] == 3:
                return {"id": 3, "sourceType": "product_profile", "sourceRef": "product_profile:7",
                        "versionTag": "abc123", "contentHash": "abc123", "contentText": "original",
                        "summary": "Product", "createTime": "2026-11-01T00:00:00"}
        return None

    async def fetch_all(self, query, values):
        return [{"id": 1, "eventType": "MATERIAL", "snapshotId": 3,
                 "toolName": None, "arguments": None, "status": "PROVIDED",
                 "resultSummary": "Product", "errorMessage": None, "sourceRefs": None,
                 "durationMs": None, "createTime": "2026-11-01T00:00:00",
                 "sourceType": "product_profile", "sourceRef": "product_profile:7",
                 "versionTag": "abc123", "contentHash": "abc123", "summary": "Product"}]


def user(user_id, role="user"):
    return LoginUserVO(id=user_id, userAccount="test", userName="Test", userRole=role,
                       createTime="2026-11-01T00:00:00", updateTime="2026-11-01T00:00:00")


class ProvenanceEndpointTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        app.include_router(article_router)
        app.dependency_overrides[get_db] = lambda: FakeDatabase()
        app.dependency_overrides[require_login] = lambda: user(1)

        @app.exception_handler(BusinessException)
        async def business_error(request, error):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=403, content={"code": error.error_code.code})

        self.app = app
        self.client = TestClient(app)

    def test_owner_can_read_trace_and_archived_material(self):
        trace = self.client.get("/article/task-1/trace")
        self.assertEqual(trace.status_code, 200)
        self.assertEqual(trace.json()["data"][0]["versionTag"], "abc123")
        material = self.client.get("/article/task-1/materials/3")
        self.assertEqual(material.json()["data"]["contentText"], "original")

    def test_other_user_cannot_read_trace_or_material(self):
        self.app.dependency_overrides[require_login] = lambda: user(2)
        self.assertEqual(self.client.get("/article/task-1/trace").status_code, 403)
        self.assertEqual(self.client.get("/article/task-1/materials/3").status_code, 403)

    def test_existing_execution_log_route_also_checks_owner(self):
        self.app.dependency_overrides[require_login] = lambda: user(2)
        response = self.client.get("/article/execution-logs/task-1")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_read_another_users_trace(self):
        self.app.dependency_overrides[require_login] = lambda: user(2, "admin")
        response = self.client.get("/article/task-1/trace")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["snapshotId"], 3)
