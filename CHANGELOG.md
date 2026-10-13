# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-13

### Added
- Core codebase discovery and packaging engine (`Collector`).
- `.gitignore` wildmatch support powered by `pathspec` with fallbacks.
- Default ignore rules for build artifacts, virtualenvs, cache files, and node_modules.
- Binary file detection via byte inspection and known extension matching.
- AST skeleton extraction for Python with function, class, and docstring preservation.
- Signature outlines for TypeScript, JavaScript, Go, and Rust.
- Real-time secret scanning and automatic redaction for OpenAI, Anthropic, AWS, GitHub, and private keys.
- Output formatting: Markdown, XML (Claude-optimized), JSON, and Plaintext.
- Cross-platform clipboard support with native OS fallbacks (PowerShell, pbcopy, xclip).
- CLI commands: `pack`, `analyze`, `diff`, and `init`.
- Complete test suite and GitHub Actions CI workflow.
