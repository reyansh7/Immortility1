"""Check the actual configured provider key never entered tracked source or UI bundles."""
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'services/broker/src'))
from immortility_broker.config import Settings
settings=Settings()
settings.load_credentials()
keys=[
    settings.openrouter_api_key.get_secret_value(),
    settings.gemini_api_key.get_secret_value(),
    settings.groq_api_key.get_secret_value(),
    settings.nvidia_api_key.get_secret_value(),
]
keys=[key for key in keys if key]
assert '.env' in (root/'.gitignore').read_text()
if keys:
    for directory in [root/'apps/desktop/src',root/'apps/desktop/dist',root/'docs',root/'config']:
        if not directory.exists():
            continue
        for path in directory.rglob('*'):
            if path.is_file():
                blob=path.read_bytes()
                for key in keys:
                    assert key.encode() not in blob, 'Provider key found outside private storage'
    print('Configured provider keys are absent from frontend source, bundle, docs and config.')
else:
    print('No configured provider key; static boundary checks only.')
