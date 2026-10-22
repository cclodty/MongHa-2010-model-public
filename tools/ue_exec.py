"""Run Python inside the open Unreal Editor via the PythonScriptPlugin remote-execution protocol.

usage: py -3 ue_exec.py file <script.py> | py -3 ue_exec.py cmd "<statement>"
"""
import sys
import time

sys.path.insert(0, r"G:\UE_5.8\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python")
import remote_execution as rex  # noqa: E402


def main():
    mode, arg = sys.argv[1], sys.argv[2]
    rc = rex.RemoteExecution()
    rc.start()
    t0 = time.time()
    while not rc.remote_nodes and time.time() - t0 < 25:
        time.sleep(0.25)
    if not rc.remote_nodes:
        print('NO_EDITOR_NODE (is the editor open with remote execution enabled?)')
        rc.stop()
        sys.exit(2)
    rc.open_command_connection(rc.remote_nodes[0]['node_id'])
    if mode == 'file':
        with open(arg, encoding='utf-8') as fh:
            src = fh.read()
        pre = ''.join('%s = %r' % tuple(kv.split('=', 1)) + chr(10) for kv in sys.argv[3:])
        src = pre + src
        res = rc.run_command(src, unattended=True, exec_mode=rex.MODE_EXEC_FILE)
    else:
        res = rc.run_command(arg, unattended=True, exec_mode=rex.MODE_EXEC_STATEMENT)
    for o in res.get('output', []):
        line = o.get('output', '').rstrip()
        if line:
            print(line)
    print('SUCCESS' if res.get('success') else 'FAILED', res.get('result', '')[:2000])
    rc.stop()
    sys.exit(0 if res.get('success') else 1)


if __name__ == '__main__':
    main()
