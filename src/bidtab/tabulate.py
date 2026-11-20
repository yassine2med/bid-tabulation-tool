"""Bid tabulation: compare vendor bids after normalizing scope gaps."""
from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass, field
from pathlib import Path

FILL_MODES = ("median", "max", "none")


@dataclass
class BidResult:
    """Totals for one bidder."""

    bidder: str
    total: float
    missing: list[str] = field(default_factory=list)
    filled: float = 0.0

    @property
    def adjusted(self) -> float:
        """Bid total plus the estimated price of the scope items the bidder left out."""
        return self.total + self.filled


def read_bids(path: str | Path) -> dict[str, dict[str, float]]:
    """Read a CSV with bidder, item, amount columns into {bidder: {item: amount}}.

    An empty amount or the word 'excluded' means the bidder left the item out.
    """
    bids: dict[str, dict[str, float]] = {}
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        needed = {"bidder", "item", "amount"}
        if not needed <= set(reader.fieldnames or []):
            raise ValueError(f"CSV needs columns {sorted(needed)}")
        for line, row in enumerate(reader, start=2):
            bidder, item = row["bidder"].strip(), row["item"].strip()
            raw = (row["amount"] or "").replace(",", "").replace("$", "").strip()
            bids.setdefault(bidder, {})
            if raw == "" or raw.lower() == "excluded":
                continue
            try:
                amount = float(raw)
            except ValueError as error:
                raise ValueError(f"line {line}: bad amount {row['amount']!r}") from error
            if amount < 0:
                raise ValueError(f"line {line}: negative amount for {item}")
            if item in bids[bidder]:
                raise ValueError(f"line {line}: {bidder} lists {item!r} twice")
            bids[bidder][item] = amount
    if not bids:
        raise ValueError("no bids found")
    return bids


def tabulate(bids: dict[str, dict[str, float]], fill: str = "median") -> list[BidResult]:
    """Rank bidders by adjusted total, lowest first.

    Every item that at least one bidder priced is part of the scope. For a bidder that
    left an item out, 'median' adds the median price other bidders gave, 'max' adds the
    highest, and 'none' adds nothing (a raw comparison).
    """
    if fill not in FILL_MODES:
        raise ValueError(f"fill must be one of {', '.join(FILL_MODES)}")
    scope = sorted({item for items in bids.values() for item in items})
    results = []
    for bidder, items in bids.items():
        result = BidResult(bidder, sum(items.values()))
        for item in scope:
            if item in items:
                continue
            result.missing.append(item)
            prices = [b[item] for b in bids.values() if item in b]
            if fill == "median":
                result.filled += statistics.median(prices)
            elif fill == "max":
                result.filled += max(prices)
        results.append(result)
    return sorted(results, key=lambda r: (r.adjusted, r.bidder))


def render(results: list[BidResult]) -> str:
    """Text table of the ranked results plus a list of scope gaps."""
    low = results[0].adjusted
    lines = [f"{'Rank':<5}{'Bidder':<18}{'Bid total':>13}{'Gaps':>6}{'Adjusted':>13}{'Over low':>10}"]
    for rank, r in enumerate(results, start=1):
        over = 100.0 * (r.adjusted - low) / low if low else 0.0
        lines.append(
            f"{rank:<5}{r.bidder:<18}{r.total:>13,.2f}{len(r.missing):>6}"
            f"{r.adjusted:>13,.2f}{over:>9.1f}%"
        )
    gaps = [r for r in results if r.missing]
    if gaps:
        lines.append("")
        lines.append("Scope gaps (priced by others, left out by this bidder):")
        for r in gaps:
            lines.append(f"  {r.bidder}: {', '.join(r.missing)} (+{r.filled:,.2f})")
    return "\n".join(lines)
