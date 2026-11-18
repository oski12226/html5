#!/usr/bin/env python3
"""Zbiera śmieszne/ciekawe wpisy o Sejmie i zapisuje data.json (tylko biblioteka standardowa)."""
import json, os, re, html, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

UA = {"User-Agent": "sejm-bez-powagi/1.0"}
KEYWORDS = ["wpadka","gafa","śmiesz","żart","awantur","kłótni","spięci","skandal","mem","viral",
            "wybuch","zaskocz","dziwn","absurd","kuriozum","przejęzyczen","pyskówk","bójk","tupet",
            "pomyłk","kompromitac","hit","nagranie","ostra wymiana"]
MAX_ITEMS = 120

def get(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def clean(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()

def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()

def funny(text):
    t = text.lower()
    return any(k in t for k in KEYWORDS)

def google_news():
    out = []
    queries = ["Sejm wpadka", "Sejm awantura", "Sejm zabawne", "Sejm gafa poseł", "Sejm spięcie marszałek"]
    for q in queries:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
            {"q": q + " when:7d", "hl": "pl", "gl": "PL", "ceid": "PL:pl"})
        try:
            root = ET.fromstring(get(url))
        except Exception as e:
            print("google news błąd:", e); continue
        for it in root.iter("item"):
            title = clean(it.findtext("title"))
            src = it.find("source")
            out.append({"title": title, "url": it.findtext("link"),
                        "source": "Wiadomości", "date": iso(parsedate_to_datetime(it.findtext("pubDate"))),
                        "text": src.text if src is not None else ""})
    return out

def mastodon():
    out = []
    for tag in ["sejm", "sejmrp"]:
        try:
            data = json.loads(get(f"https://mastodon.social/api/v1/timelines/tag/{tag}?limit=40"))
        except Exception as e:
            print("mastodon błąd:", e); continue
        for p in data:
            text = clean(p["content"])
            if not funny(text): continue
            out.append({"title": text[:140] + ("…" if len(text) > 140 else ""), "url": p["url"],
                        "source": "Mastodon", "date": p["created_at"], "text": f"@{p['account']['acct']}"})
    return out

def reddit():
    out = []
    url = "https://www.reddit.com/r/Polska/search.rss?q=sejm&restrict_sr=1&sort=new&t=week"
    try:
        root = ET.fromstring(get(url))
    except Exception as e:
        print("reddit błąd:", e); return out
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for e in root.findall("a:entry", ns):
        title = clean(e.findtext("a:title", namespaces=ns))
        if not funny(title): continue
        out.append({"title": title, "url": e.find("a:link", ns).get("href"), "source": "Reddit",
                    "date": e.findtext("a:updated", namespaces=ns), "text": ""})
    return out

def x_api():
    token = os.environ.get("X_BEARER_TOKEN")
    if not token: return []
    q = urllib.parse.quote('(Sejm OR sejmowa) (wpadka OR gafa OR awantura OR śmieszne) lang:pl -is:retweet')
    url = f"https://api.x.com/2/tweets/search/recent?query={q}&max_results=30&tweet.fields=created_at,author_id"
    try:
        data = json.loads(get(url, {"Authorization": f"Bearer {token}"}))
    except Exception as e:
        print("X błąd:", e); return []
    return [{"title": t["text"][:140], "url": f"https://x.com/i/status/{t['id']}", "source": "X",
             "date": t["created_at"], "text": ""} for t in data.get("data", [])]

def manual():
    try:
        return json.load(open("manual.json", encoding="utf-8"))
    except Exception:
        return []

items = google_news() + mastodon() + reddit() + x_api() + manual()
seen, unique = set(), []
for i in items:
    key = re.sub(r"\W+", "", i["title"].lower())[:60]
    if key and key not in seen and i.get("url"):
        seen.add(key); unique.append(i)
unique.sort(key=lambda i: i["date"], reverse=True)
json.dump({"updated": iso(datetime.now(timezone.utc)), "items": unique[:MAX_ITEMS]},
          open("data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("zapisano", min(len(unique), MAX_ITEMS), "wpisów")
