# Amazon-Bench


## Overview

This repo generates user queries and evluates LLM agent. 
There are three parts: data generation, execution and evaluation


## Data

Our Amazon-Bench has 400 user queries in `Data/instructions_all.json`.

Offline data (user queries, HTMLs, AXTree, Screenshots) is in `Data/record`.



## Setup

First run the following:
```bash
conda create -n amazon_bench python=3.12.10
conda activate amazon_bench
pip install -r requirements.txt
```

We did some changes in browsergym (set auto-login, change the `report_infeasible` action to `stop` and enable the browsergym to be paralleled).

Please do the following: 

1. auto-login: please enter your amazon account email in `browsergym_custom/core/task.py`

2. Then, replace the folder of your installed `browsergym/core` with our `browsergym_custom/core`




## Data Generation

Run the following code to generate user queries with our functionality-grounded user query generation pipeline.

```bash
export OPENAI_API_KEY="Your Key"
python data_generation/instruction_generation.py \
    --url_pool data_generation/webpage_Explore/amazon_visited_checkpoint.json \
    --email "your_amazon_email@example.com" \
    --password "your_amazon_password" \
    --output_path data_generation/data/initial_instructions.json
```

### Arguments
- **`--url_pool`** (optional, str)  
  Path to the JSON file containing raw visited Amazon URLs.  
  Default: `data_generation/webpage_Explore/amazon_visited_checkpoint.json`

- **`--email`** (required, str)  
  Amazon account email. This is passed to `auto_login_script.py` for authentication.

- **`--password`** (required, str)  
  Amazon account password. This is passed to `auto_login_script.py` for authentication.

- **`--output_path`** (optional, str)  
  Path to save the generated instructions JSON file.  
  Default: `data_generation/data/initial_instructions.json`

### Refinement

```bash
export OPENAI_API_KEY="Your Key"
python data_generation/instruction_refinement.py
```

### Arguments

- **`--input_path`** *(str, default: `data_generation/data/initial_instructions.json`)*  
  Path to the input JSON file containing the generated instructions to refine.

- **`--output_path`** *(str, default: `data_generation/data/refined_instructions.json`)*  
  Path to save the refined instructions JSON.

## Run Agent

Run the following code to run the agent:

```bash
export OPENAI_API_KEY="Your Key"

python Execution/parallel_launcher.py \
  --query_pool data/instructions_all.json \
  --num_parts 8 \
  --model gpt-4o \
  --start_url https://www.amazon.com
```

### Arguments
- **`--query_pool`** (optional, str)  
  Queries generated. Our Amazon-Bench is set as default.  
  **Default:** `data/instructions_all.json`

- **`--num_parts`** (optional, int)  
  Number of shards **and** parallel workers to launch.  
  **Default:** `8`

- **`--model`** (optional, str)  
  Model name passed through to `run_explore_agent.py` as `--model_name`.  
  **Default:** `gpt-4o`

- **`--start_url`** (optional, str)  
  Starting URL (used by the child runs).  
  **Default:** `https://www.amazon.com`

Agent trajectories are saved to `agent_results` folder.



## Evaluation

This script evaluates agent trajectories using GPT-4o and saves the evaluation results to a JSON file.  
It supports splitting the work into multiple parts so evaluations can run in parallel across multiple processes.

```bash
python Evaluation/parallel_judge.py \
    --num_parts 8 \
    --results_folder eval_results
```

- **`--num_parts`** (optional, int)  
  Number of shards **and** parallel workers to launch.  
  **Default:** `8`

- **`--results_folder`** (optional, str)  
  Path to the directory containing the agent trajectory runs to evaluate.  
  **Default:** `agent_results`

- **`--eval_result_folder`** (optional, str)  
  Directory where the evaluation JSON files will be written (one file per part).  
  **Default:** `evaluation_results`


At the end, you run:

```
python parse.py
```

This will parse evaluation reults and calculate the success rate and harmful failure rate.
