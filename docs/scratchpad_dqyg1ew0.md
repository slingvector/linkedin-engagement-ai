# End-to-End Testing: Radar Page

## Checklist
- [x] Navigate to http://localhost:3000/radar (Current Page: http://localhost:3000/radar)
- [f] Check if "Action Desk Feed" has loaded mock posts. (Failed: 401 Unauthorized from backend)
- [ ] (If needed) Add a creator ('https://linkedin.com/in/testcreator') and wait for update. (Attempted, but failed due to 401)
- [ ] Click "Generate Comment Strategies" (if post not processed) and wait.
- [ ] Edit "AI Copilot Strategies" text area with 'Test feedback comment'.
- [ ] Click "Copy & Track Feedback" button.
- [ ] Verify POST request to `/api/v1/comments/feedback` (200 Success) in Network tab.
- [ ] Document outcomes for:
    - [ ] Feed Loading: Failure (401 Unauthorized)
    - [ ] Comment Generation: Not attempted (Feed failed)
    - [ ] Feedback Submission: Not attempted (Feed failed)

## Findings
- Initial load of http://localhost:3000/radar resulted in "No posts yet".
- Console logs reveal 401 Unauthorized errors for `http://localhost:8000/api/v1/copilot/feed` and `http://localhost:8000/api/v1/radar/creators`.
- Attempted to add a creator (`https://linkedin.com/in/testcreator`), but it also likely failed due to auth issues.
- Tried `userId=1` and `x-user-id=1` query parameters, but 401 persisted.
- Investigating network requests to see if any auth headers are missing or malformed.
