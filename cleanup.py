#!/usr/bin/env python3
"""
Silent WAV Cleaner (recursive, with progress bar)

What it does:
  - Recursively finds .wav files under ROOT_DIRECTORY
  - For each file, samples NUM_SAMPLES_PER_FILE chunks, each INTERVAL_SECONDS long
  - If ALL sampled chunks are below SILENCE_THRESHOLD (peak abs amplitude), the file is treated as "silent"
  - AUDIT mode: does NOT delete; writes a CSV of files that *would* be deleted
  - DELETE mode: deletes files deemed silent; writes a CSV of files that were targeted (and any errors)

Designed for very large WAV files (multi-GB, multi-hour):
  - Reads only small chunks (7 seconds) from multiple positions using seek()
  - Does NOT load whole files into memory

Requirements:
  pip install soundfile numpy tqdm
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Tuple

import numpy as np
import soundfile as sf
from tqdm import tqdm

# ===================== HARD-CODED CONFIG =====================
ROOT_DIRECTORY = Path(r"PATH\HERE").resolve()  # <-- change me
MODE = "AUDIT"  # "AUDIT" or "DELETE"  <-- change me

REPORT_CSV = Path("silent_wav_audit.csv").resolve()

INTERVAL_SECONDS = 7

# For ~2 hour files: 16 samples => roughly every 7.5 minutes across the file
NUM_SAMPLES_PER_FILE = 16

# Practical default:
#  - 1e-6 is extremely strict (near digital zero)
#  - 1e-4 better matches "effectively silent" real-world files (tiny noise/dither/DC won't block deletion)
SILENCE_THRESHOLD = 1e-4

# Optional: only consider files at/above this size (0 disables the filter)
MIN_SIZE_BYTES = 0
# =============================================================


@dataclass
class ScanResult:
    # What file did we scan?
    path: str

    # SILENT => candidate for deletion
    # KEEP   => not silent
    # ERROR  => scan failed
    decision: str

    # Human-readable explanation (peak value, error message, etc.)
    detail: str

    # File + audio metadata for reporting
    size_bytes: int
    duration_sec: float
    samplerate: int
    channels: int

    # Scan parameters used (useful to confirm you scanned how you intended)
    interval_seconds: int
    num_samples_used: int
    threshold: float

    # The loudest peak we saw in any sampled chunk (useful for tuning threshold)
    max_abs_seen: float


def find_wav_files(root: Path) -> list[Path]:
    """
    Recursively gather all .wav files so tqdm can show a true progress bar (known total).
    """
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".wav"]


def compute_sample_positions(
    total_frames: int,
    sr: int,
    interval_seconds: int,
    num_samples: int,
) -> Tuple[np.ndarray, int]:
    """
    Decide where to sample inside the audio file.

    - interval_seconds determines chunk length (in seconds)
    - num_samples determines how many chunks we test
    - returns:
        starts: array of frame indices where each chunk begins
        frames_per_interval: how many frames to read for each chunk

    We sample at evenly spaced positions from start to end to increase confidence
    without scanning the entire file.
    """
    frames_per_interval = int(sr * interval_seconds)
    if sr <= 0 or total_frames <= 0 or frames_per_interval <= 0:
        return np.array([], dtype=np.int64), frames_per_interval

    # If the file is shorter than one interval, just sample from the start
    if total_frames <= frames_per_interval:
        return np.array([0], dtype=np.int64), frames_per_interval

    # Largest starting frame that still allows reading a full chunk
    max_start = total_frames - frames_per_interval

    # Evenly spaced chunk starts across the file
    starts = np.linspace(0, max_start, num=max(1, num_samples), dtype=np.int64)

    # Remove duplicates (can happen if file is short and num_samples is big)
    starts = np.unique(starts)
    return starts, frames_per_interval


def scan_wav_for_silence(wav_path: Path) -> ScanResult:
    """
    Returns ScanResult with decision:
      - KEEP: if ANY sampled chunk is above SILENCE_THRESHOLD
      - SILENT: if ALL sampled chunks are at/below SILENCE_THRESHOLD
      - ERROR: if the file cannot be read/parsed
    """
    try:
        size_bytes = wav_path.stat().st_size

        # Optional size gate (helps if you want to ignore tiny files)
        if size_bytes < MIN_SIZE_BYTES:
            return ScanResult(
                path=str(wav_path),
                decision="KEEP",
                detail=f"Below MIN_SIZE_BYTES ({size_bytes} < {MIN_SIZE_BYTES}).",
                size_bytes=size_bytes,
                duration_sec=0.0,
                samplerate=0,
                channels=0,
                interval_seconds=INTERVAL_SECONDS,
                num_samples_used=0,
                threshold=SILENCE_THRESHOLD,
                max_abs_seen=0.0,
            )

        # SoundFile allows seeking and reading small chunks without loading the whole WAV
        with sf.SoundFile(wav_path) as f:
            sr = int(f.samplerate)
            ch = int(f.channels)
            total_frames = int(len(f))
            duration_sec = total_frames / sr if sr > 0 else 0.0

            starts, frames_per_interval = compute_sample_positions(
                total_frames=total_frames,
                sr=sr,
                interval_seconds=INTERVAL_SECONDS,
                num_samples=NUM_SAMPLES_PER_FILE,
            )

            if starts.size == 0:
                return ScanResult(
                    path=str(wav_path),
                    decision="ERROR",
                    detail="Could not compute sample positions (invalid WAV metadata or empty audio).",
                    size_bytes=size_bytes,
                    duration_sec=duration_sec,
                    samplerate=sr,
                    channels=ch,
                    interval_seconds=INTERVAL_SECONDS,
                    num_samples_used=0,
                    threshold=SILENCE_THRESHOLD,
                    max_abs_seen=0.0,
                )

            max_abs_seen = 0.0

            # Sample a handful of chunks across the file
            for start in starts:
                # Jump to the chunk start (frame index)
                f.seek(int(start))

                # Read INTERVAL_SECONDS worth of frames
                data = f.read(frames_per_interval, dtype="float32", always_2d=True)

                # If we got no data, continue (rare edge cases)
                if data.size == 0:
                    continue

                # Peak absolute amplitude in this chunk
                peak = float(np.max(np.abs(data)))
                max_abs_seen = max(max_abs_seen, peak)

                # Early exit: if ANY chunk exceeds threshold, file is NOT silent
                if peak > SILENCE_THRESHOLD:
                    return ScanResult(
                        path=str(wav_path),
                        decision="KEEP",
                        detail=f"Non-silent chunk found (peak={peak:.6g} > threshold).",
                        size_bytes=size_bytes,
                        duration_sec=duration_sec,
                        samplerate=sr,
                        channels=ch,
                        interval_seconds=INTERVAL_SECONDS,
                        num_samples_used=int(starts.size),
                        threshold=SILENCE_THRESHOLD,
                        max_abs_seen=max_abs_seen,
                    )

            # If we never exceeded the threshold, treat as silent
            return ScanResult(
                path=str(wav_path),
                decision="SILENT",
                detail="All sampled chunks were below threshold.",
                size_bytes=size_bytes,
                duration_sec=duration_sec,
                samplerate=sr,
                channels=ch,
                interval_seconds=INTERVAL_SECONDS,
                num_samples_used=int(starts.size),
                threshold=SILENCE_THRESHOLD,
                max_abs_seen=max_abs_seen,
            )

    except Exception as e:
        # Any failure (corrupt header, permissions, codec edge case) gets recorded as ERROR
        return ScanResult(
            path=str(wav_path),
            decision="ERROR",
            detail=f"{type(e).__name__}: {e}",
            size_bytes=0,
            duration_sec=0.0,
            samplerate=0,
            channels=0,
            interval_seconds=INTERVAL_SECONDS,
            num_samples_used=0,
            threshold=SILENCE_THRESHOLD,
            max_abs_seen=0.0,
        )


def write_csv(path: Path, rows: list[ScanResult]) -> None:
    """
    Writes the report CSV. (If Excel has it open, Windows can block overwriting.)
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "path",
        "decision",
        "detail",
        "size_bytes",
        "duration_sec",
        "samplerate",
        "channels",
        "interval_seconds",
        "num_samples_used",
        "threshold",
        "max_abs_seen",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({
                "path": r.path,
                "decision": r.decision,
                "detail": r.detail,
                "size_bytes": r.size_bytes,
                "duration_sec": f"{r.duration_sec:.3f}",
                "samplerate": r.samplerate,
                "channels": r.channels,
                "interval_seconds": r.interval_seconds,
                "num_samples_used": r.num_samples_used,
                "threshold": f"{r.threshold:.6g}",
                "max_abs_seen": f"{r.max_abs_seen:.6g}",
            })


