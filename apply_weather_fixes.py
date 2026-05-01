import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def apply_weather_fixes():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    mission_path = "/dayzxb_missions/dayzOffline.chernarusplus"

    # --- 1. AJUSTE EM INIT.C ---
    print(f"Acessando {mission_path}/init.c...")
    ftp.cwd(mission_path)

    bio_i = io.BytesIO()
    ftp.retrbinary("RETR init.c", bio_i.write)
    init_c = bio_i.getvalue().decode("utf-8", errors="ignore")

    # Backup
    with open("init.c.bak", "w", encoding="utf-8") as f:
        f.write(init_c)

    print("Modificando init.c (Fog)...")
    # De: weather.GetFog().Set(Math.RandomFloatInclusive(0.05, 0.1), 1, 0);
    # Para: weather.GetFog().Set(0, 0, 1);
    new_init_c = re.sub(
        r"weather\.GetFog\(\)\.Set\(Math\.RandomFloatInclusive\(.*?\),\s*1,\s*0\);",
        "weather.GetFog().Set(0, 0, 1);",
        init_c,
    )

    # Upload init.c
    bio_new_i = io.BytesIO(new_init_c.encode("utf-8"))
    ftp.storbinary("STOR init.c", bio_new_i)
    print("init.c atualizado.")

    # --- 2. AJUSTE EM CFGWEATHER.XML ---
    print(f"\nModificando {mission_path}/cfgweather.xml...")
    bio_w = io.BytesIO()
    ftp.retrbinary("RETR cfgweather.xml", bio_w.write)
    weather_xml = bio_w.getvalue().decode("utf-8", errors="ignore")

    # Backup
    with open("cfgweather.xml.bak", "w", encoding="utf-8") as f:
        f.write(weather_xml)

    # Zerar limites de neblina (fog)
    # Padrão: <fog> ... <limits min="0.0" max="0.8" /> ... </fog>
    print("Zerando limites de Fog...")
    new_weather_xml = re.sub(
        r'(<fog>.*?)<limits min=".*?" max=".*?" />',
        r'\1<limits min="0.0" max="0.0" />',
        weather_xml,
        flags=re.DOTALL,
    )
    # Zerar neblina atual
    new_weather_xml = re.sub(
        r'(<fog>.*?)<current actual=".*?"',
        r'\1<current actual="0.0"',
        new_weather_xml,
        flags=re.DOTALL,
    )

    # Zerar limites de neve (snowfall)
    print("Zerando limites de Snowfall...")
    new_weather_xml = re.sub(
        r'(<snowfall>.*?)<limits min=".*?" max=".*?" />',
        r'\1<limits min="0.0" max="0.0" />',
        new_weather_xml,
        flags=re.DOTALL,
    )
    # Zerar neve atual e thresholds
    new_weather_xml = re.sub(
        r'(<snowfall>.*?)<current actual=".*?"',
        r'\1<current actual="0.0"',
        new_weather_xml,
        flags=re.DOTALL,
    )
    new_weather_xml = re.sub(
        r'(<snowfall>.*?)<thresholds min=".*?" max=".*?"',
        r'\1<thresholds min="1.1" max="1.2"',
        new_weather_xml,
        flags=re.DOTALL,
    )

    # Upload cfgweather.xml
    bio_new_w = io.BytesIO(new_weather_xml.encode("utf-8"))
    ftp.storbinary("STOR cfgweather.xml", bio_new_w)
    print("cfgweather.xml atualizado.")

    ftp.quit()
    print("\n--- TODOS OS AJUSTES DE CLIMA CONCLUÍDOS ---")


if __name__ == "__main__":
    apply_weather_fixes()
