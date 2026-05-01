#!/usr/bin/env python3
"""
Aplica Modo Pausa ao main_247.py
- Bot fica ligado no Discord, comandos funcionam normalmente
- NAO le logs, NAO conecta FTP fora do raid
- Sabados 20h-22h BRT: ativa tudo, raid + construcao livre
- Apos raid: desliga tudo, construcao restrita
"""

FILE = '/home/ubuntu/24-7-Bot/main_247.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Backup
with open(FILE + '.bak_pre_pause', 'w', encoding='utf-8') as f:
    f.write(content)
print('[BACKUP] main_247.py.bak_pre_pause criado')

changes = 0

# ===== 1. Adicionar _bot_paused flag =====
old_1 = '_ban_notify_queue: asyncio.Queue = asyncio.Queue()'
new_1 = """_ban_notify_queue: asyncio.Queue = asyncio.Queue()

# === MODO PAUSA ===
# Bot inicia PAUSADO: conectado ao Discord mas sem ler FTP/Nitrado.
# Apenas o raid_scheduler e drain_ban_queue rodam sempre.
# No sabado 20h-22h BRT, o raid_scheduler ativa as tasks FTP.
_bot_paused = True"""

if old_1 in content:
    content = content.replace(old_1, new_1, 1)
    changes += 1
    print('[1] Flag _bot_paused adicionada')
else:
    print('[1] SKIP - texto nao encontrado')

# ===== 2. Adicionar funcoes helper antes de monitor_truck_spawns =====
old_2 = '@tasks.loop(minutes=5)\nasync def monitor_truck_spawns():'
new_2 = '''async def _start_raid_tasks():
    """Inicia tasks FTP/Nitrado para o periodo de raid."""
    global _bot_paused, last_byte_offset
    _bot_paused = False
    last_byte_offset = -1  # Flag: pular para fim do arquivo (ignorar logs antigos)
    logger.info("[PAUSE] === ATIVANDO MODO RAID ===")

    if not monitor_logs.is_running():
        monitor_logs.start()
        logger.info("[PAUSE] monitor_logs INICIADO")
    if not sync_ban_list.is_running():
        sync_ban_list.start()
        logger.info("[PAUSE] sync_ban_list INICIADO")
    if not ftp_health_monitor.is_running():
        ftp_health_monitor.start()
        logger.info("[PAUSE] ftp_health_monitor INICIADO")
    if not monitor_device_ids.is_running():
        monitor_device_ids.start()
        logger.info("[PAUSE] monitor_device_ids INICIADO")


async def _stop_raid_tasks():
    """Para tasks FTP/Nitrado apos o raid."""
    global _bot_paused
    _bot_paused = True
    logger.info("[PAUSE] === DESATIVANDO MODO RAID ===")

    for task_obj, name in [
        (monitor_logs, "monitor_logs"),
        (sync_ban_list, "sync_ban_list"),
        (ftp_health_monitor, "ftp_health_monitor"),
        (monitor_device_ids, "monitor_device_ids"),
    ]:
        if task_obj.is_running():
            task_obj.cancel()
            logger.info(f"[PAUSE] {name} PARADO")


async def _toggle_free_building(free: bool):
    """Toggle construcao livre (free=True) ou restrita (free=False)."""
    downloaded = await asyncio.to_thread(
        download_file, GAMEPLAY_CONFIG_PATH, LOCAL_GAMEPLAY_CONFIG
    )
    if not downloaded:
        logger.error("[BUILD] Nao foi possivel baixar cfggameplay.json")
        return
    try:
        with open(LOCAL_GAMEPLAY_CONFIG, "r") as f:
            config = json.load(f)

        if "BaseBuildingData" not in config:
            config["BaseBuildingData"] = {}
        if "HologramData" not in config["BaseBuildingData"]:
            config["BaseBuildingData"]["HologramData"] = {}
        hologram = config["BaseBuildingData"]["HologramData"]

        keys = [
            "disableIsCollidingBBoxCheck",
            "disableIsCollidingPlayerCheck",
            "disableIsClippingRoofCheck",
            "disableIsBaseViableCheck",
            "disableIsCollidingGPlotCheck",
            "disableIsCollidingAngleCheck",
            "disableIsPlacementPermittedCheck",
            "disableHeightPlacementCheck",
            "disableIsUnderwaterCheck",
            "disableIsInTerrainCheck",
            "disableColdAreaBuildingCheck",
        ]
        for key in keys:
            hologram[key] = free

        with open(LOCAL_GAMEPLAY_CONFIG, "w") as f:
            json.dump(config, f, indent=4)

        uploaded = await asyncio.to_thread(
            upload_file, LOCAL_GAMEPLAY_CONFIG, GAMEPLAY_CONFIG_PATH
        )
        if uploaded:
            mode = "LIVRE" if free else "RESTRITA"
            logger.info(f"[BUILD] Construcao {mode} aplicada no cfggameplay.json")
    except Exception as e:
        logger.error(f"[BUILD] Erro ao toggle free building: {e}")
    finally:
        if os.path.exists(LOCAL_GAMEPLAY_CONFIG):
            os.remove(LOCAL_GAMEPLAY_CONFIG)


@tasks.loop(minutes=5)
async def monitor_truck_spawns():'''

