import gymnasium as gym
import browsergym.core  # register the openended task as a gym environment
import subprocess

import json
from query_generation.sample_url import sample_urls_by_category
import pathlib 
from browsergym.utils.obs import flatten_axtree_to_str, flatten_dom_to_str, prune_html
from query_generation.GPT_chat import ask_gpt
import argparse

NUM_INSTRUCTIONS  = 20

def build_axtree_prompt(axtree: str, web_category: str, url: str) -> str:
    """
    Generate a prompt for an LLM to identify and list the main shopper-visible
    functionalities on an Amazon webpage, given its accessibility tree.
    
    Parameters:
        axtree (str): The full AXTree string of the current Amazon page.
        num_instructions (int): Unused in this version; kept for API compatibility.

    Returns:
        str: A formatted prompt ready to send to the LLM.
    """
    prompt = f"""You are an *Instruction Generator* for a webpage on Amazon.

**Input:** The accessibility tree (AXTree) of a {web_category} category page (url:{url}).

**Your task:** Assume you're an Amazon user giving a single instruction to an Amazon AI Agent, where the task would involve or depend on this page. Observe the core functionalities and interactable elements on this page—such as links, buttons, boxes, and forms. Inspired by these elements and main function of the page, generate realistic user instructions. The instructions should reflect plausible user intents that involve or reference the functionalities available on this page.

**Page context (AXTree):**
{axtree}

**Output requirements**
- Write a bullet list of concrete user instructions, based on main function of the page and interactable elements (e.g., link, form, button) on the page.
- Only consider existing main functionalities on web pages. 
- Assume the user starts off the page; write self-contained tasks that don't need extra information. For example, use “Create a new wish list named 'My Shoes'” instead of “Click the 'Create a List' button on the current page.”
- Ensure each instruction includes all necessary context to complete the task. If an action heavily depends on a specific location, mention it explicitly (e.g., “Show all Shoulder Bags in the Coach brand store”).
- The instructions should be realistic and typical in user needs. If specific details (like a name, address, or phone number) are required but missing, please use reasonable content to complete the instruction naturally.
- Ignore general functionalities on the footer or navigation bar. 
- Ignore generic recommendation widgets that aren't relevant to this page's main purpose (e.g., Ignore “Browsing history” or "Recently Viewed" strips on an address-management page since they are not relavant to address edition).
- Return **only** the list—no extra commentary before or after. (follow the format of the following example)


**Illustrative examples:**
- Can you find a pair of Nike running shoes and add the white one to my cart. 
- Set up auto-reload for my Amazon gift card so it adds $50 whenever the balance drops below $20.
- Go to Amazon's Best Sellers and check the Top 100 Free apps.
- Find a CeraVe cream and filter the reviews to show only 1-star ratings.
- Add the “Frequently Bought Together” bundle on a Switch product page to my cart.
- Can you add a new address for me: 233 S Wacker Dr, Apt 3402, Chicago, IL 60606, United States. Phone: (312)5550198.
- Go to the SAFAVIEH brand page and open the 'Area Rugs' dropdown to find a rug for my living room.
- Sort items in my Wish List by price from low to high.



**Now generate a list of realistic instructions based on the core functionalities of this page:**"""
    return prompt






def parse_instructions(llm_output: str, expected_count: int) -> list[str]:
    """
    Extract a clean list of bullet-point items from an LLM response.

    The function expects lines that start with '- ' (dash + space) but is
    tolerant of a few common variants (numbered or • lists). Blank lines and
    leading/trailing spaces are ignored.

    If the model returns fewer than `expected_count` items, the shorter
    list is returned with a warning.  If it returns more, the list is
    truncated to `expected_count`.

    Parameters
    ----------
    llm_output : str
        Raw text produced by the language model.
    expected_count : int
        Number of items you hope to obtain.

    Returns
    -------
    list[str]
        A list of bullet-content strings, stripped of markers/whitespace.
    """
    import re

    # Regex captures common bullet/number prefixes and the following text.
    bullet_pat = re.compile(r"""
        ^\s*                # optional leading spaces
        (?:                 # bullet or number styles:
            -\s+            #   "- " bullet
          | \d+[\).\s]+\s*  #   "1. ", "1) ", "1- " etc.
          | [•*]\s+         #   "• " or "* "
        )
        (.*\S)              # capture the actual content (non-blank)
        $""", re.VERBOSE)

    items = []
    for line in llm_output.splitlines():
        line = line.rstrip()
        if not line:
            continue
        m = bullet_pat.match(line)
        if m:
            items.append(m.group(1).strip())

    if len(items) < expected_count:
        print(f"[warn] expected {expected_count} items, got {len(items)}")

    return items[:expected_count]


