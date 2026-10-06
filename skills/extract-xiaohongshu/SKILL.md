---
name: extract-xiaohongshu
description: Extract a Xiaohongshu (XHS or 小红书) note's content and requested media using EMMMM for media discovery, with original-file verification. Use for full-note extraction, text-only requests, or selected original media without creating a Markdown archive.
---

# Extract Xiaohongshu

Read the supplied note link and return its content and requested original media. Accept `xiaohongshu.com/explore/<note_id>`, `xiaohongshu.com/discovery/item/<note_id>`, and `xhslink.cn` / `xhslink.com` short links, with or without share parameters.

Never attempt login or ask the user to log in: no sign-in clicks, QR scans, credential/SMS requests, account-cookie imports, or authenticated-profile switching. A login prompt does not prevent extraction when the public note data is already loaded.

## Workflow

1. For a media request, submit the complete supplied URL to the [EMMMM Xiaohongshu tool](https://tools.emmmm.dev/xiaohongshu) through its anonymous parser below, with a 25-second timeout. Send only the note URL, preserving all share parameters; let EMMMM expand short links. Do not first open the note in a browser or send account cookies, credentials, or surrounding conversation content. Serialize the request body as JSON rather than interpolating the URL into shell code. For a text-only request, skip the parser and read the supplied URL in step 3.

   ```http
   POST https://tools.emmmm.dev/xiaohongshu/api/parser
   Content-Type: application/json

   {"share":"<complete-user-provided-url>"}
   ```

2. Require `code: 0`, a string `title`, a supported Xiaohongshu note URL in `realUrl`, and ordered string arrays `imgList` and `videoList`. Extract `note_id` from `realUrl`; if the input already contains a note ID, reject a mismatch. Preserve an empty title and every media URL exactly, including transformation parameters and signatures. These URLs are candidates, not verified originals. Empty arrays mean the parser found no candidates, not that the note has no media. A failed, gated, or malformed parser response is `blocked`; report the reason without switching providers or requesting login. If its interface changes, inspect the tool's current public UI before adapting the request; do not guess endpoints.
3. EMMMM supplies the title, resolved note URL, and media candidates; it does not establish author, publication time, body, tags, note type, media roles, or original-file provenance. Only when requested fields or verification evidence are missing, open the resolved note URL (or the supplied URL for text-only extraction) once in an unauthenticated Chrome-based browser, preserving share parameters and normal short-link redirects. Allow up to 30 seconds for matching note data without waiting for full-page loading or network idle. Read the already-loaded state below, cross-checking its ID against the resolved path and EMMMM's `note_id` when present. A valid note must contain body or media data; an empty title is valid. Do not scrape page chrome or execute downloaded page scripts to parse HTML. If the page is blocked, retain any parser result and report unresolved requested fields or originals as `partial`; use `blocked` if no note data was retrieved. Missing fields are not confirmed absent.

   ```javascript
   (() => {
     const id = location.pathname.match(/^\/(?:explore|discovery\/item)\/([^/]+)\/?$/)?.[1];
     const note = window.__INITIAL_STATE__?.note?.noteDetailMap?.[id]?.note;
     if (!id || !note || note.noteId !== id) return null;
     if (!note.desc && !note.imageList?.length && !note.video) return null;
     return {
       noteId: note.noteId, type: note.type, title: note.title,
       user: {userId: note.user?.userId, nickname: note.user?.nickname},
       time: note.time, desc: note.desc, tagList: note.tagList,
       imageList: note.imageList, video: note.video
     };
   })()
   ```

4. Verify the requested EMMMM media candidates as below and return the result. A whole-note request includes all metadata and media; a text-only request needs no media downloads. Preserve `imgList` / `videoList` order and use 1-based indices; cross-check against source `imageList` / video metadata when available. For a selected image, verify only that item and report an ambiguous source-index mapping rather than choosing a different image. Close any browser opened for extraction on completion or failure.

## Original media

- **Images:** fetch the selected `imgList` URL unchanged after checking that it is a public HTTP(S) media address; prefer returned platform CDN links and disclose any intermediary. Do not rebuild CDN URLs from paths or remove transformation parameters to claim an original. Read `file_id` only from matching source metadata when available; otherwise use `null`.
- **Verification:** decode the returned bytes, confirm asset identity and dimensions against source metadata (accounting for orientation), and inspect for platform-added watermarks or cropping. Detect the actual format: a response labeled `image/jpeg` may contain HEIC. Keep the retrieved format and disclose viewer limitations; preserve watermarks authored into the original. Accessibility, absence of platform watermarks, and original-file provenance are separate findings. EMMMM's success flag or advertised original quality is not provenance evidence; URLs containing transformations such as `imageView2/2/w/6000/h/6000/format/jpg&redImage/frame/0` must not be presented as proven unchanged source files. Failed retrieval or insufficient source evidence leaves the original unavailable/unverified rather than triggering another retrieval route.
- **Video:** fetch/probe the selected `videoList` candidate to verify its actual container, identity, and source properties. Cross-check against `note.video` metadata when available, parsing `mediaV2` as JSON when needed or reading `media` where provided. Mark a URL as original only when source evidence identifies it as such; a `master_url`/`masterUrl` label, high resolution, or high bitrate alone is not proof. If only playback transcodes are exposed, report that no original was established instead of returning a transcode as the original.
- **Posters and Live Photos:** when source metadata identifies a video note, its `imageList[0]` is its poster, not the video. EMMMM's separate arrays alone do not prove roles or pairings; use `null` for an unknown role and report the limitation. Keep confirmed Live Photo still/video components as separate records sharing the source image index. A request for the full Live Photo requires both; a request for only its still image does not.
- Preserve required media URL signatures and query parameters. Original means the platform's source asset; byte identity with the author's pre-upload file requires that file for comparison.

## Result

Keep raw source text unchanged: no tag removal, typography changes, translation, or implicit OCR. Read tags from `tagList` and explicit topic markers/links, retain first-seen order, and deduplicate by ID or exact name. Literal `#` in code or URLs is not a topic tag.

| Field | Value |
| - | - |
| `note_id`, `note_type` | ID from EMMMM's `realUrl` or `note.noteId` for text-only extraction, cross-checked when both are available; `note.type` or `null` |
| `canonical_url` | `https://www.xiaohongshu.com/explore/<note_id>` without share parameters |
| `title` | Exact `note.title` when available, otherwise EMMMM's `title`, including an empty string |
| `author` | `{id, name}` from `user.userId` and `user.nickname` |
| `published_at_ms` | `note.time` in Unix milliseconds |
| `body_raw` | Exact `note.desc`, including topic markers and line breaks |
| `tags` | Ordered `{id, name, source}` records; source is `tagList`, `body_marker`, or `topic_link` |
| `scope.fields`, `scope.media` | Requested fields; media is `all`, `none`, or a selection such as `{"image_indices":[3],"video":false,"poster":false}` |
| `media` | Requested media records in source order |
| `status`, `issues` | `complete`, `partial`, or `blocked`, plus specific limitations |

Each media record contains `kind` (`image`/`video`), `role` (`content`/`poster`/`live_photo`), source `index`, `file_id`, `original_url`, `original_status`, actual `format`, `mime_type`, `width`, `height`, and brief `verification` evidence. The main note video is index 1. Set `original_status` to `verified`, `unavailable`, or `unverified`; `original_url` must be `null` unless verified.

Always return identity, scope, status, and issues; include other fields only when requested. Use `null` for absent or unknown values, preserving genuinely empty strings and arrays. Metadata missing from EMMMM is unknown, not confirmed absent; an empty parser media array does not establish source completeness. `complete` requires every requested field to be extracted or confirmed absent and every requested original to be verified. Use `partial` for unresolved requested items and `blocked` when the note cannot be retrieved or identified; unrequested media does not affect completion. Exclude note share tokens from the result.

Return content and verified links by default. For requested files, deliver the unchanged original bytes with the correct extension through the environment's file-sharing mechanism; temporary files stay outside the archive repository. This skill creates no Markdown archive or Git changes. The calling archive skill owns formatting, translation, deduplication, and saving.
