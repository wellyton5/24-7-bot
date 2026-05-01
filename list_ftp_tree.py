import ftplib, os
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/24-7-Bot/.env")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def traverse(ftp, path="/", depth=0):
    if depth > 3:
        return
    try:
        print("  " * depth + f"[{path}]")
        items = ftp.nlst(path)
        for i in items:
            # If it's a file, it usually contains a dot or is in a known list
            if "." in i:
                print("  " * (depth + 1) + i)
            else:
                # Potential directory
                traverse(
                    ftp,
                    i if i.startswith("/") else path.rstrip("/") + "/" + i,
                    depth + 1,
                )
    except Exception as e:
        # print('  ' * (depth + 1) + f"Error: {e}")
        pass


if __name__ == "__main__":
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        traverse(ftp)
        ftp.quit()
    except Exception as e:
        print(f"FTP Error: {e}")
