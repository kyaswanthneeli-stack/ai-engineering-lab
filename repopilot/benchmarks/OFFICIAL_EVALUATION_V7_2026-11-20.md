# RepoPilot v7 — independently verified SWE-bench Lite result (November 20, 2026)

**Official outcome: 1 resolved / 12 selected = 8.3%, unchanged from v6.** More legitimate model patches were submitted (7 vs 6), but only the same SymPy issue was independently resolved.

This report relies on [official v7 GitHub Actions run #44753246638](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44753246638), the [official evaluation ZIP artifact #14641033373](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44753246638/artifacts/14641033373) and [model-attempts ZIP #14638963126](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44753246638/artifacts/14638963126). Both jobs finished successfully. **A green job is not proof that every issue was fixed.**

## Reproducibility and provenance

- **Commit:** `9a1a59b7351d7d1bccbab3df38ad78bcb5faa10e`, including merged [bounded Ollama retry PR #37](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/37) and [implementation-localization PR #40](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/pull/40)
- **Model:** `qwen2.5-coder:3b` running on CPU via native localhost Ollama
- **Dataset:** `princeton-nlp/SWE-bench_Lite`, the same 12 fixed task IDs and base commits used in v6
- **Harness:** official independent `swebench.harness.run_evaluation`, run ID `repopilot-12-qwen3b-v7`
- **Original v7 manifest SHA-256:** `1e2f90672055036e11c0bbe4c533e4382fd451a4b021ab7901a3a2881aeed48c`
- **Submitted predictions JSONL SHA-256:** `42b677dd9bbe9cb9cdf6e524a0f02c284e7cd623af12f46cde4e0feafe31835e`
- **Original official-evaluation-result.json SHA-256:** `0915925d6f7c0f4a1a1f06b49a8a6626db64c82e7a56bec5aedd04db1e231e37`
- **Original official-summary.json SHA-256:** `d8500fb3871fe343f495c2863ff7ad9afc7acff6d0d06c90bfd393da0b9d3102`
- **Provenance JSON SHA-256:** `1894db405411c8cb5e0f47a2ebbd45d2e6a5aa931188c3fbcca14a5c1eded47d`

The official harness scored exactly the **seven genuine model-generated submitted patches**. The five issues without predictions were **not** officially evaluated. Consequently, the summary field `is_complete_12_task_evaluation` is correctly **false**.

## v6 vs v7

| Metric | Verified v6 | Verified v7 |
|---|---:|---:|
| Selected issues | 12 | 12 |
| Submitted model patches | 6 | 7 |
| Independently evaluated | 6 | 7 |
| Resolved patches | 1 | 1 |
| Unresolved evaluated patches | 5 | 6 |
| Evaluator errors | 0 | 0 |
| No-patch attempts (not evaluated) | 6 | 5 |
| Hard outer per-task timeouts | 0 | 0 |
| Resolved / selected | 1/12 (8.3%) | 1/12 (8.3%) |
| Resolved / submitted | 1/6 (16.7%) | 1/7 (14.3%) |

**No official solve-rate improvement occurred.** v7 generated one extra submitted patch but did not resolve any additional issue. The only resolved task in both experiments was `sympy__sympy-14774`.

## Exact official v7 task outcomes

**Resolved:** `sympy__sympy-14774`.

**Submitted, independently evaluated, unresolved:**
- `django__django-12113`
- `django__django-12125`
- `django__django-14730`
- `matplotlib__matplotlib-22835`
- `scikit-learn__scikit-learn-12471`
- `sympy__sympy-13773`

**Attempted, no patch submitted, not officially evaluated:**
- `django__django-12589`: `TransientOllamaError`
- `sympy__sympy-11870`: `TransientOllamaError`
- `sympy__sympy-20212`: `TransientOllamaError`
- `pytest-dev__pytest-11148`: agent deadline expired before native retry
- `pydata__xarray-4493`: `TransientOllamaError`

## Source-level diagnosis from actual failed model patches

These are code inspection findings from the **original pinned repository source**, not hidden-test diagnostics or gold/reference patches.

1. **SymPy geometry regression, `sympy__sympy-13773`.** The proposed patch adds `not isinstance(p1, Matrix) or not isinstance(p2, Matrix)` to `LinearEntity.__new__` after `Point._normalize_dimension`. The normal arguments are geometry `Point` objects (which inherit `GeometryEntity`, not `Matrix`); ordinary valid `Line(Point(...), Point(...))` would be rejected. This is an obvious semantic regression missed by `git apply --check`.
2. **Django constructor regression, `django__django-12125`.** The proposed patch reads `self.model._meta.get_field(ct_field).column` from `GenericForeignKey.__init__`. In the pinned original, `self.model` is assigned only later in `contribute_to_class`, so normal field construction would raise before model attachment. This also replaces the field name with a database column identifier, which changes its intended meaning.
3. **Django redundant default override, `django__django-14730`.** The proposed patch changes `BaseModelAdmin.formfield_overrides` from an empty mapping to a copy of `FORMFIELD_FOR_DBFIELD_DEFAULTS`. The existing `BaseModelAdmin.__init__` already deep-copies and merges those defaults into overrides, so the model made a change that duplicates existing behavior rather than demonstrating a fix for the reported bug.

The other three unresolved submitted patches (`django__django-12113`, `matplotlib__matplotlib-22835`, `scikit-learn__scikit-learn-12471`) are officially failed repairs, but the precise root cause **cannot** be determined from the final diff alone. Do not overstate why the hidden tests failed.

## Priority order (evidence-based)

**P1 — Add bounded semantic candidate verification before patch export.** Current generation enforces inspected-path validation, Python syntax, and `git apply --check`, but those checks accept code that changes intended behavior. Run a narrowly selected, fail-safe, short behavior smoke test for patched implementation inside the existing **restricted Docker sandbox** where dependencies allow, ideally against unmodified and modified worktrees; obtain sanitized failure feedback for a single bounded model correction. Do not execute untrusted code on the host, use gold/reference patches, depend on hidden tests, or claim that a smoke-test pass is an official resolution. Add unit tests for candidates that apply cleanly but break otherwise-valid construction or import paths.

**P2 — Improve CPU Ollama inference reliability and budget scheduling.** Five tasks still had no submitted patch despite bounded retry. Prefer measured prompt/deadline diagnostics and early graceful fallback rather than escalating unlimited retries.

**P3 — Upgrade failure-to-issue feedback.** Use the independent evaluator's complete unresolved IDs plus safely retrieved public issue context to improve bug localization, and compare against the same pinned cohort again before making a new score claim.

**Limits:** This is a fixed 12-task SWE-bench Lite sample (not all SWE-bench Lite instances). The released portfolio prototype remains separate from research on general-purpose autonomous bug solving. Human approval remains required for production PR merges.
