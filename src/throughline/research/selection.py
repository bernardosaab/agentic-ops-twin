"""Budgeted ranking and selection: equal allocation versus OCBA-style sequential allocation.

Procedures draw replications without replacement from a precomputed pool per alternative (so
macro-replications are cheap); correctness is judged against separate long-run means. Resampling
from a finite pool understates variability somewhat at budgets close to the pool size.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np


def ocba_fractions(means: np.ndarray, sds: np.ndarray) -> np.ndarray:
    """Asymptotic OCBA allocation for selecting the minimum (Chen et al.)."""
    k = len(means)
    b = int(np.argmin(means))
    sds = np.maximum(sds, 1e-9)
    delta = means - means[b]
    w = np.zeros(k)
    others = [i for i in range(k) if i != b]
    delta_o = np.maximum(np.abs(delta[others]), 1e-9)
    w[others] = (sds[others] / delta_o) ** 2
    w[b] = sds[b] * math.sqrt(float(np.sum((w[others] / sds[others]) ** 2)))
    out: np.ndarray = w / w.sum()
    return out


def equal_allocation(pool: Sequence[np.ndarray], budget: int, rng: np.random.Generator) -> int:
    k = len(pool)
    n = budget // k
    means = [rng.permutation(p)[:n].mean() for p in pool]
    return int(np.argmin(means))


def ocba_allocation(
    pool: Sequence[np.ndarray], budget: int, rng: np.random.Generator, n0: int = 5, delta: int = 10
) -> int:
    k = len(pool)
    orders = [rng.permutation(len(p)) for p in pool]
    n = np.full(k, n0)
    used = n0 * k
    while used < budget:
        means = np.array([pool[i][orders[i][: n[i]]].mean() for i in range(k)])
        sds = np.array([pool[i][orders[i][: n[i]]].std(ddof=1) for i in range(k)])
        add = min(delta, budget - used)
        target = ocba_fractions(means, sds) * (used + add)
        need = np.maximum(target - n, 0)
        cap = np.array([len(p) for p in pool]) - n
        need = np.minimum(need, cap)
        if need.sum() <= 0:
            # Fall back to the least-sampled alternative with remaining pool.
            i = int(np.argmin(np.where(cap > 0, n, np.iinfo(np.int64).max)))
            if cap[i] <= 0:
                break
            n[i] += 1
            used += 1
            continue
        alloc = np.floor(need / need.sum() * add).astype(int)
        rem = add - int(alloc.sum())
        for i in np.argsort(-(need - alloc))[:rem]:
            alloc[i] += 1
        alloc = np.minimum(alloc, cap)
        if alloc.sum() == 0:
            break
        n += alloc
        used += int(alloc.sum())
    means = np.array([pool[i][orders[i][: n[i]]].mean() for i in range(k)])
    return int(np.argmin(means))


def pcs(
    pool: Sequence[np.ndarray],
    true_means: np.ndarray,
    budget: int,
    procedure: str,
    macro: int,
    delta_iz: float,
    seed: int,
) -> tuple[float, float]:
    """Probability of correct selection (within indifference zone) and its standard error."""
    rng = np.random.default_rng(seed)
    best = float(true_means.min())
    hits = 0
    for _ in range(macro):
        choice = (
            equal_allocation(pool, budget, rng)
            if procedure == "equal"
            else ocba_allocation(pool, budget, rng)
        )
        hits += int(true_means[choice] - best <= delta_iz)
    p = hits / macro
    return p, math.sqrt(p * (1 - p) / macro)
