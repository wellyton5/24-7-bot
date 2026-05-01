import io
import os
from ftp_helpers import connect_ftp


def diagnose_logs():
    ftp = connect_ftp()
    if not ftp:
        print("Erro: FTP nao conectou.")
        return

    print("\n--- DIAGNOSTICO DE LOGS ---")
    paths = ["/dayzxb/config", "/dayzxb", "/profile", "/"]

    found_adm = []

    for path in paths:
        try:
            print(f"Buscando em {path}...")
            ftp.cwd(path)
            items = ftp.nlst()
            for item in items:
                if item.lower().endswith(".adm"):
                    # Pegar data de modificacao se possivel
                    try:
                        mdtm = ftp.voidcmd(f"MDTM {item}").split()[1]
                    except:
                        mdtm = "Desconhecida"

                    # Pegar tamanho
                    ftp.voidcmd("TYPE I")
                    size = ftp.size(item)

                    found_adm.append(
                        {
                            "path": f"{path}/{item}",
                            "name": item,
                            "size": size,
                            "time": mdtm,
                        }
                    )
        except:
            continue

    if not found_adm:
        print("❌ Nenhum arquivo .adm encontrado!")
    else:
        # Ordenar por nome (geralmente cronologico)
        found_adm.sort(key=lambda x: x["name"], reverse=True)
        print(f"\n✅ Encontrados {len(found_adm)} arquivos .adm. Os 3 mais recentes:")
        for log in found_adm[:3]:
            print(f"- {log['path']} | Tam: {log['size']} bytes | Data: {log['time']}")

            # Tentar ler o final do log mais recente
            if log == found_adm[0]:
                print(f"\n--- Conteudo final de {log['name']} ---")
                bio = io.BytesIO()
                # Ler ultimos 5000 bytes
                offset = max(0, log["size"] - 5000)
                ftp.retrbinary(f"RETR {item}", bio.write, rest=offset)
                content = bio.getvalue().decode("utf-8", errors="ignore")
                for line in content.split("\n")[-10:]:
                    if line.strip():
                        print(f"> {line.strip()}")

    ftp.quit()


if __name__ == "__main__":
    diagnose_logs()
