"""REST API endpoints for Voice Eval Harness & Release Thresholds Scorecard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import (
    ROLE_OPERATOR,
    ROLE_OWNER,
    ROLE_VIEWER,
    require_authenticated_user,
    require_tenant_role,
)
from ..db import Tenant, get_session
from ..services.eval_service import (
    ReleaseThresholds,
    load_scenarios,
    run_voice_eval,
)

router = APIRouter(prefix="/api/evals", tags=["evals"])
tenant_eval_router = APIRouter(prefix="/api/tenants/{tenant_id}/evals", tags=["tenant-evals"])

# Cache the latest run report in memory for instant dashboard display. Keyed by
# tenant scope ("__all__" for the unfiltered run) so one tenant's operator run
# never serves scenario replies (call transcripts, order data) to another.
_EVAL_REPORT_CACHE: dict[str, dict[str, Any]] = {}
_ALL_SCOPE = "__all__"


class RunEvalRequest(BaseModel):
    category_filter: Optional[str] = Field(default=None, description="Optional category filter (e.g. 'security_adversarial')")
    tenant_id: Optional[str] = Field(default=None, description="Optional tenant ID to evaluate against")
    scenario_ids: Optional[list[str]] = Field(default=None, description="Optional specific scenario IDs to run")
    min_overall_pass_rate: Optional[float] = None
    min_security_pass_rate: Optional[float] = None
    min_verification_accuracy: Optional[float] = None
    min_tool_accuracy: Optional[float] = None
    max_avg_brevity_words: Optional[float] = None
    max_latency_p95_ms: Optional[float] = None


@router.get("/scenarios")
def list_eval_scenarios(
    category: Optional[str] = Query(None, description="Filter by scenario category"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
) -> list[dict[str, Any]]:
    """List all available benchmark test scenarios with metadata."""
    scenarios = load_scenarios(category_filter=category, tenant_filter=tenant_id)
    # Sanitize turns/assertions summary for the listing
    summary = []
    for sc in scenarios:
        summary.append({
            "id": sc.get("id"),
            "category": sc.get("category"),
            "name": sc.get("name"),
            "description": sc.get("description"),
            "tenant_id": sc.get("tenant_id"),
            "turns_count": len(sc.get("turns", [])),
            "hard_gate": sc.get("assertions", {}).get("hard_gate", False),
            "must_call_tools": sc.get("assertions", {}).get("must_call_tools", []),
            "forbidden_tools": sc.get("assertions", {}).get("forbidden_tools", []),
            "verified": sc.get("verified", False),
        })
    return summary


@router.get("/scorecard")
async def get_latest_scorecard(
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Get the latest voice eval scorecard or run a default baseline if none exists."""
    # Eval reports embed real scenario replies (order data, verification
    # details). They are tenant data — an authenticated member only.
    require_authenticated_user(request, allow_demo=True)

    cached = _EVAL_REPORT_CACHE.get(_ALL_SCOPE)
    if cached is not None:
        return cached

    # Run default eval suite to prime the scorecard
    report = await run_voice_eval()
    report_dict = report.to_dict()
    _EVAL_REPORT_CACHE[_ALL_SCOPE] = report_dict
    return report_dict


@router.post("/run")
async def execute_voice_eval(
    req: RunEvalRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Execute the voice eval harness on-demand and update the scorecard."""
    if req.tenant_id:
        if db.get(Tenant, req.tenant_id) is None:
            raise HTTPException(status_code=404, detail="Tenant not found")
        require_tenant_role(
            request,
            db,
            tenant_id=req.tenant_id,
            allowed_roles={ROLE_OWNER, ROLE_OPERATOR},
            allow_demo=True,
        )
    else:
        # An unscoped run covers every tenant's data; it must not be triggerable
        # anonymously (expensive LLM runs + cached results leak across tenants).
        require_authenticated_user(request, allow_demo=True)

    thresholds = ReleaseThresholds()
    if req.min_overall_pass_rate is not None:
        thresholds.min_overall_pass_rate = req.min_overall_pass_rate
    if req.min_security_pass_rate is not None:
        thresholds.min_security_pass_rate = req.min_security_pass_rate
    if req.min_verification_accuracy is not None:
        thresholds.min_verification_accuracy = req.min_verification_accuracy
    if req.min_tool_accuracy is not None:
        thresholds.min_tool_accuracy = req.min_tool_accuracy
    if req.max_avg_brevity_words is not None:
        thresholds.max_avg_brevity_words = req.max_avg_brevity_words
    if req.max_latency_p95_ms is not None:
        thresholds.max_latency_p95_ms = req.max_latency_p95_ms

    all_scenarios = load_scenarios(
        category_filter=req.category_filter,
        tenant_filter=req.tenant_id,
    )
    if req.scenario_ids:
        all_scenarios = [s for s in all_scenarios if s.get("id") in req.scenario_ids]

    report = await run_voice_eval(
        scenarios=all_scenarios,
        tenant_filter=req.tenant_id,
        category_filter=req.category_filter,
        thresholds=thresholds,
    )
    report_dict = report.to_dict()
    _EVAL_REPORT_CACHE[req.tenant_id or _ALL_SCOPE] = report_dict
    return report_dict


@tenant_eval_router.get("/scorecard")
async def get_tenant_eval_scorecard(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Get the evaluation scorecard scoped to a specific tenant."""
    if db.get(Tenant, tenant_id) is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    require_tenant_role(
        request,
        db,
        tenant_id=tenant_id,
        allowed_roles={ROLE_OWNER, ROLE_OPERATOR, ROLE_VIEWER},
        allow_demo=True,
    )

    cached = _EVAL_REPORT_CACHE.get(tenant_id)
    if cached is not None:
        return cached

    report = await run_voice_eval(tenant_filter=tenant_id)
    report_dict = report.to_dict()
    _EVAL_REPORT_CACHE[tenant_id] = report_dict
    return report_dict


@tenant_eval_router.post("/run")
async def run_tenant_eval(
    tenant_id: str,
    req: RunEvalRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Execute evaluation harness for a specific tenant as an owner or operator."""
    if db.get(Tenant, tenant_id) is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    require_tenant_role(
        request,
        db,
        tenant_id=tenant_id,
        allowed_roles={ROLE_OWNER, ROLE_OPERATOR},
        allow_demo=True,
    )

    req.tenant_id = tenant_id
    return await execute_voice_eval(req=req, request=request, db=db)


def clear_eval_report_cache(tenant_id: str | None = None) -> None:
    """Invalidate cached scorecards (tests, tenant data changes)."""
    if tenant_id:
        _EVAL_REPORT_CACHE.pop(tenant_id, None)
    else:
        _EVAL_REPORT_CACHE.clear()

