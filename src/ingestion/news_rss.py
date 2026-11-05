import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict

import feedparser


class NewsAdapter:
    def __init__(self, sources_config: Dict):
        self.sources = sources_config.get("rss_feeds", [])
        self.max_age_hours = sources_config.get("max_age_hours", 36)
        self.max_items = sources_config.get("max_items", 40)
        self.prioritize_watchlist = sources_config.get("prioritize_watchlist", False)
        self.watchlist = sources_config.get("watchlist", [])

    def fetch_latest_news(self) -> List[Dict]:
        articles = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.max_age_hours)

        for feed in self.sources:
            try:
                parsed = feedparser.parse(feed["url"])
                for entry in parsed.entries:
                    published = self._parse_date(entry)
                    if published and published < cutoff:
                        continue

                    articles.append({
                        "title": entry.get("title", ""),
                        "source": feed.get("name", ""),
                        "link": entry.get("link", ""),
                        "published": published.isoformat() if published else "",
                    })
            except Exception as e:
                print(f"Error RSS {feed.get('name', '')}: {e}")

        if self.prioritize_watchlist and self.watchlist:
            def mentions_watchlist(article):
                text = (article["title"] or "").lower()
                return any(sym.lower().split(".")[0] in text for sym in self.watchlist)
            articles.sort(key=mentions_watchlist, reverse=True)

        return articles[: self.max_items]

    @staticmethod
    def _parse_date(entry):
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
        return None
