import json, yaml
try:
    with open("service_catalog.yaml", "r") as f:
        data = yaml.safe_load(f)
except (FileNotFoundError, yaml.YAMLError):
    print("Error: service_catalog.yaml is missing or unreadable.")
    raise SystemExit

services = data["services"]
healthy = [s for s in services if s["status"] == "healthy"]
unhealthy = [s for s in services if s["status"] == "unhealthy"]
maintenance = [s for s in services if s["status"] == "maintenance"]

data["services"] = healthy
with open("healthy_services.json", "w") as f:
    json.dump(data, f, indent=4)

print(f"Healthy: {len(healthy)} | Unhealthy: {len(unhealthy)} | Maintenance: {len(maintenance)}")
print("Healthy services: " + ", ".join(sorted(s["name"] for s in healthy)))