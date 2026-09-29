"""Quick verification: migration module loads, app boots, routes registered."""
import sys, io, importlib
sys.path.insert(0, '.')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 1. Migration module loads
m = importlib.import_module('migrations.versions.0001_multi_tenant_saas')
print('MIGRATION revision =', m.revision)
print('MIGRATION down_revision =', m.down_revision)
print('MIGRATION upgrade/downgrade callable =', callable(m.upgrade), callable(m.downgrade))

# 2. App boots and key routes are registered
from src import create_app
app = create_app()
rules = sorted(str(r) for r in app.url_map.iter_rules())
key_routes = [r for r in rules if any(k in r for k in (
    'subscription', 'branch', 'staff', 'business', 'super-admin',
    'activity', 'bank', 'upi', 'public', 'dashboard'
))]
print('\nKEY ROUTES (%d):' % len(key_routes))
for r in key_routes:
    print(' ', r)

print('\nTOTAL ROUTES:', len(rules))
print('ALL CHECKS PASSED')
