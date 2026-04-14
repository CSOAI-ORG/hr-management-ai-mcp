#!/usr/bin/env python3
"""
HR Management AI MCP Server
===============================
Human resources toolkit for AI agents: leave calculation, payroll estimation,
performance review drafting, onboarding checklists, and compliance checking.

By MEOK AI Labs | https://meok.ai

Install: pip install mcp
Run:     python server.py
"""

import math
import re
from collections import defaultdict
from datetime import datetime, timedelta, date
from typing import Any, Optional
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
FREE_DAILY_LIMIT = 30
_usage: dict[str, list[datetime]] = defaultdict(list)


def _check_rate_limit(caller: str = "anonymous") -> Optional[str]:
    now = datetime.now()
    cutoff = now - timedelta(days=1)
    _usage[caller] = [t for t in _usage[caller] if t > cutoff]
    if len(_usage[caller]) >= FREE_DAILY_LIMIT:
        return f"Free tier limit reached ({FREE_DAILY_LIMIT}/day). Upgrade: https://mcpize.com/hr-management-ai-mcp/pro"
    _usage[caller].append(now)
    return None


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
LEAVE_POLICIES = {
    "US": {"annual": 15, "sick": 10, "personal": 3, "parental": 84, "bereavement": 5},
    "UK": {"annual": 28, "sick": 28, "personal": 0, "parental": 273, "bereavement": 5},
    "EU": {"annual": 25, "sick": 20, "personal": 2, "parental": 182, "bereavement": 5},
    "AU": {"annual": 20, "sick": 10, "personal": 2, "parental": 126, "bereavement": 3},
    "CA": {"annual": 15, "sick": 10, "personal": 3, "parental": 231, "bereavement": 5},
}

TAX_BRACKETS_US = [
    (11000, 0.10), (44725, 0.12), (95375, 0.22),
    (182100, 0.24), (231250, 0.32), (578125, 0.35), (float('inf'), 0.37),
]

