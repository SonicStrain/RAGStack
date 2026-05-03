Index files into RAGStack so they can be searched.

Target: $ARGUMENTS

Steps:
1. If no path was given in $ARGUMENTS, use "." (the current project root).
2. Call `rag_ingest_directory` on the target path.
   - Default extensions cover: .py .js .ts .go .rs .java .md .txt .yaml .toml
   - To restrict to specific types, mention them (e.g. "only .py and .md files")
3. After indexing, call `rag_status` and report:
   - How many files and chunks were indexed
   - Which retriever backend is active
   - Total indexed docs now available

Tip: re-running this command on the same directory adds new/changed files to
the index (duplicates are harmless — the retriever scores by relevance).
