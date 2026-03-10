import json
import logging
from fetch_magister import fetch_magister_calendar, fetch_magister_token
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
import asyncio
from ics_manager import calendar_to_ics, save_ics_file, read_ics_file

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
    print("Addon started, sleeping 10 seconds...")
    await asyncio.sleep(10)
    credentials_list, days_to_fetch = get_options()

    if not credentials_list:
        logging.warning("Credentials not defined, exiting program...")
        return

    for credenials in credentials_list:
        name = credenials.get('name', None)
        username = credenials.get('username', None)
        password = credenials.get('password', None)

        print(f"Checking info for {username}")

        if not (username and password):
            logging.error(f"Invalid credentials found (username={username}, password={password})")
            continue

        token, user_id = get_user_info(username)

        calendar = None

        if token and user_id:
            calendar = fetch_magister_calendar(user_id, token, days_to_fetch)
    
        if not (token and user_id) or not calendar:
            print("Fetching token...")
            async with async_playwright() as playwright:
                token, user_id = await fetch_magister_token(playwright, name, username, password)
        
        calendar = fetch_magister_calendar(user_id, token, days_to_fetch)

        if not calendar:
            print("Unable to fetch magister calendar")
            continue

        ics_calendar = calendar_to_ics(calendar)

        calendar_folder = PROGRAM_PATH / "calendars"

        save_ics_file(ics_calendar, calendar_folder, "Djayden_Magister.ics")

if __name__ == "__main__":
    asyncio.run(main())