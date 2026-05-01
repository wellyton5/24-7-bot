# -*- coding: utf-8 -*-
"""Script para modificar init.c no FTP - Adiciona Device ID logging"""
import os
import io
import re
from ftplib import FTP
from dotenv import load_dotenv

load_dotenv()

ftp = FTP()
ftp.connect(os.environ["FTP_HOST"], int(os.environ.get("FTP_PORT", 21)))
ftp.login(os.environ["FTP_USER"], os.environ["FTP_PASS"])

ftp.cwd("/dayzxb_missions/dayzOffline.chernarusplus")
buf = io.BytesIO()
ftp.retrbinary("RETR init.c", buf.write)
content = buf.getvalue().decode("utf-8", errors="replace")

# Use regex to find and replace the specific block
# Match: pUID = identity.GetId();\n  }
# Replace with the same + GetPlainId() + Print

old_pattern = r'(pUID = identity\.GetId\(\);)\s*(\})'
new_replacement = r'''\1
    pPlainId = identity.GetPlainId();
    // [BigodeBot 24/7] Device ID Logger - Captura Device ID do console Xbox
    Print("[DEVICE_LOG] " + identity.GetName() + "|" + pUID + "|" + pPlainId);
  \2'''

# Also need to add pPlainId declaration
# Find: string pUID = "";
# Add after: string pPlainId = "";

if 'pPlainId' in content:
    print("WARNING: pPlainId already exists in init.c - skipping modification")
else:
    # Step 1: Add pPlainId declaration after pUID declaration
    content = content.replace(
        'string pUID = "";',
        'string pUID = "";\n  string pPlainId = "";',
        1  # Only first occurrence
    )

    # Step 2: Add GetPlainId() and Print after GetId()
    content = re.sub(
        r'(pUID = identity\.GetId\(\);)\s*\n(\s*\})',
        r'\1\n    pPlainId = identity.GetPlainId();\n    // [BigodeBot 24/7] Device ID Logger\n    Print("[DEVICE_LOG] " + identity.GetName() + "|" + pUID + "|" + pPlainId);\n\2',
        content,
        count=1
    )

    # Verify the modification
    if 'pPlainId = identity.GetPlainId()' in content:
        print("SUCCESS: init.c modified with Device ID logging")

        # Upload
        buf_out = io.BytesIO(content.encode("utf-8"))
        ftp.storbinary("STOR init.c", buf_out)
        print("Modified init.c uploaded to FTP successfully!")
    else:
        print("ERROR: Modification failed")
        # Debug
        idx = content.find("GetId()")
        if idx >= 0:
            print("Context around GetId():")
            print(repr(content[idx-50:idx+100]))

ftp.quit()
