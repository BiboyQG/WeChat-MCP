from __future__ import annotations

from PIL import Image, ImageDraw

from wechat_mcp import fetch_messages_by_chat_utils as fm

LIST_ORIGIN = (0.0, 0.0)
WIDTH, HEIGHT = 740, 200


def _canvas(background):
    return Image.new("RGB", (WIDTH, HEIGHT), background)


def _bubble(image, box, colour):
    ImageDraw.Draw(image).rounded_rectangle(box, radius=8, fill=colour)


def test_classifier_light_theme_other_and_me():
    bg = (250, 250, 250)
    img = _canvas(bg)
    _bubble(img, (20, 20, 56, 56), (40, 40, 40))  # avatar left
    _bubble(img, (70, 20, 320, 90), (238, 238, 240))  # grey bubble left
    _bubble(img, (400, 110, 700, 180), (149, 236, 105))  # green bubble right
    _bubble(img, (704, 110, 736, 146), (40, 40, 40))  # avatar right
    assert fm.classify_sender_for_message(img, LIST_ORIGIN, (0, 10), (WIDTH, 90), bg) == "OTHER"
    assert fm.classify_sender_for_message(img, LIST_ORIGIN, (0, 100), (WIDTH, 90), bg) == "ME"


def test_classifier_dark_theme():
    bg = (25, 25, 25)
    img = _canvas(bg)
    _bubble(img, (20, 20, 56, 56), (200, 200, 200))
    _bubble(img, (70, 20, 320, 90), (44, 44, 44))
    _bubble(img, (400, 110, 700, 180), (60, 150, 80))
    _bubble(img, (704, 110, 736, 146), (200, 200, 200))
    assert fm.classify_sender_for_message(img, LIST_ORIGIN, (0, 10), (WIDTH, 90), bg) == "OTHER"
    assert fm.classify_sender_for_message(img, LIST_ORIGIN, (0, 100), (WIDTH, 90), bg) == "ME"


def test_classifier_ignores_overlay_scrollbar():
    bg = (250, 250, 250)
    img = _canvas(bg)
    _bubble(img, (20, 20, 56, 56), (40, 40, 40))
    _bubble(img, (70, 20, 320, 90), (238, 238, 240))
    ImageDraw.Draw(img).rectangle((733, 0, 737, HEIGHT), fill=(180, 180, 180))  # scrollbar
    assert fm.classify_sender_for_message(img, LIST_ORIGIN, (0, 10), (WIDTH, 90), bg) == "OTHER"


def test_classifier_unknown_for_empty_or_offscreen_rows():
    bg = (250, 250, 250)
    img = _canvas(bg)
    assert fm.classify_sender_for_message(img, LIST_ORIGIN, (0, 10), (WIDTH, 90), bg) == "UNKNOWN"
    assert fm.classify_sender_for_message(img, LIST_ORIGIN, (0, -300), (WIDTH, 90), bg) == "UNKNOWN"


def test_estimate_background_uses_dominant_colour():
    img = _canvas((250, 250, 250))
    _bubble(img, (70, 20, 320, 90), (238, 238, 240))
    assert fm.estimate_background(img) == (250, 250, 250)


def test_merge_older_uses_longest_overlap():
    known = [fm.ChatMessage("ME", t) for t in ["c", "d", "e"]]
    visible = [fm.ChatMessage("ME", t) for t in ["a", "b", "c", "d"]]
    assert [m.text for m in fm._merge_older(visible, known)] == ["a", "b"]
    # Repeated messages: overlap is matched as a sequence, not a single anchor.
    known = [fm.ChatMessage("ME", t) for t in ["x", "x", "y"]]
    visible = [fm.ChatMessage("ME", t) for t in ["w", "x", "x"]]
    assert [m.text for m in fm._merge_older(visible, known)] == ["w"]
    # No overlap: everything visible is treated as older.
    assert len(fm._merge_older(visible, [fm.ChatMessage("ME", "z")])) == 3


def test_message_kind_detection():
    assert fm.message_kind("File\nreport.pdf\n2.1M\n微信电脑版", "OTHER") == "file"
    assert fm.message_kind("Image", "OTHER") == "image"
    assert fm.message_kind("Video", "ME") == "video"
    assert fm.message_kind("Animated Stickers [Thank You]", "OTHER") == "sticker"
    assert fm.message_kind("Voice CallDuration: 00:23", "OTHER") == "voice"
    assert fm.message_kind("[Sticker] Yes", "OTHER") == "sticker"
    assert fm.message_kind("ChannelsWHEAT-Mia", "ME") == "link"
    assert fm.message_kind("https://example.com/x", "ME") == "link"
    assert fm.message_kind("Images are ready", "ME") == "text"
    assert fm.message_kind("16:10", "SYSTEM") == "system"


def test_preview_matches_text():
    assert fm.preview_matches_text("Ivy: [Sticker] Thank\xa0You", "Animated Stickers [Thank\xa0You]")
    assert fm.preview_matches_text("[File] YES-Final.pdf", "File\nYES-Final.pdf\n2.1M\n微信电脑版")
    assert fm.preview_matches_text("wechat-mcp v4 reply test ✅", "wechat-mcp v4 reply test ✅")
    assert not fm.preview_matches_text("[Photo]", "Image")
    assert not fm.preview_matches_text("hello there friend", "completely different")
