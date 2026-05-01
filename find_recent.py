import os
from ftp_helpers import connect_ftp


def find_newest_files():
    ftp = connect_ftp()
    if not ftp:
        print("Erro: FTP nao conectou.")
        return

    print("\n--- BUSCANDO ARQUIVOS MAIS RECENTES ---")

    candidates = []

    def scan(path):
        try:
            ftp.cwd(path)
            # Usar MLSD para pegar atributos detalhados
            for name, attrs in ftp.mlsd():
                if attrs.get("type") == "file":
                    candidates.append(
                        {
                            "path": f"{path}/{name}",
                            "name": name,
                            "modify": attrs.get("modify", ""),
                            "size": attrs.get("size", 0),
                        }
                    )
                elif attrs.get("type") == "dir" and name not in [".", ".."]:
                    # Limitar profundidade para nao demorar
                    if path.count("/") < 3:
                        scan(f"{path}/{name}")
                        ftp.cwd(path)  # Voltar
        except:
            pass

    scan("/dayzxb/config")
    scan("/dayzxb_missions")

    if not candidates:
        print("Nenhum arquivo encontrado.")
        return

    # Ordenar por data de modificacao (YMDHMS)
    candidates.sort(key=lambda x: x["modify"], reverse=True)

    print("\nTop 10 arquivos mais recentes no servidor:")
    for c in candidates[:10]:
        print(f"- {c['path']} | Modificado: {c['modify']} | Tam: {c['size']} bytes")

    ftp.quit()


if __name__ == "__main__":
    find_newest_files()
