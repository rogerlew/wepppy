# God-Tier Prompting Strategy for AI-Assisted Development

> A generalized framework for composing agent prompts that deliver consistent, high-quality results across any complex, repetitive development task.

**Core Insight:** AI agents are deterministic functions that need explicit inputs, clear interfaces, validation gates, and observable outputs. By treating documentation as specification and tasks as mechanical transformations, we can achieve 10–50x productivity gains on pattern-based work.

**Proven Results:** Used to migrate 25+ JavaScript controllers (~23,300 LOC) from jQuery to vanilla helpers in **1 day** with zero regressions.

---

## Terminology

**Follow-up Agent (Worker Agent):**  
An AI assistant that executes a task in a fresh conversation with no memory of prior planning discussions. The agent must rely entirely on the prompt and referenced documentation. Can be the same model in a new session, a different AI instance, or even a different model entirely (Claude → GPT-5).

**Lead Agent (Work-Package Manager):**  
An AI assistant that maintains context across planning sessions, tracks progress, decomposes work into subtasks, writes standardized prompts for workers, and validates completed work. Retains memory of the project state and coordinates parallel execution.

**Anchor Documents:**  
Permanent documentation that serves as the specification and ground truth: architecture guides, workflow processes, coding standards, API contracts. These are cited in every prompt to ensure consistent interpretation.

**Working Set:**  
The explicit enumeration of files an agent should read (inputs), modify (outputs), reference (dependencies), or avoid (exclusions). Eliminates discovery ambiguity.

**Deliverables:**  
Atomic, independently verifiable sections of work with clear success criteria. Each deliverable should be checkpointable and reportable in the handoff summary.

**Validation Gates:**  
Automated tests, linters, builds, and manual checks that must pass before work is considered complete. These are executable commands with expected results, not suggestions.

**Observable Outputs:**  
Concrete examples of what correct implementation looks like: before/after code snippets, reference implementations, anti-patterns to avoid. Shows rather than tells.

---

## Architectural Pattern: Lead-Worker Orchestration

The controller modernization used a two-tier agent architecture:

### Lead Agent (Work-Package Manager)
**Context window:** Persistent across planning sessions  
**Responsibilities:**
- Decompose large work (25 controllers) into atomic tasks
- Track completion status across all subtasks
- Write standardized prompts following this framework
- **Iterate prompts with agent feedback** until "god-tier"
- Validate worker output and catch regressions
- Maintain architectural consistency
- Update documentation and checklists

**Memory requirement:** Must retain project state across conversations

### Worker Agents (Execution Agents)
**Context window:** 65% consumed by prompt (~177k of 272k tokens)  
**Responsibilities:**
- Execute exactly one controller modernization
- Follow prompt instructions mechanically
- Run validation gates
- Report results in standardized handoff format
- **No memory of previous work** - each is a fresh instance

**Memory requirement:** Stateless (prompt provides all context)

### Prompt Refinement Process (Critical Discovery)

The "god-tier" prompt didn't emerge fully formed—it was **iteratively refined** through agent feedback:

**1. Assess Feasibility:**
- "Given this prompt, can you thoroughly review all details needed for one controller?"
- "What's feasible in a single pass without follow-up questions?"
- "What information is missing or ambiguous?"

**2. Agent Feedback Loop:**
- Draft initial prompt based on framework
- Ask agent: "What would prevent you from completing this in one shot?"
- Agent identifies gaps, ambiguities, missing context
- **Agent suggests architectural improvements** (e.g., event-driven architecture)
- Refine prompt based on feedback
- Repeat until agent confirms: "Yes, I can execute this completely"

**3. Key Agent Contributions:**
- **Event-driven architecture suggestion:** Agent recommended `useEventMap` pattern for type-safe events
- **Validation gate ordering:** Agent suggested running lints before tests (faster feedback)
- **Reference implementation requests:** Agent asked for concrete examples beyond abstract patterns
- **Handoff format specification:** Agent needed explicit output structure for validation

