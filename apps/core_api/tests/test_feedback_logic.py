import pytest
from unittest.mock import MagicMock, AsyncMock
import difflib

from app.controllers.comment_controller import capture_comment_feedback
from app.schemas.comment import CommentFeedbackCreate

@pytest.mark.asyncio
async def test_capture_comment_feedback_logic():
    """
    Test the business logic of feedback capture, including similarity calculation.
    Mocks the database and user dependencies.
    """
    # Mock Request Data
    original = "This is a great AI generated comment."
    edited = "This is a great AI generated comment! I modified it slightly."
    
    request = CommentFeedbackCreate(
        post_id="post_123",
        original_generated_comment=original,
        final_user_edited_comment=edited,
        was_used=True,
        engagement_likes=0,
        engagement_replies=0
    )
    
    # Mock Database Session
    db = AsyncMock()
    db.add = MagicMock() # add is synchronous
    
    # Mock Current User
    current_user = MagicMock()
    current_user.id = "user_uuid_456"
    
    # Call the controller function directly
    response = await capture_comment_feedback(
        request=request,
        db=db,
        current_user=current_user
    )
    
    # Verify Response
    assert response["status"] == "success"
    
    # Verify Database Calls
    assert db.add.call_count == 2
    
    # Extract added objects (first call is CommentFeedback, second is ShadowActionLog)
    feedback_obj = db.add.call_args_list[0][0][0]
    shadow_log_obj = db.add.call_args_list[1][0][0]
    
    # Verify Feedback Object
    assert feedback_obj.post_id == "post_123"
    assert feedback_obj.original_generated_comment == original
    assert feedback_obj.final_user_edited_comment == edited
    
    # Verify Similarity Calculation (Manual check)
    expected_similarity = difflib.SequenceMatcher(None, original, edited).ratio()
    assert shadow_log_obj.edit_similarity_score == expected_similarity
    assert shadow_log_obj.action_type == "comment_generation"
    
    # Verify commit was called
    db.commit.assert_awaited_once()

@pytest.mark.parametrize("original,edited,expected_status", [
    ("Same", "Same", 1.0),
    ("ABC", "XYZ", 0.0), # Totally different
])
async def test_similarity_edge_cases(original, edited, expected_status):
    # Just verify the difflib logic used in the controller
    similarity = difflib.SequenceMatcher(None, original, edited).ratio()
    if original == edited:
        assert similarity == 1.0
    else:
        assert similarity < 0.2
