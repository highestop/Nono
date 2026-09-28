---
name: github-dashboard-items
description: List the authenticated user's open authored and assigned pull requests and created and assigned issues, matching GitHub's four personal dashboards. Use for a grouped personal GitHub work list or requests referencing those dashboard URLs.
---

# GitHub Dashboard Items

The four signed-in GitHub dashboards below are the acceptance target. Each group must contain the same open items as its corresponding dashboard for the same account and repository access. Reproduce the dashboards' scope, including exclusion of archived repositories; a broader search of the user's history is not equivalent.

| Group, in output order | Canonical dashboard | API search query |
| --- | --- | --- |
| PR · Authored by me | https://github.com/pulls/authored | `is:pr is:open author:{login} archived:false` |
| PR · Assigned to me | https://github.com/pulls/assigned | `is:pr is:open assignee:{login} archived:false` |
| Issue · Created by me | https://github.com/issues/created | `is:issue is:open author:{login} archived:false` |
| Issue · Assigned to me | https://github.com/issues/assigned | `is:issue is:open assignee:{login} archived:false` |

- Resolve `{login}` from the authenticated account, not from a repository owner or a previous report.
- Query across all repositories accessible to that account, including other owners and organizations. Do not add `user:`, `org:`, or `repo:` restrictions unless requested.
- `Assigned to me` means `assignee:`, not review requests, mentions, or participation.
- Keep open draft PRs. Exclude closed issues, closed PRs, merged PRs, and items in archived repositories.
- Keep overlapping memberships: an item created by and assigned to the user appears in both relevant groups.

## Query

1. Verify authentication with `gh auth status` and identify the account with `gh api user --jq '.login'`.
2. Run each query from the table through GitHub's authenticated search API. The example uses `gh` and `jq` for the first group; substitute each remaining query without changing its scope.

   ```bash
   set -euo pipefail
   github_login="$(gh api user --jq '.login')"
   dashboard_query="is:pr is:open author:${github_login} archived:false"
   gh api --method GET search/issues \
     -f q="$dashboard_query" \
     -f per_page=100 \
     --paginate --slurp | \
     jq '{total_count: .[0].total_count, incomplete_results: any(.[]; .incomplete_results), items: [.[].items[] | {id, number, title, html_url, repository_url, state}]}'
   ```

3. Read every page. Verify `incomplete_results` is false, all returned states are `open`, and the unique item count matches `total_count`. Remove duplicates only within a group. GitHub search exposes at most 1,000 results per query; if needed, retrieve disjoint creation-date ranges and combine their complete results without changing the overall time scope. Do not silently impose a date window or a latest-N limit.
4. If a signed-in browser is available, compare the corresponding dashboard's Open results, scope, and ordering. If the page differs, check account identity, authorization coverage, filters, pagination, and recent changes before adjusting the API query. The dashboard's Open view is authoritative; do not silently broaden the result set.
5. When using only the API, describe the result as an API reproduction of the dashboard filters. Do not claim to have inspected the logged-in pages. Report access errors or incomplete results as limitations, not as empty groups or exact page parity.

## Output

- Respond in the user's language, directly in chat unless another destination is requested. Identify the account and query time once.
- Always show the four groups in the table's order. Link each group label to its exact canonical dashboard URL and show its item count. For an empty group, state `0` or the equivalent of `None`.
- For each nonempty group, use exactly two table columns: repository / item link, and title. Display the full `owner/repo` and item number in the link label, linking to the API's `html_url`. Derive the repository from `repository_url` or the item URL rather than assuming ownership.
- Preserve the complete original title, escaping Markdown table delimiters and normalizing embedded line breaks for display. Match dashboard ordering when it is available.
- Do not include a status column, status badges, or repeated `Open` labels: every listed item is already open. Do not include historical closed or merged totals.

Example row shape, with placeholders replaced by live data:

| Repository / item | Title |
| --- | --- |
| [owner/repo #123](https://github.com/owner/repo/issues/123) | Original issue title |
