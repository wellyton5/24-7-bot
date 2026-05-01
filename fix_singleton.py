import sys
import os
path = '/home/ubuntu/24-7-Bot/main_24-7.py'
if not os.path.exists(path):
    sys.exit(1)
content = open(path).read()
if 'import fcntl' not in content:
    lines = content.splitlines()
    lock_code = [
        'import fcntl',
        'import sys',
        'fp = open(" /tmp/bot_24_7.lock\, \w\)',
 'try:',
 ' fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)',
 'except IOError:',
 ' print(\--- ERRO: O bot ja esta rodando! ---\)',
 ' sys.exit(1)',
 ''
 ]
 # Insere logo após os primeiros imports
 new_lines = lines[:5] + lock_code + lines[5:]
 with open(path, 'w') as f:
 f.write('\\n'.join(new_lines))
 print('Trava singleton aplicada com sucesso.')
else:
 print('Trava singleton ja existe.')
