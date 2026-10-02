---
name: dota2-replay-manager
description: Inspect and safely manage locally downloaded Dota 2 replay files on macOS. Use for locating `.dem` files, listing file and match metadata, identifying tournament replays, reading local replay titles, or changing an existing local replay title with a backup.
---

# Dota 2 replay management on macOS

## Scope and safety

- This skill applies to the macOS Steam installation of Dota 2.
- A replay's match content is in its `.dem` file; its display title is stored separately in Dota's local download index. Do not rename a `.dem` file merely to change its display title.
- File deletion and title writes require the user's explicit approval. Before any title write, create and report a timestamped backup of the `.dat` index.
- A Steam/Dota sync or a replay re-download can replace local titles. Treat titles as local annotations, not durable match metadata.
- Do not embed or commit local match IDs, Steam account IDs, player names, replay titles, timestamps, screenshots, index files, or backups. Use placeholders in skill documentation and test only on temporary copies.

## Locations

| Purpose | Path |
|---|---|
| Downloaded replay files | `~/Library/Application Support/Steam/steamapps/common/dota 2 beta/game/dota/replays/` |
| Per-account replay index | `~/Library/Application Support/Steam/userdata/<steam-account-id>/570/remote/cfg/downloaded_replays_info.dat` |
| Pending replay downloads | `~/Library/Application Support/Steam/userdata/<steam-account-id>/570/remote/cfg/pending_replay_requests.lst` |

- Each `.dem` filename is normally its decimal Dota 2 match ID, for example `<match-id>.dem`.
- Do not assume one Steam account. Discover every matching `userdata/<steam-account-id>/.../downloaded_replays_info.dat` file and associate an index only after it contains the relevant match ID.
- Ignore `placeholder.txt` and `.DS_Store` in the replay directory.

## Inspect replay files

1. List `.dem` files, sorted by modification time. Treat the modification time as the local download/save time, not necessarily match start time.
2. Record the exact filename, byte size, and modification timestamp with `stat`.
3. Convert the basename without `.dem` to a match ID.
4. For match information, request `https://api.opendota.com/api/matches/<match-id>` and report only fields actually returned:
   - Match start time, duration, game mode, lobby type, winner, score, and player/hero data.
   - `leagueid`, series ID/type, team names, and tournament data when present.
5. `leagueid: 0` means there is no ticketed league record in the response. Describe it as a public match with its available mode/lobby information; do not invent a tournament name.
6. For tournament series, group maps by `series_id`. Infer a game number only from chronological order and state that it is an inference unless the data explicitly provides `series_game`.

Use the user's local timezone for all user-facing timestamps. Keep match start time and file modification time in separate columns or fields.

## Read local replay titles and index metadata

`downloaded_replays_info.dat` is a Valve Binary KeyValues (`VBKV`) file. It contains `download<N>` records. Useful fields include:

- `match.match_id`, `start_time`, `duration`, `game_mode`, `players`, `match_outcome`, `radiant_score`, `dire_score`, `lobby_type`, `is_player_draft`.
- Per-player `account_id`, `hero_id`, K/D/A, item IDs, slot, `pro_name`, level, and team number.
- `title`, `size`, and `exists_on_disk`.
- For tournament records, `tourney` fields may include league, series, game, and team identifiers/names.

Run the bundled helper to map match IDs to stored titles:

```bash
node ./replay_notes.js list "<downloaded_replays_info.dat>"
```

The helper validates the `VBKV` CRC-32 header before reading. A match can remain in the index after its `.dem` was deleted, and a `.dem` can lack an index entry; report these as separate states.

## Change a local replay title

Only change a title after the user supplies the exact match ID and new title. First show the current title and the target title. Then run:

```bash
node ./replay_notes.js title "<downloaded_replays_info.dat>" <match-id> "<new-title>" --write
```

- Without `--write`, the command is a dry run.
- With `--write`, it writes a sibling backup named `downloaded_replays_info.dat.bak-<timestamp>` before changing the file and recomputes the `VBKV` checksum.
- The helper modifies only an existing `title` field. If a record has no title, do not hand-edit the binary file; explain the limitation and offer to use the Dota client to create an initial title.
- Re-run `list` after a write and report the updated title and backup path.

## Deletion workflow

1. Resolve the exact `.dem` paths and display their titles, match IDs, sizes, and total space to be recovered.
2. Delete only the user-approved paths.
3. Verify that each target no longer exists. Do not modify the `.dat` index unless the user separately asks to remove local index records.
