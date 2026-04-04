import os
import json

from read_flow import ReadFlow
from read_flow.storage.base import StorageProtocol

# Dummy storage just to print the output without saving to the real database
class DummyStorage(StorageProtocol):
    def save_post(self, post):
        likes = post.get('likes', 'Not Found')
        comments = post.get('comments', 'Not Found')
        print(f"[TEST] Extracted Post -> Likes: {likes} | Comments: {comments} | URL: {post.get('url')}")
        return True
    def post_exists(self, url): return False
    def get_all_urls(self): return set()

def test_inline_extraction():
    # 1. Monkey-patch the VoyagerClient inside the library
    from read_flow.clients.voyager_client import VoyagerClient
    
    original_normalise = VoyagerClient._normalise_feed_post
    
    def wrapped_normalise(self, raw: dict):
        # Let the library do its standard normalization
        post = original_normalise(self, raw)
        
        # 2. Attempt to dig into the `raw` dict returned by the underlying linkedin-api
        # The underlying linkedin-api might expose numLikes at the top level or nested.
        likes = raw.get('numLikes', 0)
        comments = raw.get('numComments', 0)
        
        if not likes and 'socialDetail' in raw:
            counts = raw['socialDetail'].get('totalSocialActivityCounts', {})
            likes = counts.get('numLikes', 0)
            comments = counts.get('numComments', 0)
            
        post['likes'] = likes
        post['comments'] = comments
        
        # 3. Dump the very first RAW post to disk so we can inspect the exact shape 
        # that linkedin-api passes to linkedin-read-flow.
        if not hasattr(self, '_dumped_raw'):
            with open("/tmp/linkedin_api_raw_sample.json", "w") as f:
                json.dump(raw, f, indent=2)
            self._dumped_raw = True
            print("✅ Dumped the first 'raw' payload to /tmp/linkedin_api_raw_sample.json for inspection")
            
        return post
        
    VoyagerClient._normalise_feed_post = wrapped_normalise
    
    # Setup Auth from our namespaced environments
    from app.config import get_settings
    settings = get_settings()
    if settings.linkedin_read_li_at_cookie:
        os.environ["LINKEDIN_LI_AT"] = settings.linkedin_read_li_at_cookie
    os.environ["LINKEDIN_EMAIL"] = settings.linkedin_read_email or "dummy@example.com"
    os.environ["LINKEDIN_PASSWORD"] = settings.linkedin_read_password or "dummy_password"
    
    print("Starting Inline Extraction Test...")
    try:
        flow = ReadFlow(storage=DummyStorage())
        flow.fetch_feed()
        print("\\nTest complete. Check the console output above to see if Likes/Comments were populated.")
        print("If they say '0', check /tmp/linkedin_api_raw_sample.json to see if the data is buried in another object key (or stripped entirely).")
    except SystemExit:
        print("Authentication dropped. Ensure your LINKEDIN_READ_LI_AT is populated in your .env.")

if __name__ == "__main__":
    test_inline_extraction()
