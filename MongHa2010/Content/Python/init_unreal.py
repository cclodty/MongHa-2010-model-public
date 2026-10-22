"""Local TCP bridge (127.0.0.1:9876) so scripts can run Python on the editor's game thread.

Protocol: 8-digit ASCII length + UTF-8 source; reply: 8-digit length + JSON {ok, out}.
Only binds to loopback. Used by G:/Claude/mongha-ue/tools/ue_bridge.py.
"""
import contextlib
import io
import json
import socket
import traceback

import unreal

_HOST, _PORT = '127.0.0.1', 9876
_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
_srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
_srv.bind((_HOST, _PORT))
_srv.listen(4)
_srv.setblocking(False)
_GLOBALS = {'__name__': '__bridge__', 'unreal': unreal}


def _recv_exact(conn, n):
    buf = b''
    while len(buf) < n:
        part = conn.recv(n - len(buf))
        if not part:
            raise ConnectionError('closed')
        buf += part
    return buf


def _tick(_dt):
    try:
        conn, _ = _srv.accept()
    except (BlockingIOError, OSError):
        return
    try:
        conn.setblocking(True)
        conn.settimeout(30)
        code = _recv_exact(conn, int(_recv_exact(conn, 8))).decode('utf-8')
        out = io.StringIO()
        ok = True
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            try:
                exec(compile(code, '<bridge>', 'exec'), dict(_GLOBALS))   # fresh namespace per request
            except Exception:
                ok = False
                traceback.print_exc()
        resp = json.dumps({'ok': ok, 'out': out.getvalue()}).encode('utf-8')
        conn.sendall(b'%08d' % len(resp) + resp)
    except Exception as e:  # never let the tick callback die
        unreal.log_warning('bridge: %s' % e)
    finally:
        conn.close()


unreal.register_slate_post_tick_callback(_tick)
unreal.log('bridge: listening on %s:%d' % (_HOST, _PORT))
