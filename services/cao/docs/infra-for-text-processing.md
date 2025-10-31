# Infrastructure for Large-Scale Text-to-JSON Transformation

> Multi-agent orchestration strategy for converting 10s of millions of tokens of technical procedures (with ASCII diagrams and image-based tables) into structured JSON using CAO-coordinated AI agents.

**Context:** Engineering and operating procedures spanning decades with inconsistent formatting, ASCII flow diagrams, image-based tables, and evolved terminology. Target is structured JSON with flexible schema accommodating one-off variations.

---

## Overview

This document describes the ideal infrastructure environment, tooling, and pipeline strategies for an AI agent (or swarm of agents) working within a CAO-orchestrated workflow to transform unstructured technical text into validated JSON documents.

**Core assumptions:**
- Source material: PDFs → extracted text + metadata
- Intermediate artifacts: Text, parsed structures, validation reports
- Target output: `.json` files conforming to evolving schema
- Quality gates: Linter/validator, Git version control, human oversight
- Scale: 10s of millions of tokens; hundreds to thousands of procedures
- Dynamic workflow: All resources (text, schema, tools) subject to change

---

## Ideal Infrastructure Environment

### 1. CAO Server as Orchestration Hub

**Deployment:**
- Single `cao-server` instance running as systemd service
- SQLite database tracking all agent sessions, flows, and work assignments
- Flow scheduler managing batch processing windows
- Inbox service handling agent-to-agent communication

**Why CAO:**
- **Work isolation:** Each procedure family gets dedicated agent terminal (prevents context pollution)
- **Parallel execution:** Multiple extraction agents work independently on procedure subsets
- **Supervisor coordination:** A supervisor agent assigns work, aggregates results, flags edge cases
- **Human-in-loop:** Attach to tmux sessions for live debugging, course correction, approval gates

### 2. Git Repository Structure

```
/workspace/procedure-corpus/
├── raw/                          # Original PDFs, metadata
│   ├── era-1990s/
│   ├── era-2000s/
│   └── era-2010s/
├── extracted/                    # OCR output, cleaned text
│   ├── <procedure-id>.txt
│   └── <procedure-id>.metadata.json
├── intermediate/                 # Parsed structures, pre-validation JSON
│   ├── <procedure-id>.draft.json
│   └── <procedure-id>.parse-notes.md
├── output/                       # Final validated JSON
│   └── <procedure-id>.json
├── schema/                       # JSON schema definitions
│   ├── core-v1.schema.json
│   ├── extensions/
│   │   ├── era-1990s.schema.json
│   │   └── domain-electrical.schema.json
│   └── validation-rules.py
├── tools/                        # Linter, validators, converters
│   ├── validate-json.py
│   ├── ascii-diagram-parser.py
│   └── template-matcher.py
└── agent-prompts/                # Agent profiles for CAO
    ├── extractor-supervisor.md
    ├── extractor-worker.md
    ├── validator-agent.md
    └── schema-evolver.md
```

**Git workflow:**
- `main` branch: validated, human-approved procedures
- `extraction/<batch-id>` branches: agent work-in-progress
- Pull requests for human review before merge
- Tags for schema versions (`schema-v1.0`, `schema-v1.1`)

### 3. Agent Roles and CAO Profiles

**Supervisor Agent (`extractor-supervisor`):**
- Reads work queue (list of procedures needing extraction)
- Assigns work to extractor workers via CAO `assign()` tool
- Aggregates results from workers
- Flags edge cases for human review (confidence < threshold)
- Generates summary reports

**Extractor Worker Agent (`extractor-worker`):**
- Specializes in one procedure family or era
- Receives text + metadata from supervisor
- Applies few-shot prompts specific to procedure type
- Outputs draft JSON + confidence score + parse notes
- Reports back to supervisor via `send_message()`

**Validator Agent (`validator-agent`):**
- Runs linter on draft JSON
- Cross-references original text (catches hallucinations)
- Checks for missing required fields, type mismatches
- Generates validation report with line-number references
- Handoff to human if validation fails

**Schema Evolver Agent (`schema-evolver`):**
- Monitors validation failures across corpus
- Identifies patterns requiring schema extensions
- Proposes schema updates via Git branch + PR
- Documents rationale in PR description