COMPLIANCE_FRAMEWORKS = {
    "FLSA": {"region": "US", "topics": ["minimum_wage", "overtime", "child_labor", "recordkeeping"]},
    "GDPR": {"region": "EU", "topics": ["data_privacy", "consent", "right_to_erasure", "data_portability"]},
    "ADA": {"region": "US", "topics": ["disability_accommodation", "hiring", "workplace_access"]},
    "EEOC": {"region": "US", "topics": ["discrimination", "harassment", "equal_pay", "retaliation"]},
    "OSHA": {"region": "US", "topics": ["workplace_safety", "hazard_communication", "ppe", "reporting"]},
    "FMLA": {"region": "US", "topics": ["family_leave", "medical_leave", "job_protection"]},
    "WorkChoices": {"region": "AU", "topics": ["fair_work", "minimum_wage", "unfair_dismissal"]},
    "ERA": {"region": "UK", "topics": ["employment_rights", "unfair_dismissal", "redundancy", "notice_periods"]},
}


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------
def _leave_calculator(employee_start_date: str, region: str, leave_type: str,
                      days_taken: int, custom_allowance: int) -> dict:
    """Calculate leave balance and projections."""
    try:
        start = datetime.strptime(employee_start_date, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}

    policy = LEAVE_POLICIES.get(region, LEAVE_POLICIES["US"])
    total_allowance = custom_allowance if custom_allowance > 0 else policy.get(leave_type, 0)

    now = datetime.now()
    tenure_days = (now - start).days
    tenure_years = tenure_days / 365.25

    # Prorate for first year
    if tenure_years < 1:
        months_worked = min(12, max(1, tenure_days // 30))
        prorated_allowance = round(total_allowance * (months_worked / 12), 1)
    else:
        prorated_allowance = total_allowance
        # Seniority bonus
        if tenure_years > 5:
            prorated_allowance += 3
        elif tenure_years > 3:
            prorated_allowance += 1

    remaining = prorated_allowance - days_taken
    months_left = max(1, 12 - now.month)
    accrual_rate = total_allowance / 12

    return {
        "employee_start_date": employee_start_date,
        "region": region,
        "leave_type": leave_type,
        "tenure": {
            "days": tenure_days,
            "years": round(tenure_years, 1),
        },
        "allowance": {
            "base": total_allowance,
            "prorated": prorated_allowance,
            "seniority_bonus": prorated_allowance - total_allowance if prorated_allowance > total_allowance else 0,
        },
        "balance": {
            "taken": days_taken,
            "remaining": remaining,
            "accrual_rate_per_month": round(accrual_rate, 2),
            "projected_year_end": round(remaining + (accrual_rate * months_left) - days_taken, 1) if remaining < 0 else remaining,
        },
        "policy_reference": policy,
        "warnings": (
            ["Employee has exceeded leave allowance"] if remaining < 0
            else ["Low balance - less than 3 days remaining"] if remaining < 3
            else []
        ),
    }


def _payroll_estimator(annual_salary: float, region: str, pay_frequency: str,
                       retirement_pct: float, health_deduction: float) -> dict:
    """Estimate payroll breakdown with taxes and deductions."""
    if annual_salary <= 0:
        return {"error": "Salary must be positive"}

    frequencies = {"weekly": 52, "biweekly": 26, "semimonthly": 24, "monthly": 12}
    periods = frequencies.get(pay_frequency, 12)

    # Federal tax (US simplified)
    federal_tax = 0.0
    remaining_income = annual_salary
    prev_bracket = 0
    for bracket, rate in TAX_BRACKETS_US:
        taxable = min(remaining_income, bracket - prev_bracket)
        if taxable <= 0:
            break
        federal_tax += taxable * rate
        remaining_income -= taxable
        prev_bracket = bracket

    # State tax approximation
    state_tax_rates = {"US": 0.05, "UK": 0.20, "EU": 0.25, "AU": 0.15, "CA": 0.10}
    state_rate = state_tax_rates.get(region, 0.05)
    state_tax = annual_salary * state_rate

    # Social security / Medicare
    ss_tax = min(annual_salary, 160200) * 0.062
    medicare_tax = annual_salary * 0.0145
    if annual_salary > 200000:
        medicare_tax += (annual_salary - 200000) * 0.009

    # Deductions
    retirement = annual_salary * (retirement_pct / 100)
    health_annual = health_deduction * periods

    total_tax = federal_tax + state_tax + ss_tax + medicare_tax
    total_deductions = retirement + health_annual
    net_annual = annual_salary - total_tax - total_deductions
    net_per_period = net_annual / periods

    return {
        "gross_annual": annual_salary,
        "gross_per_period": round(annual_salary / periods, 2),
        "pay_frequency": pay_frequency,
        "pay_periods": periods,
        "taxes": {
            "federal": round(federal_tax, 2),
            "state": round(state_tax, 2),
            "social_security": round(ss_tax, 2),
            "medicare": round(medicare_tax, 2),
            "total_annual": round(total_tax, 2),
            "effective_rate_pct": round((total_tax / annual_salary) * 100, 2),
        },
        "deductions": {
            "retirement_annual": round(retirement, 2),
            "retirement_pct": retirement_pct,
            "health_annual": round(health_annual, 2),
            "health_per_period": health_deduction,
            "total_annual": round(total_deductions, 2),
        },
        "net": {
            "annual": round(net_annual, 2),
            "per_period": round(net_per_period, 2),
            "monthly_take_home": round(net_annual / 12, 2),
        },
        "region": region,
        "disclaimer": "Estimates only. Consult a tax professional for actual calculations.",
    }


def _performance_review(employee_name: str, role: str, period: str,
                        ratings: dict, goals_met: int, goals_total: int) -> dict:
    """Draft a structured performance review."""
    valid_categories = ["technical_skills", "communication", "leadership", "initiative",
                        "teamwork", "reliability", "creativity", "time_management"]

    validated_ratings = {}
    for cat, score in ratings.items():
        if cat not in valid_categories:
            continue
        score = max(1, min(5, int(score)))
        validated_ratings[cat] = score

    if not validated_ratings:
        validated_ratings = {"technical_skills": 3, "communication": 3, "teamwork": 3}

    avg_score = sum(validated_ratings.values()) / len(validated_ratings)
    goal_completion = (goals_met / max(goals_total, 1)) * 100

    # Performance tier
    if avg_score >= 4.5:
        tier = "Exceptional"
        summary = f"{employee_name} has consistently exceeded expectations across all dimensions."
        recommendation = "Promote or assign stretch projects. Consider for leadership pipeline."
    elif avg_score >= 3.5:
        tier = "Exceeds Expectations"
        summary = f"{employee_name} has performed above standard in most areas."
        recommendation = "Merit increase recommended. Identify growth opportunities."
    elif avg_score >= 2.5:
        tier = "Meets Expectations"
        summary = f"{employee_name} has reliably met job requirements."
        recommendation = "Continue current trajectory. Focus on development areas."
    elif avg_score >= 1.5:
        tier = "Needs Improvement"
        summary = f"{employee_name} has fallen below expectations in some areas."
        recommendation = "Create a Performance Improvement Plan (PIP). Weekly check-ins."
    else:
        tier = "Unsatisfactory"
        summary = f"{employee_name} has not met minimum job requirements."
        recommendation = "Immediate PIP required. Consider role change or termination process."

    # Strengths and development areas
    sorted_ratings = sorted(validated_ratings.items(), key=lambda x: x[1], reverse=True)
    strengths = [f"{cat.replace('_', ' ').title()} ({score}/5)" for cat, score in sorted_ratings[:3] if score >= 3]
    development = [f"{cat.replace('_', ' ').title()} ({score}/5)" for cat, score in sorted_ratings if score < 3]

    return {
        "employee": employee_name,
        "role": role,
        "review_period": period,
        "performance_tier": tier,
        "overall_score": round(avg_score, 2),
        "summary": summary,
        "ratings": validated_ratings,
        "goals": {
            "met": goals_met,
            "total": goals_total,
            "completion_pct": round(goal_completion, 1),
        },
        "strengths": strengths,
        "development_areas": development,
        "recommendation": recommendation,
        "next_steps": [
            f"Schedule follow-up meeting to discuss review",
            f"Set {max(3, goals_total)} goals for next period",
            f"{'Create development plan for: ' + ', '.join(development) if development else 'Identify stretch assignments'}",
            f"{'Schedule PIP check-ins' if avg_score < 2.5 else 'Quarterly check-in on progress'}",
        ],
        "valid_rating_categories": valid_categories,
    }


def _onboarding_checklist(role: str, department: str, start_date: str,
                          remote: bool) -> dict:
    """Generate a comprehensive onboarding checklist."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}

    pre_start = {
        "title": "Pre-Start (Before Day 1)",
        "due": (start - timedelta(days=7)).strftime("%Y-%m-%d"),
        "tasks": [
            {"task": "Send welcome email with start date and first-day details", "owner": "HR"},
            {"task": "Prepare employment contract and NDA", "owner": "HR"},
            {"task": "Set up email account and software licenses", "owner": "IT"},
            {"task": "Order laptop and peripherals", "owner": "IT"},
            {"task": "Assign buddy/mentor from the team", "owner": "Manager"},
            {"task": "Prepare desk/workspace" if not remote else "Ship home office equipment", "owner": "Facilities" if not remote else "IT"},
        ],
    }

    day_one = {
        "title": "Day 1",
        "due": start.strftime("%Y-%m-%d"),
        "tasks": [
            {"task": "Welcome meeting with manager", "owner": "Manager"},
            {"task": "Complete I-9, W-4, and benefits enrollment forms", "owner": "HR"},
            {"task": "IT setup: laptop, email, Slack, VPN", "owner": "IT"},
            {"task": "Office tour and team introductions" if not remote else "Virtual office tour and team video calls", "owner": "Buddy"},
            {"task": "Review company handbook and policies", "owner": "New Hire"},
            {"task": "Set up development environment" if department in ["Engineering", "Product"] else "Review department tools and processes", "owner": "New Hire"},
        ],
    }

    week_one = {
        "title": "Week 1",
        "due": (start + timedelta(days=5)).strftime("%Y-%m-%d"),
        "tasks": [
            {"task": "Complete compliance training (security, harassment prevention)", "owner": "New Hire"},
            {"task": "1:1 meeting with manager to discuss role expectations", "owner": "Manager"},
            {"task": "Meet with key stakeholders and cross-functional partners", "owner": "New Hire"},
            {"task": "Review current projects and documentation", "owner": "New Hire"},
            {"task": "Set up regular 1:1 cadence with manager", "owner": "Manager"},
        ],
    }

    month_one = {
        "title": "First 30 Days",
        "due": (start + timedelta(days=30)).strftime("%Y-%m-%d"),
        "tasks": [
            {"task": "Complete all required training modules", "owner": "New Hire"},
            {"task": "Deliver first small project or contribution", "owner": "New Hire"},
            {"task": "30-day check-in with HR", "owner": "HR"},
            {"task": "30-day check-in with manager - review initial goals", "owner": "Manager"},
            {"task": "Provide onboarding feedback survey", "owner": "New Hire"},
        ],
    }

    ninety_days = {
        "title": "First 90 Days",
        "due": (start + timedelta(days=90)).strftime("%Y-%m-%d"),
        "tasks": [
            {"task": "90-day performance review", "owner": "Manager"},
            {"task": "Confirm probation completion (if applicable)", "owner": "HR"},
            {"task": "Set goals for remainder of year", "owner": "Manager"},
            {"task": "Complete all compliance and role-specific certifications", "owner": "New Hire"},
        ],
    }

    phases = [pre_start, day_one, week_one, month_one, ninety_days]
    total_tasks = sum(len(p["tasks"]) for p in phases)

    return {
        "role": role,
        "department": department,
        "start_date": start_date,
        "remote": remote,
        "total_tasks": total_tasks,
        "phases": phases,
        "key_contacts": {
            "hr_representative": "Assigned by HR team",
            "direct_manager": "Assigned by department head",
            "buddy_mentor": "Assigned peer from team",
            "it_support": "IT helpdesk",
        },
    }


def _compliance_checker(region: str, company_size: int, topics: list[str]) -> dict:
    """Check applicable compliance frameworks and requirements."""
    applicable = []
    for name, framework in COMPLIANCE_FRAMEWORKS.items():
        if framework["region"] == region or region == "ALL":
            topic_overlap = set(topics) & set(framework["topics"])
            if topic_overlap or not topics:
                applicable.append({
                    "framework": name,
                    "region": framework["region"],
                    "matching_topics": list(topic_overlap) if topic_overlap else framework["topics"],
                    "all_topics": framework["topics"],
                })

    size_requirements = []
    if region == "US":
        if company_size >= 1:
            size_requirements.append({"threshold": 1, "requirement": "FLSA wage and hour laws apply"})
        if company_size >= 15:
            size_requirements.append({"threshold": 15, "requirement": "Title VII, ADA, GINA anti-discrimination laws apply"})
        if company_size >= 20:
            size_requirements.append({"threshold": 20, "requirement": "ADEA age discrimination protections apply"})
        if company_size >= 50:
            size_requirements.append({"threshold": 50, "requirement": "FMLA family/medical leave required; ACA employer mandate"})
        if company_size >= 100:
            size_requirements.append({"threshold": 100, "requirement": "EEO-1 reporting required; WARN Act notice for layoffs"})

    risk_items = []
    if "data_privacy" in topics and region in ["EU", "UK"]:
        risk_items.append({"risk": "GDPR non-compliance", "severity": "HIGH", "action": "Appoint DPO, conduct DPIA, update privacy policies"})
    if "discrimination" in topics:
        risk_items.append({"risk": "Discrimination claims", "severity": "HIGH", "action": "Regular training, documented policies, complaint procedures"})
    if "workplace_safety" in topics:
        risk_items.append({"risk": "OSHA violations", "severity": "MEDIUM", "action": "Safety audits, training records, incident reporting system"})
    if "minimum_wage" in topics:
        risk_items.append({"risk": "Wage violations", "severity": "HIGH", "action": "Regular pay audits, classification review, overtime tracking"})

    return {
        "region": region,
        "company_size": company_size,
        "topics_checked": topics,
        "applicable_frameworks": applicable,
        "size_based_requirements": size_requirements,
        "risk_items": risk_items,
        "recommendation": "Consult with an employment attorney for jurisdiction-specific compliance.",
        "last_updated": "2026-01-01",
    }


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "HR Management AI MCP",
    instructions="Human resources toolkit: leave calculation, payroll estimation, performance reviews, onboarding checklists, and compliance checking. By MEOK AI Labs.")


@mcp.tool()
def leave_calculator(employee_start_date: str, region: str = "US",
                     leave_type: str = "annual", days_taken: int = 0,
                     custom_allowance: int = 0) -> dict:
    """Calculate leave balance, accrual rate, and year-end projections based on
    region-specific policies and employee tenure.

    Args:
        employee_start_date: Employee start date (YYYY-MM-DD)
        region: Policy region (US, UK, EU, AU, CA)
        leave_type: Type of leave (annual, sick, personal, parental, bereavement)
        days_taken: Days already taken this year
        custom_allowance: Override default allowance (0 = use policy default)
    """
    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _leave_calculator(employee_start_date, region, leave_type, days_taken, custom_allowance)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def payroll_estimator(annual_salary: float, region: str = "US",
                      pay_frequency: str = "monthly",
                      retirement_pct: float = 6.0,
                      health_deduction: float = 250.0) -> dict:
    """Estimate net pay with tax brackets, Social Security, Medicare, retirement
    contributions, and health insurance deductions.

    Args:
        annual_salary: Gross annual salary
        region: Tax region (US, UK, EU, AU, CA)
        pay_frequency: Pay period (weekly, biweekly, semimonthly, monthly)
        retirement_pct: 401k/pension contribution percentage
        health_deduction: Health insurance deduction per pay period
    """
    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _payroll_estimator(annual_salary, region, pay_frequency, retirement_pct, health_deduction)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def performance_review(employee_name: str, role: str, period: str,
                       ratings: dict = {}, goals_met: int = 0,
                       goals_total: int = 5) -> dict:
    """Draft a structured performance review with tier assessment, strengths,
    development areas, and next steps.

    Args:
        employee_name: Employee's full name
        role: Job title
        period: Review period (e.g. "Q1 2026" or "2025 Annual")
        ratings: Category scores 1-5 as {category: score}. Categories: technical_skills, communication, leadership, initiative, teamwork, reliability, creativity, time_management
        goals_met: Number of goals achieved
        goals_total: Total goals set for the period
    """
    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _performance_review(employee_name, role, period, ratings, goals_met, goals_total)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def onboarding_checklist(role: str, department: str, start_date: str,
                         remote: bool = False) -> dict:
    """Generate a phased onboarding checklist covering pre-start through 90 days
    with task ownership assignments.

    Args:
        role: Job title for the new hire
        department: Department name (e.g. Engineering, Sales, Marketing)
        start_date: Start date (YYYY-MM-DD)
        remote: Whether the employee is remote
    """
    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _onboarding_checklist(role, department, start_date, remote)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def compliance_checker(region: str = "US", company_size: int = 50,
                       topics: list[str] = []) -> dict:
    """Check applicable employment compliance frameworks based on region,
    company size, and specific topics of concern.

    Args:
        region: Jurisdiction (US, UK, EU, AU, CA, or ALL)
        company_size: Number of employees
        topics: Specific compliance topics to check (e.g. ["minimum_wage", "data_privacy", "discrimination"])
    """
    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _compliance_checker(region, company_size, topics)
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()
