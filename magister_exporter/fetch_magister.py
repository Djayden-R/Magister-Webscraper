import requests
import json
from datetime import datetime, timedelta
import logging
from playwright.async_api import Playwright, TimeoutError, async_playwright
import asyncio
from collections.abc import Iterable
from functools import wraps

logger = logging.getLogger(__name__)

class UnexpectedPageState(Exception):
    pass

from functools import wraps

class TooManyTriesException(Exception):
    pass

def tries(times: int, no_retry_exceptions: tuple[type[BaseException], ...] = ()):
    def func_wrapper(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            last_exc = None

            for i in range(times):
                try:
                    return await f(*args, **kwargs)
                except Exception as exc:
                    # If exception type is in no-retry list, re-raise immediately
                    if isinstance(exc, no_retry_exceptions):
                        raise

                    last_exc = exc
                    logger.debug(f"retry: {i+1}/{times} ({type(exc).__name__})")

            raise TooManyTriesException() from last_exc

        return wrapper
    return func_wrapper

@tries(times=3, no_retry_exceptions=(ValueError,))
async def fetch_magister_token(playwright: Playwright, base_url: str, name: str, username: str, password:str, headless: bool = True):
    page = None
    try:
        playwright.selectors.set_test_id_attribute("id")

        chromium = playwright.chromium
        browser = await chromium.launch(headless=headless)
        page = await browser.new_page()

        logger.info(f"Finding {name}'s token")
        await page.goto(f"https://{base_url}/oidc/redirect_callback.html")
        
        await page.get_by_test_id("username").fill(username)
        await page.get_by_test_id("username_submit").click()
        logger.debug("Submitted username")

        await page.wait_for_load_state("load")

        await page.get_by_test_id('i0118').fill(password)
        await page.get_by_test_id("idSIButton9").click()
        logger.debug("Submitted password")

        """
        Now check if id passwordError or id KmsiDescription is visible, 
        passwordError means password is wrong, 
        KmsiDescription means that the password is correct
        """
        await page.wait_for_load_state("load")

        signed_in_description = await page.get_by_test_id('KmsiDescription').is_visible(timeout=10)
        password_error = await page.get_by_test_id('passwordError').is_visible(timeout=10)

        if password_error:
            logger.error("Password is incorrect")
            raise ValueError
        elif not signed_in_description:
            logger.error("Program didn't continue for an unexpected reason")
            raise UnexpectedPageState
        
        await page.get_by_test_id('idSIButton9').click()
        logger.debug("Continued past Microsoft prompt")
        
        # Use a glob url pattern
        async with page.expect_response("**/api/leerlingen/**", timeout=0) as response_info:
            logger.debug("Found network leerling request")
            response = await response_info.value
            headers = await response.request.all_headers()
            url = response.url
        
        token = headers.get('authorization', None)
        user_id = url.split('/api/leerlingen/')[1].split("/")[0]

        if not token:
            raise ValueError("Unable to find token in requests")
        
        logger.info(f"Bearer token found: {token[:20]}")
        logger.info(f"User id found: {user_id}")

        await browser.close()
        return token, user_id
    except TimeoutError:
        if page:
            content = await page.content()
            raise TimeoutError(f"Failed to load calendar: \nCurrent url: {page.url}\nPage content: {content}")

def fetch_magister_calendar(base_url: str, user_id: str, bearer_token: str, days_to_fetch: int):
    headers = {
        "Authorization": bearer_token,
        "content-type": "application/json"
    }

    current_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_to_fetch)).strftime("%Y-%m-%d")

    url = f"https://{base_url}/api/personen/{user_id}/afspraken?status=1&tot={end_date}&van={current_date}"

    r = requests.get(url, headers=headers)

    if r.ok:
        calendar = json.loads(r.text)
        return calendar
    else:
        return None