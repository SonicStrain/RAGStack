Flush the RAGStack semantic cache so the next queries are retrieved fresh.

Steps:
1. Call `rag_clear_cache`.
2. Report how many cache entries were cleared.
3. Confirm with a follow-up `rag_status` showing cached_queries is now 0.

Use this when:
- You have updated source files and want fresh answers
- A cached answer looked stale or incorrect
- You are testing pipeline changes and want to bypass the cache
