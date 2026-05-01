import asyncio
import ftplib
import json
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("bot247")

FTP_HOST = os.getenv("FTP_HOST")
FTP_PORT = int(os.getenv("FTP_PORT", 21))
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def connect_ftp():
    """Estabelece conexão FTP com o servidor Nitrado (sem TLS — não suportado)."""
    try:
        ftp = ftplib.FTP()
        ftp.connect(FTP_HOST, FTP_PORT, timeout=5)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.set_pasv(True)
        ftp.voidcmd("TYPE I")
        return ftp
    except Exception as e:
        logger.error(f"FTP connection failed: {e}")
        return None


def go_to_profile(ftp):
    """Navega para o diretório de perfil onde ficam os JSONs."""
    for path in [
        "/dayzxb/config",
        "SC",
        "profile",
        "/dayzxb_missions/dayzOffline.chernarusplus",
    ]:
        try:
            ftp.cwd(path)
            return True
        except Exception:
            continue
    return False


def upload_spawn_request(item_name, coords, gamertag=None):
    """Gera o JSON de spawn e envia para o FTP do servidor DayZ."""
    spawn_data = {
        "items": [{"name": item_name, "coords": coords, "gamertag": gamertag}]
    }

    filename = "spawns.json"
    try:
        with open(filename, "w") as f:
            json.dump(spawn_data, f)

        ftp = connect_ftp()
        if ftp:
            try:
                go_to_profile(ftp)
                with open(filename, "rb") as f:
                    ftp.storbinary(f"STOR {filename}", f)
                return True
            finally:
                try:
                    ftp.quit()
                except Exception:
                    pass
        return False

    except Exception as e:
        logger.error(f"Erro upload spawn: {e}")
        return False
    finally:
        # Garante a limpeza do arquivo localmente
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception as e:
                logger.error(f"Erro ao remover arquivo temporário {filename}: {e}")


def download_file(remote_path, local_path):
    """Baixa um arquivo do servidor FTP."""
    ftp = connect_ftp()
    if not ftp:
        return False
    try:
        go_to_profile(ftp)
        with open(local_path, "wb") as f:
            ftp.retrbinary(f"RETR {remote_path}", f.write)
        return True
    except Exception as e:
        logger.error(f"Erro download FTP ({remote_path}): {e}")
        return False
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def upload_file(local_path, remote_path):
    """Envia um arquivo para o servidor FTP."""
    ftp = connect_ftp()
    if not ftp:
        return False
    try:
        go_to_profile(ftp)
        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {remote_path}", f)
        return True
    except Exception as e:
        logger.error(f"Erro upload FTP ({remote_path}): {e}")
        return False
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


# ==================== ASYNC WRAPPERS ====================


async def async_connect_ftp():
    """Async wrapper para connect_ftp() - não bloqueia o event loop."""
    return await asyncio.to_thread(connect_ftp)


async def async_download_file(remote_path, local_path):
    """Async wrapper para download_file() - não bloqueia o event loop."""
    return await asyncio.to_thread(download_file, remote_path, local_path)


async def async_upload_file(local_path, remote_path):
    """Async wrapper para upload_file() - não bloqueia o event loop."""
    return await asyncio.to_thread(upload_file, local_path, remote_path)
