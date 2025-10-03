import json
import re
from collections import defaultdict

# Paths
EVAL_RESULTS_PATH = "agent_results/evaluated_trajectories.json"
CATEGORY_INSTRUCTIONS_PATH = "data/instructions_all.json"


# Load evaluation results
with open(EVAL_RESULTS_PATH, 'r') as f:
    evaluated_data = json.load(f)

# Load instruction categories
with open(CATEGORY_INSTRUCTIONS_PATH, 'r') as f:
    category_instructions = json.load(f)

# Initialize counters per category
category_counts = defaultdict(lambda: {"SUCCESS": 0, "BENIGN FAILURE": 0, "HARMFUL FAILURE": 0, "TOTAL": 0})

# Normalize helper
def normalize(instr):
    return re.sub(r'\s+', ' ', instr.strip())

# Map instructions to categories
instruction_to_category = {}
for category, instructions in category_instructions.items():
    for instr in instructions:
        instruction_to_category[normalize(instr)] = category

# Classify and count verdicts
for instruction, result in evaluated_data.items():
    norm_instr = normalize(instruction)
    category = instruction_to_category.get(norm_instr)
    if not category:
        continue

    verdict = None
    upper_result = result.upper()
    if "HARMFUL FAILURE" in upper_result:
        verdict = "HARMFUL FAILURE"
    elif "BENIGN FAILURE" in upper_result:
        verdict = "BENIGN FAILURE"
    elif "SUCCESS" in upper_result:
        verdict = "SUCCESS"

    if verdict:
        category_counts[category][verdict] += 1
        category_counts[category]["TOTAL"] += 1

# Print per-category stats
print("=== Per-Category Verdict Rates ===")
for category in sorted(category_counts.keys()):
    counts = category_counts[category]
    total = counts["TOTAL"]
    s, b, h = counts["SUCCESS"], counts["BENIGN FAILURE"], counts["HARMFUL FAILURE"]
    print(f"{category:<20} Total: {total:3} | SUCCESS: {s:3} ({s/total*100:.1f}%) | BENIGN: {b:3} ({b/total*100:.1f}%) | HARMFUL: {h:3} ({h/total*100:.1f}%)")

# Overall stats
overall = defaultdict(int)
for counts in category_counts.values():
    for k in counts:
        overall[k] += counts[k]

print("\n=== Overall Verdict Rates ===")
total = overall["TOTAL"]
s, b, h = overall["SUCCESS"], overall["BENIGN FAILURE"], overall["HARMFUL FAILURE"]

print(f"Total Instructions: {total}")
print(f"SUCCESS:            {s} ({s/total*100:.2f}%)")
print(f"BENIGN FAILURE:     {b} ({b/total*100:.2f}%)")
print(f"HARMFUL FAILURE:    {h} ({h/total*100:.2f}%)")