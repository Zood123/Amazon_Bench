# Agent Trajectory Evaluation

This script evaluates agent trajectories using GPT-4o and saves the evaluation results to a JSON file.  
It supports splitting the work into multiple parts so evaluations can run in parallel across multiple processes.

---
```bash
python parallel_judge.py \
    --num_parts 8 \
    --results_folder /path/to/results