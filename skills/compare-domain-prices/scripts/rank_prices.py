#!/usr/bin/env python3
"""Render researched domain offers; Python 3.9+, standard library, no network."""

import argparse
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


REGISTRARS = ("Cloudflare", "Dynadot", "Porkbun")
STATUSES = {"available", "reference", "registered", "aftermarket", "unsupported", "unknown"}
HORIZON = 3
DEFAULT_WATCHLIST = Path(__file__).resolve().parents[1] / "domains.txt"


def normalize_domain(value):
    name = value.strip().lower().rstrip(".").encode("idna").decode("ascii")
    labels = name.split(".")
    if len(name) > 253 or len(labels) < 2 or labels[-1].isdigit() or any(
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in labels
    ):
        raise ValueError("expected a complete domain name without a URL, wildcard, or path")
    return name


def read_watchlist(path):
    domains, errors = [], []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            name = normalize_domain(line)
        except (UnicodeError, ValueError) as exc:
            errors.append(f"第 {number} 行：{line.strip()}（{exc}）")
            continue
        if name not in domains:
            domains.append(name)
    return domains, errors


def term(value):
    if not isinstance(value, dict) or set(value) != {"usd", "years"}:
        raise ValueError("a price term must contain usd and years")
    years = value["years"]
    if type(years) is not int or years < 1:
        raise ValueError("years must be a positive integer")
    try:
        amount = Decimal(str(value["usd"]))
    except InvalidOperation as exc:
        raise ValueError("usd must be a decimal amount") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("usd must be finite and nonnegative")
    return amount, years


def annual(value):
    amount, years = term(value)
    return amount / years


def money(amount):
    return f"${amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def price(amount):
    icon = "🟢" if amount <= 10 else "🟡" if amount <= 20 else "🔴"
    return f"{icon} {money(amount)}"


def score(offer):
    registration, years = term(offer["registration"])
    renewal, renewal_years = term(offer["renewal"])
    return registration * min(years, HORIZON) / years + renewal * max(
        0, HORIZON - years
    ) / renewal_years


def eligible(offer):
    return offer["status"] in {"available", "reference"} and all(
        offer.get(key) is not None for key in ("registration", "renewal")
    )


