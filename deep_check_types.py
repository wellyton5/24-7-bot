import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def deep_check_types():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path_db = "/dayzxb_missions/dayzOffline.chernarusplus/db"

    try:
        ftp.cwd(path_db)
        bio = io.BytesIO()
        ftp.retrbinary("RETR types.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        # Procurar por qualquer bloco que tenha o nome Truck_01_Covered e ver tudo que tem nele
        pattern = re.compile(r'<type name="Truck_01_Covered">.*?</type>', re.DOTALL)
        matches = pattern.findall(content)

        print("--- BLOCOS Truck_01_Covered ENCONTRADOS ---")
        for m in matches:
            print(m)

        # Procurar por outros tipos que possam ter sido criados pelo usuário
        print("\n--- BUSCANDO TIPOS COM NOMINAIS ALTOS E CATEGORIA VEHICLES ---")
        # Regex para capturar nominal e name
        types = re.findall(
            r'<type name="([^"]+)".*?<nominal>(\d+)</nominal>.*?<category name="([^"]+)"/>',
            content,
            re.DOTALL,
        )
        for name, nominal, category in types:
            if int(nominal) > 10 and category == "vehicles":
                print(f"Tipo: {name}, Nominal: {nominal}, Categoria: {category}")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    deep_check_types()
