"""Explicit public model download. Never opens an audio device or uses API keys."""
import os
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'services/broker/src'))
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN']='1'
from immortility_broker.voice_models import prepare
destination=Path.home()/'AppData/Local/Immortility/models'
result=prepare(destination)
print('Local voice models ready:',result['ready'])
