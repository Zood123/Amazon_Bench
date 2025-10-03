import json
from pathlib import Path

# Define directory where your part files are stored
base_dir = Path("eval_results")  # change this to your actual path

combined_data = {}

for i in range(1, 9):
    part_file = base_dir / f"evaluated_trajectories_voyager2_part{i}.json"
    with part_file.open("r", encoding="utf-8") as f:
        part_data = json.load(f)
        combined_data.update(part_data)

# Save the combined result
output_file = base_dir / "evaluated_trajectories_voyager2.json"
with output_file.open("w", encoding="utf-8") as f:
    json.dump(combined_data, f, indent=2, ensure_ascii=False)

print(f"Combined JSON saved to {output_file}")
