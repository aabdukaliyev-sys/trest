"""Matches BUY/SELL trades per instrument to produce realized gains and open lots.

Kazakhstan's Tax Code does not mandate a single cost-basis method for individuals;
brokers commonly report on a FIFO basis, so FIFO is the default here. LIFO and
HIFO (highest-cost-first) are also provided so ``optimizer.py`` can show the tax
impact of each -- purely as an analytical comparison. Whichever method is used
must match what the broker actually reports, since the broker's records are the
basis for any tax filing.
"""

from __future__ import annotations

from decimal import Decimal

from .models import Lot, OpenPosition, RealizedGain, Trade

METHOD_FIFO = "FIFO"
METHOD_LIFO = "LIFO"
METHOD_HIFO = "HIFO"

_SORT_KEYS = {
    METHOD_FIFO: lambda lot: lot.open_date,
    METHOD_LIFO: lambda lot: lot.open_date,
    METHOD_HIFO: lambda lot: -lot.unit_cost_kzt,
}


def match_trades(
    trades: list[Trade], method: str = METHOD_FIFO
) -> tuple[list[RealizedGain], dict[str, OpenPosition]]:
    """Run cost-basis matching for every instrument in ``trades``.

    Returns (realized_gains, open_positions_by_instrument).
    """
    if method not in _SORT_KEYS:
        raise ValueError(f"unknown method: {method}")

    by_instrument: dict[str, list[Trade]] = {}
    for t in trades:
        by_instrument.setdefault(t.instrument, []).append(t)

    realized: list[RealizedGain] = []
    open_positions: dict[str, OpenPosition] = {}

    for instrument, instrument_trades in by_instrument.items():
        ordered = sorted(instrument_trades, key=lambda t: t.trade_date)
        open_lots: list[Lot] = []

        for trade in ordered:
            if trade.side == "BUY":
                unit_cost = (trade.gross_amount_kzt + trade.commission_kzt) / trade.quantity
                open_lots.append(
                    Lot(
                        open_date=trade.trade_date,
                        instrument=instrument,
                        quantity=trade.quantity,
                        unit_cost_kzt=unit_cost,
                        kase_official_list=trade.kase_official_list,
                    )
                )
                continue

            total_open = sum((lot.quantity for lot in open_lots), Decimal("0"))
            if trade.quantity > total_open:
                raise ValueError(
                    f"SELL of {trade.quantity} {instrument} on {trade.trade_date} "
                    "exceeds open quantity -- check trade history for missing BUYs"
                )

            open_lots.sort(key=_SORT_KEYS[method], reverse=(method == METHOD_LIFO))
            unit_proceeds = (trade.gross_amount_kzt - trade.commission_kzt) / trade.quantity
            remaining = trade.quantity

            while remaining > 0:
                lot = open_lots[0]
                take = min(lot.quantity, remaining)
                realized.append(
                    RealizedGain(
                        close_date=trade.trade_date,
                        instrument=instrument,
                        quantity=take,
                        proceeds_kzt=take * unit_proceeds,
                        cost_basis_kzt=take * lot.unit_cost_kzt,
                        kase_official_list=trade.kase_official_list and lot.kase_official_list,
                        open_date=lot.open_date,
                    )
                )
                lot.quantity -= take
                remaining -= take
                if lot.quantity == 0:
                    open_lots.pop(0)

        if open_lots:
            total_qty = sum((lot.quantity for lot in open_lots), Decimal("0"))
            total_cost = sum((lot.quantity * lot.unit_cost_kzt for lot in open_lots), Decimal("0"))
            all_exempt = all(lot.kase_official_list for lot in open_lots)
            open_positions[instrument] = OpenPosition(
                instrument=instrument,
                quantity=total_qty,
                cost_basis_kzt=total_cost,
                kase_official_list=all_exempt,
                open_date=min(lot.open_date for lot in open_lots),
                lots=open_lots,
            )

    return realized, open_positions
