#!/usr/bin/env python3
"""Desbanir todos os jogadores EXCETO os banidos por garden_exploit."""
import io
import os
import sqlite3
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'security.db')

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Identificar bans a manter (garden_exploit)
    cur.execute("""
        SELECT DISTINCT xuid FROM infractions
        WHERE auto_banned=1 AND ban_lifted=0 AND infraction_type = 'garden_exploit'
        AND xuid IS NOT NULL AND xuid != ''
    """)
    garden_xuids = set(r[0] for r in cur.fetchall())
    print(f'Garden XUIDs (MANTER banidos): {len(garden_xuids)}')
    for x in garden_xuids:
        cur.execute('SELECT gamertag FROM infractions WHERE xuid=? AND infraction_type="garden_exploit" LIMIT 1', (x,))
        row = cur.fetchone()
        gt = row[0] if row else '???'
        print(f'  MANTER: {gt} ({x[:16]}...)')

    # 2. Desbanir todos os outros no DB
    cur.execute("""
        SELECT id, gamertag, xuid, infraction_type FROM infractions
        WHERE auto_banned=1 AND ban_lifted=0 AND infraction_type != 'garden_exploit'
    """)
    to_unban = cur.fetchall()
    print(f'\nDesbanindo {len(to_unban)} jogadores no DB...')

    for row in to_unban:
        ban_id, gt, xuid, itype = row
        cur.execute('UPDATE infractions SET ban_lifted=1, admin_notes="Unban geral - modo pausa" WHERE id=?', (ban_id,))
        print(f'  DESBANIDO: [{ban_id}] {gt} ({itype})')

    conn.commit()
    print(f'\nDB atualizado: {len(to_unban)} bans levantados.')

    # 3. Atualizar ban.txt via FTP (apenas garden XUIDs)
    ftp_host = os.getenv('FTP_HOST')
    ftp_user = os.getenv('FTP_USER')
    ftp_pass = os.getenv('FTP_PASS')

    if not all([ftp_host, ftp_user, ftp_pass]):
        print('ERRO: FTP credentials nao configuradas')
        conn.close()
        return

    ftp = FTP()
    try:
        ftp.connect(ftp_host, 21, timeout=10)
        ftp.login(ftp_user, ftp_pass)
        ftp.set_pasv(True)

        # Ler ban.txt atual
        buf = io.BytesIO()
        try:
            ftp.retrbinary('RETR /dayzxb/config/ban.txt', buf.write)
            old_xuids = set(l.strip() for l in buf.getvalue().decode('utf-8', errors='ignore').split('\n') if l.strip())
            print(f'\nban.txt antigo: {len(old_xuids)} XUIDs')
        except Exception:
            old_xuids = set()

        # Novo ban.txt = apenas garden XUIDs
        new_content = '\n'.join(sorted(garden_xuids)) + '\n' if garden_xuids else ''
        upload_buf = io.BytesIO(new_content.encode('utf-8'))
        ftp.storbinary('STOR /dayzxb/config/ban.txt', upload_buf)
        print(f'ban.txt atualizado: {len(garden_xuids)} XUIDs (apenas garden)')

        removed = old_xuids - garden_xuids
        print(f'Removidos do ban.txt: {len(removed)} XUIDs')
    except Exception as e:
        print(f'ERRO FTP: {e}')
    finally:
        try:
            ftp.quit()
        except Exception:
            pass

    conn.close()
    print('\nCONCLUIDO!')

if __name__ == '__main__':
    main()
