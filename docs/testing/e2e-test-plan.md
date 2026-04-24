# Signal Archive — End-to-End Test Plan

**Purpose:** Verify every system feature works correctly while generating real research data that permanently enriches the archive. Each test scenario submits genuine content — not throwaway fixtures.

**Production base URL:** `https://signal-archive-api.fly.dev`  
**Website:** (local dev or production deploy)

---

## Prerequisites

```bash
export API_BASE="https://signal-archive-api.fly.dev"
```

---

## Phase 1 — Contributor Setup

Create three distinct contributors to simulate a real multi-user archive.

### 1.1 Create researcher accounts

```bash
# Researcher A — general AI/ML focus
curl -s -X POST "$API_BASE/contributors" \
  -H "Content-Type: application/json" \
  -d '{"handle": "ml-researcher", "display_name": "ML Researcher"}' | tee /tmp/researcher_a.json

# Researcher B — enterprise/cloud focus
curl -s -X POST "$API_BASE/contributors" \
  -H "Content-Type: application/json" \
  -d '{"handle": "cloud-engineer", "display_name": "Cloud Engineer"}' | tee /tmp/researcher_b.json

# signal-bot already exists — used for batch ingestion
```

Save the API keys from the responses:
```bash
export KEY_A=$(cat /tmp/researcher_a.json | python3 -c "import sys,json; print(json.load(sys.stdin)['api_key'])")
export KEY_B=$(cat /tmp/researcher_b.json | python3 -c "import sys,json; print(json.load(sys.stdin)['api_key'])")
export KEY_BOT="7um1wA2C1z365qkQh5Pz7rcqNttIjwwGAmHJPbDZN0E"
```

**Expected:** 201 with `{"handle": "...", "api_key": "..."}` for each.

### 1.2 Verify contributor profiles are readable

```bash
curl -s "$API_BASE/contributors/ml-researcher" | python3 -m json.tool
curl -s "$API_BASE/contributors/cloud-engineer" | python3 -m json.tool
```

**Expected:** 200 with `total_contributions: 0`, `reputation_score: 0.0`.

---

## Phase 2 — Authentication Flow

### 2.1 Exchange API key for JWT

```bash
# Researcher A gets a JWT
JWT_A=$(curl -s -X POST "$API_BASE/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"api_key\": \"$KEY_A\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['jwt'])")

echo "JWT_A: ${JWT_A:0:40}..."
```

**Expected:** 200 with `jwt`, `handle`, `email` fields.

### 2.2 Fetch authenticated profile

```bash
curl -s "$API_BASE/auth/me" \
  -H "Authorization: Bearer $JWT_A" | python3 -m json.tool
```

**Expected:** 200 with `handle: "ml-researcher"`, `total_contributions: 0`.

### 2.3 Retrieve API key via endpoint

```bash
curl -s "$API_BASE/auth/api-key" \
  -H "Authorization: Bearer $JWT_A" | python3 -m json.tool
```

**Expected:** 200 with `api_key` matching `$KEY_A`.

### 2.4 Update display name

```bash
curl -s -X PATCH "$API_BASE/auth/me" \
  -H "Authorization: Bearer $JWT_A" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "ML Researcher — Updated"}' | python3 -m json.tool
```

**Expected:** 200 with updated `display_name`.

### 2.5 Reject invalid API key

```bash
curl -s -X POST "$API_BASE/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"api_key": "invalid-key-000"}' | python3 -m json.tool
```

**Expected:** 401.

---

## Phase 3 — Artifact Submission (New Canonical Questions)

Each submission below creates a new canonical question and a research artifact. Researcher A and the bot submit different perspectives.

### 3.1 Researcher A — LLM fine-tuning techniques

