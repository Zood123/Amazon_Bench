from urllib.parse import urlparse



def categorize_url(url, title=""):
    homepages = [
      "https://www.amazon.com/gp/css/homepage",
      "https://www.amazon.com/a/addresses",
      "https://www.amazon.com/accountlink/home",
      "https://www.amazon.com/adprefs",
      "https://www.amazon.com/aee/kyc/savedId/display",
      "https://www.amazon.com/alexashopping/notification",
      "https://www.amazon.com/amazonsecondchance",
      "https://www.amazon.com/atep/taxexemption",
      "https://www.amazon.com/benefitsbalance",
      "https://www.amazon.com/clouddrive/manage",
      "https://www.amazon.com/comixology/account",
      "https://www.amazon.com/cpe/manageoneclick",
      "https://www.amazon.com/cpe/managepaymentmethods",
      "https://www.amazon.com/cpe/yourpayments/transactions",
      "https://www.amazon.com/cpe/yourpayments/wallet",
      "https://www.amazon.com/cr/teensProgram",
      "https://www.amazon.com/creatorhub",
      "https://www.amazon.com/gc/pv/balance",
      "https://www.amazon.com/gg/links",
      "https://www.amazon.com/gp/browse",
      "https://www.amazon.com/gp/coins/account",
      "https://www.amazon.com/gp/cpc/homepage",
      "https://www.amazon.com/gp/css/texttrace/view.html",
      "https://www.amazon.com/gp/dmusic/player/settings",
      "https://www.amazon.com/gp/gss/manage",
      "https://www.amazon.com/gp/magazines-subscription-manager/manager",
      "https://www.amazon.com/gp/message",
      "https://www.amazon.com/gp/primecentral",
      "https://www.amazon.com/gp/profile",
      "https://www.amazon.com/gp/rental/your-account",
      "https://www.amazon.com/gp/vatRegistration/manage",
      "https://www.amazon.com/gp/video/ontv/settings",
      "https://www.amazon.com/gp/video/subscriptions/manage",
      "https://www.amazon.com/gp/your-account/order-history",
      "https://www.amazon.com/hp/shopwithpoints/account",
      "https://www.amazon.com/hz/audible/settings",
      "https://www.amazon.com/hz/mycd/digital-console/contentlist/receivedGifts",
      "https://www.amazon.com/hz/privacy-central/data-requests/preview.html",
      "https://www.amazon.com/hz/profilepicker/amazonfamily",
      "https://www.amazon.com/key-delivery",
      "https://www.amazon.com/kindle-dbs/ku/ku-central",
      "https://www.amazon.com/norushcredits",
      "https://www.amazon.com/pb/summary",
      "https://www.amazon.com/privacy/data-deletion",
      "https://www.amazon.com/purchase-reminders",
      "https://www.amazon.com/slc/hub",
      "https://www.amazon.com/tradein/ya",
      "https://www.amazon.com/wwgs/customer-contact-preferences/wwgs-contact-preferences",
      "https://www.amazon.com/yourinterests"
    ]
    parsed = urlparse(url)
    path = parsed.path
    netloc = parsed.netloc

    if "Page Not Found" in title or "amzn1" in url:
        return None

    # --- First level check: External ---
    if netloc != "www.amazon.com":
        if "advertising.amazon.com" in netloc:
            return "External - Advertising"
        if "aws.amazon.com" in netloc:
            return "External - AWS"
        if "affiliate-program.amazon.com" in netloc:
            return "External - Affiliate Program"
        if "developer.amazon.com" in netloc:
            return "External - Developer"
        if "logistics.amazon.com" in netloc:
            return "External - Logistics"
        if "sell.amazon.com" in netloc:
            return "External - Sell on Amazon"
        if "supply.amazon.com" in netloc:
            return "External - Supply Chain"
        if "videodirect.amazon.com" in netloc:
            return "External - Video Direct"
        if "aboutamazon.com" in netloc or "sustainability.aboutamazon.com" in netloc:
            return "External - Corporate"
        if any(domain in netloc for domain in [
            "audible.com", "zappos.com", "imdb.com", "goodreads.com",
            "wholefoodsmarket.com", "ring.com", "shopbop.com",
            "woot.com", "6pm.com", "abebooks.com"
        ]):
            return "External - Subsidiaries"

        return "External - Other"
    
    # --- Internal (www.amazon.com) ---
    if "/dp" in path:
        return "Product Page"
    if (
        "/b/" in path or "/b?" in path or "node=" in url or "/gp/browse.html" in path or
        "/s/" in path or "k=" in url
    ):
        return "Product List / Search"
    if any(segment in path for segment in [
        "/css", "/gp/cart", "/hz/", "/ap/", "/yourstore",
        "/wishlist", "/gp/history", "/gp/help", "buyagain",
        "/hz/contact-us", "/help/customer",  "membership", "subscription","credit","/a/"  #"sign",
    ]) or url in homepages:
        return "User / Account"
    if any(segment in path for segment in [
        "video", "music", "kindle", 
        "/videodirect", "/book", "/audible", "live"
    ]):
        return "Media"
    if (
        path.startswith("/ir") or
        path.startswith("/pr/") or
        path.startswith("/sustainability") or
        "/vdp/" in url
    ):
        return "Corporate / Investor Relations"
    if "-reviews" in path:
        return "Reviews"
    if "/gp/offer-listing/" in path:
        return "Offer Listing"
    if "bestseller" in path or "/gp/new-releases" in path:
        return "Best Sellers / New Releases"
    if "deal" in path:
        return "Deal"
    if "store" in path or "shop" in path:
        return "Stores and Shops"
        
    return "Other"