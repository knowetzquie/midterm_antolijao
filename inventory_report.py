import argparse
import requests
from registry_client import RegistryClient

def fetch_all(client, status=None):
    collected, offset, limit = [], 0, 10
    while True:
        page = client.get_services(limit=limit, offset=offset, status=status)
        collected.extend(page["results"])
        offset += limit
        if offset >= page["count"]:
            break
    return collected

parser = argparse.ArgumentParser()
parser.add_argument("--status", default=None)  # optional filter
args = parser.parse_args()

client = RegistryClient()
try:
    services = fetch_all(client, status=args.status)
except requests.exceptions.ConnectionError:
    print("Cannot reach the registry. Is mock_registry_server.py running on port 8080?")
    raise SystemExit
except requests.exceptions.HTTPError as exc:
    print(f"Registry returned an error: {exc}. Check the API key.")
    raise SystemExit

print(f"{'ID':<4} | {'NAME':<20} | {'VERSION':<8} | {'STATUS':<12} | ENVIRONMENT")
print("-" * 66)
for s in services:
    print(f"{s['id']:<4} | {s['name']:<20} | {s['version']:<8} | {s['status']:<12} | {s['environment']}")