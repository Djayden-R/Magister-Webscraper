import json
import logging
from fetch_magister import fetch_magister_calendar, fetch_magister_token
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
import asyncio

PROGRAM_PATH = Path("/usr/src/app")
OPTIONS_FILE_PATH = "/data/options.json"


def get_options():
    with open(OPTIONS_FILE_PATH, 'r') as f:
        options = json.load(f)

    # Load dictionary with credentials
    # Expected format: [{'username': username, 'password': password}, ...]
    credentials_list: list[dict] = options['credentials']
    days_to_fetch: int = options['days_to_fetch']

    return credentials_list, days_to_fetch


def get_user_info(username):
    token_path = PROGRAM_PATH / "tokens.json"

    token = user_id = None

    if token_path.exists():
        with open(token_path, 'r') as f:
            data = json.load(f)

        user_info = data.get(username, None)

        if user_info:
            token = user_info.get("token", None)
            user_id = user_info.get("user_id", None)
            
    return token, user_id


async def main():
    credentials_list, days_to_fetch = get_options()

    if not credentials_list:
        logging.warning("Credentials not defined, exiting program...")
        return

    for credenials in credentials_list:
        name = credenials.get('name', None)
        username = credenials.get('username', None)
        password = credenials.get('password', None)

        if not (username and password):
            logging.error(f"Invalid credentials found (username={username}, password={password})")
            continue

        token, user_id = get_user_info(username)

        if token and user_id:
            calendar = fetch_magister_calendar(user_id, token, days_to_fetch)
    
        if not (token and user_id) or not calendar:
            async with async_playwright() as playwright:
                token, user_id = await fetch_magister_token(playwright, name, username, password)
        
        calendar = fetch_magister_calendar(user_id, token, days_to_fetch)

        lessons = calendar['Items']
        prev_day = None

        for lesson in lessons:
            date_str = lesson["Start"]
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            day = date.strftime("%A (%d/%m)")

            if day != prev_day:
                logging.info(day)
                prev_day = day

            logging.info(f"{lesson['LesuurVan']}e hour - {lesson['Omschrijving']} {lesson['Lokatie']}")

if __name__ == "__main__":
    asyncio.run(main())