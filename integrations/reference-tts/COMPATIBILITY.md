# XTTS evaluation compatibility adapter

Reviewed source: idiap/coqui-ai-TTS commit
`ed4ec35c2282bf61a6b4297f066892d33ae71fc0`, published coqui-tts 0.28.0.

The first native check exposed two integration issues: Xtts.eval returns None,
and Xtts._load_checkpoint converts a legacy config pickle and calls torch.save on
the original checkpoint. The app adapter now avoids chaining eval and subclasses
only the checkpoint reader. It uses restricted, memory-mapped torch.load with the
same four reviewed legacy config classes, validates a tensor-only model state,
and never serializes the config or writes the model. It does not patch installed
packages, global Transformers behavior, metadata or arbitrary safe globals.

The integrity gate rejected the upstream-rewritten first download. The official
pinned original is restored and remains the required identity. The changed hash
is not accepted as a new baseline. `scripts/verify-reference-contracts.py` tests
read-only loading, rejection of unknown pickle classes and non-tensor state using
small CPU fixtures; these are separate from pretrained inference tests.

Current Coqui also requires its codec extra on Torch 2.9+ at import, even though
our approved local PCM WAV path uses SoundFile plus the documented model tensor
conditioning methods. Six is imported but undeclared in the published base graph.
Both were added as explicit, audited pinned dependencies, without --no-deps or
forced installation. TorchAudio 2.11's stable ABI supports Torch 2.15 per its
official installation documentation; actual CUDA inference must still pass.
