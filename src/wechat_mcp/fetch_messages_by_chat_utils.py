from __future__ import annotations

import re
import time
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Literal

from ApplicationServices import (
    kAXChildrenAttribute,
    kAXIdentifierAttribute,
    kAXListRole,
    kAXTitleAttribute,
)
from PIL import Image

from .capture import (
    capture_screen_region,
    capture_window_region,
    find_window_id,
    looks_blank,
    recognize_text,
)
from .logging_config import logger
from .wechat_accessibility import (
    ID_MESSAGE_LIST,
    ID_SESSION_ITEM_PREFIX,
    activate_wechat,
    ax_get,
    dfs,
    element_frame,
    element_text,
    ensure_chats_tab,
    find_by_identifier,
    get_current_chat_name,
    get_list_center,
    get_main_window,
    get_session_list,
    get_wechat_ax_app,
    get_wechat_pid,
    post_scroll,
)

ID_MESSAGE_BUBBLE = "chat_bubble_item_view"
ID_CHAT_COUNT_LABEL = "current_chat_count_label"
MESSAGE_LIST_TITLES = ("Messages", "消息")

SenderLabel = Literal["ME", "OTHER", "SYSTEM", "UNKNOWN"]

# Pixels ignored at the edges of the message list when measuring bubbles.
SCROLLBAR_MARGIN_LEFT = 2
SCROLLBAR_MARGIN_RIGHT = 10
MessageKind = Literal[
    "text", "image", "file", "video", "sticker", "voice", "link", "card", "system"
]


def get_messages_list(ax_app: Any) -> Any:
    """
    Find the AX list that contains chat messages in the main WeChat window.
    """
    main_window = ensure_chats_tab(ax_app)

    def is_message_list(el, role, title, identifier):
        return role == kAXListRole and (
            identifier == ID_MESSAGE_LIST or (title or "") in MESSAGE_LIST_TITLES
        )

    msg_list = dfs(main_window, is_message_list)
    if msg_list is None:
        raise RuntimeError("Could not find WeChat 'Messages' list in AX tree")
    return msg_list


def is_group_chat(ax_app: Any) -> bool:
    """WeChat shows a "(N)" member count next to group chat titles."""
    main_window = get_main_window(ax_app)
    label = find_by_identifier(main_window, ID_CHAT_COUNT_LABEL)
    if label is None:
        return False
    value = element_text(label) or ""
    return bool(re.fullmatch(r"\(\d+\)", value.strip()))


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------


class MessageAreaCapturer:
    """
    Captures the message list region, preferring a window-server capture
    (works while WeChat is behind other windows) and falling back to a
    screen grab.
    """

    def __init__(self, ax_app: Any, msg_list: Any):
        self.ax_app = ax_app
        self.msg_list = msg_list
        self.main_window = get_main_window(ax_app)
        self.window_id: int | None = None
        self.uses_window_capture = True
        try:
            self.window_id = find_window_id(get_wechat_pid(), element_frame(self.main_window))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not resolve WeChat window id: %s", exc)

    def capture(self) -> tuple[Image.Image, tuple[float, float], tuple[float, float]]:
        frame = element_frame(self.msg_list)
        if frame is None:
            raise RuntimeError("Failed to get bounds for WeChat messages list")
        x, y, w, h = frame
        image: Image.Image | None = None
        if self.uses_window_capture and self.window_id is not None:
            window_frame = element_frame(self.main_window)
            if window_frame is not None:
                image = capture_window_region(self.window_id, window_frame, frame)
            if image is None or looks_blank(image):
                logger.info(
                    "Window capture unavailable (Screen Recording permission?); "
                    "falling back to screen grab"
                )
                self.uses_window_capture = False
                image = None
        if image is None:
            activate_wechat()
            time.sleep(0.2)
            image = capture_screen_region(frame)
        return image, (x, y), (w, h)


def capture_message_area(msg_list: Any):
    """
    Backwards compatible helper: capture the visible message area and
    return the image together with the list origin and size (points).
    """
    image = capture_screen_region(element_frame(msg_list))
    frame = element_frame(msg_list)
    return image, (frame[0], frame[1]), (frame[2], frame[3])


# ---------------------------------------------------------------------------
# Scrolling
# ---------------------------------------------------------------------------


def _visible_row_texts(msg_list: Any) -> list[str]:
    texts: list[str] = []
    for child in ax_get(msg_list, kAXChildrenAttribute) or []:
        txt = element_text(child)
        if txt:
            texts.append(txt)
    return texts