**4. Convergence Criteria:**
When the agent can answer "yes" to:
- ✅ "Can you complete this without asking clarifying questions?"
- ✅ "Do you know exactly which files to read and modify?"
- ✅ "Are success criteria unambiguous and testable?"
- ✅ "Do you have examples showing what 'correct' looks like?"
- ✅ "Can you validate your work before handoff?"

**Result:** The final prompt (177k tokens) was agent-validated as complete before executing against 25 controllers.

### Why This Works

**Scalability:**  
- Workers execute in parallel (all 25 controllers simultaneously if desired)
- No coordination needed between workers
- Lead handles serialization points (documentation updates, progress tracking)

**Reliability:**  
- Workers are disposable (failure = retry with fresh instance)
- Large prompts (65% context) ensure completeness without conversation
- Lead validates output, catches edge cases workers missed
- **Prompt pre-validated by agent feedback** reduces worker failure rate

**Cost Efficiency:**  
- Workers aren't reused (context window near capacity)
- Lead maintains long-running context (planning, validation, documentation)
- Most tokens spent on execution, not coordination
- **Upfront prompt iteration cheaper than worker retries**

### Context Window Economics

**Observed constraints:**
- GPT-5 context: 272k tokens
- Typical controller prompt: ~177k tokens (65%)
- Remaining budget: ~95k tokens (responses, tool calls)

**Design implications:**
- ✅ Prompts must be complete and self-contained (no follow-up questions)
- ✅ Workers are single-use (near context limit prevents conversation)
- ✅ Lead maintains state, workers are stateless executors
- ✅ **Prompt iteration happens with lead, not workers** (cheaper than worker retries)
- ❌ Can't iterate with worker (too expensive, near limit)
- ❌ Can't reuse worker for multiple controllers (prompt too large)

**This forces excellence in prompt composition:** Everything must be right the first time.

**The iteration paradox:** 
- Workers can't iterate (context too large)
- But prompts must be perfect for workers
- **Solution:** Lead iterates the prompt template with agent feedback before deploying to workers
- Investment: 5–10 iterations with lead to refine prompt
- Payoff: 25 workers execute successfully without retries

---

## Meta-Strategy: Prompt Refinement Through Agent Feedback

Before deploying prompts to worker agents, iterate the prompt design with the lead agent using this feedback protocol:

### Step 1: Draft Initial Prompt
Compose the prompt following the 6-part framework:
1. Anchor documents
2. Working set
3. Deliverables breakdown
4. Validation commands
5. Target patterns
6. Positive framing

### Step 2: Feasibility Assessment
Ask the lead agent explicitly:
```
"Given this prompt, can you thoroughly review all details needed 
to complete [task] in one pass without follow-up questions?

Specifically:
- Is any information missing or ambiguous?
- Are there architectural decisions you'd need to make?
- Do you need examples you don't have?
- Are success criteria testable and unambiguous?
- Would you know when you're done?"
```

### Step 3: Incorporate Agent Feedback
The agent will identify gaps such as:
- Missing context (what files to read)
- Ambiguous requirements (what counts as "modernized")
- Architectural decisions needed (how to structure events)
- Unclear success criteria (how to validate)
- Missing examples (what does good look like)

**Critical insight:** Agents often suggest **better architectural patterns** than humans initially conceived. Be open to these suggestions.

### Step 4: Iterate Until "God-Tier"
Refine the prompt based on feedback and re-assess:
```
"With these updates, can you now complete the task in one shot?"
```

Continue until the agent confirms all criteria met.

### Step 5: Convergence Checklist
The prompt is "god-tier" when the agent answers "yes" to:
- [ ] Can you complete this without asking clarifying questions?
- [ ] Do you know exactly which files to read and modify?
- [ ] Are architectural patterns and conventions clear?
- [ ] Are success criteria unambiguous and testable?
- [ ] Do you have concrete examples of correct implementation?
- [ ] Can you validate your work before handoff?
- [ ] Do you know what to document and where?

### Step 6: Deploy to Workers
Once validated, the prompt can be reused across all similar tasks (25 controllers) with confidence.

### Agent-Contributed Improvements (Controller Modernization)

**Architectural suggestions:**
- **Event-driven architecture:** Agent suggested `useEventMap` with typed event names for compile-time safety
- **Bootstrap protocol:** Agent recommended idempotent `bootstrap(context, meta)` over constructor initialization
- **Scoped emitters:** Agent proposed per-controller event namespacing to prevent collisions

