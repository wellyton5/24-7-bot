import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def read_weather_configs():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus"
    ftp.cwd(path)

    files = ["cfgweather.xml", "cfgenvironment.xml", "init.c"]

    for f in files:
        print(f"\n--- LENDO {f} ---")
        try:
            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {f}", bio.write)
            content = bio.getvalue().decode("utf-8", errors="ignore")

            # Mostrar trechos relevantes para neblina e neve
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if any(
                    k in line.lower()
                    for k in ["fog", "snow", "weather", "rain", "overcast"]
                ):
                    start = max(0, i - 1)
                    end = min(len(lines), i + 3)
                    for j in range(start, end):
                        print(f"  {f}:{j + 1}: {lines[j]}")
        except Exception as e:
            print(f"Erro ao ler {f}: {e}")

    ftp.quit()


if __name__ == "__main__":
    read_weather_configs()
