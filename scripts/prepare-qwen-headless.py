"""Materialize a pinned, separately named research fork. Does not install or execute Qwen."""

import ast
import argparse
import difflib
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "integrations/qwen-headless"
WORK = ROOT / ".cache/qwen-remediation-v2"
SOURCE_SHA = "00969daa8064e23adc9e5f52cdf20cf247f94159"
ARCHIVE_SHA = "545855ad56ddbddc237b746922aed5c789ca21e901347e68d5ee0deecfd2bd58"
SOURCE_URL = f"https://codeload.github.com/andimarafioti/Qwen3-TTS/zip/{SOURCE_SHA}"


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError("Reviewed patch context changed; refusing to guess")
    return text.replace(old, new, 1)


def transform(name: str, text: str) -> str:
    original = text
    if name == "qwen_tts/core/__init__.py":
        text = "\n".join(line for line in text.splitlines() if "tokenizer_25hz" not in line) + "\n"
    if name == "qwen_tts/inference/qwen3_tts_tokenizer.py":
        text = (
            "\n".join(line for line in text.splitlines() if "Qwen3TTSTokenizerV1" not in line)
            + "\n"
        )
        text = replace_once(
            text,
            "        inst = cls()",
            "        from .._immortility_security import local_options\n        pretrained_model_name_or_path, kwargs = local_options(pretrained_model_name_or_path, kwargs, tokenizer=True)\n        inst = cls()",
        )
        text = replace_once(
            text,
            "AutoFeatureExtractor.from_pretrained(pretrained_model_name_or_path)",
            "AutoFeatureExtractor.from_pretrained(pretrained_model_name_or_path, local_files_only=True, trust_remote_code=False)",
        )
    if name == "qwen_tts/inference/qwen3_tts_model.py":
        text = replace_once(
            text,
            '        AutoConfig.register("qwen3_tts", Qwen3TTSConfig)',
            '        from .._immortility_security import local_options\n        pretrained_model_name_or_path, kwargs = local_options(pretrained_model_name_or_path, kwargs)\n        AutoConfig.register("qwen3_tts", Qwen3TTSConfig)',
        )
        text = replace_once(
            text,
            "fix_mistral_regex=True,)",
            "fix_mistral_regex=True, local_files_only=True, trust_remote_code=False)",
        )
    if name in {
        "qwen_tts/inference/qwen3_tts_model.py",
        "qwen_tts/inference/qwen3_tts_tokenizer.py",
    }:
        old = """        if self._is_url(x):
            with urllib.request.urlopen(x) as resp:
                audio_bytes = resp.read()
            with io.BytesIO(audio_bytes) as f:
                audio, sr = sf.read(f, dtype="float32", always_2d=False)
        elif self._is_probably_base64(x):"""
        text = replace_once(
            text,
            old,
            """        if self._is_url(x):
            raise ValueError("remote_audio_disabled")
        elif self._is_probably_base64(x):""",
        )
    if name == "qwen_tts/core/models/modeling_qwen3_tts.py":
        start = text.index("def download_weights_from_hf_specific(")
        end = text.index("class Res2NetBlock", start)
        text = (
            text[:start]
            + 'def download_weights_from_hf_specific(*args, **kwargs):\n    raise ValueError("remote_model_download_disabled")\n\n\n'
            + text[end:]
        )
        text = text.replace(
            'local_files_only=kwargs.pop("local_files_only", False)', "local_files_only=True"
        )
        text = replace_once(
            text,
            "        speech_tokenizer = Qwen3TTSTokenizer.from_pretrained(",
            "        kwargs.update(local_files_only=True, trust_remote_code=False, use_safetensors=True, weights_only=True)\n        speech_tokenizer = Qwen3TTSTokenizer.from_pretrained(",
        )
    if text != original:
        text = (
            "# Modified by Immortility, 2026-11-13: headless 12Hz/offline research derivative.\n"
            + text
        )
    ast.parse(text, filename=name)
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=WORK / "source")
    args = parser.parse_args()
    archive = WORK / "public/pr-source.zip"
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        with urlopen(SOURCE_URL, timeout=30) as response:
            archive.write_bytes(response.read(8 * 1024 * 1024))
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA:
        raise ValueError("Upstream source archive checksum mismatch")
    target = args.output.resolve()
    if not target.is_relative_to(WORK.resolve()):
        raise ValueError("Candidate source must stay inside the research cache")
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise ValueError("Refusing to overwrite a materialized candidate")
    differences, fingerprints = [], {}
    with zipfile.ZipFile(archive) as handle:
        prefix = f"Qwen3-TTS-{SOURCE_SHA}/"
        license_text = handle.read(prefix + "LICENSE").decode()
        if "Apache License" not in license_text or "Version 2.0" not in license_text:
            raise ValueError("Reviewed Apache license missing")
        (target / "LICENSE").write_text(license_text, encoding="utf-8")
        for entry in handle.infolist():
            name = entry.filename.removeprefix(prefix)
            if not name.startswith("qwen_tts/") or entry.is_dir():
                continue
            if (
                ".." in Path(name).parts
                or "/cli/" in name
                or "tokenizer_25hz/" in name
                or name.endswith("__main__.py")
            ):
                continue
            original = handle.read(entry).decode("utf-8")
            updated = transform(name, original)
            resource = target / name
            resource.parent.mkdir(parents=True, exist_ok=True)
            resource.write_text(updated, encoding="utf-8", newline="\n")
            fingerprints[name] = {
                "upstream_sha256": hashlib.sha256(original.encode()).hexdigest(),
                "candidate_sha256": hashlib.sha256(updated.encode()).hexdigest(),
            }
            # Normalize an upstream missing terminal newline in the human review diff only.
            if original != updated:
                differences.extend(
                    difflib.unified_diff(
                        (original.rstrip("\n") + "\n").splitlines(True),
                        (updated.rstrip("\n") + "\n").splitlines(True),
                        fromfile="upstream/" + name,
                        tofile="candidate/" + name,
                    )
                )
    for source, destination in (
        ("pyproject.toml", "pyproject.toml"),
        ("security.py", "qwen_tts/_immortility_security.py"),
        ("artifacts.json", "qwen_tts/artifacts.json"),
        ("profile_contract.py", "qwen_tts/_immortility_profile.py"),
        ("uv.lock", "uv.lock"),
    ):
        shutil.copyfile(SPEC / source, target / destination)
    notice = (
        "Research-only Immortility derivative of Qwen3-TTS, Apache-2.0.\nCopyright 2026 Alibaba Qwen team and original source contributors.\nBased on unmerged PR #360 by andimarafioti, commit "
        + SOURCE_SHA
        + ".\nImmortility modifications: 12Hz-only headless packaging, patched dependency contract, local-artifact validation, offline loaders and remote-input denial. No official Qwen endorsement.\n"
    )
    (target / "NOTICE").write_text(notice, encoding="utf-8")
    (SPEC / "reviewed-source.patch").write_text("".join(differences), encoding="utf-8")
    manifest = {
        "upstream_commit": SOURCE_SHA,
        "archive_url": SOURCE_URL,
        "archive_sha256": ARCHIVE_SHA,
        "license": "Apache-2.0",
        "status": "research-only; not activated",
        "source_files": fingerprints,
        "local_files": {
            str(p.relative_to(SPEC)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (
                SPEC / "pyproject.toml",
                SPEC / "security.py",
                SPEC / "artifacts.json",
                SPEC / "profile_contract.py",
                SPEC / "uv.lock",
            )
        },
    }
    (SPEC / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Materialized reviewed research source:", target.relative_to(ROOT))


if __name__ == "__main__":
    main()
