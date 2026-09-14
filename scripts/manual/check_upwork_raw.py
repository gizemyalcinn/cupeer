from src.scraping.apify_client import run_actor
import json

UPWORK_ACTOR_ID = "XYTgO05GT5qAoSlxy"

items = run_actor(UPWORK_ACTOR_ID, {
    "query": "data scientist",
    "pagesToScrape": 1,
    "perPage": 10,
})

print(json.dumps(items[0], indent=2, ensure_ascii=False))