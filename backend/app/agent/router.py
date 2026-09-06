"""Agent control API routes — start, stop, status, runs."""

import logging

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.auth.schemas import UserProfile
from app.agent.worker import agent_worker
from app.agent.schemas import AgentStatus, AgentRunResponse, AgentControlResponse
from app.database import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status", response_model=AgentStatus)
async def get_agent_status(user: UserProfile = Depends(get_current_user)):
    """Get the current agent worker status."""
    status = agent_worker.get_status()
    return AgentStatus(**status)


@router.post("/start", response_model=AgentControlResponse)
async def start_agent(user: UserProfile = Depends(get_current_user)):
    """Start the agent worker."""
    if agent_worker.is_running:
        status = agent_worker.get_status()
        return AgentControlResponse(
            success=False,
            message="Agent is already running.",
            status=AgentStatus(**status),
        )

    await agent_worker.start()
    status = agent_worker.get_status()

    return AgentControlResponse(
        success=True,
        message="Agent started successfully.",
        status=AgentStatus(**status),
    )


@router.post("/stop", response_model=AgentControlResponse)
async def stop_agent(user: UserProfile = Depends(get_current_user)):
    """Stop the agent worker."""
    if not agent_worker.is_running:
        status = agent_worker.get_status()
        return AgentControlResponse(
            success=False,
            message="Agent is not running.",
            status=AgentStatus(**status),
        )

    await agent_worker.stop()
    status = agent_worker.get_status()

    return AgentControlResponse(
        success=True,
        message="Agent stopped.",
        status=AgentStatus(**status),
    )


@router.get("/runs", response_model=list[AgentRunResponse])
async def list_agent_runs(
    user: UserProfile = Depends(get_current_user),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List agent run history for the current user."""
    supabase = get_supabase_client()

    resp = (
        supabase.table("agent_runs")
        .select("*")
        .eq("user_id", user.id)
        .order("started_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    return [AgentRunResponse(**row) for row in (resp.data or [])]
