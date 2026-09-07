"""End-to-end verification against the live service.

Run it yourself:

    python scripts/verify_live.py
    python scripts/verify_live.py https://your-own-deployment.example

Every assertion corresponds to a claim made in README, JUDGING or STATUS. It
checks behaviour, not just that endpoints return 200: that the bytes served for
a demo fragment hash to the value the manifest publishes, that a held-out case
is refused on every path, that a key minted once authenticates across the whole
instance pool, that the worked example is marked as an example everywhere and
cites only unresolvable domains, and that a missing partner credential produces
a refusal rather than a guess.

Needs network but no credentials. Deliberately not under tests/, because CI runs
offline against the pinned lock.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else
        "https://last-seen-alive-109051079423.us-central1.run.app").rstrip("/")
results: list[tuple[bool, str, str]] = []


def call(path, *, method="GET", key=None, body=None, headers=None, raw=False):
    url = path if path.startswith("http") else BASE + path
    h = dict(headers or {})
    if key:
        h["Authorization"] = f"Bearer {key}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            payload = r.read()
            return r.status, Headers(r.headers), (payload if raw else json.loads(payload or b"{}"))
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            return e.code, Headers(e.headers), json.loads(payload or b"{}")
        except json.JSONDecodeError:
            return e.code, Headers(e.headers), {}


class Headers(dict):
    """Case-insensitive header access. HTTP/2 lowercases field names."""

    def get(self, key, default=None):
        lowered = {k.lower(): v for k, v in self.items()}
        return lowered.get(key.lower(), default)

    def __contains__(self, key):
        return key.lower() in {k.lower() for k in self.keys()}


def check(name, condition, detail=""):
    results.append((bool(condition), name, detail))


# ---------------------------------------------------------------- surfaces
for path in ("/", "/presets", "/api", "/stack", "/docs", "/openapi.json",
             "/static/styles.css", "/static/common.js", "/static/console.js",
             "/static/favicon.svg"):
    status, _, _ = call(path, raw=True)
    check(f"page {path}", status == 200, f"HTTP {status}")

# ---------------------------------------------------------------- health
status, _, health = call("/health/integrations")
integ = health["data"]["integrations"]
check("health reports Google live", integ["google_vertex_ai"]["ok"] is True)
check("health reports signing pepper present", integ["api_keys"]["ok"] is True)
check("health reports Parallel honestly as unavailable",
      integ["parallel_search"]["ok"] is False
      and integ["parallel_search"]["detail"] == "credential_not_configured")

# ---------------------------------------------------------------- stack
status, _, stack = call("/v1/stack")
d = stack["data"]
parallel_keys = {e["key"] for e in d["parallel"]}
check("all six Parallel surfaces listed", parallel_keys == {
    "parallel_search", "parallel_task", "parallel_extract",
    "parallel_findall", "parallel_task_group", "parallel_monitor"}, str(parallel_keys))
check("five Google Cloud surfaces listed", len(d["google_cloud"]) == 5)
check("every surface names its call site",
      all(e.get("call_site") for e in d["google_cloud"] + d["parallel"]))
check("every surface has a short ribbon label",
      all(e.get("short") for e in d["google_cloud"] + d["parallel"]))
check("Parallel surfaces reported unavailable, not optimistic",
      all(e["status"] == "unavailable" for e in d["parallel"]))
check("Google surfaces reported live", all(e["status"] == "live" for e in d["google_cloud"]))

# ---------------------------------------------------------------- presets
status, _, presets = call("/v1/presets")
rows = presets["data"]["presets"]
check("ten demo fragments", len(rows) == 10)
check("five runnable", sum(r["runnable"] for r in rows) == 5)
check("five sealed", sum(not r["runnable"] for r in rows) == 5)
check("every preset carries the LOC credit",
      all(r["credit"].startswith("Library of Congress") for r in rows))
blob = json.dumps(presets).lower()
check("listing does not leak the discriminating clue",
      "jiminy" not in blob and "bray studios" not in blob)
check("required behaviour is published per case",
      {r["expected_outcome"] for r in rows} == {"identify", "candidates", "abstain", "contradict"})

# media integrity
status, _, manifest = call("/v1/eval/manifest")
by_id = {r["case_id"]: r for r in manifest}
for case in ("D01", "D02", "D05"):
    status, headers, body = call(f"/v1/presets/{case}/media", raw=True)
    served = hashlib.sha256(body).hexdigest()
    check(f"{case} media served", status == 200)
    check(f"{case} bytes match published manifest hash", served == by_id[case]["sha256"])
    check(f"{case} hash header matches bytes", headers.get("X-Fragment-SHA256") == served)
    check(f"{case} carries the credit header",
          (headers.get("X-Credit") or "").startswith("Library of Congress"))

status, headers, _ = call("/v1/presets/D02/media", headers={"Range": "bytes=0-999"}, raw=True)
check("media supports range requests (scrubbing)", status == 206, f"HTTP {status}")

status, _, _ = call("/v1/presets/H01/media", raw=True)
check("holdout media is never served", status == 423, f"HTTP {status}")

# ---------------------------------------------------------------- worked example
status, _, example = call("/v1/example/dossier")
check("worked example needs no key", status == 200)
check("worked example is marked at every level",
      example["meta"]["example"] is True and example["data"]["example"] is True)
check("worked example demonstrates the gate refusing",
      example["meta"]["verdict"] == "candidates")
check("worked example blocked by human approval",
      "human_approved" in example["meta"]["gate"]["failed"])
urls = json.dumps(example)
check("worked example cites only reserved domains",
      "example.org" in urls and "example.com" in urls
      and "loc.gov" not in urls.replace("Library of Congress", ""))
refused = [s for c in example["data"]["evidence"]["claims"] for s in c["sources"]
           if s["live_verified"] is False]
check("worked example shows a citation refused by the live audit", bool(refused))
check("a refused citation cannot carry a threshold",
      all(s["counts_toward_gate"] is False for s in refused))

# ---------------------------------------------------------------- keys
status, _, minted = call("/v1/keys", method="POST", body={"tier": "judge"})
key = minted["data"]["key"]
check("judge key minted with no email", status == 200 and key.startswith("lsa_"))
check("key is not recoverable server-side",
      "not stored" in minted["data"]["storage"].lower())

ok = 0
for _ in range(8):
    s, _, _ = call("/v1/eval/latest", key=key)
    ok += s == 200
check("key authenticates across the instance pool", ok == 8, f"{ok}/8")

s, _, err = call("/v1/eval/latest", key="lsa_not.a.key")
check("forged key rejected", s == 401 and err["error"]["code"] == "invalid_api_key")
s, _, err = call("/v1/eval/latest")
check("missing key distinguished from invalid",
      s == 401 and err["error"]["code"] == "missing_api_key")

# ---------------------------------------------------------------- boundaries
s, _, err = call("/v1/identify", method="POST", body={"sample_id": "D02"})
check("identify requires a key", s == 401)

s, _, err = call("/v1/identify", method="POST", key=key, body={"sample_id": "D02"})
check("identify fails closed without Parallel",
      s == 503 and err["error"]["code"] == "partner_credential_not_configured", f"HTTP {s}")
check("the fail-closed message refuses to guess",
      "model memory" in err["error"]["message"])

s, _, err = call("/v1/identify", method="POST", key=key, body={"sample_id": "H01"})
check("holdout sealed even with a valid key",
      s == 423 and err["error"]["code"] == "holdout_sealed")

s, _, err = call("/v1/identify", method="POST", key=key, body={"sample_id": "ZZ9"})
check("malformed sample id rejected", s == 422, f"HTTP {s}")

# A real multipart upload of an unsupported type. This proves the validation
# ordering fix live: the caller is told what is wrong with *their* request
# rather than being blamed on a missing partner credential.
boundary = "----lsae2e"
CRLF = chr(13) + chr(10)
part = (
    "--" + boundary + CRLF
    + 'Content-Disposition: form-data; name="fragment"; filename="x.zip"' + CRLF
    + "Content-Type: application/zip" + CRLF + CRLF
).encode() + b"not a video" + (CRLF + "--" + boundary + "--" + CRLF).encode()
req = urllib.request.Request(
    BASE + "/v1/investigate", data=part, method="POST",
    headers={"Authorization": f"Bearer {key}",
             "Content-Type": f"multipart/form-data; boundary={boundary}"})
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        s, err = r.status, json.loads(r.read() or b"{}")
except urllib.error.HTTPError as e:
    s, err = e.code, json.loads(e.read() or b"{}")
check("upload validated before the partner credential is blamed",
      s == 422 and err.get("error", {}).get("code") == "fragment_rejected", f"HTTP {s} {err}")

s, _, err = call("/v1/watch", method="POST", key=key,
                 body={"fragment_label": "reel 41B", "rare_strings": ["a visible intertitle"]})
check("watch fails closed without Parallel", s == 503, f"HTTP {s}")

# ---------------------------------------------------------------- error contract
for path, body in (("/v1/identify", {"sample_id": "H01"}),):
    s, _, err = call(path, method="POST", key=key, body=body)
    e = err.get("error", {})
    check("errors carry code, message, fix and docs",
          all(k in e for k in ("code", "message", "fix", "docs")), str(sorted(e)))
    check("errors carry a request id", "request_id" in err.get("meta", {}))

# ---------------------------------------------------------------- CORS
s, headers, _ = call("/v1/presets", method="OPTIONS", headers={
    "Origin": "https://an-archive.example.org",
    "Access-Control-Request-Method": "GET",
    "Access-Control-Request-Headers": "authorization"}, raw=True)
check("CORS preflight allows a third-party browser client",
      headers.get("Access-Control-Allow-Origin") == "*", f"HTTP {s}")
check("CORS does not allow credentials (no CSRF surface)",
      "Access-Control-Allow-Credentials" not in headers)

# ---------------------------------------------------------------- openapi
s, _, spec = call("/openapi.json")
paths = set(spec["paths"])
for required in ("/v1/keys", "/v1/identify", "/v1/investigate", "/v1/watch",
                 "/v1/presets", "/v1/stack", "/v1/example/dossier",
                 "/health/integrations", "/v1/eval/manifest"):
    check(f"openapi documents {required}", required in paths)
check("openapi describes the abstention contract",
      "abstention" in json.dumps(spec).lower())

# ---------------------------------------------------------------- report
passed = sum(1 for ok_, _, _ in results if ok_)
print(f"\n{'=' * 62}\nLast Seen Alive · live verification\n{BASE}\n{'=' * 62}")
for ok_, name, detail in results:
    if not ok_:
        print(f"  FAIL  {name}  {detail}")
if passed == len(results):
    print("  every check passed")
print(f"\n  {passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)