if old_2 in content:
    content = content.replace(old_2, new_2, 1)
    changes += 1
    print('[2] _start_raid_tasks, _stop_raid_tasks, _toggle_free_building adicionadas')
else:
    print('[2] SKIP - texto nao encontrado')

# ===== 3. Reescrever raid_scheduler =====
old_3 = '''@tasks.loop(seconds=60)
async def raid_scheduler():
    """Scheduled task: enable base damage at raid start, disable at raid end."""
    global _raid_toggled_this_hour
    br_now = datetime.now(timezone.utc) - timedelta(hours=3)
    if br_now.weekday() != 5:
        _raid_toggled_this_hour = None
        return

    current_key = (br_now.date(), br_now.hour)
    if current_key == _raid_toggled_this_hour:
        return

    raid_start = _server_config["raid_start_hour"]
    raid_end = _server_config["raid_end_hour"]
    if br_now.hour == raid_start and br_now.minute == 0:
        _raid_toggled_this_hour = current_key
        await _toggle_base_damage(enabled=True)
        await notify_ban(f"**RAID INICIADO!** Dano em bases liberado ate as {raid_end:02d}:00!")
    elif br_now.hour == raid_end and br_now.minute == 0:
        _raid_toggled_this_hour = current_key
        await _toggle_base_damage(enabled=False)
        await notify_ban("**RAID ENCERRADO!** Dano em bases bloqueado!")'''

new_3 = '''@tasks.loop(seconds=60)
async def raid_scheduler():
    """Master controller: gerencia modo pausa/raid.
    - Sabados 20h-22h BRT: ativa raid (base damage ON, construcao livre, tasks FTP)
    - Fora do horario: modo pausa (base damage OFF, construcao restrita, sem FTP)
    """
    global _raid_toggled_this_hour, _bot_paused
    br_now = datetime.now(timezone.utc) - timedelta(hours=3)

    raid_start = _server_config["raid_start_hour"]
    raid_end = _server_config["raid_end_hour"]

    # Fora de sabado: garantir que esta pausado
    if br_now.weekday() != 5:
        _raid_toggled_this_hour = None
        if not _bot_paused:
            logger.info("[RAID] Dia mudou - desativando modo raid")
            await _toggle_base_damage(enabled=False)
            await _toggle_free_building(free=False)
            await _stop_raid_tasks()
            await restart_nitrado()
            await notify_ban(
                "**RAID ENCERRADO!** Dano em bases bloqueado. "
                "Construcao restrita. Bot em modo pausa."
            )
        return

    current_key = (br_now.date(), br_now.hour)
    if current_key == _raid_toggled_this_hour:
        return

    # SABADO - Hora de iniciar o raid
    if br_now.hour == raid_start and br_now.minute < 2:
        _raid_toggled_this_hour = current_key
        logger.info(f"[RAID] INICIANDO RAID - {raid_start:02d}:00 BRT")
        await _start_raid_tasks()
        await _toggle_free_building(free=True)
        await _toggle_base_damage(enabled=True)
        await restart_nitrado()
        await notify_ban(
            f"**RAID INICIADO!**\\n"
            f"Dano em bases **LIBERADO** ate as {raid_end:02d}:00 BRT!\\n"
            f"Construcao **LIVRE** durante o raid.\\n"
            f"Monitoramento de logs **ATIVO**."
        )

    # SABADO - Hora de encerrar o raid
    elif br_now.hour == raid_end and br_now.minute < 2:
        _raid_toggled_this_hour = current_key
        logger.info(f"[RAID] ENCERRANDO RAID - {raid_end:02d}:00 BRT")
        await _toggle_base_damage(enabled=False)
        await _toggle_free_building(free=False)
        await restart_nitrado()
        await _stop_raid_tasks()
        await notify_ban(
            "**RAID ENCERRADO!**\\n"
            "Dano em bases **BLOQUEADO**.\\n"
            "Construcao **RESTRITA**.\\n"
            "Bot em **modo pausa** ate o proximo raid."
        )'''

