"""Browser automation utilities built on Playwright."""
from __future__ import annotations

import asyncio
import io
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

from ..config import AutomationSettings, UserProfile
from ..cv.button_locator import ButtonLocator
from ..job_sources import JobPosting


class BrowserAutomation:
    """Navigate job pages and attempt to complete the application flow."""

    def __init__(
        self,
        settings: AutomationSettings,
        button_locator: Optional[ButtonLocator] = None,
    ) -> None:
        self.settings = settings
        self.button_locator = button_locator or ButtonLocator()
        self._playwright_manager = None
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    async def __aenter__(self) -> "BrowserAutomation":
        async_playwright = self._require_playwright()
        self._playwright_manager = async_playwright()
        self._playwright = await self._playwright_manager.__aenter__()
        self._browser = await self._playwright.chromium.launch(headless=self.settings.headless)
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright_manager:
            await self._playwright_manager.__aexit__(exc_type, exc, tb)

    async def apply_to_job(
        self, job: JobPosting, user: UserProfile, resume_path: Path
    ) -> Tuple[bool, str]:
        """Attempt to apply for a job posting."""
        if not self._page:
            raise RuntimeError("BrowserAutomation must be used as an async context manager")
        url = job.apply_url or job.url
        await self._page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(self.settings.wait_after_navigation)

        clicked = await self._click_apply_button()
        if not clicked:
            return False, "Apply button not located"

        await asyncio.sleep(0.5)
        await self._upload_resume(resume_path)
        await self._populate_contact_details(user)
        submitted = await self._submit_if_possible()
        return submitted, "Application submitted" if submitted else "Form not submitted"

    async def _click_apply_button(self) -> bool:
        assert self._page
        candidates = [
            "text=/apply now/i",
            "text=/quick apply/i",
            "text=/submit application/i",
            "role=button[name=/apply/i]",
        ]
        for selector in candidates:
            locator = self._page.locator(selector)
            if await locator.count():
                try:
                    await locator.first.click()
                    return True
                except Exception:
                    continue
        screenshot_bytes = await self._page.screenshot(full_page=True)
        image = Image.open(io.BytesIO(screenshot_bytes))
        match = self.button_locator.find_best_match(image)
        if not match:
            return False
        await self._page.mouse.click(match.position[0], match.position[1])
        return True

    async def _upload_resume(self, resume_path: Path) -> bool:
        assert self._page
        file_inputs = self._page.locator("input[type='file']")
        if await file_inputs.count():
            try:
                await file_inputs.first.set_input_files(str(resume_path))
                return True
            except Exception:
                return False
        return False

    async def _populate_contact_details(self, user: UserProfile) -> None:
        if not self._page:
            return
        mapping = {
            "name": user.full_name,
            "email": user.email,
            "phone": user.phone,
        }
        for field, value in mapping.items():
            if not value:
                continue
            selectors = [
                f"input[name*='{field}' i]",
                f"input[placeholder*='{field}' i]",
                f"input[aria-label*='{field}' i]",
            ]
            await self._fill_first_available(selectors, value)

        if user.location:
            await self._fill_first_available(
                [
                    "input[name*='city' i]",
                    "input[placeholder*='location' i]",
                ],
                user.location,
            )

    async def _fill_first_available(self, selectors, value: str) -> bool:
        assert self._page
        for selector in selectors:
            locator = self._page.locator(selector)
            if await locator.count():
                try:
                    await locator.first.fill(value)
                    return True
                except Exception:
                    continue
        return False

    async def _submit_if_possible(self) -> bool:
        assert self._page
        selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "role=button[name=/submit/i]",
        ]
        for selector in selectors:
            locator = self._page.locator(selector)
            if await locator.count():
                try:
                    await locator.first.click()
                    await asyncio.sleep(1)
                    return True
                except Exception:
                    continue
        return False

    @staticmethod
    def _require_playwright():
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover - runtime dependency
            raise RuntimeError(
                "Playwright is required for browser automation. Install with 'pip install autoapply[playwright]'"
            ) from exc
        return async_playwright


@asynccontextmanager
async def automation_context(settings: AutomationSettings):
    automation = BrowserAutomation(settings)
    try:
        await automation.__aenter__()
        yield automation
    finally:
        await automation.__aexit__(None, None, None)
