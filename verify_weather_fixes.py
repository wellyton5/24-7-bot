import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def verify_weather_fixes():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    mission_path = "/dayzxb_missions/dayzOffline.chernarusplus"
    ftp.cwd(mission_path)

    # 1. Verificar init.c
    print("--- VERIFICANDO INIT.C ---")
    bio_i = io.BytesIO()
    ftp.retrbinary("RETR init.c", bio_i.write)
    content_i = bio_i.getvalue().decode("utf-8", errors="ignore")
    if "weather.GetFog().Set(0, 0, 1);" in content_i:
        print("[SUCCESS] Fog zerado no init.c")
    else:
        print("[ERROR] Fog NÃO encontrado ou incorreto no init.c")

    # 2. Verificar cfgweather.xml
    print("\n--- VERIFICANDO CFGWEATHER.XML ---")
    bio_w = io.BytesIO()
    ftp.retrbinary("RETR cfgweather.xml", bio_w.write)
    content_w = bio_w.getvalue().decode("utf-8", errors="ignore")

    if '<fog><current actual="0.0"' in content_w.replace(" ", "").replace(
        "\n", ""
    ).replace("\t", ""):  # Simplified check
        print("[SUCCESS] Fog actual zerado no XML")
    else:
        # More robust check
        import re

        fog_match = re.search(
            r'<fog>.*?<limits min="0\.0" max="0\.0" />', content_w, re.DOTALL
        )
        if fog_match:
            print("[SUCCESS] Fog limits zerados no XML")
        else:
            print("[ERROR] Fog limits incorretos no XML")

    snow_match = re.search(
        r'<snowfall>.*?<limits min="0\.0" max="0\.0" />', content_w, re.DOTALL
    )
    if snow_match:
        print("[SUCCESS] Snowfall limits zerados no XML")
    else:
        print("[ERROR] Snowfall limits incorretos no XML")

    ftp.quit()


if __name__ == "__main__":
    verify_weather_fixes()
