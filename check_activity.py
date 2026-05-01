import sqlite3
import os

db_path = "security.db"


def check_db():
    if not os.path.exists(db_path):
        print(f"Erro: Arquivo {db_path} nao encontrado.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Verificar Bases Registradas
        print("\n--- BASES PROTEGIDAS (SOBERANIA) ---")
        cursor.execute("SELECT * FROM bases_security")
        bases = cursor.fetchall()
        if not bases:
            print("Nenhuma base registrada ainda.")
        for b in bases:
            print(f"Dono: {b[1]} | Coords: ({b[2]}, {b[4]}) | Raio: {b[5]}")

        # 2. Verificar Limites de Itens
        print("\n--- LIMITES DE ITENS (FOGUEIRAS/JARDINS) ---")
        cursor.execute("SELECT * FROM item_limits")
        limits = cursor.fetchall()
        if not limits:
            print("Nenhum item monitorado ainda.")
        for l in limits:
            print(f"Jogador: {l[0]} | Item: {l[1]} | Qtd: {l[2]}")

        conn.close()
    except Exception as e:
        print(f"Erro ao ler DB: {e}")


if __name__ == "__main__":
    check_db()
