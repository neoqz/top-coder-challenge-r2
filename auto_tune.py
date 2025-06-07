import json
import numpy as np
import random
import sys

# Load data once
with open('public_cases.json') as f:
    data = json.load(f)
inputs = np.array([
    [d['input']['trip_duration_days'], d['input']['miles_traveled'], d['input']['total_receipts_amount']]
    for d in data
], dtype=float)
expected = np.array([d['expected_output'] for d in data], dtype=float)

n_cases = len(expected)

# Deterministic splits
rng = np.random.default_rng(0)
perm = rng.permutation(n_cases)
val_size = n_cases // 10
val_idx = perm[:val_size]
train_idx_all = perm[val_size:]

fold_size = int(0.8 * len(train_idx_all))
fold_indices = [rng.choice(train_idx_all, fold_size, replace=False) for _ in range(5)]

# evaluation helpers

def predict(constants, idx=None):
    c0, c1, c2, c3 = constants
    if idx is None:
        idx = slice(None)
    arr = inputs[idx]
    days = arr[:,0]
    miles = arr[:,1]
    receipts = arr[:,2]
    mileage = c1 * np.minimum(miles, 600) + c2 * np.maximum(miles - 600, 0)
    return c3 * receipts + c0 * days + mileage

def score(constants, idx):
    preds = predict(constants, idx)
    diff = np.abs(preds - expected[idx])
    avg_err = diff.mean()
    exact = np.sum(diff < 0.01)
    return avg_err * 100 + (len(diff) - exact) * 0.1

def train_score(constants):
    return np.mean([score(constants, fi) for fi in fold_indices])

def val_score(constants):
    return score(constants, val_idx)

# simulated annealing parameters
ITERATIONS = 1500
RESTARTS = 20
T0 = 15000.0
COOL = 0.97

base_constants = np.array([50.0, 0.35, 0.20, 0.80], dtype=float)

best_const = None
best_train = float('inf')
best_val = float('inf')

for r in range(RESTARTS):
    if r == 0:
        current = base_constants.copy()
    else:
        current = base_constants * (1 + rng.uniform(-0.5, 0.5, size=4))
    current = current.astype(float)
    cur_train = train_score(current)
    cur_val = val_score(current)
    if cur_train < best_train:
        best_train, best_val, best_const = cur_train, cur_val, current.copy()
    T = T0
    for n in range(ITERATIONS):
        indices = rng.choice(4, 3, replace=False)
        proposal = current.copy()
        proposal[indices] = np.round(proposal[indices]*(1+rng.uniform(-0.15,0.15,3)),4)
        prop_train = train_score(proposal)
        prop_val = val_score(proposal)
        if prop_train < cur_train or rng.random() < np.exp((cur_train-prop_train)/T):
            current, cur_train, cur_val = proposal, prop_train, prop_val
            if cur_train < best_train:
                best_train, best_val, best_const = cur_train, cur_val, current.copy()
        T *= COOL
        if n % 500 == 0:
            print(f"restart {r} iter {n}: train {cur_train:.2f}  val {cur_val:.2f}")
        if cur_train < 8800 and cur_val <= 1.05 * cur_train:
            print(' '.join(f'{x:.4f}' for x in current))
            print(f'Score: {cur_train:.2f}')
            sys.exit(0)

print(f"Need more tuning – best so far {best_train:.2f}")
