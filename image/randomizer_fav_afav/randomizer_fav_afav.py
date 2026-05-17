from __future__ import annotations

import random
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


TOP_AFAV_COUNT = 10
BOTTOM_FAV_COUNT = 12
AFAV_Y_OFFSET = 90
AFAV_MIDDLE_ROW_EXTRA_OFFSET = 50
FAV_X_OFFSET = 300
FAV_Y_OFFSET = 148
FAV_SLOT_W = 320
FAV_SLOT_H = 280


def list_images(folder: Path) -> list[Path]:
    allowed = {".png", ".jpg", ".jpeg", ".webp"}
    return sorted([path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in allowed])


def pick_cards(paths: list[Path], count: int, rng: random.Random, *, allow_repeats: bool = False) -> list[Path]:
    if not paths:
        raise ValueError("No images found.")
    if allow_repeats:
        picked = [rng.choice(paths) for _ in range(count)]
    elif len(paths) >= count:
        picked = rng.sample(paths, count)
    else:
        picked = [rng.choice(paths) for _ in range(count)]

    # Shuffle once more to avoid any perceived ordering pattern.
    rng.shuffle(picked)
    return picked


def build_grid_slots(
    *,
    left: int,
    top: int,
    cols: int,
    rows: int,
    cell_w: int,
    cell_h: int,
    gap_x: int,
    gap_y: int,
) -> list[tuple[int, int, int, int]]:
    slots: list[tuple[int, int, int, int]] = []
    for row in range(rows):
        for col in range(cols):
            x1 = left + col * (cell_w + gap_x)
            y1 = top + row * (cell_h + gap_y)
            x2 = x1 + cell_w
            y2 = y1 + cell_h
            slots.append((x1, y1, x2, y2))
    return slots


def paste_cards(canvas: Image.Image, cards: list[Path], slots: list[tuple[int, int, int, int]]) -> None:
    for card_path, slot in zip(cards, slots):
        x1, y1, x2, y2 = slot
        target_size = (x2 - x1, y2 - y1)
        with Image.open(card_path) as source:
            card = ImageOps.fit(source.convert("RGBA"), target_size, method=Image.Resampling.LANCZOS)
        canvas.paste(card, (x1, y1), card)


def generate_fav_afav_setup(
    *,
    rng: random.Random | None = None,
    base_path: Path | None = None,
    image_root: Path | None = None,
) -> dict[str, Any]:
    script_dir = Path(__file__).resolve().parent
    image_root = image_root or script_dir.parent
    base_path = base_path or (script_dir / "downloaded_image.jpg")

    rng = rng or random.Random()

    afav_dir = image_root / "afav"
    fav_dir = image_root / "fav"

    afav_images = list_images(afav_dir)
    fav_images = list_images(fav_dir)

    selected_afav = pick_cards(afav_images, TOP_AFAV_COUNT, rng)
    selected_fav = pick_cards(fav_images, BOTTOM_FAV_COUNT, rng)

    with Image.open(base_path) as base:
        canvas = base.convert("RGBA")

        # AFAV: 10 gray bulb areas (2 top pads + 8 middle bulb slots).
        raw_top_slots = [
            (492, 160, 1132, 561),
            (2147, 160, 2787, 561),
            (99, 957, 739, 1358),
            (906, 957, 1546, 1358),
            (1731, 957, 2371, 1358),
            (2539, 957, 3179, 1358),
            (99, 1629, 739, 2030),
            (906, 1629, 1546, 2030),
            (1731, 1629, 2371, 2030),
            (2539, 1629, 3179, 2030),
        ]
        top_slots: list[tuple[int, int, int, int]] = []
        for index, (x1, y1, x2, y2) in enumerate(raw_top_slots):
            offset = AFAV_Y_OFFSET
            if 2 <= index <= 5:
                offset += AFAV_MIDDLE_ROW_EXTRA_OFFSET
            top_slots.append((x1, y1 + offset, x2, y2 + offset))

        # FAV: 12 lower card placeholders (4 cols x 3 rows), avoiding the left icon column.
        lower_cards = build_grid_slots(
            left=17,
            top=2450,
            cols=4,
            rows=3,
            cell_w=748,
            cell_h=500,
            gap_x=64,
            gap_y=0,
        )

        bottom_slots: list[tuple[int, int, int, int]] = []
        for x1, y1, _x2, _y2 in lower_cards:
            slot_x1 = x1 + FAV_X_OFFSET
            slot_y1 = y1 + FAV_Y_OFFSET
            slot_x2 = slot_x1 + FAV_SLOT_W
            slot_y2 = slot_y1 + FAV_SLOT_H
            bottom_slots.append((slot_x1, slot_y1, slot_x2, slot_y2))

        paste_cards(canvas, selected_afav, top_slots)
        paste_cards(canvas, selected_fav, bottom_slots)

        result = {
            "image": canvas.copy(),
            "afav": selected_afav,
            "fav": selected_fav,
        }

    return result


def save_fav_afav_setup(
    *,
    output_dir: Path | None = None,
    file_name: str | None = None,
    rng: random.Random | None = None,
) -> Path:
    script_dir = Path(__file__).resolve().parent
    output_dir = output_dir or script_dir

    result = generate_fav_afav_setup(rng=rng)
    board_image: Image.Image = result["image"]

    if file_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"setup_randomized_{timestamp}.jpg"

    out_file = output_dir / file_name
    board_image.convert("RGB").save(out_file, format="JPEG", quality=92, optimize=True)
    return out_file


def main() -> None:
    out_file = save_fav_afav_setup(rng=random.Random())

    print(f"Saved randomized setup to: {out_file}")


if __name__ == "__main__":
    main()