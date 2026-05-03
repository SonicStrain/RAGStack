"""
ragstack/docs.py — Documentation HTML generator

Returns a self-contained HTML page (Mermaid + syntax highlighting included via CDN)
served at /ragstack-docs by the FastAPI layer in gui.py.
"""
from __future__ import annotations


def get_docs_html() -> str:
    """Return the full docs HTML page."""
    return _HTML


_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RAGStack Docs</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<link rel="stylesheet"
  href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<style>
  :root {
    --indigo: #4f46e5; --indigo-light: #e0e7ff; --green: #16a34a;
    --slate: #475569;  --bg: #f8fafc;           --card: #ffffff;
    --border: #e2e8f0; --text: #1e293b;         --muted: #64748b;
    --code-bg: #f1f5f9;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg); color: var(--text); font-size: 15px;
    line-height: 1.7; display: flex; min-height: 100vh;
  }

  /* -- Sidebar -- */
  nav {
    width: 230px; min-width: 230px; background: var(--card);
    border-right: 1px solid var(--border); padding: 24px 0;
    position: sticky; top: 0; height: 100vh; overflow-y: auto;
    flex-shrink: 0;
  }
  nav .logo {
    padding: 0 20px 20px; border-bottom: 1px solid var(--border);
    margin-bottom: 12px;
  }
  nav .logo span { font-size: 1.15rem; font-weight: 700; color: var(--indigo); }
  nav .logo small { display: block; color: var(--muted); font-size: 0.75rem; margin-top: 2px; }
  nav a {
    display: block; padding: 7px 20px; color: var(--slate);
    text-decoration: none; font-size: 0.875rem; border-left: 3px solid transparent;
    transition: all 0.15s;
  }
  nav a:hover { background: var(--indigo-light); color: var(--indigo); }
  nav a.active { border-left-color: var(--indigo); color: var(--indigo);
    background: var(--indigo-light); font-weight: 600; }
  nav .section-head {
    padding: 14px 20px 4px; font-size: 0.7rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: .1em; color: var(--muted);
  }

  /* -- Main content -- */
  main { flex: 1; padding: 40px 48px; max-width: 960px; overflow-y: auto; }
  section { margin-bottom: 64px; scroll-margin-top: 20px; }

  h1 { font-size: 2rem; font-weight: 800; color: var(--indigo); margin-bottom: 8px; }
  h2 { font-size: 1.4rem; font-weight: 700; margin: 40px 0 14px;
    padding-bottom: 8px; border-bottom: 2px solid var(--indigo-light); color: var(--text); }
  h3 { font-size: 1.1rem; font-weight: 600; margin: 24px 0 10px; color: var(--text); }
  h4 { font-size: 0.95rem; font-weight: 600; margin: 16px 0 8px; color: var(--slate); }
  p  { margin-bottom: 12px; }
  ul, ol { padding-left: 22px; margin-bottom: 12px; }
  li { margin-bottom: 4px; }
  a  { color: var(--indigo); }
  code {
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    background: var(--code-bg); border-radius: 4px;
    padding: 1px 6px; font-size: 0.875em; color: #be123c;
  }
  pre {
    background: var(--code-bg); border: 1px solid var(--border);
    border-radius: 8px; padding: 16px 20px; overflow-x: auto;
    margin: 12px 0; font-size: 0.85em; line-height: 1.6;
  }
  pre code { background: none; padding: 0; color: inherit; }

  /* -- Cards & callouts -- */
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 20px 24px; margin-bottom: 16px;
  }
  .callout {
    border-left: 4px solid var(--indigo); background: var(--indigo-light);
    border-radius: 0 8px 8px 0; padding: 14px 18px; margin: 16px 0;
  }
  .callout.tip  { border-color: var(--green); background: #dcfce7; }
  .callout.warn { border-color: #d97706;      background: #fef9c3; }
  .callout.free { border-color: var(--green); background: #dcfce7; }

  /* -- Preset cards -- */
  .preset-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 14px; margin: 20px 0;
  }
  .preset-card {
    background: var(--card); border: 2px solid var(--border);
    border-radius: 12px; padding: 18px 20px;
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  .preset-card:hover { border-color: var(--indigo); box-shadow: 0 2px 12px #4f46e520; }
  .preset-card .preset-icon { font-size: 1.6rem; margin-bottom: 8px; }
  .preset-card .preset-name { font-weight: 700; font-size: 0.95rem; margin-bottom: 4px; }
  .preset-card .preset-cost {
    display: inline-block; font-size: 0.72rem; font-weight: 700;
    border-radius: 20px; padding: 2px 10px; margin-bottom: 8px;
  }
  .preset-card .preset-cost.free { background: #dcfce7; color: #15803d; }
  .preset-card .preset-cost.paid { background: #e0e7ff; color: #4338ca; }
  .preset-card .preset-desc { font-size: 0.85rem; color: var(--slate); }
  .preset-card code { font-size: 0.78rem; }

  /* -- Steps -- */
  .steps { counter-reset: step; list-style: none; padding: 0; }
  .steps li {
    counter-increment: step; display: flex; gap: 16px;
    align-items: flex-start; margin-bottom: 18px;
  }
  .steps li::before {
    content: counter(step); min-width: 32px; height: 32px;
    background: var(--indigo); color: white; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.9rem; flex-shrink: 0; margin-top: 2px;
  }
  .steps li .step-body { flex: 1; }
  .steps li .step-body strong { display: block; margin-bottom: 4px; }

  /* -- Tables -- */
  table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.9rem; }
  th { background: var(--indigo); color: white; padding: 10px 14px; text-align: left; }
  td { padding: 9px 14px; border-bottom: 1px solid var(--border); }
  tr:nth-child(even) td { background: #f8fafc; }
  tr:hover td { background: var(--indigo-light); }

  /* -- Layer badges -- */
  .layer-badge {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-size: 0.75rem; font-weight: 700; margin-right: 6px;
    background: var(--indigo); color: white;
  }

  /* -- Mermaid -- */
  .mermaid {
    background: white; border: 1px solid var(--border);
    border-radius: 10px; padding: 20px; margin: 20px 0; text-align: center;
    overflow-x: auto;
  }

  /* -- Hero -- */
  .hero-sub { color: var(--muted); font-size: 1.05rem; margin-bottom: 24px; }
  .badge {
    display: inline-block; background: var(--indigo); color: white;
    border-radius: 20px; padding: 4px 14px; font-size: 0.8rem;
    font-weight: 600; margin-right: 6px; margin-bottom: 8px;
  }
  .badge.green { background: var(--green); }
  .badge.gray  { background: var(--slate); }
</style>
</head>
<body>

<!-- Sidebar -->
<nav>
  <div class="logo">
    <span>&#x1F537; RAGStack</span>
    <small>Token-Optimized RAG Pipeline</small>
  </div>

  <div class="section-head">Getting Started</div>
  <a href="#quick-setup">Quick Setup</a>
  <a href="#presets">Quick Presets</a>
  <a href="#api-keys">API Keys</a>
  <a href="#gui-guide">GUI Guide</a>

  <div class="section-head">Architecture</div>
  <a href="#overview">Pipeline Overview</a>
  <a href="#layers">The 6 Layers</a>
  <a href="#query-context">QueryContext</a>
  <a href="#token-savings">Token Savings</a>

  <div class="section-head">Retrievers</div>
  <a href="#graphify">Graphify (Graph RAG)</a>
  <a href="#memory-retriever">Memory Retriever</a>

  <div class="section-head">Workflows</div>
  <a href="#claude-code">Claude Code + Pro</a>
  <a href="#any-project">Using Any Project</a>

  <div class="section-head">Reference</div>
  <a href="#config-ref">Configuration YAML</a>
  <a href="#backends-ref">Backends Reference</a>
  <a href="#slash-commands">Slash Commands</a>
  <a href="#adding-backend">Adding a Backend</a>
</nav>

<!-- Main -->
<main>

<!-- ============================================================ -->
<section id="quick-setup">
  <h1>RAGStack Documentation</h1>
  <p class="hero-sub">A 6-layer token-optimization pipeline that plugs into Claude Code via MCP.</p>
  <span class="badge">Python 3.10+</span>
  <span class="badge green">Free with Ollama</span>
  <span class="badge gray">MCP + GUI + CLI</span>

  <h2>Quick Setup</h2>
  <ol class="steps">
    <li>
      <div class="step-body">
        <strong>Run the one-click installer</strong>
        <pre><code class="language-bash">cd path/to/ragstack
python install.py</code></pre>
        Installs all dependencies, copies config, registers the MCP server globally in
        <code>~/.claude/settings.json</code>, and writes slash commands to
        <code>.claude/commands/</code>.
      </div>
    </li>
    <li>
      <div class="step-body">
        <strong>Launch the Pipeline Studio GUI</strong>
        <pre><code class="language-bash">python ragstack/gui.py</code></pre>
        Opens at <code>http://localhost:7860</code>. Go to <strong>Configuration</strong>
        and pick a <strong>Quick Preset</strong> for your provider (Ollama is free and auto-installs everything).
      </div>
    </li>
    <li>
      <div class="step-body">
        <strong>Install Claude Code CLI</strong>
        <pre><code class="language-bash"># Windows (PowerShell)
irm https://claude.ai/install.ps1 | iex

# macOS / Linux
curl -fsSL https://claude.ai/install.sh | sh</code></pre>
        Then add it to your PATH if prompted (the installer will tell you the path).
        Verify with: <code>claude --version</code>
      </div>
    </li>
    <li>
      <div class="step-body">
        <strong>Make slash commands global (one-time)</strong>
        <pre><code class="language-bash"># Windows PowerShell
Copy-Item ".claude\commands\*.md" "$HOME\.claude\commands\" -Force

# macOS / Linux
cp .claude/commands/*.md ~/.claude/commands/</code></pre>
        After this, <code>/rag-query</code>, <code>/rag-index</code> etc. work in
        <strong>every</strong> Claude Code project, not just this one.
      </div>
    </li>
    <li>
      <div class="step-body">
        <strong>Index your codebase</strong>
        <pre><code>/rag-index .          # in Claude Code, or use GUI Status &amp; Tools tab</code></pre>
      </div>
    </li>
    <li>
      <div class="step-body">
        <strong>Ask questions</strong>
        <pre><code>/rag-query how does authentication work?
/rag-query what calls the token validator?</code></pre>
        Or just ask naturally — Claude uses the MCP tools automatically.
      </div>
    </li>
  </ol>

  <div class="callout tip">
    <strong>No API key?</strong> Inspect mode in the GUI runs completely free
    (no LLM call). For a full LLM answer, use the Ollama preset -- completely
    local, no API key, no cost.
  </div>
</section>

<!-- ============================================================ -->
<section id="presets">
  <h2>Quick Presets</h2>
  <p>
    Presets are one-click configurations available in the
    <strong>Configuration</strong> tab of the GUI. Each preset sets the LLM
    provider, model, and prompt-cache backend in one click and immediately
    reloads the pipeline.
  </p>

  <div class="preset-grid">

    <div class="preset-card">
      <div class="preset-icon">&#x1F999;</div>
      <div class="preset-name">Ollama / Llama (Free)</div>
      <span class="preset-cost free">FREE -- no API key</span>
      <div class="preset-desc">
        Runs <code>llama3.2</code> locally via Ollama. Zero cost, full privacy.
        Clicking this preset <strong>automatically</strong>:
        <ul>
          <li>Installs the <code>ollama</code> Python package if missing</li>
          <li>Checks that Ollama is running at <code>localhost:11434</code></li>
          <li>Pulls <code>llama3.2</code> if not already downloaded</li>
        </ul>
        You still need to <a href="https://ollama.com" target="_blank">install Ollama</a>
        itself first — the GUI handles everything else.
      </div>
    </div>

    <div class="preset-card">
      <div class="preset-icon">&#x1F916;</div>
      <div class="preset-name">Anthropic Claude</div>
      <span class="preset-cost paid">Requires API key</span>
      <div class="preset-desc">
        Uses <code>claude-sonnet-4-6</code> with Anthropic prompt caching (L5)
        for reduced costs on repeated calls. Set <code>ANTHROPIC_API_KEY</code>
        in Status &amp; Tools before applying.
      </div>
    </div>

    <div class="preset-card">
      <div class="preset-icon">&#x1F535;</div>
      <div class="preset-name">OpenAI GPT-4o</div>
      <span class="preset-cost paid">Requires API key</span>
      <div class="preset-desc">
        Uses <code>gpt-4o-mini</code> with OpenAI prompt caching (tokens cached
        automatically at &gt;= 1024 tokens). Set <code>OPENAI_API_KEY</code>.
      </div>
    </div>

    <div class="preset-card">
      <div class="preset-icon">&#x1F31F;</div>
      <div class="preset-name">Google Gemini</div>
      <span class="preset-cost paid">Requires API key</span>
      <div class="preset-desc">
        Uses <code>gemini-1.5-flash</code>. Set <code>GOOGLE_API_KEY</code>
        in Status &amp; Tools. Run <code>python install.py --extras gemini</code>
        first.
      </div>
    </div>

    <div class="preset-card">
      <div class="preset-icon">&#x1F578;</div>
      <div class="preset-name">Graphify + Ollama</div>
      <span class="preset-cost free">FREE -- local LLM + graph RAG</span>
      <div class="preset-desc">
        Graph-based code retriever (BFS traversal) + local Llama LLM.
        Clicking this preset <strong>automatically</strong>:
        <ul>
          <li>Installs <code>ollama</code> Python package + pulls <code>llama3.2</code></li>
          <li>Installs <code>graphifyy</code> (the Graphify package) via pip</li>
          <li>Runs <code>graphify install</code> to register the Claude Code skill</li>
          <li>Warns if <code>graphify-out/graph.json</code> is missing</li>
        </ul>
        After applying: run <code>/graphify .</code> in Claude Code to build
        the knowledge graph, then use <code>/rag-query</code> normally.
        See <a href="#graphify">Graphify</a> for full details.
      </div>
    </div>

  </div>

  <div class="callout">
    <strong>Tip:</strong> Ollama and Graphify presets auto-install their required
    packages on first click and show progress in the Status box. Other settings
    (retriever backend, compressor, cache threshold) are preserved across preset
    changes.
  </div>
</section>

<!-- ============================================================ -->
<section id="api-keys">
  <h2>API Keys</h2>

  <div class="callout warn">
    <strong>Claude Pro does not equal the Anthropic API.</strong>
    Claude Pro gives you the claude.ai chat interface. The Anthropic API is a
    separate pay-as-you-go service with its own credit balance. See the
    <a href="#claude-code">Claude Code + Pro</a> section for the free workflow.
  </div>

  <h3>Setting keys in the GUI</h3>
  <p>
    Open <strong>Status &amp; Tools &rarr; API Keys</strong>. Select the variable,
    paste your key, click <strong>Set Key</strong>. Keys are applied in-memory for
    the current session only -- never written to disk.
  </p>

  <table>
    <tr><th>Variable</th><th>Where to get it</th><th>Used for</th></tr>
    <tr>
      <td><code>ANTHROPIC_API_KEY</code></td>
      <td><a href="https://console.anthropic.com/settings/keys">console.anthropic.com</a></td>
      <td>Claude LLM answers, LLM rewriter, LLM optimizer</td>
    </tr>
    <tr>
      <td><code>OPENAI_API_KEY</code></td>
      <td><a href="https://platform.openai.com/api-keys">platform.openai.com</a></td>
      <td>Embeddings (semantic cache), OpenAI LLM</td>
    </tr>
    <tr>
      <td><code>GOOGLE_API_KEY</code></td>
      <td><a href="https://aistudio.google.com/app/apikey">aistudio.google.com</a></td>
      <td>Gemini LLM</td>
    </tr>
  </table>

  <h3>Setting keys in the terminal (persistent)</h3>
  <pre><code class="language-bash"># Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# macOS / Linux
export ANTHROPIC_API_KEY="sk-ant-..."</code></pre>

  <h3>Free / zero-key configuration</h3>
  <p>Use the <strong>Ollama / Llama</strong> preset or set these manually:</p>
  <table>
    <tr><th>Layer</th><th>Free backend</th></tr>
    <tr><td>L0 Optimizer</td><td><code>rules</code></td></tr>
    <tr><td>L1 Cache</td><td><code>memory</code> (skips embed call when cache is empty)</td></tr>
    <tr><td>L2 Rewriter</td><td><code>llm</code> (uses Ollama — free &amp; recommended) or <code>passthrough</code></td></tr>
    <tr><td>L3 Retriever</td><td><code>memory</code> or <code>graphify</code></td></tr>
    <tr><td>L4 Compressor</td><td><code>passthrough</code></td></tr>
    <tr><td>L5 Prompt Cache</td><td><code>none</code></td></tr>
    <tr><td>LLM</td><td><code>ollama</code> (local, free)</td></tr>
  </table>
</section>

<!-- ============================================================ -->
<section id="gui-guide">
  <h2>GUI Guide</h2>

  <h3>Pipeline Studio tab</h3>
  <p>The primary interface. Type any query and see every pipeline stage in detail.</p>
  <ul>
    <li><strong>Inspect only</strong> -- runs L0-L5 without calling the LLM. Free.</li>
    <li><strong>Full pipeline</strong> -- runs inspect then makes one LLM call for an answer.</li>
    <li><strong>Show raw prompt JSON</strong> -- reveals the exact messages dict sent to the LLM.</li>
    <li><strong>Token counter</strong> -- accumulates tokens saved this session by the optimizer.</li>
  </ul>

  <h3>Configuration tab</h3>
  <p>
    <strong>Quick Presets</strong> at the top let you switch provider in one click.
    Below that, change any backend using the dropdowns -- no YAML knowledge needed.
    The YAML editor on the right stays in sync. Click <strong>Save &amp; Reload
    Pipeline</strong> to apply. You can also edit raw YAML and click
    <strong>Apply YAML &amp; Reload</strong>.
  </p>
    <p>
      The <strong>Status box</strong> below the preset buttons shows per-step
      progress for any auto-installation that the preset triggers (ollama package,
      llama3.2 model pull, graphifyy install, graphify install). Installation
      runs synchronously — the GUI will pause briefly while packages are fetched.
    </p>

  <h3>Status &amp; Tools tab</h3>
  <ul>
    <li><strong>API Keys</strong> -- paste keys in-browser, session-scoped</li>
    <li><strong>Refresh</strong> -- shows active backends and index counts</li>
    <li><strong>Index a directory</strong> -- crawl &amp; chunk a local folder</li>
    <li><strong>Add a text snippet</strong> -- manually add any text to the index</li>
    <li><strong>Clear Semantic Cache</strong> -- flush cached answers</li>
  </ul>
</section>

<!-- ============================================================ -->
<section id="overview">
  <h2>Pipeline Overview</h2>
  <p>
    Every query passes through up to 6 layers before reaching the LLM. Each layer
    is independently swappable via a single line in <code>ragstack.config.yaml</code>.
  </p>

  <div class="mermaid">
flowchart TD
    subgraph SG0 ["L0 Prompt Optimizer"]
      N0["rules, llm, passthrough"]
    end
    subgraph SG1 ["L1 Semantic Cache"]
      N1["memory, redis, qdrant"]
    end
    subgraph SG2 ["L2 Query Rewriter"]
      N2["passthrough, llm, hyde"]
    end
    subgraph SG3 ["L3 Retriever"]
      N3["graphify, memory, chroma, pinecone, weaviate"]
    end
    subgraph SG4 ["L4 Compressor"]
      N4["passthrough, reranker, llmlingua"]
    end
    subgraph SG5 ["L5 Prompt Cache Builder"]
      N5["anthropic, openai, none"]
    end

    A(["User Query"]) --> N0
    N0 -->|optimized query| N1
    N1 -->|cache hit| CACHED(["Cached answer"])
    N1 -->|cache miss| N2
    N2 -->|rewritten query| N3
    N3 -->|top K chunks| N4
    N4 -->|final chunks| N5
    N5 --> MODEL(["Model API Call"])
    MODEL --> STORE["Store in L1 Cache"]
    STORE --> RESP(["Return to caller"])

    style CACHED fill:#16a34a,color:#fff
    style MODEL  fill:#4f46e5,color:#fff
    style RESP   fill:#4f46e5,color:#fff
    style STORE  fill:#0891b2,color:#fff
  </div>
</section>

<!-- ============================================================ -->
<section id="layers">
  <h2>The 6 Layers</h2>

  <!-- L0 -->
  <div class="card">
    <h3><span class="layer-badge">L0</span>Prompt Optimizer</h3>
    <p>
      Strips filler words and redundant phrasing from the raw user query
      <em>before</em> anything else runs. The optimized query becomes the cache key,
      the LLM question, and the retrieval seed -- so every downstream layer benefits.
    </p>
    <table>
      <tr><th>Backend</th><th>How it works</th><th>API key?</th></tr>
      <tr><td><code>rules</code></td><td>Regex strips "Could you please", "basically", trailing "thanks" etc.</td><td>No</td></tr>
      <tr><td><code>llm</code></td><td>Sends to a cheap fast model with a strict optimizer prompt</td><td>Yes</td></tr>
      <tr><td><code>passthrough</code></td><td>Returns query unchanged</td><td>No</td></tr>
    </table>
    <p><strong>Typical savings:</strong> 15-77% token reduction on developer prompts.</p>
  </div>

  <!-- L1 -->
  <div class="card">
    <h3><span class="layer-badge">L1</span>Semantic Cache</h3>
    <p>
      Embeds the optimized query and cosine-compares against stored embeddings.
      On a hit, layers 2-5 are skipped entirely -- instant free answer.
    </p>
    <div class="mermaid">
flowchart LR
    Q[optimized_query] --> EMPTY{Cache empty}
    EMPTY -->|Yes| SKIP([Return None])
    EMPTY -->|No| EMB[Embed query]
    EMB --> COS{Above threshold}
    COS -->|Yes| CACHED([Return cached answer])
    COS -->|No| CONT[Continue to L2]
    style CACHED fill:#16a34a,color:#fff
    style SKIP   fill:#64748b,color:#fff
  </div>
    <table>
      <tr><th>Backend</th><th>Storage</th><th>Notes</th></tr>
      <tr><td><code>memory</code></td><td>In-process list</td><td>Zero deps. Short-circuits on empty cache (no embed call).</td></tr>
      <tr><td><code>redis</code></td><td>Redis + RediSearch</td><td>Persists across restarts. Needs <code>redis[hiredis]</code>.</td></tr>
      <tr><td><code>qdrant</code></td><td>Qdrant vector DB</td><td>Scalable. Needs <code>qdrant-client</code>.</td></tr>
    </table>
  </div>

  <!-- L2 -->
  <div class="card">
    <h3><span class="layer-badge">L2</span>Query Rewriter</h3>
    <p>
      Enriches the optimized query for <em>retrieval only</em> — the rewritten form
      is never seen by the final LLM. Expanding a short query with synonyms dramatically
      improves recall, especially for keyword-based retrievers like Graphify and Memory.
    </p>
    <table>
      <tr><th>Backend</th><th>Strategy</th><th>API key?</th><th>Best for</th></tr>
      <tr>
        <td><code>llm</code></td>
        <td>Expands abbreviations, makes intent explicit, adds synonyms</td>
        <td>No — reuses pipeline LLM (Ollama if configured)</td>
        <td><strong>Default for Ollama presets.</strong> Free when Ollama is running.</td>
      </tr>
      <tr>
        <td><code>hyde</code></td>
        <td>Generates a full hypothetical answer, embeds it for retrieval</td>
        <td>No — reuses pipeline LLM + embedder</td>
        <td>Vector-search retrievers (Chroma, Pinecone, Weaviate)</td>
      </tr>
      <tr>
        <td><code>passthrough</code></td>
        <td>Returns query unchanged</td>
        <td>No</td>
        <td>Debugging / when query is already well-formed</td>
      </tr>
    </table>
    <div class="callout tip">
      <strong>Why LLM rewriting is always worth it with Ollama:</strong>
      The rewriter fires once per query, uses only ~256 tokens, and sends its output
      directly to L3 — not to the final LLM. Because the Ollama server is already
      running for the main answer, this extra call costs nothing (no API fees, ~1&ndash;2s
      latency). In return, a query like <em>"How RAGStack works?"</em> becomes
      <em>"How does the RAGStack pipeline function? RAG retrieval-augmented generation
      token optimization layers cache"</em> — giving the retriever far more keywords
      to match against.
    </div>
  </div>

  <!-- L3 -->
  <div class="card">
    <h3><span class="layer-badge">L3</span>Retriever</h3>
    <p>Finds the top-K most relevant chunks from the indexed corpus.</p>
    <table>
      <tr><th>Backend</th><th>Method</th><th>Best for</th></tr>
      <tr><td><code>graphify</code></td><td>BFS graph traversal</td><td>Code with explicit relationships (calls, imports)</td></tr>
      <tr><td><code>memory</code></td><td>TF-IDF word overlap</td><td>Small corpora, zero deps, no API key</td></tr>
      <tr><td><code>chroma</code></td><td>Local vector DB</td><td>Medium corpora, no cloud</td></tr>
      <tr><td><code>pinecone</code></td><td>Managed vector DB</td><td>Large corpora, production</td></tr>
      <tr><td><code>weaviate</code></td><td>Managed vector DB</td><td>Large corpora with metadata filters</td></tr>
    </table>
  </div>

  <!-- L4 -->
  <div class="card">
    <h3><span class="layer-badge">L4</span>Compressor / Reranker</h3>
    <p>
      Reorders and filters the retrieved chunks so only the best <code>top_k</code>
      reach the LLM. Reduces context window usage significantly.
    </p>
    <table>
      <tr><th>Backend</th><th>How it works</th><th>Needs</th></tr>
      <tr><td><code>passthrough</code></td><td>Returns chunks unchanged, up to top_k</td><td>Nothing</td></tr>
      <tr><td><code>reranker</code></td><td>CrossEncoder cross-attention scoring (ms-marco)</td><td><code>sentence-transformers</code></td></tr>
      <tr><td><code>llmlingua</code></td><td>Token-level compression of chunk text</td><td><code>llmlingua</code></td></tr>
    </table>
  </div>

  <!-- L5 -->
  <div class="card">
    <h3><span class="layer-badge">L5</span>Prompt Cache Builder</h3>
    <p>
      Assembles the final <code>system + messages</code> dict. When using Anthropic,
      the static system prefix is marked <code>ephemeral</code> so it is served from
      Anthropic's prompt cache on repeated calls -- saving prefix tokens every time.
    </p>
    <table>
      <tr><th>Backend</th><th>Behaviour</th></tr>
      <tr><td><code>anthropic</code></td><td>Marks system prefix with <code>cache_control: ephemeral</code></td></tr>
      <tr><td><code>openai</code></td><td>Concatenates prefix as system message (OpenAI caches >= 1024 tokens automatically)</td></tr>
      <tr><td><code>none</code></td><td>Plain system + user messages, no cache markers. Use with Ollama/Gemini.</td></tr>
    </table>
  </div>
</section>

<!-- ============================================================ -->
<section id="query-context">
  <h2>QueryContext -- the data object</h2>
  <p>
    A single <code>QueryContext</code> dataclass flows through all 6 layers.
    No layer imports another layer; they all read/write the same object.
  </p>
  <pre><code class="language-python">@dataclass
class QueryContext:
    original_query:    str         # what the user typed
    optimized_query:   str = ""    # after Layer 0 (shorter)
    rewritten_query:   str = ""    # after Layer 2 (richer, for retrieval only)
    retrieved_chunks:  list[dict]  # after Layer 3
    compressed_chunks: list[dict]  # after Layer 4

    @property
    def cache_key(self) -> str:
        # normalises phrasing variations -> more cache hits
        return self.optimized_query or self.original_query

    @property
    def active_query(self) -> str:
        # richest form used for vector retrieval
        return self.rewritten_query or self.optimized_query or self.original_query

    @property
    def llm_query(self) -> str:
        # what the LLM sees -- concise, optimized
        return self.optimized_query or self.original_query

    @property
    def final_chunks(self) -> list[dict]:
        return self.compressed_chunks or self.retrieved_chunks</code></pre>
</section>

<!-- ============================================================ -->
<section id="token-savings">
  <h2>Token Savings Walkthrough</h2>
  <div class="mermaid">
flowchart LR
    A["Raw query 35 tokens"] -->|L0 reduces 77 pct| B["Optimized 8 tokens"]
    B -->|cache key| C1{L1 Cache}
    B -->|L2 rewrites| D["Expanded query"]
    B -->|model input| E["Model call"]

    C1 -->|cache hit| FREE([Free instant answer])
    C1 -->|cache miss| D

    D -->|L3 gets 8 chunks| F["8 chunks retrieved"]
    F -->|L4 keeps top 3| G["600 context tokens"]
    G --> E

    E --> ANS([Final answer])

    style FREE fill:#16a34a,color:#fff
    style ANS  fill:#4f46e5,color:#fff
  </div>

  <table>
    <tr><th>Source</th><th>Without RAGStack</th><th>With RAGStack</th></tr>
    <tr><td>User prompt</td><td>35 tokens</td><td><strong>8 tokens</strong> (L0 -77%)</td></tr>
    <tr><td>Context</td><td>Full corpus, unfiltered</td><td><strong>Top 3 chunks</strong> (L4)</td></tr>
    <tr><td>System prefix</td><td>Repeated every call</td><td><strong>Cached</strong> (L5)</td></tr>
    <tr><td>Repeated questions</td><td>Full LLM call each time</td><td><strong>Cache hit</strong> (L1, free)</td></tr>
  </table>
</section>

<!-- ============================================================ -->
<section id="graphify">
  <h2>Graphify -- Graph-Based RAG</h2>
  <div class="callout">
    <strong>What makes Graphify different:</strong> Instead of pure semantic
    similarity, Graphify traverses an explicit code relationship graph. It finds
    nodes matching your query, then follows <em>calls</em>, <em>depends_on</em>,
    and other edges to surface related code you might not have thought to ask for.
    <br><br>
    <strong>GitHub:</strong>
    <a href="https://github.com/safishamsi/graphify" target="_blank">
      github.com/safishamsi/graphify
    </a>
    <br><br>
    <strong>Auto-setup:</strong> Click the <strong>🕸 Graphify + Ollama</strong>
    preset in the GUI Configuration tab — it installs <code>graphifyy</code> and
    registers the Claude Code skill automatically. You still need to run
    <code>/graphify .</code> once to build the <code>graph.json</code>.
  </div>

  <h3>How it works</h3>
  <div class="mermaid">
flowchart TD
    subgraph SGA[Seed Node Matching]
      S1["Scan labels for keyword overlap"]
      S2["Keep top 5 matching nodes"]
    end
    subgraph SGB[BFS Graph Traversal]
      B1["Seed nodes at depth 0"]
      B2["Depth 1 neighbours"]
      B3["Depth 2 and beyond"]
    end

    Q[Query keywords] --> S1
    S1 --> S2
    S2 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> FLT["Filter by allowed edge types"]
    FLT --> TOPK["Slice to top K nodes"]
    TOPK --> ROUT([Retrieved chunks])

    style ROUT fill:#4f46e5,color:#fff
  </div>

  <h3>Graph JSON format</h3>
  <p>Graphify reads a graph from a JSON file. Each node becomes a retrievable chunk.</p>
  <pre><code class="language-json">{
  "nodes": [
    {
      "id": "auth/auth_service.py::AuthService",
      "label": "AuthService",
      "type": "class",
      "file": "auth/auth_service.py",
      "content": "class AuthService:\\n    def authenticate(self, token): ..."
    },
    {
      "id": "auth/token_validator.py::TokenValidator",
      "label": "TokenValidator",
      "type": "class",
      "file": "auth/token_validator.py",
      "content": "class TokenValidator:\\n    def validate(self, jwt): ..."
    }
  ],
  "edges": [
    {
      "source": "auth/auth_service.py::AuthService",
      "target": "auth/token_validator.py::TokenValidator",
      "relation": "calls"
    },
    {
      "source": "auth/token_validator.py::TokenValidator",
      "target": "auth/auth_service.py::AuthService",
      "relation": "depends_on"
    }
  ]
}</code></pre>

  <h3>Supported edge types</h3>
  <table>
    <tr><th>Edge type</th><th>Meaning</th></tr>
    <tr><td><code>calls</code></td><td>Function/method A calls B</td></tr>
    <tr><td><code>depends_on</code></td><td>Module A imports or depends on B</td></tr>
    <tr><td><code>semantically_similar_to</code></td><td>A and B are semantically related</td></tr>
    <tr><td><code>rationale_for</code></td><td>A explains the reason B exists</td></tr>
  </table>

  <h3>Configuration</h3>
  <pre><code class="language-yaml">retriever:
  backend: graphify
  graphify:
    graph_path:  ./graphify-out/graph.json    # required
    report_path: ./graphify-out/GRAPH_REPORT.md
    hop_limit: 3          # BFS depth (1-5 recommended)
    edge_types:           # omit to follow all edge types
      - calls
      - depends_on
      - semantically_similar_to
      - rationale_for</code></pre>

  <h3>Generating a graph</h3>
  <ul>
    <li>
      <strong><a href="https://github.com/safishamsi/graphify" target="_blank">Graphify tool</a></strong>
      -- the dedicated graph generator for this retriever. Analyses your Python/JS
      codebase and outputs the exact JSON schema above with nodes, edges, and a
      <code>GRAPH_REPORT.md</code> summary.
    </li>
    <li>
      <strong>Claude Code + slash command</strong> -- ask Claude to analyse
      your codebase and emit the graph JSON using the schema above.
    </li>
    <li>
      <strong>tree-sitter + custom extractor</strong> -- parse AST to extract
      function calls and imports as edges automatically.
    </li>
    <li>
      <strong>Manual</strong> -- for small codebases, write the JSON directly.
    </li>
  </ul>

  <div class="callout tip">
    <strong>Tip:</strong> Graphify falls back to returning the
    <code>GRAPH_REPORT.md</code> file content if no seed nodes match. Keep a
    human-readable summary of your architecture there for broad questions.
  </div>

  <h3>When to use Graphify vs Memory</h3>
  <table>
    <tr><th>Scenario</th><th>Best retriever</th></tr>
    <tr><td>Questions about call chains ("what calls X?")</td><td>Graphify</td></tr>
    <tr><td>Questions about dependencies ("what does X depend on?")</td><td>Graphify</td></tr>
    <tr><td>Questions about text content ("where is X documented?")</td><td>Memory or Chroma</td></tr>
    <tr><td>Small codebase, no graph available</td><td>Memory</td></tr>
    <tr><td>Large codebase, cloud deployment</td><td>Pinecone / Weaviate</td></tr>
  </table>
</section>

<!-- ============================================================ -->
<section id="memory-retriever">
  <h2>Memory Retriever</h2>
  <p>
    Zero-dependency retriever. Uses TF-IDF-style word overlap scoring -- no
    embeddings, no API key, no external services. Documents live in-process as a
    Python list, optionally pre-seeded from <code>ragstack.config.yaml</code>.
  </p>
  <pre><code class="language-yaml">retriever:
  backend: memory
  memory:
    docs:
      - text: "AuthController delegates to AuthService.authenticate()."
        source: auth/auth_controller.py
      - text: "TokenValidator checks JWT using RS256 public key from config."
        source: auth/token_validator.py</code></pre>
  <p>
    Documents can also be added at runtime via the MCP tools
    (<code>rag_ingest_file</code>, <code>rag_ingest_directory</code>,
    <code>rag_ingest_text</code>) or the GUI "Add a text snippet" panel.
  </p>
</section>

<!-- ============================================================ -->
<section id="claude-code">
  <h2>Using RAGStack with Claude Code / Claude Pro</h2>

  <div class="callout warn">
    <strong>Important distinction:</strong> Claude Pro (claude.ai subscription)
    does NOT include Anthropic API credits. API access is billed separately.
    But you can still get powerful RAG for free using Ollama.
  </div>

  <h3>The free workflow for Claude Pro users</h3>
  <p>
    RAGStack works as an MCP server inside Claude Code. The LLM that Claude Code
    uses is handled by Anthropic separately -- RAGStack only needs a local model
    for its own pipeline answers. So even without API credits, you get:
  </p>
  <ul>
    <li>Full 6-layer pipeline (L0 optimizer, L1 cache, L2 rewriter, L3 retriever, L4 compressor)</li>
    <li>Semantic cache -- repeated questions answered instantly for free</li>
    <li>MCP tools that Claude Code can call to retrieve context from your codebase</li>
    <li>The Inspect-only GUI mode that traces all layers without any LLM call</li>
  </ul>

  <div class="mermaid">
flowchart LR
    CC["Claude Code"] -->|rag_query MCP call| RS["RAGStack L0 to L5"]
    RS -->|retrieves context| DB["Indexed codebase"]
    RS -->|answer and citations| CC
    CC -->|uses context| ANS([Claude answers])

    style ANS fill:#4f46e5,color:#fff
  </div>

  <p>
    In this workflow, RAGStack acts as a <strong>context retriever</strong>, not
    as an LLM itself. Claude Code's own Claude model does the final answering --
    using the context that RAGStack found. The pipeline LLM in RAGStack is only
    called when you use <code>/rag-query</code> or the GUI "Full pipeline" mode
    directly.
  </p>

  <h3>Step-by-step: Free setup with Ollama</h3>
  <ol class="steps">
    <li>
      <div class="step-body">
        <strong>Install Ollama</strong>
        Download from <a href="https://ollama.com" target="_blank">ollama.com</a>.
        Runs on Windows, macOS, and Linux. No account required.
      </div>
    </li>
    <li>
      <div class="step-body">
        <strong>Pull a model</strong>
        <pre><code class="language-bash">ollama pull llama3.2       # 2 GB, fast, great for code
ollama pull codellama      # code-specialized alternative
ollama pull mistral        # strong general model</code></pre>
      </div>
    </li>
    <li>
      <div class="step-body">
        <strong>Apply the Ollama preset in the GUI</strong>
        Open the <strong>Configuration</strong> tab and click
        <strong>Ollama / Llama (Free)</strong>. The pipeline reloads in seconds.
      </div>
    </li>
    <li>
      <div class="step-body">
        <strong>Index your project</strong>
        <pre><code>/rag-index .       # or use GUI Status &amp; Tools tab</code></pre>
      </div>
    </li>
    <li>
      <div class="step-body">
        <strong>Ask questions in Claude Code</strong>
        <pre><code>/rag-query how does the payment flow work?</code></pre>
        Claude Code calls the MCP tool, RAGStack retrieves relevant chunks,
        Claude Code uses those chunks to answer. No API credits consumed by RAGStack.
      </div>
    </li>
  </ol>

  <div class="callout tip">
    <strong>Best combo for Claude Code projects:</strong> Use the
    <strong>Graphify + Ollama</strong> preset. Index your codebase with Graphify
    (graph-based traversal finds call chains that vector search misses), and answer
    with Llama locally. The Semantic Cache (L1) means repeated questions about the
    same code are answered instantly.
  </div>

  <h3>What each part costs</h3>
  <table>
    <tr><th>Component</th><th>With Ollama preset</th><th>With Anthropic preset</th></tr>
    <tr><td>RAGStack pipeline (L0-L5)</td><td>Free (local)</td><td>~$0.001/query (mini model)</td></tr>
    <tr><td>Semantic cache hit</td><td>Free</td><td>Free</td></tr>
    <tr><td>Embeddings (L1 cache)</td><td>Free (TF-IDF memory retriever)</td><td>OpenAI API (~$0.0001/query)</td></tr>
    <tr><td>Claude Code final answer</td><td>Covered by Claude Code subscription</td><td>Covered by Claude Code subscription</td></tr>
  </table>

  <h3>MCP tools available in Claude Code</h3>
  <p>After <code>python install.py</code>, Claude Code can call these automatically:</p>
  <table>
    <tr><th>Tool</th><th>What it does</th></tr>
    <tr><td><code>rag_query</code></td><td>Run full RAGStack pipeline for a question, return answer + citations</td></tr>
    <tr><td><code>rag_ingest_file</code></td><td>Index a single file</td></tr>
    <tr><td><code>rag_ingest_directory</code></td><td>Index a directory recursively</td></tr>
    <tr><td><code>rag_ingest_text</code></td><td>Add a raw text snippet to the index</td></tr>
    <tr><td><code>rag_status</code></td><td>Return pipeline health as JSON</td></tr>
    <tr><td><code>rag_clear_cache</code></td><td>Flush the semantic cache</td></tr>
  </table>
</section>

<!-- ============================================================ -->
<section id="any-project">
  <h2>Using RAGStack with Any Project</h2>

  <p>
    RAGStack is installed <strong>once</strong> and works across all your projects.
    Understanding what is global vs local saves confusion.
  </p>

  <h3>What is global (works everywhere automatically)</h3>
  <table>
    <tr><th>Thing</th><th>Location</th><th>How it's registered</th></tr>
    <tr>
      <td>MCP tools (<code>rag_query</code>, <code>rag_ingest_directory</code>&hellip;)</td>
      <td><code>~/.claude/settings.json</code></td>
      <td>Written by <code>install.py</code> — Claude Code picks them up in every session</td>
    </tr>
    <tr>
      <td>Slash commands (<code>/rag-query</code>, <code>/rag-index</code>&hellip;)</td>
      <td><code>~/.claude/commands/</code></td>
      <td>Copy once from <code>.claude/commands/</code> — available in every project</td>
    </tr>
    <tr>
      <td>RAGStack GUI</td>
      <td><code>http://localhost:7860</code></td>
      <td>Can index any directory path regardless of where it's running from</td>
    </tr>
  </table>

  <h3>What is per-project (needs to be done per codebase)</h3>
  <table>
    <tr><th>Thing</th><th>What to do</th></tr>
    <tr>
      <td>Index (the stored chunks)</td>
      <td>Run <code>/rag-index .</code> in each new project. Clear first with <code>/rag-clear</code>.</td>
    </tr>
    <tr>
      <td>Graphify graph</td>
      <td>Run <code>/graphify .</code> in Claude Code once per project to build <code>graphify-out/graph.json</code>.</td>
    </tr>
  </table>

  <div class="callout warn">
    <strong>Switching projects?</strong> The memory retriever shares one index.
    Run <code>/rag-clear</code> before indexing a new project, otherwise chunks
    from the old project mix into answers.
  </div>

  <h3>Workflow for any new project</h3>
  <ol class="steps">
    <li>
      <div class="step-body">
        <strong>Navigate to your project and open Claude Code</strong>
        <pre><code class="language-bash">cd /path/to/your/project
claude</code></pre>
      </div>
    </li>
    <li>
      <div class="step-body">
        <strong>Clear the previous project's index</strong>
        <pre><code>/rag-clear</code></pre>
      </div>
    </li>
    <li>
      <div class="step-body">
        <strong>Index your project</strong>
        <pre><code>/rag-index .</code></pre>
        This calls <code>rag_ingest_directory</code> via MCP. You can also use the
        GUI <strong>Status &amp; Tools &rarr; Index a directory</strong> and paste any path.
      </div>
    </li>
    <li>
      <div class="step-body">
        <strong>(Optional) Build the knowledge graph</strong>
        <pre><code>/graphify .</code></pre>
        Builds <code>graphify-out/graph.json</code> for graph-based retrieval.
        Requires Claude Code CLI. Only needed if using the Graphify + Ollama preset.
      </div>
    </li>
    <li>
      <div class="step-body">
        <strong>Ask questions</strong>
        <pre><code>/rag-query how does the payment flow work?
/rag-query what calls UserService?</code></pre>
      </div>
    </li>
  </ol>

  <h3>Embeddings — no OpenAI key needed with Ollama</h3>
  <p>
    RAGStack automatically picks the right embedding provider based on your LLM:
  </p>
  <table>
    <tr><th>LLM provider</th><th>Embedder used</th><th>API key needed?</th></tr>
    <tr><td><code>ollama</code></td><td>Ollama embedding endpoint (local)</td><td>No</td></tr>
    <tr><td><code>anthropic</code> / <code>openai</code> / <code>gemini</code></td><td>OpenAI <code>text-embedding-3-small</code></td><td><code>OPENAI_API_KEY</code></td></tr>
    <tr><td>explicit <code>embeddings.provider: none</code></td><td>Null embedder (cache disabled)</td><td>No</td></tr>
  </table>
  <p>
    This means the full pipeline works completely free and key-free when using
    any Ollama preset — including semantic cache hits and query rewriting.
  </p>
</section>

<!-- ============================================================ -->
<section id="config-ref">
  <h2>Configuration Reference</h2>
  <pre><code class="language-yaml"># ragstack.config.yaml -- full reference

llm:
  provider: ollama          # anthropic | openai | gemini | ollama
  model: llama3.2           # any model name for the chosen provider
  max_tokens: 1024
  ollama:
    base_url: http://localhost:11434

layers:

  optimizer:
    backend: rules          # rules | llm | passthrough
    report_savings: true    # print token savings to console
    llm:
      model: claude-haiku-4-5-20251001   # cheapest model for optimization
      max_tokens: 512

  cache:
    backend: memory         # memory | redis | qdrant
    similarity_threshold: 0.92   # 0.0-1.0; higher = stricter matching
    ttl_seconds: 3600            # 0 = never expire
    redis:
      url: redis://localhost:6379
      index_name: ragstack_cache
    qdrant:
      url: http://localhost:6333
      collection: ragstack_cache

  rewriter:
    backend: passthrough    # passthrough | llm | hyde
    model: claude-haiku-4-5-20251001
    strategy: expand        # expand | rephrase
    hyde:
      model: claude-haiku-4-5-20251001

  retriever:
    backend: memory         # memory | graphify | chroma | pinecone | weaviate
    top_k: 8
    graphify:
      graph_path:  ./graphify-out/graph.json
      report_path: ./graphify-out/GRAPH_REPORT.md
      hop_limit: 3
      edge_types: [calls, depends_on, semantically_similar_to, rationale_for]
    chroma:
      host: localhost
      port: 8000
      collection: ragstack_docs
    pinecone:
      index_name: ragstack-index
      environment: us-east-1
    weaviate:
      url: http://localhost:8080
      class_name: Document
    memory:
      docs: []              # pre-seed documents here

  compressor:
    backend: passthrough    # passthrough | reranker | llmlingua
    top_k: 3
    reranker:
      model: cross-encoder/ms-marco-MiniLM-L-6-v2
      score_threshold: 0.3
    llmlingua:
      ratio: 0.4

  prompt_cache:
    backend: none           # anthropic | openai | none
    cached_prefix: |
      You are a precise technical assistant. Answer only from the provided
      context. Cite the source file for every claim you make.

embeddings:
  model: text-embedding-3-small
  dimensions: 1536</code></pre>
</section>

<!-- ============================================================ -->
<section id="backends-ref">
  <h2>Backends Reference</h2>

  <h3>Installing optional backends</h3>
  <pre><code class="language-bash">python install.py --extras redis reranker chroma

# Available extras:
# openai      -- embeddings + GPT models
# redis       -- cache backend
# qdrant      -- cache backend
# reranker    -- sentence-transformers compressor
# llmlingua   -- token compression
# chroma      -- local vector retriever
# pinecone    -- cloud vector retriever
# weaviate    -- cloud vector retriever
# gemini      -- Google LLM provider
# ollama      -- local LLM (free, no API key)</code></pre>

  <h3>LLM providers</h3>
  <table>
    <tr><th>Provider</th><th>Config value</th><th>Env var</th><th>Cost</th></tr>
    <tr><td>Ollama (local)</td><td><code>ollama</code></td><td>None</td><td><strong>Free</strong></td></tr>
    <tr><td>Anthropic</td><td><code>anthropic</code></td><td><code>ANTHROPIC_API_KEY</code></td><td>Pay per token</td></tr>
    <tr><td>OpenAI</td><td><code>openai</code></td><td><code>OPENAI_API_KEY</code></td><td>Pay per token</td></tr>
    <tr><td>Google Gemini</td><td><code>gemini</code></td><td><code>GOOGLE_API_KEY</code></td><td>Pay per token</td></tr>
  </table>
</section>

<!-- ============================================================ -->
<section id="slash-commands">
  <h2>Slash Commands</h2>
  <p>Available in Claude Code after <code>python install.py</code>:</p>
  <table>
    <tr><th>Command</th><th>What it does</th></tr>
    <tr><td><code>/rag-index .</code></td><td>Index the current directory into RAGStack</td></tr>
    <tr><td><code>/rag-query &lt;question&gt;</code></td><td>Search the index and answer the question</td></tr>
    <tr><td><code>/rag-status</code></td><td>Show active backends and index health</td></tr>
    <tr><td><code>/rag-clear</code></td><td>Flush the semantic cache</td></tr>
    <tr><td><code>/rag-add &lt;text&gt;</code></td><td>Add a raw text snippet to the index</td></tr>
  </table>
  <pre><code>/rag-index src/
/rag-query how does the authentication flow work?
/rag-add [api-spec]: All POST /auth/login requests must include a CSRF token.</code></pre>
  <div class="callout tip">
    <strong>Make slash commands global:</strong> By default they are installed into
    <code>.claude/commands/</code> in the RAGStack project. Copy them once to
    <code>~/.claude/commands/</code> and they work in every project:
    <pre><code class="language-bash"># Windows PowerShell
Copy-Item ".claude\commands\*.md" "$HOME\.claude\commands\" -Force

# macOS / Linux
cp .claude/commands/*.md ~/.claude/commands/</code></pre>
  </div>
</section>

<!-- ============================================================ -->
<section id="adding-backend">
  <h2>Adding a New Backend</h2>
  <p>Example: adding a <strong>Milvus</strong> retriever.</p>

  <h4>1. Implement the class in <code>layers/retriever.py</code></h4>
  <pre><code class="language-python">class MilvusRetrieverBackend(RetrieverBackend):
    def __init__(self, embedder, uri: str, collection: str):
        from pymilvus import MilvusClient          # lazy import
        self._embedder   = embedder
        self._client     = MilvusClient(uri=uri)
        self._collection = collection

    def retrieve(self, query: str, top_k: int) -> list[dict]:
        vec = self._embedder.embed(query)
        results = self._client.search(
            collection_name=self._collection,
            data=[vec], limit=top_k,
            output_fields=["text", "source"],
        )
        return [
            {"text": r["entity"]["text"],
             "source": r["entity"]["source"],
             "score": r["distance"], "metadata": {}}
            for r in results[0]
        ]</code></pre>

  <h4>2. Add one line to the registry</h4>
  <pre><code class="language-python">RETRIEVER_BACKENDS["milvus"] = MilvusRetrieverBackend</code></pre>

  <h4>3. Wire it in <code>pipeline.py</code> <code>from_config()</code></h4>
  <pre><code class="language-python">elif ret_backend_name == "milvus":
    m_cfg = ret_cfg.get("milvus", {})
    retriever = RETRIEVER_BACKENDS["milvus"](
        embedder=embedder,
        uri=m_cfg.get("uri", "http://localhost:19530"),
        collection=m_cfg.get("collection", "ragstack_docs"),
    )</code></pre>

  <h4>4. Update <code>ragstack.config.yaml</code></h4>
  <pre><code class="language-yaml">retriever:
  backend: milvus
  milvus:
    uri: http://localhost:19530
    collection: ragstack_docs</code></pre>

  <h4>5. Done</h4>
  <p>
    The MCP server, GUI, slash commands, and all other layers work with zero
    additional changes. Restart Claude Code and the new backend is active.
  </p>

  <div class="callout tip">
    <strong>Dependency policy:</strong> Always lazy-import the backend SDK inside
    <code>__init__</code> or the first method call. Never at module level. This
    keeps the passthrough/memory backends importable without optional packages.
  </div>
</section>

</main>

<script>
  mermaid.initialize({ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' });
  if (typeof hljs !== 'undefined') hljs.highlightAll();

  // Sidebar active-link tracking
  const sections = document.querySelectorAll('section[id]');
  const links = document.querySelectorAll('nav a');
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        links.forEach(l => l.classList.remove('active'));
        const active = document.querySelector('nav a[href="#' + e.target.id + '"]');
        if (active) active.classList.add('active');
      }
    });
  }, { threshold: 0.2 });
  sections.forEach(s => observer.observe(s));
</script>
</body>
</html>
"""
