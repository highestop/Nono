---
name: extract-wechat
description: Extract a WeChat Official Account (微信公众号) article's title, author, account, publication time, body, and selected original images from an mp.weixin.qq.com link. Use for full-article extraction, text-only requests, or individual original images without creating a Markdown archive.
---

# Extract WeChat

Return source content and requested original media independently of archiving. Accept `https://mp.weixin.qq.com/s/<short_id>` and article links with `__biz`, `mid`, `idx`, and `sn` parameters. Preserve the complete input URL for fetching; a long link may be inaccessible even when a short link works.

## Workflow

1. Make one direct request to the supplied WeChat URL using the command below. Build `fetch_url` by adding `scene=1` only when `scene` is absent, before any fragment; preserve existing parameters. Keep temporary HTML outside the archive repository. This is the sole fetching route: no browser, login, account cookies, verification clicks, mirrors, or retry sequence.

   ```bash
   curl -4 -f -sS -L --compressed --max-time 45 \
     -A 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 MicroMessenger/8.0.54' \
     -H 'Accept-Language: zh-CN,zh;q=0.9' \
     '<fetch_url>' -o '<temporary_html_path>'
   ```

2. Require a successful, complete transfer and parse the HTML without executing page scripts. Require an article title and a non-empty `#js_content` containing text or content media; cross-check its account, publication metadata, and identity with the supplied link. HTTP `200` is insufficient: a verification page such as `mmbizwap:secitptpage/verify.html` without article content is `blocked`. Deleted, inaccessible, or unidentified articles are also `blocked`; an identified article with only a paid/truncated preview is `partial`, never a complete body.
3. Extract the requested fields below and verify only the requested media. A whole-article request includes all metadata, the complete body, and all content media. A text-only request downloads no media. Image selections use 1-based `<img>` positions inside `#js_content`, including repeated occurrences; account avatars and page controls outside that body do not count. Return results without creating an archive.

## Source fields

Read all of `#js_content`, not just its first child. Preserve the body HTML, text, punctuation, links, headings, code, tables, captions, and media order. Do not summarize, translate, remove author-written recommendations/QR codes, adjust typography, or perform implicit OCR. Page controls and comments outside the article body are excluded naturally.

| Field | Source |
| - | - |
| `identity` | `{short_id, biz, mid, idx, sn}` from the resolved article URL and literal page variables; cross-check available values |
| `article_id` | `biz:mid:idx` when all three exist, otherwise `short:<short_id>`; never use a request token as an ID |
| `canonical_url` | Static short article URL from the resolved URL, `og:url`, or literal `msg_link` when verified; otherwise the public article URL retaining identity/access parameters. Omit fetch-only `scene=1`, fragments, and session credentials |
| `title` | `#activity-name` text or `meta[property="og:title"]` |
| `author` | `#js_author_name` or an explicitly identified author field; `null` when absent, not the account name |
| `account` | `{id, name}` from `biz` and `#js_name` / literal `nickname` |
| `published_at_ms`, `published_at_text` | Literal `ct` or `create_time` Unix seconds multiplied by 1000; retain an explicit DOM date as text when no timestamp exists, leaving milliseconds `null` |
| `body_html` | Complete `#js_content` subtree, retaining original media attributes |
| `body_text` | Text from that subtree, preserving paragraph and code line breaks; image text requires an explicit OCR request |
| `scope.fields`, `scope.media` | Requested fields; media is `all`, `none`, or `{"image_indices":[3]}` |
| `media` | Requested source media records in body order |
| `status`, `issues` | `complete`, `partial`, or `blocked`, with specific missing content or verification limits |

Decode HTML entities and quoted metadata values as data. Do not run wrappers such as `htmlDecode(...)` or `.html(false)` from downloaded scripts. Trim only surrounding metadata whitespace; preserve the source wording. Always return `identity`, `article_id`, `canonical_url`, scope, status, and issues; include other fields only when requested and use `null` for unknown values.

## Original media

- Locate each image through `data-src`, or a non-placeholder `src`. Prefer an explicit original such as `data-croporisrc` on the same source element. Otherwise, for a recognized `mmbiz.qpic.cn` article-image URL under `/mmbiz/` or `/mmbiz_*/`, replace only its final numeric size segment, such as `/640`, with `/0`. Preserve the host, asset ID, format, and required query parameters. This selects one candidate from source metadata; do not cycle through hosts or strip arbitrary parameters. Other hosts need explicit original-asset evidence.
- Fetch and decode the candidate before setting `original_url`. Confirm the asset identity, actual format, full dimensions, and absence of platform-added watermarking or derivative cropping. `data-w` and `data-ratio` may describe a capped or cropped display, not the original dimensions: a valid original can exceed `data-w`. Keep evidence from original-source attributes and decoded bytes; URL shape, HTTP success, or dimensions alone are insufficient.
- Preserve original bytes, animation, and author-created watermarks. Do not convert formats, reduce dimensions, remove authored marks, or rehost files for preview compatibility. “Original” means the platform's source asset, not proven byte identity with the author's pre-upload file.
- Keep article video, audio, and other media embeds at their body positions. A player URL, poster, or screenshot is not an original media file; unresolved requested originals must remain explicit partial results rather than silently disappearing.

Each media record contains `kind`, `role` (`content`/`poster`), `index` (1-based within that media kind), `source_url`, `original_url`, `original_status`, actual `format`, `mime_type`, `width`, `height`, and brief `verification` evidence. Retain source attributes needed to locate the occurrence and explain provenance. `original_status` is `verified`, `unavailable`, or `unverified`; `original_url` is `null` unless verified.

`complete` requires every requested field to be extracted or confirmed absent, a complete body when requested, and every requested original to be verified. Use `partial` for unresolved requested items and `blocked` when the article cannot be retrieved or identified. Unrequested media does not block text-only or selected-image requests. Never substitute a preview for an unresolved original.

Return the requested content and verified links by default; a JSON file is unnecessary for a direct user request. When files are requested, deliver unchanged originals with their detected extensions through the environment's file-sharing mechanism. Temporary inspection files stay outside the archive repository. This skill creates no Markdown archive, translation, commit, or pull request; the caller owns those actions.
