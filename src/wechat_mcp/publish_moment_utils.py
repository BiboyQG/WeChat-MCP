from __future__ import annotations

import time
from typing import Any

from ApplicationServices import (
    kAXButtonRole,
    kAXDescriptionAttribute,
    kAXSheetRole,
    kAXTextAreaRole,
)

from .logging_config import logger
from .wechat_accessibility import (
    WINDOW_MENU_TITLES,
    _find_window_by_title,
    _press_menu_item,
    _wait_for_window,
    ax_get,
    click_element_center,
    dfs,
    element_frame,
    ensure_chats_tab,
    find_by_identifier,
    get_main_window,
    get_wechat_ax_app,
    long_press_element_center,
)

ID_MOMENTS_LIST = "sns_list"
MOMENTS_TITLES = ("Moments", "朋友圈")
DISCOVER_TAB_TITLES = ("Discover", "发现")
POST_BUTTON_TITLES = ("Post", "发表")
CANCEL_BUTTON_TITLES = ("Cancel", "取消")


def _wait_for(predicate, timeout: float, interval: float = 0.1):
    end = time.time() + timeout
    while time.time() < end:
        result = predicate()
        if result is not None:
            return result
        time.sleep(interval)
    return None


def _open_moments_window(ax_app: Any, timeout: float = 5.0) -> Any:
    """
    Show Moments and return the AX element that hosts the Moments UI.

    WeChat 4.x renders Moments inside the main window (Discover tab), so
    the main window is returned once its ``sns_list`` appears. Older
    clients opened a separate "Moments" window, which is handled as a
    fallback.
    """
    main_window = get_main_window(ax_app)

    def moments_root():
        if find_by_identifier(main_window, ID_MOMENTS_LIST) is not None:
            return main_window
        for title in MOMENTS_TITLES:
            window = _find_window_by_title(ax_app, title)
            if window is not None and window is not main_window:
                return window
        return None

    root = moments_root()
    if root is not None:
        return root

    # Preferred: Window menu -> Moments (works from any tab).
    if _press_menu_item(ax_app, WINDOW_MENU_TITLES, MOMENTS_TITLES):
        logger.info("Opened Moments via the Window menu")
        root = _wait_for(moments_root, timeout)
        if root is not None:
            return root

    # Fallback: Discover tab -> Moments entry.
    win_frame = element_frame(main_window)

    def is_discover_tab(el, role, title, identifier):
        if role != kAXButtonRole or title not in DISCOVER_TAB_TITLES:
            return False
        frame = element_frame(el)
        return frame is not None and win_frame is not None and frame[0] - win_frame[0] < 80

    discover = dfs(main_window, is_discover_tab)
    if discover is not None:
        click_element_center(discover)
        time.sleep(0.6)

        def is_moments_entry(el, role, title, identifier):
            return role == kAXButtonRole and title in MOMENTS_TITLES

        entry = dfs(main_window, is_moments_entry)
        if entry is not None:
            logger.info("Clicking 'Moments' entry in the Discover tab")
            click_element_center(entry)
            root = _wait_for(moments_root, timeout)
            if root is not None:
                return root

    # Legacy (WeChat 3.x): a "Moments" button in the main window opens a window.
    def is_moments_button(el, role, title, identifier):
        return role == kAXButtonRole and title in MOMENTS_TITLES

    button = dfs(main_window, is_moments_button)
    if button is not None:
        click_element_center(button)
        for title in MOMENTS_TITLES:
            window = _wait_for_window(ax_app, title, timeout=timeout)
            if window is not None:
                return window

    raise RuntimeError("Could not open Moments in WeChat")


def _find_moments_post_button(root: Any):
    """
    Locate the toolbar "Post" (camera) button of the Moments page, i.e.
    the one that is not part of a composer sheet.
    """

    def is_post_button(el, role, title, identifier):
        if role != kAXButtonRole or title not in POST_BUTTON_TITLES:
            return False
        description = ax_get(el, kAXDescriptionAttribute)
        # In WeChat 4.x the toolbar button carries description "Post";
        # the composer's confirm button has no description.
        return description in POST_BUTTON_TITLES or description is None

    return dfs(root, is_post_button)


