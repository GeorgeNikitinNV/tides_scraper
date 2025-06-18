import json
import logging
from datetime import datetime
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

logger.info(
    f"""Using settings: 
    Broker: {MQTT_BROKER}:{MQTT_PORT} 
    User: {MQTT_USER}
    URL: {URL}
    """
)


with sync_playwright() as p:
    logger.info("Launcing chromium browser")
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