```bash
curl -s -X POST "$API_BASE/artifacts" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY_A" \
  -d '{
    "cleaned_question": "What are the main techniques for fine-tuning large language models?",
    "cleaned_prompt": "Explain the main techniques for fine-tuning LLMs in 2025: full fine-tuning, LoRA, QLoRA, RLHF, DPO, and instruction tuning. Cover compute requirements, data needs, and when to choose each method.",
    "clarifying_qa": [
      {"question": "Open-source or proprietary models?", "answer": "Focus on open-source (Llama, Mistral, Qwen) but note differences with proprietary fine-tuning APIs."}
    ],
    "short_answer": "The dominant techniques are LoRA/QLoRA for parameter-efficient fine-tuning (low VRAM, 1-10% of parameters updated), full fine-tuning for maximum quality on ample hardware, and DPO/RLHF for alignment. For most use cases in 2025, QLoRA + a small curated dataset (1K-10K examples) gives the best quality-to-cost ratio.",
    "full_body": "## LLM Fine-Tuning Techniques (2025)\n\n### Full Fine-Tuning\nUpdates all model parameters. Highest quality but requires significant GPU memory (70B model needs ~8x A100 80GB). Best when you have large, high-quality domain data and dedicated GPU infrastructure.\n\n### LoRA (Low-Rank Adaptation)\nFreezes base model weights and trains small rank-decomposition matrices inserted at attention layers. Typically updates <1% of parameters. Reduces VRAM by 60-80%. Quality close to full fine-tuning for most tasks. Supported by Hugging Face PEFT library.\n\n### QLoRA (Quantized LoRA)\nCombines LoRA with 4-bit quantization of the base model. Enables fine-tuning 70B models on a single A100 80GB. Slight quality loss vs LoRA but dramatically lower cost. The most practical choice for teams without large GPU clusters.\n\n### Instruction Tuning\nFine-tunes on (instruction, output) pairs to make models follow directions. Foundation of ChatGPT-style behavior. Datasets: Alpaca, FLAN, OpenHermes.\n\n### RLHF (Reinforcement Learning from Human Feedback)\nTrain a reward model from human preference data, then use PPO to align LLM outputs with that reward. Expensive, complex, but produces best alignment. Used by OpenAI, Anthropic.\n\n### DPO (Direct Preference Optimization)\nSimpler alternative to RLHF — directly fine-tunes on preference pairs (chosen vs rejected responses) without a separate reward model. Nearly as effective as RLHF at a fraction of the complexity. Now the preferred alignment technique for most labs.\n\n### When to Use What\n| Technique | VRAM | Data needed | Use when |\n|---|---|---|---|\n| QLoRA | Low (1 GPU) | 1K-50K examples | Most domain adaptation |\n| LoRA | Medium | 1K-50K examples | When max quality needed |\n| Full FT | High (8+ GPUs) | 100K+ examples | Max quality, large data |\n| DPO | Medium | 1K-10K pairs | Alignment / safety |\n| RLHF | Very high | 10K+ comparisons | Frontier model alignment |",
    "citations": [
      {"url": "https://arxiv.org/abs/2106.09685", "title": "LoRA: Low-Rank Adaptation of Large Language Models", "domain": "arxiv.org"},
      {"url": "https://arxiv.org/abs/2305.14314", "title": "QLoRA: Efficient Finetuning of Quantized LLMs", "domain": "arxiv.org"},
      {"url": "https://arxiv.org/abs/2305.18290", "title": "Direct Preference Optimization (DPO)", "domain": "arxiv.org"},
      {"url": "https://huggingface.co/docs/peft/index", "title": "Hugging Face PEFT Library", "domain": "huggingface.co"}
    ],
    "run_date": "2025-04-24T00:00:00Z",
    "worker_type": "manual-research",
    "model_info": "claude-sonnet-4-6",
    "source_domains": ["arxiv.org", "huggingface.co"],
    "prompt_modified": false,
    "version": "1.0"
  }' | python3 -m json.tool
```

**Expected:** 201 with new `id` and `canonical_question_id`.

### 3.2 Cloud Engineer — RAG vs fine-tuning decision guide

