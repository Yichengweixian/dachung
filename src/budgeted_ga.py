"""Frozen U12R02 budget and post-search decision calculation."""
import numpy as np
from .genetic_search import run_ga

SEEDS = [42, 7, 2026, 11, 23, 101, 314, 509, 1024, 4096]
PARAMETERS = dict(population=12, generations=7, eta_c=15, eta_m=20,
                  crossover_probability=.9, mutation_probability=.5)


def search(evaluate_batch, seed, progress=None):
    best, cost, history = run_ga(evaluate_batch, PARAMETERS, seed, progress)
    if len(history) != 89 or [r['evaluation'] for r in history] != list(range(1, 90)):
        raise ValueError('Incorrect objective count')
    if np.any(np.diff([r['best_cost'] for r in history]) > 0):
        raise ValueError('Increasing incumbent cost')
    return best, cost, history


def decision(table, benchmark):
    if not np.isfinite(benchmark) or benchmark <= 0:
        raise ValueError('Invalid benchmark')
    if len(table) != 10 or set(table.seed) != set(SEEDS):
        raise ValueError('Incomplete primary seed set')
    if not (table.evaluations == 89).all() or not np.isfinite(table.cost).all():
        raise ValueError('Invalid budget or cost')
    result = table.copy()
    result['signed_relative_difference'] = (result.cost-benchmark)/benchmark
    result['absolute_relative_difference'] = result.signed_relative_difference.abs()
    result['quality_loss'] = result.signed_relative_difference.clip(lower=0)
    result['passed'] = result.quality_loss < .005
    return result, 'supported' if int(result.passed.sum()) >= 9 else 'inconclusive'
