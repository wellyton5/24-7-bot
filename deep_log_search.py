import os
import io
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()
F_HOST = os.getenv("FTP_HOST")
F_USER = os.getenv("FTP_USER")
F_PASS = os.getenv("FTP_PASS")


def deep_search(files):
    try:
        ftp = FTP(F_HOST)
        ftp.login(F_USER, F_PASS)

        for filename in files:
            path = f"/dayzxb/config/{filename}"
            print(f"\n--- BUSCANDO EM {filename} ---")

            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {path}", bio.write)
            content = bio.getvalue().decode("utf-8", errors="ignore")

            lines = content.split("\n")
            count = 0
            for line in lines:
                if any(
                    kw in line.lower()
                    for kw in ["garden", "plot", "fireplace", "fogueira", "explosi"]
                ):
                    print(line.strip())
                    count += 1
            print(f"Total de ocorrências em {filename}: {count}")

        ftp.quit()
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    # Logs das últimas horas do Mar 7 / Mar 8 UTC
    logs_to_search = [
        "DayZServer_X1_x64_2026-03-07_19-57-12.ADM",
        "DayZServer_X1_x64_2026-03-07_19-57-12.RPT",
        "DayZServer_X1_x64_2026-03-07_18-35-27.ADM",
        "DayZServer_X1_x64_2026-03-07_18-35-27.RPT",
    ]
    deep_search(logs_to_search)
