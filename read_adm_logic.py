import os
import io
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()
F_HOST = os.getenv("FTP_HOST")
F_USER = os.getenv("FTP_USER")
F_PASS = os.getenv("FTP_PASS")


def read_latest_adm(filename):
    try:
        ftp = FTP(F_HOST)
        ftp.login(F_USER, F_PASS)

        path = f"/dayzxb/config/{filename}"
        print(f"Lendo {path}...")

        bio = io.BytesIO()
        ftp.retrbinary(f"RETR {path}", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.split("\n")
        print(f"Total de linhas: {len(lines)}")

        # Filtrar por termos interessantes
        interesting = [
            l
            for l in lines
            if any(
                kw in l.lower()
                for kw in [
                    "garden",
                    "plot",
                    "built",
                    "placed",
                    "yasmin",
                    "fenix",
                    "stone",
                ]
            )
        ]

        print("\n--- LINHAS ENCONTRADAS ---")
        for l in interesting[-50:]:  # Mostrar as últimas 50 interessantes
            print(l.strip())

        ftp.quit()
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    # Usando o nome do arquivo identificado no passo anterior
    read_latest_adm("DayZServer_X1_x64_2026-03-07_19-57-12.ADM")
