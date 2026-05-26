from fastapi import APIRouter
from pydantic import BaseModel

from app.core.chaos import chaos_state, ChaosConfig

router = APIRouter()


class ChaosUpdate(BaseModel):
    kill_claude: bool | None = None
    latency_spike: bool | None = None
    mcp_crash: bool | None = None


@router.get("", response_model=ChaosConfig)
async def get_chaos_state():
    return chaos_state


@router.post("", response_model=ChaosConfig)
async def update_chaos_state(payload: ChaosUpdate):
    if payload.kill_claude is not None:
        chaos_state.kill_claude = payload.kill_claude
    if payload.latency_spike is not None:
        chaos_state.latency_spike = payload.latency_spike
    if payload.mcp_crash is not None:
        chaos_state.mcp_crash = payload.mcp_crash
    return chaos_state
