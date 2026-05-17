from __future__ import annotations

import importlib.util
import random
from datetime import datetime
from pathlib import Path
from types import ModuleType

from flask import Flask, abort, render_template, request, send_from_directory


ROOT_DIR = Path(__file__).resolve().parents[1]
IMAGE_ROOT = ROOT_DIR / "image"
RANDOMIZER_FILE = IMAGE_ROOT / "randomizer_fav_afav" / "randomizer_fav_afav.py"
GENERATED_DIR = Path(__file__).resolve().parent / "static" / "generated"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
CATEGORY_FOLDERS = {
    "bookAction": IMAGE_ROOT / "bookAction",
    "fraction": IMAGE_ROOT / "fraction",
    "SH": IMAGE_ROOT / "SH",
    "spawn": IMAGE_ROOT / "spawn",
    "bon": IMAGE_ROOT / "bon",
}


def load_fav_afav_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("randomizer_fav_afav_module", RANDOMIZER_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load fav/afav randomizer module.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def list_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def pick_cards(paths: list[Path], count: int, rng: random.Random) -> list[Path]:
    if count <= 0:
        return []
    if not paths:
        return []
    if len(paths) >= count:
        return rng.sample(paths, count)
    return [rng.choice(paths) for _ in range(count)]


def counts_for_players(player_count: int) -> dict[str, int]:
    return {
        "bookAction": 3,
        "fraction": player_count + 1,
        "SH": player_count + 1,
        "spawn": 6,
        "bon": player_count + 3,
    }


def build_random_setup(player_count: int) -> dict[str, object]:
    rng = random.Random()
    module = load_fav_afav_module()
    board_result = module.generate_fav_afav_setup(rng=rng)

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    file_stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    board_file = GENERATED_DIR / f"board_{file_stamp}.jpg"
    board_image = board_result["image"]
    board_image.convert("RGB").save(board_file, format="JPEG", quality=92, optimize=True)

    counts = counts_for_players(player_count)
    picked_by_category: dict[str, list[dict[str, str]]] = {}
    for category, count in counts.items():
        pool = list_images(CATEGORY_FOLDERS[category])
        selected = pick_cards(pool, count, rng)
        picked_by_category[category] = [
            {"file_name": path.name, "category": category}
            for path in selected
        ]

    return {
        "board_file_name": board_file.name,
        "player_count": player_count,
        "counts": counts,
        "picked": picked_by_category,
    }


app = Flask(__name__)


@app.get("/")
def index_get():
    return render_template("index.html", title="Age of Innovation", result=None, player_count=2)


@app.post("/")
def index_post():
    player_raw = request.form.get("player_count", "2")
    try:
        player_count = int(player_raw)
    except ValueError:
        player_count = 2

    player_count = max(1, min(4, player_count))
    result = build_random_setup(player_count)
    return render_template("index.html", title="Age of Innovation", result=result, player_count=player_count)


@app.get("/asset/<category>/<file_name>")
def asset(category: str, file_name: str):
    if category not in CATEGORY_FOLDERS:
        abort(404)
    folder = CATEGORY_FOLDERS[category]
    return send_from_directory(folder, file_name)


@app.get("/generated/<file_name>")
def generated(file_name: str):
    return send_from_directory(GENERATED_DIR, file_name)


if __name__ == "__main__":
    app.run(debug=True)
