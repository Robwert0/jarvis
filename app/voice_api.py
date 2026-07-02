from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.agent import DISPATCH
from app.config import Settings, get_settings

router = APIRouter(prefix="/jarvis")

SIGNED_URL_ENDPOINT = "https://api.elevenlabs.io/v1/convai/conversation/get-signed-url"

_http_get = httpx.get


@router.get("/voice/signed-url")
def get_signed_url(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    if not settings.elevenlabs_api_key or not settings.elevenlabs_agent_id:
        raise HTTPException(status_code=503, detail="ElevenLabs is not configured")
    try:
        res = _http_get(
            SIGNED_URL_ENDPOINT,
            params={"agent_id": settings.elevenlabs_agent_id},
            headers={"xi-api-key": settings.elevenlabs_api_key},
            timeout=10.0,
        )
        res.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not get a signed URL from ElevenLabs")
    return {"signed_url": res.json()["signed_url"]}


@router.get("/voice/wake-config")
def get_wake_config(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    if not settings.picovoice_access_key:
        raise HTTPException(status_code=503, detail="Picovoice is not configured")
    return {"access_key": settings.picovoice_access_key}


@router.post("/tools/{name}")
def execute_tool(name: str, params: dict[str, Any] | None = None) -> dict[str, str]:
    fn = DISPATCH.get(name)
    if fn is None:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")
    return {"result": fn(params or {})}
