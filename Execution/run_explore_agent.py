from agent.agent import MyAgentArgs
import argparse
# browsergym experiments utils
import json          # NEW
from pathlib import Path   # NEW
import os
from browsergym.experiments import EnvArgs, ExpArgs, get_exp_result
import subprocess
import math


TASKS_JSON = Path("data/instructions_all.json")       


def load_goals(json_path: Path):
    """Flatten all task descriptions from the JSON into a single list."""
    with open(json_path) as f:
        tasks = json.load(f)
    return [desc for page in tasks.values() for desc in page]

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def parse_args():
    parser = argparse.ArgumentParser(description="Run experiment with hyperparameters.")
    parser.add_argument(
        "--model_name",
        type=str,
        default="gpt-4o",  
        help="Your model name",
    )
    parser.add_argument(
        "--task_name",
        type=str,
        default="explore",#openended
        help="Name of the Browsergym task to run.",
    )
    parser.add_argument(
        "--start_url",
        type=str,
        default="https://www.amazon.com",
        help="Starting URL (only for the openended task).",
    )
    parser.add_argument(
        "--visual_effects",
        type=str2bool,
        default=False,
        help="Add visual effects when the agents performs actions.",
    )
    parser.add_argument(
        "--use_html",
        type=str2bool,
        default=False,
        help="Use HTML in the agent's observation space.",
    )
    parser.add_argument(
        "--use_axtree",
        type=str2bool,
        default=True,
        help="Use AXTree in the agent's observation space.",
    )
    parser.add_argument(
        "--use_screenshot",
        type=str2bool,
        default=False,
        help="Use screenshot in the agent's observation space.",
    )
    parser.add_argument(
        "--goal",
        type=str,
        default="On Amazon, go to some product detail pages and show some operations that user would do.",
        help="test the goal",
    )
    parser.add_argument(
        "--query_pool",
        type=str,
        default="data/instructions_all.json",
        help="Path to JSON containing all instructions",
    )
    parser.add_argument(
    "--part",
    type=int,
    default=1,
    help="Which quarter of the data to run (1–8)",
    )
    parser.add_argument(
        "--num_parts",
        type=int,
        default=8,
        help="Total number of parts the data is split into",
    )
    return parser.parse_args()


def filtering_finished(instructions, part_num=None):
    """
    Filters out instructions that have already been saved in instruction.json
    under the results folder for the given part.
    """
    if part_num is None:
        raise ValueError("You must specify the part number to locate the results folder.")

    # Build the path to the result folder
    #results_folder = Path(f"./gpt4_1/results_part{part_num}")
    results_folder = Path("/Users/xianrenz/Project/Explore_Agent/gpt4o/all_results")

    # Collect all existing instructions from instruction.json files
    existing_instructions = set()
    for run_dir in results_folder.glob("*/instruction.json"):
        try:
            with run_dir.open() as f:
                data = json.load(f)
                existing_instructions.add(data.get("instruction", "").strip())
        except Exception as e:
            print(f"Warning: failed to read {run_dir}: {e}")

    # Filter instructions
    remaining = [inst for inst in instructions if inst.strip() not in existing_instructions]
    print(f"Part: {part_num}, Filtered {len(instructions) - len(remaining)} completed instructions, {len(remaining)} remain.")
    return remaining

def main():
    print(
        """Explore Begin"""
    )
    
    args = parse_args()
    goals = load_goals(Path(args.query_pool))
    '''
    filtered_goals= filtering_finished(goals,args.part)
    '''
    filtered_goals = goals
    # Split the list into 4 chunks
    total = len(filtered_goals)
    chunk_size = math.ceil(total / args.num_parts)
    start = (args.part - 1) * chunk_size
    end = min(start + chunk_size, total)
    # Your assigned chunk
    my_instructions = filtered_goals[start:end]
    # f"./gpt4o/results_part{args.part}"
    
    for goal in my_instructions:
        print(f"\n=== Running episode for goal: {goal[:80]}… ===")
        subprocess.run(["python", "auto_login_script.py"])
        # Agent config (unchanged)
        agent_args = MyAgentArgs(
            model_name=args.model_name,
            chat_mode=False,
            demo_mode="default" if args.visual_effects else "off",
            use_html=args.use_html,
            use_axtree=args.use_axtree,
            use_screenshot=args.use_screenshot,
        )
        # Environment config
        env_args = EnvArgs(
            task_name=args.task_name,
            max_steps=15,
            headless=True,
        )

        # For non-openended tasks we inject start_url + per-goal text
        if args.task_name != "openended":
            agent_args.chat_mode = False
            env_args.wait_for_user_message = False
            env_args.task_kwargs = {"start_url": args.start_url, "goal": goal}
        else:
            # openended: keep chat_mode & wait_for_user_message behaviour
            agent_args.chat_mode = False
            env_args.wait_for_user_message = False

        # Set up and run
        exp_args = ExpArgs(env_args=env_args, agent_args=agent_args)
        exp_args.prepare(f"agent_results/results_part{args.part}")
        exp_args.run()

        # Print summary
        path = os.path.join(exp_args.exp_dir, "instruction.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"instruction": goal}, f, indent=2)
            
        exp_result = get_exp_result(exp_args.exp_dir)
        exp_record = exp_result.get_exp_record()
        for key, val in exp_record.items():
            print(f"{key}: {val}")


if __name__ == "__main__":
    main()


