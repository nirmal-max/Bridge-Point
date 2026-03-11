"""
Bridge Point — Commission Calculator
Deterministic financial logic. AI must NEVER override these calculations.

Dual-Sided Commission Model (4% + 4%):
  Let B = budget (job amount)
  Employer pays:        B × 1.04  (budget + 4% surcharge)
  Worker receives:      B × 0.96  (budget - 4% deduction)
  Platform earns:       B × 0.08  (8% total)

All values stored as integer paise (1 ₹ = 100 paise) to avoid
floating-point rounding issues in financial calculations.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.config import (
    COMMISSION_RATE_EMPLOYER,
    COMMISSION_RATE_LABOR,
    COMMISSION_RATE_PLATFORM,
)

EMPLOYER_RATE = Decimal(str(COMMISSION_RATE_EMPLOYER))
LABOR_RATE = Decimal(str(COMMISSION_RATE_LABOR))


@dataclass(frozen=True)
class CommissionBreakdown:
    """Immutable breakdown of a job's financial components."""
    budget_paise: int                 # Original job budget in paise
    employer_commission_paise: int    # What employer pays extra (4%)
    employer_total_paise: int         # Total employer pays (budget + 4%)
    labor_commission_paise: int       # What worker pays Platform (4%)
    labor_receives_paise: int         # What worker receives (budget - 4%)
    platform_earning_paise: int       # Total platform revenue (8%)
    # ─── Aliases for backward compat ─────────────────────
    platform_commission_paise: int    # Same as platform_earning_paise
    worker_payout_paise: int          # Same as labor_receives_paise

    @property
    def budget_rupees(self) -> Decimal:
        return Decimal(self.budget_paise) / 100

    @property
    def employer_total_rupees(self) -> Decimal:
        return Decimal(self.employer_total_paise) / 100

    @property
    def labor_receives_rupees(self) -> Decimal:
        return Decimal(self.labor_receives_paise) / 100

    @property
    def platform_earning_rupees(self) -> Decimal:
        return Decimal(self.platform_earning_paise) / 100

    @property
    def worker_payout_rupees(self) -> Decimal:
        return Decimal(self.worker_payout_paise) / 100

    def to_dict(self) -> dict:
        return {
            "budget": float(self.budget_rupees),
            "employer_commission": float(Decimal(self.employer_commission_paise) / 100),
            "employer_total": float(self.employer_total_rupees),
            "labor_commission": float(Decimal(self.labor_commission_paise) / 100),
            "labor_receives": float(self.labor_receives_rupees),
            "platform_earning": float(self.platform_earning_rupees),
            "platform_commission": float(Decimal(self.platform_commission_paise) / 100),
            "worker_payout": float(self.worker_payout_rupees),
            "currency": "INR",
        }


def calculate_commission(budget_rupees: float) -> CommissionBreakdown:
    """
    Deterministic commission calculation — Dual-Sided 4% + 4% Model.

    Args:
        budget_rupees: The base job budget in ₹ (e.g., 800.0)

    Returns:
        CommissionBreakdown with all financial components in paise.

    Example for ₹800 job:
        Employer extra fee:    ₹32.00  (4%)
        Employer total pays:   ₹832.00
        Worker deducted fee:   ₹32.00  (4%)
        Worker receives:       ₹768.00
        Total Platform logic:  ₹64.00  (8%)
    """
    budget = Decimal(str(budget_rupees))

    # Calculate both commissions
    employer_commission = (budget * EMPLOYER_RATE).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    labor_commission = (budget * LABOR_RATE).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Employer pays budget + 4% surcharge
    employer_total = budget + employer_commission

    # Worker receives budget - 4% deduction
    worker_payout = budget - labor_commission

    # Platform earns exactly the sum of both commissions
    platform_earning = employer_commission + labor_commission

    # Convert to paise (integer) for storage
    def to_paise(amount: Decimal) -> int:
        return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    return CommissionBreakdown(
        budget_paise=to_paise(budget),
        employer_commission_paise=to_paise(employer_commission),
        employer_total_paise=to_paise(employer_total),
        labor_commission_paise=to_paise(labor_commission),
        labor_receives_paise=to_paise(worker_payout),
        platform_earning_paise=to_paise(platform_earning),
        platform_commission_paise=to_paise(platform_earning),
        worker_payout_paise=to_paise(worker_payout),
    )
