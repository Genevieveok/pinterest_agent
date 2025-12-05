import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

def fetch_sitemap_posts(site_url, limit=100):
    sitemap_url = urljoin(site_url, '/sitemap.xml')
    try:
        r = requests.get(sitemap_url, timeout=20)
    except Exception:
        return []
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.content, 'xml')
    urls = [loc.text for loc in soup.find_all('loc')]
    posts = [u for u in urls if '/20' in u or '/post' in u or '/posts' in u or '/blog' in u]
    return posts[:limit]

def extract_post_meta(post_url):
    r = requests.get(post_url, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    title_tag = soup.find('meta', property='og:title') or soup.find('title')
    title = ''
    if title_tag:
        title = title_tag.get('content') if getattr(title_tag,'has_attr','') and title_tag.has_attr('content') else title_tag.text.strip()
    desc_tag = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', property='og:description')
    description = desc_tag.get('content') if desc_tag and getattr(desc_tag,'has_attr','') and desc_tag.has_attr('content') else ''
    keywords = []
    if title:
        keywords = [w.strip().lower() for w in title.split() if len(w) > 2][:15]
    og_img = soup.find('meta', property='og:image')
    image = og_img.get('content') if og_img and getattr(og_img,'has_attr','') and og_img.has_attr('content') else None
    return {'title': title, 'description': description, 'keywords': keywords, 'image': image, 'url': post_url, 'fetched_at': int(time.time())}
