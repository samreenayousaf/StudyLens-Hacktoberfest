from typing import Any, Dict, Optional
import httpx
from fastapi import HTTPException, status


class OllamaClient:
    """Client for local Ollama HTTP API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "gemma3:1b",
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call local Ollama /api/generate endpoint and return raw text response."""
        url = f"{self.base_url}/api/generate"
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, json=payload)
                if res.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Ollama model '{self.model_name}' is not loaded or unavailable.",
                    )
                res.raise_for_status()
                data = res.json()
                return data.get("response", "")
        except httpx.ConnectError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Local Ollama service is not reachable on http://localhost:11434.",
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Ollama request timed out.",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error communicating with local Ollama: {str(exc)}",
            )
