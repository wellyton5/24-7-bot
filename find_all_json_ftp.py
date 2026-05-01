import ftplib
import os
from dotenv import load_dotenv

load_dotenv()


def find_all_json():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    found_files = []

    def walk(path):
        try:
            ftp.cwd(path)
            items = ftp.nlst()
            for item in items:
                # Se tem ponto, supomos que é arquivo ou extensão comum
                if "." in item:
                    if item.lower().endswith(".json"):
                        full_path = f"{path}/{item}".replace("//", "/")
                        found_files.append(full_path)
                        print(f"ENCONTRADO: {full_path}")
                else:
                    # Supomos que é diretório
                    walk(f"{path}/{item}".replace("//", "/"))
                    ftp.cwd("..")  # Volta um nível
        except:
            pass

    walk("/")
    ftp.quit()

    print("\n--- Todos os JSONs encontrados ---")
    for f in found_files:
        print(f)


if __name__ == "__main__":
    find_all_json()
