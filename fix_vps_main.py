import os
vps_path = '/home/ubuntu/24-7-Bot/main_24-7.py'
with open(vps_path, 'r') as f:
    lines = f.readlines()
lock_lines = [
    'import fcntl, sys\n',
    'fp = open(" /tmp/bot_24_7.lock\, \w\)\n',
 'try:\n',
 ' fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)\n',
 'except IOError:\n',
 ' sys.exit(1)\n'
]
if 'import fcntl' in lines[0]:
 new_lines = lock_lines + lines[6:]
else:
 new_lines = lock_lines + lines
with open(vps_path, 'w') as f:
 f.writelines(new_lines)
