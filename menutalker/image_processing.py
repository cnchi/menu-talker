from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps


def _uploaded_path(uploaded: object) -> Path:
    if isinstance(uploaded, (str, Path)):
        return Path(uploaded)
    name = getattr(uploaded, "name", None)
    if name:
        return Path(name)
    raise TypeError(f"Unsupported uploaded file object: {type(uploaded)!r}")


def save_uploaded_images(uploaded_files: Iterable[object], session_dir: Path) -> list[Path]:
    image_dir = session_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []

    for index, uploaded in enumerate(uploaded_files or [], start=1):
        source = _uploaded_path(uploaded)
        target = image_dir / f"menu_image_{index:02d}.png"
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.save(target, format="PNG")
        saved.append(target)
    return saved


def preprocess_images(image_paths: list[Path], session_dir: Path) -> tuple[list[Path], list[Path]]:
    import cv2

    processed_dir = session_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    ocr_inputs: list[Path] = []
    preview_images: list[Path] = []

    for index, image_path in enumerate(image_paths, start=1):
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Could not read image: {image_path}")

        height, width = image.shape[:2]
        target_width = 1800
        scale = max(1.0, min(2.5, target_width / max(width, 1)))
        if scale > 1.0:
            image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, None, h=7, templateWindowSize=7, searchWindowSize=21)
        lightly_blurred = cv2.GaussianBlur(denoised, (3, 3), 0)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(lightly_blurred)

        block_size = max(31, ((min(enhanced.shape[:2]) // 40) | 1))
        binary = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            11,
        )

        ocr_input = processed_dir / f"menu_image_{index:02d}_ocr.png"
        preview = processed_dir / f"menu_image_{index:02d}_binary.png"
        cv2.imwrite(str(ocr_input), enhanced)
        cv2.imwrite(str(preview), binary)
        ocr_inputs.append(ocr_input)
        preview_images.append(preview)

    return ocr_inputs, preview_images