**Clarity improvements:**
- **Validation ordering:** "Run lints before tests (faster feedback loop)"
- **Reference implementation specificity:** "Don't just say 'see climate.js', quote the exact pattern with line numbers"
- **Handoff format:** "Specify exactly what goes in the summary: code changes, test commands run, pass/fail results, remaining risks"

**Scope adjustments:**
- **File boundary clarity:** "Explicitly list what NOT to touch (e.g., vendor files, legacy templates)"
- **Test coverage expectations:** "State minimum: controller test + route test, optional: full suite"
- **Documentation granularity:** "Update README.md controller reference section, AGENTS.md quick reference, and domain plan events table"

### Why Agent Feedback Works

**Agents as specification validators:**
- They immediately spot ambiguities humans overlook
- They expose gaps in assumed context
- They identify decision points that need explicit guidance
- They suggest architectural improvements from broader pattern knowledge

**Cheaper than debugging:**
- Iterating prompts with lead: ~5k tokens × 10 iterations = 50k tokens
- Worker executing bad prompt + debugging: 177k tokens × 2+ attempts = 354k+ tokens
- **7x cost savings** plus time savings

**Quality amplification:**
- Human writes prompt based on domain knowledge
- Agent validates prompt against execution requirements
- **Result:** Prompts that work for both human intent and machine execution

**Unexpected benefits:**
- Agents contribute architectural insights humans didn't consider
- Cross-pollination from agent's training across many codebases
- Forces human to be explicit about implicit knowledge

---

## Universal Framework

The goal of every prompt is to give a follow-up agent enough context, constraints, and acceptance criteria to ship complete work without guesswork, human intervention, or architectural ambiguity.

### The Recipe (Applicable to Any Task)

## 1. Anchor in Shared Truth (Deterministic Inputs)

**Principle:** AI agents don't have memory across sessions. Anchor every prompt in the same foundational documents to ensure consistent interpretation.

**Universal Application:**
- **Architecture docs:** Cite the canonical vision/patterns document (e.g., `architecture.md`, `design-principles.md`, `api-contracts.md`)
- **Process docs:** Reference the step-by-step workflow (e.g., `development-workflow.md`, `testing-strategy.md`)
- **Domain context:** Point to task-specific plans/specs (e.g., feature specs, migration plans, API schemas)

**Why it works:** Documentation becomes the **specification**, not just guidance. Anchoring prevents drift across parallel tasks and ensures every agent operates from the same ground truth.

**Controller Refactor Example:**
- Architecture: `docs/dev-notes/controller_foundations.md` (helpers, events, schemas)
- Workflow: `docs/dev-notes/module_refactor_workflow.md` (end-to-end process)
- Domain: `archived-plans/<controller>-plan.md` (per-controller contracts)

**Other Applications:**
- **API development:** OpenAPI spec + coding standards + error handling conventions
- **Database migrations:** Schema design doc + migration workflow + rollback procedures
- **Test authoring:** Test strategy doc + fixture patterns + assertion conventions

## 2. Enumerate the Working Set (Clear Interfaces)

**Principle:** Eliminate the "what should I touch?" ambiguity. Explicitly list every file the agent needs to read, modify, or reference.

**Universal Application:**
- **Input files:** What to read (source code, configs, schemas, existing tests)
- **Output files:** What to modify (source, tests, docs, configs)
- **Reference files:** What to consult but not change (helper modules, utilities, shared libraries)
- **Exclusions:** What to explicitly avoid touching (legacy code, deprecated modules)

**Why it works:** Agents know exactly:
- ✅ Which files to scan for context
- ✅ Which files to edit
- ✅ What dependencies exist
- ✅ What to leave alone (prevents scope creep)

**Controller Refactor Example:**
- Input: `controllers_js/<name>.js`, `templates/controls/<name>.htm`, `routes/<name>_bp.py`
- Output: Same files (in-place modification)
- Reference: `dom.js`, `http.js`, `forms.js`, `events.js`, `control_base.js`
- Tests: `__tests__/<name>.test.js`, `tests/weppcloud/routes/test_<name>_bp.py`