**ASCII Diagram Specialist (`diagram-parser`):**
- Focused on converting ASCII flowcharts to structured graphs
- Uses vision-language reasoning (GPT-4o, Claude 3.5) to interpret box-drawing characters
- Outputs Mermaid/Graphviz intermediate, then converts to JSON

### 4. Data Storage and State Management

**SQLite Database (CAO):**
- Tracks which procedures assigned to which agents
- Stores agent terminal IDs, status, completion timestamps
- Inbox messages for coordination

**Redis Cache (Optional):**
- Cache parsed intermediate structures (TTL: 24 hours)
- Store few-shot prompt templates by procedure family
- Memoize schema validation results (avoid redundant checks)

**Parquet/DuckDB (Telemetry):**
- Log every extraction attempt: procedure_id, agent_id, timestamp, confidence, validation_status
- Fast aggregation queries: "Which procedure families have <80% success rate?"
- Agent performance metrics: "Which worker has highest hallucination rate?"

**File System:**
- Working directories per agent terminal: `~/.wepppy/cao/agent-context/<terminal-id>/`
- Agent can read/write local files, commit to Git branches
- Supervisor aggregates outputs from worker directories

### 5. Human Oversight Interface

**Web Dashboard (FastAPI + HTMX):**
- List view: All procedures with status (pending/in-progress/validated/failed)
- Detail view: Side-by-side original text vs. draft JSON
- Approval workflow: Thumbs up/down, inline comments
- Schema browser: Current schema + proposed extensions
- Agent activity monitor: Live view of which agents are working on what

**Tmux Access:**
- Attach to any agent terminal: `tmux attach -t cao-<session>`
- Inspect logs: `tail -f ~/.wepppy/cao/logs/terminal/<terminal-id>.log`
- Manual intervention: Type corrections directly into agent session

**GitHub Integration:**
- Agents create PRs for completed batches
- Human reviewers approve/request changes
- CI runs validation suite on PR (linter, schema compliance, text span checks)

---

## Toolset for Text and JSON Manipulation

### Core Tools (Available to All Agents)

#### 1. Text Processing

**`markdown-extract` (Rust-based):**
- Extract sections from documentation by heading pattern
- Useful for isolating procedure steps from larger documents
- Already integrated in CAO via Python bindings

```bash
markdown-extract "Installation" procedure.md --no-print-matched-heading
```

**`jq` (JSON Query):**
- Inspect, filter, transform JSON from command line
- Validate structure: `jq empty procedure.json` (exits non-zero if invalid)
- Extract fields for comparison: `jq '.steps[].description' procedure.json`

**`difftastic` or `delta` (Structural Diff):**
- Human-readable diffs for JSON (better than line-based diff)
- Agents use to generate change summaries for human review

```bash
difft original.json updated.json
```

**`ripgrep` (rg):**
- Fast text search across corpus
- Find similar procedures: `rg "Emergency Shutdown" extracted/`
- Identify terminology shifts: `rg -i "colour|color" extracted/`

#### 2. JSON Schema Validation

**`jsonschema` (Python CLI):**
- Validate JSON against schema
- Return detailed error messages with JSON path references

```bash
jsonschema -i output/proc-123.json schema/core-v1.schema.json
```

**Custom Linter (`tools/validate-json.py`):**
- Extends JSON schema with domain-specific rules
- Checks cross-field consistency (e.g., step IDs referenced in flowchart exist)
- Validates text span anchors (quoted text from original exists)
- Outputs structured report (JSON or markdown)

```python
# Example linter output
{
  "procedure_id": "proc-123",
  "schema_version": "core-v1",
  "errors": [
    {"type": "missing_field", "path": "$.steps[3].conditions", "severity": "error"},
    {"type": "hallucination", "path": "$.steps[1].description", "original_text": "...", "severity": "warning"}
  ],
  "confidence": 0.85
}
```

#### 3. Git Integration

**`gh` (GitHub CLI):**
- Create branches: `gh repo create-branch extraction/batch-42`
- Open PRs: `gh pr create --title "Extract procedures 100-150" --body "Confidence: 92%"`
- Check PR status: `gh pr status`
- Agents use for automated PR workflow

**`git-absorb` (Optional):**
- Automatically fixup commits during iterative refinement
- Useful when validator finds errors and worker re-extracts

#### 4. ASCII Diagram Parsing

**Custom Parser (`tools/ascii-diagram-parser.py`):**
- Uses regex + heuristics to detect box-drawing characters
- Converts to intermediate graph representation (nodes, edges)
- LLM interprets semantic meaning (decision points, actions, loops)

