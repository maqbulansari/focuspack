# 🎯 focuspack Product Charter & Goal Guardrails

> *"Perfection is achieved, not when there is nothing more to add, but when there is nothing left to take away."*  
> — Antoine de Saint-Exupéry

This document defines the **North Star Mission**, **Core Pillars**, **Explicit Non-Goals**, and **Decision Rubric** for `focuspack`. Its purpose is to protect the project from scope creep, feature bloat, and mission drift during community PRs, issue triage, and roadmap planning.

---

## 🌟 The North Star Mission

**`focuspack` delivers the highest-signal, zero-loss, budget-adaptive codebase context compiler for LLMs, running everywhere with pure-Python zero-heavy-runtime portability.**

We do not dump whole repositories blindly. We deliver the exact slice of code an LLM needs to reason, debug, and implement correctly without hitting "Lost in the Middle" attention degradation or exceeding token windows.

---

## 🏛️ The Four Core Pillars (Non-Negotiable)

Every feature, PR, and bugfix must strengthen at least one of these pillars:

### 1. Focus Target Inviolability
The primary target file(s) specified by the user must **never** be silently dropped, discarded, or corrupted. If budget constraints are tight, internal method implementations are tiered down via AST method body compression, but public interface contracts and primary files remain anchored.

### 2. Interface Contracts Over Flat Dumps
Peripheral dependencies should be represented by their **AST interface contracts** (class hierarchies, type annotations, signatures, and docstrings), not hundreds of lines of implementation logic. LLMs only need the contract to call code correctly.

### 3. Active Adaptive Budgeting (Multi-Stage Optimization)
We do not just check an assertion and crash. `focuspack` actively tiers context through 4 deterministic stages:
1. Pruning peripherals
2. Downgrading contracts to AST skeletons
3. Clean AST docstring stripping
4. AST method body compression on oversized targets
*(Plus `--strict-budget` for pipeline gating).*

### 4. Zero-Node, Pure-Python Portability
`focuspack` must remain instantly executable via `uvx focuspack` or `pip install focuspack` in under 2 seconds. No Node.js runtime, no npm packages, no heavy compilation toolchains, no mandatory Docker.

---

## 🛑 Explicit Non-Goals (What We Will NEVER Build)

To avoid becoming another bloated, generic developer tool or accidental clone of existing tools, the following features are **explicitly out of scope**:

| Non-Goal | Rationale | What to Use Instead |
| :--- | :--- | :--- |
| ❌ **Flat Monolithic Dumps** | Blindly dumping 500 files into a 200k token blob degrades LLM attention heads and wastes budget. | Repomix, code2prompt |
| ❌ **Vector DBs, RAG, or Embeddings** | `focuspack` is an instant deterministic context compiler, not an indexing daemon or RAG search engine. | Chroma, Qdrant, LanceDB |
| ❌ **Local LLM Inference / Agent Loop** | We prepare context *for* models; we do not run the models or manage autonomous agent loops. | Ollama, Claude Code, Aider |
| ❌ **Cloud Processing / Remote APIs** | `focuspack` must remain 100% private, offline-first, and run locally without API keys or telemetry. | Proprietary SaaS |
| ❌ **Web UIs / Electron Desktop Apps** | `focuspack` is a fast CLI and pipeline tool for terminal developers and IDE integrations. | Web-based visualizers |
| ❌ **Fragile Pseudo-AST Regex Parsing** | Never use brittle regexes that break on multiline signatures or arrow functions. Use real AST or language outlines. | Tree-sitter / native AST |
| ❌ **Code Modification / Auto-refactoring** | `focuspack` inspects, filters, and formats code context; it does not edit or refactor source files. | Ruff, Black, Rope |

---

## 🧭 The "Out-of-Goal" Decision Rubric

When reviewing any **Issue**, **Feature Request**, or **Pull Request**, run it through this 4-step checklist:

```
                  [New Issue / PR / Enhancement]
                               │
            1. Does it strengthen one of our 4 Pillars?
                               │
                    ├── NO  ──────► [DECLINE: Out of Scope]
                    └── YES
                               │
            2. Does it touch any of our Explicit Non-Goals?
                               │
                    ├── YES ──────► [DECLINE: Violates Non-Goals]
                    └── NO
                               │
            3. Does it keep focus targets whole & preserve signal?
                               │
                    ├── NO  ──────► [REQUEST REVISION]
                    └── YES
                               │
            4. Does it maintain pure-Python zero-heavy runtime?
                               │
                    ├── NO  ──────► [DECLINE: Dependency Bloat]
                    └── YES
                               ▼
                    [APPROVE & MERGE 🎉]
```

### Response Template for Out-of-Scope Requests

When closing an issue or PR that falls outside the charter, be transparent and kind:

> *"Thank you for opening this! While this is an interesting capability, it falls outside `focuspack`'s core mission as defined in our [Product Charter (CHARTER.md)](CHARTER.md). Specifically, `focuspack` is strictly focused on focus-driven graph traversal and adaptive AST context budgeting, and we explicitly avoid [insert Non-Goal here, e.g., vector database indexing / heavy native toolchains].  
> We recommend exploring [suggested alternative] for this workflow. Thank you for contributing to the discussion!"*

---

## 🏷️ GitHub Labeling Scheme

To maintain clarity across issues and PRs:

- `goal-aligned`: Confirmed to directly strengthen the 4 Core Pillars.
- `out-of-scope`: Violates Non-Goals or does not serve the core mission (marked for polite closure).
- `feature-creep`: Adds unnecessary complexity without improving LLM reasoning signal.
- `benchmark`: Quantified token efficiency and context fidelity measurements.
