import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_event_groups():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus"

    try:
        ftp.cwd(path)
        bio = io.BytesIO()
        ftp.retrbinary("RETR cfgeventgroups.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.splitlines()
        print("--- BUSCANDO TRUCK EM CFGEVENTGROUPS.XML ---")
        for i, line in enumerate(lines):
            if "Truck" in line or "M3S" in line:
                print(f"\nMatch na linha {i + 1}:")
                # Mostrar contexto do grupo
                start = max(0, i - 10)
                end = min(len(lines), i + 5)
                for j in range(start, end):
                    print(f"  {j + 1}: {lines[j]}")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_event_groups()
