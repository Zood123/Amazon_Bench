import json
from tqdm import tqdm  # progress bar (optional)
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, unquote
import re

def unwrap_amazon_redirect(url):
    """
    If url is an Amazon redirect:
    - /sspa/click → unwrap 'url=' parameter
    - aax-us-iad.amazon.com/x/c/ → unwrap embedded https:// URL
    Returns unwrapped target URL, or None if not a known redirect.
    """
    parsed = urlparse(url)

    # --- Case 1: aax-us-iad.amazon.com ---
    if parsed.netloc == "aax-us-iad.amazon.com" and "/x/c/" in parsed.path:
        # Try to extract embedded https://www.amazon.com/... URL
        match = re.search(r'/https://([^/]+)(/[^ ]+)', url)
        if match:
            embedded_netloc = match.group(1)
            embedded_path = match.group(2)
            target_url = f"https://{embedded_netloc}{embedded_path}"
            return target_url

    # --- Case 2: www.amazon.com/sspa/click ---
    if parsed.netloc == "www.amazon.com" and parsed.path.startswith("/sspa/click"):
        query_dict = parse_qs(parsed.query)
        encoded_target_url = query_dict.get('url', [None])[0]
        if encoded_target_url:
            decoded_target_url = unquote(encoded_target_url)
            target_url = f"https://www.amazon.com{decoded_target_url}"
            return target_url

    # No known redirect
    return None

def clean_url(url):
    if not url:
        return url

    # Step 1 — unwrap redirect if applicable
    unwrapped_url = unwrap_amazon_redirect(url)
    if unwrapped_url:
        # Recursively clean the target
        return clean_url(unwrapped_url)

    # Step 2 — normal parsing
    parsed = urlparse(url)

    # --- If external URL ---
    if parsed.netloc != "www.amazon.com":
        clean_path = parsed.path.split("ref=")[0]
        cleaned = parsed._replace(path=clean_path, query="", fragment="")
        output_url = urlunparse(cleaned)
        if output_url.endswith("/"):
            output_url = output_url.rstrip("/")
        return output_url

    # --- www.amazon.com cleaning ---

    # Product page
    match = re.search(r'/dp/([A-Z0-9]{10})', parsed.path)
    if match:
        product_id = match.group(1)
        return f"https://www.amazon.com/dp/{product_id}"

    # Category /b/ or subcategory
    if parsed.path.endswith("/b/") or "/b/" in parsed.path or "b?" in parsed.path:
        query_dict = parse_qs(parsed.query)
        node = query_dict.get('node', [None])[0]
        #sub_path = parsed.path.split("/b/")[0]
        if node:
            return f"https://www.amazon.com/b/node={node}"


    # Store/brand page
    if parsed.path.startswith("/stores/") and "/page/" in parsed.path:
        clean_path = parsed.path.split("ref=")[0]
        cleaned = parsed._replace(path=clean_path, query="", fragment="")
        
        output_url = urlunparse(cleaned)
        if output_url.endswith("/"):
            output_url = output_url.rstrip("/")
        return output_url

    # User/account pages
    user_account_prefixes = [
        "/hz/", "/gp/", "/ap/", "/yourstore", "/wishlist", "/order-history",
        "/gp/help", "/hz/contact-us", "/help/customer", "/gp/cart", "/gp/css",
        "/your-books", "/profile", "/redeem", "/giftcard", "/customer-preferences",
        "/prime", "/b2b", "/business", "/subscriptions",
        "/cart/", "/cart"
    ]
    for prefix in user_account_prefixes:
        if parsed.path.startswith(prefix):
            clean_path = parsed.path.split("ref=")[0]
            if "ref=" in clean_path:
                return clean_url(clean_path)
            cleaned = parsed._replace(path=clean_path, query="", fragment="")
            output_url = urlunparse(cleaned)
            if output_url.endswith("/"):
                output_url = output_url.rstrip("/")
            return output_url

    # General cleaning (home, search, browse)
    bad_prefixes = ['ref_', 'pf_rd_', 'pd_rd_', 'ie', 'qid', 'sr', 'sprefix', 'crid', 'adv', 'psc', 'channel','ref','plattr','formatType','pageNumber']
    allowed_keys = ['k','node']  # for search keywords

    query_dict = parse_qs(parsed.query)
    cleaned_query_dict = {}

    for key, value in query_dict.items():
        if key in allowed_keys:
            cleaned_query_dict[key] = value
        #elif not any(key.startswith(prefix) for prefix in bad_prefixes):
        #    cleaned_query_dict[key] = value

    # Strip /ref=
    clean_path = parsed.path.split("ref=")[0]
    if "ref=" in clean_path:
        return clean_url(clean_path)
    cleaned = parsed._replace(path=clean_path, query=urlencode(cleaned_query_dict, doseq=True), fragment="")
    output_url = urlunparse(cleaned)
    if "ref=" in output_url:
        output_url = output_url.split("ref=")[0]
        return clean_url(output_url)
    
    
    if output_url.endswith("/"):
        output_url = output_url.rstrip("/")

    if output_url == "https://www.amazon.com/b":
        print(f"[WARN] Empty /b URL after cleaning: {url}")
        return url

    return output_url








# --- Example usage ---
if __name__ == "__main__":
    url = "https://www.amazon.com/Apple-Watch-Smartwatch-Aluminium-Always/dp/B0DGHYQ1VJ/ref=pd_ci_mcx_mh_mcx_views_0_title?pd_rd_w=j5CC2&content-id=amzn1.sym.bb21fc54-1dd8-448e-92bb-2ddce187f4ac%3Aamzn1.symc.40e6a10e-cbc4-4fa5-81e3-4435ff64d03b&pf_rd_p=bb21fc54-1dd8-448e-92bb-2ddce187f4ac&pf_rd_r=8TTKQKF1JWJ518YKNEJD&pd_rd_wg=7bkfG&pd_rd_r=ef06ddda-07ad-46ef-8631-12065444985b&pd_rd_i=B0DGHYQ1VJ"
    print(clean_url(url=url))