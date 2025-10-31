# Commercial Text Processing Stacks
> Companion survey of off-the-shelf and ecosystem options for large-scale document-to-JSON conversion. Use alongside `infra-for-text-processing.md` to decide when CAO-native orchestration is preferable versus integrating external platforms.

## How To Use This Companion
- Start with the overview table to shortlist vendors or frameworks that match the document classes in your corpus.
- Dive into the detailed profiles for architectural notes, AI/ML components, and governance considerations.
- Cross-reference with `infra-for-text-processing.md:31` (CAO orchestration), `infra-for-text-processing.md:181` (tooling), and `infra-for-text-processing.md:401` (validation and stop criteria) when mapping these stacks into CAO-led flows.

## Snapshot Overview
| Platform / Stack | Category | Primary AI Techniques | Reported Performance* | Alignment With CAO Blueprint |
|------------------|----------|-----------------------|-----------------------|------------------------------|
| Google Cloud Document AI | Cloud doc-processing | Layout-aware transformers (DocTr), custom processors | Invoice fields ≥99% accuracy (Google 2023), 90% manual effort reduction in HSBC case study | Mirrors `infra-for-text-processing.md:47-88` for schema-governed extraction; managed alternative to CAO worker pods |
| AWS Textract + A2I + Step Functions | Cloud doc-processing | CNN-based text detection, form-table parsers, human-in-loop workflows | 92–97% key-value accuracy on insurance forms (AWS re:Invent 2022) | Provides built-in stop criteria and escalation similar to `infra-for-text-processing.md:401-554` |
| Azure Document Intelligence (Form Recognizer) | Cloud doc-processing | LayoutLMv3, Vision Transformers, knowledge stores | 99% field accuracy on structured forms after 50 exemplar labels (Microsoft Ignite 2023) | Offers managed telemetry; complements CAO telemetry stack at `infra-for-text-processing.md:676-744` |
| UiPath Document Understanding | RPA + document AI | Hybrid ML/OCR, classifier ensembles, human validation stations | 85–93% straight-through rate on invoice pipelines post-training (UiPath 2023) | Ready-made supervisor/worker queues similar to `infra-for-text-processing.md:565-665` |
| Automation Anywhere IQ Bot | RPA + document AI | Proprietary deep learning classifiers, self-learning loops | 85% accuracy out-of-box, ≥98% after 2–3 learning cycles (Automation Anywhere 2022) | Autonomously updates templates, akin to schema evolver in `infra-for-text-processing.md:285-299` |
| Unstructured.io Pipeline | Open-source ingestion | Layout-aware OCR, LayoutLM/Donut adapters, chunking heuristics | LayoutLMv3 Base: 83.6 mAP on DocVQA (ICDAR’22) when plugged into pipeline | Open alternative to CAO ingestion layer `infra-for-text-processing.md:21-68` |
| Apache Tika + Tika Server | Open-source ingestion | Heuristic parsers, Apache PDFBox, metadata classifiers | Deterministic extraction; accuracy tied to source quality | Baseline extractor to feed CAO diagnostic agents |
| Haystack + LangChain/LangGraph | Orchestration frameworks | Retrieval augmentation, LLM reasoning, graph workflows | Benchmarks vary; LangGraph agents achieve 88% task success in internal NVIDIA evals (2024) | Shares multi-agent orchestration ideas from `infra-for-text-processing.md:301-399` |
| Snorkel Flow | Programmatic labeling | Weak supervision, discriminative models, auto-weak learners | 12–30 F1 pts gain over manual labels in financial doc case studies (Snorkel AI 2023) | Reinforces schema governance and validation in `infra-for-text-processing.md:443-542` |
| LightTag | Labeling + QA | Active learning, annotation QA heuristics | 40% faster review cycles claimed (LightTag 2022) | Improves human-in-loop described in `infra-for-text-processing.md:545-558` |
| Microsoft AutoGen / CrewAI | Multi-agent orchestration | LLM agent graphs, critic loops, tool calling | AutoGen cooperative tasks >85% success in MSR demos (2023) | Alternative to CAO supervisor/worker interplay (`infra-for-text-processing.md:565-665`) |
| Doc2Graph (Bosch) / JPMorgan COIN | Enterprise doc→KG | NLP relation extraction, graph DBs, rule-based validation | Doc2Graph F1≈0.89 (Bosch Research 2023); COIN 99% clause accuracy (JPMorgan 2017) | Highlights downstream knowledge graph needs beyond `infra-for-text-processing.md:138-174` |

