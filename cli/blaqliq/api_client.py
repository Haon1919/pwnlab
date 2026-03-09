import httpx
from typing import Optional, Any, Dict
from blaqliq.config import get_api_url, get_token

class APIError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class BlaqLiqClient:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = base_url or get_api_url()
        self.token = token or get_token()

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise APIError(detail, response.status_code)
        return response.json()

    def post(self, path: str, data: dict = None, form: dict = None) -> Any:
        with httpx.Client(base_url=self.base_url, timeout=30.0) as client:
            if form:
                response = client.post(path, data=form, headers={
                    k: v for k, v in self._headers().items() if k != "Content-Type"
                })
            else:
                response = client.post(path, json=data or {}, headers=self._headers())
        return self._handle_response(response)

    def get(self, path: str, params: dict = None) -> Any:
        with httpx.Client(base_url=self.base_url, timeout=30.0) as client:
            response = client.get(path, params=params or {}, headers=self._headers())
        return self._handle_response(response)

    def delete(self, path: str) -> Any:
        with httpx.Client(base_url=self.base_url, timeout=30.0) as client:
            response = client.delete(path, headers=self._headers())
        return self._handle_response(response)

    def login(self, username: str, password: str) -> str:
        data = self.post("/auth/token", form={"username": username, "password": password})
        return data["access_token"]

    def register(self, username: str, email: str, password: str) -> dict:
        return self.post("/auth/register", {"username": username, "email": email, "password": password})

    def get_me(self) -> dict:
        return self.get("/auth/me")

    def list_scenarios(self, difficulty: str = None, tag: str = None) -> list:
        params = {}
        if difficulty:
            params["difficulty"] = difficulty
        if tag:
            params["tag"] = tag
        return self.get("/scenarios", params=params)

    def start_session(self, scenario_id: str, wargame: bool = False, blackbox: bool = False) -> dict:
        return self.post("/sessions", {
            "scenario_id": scenario_id,
            "wargame": wargame,
            "blackbox": blackbox,
        })

    def get_session(self, session_id: str) -> dict:
        return self.get(f"/sessions/{session_id}")

    def list_sessions(self) -> list:
        return self.get("/sessions")

    def stop_session(self, session_id: str) -> dict:
        return self.delete(f"/sessions/{session_id}")

    def submit_flag(self, session_id: str, flag: str, objective_id: str) -> dict:
        return self.post(f"/sessions/{session_id}/flag", {"flag": flag, "objective_id": objective_id})

    def get_wargame(self, session_id: str) -> dict:
        return self.get(f"/wargames/{session_id}")

    def get_wargame_events(self, session_id: str, limit: int = 20) -> list:
        return self.get(f"/wargames/{session_id}/events", {"limit": limit})

    def generate_scenario(self, prompt: str, difficulty: str = "beginner", tags: list = None, wargame: bool = False, api_key: str = None) -> dict:
        data = {"prompt": prompt, "difficulty": difficulty, "tags": tags or [], "wargame": wargame}
        if api_key:
            data["gemini_api_key"] = api_key
        return self.post("/ai/generate-scenario", data)

    def start_blackbox(self, novel: bool = False) -> dict:
        return self.post("/ai/blackbox", {"novel": novel})

    def reveal_blackbox(self, session_id: str) -> dict:
        return self.get(f"/ai/blackbox/{session_id}/reveal")

    def create_api_key(self, label: str = "default") -> dict:
        return self.post("/auth/api-keys", {"label": label})

    def list_api_keys(self) -> list:
        return self.get("/auth/api-keys")
