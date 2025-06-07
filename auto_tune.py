#!/usr/bin/env python3
import json
import numpy as np
import random
import time
import subprocess
import sys
from calculate import SEED_CONSTS, calculate, BASE_PD, BONUS_DAY5, RATE_0_100, RATE_101_500, RATE_501_800, RATE_801P, REC_CAP_LOW, REC_CAP_HIGH, ROUND_OFFSET, CURVE_A, PEAK_SPEND, CURVE_B, EFF_CTR, EFF_WDTH, EFF_AMPL, RCPT_BUMP, SECOND_WEEK_PENALTY, CENTS_BUG_F, MILE_CAP_RATE, REC_CAP_RATE, MULT_1D, MULT_5D, MULT_7D, MULT_9D, MULT_14D

CONST_NAMES = [
    'BASE_PD','BONUS_DAY5','RATE_0_100','RATE_101_500','RATE_501_800','RATE_801P',
    'REC_CAP_LOW','REC_CAP_HIGH','ROUND_OFFSET',
    'CURVE_A','PEAK_SPEND','CURVE_B',
    'EFF_CTR','EFF_WDTH','EFF_AMPL',
    'RCPT_BUMP','SECOND_WEEK_PENALTY',
    'CENTS_BUG_F','MILE_CAP_RATE','REC_CAP_RATE',
    'MULT_1D','MULT_5D','MULT_7D','MULT_9D','MULT_14D'
]

SEED_CONSTS = np.array(SEED_CONSTS, dtype=float)

# bounds for new variables
BOUNDS = {
    'CENTS_BUG_F': (0.3, 0.9),
    'MILE_CAP_RATE': (0.05, 0.9),
    'REC_CAP_RATE': (0.05, 0.9),
    'MULT_1D': (0.7, 1.5),
    'MULT_5D': (0.7, 1.5),
    'MULT_7D': (0.7, 1.5),
    'MULT_9D': (0.7, 1.5),
    'MULT_14D': (0.7, 1.5),
}

# load data once
with open('public_cases.json') as f:
    data = json.load(f)
inputs = np.array([
    [d['input']['trip_duration_days'], d['input']['miles_traveled'], d['input']['total_receipts_amount']]
    for d in data
], dtype=float)
expected = np.array([d['expected_output'] for d in data], dtype=float)

n_cases = len(expected)

rng_global = np.random.default_rng(0)
perm = rng_global.permutation(n_cases)
val_size = n_cases // 10
val_idx = perm[:val_size]
train_idx_all = perm[val_size:]


def calc_vec(consts, idx):
    arr = inputs[idx]
    res = []
    for d, m, r in arr:
        res.append(calculate_with_consts(consts, d, m, r))
    return np.array(res, dtype=float)


def calculate_with_consts(c, days, miles, receipts):
    (
        BASE_PD, BONUS_DAY5,
        RATE_0_100, RATE_101_500, RATE_501_800, RATE_801P,
        REC_CAP_LOW, REC_CAP_HIGH,
        ROUND_OFFSET,
        CURVE_A, PEAK_SPEND, CURVE_B,
        EFF_CTR, EFF_WDTH, EFF_AMPL,
        RCPT_BUMP, SECOND_WEEK_PENALTY,
        CENTS_BUG_F, MILE_CAP_RATE, REC_CAP_RATE,
        MULT_1D, MULT_5D, MULT_7D, MULT_9D, MULT_14D
    ) = c

    def _cents(x):
        return round(x + ROUND_OFFSET, 2)

    def _trip_multiplier(d, r, m):
        if d <= 2:
            return MULT_1D
        if d == 5:
            return MULT_5D
        if 7 <= d <= 8 and r > 900:
            return MULT_7D
        if 9 <= d <= 13 and r > 1200:
            return MULT_9D
        if d >= 14 and m / max(d, 1) > 180:
            return MULT_14D
        return 1.0

    total = 0.0
    total += _cents(BASE_PD * days)
    if days == 5:
        total += _cents(BONUS_DAY5)
    total += _cents(RATE_0_100 * min(miles, 100))
    total += _cents(RATE_101_500 * max(min(miles, 500) - 100, 0))
    total += _cents(RATE_501_800 * max(min(miles, 800) - 500, 0))
    total += _cents(RATE_801P * max(miles - 800, 0))
    spend_adj = CURVE_A * (receipts - PEAK_SPEND) ** 2 + receipts
    spend_adj = max(0.0, min(spend_adj, REC_CAP_HIGH))
    total += _cents(spend_adj)
    if days > 0:
        eff = EFF_AMPL * np.exp(-((miles / days - EFF_CTR) / EFF_WDTH) ** 2)
        total += _cents(eff)
    if receipts > REC_CAP_LOW:
        total += _cents(RCPT_BUMP)
    if days > 7:
        total -= _cents(SECOND_WEEK_PENALTY * (days - 7))
    total += _cents(MILE_CAP_RATE * max(miles - 800, 0))
    total += _cents(REC_CAP_RATE * max(receipts - 1800, 0))
    if receipts % 1 in {0.49, 0.99}:
        total *= CENTS_BUG_F
    total *= _trip_multiplier(days, receipts, miles)
    return _cents(total)


