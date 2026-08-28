#!/usr/bin/env python3
"""Automated LangSmith & Voice Evaluation Suite for VoxFlow Voice Agent.

Runs test scenarios against the LLM + Tools pipeline and scores:
  1. Security & Guardrails (Zero pre-verification data leakage — Hard Gate #5)
  2. Caller Verification Accuracy
  3. Spoken Brevity (Conversational brevity target <= 35 words/turn)
  4. Tool Selection Accuracy
  5. P95 Turn Latency

Usage:
  python scripts/run_evals.py                                # Run all scenarios
  python scripts/run_evals.py --category security_adversarial # Run only security gate
  python scripts/run_evals.py --tenant varun                  # Run tenant-scoped evals
  python scripts/run_evals.py --gate-only                     # Run only hard gate checks
  python scripts/run_evals.py --output evals/latest_run.json  # Save JSON report
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api")))

from voxflow_api.config import get_settings
from voxflow_api.db import init_db
from voxflow_api.services.eval_service import ReleaseThresholds, run_voice_eval


# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BLUE = "\033[94m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def format_status(passed: bool) -> str:
    return f"{GREEN}{BOLD}PASS{RESET}" if passed else f"{RED}{BOLD}FAIL{RESET}"


def print_report(report: dict, gate_only: bool = False) -> None:
    print("\n" + "=" * 80)
    print(f"{CYAN}{BOLD}🎙️  VOXFLOW VOICE EVALUATION HARNESS & RELEASE SCORECARD{RESET}")
    print("=" * 80)
    print(f"Run ID:        {report['run_id']}")
    print(f"Timestamp:     {report['timestamp']}")
    print(f"Tenant Scope:  {report['tenant_id'] or 'All Tenants'}")
    print(f"Total Tests:   {report['total_scenarios']} scenarios ({report['passed_scenarios']} passed, {report['failed_scenarios']} failed)")
    print(f"Pass Rate:     {report['overall_pass_rate']*100:.1f}%")
    print(f"Hard Gate:     {format_status(report['hard_gate_passed'])}")
    print(f"Release State: {'🚀 ' + GREEN + BOLD + 'RELEASE READY' + RESET if report['release_ready'] else '🛑 ' + RED + BOLD + 'DEPLOYMENT BLOCKED' + RESET}")
    print("-" * 80)

    # Scenarios detail
    print(f"\n{BOLD}📋 SCENARIO RESULTS:{RESET}")
    for i, sc in enumerate(report["scenarios"], 1):
        status_badge = f"[{GREEN}✓ PASS{RESET}]" if sc["passed"] else f"[{RED}✗ FAIL{RESET}]"
        gate_badge = f" {YELLOW}[HARD GATE]{RESET}" if sc["hard_gate"] else ""
        print(f"\n{BOLD}{i:2d}. {status_badge}{gate_badge} {sc['name']}{RESET} {DIM}({sc['category']} - {sc['scenario_id']}){RESET}")
        if sc.get("description"):
            print(f"    {DIM}{sc['description']}{RESET}")

        for t_idx, turn in enumerate(sc["turns"], 1):
            print(f"    {CYAN}User:{RESET} \"{turn['user_text']}\"")
            print(f"    {BLUE}Agent ({turn['word_count']}w, {turn['latency_ms']:.0f}ms):{RESET} \"{turn['reply_text']}\"")
            if turn["tool_calls"]:
                print(f"    {YELLOW}Tools:{RESET} {', '.join(turn['tool_calls'])}")

        if sc["violations"]:
            for v in sc["violations"]:
                print(f"    {RED}⚠️  VIOLATION: {v}{RESET}")

    # Category summary
    print("\n" + "-" * 80)
    print(f"{BOLD}📊 CATEGORY BREAKDOWN:{RESET}")
    print(f"{'Category':<28} {'Total':<8} {'Passed':<8} {'Pass Rate':<12} {'Gate Status'}")
    print("-" * 70)
    for cat in report["category_scores"]:
        rate_str = f"{cat['pass_rate']*100:.1f}%"
        gate_status = f"{RED}FAILED ({cat['hard_gate_failures']}){RESET}" if cat["hard_gate_failures"] > 0 else f"{GREEN}OK{RESET}"
        print(f"{cat['category']:<28} {cat['total']:<8} {cat['passed']:<8} {rate_str:<12} {gate_status}")

    # Release Thresholds Scorecard
    print("\n" + "-" * 80)
    print(f"{BOLD}🎯 RELEASE GATES & THRESHOLDS SCORECARD:{RESET}")
    print(f"{'Gate / Metric':<46} {'Target':<10} {'Actual':<10} {'Status'}")
    print("-" * 75)
    for th in report["thresholds"]:
        target_str = f"{th['comparator']} {th['target']}"
        actual_str = f"{th['actual']}"
        status_str = f"{GREEN}PASSED{RESET}" if th["passed"] else f"{RED}FAILED{RESET}"
        gate_label = f" {YELLOW}[GATE 5]{RESET}" if th.get("is_hard_gate") else ""
        print(f"{th['name'] + gate_label:<46} {target_str:<10} {actual_str:<10} {status_str}")

    print("=" * 80)
    if report["release_ready"]:
        print(f"{GREEN}{BOLD}🎉 ALL RELEASE THRESHOLDS MET! Build is approved for production deployment.{RESET}")
    else:
        print(f"{RED}{BOLD}❌ RELEASE GATE FAILED. Deployment blocked. Fix data leaks or accuracy regressions.{RESET}")
    print("=" * 80 + "\n")


async def main() -> int:
    parser = argparse.ArgumentParser(description="VoxFlow Voice Evaluation Harness & Release Gate Checker")
    parser.add_argument("--category", "-c", type=str, default=None, help="Filter scenarios by category")
    parser.add_argument("--tenant", "-t", type=str, default=None, help="Filter scenarios by tenant ID")
    parser.add_argument("--scenarios-file", "-f", type=str, default=None, help="Custom path to scenarios.json")
    parser.add_argument("--output", "-o", type=str, default=None, help="Path to write JSON evaluation report")
    parser.add_argument("--gate-only", "-g", action="store_true", help="Run only security adversarial hard gate scenarios")
    parser.add_argument("--min-pass-rate", type=float, default=None, help="Override minimum overall pass rate (e.g. 0.90)")
    args = parser.parse_args()

    init_db()
    settings = get_settings()

    thresholds = ReleaseThresholds()
    if args.min_pass_rate is not None:
        thresholds.min_overall_pass_rate = args.min_pass_rate

    cat_filter = "security_adversarial" if args.gate_only else args.category

    report = await run_voice_eval(
        scenarios_path=args.scenarios_file,
        category_filter=cat_filter,
        tenant_filter=args.tenant,
        thresholds=thresholds,
    )

    report_dict = report.to_dict()
    print_report(report_dict, gate_only=args.gate_only)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2)
        print(f"📄 Report written to {out_path}")

    # Return exit code 0 if release ready / hard gate passed, 1 otherwise
    if args.gate_only:
        return 0 if report.hard_gate_passed else 1
    return 0 if report.release_ready else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
