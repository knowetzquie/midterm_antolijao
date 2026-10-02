#!/usr/bin/env python3
"""
mock_registry_server.py
========================
AeroPay Service Registry - Local Mock API (no internet required)

ELEC001b Midterm Exam - provided file.

Run this server locally so your Python scripts can talk to a realistic
REST API without touching the internet.

START THE SERVER
----------------
    python3 mock_registry_server.py

Options:
    --port PORT     Port to listen on              (default: 8080)
    --api-key KEY   API key clients must send      (default: aep-registry-key-2026)
    --reset         Wipe registry.json and reseed the demo data

State is saved to registry.json in the current folder, so the registry
survives a restart. Start with --reset to go back to the demo data.

AUTHENTICATION
--------------
Every call to /api/v1/... (except /ping) must send the header:

    X-API-Key: aep-registry-key-2026

If the header is missing or wrong, the API answers 401.

ENDPOINTS  (base http://localhost:8080/api/v1)
------------------------------------------------
Method  Path               Description
------  ----               -----------
GET     /ping              Liveness check (no api key needed)
GET     /services          List services (paginated)
GET     /services/{id}     Fetch one service
POST    /services          Register a new service
PUT     /services/{id}     Replace all mutable fields
PATCH   /services/{id}     Update some mutable fields
DELETE  /services/{id}     Deregister a service
GET     /health            Aggregate registry health

SERVICE FIELDS
--------------
id            int      read-only, assigned by the registry
name          str      required on POST, cannot change afterwards
version       str      required
owner         str      required (team or email)
environment   str      default "production"  (production | staging | development)
status        str      default "healthy"     (healthy | unhealthy | maintenance)
health_url    str      optional
dependencies  list     optional, names of other services

PAGINATION
----------
GET /services?limit=10&offset=0  -> {"count": N, "next": ..., "previous": ..., "results": [...]}
GET /services?status=unhealthy   -> only services with that status

STATUS CODES
------------
200 OK, 201 Created, 204 No Content, 400 Bad Request,
401 Unauthorized, 404 Not Found
"""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

API_PREFIX = "/api/v1"
STATE_FILE = "registry.json"
DEFAULT_KEY = "aep-registry-key-2026"

DEFAULT_ENVIRONMENT = "production"
DEFAULT_STATUS = "healthy"
VALID_ENVIRONMENTS = ["production", "staging", "development"]
VALID_STATUSES = ["healthy", "unhealthy", "maintenance"]
MUTABLE_FIELDS = [
    "version",
    "owner",
    "environment",
    "status",
    "health_url",
    "dependencies",
]

# ---------------------------------------------------------------------------
# Seed data (used on first run, or with --reset)
# ---------------------------------------------------------------------------
SEED_SERVICES = [
    {"name": "billing-svc",        "version": "1.4.0", "owner": "billing-team@aeropay.io",         "environment": "production",  "status": "healthy",    "health_url": "/health/billing",        "dependencies": []},
    {"name": "invoicing-svc",      "version": "2.1.1", "owner": "billing-team@aeropay.io",         "environment": "production",  "status": "healthy",    "health_url": "/health/invoicing",      "dependencies": ["billing-svc"]},
    {"name": "wallet-svc",         "version": "0.9.2", "owner": "core-ledger@aeropay.io",          "environment": "production",  "status": "healthy",    "health_url": "/health/wallet",         "dependencies": ["billing-svc"]},
    {"name": "card-processor",     "version": "3.2.0", "owner": "payments@aeropay.io",             "environment": "production",  "status": "unhealthy",  "health_url": "/health/card-processor", "dependencies": ["invoicing-svc"]},
    {"name": "atm-network",        "version": "1.0.3", "owner": "channels@aeropay.io",             "environment": "production",  "status": "maintenance", "health_url": "/health/atm",             "dependencies": ["card-processor"]},
    {"name": "loan-originator",    "version": "1.7.0", "owner": "lending@aeropay.io",              "environment": "staging",     "status": "healthy",    "health_url": "/health/loan",            "dependencies": ["billing-svc", "invoicing-svc"]},
    {"name": "savings-engine",     "version": "2.3.1", "owner": "lending@aeropay.io",              "environment": "production",  "status": "healthy",    "health_url": "/health/savings",         "dependencies": ["billing-svc"]},
    {"name": "treasury-svc",       "version": "0.6.4", "owner": "core-ledger@aeropay.io",          "environment": "staging",     "status": "unhealthy",  "health_url": "/health/treasury",         "dependencies": ["billing-svc", "wallet-svc"]},
    {"name": "compliance-audit",   "version": "1.1.0", "owner": "compliance@aeropay.io",           "environment": "production",  "status": "healthy",    "health_url": "/health/compliance-audit", "dependencies": ["atm-network"]},
    {"name": "merchant-portal",    "version": "2.0.2", "owner": "platform@aeropay.io",             "environment": "development", "status": "healthy",    "health_url": "/health/merchant-portal",  "dependencies": ["card-processor", "wallet-svc"]},
    {"name": "user-profile-svc",   "version": "1.3.0", "owner": "iam-team@aeropay.io",             "environment": "production",  "status": "maintenance", "health_url": "/health/user-profile",     "dependencies": ["merchant-portal"]},
    {"name": "session-svc",        "version": "0.8.1", "owner": "iam-team@aeropay.io",             "environment": "production",  "status": "healthy",    "health_url": "/health/sessions",         "dependencies": ["user-profile-svc"]},
]