```bash
curl -s -X POST "$API_BASE/artifacts" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY_B" \
  -d '{
    "cleaned_question": "When should you use RAG versus fine-tuning for LLM customization?",
    "cleaned_prompt": "When is Retrieval-Augmented Generation (RAG) the right choice versus fine-tuning an LLM? Cover knowledge freshness, cost, latency, data privacy, and accuracy trade-offs.",
    "clarifying_qa": [],
    "short_answer": "Use RAG when knowledge changes frequently, data is proprietary/sensitive, or you need source attribution. Use fine-tuning when you need consistent style/format, domain-specific reasoning patterns, or low-latency inference without retrieval overhead. In practice, the best production systems combine both.",
    "full_body": "## RAG vs Fine-Tuning Decision Framework\n\n### Use RAG when:\n- **Knowledge is dynamic:** Product catalogs, regulations, news — anything updated more than quarterly.\n- **Sources matter:** Legal, medical, or compliance contexts where citations are required.\n- **Data is sensitive:** Keep proprietary data out of model weights — it stays in your vector store under your access controls.\n- **Budget is tight:** RAG with a frontier API is cheaper than fine-tuning and serving your own model.\n- **Fast iteration:** Add new documents without retraining.\n\n### Use Fine-Tuning when:\n- **Style consistency:** You need the model to always respond in a specific format, persona, or tone.\n- **Latency matters:** No retrieval hop — the knowledge is baked in.\n- **Domain reasoning:** Teaching the model a new problem-solving pattern (not just facts).\n- **Small context:** If all needed knowledge fits in a fine-tune and never changes.\n\n### Combine both (recommended for production):\n1. Fine-tune for style, format, and domain reasoning.\n2. RAG for facts, documents, and live knowledge.\n\n### Cost comparison (rough estimates, 2025)\n| Approach | Setup cost | Per-query cost | Update cost |\n|---|---|---|---|\n| RAG only | $500-5K | $0.01-0.10 | Low (re-embed docs) |\n| Fine-tune only | $1K-50K | $0.001-0.01 | High (retrain) |\n| RAG + fine-tune | $2K-60K | $0.01-0.05 | Low-Medium |",
    "citations": [
      {"url": "https://arxiv.org/abs/2005.11401", "title": "RAG: Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", "domain": "arxiv.org"},
      {"url": "https://www.pinecone.io/learn/retrieval-augmented-generation/", "title": "Pinecone RAG Guide", "domain": "pinecone.io"}
    ],
    "run_date": "2025-04-24T00:00:00Z",
    "worker_type": "manual-research",
    "model_info": "claude-sonnet-4-6",
    "source_domains": ["arxiv.org", "pinecone.io"],
    "prompt_modified": false,
    "version": "1.0"
  }' | python3 -m json.tool
```

**Expected:** 201, new canonical question.

### 3.3 Signal Bot — Vector databases comparison

