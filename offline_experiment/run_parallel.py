import subprocess
from multiprocessing import Pool

NUM_PARTS = 8
PYTHON_BIN = "/Users/xianrenz/miniconda3/envs/agent_exp/bin/python"

def run_part(part):
    subprocess.run([PYTHON_BIN,
        "generate_ans.py",
        "--part", str(part),
        "--input", "all_trace_prompts.json",
        "--output_dir", "."
    ])

if __name__ == "__main__":
    with Pool(processes=NUM_PARTS) as pool:
        pool.map(run_part, range(1, NUM_PARTS + 1))
