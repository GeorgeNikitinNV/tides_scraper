# Simple tides data scraper

This script scrapes tide data from the [Niwa](https://tides.niwa.co.nz/) website and publishes it to an MQTT broker. 

I wrote it to scrape info about tides and then use it in my Homeassist, but it can be used for any other purpose that requires data scraping and publishing to an MQTT broker.


## Installation

To install this script, you can use `uv`:

```sh
uv sync
```

## Usage

1. **Set up your environment**: Create a `.env` file with the necessary configuration, take `.env.example` as a reference.

2. **Run the script**: Execute the script using:

```sh
uv run main.py
```
