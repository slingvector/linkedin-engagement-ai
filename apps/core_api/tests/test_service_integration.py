import pytest
import time
from unittest.mock import MagicMock, patch
from app.services.appium_read_service import AppiumReadService

@pytest.fixture
def service_integration():
    AppiumReadService.reset()
    # Mock ADBClient._run to simplify integration testing
    with patch("app.services.adb_client.ADBClient._run") as mock_run:
        mock_run.return_value = (0, "test_device\tdevice", "")
        svc = AppiumReadService(config={"device_udid": "test_device"})
        svc._driver = MagicMock()
        return svc, mock_run

def test_dismiss_popups_integration(service_integration):
    svc, mock_adb_run = service_integration
    
    # Mock driver to return elements for both ID and Text
    mock_el_id = MagicMock()
    mock_el_text = MagicMock()
    
    # Mock the driver's find_element and finding elements via XML (for click_text)
    svc._driver.find_element.return_value = mock_el_id
    with patch.object(svc, "_tap_by_text_xml") as mock_tap_xml:
        mock_tap_xml.return_value = True
        
        result = svc.dismiss_popups()
        
        assert result is True
        # Verify it tries ID first
        svc._driver.find_element.assert_any_call("id", "com.linkedin.android:id/ad_non_modal_dialog_close_button")
        # Verify it continues to text tokens if needed (well, my dismiss_popups returns early if ID succeeds, or does it?)
        # Let's check the code:
        # if self.device.click_element_by_id(popup_id): ... return popups_dismissed
        # It doesn't break, it continues to check texts.
        mock_tap_xml.assert_called()

def test_get_post_link_integration(service_integration):
    svc, mock_adb_run = service_integration
    
    with patch.object(svc, "_tap_by_text_xml") as mock_tap_xml, \
         patch.object(svc, "get_clipboard_text") as mock_get_clip:
        
        mock_tap_xml.return_value = True
        mock_get_clip.return_value = "https://linkedin.com/posts/abc"
        
        link = svc.get_post_link()
        
        assert link == "https://linkedin.com/posts/abc"
        assert mock_tap_xml.call_count >= 2 # Send and Copy link

def test_scroll_down_calls_adb(service_integration):
    svc, mock_adb_run = service_integration
    
    # Reset mock_adb_run because it was called during init
    mock_adb_run.reset_mock()
    
    svc.scroll_down()
    
    # Verify it calls adb shell input swipe
    # scroll_up calls swipe(540, 1800, 540, 400, 800)
    args_list = [call.args[0] for call in mock_adb_run.call_args_list]
    flattened_args = [arg for sublist in args_list for arg in sublist]
    assert "swipe" in flattened_args
    assert "input" in flattened_args
