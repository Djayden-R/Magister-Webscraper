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


class HTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=CALENDAR_FOLDER, **kwargs)
    
    # Prevent scrapers from finding names of calendars
    def list_directory(self, path):
        self.send_error(404)
        return None


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

IP_ADRESS = get_ip()


def get_options():
    with open(OPTIONS_FILE_PATH, 'r') as f:
        options = json.load(f)

    # Load dictionary with credentials
    # Expected format: [{'username': username, 'password': password}, ...]
    credentials_list: list[dict[str, str]] = options['credentials']
    days_to_fetch: int = options['days_to_fetch']
    refresh_time: int = options['refresh_time']
    base_url: str = options['base_url']

    return credentials_list, days_to_fetch, refresh_time, base_url


def get_user_info(username: str):
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


def save_user_info(username: str, token: str, user_id: str):
    token_path = PROGRAM_PATH / "tokens.json"

    logging.info("Saving token to tokens.json")

    data = {}

    if token_path.exists():
        with open(token_path, 'r') as f:
            content = f.read()
            if content != "":
                data = json.loads(content)

    with open(token_path, 'w') as f: 
        data[username] = {"token": token, "user_id": user_id}
        json.dump(data, f, indent=2)


def start_http_server():
    server = http.server.ThreadingHTTPServer(("0.0.0.0", 15060), HTTPHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    logging.info(f"Started server on http://{IP_ADRESS}:15060")


async def main():
    if not CALENDAR_FOLDER.exists():
        CALENDAR_FOLDER.mkdir(parents=True, exist_ok=True)
        logging.info(f"Created folder: {CALENDAR_FOLDER}")
    
    start_http_server()
    credentials_list, days_to_fetch, refresh_time, base_url = get_options()

    if not credentials_list:
        logging.warning("Credentials not defined, exiting program...")
        return

    while True:
        for credenials in credentials_list:
            name = credenials.get('name', None)
            username = credenials.get('username', None)
            password = credenials.get('password', None)
            uuid = credenials.get('uuid', None)

            logging.info(f"Checking info for {username}")

            if not (name and username and password):
                logging.error(f"Invalid credentials found (name={name}, username={username}, password={password})")
                continue
            if not uuid:
                logging.error(f"You must set a uuid for every credential")
                continue
            
            token, user_id = get_user_info(username)

            calendar = None

            if token and user_id:
                logging.info("Token found in tokens.json")
                calendar = fetch_magister_calendar(base_url, user_id, token, days_to_fetch)
        
            if not (token and user_id) or not calendar:
                logging.info("Fetching token...")
                async with async_playwright() as playwright:
                    token, user_id = await fetch_magister_token(playwright, base_url, name, username, password)
            
            save_user_info(username, token, user_id)
            
            calendar = fetch_magister_calendar(base_url, user_id, token, days_to_fetch)

            if not calendar:
                logging.error("Unable to fetch magister calendar")
                continue

            ics_calendar = calendar_to_ics(calendar)

            file_name = f"{uuid}.ics"

            save_ics_file(ics_calendar, CALENDAR_FOLDER, file_name)

            logging.info(f"{name}'s calendar is hosted on http://{IP_ADRESS}:15060/{file_name}")

        await asyncio.sleep(refresh_time * 60)

if __name__ == "__main__":
    asyncio.run(main())