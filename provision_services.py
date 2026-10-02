from registry_client import RegistryClient

# P3 from your API Reference Card
def fetch_all(client, status=None):
    collected, offset, limit = [], 0, 10
    while True:
        page = client.get_services(limit=limit, offset=offset, status=status)
        collected.extend(page["results"])
        offset += limit
        if offset >= page["count"]:
            break
    return collected

# From the B3 table in the paper
NEW_SERVICES = [
    {"name": "rewards-svc", "version": "0.1.0", "owner": "engagement@aeropay.io",
     "environment": "staging", "status": "healthy", "health_url": "/health/rewards",
     "dependencies": ["notification-svc"]},
    {"name": "audit-trail-svc", "version": "1.0.0", "owner": "compliance@aeropay.io",
     "environment": "production", "status": "healthy", "health_url": "/health/audit-trail",
     "dependencies": []},
    {"name": "rate-limiter", "version": "0.9.0", "owner": "platform@aeropay.io",
     "environment": "production", "status": "healthy", "health_url": "/health/rate-limiter",
     "dependencies": ["api-gateway", "auth-svc"]},
]

client = RegistryClient()
existing_names = {s["name"] for s in fetch_all(client)}

for payload in NEW_SERVICES:
    name = payload["name"]
    if name in existing_names:
        print(f"Already registered: {name}")
        continue
    created = client.create_service(payload)
    verified = client.get_service(created["id"])
    print(f"Registered {name} with id {verified['id']}")