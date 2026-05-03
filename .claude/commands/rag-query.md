Search the indexed codebase using RAGStack and answer the following question: $ARGUMENTS

Steps:
1. Call `rag_status` to confirm documents are indexed. If indexed_docs is 0, call `rag_ingest_directory` on the project root first, then proceed.
2. Call `rag_query` with the question above.
3. Present the answer with source citations clearly highlighted.

If no arguments were provided, ask the user what they want to search for.
