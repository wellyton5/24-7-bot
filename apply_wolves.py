import ftplib, os
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")

MISSION_PATH = "/dayzxb_missions/dayzOffline.chernarusplus"


def apply_wolves():
    try:
        # 1. Prepare Modified events.xml
        with open("/home/ubuntu/24-7-Bot/backups/events.xml.bak", "r") as f:
            events_content = f.read()

        # Increase nominal to 50, min to 45, max to 48
        # This allows 20 extra wolves for the cities
        new_events = events_content.replace(
            '<event name="AnimalWolf">\n        <nominal>30</nominal>\n        <min>27</min>\n        <max>29</max>',
            '<event name="AnimalWolf">\n        <nominal>50</nominal>\n        <min>45</min>\n        <max>48</max>',
        )

        # 2. Prepare Modified wolf_territories.xml
        with open("/home/ubuntu/24-7-Bot/backups/wolf_territories.xml.bak", "r") as f:
            territories_content = f.read()

        # Add city territories at the end before </territory-type>
        city_territories = """
    <territory color="4291611852">
        <zone name="HuntingGround" smin="0" smax="0" dmin="0" dmax="0" x="6644" z="2595" r="150"/> <!-- Cherno Square -->
        <zone name="Rest" smin="0" smax="0" dmin="0" dmax="0" x="6533" z="2446" r="50"/>
    </territory>
    <territory color="4291611852">
        <zone name="HuntingGround" smin="0" smax="0" dmin="0" dmax="0" x="10467" z="2275" r="150"/> <!-- Elektro Square -->
        <zone name="Rest" smin="0" smax="0" dmin="0" dmax="0" x="10550" z="2350" r="50"/>
    </territory>
    <territory color="4291611852">
        <zone name="HuntingGround" smin="0" smax="0" dmin="0" dmax="0" x="12061" z="9071" r="150"/> <!-- Berezino Church -->
        <zone name="Rest" smin="0" smax="0" dmin="0" dmax="0" x="12150" z="9150" r="50"/>
    </territory>
"""
        new_territories = territories_content.replace(
            "</territory-type>", city_territories + "</territory-type>"
        )

        # Write temporary files
        with open("/home/ubuntu/24-7-Bot/urban_events.xml", "w") as f:
            f.write(new_events)
        with open("/home/ubuntu/24-7-Bot/urban_wolf_territories.xml", "w") as f:
            f.write(new_territories)

        # Upload
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)

        print("Uploading urban_events.xml to db/events.xml...")
        with open("/home/ubuntu/24-7-Bot/urban_events.xml", "rb") as f:
            ftp.storbinary(f"STOR {MISSION_PATH}/db/events.xml", f)

        print("Uploading urban_wolf_territories.xml to env/wolf_territories.xml...")
        with open("/home/ubuntu/24-7-Bot/urban_wolf_territories.xml", "rb") as f:
            ftp.storbinary(f"STOR {MISSION_PATH}/env/wolf_territories.xml", f)

        ftp.quit()
        print("Urban Wolf configuration uploaded. Waiting for auto-restart.")

    except Exception as e:
        print(f"Apply error: {e}")


if __name__ == "__main__":
    apply_wolves()
