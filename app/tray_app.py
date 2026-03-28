"""System tray application using pystray."""
from __future__ import annotations

import logging
import threading
from typing import Callable

import pystray
from PIL import Image, ImageDraw, ImageFont

from app.models.battery_status import BatteryStatus, BatteryStatusType, ChargingState

logger = logging.getLogger(__name__)

ICON_SIZE = 64

# Battery body dimensions within the 64x64 canvas
_BAT_LEFT = 6
_BAT_RIGHT = 57
_BAT_TOP = 8
_BAT_BOTTOM = 60
_BAT_RADIUS = 6
# Battery terminal (the little bump on top)
_TERM_LEFT = 22
_TERM_RIGHT = 41
_TERM_TOP = 2
_TERM_BOTTOM = _BAT_TOP + 2


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try loading a bold font, falling back to regular then default."""
    for name in (
        # Windows
        "arialbd.ttf", "arial.ttf", "segoeui.ttf",
        # macOS
        "Helvetica Neue Bold.ttc", "Helvetica Neue.ttc", "Helvetica.ttc",
        # Linux
        "DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "LiberationSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _bolt_points(cx: int, cy: int) -> list[tuple[int, int]]:
    """Return the lightning bolt polygon vertices centered at (cx, cy)."""
    return [
        (cx + 3, cy - 28),
        (cx - 14, cy + 2),
        (cx - 2, cy + 2),
        (cx - 7, cy + 28),
        (cx + 14, cy - 2),
        (cx + 2, cy - 2),
    ]


def _draw_lightning_bolt(draw: ImageDraw.ImageDraw, cx: int, cy: int,
                         fill: tuple = (0, 0, 0, 255),
                         outline: tuple = (255, 255, 255, 220)) -> None:
    """Draw a lightning bolt polygon centered at (cx, cy)."""
    points = _bolt_points(cx, cy)
    # Outline for visibility
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            if dx == 0 and dy == 0:
                continue
            shifted = [(px + dx, py + dy) for px, py in points]
            draw.polygon(shifted, fill=outline)
    # Colored bolt on top
    draw.polygon(points, fill=fill)


def _create_charging_icon(charging_state: ChargingState) -> Image.Image:
    """Draw a standalone lightning bolt icon (no battery shell)."""
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2
    if charging_state == ChargingState.FULL:
        # Green bolt = fully charged
        _draw_lightning_bolt(draw, cx, cy,
                             fill=(50, 205, 50, 255),
                             outline=(255, 255, 255, 220))
    else:
        # Orange-yellow gradient bolt = charging
        # 1) Draw white outline
        points = _bolt_points(cx, cy)
        for dx in (-2, -1, 0, 1, 2):
            for dy in (-2, -1, 0, 1, 2):
                if dx == 0 and dy == 0:
                    continue
                shifted = [(px + dx, py + dy) for px, py in points]
                draw.polygon(shifted, fill=(255, 255, 255, 220))
        # 2) Build vertical gradient (orange top → yellow bottom)
        grad = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
        for y in range(ICON_SIZE):
            t = y / (ICON_SIZE - 1)
            r = int(255 * (1 - t) + 255 * t)
            g = int(140 * (1 - t) + 220 * t)
            b = int(0 * (1 - t) + 0 * t)
            ImageDraw.Draw(grad).line([(0, y), (ICON_SIZE - 1, y)],
                                      fill=(r, g, b, 255))
        # 3) Mask gradient to bolt shape
        bolt_mask = Image.new("L", (ICON_SIZE, ICON_SIZE), 0)
        ImageDraw.Draw(bolt_mask).polygon(points, fill=255)
        img.paste(grad, mask=bolt_mask)
    return img


def _create_battery_icon(level: int | None, status: BatteryStatusType,
                         charging_state: ChargingState = ChargingState.DISCHARGING) -> Image.Image:
    """Draw the tray icon based on charging state and battery level."""
    # Charging / Full → standalone lightning bolt (no battery shell)
    if (status == BatteryStatusType.SUCCESS and level is not None
            and charging_state in (ChargingState.CHARGING, ChargingState.FULL)):
        return _create_charging_icon(charging_state)

    # Normal / error / unavailable → battery shape with number
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Determine fill color and text
    if status != BatteryStatusType.SUCCESS or level is None:
        fill_color = (160, 160, 160, 255)   # Gray
        text = "?"
        fill_pct = 100  # full gray fill for unknown
    elif level <= 15:
        fill_color = (220, 50, 50, 255)     # Red
        text = str(level)
        fill_pct = level
    elif level <= 50:
        fill_color = (240, 200, 30, 255)    # Yellow
        text = str(level)
        fill_pct = level
    else:
        fill_color = (60, 185, 60, 255)     # Green
        text = str(level)
        fill_pct = level

    outline_color = (220, 220, 220, 255)         # Light border
    body_bg = (40, 40, 40, 255)                   # Dark empty area

    # --- Draw battery terminal (top bump) ---
    draw.rounded_rectangle(
        [(_TERM_LEFT, _TERM_TOP), (_TERM_RIGHT, _TERM_BOTTOM)],
        radius=3, fill=outline_color,
    )

    # --- Draw battery body outline ---
    draw.rounded_rectangle(
        [(_BAT_LEFT, _BAT_TOP), (_BAT_RIGHT, _BAT_BOTTOM)],
        radius=_BAT_RADIUS, fill=outline_color,
    )

    # --- Draw inner dark background (2px inset) ---
    inner_l, inner_t = _BAT_LEFT + 2, _BAT_TOP + 2
    inner_r, inner_b = _BAT_RIGHT - 2, _BAT_BOTTOM - 2
    draw.rounded_rectangle(
        [(inner_l, inner_t), (inner_r, inner_b)],
        radius=max(_BAT_RADIUS - 2, 2), fill=body_bg,
    )

    # --- Draw liquid fill from bottom up ---
    if fill_pct > 0:
        inner_h = inner_b - inner_t
        fill_h = max(int(inner_h * fill_pct / 100), 3)
        fill_top = inner_b - fill_h

        # Use a clipping mask: draw filled rect, then mask to inner rounded rect
        fill_layer = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
        fill_draw = ImageDraw.Draw(fill_layer)
        fill_draw.rectangle([(inner_l, fill_top), (inner_r, inner_b)], fill=fill_color)

        # Create mask from inner rounded rectangle
        mask = Image.new("L", (ICON_SIZE, ICON_SIZE), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            [(inner_l, inner_t), (inner_r, inner_b)],
            radius=max(_BAT_RADIUS - 2, 2), fill=255,
        )

        img = Image.composite(fill_layer, img, mask)
        draw = ImageDraw.Draw(img)

    # --- Draw text number ---
    body_cx = (_BAT_LEFT + _BAT_RIGHT) // 2
    body_cy = (_BAT_TOP + _BAT_BOTTOM) // 2

    if len(text) == 1:
        font = _load_font(40)
    elif len(text) == 2:
        font = _load_font(36)
    else:
        font = _load_font(28)

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = body_cx - tw // 2 - bbox[0]
    y = body_cy - th // 2 - bbox[1]

    # White outline for readability on both dark and colored backgrounds
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, fill=(255, 255, 255, 220), font=font)

    # Black bold text on top
    draw.text((x, y), text, fill=(0, 0, 0, 255), font=font)

    return img


class TrayApp:
    def __init__(self, on_refresh: Callable[[], None], on_quit: Callable[[], None]):
        self._on_refresh = on_refresh
        self._on_quit = on_quit
        self._status = BatteryStatus()
        initial_icon = _create_battery_icon(None, BatteryStatusType.UNAVAILABLE)
        self._icon = pystray.Icon(
            name="mouse-battery",
            icon=initial_icon,
            title="Mouse Battery Monitor\n啟動中...",
            menu=pystray.Menu(
                pystray.MenuItem("立即更新", self._handle_refresh),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("離開", self._handle_quit),
            ),
        )

    def update(self, status: BatteryStatus) -> None:
        """Update tray icon and tooltip with new battery status."""
        self._status = status
        self._icon.icon = _create_battery_icon(status.level, status.status, status.charging_state)
        self._icon.title = status.tooltip
        logger.debug("Tray 已更新: %s", status.display_text)

    def run(self) -> None:
        """Run the tray icon (blocks until stopped)."""
        logger.info("系統匣 icon 啟動")
        self._icon.run()

    def stop(self) -> None:
        """Stop the tray icon."""
        self._icon.stop()
        logger.info("系統匣 icon 已停止")

    def _handle_refresh(self, icon, item) -> None:
        logger.info("使用者點擊「立即更新」")
        threading.Thread(target=self._on_refresh, daemon=True).start()

    def _handle_quit(self, icon, item) -> None:
        logger.info("使用者點擊「離開」")
        self._on_quit()
