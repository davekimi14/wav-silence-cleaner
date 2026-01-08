# wav-silence-cleaner

[![Contributors](https://img.shields.io/github/contributors/davekimi14/wav-silence-cleaner.svg?style=for-the-badge)](https://github.com/davekimi14/wav-silence-cleaner/graphs/contributors)
[![Forks](https://img.shields.io/github/forks/davekimi14/wav-silence-cleaner.svg?style=for-the-badge)](https://github.com/davekimi14/wav-silence-cleaner/network/members)
[![Stargazers](https://img.shields.io/github/stars/davekimi14/wav-silence-cleaner.svg?style=for-the-badge)](https://github.com/davekimi14/wav-silence-cleaner/stargazers)
[![Issues](https://img.shields.io/github/issues/davekimi14/wav-silence-cleaner.svg?style=for-the-badge)](https://github.com/davekimi14/wav-silence-cleaner/issues)
[![MIT License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](#license)

---

## About The Project

**wav-silence-cleaner** is a fast, storage-safe cleanup tool for large multitrack WAV session dumps.
It scans multi‑GB, multi‑hour audio files using optimized probe windows to detect silent or placeholder tracks without loading entire files into memory.

It is designed for workflows like:
- Live sound multitrack recordings
- Concerts and rehearsals
- Podcast and broadcast session dumps
- Studio sessions with unused inputs

The tool can **report** silent files or **delete** them once verified.

---

## Built With

- Python 3
- [NumPy](https://numpy.org/)
- [SoundFile / libsndfile](https://pysoundfile.readthedocs.io/)
- [tqdm](https://tqdm.github.io/)

---

## Getting Started

### Prerequisites

- Python **3.9+** recommended
- `libsndfile` support  
  (Automatically installed with `soundfile` on Windows/macOS.  
  Linux users may need to install `libsndfile` via their package manager.)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/davekimi14/wav-silence-cleaner.git
cd wav-silence-cleaner
```

2. Install dependencies:


```bash
pip install numpy soundfile tqdm
```

---

## Usage

This repository currently runs as a single script:

- `cleanup.py`

### Modes

The script supports the following modes (set via `MODE` in the config section):

- **REPORT** (recommended first)  
  Scans WAV files and writes a report of files considered silent.

- **DELETE**  
  Deletes files determined to be silent.

> ⚠️ Always run **REPORT** first and review results before using **DELETE**.

### Configuration Options

Edit the configuration block at the top of `cleanup.py`:

- `ROOT_DIRECTORY` – Root folder to scan
- `MODE` – `REPORT`, `DELETE` OR `MOVE`
- `REPORT_FILE` – Output report filename
- `SILENCE_THRESHOLD` – Amplitude threshold considered silence
- `MIN_NON_SILENT_RATIO` – Minimum fraction of non‑silent audio to keep a file
- `CHUNK_SECONDS` – Probe window size (larger = faster, smaller = more accurate)

### Example Workflow

**1. Generate a report (safe):**

```bash
python cleanup.py
```

Review the generated report file (for example `silent_wav_report.txt`).

**2. Delete confirmed silent files:**

Edit the config:

```python
MODE = "DELETE"
```

Then run:

```bash
python cleanup.py
```

---

## Safety Notes

- Always back up or test on a copy of your session data.
- Very quiet room tone or ambience tracks may be flagged as silent.
  Adjust thresholds if needed.
- Consider adding a quarantine or move-to-folder step before deleting.

---

## Roadmap

- [ ] Command-line arguments (`--mode`, `--path`)
- [ ] Multiprocessing support
- [ ] Structured logging (CSV / JSON)
- [ ] Unit tests for silence detection

---


## Acknowledgments

- README layout inspired by https://github.com/othneildrew/Best-README-Template
- `libsndfile` for efficient audio access
- `tqdm` for progress bars
