#!/usr/bin/python3
import json
import os
import subprocess
import time
from waveshare_epd import epd2in7_V2
from PIL import Image, ImageDraw, ImageFont

# Path to OpenCanary config file
CONFIG_PATH = "/etc/opencanaryd/opencanary.conf"
REFRESH_INTERVAL = 10  # Refresh every 10 seconds

def parse_config(config_path):
    """Parse the OpenCanary config and return active services."""
    if not os.path.exists(config_path):
        return ["Error: Config file not found"]

    try:
        with open(config_path, "r") as config_file:
            config = json.load(config_file)

        active_services = []
        for key, value in config.items():
            if isinstance(value, bool) and key.endswith(".enabled") and value:
                service_name = key.split(".")[0].upper()
                port_key = f"{service_name.lower()}.port"
                port = config.get(port_key, "N/A")
                active_services.append(f"{service_name} on Port {port}")

        return active_services or ["No active services found"]
    except json.JSONDecodeError as e:
        return [f"Error: Invalid JSON ({str(e)})"]
    except Exception as e:
        return [f"Error: {str(e)}"]

def check_honeypot_status():
    """Check if the honeypot service is running and return its status."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "opencanary.service"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0:
            return "Active"
        elif result.stdout.strip() == "inactive":
            return "Inactive"
        else:
            return f"Unknown status ({result.stdout.strip()})"
    except Exception as e:
        return f"Error checking status ({str(e)})"

def display_on_epaper(epd, status, services):
    """Display the honeypot status and services on the e-Paper display."""
    epd.init()
    epd.Clear()

    # Prepare the image and draw object
    image = Image.new("1", (epd.height, epd.width), 255)  # Clear screen (white)
    draw = ImageDraw.Draw(image)
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    font_status = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    font_heading = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    font_services = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)

    # Calculate total height of text block
    line_spacing = 5
    extra_spacing_after_status = 10  # Extra space after the status line
    title_height = draw.textbbox((0, 0), "Not a Honeypot", font=font_title)[3]
    status_height = draw.textbbox((0, 0), f"Status: {status}", font=font_status)[3]
    heading_height = draw.textbbox((0, 0), "Listening for:", font=font_heading)[3]
    services_height = len(services) * (draw.textbbox((0, 0), "A", font=font_services)[3] + line_spacing)
    total_text_height = title_height + status_height + heading_height + services_height + (line_spacing * 3) + extra_spacing_after_status

    # Calculate starting y-position to center the text block
    start_y = max(0, (epd.width - total_text_height) // 2)

    # Draw the text block
    y = start_y
    draw.text((10, y), "Not a Honeypot", font=font_title, fill=0)
    y += title_height + line_spacing

    draw.text((10, y), f"{status}", font=font_status, fill=0)
    y += status_height + line_spacing + extra_spacing_after_status

    draw.text((10, y), "Listening for:", font=font_heading, fill=0)
    y += heading_height + line_spacing

    for line in services[:8]:  # Display up to 8 services
        draw.text((10, y), line, font=font_services, fill=0)
        y += draw.textbbox((0, 0), line, font=font_services)[3] + line_spacing

    epd.display(epd.getbuffer(image))
    epd.sleep()

def main():
    epd = epd2in7_V2.EPD()

    last_status = None
    last_services = None

    try:
        while True:
            # Check honeypot status
            honeypot_status = check_honeypot_status()

            # Parse configuration
            services = parse_config(CONFIG_PATH)

            # Refresh the display only if there are changes
            if honeypot_status != last_status or services != last_services:
                print("Changes detected. Refreshing display...")
                display_on_epaper(epd, honeypot_status, services)
                last_status = honeypot_status
                last_services = services
            else:
                print("No changes detected. Skipping refresh...")

            # Wait before checking again
            time.sleep(REFRESH_INTERVAL)
    except KeyboardInterrupt:
        print("Exiting...")
        epd2in7_V2.epdconfig.module_exit()
    except Exception as e:
        print(f"Unexpected error: {e}")
        epd2in7_V2.epdconfig.module_exit()

if __name__ == "__main__":
    main()
