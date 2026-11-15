"""Isolated, broker-authorized reference-TTS worker. Never an agent loop."""

import contextlib
import json
import os
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any

from .reference_contracts import ROOT, ReferenceRequest, approved_paths, sha256

PROTOCOL = sys.stdout
MEMORY = {"peak_mib": 0.0}


def sample_memory() -> None:
    import psutil

    process = psutil.Process()
    while True:
        MEMORY["peak_mib"] = max(MEMORY["peak_mib"], process.memory_info().rss / 1024**2)
        time.sleep(0.05)


def emit(kind: str, **data: Any) -> None:
    PROTOCOL.write(json.dumps({"kind": kind, **data}) + "\n")
    PROTOCOL.flush()


class Engine:
    def __init__(self, model_root: Path):
        import psutil
        import torch
        from TTS.tts.configs.xtts_config import XttsConfig
        from .reference_xtts import create_model

        if psutil.virtual_memory().available < 2 * 1024**3:
            raise RuntimeError("insufficient_available_ram")
        if not torch.cuda.is_available():
            raise RuntimeError("cuda_unavailable")
        from .gpu_budget import allow_heavy_gpu, free_vram_mib

        allowed, reason = allow_heavy_gpu(free_vram_mib(), 0)
        if not allowed:
            raise RuntimeError(reason)
        torch.set_num_threads(2)
        torch.cuda.set_per_process_memory_fraction(0.80, 0)
        torch.cuda.reset_peak_memory_stats()
        emit("state", state="loading_weights")
        start = time.perf_counter()
        config = XttsConfig()
        config.load_json(str(model_root / "config.json"))
        if config.model != "xtts":
            raise ValueError("unauthorized_model_type")
        disabled_speakers = model_root / "__disabled_stock_speakers__.pth"
        if disabled_speakers.exists():
            raise ValueError("unauthorized_stock_speakers")
        # Construct on GPU instead of retaining a second ~1.8 GB CPU parameter
        # allocation. The reviewed checkpoint reader explicitly maps CPU pages;
        # load_state_dict copies them into the GPU tensors, without a meta shim.
        with torch.device("cuda"):
            self.model = create_model(config)
            self.model.load_checkpoint(
                config,
                checkpoint_dir=model_root,
                vocab_path=model_root / "vocab.json",
                speaker_file_path=disabled_speakers,
                use_deepspeed=False,
            )
            # Xtts.eval() overrides nn.Module.eval and returns None in this release.
            self.model.eval()
        # Legacy FloatTensor constructors ignore the default-device context;
        # move their small registered buffers/parameters as well.
        self.model.to("cuda")
        if any(
            value.device.type != "cuda"
            for value in list(self.model.parameters()) + list(self.model.buffers())
        ):
            raise RuntimeError("incomplete_cuda_placement")
        torch.cuda.synchronize()
        self.load_seconds = time.perf_counter() - start
        self.conditioning: dict[str, tuple[Any, Any]] = {}
        self.primed = False

    def prepare(self, path: Path) -> None:
        gpt, speaker = self.condition(path)
        if not self.primed:
            # Prime lazy GPU/vocoder kernels once with fixed local text. No
            # playback, cloud tokens, files or weight updates are involved.
            for _ in self.model.inference_stream(
                "Ready.", "en", gpt, speaker, stream_chunk_size=16, temperature=0.65
            ):
                pass
            self.primed = True

    def condition(self, path: Path) -> tuple[Any, Any]:
        import soundfile as sf
        import torch

        # SoundFile handles our reviewed local PCM WAV, avoiding optional FFmpeg IO.
        # No global monkey patch or permissive deserializer is installed.
        key = str(path) + sha256(path)
        if key not in self.conditioning:
            audio, rate = sf.read(path, dtype="float32", always_2d=True)
            if audio.shape[1] != 1 or not 3 <= len(audio) / rate <= 12:
                raise ValueError("reference_audio_bounds")
            tensor = torch.from_numpy(audio.T.copy()).to("cuda")
            with torch.inference_mode():
                gpt = self.model.get_gpt_cond_latents(tensor, rate, length=8, chunk_length=4)
                speaker = self.model.get_speaker_embedding(tensor, rate)
            self.conditioning[key] = (gpt, speaker)
        return self.conditioning[key]

    def synthesize(self, request: ReferenceRequest, reference: Path) -> None:
        import numpy as np
        import psutil
        import soundfile as sf
        import torch
        from .infernal import Coloration, InfernalDSP

        folder = ROOT / "data/reference-tts/runs" / request.run_id
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / (request.case + "-" + request.reference + "-dry.wav")
        if target.exists():
            raise ValueError("output_already_exists")
        temporary = target.with_suffix(".partial.wav")
        text = (
            request.text
            if request.operation == "speak"
            else json.loads((ROOT / "config/reference-tts-evaluation.json").read_text())[
                request.case
            ]
        )
        if not text.strip():
            raise ValueError("empty_speech")
        condition_start = time.perf_counter()
        gpt, speaker = self.condition(reference)
        conditioning_seconds = time.perf_counter() - condition_start
        torch.manual_seed(42)
        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        cpu_before = psutil.Process().cpu_times()
        blocks: list[Any] = []
        first_audio: float | None = None
        try:
            with sf.SoundFile(
                temporary, "w", samplerate=24000, channels=1, subtype="PCM_16"
            ) as output:
                with torch.inference_mode():
                    for chunk in self.model.inference_stream(
                        text,
                        "en",
                        gpt,
                        speaker,
                        stream_chunk_size=16,
                        temperature=0.65,
                        speed=request.speed,
                        enable_text_splitting=True,
                    ):
                        pcm = chunk.detach().float().cpu().numpy().reshape(-1)
                        if (
                            not np.isfinite(pcm).all()
                            or sum(map(len, blocks)) + len(pcm) > 24000 * 30
                        ):
                            raise ValueError("generated_audio_bounds")
                        if first_audio is None:
                            first_audio = time.perf_counter() - started
                        output.write(np.clip(pcm, -0.98, 0.98))
                        blocks.append(pcm)
                        emit("chunk", samples=len(pcm), sample_rate=24000)
            torch.cuda.synchronize()
            dry = np.concatenate(blocks)
            dry *= 0.1 / max(1e-9, float(np.sqrt(np.mean(dry * dry))))
            dry *= min(1.0, 0.9 / max(1e-9, float(np.max(np.abs(dry)))))
            sf.write(temporary, dry, 24000, subtype="PCM_16")
            temporary.replace(target)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        after = psutil.Process().cpu_times()
        if request.operation == "speak":
            from .reference_effects import mechanical

            effects_started = time.perf_counter()
            output = mechanical(dry, 24000)
            mechanical_path = target.with_name("mechanical.wav")
            sf.write(mechanical_path, output, 24000, subtype="PCM_16")
            target.unlink(missing_ok=True)
            emit(
                "done",
                path=str(mechanical_path.relative_to(ROOT)),
                first_chunk_seconds=first_audio,
                synthesis_seconds=time.perf_counter() - started,
                effects_ms=(time.perf_counter() - effects_started) * 1000,
            )
            return
        generation_seconds = time.perf_counter() - started
        peak_allocated = torch.cuda.max_memory_allocated() / 1024**2
        peak_reserved = torch.cuda.max_memory_reserved() / 1024**2
        effects_started = time.perf_counter()
        metal = InfernalDSP(Coloration(0, 0.24, 0.35, "clear_baritone")).process(dry, 24000)
        metal *= 0.1 / max(1e-9, float(np.sqrt(np.mean(metal * metal))))
        metal *= min(1.0, 0.9 / max(1e-9, float(np.max(np.abs(metal)))))
        metal_path = target.with_name(request.case + "-" + request.reference + "-metal.wav")
        sf.write(metal_path, metal, 24000, subtype="PCM_16")
        effects_ms = (time.perf_counter() - effects_started) * 1000
        similarity = {}
        candidates = {"cloned_dry": dry, "cloned_metal": metal}
        baseline = ROOT / "data/reference-tts/kokoro" / (request.case + "-onyx.wav")
        if baseline.is_file() and baseline.stat().st_size < 3_000_000:
            data, rate = sf.read(baseline, dtype="float32")
            if rate == 24000:
                candidates["original_onyx"] = data
        with torch.inference_mode():
            for name, data in candidates.items():
                embedding = self.model.get_speaker_embedding(
                    torch.from_numpy(data.copy()).reshape(1, -1).to("cuda"), 24000
                )
                similarity[name] = float(
                    torch.nn.functional.cosine_similarity(
                        embedding.reshape(-1), speaker.reshape(-1), dim=0
                    ).item()
                )
        emit(
            "done",
            path=str(target.relative_to(ROOT)),
            metal_path=str(metal_path.relative_to(ROOT)),
            effects_ms=effects_ms,
            xtts_internal_encoder_cosine=similarity,
            case=request.case,
            first_chunk_seconds=first_audio,
            synthesis_seconds=generation_seconds,
            conditioning_seconds=conditioning_seconds,
            load_seconds=self.load_seconds,
            duration_seconds=sum(map(len, blocks)) / 24000,
            gpu_peak_allocated_mib=peak_allocated,
            gpu_peak_reserved_mib=peak_reserved,
            working_set_mib=psutil.Process().memory_info().rss / 1024**2,
            worker_sampled_peak_working_set_mib=MEMORY["peak_mib"],
            cpu_seconds=after.user + after.system - cpu_before.user - cpu_before.system,
        )


