"""Unit tests for the tiering logic.

Run from repo root:
    python3 -m unittest watchlist.test_weekly_sectors -v
"""

import unittest
from watchlist.weekly_sectors import (
    compute_return_pct,
    tier_sectors,
)


NON_CORE = ["MAGS", "XMAG", "BUZZ", "FFTY", "XLRE", "IBB"]


class TestComputeReturn(unittest.TestCase):
    def test_basic_gain(self):
        self.assertAlmostEqual(compute_return_pct(110, 100), 10.0)

    def test_loss(self):
        self.assertAlmostEqual(compute_return_pct(90, 100), -10.0)

    def test_zero_then_raises(self):
        with self.assertRaises(ValueError):
            compute_return_pct(100, 0)


class TestTierSectors(unittest.TestCase):
    def test_more_than_10_outperformers_caps_to_10(self):
        # 12 core ETFs all beating SPY (3% return)
        returns = {f"XL{c}": 5.0 + i for i, c in enumerate("ABCDEFGHIJKL")}
        result = tier_sectors(returns, spy_return=3.0, non_core=NON_CORE, target=10)
        self.assertEqual(len(result.core), 10)
        self.assertTrue(all(e.tier == "absolute_relative" for e in result.core))
        # Highest-return first
        self.assertGreater(result.core[0].return_pct, result.core[-1].return_pct)

    def test_fewer_than_10_outperformers_fills_with_absolute(self):
        # 7 outperforming SPY (5%); 4 positive but lagging; 2 negative
        returns = {
            **{f"OP{i}": 6.0 + i for i in range(7)},        # tier 1
            **{f"AB{i}": 1.0 + i * 0.5 for i in range(4)},  # tier 2
            "NEG1": -1.0, "NEG2": -3.0,                     # excluded
        }
        result = tier_sectors(returns, spy_return=5.0, non_core=NON_CORE, target=10)
        self.assertEqual(len(result.core), 10)
        tier1_count = sum(1 for e in result.core if e.tier == "absolute_relative")
        tier2_count = sum(1 for e in result.core if e.tier == "absolute")
        self.assertEqual(tier1_count, 7)
        self.assertEqual(tier2_count, 3)
        # Tier 1 ahead of Tier 2 in the list
        for i, entry in enumerate(result.core):
            if entry.tier == "absolute":
                self.assertTrue(all(e.tier == "absolute_relative" for e in result.core[:i]))
                break

    def test_bear_tape_returns_fewer_than_target(self):
        # Only 3 sectors positive; rest negative — should NOT pad with negatives
        returns = {"A": 2.0, "B": 1.0, "C": 0.5, "D": -1.0, "E": -5.0}
        result = tier_sectors(returns, spy_return=1.5, non_core=NON_CORE, target=10)
        self.assertEqual(len(result.core), 3)
        self.assertNotIn("D", [e.etf for e in result.core])
        self.assertNotIn("E", [e.etf for e in result.core])

    def test_non_core_excluded_from_core(self):
        returns = {"XLK": 8.0, "MAGS": 12.0, "IBB": 7.0, "XLF": 4.0}
        result = tier_sectors(returns, spy_return=3.0, non_core=NON_CORE, target=10)
        core_etfs = [e.etf for e in result.core]
        self.assertIn("XLK", core_etfs)
        self.assertIn("XLF", core_etfs)
        self.assertNotIn("MAGS", core_etfs)
        self.assertNotIn("IBB", core_etfs)

    def test_non_core_outperformers_become_honoraries(self):
        returns = {"MAGS": 12.0, "BUZZ": 8.0, "IBB": 1.0}  # IBB underperforms SPY
        result = tier_sectors(returns, spy_return=5.0, non_core=NON_CORE, target=10)
        honorary_etfs = [e.etf for e in result.honoraries]
        self.assertEqual(set(honorary_etfs), {"MAGS", "BUZZ"})
        self.assertNotIn("IBB", honorary_etfs)  # honoraries also require beating SPY

    def test_etf_equal_to_spy_goes_to_tier2(self):
        returns = {"XLA": 5.0, "XLB": 4.99}
        result = tier_sectors(returns, spy_return=5.0, non_core=NON_CORE, target=10)
        tiers = {e.etf: e.tier for e in result.core}
        self.assertEqual(tiers["XLA"], "absolute")  # exactly equal → tier 2
        self.assertEqual(tiers["XLB"], "absolute")


if __name__ == "__main__":
    unittest.main()
