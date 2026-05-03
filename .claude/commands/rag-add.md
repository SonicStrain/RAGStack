Add a raw text snippet to RAGStack's index so it can be retrieved later.

Text to add: $ARGUMENTS

Steps:
1. Parse the input: the text to index is everything in $ARGUMENTS.
   - If it starts with a quoted source label like [auth-spec]:, use that as the source name.
   - Otherwise, default source label is "manual".
2. Call `rag_ingest_text` with the text and source label.
3. Confirm how many total chunks are now indexed.

Example usage:
  /rag-add [api-spec]: All POST /auth/login requests must include a CSRF token header.
  /rag-add The database uses PostgreSQL 15 with pgvector for embeddings.
