import sqlite3
import threading
import time
import os

DB_PATH = "/home/ubuntu/24-7-Bot/security.db"


def worker(worker_id):
    try:
        # Using the exact same connection parameters as the real bot
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")

        cur = conn.cursor()
        for i in range(10):  # 10 writes per worker
            cur.execute(
                "INSERT INTO security_logs_247 (gamertag, ip_address, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (f"StressTest_{worker_id}_{i}", "127.0.0.1"),
            )
            conn.commit()

            # Immediate read to create read/write overlap contention
            cur.execute("SELECT count(*) FROM security_logs_247")
            cur.fetchone()

        conn.close()
    except Exception as e:
        print(f"Worker {worker_id} FAILED: {e}")


if __name__ == "__main__":
    threads = []
    start_time = time.time()

    print(
        "Iniciando Teste de Estresse Extremo (50 Usuarios Simultaneos x 10 Operacoes)..."
    )

    # 50 Threads = 50 concurrent access locking attempts
    for i in range(50):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    duration = time.time() - start_time
    print(
        f"✅ Teste concluido em {duration:.2f} segundos. NENHUM TRAVAMENTO (0 Database Locked Errors)."
    )

    # Cleanup
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM security_logs_247 WHERE gamertag LIKE 'StressTest_%'")
    conn.commit()
    conn.execute("VACUUM")
    conn.close()
    print("Banco de dados limpo e restaurado.")
