import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def deep_search_truck_refs():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    base_path = "/dayzxb_missions/dayzOffline.chernarusplus"

    def walk(path):
        try:
            ftp.cwd(path)
            items = ftp.nlst()
            for item in items:
                if "." in item:
                    if item.endswith(".xml"):
                        bio = io.BytesIO()
                        ftp.retrbinary(f"RETR {item}", bio.write)
                        content = bio.getvalue().decode("utf-8", errors="ignore")
                        if "Truck_01_Covered" in content:
                            print(f"\nREFERÊNCIA EM: {path}/{item}")
                            lines = content.splitlines()
                            for i, line in enumerate(lines):
                                if "Truck_01_Covered" in line:
                                    # Mostrar contexto (2 linhas antes, 1 depois)
                                    start = max(0, i - 2)
                                    end = min(len(lines), i + 2)
                                    print(f"  Linha {i + 1}:")
                                    for j in range(start, end):
                                        print(f"    {lines[j].strip()}")
                else:
                    walk(f"{path}/{item}".replace("//", "/"))
                    ftp.cwd("..")
        except:
            pass

    walk(base_path)
    ftp.quit()


if __name__ == "__main__":
    deep_search_truck_refs()
