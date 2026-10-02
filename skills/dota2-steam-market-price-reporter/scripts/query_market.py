#!/usr/bin/env python3
"""Query public Steam Community Market prices with optional historical medians."""

import argparse
import calendar
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


MARKET_BASE_URL = "https://steamcommunity.com/market"
USER_AGENT = "Mozilla/5.0 (compatible; dota2-steam-market-price-reporter/1.0)"


class SteamMarketError(RuntimeError):
    pass


class SteamMarketClient:
    def __init__(self, delay, retries, timeout):
        self.delay = delay
        self.retries = retries
        self.timeout = timeout
        self.last_request_at = None

    def _pace(self):
        if self.last_request_at is not None:
            remaining = self.delay - (time.monotonic() - self.last_request_at)
            if remaining > 0:
                time.sleep(remaining)
        self.last_request_at = time.monotonic()

    def get_text(self, url):
        for attempt in range(self.retries + 1):
            self._pace()
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    charset = response.headers.get_content_charset() or "utf-8"
                    return response.read().decode(charset, errors="replace")
            except urllib.error.HTTPError as error:
                retryable = error.code == 429 or 500 <= error.code < 600
                if retryable and attempt < self.retries:
                    wait = retry_delay(error, attempt)
                    print(
                        f"Steam returned HTTP {error.code}; retrying in {wait:.1f}s "
                        f"({attempt + 1}/{self.retries}).",
                        file=sys.stderr,
                    )
                    time.sleep(wait)
                    continue
                raise SteamMarketError(
                    f"Steam request failed with HTTP {error.code}: {url}"
                ) from error
            except urllib.error.URLError as error:
                if attempt < self.retries:
                    wait = min(5 * (2**attempt), 30)
                    print(
                        f"Steam request failed; retrying in {wait:.1f}s "
                        f"({attempt + 1}/{self.retries}): {error.reason}",
                        file=sys.stderr,
                    )
                    time.sleep(wait)
                    continue
                raise SteamMarketError(
                    f"Steam request failed after {self.retries + 1} attempts: {url}"
                ) from error
        raise SteamMarketError(f"Steam request failed: {url}")

    def get_json(self, url):
        try:
            return json.loads(self.get_text(url))
        except json.JSONDecodeError as error:
            raise SteamMarketError(f"Steam returned invalid JSON: {url}") from error


def retry_delay(error, attempt):
    value = error.headers.get("Retry-After") if error.headers else None
    if value:
        try:
            return min(max(float(value), 0), 30)
        except ValueError:
            pass
    return min(5 * (2**attempt), 30)


def build_url(path, params=None):
    url = MARKET_BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return url


def parse_money(text):
    if not text:
        return None
    match = re.search(r"-?\d[\d.,]*", text)
    if not match:
        return None
    value = match.group(0)
    if "." in value:
        value = value.replace(",", "")
    elif value.count(",") == 1 and len(value.rsplit(",", 1)[1]) in (1, 2):
        value = value.replace(",", ".")
    else:
        value = value.replace(",", "")
    try:
        return float(value)
    except ValueError:
        return None


def extract_ssr_market_data(html, requested_name):
    match = re.search(r'JSON\.parse\(("(?:\\.|[^"\\])*")\)', html)
    if not match:
        raise SteamMarketError(f"Steam SSR payload is missing for {requested_name!r}")
    try:
        root = json.loads(json.loads(match.group(1)))
        query_data = json.loads(root["queryData"])
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise SteamMarketError(
            f"Steam SSR payload is invalid for {requested_name!r}"
        ) from error

    queries = query_data.get("queries") or []
    description = find_query(queries, "description", requested_name)
    history = find_query(queries, "pricehistory", requested_name)
    orderbook = find_query(queries, "orderbook", requested_name)
    if not description or not history or not orderbook:
        raise SteamMarketError(
            f"Steam market data is incomplete for exact item {requested_name!r}"
        )

    description_data = description["state"]["data"]
    history_data = history["state"]["data"]
    orderbook_data = orderbook["state"]["data"]
    history_currency = history_data.get("ecurrency")
    orderbook_currency = orderbook_data.get("eCurrency")
    if history_currency != orderbook_currency:
        raise SteamMarketError(
            f"Steam returned inconsistent currencies for {requested_name!r}: "
            f"history={history_currency}, orderbook={orderbook_currency}"
        )

    amount = orderbook_data.get("amtMinSellOrder")
    current_base = amount / 100 if isinstance(amount, (int, float)) and amount > 0 else None
    return {
        "market_name": description_data.get("market_name") or requested_name,
        "type": description_data.get("type"),
        "base_currency_id": history_currency,
        "current_base": current_base,
        "listing_count": orderbook_data.get("cSellOrders"),
        "prices": history_data.get("prices") or [],
        "history_updated_at": history["state"].get("dataUpdatedAt"),
    }