def score(consts, mask):
    preds = calc_vec(consts, mask)
    diff = np.abs(preds - expected[mask])
    avg_err = diff.mean()
    exact = np.sum(diff < 0.01)
    return avg_err * 100 + 0.1 * (len(diff) - exact)


def train_score(consts, folds):
    return np.mean([score(consts, fi) for fi in folds])


def val_score(consts):
    return score(consts, val_idx)


ITERATIONS = 30000
RESTARTS = 10
T0 = 15000.0
COOL = 0.97

best_const = SEED_CONSTS.copy()
best_train = float('inf')
best_val = float('inf')
start_time = time.time()

for r in range(RESTARTS):
    rng = np.random.default_rng(r)
    folds = [rng.choice(train_idx_all, int(0.8 * len(train_idx_all)), replace=False) for _ in range(5)]
    current = SEED_CONSTS.copy()
    cur_train = train_score(current, folds)
    cur_val = val_score(current)
    best_local = current.copy()
    best_local_train = cur_train
    best_local_val = cur_val
    T = T0
    for i in range(ITERATIONS):
        idx = rng.choice(len(SEED_CONSTS), 3, replace=False)
        prop = current.copy()
        prop[idx] = np.round(prop[idx] * (1 + rng.uniform(-0.15, 0.15, size=3)), 4)
        # bounds for new vars
        for j in idx:
            name = CONST_NAMES[j]
            if name in BOUNDS:
                lo, hi = BOUNDS[name]
                prop[j] = float(np.clip(prop[j], lo, hi))
        prop_train = train_score(prop, folds)
        prop_val = val_score(prop)
        if prop_train < cur_train or rng.random() < np.exp((cur_train - prop_train) / T):
            current, cur_train, cur_val = prop, prop_train, prop_val
            if cur_train < best_local_train:
                best_local_train, best_local_val, best_local = cur_train, prop_val, prop.copy()
        T *= COOL
        if i % 500 == 0:
            print(f"restart {r} iter {i}  train {cur_train:.2f}  val {cur_val:.2f}  best {best_local_train:.2f}")
        if cur_train < 6500 and cur_val <= 1.05 * cur_train:
            break
    # micro tweak
    def micro_tweak(c):
        best_c = c.copy()
        best_score = train_score(best_c, folds)
        best_val_s = val_score(best_c)
        improved = True
        while improved:
            improved = False
            for j in range(len(best_c)):
                for delta in (-0.01, 0.01):
                    cand = best_c.copy()
                    cand[j] = np.round(cand[j] + delta, 4)
                    cand_train = train_score(cand, folds)
                    cand_val = val_score(cand)
                    if cand_train < best_score and cand_val <= 1.05 * cand_train:
                        best_c = cand
                        best_score = cand_train
                        best_val_s = cand_val
                        improved = True
                        break
        return best_c

    current = micro_tweak(current)
    cur_train = train_score(current, folds)
    cur_val = val_score(current)
    if cur_train < best_train and cur_val <= 1.05 * cur_train:
        best_const, best_train, best_val = current, cur_train, cur_val
    if best_train < 6500 and best_val <= 1.05 * best_train:
        break

elapsed = time.time() - start_time

if best_train < 6500 and best_val <= 1.05 * best_train:
    with open('calculate.py') as f:
        lines = f.readlines()
    with open('calculate.py', 'w') as f:
        for line in lines:
            if line.startswith('BASE_PD'):
                for name, value in zip(CONST_NAMES, best_const):
                    f.write(f"{name} = {value:.6f}\n")
                continue
            f.write(line)
    subprocess.run(['./generate_results.sh'], check=False)
    exact = np.sum(np.abs(calc_vec(best_const, slice(None)) - expected) < 0.01)
    with open('README.md') as f:
        text = f.read()
    prefix = '**Score:**'
    start = text.find(prefix)
    if start != -1:
        end = text.find('\n', start)
        text = text[:start] + f'**Score:** {best_train:.2f} (public, exact {exact}/1000)' + text[end:]
    with open('README.md', 'w') as f:
        f.write(text)
    with open('private_results.txt', 'r') as f:
        pass
    print(f"Final Score: {best_train:.2f}  Val: {best_val:.2f}  Runtime: {elapsed:.2f}s")
else:
    print(f"Need more tuning – best so far {best_train:.2f}")

    sys.exit(1)

