import os

vps_path = "/home/ubuntu/24-7-Bot/main_24-7.py"

if not os.path.exists(vps_path):
    print("Erro: Arquivo não encontrado.")
    exit(1)

with open(vps_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Trava singleton definitiva com aspas corretas
lock_lines = [
    "import fcntl, sys\n",
    'fp = open("/tmp/bot_24_7.lock", "w")\n',
    "try:\n",
    "    fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)\n",
    "except IOError:\n",
    "    sys.exit(1)\n",
]

# Se o arquivo já começa com 'import fcntl', vamos substituir as 6 primeiras linhas
# para garantir que as aspas e a indentação estejam corretas.
if "import fcntl" in lines[0]:
    new_lines = lock_lines + lines[6:]
else:
    # Se não tem, apenas insere no topo
    new_lines = lock_lines + lines

with open(vps_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Script main_24-7.py corrigido com sucesso!")
