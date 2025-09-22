from __future__ import annotations

from PIL import Image

from autoapply.cv.button_locator import ButtonLocator


def test_button_locator_finds_button():
    locator = ButtonLocator()
    screenshot = Image.new("RGB", (400, 300), "white")
    template = locator.templates[0]
    paste_position = (120, 140)
    screenshot.paste(template, paste_position)

    match = locator.find_best_match(screenshot)
    assert match is not None
    expected_x = paste_position[0] + template.width // 2
    expected_y = paste_position[1] + template.height // 2
    assert abs(match.position[0] - expected_x) < template.width // 2
    assert abs(match.position[1] - expected_y) < template.height // 2