def _open_moment_composer(root: Any) -> None:
    """
    Open the Moments composer sheet by long-pressing the Post button
    (a short click would open the photo picker instead).
    """
    button = _find_moments_post_button(root)
    if button is None:
        raise RuntimeError("Could not find 'Post' button in Moments")

    logger.info("Long-pressing 'Post' button to open composer sheet")
    long_press_element_center(button, hold_seconds=1.5)
    time.sleep(0.3)


def _find_moments_sheet(root: Any, timeout: float = 5.0) -> Any | None:
    """
    Wait for the Moments composer sheet to appear inside ``root``.
    """

    def is_sheet(el, role, title, identifier):
        return role == kAXSheetRole

    sheet = _wait_for(lambda: dfs(root, is_sheet), timeout)
    if sheet is None:
        logger.warning("Timed out waiting for Moments composer sheet")
    return sheet


def _find_editor_root(root: Any, timeout: float = 5.0) -> Any | None:
    """
    Return the element that contains the Moments composer controls.
    """
    sheet = _find_moments_sheet(root, timeout=timeout)
    if sheet is not None:
        return sheet
    logger.warning("Composer sheet not found; falling back to the Moments root")
    return root


def _find_moment_text_area(editor_root: Any) -> Any | None:
    def is_text_area(el, role, title, identifier):
        return role == kAXTextAreaRole

    return dfs(editor_root, is_text_area)


def _find_post_button_in_editor(editor_root: Any) -> Any | None:
    def is_post_button(el, role, title, identifier):
        return role == kAXButtonRole and title in POST_BUTTON_TITLES

    return dfs(editor_root, is_post_button)


def publish_moment_without_media(content: str, publish: bool = True) -> dict[str, Any]:
    """
    Publish a Moments post containing only text (no media).

    High-level flow:
    - Show Moments (Window menu -> Moments, or Discover -> Moments).
    - Long-press the toolbar "Post" button to reveal the text composer.
    - Set the composer text area's value to the provided content.
    - If `publish` is True (default), click the composer's "Post" button
      and wait for the sheet to close; if False, leave the composer open
      so the user can review the draft.
    """
    if not isinstance(content, str) or not content.strip():
        return {
            "error": "content must be a non-empty string",
            "content": content,
            "stage": "validate_input",
        }

    logger.info(
        "Starting publish_moment_without_media (content_length=%d, publish=%s)",
        len(content),
        publish,
    )

    try:
        ax_app = get_wechat_ax_app()
        moments_root = _open_moments_window(ax_app)
        _open_moment_composer(moments_root)

        editor_root = _find_editor_root(moments_root, timeout=5.0)
        text_area = _find_moment_text_area(editor_root)
        if text_area is None:
            error_msg = "Could not find text entry area in Moments composer"
            logger.warning(error_msg)
            return {"error": error_msg, "content": content, "stage": "text_area"}

        from .wechat_accessibility import set_text_value

        if not set_text_value(text_area, content):
            error_msg = "Failed to set composer text"
            logger.warning(error_msg)
            return {"error": error_msg, "content": content, "stage": "set_text"}

        if not publish:
            logger.info(
                "Moments composer text updated; publish=False so skipping Post click"
            )
            return {"content": content, "posted": False}

        post_button = _find_post_button_in_editor(editor_root)
        if post_button is None:
            error_msg = "Could not find 'Post' button in Moments composer"
            logger.warning(error_msg)
            return {"error": error_msg, "content": content, "stage": "post_button"}

        logger.info("Clicking Post in the Moments composer")
        click_element_center(post_button)

        def sheet_gone():
            def is_sheet(el, role, title, identifier):
                return role == kAXSheetRole

            return True if dfs(moments_root, is_sheet) is None else None

        if _wait_for(sheet_gone, timeout=8.0) is None:
            logger.warning("Composer sheet still open after clicking Post")
            return {
                "error": "Composer sheet did not close after clicking Post",
                "content": content,
                "stage": "post_confirm",
            }

        # Return to the Chats tab so subsequent chat tools work immediately.
        try:
            ensure_chats_tab(ax_app)
        except RuntimeError as exc:
            logger.debug("Could not switch back to Chats tab: %s", exc)

        logger.info("Moments post submitted successfully")
        return {"content": content, "posted": True}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error while publishing moment without media: %s", exc)
        return {"error": str(exc), "content": content, "stage": "unexpected_error"}
