import os
from pathlib import Path
from shutil import rmtree
from time import sleep

import pytest
from slugify import slugify
from playwright.sync_api import Page

# Default timeout in milliseconds
DEFAULT_TIMEOUT = 10000  # type: int
SCREENSHOTS_DIR = Path(".playwright") / "screenshots"
SLOW_MOTION_TIME = int(
    os.getenv("PLAYWRIGHT_SLOWMO", "2000")  # None 0 to add some viscosity
)  # Time to wait between action in milliseconds
VIDEOS_DIR = Path(".playwright") / "videos"


def pytest_sessionstart(session):
    """Clean up screenshots and videos directories"""
    if SCREENSHOTS_DIR.exists():
        rmtree(SCREENSHOTS_DIR, ignore_errors=True)
    if VIDEOS_DIR.exists():
        rmtree(VIDEOS_DIR, ignore_errors=True)


def take_screenshot(page, uid):
    screenshot_dir = Path(".playwright") / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)
    page.screenshot(path=str(screenshot_dir / f"{uid}.png"))


def pytest_runtest_makereport(item, call) -> None:
    if "browser" in item.funcargs:
        path, _, test_name = item.nodeid.partition("::")

        if call.when == "call":
            for cidx, context in enumerate(item.funcargs["browser"].contexts):
                for idx, page in enumerate(context.pages):
                    human_name = Path(path).with_suffix("") / "-".join(
                        (slugify(test_name), str(cidx), str(idx))
                    )
                    # Rename the video to some more human name
                    video = Path(page.video.path())
                    if video.exists():
                        new_name = video.parent / human_name.with_suffix(video.suffix)
                        new_name.parent.mkdir(parents=True, exist_ok=True)
                        video.rename(new_name)
                    # Take a screenshots in case of failure
                    if call.excinfo is not None:
                        take_screenshot(page, human_name)
        elif call.when == "teardown":
            # In case there are some videos with cryptic uuid, assume they came from the current test
            for vidx, video in enumerate(VIDEOS_DIR.glob("*.webm")):
                human_name = Path(path).with_suffix("") / "-".join((slugify(test_name), str(vidx)))
                new_name = video.parent / human_name.with_suffix(video.suffix)
                new_name.parent.mkdir(parents=True, exist_ok=True)
                video.rename(new_name)


@pytest.fixture(scope="session")
def slow_motion():
    """Sleep for delay seconds.

    By default 0.001 * SLOW_MOTION_TIME
    """

    def pause(delay=SLOW_MOTION_TIME * 0.001):
        sleep(delay)

    return pause


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {**browser_type_launch_args, "slowMo": SLOW_MOTION_TIME, "timeout": DEFAULT_TIMEOUT}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "recordVideo": {"dir": str(VIDEOS_DIR)},
    }


@pytest.fixture(scope="function")
def login(page: Page, base_url:str):
    page.goto(base_url + "/hub/login")

    # Fill input[name="username"]
    page.fill('input[name="username"]', "marc")

    # Login
    with page.expect_navigation():
        page.click('input[type="submit"]')

    yield page


@pytest.fixture(scope="function")
def report_page(login: Page, base_url: str):
    login.goto(base_url + "/services/report/")

    # Acknowledge oauth
    login.click('input[type="submit"]')

    yield login
