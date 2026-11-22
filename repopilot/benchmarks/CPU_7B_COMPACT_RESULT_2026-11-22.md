# Independent compact 7B preflight: unresolved

[Run 44998179241](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44998179241) completed both jobs. The official result is 1 submitted, 1 evaluated, 0 resolved, 1 unresolved, 0 evaluator errors. This is a single unassisted task, not a new full-cohort result.

- [Generation artifact 14744697711](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44998179241/artifacts/14744697711): SHA-256 `20edd223d2ae82fb412cd9c68ff937dffab5dbc7dd54914cd6013d1a8cc59e1b`.
- [Official artifact 14744554824](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44998179241/artifacts/14744554824): SHA-256 `468586fd9f8b671bdc1d812d2e501e2b52decb75f99cd0d4b4f968e21e196d24`.
- Both archives contain identical predictions.jsonl bytes (SHA-256 `5e4a56014acfdf4f6072b28614690f78215b84d22a46ccdf9ca7b49b3ce42d0d`).
- Official JSON SHA-256 `0bc3dee3c27b90327e83ca99a778eec73813f68d68757629e3872ac213d5d8a2`.
- Qwen2.5-Coder 7B model digest `dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`; warmup 5.984 generated tokens/s; attempt elapsed 454685 ms.

The model repeated placeholder search/read values and made changes to unrelated auth files. The prediction introduced improperly indented lines; static review returned unavailable and the smoke baseline was inconclusive. No valid behavioral repair was demonstrated. The follow-up gate distinguishes introduced compile regressions from unavailable analysis, checks every modified file before returning a verdict, and rejects compile-regressing candidates before smoke/evaluation. Compilation does not execute target source. An unsupported baseline remains unavailable. The model experiment is now manual-only to avoid repeated costly runs without a substantially different approach. No accuracy improvement or full-cohort launch is warranted. Last comparable official baseline: 1/12 (8.3%). Stable v2.2.0 remains unchanged.
