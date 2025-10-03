#!/usr/bin/env python3
"""
Compute per-category “widget diversity” by:
  1. Loading your existing JSON of pages (to get URLs)
  2. Fetching each URL with Playwright (using a signed-in storage state)
  3. Extracting the visible texts of buttons, inputs, selects, and textareas
  4. Embedding each page’s widget-corpus with a SentenceTransformer
  5. Computing average pairwise dissimilarity per category
"""

import os
import json
import numpy as np
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from playwright.sync_api import sync_playwright
from browsergym.core.observation import _pre_extract,extract_merged_axtree,_post_extract  
from categorize_url import categorize_url
import argparse

# ──────────────────────────────────────────────────────────────────────────────
# 1) CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────


# Path to Playwright storage state (signed-in session)
STORAGE_STATE = "amazon_state.json"

# Maximum pages to sample per category
MAX_PAGES_PER_CATEGORY = 10

# Playwright browser timeout (ms)
PLAYWRIGHT_TIMEOUT_MS = 60_000
# --- AXTree-based text extraction -------------------------------------------

AX_INTERACTIVE_ROLES = {
    "button", "link", "radio", "checkbox", "menuitem",
    "option", "tab", "switch", "slider", "spinbutton",
    "combobox", "listbox", "textbox", "searchbox"
}

AX_CONTAINER_ROLES = {
    "radiogroup", "heading"
}

def _iter_ax_nodes(snapshot):
    """
    Yield nodes from:
      1) Playwright nested snapshot dict with 'role','name','children', OR
      2) A flat list[dict] of AX nodes with 'nodeId', 'parentId', 'childIds', etc.
    """
    if isinstance(snapshot, dict) and ("role" in snapshot or "children" in snapshot):
        # Nested tree
        stack = [snapshot]
        while stack:
            node = stack.pop()
            yield node
            for c in node.get("children", []) or []:
                stack.append(c)
        return

    if isinstance(snapshot, list) and snapshot and isinstance(snapshot[0], dict) and "nodeId" in snapshot[0]:
        # Flat list of nodes
        for node in snapshot:
            yield node
        return

    # Sometimes wrapped like {"nodes":[...]}
    if isinstance(snapshot, dict) and "nodes" in snapshot and isinstance(snapshot["nodes"], list):
        for node in snapshot["nodes"]:
            yield node
        return

    # Fallback: nothing
    return


def _get_ax_role(node) -> str:
    # Playwright nested: node.get("role") is a string
    r = node.get("role")
    if isinstance(r, str):
        return r.lower().strip()

    # Chrome DevTools style: node["role"] is {"type":"role","value":"link"}
    if isinstance(r, dict):
        v = r.get("value")
        if isinstance(v, str):
            return v.lower().strip()

    # Sometimes only chromeRole/internalRole appears — ignore numeric internals
    return ""


def _get_ax_name(node) -> str:
    # Playwright nested: node.get("name") is already a string
    n = node.get("name")
    if isinstance(n, str):
        return n.strip()

    # Chrome DevTools style name object
    if isinstance(n, dict):
        v = n.get("value")
        if isinstance(v, str):
            return v.strip()

    return ""

