import os
import json
import io
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()
F_HOST = os.getenv("FTP_HOST")
F_USER = os.getenv("FTP_USER")
F_PASS = os.getenv("FTP_PASS")


def check_free_build():
    try:
        print(f"Conectando ao FTP: {F_HOST}...")
        ftp = FTP(F_HOST)
        ftp.login(F_USER, F_PASS)

        cfg_path = "/dayzxb_missions/dayzOffline.chernarusplus/cfggameplay.json"
        print(f"Baixando {cfg_path}...")

        bio = io.BytesIO()
        ftp.retrbinary(f"RETR {cfg_path}", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        data = json.loads(content)

        bbd = data.get("BaseBuildingData", {})
        cd = bbd.get("ConstructionData", {})
        hd = bbd.get("HologramData", {})

        status = {
            "disableDistanceCheck": cd.get("disableDistanceCheck"),
            "disableIsCollidingCheck": cd.get("disableIsCollidingCheck"),
            "disableIsCollidingGPlotCheck": hd.get("disableIsCollidingGPlotCheck"),
            "disableIsPlacementPermittedCheck": hd.get(
                "disableIsPlacementPermittedCheck"
            ),
            "disableIsBaseViableCheck": hd.get("disableIsBaseViableCheck"),
        }

        print("\n--- STATUS CONSTRUÇÃO LIVRE ---")
        is_free = all(status.values())
        for k, v in status.items():
            print(f"{k}: {'✅ TRUE (Livre)' if v else '❌ FALSE (Restrito)'}")

        if is_free:
            print("\nRESULTADO: MODO CONSTRUÇÃO LIVRE ESTÁ 100% ATIVO.")
        else:
            print("\nRESULTADO: O MODO CONSTRUÇÃO LIVRE ESTÁ PARCIALMENTE RESTRITO.")

        ftp.quit()
    except Exception as e:
        print(f"Erro ao verificar JSON: {e}")


if __name__ == "__main__":
    check_free_build()
