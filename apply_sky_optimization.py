import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def apply_sky_optimization():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    mission_path = "/dayzxb_missions/dayzOffline.chernarusplus"
    ftp.cwd(mission_path)

    # --- 1. AJUSTE EM INIT.C ---
    print(f"Lendo {mission_path}/init.c...")
    bio_i = io.BytesIO()
    ftp.retrbinary("RETR init.c", bio_i.write)
    init_c = bio_i.getvalue().decode("utf-8", errors="ignore")

    print("Modificando init.c (Overcast)...")
    # De: weather.GetOvercast().Set(Math.RandomFloatInclusive(0.4, 0.6), 1, 0);
    # Para: weather.GetOvercast().Set(0, 0, 1);
    new_init_c = re.sub(
        r"weather\.GetOvercast\(\)\.Set\(Math\.RandomFloatInclusive\(.*?\),\s*1,\s*0\);",
        "weather.GetOvercast().Set(0, 0, 1);",
        init_c,
    )

    # Upload init.c
    bio_new_i = io.BytesIO(new_init_c.encode("utf-8"))
    ftp.storbinary("STOR init.c", bio_new_i)
    print("init.c atualizado.")

    # --- 2. AJUSTE EM CFGWEATHER.XML ---
    print(f"\nLendo {mission_path}/cfgweather.xml...")
    bio_w = io.BytesIO()
    ftp.retrbinary("RETR cfgweather.xml", bio_w.write)
    weather_xml = bio_w.getvalue().decode("utf-8", errors="ignore")

    print("Zerando Overcast no XML...")
    # Zerar limites de nebulosidade (overcast)
    # Padrão: <overcast> ... <limits min="0.1" max="1.0" /> ... </overcast>
    new_weather_xml = re.sub(
        r'(<overcast>.*?)<limits min=".*?" max=".*?" />',
        r'\1<limits min="0.0" max="0.0" />',
        weather_xml,
        flags=re.DOTALL,
    )
    # Zerar overcast atual
    new_weather_xml = re.sub(
        r'(<overcast>.*?)<current actual=".*?"',
        r'\1<current actual="0.0"',
        new_weather_xml,
        flags=re.DOTALL,
    )
    # Ajustar change-limits para 0
    new_weather_xml = re.sub(
        r'(<overcast>.*?)<changelimits min=".*?" max=".*?" />',
        r'\1<changelimits min="0.0" max="0.0" />',
        new_weather_xml,
        flags=re.DOTALL,
    )

    # Upload cfgweather.xml
    bio_new_w = io.BytesIO(new_weather_xml.encode("utf-8"))
    ftp.storbinary("STOR cfgweather.xml", bio_new_w)
    print("cfgweather.xml atualizado.")

    ftp.quit()
    print("\n--- OTIMIZAÇÃO DE CÉU LIMPO CONCLUÍDA ---")


if __name__ == "__main__":
    apply_sky_optimization()
