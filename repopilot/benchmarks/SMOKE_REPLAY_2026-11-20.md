# Four-case v9 smoke replay — November 20, 2026

**Usable smoke baselines: 1/4 before, 3/4 after opt-in import setup.** This is
validation coverage on four preserved proposals, not a new model benchmark or
bug-resolution result. Official v9 remains **1/12 selected resolved (8.3%)**.

## Reproducible evidence

- [Initial diagnostic replay #44797079190](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44797079190), source `b2b4d03a2177c1c7308789d9bb870dc771d05a46`, reproduced three inconclusive baselines and one passing control.
- [Final paired replay #44798561583](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44798561583), source `96d58064841f53d9c1a6975dc586148e8aa6d8ca`, runs the same diagnostic implementation with `REPOPILOT_CANDIDATE_SMOKE_BOOTSTRAP=0` and `=1`.
- [Final artifact #14659378046](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44798561583/artifacts/14659378046), verified ZIP SHA-256 `f0e19bed2828b84cad33cac195eb6782654358a25b472c22669a52b4da4da138`.
- Byte-preserved [before summary](evidence/smoke-replay-2026-11-20/before/summary.json), [after summary](evidence/smoke-replay-2026-11-20/after/summary.json), and [retrieval/file checksums](evidence/smoke-replay-2026-11-20/retrieval-provenance.json).
- [Original official v9 run](https://github.com/kyaswanthneeli-stack/ai-engineering-lab/actions/runs/44776554310), source `5ffdcd5695fc2df32fef40d0e388a04798f4dee7`, supplies the original proposals, scorecard and SHA-256 provenance. The replay verifies those hashes and recomputes the historical 12/6/6/1 selected/submitted/evaluated/resolved counts before checkout.

Both conditions use identical original patch hashes, public issue statements,
pinned commits, trusted Python 3.10 dependency image and Docker restrictions.
There are four cases, eight smoke invocations and **zero model calls**. The
official evaluator is not run; `officially_resolved` stays null in both outputs.

## Measured outcomes

| Pinned instance | Before | After import setup | Interpretation |
|---|---|---|---|
| `sympy__sympy-13773` | Inconclusive: `legacy_collections_api` | Original import 0, candidate import 0 | Legacy `collections` aliases restored inside Docker; weak usable baseline |
| `django__django-12125` | Inconclusive: `configuration_error` | Original import 0, candidate import 0 | Minimal in-memory settings/app registry enables import; weak usable baseline |
| `matplotlib__matplotlib-22835` | Inconclusive: `import_error` in issue example and import fallback | Inconclusive: `native_extension_unavailable` in both | Source layout resolves; native runtime remains unsupported |
| `django__django-12589` (control) | Original import 0, candidate import 0 | Original import 0, candidate import 0 | Existing passing control preserved |

The SymPy checkout directly imports `Mapping` and `MutableMapping` from
`collections`, defines a class inheriting `collections.MutableSet`, and uses
other legacy aliases. Restoring nine fixed ABC aliases from `collections.abc`
removes this import compatibility blocker in the small replay. It does not
modify the source or generate a corrected patch.

The Django contenttypes module imports application models, which require a
configured app registry. A developer-owned contenttypes/in-memory SQLite setup
removes that baseline blocker. It executes only inside the offline sandbox and
is identical for original and candidate. Public issue examples retain their
own setup; the prefix applies to generated import probes and import fallbacks.

Matplotlib uses `lib/matplotlib` and requires native extensions such as
`_c_internal_utils`. The optional source-layout correction reveals that further
runtime blocker. No native build or arbitrary dependency installation is added,
and this case remains inconclusive. Generated imports now check their file
origin, preventing installed packages from impersonating the pinned source.

## Limits and next gate

All three usable outcomes are `no_regression_observed: limited_probe_only`.
**Zero confirmed regressions were found by this four-case import replay.** The
original proposals remain officially unresolved: imports do not establish that
their semantic changes fix the reported bug. This diagnostic subset excludes
the six v9 attempts that generated no patch and is not representative of all
twelve tasks.

The import profile defaults to **off** and remains an explicit operator choice.
Real Docker CI separately proves a legacy-import baseline can pass with the
profile while an import-breaking candidate fails; it is not promoted to a solve.

Before another full benchmark, strengthen behavior probes and repository-file
selection on a controlled subset, and supply a trusted compatible native runtime
for Matplotlib or keep that limitation explicit. Repeating a full benchmark on
the basis of three successful imports alone is not justified. Keep model patch
generation, smoke coverage and independently evaluated resolution separate.
