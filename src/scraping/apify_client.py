from apify_client import ApifyClient
import os
from dotenv import load_dotenv

load_dotenv()


def run_actor(actor_id: str, run_input: dict) -> list[dict]:
    token = os.getenv("APIFY_API_TOKEN")
    client = ApifyClient(token)
    run = client.actor(actor_id).call(run_input=run_input)
    dataset_id = run["defaultDatasetId"]
    return list(client.dataset(dataset_id).iterate_items())