import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def global_truck_search():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    base_path = "/dayzxb_missions/dayzOffline.chernarusplus"

    def search_recursive(path):
        try:
            ftp.cwd(path)
            items = ftp.nlst()
            for item in items:
                # Filtrar arquivos XML, C, JSON
                if any(item.endswith(ext) for ext in [".xml", ".c", ".json"]):
                    bio = io.BytesIO()
                    ftp.retrbinary(f"RETR {item}", bio.write)
                    content = bio.getvalue().decode("utf-8", errors="ignore")
                    if "Truck_01_Covered" in content:
                        print(f"\n--- ENCONTRADO EM {path}/{item} ---")
                        lines = content.splitlines()
                        for i, line in enumerate(lines):
                            if "Truck_01_Covered" in line:
                                start = max(0, i - 10)
                                end = min(len(lines), i + 5)
                                print(f"Linha {i + 1}:")
                                for j in range(start, end):
                                    tag = ">> " if j == i else "   "
                                    print(f"{tag}{j + 1}: {lines[j].strip()}")
                elif "." not in item:
                    search_recursive(f"{path}/{item}".replace("//", "/"))
                    ftp.cwd("..")
        except:
            pass

    search_recursive(base_path)
    ftp.quit()


if __name__ == "__main__":
    global_truck_search()
