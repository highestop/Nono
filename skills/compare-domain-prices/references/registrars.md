# Registrar lookup guidance

These are discovery entry points, not stored prices. Inspect the current page and its terms on each run; interfaces and promotions can change. Start with available public HTTP or browser tools. If one route is blocked, try another ordinary public source once, then mark the gap instead of looping or bypassing an access challenge.

## Cloudflare Registrar

- Start at [Cloudflare Domains](https://www.cloudflare.com/domains/) or its [domain search](https://www.cloudflare.com/domains/search). Search the complete domain. Use official registration and renewal quotes when the search is available.
- If public search fails, [Cloudflare Domain Pricing](https://cfdomainpricing.com/) is a **third-party** fallback for suffix reference prices. Record its update date and source; never describe it as Cloudflare's official price list or confirmation that the exact name is available.
- The [official Registrar API documentation](https://developers.cloudflare.com/registrar/registrar-api/) describes account-based search and checks. Use an already authorized connection only when it supports these read-only queries. Cached search suggestions and documentation sample prices are not confirmed offers. An extension unsupported by an API does not necessarily mean the dashboard cannot register it. Do not call registration or transfer mutation endpoints.
- Separate a supported extension, a reference price, and a registrable exact name. None proves the other two.

## Dynadot

- Use [bulk domain search](https://www.dynadot.com/domain/bulk-search) for the current watchlist. Select **Exact Search**, paste complete domains one per line, and verify the returned names. The alternative suffix-filter mode can search different names.
- Inspect the rendered results after they finish loading. Registration and renewal can appear in a different order; read the labels instead of assuming the first number is the initial fee. Confirm that the currency is USD.
- Read the relevant official extension page for sale terms, crossed-out regular renewal prices, and multi-year discounts. A bundle price may differ from adding today's registration and future renewal prices; record the bundle as a separate purchase plan only when its exact total and eligibility are verified.
- Loading placeholders, suggested alternatives, auctions, and premium listings are not ordinary available-domain quotes. Use fresh browser references after dialogs or layout changes.

## Porkbun

- Start with the official [domain pricing table](https://porkbun.com/products/domains), then check exact-domain availability through the site's search. The table normally quotes standard non-premium suffix prices; it does not prove a particular watched name qualifies.
- Public HTML may expose `data-extension`, `data-price-registration`, and `data-price-renewal` on pricing rows. These numeric price attributes have been expressed in **cents**; verify their scale against a visible row before converting them. Read visible sale labels and terms as well as data attributes.
- Distinguish registration, renewal, and transfer columns. Check the current fee-inclusion statement rather than adding ICANN fees a second time.
- Search results may initially contain pending placeholders. Wait for completed availability checks; do not infer availability from a prefilled domain or an “add” element on a loading row.
- Check the official [`.ai` terms](https://porkbun.com/tld/ai) for minimum registration and renewal periods. Verify the equivalent restriction at each other registrar instead of extrapolating a one-year checkout from an annual advertisement.

## Evidence and promotion notes

- Retain exact-domain evidence separately from suffix price references. A WHOIS/RDAP result can help identify registered names, but an absent record does not rule out a reserved or premium name.
- Capture the advertised price, whether it is per year or a total, minimum term, current renewal fee, normal renewal fee if shown, applicable coupon or account conditions, and sale end date if published.
- If a future renewal is advertised at a temporary sale price, use the observed price only as a provisional projection and explain its effect on the recommendation. Do not treat it as a contract for future renewals.
- Do not fabricate a promotion expiry, tax amount, availability result, or checkout total when a page does not expose it. Preserve useful results from the other registrars and label the incomplete comparison.
