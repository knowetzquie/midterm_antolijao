import requests
from registry_client import RegistryClient

# wrong api key
try:
    RegistryClient(api_key="wrong-key").get_services()
except requests.exceptions.HTTPError as exc:
    print(f"[401 demo] {exc}")
    print("[401 demo] Probable cause: the X-API-Key header has the wrong key (or is missing).")

# correct key
try:
    RegistryClient().get_service(9999)
except requests.exceptions.HTTPError as exc:
    print(f"[404 demo] {exc}")
    print("[404 demo] Probable cause: no service with id 9999 (never registered or already deleted).")