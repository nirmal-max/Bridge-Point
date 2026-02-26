"""
Bridge Point — Commission Calculator
Deterministic financial logic. AI must NEVER override these calculations.

Platform Custody Model:
  Let B = budget (job amount)
  Platform commission = B × 0.03
  Worker payout = B - (B × 0.03) = B × 0.97
  Employer pays = B (exact budget, no extra charge)

All values stored as integer paise (1 ₹ = 100 paise) to avoid
floating-point rounding issues in financial calculations.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.config import COMMISSION_RATE_EMPLOYER, COMMISSION_RATE_LABOR


# Platform custody rate: 3% retained from budget
PLATFORM_CUSTODY_RATE = Decimal("0.03")


@dataclass(frozen=True)
class CommissionBreakdown:
    """Immutable breakdown of a job's financial components."""
    budget_paise: int                 # Original job budget in paise
    employer_commission_paise: int    # Legacy: 0 in platform custody model
    employer_total_paise: int         # What employer pays (= budget)
    labor_commission_paise: int       # Legacy: 0 in platform custody model
    labor_receives_paise: int         # Legacy alias for worker_payout
    platform_earning_paise: int       # Platform commission (3%)
    # ─── Platform Custody fields ────────────────────────
    platform_commission_paise: int    # budget × 0.03
    worker_payout_paise: int          # budget × 0.97

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
    Deterministic commission calculation — Platform Custody Model.

    Args:
        budget_rupees: The base job budget in ₹ (e.g., 700.0)

    Returns:
        CommissionBreakdown with all financial components in paise.

    Example for ₹700 job:
        Employer pays:         ₹700.00 (exact budget)
        Platform commission:   ₹21.00 (3%)
        Worker payout:         ₹679.00 (97%)
    """
    budget = Decimal(str(budget_rupees))

    # Platform custody: 3% retained
    platform_commission = (budget * PLATFORM_CUSTODY_RATE).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    worker_payout = budget - platform_commission

    # Employer pays exact budget (no extra surcharge)
    employer_total = budget

    # Convert to paise (integer) for storage
    def to_paise(amount: Decimal) -> int:
        return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    return CommissionBreakdown(
        budget_paise=to_paise(budget),
        employer_commission_paise=0,               # No extra employer charge
        employer_total_paise=to_paise(employer_total),
        labor_commission_paise=0,                   # No labor-side deduction label
        labor_receives_paise=to_paise(worker_payout),
        platform_earning_paise=to_paise(platform_commission),
        platform_commission_paise=to_paise(platform_commission),
        worker_payout_paise=to_paise(worker_payout),
    )
