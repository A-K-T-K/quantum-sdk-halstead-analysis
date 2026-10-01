"""Run the statistical notebook and minimally refresh manuscript results.

The initial configure step updates notebook analysis cells and output paths.
The run step executes every code cell and stores the fresh notebook outputs.
"""
import contextlib
import io
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["MPLBACKEND"] = "Agg"
import nbformat


def configure():
    path = ROOT / "stats_test.ipynb"
    nb = nbformat.read(path, as_version=4)
    nb.cells[1].source = nb.cells[1].source.replace('pd.read_csv("halstead_results.csv")',
                                                'pd.read_csv("data/halstead_results.csv")')
    nb.cells[1].source = 'from pathlib import Path\nPath("data").mkdir(exist_ok=True)\nPath("figures").mkdir(exist_ok=True)\n' + nb.cells[1].source
    nb.cells[8].source = """# Inferential statistics: eight circuit blocks

Both import conditions are retained within each circuit. Exact omnibus
permutations apply the same SDK-label permutation to both conditions;
signed-rank tests flip all observations of each circuit together.

* Omnibus: exact permutation distribution of the pooled Friedman statistic.
* Post-hoc: exact circuit-blocked signed-rank tests, BH within six contrasts per metric.
* Omnibus and import tests: separate BH corrections across their three metrics.
* Effect sizes: absolute matched-pairs rank-biserial correlations.

Condition-specific exact results are exported as sensitivity analyses.
"""
    nb.cells[9].source = """from corrected_stats import analyze

friedman_df, corrected_posthoc, import_df, condition_friedman_df, condition_posthoc_df = analyze(df)
friedman_df.to_csv("data/friedman_results.csv", index=False)
condition_friedman_df.to_csv("data/condition_friedman_results.csv", index=False)
condition_posthoc_df.to_csv("data/condition_posthoc_results.csv", index=False)

def _magnitude_label(r):
    r = abs(r)
    if r < 0.10: return "Negligible"
    if r < 0.30: return "Small"
    if r < 0.50: return "Medium"
    return "Large"

results_summary = corrected_posthoc[[
    "Metric", "Comparison", "Test", "Effect Size (r / d)",
    "Raw p", "BH-corrected p", "Significant (BH α=0.05)"
]].values.tolist()
display(friedman_df)
display(corrected_posthoc)
display(condition_friedman_df)
"""
    nb.cells[10].source = """# Import-condition analysis

The 32 circuit-SDK pairs are retained, with one joint sign flip per circuit
(eight independent blocks). Exact p-values and BH correction across the
three metrics are reported. Percentage changes use the without-import mean
as the baseline; rank-biserial correlations summarize all nonzero paired rows.
"""
    nb.cells[11].source = """display(import_df)
for sdk in SDK_ORDER:
    d_with = df[(df.sdk == sdk) & (df.dataset == "With import")].difficulty.mean()
    d_without = df[(df.sdk == sdk) & (df.dataset == "Without import")].difficulty.mean()
    print(f"{sdk}: difficulty without imports is {(d_without-d_with)/d_with*100:+.1f}% relative to with imports")
"""
    nb.cells[12].source = """# Post-hoc effect-size summary

Exact circuit-blocked signed-rank p-values, BH correction within each metric,
and absolute rank-biserial effect sizes. Magnitude labels use the existing
descriptive thresholds (0.10, 0.30, and 0.50).
"""
    nb.cells[13].source = """summary_df = corrected_posthoc.copy()
summary_df["Metric"] = pd.Categorical(summary_df["Metric"], categories=METRICS, ordered=True)
summary_df = summary_df.sort_values(["Metric", "Comparison"]).reset_index(drop=True)
display(summary_df.round(6))
"""
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.source = cell.source.replace('fig.savefig(f"box_plot_', 'fig.savefig(f"figures/box_plot_')
            cell.source = cell.source.replace('fig.savefig(f"heatmap_', 'fig.savefig(f"figures/heatmap_')
            cell.source = cell.source.replace('fig.savefig("effort_by_circuit.pdf"', 'fig.savefig("figures/effort_by_circuit.pdf"')
            cell.source = cell.source.replace('fig.savefig("posthoc_heatmap.pdf"', 'fig.savefig("figures/posthoc_heatmap.pdf"')
            cell.source = cell.source.replace('dataframe.to_csv(filename,', 'dataframe.to_csv("data/" + filename,')
            cell.execution_count = None
            cell.outputs = []
            cell.metadata.pop("execution", None)
    nbformat.write(nb, path)


def run():
    os.chdir(ROOT)
    path = ROOT / "stats_test.ipynb"
    nb = nbformat.read(path, as_version=4)
    ns = {"__name__": "__notebook__"}
    import matplotlib.pyplot as plt
    # Execute plotting headlessly; the exported PDFs remain the output artifacts.
    plt.show = lambda *args, **kwargs: plt.close("all")
    count = 0
    log = ROOT / "audit" / "revision_statistics.log"
    log.parent.mkdir(exist_ok=True)
    with log.open("w", encoding="utf-8") as logfile:
        for i, cell in enumerate(nb.cells):
            if cell.cell_type != "code":
                continue
            count += 1
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                exec(compile(cell.source, f"stats_test.ipynb:cell{i}", "exec"), ns)
            value = captured.getvalue()
            logfile.write(value)
            cell.execution_count = count
            cell.metadata.pop("execution", None)
            cell.outputs = [nbformat.v4.new_output("stream", name="stdout", text=value)] if value else []
    nbformat.write(nb, path)
    print(f"Executed {count} statistical cells; fresh outputs saved to {path.name}")


if __name__ == "__main__":
    if "--configure" in sys.argv:
        configure()
    run()
