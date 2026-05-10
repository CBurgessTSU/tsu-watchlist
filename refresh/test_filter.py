import unittest

from filter import FilterResult, filter_holdings, normalize_ticker


# Fixture: SIL (Global X Silver Miners ETF) top 15 holdings as displayed on etfdb.
# Ground truth below is derived from the user's manual review of this list:
#   - Shape-reject: 010130 (digit), PE&OLES (ampersand)
#   - Name-reject:  FRES (PLC)
#   - Pass to TV probe: the remaining 12 (incl. DSV and FVI, which likely fail the
#     probe because their US listings are OTC-only — but shape/name can't tell).
SIL_TOP_15 = [
    {"ticker": "WPM",     "name": "Wheaton Precious Metals Corp"},
    {"ticker": "PAAS",    "name": "Pan American Silver Corp."},
    {"ticker": "CDE",     "name": "Coeur Mining, Inc."},
    {"ticker": "AG",      "name": "First Majestic Silver Corp."},
    {"ticker": "FRES",    "name": "Fresnillo PLC"},
    {"ticker": "HL",      "name": "Hecla Mining Company"},
    {"ticker": "010130",  "name": "Korea Zinc Co., Ltd."},
    {"ticker": "PE&OLES", "name": "Industrias Penoles SAB de CV"},
    {"ticker": "BVN",     "name": "Compania de Minas Buenaventura SAA Sponsored ADR"},
    {"ticker": "SSRM",    "name": "SSR Mining Inc"},
    {"ticker": "OR",      "name": "OR Royalties Inc."},
    {"ticker": "DSV",     "name": "Discovery Silver Corp"},
    {"ticker": "FVI",     "name": "Fortuna Mining Corp."},
    {"ticker": "EDR",     "name": "Endeavour Silver Corp."},
    {"ticker": "TFPM",    "name": "Triple Flag Precious Metals Corp."},
]


class SilFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result: FilterResult = filter_holdings(SIL_TOP_15)

    def test_total_accounted_for(self) -> None:
        self.assertEqual(len(self.result.kept) + len(self.result.skipped), 15)

    def test_expected_kept_set(self) -> None:
        kept = {h.ticker for h in self.result.kept}
        self.assertEqual(
            kept,
            {"WPM", "PAAS", "CDE", "AG", "HL", "BVN", "SSRM", "NYSE:OR", "DSV", "FVI", "EDR", "TFPM"},
        )

    def test_shape_rejects(self) -> None:
        by_ticker = {s.ticker: s.reason for s in self.result.skipped}
        self.assertIn("010130", by_ticker)
        self.assertIn("digit", by_ticker["010130"])
        self.assertIn("PE&OLES", by_ticker)
        self.assertIn("&", by_ticker["PE&OLES"])

    def test_name_rejects(self) -> None:
        by_ticker = {s.ticker: s.reason for s in self.result.skipped}
        self.assertIn("FRES", by_ticker)
        self.assertIn("PLC", by_ticker["FRES"])

    def test_kept_order_preserved(self) -> None:
        # etfdb presents holdings sorted by % assets desc; the filter must not
        # reorder survivors, so the top-N slice downstream picks the right tickers.
        kept_order = [h.ticker for h in self.result.kept]
        self.assertEqual(kept_order[:3], ["WPM", "PAAS", "CDE"])


class ClassShareTests(unittest.TestCase):
    def test_normalize_slash_to_dot(self) -> None:
        self.assertEqual(normalize_ticker("BRK/B"), "BRK.B")
        self.assertEqual(normalize_ticker("BF/A"), "BF.A")

    def test_normalize_preserves_dot(self) -> None:
        self.assertEqual(normalize_ticker("BRK.B"), "BRK.B")

    def test_dual_class_passes_filter(self) -> None:
        rows = [
            {"ticker": "BRK.B", "name": "Berkshire Hathaway Inc."},
            {"ticker": "BF/B", "name": "Brown-Forman Corporation"},
            {"ticker": "LGF.A", "name": "Lions Gate Entertainment Corp."},
        ]
        result = filter_holdings(rows)
        self.assertEqual({h.ticker for h in result.kept}, {"BRK.B", "BF.B", "LGF.A"})
        self.assertEqual(result.skipped, [])


class ShapeRejectEdgeTests(unittest.TestCase):
    def test_digit_anywhere_rejects(self) -> None:
        for ticker in ("010130", "7203", "A1B"):
            result = filter_holdings([{"ticker": ticker, "name": "X"}])
            self.assertEqual(len(result.skipped), 1, f"expected reject for {ticker}")

    def test_ampersand_rejects(self) -> None:
        result = filter_holdings([{"ticker": "A&B", "name": "X"}])
        self.assertEqual(len(result.skipped), 1)
        self.assertIn("&", result.skipped[0].reason)


class NameRejectEdgeTests(unittest.TestCase):
    def test_plc_case_insensitive(self) -> None:
        for name in ("Fresnillo PLC", "Fresnillo plc", "FRESNILLO Plc"):
            result = filter_holdings([{"ticker": "XYZ", "name": name}])
            self.assertEqual(len(result.skipped), 1, f"expected reject for {name!r}")

    def test_plc_not_mid_name(self) -> None:
        # "Replica Inc." (hypothetical) contains 'plc' as substring but not as
        # the corporate suffix — must not trigger.
        result = filter_holdings([{"ticker": "RPLC", "name": "Replica Holdings Inc."}])
        self.assertEqual(len(result.skipped), 0)

    def test_sab_de_cv_rejects(self) -> None:
        result = filter_holdings(
            [{"ticker": "XYZ", "name": "Industrias Algo SAB de CV"}]
        )
        self.assertEqual(len(result.skipped), 1)
        self.assertIn("SAB DE CV", result.skipped[0].reason)


class ForeignPrimaryTickerTests(unittest.TestCase):
    def test_kap_rejected(self) -> None:
        result = filter_holdings([{"ticker": "KAP", "name": "National Atomic Company Kazatomprom JSC"}])
        self.assertEqual(len(result.kept), 0)
        self.assertEqual(len(result.skipped), 1)
        self.assertIn("foreign-primary", result.skipped[0].reason)

    def test_pdn_rejected(self) -> None:
        result = filter_holdings([{"ticker": "PDN", "name": "Paladin Energy Ltd"}])
        self.assertEqual(len(result.kept), 0)

    def test_lun_kgh_rejected(self) -> None:
        rows = [
            {"ticker": "LUN", "name": "Lundin Mining Corporation"},
            {"ticker": "KGH", "name": "KGHM Polska Miedz S.A."},
            {"ticker": "FCX", "name": "Freeport-McMoRan Inc."},
        ]
        result = filter_holdings(rows)
        self.assertEqual({h.ticker for h in result.kept}, {"FCX"})


class TickerRemapTests(unittest.TestCase):
    def test_or_remapped_to_nyse_prefix(self) -> None:
        result = filter_holdings([{"ticker": "OR", "name": "OR Royalties Inc."}])
        self.assertEqual([h.ticker for h in result.kept], ["NYSE:OR"])

    def test_bhp_remapped_to_nyse_prefix(self) -> None:
        result = filter_holdings([{"ticker": "BHP", "name": "BHP Group Limited"}])
        self.assertEqual([h.ticker for h in result.kept], ["NYSE:BHP"])


if __name__ == "__main__":
    unittest.main()
