from __future__ import annotations

import time
from typing import Any

from ApplicationServices import (
    AXUIElementSetAttributeValue,
    kAXButtonRole,
    kAXCheckBoxRole,
    kAXChildrenAttribute,
    kAXPositionAttribute,
    kAXRoleAttribute,
    kAXStaticTextRole,
    kAXTextAreaRole,
    kAXTextFieldRole,
    kAXValueAttribute,
)

from .logging_config import logger
from .wechat_accessibility import (
    _wait_for_window,
    _collect_search_entries,
    ax_get,
    axvalue_to_point,
    click_element_center,
    dfs,
    focus_and_type_search,
    get_search_list,
    get_wechat_ax_app,
)


def _click_more_card_by_title(ax_app: Any, label: str) -> bool:
    """
    Click a card with the given label in the global search results list.

    This reuses the same search-entry collection logic as
    _select_contact_from_search_results but targets entries by their
    visible text only (e.g. a card labeled "Search WeChat ID").
    """
    search_list = get_search_list(ax_app)
    entries = _collect_search_entries(search_list)

    target = label.strip()
    for entry in entries:
        text = entry.text
        if not text:
            continue
        if text == target or text.startswith(f"{target}:"):
            logger.info("Clicking %r entry in search results", text)
            click_element_center(entry.element)
            time.sleep(0.4)
            return True

    logger.warning("Did not find %r entry in search results", target)
    return False


def _click_add_to_contacts_button(add_contacts_window) -> None:
    """
    Click the 'Add to Contacts' button inside the Add Contacts window.
    """

    def is_add_button(el, role, title, identifier):
        if role != kAXButtonRole:
            return False
        if identifier == "add_friend_button":
            return True
        if isinstance(title, str) and title == "Add to Contacts":
            return True
        return False

    button = dfs(add_contacts_window, is_add_button)
    if button is None:
        raise RuntimeError(
            "Could not find 'Add to Contacts' button in Add Contacts window"
        )

    logger.info("Clicking 'Add to Contacts' button")
    click_element_center(button)
    time.sleep(0.4)


def _set_checkbox_state(checkbox, desired: bool) -> None:
    current = ax_get(checkbox, kAXValueAttribute)
    current_bool = bool(current)
    if current_bool == desired:
        return

    click_element_center(checkbox)
    time.sleep(0.2)


def _set_checkbox_by_title(window, title: str, desired: bool) -> None:
    """
    Set an AXCheckBox with the given title to the desired checked state.
    """

    def is_checkbox(el, role, checkbox_title, identifier):
        return (
            role == kAXCheckBoxRole
            and isinstance(checkbox_title, str)
            and checkbox_title == title
        )

    checkbox = dfs(window, is_checkbox)
    if checkbox is None:
        logger.warning("Could not find checkbox with title %r", title)
        return

    _set_checkbox_state(checkbox, desired)


def _click_privacy_option(window, label: str) -> None:
    """
    Click the radio/button control associated with the given privacy
    label ("Chats, Moments, WeRun, etc." or "Chats Only").
    """

    def is_label(el, role, title, identifier):
        if role != kAXStaticTextRole:
            return False
        value = ax_get(el, kAXValueAttribute)
        return isinstance(value, str) and value == label

    label_el = dfs(window, is_label)
    if label_el is None:
        logger.warning("Could not find privacy label %r", label)
        return

    pos_ref = ax_get(label_el, kAXPositionAttribute)
    point = axvalue_to_point(pos_ref)
    if point is None:
        logger.warning("Could not get position for privacy label %r", label)
        return

    label_x, label_y = point

    # Find the small button to the left of the label on the same row.
    best_button = None
    best_dx = None

    def consider_button(el):
        nonlocal best_button, best_dx
        role = ax_get(el, kAXRoleAttribute)
        if role != kAXButtonRole:
            return
        pos_ref_btn = ax_get(el, kAXPositionAttribute)
        point_btn = axvalue_to_point(pos_ref_btn)
        if point_btn is None:
            return
        btn_x, btn_y = point_btn
        if abs(btn_y - label_y) > 6.0:
            return
        if btn_x >= label_x:
            return
        dx = label_x - btn_x
        if best_dx is None or dx < best_dx:
            best_dx = dx
            best_button = el

    def walk(el):
        consider_button(el)
        children = ax_get(el, kAXChildrenAttribute) or []
        for child in children:
            walk(child)

    walk(window)

    if best_button is None:
        logger.warning("Could not find button for privacy label %r", label)
        return

    logger.info("Clicking privacy option %r", label)
    click_element_center(best_button)
    time.sleep(0.2)