def validate_quotes(data, domains):
    if data.get("currency") != "USD":
        raise ValueError("quotes must use USD; do not mix currencies")
    stamp = datetime.fromisoformat(str(data.get("checked_at", "")).replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("checked_at must include a timezone")
    if not isinstance(data.get("offers"), list):
        raise ValueError("offers must be a list")
    offers = []
    for raw in data["offers"]:
        if not isinstance(raw, dict):
            raise ValueError("each offer must be an object")
        offer = dict(raw)
        offer["domain"] = normalize_domain(offer.get("domain", ""))
        if offer["domain"] not in domains:
            continue  # Edits to the watchlist immediately remove stale observations.
        if offer.get("registrar") not in REGISTRARS or offer.get("status") not in STATUSES:
            raise ValueError("unrecognized registrar or offer status")
        sources = offer.get("sources")
        if not isinstance(sources, list) or not sources or any(
            not isinstance(url, str) or urlsplit(url).scheme not in {"http", "https"}
            or not urlsplit(url).netloc for url in sources
        ):
            raise ValueError("each offer needs at least one HTTP(S) source URL")
        if not isinstance(offer.get("notes", ""), str):
            raise ValueError("notes must be text")
        for key in ("registration", "renewal", "renewal_regular"):
            if offer.get(key) is not None:
                term(offer[key])
        offers.append(offer)
    return offers


def cell(value):
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render(domains, errors, data):
    offers = validate_quotes(data, domains)
    source_urls = list(dict.fromkeys(url for offer in offers for url in offer["sources"]))
    rows = []
    status_labels = {
        "registered": "已注册", "aftermarket": "二级市场报价", "unsupported": "不支持",
        "unknown": "未核实", "available": "报价不完整", "reference": "参考价不完整",
    }
    for domain in domains:
        current = [offer for offer in offers if offer["domain"] == domain]
        blocked = any(offer["status"] in {"registered", "aftermarket"} for offer in current)
        candidates = [] if blocked else [offer for offer in current if eligible(offer)]
        gaps = [registrar for registrar in REGISTRARS if not any(
            offer["registrar"] == registrar and (
                eligible(offer) or offer["status"] == "unsupported"
            ) for offer in current
        )]
        notes = []
        if candidates:
            winner = min(candidates, key=lambda offer: (
                score(offer), annual(offer["renewal"]), term(offer["registration"])[0],
                offer["registrar"], offer["status"] != "available",
            ))
            ranking_score = score(winner)
            provider = winner["registrar"]
            if winner["status"] == "reference":
                provider += "（参考）"
                notes.append("仅参考价，未确认该域名适用")
            if gaps or any(offer["status"] == "reference" for offer in candidates):
                notes.append("暂定推荐")
            notes.append(winner.get("notes", ""))
            totals = [winner["registration"], winner["renewal"]]
            register_total, register_years = term(totals[0])
            renew_total, renew_years = term(totals[1])
            if register_years > 1:
                notes.append(f"注册需购 {register_years} 年，首次支付 {money(register_total)}；首列为年均价")
            if renew_years > 1:
                notes.append(f"续费每 {renew_years} 年 {money(renew_total)}")
            remaining = max(0, HORIZON - register_years)
            paid_years = register_years + ((remaining + renew_years - 1) // renew_years) * renew_years
            if paid_years > HORIZON:
                notes.append(f"使用至第 {HORIZON} 年需付至第 {paid_years} 年")
            if winner.get("renewal_regular") is not None:
                normal = annual(winner["renewal_regular"])
                if normal > annual(winner["renewal"]):
                    notes.append(f"续费促销；页面常规价 {price(normal)} / 年，恢复后排序可能变化")
            tied = sorted({offer["registrar"] for offer in candidates if (
                score(offer) == ranking_score and offer["registrar"] != winner["registrar"]
            )})
            if tied:
                notes.append("折算成本并列：" + "、".join(tied))
            notes.extend(f"{offer['registrar']} 不支持" for offer in current if offer["status"] == "unsupported")
            prices = " / ".join(price(annual(value)) for value in totals)
        else:
            ranking_score, provider, prices = None, "—", "— / —"
            for offer in current:
                label = "普通注册报价未参与排名" if blocked and eligible(offer) else status_labels[offer["status"]]
                notes.append(f"{offer['registrar']}：{label}")
                notes.append(offer.get("notes", ""))
        if gaps:
            notes.append("比较未完成：" + "、".join(gaps))
        linked_sources = sorted({source_urls.index(url) + 1 for offer in current for url in offer["sources"]})
        if linked_sources:
            notes.append("来源 " + " ".join(f"[{number}]" for number in linked_sources))
        rows.append((ranking_score, domain, provider, prices, "；".join(dict.fromkeys(n for n in notes if n))))
    rows.sort(key=lambda row: (row[0] is None, row[0] or Decimal(0), row[1]))
    lines = [
        f"查询时间：{data['checked_at']}。币种：USD；按页面报价，所在地税费另行核实。",
        "排序参考三年持有成本：普通年度方案为首年注册费 + 2 次年续费；多年方案按覆盖年限折算，假设当前价格不变。",
        "🟢 ≤ $10；🟡 > $10 且 ≤ $20；🔴 > $20。颜色对应单年价格。",
        "", "| 排名 | 域名 | 较省渠道 | 首年 / 年续费（USD） | 备注 |",
        "|---|---|---|---|---|",
    ]
    rank = 0
    for ranking_score, domain, provider, prices, notes in rows:
        if ranking_score is not None:
            rank += 1
        values = [str(rank) if ranking_score is not None else "—", f"`{domain}`", provider, prices, notes or "—"]
        lines.append("| " + " | ".join(cell(value) for value in values) + " |")
    if source_urls:
        lines.append("")
        lines.extend(f"[{number}]: <{url}>" for number, url in enumerate(source_urls, 1))
    if errors:
        lines.extend(["", "未查询的无效清单行："] + [f"- {cell(error)}" for error in errors])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watchlist", type=Path, default=DEFAULT_WATCHLIST)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true", help="print normalized domains and invalid lines as JSON")
    mode.add_argument("--quotes", type=Path, help="render researched offers from a temporary JSON file")
    args = parser.parse_args()
    try:
        domains, errors = read_watchlist(args.watchlist)
        if args.list:
            print(json.dumps({"domains": domains, "invalid_lines": errors}, ensure_ascii=False, indent=2))
        if not domains:
            raise ValueError("watchlist has no valid domains; edit domains.txt before querying")
        if args.quotes:
            data = json.loads(args.quotes.read_text(encoding="utf-8"))
            print(render(domains, errors, data))
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
