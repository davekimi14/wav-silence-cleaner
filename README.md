# wav-silence-cleaner

[![Contributors](https://img.shields.io/github/contributors/davekimi14/wav-silence-cleaner.svg?style=for-the-badge)](https://github.com/davekimi14/wav-silence-cleaner/graphs/contributors)
[![Forks](https://img.shields.io/github/forks/davekimi14/wav-silence-cleaner.svg?style=for-the-badge)](https://github.com/davekimi14/wav-silence-cleaner/network/members)
[![Stargazers](https://img.shields.io/github/stars/davekimi14/wav-silence-cleaner.svg?style=for-the-badge)](https://github.com/davekimi14/wav-silence-cleaner/stargazers)
[![Issues](https://img.shields.io/github/issues/davekimi14/wav-silence-cleaner.svg?style=for-the-badge)](https://github.com/davekimi14/wav-silence-cleaner/issues)

---

## About The Project

**wav-silence-cleaner** is a fast, storage-safe cleanup tool for large multitrack WAV session dumps.

It is specifically designed to handle **multi-GB, multi-hour WAV files** by sampling short probe windows across each file instead of loading entire recordings into memory. This makes it suitable for very large audio archives and network storage.

Typical use cases include:
- Live sound multitrack recordings
- Concerts and rehearsals
- Podcast and broadcast session dumps
- Studio sessions with unused or disconnected inputs
- Placeholder or accidentally recorded tracks

The tool supports:
- **Audit mode** to safely identify silent files
- **Delete mode** to remove confirmed silent files
- A live **progress bar**
- **CSV reporting**
- A terminal summary showing **GB of storage available to be saved**

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

On Windows and macOS this is installed automatically with `soundfile`.  
Linux users may need to install it manually (e.g. `libsndfile1`).

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

The project currently runs as a **single script**:

- `cleanup.py` (or your chosen filename)

All configuration is done by editing the **hard-coded config block** at the top of the script.

---

## Modes

Set the mode in the configuration section:

```python
MODE = "AUDIT"   # or "DELETE"
```

### AUDIT (recommended first)

- Scans all WAV files
- Identifies files that appear silent
- Writes a CSV report
- **Does NOT delete anything**
- Prints **GB available to be saved** in the terminal

### DELETE

- Deletes files determined to be silent
- Writes a CSV report
- Prints **GB actually freed** in the terminal

> ⚠️ Always run **AUDIT** first and review the CSV before switching to **DELETE**.

---

## Configuration Options

Edit the configuration block at the top of the script:

| Setting | Description |
|------|------------|
| `ROOT_DIRECTORY` | Root folder to scan (recursive) |
| `MODE` | `"AUDIT"` or `"DELETE"` |
| `REPORT_CSV` | Output CSV report filename |
| `INTERVAL_SECONDS` | Length of each sampled chunk (seconds) |
| `NUM_SAMPLES_PER_FILE` | How many chunks to sample per file |
| `SILENCE_THRESHOLD` | Peak amplitude threshold considered silence |
| `MIN_SIZE_BYTES` | Optional size filter to ignore tiny files |

### Recommended Defaults (Large Files)

For ~2 hour, 4–5GB WAV files:

```python
INTERVAL_SECONDS = 7
NUM_SAMPLES_PER_FILE = 16
SILENCE_THRESHOLD = 1e-4
```

This samples roughly every **7–8 minutes** across the file while remaining fast.

---

## Example Workflow

### 1. Run an audit (safe)

```bash
python cleanup.py
```

Terminal output will include:
- Files scanned
- Silent candidates
- Errors
- **GB available to be saved**

Review the generated CSV report before proceeding.

---

### 2. Delete confirmed silent files

Edit the config:

```python
MODE = "DELETE"
```

Run again:

```bash
python cleanup.py
```

Terminal output will now show:
- Files deleted
- Errors
- **GB actually freed**

---

## How Silence Detection Works

- Each WAV file is sampled at multiple evenly spaced positions
- Each sample reads a **7-second chunk**
- The **peak absolute amplitude** is measured
- If **any** sampled chunk exceeds the threshold → file is kept
- If **all** sampled chunks are below the threshold → file is considered silent

This approach balances:
- Speed
- Accuracy
- Memory safety for massive files

---

## Safety Notes

- Always back up or test on a copy of your data first
- Very quiet ambience or room-tone tracks may be flagged as silent
- Adjust `SILENCE_THRESHOLD` if needed
- Consider extending the script to move files to a quarantine folder before deleting

---

## Roadmap

- [ ] Command-line arguments (`--mode`, `--path`)
- [ ] Move-to-folder (quarantine) mode
- [ ] RMS-based silence detection
- [ ] Multiprocessing support
- [ ] JSON + CSV reporting
- [ ] Resume-safe scanning
- [ ] Unit tests

---


## Acknowledgments

- README structure inspired by https://github.com/othneildrew/Best-README-Template
- `libsndfile` for efficient, seek-based audio access
- `tqdm` for clean, informative progress bars
