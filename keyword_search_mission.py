import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def string_search():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    base_path = "/dayzxb_missions/dayzOffline.chernarusplus"

    keywords = ["vara", "curta", "stick", "heli"]

    def walk(path):
        try:
            ftp.cwd(path)
            items = ftp.nlst()
            for item in items:
                if "." in item:
                    if (
                        item.endswith(".xml")
                        or item.endswith(".c")
                        or item.endswith(".json")
                    ):
                        bio = io.BytesIO()
                        ftp.retrbinary(f"RETR {item}", bio.write)
                        content = bio.getvalue().decode("utf-8", errors="ignore")
                        content_lower = content.lower()
                        for k in keywords:
                            if k in content_lower:
                                print(f"KEYWORD '{k}' ENCONTRADA EM: {path}/{item}")
                                break
                else:
                    walk(f"{path}/{item}".replace("//", "/"))
                    ftp.cwd("..")
        except:
            pass

    walk(base_path)
    ftp.quit()


if __name__ == "__main__":
    string_search()
