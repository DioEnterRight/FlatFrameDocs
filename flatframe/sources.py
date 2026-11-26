"""Free source access for research: the Wikipedia API (discovery) and the pages Wikipedia cites (verification).

Nothing here needs a key. Requests carry an identifying User-Agent (Wikimedia API etiquette), a timeout and a size
limit; failures are recorded, never retried in a loop.
"""
import html
import io
import re
import urllib.parse

import requests

from .common import log

WIKI_MIRRORS = ("wikipedia.org", "wikimedia.org", "wikiwand.com", "wikidata.org", "dbpedia.org", "everybodywiki.com",
                "wikizero", "wiki2.org", "justapedia", "infogalactic", "alchetron.com", "wikiless", "fandom.com")
SKIP_HOSTS = ("books.google.", "google.com/books", "jstor.org", "worldcat.org", "doi.org/10.2307", "youtube.com",
              "facebook.com", "twitter.com", "x.com", "instagram.com", "tiktok.com", "reddit.com", "amazon.", "ebay.",
              "imdb.com", "ancestry.", "newspapers.com", "proquest.com")
TWO_PART_TLDS = ("co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "org.au", "gov.au", "net.au", "edu.au", "co.nz", "govt.nz",
                 "co.in", "gov.in", "co.jp", "ne.jp", "or.jp", "ac.jp", "com.br", "gov.br", "co.za", "gov.za", "com.cn",
                 "gc.ca", "com.sg", "gov.sg", "com.mx")


def original_url(url):
    """web.archive.org/web/2020.../https://example.com/x -> https://example.com/x (for domain independence)."""
    m = re.match(r"https?://web\.archive\.org/web/[^/]+/(.+)$", url)
    return m.group(1) if m else url


def site_of(url):
    """Registrable domain of the ORIGINAL page (archive links count as the site they archive)."""
    host = urllib.parse.urlsplit(original_url(url)).hostname or ""
    host = host.lower().removeprefix("www.")
    parts = host.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in TWO_PART_TLDS:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def is_wiki(url):
    host = (urllib.parse.urlsplit(original_url(url)).hostname or "").lower()
    return any(m in host for m in WIKI_MIRRORS)


def usable_source(url):
    if not url.startswith(("http://", "https://")):
        return False
    low = url.lower()
    return not is_wiki(url) and not any(s in low for s in SKIP_HOSTS)


class Web:
    def __init__(self, cfg):
        r = cfg["research"]
        self.timeout = int(r["request_timeout"])
        self.max_chars = int(r["max_source_chars"])
        self.lang = r.get("wikipedia_lang", "en")
        self.s = requests.Session()
        self.s.headers["User-Agent"] = r["user_agent"]

    # ------------- Wikipedia (discovery only)
    def _wiki(self, **params):
        params.update({"format": "json", "formatversion": "2"})
        r = self.s.get(f"https://{self.lang}.wikipedia.org/w/api.php", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def wiki_search(self, query, n=5):
        data = self._wiki(action="query", list="search", srsearch=query, srlimit=n)
        return [h["title"] for h in data.get("query", {}).get("search", [])]

    def wiki_page(self, title):
        data = self._wiki(action="query", prop="extracts|extlinks|info|pageprops", explaintext=1, titles=title,
                          ellimit="max", inprop="url", redirects=1)
        pages = data.get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing"):
            return None
        p = pages[0]
        if "disambiguation" in (p.get("pageprops") or {}):
            return None
        links = [l.get("url") or l.get("*") for l in p.get("extlinks", [])]
        return {"title": p["title"], "pageid": p["pageid"], "url": p.get("fullurl"), "lastrevid": p.get("lastrevid"),
                "text": p.get("extract", ""), "links": [u for u in links if u]}

    # ------------- cited pages (verification)
    def fetch_text(self, url):
        """-> plain text of an HTML or PDF page, or raises."""
        r = self.s.get(url, timeout=self.timeout, stream=True, allow_redirects=True)
        r.raise_for_status()
        ctype = r.headers.get("Content-Type", "").lower()
        raw = r.raw.read(4_000_000, decode_content=True)
        if raw[:5] == b"%PDF-":
            return pdf_text(raw)[: self.max_chars]
        if "pdf" in ctype and "html" not in ctype:
            raise ValueError("says PDF but is not one")
        if "html" not in ctype and "text" not in ctype:
            raise ValueError(f"not a text page ({ctype or 'unknown type'})")
        enc = r.encoding or "utf-8"
        return html_text(raw.decode(enc, "replace"))[: self.max_chars]


def html_text(doc):
    doc = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header|form|aside)\b.*?</\1>", " ", doc)
    doc = re.sub(r"(?is)<!--.*?-->", " ", doc)
    doc = re.sub(r"(?i)<br\s*/?>|</p>|</h\d>|</li>|</div>", "\n", doc)
    doc = re.sub(r"(?s)<[^>]+>", " ", doc)
    doc = html.unescape(doc)
    lines = [re.sub(r"[ \t ]+", " ", l).strip() for l in doc.splitlines()]
    return "\n".join(l for l in lines if len(l) > 2)


def pdf_text(raw):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(raw))
    return "\n".join((p.extract_text() or "") for p in reader.pages[:40])


def fetch_sources(web, links, limit):
    """Fetch up to `limit` usable cited pages, at most 2 per site. -> [{id, url, site, ok, text|error}]"""
    out, per_site = [], {}
    for url in links:
        if len([s for s in out if s["ok"]]) >= limit or len(out) >= limit * 2:
            break
        if not usable_source(url):
            continue
        site = site_of(url)
        if per_site.get(site, 0) >= 2:
            continue
        per_site[site] = per_site.get(site, 0) + 1
        sid = f"S{len(out) + 1}"
        try:
            text = web.fetch_text(url)
            if len(text) < 400:
                raise ValueError("page has almost no text")
            out.append({"id": sid, "url": url, "site": site, "ok": True, "text": text})
            log(f"source {sid}: {site} ({len(text):,} chars)")
        except Exception as e:  # noqa: BLE001  (a dead link is normal; it is recorded, not fatal)
            out.append({"id": sid, "url": url, "site": site, "ok": False, "error": str(e)[:160]})
    return out