```bash
curl -s -X POST "$API_BASE/artifacts" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY_BOT" \
  -d '{
    "cleaned_question": "Comparison of vector databases for AI applications: Pinecone, Weaviate, Qdrant, pgvector",
    "cleaned_prompt": "Compare the leading vector database options for AI/RAG applications in 2025: Pinecone, Weaviate, Qdrant, Chroma, and pgvector. Cover performance, scalability, filtering, pricing, and when to choose each.",
    "clarifying_qa": [
      {"question": "Self-hosted or managed?", "answer": "Both — note which options have managed cloud services vs self-hosted only."}
    ],
    "short_answer": "Pinecone leads for serverless managed deployments with zero ops overhead. Qdrant leads for self-hosted performance and rich filtering. pgvector is best when you are already on PostgreSQL and scale is moderate (<10M vectors). Weaviate excels at hybrid search (vector + keyword). Chroma is the easiest for local development but not production-ready at scale.",
    "full_body": "## Vector Database Comparison (2025)\n\n### Pinecone\n- **Type:** Managed SaaS only\n- **Strengths:** Zero ops, serverless tier available, excellent SDK support, enterprise reliability.\n- **Weaknesses:** Vendor lock-in, cost at scale, no self-hosted option.\n- **Best for:** Teams that want managed infrastructure and fast time-to-production.\n- **Pricing:** Serverless ($0.033/1M vectors stored), Pod-based for high-throughput.\n\n### Qdrant\n- **Type:** Open-source + managed cloud\n- **Strengths:** Best performance benchmark results (Approximate Nearest Neighbor benchmark), rich payload filtering, sparse+dense hybrid search, Rust-based for low latency.\n- **Weaknesses:** Smaller ecosystem than Pinecone.\n- **Best for:** High-performance self-hosted deployments, filtering-heavy workloads.\n- **Pricing:** Open-source free; Qdrant Cloud from $0.\n\n### Weaviate\n- **Type:** Open-source + managed cloud\n- **Strengths:** Best hybrid search (BM25 + vector), built-in vectorization modules, GraphQL API.\n- **Weaknesses:** Higher memory usage, more complex setup.\n- **Best for:** Hybrid search workloads, multi-modal use cases.\n\n### pgvector\n- **Type:** PostgreSQL extension (open-source)\n- **Strengths:** No new infrastructure if you already use Postgres. ACID transactions. Full SQL queries with vector similarity.\n- **Weaknesses:** Performance degrades past ~5-10M vectors without careful tuning. Not purpose-built for ANN.\n- **Best for:** Existing Postgres users, moderate scale (<5M vectors), applications that need SQL + vector queries together.\n\n### Chroma\n- **Type:** Open-source, local-first\n- **Strengths:** Easiest to get started (pip install, in-process). Great for prototyping.\n- **Weaknesses:** Not production-ready at scale. Limited filtering.\n- **Best for:** Local development, small-scale experiments.\n\n### Decision Guide\n- Already on Postgres, <5M vectors → **pgvector**\n- Need managed, zero-ops → **Pinecone**\n- Self-hosted, high performance → **Qdrant**\n- Hybrid search critical → **Weaviate**\n- Just prototyping → **Chroma**",
    "citations": [
      {"url": "https://ann-benchmarks.com/", "title": "ANN Benchmarks", "domain": "ann-benchmarks.com"},
      {"url": "https://docs.pinecone.io/", "title": "Pinecone Documentation", "domain": "docs.pinecone.io"},
      {"url": "https://qdrant.tech/documentation/", "title": "Qdrant Documentation", "domain": "qdrant.tech"},
      {"url": "https://github.com/pgvector/pgvector", "title": "pgvector GitHub", "domain": "github.com"},
      {"url": "https://weaviate.io/developers/weaviate", "title": "Weaviate Documentation", "domain": "weaviate.io"}
    ],
    "run_date": "2025-04-24T00:00:00Z",
    "worker_type": "manual-research",
    "model_info": "claude-sonnet-4-6",
    "source_domains": ["ann-benchmarks.com", "docs.pinecone.io", "qdrant.tech", "github.com", "weaviate.io"],
    "prompt_modified": false,
    "version": "1.0"
  }' | python3 -m json.tool
```

**Expected:** 201, new canonical question.

---

## Phase 4 — Canonical Matching (Same Topic, Second Opinion)

These submissions should match existing canonical questions (similarity ≥ 0.88), triggering a `synthesized_summary` update via LLM.

### 4.1 Second opinion on AI chatbot comparison (matches Phase 0 artifact)

Submit from Researcher B — different angle on the same topic. Should map to the existing ChatGPT/Claude/Gemini canonical question.

