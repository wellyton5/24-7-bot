import io
import os
from dotenv import load_dotenv
from ftp_helpers import connect_ftp

load_dotenv()


def find_all_adm_logs(ftp):
    all_logs = []
    for path in ["/dayzxb/config", "/dayzxb", "/profile"]:
        try:
            ftp.cwd(path)
            items = ftp.nlst()
            for f in items:
                if f.lower().endswith(".adm"):
                    all_logs.append(f"{path}/{f}")
        except:
            continue
    return all_logs


def find_built_example():
    ftp = connect_ftp()
    if not ftp:
        print("Falha ao conectar FTP")
        return

    logs = find_all_adm_logs(ftp)
    logs.sort(reverse=True)

    print(f"Pesquisando em {len(logs)} arquivos .adm...")

    found = False
    for log_file in logs[:10]:  # Checar os últimos 10 logs
        print(f"Checando {log_file}...")
        try:
            ftp.voidcmd("TYPE I")
            bio = io.BytesIO()
            ftp.retrbinary(f"RETR {log_file}", bio.write)
            content = bio.getvalue().decode("utf-8", errors="ignore")

            for line in content.split("\n"):
                if " Built " in line or " built " in line or " built: " in line:
                    print(f"EXEMPLO ENCONTRADO em {log_file}:")
                    print(line)
                    found = True
                    # Pegar uns 3 exemplos e parar
                    break
        except Exception as e:
            print(f"Erro ao ler {log_file}: {e}")

        if found:
            break

    if not found:
        print("Nenhum exemplo de 'Built' encontrado nos últimos 10 logs.")


if __name__ == "__main__":
    find_built_example()
