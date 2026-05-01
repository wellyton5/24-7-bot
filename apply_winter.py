import ftplib, os, json
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")

MISSION_PATH = "/dayzxb_missions/dayzOffline.chernarusplus"

NEW_WEATHER = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<weather reset="1" enable="1">
    <overcast>
        <current actual="0.4" time="120" duration="240" />
        <limits min="0.1" max="1.0" />
        <timelimits min="900" max="3600" />
        <changelimits min="0.2" max="0.6" />
    </overcast>
    <fog>
        <current actual="0.1" time="120" duration="240" />
        <limits min="0.0" max="0.8" />
        <timelimits min="600" max="1800" />
        <changelimits min="0.3" max="0.7" />
    </fog>
    <rain>
        <current actual="0.0" time="120" duration="240" />
        <limits min="0.0" max="0.0" />
        <timelimits min="300" max="600" />
        <changelimits min="0.0" max="0.0" />
        <thresholds min="0.5" max="1.0" end="120" />
    </rain>
    <snowfall>
        <current actual="0.0" time="120" duration="240" />
        <limits min="0.0" max="1.0" />
        <timelimits min="300" max="1200" />
        <changelimits min="0.4" max="1.0" />
        <thresholds min="0.75" max="0.9" end="120" />
    </snowfall>
    <wind>
        <maxspeed>45</maxspeed>
        <params min="0.2" max="1.0" frequency="30" />
    </wind>
    <storm density="0.0" threshold="1.1" timeout="0"/>
</weather>"""


def update_winter():
    try:
        # Load original backup to ensure we start from a clean baseline
        backup_json = "/home/ubuntu/24-7-Bot/backups/cfggameplay.json.bak"
        if not os.path.exists(backup_json):
            print(f"Error: {backup_json} not found.")
            return

        with open(backup_json, "r") as f:
            gameplay = json.load(f)

        # 1. Temperature moderation (1°C to 8°C)
        gameplay["WorldsData"]["environmentMinTemps"] = [1] * 12
        gameplay["WorldsData"]["environmentMaxTemps"] = [8] * 12
        gameplay["WorldsData"]["WeatherData"]["overcast"] = 0.4

        # 2. Health regeneration (15.0 to negate cold HP loss)
        gameplay["Buffs"]["HealthRegen"] = 15.0

        # 3. Full disease immunity
        gameplay["Buffs"]["DiseaseImmunity"] = {
            "cholera": True,
            "parasites": True,
            "influenza": True,
            "salmonella": True,
            "cold": True,
            "poisoning": True,
            "woundInfection": True,
        }

        # Save winter files
        with open("/home/ubuntu/24-7-Bot/winter_cfggameplay.json", "w") as f:
            json.dump(gameplay, f, indent=4)

        with open("/home/ubuntu/24-7-Bot/winter_cfgweather.xml", "w") as f:
            f.write(NEW_WEATHER)

        # Upload via FTP
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)

        print("Uploading cfgweather.xml (Sakhal Dynamic)...")
        with open("/home/ubuntu/24-7-Bot/winter_cfgweather.xml", "rb") as f:
            ftp.storbinary(f"STOR {MISSION_PATH}/cfgweather.xml", f)

        print("Uploading cfggameplay.json (Moderate Winter & Immunity)...")
        with open("/home/ubuntu/24-7-Bot/winter_cfggameplay.json", "rb") as f:
            ftp.storbinary(f"STOR {MISSION_PATH}/cfggameplay.json", f)

        ftp.quit()
        print("Winter deployment successful.")

    except Exception as e:
        print(f"Update error: {e}")


if __name__ == "__main__":
    update_winter()
