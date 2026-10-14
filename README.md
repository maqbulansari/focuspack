<div align="center">

# 🎯 focuspack

**Focus-driven, budget-aware codebase context packager for LLMs**

[![CI](https://github.com/maqbulansari/focuspack/actions/workflows/ci.yml/badge.svg)](https://github.com/maqbulansari/focuspack/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

*Don't dump blindly. Pack the exact slice of code your LLM needs with AST contracts, semantic roles, and adaptive token budgets.*

[Quick Start](#-quick-start) • [Why focuspack?](#-why-focuspack-vs-flat-dumpers) • [Key Features](#-key-features) • [CLI Reference](#-cli-reference) • [Contributing](#-contributing)

---

</div>

## 💡 Why focuspack? vs Flat Dumpers

Static file packagers (like Repomix or code2prompt) suffer from a fundamental blind spot: **they treat codebases as flat buckets of files**. If you run them on a 100-file project, they dump all 100 files into a 150k-token monolith.

### The Attention Breakdown (Lost in the Middle)
Transformer research proves that as context length grows, reasoning accuracy plummets in the middle 60–80% of the prompt. Dumping 80 irrelevant files dilutes attention heads, causing missed edge cases and hallucinations.

### What LLMs Actually Love to Read
1. **High Signal-to-Noise:** The file you are actively touching in **FULL**.
2. **Contract-First Dependencies:** When an LLM calls helper functions, it does **not** need 400 lines of implementation logic. It only needs the **interface contract** (class signatures, argument types, return annotations, and docstrings).
3. **Adaptive Token Budgets:** If you have a 32k or 64k token target, the tool should **actively compress and tier** files to fit—not just fail a CI assertion.
4. **Semantic Role Labeling:** Tagging files with `role="focus_target"` vs `role="dependency_contract"` explicitly instructs the model what it is allowed to modify versus what is an immutable external API.

---

## ⚡ Feature Comparison

| Capability | Flat Dumpers (Repomix, etc.) | 🎯 focuspack |
| :--- | :---: | :---: |
| **Selection Model** | Flat / Dump All (or manual globs) | **Focus-Driven Graph** (`--focus src/auth.py`) |
| **Dependency Awareness** | ❌ None (no AST import traversal) | ✅ **Automated import graph discovery** |
| **Token Budgeting** | ❌ Dummy exit-code check | ✅ **Active Adaptive Fitting** (`--budget 32k`) |
| **Multi-Tier Compression** | ❌ Global all-or-nothing flag | ✅ **Tiered**: Focus is Full, dependencies are Contracts |
| **Semantic Role Tags** | ❌ Generic `<file path="...">` | ✅ `<file role="focus_target\|dependency_contract">` |
| **Task / Mission Framing** | ❌ Raw code dump | ✅ `--task bugfix\|review\|refactor` system anchors |
| **Runtime Requirement** | ⚠️ Node.js / NPM (`npx repomix`) | ✅ **Zero-Node Pure Python** (`pip`, `uvx`) |

---

## 🚀 Quick Start

### Installation

```bash
# Install via pip
pip install focuspack

# Or run instantly with uvx / pipx
uvx focuspack
```

### 1-Minute Workflows

```bash
# 1. Target a specific file — packages auth.py in FULL and its imported dependencies as Skeletons:
focuspack --focus src/auth/service.py

# 2. Fit strictly within a 32k token window with zero overflow:
focuspack --focus src/auth/service.py --budget 32k

# 3. Add an automated debugging mission and copy straight to clipboard:
focuspack --focus src/payment.py --task bugfix --copy

# 4. Package git-modified files + their connected contracts:
focuspack diff --copy
```

---

## 📦 Output Format (Claude & LLM Optimized)

By default, `focuspack` generates semantic XML structured for Anthropic Claude 3.5/3.7, OpenAI GPT-4o, and Gemini:

```xml
<documents>
  <context_manifest>
    <tool>focuspack v0.2.0</tool>
    <token_budget total_allowed="32000" tokens_used="14520" utilization="45.4%" status="fits"/>
    <role_counts focus_targets="1" dependency_contracts="3"/>
  </context_manifest>

  <directory_structure>
  src/
  ├── auth/
  │   └── service.py  [FOCUS]
  └── db/
      └── client.py   [CONTRACT]
  </directory_structure>

  <files>
    <file index="1" path="src/auth/service.py" role="focus_target" mode="full" tokens="3420">
      <document_content>
        <!-- Full implementation code of the focus target -->
      </document_content>
    </file>

    <file index="2" path="src/db/client.py" role="dependency_contract" mode="skeleton" tokens="380">
      <document_content>
        <!-- AST Contract: classes, methods, type hints, docstrings without bodies -->
      </document_content>
    </file>
  </files>

  <task_instruction>
    You are a principal debugging engineer. Analyze the enclosed focus targets and their dependency contracts...
  </task_instruction>
</documents>
```

*(Also supports `--format markdown`, `--format json`, and `--format plain`).*

---

## 📖 CLI Reference

```text
Usage: focuspack [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --version  Show version and exit.
  --help         Show this message and exit.

Commands:
  pack     Package focused codebase context optimized for LLMs.
  analyze  Inspect repository dependency graph, token metrics, and largest files.
  diff     Package only git-changed files + their connected dependency contracts.
  init     Create a .focuspack.json configuration file.
```

### `focuspack pack` Options

| Option | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| `--focus` | `-F` | File(s) or directories to focus on (kept in Full; imports become Contracts) | `None` |
| `--depth` | `-d` | Dependency traversal depth (1 = direct imports, 2 = 2 hops) | `1` |
| `--budget` | `-b` | Token budget (e.g. `32k`, `64k`). Dynamically tiers files to fit | `None` |
| `--task` | `-t` | Task prompt template (`bugfix`, `review`, `refactor`, `explain`, `test`) | `None` |
| `--format` | `-f` | Output format (`xml`, `markdown`, `json`, `plain`) | `xml` |
| `--mode` | `-m` | Compression mode (`auto`, `full`, `skeleton`) | `auto` |
| `--copy` | `-c` | Copy output directly to system clipboard | `False` |
| `--stdout` | | Stream output directly to stdout | `False` |
| `--diff` | | Focus on git uncommitted/staged changes + connected contracts | `False` |
| `--output` | `-o` | Output file path | `context.<format>` |
| `--no-redact-secrets` | | Disable automated secret redaction | `False` |
| `--quiet` | `-q` | Suppress console UI | `False` |

---

## ⚙️ Configuration

Generate a configuration file with:

```bash
focuspack init
```

Creates `.focuspack.json`:

```json
{
  "output_format": "xml",
  "mode": "auto",
  "token_budget": 32000,
  "focus_depth": 1,
  "focus_targets": [],
  "max_size": "500kb",
  "exclude": [
    "docs/build/**",
    "scratch/**"
  ],
  "respect_gitignore": true,
  "redact_secrets": true,
  "include_tree": true
}
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
See [CONTRIBUTING.md](CONTRIBUTING.md) for local dev setup and guidelines.

1. Fork the repo & clone locally
2. Create your branch (`git checkout -b feature/awesome-feature`)
3. Install dependencies (`pip install -e ".[dev,all]"`)
4. Run tests (`pytest`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
