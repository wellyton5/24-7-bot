# 24/7 DayZ Security Bot

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Discord.py](https://img.shields.io/badge/discord.py-2.x-7289da.svg)](https://github.com/Rapptz/discord.py)

An autonomous Discord bot that enforces base ownership, anti-raid rules, and gameplay automation on a DayZ server hosted at Nitrado. Runs 24/7 on a small VPS, integrating with the Nitrado API, FTP server logs, and Discord for admin control.

## Features

- **Base Sovereignty** — first player to place a fence/gate within a configurable radius (50m default) becomes the registered owner in `security.db`.
- **Auto-Ban (Anti-Raider)** — instant ban for any unauthorized player who tries to build or place items inside another player base perimeter.
- **Anti-Lag Limits** — caps fireplaces and gardens per player outside their own base (configurable via `!config`).
- **Free Building Toggle** — monitors `cfggameplay.json` and keeps collision restrictions disabled.
- **Scheduled Raid Window** — automatically ends raids on Saturdays at 22:00 BRT, editing the server config and restarting via the Nitrado API.
- **FTP Health Monitor** — alerts admins on Discord if the Nitrado FTP is offline for 15+ minutes.
- **Daily DB Backup** — uploads `security.db` to the admin channel every day at 04:00 BRT.
- **Notification Rate Limiter** — async queue that throttles Discord notifications to 1/s, preventing API rate-limits.
- **Truck Spawn Monitor** — detects and notifies Truck Kit availability on the server.
- **Live Config** — `!config` commands to change raid windows, limits, and base radius without restart.

## Stack

- Python 3.10+ with discord.py
- SQLite (`security.db`, `bigode_unified.db`)
- systemd service for 24/7 operation
- Ubuntu Linux on Oracle Cloud Always-Free VPS
- Nitrado REST API + FTP for game server integration

## Quick Start

```bash
git clone https://github.com/<your-user>/24-7-bot.git
cd 24-7-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill in DISCORD_TOKEN, NITRADO_TOKEN, FTP_*, channel IDs, etc.
python3 main_247.py
```

## Running as a systemd service

```ini
[Unit]
Description=24-7 DayZ Security Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/24-7-Bot
ExecStart=/home/ubuntu/24-7-Bot/venv/bin/python3 -u main_247.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now 24-7-bot
sudo journalctl -u 24-7-bot -f
```

## Repository structure

- `main_247.py` — bot entry point, command registration, event loop
- `auto_ban_system.py` — perimeter intrusion detection and auto-ban pipeline
- `admin_dashboard.py` — Discord-based admin UI with persistent views
- `apply_*.py` — one-shot scripts to apply gameplay tweaks (winter, weather, sky, helis, wolves, pause mode)
- `audit_*.py` — diagnostic scripts that audit bans, intrusions, and event groups
- `read_*.py` — config readers used by the live `!config` command set

---

## 🇧🇷 Versão Portuguesa

# 🤖 24/7 DayZ Security Bot - Estado do Projeto

Este documento serve como a **Fonte da Verdade** para futuras assistências de IA sobre o sistema de segurança independente do servidor DayZ BigodeTexas.

> 📋 Para o registro completo de melhorias e pendências, veja `MELHORIAS_PENDENTES.md`

## 🏁 Visão Geral

O bot é uma entidade independente do "BigodeBot" principal, focada em segurança pesada, automação de gameplay e execução 24/7 na nuvem.

### 📍 Localização

- **Local (Desenvolvimento)**: `D:\dayz xbox\24-7 Bot`
- **Nuvem (Produção)**: `/home/ubuntu/24-7-Bot` (Oracle Cloud VPS)
- **IP VPS**: `141.148.177.242`

## 🛠️ Funcionalidades Implementadas

1. **Soberania de Base**: O primeiro jogador a construir uma cerca/portão em um raio de 50m (configurável) é registrado como dono no `security.db`.
2. **Auto-Ban (Anti-Raider)**: Banimento imediato de qualquer jogador não-autorizado que tentar construir ou colocar itens dentro do perímetro de uma base alheia.
3. **Limites Anti-Lag**: Máximo de 2 Fogueiras ou Jardins por jogador fora de sua própria base (configurável via `!config`).
4. **Free Building Automático**: O bot monitora o `cfggameplay.json` e garante que todas as restrições de colisão estejam desativadas (`true`).
5. **Raid Agendado**: Encerramento automático de Raids aos sábados às 22:00 BRT, com alteração de config e restart via API Nitrado. Horário configurável via `!config`.
6. **Monitor de Saúde FTP**: Alerta no Discord se o FTP da Nitrado ficar offline por 15+ minutos.
7. **Backup Automático do DB**: Envia `security.db` diariamente às 04:00 BRT como arquivo no canal admin.
8. **Rate Limiting de Notificações**: Fila assíncrona limita notificações a 1/segundo para evitar rate-limit da API Discord.
9. **Monitor de Caminhões**: Detecta e notifica disponibilidade de Truck Kit spawns no servidor.
10. **Config Dinâmica**: Comandos `!config` permitem alterar horários de raid, limites e raio de base sem restart.

## ⚙️ Infraestrutura e Execução

- **S.O.**: Ubuntu Linux (Oracle Cloud Always-Free)
- **Gerenciador de Processo**: Systemd (`24-7-bot.service`) — **auto-start no boot ativado** ✅
- **Python**: v3.10+ em ambiente virtual (`venv`)
- **Logs**: `journalctl` com limite de 500MB configurado

### 📟 Comandos Úteis na VPS
```bash
sudo journalctl -u 24-7-bot -f      # Logs em tempo real
sudo systemctl status 24-7-bot       # Status do bot
sudo systemctl restart 24-7-bot      # Restart
```

## 🔑 Credenciais e Arquivos Críticos

- **.env**: Localizado no diretório raiz do bot. Contém `DISCORD_TOKEN`, `NITRADO_TOKEN`, `FTP_PASS`, `SERVICE_ID`, `ADMIN_BACKUP_CHANNEL_ID`.
- **security.db**: Banco SQLite3 que armazena as bases, clãs, identidades e contagens de itens.
- **CHAVE SSH**: Localizada em `C:\Users\Wellyton\Desktop\ssh-key-2026-02-08.key`. Necessária para acesso à Oracle Cloud.

## 💬 Comandos Discord do Bot

| Comando | Descrição | Permissão |
|---|---|---|
| `!vincular <gamertag>` | Vincula Discord ao Xbox Gamertag | Todos |
| `!clan criar <nome>` | Cria um novo clã | Todos |
| `!clan convidar @membro` | Convida membro para o clã | Líder |
| `!clan aceitar` | Aceita convite pendente | Todos |
| `!clan lista` | Lista clãs registrados | Todos |
| `!config` | Exibe configurações atuais | Admin |
| `!config raid_start <hora>` | Muda hora de início do raid | Admin |
| `!config raid_end <hora>` | Muda hora de fim do raid | Admin |
| `!config fire_limit <n>` | Muda limite de fogueiras | Admin |
| `!config base_radius <m>` | Muda raio de soberania | Admin |
| `!lookup <gamertag>` | Ficha completa do jogador | Admin |
| `!alts <gamertag>` | Contas alternativas detectadas | Admin |
| `!deaths` | Killfeed recente | Todos |

## 📝 Notas para a próxima IA

- O bot utiliza um parser de logs via FTP que roda a cada 3 segundos.
- Se houver necessidade de alterar o código, a alteração deve ser feita localmente (`*_fix.py`) e enviada via `scp`.
- **SEMPRE** validar com `python -c "import ast; ast.parse(open('arquivo.py', encoding='utf-8').read())"` antes do deploy.
- O arquivo `MELHORIAS_PENDENTES.md` contém o registro completo de pendências e histórico de sessões.
- O erro `truck_availability.json: No such file or directory` nos logs é **normal** — o arquivo só aparece se o servidor de jogo criá-lo.
