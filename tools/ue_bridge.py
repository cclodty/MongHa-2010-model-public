"""Send a Python file (or statement) to the editor bridge in Content/Python/init_unreal.py.

usage: py -3 ue_bridge.py file <script.py> [NAME=value ...] | py -3 ue_bridge.py cmd "<code>"
"""
import json
import socket
import sys


def run(code, timeout=1800):
    s = socket.create_connection(('127.0.0.1', 9876), timeout=10)
    s.settimeout(timeout)
    data = code.encode('utf-8')
    s.sendall(b'%08d' % len(data) + data)

    def exact(n):
        buf = b''
        while len(buf) < n:
            part = s.recv(n - len(buf))
            if not part:
                raise ConnectionError('bridge closed')
            buf += part
        return buf

    res = json.loads(exact(int(exact(8))).decode('utf-8'))
    s.close()
    return res


if __name__ == '__main__':
    mode, arg = sys.argv[1], sys.argv[2]
    if mode == 'file':
        pre = ''.join('%s = %r' % tuple(kv.split('=', 1)) + chr(10) for kv in sys.argv[3:])
        with open(arg, encoding='utf-8') as fh:
            code = pre + fh.read()
    else:
        code = arg
    try:
        r = run(code)
    except OSError as e:
        print('BRIDGE_UNAVAILABLE', e)
        sys.exit(2)
    sys.stdout.write(r['out'])
    print('OK' if r['ok'] else 'FAILED')
    sys.exit(0 if r['ok'] else 1)
