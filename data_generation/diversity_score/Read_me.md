# Measure Diversity

## Overview
`measure_diversity.sh` runs `diversity_measure_elements.py` to meaure the diversity score for each webpage category


## Usage


You first need to run the login script and manually login your amazon account

```
onetime_signin.py
```

Then, you can run

```
bash measure_diversity.sh
```

## Environment Variable
- `HUGGINGFACEHUB_API_TOKEN`


## Script Arguments
- `--url_path` (str)  
  Path to a JSON file containing a **list of URLs**.  
  **Default:** `amazon_visited_checkpoint.json`

## Output

A json file records the diversity score of each category.

```
diversity_results.json
```