# Root Cause Analysis: Feed Corruption & AI Null Outputs

This document summarizes the investigation and resolution of the three critical bugs discovered during the end-to-end verification of the Creator Radar pipeline.

## 1. Feed Corruption (Notification Cards)

**Symptom**: The Action Desk Feed was populated with strange posts featuring "LinkedIn User None" and URNs looking like `urn:li:fsd_notificationCard:(SHARED_BY_YOUR_NETWORK...)`.
**Root Cause**: The headless Playwright network interceptor was broadly configured to capture any JSON payloads from LinkedIn's `api/graphql` or `updatesV2` APIs. LinkedIn frequently bundles system notification alerts (like "X reposted Y" or "Check out these new jobs") into these same GraphQL payload arrays along with actual user posts. The recursive dictionary parser ([extract_posts_recursively](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/workers/ingestion_worker.py#26-127)) correctly found matching `numLikes` sub-properties within these notification cards and mistakenly injected them into the Creator Radar database as standard posts.
**Resolution**: We updated the [ingestion_worker.py](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/workers/ingestion_worker.py) recursion logic to explicitly evaluate the `entityUrn` of every node before extracting stats. Any URN containing the substrings `fsd_notificationCard` or `fs_miniProfile` is now strictly skipped entirely, ensuring the [IngestedPost](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/models/creator.py#41-75) database remains pure.

## 2. Empty AI Strategy Comments (Null String Outputs)

**Symptom**: Clicking "Generate Comment Strategies" successfully hit the `/webhooks/generate/comments` API and returned HTTP 200, but the UI text areas remained completely empty.
**Root Cause**: The `gpt-4o-mini` OpenAI fallback was misconfigured. While the primary Gemini SDK `GenerateContentConfig` correctly enforces the expected JSON schema (e.g., `comment_insightful`, `comment_contrarian`), the [LLMService](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/app/services/llm_service.py#18-148)'s OpenAI fallback logic was only passing `response_format={"type": "json_object"}` without actually providing the expected schema definition to the model. Without knowing the required keys, OpenAI either returned `{}` or hallucinatory keys that didn't match the frontend properties. During the Python response unpack (`result.get("comment_insightful", "")`), these missing keys resolved to empty strings.
**Resolution**: Modified [llm_service.py](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/app/services/llm_service.py) to aggressively bind the stringified JSON schema directly into the `fallback_prompt` system instruction before calling `openai`. Additionally, we increased visibility by logging the full `json.dumps(result)` immediately after generation inside [CommentService](file:///Users/cortex/ventures/linkedin-as-a-service/apps/ai_engine/app/services/comment_service.py#25-91).

## 3. Global Loading State Bug (All Buttons Spinning)

**Symptom**: Pressing the AI Generation button on a single post caused *all* generation buttons across the entire feed to simultaneously enter the "Generating Strategies (Ollama)..." loading state.
**Root Cause**: A shared React state bug. The interface relied on a single generalized `useMutation` hook (`generateComments`) that was defined outside the map iteration block. The `disabled` status and the text swap in the UI relied simply on the global boolean `generateComments.isPending`. Because every single mapped row referenced this exact same boolean, any active network connection painted the entire list as "busy".
**Resolution**: Leveraged React Query's built-in `variables` property. By qualifying the loading condition to only trigger if [(generateComments.isPending && generateComments.variables === post.post.id)](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/tests/conftest.py#9-13), we successfully constrained the loading indicator solely to the specific post row initiating the asynchronous request.