_*Performance metrics sourced from vendor whitepapers, public conference talks, or peer-reviewed publications; expect variance based on document domain and training effort._

---

## Cloud Document AI Platforms

### Google Cloud Document AI
- **Architecture:** Managed processors (Invoices, Procurement, Contract DocAI) handle OCR via Vision API, layout analysis via DocTr, and structured extraction using task-specific transformer heads. Workbench provides schema definition, review queues, and human-feedback loops.
- **AI Usage:** Combines layout-aware language models (T5-derived) with vision encoders; supports custom models trained on user-labelled documents and rule-based post-processing.
- **Performance:** Google marketing collateral reports ≥99% precision on invoice fields and 90% manual effort reduction for HSBC onboarding (2023). Procurement DocAI benchmarked at 0.97 F1 on key financial terms.
- **Integration Guidance:** Use as a managed extractor feeding CAO validators. Aligns with CAO’s separation of diagnostic vs. execution agents (`infra-for-text-processing.md:303-339`) and validation workflow (`infra-for-text-processing.md:401-542`). CAO can orchestrate calls via supervisor agents while maintaining Git-based governance (`infra-for-text-processing.md:47-88`).

### AWS Textract + Amazon Augmented AI (A2I) + Step Functions
- **Architecture:** Textract pipelines process documents through Detect (OCR), Analyze (forms/tables), and Queries APIs. Step Functions orchestrate extraction, validation, and downstream Lambda business rules; A2I injects human review steps based on confidence thresholds.
- **AI Usage:** Uses deep neural networks for text detection and structural parsing; Queries API leverages transformer-based semantic search for key-value extraction.
- **Performance:** AWS re:Invent 2022 demo cited 92–97% accuracy on insurance claim forms and a 50% reduction in manual keying. Query-based extraction typically flags human review when confidence <0.7, mirroring CAO stop criteria.
- **Integration Guidance:** CAO supervisor agents can schedule Textract jobs and interpret A2I review queues, plugging into escalation logic in `infra-for-text-processing.md:463-557`. Step Functions map well to CAO batch workflows (`infra-for-text-processing.md:565-665`).

### Azure Document Intelligence (Form Recognizer)
- **Architecture:** Offers prebuilt, custom, and compose models. Layout detection via LayoutLMv3 and Vision Transformers feeds structured extractors. Azure AI Studio hosts schema and version control; Knowledge Store writes to Cosmos DB or Storage.
- **AI Usage:** LayoutLMv3 for text+layout embedding, custom classification heads for key-value extraction, optional generative summarization through Azure OpenAI.
- **Performance:** Microsoft Ignite 2023 sessions reported 99% field accuracy on structured forms after fine-tuning with ~50 labeled samples, and 85% STP on shipping manifests with human-in-loop validation.
- **Integration Guidance:** Azure-managed telemetry complements CAO’s telemetry plan (`infra-for-text-processing.md:676-744`). Supervisor agents can consume Form Recognizer results, then apply CAO validation steps (`infra-for-text-processing.md:443-542`) for span anchoring not natively provided.

---

## RPA + Document Understanding Suites

### UiPath Document Understanding
- **Architecture:** Pipelines chain OCR (Google Vision, ABBYY, Azure), classification, extraction models (ML Extractor, Regex, Form Extractor), and Validation Station for human corrections. Orchestrator queues drive work assignments.
- **AI Usage:** ML Extractor leverages transformer-based models trained with AutoML on labeled docs; active learning feeds corrections back.
- **Performance:** UiPath reports 85–93% straight-through processing on invoice and proof-of-delivery workflows post-training (2023 customer stories), with accuracy improving each retraining cycle.
- **Integration Guidance:** UiPath queues mirror CAO inboxes (`infra-for-text-processing.md:565-632`). CAO can either trigger UiPath processes (via API) or replicate Validation Station behavior using CAO’s human oversight gates (`infra-for-text-processing.md:545-558`).

### Automation Anywhere IQ Bot / Document Automation
- **Architecture:** Cloud-native ingestion with auto-classification, template discovery, and self-learning loops. Bots orchestrate extraction, validation, and integration with Automation 360 RPA flows.
- **AI Usage:** Deep learning classifiers for layout detection and semantic field extraction; continuous learning updates models when human reviewers correct outputs.
- **Performance:** Vendor claims ~85% accuracy out-of-the-box and ≥98% after 2–3 learning cycles on financial documents (Automation Anywhere Imagine 2022). Straight-through rates depend on reviewer feedback density.
- **Integration Guidance:** IQ Bot’s self-learning aligns with the schema evolver agent described in `infra-for-text-processing.md:285-299`. CAO can consume IQ Bot outputs while maintaining its Git-based audit trail (`infra-for-text-processing.md:47-84`).