**Other Applications:**
- **API endpoint:** Input (spec, models), Output (route, tests, docs), Reference (auth middleware, validators)
- **Database migration:** Input (schema v1), Output (migration script, schema v2), Reference (ORM models, seed data)
- **Component refactor:** Input (old component), Output (new component, updated imports), Reference (design system, hooks)

## 3. Break Down Deliverables (Explicit Contracts)

**Principle:** Decompose work into independently verifiable sections with clear success criteria. Each section should be atomic and checkpointable.

**Universal Structure:**
1. **Core transformation** (the primary technical work)
2. **Integration points** (how this connects to other systems)
3. **Side effects** (what else must change: configs, docs, related code)
4. **Validation gates** (tests, linters, builds that must pass)
5. **Documentation** (what to update, where)
6. **Handoff checklist** (summary for human reviewer)

**Why it works:**
- Each section is independently verifiable
- Agent can self-check progress
- Natural stopping points if interrupted
- Clear success criteria prevent partial/ambiguous work
- Human reviewer can validate section-by-section

**Controller Refactor Example:**
1. **Core:** Remove jQuery, use helper APIs, emit events via `useEventMap`
2. **Integration:** Template data attributes, StatusStream attachment
3. **Side effects:** Update routes to use `parse_request_payload`, adjust NoDb setters
4. **Validation:** `wctl run-npm lint`, `wctl run-npm test`, rebuild bundle, pytest
5. **Documentation:** Update README.md, AGENTS.md, domain plan with events/payloads
6. **Handoff:** Code changes summary, test results, remaining risks/follow-ups

**Other Applications:**

**API Endpoint Development:**
1. Core: Implement route handler, request/response models
2. Integration: Authentication middleware, database queries
3. Side effects: Update OpenAPI spec, add error codes to docs
4. Validation: Unit tests, integration tests, API contract tests
5. Documentation: API reference, changelog entry
6. Handoff: Endpoint URL, example request/response, performance notes

**Database Migration:**
1. Core: Write migration script (up/down), update ORM models
2. Integration: Seed data adjustments, foreign key constraints
3. Side effects: Update fixtures, adjust API serializers
4. Validation: Migration dry-run, model tests, data integrity checks
5. Documentation: Schema changelog, migration notes
6. Handoff: Rollback tested, data loss risk assessment

**Component Refactor:**
1. Core: Rewrite component with new API/patterns
2. Integration: Update parent components, adjust props/events
3. Side effects: Update storybook stories, design system docs
4. Validation: Unit tests, visual regression tests, a11y checks
5. Documentation: Component README, migration guide for consumers
6. Handoff: Breaking changes list, deprecation timeline

## 4. Validations Are Deliverables (Verification Gates)

**Principle:** Testing and validation aren't optional cleanup—they're part of the contract. Make them explicit, executable, and reportable.

**Universal Application:**
- **Static analysis:** Linters, type checkers, formatters with exact commands
- **Automated tests:** Unit, integration, e2e with coverage requirements
- **Build verification:** Compilation, bundling, deployment dry-runs
- **Manual checks:** Specific scenarios to validate, expected behaviors
- **Performance gates:** Benchmarks, memory usage, bundle size limits

**Why it works:**
- Flips from ❌ "Make changes, then maybe test" to ✅ "Testing is part of done"
- Agent knows work isn't complete until validations pass
- Exact commands eliminate "how do I test this?" ambiguity
- Results are reportable in handoff (pass/fail, coverage numbers)

**Controller Refactor Example:**
```bash
# Required validations (must pass)
wctl run-npm lint                          # ESLint + Prettier
wctl run-npm test -- <controller>          # Jest suite for controller
python wepppy/.../build_controllers_js.py  # Bundle builds without errors
wctl run-pytest tests/weppcloud/routes/test_<name>_bp.py  # Backend integration

# Optional validations (recommended)
wctl run-pytest tests --maxfail=1          # Full suite (if time allows)
```

**Other Applications:**

