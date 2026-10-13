<div align="center">

# 📦 repodigest

**Fast, intelligent codebase packaging & AST-aware context generator for LLMs & Developers**

[![CI](https://github.com/USER/repodigest/actions/workflows/ci.yml/badge.svg)](https://github.com/USER/repodigest/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

*Pack your entire repository into clean, token-efficient prompt context with structural outlines and secret protection in one second.*

[Quick Start](#-quick-start) • [Key Features](#-key-features) • [CLI Usage](#-cli-usage) • [Configuration](#-configuration) • [Contributing](#-contributing)

---

</div>

## 💡 Why repodigest?

When feeding codebases into LLMs (**Claude 3.5 Sonnet**, **ChatGPT**, **Gemini**, or local models), developers face three major headaches:

1. **Token Exhaustion:** Pasting full files quickly hits context limits or wastes expensive tokens on repetitive implementation bodies.
2. **Accidental Credential Leaks:** Developers routinely paste `.env` values, API keys (OpenAI, AWS, GitHub), or private tokens into cloud chat interfaces by accident.
3. **Noisy Clutter:** Blindly concatenating directories drags in `node_modules`, lockfiles, binary images, and cache directories.

**`repodigest` solves all of this out-of-the-box.**

---

## ✨ Key Features

- 🧠 **AST Skeleton Mode:** Automatically parses Python (AST) and JS/TS/Go/Rust files to extract classes, type annotations, signatures, and docstrings while stripping function bodies. **Saves up to 80% tokens** while giving the LLM the complete architecture!
- 🔒 **Active Secret Safeguards:** Built-in scanner automatically detects and redacts OpenAI, Anthropic, AWS, GitHub, and private keys before your prompt is ever generated.
- ⚡ **Smart Ignore & Filtering:** Full `.gitignore` wildmatch support + built-in defaults that filter binaries, lockfiles (`package-lock.json`, `poetry.lock`), and virtual environments.
- 📋 **Zero-Friction Clipboard:** `--copy` instantly places the formatted digest onto your system clipboard (Windows, macOS, Linux) for pasting straight into AI chats.
- 📐 **Multiple Formats:**
  - `markdown`: Clean Markdown with code fences and table of contents.
  - `xml`: Claude/Anthropic prompt-optimized `<documents><document>` structure.
  - `json`: Machine-readable schema for automated pipelines.
  - `plain`: Clean delimiter-separated text.
- 📊 **Token Analytics:** Accurate token count estimation with per-extension breakdown tables and largest-file detection.
- 🪶 **Lightweight & Fast:** Pure Python core, minimal dependencies, sub-second execution on large repos.

---

## 🚀 Quick Start

### Installation

```bash
# Install via pip
pip install repodigest

# Or run instantly with pipx / uv
pipx run repodigest
```

### 1-Minute Usage

```bash
# Package current directory into digest.md
repodigest

# Package and copy directly to clipboard for ChatGPT / Claude
repodigest --copy

# Compress large files into AST skeletons to save tokens
repodigest --mode skeleton --copy

# Output Claude-optimized XML format
repodigest --format xml -o prompt.xml

# Package only your uncommitted / staged git changes
repodigest diff --copy
```

---

## 🖥️ Terminal Experience

Inspect your codebase metrics without generating a digest:

```bash
repodigest analyze
```

```text
╭───────────────────────── repodigest v0.1.0 ─────────────────────────╮
│  Total Files Included    18                                         │
│  Total Lines of Code     2,450                                      │
│  Estimated Tokens        ~14,280                                    │
│  Total Codebase Size     84.2 KB                                    │
│  Destination             digest.md                                  │
╰─────────────────────────────────────────────────────────────────────╯
```

---

## 📖 CLI Usage

```text
Usage: repodigest [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --version  Show version and exit.
  --help         Show this message and exit.

Commands:
  pack     Package repository into an optimized context document.
  analyze  Inspect codebase metrics, token counts, and language distribution.
  diff     Package only git uncommitted and staged changes.
  init     Create a .repodigest.json configuration file.
```

### `repodigest pack` Options

| Option | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| `--output` | `-o` | Output file path | `digest.<format>` |
| `--format` | `-f` | Output format (`markdown`, `xml`, `json`, `plain`) | `markdown` |
| `--mode` | `-m` | Inclusion mode (`full`, `skeleton`, `auto`) | `full` |
| `--copy` | `-c` | Copy digest directly to system clipboard | `False` |
| `--stdout` | | Stream formatted output directly to stdout | `False` |
| `--diff` | | Only include git-modified or staged files | `False` |
| `--include` | `-i` | Glob patterns to include (e.g. `*.py`, `src/**`) | `None` |
| `--exclude` | `-e` | Glob patterns to exclude | `None` |
| `--max-size` | | Maximum file size threshold (e.g. `500kb`, `1mb`) | `500kb` |
| `--no-redact-secrets` | | Disable secret scanning and redaction | `False` |
| `--no-tree` | | Omit directory ASCII tree from digest | `False` |
| `--quiet` | `-q` | Suppress banner and progress bars | `False` |

---

## ⚙️ Configuration

Generate a configuration file in your project root:

```bash
repodigest init
```

This creates `.repodigest.json`:

```json
{
  "output_format": "markdown",
  "mode": "full",
  "max_size": "500kb",
  "include": [],
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

We welcome community contributions, bug reports, and suggestions!
Please see [CONTRIBUTING.md](CONTRIBUTING.md) for local development setup and guidelines.

1. Fork the repo & clone locally
2. Create your branch (`git checkout -b feature/amazing-feature`)
3. Install dev dependencies (`pip install -e ".[dev]"`)
4. Run tests (`pytest`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
