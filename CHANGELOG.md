# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-14

### Added
- **Focus-Driven Traversal Engine**: Automated AST import graph resolution (`DependencyGraph`) with `--focus` (`-F`) supporting relative imports (`from . import models`), submodule imports (`from app.core import store`), and cyclic imports.
- **Semantic Role Labeling**: Classifies code into `focus_target` (full code), `dependency_contract` (interface skeletons), and `peripheral` (pruned by default under focus).
- **Multi-Stage Adaptive Budget Optimizer**: 4 deterministic stages (peripheral pruning $\to$ contract skeletonization $\to$ AST docstring stripping $\to$ large target method body compression) guaranteeing target retention without blind truncation or dropping the focus target.
- **Strict Budget Mode**: `--strict-budget` flag to enforce zero-overflow gating in automated pipelines.
- **Database Credential Redaction**: Automated credential scanning and redaction across connection URLs (`postgres://`, `mysql://`, `mongodb://`, `redis://`, etc.).
- **Task / Mission Prompt Templates**: Pre-built system instructions with `--task` (`-t`) for `bugfix`, `review`, `refactor`, `explain`, and `test`.
- **Product Scope Charter & Governance**: Added `CHARTER.md` defining the North Star, 4 Core Pillars, explicit Non-Goals, and automated PR review bot with GitHub Actions CI.
- **Enhanced XML Layout**: Context manifest with role counts, utilization percentage, directory structure, and prompt-cache friendly deterministic tags.
- Renamed project to **focuspack** with CLI aliases `focuspack` and `fp`.

### Fixed
- Fixed bug where submodule imports resolved to package `__init__.py`.
- Fixed bug where peripheral files were included in full when focus mode was active without budget.
- Fixed docstring compaction damaging multiline code by using `ast.NodeTransformer`.
- Fixed path normalization stripping leading dots from `.git`, `.gitignore`, and `.venv`.
- Fixed Windows terminal `UnicodeEncodeError` with tree box characters by ensuring UTF-8 reconfiguration.


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
