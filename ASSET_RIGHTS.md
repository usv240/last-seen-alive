# Asset rights register

No asset is approved for the final submission until this register includes its origin, licence,
credit line and SHA-256.

| Asset | Origin | Rights status | Required credit | SHA-256 | Approved |
|---|---|---|---|---|---|
| Landing-page illustrated frame | Self-created HTML/CSS | Original work | None | N/A | Yes |
| Ten evaluation fragments (D01–D05, H01–H05) | Library of Congress National Screening Room; every work published by 1929 | United States public domain | Library of Congress, Motion Picture, Broadcasting, and Recorded Sound Division. | Per case in [`eval/manifest.json`](eval/manifest.json), served as the `X-Fragment-SHA256` response header | Yes |
| Demo narration and captions | Self-created | Original work | None | Pending | No |

Per-case provenance — the exact LOC item page, the source segment URLs, the visual-selection
rationale and every transform applied — is recorded in [`eval/ASSET_RIGHTS.md`](eval/ASSET_RIGHTS.md)
and the private answer key.

The required credit appears in four places at runtime, not only in this file: the
`X-Credit` header on every media response, each preset card on `/presets`, the
`credit` field of every `/v1/presets` record, and the footer of every page.

The Library states it is unaware of U.S. restrictions for the vast majority of these films but
places item-specific copyright, privacy, publicity, licensing and trademark assessment on the
user. Recheck each item immediately before public release and retain a dated record of that
review.

Third-party trailers, broadcast clips, logos and published screenplay pages are prohibited from
the submission even when they would ordinarily qualify as fair use.

## Material supplied by users

`POST /v1/investigate` accepts a caller's own file. That material is held in memory for the
duration of the request and is never written to disk, logged, retained, or used to train
anything. It is transmitted to Gemini on Vertex AI for reading and text drawn from it is sent to
Parallel as search queries, which is what the investigation consists of. This is stated on the
upload form, in the OpenAPI description, and in [SECURITY.md](SECURITY.md). No rights in
user-supplied material are claimed, and none are verified — callers are told not to upload
material they are not free to send to those two services.
