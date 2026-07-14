# sobes — Real-time AI Interview Assistant

Desktop AI assistant for real-time interview coaching: captures audio, transcribes speech offline, matches questions to a script database, and displays AI-generated hints in a transparent overlay.

## Key AI/ML Features

- **Offline ASR:** Russian speech recognition using Vosk (vosk-model-ru-0.42), no cloud dependency
- **Semantic search:** sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2) → ChromaDB vector storage for script matching
- **Real-time AI:** DeepSeek API for live answer generation, rate-limited (5s), deduplication
- **Dual-backend analyzer:** TemplateBackend (rule-based) + DeepSeekBackend (LLM) for resume + vacancy analysis
- **3 phases:** Preparation (analysis) → Live (transcription + hints) → Post (analytics report)

## Stack

| Layer | Technology |
|-------|-----------|
| GUI | PySide6 (Qt 6, Catppuccin Mocha theme) |
| ASR | Vosk (offline Russian model) |
| Audio | PyAudio (mic + system audio capture) |
| Vector DB | ChromaDB |
| Embeddings | sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2) |
| AI | DeepSeek API |
| IPC | ZeroMQ (PUB/SUB messaging) |
| Storage | SQLite |
| Packaging | PyInstaller (Windows .exe) |

## Architecture

```
Microphone ──→ Audio Capture ──→ Vosk ASR ──→ Script Matcher ──→ DeepSeek ──→ Overlay
                  │                   │            │                  │
              ZeroMQ PUB          ZeroMQ SUB   ChromaDB          Rate Limiter
```

## Quick Start

```bash
pip install -r requirements.txt
python sobes_app.py
```

## Project Status

Working PoC: offline speech recognition, live hints, post-session analytics. Ready for PyInstaller packaging.
