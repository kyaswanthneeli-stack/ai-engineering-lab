"""Security helpers for secret redaction, prompt-injection delimiters, and path safety."""

from __future__ import annotations

import os
import re
import secrets
from pathlib import Path

_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{16,})\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\b(github_pat_[A-Za-z0-9_]{20,})\b"), "[REDACTED_GITHUB_PAT]"),
    (re.compile(r"\b(sk-[A-Za-z0-9_-]{20,})\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"\b(gsk_[A-Za-z0-9]{20,})\b"), "[REDACTED_GROQ_KEY]"),
    (re.compile(r"\b(AIza[0-9A-Za-z_-]{25,})\b"), "[REDACTED_GOOGLE_KEY]"),
    (re.compile(r"(?i)(Authorization\s*:\s*(?:Bearer|Basic|Token)\s+)[^\s\"']+"), r"\1[REDACTED_AUTH]"),
    (re.compile(r"(?i)((?:GITHUB_TOKEN|REPOPILOT_API_KEY|API_KEY|TOKEN|SECRET)\s*=\s*)[^\s\"']+"), r"\1[REDACTED_ENV]"),
)

_PROCESS_NONCE = secrets.token_hex(6)


def redact_secrets(text: str) -> str:
    """Scrub common API keys, GitHub tokens, and auth headers from logs and artifacts."""
    if not text:
        return text
    redacted = text
    for pattern, replacement in _SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    for env_name in ("GITHUB_TOKEN", "REPOPILOT_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "REPOPILOT_ACCESS_TOKEN"):
        val = os.getenv(env_name, "")
        if len(val) >= 8 and val in redacted:
            redacted = redacted.replace(val, f"[REDACTED_{env_name}]")
    return redacted


def wrap_untrusted(label: str, text: str, *, nonce: str | None = None) -> str:
    """Wrap untrusted issue/repo/log text in randomized boundary tags."""
    safe_label = re.sub(r"[^a-z0-9_]", "_", label.lower())
    tag_nonce = nonce or _PROCESS_NONCE
    tag = f"untrusted_{safe_label}_{tag_nonce}"
    # Neutralize any accidental or adversarial closing tag inside the payload
    cleaned = text.replace(f"</{tag}>", f"&lt;/{tag}&gt;")
    return f"<{tag}>\n{cleaned}\n</{tag}>"


def validate_safe_relpath(root: Path, rel: str) -> Path:
    """Resolve a relative path under root, rejecting traversal, .git, and symlinks."""
    if not rel or rel.startswith("/") or "\\" in rel:
        raise ValueError(f"Unsafe relative path: {rel!r}")
    parts = [p for p in rel.split("/") if p]
    if not parts or any(p in (".", "..", ".git") for p in parts):
        raise ValueError(f"Unsafe path component in: {rel!r}")
    root_resolved = root.resolve(strict=True)
    cur = root_resolved
    for part in parts:
        cur = cur / part
        if cur.is_symlink():
            raise ValueError(f"Symlink component rejected: {cur}")
    resolved = cur.resolve(strict=False)
    if not resolved.is_relative_to(root_resolved):
        raise ValueError(f"Path escapes workspace root: {rel!r}")
    return resolved


def redact_secrets_recursive(obj):
    """Recursively scrub secrets from nested dicts, lists, and strings."""
    if isinstance(obj, str):
        return redact_secrets(obj)
    if isinstance(obj, list):
        return [redact_secrets_recursive(item) for item in obj]
    if isinstance(obj, dict):
        return {k: redact_secrets_recursive(v) for k, v in obj.items()}
    return obj
