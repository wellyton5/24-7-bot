import ftplib
import os
import re
from dotenv import load_dotenv

load_dotenv()


def patch_init():
    ftp_host = os.getenv("FTP_HOST")
    ftp_user = os.getenv("FTP_USER")
    ftp_pass = os.getenv("FTP_PASS")

    print(f"Conectando ao FTP {ftp_host}...")
    ftp = ftplib.FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)

    remote_init = "/dayzxb_missions/dayzOffline.chernarusplus/init.c"
    local_init = "init_temp_bunker.c"

    print(f"Baixando {remote_init}...")
    with open(local_init, "wb") as f:
        ftp.retrbinary(f"RETR {remote_init}", f.write)

    with open(local_init, "r", encoding="utf-8") as f:
        content = f.read()

    # Verifica se já está lá
    if "CleanBunkerZone()" in content and "Zelador" in content:
        print("Zelador já foi instalado anteriormente!")
        ftp.quit()
        return

    # Injeta a função CleanBunkerZone() no final do arquivo
    cleaner_code = """
// [BigodeTexas - Modulo de Zeladoria e Limpeza de Cordon]
void CleanBunkerZone()
{
    vector bunker_center = "13280.0 0 12100.0".ToVector();
    float cleanup_radius = 200.0;

    array<Object> objects_in_zone = new array<Object>;
    GetGame().GetObjectsAtPosition(bunker_center, cleanup_radius, objects_in_zone, null);

    int count_deleted = 0;
    for (int i = 0; i < objects_in_zone.Count(); i++)
    {
        Object obj = objects_in_zone.Get(i);
        if (obj)
        {
            string obj_type = obj.GetType();
            obj_type.ToLower();
            if (obj_type.Contains("fence") || obj_type.Contains("watchtower") || obj_type.Contains("tent") || obj_type.Contains("barrel") || obj_type.Contains("sea_chest") || obj_type.Contains("gate") || obj_type.Contains("wall") || obj_type.Contains("base"))
            {
                GetGame().ObjectDelete(obj);
                count_deleted++;
            }
        }
    }
    Print("[Zelador] Limpeza de Base no Bunker executada com sucesso! Itens: " + count_deleted);
}
"""
    if "void CleanBunkerZone()" in content:
        # Substitui a função inteira se ela já existir usando regex
        content = re.sub(
            r"// \[BigodeTexas - Modulo de Zeladoria e Limpeza de Cordon\]\s*void CleanBunkerZone\(\)\s*\{.*?\n\}",
            cleaner_code,
            content,
            flags=re.DOTALL,
        )
    else:
        content += "\n" + cleaner_code

    # Procura OnInit para injetar a chamada
    # Vamos usar regex para injetar depois de super.OnInit();
    pattern = r"(override\s+void\s+OnInit\(\)\s*\{[^{}]+super\.OnInit\(\);)"
    replacement = r"\1\n\n\t\t// --- CHAMA O ZELADOR DO BUNKER PARA LIMPAR CONSTRUCOES NA INICIALIZACAO ---\n\t\tCleanBunkerZone();\n"

    new_content = re.sub(pattern, replacement, content, count=1)

    with open(local_init, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Enviando arquivo atualizado para {remote_init}...")
    with open(local_init, "rb") as f:
        ftp.storbinary(f"STOR {remote_init}", f)

    print("Concluído! O Zelador foi injetado com sucesso no init.c!")
    ftp.quit()


if __name__ == "__main__":
    patch_init()
