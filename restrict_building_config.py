import os
import json
import io
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()
F_HOST = os.getenv("FTP_HOST")
F_USER = os.getenv("FTP_USER")
F_PASS = os.getenv("FTP_PASS")


def restrict_building():
    try:
        print(f"Conectando ao FTP: {F_HOST}...")
        ftp = FTP(F_HOST)
        ftp.login(F_USER, F_PASS)

        cfg_path = "/dayzxb_missions/dayzOffline.chernarusplus/cfggameplay.json"

        # 1. Baixar o arquivo atual
        bio = io.BytesIO()
        ftp.retrbinary(f"RETR {cfg_path}", bio.write)
        content = bio.getvalue().decode("utf-8", errors="ignore")
        config = json.loads(content)

        # 2. Modificar para RESTRICTED BUILDING
        # ConstructionData
        if "BaseBuildingData" not in config:
            config["BaseBuildingData"] = {}
        if "ConstructionData" not in config["BaseBuildingData"]:
            config["BaseBuildingData"]["ConstructionData"] = {}

        cd = config["BaseBuildingData"]["ConstructionData"]
        cd["disableDistanceCheck"] = False
        cd["disableIsCollidingCheck"] = False
        cd["disablePerformRoofCheck"] = False

        # HologramData
        if "HologramData" not in config["BaseBuildingData"]:
            config["BaseBuildingData"]["HologramData"] = {}
        hd = config["BaseBuildingData"]["HologramData"]
        hd["disableIsCollidingGPlotCheck"] = False
        hd["disableIsPlacementPermittedCheck"] = False
        hd["disableIsBaseViableCheck"] = False
        hd["disableHeightPlacementCheck"] = False
        hd["disableIsClippingRoofCheck"] = False
        hd["disableIsCollidingAngleCheck"] = False
        hd["disableIsCollidingBBoxCheck"] = False
        hd["disableIsCollidingPlayerCheck"] = False
        hd["disableIsInTerrainCheck"] = False
        hd["disableIsUnderwaterCheck"] = False

        print("Configurações de restrição aplicadas no objeto JSON local.")

        # 3. Upload de volta
        new_content = json.dumps(config, indent=4)
        bio_out = io.BytesIO(new_content.encode("utf-8"))
        ftp.storbinary(f"STOR {cfg_path}", bio_out)

        print(
            f"Upload de {cfg_path} concluído com sucesso. Construção Restringida ATIVA."
        )

        ftp.quit()
    except Exception as e:
        print(f"Erro ao atualizar JSON via FTP: {e}")


if __name__ == "__main__":
    restrict_building()
