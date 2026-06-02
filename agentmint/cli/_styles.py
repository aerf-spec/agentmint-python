"""Centralized CLI styling helpers."""

from __future__ import annotations

import os
import sys
from typing import Any, List, Optional

RichConsole: Any = None
RichTheme: Any = None

try:
    from rich.console import Console as _RichConsole
    from rich.theme import Theme as _RichTheme

    RichConsole = _RichConsole
    RichTheme = _RichTheme
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

THEME = (
    RichTheme(
        {
            "primary": "#E2E8F0",
            "secondary": "#94A3B8",
            "dim": "#64748B",
            "blue": "#3B82F6",
            "green": "#10B981",
            "red": "#EF4444",
            "yellow": "#FBBF24",
            "border": "#1E293B",
            "surface": "#151D2E",
            "brand.agent": "#3B82F6",
            "brand.mint": "#E2E8F0",
            "success": "#10B981",
            "error": "#EF4444",
            "warning": "#FBBF24",
            "info": "#94A3B8",
        }
    )
    if _HAS_RICH
    else None
)

_NO_COLOR = False
_CONSOLE: Optional[Any] = (
    RichConsole(theme=THEME) if _HAS_RICH and RichConsole is not None else None
)
_FIRST_HEADING = True

BLUE = "\033[38;2;59;130;246m"
GREEN = "\033[38;2;16;185;129m"
RED = "\033[38;2;239;68;68m"
YELLOW = "\033[38;2;251;191;36m"
FG = "\033[38;2;226;232;240m"
SEC = "\033[38;2;148;163;184m"
DIM = "\033[38;2;100;116;139m"
BOLD = "\033[1m"
RESET = "\033[0m"


def set_no_color(value: bool) -> None:
    global _NO_COLOR, _CONSOLE
    _NO_COLOR = value or bool(os.environ.get("NO_COLOR")) or not sys.stdout.isatty()
    if _NO_COLOR:
        globals().update(
            {
                key: ""
                for key in ["BLUE", "GREEN", "RED", "YELLOW", "FG", "SEC", "DIM", "BOLD", "RESET"]
            }
        )
    if _HAS_RICH and RichConsole is not None:
        _CONSOLE = RichConsole(theme=THEME, no_color=_NO_COLOR)


set_no_color(False)


def _glyph(unicode_value: str, ascii_value: str) -> str:
    encoding = (sys.stdout.encoding or "").lower()
    return unicode_value if "utf" in encoding else ascii_value


def brand() -> str:
    if _HAS_RICH and _CONSOLE is not None:
        return "[brand.agent]Agent[/brand.agent][brand.mint]Mint[/brand.mint]"
    return "%sAgent%s%sMint%s" % (BLUE, RESET, FG, RESET)


def success(message: str, suffix: str = "") -> str:
    icon = _glyph("✓", "+")
    return f"{GREEN}{icon} {FG}{message}{RESET}{DIM}{(' ' + suffix) if suffix else ''}{RESET}"


def error(message: str, suffix: str = "") -> str:
    icon = _glyph("✗", "x")
    return f"{RED}{icon} {RED}{message}{RESET}{DIM}{(' ' + suffix) if suffix else ''}{RESET}"


def warning(message: str, suffix: str = "") -> str:
    icon = _glyph("⚠", "!")
    return f"{YELLOW}{icon} {YELLOW}{message}{RESET}{SEC}{(' ' + suffix) if suffix else ''}{RESET}"


def info(message: str) -> str:
    return f"{SEC}{message}{RESET}"


def dim(message: str) -> str:
    return f"{DIM}{message}{RESET}"


def primary(message: str, bold: bool = False) -> str:
    return f"{BOLD if bold else ''}{FG}{message}{RESET}"


def accent(message: str) -> str:
    return f"{BLUE}{message}{RESET}"


def panel(title: str, body: str, kind: str = "info") -> str:
    lines = body.splitlines() or [""]
    width = max([len(title)] + [len(line) for line in lines])
    top = "+" + "-" * (width + 2) + "+"
    content = [f"| {line.ljust(width)} |" for line in lines]
    if title:
        content.insert(0, f"| {title.ljust(width)} |")
    return "\n".join([top] + content + [top])


def table(headers: List[str], rows: List[List[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    fmt = "  ".join("{:<" + str(width) + "}" for width in widths)
    rendered = [fmt.format(*headers)]
    rendered.extend(fmt.format(*row) for row in rows)
    return "\n".join(rendered)


def confirm(prompt: str, default: bool = True) -> bool:
    suffix = "Y/n" if default else "y/N"
    answer = input(f"{primary(prompt)} {dim(f'[{suffix}]')} ").strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}


def console_print(text: str) -> None:
    if _HAS_RICH and _CONSOLE is not None:
        _CONSOLE.print(text)
    else:
        print(text)


def heading(text: str) -> None:
    global _FIRST_HEADING
    console_print("")
    if _FIRST_HEADING:
        console_print(brand())
        _FIRST_HEADING = False
    console_print(primary(text, bold=True))
    console_print("")
