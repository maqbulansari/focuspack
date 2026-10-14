## Description
Briefly describe the change and why it was made.

## Type of Change
- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] ⚡ Performance improvement / code refactor

## 🎯 Goal Alignment Verification (See [CHARTER.md](../CHARTER.md))
Before opening this PR, verify alignment with `focuspack`'s core mission:
- [ ] **Strengthens Core Pillars:** This PR directly improves Focus Target Retention, AST Dependency Contracts, Adaptive Token Budgeting, or Pure-Python Portability.
- [ ] **Respects Non-Goals:** This PR does NOT introduce any Non-Goals (no vector DBs/RAG, no cloud APIs, no Web UIs, no flat monolithic dumping, no brittle regex line-parsers).
- [ ] **Target Inviolability:** Focus target files are preserved or adaptively tiered—never silently omitted or truncated.
- [ ] **Zero-Node Runtime:** No Node.js/npm or heavy native C++ build toolchains were introduced.

## Checklist
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] All new and existing tests passed (`pytest`)
- [ ] Linting checks passed (`ruff check .`)