```bash
curl -s -X POST "$API_BASE/artifacts" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY_B" \
  -d '{
    "cleaned_question": "ChatGPT vs Claude vs Gemini: which AI assistant is best for enterprise use?",
    "cleaned_prompt": "From an enterprise IT perspective, compare ChatGPT (OpenAI), Claude (Anthropic), and Gemini (Google) for business use. Focus on data privacy, compliance, API reliability, enterprise contracts, and integration with productivity tools.",
    "clarifying_qa": [
      {"question": "Consumer or enterprise API tier?", "answer": "Enterprise tier — ChatGPT Enterprise, Claude for Business/Teams, Gemini for Workspace."}
    ],
    "short_answer": "For enterprise: Claude for Business offers the strongest data privacy guarantees (no training on API data, SOC 2). ChatGPT Enterprise offers best ecosystem and OpenAI API reliability. Gemini for Workspace wins for Google Workspace-native companies with built-in Drive, Docs, and Gmail integration. All three offer enterprise SLAs and DPA agreements.",
    "full_body": "## Enterprise AI Assistant Comparison\n\n### Data Privacy\n- **ChatGPT Enterprise:** Data not used for training. SOC 2 Type II. Azure-hosted.\n- **Claude for Business:** Zero training on API/business data. SOC 2 Type II. HIPAA eligible.\n- **Gemini for Workspace:** Data not used for training when using Workspace plans. ISO 27001, SOC 2, HIPAA eligible.\n\n### Compliance\nAll three support GDPR, HIPAA-eligible tiers, and enterprise DPAs. Claude leads slightly for financial services compliance documentation.\n\n### Productivity Integration\n- **ChatGPT:** Microsoft 365 Copilot (GPT-4 based), Teams integration, Zapier/Make.\n- **Claude:** Slack, Jira, Confluence integrations. Strongest for document-heavy workflows via Projects feature.\n- **Gemini:** Native Google Workspace (Gmail, Docs, Sheets, Meet). Best for Google-first companies.\n\n### Pricing (Enterprise)\n- ChatGPT Enterprise: Custom pricing, ~$30-60/user/month.\n- Claude for Business: $25-40/user/month.\n- Gemini for Workspace: Business+ tier at $22/user/month adds Gemini features.\n\n### Recommendation\n- Google Workspace shop → **Gemini for Workspace**\n- Microsoft 365 shop → **ChatGPT Enterprise** (via Copilot)\n- Compliance-first / document-heavy → **Claude for Business**",
    "citations": [
      {"url": "https://openai.com/enterprise", "title": "ChatGPT Enterprise", "domain": "openai.com"},
      {"url": "https://www.anthropic.com/claude-for-business", "title": "Claude for Business", "domain": "anthropic.com"},
      {"url": "https://workspace.google.com/gemini", "title": "Gemini for Google Workspace", "domain": "workspace.google.com"}
    ],
    "run_date": "2025-04-24T00:00:00Z",
    "worker_type": "manual-research",
    "model_info": "claude-sonnet-4-6",
    "source_domains": ["openai.com", "anthropic.com", "workspace.google.com"],
    "prompt_modified": false,
    "version": "1.0"
  }' | python3 -m json.tool
```

**Expected:** 201. `canonical_question_id` should match the existing `0f04ddaf-da29-4ae0-8ec3-9cb90cb74bfd`. `artifact_count` on that canonical goes to 2. `synthesized_summary` updates to reflect both perspectives.

**Verify:**
```bash
curl -s "$API_BASE/canonical/0f04ddaf-da29-4ae0-8ec3-9cb90cb74bfd" | python3 -m json.tool
# artifact_count should be 2
# synthesized_summary should now incorporate both consumer and enterprise angles
```

### 4.2 Second opinion on agent frameworks (matches Phase 0 artifact)

```bash
curl -s -X POST "$API_BASE/artifacts" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY_A" \
  -d '{
    "cleaned_question": "LangGraph vs AutoGen: which agentic framework should I pick for production in 2025?",
    "cleaned_prompt": "Detailed comparison of LangGraph and AutoGen for building production AI agents. Focus on state management, debugging, human-in-the-loop, error handling, and community support.",
    "clarifying_qa": [],
    "short_answer": "LangGraph wins for production: better state persistence (checkpointing), clearer execution graphs, first-class human-in-the-loop, and LangSmith tracing. AutoGen wins for rapid multi-agent experiments and code-execution pipelines. If deploying to users, choose LangGraph; if building a research prototype with multiple cooperating agents, choose AutoGen.",
    "full_body": "## LangGraph vs AutoGen: Production Decision Guide\n\n### State Management\n- **LangGraph:** First-class checkpointing — agent state is saved to a database (SQLite, Postgres) after every step. Resume from any point. Ideal for long-running workflows.\n- **AutoGen:** Conversational state is in-memory by default. v0.4 adds async persistence but less mature than LangGraph.\n\n### Debugging\n- **LangGraph:** Visual graph inspection via LangGraph Studio. Step-by-step replay. LangSmith integration for full trace.\n- **AutoGen:** Console message logging. AutoGen Studio provides a UI. Harder to trace non-linear multi-agent flows.\n\n### Human-in-the-Loop\n- **LangGraph:** Native `interrupt()` mechanism — pause agent at any node, wait for human input, resume. Cleanly handles approvals.\n- **AutoGen:** `human_input_mode` parameter — simpler but less flexible for async/streaming contexts.\n\n### Error Handling\n- **LangGraph:** Explicit error nodes in the graph. Retry policies per edge.\n- **AutoGen:** Exception handling in message processing loop.\n\n### Community & Ecosystem\n- **LangGraph:** Part of LangChain ecosystem — 80K+ GitHub stars combined. Extensive tutorials.\n- **AutoGen:** Microsoft Research backing. Strong academic community. 35K+ GitHub stars.\n\n### Verdict\nFor production systems serving real users: **LangGraph**. For research and multi-agent experiments: **AutoGen**.",
    "citations": [
      {"url": "https://langchain-ai.github.io/langgraph/concepts/", "title": "LangGraph Concepts", "domain": "langchain-ai.github.io"},
      {"url": "https://microsoft.github.io/autogen/stable/user-guide/", "title": "AutoGen User Guide", "domain": "microsoft.github.io"},
      {"url": "https://github.com/langchain-ai/langgraph", "title": "LangGraph GitHub", "domain": "github.com"}
    ],
    "run_date": "2025-04-24T00:00:00Z",
    "worker_type": "manual-research",
    "model_info": "claude-sonnet-4-6",
    "source_domains": ["langchain-ai.github.io", "microsoft.github.io", "github.com"],
    "prompt_modified": false,
    "version": "1.0"
  }' | python3 -m json.tool
```