def scroll_to_bottom(msg_list: Any, center: tuple[float, float]) -> None:
    """
    Scroll the messages list to the bottom (newest messages) by repeatedly
    sending large negative scroll events until the last visible message
    stabilizes.
    """
    last_text: str | None = None
    stable = 0

    for _ in range(40):
        post_scroll(center, -1000)
        time.sleep(0.05)

        texts = _visible_row_texts(msg_list)
        if not texts:
            continue

        new_last = texts[-1]
        if new_last == last_text:
            stable += 1
            if stable >= 3:
                break
        else:
            last_text = new_last
            stable = 0

    time.sleep(0.2)


def scroll_up_small(center: tuple[float, float]) -> None:
    """
    Scroll slightly upwards to reveal older messages.
    """
    post_scroll(center, 50)
    time.sleep(0.15)


# ---------------------------------------------------------------------------
# Sender classification
# ---------------------------------------------------------------------------


def estimate_background(image) -> tuple[int, int, int]:
    """
    Estimate the chat background colour as the most common colour in the
    capture. Works for both the light and the dark theme.
    """
    pixels = image.load()
    counter: Counter = Counter()
    for y in range(0, image.height, 3):
        for x in range(0, image.width, 3):
            counter[pixels[x, y]] += 1
    if not counter:
        return (250, 250, 250)
    return counter.most_common(1)[0][0]


def _is_background(pixel, background, tolerance: int = 6) -> bool:
    return (
        abs(pixel[0] - background[0]) <= tolerance
        and abs(pixel[1] - background[1]) <= tolerance
        and abs(pixel[2] - background[2]) <= tolerance
    )


def _is_wechat_green(pixel) -> bool:
    r, g, b = pixel
    return g > 90 and g > r + 25 and g > b + 25


def classify_sender_for_message(
    image,
    list_origin,
    message_pos,
    message_size,
    background: tuple[int, int, int] | None = None,
) -> SenderLabel:
    """
    Classify a message bubble as sent by ME or by the OTHER side.

    WeChat 4.x exposes every bubble row as a full-width element, so the
    AX geometry alone does not reveal the sender. The screenshot is
    sampled along a few rows of the bubble: rows from the other party hug
    the left edge (avatar + bubble) while the user's own rows hug the
    right edge. The distance from each edge to the first non-background
    pixel decides the side; WeChat's green bubble colour breaks ties.
    """
    list_x, list_y = list_origin
    msg_x, msg_y = message_pos
    msg_w, msg_h = message_size

    if background is None:
        background = estimate_background(image)

    rel_top = max(0.0, msg_y - list_y)
    rel_bottom = min(float(image.height), msg_y - list_y + msg_h)
    if rel_bottom - rel_top < 8:
        return "UNKNOWN"

    pixels = image.load()
    width = image.width
    rows = 5
    span = rel_bottom - rel_top
    sample_rows = [int(rel_top + span * (i + 1) / (rows + 1)) for i in range(rows)]

    # WeChat paints an overlay scrollbar along the right edge of the list;
    # ignore that strip (and a hairline on the left) so it never counts
    # as bubble content.
    x_start = SCROLLBAR_MARGIN_LEFT
    x_end = max(x_start + 1, width - SCROLLBAR_MARGIN_RIGHT)

    leftmost = width
    rightmost = -1
    non_background = 0
    green = 0
    for ry in sample_rows:
        if ry < 0 or ry >= image.height:
            continue
        for rx in range(x_start, x_end):
            px = pixels[rx, ry]
            if _is_background(px, background):
                continue
            non_background += 1
            leftmost = min(leftmost, rx)
            rightmost = max(rightmost, rx)
            if _is_wechat_green(px):
                green += 1

    if non_background < 20 or rightmost < 0:
        return "UNKNOWN"

    left_margin = leftmost - x_start
    right_margin = (x_end - 1) - rightmost

    if left_margin + 15 < right_margin:
        return "OTHER"
    if right_margin + 15 < left_margin:
        return "ME"
    if green >= non_background * 0.25:
        return "ME"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Message kinds and sender names
# ---------------------------------------------------------------------------

