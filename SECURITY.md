# Security

Report vulnerabilities privately to the repository owner rather than opening a public issue.

- Credentials are loaded from environment variables backed by Secret Manager in deployment.
- The Parallel key is never sent to the browser or returned by an endpoint.
- Held-out samples are rejected before their media files are read.
- The public workflow accepts only allow-listed corpus IDs; it is not an arbitrary URL fetcher.
- Generated findings cannot approve an identity. The deterministic gate and an archivist own it.

Rotate a credential immediately if it appears in logs, commits, screenshots, or demo footage.
