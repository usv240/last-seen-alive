# Security

Report vulnerabilities privately to the repository owner rather than opening a public issue.

## Credentials

- Credentials are loaded from environment variables backed by Secret Manager in deployment.
- The Parallel key is never sent to the browser and is never returned by an endpoint. The
  integration health probe reports only whether a call succeeded and its search id.
- API keys are HMAC-signed over a server-side pepper and are not stored anywhere. A plaintext key
  is shown once at mint time and cannot be listed or recovered afterwards. Rotating
  `API_KEY_PEPPER` invalidates every outstanding key at once, which is the revocation mechanism.
- Rotate a credential immediately if it appears in logs, commits, screenshots or demo footage.

## Request surface

- `POST /v1/identify` accepts only allow-listed corpus IDs. It is not an arbitrary URL fetcher.
- `POST /v1/investigate` accepts a caller-supplied file. It is validated before any model or
  partner call: non-empty, at most 48 MB, and one of an allow-list of video and image media
  types. Nothing in the request is interpreted as a path, a URL, or a command.
- Both investigation endpoints and `POST /v1/watch` require a Bearer key. Presets, health, stack
  and corpus metadata are public so a judge can inspect the system without minting anything.
- Held-out samples are rejected before their media files are read, and held-out media is never
  served on any path.

## Caller-supplied material

An uploaded fragment is held in memory for the duration of the request and is never written to
disk, logged, retained, or used to train anything. It is transmitted to Gemini on Vertex AI to be
read, and text drawn from it is sent to Parallel as search queries — that is the investigation
itself. This is stated on the upload form and in the OpenAPI description, and callers are told
not to upload material they are not free to send to those two services.

## Decision boundary

- Generated findings cannot approve an identity. The deterministic gate and an archivist own it.
- `human_approved` is a gate threshold that no API call can satisfy, so the API can never return
  a confirmed identification.
- A missing partner credential produces a 503, never a degraded answer from model memory.
