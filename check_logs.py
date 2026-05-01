import io
import os
from ftp_helpers import connect_ftp


def find_latest_adm_log(ftp):
    for path in ["/dayzxb/config", "/dayzxb", "/profile"]:
        try:
            ftp.cwd(path)
            items = ftp.nlst()
            adm_files = [f"{path}/{f}" for f in items if f.lower().endswith(".adm")]
            if adm_files:
                adm_files.sort()
                return adm_files[-1]
        except:
            continue
    return None


def check_live_activity():
    ftp = connect_ftp()
    if not ftp:
        print("Erro: Nao foi possivel conectar ao FTP.")
        return

    latest_log = find_latest_adm_log(ftp)
    if not latest_log:
        print("Erro: Nenhum log ADM encontrado.")
        ftp.quit()
        return

    print(f"\n--- ATIVIDADE RECENTE NO LOG: {latest_log} ---")
    try:
        ftp.voidcmd("TYPE I")
        size = ftp.size(latest_log)
        # Ler os últimos 2000 bytes para pegar as últimas linhas
        offset = max(0, size - 2000)

        bio = io.BytesIO()
        ftp.retrbinary(f"RETR {latest_log}", bio.write, rest=offset)
        content = bio.getvalue().decode("utf-8", errors="ignore")

        lines = content.split("\n")
        for line in lines[-15:]:  # Mostrar apenas as últimas 15 linhas
            if line.strip():
                print(f"> {line.strip()}")

    except Exception as e:
        print(f"Erro ao ler log: {e}")
    finally:
        ftp.quit()


if __name__ == "__main__":
    check_live_activity()
