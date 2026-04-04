# Swagger UI Testing Checklist

## core_api (8000)
- [ ] Get auth token
- [x] GET /api/v2/analytics/heatmap (200 OK)
- [x] POST /api/v2/calendar/smart-fill (201 Created)
- [x] POST /api/v2/posts/{post_id}/score (200 OK)
- [x] GET /api/v2/posts/{post_id}/score (200 OK)
- [x] POST /api/v2/posts/{post_id}/carousel (500 Internal Server Error)
- [x] GET /api/v2/posts/{post_id}/carousel (404 Not Found)
- [x] POST /api/v2/posts/{post_id}/carousel/publish (401 Unauthorized)

## ai_engine (8001)
- [x] POST /webhooks/v2/generate/carousel-outline (200 OK)
- [x] POST /webhooks/v2/score/post (200 OK)
- [x] POST /webhooks/v2/generate/week-plan (200 OK)

## carousel_renderer (8002)
- [ ] GET /health
- [ ] POST /render