def main() -> None:
    if os.environ.get("IMMORTILITY_REFERENCE_EVALUATION") != "1":
        emit("error", code="reference_evaluation_disabled")
        return
    engine = None
    model_digest = None

    # Python-level egress defense; this is not an OS-level sandbox.
    def audit(event: str, args: tuple[Any, ...]) -> None:
        if event in {"socket.connect", "socket.getaddrinfo"}:
            raise PermissionError("reference_worker_network_disabled")

    sys.addaudithook(audit)
    if os.environ.get("IMMORTILITY_REFERENCE_PROFILE") == "1":
        threading.Thread(target=sample_memory, daemon=True).start()
    while line := sys.stdin.readline(4097):
        try:
            if len(line) > 4096:
                raise ValueError("request_too_large")
            request = ReferenceRequest.model_validate_json(line)
            if model_digest is not None and request.model_manifest_sha256 != model_digest:
                raise ValueError("loaded_model_manifest_changed")
            model_root, reference = approved_paths(request, loaded_model=engine is not None)
            with contextlib.redirect_stdout(sys.stderr):
                if engine is None:
                    engine = Engine(model_root)
                    model_digest = request.model_manifest_sha256
                if request.operation == "prepare":
                    import psutil
                    import torch

                    engine.prepare(reference)
                    emit(
                        "done",
                        ready=True,
                        load_seconds=engine.load_seconds,
                        resident_ram_mib=psutil.Process().memory_info().rss / 1024**2,
                        gpu_allocated_mib=torch.cuda.memory_allocated() / 1024**2,
                        gpu_reserved_mib=torch.cuda.memory_reserved() / 1024**2,
                    )
                else:
                    engine.synthesize(request, reference)
        except Exception as error:
            traceback.print_exc(file=sys.stderr)
            known = {
                "insufficient_available_ram",
                "cuda_unavailable",
                "asset_integrity_failed",
                "loaded_model_manifest_changed",
            }
            emit("error", code=str(error) if str(error) in known else type(error).__name__)
            return


if __name__ == "__main__":
    main()
