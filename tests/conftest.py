"""
Test fixtures: a fake Accessibility tree so the automation logic can be
exercised without WeChat, Accessibility permissions or a display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from wechat_mcp import wechat_accessibility as wa


@dataclass
class FakeElement:
    role: str = "AXGroup"
    title: str | None = None
    identifier: str | None = None
    value: Any = None
    description: str | None = None
    subrole: str | None = None
    position: tuple[float, float] | None = None
    size: tuple[float, float] | None = None
    children: list["FakeElement"] = field(default_factory=list)
    attrs: dict[str, Any] = field(default_factory=dict)

    def attribute(self, name: str):
        mapping = {
            "AXRole": self.role,
            "AXTitle": self.title,
            "AXIdentifier": self.identifier,
            "AXValue": self.value,
            "AXDescription": self.description,
            "AXSubrole": self.subrole,
            "AXPosition": self.position,
            "AXSize": self.size,
            "AXChildren": list(self.children),
        }
        if name in self.attrs:
            return self.attrs[name]
        return mapping.get(name)

    def find(self, identifier: str) -> "FakeElement | None":
        if self.identifier == identifier:
            return self
        for child in self.children:
            found = child.find(identifier)
            if found is not None:
                return found
        return None


def fake_copy_attribute(element, attribute, _out):
    if not isinstance(element, FakeElement):
        return -25200, None  # kAXErrorAttributeUnsupported
    value = element.attribute(attribute)
    if value is None:
        return -25205, None  # kAXErrorNoValue
    return 0, value


@pytest.fixture
def fake_ax(monkeypatch):
    """Route ax_get through FakeElement attributes."""
    monkeypatch.setattr(wa, "AXUIElementCopyAttributeValue", fake_copy_attribute)
    return FakeElement


def session_item(name: str, preview: str, when: str, muted: bool = False, y: float = 0.0):
    title = f"{name}\n{preview}\n{when}\n" + ("Mute Notifications\n" if muted else "")
    return FakeElement(
        role="AXStaticText",
        title=title,
        identifier=f"session_item_{name}",
        position=(470.0, y),
        size=(240.0, 65.0),
    )


def make_main_window(session_items: list[FakeElement], current_chat: str = "Alice"):
    session_list = FakeElement(
        role="AXList",
        title="Chats",
        identifier="session_list",
        position=(470.0, 256.0),
        size=(240.0, 767.0),
        children=session_items,
    )
    name_label = FakeElement(
        role="AXStaticText", identifier="current_chat_name_label", value=current_chat
    )
    title_line = FakeElement(
        role="AXStaticText",
        identifier="big_title_line_h_view",
        value=f"{current_chat}(5)",
        children=[name_label],
    )
    search = FakeElement(role="AXTextArea", title="Search", value="")
    splitter = FakeElement(
        identifier="main_window_main_splitter_view",
        children=[title_line, search, session_list],
    )
    return FakeElement(
        role="AXWindow",
        subrole="AXStandardWindow",
        title="WeChat",
        position=(410.0, 204.0),
        size=(1044.0, 823.0),
        children=[splitter],
    )


def make_app(main_window: FakeElement, extra_windows: list[FakeElement] | None = None):
    windows = [main_window, *(extra_windows or [])]
    return FakeElement(
        role="AXApplication",
        title="WeChat",
        children=windows,
        attrs={"AXWindows": windows},
    )
