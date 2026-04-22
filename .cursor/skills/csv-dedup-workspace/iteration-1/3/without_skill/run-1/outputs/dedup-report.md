# Deduplication Report

## Method

Case-insensitive comparison across all fields. Headers are preserved exactly as supplied. The first occurrence of each unique row (lowercased for comparison) is kept; subsequent duplicates are dropped.

## Input

| # | Name  | EMAIL                | City    |
|---|-------|----------------------|---------|
| 1 | Alice | alice@example.com    | Boston  |
| 2 | Bob   | bob@example.com      | Seattle |
| 3 | ALICE | alice@example.com    | BOSTON  |
| 4 | alice | ALICE@EXAMPLE.COM    | boston  |
| 5 | Bob   | BOB@EXAMPLE.COM      | Seattle |

**Total input rows:** 5

## Duplicates Removed

| Row | Name  | EMAIL             | City    | Duplicate of row |
|-----|-------|-------------------|---------|------------------|
| 3   | ALICE | alice@example.com | BOSTON  | 1                |
| 4   | alice | ALICE@EXAMPLE.COM | boston  | 1                |
| 5   | Bob   | BOB@EXAMPLE.COM   | Seattle | 2                |

**Rows removed:** 3

## Output

| # | Name  | EMAIL             | City    |
|---|-------|-------------------|---------|
| 1 | Alice | alice@example.com | Boston  |
| 2 | Bob   | bob@example.com   | Seattle |

**Total output rows:** 2
