import os, ftplib, re
from dotenv import load_dotenv
load_dotenv()
FTP_HOST = os.getenv('FTP_HOST')
FTP_USER = os.getenv('FTP_USER')
FTP_PASS = os.getenv('FTP_PASS')
def check():
    ftp = ftplib.FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.cwd('/dayzxb_missions/dayzOffline.chernarusplus/db')
    with open('tmp_types.xml', 'wb') as f:
        ftp.retrbinary('RETR types.xml', f.write)
    with open('tmp_types.xml', 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        for name in ['Wreck_UH1Y', 'Wreck_Mi8', 'StaticHeli', 'Truck_01_Covered']:
            if name in content:
                print(f'FOUND: {name}')
    ftp.quit()
check()
