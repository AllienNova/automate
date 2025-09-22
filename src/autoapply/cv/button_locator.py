"""Locate buttons within screenshots using simple template matching."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


@dataclass
class MatchResult:
    """Result of a button match."""

    position: Tuple[int, int]
    score: float


class ButtonLocator:
    """Identify application buttons on a web page screenshot."""

    def __init__(self, templates: Optional[Sequence[Image.Image]] = None) -> None:
        self.templates = list(templates) if templates else [self._default_template()]
        self._template_arrays = [self._prepare_template(template) for template in self.templates]

    def _prepare_template(self, template: Image.Image) -> np.ndarray:
        template_gray = template.convert("L")
        return np.asarray(template_gray, dtype=np.float32) / 255.0

    def find_best_match(self, screenshot: Image.Image) -> Optional[MatchResult]:
        """Return the best matching template coordinate."""
        image = screenshot.convert("L")
        array = np.asarray(image, dtype=np.float32) / 255.0
        matches = [self._match_template(array, template) for template in self._template_arrays]
        matches = [match for match in matches if match is not None]
        if not matches:
            return None
        return min(matches, key=lambda result: result.score)

    def _match_template(self, image: np.ndarray, template: np.ndarray) -> Optional[MatchResult]:
        ih, iw = image.shape
        th, tw = template.shape
        if ih < th or iw < tw:
            return None
        best_score = float("inf")
        best_position: Optional[Tuple[int, int]] = None
        for y in range(0, ih - th + 1, max(1, th // 4)):
            for x in range(0, iw - tw + 1, max(1, tw // 4)):
                patch = image[y : y + th, x : x + tw]
                score = float(np.mean((patch - template) ** 2))
                if score < best_score:
                    best_score = score
                    best_position = (x + tw // 2, y + th // 2)
        if best_position is None:
            return None
        return MatchResult(position=best_position, score=best_score)

    def _default_template(self) -> Image.Image:
        width, height = 160, 50
        template = Image.new("RGB", (width, height), color="#f97316")
        draw = ImageDraw.Draw(template)
        try:
            font = ImageFont.truetype("arial.ttf", 28)
        except OSError:  # pragma: no cover - depends on environment fonts
            font = ImageFont.load_default()
        text = "Apply Now"
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except AttributeError:  # pragma: no cover - compatibility with older Pillow
            text_width, text_height = draw.textsize(text, font=font)
        draw.text(
            ((width - text_width) / 2, (height - text_height) / 2),
            text,
            font=font,
            fill="white",
        )
        return template

    def generate_augmented_templates(self) -> Iterable[Image.Image]:
        """Return a set of rotated/scaled template variants."""
        for template in self.templates:
            yield template
            yield template.resize((int(template.width * 0.9), int(template.height * 0.9)))
            yield template.resize((int(template.width * 1.1), int(template.height * 1.1)))