**Expected:** `canonical_question_id` matches `8c3bd9bf-...`. `artifact_count` → 2.

---

## Phase 5 — Community Features

### 5.1 Record reuse events

Simulate another team marking they reused a research result:

```bash
# Team A reuses the AI chatbot comparison
curl -s -X POST "$API_BASE/canonical/0f04ddaf-da29-4ae0-8ec3-9cb90cb74bfd/reuse?reused_by=team-alpha" | python3 -m json.tool

# Signal bot reuses the agent framework comparison
curl -s -X POST "$API_BASE/canonical/8c3bd9bf-1083-46f1-a42c-98cc3dab5201/reuse?reused_by=signal-bot" | python3 -m json.tool

# Researcher B reuses governance toolkit comparison
curl -s -X POST "$API_BASE/canonical/cec67901-f9de-40c2-84cc-f54ad8050295/reuse?reused_by=cloud-engineer" | python3 -m json.tool
```

**Expected:** 201 `{"recorded": true}`. `reuse_count` increments on canonical questions.

**Verify:**
```bash
curl -s "$API_BASE/canonical?sort=popular" | python3 -c "
import sys,json
for q in json.load(sys.stdin): print(q['title'][:50], '| reuse:', q['reuse_count'])
"
```

### 5.2 Submit community flags

Get artifact IDs first:
```bash
# Get artifacts for the chatbot canonical
curl -s "$API_BASE/canonical/0f04ddaf-da29-4ae0-8ec3-9cb90cb74bfd/artifacts" | python3 -m json.tool
```

Note artifact IDs, then submit flags:
```bash
ARTIFACT_ID="<id-from-above>"  # replace with actual ID

# Flag as useful
curl -s -X POST "$API_BASE/flags" \
  -H "Content-Type: application/json" \
  -d "{\"artifact_id\": \"$ARTIFACT_ID\", \"flag_type\": \"useful\"}" | python3 -m json.tool

# Flag second artifact as useful too
ARTIFACT_ID2="<second-artifact-id>"
curl -s -X POST "$API_BASE/flags" \
  -H "Content-Type: application/json" \
  -d "{\"artifact_id\": \"$ARTIFACT_ID2\", \"flag_type\": \"useful\"}" | python3 -m json.tool
```

**Expected:** 201 `{"flagged": true}`. `useful_count` increments on artifact.

**Verify flag counts:**
```bash
curl -s "$API_BASE/artifacts/$ARTIFACT_ID" | python3 -c "
import sys,json; a=json.load(sys.stdin)
print('useful:', a['useful_count'], 'stale:', a['stale_count'])
"
```

---

## Phase 6 — Search and Discovery

### 6.1 Semantic search (requires JWT)

```bash
JWT_B=$(curl -s -X POST "$API_BASE/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"api_key\": \"$KEY_B\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['jwt'])")

# Search for a topic in the archive
curl -s "$API_BASE/search?q=how+to+fine-tune+language+models&limit=3" \
  -H "Authorization: Bearer $JWT_B" | python3 -m json.tool
```