# ---------------------------------------------------------------------------
# Registry state + persistence
# ---------------------------------------------------------------------------
class RegistryState:
    def __init__(self, services):
        self.services = services
        self._next_id = max((s.get("id", 0) for s in services), default=0) + 1

    def next_id(self):
        i = self._next_id
        self._next_id += 1
        return i

    def find(self, service_id):
        for s in self.services:
            if s.get("id") == service_id:
                return s
        return None

    def find_by_name(self, name):
        for s in self.services:
            if s.get("name") == name:
                return s
        return None


def load_state(reset=False):
    if not reset and os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                payload = json.load(f)
            services = payload.get("services", [])
            state = RegistryState(services)
            state._next_id = int(payload.get("next_id", state._next_id))
            print("[server] Loaded registry from %s (%d services)" % (STATE_FILE, len(services)))
            return state
        except Exception as exc:  # corrupted state -> reseed
            print("[server] Could not read %s (%s). Reseeding demo data." % (STATE_FILE, exc))
    state = RegistryState([dict(s, id=i + 1) for i, s in enumerate(SEED_SERVICES)])
    print("[server] Seeded demo registry with %d services" % len(state.services))
    return state


def save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"services": state.services, "next_id": state._next_id}, f, indent=2)
    except Exception as exc:
        print("[server] WARNING: could not persist state (%s)" % exc)


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------
class RegistryHandler(BaseHTTPRequestHandler):
    server_version = "AeroPayRegistryMock/1.0"

    # -- helpers ----------------------------------------------------------
    def _json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _empty(self, code=204):
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._json(400, {"detail": "Invalid Content-Length header."})
            return None
        if length == 0:
            self._json(400, {"detail": "A JSON object body is required."})
            return None
        try:
            raw = self.rfile.read(length).decode("utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("body must be a JSON object")
            return data
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"detail": "Request body must be valid JSON and an object."})
            return None

    def _authorized(self):
        if self.headers.get("X-API-Key") != self.server.api_key:
            self._json(401, {"detail": "Invalid or missing API key. Send the X-API-Key header."})
            return False
        return True

    def _route(self):
        parsed = urlparse(self.path)
        if not parsed.path.startswith(API_PREFIX):
            self._json(404, {"detail": "Unknown endpoint. Base path is %s" % API_PREFIX})
            return None
        rel = [s for s in parsed.path[len(API_PREFIX):].split("/") if s]
        query = parse_qs(parsed.query)
        return rel, query

    def _int(self, q, name, default, lo, hi):
        values = q.get(name, [str(default)])
        try:
            value = int(values[0])
        except (TypeError, ValueError):
            self._json(400, {"detail": "%s must be an integer." % name})
            return None
        return max(lo, min(hi, value))

    # -- dispatch ---------------------------------------------------------
    def do_GET(self):
        if urlparse(self.path).path == "/ping":
            self._json(200, {"status": "ok", "service": "aero-registry-mock"})
            return
        routed = self._route()
        if routed is None:
            return
        rel, q = routed
        if not self._authorized():
            return
        if rel == ["services"]:
            self._list_services(q)
        elif len(rel) == 2 and rel[0] == "services":
            self._get_service(rel[1])
        elif rel == ["health"]:
            self._health()
        else:
            self._json(404, {"detail": "Unknown endpoint."})

    def do_POST(self):
        routed = self._route()
        if routed is None:
            return
        rel, _ = routed
        if not self._authorized():
            return
        if rel == ["services"]:
            self._create_service()
        else:
            self._json(404, {"detail": "Unknown endpoint."})

    def do_PUT(self):
        routed = self._route()
        if routed is None:
            return
        rel, _ = routed
        if not self._authorized():
            return
        if len(rel) == 2 and rel[0] == "services":
            self._replace_service(rel[1])
        else:
            self._json(404, {"detail": "Unknown endpoint."})

    def do_PATCH(self):
        routed = self._route()
        if routed is None:
            return
        rel, _ = routed
        if not self._authorized():
            return
        if len(rel) == 2 and rel[0] == "services":
            self._patch_service(rel[1])
        else:
            self._json(404, {"detail": "Unknown endpoint."})

    def do_DELETE(self):
        routed = self._route()
        if routed is None:
            return
        rel, _ = routed
        if not self._authorized():
            return
        if len(rel) == 2 and rel[0] == "services":
            self._delete_service(rel[1])
        else:
            self._json(404, {"detail": "Unknown endpoint."})

    # -- endpoint implementations ----------------------------------------
    def _list_services(self, q):
        limit = self._int(q, "limit", 10, 1, 100)
        if limit is None:
            return
        offset = self._int(q, "offset", 0, 0, 10 ** 9)
        if offset is None:
            return
        status = q.get("status", [None])[0]
        services = self.server.state.services
        if status:
            if status not in VALID_STATUSES:
                self._json(400, {"detail": "status must be one of %s" % VALID_STATUSES})
                return
            services = [s for s in services if s.get("status") == status]
        count = len(services)
        results = services[offset:offset + limit]
        host = self.headers.get("Host", "localhost:8080")
        base = "http://%s%s/services" % (host, API_PREFIX)
        next_url = base + "?limit=%d&offset=%d" % (limit, offset + limit) if offset + limit < count else None
        prev_url = base + "?limit=%d&offset=%d" % (limit, max(0, offset - limit)) if offset > 0 else None
        self._json(200, {
            "count": count,
            "next": next_url,
            "previous": prev_url,
            "results": results,
        })

    def _get_service(self, raw_id):
        try:
            service_id = int(raw_id)
        except ValueError:
            self._json(404, {"detail": "Service %r not found." % raw_id})
            return
        svc = self.server.state.find(service_id)
        if svc is None:
            self._json(404, {"detail": "Service with id %d not found." % service_id})
            return
        self._json(200, svc)

    def _validate_payload(self, data, require=()):
        missing = [f for f in require if not data.get(f)]
        if missing:
            self._json(400, {"detail": "Missing required field(s): %s" % ", ".join(missing)})
            return None
        for field in ("environment", "status"):
            value = data.get(field)
            if value is not None:
                allowed = VALID_ENVIRONMENTS if field == "environment" else VALID_STATUSES
                if value not in allowed:
                    self._json(400, {"detail": "%s must be one of %s" % (field, allowed)})
                    return None
        deps = data.get("dependencies")
        if deps is not None and not (isinstance(deps, list) and all(isinstance(d, str) for d in deps)):
            self._json(400, {"detail": "dependencies must be a list of service names (strings)."})
            return None
        for field in ("version", "owner", "name", "health_url"):
            value = data.get(field)
            if value is not None and not isinstance(value, str):
                self._json(400, {"detail": "%s must be a string." % field})
                return None
        return data

    def _create_service(self):
        data = self._read_body()
        if data is None:
            return
        data = self._validate_payload(data, require=("name", "version", "owner"))
        if data is None:
            return
        name = data["name"]
        if self.server.state.find_by_name(name) is not None:
            self._json(400, {"detail": "A service named %r is already registered." % name})
            return
        record = {
            "id": self.server.state.next_id(),
            "name": name,
            "version": data["version"],
            "owner": data["owner"],
            "environment": data.get("environment", DEFAULT_ENVIRONMENT),
            "status": data.get("status", DEFAULT_STATUS),
            "health_url": data.get("health_url"),
            "dependencies": data.get("dependencies", []),
        }
        self.server.state.services.append(record)
        save_state(self.server.state)
        self._json(201, record)

    def _replace_service(self, raw_id):
        try:
            service_id = int(raw_id)
        except ValueError:
            self._json(404, {"detail": "Service %r not found." % raw_id})
            return
        svc = self.server.state.find(service_id)
        if svc is None:
            self._json(404, {"detail": "Service with id %d not found." % service_id})
            return
        data = self._read_body()
        if data is None:
            return
        data = self._validate_payload(data, require=("version", "owner"))
        if data is None:
            return
        svc["version"] = data["version"]
        svc["owner"] = data["owner"]
        svc["environment"] = data.get("environment", DEFAULT_ENVIRONMENT)
        svc["status"] = data.get("status", DEFAULT_STATUS)
        svc["health_url"] = data.get("health_url")
        svc["dependencies"] = data.get("dependencies", [])
        save_state(self.server.state)
        self._json(200, svc)

    def _patch_service(self, raw_id):
        try:
            service_id = int(raw_id)
        except ValueError:
            self._json(404, {"detail": "Service %r not found." % raw_id})
            return
        svc = self.server.state.find(service_id)
        if svc is None:
            self._json(404, {"detail": "Service with id %d not found." % service_id})
            return
        data = self._read_body()
        if data is None:
            return
        unknown = [k for k in data if k not in MUTABLE_FIELDS]
        if unknown:
            self._json(400, {"detail": "PATCH can only update %s (got: %s)" % (MUTABLE_FIELDS, unknown)})
            return
        data = self._validate_payload(data)
        if data is None:
            return
        for key, value in data.items():
            svc[key] = value
        save_state(self.server.state)
        self._json(200, svc)

    def _delete_service(self, raw_id):
        try:
            service_id = int(raw_id)
        except ValueError:
            self._json(404, {"detail": "Service %r not found." % raw_id})
            return
        svc = self.server.state.find(service_id)
        if svc is None:
            self._json(404, {"detail": "Service with id %d not found." % service_id})
            return
        self.server.state.services = [s for s in self.server.state.services if s.get("id") != service_id]
        save_state(self.server.state)
        self._empty(204)

    def _health(self):
        by_status = {s: 0 for s in VALID_STATUSES}
        degraded = []
        for svc in self.server.state.services:
            status = svc.get("status", DEFAULT_STATUS)
            by_status[status] = by_status.get(status, 0) + 1
            if status in ("unhealthy", "maintenance"):
                degraded.append(svc.get("name"))
        total = len(self.server.state.services)
        self._json(200, {
            "service": "aero-registry",
            "total": total,
            "by_status": by_status,
            "degraded_services": sorted(degraded),
            "overall_ok": total > 0 and not degraded,
        })

    def log_message(self, fmt, *args):
        sys.stderr.write("[server] %s\n" % (fmt % args))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="AeroPay Service Registry mock API")
    parser.add_argument("--port", type=int, default=8080, help="port to listen on (default 8080)")
    parser.add_argument("--api-key", default=DEFAULT_KEY, help="API key clients must send (default: %s)" % DEFAULT_KEY)
    parser.add_argument("--reset", action="store_true", help="wipe registry.json and reseed demo data")
    args = parser.parse_args()

    state = load_state(reset=args.reset)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), RegistryHandler)
    server.state = state
    server.api_key = args.api_key

    print()
    print("=" * 64)
    print("  AeroPay Service Registry - Mock API")
    print("  Base URL : http://localhost:%d/api/v1" % args.port)
    print("  API key  : %s" % args.api_key)
    print("  State    : %s  (use --reset to reseed)" % STATE_FILE)
    print("=" * 64)
    print("  Try:  curl http://localhost:%d/ping" % args.port)
    print("        curl -H 'X-API-Key: %s' http://localhost:%d/api/v1/services?limit=5" % (args.api_key, args.port))
    print("  Press Ctrl+C to stop.")
    print()
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] Stopping (state saved to %s)." % STATE_FILE)
        server.shutdown()


if __name__ == "__main__":
    main()