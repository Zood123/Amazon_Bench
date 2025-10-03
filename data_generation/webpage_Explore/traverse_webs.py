from playwright.sync_api import sync_playwright
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
import json
import re
import time
from collections import deque
from URL_Cleaning import clean_url
from categorize_url import categorize_url
import argparse

# --- Helper ---
def is_valid_amazon_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ('http', 'https') and 'amazon.com' in parsed.netloc

def classify_link(link):
    parsed = urlparse(link)
    if parsed.netloc != "www.amazon.com":
        return "external"
    if re.search(r'/dp/([A-Z0-9]{10})', parsed.path):
        return "asin"
    return "regular"

# --- Main recursive traversal ---
def traverse(start_url,max_depth,checkpoint_every):
    with open("static_urls.json", "r") as f:
        static_urls_data = json.load(f)
    # Flatten static URL sets
    static_links_set = set()
    for key in ["top_nav_links", "footer_nav_links", "footer_line_links","flyout_nav_links","hmenu_links"]:
        static_links_set.update(static_urls_data.get(key, []))

    with sync_playwright() as p:
        user_data_dir = "./amazon_user_data"
        browser = p.chromium.launch_persistent_context(user_data_dir, headless=False)
        page = browser.new_page()
        page.goto(start_url)
        input("When done logging in, type 'ok' here and press Enter to continue: ")

        # --- Resume from checkpoint if exists ---
        try:
            with open("amazon_traversal_checkpoint.json", "r", encoding="utf-8") as f:
                results = json.load(f)
            with open("amazon_visited_checkpoint.json", "r", encoding="utf-8") as f:
                visited_list = json.load(f)
            visited = set(visited_list)
            print(f"[Resume] Loaded checkpoint: {len(visited)} pages visited.")
        except FileNotFoundError:
            results = {}
            visited = set()
            print("[Start] No checkpoint found. Starting fresh.")


        queue = deque()
        if not visited:
            queue.append((start_url, 0))
        else:
            # Resume from where we left off — add unvisited regular_links back to queue
            for url, data in results.items():
                interested_candidates =data["regular_links"] # + data["asin_links"]
                for link in interested_candidates:
                    if (link not in visited):
                        queue.append((link, data["depth"] + 1))

        
        while queue:
            current_url, depth = queue.popleft()
            #print(depth)
            if depth > max_depth:
                continue

            cleaned_url = clean_url(current_url)
            if cleaned_url in visited:
                continue
            
            visited.add(cleaned_url)

            # Special case: skip visiting sign-out
            if "sign-out" in cleaned_url:
                print(f"[Depth {depth}] Skipping visit to: {cleaned_url} (logout page)")
                results[cleaned_url] = {
                    "title": "Amazon logout (Skipped)",
                    "description": "",
                    "asin_links": [],
                    "regular_links": [],
                    "external_links": [],
                    "depth": depth,
                    }
                continue
            elif "signin" in cleaned_url:
                print(f"[Depth {depth}] Skipping visit to: {cleaned_url} (login page)")
                results[cleaned_url] = {
                    "title": "Amazon Sign In (Skipped)",
                    "description": "",
                    "asin_links": [],
                    "regular_links": [],
                    "external_links": [],
                    "depth": depth,
                    }
                continue
            
            print(f"[Depth {depth}] Visiting: {cleaned_url}")
            try:
                page.goto(current_url, timeout=30000)
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f"⚠️ Failed to load {current_url}: {e}")
                continue

            # Extract title and description
            title = page.title()
            try:
                description = page.query_selector('meta[name="description"]')
                description = description.get_attribute('content') if description else ""
            except:
                description = ""

            # Extract links
            raw_links = page.eval_on_selector_all('a[href]', 'elements => elements.map(e => e.href)')
            asin_links = []
            regular_links = []
            external_links = []
            for link in raw_links:
                link_cleaned = clean_url(urljoin(current_url, link))
                if link_cleaned in static_links_set:
                    continue
                link_type = classify_link(link_cleaned)
                if link_type == "asin":
                    asin_links.append(link_cleaned)
                elif link_type == "regular":
                    regular_links.append(link_cleaned)
                else:
                    external_links.append(link)
            # Record the current page info
            results[cleaned_url] = {
                "title": title,
                "description": description,
                "asin_links": sorted(set(asin_links)),
                "regular_links": sorted(set(regular_links)),
                "external_links": sorted(set(external_links)),
                "depth": depth,
            }

            # Checkpoint save every N pages
            if len(visited) % checkpoint_every == 0:
                with open("amazon_traversal_checkpoint.json", "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                with open("amazon_visited_checkpoint.json", "w", encoding="utf-8") as f:
                    json.dump(sorted(visited), f, indent=2, ensure_ascii=False)
                print(f"[Checkpoint] Saved {len(visited)} pages.")

            # Enqueue new regular_links
            for link in regular_links:
                if link not in visited:
                    queue.append((link, depth + 1))

        browser.close()
        return results, visited

# --- Run ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Traverse Amazon webpages using BFS.")
    parser.add_argument("--start_url", type=str, default="https://www.amazon.com/",
                        help="Starting URL for traversal")
    parser.add_argument("--max_depth", type=int, required=True,
                        help="Maximum traversal depth")
    parser.add_argument("--checkpoint_every", type=int, required=True,
                        help="Save checkpoint every visiting N webpages")
    parser.add_argument("--output_file_traversal", type=str, default="amazon_traversal.json",
                        help="Output traversal graph")
    parser.add_argument("--output_file_visited", type=str, default="amazon_visited_urls.json",
                        help="Output file for all visited URLs")
    args = parser.parse_args()

    results, visited = traverse(args.start_url, args.max_depth, args.checkpoint_every)

    # Save final results
    with open(args.output_file_traversal, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open(args.output_file_visited, "w", encoding="utf-8") as f:
        json.dump(sorted(visited), f, indent=2, ensure_ascii=False)
