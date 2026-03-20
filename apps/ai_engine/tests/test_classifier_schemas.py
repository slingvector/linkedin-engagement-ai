import pytest
from app.schemas.classifier_schemas import ClassificationRequest, ProfileItem, ClassificationResponse, ClassificationItem

class TestClassifierSchemas:
    def test_valid_request(self):
        req = ClassificationRequest(
            profiles=[
                ProfileItem(id="123", headline="Software Engineer at ACME"),
                ProfileItem(id="456", headline="Founding Partner")
            ]
        )
        assert len(req.profiles) == 2
        assert req.profiles[0].id == "123"

    def test_valid_response(self):
        resp = ClassificationResponse(
            classifications=[
                ClassificationItem(id="123", persona="Engineering & Tech"),
                ClassificationItem(id="456", persona="Founder / C-Suite")
            ]
        )
        assert len(resp.classifications) == 2
        assert resp.classifications[1].persona == "Founder / C-Suite"
