import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def deep_search_stick():
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
                if "." in item:  # Provável arquivo
                    if (
                        item.endswith(".xml")
                        or item.endswith(".c")
                        or item.endswith(".json")
                    ):
                        bio = io.BytesIO()
                        ftp.retrbinary(f"RETR {item}", bio.write)
                        content = bio.getvalue().decode("utf-8", errors="ignore")
                        if "ShortStick" in content or "WoodenStick" in content:
                            print(f"VALOR ENCONTRADO EM: {path}/{item}")
                            for i, line in enumerate(content.splitlines()):
                                if "ShortStick" in line or "WoodenStick" in line:
                                    print(f"  [{i + 1}] {line.strip()}")
                else:  # Diretório
                    walk(f"{path}/{item}".replace("//", "/"))
                    ftp.cwd("..")
        except:
            pass

    walk(base_path)
    ftp.quit()


if __name__ == "__main__":
    deep_search_stick()
