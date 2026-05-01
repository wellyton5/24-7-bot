import ftplib
import os
from dotenv import load_dotenv

load_dotenv()


def list_profile_json():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    target_dirs = ["/profile", "/dayzxb/config", "/dayzxb", "/"]

    for d in target_dirs:
        print(f"\n--- LISTING {d} ---")
        try:
            ftp.cwd(d)
            items = ftp.nlst()
            json_files = [i for i in items if i.lower().endswith(".json")]
            if json_files:
                for f in json_files:
                    size = ftp.size(f)
                    print(f"  [JSON] {f} ({size} bytes)")
            else:
                print("  No JSON files found.")
        except Exception as e:
            print(f"  Error: {e}")

    ftp.quit()


if __name__ == "__main__":
    list_profile_json()
