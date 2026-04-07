# Root Cause Analysis: Radar Page Crash

## Error Profile
- **Error:** `TypeError: Cannot read properties of undefined (reading 'map')`
- **Location:** [apps/web/src/app/radar/page.tsx](file:///Users/cortex/ventures/linkedin-as-a-service/apps/web/src/app/radar/page.tsx) line 131

## Root Cause
1. **React Query Lifecycle Fallthrough:** The `useQuery` hook for `["radar-feed"]` defaults `feedData` to `undefined` during its initial state or if the query encounters an error (like an API failure or network timeout).
2. **Defective Ternary Logic:** The render logic used `feedData?.length === 0` to check for an empty array. If `feedData` is `undefined`, optional chaining evaluates to `undefined`, which does not equal `0`. This evaluates as `false`.
3. **Unsafe Mapping:** Because both `feedLoading` and `feedData?.length === 0` evaluated to `false`, the React component mistakenly fell through to the `else` block containing `{feedData.map(...)}`. Mapping an `undefined` value caused the application crash.

## Robust Fix Implemented
- **Frontend Safeguard:** Updated the ternary condition from `feedData?.length === 0` to `!feedData || feedData.length === 0`. This guarantees that if `feedData` is `null` or `undefined` (due to a failed network request), the UI will gracefully show the "No posts yet" empty state rather than attempting to iterate over undefined memory.
- **Backend Stability:** While the frontend is now crash-proof, standard network observability should track why `res.data.items` failed to parse in the [queryFn](file:///Users/cortex/ventures/linkedin-as-a-service/apps/web/src/app/radar/page.tsx#24-28) (e.g., initial 502 Bad Gateway during Docker startup or database lock).
