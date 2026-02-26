#!/usr/bin/env python3
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser

class DDGParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.in_snippet = False
        self.current_title = None
        self.current_snippet = None
        self.results = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("class") == "result__a":
            self.in_title = True
            self.current_title = ""
        elif tag == "a" and attrs.get("class") == "result__snippet":
            self.in_snippet = True
            self.current_snippet = ""

    def handle_endtag(self, tag):
        if tag == "a":
            if self.in_snippet and self.current_title and self.current_snippet:
                self.results.append({
                    "title": self.current_title.strip(),
                    "snippet": self.current_snippet.strip()
                })
            self.in_title = False
            self.in_snippet = False

    def handle_data(self, data):
        if self.in_title:
            self.current_title += data
        elif self.in_snippet:
            self.current_snippet += data

def search_(query, max_results=10):
    url = "https://duckduckgo.com/html/?q=" + urllib.parse.quote_plus(query)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req, timeout=10) as r:
        html = r.read().decode("utf-8", errors="ignore")

    parser = DDGParser()
    parser.feed(html)
    return parser.results[:max_results]

def search(query, max_results=10):
    try:
        ret = "("
        for r in search_(query):
            ret += "(TITLE: " + r["title"] + " SNIPPET: " + r["snippet"] + ") "
        ret += ")"
        return ret
    except Exception:
        return ""
