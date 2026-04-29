---
tags: [environment, cloudflare, r2, s3, storage]
created: 2026-04-26
updated: 2026-04-27
type: environment
related: [[pipeline-system]], [[giro3d-viewer]], [[wsl2-setup]]
---

# Cloudflare R2 — Setup & Usage

Object storage for COPC and COG files. Accessed via the AWS CLI using R2's S3-compatible API.

---

## Credentials

Stored in standard AWS CLI config files — **not** in `.bashrc`.

**`~/.aws/credentials`**
```ini
[r2]
aws_access_key_id     = <R2 API token key ID>
aws_secret_access_key = <R2 API token secret>
```

**`~/.aws/config`**
```ini
[profile r2]
region       = auto
output       = json
endpoint_url = https://<account_id>.r2.cloudflarestorage.com
```

The account ID is the 32-char hex string visible in the Cloudflare dashboard URL and in the endpoint. The API token is created under **R2 → Manage API tokens** in the Cloudflare dashboard — token must have at minimum **Object Read & Write** on the target bucket.

---

## Bucket structure

| Bucket | Prefix | Contents |
|---|---|---|
| `geospatial-vision` | `copc/` | COPC point cloud files (`.copc.laz`) |
| `geospatial-vision` | `cog/` | COG terrain files (`.tif`) — live, served via TiTiler |

---

## Key commands

Always pass `--profile r2`. `ListBuckets` is denied by the token — address the bucket directly.

```bash
# List contents
aws s3 ls s3://geospatial-vision/copc/ --profile r2

# Upload a file
aws s3 cp file.copc.laz s3://geospatial-vision/copc/ --profile r2

# Sync a directory
aws s3 sync ./output/copc/ s3://geospatial-vision/copc/ --profile r2
```

---

## Public access & CORS

The bucket is configured for public read access via the Cloudflare dashboard (**R2 → geospatial-vision → Settings → Public access**). CORS is set to allow `GET` from any origin so browser clients (Giro3D, COPC viewer) can fetch files directly.

Public URL format:
```
https://pub-<hash>.r2.dev/copc/<filename>
```
or via a custom domain if configured. Verify the exact public URL in the Cloudflare dashboard.

COPC file confirmed working in the official COPC viewer at `viewer.copc.io`.

---

## Uploading pipeline outputs

After a pipeline run, upload from `Geoprocessor/pipeline/output/`:

```bash
# COPC
aws s3 cp Geoprocessor/pipeline/output/<stem>.copc.laz \
  s3://geospatial-vision/copc/ --profile r2

# COG DTM (after make_cog step)
aws s3 cp Geoprocessor/pipeline/output/<stem>_dtm_cog.tif \
  s3://geospatial-vision/cog/ --profile r2
```
