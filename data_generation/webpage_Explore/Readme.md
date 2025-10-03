# Webpage Exploration

## Overview
This script explores and collects URLs from Amazon.com (or a specified starting URL) using a BFS traversal strategy.  It supports setting traversal depth, checkpoint frequency, and custom output file names.


## Usage
Run the following command:

```bash
python traverse_webs.py \
    --start_url "https://www.amazon.com/" \
    --max_depth 4 \
    --checkpoint_every 10 \
    --output_file_traversal "amazon_traversal.json" \
    --output_file_visited "amazon_visited_urls.json"
```

### Arguments
- `--start_url` *(str, default="https://www.amazon.com/")* — Starting URL for traversal.
- `--max_depth` *(int, required)* — Maximum traversal depth.
- `--checkpoint_every` *(int, required)* — Save a checkpoint after visiting N webpages.
- `--output_file_traversal` *(str, default="amazon_traversal.json")* — Output traversal graph.
- `--output_file_visited` *(str, default="amazon_visited_urls.json")* — Output file for all visited URLs.

## Output Files
- **amazon_traversal.json** — Contains all collected URLs in traversal graph form.
- **amazon_visited_urls.json** — Contains all visited webpages during the traversal.

## Checkpoint
You can check **amazon_traversal_checkpoint.json**, which is the traversal graph built after exploring Amazon with depth 3.