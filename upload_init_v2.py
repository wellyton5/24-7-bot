import os, ftplib, sys
from dotenv import load_dotenv

def upload():
    load_dotenv()
    FTP_HOST = os.getenv('FTP_HOST')
    FTP_USER = os.getenv('FTP_USER')
    FTP_PASS = os.getenv('FTP_PASS')
    LOCAL_PATH = '/home/ubuntu/24-7-Bot/init.c_transfer'
    REMOTE_FILENAME = 'init.c'
    
    paths = ['/dayzxb_missions/dayzOffline.chernarusplus', '/missions/dayzOffline.chernarusplus', '/dayzxb']
    found = False
    try:
        print(f'Conectando a {FTP_HOST}...')
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        for p in paths:
            try:
                ftp.cwd(p)
                with open(LOCAL_PATH, 'rb') as f_local:
                    ftp.storbinary(f'STOR {REMOTE_FILENAME}', f_local)
                print(f'Upload concluido para {p}')
                found = True
                break
            except Exception as e:
                print(f'Falha em {p}: {e}')
                continue
        ftp.quit()
        if not found:
            print('Erro: Pasta da missao nao encontrada')
            sys.exit(1)
    except Exception as e:
        print(f'Erro fatal: {e}')
        sys.exit(1)

if __name__ == '__main__':
    upload()