def extract_widget_texts(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    texts: list[str] = []

    # Buttons
    for btn in soup.find_all("button"):
        if is_in_shared_container(btn): continue
        t = btn.get_text(strip=True)
        if t: texts.append(t)

    # Inputs (text/search + button/submit)
    for inp in soup.find_all("input", {"type": ["text", "search", "button", "submit", "radio", "checkbox"]}):
        if is_in_shared_container(inp): continue
        # prefer placeholder/value/aria-label
        grabbed = False
        for attr in ("placeholder", "value", "aria-label"):
            if inp.has_attr(attr) and inp[attr].strip():
                texts.append(inp[attr].strip())
                grabbed = True
                break
        if not grabbed:
            lab = get_associated_label_text(inp, soup)
            if lab: texts.append(lab)

    # Select → option
    for sel in soup.find_all("select"):
        if is_in_shared_container(sel): continue
        for opt in sel.find_all("option"):
            t = opt.get_text(strip=True)
            if t: texts.append(t)

    # Textareas
    for ta in soup.find_all("textarea"):
        if is_in_shared_container(ta): continue
        if ta.has_attr("placeholder") and ta["placeholder"].strip():
            texts.append(ta["placeholder"].strip())

    # NEW: any element with an interactive ARIA role (e.g., swatches use role="radio"/"button")
    for el in soup.find_all(attrs={"role": True}):
        if is_in_shared_container(el): continue
        role = el.get("role", "").strip().lower()
        if role in INTERACTIVE_ROLES:
            t = el.get_text(strip=True)
            if t: texts.append(t)

    return texts
def extract_widget_texts_axtree(ax_snapshot, include_containers: bool = False) -> list[str]:
    """
    Extract accessible names from AX nodes for interactive widgets.
    Set include_containers=True to also include 'group', 'radiogroup', 'heading'.
    """
    targets = set(AX_INTERACTIVE_ROLES)
    if include_containers:
        targets |= AX_CONTAINER_ROLES

    seen = set()
    out = []

    for node in _iter_ax_nodes(ax_snapshot):
        # Skip explicitly ignored nodes when present
        if node.get("ignored") is True:
            continue

        role = _get_ax_role(node)
        if role not in targets:
            continue

        name = _get_ax_name(node)
        # Filter out empty/whitespace and ultra-long noise strings if you want
        if not name:
            continue

        # De-dupe while preserving order
        key = (role, name)
        if key in seen:
            continue
        seen.add(key)
        out.append(name)

    return out

# ──────────────────────────────────────────────────────────────────────────────
# 2) HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────
def is_in_shared_container(el) -> bool:
    """
    Return True if the element is inside a shared container like:
      - id='nav-belt'
      - class='nav-fill'
      - class='nav-right'
    """
    for parent in el.parents:
        if parent is None or not hasattr(parent, "attrs"):
            continue
        if parent.get("id") == "nav-belt":
            return True
        if "class" in parent.attrs:
            classes = parent.get("class", [])
            if "nav-fill" in classes or "nav-right" in classes:
                return True
    return False

def is_in_shared_container(el) -> bool:
    """
    Return True if the element is inside a shared container:
    - id='nav-belt'
    - class='nav-fill' or 'nav-right'
    """
    for parent in el.parents:
        if parent is None or not hasattr(parent, "attrs"):
            continue
        if parent.get("id") == "nav-belt":
            return True
        if "class" in parent.attrs:
            classes = parent.get("class", [])
            if "nav-fill" in classes or "nav-right" in classes:
                return True
    return False

INTERACTIVE_ROLES = {"button", "radio", "checkbox", "tab", "menuitem", "option", "link"}

def get_associated_label_text(inp, soup):
    # label wrapping the input
    lab_wrap = inp.find_parent("label")
    if lab_wrap:
        t = lab_wrap.get_text(strip=True)
        if t: return t
    # label[for=id]
    iid = inp.get("id")
    if iid:
        lab_for = soup.find("label", {"for": iid})
        if lab_for:
            t = lab_for.get_text(strip=True)
            if t: return t
    # aria-labelledby
    al = inp.get("aria-labelledby")
    if al:
        parts = []
        for lid in al.split():
            ref = soup.find(id=lid)
            if ref:
                tt = ref.get_text(strip=True)
                if tt: parts.append(tt)
        if parts:
            return " ".join(parts)
    return None


def average_dissimilarity(docs: list[str], model: SentenceTransformer) -> float:
    """
    Embed each document, compute pairwise cosine-similarity,
    convert to dissimilarity = 1 - cosine, and return average off-diagonal.
    """
    n = len(docs)
    if n < 2:
        return 0.0

    embs = model.encode(docs, normalize_embeddings=True)
    sims = np.inner(embs, embs)
    diss = 1.0 - sims
    np.fill_diagonal(diss, 0.0)
    return diss.sum() / (n * (n - 1))

import random

def main(url_path):
    # Load your existing JSON to get URLs
    with open(url_path, "r", encoding="utf-8") as f:
        urls = json.load(f)
    random.shuffle(urls) 

    MAX_PAGES_PER_CATEGORY = 10
    # Build a mapping: category → list of URLs (limit to first N)
    pages_by_category = {}

    for url in urls:
        cat = categorize_url(url)
        if not cat:
            continue

        if cat not in pages_by_category:
            pages_by_category[cat] = []

        # Enforce per-category cap
        if len(pages_by_category[cat]) < MAX_PAGES_PER_CATEGORY:
            pages_by_category[cat].append(url)


    # Initialize embedding model once
    model = SentenceTransformer("all-MiniLM-L6-v2")

    results: dict[str, dict[str, float | int]] = {}
    widget_texts_by_url: dict[str, str] = {}
    # Start Playwright with signed-in context
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(storage_state=STORAGE_STATE)
        page = context.new_page()
        page.set_default_navigation_timeout(PLAYWRIGHT_TIMEOUT_MS)

        for category, urls in pages_by_category.items():
            
            widget_docs: list[str] = []
            print(f"[+] Processing category '{category}' ({len(urls)} pages)...")

            for i, url in enumerate(urls):
                try:
                    page.goto(url, wait_until="domcontentloaded")
                    accessibility_snapshot = extract_merged_axtree(page)
                    texts = extract_widget_texts_axtree(accessibility_snapshot, include_containers=True)  # set False if you only want interactives
                    #texts = extract_widget_texts(page.content())
                    doc = "\n".join(texts)
                    if doc.strip():
                        widget_docs.append(doc)
                        widget_texts_by_url[url] = doc
                    else:
                        print(f"    ⚠️ No widget text found for {url}")
                except Exception as e:
                    print(f"    ⚠️ Failed to fetch {url}: {e}")

            # Compute average dissimilarity for this category
            avg_dis = average_dissimilarity(widget_docs, model)
            avg_dis = float(avg_dis)  # ensure it's a Python float

            results[category] = {
                "n_pages": len(widget_docs),
                "avg_dissimilarity": avg_dis
            }

        context.close()
        browser.close()

    # 4) PRINT & SAVE RESULTS
    with open("widget_texts.json", "w") as outf:
        json.dump(widget_texts_by_url, outf, indent=2)
        print("Widget texts saved to widget_texts.json")
    with open("diversity_results.json", "w") as outf:
        json.dump(results, outf, indent=2)
        print("Diversity results saved to diversity_results.json")

    print("\nCategory diversity (average widget dissimilarity):")
    for cat, stats in results.items():
        print(f"  {cat:25s}  pages={stats['n_pages']:2d}  avg_dissim={stats['avg_dissimilarity']:.3f}")
    print(results)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Measure diversity of webpage category.")
    parser.add_argument(
        "--url_path",
        type=str,
        default="/Users/xianrenz/Project/Xianren_upload/Shopping_agent_benchmark/data_generation/webpage_Explore/amazon_visited_checkpoint.json",
        help="Path to the visited URLs checkpoint file"
    )
    args = parser.parse_args()

    main(args.url_path)