'''
k_per_category = {
    "Other": 15,
    "User / Account": 20,
    "Reviews":5,
    "Product List / Search": 15,
    "Deal": 12,
    "Product Page": 13,
    "Best Sellers / New Releases": 5,
    "Offer Listing": 10,
    "Corporate / Investor Relations": 0,
    "Media": 5,
    "Stores and Shops": 5
}'''





def main(url_pool: str,
         output_path: str = "generated_instructions_vt.json",
         seed: int = 42,
         email: str = "",
         password: str = ""):
    k_per_category = {
    "Other": 2,
    "User / Account": 2,
    "Reviews":2,
    "Product List / Search": 2,
    "Deal": 2,
    "Product Page": 2,
    "Best Sellers / New Releases": 2,
    "Offer Listing": 2,
    "Corporate / Investor Relations": 0,
    "Media": 2,
    "Stores and Shops": 2
    }

    """
    - Reads a raw URL pool (amazon_visited_urls.json)
    - Samples per-category URLs according to k_per_category (reproducible via seed)
    - (If present) loads an external pre-sampled mapping and uses it directly
    - Runs the BrowserGym loop to generate instructions per URL
    - Saves checkpoints to `output_path` after each page
    """
    # --- load the raw URL list ---
    path = pathlib.Path(url_pool)
    with path.open("r", encoding="utf-8") as f:
        url_list = json.load(f)  # should be a plain Python list[str]

    # --- sample k URLs per category (using provided mapping) ---
    sampled = {
        cat: sample_urls_by_category(url_list, k=k, seed=seed).get(cat, [])[:k]
        for cat, k in k_per_category.items()
    }
    
    # ------------- main loop ---------------------------------------------------
    results: dict[str, list[dict[str, list[str]]]] = {cat: [] for cat in sampled.keys()}

    for category, urls in sampled.items():
        print(f"\n=== {category.upper()} =============================")

        for url in urls:
            # Ensure fresh signed-in session prior to each page (unchanged)
            subprocess.run([
                "python", "data_generation/query_generation/auto_login_script.py",
                "--email", email,
                "--password", password
            ])

            # 1) Launch env at this URL
            print("•", url)
            env = gym.make(
                "browsergym/openended",
                task_kwargs={"start_url": url},
                headless=True,
                wait_for_user_message=False,
            )
            obs, _ = env.reset()
            print(obs.keys())

            # 2) Extract AXTree text
            axtree = obs.get("axtree_object", "")
            axtree = flatten_axtree_to_str(axtree)
            if not axtree:
                print("⚠️  No AXTree found, skipping:", url)
                env.close()
                continue
            else:
                print("good one!")

            if len(axtree) > 130000:
                axtree = axtree[:130000]

            # 3) Build prompt & ask LLM
            prompt = build_axtree_prompt(axtree, category.upper(), url)
            llm_response = ask_gpt(prompt)

            # 4) Parse numbered output
            instructions = parse_instructions(llm_response, NUM_INSTRUCTIONS)
            results[category].append({url: instructions})

            print(llm_response)

            # 5) Checkpoint: Save after each page (unchanged behavior)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)

            env.close()

    print(f"\n✅  All done — instructions written to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Amazon instructions per category")
    parser.add_argument(
        "--url_pool",
        type=str,
        default="data_generation/webpage_Explore/amazon_visited_checkpoint.json",
        help="Path to JSON file containing raw visited URLs"
    )
    parser.add_argument(
        "--email",
        type=str,
        required=True,
        help="Amazon account email (passed to auto_login_script.py)"
    )
    parser.add_argument(
        "--password",
        type=str,
        required=True,
        help="Amazon account password (passed to auto_login_script.py)"
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default="data_generation/data/initial_instructions.json",
        help="Path to save generated instructions JSON"
    )
    args = parser.parse_args()

    main(
        url_pool=args.url_pool,
        output_path=args.output_path,
        email=args.email,
        password=args.password
    )


