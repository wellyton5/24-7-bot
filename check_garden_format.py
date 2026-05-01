import os
import io
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()
F_HOST = os.getenv("FTP_HOST")
F_USER = os.getenv("FTP_USER")
F_PASS = os.getenv("FTP_PASS")


def search_garden_format():
    try:
        ftp = FTP(F_HOST)
        ftp.login(F_USER, F_PASS)
        ftp.cwd("/dayzxb/config")

        all_files = ftp.nlst()
        # Buscar em todos os ADMs disponíveis para encontrar UM exemplo sequer
        adm_files = [f for f in all_files if f.endswith(".ADM")]

        print(f"Buscando GardenPlot em {len(adm_files)} arquivos ADM...")

        found_examples = []
        for filename in sorted(adm_files, reverse=True):
            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {filename}", bio.write)
            content = bio.getvalue().decode("utf-8", errors="ignore")

            for line in content.split("\n"):
                if "garden" in line.lower() or "plot" in line.lower():
                    found_examples.append(f"[{filename}] {line.strip()}")
                    if len(found_examples) >= 10:
                        break
            if len(found_examples) >= 10:
                break

        if found_examples:
            print("\nExemplos encontrados:")
            for ex in found_examples:
                print(ex)
        else:
            print("Nenhum exemplo de garden/plot encontrado em todos os logs.")

        ftp.quit()
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    search_garden_format()
