"""Move only the existing OpenRouter credential to the current Windows user's vault."""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'services/broker/src'))
from immortility_broker.secrets import CredentialError,CredentialManager,migrate_env

try:
    migrate_env(root/'.env',CredentialManager())
    print('OpenRouter credential verified in Windows Credential Manager; plaintext .env entry removed.')
except CredentialError as error:
    print(str(error))
    raise SystemExit(1)