**Expected:** Returns ranked results with `similarity` scores. The fine-tuning artifact from Phase 3 should appear.

```bash
# Search for a topic not yet in the archive
curl -s "$API_BASE/search?q=quantum+computing+applications&limit=3" \
  -H "Authorization: Bearer $JWT_B" | python3 -m json.tool
```

**Expected:** Returns results (closest matches by embedding) with low similarity scores.

**Reject unauthenticated search:**
```bash
curl -s "$API_BASE/search?q=LLM+fine-tuning" | python3 -m json.tool
```

**Expected:** 403.

### 6.2 Related questions discovery

```bash
# Get questions related to the AI chatbot comparison
curl -s "$API_BASE/canonical/0f04ddaf-da29-4ae0-8ec3-9cb90cb74bfd/related" | python3 -m json.tool
```

**Expected:** Returns similar canonical questions (agent frameworks, governance alternatives) with similarity scores.

### 6.3 Browse with sorting

```bash
# Sort by most recently updated
curl -s "$API_BASE/canonical?sort=recent&limit=5" | python3 -c "
import sys,json
for q in json.load(sys.stdin): print(q['title'][:60], '| artifacts:', q['artifact_count'])
"

# Sort by most popular (reuse_count)
curl -s "$API_BASE/canonical?sort=popular&limit=5" | python3 -c "
import sys,json
for q in json.load(sys.stdin): print(q['title'][:60], '| reuse:', q['reuse_count'])
"

# Sort by most active (artifact_count)
curl -s "$API_BASE/canonical?sort=active&limit=5" | python3 -c "
import sys,json
for q in json.load(sys.stdin): print(q['title'][:60], '| artifacts:', q['artifact_count'])
"
```

**Expected:** Consistent ordering, no duplicates.

---

## Phase 7 — Reputation Scoring

Run the reputation batch after all submissions and flags above.

```bash
# Set up env with production secrets
export DATABASE_URL=$(op item get dqd6p5r7j5gpom5z7yem4mdata --vault ch-os-priv --fields website)
export OPENAI_API_KEY=$(op item get "openai-api-key" --vault ch-os-priv --fields username)
export API_KEY_SALT=$(op item get y7e2ovwrogyffufrfvjb4mblsq --vault ch-os-priv --fields password)

cd /path/to/signal-archive
python3 reputation/runner.py
```

**Expected:** `[reputation] Updated N contributor(s).`

**Verify scores updated:**
```bash
curl -s "$API_BASE/contributors/signal-bot" | python3 -c "
import sys,json; c=json.load(sys.stdin)
print('contributions:', c['total_contributions'])
print('reputation:', c['reputation_score'])
"
curl -s "$API_BASE/contributors/ml-researcher" | python3 -m json.tool
curl -s "$API_BASE/contributors/cloud-engineer" | python3 -m json.tool
```

**Expected:** Contributors who submitted more artifacts and received `useful` flags have higher reputation scores.

---

## Phase 8 — Synthesized Summary Verification

After Phase 4 (second opinions submitted), verify that `synthesized_summary` was updated for matched canonicals.

```bash
curl -s "$API_BASE/canonical/0f04ddaf-da29-4ae0-8ec3-9cb90cb74bfd" | python3 -c "
import sys,json; q=json.load(sys.stdin)
print('artifact_count:', q['artifact_count'])
print('summary:', q['synthesized_summary'])
"
```

**Expected:** `artifact_count: 2` and the summary synthesizes both the consumer comparison AND the enterprise perspective.

---

## Phase 9 — Input Validation and Error Cases

These verify the API rejects bad input correctly.