```bash
python tools/ascii-diagram-parser.py extracted/proc-123.txt --section "Flow Diagram"
# Output: Mermaid syntax or JSON graph structure
```

**Vision API Fallback:**
- For complex diagrams, render ASCII as image (monospace font)
- Send to GPT-4o vision endpoint with prompt: "Describe this flowchart step-by-step"
- Parse natural language description into structured JSON

#### 5. OCR Post-Processing (For Image Tables)

**`ocrmypdf` or Cloud APIs:**
- Extract tables from images using Azure Document Intelligence, AWS Textract, or Google Document AI
- Return structured table data (rows, columns, cells)

**LLM Cleanup:**
- Pass OCR output + domain context to LLM: "Fix OCR errors in this table using engineering terminology"
- Compare corrected version against original image (human spot-check)

### Agent-Specific Tooling

**Extractor Worker:**
- Few-shot prompt library (indexed by procedure family)
- Template matcher: `tools/template-matcher.py` (identifies which prompt template to use)
- Confidence scorer: Outputs 0.0-1.0 based on parse difficulty, missing fields, ambiguity

**Validator Agent:**
- Text span checker: Ensures all quoted text in JSON exists in original
- Cross-reference database: Links procedure IDs to related docs
- Hallucination detector: Flags suspiciously specific details not present in source

**Schema Evolver:**
- Schema diff tool: Compares proposed schema vs. current
- Impact analyzer: "How many existing procedures break with this change?"
- Migration script generator: Produces transformation code for schema upgrades

---

## Pipeline Strategies to Combat Context Size

### 1. Hierarchical Decomposition

**Problem:** 10M+ token corpus won't fit in any context window.

**Solution:** Supervisor/worker pattern with chunking.

```
Supervisor Agent
  ↓
  ├─ assign(worker-1, "Procedures 1-50")
  ├─ assign(worker-2, "Procedures 51-100")
  ├─ assign(worker-3, "Procedures 101-150")
  └─ ...
  ↓
Workers extract in parallel, report back
  ↓
Supervisor aggregates, flags outliers for human review
```

**Chunking strategy:**
- By procedure family (electrical, mechanical, safety)
- By era (1990s, 2000s, 2010s) if terminology/format differs
- By document length (short procedures vs. complex multi-page)

**Context per worker:**
- Original text for assigned procedures (~10-50K tokens)
- Few-shot examples for that family (~5-10K tokens)
- Schema definition (~2-5K tokens)
- **Total:** 20-70K tokens per worker (well within GPT-4/Claude limits)

### 2. Incremental Streaming Pattern

**Problem:** Long procedures might exceed worker context even after chunking.

**Solution:** Stream-and-aggregate.

1. Worker requests procedure text from supervisor
2. Supervisor sends text in chunks (e.g., by section: Overview, Steps 1-10, Steps 11-20, etc.)
3. Worker processes each chunk, builds partial JSON
4. Worker merges chunks into complete JSON at end
5. Worker validates merge consistency (step numbering continuous, cross-references valid)

**CAO workflow:**
```python
# Worker agent receives: "Extract procedure-123 in streaming mode"
# Worker sends_message(supervisor): "Ready for chunk 1"
# Supervisor sends_message(worker): "Chunk 1: Overview section"
# Worker processes, sends_message(supervisor): "Ready for chunk 2"
# ...
# Worker: "All chunks received, validating merge"
# Worker: "Extraction complete, confidence: 0.91"
```

### 3. Memoization and Deduplication

**Problem:** Similar procedures require re-parsing similar structures.

**Solution:** Cache intermediate parses.

- **Redis cache key:** `hash(procedure_text_chunk)` → parsed structure
- Before extracting, worker checks cache: "Has this exact text been parsed before?"
- If hit, reuse structure, only customize procedure-specific fields
- If miss, parse and cache result (TTL: 7 days)

**Example:**
- 100 procedures start with identical "Safety Precautions" section
- First extraction parses and caches it
- Next 99 extractions retrieve from cache (~10ms vs. 5s LLM call)

### 4. Few-Shot Prompt Compression

**Problem:** Few-shot examples consume significant context.

**Solution:** Dynamic prompt selection.

- Maintain library of few-shot examples indexed by procedure characteristics:
  - Length (short/medium/long)
  - Has ASCII diagram (yes/no)
  - Has tables (yes/no)
  - Era (1990s/2000s/2010s)
