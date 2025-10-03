import json
from tqdm import tqdm
from Chat_v1 import llm_generate_answer
import argparse
from pathlib import Path
from math import ceil

MODEL_ID = "arn:aws:bedrock:us-east-2:334317969575:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0"
#"arn:aws:bedrock:us-east-2:334317969575:inference-profile/us.deepseek.r1-v1:0"
#"arn:aws:bedrock:us-east-2:334317969575:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0"



def split_keys(keys, part, total_parts):
    chunk_size = ceil(len(keys) / total_parts)
    start = (part - 1) * chunk_size
    end = part * chunk_size
    return keys[start:end]

def add_llm_responses(input_path: str, output_path: str, part: int, total_parts: int = 8):
    with open(input_path, "r") as f:
        all_data = json.load(f)

    keys = sorted(all_data.keys())
    assigned_keys = split_keys(keys, part, total_parts)
    assigned_data = {k: all_data[k] for k in assigned_keys}

    for trace_id, steps in tqdm(assigned_data.items(), desc=f"Processing Part {part}"):
        for step in steps:
            prompt = step["prompt"]

            response = llm_generate_answer(
                model_id=MODEL_ID,
                temperature=0.7,
                max_tokens= 32000,
                prompt=prompt
            )

            step["llm_response"] = response
            step["prompt"] = ""  # Clear out to reduce saved size

    with open(output_path, "w") as f:
        json.dump(assigned_data, f, indent=2)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", type=int, required=True, help="Part number (1-8)")
    parser.add_argument("--input", type=str, default="all_trace_prompts_with_llm.json")
    parser.add_argument("--output_dir", type=str, default=".")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    output_path = Path(args.output_dir) / f"all_trace_result_claude_part{args.part}.json"
    add_llm_responses(args.input, output_path, args.part)
