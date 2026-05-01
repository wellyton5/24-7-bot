#!/bin/bash
# Script de inicialização do bot 24/7

# Parar instância anterior
pkill -f 'python3 main.py'

# Aguardar
sleep 2

# Adicionar PATH
export PATH=$PATH:/home/ubuntu/.local/bin

# Ir para diretório
cd ~/24-7-Bot

# Iniciar bot
nohup python3 main.py > bot.log 2>&1 &

# Aguardar inicialização
sleep 5

# Mostrar status
echo "Bot iniciado com PID:"
pgrep -f 'python3 main.py'

echo ""
echo "Últimas linhas do log:"
tail -20 bot.log
