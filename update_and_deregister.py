import argparse
import requests
from registry_client import RegistryClient

# P4: command-line argument
parser = argparse.ArgumentParser()
parser.add_argument("service_id", type=int)
args = parser.parse_args()
sid = args.service_id

client = RegistryClient()
try:
    before = client.get_service(sid)
    print(f"Before: {before['name']} status = {before['status']}")

    after = client.patch_service(sid, {"status": "maintenance"})
    print(f"After PATCH: {after['name']} status = {after['status']}")

    confirm = client.get_service(sid)
    print(f"Confirmed by GET: status = {confirm['status']}")

    client.delete_service(sid)
    print(f"Deregistered {confirm['name']} (id {sid})")
except requests.exceptions.ConnectionError:
    print("Cannot reach the registry. Is mock_registry_server.py running on port 8080?")
except requests.exceptions.HTTPError as exc:
    if exc.response.status_code == 404:
        print(f"Service with id {sid} not found, nothing to do.")
    else:
        print(f"Registry returned an error: {exc}")