# 🛡️ Security Policy & Compliance Certifications

`focuspack` is engineered for sensitive, enterprise-grade development environments. Because `focuspack` prepares source code for LLM reasoning, security, data privacy, and strict containment are foundational architectural guarantees.

---

## 📜 Architectural Certifications & Guarantees

### 1. 🌐 Zero Network Egress (Air-Gapped & Offline-First)
- **Zero Network Calls:** `focuspack` contains zero HTTP clients, sockets, or external communication libraries in its core runtime.
- **Zero Telemetry:** No usage metrics, tracking pings, crash reports, or analytics are collected or transmitted.
- **Air-Gap Compatible:** `focuspack` runs completely offline in air-gapped, defense, healthcare, and enterprise environments without internet access.
- **No LLM Proxying:** `focuspack` does not invoke Claude, OpenAI, Gemini, or any LLM provider directly. It compiles clean context files for the developer to review or pass explicitly.

### 2. 🔐 In-Place Credential Redaction (Data Loss Prevention)
Before any source code is packaged or copied to the clipboard, `focuspack` runs an automated secret redaction pass:
- **API Keys & Tokens:** OpenAI (`sk-...`), Anthropic (`sk-ant-...`), GitHub tokens (`ghp_...`, `github_pat_...`), Slack tokens.
- **Cloud Infrastructure:** AWS Access Keys (`AKIA...`), AWS Secret Access Keys.
- **Database Connection Strings:** Complete password scrubbing across PostgreSQL, MySQL, MongoDB, Redis, and MSSQL connection URLs while preserving hostname and port for structural context.
- **Private Keys:** RSA, OpenSSH, and PEM-encoded private keys.
- **In-Place Redaction:** Secrets are sanitized *in-place* with safe placeholder tokens (e.g. `[REDACTED_SECRET: OPENAI_API_KEY]`), keeping Python AST integrity intact and preventing broken imports.

### 3. 🛡️ Deterministic Static Analysis (Zero Code Execution)
- **Safe AST Parsing:** Python code is inspected purely via Python's standard library `ast.parse()`. `focuspack` **never** executes code, imports modules dynamically, or invokes `eval()` / `exec()`.
- **Syntax Isolation:** Syntax warnings and non-standard escapes from external codebases are cleanly isolated during analysis.

### 4. 📦 Supply-Chain Integrity & Scope Guard
- **Strict Dependency Budget:** Governed by [`CHARTER.md`](CHARTER.md) and verified on every commit by `scripts/check_charter.py`.
- **Zero Heavy Bloat:** No vector databases, torch/tensorflow, unvetted C extensions, or electron desktop runtimes.
- **Type Safety:** PEP 561 compliant (`py.typed`) for end-to-end static typing verification with Mypy and Pyright.

---

## 🏢 Enterprise Compliance Compatibility

`focuspack` is designed to be fully compatible with corporate security and compliance frameworks:

| Standard | Focuspack Design Feature |
| :--- | :--- |
| **SOC 2 Type II (Confidentiality & Privacy)** | Zero data retention; all processing is transient in local process memory. In-place credential masking prevents confidential keys from reaching LLM logs. |
| **ISO/IEC 27001 (A.8.24 Use of Cryptography & Secrets)** | Proactive detection and redaction of hardcoded secrets before prompt construction. |
| **HIPAA (Data Minimization)** | Peripheral pruning removes unrelated patient or application data, sending only the focused target and required interface contracts. |
| **Supply Chain Levels for Software Artifacts (SLSA)** | Deterministic builds, minimal surface area, automated CI verification across Linux, macOS, and Windows. |

---

## 🔒 Supported Versions

| Version | Supported |
| :--- | :---: |
| `0.2.x` | ✅ Yes |
| `< 0.2.0` | ❌ End of Life |

---

## 🚨 Reporting a Vulnerability

We take the security of `focuspack` seriously. If you discover a security vulnerability or credential bypass:

1. **Do NOT open a public GitHub issue.**
2. Please report findings privately to the security team via **GitHub Private Vulnerability Reporting** on the repository or by email to:  
   📧 `maqbul.ansari.dev@gmail.com`
3. Include detailed steps to reproduce the issue (including any sample snippets or patterns).
4. You will receive an initial response within **24–48 hours** with a patch timeline and remediation plan.
