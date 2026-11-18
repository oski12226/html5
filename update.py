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

USE_AI = bool(os.environ.get("ANTHROPIC_API_KEY"))

def funny(text):
    if USE_AI:
        return True  # szeroki zbiór kandydatów, ocenia je Claude
    t = text.lower()
    return any(k in t for k in KEYWORDS)

def google_news():
    out = []
    queries = ["Sejm wpadka", "Sejm awantura", "Sejm zabawne", "Sejm gafa poseł", "Sejm spięcie marszałek"]
    if USE_AI:
        queries += ["Sejm poseł nagranie", "Sejm mównica", "Sejm obrady", "Sejm absurd", "Sejm przepychanka"]
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


def ai_filter(items):
    """Claude ocenia, które wpisy są śmieszne/ciekawe (1-10) i pisze krótki opis."""
    if not USE_AI:
        return items
    cands = items[:150]
    lst = "\n".join(f"{n}. {i['title']}" for n, i in enumerate(cands))
    prompt = ("Poniżej lista nagłówków i wpisów o polskim Sejmie. Oceń każdy w skali 1-10 pod kątem tego, "
              "czy opisuje śmieszną, absurdalną lub zaskakującą sytuację (a nie zwykły news polityczny). "
              "Zwróć WYŁĄCZNIE JSON: tablicę obiektów {\"n\":numer,\"score\":liczba,\"opis\":\"jedno zdanie po polsku, neutralne, bez obrażania osób\"} "
              "dla wpisów z oceną co najmniej 6.\n\n" + lst)
    body = json.dumps({"model": "claude-haiku-5-5", "max_tokens": 4000,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            txt = json.load(r)["content"][0]["text"]
        rated = json.loads(re.sub(r"^```(?:json)?|```$", "", txt.strip(), flags=re.M).strip())
    except Exception as e:
        print("AI błąd, używam słów kluczowych:", e)
        return [i for i in items if any(k in i["title"].lower() for k in KEYWORDS)]
    out = []
    for r in rated:
        if 0 <= r["n"] < len(cands):
            it = dict(cands[r["n"]]); it["text"] = r.get("opis", ""); out.append(it)
    return out

items = google_news() + mastodon() + reddit() + x_api() + manual()
seen, unique = set(), []
for i in items:
    key = re.sub(r"\W+", "", i["title"].lower())[:60]
    if key and key not in seen and i.get("url"):
        seen.add(key); unique.append(i)
unique.sort(key=lambda i: i["date"], reverse=True)
unique = ai_filter([i for i in unique if i["source"] != "Ręcznie"]) + [i for i in unique if i["source"] == "Ręcznie"]
unique.sort(key=lambda i: i["date"], reverse=True)
json.dump({"updated": iso(datetime.now(timezone.utc)), "items": unique[:MAX_ITEMS]},
          open("data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("zapisano", min(len(unique), MAX_ITEMS), "wpisów")
