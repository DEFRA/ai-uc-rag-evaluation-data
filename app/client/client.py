"""Sync and async HTTP clients for the ai-uc-rag-evaluation-data API."""

from __future__ import annotations

import httpx

from app.client.models import (
    CreateKnowledgeGroupRequest,
    KnowledgeGroup,
    KnowledgeSource,
    KnowledgeSourceInput,
    KnowledgeVectorResult,
    QueryResult,
    Snapshot,
    SourceType,
)


def _parse_source(data: dict) -> KnowledgeSource:
    return KnowledgeSource(
        source_id=data.get("sourceId", data.get("source_id", "")),
        name=data["name"],
        type=SourceType(data["type"]),
        location=data["location"],
    )


def _parse_group(data: dict) -> KnowledgeGroup:
    sources_data = data.get("sources", {})
    sources = (
        {
            k: _parse_source(v) if isinstance(v, dict) else v
            for k, v in sources_data.items()
        }
        if isinstance(sources_data, dict)
        else {}
    )
    return KnowledgeGroup(
        group_id=data.get("groupId", data.get("group_id", "")),
        title=data.get("title", data.get("name", "")),
        description=data["description"],
        owner=data["owner"],
        created_at=data.get("createdAt", data.get("created_at", "")),
        updated_at=data.get("updatedAt", data.get("updated_at", "")),
        sources=sources,
    )


def _parse_snapshot(data: dict) -> Snapshot:
    return Snapshot(
        snapshot_id=data.get("snapshotId", data.get("snapshot_id", "")),
        group_id=data.get("groupId", data.get("group_id", "")),
        version=data["version"],
        created_at=data.get("createdAt", data.get("created_at", "")),
        sources=data.get("sources", []),
    )


def _parse_vector_result(data: dict) -> KnowledgeVectorResult:
    return KnowledgeVectorResult(
        content=data["content"],
        similarity_score=data.get("similarityScore", data.get("similarity_score", 0)),
        similarity_category=data.get(
            "similarityCategory", data.get("similarity_category", "")
        ),
        created_at=data.get("createdAt", data.get("created_at", "")),
        name=data["name"],
        location=data["location"],
        snapshot_id=data.get("snapshotId", data.get("snapshot_id", "")),
        source_id=data.get("sourceId", data.get("source_id", "")),
    )


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        msg = f"HTTP {response.status_code}: {detail}"
        raise httpx.HTTPStatusError(
            msg,
            request=response.request,
            response=response,
        )


class DefraDataClient:
    """Synchronous client for the Defra Data API (knowledge & snapshots)."""

    def __init__(
        self,
        base_url: str = "http://data.localhost",
        timeout: float = 30.0,
        **httpx_kwargs: object,
    ):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=base_url, timeout=timeout, **httpx_kwargs)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> DefraDataClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # --- Knowledge groups ---

    def list_groups(self) -> list[KnowledgeGroup]:
        """List all knowledge groups."""
        r = self._client.get("/knowledge/groups")
        if r.status_code == 204:
            return []
        _raise_for_status(r)
        return [_parse_group(g) for g in r.json()]

    def get_group(self, group_id: str) -> KnowledgeGroup:
        """Get a knowledge group by ID."""
        r = self._client.get(f"/knowledge/groups/{group_id}")
        _raise_for_status(r)
        return _parse_group(r.json())

    def create_group(self, req: CreateKnowledgeGroupRequest) -> KnowledgeGroup:
        """Create a new knowledge group."""
        sources = []
        for s in req.sources:
            if isinstance(s, KnowledgeSourceInput):
                sources.append(
                    {"name": s.name, "type": s.type.value, "location": s.location}
                )
            else:
                sources.append(
                    {"name": s["name"], "type": s["type"], "location": s["location"]}
                )
        payload = {
            "name": req.name,
            "description": req.description,
            "owner": req.owner,
            "sources": sources,
        }
        r = self._client.post("/knowledge/groups", json=payload)
        _raise_for_status(r)
        return _parse_group(r.json())

    def add_source(
        self,
        group_id: str,
        source: KnowledgeSourceInput,
    ) -> KnowledgeGroup:
        """Add a source to a knowledge group."""
        payload = {
            "name": source.name,
            "type": source.type.value,
            "location": source.location,
        }
        r = self._client.patch(f"/knowledge/groups/{group_id}/sources", json=payload)
        _raise_for_status(r)
        return _parse_group(r.json())

    def ingest_group(self, group_id: str) -> dict:
        """Trigger ingestion for a knowledge group (async, returns immediately)."""
        r = self._client.post(f"/knowledge/groups/{group_id}/ingest")
        _raise_for_status(r)
        return r.json()

    def list_group_snapshots(self, group_id: str) -> list[Snapshot]:
        """List all snapshots for a knowledge group."""
        r = self._client.get(f"/knowledge/groups/{group_id}/snapshots")
        _raise_for_status(r)
        data = r.json()
        if isinstance(data, list):
            return [_parse_snapshot(s) for s in data]
        return []

    # --- Snapshots ---

    def get_snapshot(self, snapshot_id: str) -> Snapshot:
        """Get a snapshot by ID."""
        r = self._client.get(f"/snapshots/{snapshot_id}")
        _raise_for_status(r)
        return _parse_snapshot(r.json())

    def activate_snapshot(self, snapshot_id: str) -> dict:
        """Activate a snapshot for its knowledge group."""
        r = self._client.patch(f"/snapshots/{snapshot_id}/activate")
        _raise_for_status(r)
        return r.json()

    def query(
        self,
        group_id: str,
        query: str,
        max_results: int = 5,
    ) -> QueryResult:
        """Query a group's active snapshot (vector search)."""
        payload = {"groupId": group_id, "query": query, "maxResults": max_results}
        r = self._client.post("/snapshots/query", json=payload)
        _raise_for_status(r)
        results = [_parse_vector_result(d) for d in r.json()]
        return QueryResult(results=results)


