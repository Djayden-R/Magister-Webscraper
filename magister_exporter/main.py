import json
import logging
from fetch_magister import fetch_magister_calendar, fetch_magister_token
from pathlib import Path
from playwright.async_api import async_playwright
import asyncio
from ics_manager import calendar_to_ics, save_ics_file, read_ics_file
import http.server
from http.server import SimpleHTTPRequestHandler
import socket
import threading

PROGRAM_PATH = Path("/usr/src/app")
OPTIONS_FILE_PATH = Path("/data/options.json")
CALENDAR_FOLDER = PROGRAM_PATH / "calendars"


# Source - https://stackoverflow.com/a/52531444
# Posted by Andy Hayden, modified by community. See post 'Timeline' for change history
# Retrieved 2026-03-11, License - CC BY-SA 4.0

class HTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=CALENDAR_FOLDER, **kwargs)


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


def save_user_info(username, token, user_id):
    token_path = PROGRAM_PATH / "tokens.json"

    print("Saving token to tokens.json")

    if token_path.exists():
        with open(token_path, 'r') as f:
            content = f.read()
            if content != "":
                print(content)
                data = json.loads(content)
                print(f"Data found: {data}")
            else:
                data = {}
    else:
        data = {}

    with open(token_path, 'w') as f: 
        data[username] = {"token": token, "user_id": user_id}
        json.dump(data, f, indent=2)


# Source - https://stackoverflow.com/q/63928479
# Posted by Elie, modified by community. See post 'Timeline' for change history
# Retrieved 2026-03-11, License - CC BY-SA 4.0

def start_http_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    server = http.server.ThreadingHTTPServer((ip, 15060), HTTPHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    print(f"Started server on http://{ip}:15060")


async def main():
    if not CALENDAR_FOLDER.exists():
        CALENDAR_FOLDER.mkdir(parents=True, exist_ok=True)
        print(f"Created folder: {CALENDAR_FOLDER}")
    
    start_http_server()
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
            print("Token found in tokens.json")
            calendar = fetch_magister_calendar(user_id, token, days_to_fetch)
    
        if not (token and user_id) or not calendar:
            print("Fetching token...")
            async with async_playwright() as playwright:
                token, user_id = await fetch_magister_token(playwright, name, username, password)
        
        save_user_info(username, token, user_id)
        
        calendar = fetch_magister_calendar(user_id, token, days_to_fetch)

        if not calendar:
            print("Unable to fetch magister calendar")
            continue

        ics_calendar = calendar_to_ics(calendar)

        save_ics_file(ics_calendar, CALENDAR_FOLDER, "Djayden_Magister.ics")

if __name__ == "__main__":
    asyncio.run(main())