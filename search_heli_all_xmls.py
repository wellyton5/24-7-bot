import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def search_heli():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    dirs = [
        "/dayzxb_missions/dayzOffline.chernarusplus",
        "/dayzxb_missions/dayzOffline.chernarusplus/db",
    ]

    found = False
    for d in dirs:
        print(f"\n--- BUSCANDO EM {d} ---")
        try:
            ftp.cwd(d)
            items = ftp.nlst()
            xmls = [f for f in items if f.lower().endswith(".xml")]

            for x in xmls:
                bio = io.BytesIO()
                ftp.retrbinary(f"RETR {x}", bio.write)
                content = bio.getvalue().decode("utf-8", errors="ignore")

                if "Heli" in content or "Heli" in x or "crash" in content.lower():
                    print(f"ENCONTRADO em {x}!")
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        if "Heli" in line or "crash" in line.lower():
                            # Mostrar contexto
                            start = max(0, i - 2)
                            end = min(len(lines), i + 5)
                            for j in range(start, end):
                                print(f"  {x}:{j + 1}: {lines[j]}")
                            found = True
                            # Só mostra os primeiros matches de cada arquivo
                            if i > 50 and found:
                                break
        except Exception as e:
            print(f"Erro em {d}: {e}")

    ftp.quit()


if __name__ == "__main__":
    search_heli()
