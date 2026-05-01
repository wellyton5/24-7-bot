import io
import os
from dotenv import load_dotenv
from ftp_helpers import connect_ftp

load_dotenv()


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


def debug_log_format():
    ftp = connect_ftp()
    if not ftp:
        print("Falha ao conectar FTP")
        return

    log_file = find_latest_adm_log(ftp)
    if not log_file:
        print("Nenhum arquivo .adm encontrado")
        return

    print(f"Lendo {log_file}...")
    ftp.voidcmd("TYPE I")
    size = ftp.size(log_file)
    offset = max(0, size - 10000)  # Ler os últimos 10KB

    bio = io.BytesIO()
    ftp.retrbinary(f"RETR {log_file}", bio.write, rest=offset)
    content = bio.getvalue().decode("utf-8", errors="ignore")

    lines = content.split("\n")
    print("Últimas 20 linhas do log:")
    for line in lines[-20:]:
        print(line)

    print("\nProcurando por 'Built':")
    for line in lines:
        if " Built " in line:
            print(f"ENCONTRADO: {line}")


if __name__ == "__main__":
    debug_log_format()
