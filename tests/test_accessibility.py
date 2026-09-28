from __future__ import annotations

from conftest import FakeElement, make_app, make_main_window, session_item

from wechat_mcp import wechat_accessibility as wa


def test_normalize_chat_title_strips_member_count():
    assert wa._normalize_chat_title("My Group(23)") == "My Group"
    assert wa._normalize_chat_title("  Alice ") == "Alice"
    assert wa._normalize_chat_title("Team (2024)") == "Team"


def test_chat_names_match_is_case_insensitive_and_ignores_count():
    assert wa.chat_names_match("File Transfer", "file transfer")
    assert wa.chat_names_match("Migsoft & Yestech(5)", "Migsoft & Yestech")
    assert not wa.chat_names_match("Migsoft & Yestech", "Migsoft and Yestech")
    assert not wa.chat_names_match(None, "x")


def test_parse_session_title_variants():
    row = wa.parse_session_title("Alice", "Alice\nBob: hello\n16:10\nMute Notifications\n")
    assert row.preview == "Bob: hello" and row.time == "16:10" and row.muted is True
    row = wa.parse_session_title("Bob", "Bob\n🙏\nSaturday\n")
    assert row.preview == "🙏" and row.time == "Saturday" and row.muted is False
    row = wa.parse_session_title("Empty", "Empty\nWednesday\n")
    assert row.preview is None and row.time == "Wednesday"


def test_get_main_window_prefers_standard_window_over_search_dialog(fake_ax):
    main = make_main_window([session_item("Alice", "hi", "16:00", y=256)])
    dialog = FakeElement(role="AXWindow", subrole="AXDialog", title="")
    app = make_app(main, [dialog])
    # The dialog is listed first, as WeChat does while searching.
    app.attrs["AXWindows"] = [dialog, main]
    assert wa.get_main_window(app) is main


def test_get_current_chat_name_uses_name_label(fake_ax, monkeypatch):
    main = make_main_window([], current_chat="Alice")
    app = make_app(main)
    assert wa.get_current_chat_name(app) == "Alice"


def test_visible_session_items_skip_rows_outside_viewport(fake_ax):
    inside = session_item("Alice", "hi", "16:00", y=256)
    partially = session_item("Bob", "yo", "15:00", y=1000)  # bottom edge 1065 > 1023
    main = make_main_window([inside, partially])
    session_list = main.find("session_list")
    items = wa._visible_session_items(session_list)
    assert set(items) == {"Alice"}


def test_find_chat_element_by_name_without_scroll(fake_ax, monkeypatch):
    main = make_main_window([session_item("Alice", "hi", "16:00", y=256)])
    app = make_app(main)
    assert wa.find_chat_element_by_name(app, "alice", scroll=False) is not None
    assert wa.find_chat_element_by_name(app, "Carol", scroll=False) is None


def _search_dialog(rows: list[tuple[str, str | None, float]]):
    children = [
        FakeElement(
            role="AXStaticText",
            title=text,
            identifier=identifier,
            position=(223.0, y),
            size=(320.0, 32.0),
        )
        for text, identifier, y in rows
    ]
    search_list = FakeElement(role="AXList", identifier="search_list", children=children,
                              position=(223.0, 220.0), size=(320.0, 765.0))
    return FakeElement(role="AXWindow", subrole="AXDialog", children=[search_list])


def test_search_entries_prefer_contacts_and_ignore_other_sections(fake_ax):
    dialog = _search_dialog(
        [
            ("Contacts", None, 220),
            ("Anna", "search_item_Anna", 252),
            ("View All(3)", None, 316),
            ("Group Chats", None, 350),
            ("Anna", "search_item_Anna", 382),
            ("Team Anna", "search_item_Team Anna", 446),
            ("Official Accounts", None, 510),
            ("Anna", "search_item_Anna", 542),
            ("Internet search results", None, 606),
            ("Anna", None, 638),
        ]
    )
    search_list = dialog.children[0]
    entries = wa._collect_search_entries(search_list)
    match = wa._find_exact_match_in_entries(entries, "Anna")
    assert match is search_list.children[1]  # the Contacts row
    candidates = wa._summarize_search_candidates(entries)
    assert candidates == {"contacts": ["Anna"], "group_chats": ["Anna", "Team Anna"]}


def test_search_entries_fall_back_to_group_chats(fake_ax):
    dialog = _search_dialog(
        [
            ("Group Chats", None, 220),
            ("Dev Team", "search_item_Dev Team", 252),
            ("Chat History", None, 316),
            ("Dev Team", None, 348),
        ]
    )
    entries = wa._collect_search_entries(dialog.children[0])
    assert wa._find_exact_match_in_entries(entries, "dev team") is dialog.children[0].children[1]
    assert wa._find_exact_match_in_entries(entries, "Dev") is None


def test_open_chat_refuses_when_search_opens_other_chat(fake_ax, monkeypatch):
    main = make_main_window([], current_chat="Someone Else")
    app = make_app(main)
    monkeypatch.setattr(wa, "get_wechat_ax_app", lambda activate=True: app)
    monkeypatch.setattr(wa, "close_search", lambda ax_app: None)
    monkeypatch.setattr(wa, "find_chat_element_by_name", lambda ax_app, name, scroll=True: None)
    monkeypatch.setattr(wa, "focus_and_type_search", lambda ax_app, text: None)
    monkeypatch.setattr(
        wa,
        "_select_contact_from_search_results",
        lambda ax_app, name: (True, {"contacts": ["Alice"], "group_chats": []}),
    )
    monkeypatch.setattr(wa.time, "sleep", lambda s: None)
    result = wa.open_chat_for_contact("Alice")
    assert result is not None and "different chat" in result["error"]
    assert result["opened_chat"] == "Someone Else"


def test_open_chat_returns_candidates_when_no_exact_match(fake_ax, monkeypatch):
    main = make_main_window([], current_chat="Someone Else")
    app = make_app(main)
    monkeypatch.setattr(wa, "get_wechat_ax_app", lambda activate=True: app)
    monkeypatch.setattr(wa, "close_search", lambda ax_app: None)
    monkeypatch.setattr(wa, "find_chat_element_by_name", lambda ax_app, name, scroll=True: None)
    monkeypatch.setattr(wa, "focus_and_type_search", lambda ax_app, text: None)
    monkeypatch.setattr(
        wa,
        "_select_contact_from_search_results",
        lambda ax_app, name: (False, {"contacts": ["Alice B"], "group_chats": []}),
    )
    result = wa.open_chat_for_contact("Alice")
    assert result["candidates"]["contacts"] == ["Alice B"]
