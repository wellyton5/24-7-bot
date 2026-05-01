import socket
import binascii
import time

def kick_player_rcon(ip, port, password, player_name):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(3.0)

        # Login Packet
        # 0x42 0x45 0x-- 0x-- 0x-- 0x-- 0xff 0x00 password
        import zlib
        
        login_header = b'BE'
        password_bytes = password.encode('utf-8')
        payload = bytes([0xFF, 0x00]) + password_bytes
        
        # calculate crc32
        crc = zlib.crc32(payload) & 0xffffffff
        crc_bytes = crc.to_bytes(4, byteorder='little')
        
        packet = login_header + crc_bytes + payload
        
        s.sendto(packet, (ip, port))
        
        try:
            data, addr = s.recvfrom(4096)
            # Response: b'BE' + 4-byte CRC32 + b'\xff' + b'\x00' + 1-byte status
            if len(data) >= 9 and data[7] == 0x00 and data[8] == 0x01:
                print('RCON Login: SUCCESS')
            else:
                print('RCON Login: FAILED/BAD RESPONSE')
                return False
        except socket.timeout:
            print('RCON Login: TIMEOUT (RCON porta bloqueada ou invalida)')
            return False

        # Kick Command
        cmd = f'kick {player_name}'.encode('utf-8')
        seq = 0
        cmd_payload = bytes([0xFF, 0x01, seq]) + cmd
        crc_cmd = zlib.crc32(cmd_payload) & 0xffffffff
        cmd_packet = login_header + crc_cmd.to_bytes(4, byteorder='little') + cmd_payload
        
        s.sendto(cmd_packet, (ip, port))
        
        try:
            data, addr = s.recvfrom(4096)
            print('RCON CMD Response length:', len(data))
            return True
        except socket.timeout:
            print('RCON CMD Response: TIMEOUT')
            # It still might have executed.
            return True

    except Exception as e:
        print('Rcon error:', e)
        return False
    finally:
        s.close()

if __name__ == '__main__':
    kick_player_rcon('31.214.158.194', 13703, 'BigodeTexasRcon2026!', 'Teste')