- Worker agent uses `tools/template-matcher.py` to select 2-3 most relevant examples
- Reduces prompt overhead from 10K tokens (full library) to 3K tokens (targeted examples)

---

## Pipeline Strategies to Combat Hallucinations

### 1. Text Span Anchoring

**Technique:** Every assertion in JSON must reference original text.

**Implementation:**
- JSON schema includes `text_span` fields:
  ```json
  {
    "step": 3,
    "description": "Open valve A to 50%",
    "text_span": {
      "start_char": 1234,
      "end_char": 1267,
      "quote": "Open valve A to 50%"
    }
  }
  ```
- Validator checks: `original_text[1234:1267] == "Open valve A to 50%"`
- Flags hallucinations: Description doesn't match quoted text

**Agent prompt guidance:**
```
When extracting step descriptions, ALWAYS:
1. Copy exact text from source document
2. Include start/end character positions
3. If paraphrasing necessary, mark with "paraphrased": true and provide original quote
```

### 2. Multi-Pass Validation

**Pass 1: Structural validation (fast, automated)**
- JSON schema compliance
- Required fields present
- Types correct (strings, numbers, arrays)

**Pass 2: Semantic validation (LLM-assisted)**
- Validator agent re-reads original text
- Asks: "Does this JSON accurately represent the procedure?"
- Generates confidence score (0.0-1.0)
- Flags discrepancies for human review

**Pass 3: Cross-document consistency (batch)**
- Compare procedure against related procedures
- Check: Do similar procedures use similar terminology?
- Flag outliers: "Procedure 123 uses 'colour' while 99% of corpus uses 'color'"

### 3. Confidence Thresholding

**Extractor worker outputs confidence score:**
- 0.95-1.0: High confidence (auto-approve)
- 0.80-0.95: Medium confidence (validator review)
- <0.80: Low confidence (human review)

**Confidence factors:**
- Text clarity (OCR quality, formatting consistency)
- Template match (how well does procedure fit known patterns)
- Ambiguity (parsing produced multiple interpretations)
- Completeness (all required fields extracted)

**CAO flow:**
```yaml
---
name: batch-extraction-review
schedule: "0 18 * * *"  # 6pm daily
agent_profile: validator-agent
script: ./check-pending-extractions.sh
---

Review all extractions with confidence < 0.80 from today:
[[procedure_list]]

For each procedure:
1. Compare draft JSON against original text
2. Identify hallucinations or errors
3. Update JSON or flag for human review
4. Log validation results
```

### 4. Adversarial Validator

**Concept:** Separate agent tries to find errors in extraction.

