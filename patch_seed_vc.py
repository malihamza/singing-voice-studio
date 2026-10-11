"""Apply the upstream Seed-VC Apple MPS float64 fix idempotently."""

from pathlib import Path

path = Path(__file__).resolve().parent / "vendor" / "seed-vc" / "inference.py"
source = path.read_text(encoding="utf-8")
old = """        F0_ori = torch.from_numpy(F0_ori).to(device)[None]
        F0_alt = torch.from_numpy(F0_alt).to(device)[None]
"""
new = """        # Apple MPS does not support float64; RMVPE may return float64 arrays.
        F0_ori = torch.from_numpy(F0_ori).float().to(device)[None]
        F0_alt = torch.from_numpy(F0_alt).float().to(device)[None]
"""
if old in source:
    source = source.replace(old, new)
elif new not in source:
    raise RuntimeError("Seed-VC inference.py changed; MPS patch could not be applied safely.")

old_save = """    torchaudio.save(os.path.join(args.output, f"vc_{source_name}_{target_name}_{length_adjust}_{diffusion_steps}_{inference_cfg_rate}.wav"), vc_wave.cpu(), sr)
"""
new_save = """    # Avoid torchaudio's new optional TorchCodec dependency for simple WAV output.
    import soundfile as sf
    output_path = os.path.join(args.output, f"vc_{source_name}_{target_name}_{length_adjust}_{diffusion_steps}_{inference_cfg_rate}.wav")
    sf.write(output_path, vc_wave.squeeze(0).cpu().numpy(), sr, subtype="PCM_16")
"""
if old_save in source:
    source = source.replace(old_save, new_save)
elif new_save not in source:
    raise RuntimeError("Seed-VC WAV save patch could not be applied safely.")

old_chunk_setup = """    processed_frames = 0
    generated_wave_chunks = []
    # generate chunk by chunk and stream the output
"""
new_chunk_setup = """    processed_frames = 0
    generated_wave_chunks = []
    chunk_advance = max_source_window - overlap_frame_len
    total_chunks = (1 if cond.size(1) <= max_source_window else
                    1 + int(np.ceil((cond.size(1) - max_source_window) / chunk_advance)))
    completed_chunks = 0
    print(f"SEEDVC_CHUNKS_TOTAL={total_chunks}", flush=True)
    # generate chunk by chunk and stream the output
"""
if old_chunk_setup in source:
    source = source.replace(old_chunk_setup, new_chunk_setup)
elif new_chunk_setup not in source:
    raise RuntimeError("Seed-VC chunk setup patch could not be applied safely.")

old_chunk_done = """        vc_wave = vocoder_fn(vc_target.float()).squeeze()
        vc_wave = vc_wave[None, :]
"""
new_chunk_done = """        vc_wave = vocoder_fn(vc_target.float()).squeeze()
        vc_wave = vc_wave[None, :]
        completed_chunks += 1
        print(f"SEEDVC_CHUNK={completed_chunks}/{total_chunks}", flush=True)
"""
if old_chunk_done in source:
    source = source.replace(old_chunk_done, new_chunk_done)
elif new_chunk_done not in source:
    raise RuntimeError("Seed-VC chunk progress patch could not be applied safely.")

path.write_text(source, encoding="utf-8")
print("Seed-VC Apple MPS and chunk-progress patches are applied")
