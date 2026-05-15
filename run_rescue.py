import runpy
import sys
print('RUNNER: starting rescue app')
try:
    runpy.run_path('c:\\Users\\Osana\\Documents\\1212\\rescue app.py', run_name='__main__')
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
print('RUNNER: finished')
