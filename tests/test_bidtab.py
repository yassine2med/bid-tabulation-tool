import json
from pathlib import Path

import pytest

from bidtab.cli import main
from bidtab.tabulate import read_bids, render, tabulate

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "bids.csv"

BIDS = {
    "A": {"x": 100.0, "y": 50.0},
    "B": {"x": 90.0},
    "C": {"x": 110.0, "y": 70.0},
}


def test_raw_comparison_favors_incomplete_bid():
    results = tabulate(BIDS, "none")
    assert results[0].bidder == "B"


def test_median_fill_adds_missing_scope():
    b = next(r for r in tabulate(BIDS, "median") if r.bidder == "B")
    assert b.missing == ["y"]
    assert b.filled == 60.0 and b.adjusted == 150.0


def test_max_fill():
    b = next(r for r in tabulate(BIDS, "max") if r.bidder == "B")
    assert b.filled == 70.0


def test_ranking_changes_after_normalizing():
    assert tabulate(BIDS, "none")[0].bidder == "B"
    assert tabulate(BIDS, "median")[0].bidder == "A"


def test_complete_bid_has_no_gaps():
    a = next(r for r in tabulate(BIDS) if r.bidder == "A")
    assert a.missing == [] and a.adjusted == a.total


def test_bad_fill_mode():
    with pytest.raises(ValueError):
        tabulate(BIDS, "average")


def test_read_example_has_three_bidders():
    bids = read_bids(EXAMPLE)
    assert set(bids) == {"Acme Mechanical", "Bay Climate", "Summit Air"}
    assert "Controls integration" not in bids["Bay Climate"]


def test_bidder_with_all_items_excluded_still_listed(tmp_path):
    p = tmp_path / "b.csv"
    p.write_text("bidder,item,amount\nA,x,10\nB,x,excluded\n", encoding="utf-8")
    results = tabulate(read_bids(p))
    assert {r.bidder for r in results} == {"A", "B"}


def test_missing_columns(tmp_path):
    p = tmp_path / "b.csv"
    p.write_text("name,price\nA,1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_bids(p)


def test_bad_amount_reports_line(tmp_path):
    p = tmp_path / "b.csv"
    p.write_text("bidder,item,amount\nA,x,ten\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        read_bids(p)


def test_negative_and_duplicate(tmp_path):
    p = tmp_path / "b.csv"
    p.write_text("bidder,item,amount\nA,x,-5\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_bids(p)
    p.write_text("bidder,item,amount\nA,x,5\nA,x,6\n", encoding="utf-8")
    with pytest.raises(ValueError, match="twice"):
        read_bids(p)


def test_render_lists_gaps():
    text = render(tabulate(BIDS))
    assert "Scope gaps" in text and "B: y" in text


def test_cli_json(capsys):
    assert main([str(EXAMPLE), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["adjusted"] <= data[-1]["adjusted"]


def test_cli_missing_file(capsys):
    assert main(["nope.csv"]) == 2
