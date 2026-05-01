import io
import os
from dotenv import load_dotenv
from ftp_helpers import connect_ftp

load_dotenv()


def find_construction_examples():
    ftp = connect_ftp()
    if not ftp:
        return

    for path in ["/dayzxb/config", "/dayzxb", "/profile"]:
        try:
            ftp.cwd(path)
            items = ftp.nlst()
            adm_files = sorted(
                [f"{path}/{f}" for f in items if f.lower().endswith(".adm")],
                reverse=True,
            )

            for log_file in adm_files[:20]:  # Checar mais logs
                print(f"Lendo {log_file}...")
                ftp.voidcmd("TYPE I")
                bio = io.BytesIO()
                ftp.retrbinary(f"RETR {log_file}", bio.write)
                content = bio.getvalue().decode("utf-8", errors="ignore")

                for line in content.split("\n"):
                    l = line.lower()
                    if ("fence" in l or "gate" in l or "watchtower" in l) and (
                        "built" in l or "placed" in l
                    ):
                        print(f"ENCONTRADO: {line}")
        except:
            continue


if __name__ == "__main__":
    find_construction_examples()
