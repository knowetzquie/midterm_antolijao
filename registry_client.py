import requests

class RegistryClient:
    def __init__(self, base_url="http://localhost:8080/api/v1",
                 api_key="aep-registry-key-2026"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self):  # sends the API key
        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    def _request(self, method, endpoint, **kwargs):  # headers + timeout, raises on 4xx/5xx
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        resp = requests.request(method, url, headers=self._headers(), timeout=5, **kwargs)
        resp.raise_for_status()
        return resp

    def get_services(self, limit=10, offset=0, status=None):
        # WORKED EXAMPLE: GET /services with optional ?status=
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        return self._request("GET", "services", params=params).json()

    # ---------- YOUR CODE: fill in the six methods below ----------
    def get_service(self, service_id):  # GET /services/{id} -> parsed JSON
        return self._request("GET", f"services/{service_id}").json()
    def create_service(self, payload):  # POST /services -> parsed JSON (201)
        return self._request("POST", "services", json=payload).json()

    def update_service(self, service_id, payload):  # PUT /services/{id} (full replace)
        return self._request("PUT", f"services/{service_id}", json=payload).json()


    def patch_service(self, service_id, patch):  # PATCH /services/{id} (partial)
        return self._request("PATCH", f"services/{service_id}", json=patch).json()


    def delete_service(self, service_id):  # DELETE -> return True on 204
        resp = self._request("DELETE", f"services/{service_id}")
        return resp.status_code == 204

    def health(self):  # GET /health -> parsed JSON
        return self._request("GET", "health").json()