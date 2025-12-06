import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import logging

logger = logging.getLogger("pinterest-agent")
logger.setLevel(logging.DEBUG)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
}
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")


def fetch_sitemap_posts(url_to_fetch, limit=100):
    """
    Fetches URLs from a sitemap, handles sitemap indexes recursively,
    and filters for likely post URLs.
    """

    # Check if this is the initial call or a recursive call
    if "sitemap.xml" in url_to_fetch or "sitemap_index" in url_to_fetch:
        sitemap_url = url_to_fetch
    else:
        # Assumes initial call passes site_url, not sitemap_url
        sitemap_url = urljoin(url_to_fetch, "/sitemap.xml")

    logger.debug("Attempting to fetch sitemap from: %s", sitemap_url)

    try:
        r = requests.get(sitemap_url, headers=DEFAULT_HEADERS, timeout=20)
        r.raise_for_status()  # Raises HTTPError for 4xx or 5xx status codes
    except requests.exceptions.RequestException as e:
        logger.warning("Sitemap request failed for %s: %s", sitemap_url, e)
        return []

    # Parse the content as XML
    # Assumes 'lxml' is installed, which is necessary for 'xml' parsing
    soup = BeautifulSoup(r.content, "xml")

    # Check for SITEMAP INDEX tags (if present, it links to other sitemaps)
    sitemap_links = [s.loc.text for s in soup.find_all("sitemap")]

    if sitemap_links:
        logger.info(
            "Found sitemap index at %s. Recursively fetching %s sub-sitemaps.",
            sitemap_url,
            len(sitemap_links),
        )
        all_posts = []
        for link in sitemap_links:
            # Recursive call to handle the sub-sitemaps
            all_posts.extend(fetch_sitemap_posts(link, limit=limit - len(all_posts)))
            if len(all_posts) >= limit:
                break
        return all_posts[:limit]

    # Check for URL tags (standard sitemap)
    # The 'loc' tag contains the actual URL
    urls = [loc.text for loc in soup.find_all("loc")]

    if not urls:
        logger.debug("No <loc> tags found in sitemap: %s", sitemap_url)
        return []

    # Filter URLs for likely posts/articles
    posts = [
        u
        for u in urls
        if ("/20" in u or "/post" in u or "/posts" in u or "/blog" in u)
        and not u.lower().endswith(IMAGE_EXTENSIONS)
    ]

    logger.debug(
        "Successfully extracted %s post URLs from %s.", len(posts), sitemap_url
    )
    return posts[:limit]


def extract_post_meta(post_url):
    r = requests.get(post_url, headers=DEFAULT_HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    title_tag = soup.find("meta", property="og:title") or soup.find("title")
    title = ""
    if title_tag:
        title = (
            title_tag.get("content")
            if getattr(title_tag, "has_attr", "") and title_tag.has_attr("content")
            else title_tag.text.strip()
        )
    desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", property="og:description"
    )
    description = (
        desc_tag.get("content")
        if desc_tag
        and getattr(desc_tag, "has_attr", "")
        and desc_tag.has_attr("content")
        else ""
    )
    keywords = []
    if title:
        keywords = [w.strip().lower() for w in title.split() if len(w) > 2][:15]
    og_img = soup.find("meta", property="og:image")
    image = (
        og_img.get("content")
        if og_img and getattr(og_img, "has_attr", "") and og_img.has_attr("content")
        else None
    )
    return {
        "title": title,
        "description": description,
        "keywords": keywords,
        "image": image,
        "url": post_url,
        "fetched_at": int(time.time()),
    }
