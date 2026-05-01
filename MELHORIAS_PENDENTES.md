# 🧠 MEMÓRIA DO PROJETO — Bot 24/7 BigodeTexas
# Arquivo de Controle de Melhorias (atualizado automaticamente pela IA)

> **Instruções para a próxima IA:** Leia este arquivo antes de qualquer ação.
> Ele descreve o que foi feito, o que está em andamento e o que falta.
> Os arquivos locais `*_fix.py` em `D:\dayz xbox\24-7 Bot\` são a fonte da verdade.
> A VPS Oracle Cloud está em `141.148.177.242`. SSH key em `C:\Users\Wellyton\Desktop\ssh-key-2026-02-08.key`.
> O bot roda como `24-7-bot.service` no systemd. **STATUS: RODANDO** ✅

---

## ✅ SESSÃO 1 — Correção de Bugs (29 bugs corrigidos + deploy)

- [x] `main_247.py`: 14 fixes
- [x] `database.py`: 4 fixes
- [x] `glitch_detector.py`: 3 fixes
- [x] `auto_ban_system.py`: 2 fixes
- [x] `admin_dashboard.py`: 3 fixes
- [x] `ftp_helpers.py`: 3 fixes
- [x] Deploy + bot confirmado `active (running)` na VPS

---

## ✅ SESSÃO 2 — Melhorias (todas implementadas + deploy)

### Implementadas no `main_247_fix.py` (→ `main_247.py` na VPS):

1. **✅ systemctl enable** — Bot agora inicia automaticamente no boot da VPS
   - Executado: `sudo systemctl enable 24-7-bot`

2. **✅ Backup automático do DB** — Task `backup_database`
   - Roda diariamente às 04:00 BRT (07:00 UTC)
   - Envia `security.db` como arquivo no canal admin do Discord
   - Configurar `ADMIN_BACKUP_CHANNEL_ID` no `.env` (opcional — usa `BAN_CHANNEL` como fallback)

3. **✅ Monitor de saúde FTP** — Task `ftp_health_monitor`
   - Roda a cada 5 minutos
   - Alerta no canal Discord se FTP falhar 3x seguidas (15 min offline)
   - Envia mensagem de restauração quando conexão voltar

4. **✅ Rate limiting de notificações** — `_ban_notify_queue` + task `drain_ban_queue`
   - Fila assíncrona com 1 mensagem/segundo máximo
   - Evita ban de rate-limit da API Discord em eventos de alto volume

5. **✅ Reativar monitor_truck_spawns**
   - Task agora inicia junto com as outras no `on_ready`
   - Aviso esperado: `truck_availability.json: No such file or directory` (arquivo não existe no FTP ainda — comportamento normal)

6. **✅ Comando !config** — Grupo de comandos para admin
   - `!config` — Exibe configurações atuais
   - `!config raid_start <hora>` — Muda hora de início do raid
   - `!config raid_end <hora>` — Muda hora de fim do raid
   - `!config fire_limit <n>` — Muda limite de fogueiras por jogador
   - `!config base_radius <m>` — Muda raio de soberania em metros
   - `raid_scheduler` agora usa `_server_config` para horários dinâmicos

7. **✅ Rotação de logs systemd**
   - Configurado: `SystemMaxUse=500M` em `/etc/systemd/journald.conf`
   - `systemd-journald` reiniciado

---

## ✅ SESSÃO 3 — Sistema de Device ID / Detecção de Alts

**Data:** 2026-03-04/05
**Objetivo:** Engenharia reversa do bot AltDetector e implementação de captura de Device IDs de consoles Xbox para detecção de contas alternativas.

### Análise do AltDetector (canal Discord #alt-detector-setup)
- Bot comercial por "Kamikaze & DonMatraca" (altdetector.com)
- Usa `/setup-ad` com Nitrado Server ID + Long Life Token
- Captura Device IDs (identificador de hardware Xbox, base64 ~44 chars)
- Device ID é diferente de XUID (ID da conta Xbox, hex 40 chars)
- Exemplo Device ID: `VUZwoETj2mkhZSZuUxOg5T8jwr0TrB4R_pt4klUoRio=`

### Descobertas Técnicas (evolução da investigação)

**Tentativa 1 — init.c (FALHOU):**
- Modificamos init.c com `Print(GetPlainId())` no `InvokeOnConnect()`
- `Print()` no EnScript **NÃO gera output** em nenhum log no DayZ Xbox (funciona só no PC)
- Backup do init.c original: `/home/ubuntu/24-7-Bot/init_c_backup.txt`
- Modificação ainda está no FTP mas é inerte (pode ser removida)

**Tentativa 2 — Linhas [MAM] no RPT (FUNCIONOU!):**
- Referência: projeto open-source `Sat727/Dayz-Console-Killfeed` no GitHub
- Device IDs são logados pelo engine em linhas `[MAM]` (Multi-Account Mitigation) no arquivo RPT
- Formato: `[MAM] :: [NetworkServer::CheckMAMData] :: device: BASE64= | account: HEX40 | time: N`
- Variantes: `RegisterMAMData`, `RegisterMAMDataHelper` (com `id1:`/`id2:` em vez de `device:`/`account:`)
- **Configuração necessária no Nitrado:** `disableMultiAccountMitigation` deve ser `false`
  - Estava `true` (MAM desabilitado) → mudado para `false` via API Nitrado em 2026-03-04
  - Endpoint: `POST /services/{id}/gameservers/settings` com `category=config&key=disableMultiAccountMitigation&value=false`

### Implementações:

1. **✅ Configuração Nitrado** — MAM habilitado via API
   - `disableMultiAccountMitigation: false` (era `true`)
   - Efeito imediato no próximo restart do servidor DayZ

2. **✅ Task `monitor_device_ids`** (no `main_247_fix.py`)
   - Lê arquivos `.RPT` (não script log) via FTP a cada 30 segundos
   - Parseia linhas `[MAM]` com 4 regex patterns:
     - `device:\s*([^\s|]+)` + `account:\s*([^\s|]+)` (formato padrão)
     - `id1:\s*([^\s|]+)` + `id2:\s*([^\s|]+)` (formato helper)
   - Cache `_xuid_to_gamertag` via linhas `[StateMachine]` do mesmo RPT
   - Fallback para `get_player_identity_by_xuid()` se gamertag não encontrada
   - Armazena via `database.update_player_identity()`

3. **✅ Função `get_player_identity_by_xuid()`** (no `database_fix.py`)
   - Nova função para buscar identidade por XUID em vez de gamertag
   - Usada pelo monitor MAM para associar Device ID ao jogador correto

4. **✅ Comando `!alts` melhorado** (rich embed)
   - Mostra identidade do jogador (XUID, Device ID, IP, última vez visto)
   - Lista contas alternativas com status de ban (🚫 BANIDO / ✅ Limpo)
   - Embed laranja se alts encontradas, verde se limpo

5. **✅ Comando `!lookup` melhorado** (rich embed)
   - Perfil completo: Gamertag, XUID, Device ID, último acesso, status de ban
   - Detecção de alts com contagem e destaque de alts banidas
   - Exibe link Discord vinculado

### Banco de dados:
- Tabela `player_identities` com coluna `device_id TEXT` (já existia)
- Nova: `get_player_identity_by_xuid(xuid)` — busca por XUID
- Existentes: `update_player_identity()`, `find_alts()`, `get_player_identity()`, `log_connection()`

### ⚠️ STATUS ATUAL:
- MAM habilitado no Nitrado ✅
- Bot monitorando RPT para linhas [MAM] ✅
- **Aguardando próximo restart do servidor DayZ** para as linhas [MAM] começarem a aparecer no RPT
- Quando jogadores conectarem após restart, Device IDs serão capturados automaticamente

---

## ⏳ PENDENTE — Próximas sessões (se necessário)

### Melhoria #5: Persistir estado entre reinicializações
- **Arquivos afetados:** `database_fix.py` + `main_247_fix.py` + `glitch_detector_fix.py`
- **Complexidade:** Alta
- **O que fazer:**
  - Criar tabela `bot_state` no SQLite com colunas: `key TEXT PRIMARY KEY, value TEXT, updated_at TIMESTAMP`
  - Salvar `_recent_player_positions` e `_fireplace_spam_tracker` nesta tabela a cada 60s
  - Carregar de volta no `on_ready` (antes de iniciar as tasks)
  - Em `glitch_detector.py`, salvar/carregar `_player_build_events` e `_emote_events` da mesma tabela

### Melhoria #8: Paginação em listagens longas
- **Arquivos afetados:** `main_247_fix.py` + `admin_dashboard_fix.py`
- **Complexidade:** Média
- **O que fazer:**
  - Criar classe `PaginatedView(discord.ui.View)` com botões ◀ e ▶
  - Adaptar `clan_lista`, `alts`, `deaths` e `btn_ban_list` para usar a view paginada
  - Limite de 5 itens por página com contagem "Página X/Y"

### Melhoria #10: Migrar para Slash Commands (/)
- **Complexidade:** Alta (afeta todos os comandos)
- **Depende de:** Migrar `!ban`, `!clan`, `!config`, `!base`, `!lookup`, `!alts` para `/`

---

## 📁 ARQUIVOS CRÍTICOS

| Arquivo Local | Arquivo VPS |
|---|---|
| `main_247_fix.py` | `/home/ubuntu/24-7-Bot/main_247.py` |
| `database_fix.py` | `/home/ubuntu/24-7-Bot/database.py` |
| `auto_ban_system_fix.py` | `/home/ubuntu/24-7-Bot/auto_ban_system.py` |
| `admin_dashboard_fix.py` | `/home/ubuntu/24-7-Bot/admin_dashboard.py` |
| `glitch_detector_fix.py` | `/home/ubuntu/24-7-Bot/glitch_detector.py` |
| `ftp_helpers_fix.py` | `/home/ubuntu/24-7-Bot/ftp_helpers.py` |
| `MELHORIAS_PENDENTES.md` | `/home/ubuntu/24-7-Bot/MELHORIAS_PENDENTES.md` |

## 🔑 COMANDOS ESSENCIAIS

```bash
# SSH na VPS
ssh -i "C:/Users/Wellyton/Desktop/ssh-key-2026-02-08.key" ubuntu@141.148.177.242

