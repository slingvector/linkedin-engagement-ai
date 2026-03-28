import pytest
from app.workers.ingestion_worker import on_response, PostBuffer, parse_voyager_payload


@pytest.mark.asyncio
async def test_parse_voyager_payload_extracts_posts():
    """
    Unit test for parse_voyager_payload — the core Voyager extraction logic.
    Tests that it correctly identifies activities from a mock JSON structure.
    """
    mock_payload = {
        "included": [
            {
                "entityUrn": "urn:li:activity:7123456789012345678",
                "commentary": {
                    "text": {
                        "text": "This is a viral post about Python and Playwright!"
                    }
                },
                "numLikes": 1500,
                "numComments": 42,
            },
            {
                "urn": "urn:li:activity:8234567890123456789",
                "commentary": {
                    "text": {
                        "text": "Another post that should be captured."
                    }
                },
                "numLikes": 10,
                "numComments": 1,
            },
            {
                # MiniProfile — should be filtered out as a post candidate
                "entityUrn": "urn:li:fs_miniProfile:ABC",
                "firstName": "John",
                "lastName": "Doe",
            },
        ]
    }

    posts = parse_voyager_payload(mock_payload)

    # Should find 2 activity posts (miniProfile is filtered)
    assert len(posts) == 2

    post1 = next(p for p in posts if "7123456789012345678" in p.post_urn)
    assert post1.text == "This is a viral post about Python and Playwright!"
    assert post1.likes == 1500
    assert post1.comments == 42

    post2 = next(p for p in posts if "8234567890123456789" in p.post_urn)
    assert post2.text == "Another post that should be captured."
    assert post2.likes == 10
    assert post2.comments == 1


@pytest.mark.asyncio
async def test_post_buffer_deduplication():
    """Test that PostBuffer deduplicates by post_urn."""
    from app.workers.ingestion_worker import RawPost

    buffer = PostBuffer()

    post = RawPost(
        post_urn="urn:li:activity:1234567890123456789",
        text="Unique post",
        likes=100,
        comments=10,
    )

    added1 = await buffer.add(post)
    added2 = await buffer.add(post)  # duplicate

    assert added1 is True
    assert added2 is False

    count = await buffer.count()
    assert count == 1

    drained = await buffer.drain()
    assert len(drained) == 1
    assert drained[0].post_urn == post.post_urn

    # Buffer should be empty after drain
    assert await buffer.count() == 0


@pytest.mark.asyncio
async def test_on_response_skips_non_voyager_urls():
    """Test that non-Voyager URLs are silently skipped."""
    buffer = PostBuffer()

    class MockResponse:
        url = "https://static.licdn.com/some-asset.js"

        async def json(self):
            return {}

    # Should not raise, and buffer should remain empty
    await on_response(MockResponse(), buffer)
    assert await buffer.count() == 0
