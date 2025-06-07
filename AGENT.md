Create / update **AGENT.md** – final tuning guide
=================================================

> **Public cases are for iteration only.**  \
> Your answers on **private cases** (no outputs provided) determine the final
> score. **Bottom line:** do **NOT** over-fit the public set—it will hurt your
> private score!

---

## 🎯 Success Criteria

| Metric                | Target                          |
|-----------------------|---------------------------------|
| **Public Score**      | **< 8 000**                     |
| **Validation Score¹** | ≤ 1.05 × Public Score           |
| **Runtime per call**  | < 0 .10 s on (14 d, 1317 mi, $2503) |

¹Validation = fixed 10 % slice of the public data (seed 0).  
Guard + slice prevent over-fit.

---

## 🔄 Agent Loop (anti-over-fit)

1. **Load** public data once → NumPy arrays.  
2. **predict(constants)** – multi-component rule (per-diem, tiered mileage, spend curve, efficiency bonus, receipt bump).  
3. **score(constants, mask=None)** → `(score, avg_err, exact)` where  
   `score = sum(abs_err) + mean(abs_err)`.  
4. **Validation + Fold Guard**  
   * Fixed 10 % validation mask (seed 0).  
   * 5 random 80 : 20 folds; accept candidate only if it wins ≥ 4 folds.  
5. **Simulated Annealing**  
   * 10 restarts × 30 000 iterations  
   * Temperature `T = 15000 × 0.97**iter`  
   * Perturb 3 random constants ± 15 % (rounded 4 dp).  
6. **Early-stop** when `train < 8 000` **and** `val ≤ 1.05 × train`.  
7. **On success**  
   * Overwrite `calculate.py` with tuned constants (stdlib only, deterministic).  
   * `./generate_results.sh` → `private_results.txt`.  
   * Update README badge: `**Score:** <train_score> (public, exact <n>/1000)`.  
   * `git add calculate.py README.md private_results.txt`  
   * `git commit -m "tune: constants achieve score <train_score>"`  
   * `git push`  
   * Print:  
     ```
     Final Score: <train>  Val: <val>  Runtime: <sec>s
     ```
8. **On failure** (`best ≥ 8 000` after all iters)  
   * Leave repo unchanged.  
   * Print `Need more tuning – best so far <score>` and exit with code 1.

---

## 🧪 Evaluation Scripts

*Run these locally to track progress.*

```bash
./eval.sh                # runs on 1 000 public cases

./generate_results.sh    # creates private_results.txt for submission

Anti-Over-fit Checklist
 Validation ≤ 1.05 × Public Score

 Candidate wins ≥ 4 of 5 folds

 Components rounded to cents before summing

 Constants rounded to 4 dp

 Monotonic sanity: more miles never pays less
```
