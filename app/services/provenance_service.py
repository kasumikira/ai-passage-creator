"""Durable, content-addressed material versions and article provenance."""

import hashlib
import json
from datetime import datetime
from typing import Any

from databases import Database


class ProvenanceService:
    def __init__(self, db: Database):
        self.db = db

    async def record_material(
        self, *, task_id: str, source_type: str, source_ref: str, content: str, summary: str
    ) -> int:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        await self.db.execute(
            query="""
                INSERT INTO material_snapshot
                    (sourceType, sourceRef, versionTag, contentHash, contentText, summary)
                VALUES (:sourceType, :sourceRef, :versionTag, :contentHash, :contentText, :summary)
                ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)
            """,
            values={
                "sourceType": source_type,
                "sourceRef": source_ref,
                "versionTag": digest[:12],
                "contentHash": digest,
                "contentText": content,
                "summary": summary[:500],
            },
        )
        snapshot = await self.db.fetch_one(
            query="""
                SELECT id FROM material_snapshot
                WHERE sourceType = :sourceType AND sourceRef = :sourceRef AND contentHash = :contentHash
            """,
            values={"sourceType": source_type, "sourceRef": source_ref, "contentHash": digest},
        )
        if snapshot is None:
            raise RuntimeError("Material snapshot was not saved")
        snapshot_id = snapshot["id"]
        if source_type != "tool_output":
            await self.db.execute(
                query="""
                    INSERT INTO article_provenance_event
                        (taskId, eventType, snapshotId, status, resultSummary)
                    VALUES (:taskId, 'MATERIAL', :snapshotId, 'PROVIDED', :resultSummary)
                """,
                values={"taskId": task_id, "snapshotId": snapshot_id, "resultSummary": summary[:500]},
            )
        return snapshot_id

    async def record_tool_call(
        self, *, task_id: str, tool_name: str, arguments: dict[str, Any], status: str,
        result_summary: str, error_message: str | None, source_refs: list[str],
        snapshot_id: int | None, duration_ms: int,
    ) -> None:
        await self.db.execute(
            query="""
                INSERT INTO article_provenance_event
                    (taskId, eventType, snapshotId, toolName, arguments, status,
                     resultSummary, errorMessage, sourceRefs, durationMs)
                VALUES (:taskId, 'TOOL', :snapshotId, :toolName, :arguments, :status,
                        :resultSummary, :errorMessage, :sourceRefs, :durationMs)
            """,
            values={
                "taskId": task_id,
                "snapshotId": snapshot_id,
                "toolName": tool_name,
                "arguments": json.dumps(arguments, ensure_ascii=False, default=str),
                "status": status,
                "resultSummary": result_summary[:500],
                "errorMessage": error_message,
                "sourceRefs": json.dumps(source_refs, ensure_ascii=False),
                "durationMs": duration_ms,
            },
        )

    async def get_trace(self, task_id: str) -> list[dict[str, Any]]:
        rows = await self.db.fetch_all(
            query="""
                SELECT e.id, e.eventType, e.snapshotId, e.toolName, e.arguments,
                       e.status, e.resultSummary, e.errorMessage, e.sourceRefs,
                       e.durationMs, e.createTime,
                       s.sourceType, s.sourceRef, s.versionTag, s.contentHash, s.summary
                FROM article_provenance_event AS e
                LEFT JOIN material_snapshot AS s ON s.id = e.snapshotId
                WHERE e.taskId = :taskId
                ORDER BY e.id
            """,
            values={"taskId": task_id},
        )
        result = []
        for row in rows:
            item = dict(row)
            for key in ("arguments", "sourceRefs"):
                if item.get(key):
                    value = item[key]
                    item[key] = json.loads(value) if isinstance(value, str) else value
            if isinstance(item.get("createTime"), datetime):
                item["createTime"] = item["createTime"].isoformat()
            result.append(item)
        return result

    async def get_material(self, task_id: str, snapshot_id: int) -> dict[str, Any] | None:
        row = await self.db.fetch_one(
            query="""
                SELECT s.id, s.sourceType, s.sourceRef, s.versionTag,
                       s.contentHash, s.contentText, s.summary, s.createTime
                FROM material_snapshot AS s
                WHERE s.id = :snapshotId AND EXISTS (
                    SELECT 1 FROM article_provenance_event AS e
                    WHERE e.taskId = :taskId AND e.snapshotId = s.id
                )
            """,
            values={"taskId": task_id, "snapshotId": snapshot_id},
        )
        if row is None:
            return None
        item = dict(row)
        if isinstance(item.get("createTime"), datetime):
            item["createTime"] = item["createTime"].isoformat()
        return item
