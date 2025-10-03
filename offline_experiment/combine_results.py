import json
from pathlib import Path

# Directory containing the part files
base_dir = Path(".")
output_file = base_dir / "all_results_claude.json"

# Initialize combined dictionary
combined_data = {}

# Loop through parts 1 to 8
for i in range(1, 9):
    part_file = base_dir / f"all_trace_result_claude_part{i}.json"
    print(f"Loading {part_file}...")
    with part_file.open("r") as f:
        part_data = json.load(f)
        combined_data.update(part_data)

# Write combined result
with output_file.open("w") as f:
    json.dump(combined_data, f, indent=2)

print(f"Combined result saved to {output_file}")