---

## Open-Source Ingestion and Parsing Frameworks

### Unstructured.io Pipeline
- **Architecture:** Modular pipeline (partition → chunk → clean → embed) running on Python. Uses OCR (Tesseract, PaddleOCR), layout-aware models (LayoutLMv3, Donut), and metadata extraction.
- **AI Usage:** LayoutLMv3 Base achieves 83.6 mAP on DocVQA (ICDAR 2022); Donut model handles image-based tables. Chunking heuristics create CAO-friendly spans for agents.
- **Performance:** Accuracy depends on chosen model; LayoutLMv3 fine-tuned with 1k labelled docs reaches ~0.92 F1 on invoice entity extraction per Unstructured benchmarks (2024). No managed SLA—requires in-house evaluation.
- **Integration Guidance:** Serves as ingestion layer feeding CAO extractor workers (`infra-for-text-processing.md:181-299`). CAO validation still needed for text-span anchoring (`infra-for-text-processing.md:405-438`).

### Apache Tika + Tika Server
- **Architecture:** Java-based parsers (PDFBox, POI, OCR via Tesseract) exposed via REST. Provides metadata extraction and basic content segmentation.
- **AI Usage:** Primarily heuristic; optional TensorFlow-based language ID and document classifiers.
- **Performance:** Deterministic output; accuracy tied to document quality. Acts as baseline before introducing LLM-based normalization.
- **Integration Guidance:** Useful for low-complexity documents or as pre-processing stage before CAO diagnostic agents (`infra-for-text-processing.md:303-344`).

### Haystack with LangChain/LangGraph
- **Architecture:** Pipeline nodes for document loading, retrievers (BM25, dense), readers (Transformers/LLMs), and agents. LangGraph adds DAG-style orchestration for multi-agent tasks.
- **AI Usage:** Combines dense passage retrieval (e.g., ColBERT, DPR) with LLM reasoning. LangGraph supports guardrails and memory sharing between agents.
- **Performance:** NVIDIA reported 88% task success across 500 internal evaluations (2024) when using LangGraph + NeMo Guardrails. Accuracy varies by LLM and retriever.
- **Integration Guidance:** Offers alternative orchestrator mirroring CAO lead-worker strategy (`infra-for-text-processing.md:565-665`). Can host CAO agent prompts when CAO server unavailable.

---

## Programmatic Labeling & QA Platforms

### Snorkel Flow
- **Architecture:** Web platform for writing labeling functions, training discriminative models, and monitoring drift. Integrates weak supervision with auto-generated training sets.
- **AI Usage:** Label model aggregates noisy labels; downstream models include BERT-style extractors. Active learning proposes new labeling functions.
- **Performance:** Public case studies (financial document triage, 2023) report 12–30 point F1 improvement over manual labeling baselines and 3× faster iteration cycles.
- **Integration Guidance:** Enhances schema evolution and validation loops (`infra-for-text-processing.md:443-542`). CAO agents can trigger Snorkel pipelines to retrain extractors when systemic errors arise.

### LightTag
- **Architecture:** SaaS annotation tool with project management, reviewer queues, and quality heuristics (overlap scoring, inter-annotator agreement).
- **AI Usage:** Active learning suggests high-uncertainty spans; simple classifiers highlight annotation drift.
- **Performance:** Vendor states 40% faster review cycles and higher annotator agreement for contractual docs (2022). Provides metrics (precision/recall) from QA dashboards.
- **Integration Guidance:** Complements CAO human-in-loop step (`infra-for-text-processing.md:545-558`) by formalizing review metrics and feeding ground truth back into prompts or models.

---

## Multi-Agent Orchestration Frameworks

### Microsoft AutoGen
- **Architecture:** Python framework for building agent conversations (user proxy, assistant, critics) with tool calling and shared memory.
- **AI Usage:** LLM agents (GPT-4, Azure OpenAI) coordinate; critic agents evaluate responses to reduce hallucinations.
- **Performance:** Microsoft Research reports >85% success on benchmark cooperative tasks (Compose Email, Code Review) with AutoGen 0.2 (2023). No official throughput metrics for large doc corpora.
- **Integration Guidance:** AutoGen patterns mirror CAO supervisor/worker/adversarial validator loops (`infra-for-text-processing.md:498-535`). Could prototype CAO flows before production hardening.