**Workflow:**
1. Extractor worker produces draft JSON
2. Adversarial validator receives: original text + draft JSON (NOT the extractor's reasoning)
3. Validator attempts to:
   - Find statements in JSON not supported by text
   - Find information in text missing from JSON
   - Identify type/format errors
4. Validator produces error report
5. If errors found, handoff back to extractor for revision
6. Iterate until validator approves or max rounds exceeded (then human review)

**CAO orchestration:**
```python
# Supervisor agent
result = handoff("extractor-worker", f"Extract {procedure_id}")
validation = handoff("validator-agent", f"Validate {result}")

if validation.status == "APPROVED":
    commit_to_git(procedure_id)
elif validation.status == "ERRORS" and validation.round < 3:
    # Retry with validator feedback
    result = handoff("extractor-worker", f"Re-extract {procedure_id} addressing: {validation.errors}")
else:
    # Flag for human
    create_pr_for_review(procedure_id, result, validation)
```

### 5. Human Spot Checks with Active Learning

**Random sampling:**
- Every 50th extraction gets human review regardless of confidence
- Builds ground truth dataset for calibrating confidence scores

**Active learning:**
- Human corrections fed back into few-shot prompt library
- "When you corrected procedure-123, you changed X to Y. Why?"
- Supervisor agent updates prompts to avoid similar errors

**Feedback loop:**
```
Extraction → Human review → Correction notes → Prompt update → Re-extraction of similar procedures
```

---

## Orchestration Workflow Example

### Batch Processing Flow

**Goal:** Extract 500 procedures (era: 2000s, family: electrical safety)

**Setup:**
1. Supervisor agent reads work queue: `extracted/manifest-2000s-electrical.json`
2. Divides into 10 batches of 50 procedures each
3. Creates Git branch: `extraction/2000s-electrical-batch1`

**Execution:**
```python
# Supervisor agent (pseudo-code from agent's perspective)

# 1. Assign work to workers
workers = []
for batch_id in range(1, 11):
    terminal_id = assign(
        agent_profile="extractor-worker-electrical",
        message=f"Extract procedures {batch_id*50-49} to {batch_id*50} from era 2000s",
        callback_message="Report extraction complete with confidence scores"
    )
    workers.append(terminal_id)

# 2. Wait for workers to report back (via inbox)
# (Supervisor becomes IDLE, inbox delivers messages as workers complete)

# 3. Aggregate results
results = []
for worker_id in workers:
    result = get_terminal_output(worker_id)
    results.append(result)

# 4. Identify edge cases
low_confidence = [r for r in results if r.confidence < 0.80]

# 5. Validator review for low confidence
for proc in low_confidence:
    validation = handoff(
        agent_profile="validator-agent",
        message=f"Validate {proc.id}: confidence was {proc.confidence}"
    )
    if validation.approved:
        proc.confidence = validation.new_confidence
    else:
        flag_for_human_review(proc)

# 6. Commit approved extractions
git_commit_all_approved()
create_pr("Batch 1: 500 procedures, 92% auto-validated")

# 7. Notify human
send_slack_message("Batch 1 complete. PR ready for review: <link>")
```

**Human review:**
- Opens PR, sees dashboard with:
  - 460 procedures auto-approved (confidence > 0.95)
  - 30 procedures validator-approved (confidence 0.80-0.95)
  - 10 procedures flagged for review (confidence < 0.80)
- Spot-checks 5 random auto-approved (all look good)
- Reviews 10 flagged procedures (makes corrections inline)
- Approves PR, merges to `main`

**Iteration:**
- Supervisor launches next batch (batch 2)
- Schema evolver notices 3 procedures in batch 1 required new extension fields
- Schema evolver opens PR proposing schema update
- After human approval, supervisor re-runs affected procedures with new schema

---

## Monitoring and Telemetry

### Real-Time Dashboard

**Metrics:**
- Procedures extracted (total, per hour, per agent)
- Average confidence score (rolling 24-hour window)
- Validation pass rate (auto-approved vs. flagged)
- Schema coverage (% of procedures using each schema version)
- Agent utilization (how many workers active, idle, blocked)

**Alerts:**
- Confidence score drops below 0.70 for >10% of batch
- Validation failure rate exceeds 20%
- Worker agent crashes or times out
- Schema evolution PR pending >24 hours

### Logs and Audit Trail

**SQLite queries:**
```sql
-- Which procedures took longest to extract?
SELECT procedure_id, agent_id, duration_seconds 
FROM extractions 
ORDER BY duration_seconds DESC 
LIMIT 10;

-- Which agent has highest approval rate?
SELECT agent_id, COUNT(*) as total, 
       SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) as approved
FROM extractions 
GROUP BY agent_id;

-- Procedures requiring human review
SELECT procedure_id, confidence, error_reason 
FROM extractions 
WHERE status='flagged_for_review';
```

**Parquet export:**
```python
# Export telemetry for analysis
duckdb.sql("""
  COPY (SELECT * FROM extractions WHERE batch_id = 1) 
  TO 'telemetry/batch-1-extractions.parquet' 
  (FORMAT PARQUET)
""")
```

---

## Infrastructure Summary

**Minimum viable setup:**
- CAO server running on single machine (systemd service)
- Git repository for corpus and schemas
- Python 3.11+ with libraries: `jsonschema`, `jq`, `ripgrep`
- 4-8 agent profiles (supervisor, worker, validator, schema-evolver)
- SQLite database (CAO built-in)
- Web dashboard (FastAPI + HTMX, ~500 LOC)

**Production setup:**
- Same as above, plus:
- Redis cache for intermediate structures (optional but recommended)
- DuckDB/Parquet for telemetry (fast aggregation queries)
- CI/CD pipeline (GitHub Actions): runs linter on every PR
- Monitoring (Prometheus + Grafana): dashboards for extraction metrics
- Scheduled flows: nightly batch processing, weekly schema consistency checks
- Human review queue (web interface): side-by-side text/JSON comparison

**Scaling considerations:**
- Single CAO server can orchestrate 10-50 concurrent agents (limited by machine resources)
- For >50 agents, consider distributed CAO (multiple servers with shared database)
- For >1M procedures, use message queue (RabbitMQ, Redis Streams) instead of CAO inbox
- For teams >5 humans, add role-based access control to web dashboard

---

## Agent Profile Examples

### Extractor Worker Profile

```markdown
---
name: extractor-worker-electrical
description: Extracts electrical safety procedures (2000s era) into structured JSON
---

You are an expert at converting technical procedures into structured JSON.

**Your task:**
1. Read the provided procedure text (electrical safety, 2000s era)
2. Identify: title, purpose, safety warnings, step-by-step instructions, conditions, decision points
3. Output JSON conforming to schema: `schema/core-v1.schema.json` + `schema/extensions/era-2000s.schema.json`

**Critical requirements:**
- Include `text_span` for every assertion (start_char, end_char, quote from original)
- If text is ambiguous, note in `parse_notes` field
- Output confidence score (0.0-1.0) based on clarity and completeness
- NEVER invent information not present in source text

**Few-shot examples:**
[Load 3 examples dynamically based on procedure characteristics]

**Tools available:**
- `tools/ascii-diagram-parser.py` for flowcharts
- `jq` for JSON validation
- `git` for committing output

**Output format:**
```json
{
  "procedure_id": "...",
  "confidence": 0.92,
  "json_output": { ... },
  "parse_notes": "Ambiguity in step 3: 'partially open' lacks numeric threshold"
}
```

When complete, report back to supervisor: "Extraction complete for <procedure_id>, confidence: <score>"
```

### Validator Agent Profile

```markdown
---
name: validator-agent
description: Validates extracted JSON against original text and schema
---

You are a meticulous validator. Your job is to find errors, hallucinations, and inconsistencies in extracted procedures.

**Your task:**
1. Receive: original procedure text + draft JSON
2. Validate:
   - JSON schema compliance (`jsonschema -i <file> schema/core-v1.schema.json`)
   - All `text_span` quotes match original text exactly
   - No information in JSON that isn't supported by text
   - No information in text that's missing from JSON
3. Output validation report with:
   - Status: APPROVED / ERRORS
   - Error list (if any) with JSON path, description, severity
   - Revised confidence score

**You are NOT trying to fix errors—just identify them.**

**Tools available:**
- `tools/validate-json.py` (custom linter)
- `jq` for JSON queries
- `difft` for comparing drafts

**Output format:**
```json
{
  "procedure_id": "...",
  "status": "ERRORS",
  "errors": [
    {"path": "$.steps[2].description", "type": "hallucination", "severity": "error", "detail": "Step says 'wait 30 seconds' but text says 'wait briefly'"}
  ],
  "confidence": 0.73
}
```

If APPROVED, say: "Validation passed for <procedure_id>"
If ERRORS, report back to supervisor with error count and severity breakdown.
```

---

## Further Reading

- [CAO README](../README.md) — Core orchestration concepts
- [CAO CODEBASE](../CODEBASE.md) — Architecture details
- [Agent Profile Guide](agent-profile.md) — Writing effective agent prompts
- [Flow Examples](../examples/) — Scheduled automation patterns

**Wepppy docs:**
- [God-Tier Prompting Strategy](../../../docs/god-tier-prompting-strategy.md) — Prompt engineering principles
- [Work Packages](../../../docs/work-packages/) — Multi-agent coordination examples

---

## Conclusion

This infrastructure leverages CAO's strengths:
- **Isolation:** Each agent works on manageable chunks (20-70K tokens)
- **Coordination:** Supervisor orchestrates without centralizing all context
- **Observability:** Tmux access + telemetry + Git history provide full audit trail
- **Human oversight:** Approval gates at batch boundaries, not per-procedure (reduces bottleneck)

**Key anti-patterns to avoid:**
- ❌ Single agent processing entire corpus (context explosion)
- ❌ No validation layer (hallucinations proliferate)
- ❌ Schema rigidity (forces bad fits instead of evolving)
- ❌ No human feedback loop (agents repeat same errors)

**Success metrics:**
- 95%+ auto-validation rate (only 5% need human review)
- <0.5% hallucination rate (caught by text span validation)
- Schema covers 90%+ of procedures without one-off hacks
- Human review time <10 minutes per 50 procedures

This approach is tractable for 10M+ token corpus with current LLM capabilities, assuming proper tooling and orchestration discipline.
