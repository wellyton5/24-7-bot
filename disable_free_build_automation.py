import os


def disable_free_build_logic():
    path = "/home/ubuntu/24-7-Bot/main_247.py"
    if not os.path.exists(path):
        print(f"Erro: {path} nao encontrado.")
        return

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    modified = False
    new_lines = []
    for line in lines:
        # Comentar a linha que chama a função no on_ready
        if "await enforce_free_building()" in line and "#" not in line:
            new_lines.append(
                line.replace(
                    "await enforce_free_building()", "# await enforce_free_building()"
                )
            )
            modified = True
        else:
            new_lines.append(line)

    if modified:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print("Automação de Construção Livre desativada no main_247.py.")
    else:
        print("Construção Livre já estava desativada ou linha não encontrada.")


if __name__ == "__main__":
    disable_free_build_logic()
