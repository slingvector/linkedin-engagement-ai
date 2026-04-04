# Implementation Plan - Fix LinkedIn API Versioning

The LinkedIn `/rest/` API now strictly requires a `LinkedIn-Version` header in the `YYYYMM` format. Our previous attempts failed because this header was missing. This plan updates the publishing pipeline to satisfy this requirement.

## User Review Required

> [!IMPORTANT]
> **API Version Target**: I am targeting version `202603` (March 2026) as per your current system date. If your LinkedIn App was created very recently, it might require a newer monthly version, but `202603` is the current stable standard.

## Proposed Changes

### Core API (Backend)

#### [MODIFY] [carousel_service.py](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/services/carousel_service.py)
- Update `headers` in `publish_to_linkedin` to include:
  - `LinkedIn-Version: 202603`
- Ensure this header is present in both `initializeUpload` (POST) and `posts` (POST) requests.
- Note: The file upload (PUT) does **not** usually require the version header as it goes to a temporary S3-style bucket, but I will monitor the logs regardless.

#### [MODIFY] [v2/auth_controller.py](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/controllers/v2/auth_controller.py)
- *Investigation*: Check if `/v2/userinfo` requires the version header. Standard OpenID Connect `/v2/` endpoints usually do NOT require it, but if it starts failing, I will add it there as well.

---

## Verification Plan

### Automated Tests
1. Re-run the `render` step to ensure the asset is ready.
2. Execute the user's `publish` curl and confirm the `VERSION_MISSING` error is resolved.
3. Monitor `core_api` logs for any 403 (Permission) or 400 (Validation) errors following the version fix.

### Manual Verification
- Confirm the `li_post_urn` is returned in the response.
- Ask the user to verify the post is visible on Account A's feed.
