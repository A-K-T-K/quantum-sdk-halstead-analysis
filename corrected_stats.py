"""Circuit-blocked inference for the two-condition quantum SDK corpus.

Both condition rows are retained; permutations/sign flips act jointly within
each circuit. No independent replication is inferred from import stripping.
"""
from collections import Counter
from itertools import permutations, product, combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent
SDK_ORDER = ["Cirq", "PennyLane", "Qiskit", "Q#"]
METRICS = ["effort", "volume", "difficulty"]


def exact_friedman(pivot):
    """Exact null over 24**8 joint SDK-label permutations, via integer DP.

The squared sum of SDK rank totals is monotone in the Friedman statistic.
Track only three totals: the fourth follows from their fixed overall sum.
Ranks are doubled to represent ties with exact integer arithmetic.
"""
    ranks = pd.DataFrame(stats.rankdata(pivot.to_numpy(), axis=1), index=pivot.index)
    grouped = ranks.groupby(level="circuit").sum().to_numpy()
    doubled = np.rint(2 * grouped).astype(np.int64)
    observed = int(np.sum(doubled.sum(axis=0) ** 2))
    distribution = np.ones((1, 1, 1), dtype=np.int64)
    minimum_total = 0
    total_rank_sum = 0
    for row in doubled:
        minimum = int(row.min())
        offsets = row - minimum
        transitions = Counter(tuple(p[:3]) for p in permutations(offsets.tolist()))
        step = int(offsets.max())
        next_shape = tuple(s + step for s in distribution.shape)
        updated = np.zeros(next_shape, dtype=np.int64)
        for (a, b, c), multiplicity in transitions.items():
            target = updated[a:a + distribution.shape[0],
                             b:b + distribution.shape[1], c:c + distribution.shape[2]]
            target += multiplicity * distribution
        distribution = updated
        minimum_total += minimum
        total_rank_sum += int(row.sum())
    a, b, c = np.ogrid[tuple(slice(0, n) for n in distribution.shape)]
    r0, r1, r2 = a + minimum_total, b + minimum_total, c + minimum_total
    r3 = total_rank_sum - r0 - r1 - r2
    squares = r0 * r0 + r1 * r1 + r2 * r2 + r3 * r3
    denominator = 24 ** len(doubled)
    assert int(distribution.sum()) == denominator
    extreme = int(distribution[squares >= observed].sum())
    statistic = float(stats.friedmanchisquare(*[pivot[s] for s in pivot]).statistic)
    return statistic, extreme / denominator, extreme, denominator


def blocked_signed_rank(differences):
    """Exact two-sided sign-flip p, assigning one sign to every circuit.

Primitive differences are rounded to 12 decimal places before ranking to
avoid breaking mathematical ties through floating-point subtraction.
Zeros are excluded (Wilcox convention); effect sizes retain all nonzero rows.
"""
    diff = differences.round(12)
    nonzero = diff != 0
    ranks = pd.Series(0.0, index=diff.index)
    ranks.loc[nonzero] = stats.rankdata(diff.loc[nonzero].abs())
    signed = ranks * np.sign(diff)
    contributions = signed.groupby(level="circuit").sum().to_numpy()
    # Half ranks and their sums become integers after doubling.
    contributions = np.rint(2 * contributions).astype(np.int64)
    signs = np.array(list(product((-1, 1), repeat=len(contributions))), dtype=np.int64)
    observed = abs(int(contributions.sum()))
    null = abs(signs @ contributions)
    p = float(np.mean(null >= observed))
    plus, minus = float(ranks[diff > 0].sum()), float(ranks[diff < 0].sum())
    total = plus + minus
    r = (plus - minus) / total if total else 0.0
    return min(plus, minus), p, r