**API Development:**
```bash
# Required
pytest tests/api/test_<endpoint>.py -v
pytest tests/integration/test_<feature>.py
curl -X POST ... | jq                      # Manual smoke test
ab -n 100 -c 10 http://...                 # Performance baseline

# Optional
pytest --cov=src/api --cov-report=term     # Coverage check
```

**Database Migration:**
```bash
# Required
python manage.py migrate --check           # Migration syntax valid
pytest tests/models/test_<model>.py
python scripts/verify_migration.py         # Data integrity script
python manage.py migrate --fake; ./rollback_test.sh  # Rollback works

# Optional
python scripts/migration_performance.py    # Large table impact
```

**Frontend Component:**
```bash
# Required
npm run lint
npm test -- Button.test.tsx
npm run build                              # No build errors
npm run storybook:build                    # Stories render

# Optional
npm run test:visual                        # Visual regression
lighthouse --view                          # Performance audit
```

## 5. Provide Target Patterns (Observable Outputs)

**Principle:** Don't just describe what to remove—show what the end state looks like. Provide concrete examples of the target pattern.

**Universal Application:**
- **Before/after code snippets:** Show exact transformations
- **Reference implementations:** Point to recently completed examples
- **Anti-patterns:** Explicitly call out what NOT to do
- **Success signatures:** Observable markers that indicate correct implementation

**Why it works:**
- Agents learn from examples better than abstract descriptions
- Reduces ambiguity ("modernize" vs "use these specific patterns")
- Reference implementations serve as tests ("does mine look like that?")
- Anti-patterns prevent common mistakes

**Controller Refactor Example:**

✅ **Target Pattern:**
```javascript
const { qs, delegate, show, hide } = WCDom;
const { postJson, HttpError } = WCHttp;
const { serializeForm } = WCForms;
const { useEventMap } = WCEvents;

controller.events = useEventMap([
  'climate:build:started',
  'climate:build:completed'
]);

delegate(form, '[data-climate-action]', 'click', handleAction);
```

❌ **Anti-Pattern:**
```javascript
$('#form').on('click', '.btn', function() { ... });  // No jQuery!
controller.buildStarted = true;  // Use events, not state flags
```

📚 **Reference:** "See `climate.js` for complete example"

**Other Applications:**

**API Endpoint Pattern:**
```python
# ✅ Target
@router.post("/items", response_model=ItemResponse)
async def create_item(
    item: ItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    validate_permissions(current_user, "items:create")
    return await crud.create_item(db, item)

# ❌ Anti-pattern
@app.route("/items", methods=["POST"])  # Use router, not app
def create_item():
    data = request.json  # Use Pydantic models
    # No auth check!
```

**React Component Pattern:**
```typescript
// ✅ Target
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size }))}
        {...props}
      />
    );
  }
);

// ❌ Anti-pattern
export default function Button(props) {  // Use named export + forwardRef
  return <button style={{ ... }} />;     // Use className + variants
}
```

## 6. Frame Positively (Goal-Oriented Language)

**Principle:** Focus on the target state, not just removal/avoidance. Positive framing reduces confusion and aligns agent behavior with desired outcomes.

**Universal Guidelines:**
- ✅ "Modernize X using Y" → ❌ "Remove old X"
- ✅ "Implement feature following pattern Z" → ❌ "Don't do it the old way"
- ✅ "Align with architecture doc" → ❌ "Fix the mess"
- ✅ Point to successful examples → ❌ Point only to failures

**Why it works:**
- Goal-oriented framing is clearer than avoidance
- Examples show agents what success looks like
- Positive language reduces ambiguous interpretations
- References create consistency across parallel work

**Controller Refactor Example:**
- ✅ "Modernize controller using WCDom/WCHttp helpers, emit lifecycle events via useEventMap"
- ❌ "Remove jQuery from controller"
- 📚 "See `climate.js`, `wepp.js`, `project.js` for reference implementations"

**Other Applications:**
- ✅ "Implement REST endpoint following FastAPI patterns in `api_conventions.md`" → ❌ "Don't use Flask routes"
- ✅ "Create accessible component per WCAG 2.1 AA in `a11y-guidelines.md`" → ❌ "Fix accessibility issues"
- ✅ "Write integration test following `tests/examples/user_flow.py` pattern" → ❌ "Tests are broken"

