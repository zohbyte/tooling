"""Simple Python client for glitch.ad CTF API (OpenAPI v3 style)."""
from __future__ import annotations

import requests
from typing import Any, Dict, List, Optional


class GlitchADClient:
    def __init__(self, base_url: str, timeout: int = 5) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        res = self.session.get(url, params=params, timeout=self.timeout)
        res.raise_for_status()
        return res.json()

    def _post(self, path: str, data: Any = None) -> Any:
        url = f"{self.base_url}{path}"
        res = self.session.post(url, json=data, timeout=self.timeout)
        res.raise_for_status()
        return res.json()

    def ping(self, code: str = "") -> Any:
        return self._get("/api/ping", params={"code": code})

    def get_teams(self) -> Any:
        return self._get("/api/teams")

    def get_scores(self) -> Any:
        return self._get("/api/scores")

    def get_info(self) -> Any:
        return self._get("/api/info")

    def get_checks(self) -> Any:
        return self._get("/api/checks")

    def get_flagids(self) -> Any:
        return self._get("/api/flagids")

    def get_flagids_service(self, service_id: int) -> Any:
        return self._get(f"/api/flagids/{service_id}")

    def get_flagids_service_team(self, service_id: int, team_id: int) -> Any:
        return self._get(f"/api/flagids/{service_id}/{team_id}")

    def steal_flag(self, flags: List[str]) -> Any:
        if not flags:
            raise ValueError("flags must be a non-empty list")
        payload = {"flags": flags}
        return self._post("/api/submit", data=payload)

    def rename_team(self, name: str) -> Any:
        if not name:
            raise ValueError("name must be non-empty")
        payload = {"name": name}
        return self._post("/api/rename", data=payload)


if __name__ == "__main__":
    import os

    base = os.environ.get("GLITCH_AD_URL", "https://glitch.ad")
    client = GlitchADClient(base)

    print("Ping:", client.ping())
    print("Teams:", client.get_teams())
    print("Scores:", client.get_scores())