def analyze(df):
    omnibus, posthoc, imports, condition_omnibus, condition_posthoc = [], [], [], [], []
    for metric in METRICS:
        pivot = df.pivot(index=["circuit", "dataset"], columns="sdk", values=metric)[SDK_ORDER]
        if pivot.isna().any().any() or pivot.shape != (16, 4):
            raise ValueError("Expected a complete eight-circuit, two-condition, four-SDK design")
        q, p, extreme, total = exact_friedman(pivot)
        omnibus.append(dict(Metric=metric.capitalize(), statistic=q, p=p, circuits=8,
                             rows_per_sdk=16, extreme_permutations=extreme, permutations=total))
        pairs = []
        for a, b in combinations(SDK_ORDER, 2):
            w, pv, r = blocked_signed_rank(pivot[a] - pivot[b])
            pairs.append({"Metric": metric, "Comparison": f"{a} vs {b}",
                          "Test": "Circuit-blocked signed-rank", "W": w,
                          "Effect Size (r / d)": round(abs(r), 4), "Signed RBC": r, "Raw p": pv})
        adjusted = stats.false_discovery_control([r["Raw p"] for r in pairs])
        for r, pv in zip(pairs, adjusted):
            r["BH-corrected p"] = float(pv)
            r["Significant (BH α=0.05)"] = bool(pv < 0.05)
        posthoc.extend(pairs)
        imp = df.pivot(index=["circuit", "sdk"], columns="dataset", values=metric)
        x, y = imp["With import"], imp["Without import"]
        w, pv, r = blocked_signed_rank(x - y)
        pct = (x.mean() - y.mean()) / y.mean() * 100
        imports.append({"Metric": metric.capitalize(), "W": w, "p-value": pv,
                        "r (RBC)": round(abs(r), 4), "Mean Δ%": f"{pct:+.2f}%",
                        "Direction": "With Import > Without Import" if pct > 0 else "Without Import > With Import"})
        for condition in ["With import", "Without import"]:
            cp = pivot.xs(condition, level="dataset").copy()
            cp.index = pd.MultiIndex.from_arrays([cp.index], names=["circuit"])
            q, pv, extreme, total = exact_friedman(cp)
            condition_omnibus.append(dict(metric=metric, condition=condition, statistic=q, p=pv,
                                           permutations=total, extreme_permutations=extreme))
            comparisons = []
            for a, b in combinations(SDK_ORDER, 2):
                w, pv, r = blocked_signed_rank(cp[a] - cp[b])
                comparisons.append(dict(metric=metric, condition=condition, comparison=f"{a} vs {b}",
                                        W=w, p=pv, r=r))
            adj = stats.false_discovery_control([r["p"] for r in comparisons])
            for r, pv in zip(comparisons, adj):
                r["p_bh"] = float(pv)
            condition_posthoc.extend(comparisons)
    for records, key in [(omnibus, "p"), (imports, "p-value")]:
        adjusted = stats.false_discovery_control([r[key] for r in records])
        for r, pv in zip(records, adjusted):
            r["BH-corrected p"] = float(pv)
            r["Significant"] = "Yes" if pv < 0.05 else "No"
    return (pd.DataFrame(omnibus), pd.DataFrame(posthoc), pd.DataFrame(imports),
            pd.DataFrame(condition_omnibus), pd.DataFrame(condition_posthoc))


def load_data(path=ROOT / "data" / "halstead_results.csv"):
    df = pd.read_csv(path)
    df["sdk"] = df["sdk"].str.split("_").str[0].replace(
        {"cirq": "Cirq", "pennylane": "PennyLane", "qiskit": "Qiskit", "qsharp": "Q#"})
    df["dataset"] = df["dataset"].replace({"With_import": "With import", "Without_import": "Without import"})
    return df


if __name__ == "__main__":
    outputs = analyze(load_data())
    names = ["friedman_results.csv", "posthoc_effect_sizes.csv", "rq3_import_condition.csv",
             "condition_friedman_results.csv", "condition_posthoc_results.csv"]
    for frame, name in zip(outputs, names):
        frame.to_csv(ROOT / "data" / name, index=False, lineterminator="\n")
        print(name)
        print(frame.to_string(index=False))
