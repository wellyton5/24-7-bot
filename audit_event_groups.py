import ftplib
import os
import io
import re
from dotenv import load_dotenv

load_dotenv()


def audit_event_groups():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    path = "/dayzxb_missions/dayzOffline.chernarusplus"

    try:
        ftp.cwd(path)
        bio = io.BytesIO()
        ftp.retrbinary("RETR cfgeventgroups.xml", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        # Regex para pegar todos os childrens de todos os grupos
        pattern = re.compile(r'<group name="([^"]+)">(.*?)</group>', re.DOTALL)
        matches = pattern.findall(content)

        print("--- AUDITORIA DE GRUPOS DE EVENTO ---")
        for group_name, group_content in matches:
            # Se o grupo parecer militar ou de comboio
            if any(
                k in group_name
                for k in [
                    "Military",
                    "Convoy",
                    "Train",
                    "Heli",
                    "Abandoned",
                    "Supply",
                    "Ambush",
                ]
            ):
                type_matches = re.findall(r'type="([^"]+)"', group_content)
                for t in type_matches:
                    # Se o tipo NÃO começar com Land_wreck, StaticObj_Wreck ou similar
                    # E for um veículo conhecido
                    if "Truck" in t or "V3S" in t or "M3S" in t:
                        if not any(k in t for k in ["wreck", "Wreck", "aban", "DE"]):
                            print(
                                f"ALERTA: Tipo suspeito '{t}' no grupo '{group_name}'"
                            )
                            print(group_content)

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    audit_event_groups()
