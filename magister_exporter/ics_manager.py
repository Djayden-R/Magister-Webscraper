from ics import Calendar, Event
import uuid
from pathlib import Path
import logging

def calendar_to_ics(calendar: dict[str, list]) -> Calendar:
    ics_calendar = Calendar()

    for event in calendar["Items"]:
        e = Event()
        e.name = event.get("Omschrijving", None)
        
        if not e.name or e.name == "flex":
            continue

        e.begin = event.get("Start", None).replace(" ", "")
        e.end = event.get("Einde", None).replace(" ", "")
        e.uid = str(uuid.uuid4())
        e.description = event.get("Inhoud", None)

        locations = event.get("Lokalen", None)
        location_str = ""
        if locations:
            for location in locations:
                location_str += location.get("Naam", None)

        e.location = location_str

        ics_calendar.events.add(e)
    
    return ics_calendar

def save_ics_file(ics_calendar: Calendar, base_path: Path, name: str):
    file_path = base_path / name
    print(f"Saved calendar to {file_path}")

    with open(file_path, 'w') as ics_file:
        ics_file.writelines(ics_calendar.serialize_iter())

def read_ics_file(base_path: Path, name: str) -> Calendar:
    file_path = base_path / name

    with open(file_path, 'r') as ics_file:
        file_content = ics_file.read()
    
    calendar = Calendar(file_content)

    return calendar