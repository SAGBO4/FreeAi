"""Vanguard Progressive Token Streaming Renderer (OpenCode Architecture).
Provides zero-flicker, token-by-token real-time streaming inside the
OpenCode vertical LeftBorder frame ('┃' ... '╹') with adaptive frame pacing
and noble terminal typography.
"""

import sys
import time
import asyncio
from typing import AsyncGenerator, Optional, Callable
from rich.console import Console, RenderableType
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text
from rich.segment import Segment


class StreamingLeftBorder:
    """Dynamic renderable that prefixes every line with the LeftBorder vertical gutter

    and appends a noble cursor during active streaming.
    """
    def __init__(self, raw_text: str, border_style: str = "bold cyan", char: str = "┃", cursor: str = "▌", is_active: bool = True):
        self.raw_text = raw_text
        self.border_style = border_style
        self.char = char
        self.cursor = cursor if is_active else ""
        self.is_active = is_active

    def __rich_console__(self, console: Console, options):
        style = console.get_style(self.border_style)
        gutter = Segment(f"{self.char} ", style)
        
        display_text = self.raw_text + (self.cursor if self.is_active else "")
        # Split text into lines preserving empty lines
        lines = display_text.split("\n")
        
        for i, line_str in enumerate(lines):
            yield gutter
            yield Segment(line_str)
            if i < len(lines) - 1:
                yield Segment.line()


class LeftBorderFinal:
    """Final snapshot of rendered content with OpenCode vertical border and bottom cap '╹'."""
    def __init__(self, renderable: RenderableType, style: str = "bold cyan", char: str = "┃", bottom_char: str = "╹"):
        self.renderable = renderable
        self.style = style
        self.char = char
        self.bottom_char = bottom_char

    def __rich_console__(self, console: Console, options):
        style = console.get_style(self.style)
        normal_gutter = Segment(f"{self.char} ", style)
        last_gutter = Segment(f"{self.bottom_char} ", style) if self.bottom_char else normal_gutter
        lines = list(console.render_lines(self.renderable, options))
        for i, line in enumerate(lines):
            is_last = (i == len(lines) - 1)
            yield last_gutter if is_last else normal_gutter
            yield from line
            yield Segment.line()


class LeftBorderStreamer:
    """High-speed token accumulator and frame pacesetter.
    Guarantees 0ms perceived latency, smooth scrollback and ZERO terminal flicker.
    """
    def __init__(
        self,
        console: Optional[Console] = None,
        border_style: str = "bold #3b82f6",
        frame_interval_sec: float = 0.025,  # 40 fps target
        char: str = "┃",
        bottom_char: str = "╹",
        cursor_char: str = "▌"
    ):
        self.console = console or Console()
        self.border_style = border_style
        self.frame_interval_sec = frame_interval_sec
        self.char = char
        self.bottom_char = bottom_char
        self.cursor_char = cursor_char
        self.accumulated_text = ""
        self.token_count = 0
        self.start_time = 0.0

    async def stream_tokens(
        self,
        token_generator: AsyncGenerator[str, None],
        on_token_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """Consumes tokens from an async generator and renders them smoothly in real time."""
        self.accumulated_text = ""
        self.token_count = 0
        self.start_time = time.perf_counter()
        last_render_time = self.start_time

        is_tty = sys.stdout.isatty() and not getattr(self.console, "record", False)

        if not is_tty:
            # Fallback for headless, mock, or pipe environments: accumulate without terminal control
            async for token in token_generator:
                self.accumulated_text += token
                self.token_count += 1
                if on_token_callback:
                    on_token_callback(token)
            
            # Print complete markdown once
            try:
                md = Markdown(self.accumulated_text)
                self.console.print(LeftBorderFinal(md, style=self.border_style, char=self.char, bottom_char=self.bottom_char))
            except Exception:
                txt = Text(self.accumulated_text)
                self.console.print(LeftBorderFinal(txt, style=self.border_style, char=self.char, bottom_char=self.bottom_char))
            return self.accumulated_text

        # Interactive TTY: Zero-flicker progressive live frame rendering
        streaming_view = StreamingLeftBorder(
            raw_text="",
            border_style=self.border_style,
            char=self.char,
            cursor=self.cursor_char,
            is_active=True
        )

        with Live(
            streaming_view,
            console=self.console,
            refresh_per_second=40,
            auto_refresh=False,
            transient=True  # Clear temporary live frame when exiting so final snap renders cleanly
        ) as live:
            async for token in token_generator:
                self.accumulated_text += token
                self.token_count += 1
                if on_token_callback:
                    on_token_callback(token)

                now = time.perf_counter()
                # Frame throttle: refresh only when frame_interval has passed or on newline
                if (now - last_render_time) >= self.frame_interval_sec or "\n" in token:
                    streaming_view.raw_text = self.accumulated_text
                    live.update(streaming_view, refresh=True)
                    last_render_time = now

            # Final render update before closing Live session
            streaming_view.raw_text = self.accumulated_text
            live.update(streaming_view, refresh=True)

        # Final Snap: Convert to beautifully highlighted Markdown with permanent LeftBorder and bottom cap '╹'
        try:
            md = Markdown(self.accumulated_text)
            self.console.print(LeftBorderFinal(md, style=self.border_style, char=self.char, bottom_char=self.bottom_char))
        except Exception:
            txt = Text(self.accumulated_text)
            self.console.print(LeftBorderFinal(txt, style=self.border_style, char=self.char, bottom_char=self.bottom_char))

        return self.accumulated_text

    def get_telemetry(self) -> dict:
        """Returns streaming performance telemetry."""
        duration = max(0.001, time.perf_counter() - self.start_time)
        tok_sec = self.token_count / duration
        return {
            "tokens": self.token_count,
            "duration_sec": duration,
            "tokens_per_sec": tok_sec,
            "char_count": len(self.accumulated_text)
        }
