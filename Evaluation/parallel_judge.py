import subprocess
import multiprocessing
import argparse

def run_part(args):
    part, num_parts, results_dir = args
    subprocess.run([
        "python", "run_judge.py",
        "--part", str(part),
        "--num_parts", str(num_parts),
        "--results_folder", results_dir
    ])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--num_parts", type=int, required=True, help="Total number of parts")
    parser.add_argument("--results_folder", type=str, required=True, help="Path to results folder")
    args = parser.parse_args()

    # Create list of tuples for each process
    part_args = [(part, args.num_parts, args.results_folder) for part in range(1, args.num_parts + 1)]

    with multiprocessing.Pool(processes=args.num_parts) as pool:
        pool.map(run_part, part_args)
