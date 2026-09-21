"""Data structures shared by the FIFO engine, tax rules and optimizer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class Trade:
    trade_date: date
    instrument: str
    side: str  # "BUY" or "SELL"
    quantity: Decimal
    price: Decimal
    currency: str
    commission: Decimal = Decimal("0")
    fx_rate_to_kzt: Decimal = Decimal("1")
    kase_official_list: bool = False

    def __post_init__(self) -> None:
        if self.side not in ("BUY", "SELL"):
            raise ValueError(f"side must be BUY or SELL, got {self.side!r}")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")

    @property
    def gross_amount_kzt(self) -> Decimal:
        return self.quantity * self.price * self.fx_rate_to_kzt

    @property
    def commission_kzt(self) -> Decimal:
        return self.commission * self.fx_rate_to_kzt


@dataclass
class Dividend:
    payment_date: date
    instrument: str
    amount: Decimal
    currency: str
    fx_rate_to_kzt: Decimal = Decimal("1")
    foreign_tax_withheld: Decimal = Decimal("0")
    kase_official_list: bool = False
    holding_period_years: Decimal = Decimal("0")

    @property
    def amount_kzt(self) -> Decimal:
        return self.amount * self.fx_rate_to_kzt

    @property
    def foreign_tax_withheld_kzt(self) -> Decimal:
        return self.foreign_tax_withheld * self.fx_rate_to_kzt


@dataclass
class Lot:
    """An open (unmatched) portion of a BUY trade, tracked for FIFO matching."""

    open_date: date
    instrument: str
    quantity: Decimal
    unit_cost_kzt: Decimal
    kase_official_list: bool


@dataclass
class RealizedGain:
    close_date: date
    instrument: str
    quantity: Decimal
    proceeds_kzt: Decimal
    cost_basis_kzt: Decimal
    kase_official_list: bool
    open_date: date | None = None

    @property
    def gain_kzt(self) -> Decimal:
        return self.proceeds_kzt - self.cost_basis_kzt


@dataclass
class OpenPosition:
    instrument: str
    quantity: Decimal
    cost_basis_kzt: Decimal
    kase_official_list: bool
    open_date: date
    lots: list = field(default_factory=list)
