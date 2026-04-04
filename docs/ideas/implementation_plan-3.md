# Implementation Plan - Stable Mac Mini Deployment

This plan outlines how to turn your Mac Mini into a permanent 24/7 server for your trial run, using a stable Ngrok URL instead of an ephemeral tunnel.

## User Review Required

> [!IMPORTANT]
> **Static Domain Requirement**: You must claim your one free static domain in the [Ngrok Dashboard](https://dashboard.ngrok.com/cloud-edge/domains).
> 
> **Persistence**: Since this is a "permanent" trial, we will use **PM2** (Process Manager) to ensure that if your Mac Mini restarts or the tunnel crashes, it automatically comes back online.

## Proposed Steps

### 1. Ngrok Configuration
- **Static Domain**: Claim `[your-name].ngrok-free.app`.
- **Tunnel Setup**: Configure Ngrok to point to port `8000` (Core API) and `3000` (Web).
  - *Recommendation*: Use a single Ngrok tunnel for the API and let the Frontend run on the same Mac Mini.

### 2. Service Persistence (PM2)
I will provide a `scripts/keep_alive.sh` that:
- Installs `pm2` (via npm).
- Starts your `docker-compose.local.yml`.
- Starts the `ngrok` tunnel as a background process.
- Sets up `pm2 startup` so it survives a Mac reboot.

### 3. LinkedIn Portal Update
Update your official URIs to use the new stable domain:
`https://[your-choice].ngrok-free.app/api/v1/auth/linkedin/callback`
`https://[your-choice].ngrok-free.app/api/v2/auth/linkedin/callback`

---

## Open Questions

- **NPM Available?**: Is `npm` installed on your Mac Mini? (Required for PM2).
- **Public URL Preference**: Do you prefer `ngrok` (faster setup) or `cloudflare` (more professional but requires a domain)?

## Verification Plan

### Manual Verification
1. I will provide a script to check if the Ngrok tunnel is active via its local API.
2. We will verify the LinkedIn login flow using the new permanent domain.
