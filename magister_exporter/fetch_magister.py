import requests
import json
from datetime import datetime, timedelta
import logging
from playwright.async_api import Playwright, TimeoutError, async_playwright
from retrying import retry
import asyncio

class UnexpectedPageState(Exception):
    pass

@retry(stop_max_attempt_number=3)
async def fetch_magister_token(playwright: Playwright, base_url: str, name: str, username: str, password:str, headless: bool = True):
    page = None
    try:
        playwright.selectors.set_test_id_attribute("id")

        chromium = playwright.chromium
        browser = await chromium.launch(headless=headless)
        page = await browser.new_page()

        print(f"Finding {name}'s token")
        await page.goto(f"https://{base_url}/oidc/redirect_callback.html")
        
        await page.get_by_test_id("username").fill(username)
        await page.get_by_test_id("username_submit").click()
        print("Submitted username")

        await page.wait_for_load_state("load")

        await page.get_by_test_id('i0118').fill(password)
        await page.get_by_test_id("idSIButton9").click()
        print("Submitted password")

        """
        Now check if id passwordError or id KmsiDescription is visible, 
        passwordError means password is wrong, 
        KmsiDescription means that the password is correct
        """
        signed_in_description = await page.get_by_test_id('KmsiDescription').is_visible(timeout=10)
        password_error = await page.get_by_test_id('passwordError').is_visible(timeout=10)

        if password_error:
            print("Password is incorrect")
            raise ValueError
        elif not signed_in_description:
            print("Program didn't continue for an unexpected reason")
            raise UnexpectedPageState
        
        await page.get_by_test_id('idSIButton9').click()
        print("Continued past Microsoft prompt")
        
        # Use a glob url pattern
        async with page.expect_response("**/api/leerlingen/**", timeout=0) as response_info:
            print("Found network leerling request")
            response = await response_info.value
            headers = await response.request.all_headers()
            url = response.url
        
        token = headers.get('authorization', None)
        user_id = url.split('/api/leerlingen/')[1].split("/")[0]

        if not token:
            raise ValueError("Unable to find token in requests")
        
        print(f"Bearer token found: {token[:20]}")
        print(f"User id found: {user_id}")

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