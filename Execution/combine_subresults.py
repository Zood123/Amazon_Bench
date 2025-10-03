import shutil
import pathlib

# Source and destination
base_path = pathlib.Path("agent_results")
parts = [base_path / f"results_part{i}" for i in range(1, 9)]
destination = base_path / "all_results"
destination.mkdir(exist_ok=True)

# Start indexing from 1
index = 385

for part in parts:
    for subfolder in sorted(part.iterdir()):
        if subfolder.is_dir():
            new_folder_name = f"trace_{index}"
            new_path = destination / new_folder_name
            shutil.copytree(subfolder, new_path)
            index += 1

print(f"Combined {index - 1} folders into {destination}")