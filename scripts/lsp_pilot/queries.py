"""GraphQL query strings used by the pipeline. Kept as plain constants so
fetch_pipeline.py stays readable.

IMPORTANT semantics note (verified empirically against the live API):
Repository.issues(labels: [...]) is OR/union semantics - it returns issues
carrying ANY of the given labels, not all of them. There is no AND filter
on that connection. To get a true AND (all labels present) for multi-label
combinations (TypeScript "Bug" + domain, golang "gopls" + BugReport, ...),
this pipeline either (a) filters client-side over already-fetched full
issue nodes (cheapest, used when we already hold the superset), or (b) for
cases needing a fresh targeted fetch, uses the `search` root with multiple
`label:"X"` qualifiers in the query string, which GitHub's search syntax
ANDs correctly (also verified empirically: search 'label:"C-bug"
label:"E-easy"' on rust-lang/rust-analyzer returns exactly the
inclusion-exclusion-computed intersection, 77, matching issues(labels:[...])
union math: |C-bug|=2670, |E-easy|=273, |union|=2866 => overlap=77).

Run: imported by fetch_pipeline.py / ts_pipeline.py, not run directly.
"""

# rateLimit is included in every query so we can log actual point cost
# and remaining quota without a separate request.
RATE_LIMIT_FIELD = "rateLimit { limit cost remaining resetAt }"

# Shared per-issue field selection, per task spec fields exactly:
# closedByPullRequestsReferences + timelineItems(CLOSED_EVENT).closer/actor +
# labels + createdAt/closedAt + comments totalCount + last-3 bodies (for the
# golang CL-link proxy scan) + reactions totalCount + title + body. Used
# under both `repository.issues` (single-label fetches) and `search`
# (multi-label AND fetches).
ISSUE_DETAIL_FIELDS = """
  number
  url
  title
  body
  createdAt
  closedAt
  comments(last: 3) {
    totalCount
    nodes { body url }
  }
  reactions { totalCount }
  labels(first: 20) { nodes { name } }
  closedByPullRequestsReferences(first: 10, includeClosedPrs: true) {
    nodes { number url merged mergedAt }
  }
  timelineItems(itemTypes: [CLOSED_EVENT], last: 1) {
    nodes {
      __typename
      ... on ClosedEvent {
        actor { login }
        closer {
          __typename
          ... on Commit { oid url }
          ... on PullRequest { number url merged }
        }
      }
    }
  }
"""

LABELS_QUERY = f"""
query($owner: String!, $name: String!, $cursor: String) {{
  {RATE_LIMIT_FIELD}
  repository(owner: $owner, name: $name) {{
    labels(first: 100, after: $cursor) {{
      totalCount
      pageInfo {{ hasNextPage endCursor }}
      nodes {{ name }}
    }}
  }}
}}
"""

# totalCount only - cheap, used for the total/closed funnel columns and for
# single-label counts-only (tier-7) targets. labels: null means "no label
# filter". Do NOT pass more than one label here (OR semantics - see module
# docstring); use SEARCH_COUNT_QUERY for a true multi-label AND count.
COUNTS_QUERY = f"""
query($owner: String!, $name: String!, $labels: [String!]) {{
  {RATE_LIMIT_FIELD}
  repository(owner: $owner, name: $name) {{
    allIssues: issues(labels: $labels, first: 1) {{ totalCount }}
    closedIssues: issues(states: [CLOSED], labels: $labels, first: 1) {{ totalCount }}
  }}
}}
"""

# Single-label (or no-filter) closed-issue detail page via
# repository.issues. Safe for 0 or 1 label; do not pass >1 (OR semantics).
ISSUES_PAGE_QUERY = f"""
query($owner: String!, $name: String!, $labels: [String!], $cursor: String) {{
  {RATE_LIMIT_FIELD}
  repository(owner: $owner, name: $name) {{
    issues(
      states: [CLOSED]
      labels: $labels
      first: 100
      after: $cursor
      orderBy: {{field: CREATED_AT, direction: DESC}}
    ) {{
      totalCount
      pageInfo {{ hasNextPage endCursor }}
      nodes {{
{ISSUE_DETAIL_FIELDS}
      }}
    }}
  }}
}}
"""

# True AND count via GitHub search syntax (multiple label: qualifiers).
SEARCH_COUNT_QUERY = f"""
query($q: String!) {{
  {RATE_LIMIT_FIELD}
  search(query: $q, type: ISSUE, first: 1) {{ issueCount }}
}}
"""

# True AND closed-issue detail page via search, for multi-label
# combinations (e.g. "Bug" AND "Domain: Formatter"). $q is a full GitHub
# search query string built by fetch_issues.build_search_query().
SEARCH_ISSUES_PAGE_QUERY = f"""
query($q: String!, $cursor: String) {{
  {RATE_LIMIT_FIELD}
  search(query: $q, type: ISSUE, first: 100, after: $cursor) {{
    issueCount
    pageInfo {{ hasNextPage endCursor }}
    nodes {{
      __typename
      ... on Issue {{
{ISSUE_DETAIL_FIELDS}
      }}
    }}
  }}
}}
"""