def find_query(queries, kind, item_name):
    for query in queries:
        key = query.get("queryKey")
        if (
            isinstance(key, list)
            and len(key) >= 4
            and key[0] == "market"
            and key[1] == kind
            and key[3] == item_name
        ):
            return query
    return None


def weighted_median(points):
    rows = sorted(
        (
            point
            for point in points
            if isinstance(point.get("price_median"), (int, float))
            and isinstance(point.get("purchases"), int)
            and point["purchases"] > 0
        ),
        key=lambda point: point["price_median"],
    )
    purchases = sum(point["purchases"] for point in rows)
    if purchases == 0:
        return None

    targets = ((purchases - 1) // 2, purchases // 2)
    values = []
    for target in targets:
        seen = 0
        for point in rows:
            seen += point["purchases"]
            if seen > target:
                values.append(point["price_median"])
                break
    return {
        "median": sum(values) / len(values),
        "purchases": purchases,
        "hourly_buckets": len(rows),
    }


def previous_calendar_month(value):
    year = value.year
    month = value.month - 1
    if month == 0:
        year -= 1
        month = 12
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def period_summary(prices, cutoff):
    points = [
        point
        for point in prices
        if isinstance(point.get("time"), (int, float))
        and datetime.fromtimestamp(point["time"], timezone.utc) >= cutoff
    ]
    return weighted_median(points)


def search_market(client, args):
    searches = []
    for query in args.search:
        data = client.get_json(
            build_url(
                "/search/render/",
                {
                    "appid": args.appid,
                    "query": query,
                    "start": 0,
                    "count": args.search_count,
                    "norender": 1,
                    "currency": 1,
                    "country": "US",
                    "l": "english",
                },
            )
        )
        if not data.get("success"):
            raise SteamMarketError(f"Steam market search failed for {query!r}")
        searches.append(
            {
                "query": query,
                "total_count": data.get("total_count", 0),
                "matches": [
                    {
                        "market_hash_name": item.get("hash_name"),
                        "listing_count": item.get("sell_listings"),
                        "search_price": item.get("sell_price_text"),
                        "type": (item.get("asset_description") or {}).get("type"),
                    }
                    for item in data.get("results") or []
                ],
            }
        )
    return {
        "source": "Steam Community Market",
        "mode": "search",
        "appid": args.appid,
        "searches": searches,
    }


def get_price_overview(client, args, item_name):
    overview_url = build_url(
        "/priceoverview/",
        {
            "appid": args.appid,
            "currency": args.currency_id,
            "country": args.country,
            "market_hash_name": item_name,
            "l": args.language,
        },
    )
    overview = client.get_json(overview_url)
    if not overview.get("success"):
        raise SteamMarketError(f"Steam price overview failed for {item_name!r}")
    return overview


def query_current_items(client, args):
    snapshot = datetime.now(timezone.utc)
    rows = []

    for item_name in args.item:
        encoded = urllib.parse.quote(item_name, safe="")
        overview = get_price_overview(client, args, item_name)
        rows.append(
            {
                "requested_name": item_name,
                "market_name": item_name,
                "market_url": f"{MARKET_BASE_URL}/listings/{args.appid}/{encoded}",
                "current_target": parse_money(overview.get("lowest_price")),
                "current_target_text": overview.get("lowest_price"),
                "current_target_is_direct": True,
                "volume_24h": overview.get("volume"),
            }
        )

    return {
        "source": "Steam Community Market",
        "mode": "report",
        "report_scope": "current-only",
        "appid": args.appid,
        "snapshot_utc": snapshot.isoformat(),
        "currency": {
            "target_id": args.currency_id,
            "target_code": args.currency_code,
            "target_symbol": args.currency_symbol,
        },
        "items": rows,
    }


def query_items(client, args):
    if args.current_only:
        return query_current_items(client, args)

    snapshot = datetime.now(timezone.utc)
    week_start = snapshot - timedelta(days=7)
    month_start = previous_calendar_month(snapshot)
    rows = []

    for item_name in args.item:
        encoded = urllib.parse.quote(item_name, safe="")
        market_url = f"{MARKET_BASE_URL}/listings/{args.appid}/{encoded}"
        html = client.get_text(market_url + "?l=english")
        market_data = extract_ssr_market_data(html, item_name)
        overview = None
        current_target_is_direct = True
        if market_data["base_currency_id"] == args.currency_id:
            current_target = market_data["current_base"]
        elif args.exchange_rate is not None:
            current_target = (
                market_data["current_base"] * args.exchange_rate
                if market_data["current_base"] is not None
                else None
            )
            current_target_is_direct = False
        else:
            overview = get_price_overview(client, args, item_name)
            current_target = parse_money(overview.get("lowest_price"))

        rows.append(
            {
                "requested_name": item_name,
                "market_name": market_data["market_name"],
                "market_url": market_url,
                "type": market_data["type"],
                "listing_count": market_data["listing_count"],
                "base_currency_id": market_data["base_currency_id"],
                "current_base": market_data["current_base"],
                "current_target": current_target,
                "current_target_text": overview.get("lowest_price") if overview else None,
                "current_target_is_direct": current_target_is_direct,
                "volume_24h": overview.get("volume") if overview else None,
                "history_updated_at": market_data["history_updated_at"],
                "seven_day": period_summary(market_data["prices"], week_start),
                "one_month": period_summary(market_data["prices"], month_start),
            }
        )

    exchange_rate, method = resolve_exchange_rate(rows, args)
    for row in rows:
        for field in ("seven_day", "one_month"):
            summary = row[field]
            if summary:
                summary["median_base"] = summary.pop("median")
                summary["median_target"] = summary["median_base"] * exchange_rate

    base_currency_ids = sorted(
        {row["base_currency_id"] for row in rows if row["base_currency_id"] is not None}
    )
    return {
        "source": "Steam Community Market",
        "mode": "report",
        "report_scope": "current-and-history",
        "appid": args.appid,
        "snapshot_utc": snapshot.isoformat(),
        "windows": {
            "seven_day_start_utc": week_start.isoformat(),
            "one_month_start_utc": month_start.isoformat(),
        },
        "currency": {
            "target_id": args.currency_id,
            "target_code": args.currency_code,
            "target_symbol": args.currency_symbol,
            "base_ids": base_currency_ids,
            "exchange_rate": exchange_rate,
            "exchange_rate_method": method,
        },
        "items": rows,
        "historical_prices_are_approximate": True,
    }


def resolve_exchange_rate(rows, args):
    if args.exchange_rate is not None:
        return args.exchange_rate, "user-provided"

    base_currencies = {
        row["base_currency_id"] for row in rows if row["base_currency_id"] is not None
    }
    if len(base_currencies) != 1:
        raise SteamMarketError(
            "Steam returned multiple history currencies; provide --exchange-rate"
        )
    base_currency = next(iter(base_currencies))
    if base_currency == args.currency_id:
        return 1.0, "history-already-in-target-currency"
    if base_currency != 1:
        raise SteamMarketError(
            f"Cannot infer conversion from Steam currency {base_currency}; "
            "provide --exchange-rate"
        )

    pairs = [
        row
        for row in rows
        if row["current_base"]
        and row["current_target"]
        and row["current_base"] > 0
        and row["current_target"] > 0
    ]
    if not pairs:
        raise SteamMarketError(
            "Cannot infer a target-currency exchange rate without active listings; "
            "provide --exchange-rate"
        )
    target_total = sum(row["current_target"] for row in pairs)
    base_total = sum(row["current_base"] for row in pairs)
    return target_total / base_total, "implied-by-current-steam-prices"


def markdown_escape(value):
    return str(value).replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")


def format_money(value, symbol, approximate=False):
    if value is None:
        return "—"
    prefix = "≈ " if approximate else ""
    return f"{prefix}{symbol}{value:.2f}"


def format_search_markdown(result):
    lines = [
        "| Query | Market hash name | Listings | Search price |",
        "|---|---|---|---|",
    ]
    for search in result["searches"]:
        for match in search["matches"]:
            name = markdown_escape(match["market_hash_name"] or "")
            lines.append(
                f'| {markdown_escape(search["query"])} | {name} | '
                f'{match["listing_count"] if match["listing_count"] is not None else "—"} | '
                f'{match["search_price"] or "—"} |'
            )
    return "\n".join(lines)


def format_report_markdown(result):
    symbol = result["currency"]["target_symbol"]
    current_only = result.get("report_scope") == "current-only"
    if current_only:
        lines = [
            "| Name | Current lowest |",
            "|---|---|",
        ]
        for item in result["items"]:
            linked_name = (
                f'[{markdown_escape(item["market_name"])}]({item["market_url"]})'
            )
            current_lowest = format_money(
                item["current_target"],
                symbol,
                not item["current_target_is_direct"],
            )
            lines.append(f"| {linked_name} | {current_lowest} |")
        lines.extend(
            [
                "",
                f'Source: Steam Community Market. Snapshot: `{result["snapshot_utc"]}`.',
            ]
        )
        return "\n".join(lines)

    lines = [
        "| Name | Current lowest | 7-day median | 1-month median |",
        "|---|---|---|---|",
    ]
    for item in result["items"]:
        linked_name = (
            f'[{markdown_escape(item["market_name"])}]({item["market_url"]})'
        )
        seven_day = item["seven_day"]
        one_month = item["one_month"]
        current_lowest = format_money(
            item["current_target"],
            symbol,
            not item["current_target_is_direct"],
        )
        lines.append(
            f"| {linked_name} | "
            f"{current_lowest} | "
            f'{format_money(seven_day["median_target"] if seven_day else None, symbol, True)} | '
            f'{format_money(one_month["median_target"] if one_month else None, symbol, True)} |'
        )
    lines.extend(
        [
            "",
            f'Source: Steam Community Market. Snapshot: `{result["snapshot_utc"]}`.',
            "Historical values are approximate volume-weighted medians of hourly data.",
        ]
    )
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Query Steam Community Market prices with optional historical medians."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--item",
        action="append",
        metavar="MARKET_HASH_NAME",
        help="Exact market hash name. Repeat for multiple items.",
    )
    mode.add_argument(
        "--search",
        action="append",
        metavar="QUERY",
        help="Search query. Repeat for multiple searches.",
    )
    parser.add_argument("--appid", type=int, default=570, help="Steam app ID.")
    parser.add_argument("--currency-id", type=int, default=23, help="Steam currency ID.")
    parser.add_argument("--country", default="CN", help="Two-letter market country code.")
    parser.add_argument("--language", default="schinese", help="Steam language name.")
    parser.add_argument("--currency-code", default="CNY", help="Output currency code.")
    parser.add_argument("--currency-symbol", default="¥", help="Output currency symbol.")
    parser.add_argument(
        "--current-only",
        action="store_true",
        help="Query current lowest prices without fetching historical data.",
    )
    parser.add_argument(
        "--exchange-rate",
        type=float,
        help="Target units per history-currency unit; overrides inference.",
    )
    parser.add_argument(
        "--search-count",
        type=int,
        default=100,
        help="Maximum matches per search, from 1 to 100.",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=2.0,
        help="Minimum seconds between Steam requests.",
    )
    parser.add_argument("--retries", type=int, default=2, help="Retry count for 429/5xx errors.")
    parser.add_argument("--timeout", type=float, default=30, help="Request timeout in seconds.")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format.",
    )
    args = parser.parse_args()

    if args.appid <= 0:
        parser.error("--appid must be positive")
    if args.currency_id <= 0:
        parser.error("--currency-id must be positive")
    if args.exchange_rate is not None and args.exchange_rate <= 0:
        parser.error("--exchange-rate must be positive")
    if args.search and args.current_only:
        parser.error("--current-only can only be used with --item")
    if args.current_only and args.exchange_rate is not None:
        parser.error("--exchange-rate cannot be used with --current-only")
    if not 1 <= args.search_count <= 100:
        parser.error("--search-count must be between 1 and 100")
    if args.request_delay < 0 or args.retries < 0 or args.timeout <= 0:
        parser.error("delay and retries must be non-negative; timeout must be positive")
    return args


def main():
    args = parse_args()
    client = SteamMarketClient(args.request_delay, args.retries, args.timeout)
    try:
        result = search_market(client, args) if args.search else query_items(client, args)
    except SteamMarketError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.format == "json":
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    elif result["mode"] == "search":
        print(format_search_markdown(result))
    else:
        print(format_report_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