def _configure_friend_request_window(
    window,
    friending_msg: str | None,
    remark: str | None,
    tags: str | None,
    privacy: str | None,
    hide_my_posts: bool,
    hide_their_posts: bool,
) -> str:
    """
    Configure the 'Send Friend Request' window before sending.

    Returns the normalized privacy mode that was applied.
    """
    # Friending message
    if friending_msg is not None:

        def is_message_area(el, role, title, identifier):
            return (
                role == kAXTextAreaRole
                and isinstance(title, str)
                and title == "Send Friend Request"
            )

        msg_area = dfs(window, is_message_area)
        if msg_area is None:
            logger.warning("Could not find friending message text area")
        else:
            err = AXUIElementSetAttributeValue(
                msg_area, kAXValueAttribute, friending_msg
            )
            if err != 0:
                logger.warning("Failed to set friending message text, AX error %s", err)
            else:
                logger.info("Updated friending message text")

    # Remark
    if remark is not None:

        def is_remark_field(el, role, title, identifier):
            return (
                role == kAXTextFieldRole
                and isinstance(title, str)
                and title == "ModifyRemark"
            )

        remark_field = dfs(window, is_remark_field)
        if remark_field is None:
            logger.warning("Could not find remark text field")
        else:
            err = AXUIElementSetAttributeValue(remark_field, kAXValueAttribute, remark)
            if err != 0:
                logger.warning("Failed to set remark text, AX error %s", err)
            else:
                logger.info("Updated remark text")

    if tags is not None:
        # Placeholder for future tag editing support.
        logger.info("Tags argument provided but tag editing is not implemented yet")

    # Privacy + posts visibility
    privacy_mode = (privacy or "all").strip().lower()
    if privacy_mode in ("chats_only", "chats-only", "chats only"):
        _click_privacy_option(window, "Chats Only")
        logger.info("Privacy set to Chats Only")
    else:
        privacy_mode = "all"
        _click_privacy_option(window, "Chats, Moments, WeRun, etc.")
        logger.info("Privacy set to Chats, Moments, WeRun, etc.")

        # Only apply hide flags when allowing Moments/Status visibility.
        _set_checkbox_by_title(window, "Hide My Posts", hide_my_posts)
        _set_checkbox_by_title(window, "Hide Their Posts", hide_their_posts)

    return privacy_mode


def add_contact_by_wechat_id(
    wechat_id: str,
    friending_msg: str | None = None,
    remark: str | None = None,
    tags: str | None = None,
    privacy: str | None = None,
    hide_my_posts: bool = False,
    hide_their_posts: bool = False,
) -> dict[str, Any]:
    """
    Add a contact by WeChat ID using WeChat's global search and the
    "Add Contacts" / "Send Friend Request" windows.

    High-level flow:
    - Use the global search box to search for the given wechat_id.
    - In the search results, click the "Search WeChat ID" card.
    - In the "Add Contacts" window, click the "Add to Contacts" button.
    - In the "Send Friend Request" window, optionally customize the
      friending message, remark and privacy options, then click "OK".

    The privacy argument controls which option is selected in the
    "Privacy" section:
    - "all" (default) selects "Chats, Moments, WeRun, etc." and applies
      the hide_my_posts / hide_their_posts flags.
    - "chats_only" selects "Chats Only" and ignores the hide flags.
    """
    logger.info("Starting add_contact_by_wechat_id for ID=%s", wechat_id)
    try:
        ax_app = get_wechat_ax_app()

        # Step 1: global search
        logger.info("Typing WeChat ID into global search")
        focus_and_type_search(ax_app, wechat_id)
        time.sleep(0.4)

        # Step 2: click "Search WeChat ID" card in More section
        if not _click_more_card_by_title(ax_app, "Search WeChat ID"):
            error_msg = (
                "Could not find a 'Search WeChat ID' entry in the "
                "More section of WeChat's global search results."
            )
            logger.warning(
                "add_contact_by_wechat_id(%s) failed at Search WeChat ID step",
                wechat_id,
            )
            return {
                "error": error_msg,
                "wechat_id": wechat_id,
                "stage": "search_wechat_id",
            }

        # Step 3a: Add Contacts window
        add_window = _wait_for_window(ax_app, "Add Contacts", timeout=5.0)
        if add_window is None:
            error_msg = (
                "The 'Add Contacts' window did not appear after selecting "
                "Search WeChat ID."
            )
            return {
                "error": error_msg,
                "wechat_id": wechat_id,
                "stage": "add_contacts_window",
            }

        # Wait a moment for the button to appear
        time.sleep(2)

        # Step 3b: Click "Add to Contacts" button
        try:
            _click_add_to_contacts_button(add_window)
        except RuntimeError as e:
            return {
                "error": str(e),
                "wechat_id": wechat_id,
                "stage": "click_add_to_contacts_button",
            }

        # Step 4: Send Friend Request window
        request_window = _wait_for_window(ax_app, "Send Friend Request", timeout=5.0)
        if request_window is None:
            error_msg = (
                "The 'Send Friend Request' window did not appear after "
                "clicking 'Add to Contacts'."
            )
            return {
                "error": error_msg,
                "wechat_id": wechat_id,
                "stage": "send_friend_request_window",
            }

        applied_privacy = _configure_friend_request_window(
            request_window,
            friending_msg=friending_msg,
            remark=remark,
            tags=tags,
            privacy=privacy,
            hide_my_posts=hide_my_posts,
            hide_their_posts=hide_their_posts,
        )

        # Final step: click OK

        def is_ok_button(el, role, title, identifier):
            return role == kAXButtonRole and isinstance(title, str) and title == "OK"

        ok_button = dfs(request_window, is_ok_button)
        if ok_button is None:
            error_msg = "Could not find 'OK' button in Send Friend Request window."
            logger.warning(error_msg)
            return {
                "error": error_msg,
                "wechat_id": wechat_id,
                "stage": "confirm_request",
            }

        logger.info("Clicking 'OK' to send friend request")
        try:
            click_element_center(ok_button)
            time.sleep(0.4)
        except RuntimeError as e:
            return {
                "error": f"Failed to click OK button: {e}",
                "wechat_id": wechat_id,
                "stage": "click_ok_button",
            }

        result: dict[str, Any] = {
            "wechat_id": wechat_id,
            "friending_msg": friending_msg,
            "remark": remark,
            "tags": tags,
            "privacy": applied_privacy,
        }
        if applied_privacy == "all":
            result["hide_my_posts"] = hide_my_posts
            result["hide_their_posts"] = hide_their_posts

        logger.info("Friend request flow completed for ID=%s", wechat_id)
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Error while adding contact by WeChat ID %s: %s", wechat_id, exc
        )
        return {
            "error": str(exc),
            "wechat_id": wechat_id,
        }