# Upload de arquivo
scp -i "C:/Users/Wellyton/Desktop/ssh-key-2026-02-08.key" ARQUIVO_LOCAL ubuntu@141.148.177.242:/home/ubuntu/24-7-Bot/

# Gerenciar bot
sudo systemctl restart 24-7-bot
sudo systemctl status 24-7-bot
sudo journalctl -u 24-7-bot -f

# Validar antes de deploy
python -c "import ast; ast.parse(open('main_247_fix.py', encoding='utf-8').read()); print('OK')"
```

## ⚙️ VARIÁVEIS DE AMBIENTE (.env na VPS)

```env
DISCORD_TOKEN=...
NITRADO_TOKEN=...
SERVICE_ID=...
FTP_HOST=...
FTP_PORT=21
FTP_USER=...
FTP_PASS=...
BAN_CHANNEL=...
PORTAL_CHANNEL_ID=...
VERIFIED_ROLE_ID=...
DISCORD_WEBHOOK_URL=...
RADAR_WEBHOOK_URL=...
RULES_CHANNEL_ID=1384330092586729472
TRUCK_ALERTS_CHANNEL_ID=1384330076174155867
ADMIN_BACKUP_CHANNEL_ID=...  # NOVO - canal para receber backup diário do DB
BASE_RADIUS=50
```
