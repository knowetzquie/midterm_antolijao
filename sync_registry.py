import time
import yaml
from datetime import datetime
from registry_client import RegistryClient

# P3 
def fetch_all(client, status=None):
    collected, offset, limit = [], 0, 10
    while True:
        page = client.get_services(limit=limit, offset=offset, status=status)
        collected.extend(page["results"])
        offset += limit
        if offset >= page["count"]:
            break
    return collected

# basahon ang P1
try:
    with open("service_catalog.yaml", "r") as f:
        data = yaml.safe_load(f)
except (FileNotFoundError, yaml.YAMLError):
    print("Error: service_catalog.yaml is missing or unreadable.")
    raise SystemExit

client = RegistryClient()

existing = {s["name"]: s["id"] for s in fetch_all(client)}

created = 0
updated = 0
rows = []

for svc in data["services"]:
    payload = {
        "name": svc["name"],
        "version": str(svc["version"]),
        "owner": svc["owner"],
        "environment": svc["environment"],
        "status": svc["status"],
        "health_url": svc["health_url"],
        "dependencies": svc["dependencies"],
    }
    if svc["name"] in existing:
        patch = {k: v for k, v in payload.items() if k != "name"}  
        result = client.patch_service(existing[svc["name"]], patch)
        updated += 1
        rows.append((svc["name"], "updated", result["id"]))
    else:
        result = client.create_service(payload)
        created += 1
        rows.append((svc["name"], "created", result["id"]))

print(f"Synced {len(data['services'])} services: {created} created, {updated} updated")

health = None
for attempt in range(3):
    try:
        health = client.health()
        break
    except Exception:
        time.sleep(1)

with open("registry_sync_report.md", "w") as f:
    f.write("# Registry Sync Report\n\n")
    f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
    f.write("| name | action | registry id |\n|---|---|---|\n")
    for name, action, rid in rows:
        f.write(f"| {name} | {action} | {rid} |\n")
    f.write("\n## Health snapshot\n\n")
    if health:
        f.write(f"- total: {health['total']}\n")
        f.write(f"- by_status: {health['by_status']}\n")
        f.write(f"- degraded_services: {', '.join(health['degraded_services'])}\n")
        f.write(f"- overall_ok: {health['overall_ok']}\n")
    else:
        f.write("Health snapshot unavailable.\n")