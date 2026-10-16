# 🛡️ Security Policy

`focuspack` operates entirely locally and offline on your machine. Because `focuspack` prepares source code for LLM reasoning and code review, data privacy, filesystem isolation, and credential redaction are foundational guarantees.

---

## 📜 Technical Guarantees

### 1. 🌐 Zero Network Egress (100% Offline)
- **Zero Network Calls:** `focuspack` contains zero HTTP clients, sockets, or network communication libraries in its runtime.
- **Zero Telemetry:** No usage metrics, tracking pings, crash reports, or analytics are collected or transmitted.
- **Offline & Air-Gap Ready:** `focuspack` runs completely offline without internet connectivity.
- **No LLM Proxying:** `focuspack` does not invoke Claude, OpenAI, Gemini, or any LLM provider directly. It generates clean context files for the developer to review and pass explicitly.

### 2. 🔐 In-Place Credential Redaction
Before any source code is packaged or copied to the clipboard, `focuspack` runs an automated secret redaction pass:
- **API Keys & Tokens:** OpenAI (`sk-...`), Anthropic (`sk-ant-...`), GitHub tokens (`ghp_...`, `github_pat_...`), Slack tokens.
- **Cloud Infrastructure:** AWS Access Keys (`AKIA...`), AWS Secret Access Keys.
- **Database Connection Strings:** Password scrubbing across PostgreSQL, MySQL, MongoDB, Redis, and MSSQL connection URLs while preserving hostname and port for structural context.
- **Private Keys:** RSA, OpenSSH, and PEM-encoded private keys.
- **In-Place Redaction:** Secrets are sanitized in-place with safe placeholder tokens (e.g. `[REDACTED_SECRET: OPENAI_API_KEY]`), keeping Python syntax and imports intact.

### 3. 📂 Filesystem & Symlink Containment
- **Repository Boundary Protection:** `focuspack` verifies that resolved file paths stay within the target directory, preventing symlinks from leaking sensitive files outside the workspace.
- **Deterministic Static Analysis:** Python files are analyzed using standard library `ast.parse()`. `focuspack` never executes code, imports untrusted modules dynamically, or invokes `eval()` / `exec()`.

### 4. 📦 Minimal Supply-Chain Surface Area
- **Strict Dependency Policy:** Governed by [`CHARTER.md`](CHARTER.md) and enforced on every commit by `scripts/check_charter.py`.
- **Zero Heavy Runtime Bloat:** No vector databases, torch/tensorflow, or unvetted C extensions.
- **Type Safety:** PEP 561 compliant (`py.typed`) for static typing verification.

---

## 🔒 Supported Versions

| Version | Supported |
| :--- | :---: |
| `0.2.x` | ✅ Yes |
| `< 0.2.0` | ❌ End of Life |

---

## 🚨 Reporting a Vulnerability

If you discover a security vulnerability or credential redaction bypass:

1. **Do NOT open a public GitHub issue.**
2. Please report findings privately via **GitHub Private Vulnerability Reporting** on the repository or by email to:  
   📧 `maqbul.ansari.dev@gmail.com`
3. Include detailed steps to reproduce the issue (including any sample snippets or patterns).
4. You will receive an initial response with a remediation plan and patch timeline.
