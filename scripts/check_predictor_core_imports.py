#!/usr/bin/env python3
import sys
import os
import importlib

root = os.path.dirname(os.path.dirname(__file__))  # workspace root
vendor_path = os.path.join(root, 'vendor')
sys.path.insert(0, vendor_path)

pkg_dir = os.path.join(vendor_path, 'predictor_core')
if not os.path.isdir(pkg_dir):
    print('vendor/predictor_core not found')
    sys.exit(2)

mods = []
for fn in os.listdir(pkg_dir):
    if not fn.endswith('.py'):
        continue
    if fn == '__init__.py':
        continue
    mods.append(fn[:-3])

failures = []
for m in sorted(mods):
    name = f'predictor_core.{m}'
    try:
        importlib.import_module(name)
        print(f'OK: {name}')
    except Exception as e:
        print(f'FAIL: {name} -> {e!r}')
        failures.append((name, repr(e)))

print('\nSummary:')
print(f'  modules checked: {len(mods)}')
print(f'  failures: {len(failures)}')
if failures:
    sys.exit(1)
else:
    sys.exit(0)