---

## Why This Framework Works

This strategy succeeds because it treats **AI agents as compiled functions** with:

1. **Deterministic inputs** → Anchor documents ensure consistent interpretation
2. **Clear interfaces** → Working set eliminates file ambiguity
3. **Explicit contracts** → Deliverables sections define success criteria
4. **Verification gates** → Validations must pass before done
5. **Observable outputs** → Target patterns show what "correct" looks like
6. **Goal orientation** → Positive framing aligns behavior

### The Mathematical Model

**Traditional development:**
```
Effort = ∑(Human hours × Task complexity)
```

**AI-accelerated development:**
```
Effort = (Documentation quality × AI execution speed) + (Human validation × Bug density)
```

The **documentation quality** is the force multiplier. When docs serve as specifications (not just guidance), AI agents can execute mechanical transformations at 10–50x human speed.

### Key Success Factors

**Required conditions:**
- ✅ Pattern-based work (not novel design)
- ✅ Comprehensive documentation (architecture + process)
- ✅ Atomic tasks (independently executable)
- ✅ Automated validation (tests catch regressions)
- ✅ Clear success criteria (observable outcomes)

**Failure modes (avoid these):**
- ❌ Vague requirements ("make it better")
- ❌ Novel architecture decisions mid-task
- ❌ Interdependent work (blocks parallelization)
- ❌ Manual-only validation (bottlenecks at human)
- ❌ Ambiguous done state ("looks good")

### Productivity Gains

**Observed results (controller modernization):**
- 25+ controllers (~23,300 LOC)
- Traditional estimate: 2–3 months (human-only)
- Actual time: **1 day** (AI execution + human validation)
- **60–90x speedup**

**Architecture:**
- 1 lead agent (planning, coordination, validation)
- 25 worker agents (parallel execution, fresh instances)
- 177k token prompts (65% of 272k context window)
- Workers single-use (context near capacity)

**Why traditional estimates fail:**
- Assume human codes sequentially
- Don't account for pattern replication speed
- Underestimate value of perfect documentation
- Overlook test automation safety net
- Miss parallelization potential

**Why this approach wins:**
- AI replicates patterns instantly (no learning curve per controller)
- Documentation consulted infinite times (zero knowledge decay)
- Tests enable confident parallelization (safety net)
- Human validation >> human implementation time (10x faster)
- Lead-worker pattern scales linearly (no coordination overhead)
- Context window constraints force excellent prompt composition

---

## Template Checklist

Use this when composing prompts for any repetitive, pattern-based task:

### Pre-Prompt Preparation
- [ ] Architecture/patterns doc exists and is current
- [ ] Step-by-step workflow doc exists
- [ ] Task-specific domain docs exist (specs, plans, schemas)
- [ ] Reference implementations available (recent examples)
- [ ] Automated tests exist or are planned
- [ ] Success criteria are measurable
- [ ] **Feasibility confirmed with agent feedback** (critical step)

### Prompt Structure
- [ ] **Section 1:** Cite 2–3 anchor documents (architecture, workflow, domain)
- [ ] **Section 2:** Enumerate working set (input files, output files, reference files, exclusions)
- [ ] **Section 3:** Break deliverables into 5–6 sections (core, integration, side effects, validation, docs, handoff)
- [ ] **Section 4:** List exact validation commands with expected results
- [ ] **Section 5:** Provide before/after code examples + reference implementations
- [ ] **Section 6:** Frame task positively ("Implement X using Y") with successful examples

### Prompt Refinement (Before Worker Deployment)
- [ ] **Iteration 1:** Draft prompt, ask agent for feasibility assessment
- [ ] **Iteration 2–N:** Incorporate agent feedback (missing context, ambiguities, architecture suggestions)
- [ ] **Convergence check:** Agent confirms all 6 criteria met (no questions, clear files, testable success, examples, validation, documentation)
- [ ] **Final validation:** Agent states "Yes, I can execute this completely in one pass"

