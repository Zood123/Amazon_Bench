## Step 1: Generate All Prompts

Run the following script to generate prompts from all traces:

```bash
python generate_prompt.py
```


---

## Step 2: Run

Run the Claude model in parallel to generate responses:

```bash
python run_parallel.py
```

This will generate the following outputs:

```
all_trace_result_claude_part1.json  
all_trace_result_claude_part2.json  
...  
all_trace_result_claude_part8.json
```

The `"prompt"` field in each entry will be cleared (set to an empty string) for cleanliness.

---

## Step 3: Combine Results

Merge all partial results into one single JSON file:

```bash
python combine_results.py
```

This will produce the final output:

```
all_results_claude.json
```



---

## Evaluate Accuracy

You can compute the accuracy by running:

```bash
python eval.py
```


