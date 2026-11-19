# Synthetic integration issue: invoice rounding and validation

The invoice calculation currently leaves floating-point artifacts in the total and permits negative line-item prices. The correct behavior is to round currency subtotals and final totals to two decimals, and reject negative line prices with ValueError. Implement the fix across pricing.py and checkout.py while keeping the original invoice test green.

This is a curated **reference-patch multi-file verification fixture**, not a model-generated resolution and not a SWE-bench issue.
