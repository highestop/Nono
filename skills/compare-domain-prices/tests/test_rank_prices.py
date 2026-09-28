"""Offline checks for watchlist edits, price arithmetic, and incomplete evidence."""

from decimal import Decimal
import importlib.util
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "rank_prices", Path(__file__).resolve().parents[1] / "scripts" / "rank_prices.py"
)
ranker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ranker)


def offer(domain, registrar, registration, renewal, years=1, status="available", **extra):
    return {
        "domain": domain, "registrar": registrar, "status": status,
        "registration": {"usd": registration, "years": years},
        "renewal": {"usd": renewal, "years": years},
        "sources": ["https://example.com/prices"], **extra,
    }


def report(domains, offers):
    return ranker.render(domains, [], {
        "checked_at": "2026-09-28T16:00:00+08:00", "currency": "USD", "offers": offers,
    })


class RankPricesTests(unittest.TestCase):
    def test_color_boundaries(self):
        for amount, icon in [("0", "🟢"), ("10", "🟢"), ("10.01", "🟡"), ("20", "🟡"), ("20.01", "🔴")]:
            with self.subTest(amount=amount):
                self.assertTrue(ranker.price(Decimal(amount)).startswith(icon))

    def test_watchlist_is_reread_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "domains.txt"
            initial = "# personal list\n Highestop.CC \nhighestop.cc\n\nhttps://invalid.com\nexample.co.uk\n"
            path.write_text(initial, encoding="utf-8")
            domains, errors = ranker.read_watchlist(path)
            self.assertEqual(domains, ["highestop.cc", "example.co.uk"])
            self.assertEqual(len(errors), 1)
            self.assertEqual(path.read_text(encoding="utf-8"), initial)
            path.write_text("highestop.site\n", encoding="utf-8")
            self.assertEqual(ranker.read_watchlist(path), (["highestop.site"], []))

    def test_renewal_cost_outweighs_teaser_and_removed_domains_disappear(self):
        output = report(["example.site", "example.cc"], [
            offer("example.site", "Porkbun", "1", "30"),
            offer("example.site", "Dynadot", "8", "10"),
            offer("example.cc", "Cloudflare", "8", "8"),
            offer("removed.com", "Porkbun", "0", "0"),
        ])
        self.assertLess(output.index("`example.cc`"), output.index("`example.site`"))
        self.assertIn("`example.site` | Dynadot", output)
        self.assertNotIn("removed.com", output)
        self.assertNotIn("| 3 年", output)
        self.assertNotIn("$28.00", output)

    def test_two_year_quote_is_annualized_once_and_upfront_payment_remains(self):
        quote = offer("example.ai", "Cloudflare", "160", "180", years=2)
        self.assertEqual(ranker.score(quote), Decimal("250"))
        output = report(["example.ai"], [quote])
        self.assertIn("🔴 $80.00 / 🔴 $90.00", output)
        self.assertIn("首次支付 $160.00", output)
        self.assertIn("续费每 2 年 $180.00", output)
        self.assertIn("使用至第 3 年需付至第 4 年", output)
        self.assertNotIn("$250.00", output)

    def test_bundle_and_renewal_promotion_are_visible(self):
        quote = offer("example.vip", "Porkbun", "4.12", "5.15", renewal_regular={"usd": "15.96", "years": 1})
        bundle = offer("example.vip", "Dynadot", "13.00", "5.03", notes="三年注册促销")
        bundle["registration"]["years"] = 3
        self.assertEqual(ranker.score(bundle), Decimal("13.00"))
        output = report(["example.vip"], [quote])
        self.assertIn("续费促销", output)
        self.assertIn("$15.96", output)
        output = report(["example.vip"], [quote, bundle])
        self.assertIn("`example.vip` | Dynadot", output)
        self.assertIn("首次支付 $13.00", output)

    def test_reference_missing_and_registered_domains_are_not_confirmed_bargains(self):
        registered = offer("taken.com", "Dynadot", "1", "1", status="registered")
        output = report(["reference.cc", "unknown.cc", "taken.com"], [
            offer("reference.cc", "Cloudflare", "8", "8", status="reference"),
            registered, offer("taken.com", "Porkbun", "1", "1", status="reference"),
        ])
        self.assertIn("Cloudflare（参考）", output)
        self.assertIn("暂定推荐", output)
        self.assertIn("| — | `unknown.cc` | — | — / — |", output)
        self.assertIn("| — | `taken.com` | — | — / — |", output)
        self.assertIn("已注册", output)

    def test_decimal_ties_and_markdown_notes(self):
        output = report(["example.fun"], [
            offer("example.fun", "Cloudflare", "4.99", "30.20", notes="sale | terms\nnext line"),
            offer("example.fun", "Porkbun", "2.57", "31.41"),
        ])
        self.assertIn("`example.fun` | Cloudflare", output)
        self.assertIn("折算成本并列：Porkbun", output)
        self.assertIn("sale \\| terms next line", output)

    def test_invalid_price_terms_are_rejected(self):
        for value in [
            {"usd": "NaN", "years": 1}, {"usd": "-1", "years": 1},
            {"usd": "1", "years": 0}, {"usd": "1", "years": True},
            {"usd": "1", "years": 1.5},
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                ranker.term(value)


if __name__ == "__main__":
    unittest.main()
