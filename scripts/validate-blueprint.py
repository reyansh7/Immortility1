#!/usr/bin/env python3
"""Zero-dependency sanity checks for this blueprint; not runtime app tests."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
required = [
    "README.md", "AGENTS.md", ".env.example",
    "docs/blueprint/00_PRODUCT_VISION.md",
    "docs/blueprint/01_SYSTEM_ARCHITECTURE.md",
    "docs/blueprint/02_TECH_STACK.md",
    "docs/blueprint/03_ROADMAP.md",
    "docs/blueprint/TARGET_REPOSITORY_TREE.md",
    "prompts/START_CODING_WITH_CURSOR.md",
]
for file in required:
    p = root / file
    assert p.exists() and p.stat().st_size > 100, f"Missing or empty: {file}"
for p in sorted((root / 'packages/contracts').rglob('*.json')):
    with p.open(encoding='utf-8') as f:
        data=json.load(f)
    assert isinstance(data, dict)
    print(f"[OK] {p.relative_to(root)}")
assert '.env' in (root / '.gitignore').read_text()
assert 'ALLOW_PAID_INFERENCE=false' in (root / '.env.example').read_text()
print('Blueprint files and JSON parse checks passed. Runtime tests are separate: scripts/check.ps1.')
