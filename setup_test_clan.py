import database
import sqlite3

USER_ID = "831391383981522964"
GAMERTAG = "BRAZIL555TEXAS"
CLAN_NAME = "TEXAS TEAM"


def setup_test_clan():
    print(f"--- CONFIGURANDO CLÃ DE TESTE ---")
    try:
        # 1. Tentar criar o clã
        cid = database.create_clan(CLAN_NAME, USER_ID)
        if cid:
            print(f"[V] Clã '{CLAN_NAME}' criado com ID {cid}")
        else:
            # Talvez já exista
            clan_info = database.get_clan_by_leader(USER_ID)
            if clan_info:
                cid = clan_info["id"]
                print(f"[!] Usuário já lidera o clã '{clan_info['name']}' (ID {cid})")
            else:
                print("[X] Erro ao criar clã (nome duplicado ou erro DB)")
                return

        # 2. Adicionar o líder como membro (role leader)
        database.add_clan_member(cid, USER_ID, GAMERTAG)
        print(f"[V] Líder {GAMERTAG} adicionado ao clã.")

        # 3. Testar Adicionar Membro Pre-registrado (o que estava falhando)
        print("[*] Testando adição de membro pendente (sem discord_id)...")
        database.add_clan_member(cid, None, "AmigoTeste123")
        print("[V] Sucesso ao adicionar membro pendente!")

    except Exception as e:
        print(f"[X] Erro durante o setup: {e}")


if __name__ == "__main__":
    setup_test_clan()
