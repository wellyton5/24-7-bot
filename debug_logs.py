import ftplib, os
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def find_latest_adm_log(ftp):
    found_any = False
    for path in ["/dayzxb/config", "/dayzxb", "/profile"]:
        try:
            print(f"Checking {path}...")
            ftp.cwd(path)
            items = ftp.nlst()
            adm_files = [f"{path}/{f}" for f in items if f.lower().endswith(".adm")]
            if adm_files:
                adm_files.sort()
                print(f"Found {len(adm_files)} .ADM files in {path}")
                for f in adm_files[-3:]:  # Print last 3
                    size = ftp.size(f)
                    print(f"  - {f} ({size} bytes)")
                found_any = True
        except Exception as e:
            print(f"  - Error in {path}: {e}")
            continue
    if not found_any:
        print("No .ADM files found in any standard path.")


if __name__ == "__main__":
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        find_latest_adm_log(ftp)
        ftp.quit()
    except Exception as e:
        print(f"FTP Error: {e}")
