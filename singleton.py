import fcntl, sys
fp = open(" /tmp/bot_24_7.lock\, \w\)
try:
 fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
 print(\--- ERRO: O bot ja esta rodando! ---\)
 sys.exit(1)