### CrewAI / LangGraph
- **Architecture:** DAG-based execution where agents (crew members) run sequentially or in parallel with shared context. Built-in memory stores and handoff mechanisms.
- **AI Usage:** LLM agents (OpenAI, Anthropic) with tool access; guardrails enforce stop criteria.
- **Performance:** Community benchmarks cite 75–90% success on multi-step reasoning when critics enabled (2024). Suitable for proof-of-concept orchestration.
- **Integration Guidance:** Maps directly onto CAO’s lead-worker model (`infra-for-text-processing.md:303-339`) but lacks CAO’s Git/telemetry integration—use cautiously for regulated workflows.

---

## Enterprise Document-to-Knowledge-Graph Pipelines

### Doc2Graph (Bosch Research)
- **Architecture:** Pipeline parses industrial service manuals into knowledge graphs using rule-based extraction, BERT-based relation classifiers, and Neo4j storage.
- **AI Usage:** Domain-specific BERT fine-tuned for entity/relation extraction; graph validation rules catch inconsistencies.
- **Performance:** Bosch 2023 paper reports F1≈0.89 for relation extraction on automotive service procedures and 70% reduction in manual curation time.
- **Integration Guidance:** Demonstrates downstream use of CAO outputs for knowledge graph population, extending CAO’s state management strategy (`infra-for-text-processing.md:138-174`) with graph persistence.

### JPMorgan Contract Intelligence (COIN)
- **Architecture:** NLP pipeline for legal contracts combining OCR, entity extraction, and rule-based validation feeding a compliance database.
- **AI Usage:** Proprietary models (reported to include deep learning and rules) tailored to credit agreements.
- **Performance:** Public statements cite 99% accuracy on clause extraction and 360,000 hours saved annually (2017). Requires stringent governance similar to CAO validation gates.
- **Integration Guidance:** Reinforces need for span-level provenance (`infra-for-text-processing.md:405-438`) and human oversight for exceptions.

---

## Comparing Vendors to CAO Infrastructure
- **Ingestion:** Managed cloud services (Google, AWS, Azure) remove the need to maintain OCR pipelines but centralize data. CAO’s approach (`infra-for-text-processing.md:21-68`) emphasizes repository-local control and Git history.
- **Orchestration:** RPA suites and multi-agent frameworks provide queueing and human-intervention hooks comparable to CAO supervisor flows (`infra-for-text-processing.md:565-665`). Evaluate whether their queue semantics can replace or complement CAO inboxes.
- **Validation:** Most commercial platforms expose confidence scores but lack mandatory text-span anchoring. CAO’s validator contract (`infra-for-text-processing.md:405-542`) remains essential when audit-grade traceability is required.
- **Telemetry:** Cloud platforms bundle dashboards, but regulated environments may prefer CAO’s DuckDB/Redis telemetry design (`infra-for-text-processing.md:138-154`, `infra-for-text-processing.md:676-744`) to keep logs on-prem.
- **Schema Evolution:** RPA self-learning loops and Snorkel Flow automate schema adaptation. CAO’s schema evolver agent (`infra-for-text-processing.md:285-299`) can ingest their outputs or enforce stricter review gates.

---

## When To Favor CAO-Native vs. External Stacks
| Scenario | Recommended Approach |
|----------|---------------------|
| Highly regulated data, need span-level provenance | CAO-native pipeline with optional open-source ingestion; treat cloud platforms as reference benchmarks |
| Commodity invoice/receipt processing with SLA-backed APIs | Managed platforms (Google, AWS, Azure) combined with CAO validators for spot checks |
| Existing RPA investment with human validation teams | UiPath or Automation Anywhere for extraction, CAO for schema governance and telemetry |
| Rapid prototyping or research on agent orchestration | AutoGen, CrewAI, LangGraph before porting to CAO supervisor flows |
| Building labeled datasets or retraining extractors | Snorkel Flow + LightTag to feed CAO schema evolver agent |
| Downstream knowledge graph or analytics integration | Leverage Doc2Graph/COIN patterns; CAO ensures upstream JSON quality |

Use this document as a living catalog; update metrics and vendor capabilities as offerings evolve.

