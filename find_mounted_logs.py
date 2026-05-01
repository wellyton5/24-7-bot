import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def find_mounted():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb/config"
    ftp.cwd(path)

    items = ftp.nlst()
    adms = [i for i in items if i.endswith(".ADM")]
    adms.sort(reverse=True)

    for adm in adms[:3]:  # Olha os últimos 3 ADMs
        print(f"\n--- PESQUISANDO EM: {adm} ---")
        try:
            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {adm}", bio.write)
            content = bio.getvalue().decode("utf-8", errors="ignore")

            lines = content.splitlines()
            for line in lines:
                lower_line = line.lower()
                if (
                    "mounted" in lower_line
                    or "unmounted" in lower_line
                    or "into" in lower_line
                ):
                    # Garantir que não seja log de tiro (hit into)
                    if "hit by" not in lower_line:
                        print(line)
        except Exception as e:
            print(f"Erro ao ler {adm}: {e}")

    ftp.quit()


if __name__ == "__main__":
    find_mounted()