# Bubble titles WeChat 4.x uses for non-text messages.
_EXACT_KINDS: dict[str, MessageKind] = {
    "Image": "image",
    "Video": "video",
    "Sticker": "sticker",
    "Voice": "voice",
}
# Prefixes that need a following separator ("\n", " " or end of text) so
# that ordinary sentences such as "Images are ready" stay text.
_WORD_PREFIXES: tuple[tuple[str, MessageKind], ...] = (
    ("File", "file"),
    ("Image", "image"),
    ("Video", "video"),
    ("Voice", "voice"),
    ("Sticker", "sticker"),
    ("Animated Stickers", "sticker"),
    ("Mini Program", "card"),
    ("Contact Card", "card"),
)
# Prefixes that can be glued to the payload ("ChannelsWHEAT-Mia").
_RAW_PREFIXES: tuple[tuple[str, MessageKind], ...] = (
    ("[File]", "file"),
    ("[Photo]", "image"),
    ("[Image]", "image"),
    ("[Video]", "video"),
    ("[Sticker]", "sticker"),
    ("[Voice]", "voice"),
    ("[Link]", "link"),
    ("Channels", "link"),
    ("[图片]", "image"),
    ("[视频]", "video"),
    ("[动画表情]", "sticker"),
    ("[语音]", "voice"),
    ("[文件]", "file"),
    ("[链接]", "link"),
)


def message_kind(text: str, sender: SenderLabel) -> MessageKind:
    if sender == "SYSTEM":
        return "system"
    stripped = text.strip()
    if stripped in _EXACT_KINDS:
        return _EXACT_KINDS[stripped]
    for prefix, kind in _WORD_PREFIXES:
        if stripped.startswith(prefix) and (
            len(stripped) == len(prefix) or stripped[len(prefix)] in ("\n", " ", "\u00a0")
        ):
            return kind
    for prefix, kind in _RAW_PREFIXES:
        if stripped.startswith(prefix):
            return kind
    if re.match(r"https?://\S+$", stripped):
        return "link"
    return "text"


# Sender name label: painted above the bubble, right of the avatar.
_NAME_STRIP_TOP = 2.0
_NAME_STRIP_HEIGHT = 30.0
_NAME_STRIP_LEFT = 58.0
_NAME_STRIP_WIDTH_RATIO = 0.7


def read_group_sender_name(
    image: Image.Image, list_origin, message_pos, message_size
) -> str | None:
    """
    OCR the sender-name strip above an incoming bubble in a group chat.
    """
    list_x, list_y = list_origin
    msg_x, msg_y = message_pos
    msg_w, msg_h = message_size
    top = msg_y - list_y + _NAME_STRIP_TOP
    bottom = top + _NAME_STRIP_HEIGHT
    if top < 0 or bottom > image.height or msg_h < _NAME_STRIP_HEIGHT + 20:
        return None
    left = _NAME_STRIP_LEFT
    right = min(image.width, left + msg_w * _NAME_STRIP_WIDTH_RATIO)
    strip = image.crop((int(left), int(top), int(right), int(bottom)))
    lines = recognize_text(strip)
    if not lines:
        return None
    name = lines[0].strip()
    return name or None


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


@dataclass
class ChatMessage:
    sender: SenderLabel
    text: str
    kind: MessageKind = "text"
    sender_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _collect_visible_messages(
    msg_list: Any,
    capturer: MessageAreaCapturer,
    group_chat: bool,
    chat_name: str | None,
) -> list[ChatMessage]:
    """
    Collect the rows currently rendered in the message list, classifying
    message bubbles by sender and marking timestamps / system notices as
    SYSTEM rows.
    """
    image, list_origin, _ = capturer.capture()
    background = estimate_background(image)

    visible: list[ChatMessage] = []
    for child in ax_get(msg_list, kAXChildrenAttribute) or []:
        text = element_text(child)
        if not text:
            continue

        identifier = ax_get(child, kAXIdentifierAttribute)
        if identifier != ID_MESSAGE_BUBBLE:
            visible.append(ChatMessage(sender="SYSTEM", text=str(text), kind="system"))
            continue

        frame = element_frame(child)
        sender: SenderLabel = "UNKNOWN"
        sender_name: str | None = None
        if frame is not None:
            pos, size = (frame[0], frame[1]), (frame[2], frame[3])
            sender = classify_sender_for_message(image, list_origin, pos, size, background)
            if sender == "OTHER":
                if group_chat:
                    sender_name = read_group_sender_name(image, list_origin, pos, size)
                else:
                    sender_name = chat_name
        visible.append(
            ChatMessage(
                sender=sender,
                text=str(text),
                kind=message_kind(str(text), sender),
                sender_name=sender_name,
            )
        )
    return visible


