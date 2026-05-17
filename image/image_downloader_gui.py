import importlib
import mimetypes
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from tkinter import StringVar, Tk, messagebox
from tkinter import ttk


INVALID_FOLDER_CHARS = re.compile(r'[<>:"/\\|?*]')


def sanitize_folder_name(folder_name: str) -> str:
    cleaned = INVALID_FOLDER_CHARS.sub("_", folder_name.strip())
    return cleaned.strip(". ")


def looks_like_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def derive_filename(url: str, content_type: str | None) -> str:
    parsed = urllib.parse.urlparse(url)
    candidate = Path(parsed.path).name

    if not candidate or "." not in candidate:
        ext = None
        if content_type:
            ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if not ext:
            ext = ".jpg"
        candidate = f"downloaded_image{ext}"

    return candidate


def unique_file_path(target_dir: Path, file_name: str) -> Path:
    base = target_dir / file_name
    if not base.exists():
        return base

    stem = base.stem
    suffix = base.suffix
    index = 1
    while True:
        candidate = target_dir / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


class ImageSaverApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Image URL Saver")
        self.root.geometry("560x270")
        self.root.resizable(False, False)

        self.folder_var = StringVar()
        self.url_var = StringVar()
        self.status_var = StringVar(value="Ready")

        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Folder name").grid(row=0, column=0, sticky="w", pady=(0, 6))
        folder_entry = ttk.Entry(frame, textvariable=self.folder_var, width=64)
        folder_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(frame, text="Image URL").grid(row=2, column=0, sticky="w", pady=(0, 6))
        url_entry = ttk.Entry(frame, textvariable=self.url_var, width=64)
        url_entry.grid(row=3, column=0, sticky="ew", pady=(0, 12))

        save_button = ttk.Button(frame, text="Create Folder and Save Image", command=self.on_save)
        save_button.grid(row=4, column=0, sticky="ew")

        paste_button = ttk.Button(frame, text="Paste URL or Screenshot (Ctrl+V)", command=self.on_paste_clipboard)
        paste_button.grid(row=5, column=0, sticky="ew", pady=(8, 0))

        status_label = ttk.Label(frame, textvariable=self.status_var, foreground="#1a4")
        status_label.grid(row=6, column=0, sticky="w", pady=(12, 0))

        frame.columnconfigure(0, weight=1)

        folder_entry.focus_set()
        self.root.bind("<Return>", lambda _event: self.on_save())
        self.root.bind("<Control-v>", self.on_paste_clipboard)
        self.root.bind("<Control-V>", self.on_paste_clipboard)

    def on_save(self) -> None:
        folder_name = sanitize_folder_name(self.folder_var.get())
        image_url = self.url_var.get().strip()

        if not folder_name:
            messagebox.showerror("Invalid folder", "Please enter a valid folder name.")
            return

        if not image_url:
            messagebox.showerror("Missing URL", "Please enter an image URL.")
            return

        self.status_var.set("Downloading...")
        thread = threading.Thread(target=self._download_image, args=(folder_name, image_url), daemon=True)
        thread.start()

    def on_paste_clipboard(self, _event=None) -> str | None:
        text_value = ""
        try:
            text_value = self.root.clipboard_get().strip()
        except Exception:
            text_value = ""

        # Auto-save when a URL is pasted from clipboard.
        if text_value and looks_like_url(text_value):
            self.url_var.set(text_value)
            self.status_var.set("URL pasted. Auto-saving...")
            self.on_save()
            return "break"

        folder_name = sanitize_folder_name(self.folder_var.get())
        if not folder_name:
            messagebox.showerror("Invalid folder", "Please enter a valid folder name.")
            return "break"

        pillow_modules = self._load_pillow_modules()
        if pillow_modules is None:
            messagebox.showerror(
                "Missing dependency",
                "Clipboard image paste needs Pillow. Install with:\npip install pillow",
            )
            return "break"

        self.status_var.set("Saving pasted screenshot...")
        thread = threading.Thread(
            target=self._save_clipboard_image,
            args=(folder_name, pillow_modules[0], pillow_modules[1]),
            daemon=True,
        )
        thread.start()
        return "break"

    def _download_image(self, folder_name: str, image_url: str) -> None:
        try:
            target_dir = Path.cwd() / folder_name
            target_dir.mkdir(parents=True, exist_ok=True)

            request = urllib.request.Request(
                image_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ImageSaver/1.0",
                },
            )

            with urllib.request.urlopen(request, timeout=20) as response:
                content_type = response.headers.get("Content-Type")
                filename = derive_filename(image_url, content_type)
                target_file = unique_file_path(target_dir, filename)
                data = response.read()

            target_file.write_bytes(data)
            self.root.after(0, lambda: self._on_success(target_file))
        except urllib.error.HTTPError as exc:
            error_message = f"HTTP error: {exc.code}"
            self.root.after(0, lambda msg=error_message: self._on_error(msg))
        except urllib.error.URLError as exc:
            error_message = f"URL error: {exc.reason}"
            self.root.after(0, lambda msg=error_message: self._on_error(msg))
        except Exception as exc:
            error_message = str(exc)
            self.root.after(0, lambda msg=error_message: self._on_error(msg))

    def _load_pillow_modules(self):
        try:
            image_module = importlib.import_module("PIL.Image")
            image_grab_module = importlib.import_module("PIL.ImageGrab")
            return image_module, image_grab_module
        except ModuleNotFoundError:
            return None

    def _save_clipboard_image(self, folder_name: str, image_module, image_grab_module) -> None:
        try:
            target_dir = Path.cwd() / folder_name
            target_dir.mkdir(parents=True, exist_ok=True)

            clipboard_data = image_grab_module.grabclipboard()
            image = None

            if isinstance(clipboard_data, image_module.Image):
                image = clipboard_data
            elif isinstance(clipboard_data, list) and clipboard_data:
                first_item = clipboard_data[0]
                if isinstance(first_item, str):
                    path_item = Path(first_item)
                    if path_item.exists():
                        image = image_module.open(path_item)

            if image is None:
                self.root.after(
                    0,
                    lambda: self._on_error(
                        "No image found in clipboard. Paste a URL or use Win+Shift+S first."
                    ),
                )
                return

            target_file = unique_file_path(target_dir, "screencrop.png")
            image.save(target_file, format="PNG")
            self.root.after(0, lambda: self._on_success(target_file))
        except Exception as exc:
            error_message = str(exc)
            self.root.after(0, lambda msg=error_message: self._on_error(msg))

    def _on_success(self, file_path: Path) -> None:
        self.status_var.set(f"Saved: {file_path}")
        messagebox.showinfo("Done", f"Image saved to:\n{file_path}")

    def _on_error(self, error_message: str) -> None:
        self.status_var.set("Failed")
        messagebox.showerror("Download failed", error_message)


def main() -> None:
    root = Tk()
    ttk.Style(root).theme_use("clam")
    ImageSaverApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
