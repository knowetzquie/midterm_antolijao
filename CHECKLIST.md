# ELEC001b Midterm — Hand-in Checklist

You receive TWO provided documents: this paper (the exam) and the
**API Reference Card** (fields, endpoints, Patterns P1–P5). The card is
provided material — not notes — keep it beside you during the exam and
return it with your paper.

## What to submit (one ZIP or GitHub repo named `midterm_<yourname>`)

### Scripts you wrote (required)

- [ ] `json_converter.py` (Part A1) → `service_catalog.json`
- [ ] `xml_converter.py` (Part A2) → `service_catalog.xml`
- [ ] `healthy_filter.py` (Part A3) → `healthy_services.json`
- [ ] `registry_client.py` (Part B1)
- [ ] `inventory_report.py` (Part B2)
- [ ] `provision_services.py` (Part B3)
- [ ] `update_and_deregister.py` (Part B4)
- [ ] `error_demo.py` (Part B4b)
- [ ] `sync_registry.py` (Part C1) → `registry_sync_report.md`

### Answers

- [ ] Part C2 short answers → `answers_c2.txt`

### Provided files (do NOT change; include them so the grader can re-run)

- [ ] `mock_registry_server.py`
- [ ] `service_catalog.yaml`

## Before you submit

- [ ] Every script runs without crashing when the mock server is running
      (`python3 mock_registry_server.py --reset` on port 8080)
- [ ] You did NOT edit `mock_registry_server.py`
- [ ] You did NOT copy someone else's code, notes, or use AI tools / the internet
