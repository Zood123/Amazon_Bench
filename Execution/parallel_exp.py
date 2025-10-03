# Execution/parallel_launcher.py
import argparse
import multiprocessing
import subprocess

# Globals set in __main__ so run_script stays simple
MODEL_NAME = None
START_URL = None
QUERY_POOL = None
NUM_PARTS = None

def run_script(part: int):
    cmd = [
        "python", "Execution/run_explore_agent.py",
        "--part", str(part),
        "--num_parts", str(NUM_PARTS),           # ← pass num_parts to child
        "--model_name", MODEL_NAME,
        "--start_url", START_URL,
        "--query_pool", QUERY_POOL,              # ensure run_explore_agent.py accepts this
    ]
    subprocess.run(cmd)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Parallel launcher for run_explore_agent.py")
    parser.add_argument(
        "--query_pool",
        type=str,
        default="data/instructions_all.json",
        help="Path to JSON file containing all instructions"
    )
    parser.add_argument(
        "--num_parts",
        type=int,
        default=8,
        help="Total number of parts to run (also number of workers)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o",
        help="Model name to pass to run_explore_agent.py"
    )
    parser.add_argument(
        "--start_url",
        type=str,
        default="https://www.amazon.com",
        help="Starting URL to pass to run_explore_agent.py"
    )
    args = parser.parse_args()

    # Bind globals used by run_script
    MODEL_NAME = args.model
    START_URL = args.start_url
    QUERY_POOL = args.query_pool
    NUM_PARTS = args.num_parts

    # Run parts in parallel
    part_list = list(range(1, args.num_parts + 1))
    with multiprocessing.Pool(processes=args.num_parts) as pool:
        pool.map(run_script, part_list)
