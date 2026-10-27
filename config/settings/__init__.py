import os
env = os.getenv('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
if 'prod' in env:
    from .prod import *
else:
    from .dev import *