```bash
# Missing required field
curl -s -X POST "$API_BASE/artifacts" \
  -H "X-API-Key: $KEY_A" \
  -H "Content-Type: application/json" \
  -d '{"cleaned_question": "test"}' | python3 -m json.tool
# Expected: 422 Unprocessable Entity

# Invalid flag type
ARTIFACT_ID="<any-valid-id>"
curl -s -X POST "$API_BASE/flags" \
  -H "Content-Type: application/json" \
  -d "{\"artifact_id\": \"$ARTIFACT_ID\", \"flag_type\": \"wrong-type\"}" | python3 -m json.tool
# Expected: 422

# Handle already taken
curl -s -X POST "$API_BASE/contributors" \
  -H "Content-Type: application/json" \
  -d '{"handle": "ml-researcher"}' | python3 -m json.tool
# Expected: 409

# Flag non-existent artifact
curl -s -X POST "$API_BASE/flags" \
  -H "Content-Type: application/json" \
  -d '{"artifact_id": "00000000-0000-0000-0000-000000000000", "flag_type": "useful"}' | python3 -m json.tool
# Expected: 404

# Reuse non-existent canonical
curl -s -X POST "$API_BASE/canonical/00000000-0000-0000-0000-000000000000/reuse" | python3 -m json.tool
# Expected: 404

# Search query too short
curl -s "$API_BASE/search?q=ai" -H "Authorization: Bearer $JWT_A" | python3 -m json.tool
# Expected: 422 (min_length=3)
```

---

## Phase 10 — Website UI Walkthrough

Manual verification of the frontend. Open a browser and:

### 10.1 Browse page
- Visit `/` or `/browse`
- Verify all canonical questions appear with titles and summaries
- Sort by Recent / Popular / Active — verify order changes
- Click a canonical question → see its artifacts listed

### 10.2 Search page
- Log in via magic link: `POST /auth/request-login` (enter email → click link in inbox)
- Visit `/search`
- Search for "fine-tuning" → should return the LoRA/QLoRA artifact
- Search for "vector database" → should return pgvector/Pinecone artifact
- Verify result cards show title, summary, similarity score

### 10.3 Account page
- Navigate to `/account` after logging in
- Verify: handle, display_name, reputation score, total_contributions shown
- Click "Edit" → update display_name → save → verify update persists
- Click "Show API Key" → verify key is displayed and can be copied

### 10.4 API Reference page
- Visit `/api-reference`
- Verify all endpoints documented with correct curl examples

### 10.5 Navigation
- Verify `@handle` nav link appears when logged in
- Verify `@handle` links to `/account`
- Verify "API" nav link goes to `/api-reference`
- Log out → verify `@handle` disappears

---

## Phase 11 — Additional Research Submissions (Archive Growth)

Submit these to keep building the archive with real, useful content. Each creates a new canonical topic.

### Research topic backlog (to submit over time)

These are ready to submit using the same `POST /artifacts` pattern with `$KEY_A`, `$KEY_B`, or `$KEY_BOT`:

| # | Topic | Suggested contributor |
|---|---|---|
| 1 | Prompt engineering techniques (chain-of-thought, few-shot, ReAct) | ml-researcher |
| 2 | Open-source LLM comparison: Llama 3, Mistral, Qwen, Gemma | ml-researcher |
| 3 | Observability and monitoring for LLM applications in production | cloud-engineer |
| 4 | Model Context Protocol (MCP): what it is and how to use it | signal-bot |
| 5 | AI safety techniques: constitutional AI, RLAIF, red-teaming | ml-researcher |
| 6 | Cost optimization strategies for LLM APIs in production | cloud-engineer |
| 7 | Evaluation frameworks for LLM outputs: RAGAS, ROUGE, LLM-as-judge | ml-researcher |
| 8 | Multi-modal AI: combining vision, text, and audio in agents | signal-bot |
| 9 | Structured output from LLMs: JSON mode, instructor, outlines | cloud-engineer |
| 10 | Privacy-preserving AI: federated learning and on-device models | ml-researcher |

---

## Checklist Summary

| Phase | What is tested | Real data generated |
|---|---|---|
| 1 | Contributor registration, profile lookup | 2 new contributors |
| 2 | JWT auth, profile, display_name update | — |
| 3 | Artifact submission (4 new topics) | 4 artifacts, 4 canonical questions |
| 4 | Canonical matching, summary update | 2 artifacts matched to existing canonicals |
| 5 | Reuse events, community flags | 3 reuse events, 2 flags |
| 6 | Search, related, browse sorting | — |
| 7 | Reputation batch scoring | Updated scores for all contributors |
| 8 | Synthesized summary LLM update | Updated summaries for matched canonicals |
| 9 | Input validation, 4xx error cases | — |
| 10 | Website UI end-to-end | — |
| 11 | Archive growth (backlog) | 10+ additional artifacts over time |
