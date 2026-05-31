import os
import re
import math
import json
import csv
import sys
from collections import Counter


# ==============================
# CONFIGURATION
# ==============================

ROOT_DIRS = ["With_import", "Without_import"]
EXPECTED_FILE_COUNT = 32
OUTPUT_FILE = "halstead_results.csv"

print("Loading operator_set.json...")
with open("operator_set.json") as f:
    OPERATOR_SET = set(json.load(f)["operators"])
print("Operator set loaded.\n")


# ==============================
# TOKENIZATION
# ==============================
# The tokenizer emits identifiers, numeric literals, string literals,
# selected operators, delimiters, braces, @, and the dot accessor.
# Matching is performed with re.findall using re.VERBOSE formatting. [web:2]

token_pattern = r"""
    [A-Za-z_][A-Za-z0-9_]* |
    \d+\.\d+|\d+ |
    '.*?'|".*?" |
    ==|!=|<=|>=|\+|-|\*|/|= |
    \(|\)|\[|\]|\{|\}|,|;|@|\.
"""


def tokenize(source):
    return re.findall(token_pattern, source, re.VERBOSE)


# ==============================
# CLASSIFICATION
# ==============================
# Classification follows the current implementation:
# 1. Any identifier immediately followed by "(" is classified as an operator.
# 2. The dot accessor "." is tokenized but ignored by the classifier.
# 3. Any token in operator_set.json is classified as an operator,
#    unless it is explicitly skipped earlier in the logic.
# 4. The brace tokens "{" and "}" are tokenized but ignored by the classifier.
# 5. "@" is classified as an operator.
# 6. "[", "]", "(", ")", ",", and ";" are classified as operators.
# 7. Arithmetic/comparison symbols such as +, -, *, /, =, ==, !=, <=, >=
#    are classified as operators.
# 8. Any identifier not immediately followed by "(" is classified as an operand.
# 9. Numeric literals are classified as operands.
# 10. String literals are classified as operands.
# 11. Any token not matched by the preceding rules is classified as an operand.
#
# Note: Some explicit operator checks below are redundant with OPERATOR_SET,
# but they are retained here to preserve the current implementation behavior.


def classify(tokens):
    operators = []
    operands = []

    ARITHMETIC_OPS = {"==", "!=", "<=", ">=", "+", "-", "*", "/", "="}

    for i, token in enumerate(tokens):
        next_tok = tokens[i + 1] if i + 1 < len(tokens) else None

        # Rule 2: dot accessor is tokenized but not counted
        if token == ".":
            continue

        # Rule 4: braces are tokenized but not counted
        elif token in {"{", "}"}:
            continue

        # Rule 3 / Rule 7: operator vocabulary and arithmetic/comparison symbols
        elif token in OPERATOR_SET or token in ARITHMETIC_OPS:
            operators.append(token)

        # Rule 5: @ is an operator
        elif token == "@":
            operators.append(token)

        # Rule 6: square brackets are operators
        elif token in {"[", "]"}:
            operators.append(token)

        # Rule 6: semicolon is an operator
        elif token == ";":
            operators.append(token)

        # Rule 1 and Rule 8: identifier classification depends on immediate "("
        elif re.match(r"[A-Za-z_][A-Za-z0-9_]*$", token):
            if next_tok == "(":
                operators.append(token)  # Rule 1
            else:
                operands.append(token)   # Rule 8

        # Rule 9: numeric literals are operands
        elif re.match(r"\d+\.\d+|\d+$", token):
            operands.append(token)

        # Rule 10: string literals are operands
        elif token.startswith(("'", '"')):
            operands.append(token)

        # Rule 11: fallback classification
        else:
            operands.append(token)

    return operators, operands


# ==============================
# HALSTEAD METRICS
# ==============================
# For each source file:
# n1 = number of distinct operators
# n2 = number of distinct operands
# N1 = total number of operator occurrences
# N2 = total number of operand occurrences
#
# Vocabulary: eta = n1 + n2
# Length:     N   = N1 + N2
# Volume:     V   = N * log2(eta), when eta > 1, else 0
# Difficulty: D   = (n1 / 2) * (N2 / n2), when n2 > 0, else 0
# Effort:     E   = D * V


def halstead(source):
    tokens = tokenize(source)
    operators, operands = classify(tokens)

    N1 = len(operators)
    N2 = len(operands)
    n1 = len(set(operators))
    n2 = len(set(operands))

    eta = n1 + n2
    N = N1 + N2
    V = 0 if eta <= 1 else N * math.log2(eta)
    D = 0 if n2 == 0 else (n1 / 2) * (N2 / n2)
    E = D * V

    return n1, n2, N1, N2, eta, N, V, D, E


# ==============================
# PROCESS FILES
# ==============================

rows = []
total_files = 0
processed_files = 0
failed_files = 0

print("Scanning corpus...\n")

for ROOT_DIR in ROOT_DIRS:
    if not os.path.exists(ROOT_DIR):
        print(f"ERROR: {ROOT_DIR} not found.")
        sys.exit(1)

    for root, dirs, files in os.walk(ROOT_DIR):

        # Exclude common non-source traversal targets
        dirs[:] = [d for d in dirs if d not in {"venv", "__pycache__", ".git"}]

        for file in files:
            if file.endswith(".py") or file.endswith(".qs"):

                total_files += 1
                path = os.path.join(root, file)

                print(f"[DETECTED] {path}")

                dataset = ROOT_DIR
                circuit = os.path.basename(os.path.dirname(path))
                sdk = os.path.splitext(file)[0]

                try:
                    with open(path, "r", encoding="utf-8") as f:
                        source = f.read()

                    n1, n2, N1, N2, eta, N, V, D, E = halstead(source)

                    rows.append([
                        dataset,
                        circuit,
                        sdk,
                        n1, n2, N1, N2,
                        eta, N, V, D, E
                    ])

                    processed_files += 1
                    print(f"[COMPLETED] {path} | Effort={round(E, 2)}")

                except Exception as e:
                    failed_files += 1
                    print(f"[FAILED] {path}")
                    print("Error:", e)
                    print("-" * 60)


# ==============================
# VALIDATION CHECK
# ==============================

dataset_counts = Counter(row[0] for row in rows)

print("\nDataset breakdown:")
for k, v in dataset_counts.items():
    print(f"{k}: {v} files")

if dataset_counts["With_import"] != 32:
    print("ERROR: With_import does not contain 32 files.")
    sys.exit(1)

if dataset_counts["Without_import"] != 32:
    print("ERROR: Without_import does not contain 32 files.")
    sys.exit(1)

if failed_files > 0:
    print("ERROR: Some files failed during processing.")
    sys.exit(1)


# ==============================
# WRITE CSV
# ==============================
# The csv module writes the header row followed by one row per processed file. [web:36]

print("\nWriting CSV...")

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "dataset",
        "circuit",
        "sdk",
        "n1", "n2", "N1", "N2",
        "vocabulary",
        "length",
        "volume",
        "difficulty",
        "effort"
    ])
    writer.writerows(rows)


# ==============================
# SUMMARY
# ==============================

print("\n==============================")
print("PROCESS COMPLETE")
print("==============================")
print(f"Total detected files : {total_files}")
print(f"Successfully processed: {processed_files}")
print(f"Failed files         : {failed_files}")
print(f"Output file          : {OUTPUT_FILE}")
print("==============================")