import ftplib
import os
import io
from dotenv import load_dotenv

load_dotenv()


def check_wreck_loot():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus"

    try:
        ftp.cwd(path)
        bio = io.BytesIO()
        ftp.retrbinary("RETR cfgspawnabletypes.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.splitlines()
        wrecks = ["Wreck_Mi8", "Wreck_UH1Y", "Wreck_Mi8_Crashed"]

        print("--- LOOT DOS DESTROÇOS EM CFGSPAWNABLETYPES.XML ---")
        for wreck in wrecks:
            print(f"\nBuscando {wreck}...")
            found = False
            for i, line in enumerate(lines):
                if f'type name="{wreck}"' in line:
                    found = True
                    for j in range(i, min(i + 100, len(lines))):
                        print(lines[j])
                        if "</type>" in lines[j]:
                            break
                    break
            if not found:
                print(f"{wreck} não encontrado.")

        # Também procurar por "ShortStick" ou "WoodenStick" no arquivo todo
        print("\n--- BUSCA POR STICK EM CFGSPAWNABLETYPES.XML ---")
        for i, line in enumerate(lines):
            if "Stick" in line:
                print(f"Linha {i + 1}: {line.strip()}")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_wreck_loot()
