import json, yaml

try:

    with open("service_catalog.yaml", "r") as f:
        data = yaml.safe_load(f)  # a Python dict

except(FileNotFoundError, yaml.YAMLError):
    print("Error: service_catalog.yaml is missing or unreachable.")
    raise SystemExit
          
with open("service_catalog.json", "w") as f:
    json.dump(data, f, indent=4)
print(f"Converted {len(data['services'])} services to service_catalog.json")