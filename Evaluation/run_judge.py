import openai
from base64 import b64encode
from typing import Dict
from pathlib import Path
from utils import collect_agent_trajectories, collect_agent_trajectories_nova,AgentTrajectory,collect_agent_trajectories_voyager
from Agent_judge import encode_image_to_base64,build_llm_evaluation_prompt,build_llm_evaluation_prompt3way,build_llm_evaluation_prompt3waynova
import json
from math import ceil
import argparse
from openai import OpenAI                           # NEW import
import os


client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])



def evaluate_trajectories_with_gpt4o(
    trajectories: Dict[str, AgentTrajectory],
    num_actions: int = 15,
    num_screenshots: int = 15
):
    for traj in trajectories.values():
        instruction = traj.instruction.strip()
        selected_actions     = traj.actions[-num_actions:]
        selected_screenshots = traj.screenshots[-num_screenshots:]

        action_history  = "\n".join(f"Step {i+1}: {a}"
                                   for i, a in enumerate(selected_actions))
        #result_response = selected_actions[-1] if selected_actions else "(No action)"
        
        if traj.nova:
            prompt = build_llm_evaluation_prompt3waynova(instruction,action_history)
        else:
            prompt = build_llm_evaluation_prompt3way(instruction,
                                             action_history)

        # ----- build multimodal message -----
        user_content = []

        # Add screenshots first
        for shot in selected_screenshots:
            if traj.nova:
                # Use base64 string as-is
                image_url = shot
            else:
                # Encode from Path object
                image_url = f"data:image/png;base64,{encode_image_to_base64(shot)}"

            user_content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })
        
        # Add prompt after screenshots
        user_content.append({"type": "text", "text": prompt})
        messages = [
            {"role": "system",
            "content": "You are a meticulous evaluator assessing the Amazon Web Agent."},
            {"role": "user", "content": user_content}
            ]

        # ----- call GPT-4o -----
        try:
            resp = client.chat.completions.create(       
                model= "gpt-4o",  
                messages=messages,
                temperature=0.7,
            )
            traj.judge_result = resp.choices[0].message.content
            print(f"✅ Evaluated: {instruction[:60]}...")
        except Exception as e:
            traj.judge_result = f"[Error: {e}]"
            print(f"❌ Failed: {instruction[:60]} – {e}")




def split_keys(keys, part, total_parts):
    chunk_size = ceil(len(keys) / total_parts)
    start = (part - 1) * chunk_size
    end = part * chunk_size
    return keys[start:end]

def main(part: int, num_parts: int, results_folder: str,eval_result_folder: str):
    path = results_folder
    if "nova" in path:
        base_path = Path(path)
        trajectories_dict = collect_agent_trajectories_nova(base_path)
    elif "WebVoyager" in path:
        base_path = Path(path)
        trajectories_dict = collect_agent_trajectories_voyager(base_path)
    else:
        base_path = Path(path)
        trajectories_dict = collect_agent_trajectories(base_path)

    keys = sorted(trajectories_dict.keys())
    assigned_keys = split_keys(keys, part, num_parts)
    assigned_trajectories = {k: trajectories_dict[k] for k in assigned_keys}

    evaluate_trajectories_with_gpt4o(
        trajectories=assigned_trajectories,
        num_actions=15,
        num_screenshots=15
    )

    out_dir = Path(eval_result_folder)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"evaluated_trajectories_part{part}.json"
    # Construct a dictionary to save
    evaluated_data = {
    instruction: traj.judge_result
    for instruction, traj in assigned_trajectories.items()
    }
    # Save to JSON
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(evaluated_data, f, ensure_ascii=False, indent=2)

    print(f"🎉 Saved evaluation results to {output_path}")
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", type=int, required=True, help="Which part to evaluate (1-N)")
    parser.add_argument("--num_parts", type=int, required=True, help="Total number of parts")
    parser.add_argument("--results_folder", type=str, required=True, help="Path to results folder")
    parser.add_argument("--eval_result_folder", type=str, default="evaluation_results",
                        help="Directory to save evaluation JSON files")
    args = parser.parse_args()

    main(args.part, args.num_parts, args.results_folder, args.eval_result_folder)