import requests
import json
from datetime import datetime, timedelta
import logging
from playwright.async_api import Playwright

async def fetch_magister_token(playwright: Playwright, name, username, password, headless = True):
    playwright.selectors.set_test_id_attribute("id")

    chromium = playwright.chromium
    browser = await chromium.launch(headless=headless)
    page = await browser.new_page()

    logging.debug(f"Finding {name}'s token")
    logging.debug("Going to Magister log-in page")
    await page.goto("https://middelharnis.magister.net/oidc/redirect_callback.html")
    
    logging.debug("Filling in username")
    await page.get_by_test_id("username").fill(username)
    await page.get_by_test_id("username_submit").click()

    logging.debug("Filling in password")
    await page.get_by_test_id('i0118').fill(password)
    await page.get_by_test_id("idSIButton9").click()

    logging.debug("Pressing 'Stay logged in'")
    await page.get_by_test_id('idSIButton9').click()
    
    # Use a glob url pattern
    async with page.expect_response("**/api/leerlingen/**") as response_info:
        logging.debug("Found network request with token")
        response = await response_info.value
        headers = await response.request.all_headers()
        url = response.url
    
    token = headers.get('authorization', None)
    user_id = url.split('/api/leerlingen/')[1].split("/")[0]
    logging.debug(f"Bearer token found: {token:.20f}")
    logging.debug(f"User id found: {user_id}")

    await browser.close()
    return token, user_id


def fetch_magister_calendar(user_id, bearer_token, days_to_fetch):
    headers = {
        "Authorization": bearer_token,
        "content-type": "application/json"
    }

    current_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_to_fetch)).strftime("%Y-%m-%d")

    url = f"https://middelharnis.magister.net/api/personen/{user_id}/afspraken?status=1&tot={end_date}&van={current_date}"

    r = requests.get(url, headers=headers)

    if r.ok:
        calendar = json.loads(r.text)
        return calendar
    else:
        return None