class AsyncDefraDataClient:
    """Asynchronous client for the Defra Data API."""

    def __init__(
        self,
        base_url: str = "http://data.localhost",
        timeout: float = 30.0,
        **httpx_kwargs: object,
    ):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=base_url, timeout=timeout, **httpx_kwargs
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncDefraDataClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def list_groups(self) -> list[KnowledgeGroup]:
        r = await self._client.get("/knowledge/groups")
        if r.status_code == 204:
            return []
        _raise_for_status(r)
        return [_parse_group(g) for g in r.json()]

    async def get_group(self, group_id: str) -> KnowledgeGroup:
        r = await self._client.get(f"/knowledge/groups/{group_id}")
        _raise_for_status(r)
        return _parse_group(r.json())

    async def create_group(self, req: CreateKnowledgeGroupRequest) -> KnowledgeGroup:
        sources = []
        for s in req.sources:
            if isinstance(s, KnowledgeSourceInput):
                sources.append(
                    {"name": s.name, "type": s.type.value, "location": s.location}
                )
            else:
                sources.append(
                    {"name": s["name"], "type": s["type"], "location": s["location"]}
                )
        payload = {
            "name": req.name,
            "description": req.description,
            "owner": req.owner,
            "sources": sources,
        }
        r = await self._client.post("/knowledge/groups", json=payload)
        _raise_for_status(r)
        return _parse_group(r.json())

    async def add_source(
        self,
        group_id: str,
        source: KnowledgeSourceInput,
    ) -> KnowledgeGroup:
        payload = {
            "name": source.name,
            "type": source.type.value,
            "location": source.location,
        }
        r = await self._client.patch(
            f"/knowledge/groups/{group_id}/sources", json=payload
        )
        _raise_for_status(r)
        return _parse_group(r.json())

    async def ingest_group(self, group_id: str) -> dict:
        r = await self._client.post(f"/knowledge/groups/{group_id}/ingest")
        _raise_for_status(r)
        return r.json()

    async def list_group_snapshots(self, group_id: str) -> list[Snapshot]:
        r = await self._client.get(f"/knowledge/groups/{group_id}/snapshots")
        _raise_for_status(r)
        data = r.json()
        if isinstance(data, list):
            return [_parse_snapshot(s) for s in data]
        return []

    async def get_snapshot(self, snapshot_id: str) -> Snapshot:
        r = await self._client.get(f"/snapshots/{snapshot_id}")
        _raise_for_status(r)
        return _parse_snapshot(r.json())

    async def activate_snapshot(self, snapshot_id: str) -> dict:
        r = await self._client.patch(f"/snapshots/{snapshot_id}/activate")
        _raise_for_status(r)
        return r.json()

    async def query(
        self,
        group_id: str,
        query: str,
        max_results: int = 5,
    ) -> QueryResult:
        payload = {"groupId": group_id, "query": query, "maxResults": max_results}
        r = await self._client.post("/snapshots/query", json=payload)
        _raise_for_status(r)
        results = [_parse_vector_result(d) for d in r.json()]
        return QueryResult(results=results)
