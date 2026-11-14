"""Replication statistics: t-intervals, paired and Welch differences.

Pairing is used only when every replication pair has an identical arrival-stream digest. If any
pair differs (for example the scenarios apply different demand conditions), the comparison falls
back to an unpaired Welch interval and says so.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from functools import lru_cache
from typing import Literal

from pydantic import Field

from throughline.core.metrics import LOWER_IS_BETTER, ReplicationMetrics
from throughline.core.model import Frozen


@lru_cache(maxsize=4096)
def t_quantile(q: float, df: float) -> float:
    """Student-t quantile; SciPy is imported lazily so simulation workers stay lightweight."""
    from scipy import stats as sps

    return float(sps.t.ppf(q, df))


class Estimate(Frozen):
    metric: str
    n: int = Field(description="Replications with a defined value.")
    n_undefined: int = Field(description="Replications where the metric was undefined.")
    mean: float | None
    sd: float | None
    ci95_low: float | None
    ci95_high: float | None


class Difference(Frozen):
    metric: str
    method: Literal["paired", "welch", "unavailable"]
    pairing_note: str
    n: int
    mean_difference: float | None = Field(description="alternative minus reference")
    ci95_low: float | None
    ci95_high: float | None
    better: Literal["alternative", "reference", "inconclusive", "unavailable"]


def estimate(metric: str, values: Sequence[float | None], level: float = 0.95) -> Estimate:
    xs = [v for v in values if v is not None and math.isfinite(v)]
    n = len(xs)
    undefined = len(values) - n
    if n == 0:
        return Estimate(
            metric=metric,
            n=0,
            n_undefined=undefined,
            mean=None,
            sd=None,
            ci95_low=None,
            ci95_high=None,
        )
    mean = sum(xs) / n
    if n == 1:
        return Estimate(
            metric=metric,
            n=1,
            n_undefined=undefined,
            mean=mean,
            sd=None,
            ci95_low=None,
            ci95_high=None,
        )
    sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / (n - 1))
    half = t_quantile(0.5 + level / 2, n - 1) * sd / math.sqrt(n)
    return Estimate(
        metric=metric,
        n=n,
        n_undefined=undefined,
        mean=mean,
        sd=sd,
        ci95_low=mean - half,
        ci95_high=mean + half,
    )


def summarise(runs: Sequence[ReplicationMetrics], metrics: Sequence[str]) -> dict[str, Estimate]:
    return {m: estimate(m, [r.scalar(m) for r in runs]) for m in metrics}


def pairing_status(
    ref: Sequence[ReplicationMetrics], alt: Sequence[ReplicationMetrics]
) -> tuple[bool, str]:
    if len(ref) != len(alt):
        return False, "different replication counts"
    if [r.seed for r in ref] != [a.seed for a in alt]:
        return False, "seed lists differ"
    mismatched = sum(r.arrival_digest != a.arrival_digest for r, a in zip(ref, alt, strict=True))
    if mismatched:
        return False, f"{mismatched}/{len(ref)} arrival-stream digests differ; unpaired comparison"
    return True, f"all {len(ref)} arrival-stream digests verified identical"


def _verdict(
    metric: str, lo: float, hi: float
) -> Literal["alternative", "reference", "inconclusive"]:
    lower_better = metric in LOWER_IS_BETTER
    if hi < 0:
        return "alternative" if lower_better else "reference"
    if lo > 0:
        return "reference" if lower_better else "alternative"
    return "inconclusive"


def compare(
    metric: str, ref: Sequence[ReplicationMetrics], alt: Sequence[ReplicationMetrics]
) -> Difference:
    paired, note = pairing_status(ref, alt)
    if paired:
        diffs = []
        for r, a in zip(ref, alt, strict=True):
            rv, av = r.scalar(metric), a.scalar(metric)
            if rv is not None and av is not None:
                diffs.append(av - rv)
        if len(diffs) < 2:
            return Difference(
                metric=metric,
                method="unavailable",
                pairing_note=note,
                n=len(diffs),
                mean_difference=None,
                ci95_low=None,
                ci95_high=None,
                better="unavailable",
            )
        e = estimate(metric, diffs)
        assert e.mean is not None and e.ci95_low is not None and e.ci95_high is not None
        return Difference(
            metric=metric,
            method="paired",
            pairing_note=note,
            n=e.n,
            mean_difference=e.mean,
            ci95_low=e.ci95_low,
            ci95_high=e.ci95_high,
            better=_verdict(metric, e.ci95_low, e.ci95_high),
        )
    er = estimate(metric, [r.scalar(metric) for r in ref])
    ea = estimate(metric, [a.scalar(metric) for a in alt])
    if er.n < 2 or ea.n < 2 or er.sd is None or ea.sd is None:
        return Difference(
            metric=metric,
            method="unavailable",
            pairing_note=note,
            n=min(er.n, ea.n),
            mean_difference=None,
            ci95_low=None,
            ci95_high=None,
            better="unavailable",
        )
    assert er.mean is not None and ea.mean is not None
    vr, va = er.sd**2 / er.n, ea.sd**2 / ea.n
    se = math.sqrt(vr + va)
    d = ea.mean - er.mean
    if se == 0:
        lo = hi = d
    else:
        df = (vr + va) ** 2 / ((vr**2 / (er.n - 1)) + (va**2 / (ea.n - 1)))
        half = t_quantile(0.975, df) * se
        lo, hi = d - half, d + half
    return Difference(
        metric=metric,
        method="welch",
        pairing_note=note,
        n=min(er.n, ea.n),
        mean_difference=d,
        ci95_low=lo,
        ci95_high=hi,
        better=_verdict(metric, lo, hi),
    )
