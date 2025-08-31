import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import paho.mqtt.publish as publish
from environs import env
from playwright.sync_api import sync_playwright

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add console handler to output logs to CLI
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Read .env into os.environ
env.read_env()

# MQTT configuration
MQTT_BROKER = env("MQTT_BROKER")
MQTT_PORT = env.int("MQTT_PORT")
MQTT_USER = env("MQTT_USER")
MQTT_PASS = env("MQTT_PASS")
# URL to scrape
URL = env("URL")

# Cache configuration
CACHE_FILE = Path(__file__).parent / "tide_cache.json"
CACHE_DURATION_HOURS = 1

logger.debug(
    f"""Using settings: 
    Broker: {MQTT_BROKER}:{MQTT_PORT} 
    User: {MQTT_USER}
    URL: {URL}
    Cache file: {CACHE_FILE}
    """
)


def load_cached_data():
    """Load cached data from file if it exists and is fresh."""
    if not CACHE_FILE.exists():
        logger.info("No cache file found")
        return None

    try:
        with open(CACHE_FILE, "r") as f:
            cached_data = json.load(f)

        # Check if cache is still fresh
        last_updated = datetime.fromisoformat(cached_data["last_updated"])
        cache_age = datetime.now(ZoneInfo("Pacific/Auckland")) - last_updated

        if cache_age < timedelta(hours=CACHE_DURATION_HOURS):
            logger.info(f"Using cached data (age: {cache_age})")
            return cached_data
        else:
            logger.info(f"Cache expired (age: {cache_age})")
            return None

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Error reading cache file: {e}")
        return None


def save_cached_data(data):
    """Save data to cache file."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Data cached to {CACHE_FILE}")
    except Exception as e:
        logger.error(f"Error saving cache: {e}")


def scrape_tide_data():
    """Scrape fresh tide data from the website."""
    logger.info("Scraping fresh data from website")

    with sync_playwright() as p:
        logger.info("Launching chromium browser")
        browser = p.chromium.launch()
        page = browser.new_page()
        logger.info(f"Navigating to URL: {URL}")
        page.goto(URL)
        page.wait_for_selector("table.table-striped", timeout=30000)  # Wait up to 30s

        # Extract all rows from the table
        logger.info("Selector found, extracting rows from table")
        rows = page.query_selector_all("table.table-striped tbody tr")
        tide_list_of_records = []
        for row in rows:
            date = row.query_selector("th").text_content().strip()
            value = row.query_selector("td").text_content().replace("m", "").strip()
            tide_list_of_records.append({"date": date, "value": float(value)})

        tide_payload = {
            "last_updated": datetime.now(ZoneInfo("Pacific/Auckland")).isoformat(),
            "data": tide_list_of_records,
        }
        browser.close()

        return tide_payload


def main():
    """Main function that handles caching logic."""
    # Try to load cached data first
    tide_payload = load_cached_data()

    # If no valid cached data, scrape fresh data
    if tide_payload is None:
        tide_payload = scrape_tide_data()
        save_cached_data(tide_payload)

    # Publish to MQTT as JSON
    logger.info("Publishing to MQTT as JSON")
    auth = (
        {"username": MQTT_USER, "password": MQTT_PASS}
        if MQTT_USER and MQTT_PASS
        else None
    )
    publish.single(
        "homeassistant/sensor/tide_table/state",
        json.dumps(tide_payload),
        hostname=MQTT_BROKER,
        port=MQTT_PORT,
        auth=auth,
    )

    logger.info("All done!")


if __name__ == "__main__":
    main()
