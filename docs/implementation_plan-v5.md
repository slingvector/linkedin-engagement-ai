# Implementation Plan - PDF Persistence & Final Verification

The previous attempt failed because the generated PDF was lost during a container rebuild. This plan ensures that carousel assets are persisted across restarts and completes the LinkedIn publishing flow.

## User Review Required

> [!IMPORTANT]
> **Host Volume Creation**: I will mount `./tmp/carousel_pdfs` on your host machine to `/tmp/carousel_pdfs` inside the `core_api` container. This ensures that even if I rebuild the API again, your rendered carousels will remain available for publishing.

## Proposed Changes

### Infrastructure (DevOps)

#### [MODIFY] [docker-compose.local.yml](file:///Users/cortex/ventures/linkedin-as-a-service/docker-compose.local.yml)
- Add a volume mapping for the `core_api` service:
  - `./tmp/carousel_pdfs:/tmp/carousel_pdfs`

---

## Verification Plan

### Automated Tests
1. Update Docker Compose and restart the stack.
2. Re-run the `render` step (one last time) to generate the PDF.
3. Verify the file exists on your host machine in `./tmp/carousel_pdfs/`.
4. Execute the user's `publish` curl and confirm the LinkedIn post URN is returned.

### Manual Verification
- Confirm the post is successfully created on LinkedIn.