def _merge_older(visible: list[ChatMessage], messages: list[ChatMessage]) -> list[ChatMessage]:
    """
    Return the rows of ``visible`` that precede the already-known
    ``messages`` by finding the longest overlap between the tail of
    ``visible`` and the head of ``messages``.
    """
    visible_texts = [m.text for m in visible]
    known_texts = [m.text for m in messages]
    max_k = min(len(visible_texts), len(known_texts))
    for k in range(max_k, 0, -1):
        if visible_texts[-k:] == known_texts[:k]:
            return visible[: len(visible) - k]
    return visible


def _preview_matches_last_message(ax_app: Any, chat_name: str | None, last_text: str) -> bool:
    """
    Decide whether the list is already scrolled to the newest message by
    comparing the session row preview with the last visible bubble.
    """
    if not chat_name:
        return False
    try:
        session_list = get_session_list(get_main_window(ax_app))
    except RuntimeError:
        return False
    for child in ax_get(session_list, kAXChildrenAttribute) or []:
        identifier = ax_get(child, kAXIdentifierAttribute) or ""
        if identifier != f"{ID_SESSION_ITEM_PREFIX}{chat_name}":
            continue
        title = ax_get(child, kAXTitleAttribute) or ""
        preview = " ".join(title.split("\n")[1:2]).strip()
        return preview_matches_text(preview, last_text)
    return False


def _normalize_for_match(text: str) -> str:
    return "".join(ch for ch in text.casefold() if ch.isalnum())


def preview_matches_text(preview: str, bubble_text: str) -> bool:
    """
    Heuristic match between a session-row preview ("[Sticker] Thank You",
    "Sender: text", "[File] name.pdf") and the text of a bubble.
    """
    p = _normalize_for_match(preview)
    b = _normalize_for_match(bubble_text)
    if len(p) < 4 or len(b) < 4:
        return False
    tail = 6
    return p[-tail:] in b or b[-tail:] in p or b[:10] in p


def fetch_recent_messages(
    last_n: int = 100,
    max_scrolls: int | None = None,
    allow_background: bool = True,
) -> list[ChatMessage]:
    """
    Fetch the true last N rows from the currently open chat, even when the
    history spans multiple screens.

    Strategy:
    - Read the rows that are rendered right now. When they already cover
      ``last_n`` and the session preview confirms the list is at the
      newest message, return without bringing WeChat to the front.
    - Otherwise activate WeChat, scroll to the bottom, and repeatedly
      scroll upwards in small steps, merging newly revealed older rows at
      the front by aligning on the overlap with already-known rows.
    - Bubbles are classified as ME/OTHER/UNKNOWN from a capture of the
      window; timestamps / notices are marked SYSTEM. In group chats the
      sender name above incoming bubbles is recovered with OCR.
    """
    ax_app = get_wechat_ax_app(activate=False)
    msg_list = get_messages_list(ax_app)
    chat_name = get_current_chat_name(ax_app)
    group_chat = is_group_chat(ax_app)
    capturer = MessageAreaCapturer(ax_app, msg_list)

    if allow_background:
        visible = _collect_visible_messages(msg_list, capturer, group_chat, chat_name)
        bubbles = [m for m in visible if m.sender != "SYSTEM"]
        if visible and len(bubbles) >= last_n and _preview_matches_last_message(
            ax_app, chat_name, bubbles[-1].text
        ):
            logger.info(
                "Fetched %d rows without activating WeChat (requested last_n=%d)",
                len(visible),
                last_n,
            )
            return visible[-last_n:] if len(visible) > last_n else visible

    activate_wechat()
    center = get_list_center(msg_list)
    scroll_to_bottom(msg_list, center)

    messages: list[ChatMessage] = []
    scrolls = 0
    no_new_counter = 0

    while True:
        visible = _collect_visible_messages(msg_list, capturer, group_chat, chat_name)
        if not visible:
            break

        if not messages:
            messages = visible
        else:
            new_older = _merge_older(visible, messages)
            if new_older:
                messages = new_older + messages
                no_new_counter = 0
            else:
                no_new_counter += 1
                if no_new_counter >= 5:
                    break

        if len(messages) >= last_n:
            break

        scroll_up_small(center)

        scrolls += 1
        if max_scrolls is not None and scrolls >= max_scrolls:
            break

    if len(messages) > last_n:
        messages = messages[-last_n:]

    logger.info(
        "Fetched %d rows from current chat (requested last_n=%d)",
        len(messages),
        last_n,
    )
    return messages
