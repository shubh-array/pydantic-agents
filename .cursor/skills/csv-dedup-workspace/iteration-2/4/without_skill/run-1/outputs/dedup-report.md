# Deduplication Report

## Summary

| Metric | Count |
|--------|-------|
| Original rows | 5 |
| Duplicate rows removed | 2 |
| Unique rows retained | 3 |

## Duplicates Removed

| Name | Address | Score | Occurrences |
|------|---------|-------|-------------|
| Smith, John | 123 Main St, New York, NY | 95 | 2 |
| Doe, Jane | 456 Oak Ave, Chicago, IL | 87 | 2 |

## Retained Records

| Name | Address | Score |
|------|---------|-------|
| Smith, John | 123 Main St, New York, NY | 95 |
| Doe, Jane | 456 Oak Ave, Chicago, IL | 87 |
| Lee, Sam | 789 Pine Rd, Boston, MA | 91 |

## Method

Exact-match deduplication across all fields (Name, Address, Score). The first occurrence of each unique row was kept; subsequent duplicates were discarded.