### Post-Execution Validation
- [ ] All validation commands passed
- [ ] Handoff summary includes: code changes, test results, risks
- [ ] Documentation updated per deliverables
- [ ] Pattern matches reference implementations
- [ ] No scope creep (exclusions respected)

---

## Application Domains

This framework applies to any work that is:
- **Repetitive:** Same pattern across multiple instances
- **Pattern-based:** Follow established conventions/architecture
- **Verifiable:** Automated tests can check correctness
- **Decomposable:** Can break into atomic, independent tasks

**Example domains:**
- 🎨 **Component migrations:** Design system adoption, framework upgrades
- 🔌 **API development:** REST/GraphQL endpoints following established patterns
- 🗄️ **Database work:** Migrations, model updates, query optimization
- 📝 **Documentation:** API docs, changelogs, migration guides
- 🧪 **Test authoring:** Unit/integration tests following test strategy
- ♻️ **Refactoring:** Code modernization, pattern extraction, tech debt reduction
- 🔧 **Config management:** Terraform modules, CI/CD pipelines, deployment scripts

**Not suitable for:**
- Novel architecture design (no established patterns)
- Exploratory work (unclear requirements)
- Complex debugging (requires creative problem-solving)
- High-risk changes (no automated validation)

---

Following this framework keeps prompts structured, explicit, and reusable. Every agent knows:
- 📚 What documents to reference (deterministic inputs)
- 📁 What files to touch (clear interfaces)
- ✅ What to deliver (explicit contracts)
- 🧪 How to validate (verification gates)
- 🎯 What success looks like (observable outputs)
- 💡 How to frame the work (goal-oriented)

This reduces ambiguity, eliminates drift, and enables massive parallelization across pattern-based development work.

---

## Appendix A: Case Study - Controller Modernization

**Task:** Migrate 25+ JavaScript controllers (~23,300 LOC) from jQuery to vanilla helpers  
**Timeline:** 1 day  
**Team:** 1 human + OpenAI GPT-5 (Codex)  
**Results:** Zero regressions, 100% test coverage maintained, comprehensive documentation updated

### How We Applied the Framework

**Lead-Worker Architecture:**
- **Lead agent:** Tracked progress via checklist, wrote 25 standardized prompts, validated worker output
- **Worker agents:** Each executed one controller modernization in fresh conversation (177k token prompts, 65% of 272k context)
- **Parallelization:** Workers executed independently (no coordination needed)
- **Context management:** Workers single-use due to prompt size, lead maintained persistent state

**1. Anchor Documents:**
- `docs/dev-notes/controller_foundations.md` — Target architecture (helpers, events, controlBase)
- `docs/dev-notes/module_refactor_workflow.md` — 5-step process (scope → plan → implement → document → validate)
- `docs/work-packages/.../archived-plans/<controller>-plan.md` — Per-controller contracts

**2. Working Set (per controller):**
- Input: `controllers_js/<name>.js`, `templates/controls/<name>.htm`, `routes/<name>_bp.py`, `nodb/core/<name>.py`
- Output: Same files (in-place modernization)
- Reference: `dom.js`, `http.js`, `forms.js`, `events.js`, `control_base.js`, `status_stream.js`
- Tests: `__tests__/<name>.test.js`, `tests/weppcloud/routes/test_<name>_bp.py`

**3. Deliverables Structure:**
- Core: Remove jQuery → use WCDom/WCHttp/WCForms/WCEvents
- Integration: StatusStream attachment, event emitter via `useEventMap`
- Side effects: Templates use `data-*` attributes, routes use `parse_request_payload`
- Validation: `wctl run-npm lint/test`, bundle rebuild, pytest
- Documentation: Update README.md, AGENTS.md, controller plan
- Handoff: Code summary, test results, remaining risks

**4. Validation Commands:**
```bash
wctl run-npm lint                          # ESLint passes
wctl run-npm test -- <controller>          # Jest suite green
python wepppy/.../build_controllers_js.py  # Bundle builds
wctl run-pytest tests/weppcloud/routes/test_<name>_bp.py  # Integration tests pass
```

**5. Target Pattern:**
```javascript
// Reference implementation: climate.js, wepp.js, project.js
const { qs, delegate, show, hide } = WCDom;
controller.events = useEventMap(['domain:event:name']);
delegate(form, '[data-action]', 'click', handler);
```