def bytes_to_gb(n: int) -> float:
    """Convert bytes to GB (base-2 GiB style, but labeled GB for convenience)."""
    return n / (1024 ** 3)


def main() -> None:
    # Basic validation
    if MODE not in ("AUDIT", "DELETE"):
        raise ValueError('MODE must be "AUDIT" or "DELETE"')

    if not ROOT_DIRECTORY.exists() or not ROOT_DIRECTORY.is_dir():
        raise FileNotFoundError(f"ROOT_DIRECTORY is not a directory: {ROOT_DIRECTORY}")

    # Pre-enumerate files so tqdm shows a true progress bar
    wav_files = find_wav_files(ROOT_DIRECTORY)

    print(f"\n[{datetime.now().isoformat(timespec='seconds')}] Starting scan")
    print(f"ROOT_DIRECTORY       : {ROOT_DIRECTORY}")
    print(f"MODE                 : {MODE}")
    print(f"INTERVAL_SECONDS     : {INTERVAL_SECONDS}")
    print(f"NUM_SAMPLES_PER_FILE : {NUM_SAMPLES_PER_FILE}")
    print(f"SILENCE_THRESHOLD    : {SILENCE_THRESHOLD}")
    print(f"REPORT_CSV           : {REPORT_CSV}")
    print(f"WAV files found      : {len(wav_files)}\n")

    # Counters for terminal summary
    scanned = 0
    silent_candidates = 0
    deleted_count = 0
    error_count = 0

    # Track bytes for "GB available to be saved"
    # - In AUDIT: sum of candidate silent file sizes
    # - In DELETE: sum of successfully deleted file sizes
    bytes_candidate_savings = 0
    bytes_deleted_savings = 0

    # Rows we write to CSV:
    # - Always include SILENT candidates
    # - Also include ERROR rows (diagnostics)
    report_rows: list[ScanResult] = []

    # tqdm progress bar over all wav files
    for wav in tqdm(wav_files, desc="Scanning WAV files", unit="file"):
        scanned += 1

        res = scan_wav_for_silence(wav)

        if res.decision == "SILENT":
            silent_candidates += 1
            bytes_candidate_savings += res.size_bytes
            report_rows.append(res)

            if MODE == "DELETE":
                # Try to delete the file
                try:
                    os.remove(res.path)
                    deleted_count += 1
                    bytes_deleted_savings += res.size_bytes
                except Exception as e:
                    error_count += 1
                    # Record delete failure as an ERROR row in the CSV
                    report_rows.append(
                        ScanResult(
                            path=res.path,
                            decision="ERROR",
                            detail=f"Delete failed: {type(e).__name__}: {e}",
                            size_bytes=res.size_bytes,
                            duration_sec=res.duration_sec,
                            samplerate=res.samplerate,
                            channels=res.channels,
                            interval_seconds=res.interval_seconds,
                            num_samples_used=res.num_samples_used,
                            threshold=res.threshold,
                            max_abs_seen=res.max_abs_seen,
                        )
                    )

        elif res.decision == "ERROR":
            error_count += 1
            report_rows.append(res)

    # Write CSV report
    write_csv(REPORT_CSV, report_rows)

    # Terminal summary
    audit_gb = bytes_to_gb(bytes_candidate_savings)
    deleted_gb = bytes_to_gb(bytes_deleted_savings)

    print("\nDone.")
    print(f"Scanned WAV files            : {scanned}")
    print(f"Silent candidates            : {silent_candidates}")
    print(f"Errors                       : {error_count}")

    # Print "GB available to be saved" in BOTH modes
    # - AUDIT: what you *could* save if you switched to DELETE
    # - DELETE: what you *actually* saved by deleting
    if MODE == "AUDIT":
        print(f"GB available to be saved     : {audit_gb:.3f} GB")
    else:
        print(f"GB available to be saved     : {deleted_gb:.3f} GB (deleted)")
        # Also helpful to know how much was *flagged* in total
        print(f"GB flagged as silent (total) : {audit_gb:.3f} GB")

    print(f"CSV report                   : {REPORT_CSV}")
    print("")


if __name__ == "__main__":
    main()
