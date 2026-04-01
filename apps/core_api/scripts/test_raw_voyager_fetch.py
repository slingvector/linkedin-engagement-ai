import os
import json

def test_pure_voyager_fetch():
    # Setup Auth
    from app.config import get_settings
    settings = get_settings()
    if settings.linkedin_read_li_at_cookie:
        os.environ["LINKEDIN_LI_AT"] = settings.linkedin_read_li_at_cookie
    os.environ["LINKEDIN_EMAIL"] = settings.linkedin_read_email or "dummy@example.com"
    os.environ["LINKEDIN_PASSWORD"] = settings.linkedin_read_password or "dummy"

    # Instantiate the underlying linkedin_api client directly
    from read_flow.auth import build_voyager_client
    client = build_voyager_client()
    api = client._api  # the raw Linkedin() instance
    
    print("Fetching raw /feed/updatesV2 bypassing all strippers...")
    params = {
        "count": "30",
        "q": "chronFeed",
        "start": 0,
    }
    res = api._fetch(
        "/feed/updatesV2",
        params=params,
        headers={"accept": "application/vnd.linkedin.normalized+json+2.1"},
    )
    
    data = res.json()
    included = data.get("included", [])
    
    # 1. First Pass: Map all disconnected stats nodes by their URNs
    stats_map = {}
    for item in included:
        if item.get("$type") == "com.linkedin.voyager.feed.shared.SocialActivityCounts":
            urn = item.get("urn")
            if urn:
                stats_map[urn] = {
                    "likes": item.get("numLikes", 0),
                    "comments": item.get("numComments", 0)
                }
                
    # 2. Second Pass: Find actual post nodes and stitch the stats back in!
    posts_found = 0
    for item in included:
        # LinkedIn posts are usually UpdateV2
        if item.get("$type") == "com.linkedin.voyager.feed.render.UpdateV2":
            urn = item.get("updateMetadata", {}).get("urn")
            if urn:
                stats = stats_map.get(urn, {"likes": 0, "comments": 0})
                print(f"✅ Stitched Post: {urn}")
                print(f"      Likes:    {stats['likes']}")
                print(f"      Comments: {stats['comments']}")
                posts_found += 1
                
    print(f"\\nSUCCESS: Found and stitched {posts_found} total posts with stats from a single HTTP call.")

if __name__ == "__main__":
    test_pure_voyager_fetch()
