import json
import re
from pathlib import Path
from collections import Counter
from typing import List, Tuple

def extract_final_action(llm_response: str) -> str:
    """Extracts the final action from the last triple-backtick block."""
    matches = re.findall(r"```(.*?)```", llm_response, re.DOTALL)
    return matches[-1].strip() if matches else ""

def parse_action(action_str: str) -> Tuple[str, List[str]]:
    """Parses action like `fill("123", "nike shoes")` into ('fill', ['123', 'nike shoes'])"""
    match = re.match(r'(\w+)\((.*)\)', action_str)
    if not match:
        return "", []
    action_type = match.group(1)
    args = [arg.strip().strip('"') for arg in re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', match.group(2))]
    return action_type, args

def compute_f1(pred: str, gold: str) -> float:
    """Computes F1 score between predicted and ground truth strings (token-level)."""
    pred_tokens = pred.lower().split()
    gold_tokens = gold.lower().split()
    common = Counter(pred_tokens) & Counter(gold_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = num_same / len(pred_tokens)
    recall = num_same / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)

def evaluate_traces(data: dict):
    total_steps = 0
    correct_actions = 0
    f1_scores = []
    successful_traces = 0
    total_traces = len(data)

    for trace_id, steps in data.items():
        trace_success = True

        for step in steps:
            total_steps += 1
            gt_action_str = step["ground_truth_action"]
            pred_action_str = extract_final_action(step["llm_response"])

            gt_type, gt_args = parse_action(gt_action_str)
            pred_type, pred_args = parse_action(pred_action_str)
            # --- Metric 1: Action Accuracy
            if gt_type == pred_type:
                if gt_type in ("stop", "search"):
                    is_correct = True  # type match only
                else:
                    is_correct = gt_args == pred_args  # all args must match
            else:
                print("-----")
                print(trace_id)
                print("------")
                print(step["llm_response"])
                print("GT----------------")
                print((gt_type, gt_args))
                print("Pre----------------")
                print((pred_type, pred_args))
                is_correct = False

            if is_correct:
                correct_actions += 1
            else:
                trace_success = False

            # --- Metric 2: Text Similarity (F1)
            if gt_type == pred_type and gt_type in ("fill", "stop"):
                gt_text = gt_args[-1] if gt_args else ""
                pred_text = pred_args[-1] if pred_args else ""
                f1 = compute_f1(pred_text, gt_text)
                f1_scores.append(f1)

        # --- Metric 3: Turn Success Rate
        if trace_success:
            successful_traces += 1

    metrics = {
        "Action Accuracy": correct_actions / total_steps if total_steps else 0,
        "Average F1 (fill + stop)": sum(f1_scores) / len(f1_scores) if f1_scores else 0,
        "Turn Success Rate": successful_traces / total_traces if total_traces else 0
    }
    return metrics



def main():
    json_path = Path("/Users/xianrenz/Project/off_line_experiment/all_results_claude.json")
    
    with open(json_path, "r", encoding="utf-8") as f:
        trace_data = json.load(f)

    metrics = evaluate_traces(trace_data)

    print("=== Evaluation Results ===")
    for metric, value in metrics.items():
        print(f"{metric}: {value:.4f}")

if __name__ == "__main__":
    main()
