"""Drive ue_02_materials.py through the editor bridge in small batches (see the note in ue_02 about thumbnail memory).

usage: py -3 ue_materials.py [--assign-only] [--meshes=SM_A,SM_B]
"""
import subprocess
import sys

HERE = r'G:\Claude\mongha-ue\tools'


def bridge(*args):
    r = subprocess.run([sys.executable, HERE + r'\ue_bridge.py', 'file', HERE + r'\ue_02_materials.py', *args],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    print(args, r.stdout.strip().splitlines()[-2:] if r.stdout.strip() else r.stderr[-800:], flush=True)
    if r.returncode != 0:
        print(r.stdout[-3000:])
        sys.exit(1)
    return r.stdout


meshes = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--meshes=')), '')
if '--assign-only' not in sys.argv:
    bridge('PART=masters')
    for a in range(0, 400, 16):   # empty batch ends the loop
        if 'done now 0' in bridge(f'PART=inst:{a}:{a + 16}'):
            break
bridge('PART=assign', *([f'MESHES={meshes}'] if meshes else []))
