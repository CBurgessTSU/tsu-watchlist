"""Unit tests for holdings.py (pure functions only — no network calls)."""

import unittest
from holdings import _decode_ticker, _parse_sveltekit_holdings


class DecodeTicker(unittest.TestCase):
    def test_us_strips_dollar(self):
        self.assertEqual(_decode_ticker("$AAPL"), "AAPL")

    def test_us_dual_class(self):
        self.assertEqual(_decode_ticker("$BRK.B"), "BRK.B")

    def test_foreign_strips_exchange_prefix(self):
        self.assertEqual(_decode_ticker("!TSX/WPM"), "WPM")
        self.assertEqual(_decode_ticker("!XLON/FRES"), "FRES")
        self.assertEqual(_decode_ticker("!XHKG/00700"), "00700")

    def test_unknown_format_passthrough(self):
        # If StockAnalysis ever changes format, pass raw value through
        self.assertEqual(_decode_ticker("AAPL"), "AAPL")

    def test_german_suffix_passthrough(self):
        # e.g. GDX holds Endeavour Mining listed as EDG.DE
        self.assertEqual(_decode_ticker("EDG.DE"), "EDG.DE")


class ParseSveltekit(unittest.TestCase):
    def _make_payload(self, rows_dicts):
        """Build a minimal SvelteKit __data.json payload from a list of plain dicts.

        Layout:
          data[0]           = None (placeholder)
          data[1]           = list of row indices [2, 3, 4, ...]  ← the "index list"
          data[2..N+1]      = row dicts with string values replaced by pool indices
          data[N+2..]       = string pool (actual string values)
        """
        n = len(rows_dicts)
        row_start = 2  # row dicts begin at index 2
        string_start = row_start + n  # string pool begins after all row dicts

        pool = {}  # string → data[] index

        def intern(s):
            if s not in pool:
                pool[s] = string_start + len(pool)
            return pool[s]

        encoded_rows = []
        for row in rows_dicts:
            encoded = {k: (intern(v) if isinstance(v, str) else v) for k, v in row.items()}
            encoded_rows.append(encoded)

        row_indices = list(range(row_start, row_start + n))
        data = [None, row_indices] + encoded_rows

        # Append string pool in insertion order
        for s in pool:
            data.append(s)

        return {"nodes": [{"data": data}]}

    def test_returns_n_rows(self):
        rows = [{"s": "$AAPL", "n": "Apple Inc.", "as": "7.5"} for _ in range(15)]
        payload = self._make_payload(rows)
        result = _parse_sveltekit_holdings(payload, 10)
        self.assertEqual(len(result), 10)

    def test_empty_payload_returns_empty(self):
        result = _parse_sveltekit_holdings({}, 10)
        self.assertEqual(result, [])

    def test_no_nodes_returns_empty(self):
        result = _parse_sveltekit_holdings({"nodes": []}, 10)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
