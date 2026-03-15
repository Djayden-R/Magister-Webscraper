# Magister Exporter

Magister Exporter is a Home Assistant app that automatically fetches your Magister calendar every so often and then hosts this calendar so it can be imported by a third-party service.

## Installation

[![Add Repository to HA][my-ha-badge]][my-ha-url]

Fill in your Magister credentials in the options menu and add a random uuid (get one [here](https://www.uuidgenerator.net/)) and configure the rest of the settings

## Requirements

- Home Assistant OS (not Container, Core or Supervised)
- A modern CPU architecture (AMD64 or ARM64)
- Around 1 GB of free space and RAM

## How does it work?

This program uses a headless browser that goes to Magister and uses your credentials to log-in. When the site is loaded, it fetches your token from the network requests and saves it. This token can be used to request your calendar, which will be formatted into .ics and then hosted on an HTTP server (default port 15060).

The file name will be the random uuid set in the configuration, this is done to protect your calendar from webscraping. In addition, the listing of the directories is also hidden, this means the URL is unknown to others and the files can safely be exposed to the internet and then be imported by a third-party calendar app. The following URL format is always used:
`http://[Home Assistant ip]:15060/[uuid].ics`

## How do I expose my calendars to the internet?

The reccomended practice is to use a reverse proxy, like NGINX proxy manager. This app can be installed from the default app store.

You should open up port `443` in your router settings and point it to the reverse proxy manager. And in NGINX you should add a custom URL (from DuckDNS for example) and point it to port `15060`. Below is a beginner-friendly tutorial for setting up NGINX:

- [NGINX tutorial](https://www.youtube.com/watch?v=CSbgLBcIuwE&t=345s)

[my-ha-badge]: https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg
[my-ha-url]: https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FDjayden-R%2FMagister-Exporter
