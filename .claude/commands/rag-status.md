Show the current RAGStack configuration and health summary.

Call `rag_status` and display the result in a clean table, including:
- Active backend for each of the 6 layers (optimizer, cache, rewriter, retriever, compressor, prompt_cache)
- Number of indexed document chunks
- Number of cached query responses
- LLM model in use
- Config file path

Then give a one-line assessment: is RAGStack ready to answer questions, or does
the user need to index documents first?