**6. Positive Framing:**
- ✅ "Modernize controller using helper APIs and event-driven architecture"
- 📚 "See `climate.js` for reference implementation"

### Results
- **25 controllers migrated** in 1 day (lead-worker pattern)
- **~177k token prompts** (65% of context window)
- **Workers single-use** (near context limit, no reuse)
- **Lead agent coordinated** progress tracking and validation
- **29 Jest test suites** maintained
- **Pytest integration tests** passing
- **Zero jQuery references** remaining
- **Comprehensive documentation** updated
- **Bundle size reduced** (removed jQuery dependency)

### Key Learnings
1. **Prompt size matters:** At 65% context usage, prompts must be complete (no iteration possible)
2. **Lead-worker scales:** Parallelization limited only by cost, not coordination
3. **Documentation quality >> everything:** Complete anchor docs enabled one-shot execution
4. **Tests are critical:** Automated validation caught edge cases workers missed
5. **Single-use workers:** Near context limit means fresh instance per task (not a bug, a feature)
6. **Agent feedback is essential:** Iterating prompts with lead agent (5–10 rounds) before worker deployment prevents expensive retries
7. **Agents contribute architecture:** Event-driven pattern, bootstrap protocol, scoped emitters were agent suggestions
8. **Iterate cheap, execute expensive:** 50k tokens refining prompt saves 354k+ tokens debugging failed workers
9. **Convergence checklist prevents guesswork:** "Can you do this in one pass?" binary test eliminates ambiguity
10. **Prompt refinement is invisible work:** The 5–10 iteration cycles don't appear in the "1 day" timeline but were critical to success

---

## Appendix B: Controllers Modernization Checklist

Use this GitHub-style checklist to track remaining controller migrations. Index generated by scanning `wepppy/weppcloud/controllers_js/*.js` for jQuery-era usage (`$(` / `$.` / `jQuery`). Copy into issues/PRs and check off as controllers go fully helper-based.

**Modernized**
- [x] `wepppy/weppcloud/controllers_js/ash.js`
- [x] `wepppy/weppcloud/controllers_js/channel_delineation.js`
- [x] `wepppy/weppcloud/controllers_js/climate.js`
- [x] `wepppy/weppcloud/controllers_js/landuse.js`
- [x] `wepppy/weppcloud/controllers_js/omni.js`
- [x] `wepppy/weppcloud/controllers_js/project.js`
- [x] `wepppy/weppcloud/controllers_js/soil.js`
- [x] `wepppy/weppcloud/controllers_js/subcatchment_delineation.js`
- [x] `wepppy/weppcloud/controllers_js/wepp.js`
- [x] `wepppy/weppcloud/controllers_js/outlet.js`
- [x] `wepppy/weppcloud/controllers_js/baer.js`
- [x] `wepppy/weppcloud/controllers_js/debris_flow.js`
- [x] `wepppy/weppcloud/controllers_js/batch_runner.js`
- [x] `wepppy/weppcloud/controllers_js/disturbed.js`
- [x] `wepppy/weppcloud/controllers_js/dss_export.js`
- [x] `wepppy/weppcloud/controllers_js/landuse_modify.js`
- [x] `wepppy/weppcloud/controllers_js/map.js`
- [x] `wepppy/weppcloud/controllers_js/observed.js` 
- [x] `wepppy/weppcloud/controllers_js/path_ce.js` 
- [x] `wepppy/weppcloud/controllers_js/rangeland_cover.js`
- [x] `wepppy/weppcloud/controllers_js/rangeland_cover_modify.js` 
- [x] `wepppy/weppcloud/controllers_js/rap_ts.js`
- [x] `wepppy/weppcloud/controllers_js/rhem.js`
- [x] `wepppy/weppcloud/controllers_js/team.js`
- [x] `wepppy/weppcloud/controllers_js/treatments.js`

**Shared Infrastructure Still Using jQuery**
- [x] Retired `wepppy/weppcloud/controllers_js/ws_client.js` in favor of the unified `controlBase.attach_status_stream` helper.
