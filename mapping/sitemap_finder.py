import requests
from urllib.parse import urljoin

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; sitemap-discovery/1.0)"}

CANDIDATES = [
    "/robots.txt",
    "/sitemap.xml",
    "/sitemap-index.xml",
    "/sitemap_index.xml",
    "/sitemapindex.xml",
    "/sitemap/sitemap.xml",
    "/sitemap/index.xml",
    "/sitemap/",
    "/sitemap1.xml",
    "/sitemap.xml.gz",
    "/sitemap.php",
    "/sitemap.txt",
    "/sitemap_news.xml",
    "/news-sitemap.xml",
    "/wp-sitemap.xml",
    "/rss",
    "/rss/",
    "/rss.xml",
    "/feed",
    "/feed/",
    "/feed.xml",
    "/atom.xml",
    "/index.xml",
]


def discover(base_url):
    found = []
    for path in CANDIDATES:
        url = urljoin(base_url, path)
        try:
            r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        except requests.RequestException as e:
            continue
        if r.status_code != 404:
            found.append((r.status_code, url))
    return found

results = discover("https://www.lemonde.fr")
print(results)