if old_3 in content:
    content = content.replace(old_3, new_3, 1)
    changes += 1
    print('[3] raid_scheduler reescrito como master controller')
else:
    print('[3] SKIP - raid_scheduler nao encontrado')

# ===== 4. Modificar _ftp_fetch_new_lines para offset -1 =====
marker_4 = '        # Log file changed (server restart) - read from beginning\n        if latest != current_file:'
insert_before_4 = '''        # Offset -1 = modo pausa -> pular para o fim do arquivo (ignorar historico)
        if byte_offset == -1:
            ftp.voidcmd("TYPE I")
            file_size = ftp.size(latest)
            logger.info(f"[PAUSE] Pulando para fim do log: {latest} (offset: {file_size})")
            return None, file_size, latest

        # Log file changed (server restart) - read from beginning
        if latest != current_file:'''

if marker_4 in content:
    content = content.replace(marker_4, insert_before_4, 1)
    changes += 1
    print('[4] _ftp_fetch_new_lines: suporte a offset -1')
else:
    print('[4] SKIP - marker nao encontrado')

# ===== 5. Modificar on_ready - NAO iniciar tasks FTP =====
marker_5_start = '    # --- Start all background tasks ---'
marker_5_end = 'logger.info("Ban list synced on startup")'

if marker_5_start in content and marker_5_end in content:
    start_idx = content.index(marker_5_start)
    end_idx = content.index(marker_5_end) + len(marker_5_end)
    new_block = '''    # --- Start background tasks (MODO PAUSA) ---
    # Em modo pausa, apenas raid_scheduler, drain_ban_queue e backup_database rodam.
    # Tasks FTP (monitor_logs, sync_ban_list, ftp_health_monitor, monitor_device_ids)
    # sao iniciadas pelo raid_scheduler no sabado 20h BRT.
    logger.info("[PAUSE] ======================================")
    logger.info("[PAUSE]   BOT INICIADO EM MODO PAUSA")
    logger.info("[PAUSE]   FTP/Nitrado: DESCONECTADO")
    logger.info("[PAUSE]   Raid: Sabados 20h-22h BRT")
    logger.info("[PAUSE]   Comandos Discord: ATIVOS")
    logger.info("[PAUSE] ======================================")

    if not raid_scheduler.is_running():
        raid_scheduler.start()
        logger.info("[PAUSE] raid_scheduler ATIVO (master controller)")
    if not drain_ban_queue.is_running():
        drain_ban_queue.start()
        logger.info("[PAUSE] drain_ban_queue ATIVO")
    if not backup_database.is_running():
        backup_database.start()
        logger.info("[PAUSE] backup_database ATIVO (04:00 BRT)")

    # Tasks FTP NAO iniciadas - serao ativadas pelo raid_scheduler
    # monitor_logs, sync_ban_list, ftp_health_monitor, monitor_device_ids = PAUSADOS'''
    content = content[:start_idx] + new_block + content[end_idx:]
    changes += 1
    print('[5] on_ready: modo pausa (tasks FTP nao iniciadas)')
else:
    print(f'[5] SKIP - markers nao encontrados')

# ===== 6. Remover enforce_free_building do on_ready =====
old_6 = '    # --- Enforce free building ---\n    await enforce_free_building()\n'
new_6 = '    # --- enforce_free_building REMOVIDO - controlado pelo raid_scheduler ---\n'

if old_6 in content:
    content = content.replace(old_6, new_6, 1)
    changes += 1
    print('[6] enforce_free_building removido do on_ready')
else:
    print('[6] SKIP - enforce_free_building nao encontrado')

# ===== SALVAR =====
with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\n=== {changes}/6 MODIFICACOES APLICADAS ===')
print(f'Arquivo: {FILE}')
print(f'Tamanho: {len(content)} bytes')
