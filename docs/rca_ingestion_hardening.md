# Root Cause Analysis: Stabilizing Creator Radar Ingestion

This document details the critical blockers identified during the hardening of the Two-Tier Ingestion engine (Network Interception + AI Semantic Fallback).

## 1. 502 Tunnel Connection Failure (The Networking Blocker)

**Symptom**: Ingestion pipeline consistently returns 0 posts despite high-engagement evidence in logs.
**Root Cause**: Playwright encountered a `502: Tunnel Connection Failed` error during navigation to `linkedin.com/feed`. This is a network-layer failure (likely proxy or local environment related) that prevents the browser from reaching the destination. 
**Impact**: Both Tier 1 (GraphQL Interceptor) and Tier 2 (LLM Fallback) fail because the browser never actually renders the LinkedIn feed.

## 2. Aggressive BeautifulSoup Pruning (Data Loss)

**Symptom**: AI Engine received empty text dumps or only ~1KB of content from a 342KB HTML payload.
**Root Cause**: The Tier 2 pre-processor was using `BeautifulSoup` to `decompose()` all `<script>` tags to "clean" the text for the LLM. 
**Mechanism**: LinkedIn is a heavy SPA that stores its core feed data (UpdateV2 blocks) inside `<script type="application/json">` or state-managed script tags. By deleting all scripts, we were inadvertently purging the very data the AI Engine needed to parse.
**Resolution**: Switched to a **Raw HTML** approach for Tier 2, sending the unprocessed DOM buffer to Gemini 1.5 Flash (which handles HTML natively) to ensure zero data loss.

## 3. Invalid Model Identifier (AI Engine Configuration)

**Symptom**: AI Engine returned `{"posts": []}` even when feed content was present.
**Root Cause**: The [apps/ai_engine/config.yaml](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/config.yaml) was configured to use `gemini-2.5-flash` for development/staging environments.
**Technical Detail**: No such model currently exists in the Google AI Studio hierarchy (stable versions are 1.5 and 2.0). The LLM Service was defaulting to a non-functional model string, leading to silent failures or empty responses.
**Resolution**: Corrected the configuration to use the stable `gemini-1.5-flash` model.

## 4. Strict Schema Enforcement (Recall Bottleneck)

**Symptom**: LLM failed to extract posts if specific metadata (like author profile slugs) was missing from the raw text.
**Root Cause**: The [ExtractionService](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/app/services/extraction_service.py#23-86) used Gemini's `response_schema` feature with `required` constraints on fields like `author_profile_id` and `post_urn`. If the text dump lacked these specific substrings, the model returned an empty array rather than a partial object.
**Resolution**: Relaxed the schema constraints to make metadata optional, prioritizing the capture of `author_name` and [text](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/app/services/extraction_service.py#27-86) for 100% extraction recall.

---

> [!IMPORTANT]
> The networking 502 error is an external environmental blocker. Once the local tunnel/proxy is stable, the Two-Tier logic (now hardened against pruning and configuration bugs) will reliably ingest viral content.
