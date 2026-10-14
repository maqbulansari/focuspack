# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-14

### Added
- **Focus-Driven Traversal Engine**: Automated AST import graph resolution (`DependencyGraph`) with `--focus` (`-F`).
- **Semantic Role Labeling**: Classifies code into `focus_target` (full code), `dependency_contract` (interface skeletons), and `peripheral`.
- **Adaptive Token Budgeting**: Real dynamic fitting with `--budget` (`-b`) to strictly guarantee prompts fit inside context windows (e.g. 32k, 64k).
- **Task / Mission Prompt Templates**: Pre-built system instructions with `--task` (`-t`) for `bugfix`, `review`, `refactor`, `explain`, and `test`.
- **Enhanced XML Layout**: Context manifest with role counts, utilization percentage, and prompt-cache friendly deterministic tags.
- Renamed project to **focuspack** with CLI aliases `focuspack` and `fp`.

## [0.1.0] - 2026-10-13

### Added
- Core codebase discovery and packaging engine (`Collector`).
- `.gitignore` wildmatch support powered by `pathspec` with fallbacks.
- Default ignore rules for build artifacts, virtualenvs, cache files, and node_modules.
- Binary file detection via byte inspection and known extension matching.
- AST skeleton extraction for Python with function, class, and docstring preservation.
- Real-time secret scanning and automatic redaction for OpenAI, Anthropic, AWS, GitHub, and private keys.
- Output formatting: Markdown, XML, JSON, and Plaintext.
- Cross-platform clipboard support with native OS fallbacks.
- CLI commands: `pack`, `analyze`, `diff`, and `init`.
