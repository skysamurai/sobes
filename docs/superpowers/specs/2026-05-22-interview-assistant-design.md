# Interview Assistant — Design Spec

**Date:** 2026-05-22
**Epic:** Assistent dlya sobesov i sozvonov cherez messendzhery

## Overview

Polniy assistent dlya sobesov i rabochih sozvonov: zhivoy suflyor vo vremya zvonka + protokol posle + analitika. Perviy PoC — Skype, zatem rasshirenie na Zoom, Google Meet, Telegram, WhatsApp, Discord.

## Roles

- **Pervaya faza**: kandidat (assistent pomogaet otvechat')
- **Vtoraya faza**: universal'niy (kandidat + intervyuer)

## Tech Stack

- **Yazyk**: Python 3.12+
- **IPC**: ZeroMQ (otdel'nye protsessy)
- **ASR**: Vosk (oflline) → zatem smenniy mekhanizm (Whisper, Yandex SpeechKit)
- **LLM**: gibrid — lokal'niy poisk po FAQ/skriptam → API (OpenAI / Claude / YandexGPT)
- **Vektornaya BD**: ChromaDB (lokal'no)
- **Metadata BD**: SQLite
- **UI**: overlay (Win32 API / Qt) + otdel'noe okno
- **Audizahvat**: sistemniy loopback cherez virtual'niy audio-kabel' (WASAPI / PyAudio)

## Architecture: Modular IPC

Kazhdiy modul' — otdel'niy protsess. Obschenie cherez ZeroMQ cherez `session_manager`.

```
audio_capturer ──→ asr_engine ──→ prompt_engine ──→ overlay_ui
        │               │               │               │
        └───────────────┴─────── session_manager ───────┘
                                (ZeroMQ broker)
```

### Modules

| Module | Role | Key Dependencies |
|--------|------|-----------------|
| `session_manager` | Orkestratsiya, broker soobscheniy, zhiznenniy tsikl | ZeroMQ |
| `preparation_service` | Sbor konteksta do zvonka: anketa, parsing vakansii, indeksatsiya | httpx, BeautifulSoup, embedding model |
| `audio_capturer` | Zahvat sistemnogo zvuka cherez loopback | PyAudio, WASAPI |
| `asr_engine` | Rechevoe raspoznavanie (Vosk → smenniy) | Vosk, Whisper (future) |
| `prompt_engine` | Poisk po FAQ → LLM API fallback, generatsiya podskazok | ChromaDB, httpx (API) |
| `overlay_ui` | Otobrazhenie podskazok: kompaktniy overlay + razvernutoe okno | Qt (PySide6) ili Win32 |
| `post_analyzer` | Formirovanie otcheta, statistika, istoriya | SQLite |
| `storage` | SQLite + ChromaDB, abstraktsiya nad obeimi | sqlite3, chromadb |

### Message Types (ZeroMQ)

| Message | Direction | Content |
|---------|-----------|---------|
| `audio.chunk` | capturer → asr | PCM 16kHz mono, ~500ms chunks |
| `asr.partial` | asr → ui | promezhutochniy tekst |
| `asr.final` | asr → prompt_engine | final'niy otrezok teksta |
| `prompt.hint` | prompt → ui | podskazka s istochnikom i confidence |
| `ui.command` | ui → session | komandi pol'zovatelya (skrit', rezhim, bystrie skripti) |
| `session.event` | session → all | start, stop, pause |

## Three Phases

### Phase 1: Preparation (offline, before call)

**Flow:**
1. **Anketa**: pol'zovatel' zapolnyaet (kompaniya, dolzhnost', tip sobesa, ssilka na vakansiyu, svoy stek/uroven')
2. **Auto-sbor**: sistema parsit vakansiyu, ischet informatsiyu o kompanii, tipovie voprosi dlya roli
3. **Skripti**: pol'zovatel' dobavlyaet zagotovlennie otveti, voprosi k kompanii, klyuchevie tsifri, samoprezentatsiyu
4. **Indeksatsiya**: vse sobrannoe vektorizuetsya lokal'noy embedding-modelyu, sohranyaetsya v ChromaDB dlya poiska za millisekundi
5. **Gotovnost'**: dashboard s obzorom (chto pokrito, probeli, rekomendatsii)

**Output**: "Gotovo. ▶ Start" — perehod k faze 2.

### Phase 2: Live (during call)

**Pipeline:**
- Audio → virtual cable → capturer → ASR → prompt_engine → overlay
- Zaderzhka tselevaya: < 2 sekundi ot voprosa do podskazki

**Overlay UI — dva rezhima:**
- **Rezhim A (Compact)**: poluprozrachniy overlay poverh vseh okon, pokazivaet tekuschiy vopros + podskazku
- **Rezhim B (Full Window)**: otdel'noe okno s transkriptom, podskazkoy, kontekstom kompanii, bistrimi skriptami
- **Pereklyuchenie**: Alt+Enter mezhdu rezhimami, Alt+Q skrit'/pokazat'
- **Bistrie skripti**: Ctrl+1..9 — mgnovenniy vivod zagotovlennogo otveta

**Prompt Engine logic:**
1. Poluchit' `asr.final` (tekst voprosa)
2. Poisk po lokal'noy baze skriptov/FAQ cherez ChromaDB (embedding similarity)
3. Esli confidence > poroga (0.75) → vernut' lokal'niy rezul'tat
4. Inache → otpravit' vopros + kontekst v LLM API, poluchit' podskazku
5. Otpravit' `prompt.hint` v UI

### Phase 3: Post-Analysis (after call)

**Otchet soderzhit:**
- Statistika: % tvoya rech / sobesednik, kolichestvo voprosov, ispol'zovannie skripti
- Hronologiya tem: chto obsuzhdali i kogda, kakie skripti ispol'zovani
- Zoni riska: voprosi bez podgotovlennih skriptov, dlitel'nye pauzi
- EkSHn-pointi: chto sdelat' (follow-up, podgotovit' skripti)
- Polniy transkript s vozhmozhnost'yu eksporta (JSON, Markdown, PDF)

**Dashboard istorii:**
- Vse sobesi po kompaniyam
- Dinamika progressa
- Kakie skripti rabotayut luchshe

## Storage

- **SQLite**: metadannie sessiy, skripti, kompanii, kontakti, nastroiki
- **ChromaDB**: vektorniy poisk po skriptam i transkriptam (lokal'no, embedding model)

## Key Design Decisions

1. **ZeroMQ vmesto asyncio-ocheredey**: izolyatsiya protsessov (krah ASR ne ronyaet UI), legko dobavlyat'/ubirat' moduli, v buduschem mozhno perepisat' modul' na drugoy yazik
2. **Vosk na start**: legkovesniy, oflline, bistro rabotaet na CPU. V dal'neyshem — smenniy backend (Whisper dlya kachestva, Yandex SpeechKit dlya skorosti)
3. **Lokal'niy FAQ → API**: bol'shinstvo podskazok iz zagotovlennih skriptov (bistro, oflline), LLM API kak fallback dlya neozhidannih voprosov
4. **Overlay na Qt (PySide6)**: krossplatformenno (grozi Windows seychas, no budet Mac/Linux), poluprozrachnost' i ontop iz korobki

## Scope: PoC (Monday)

Chto dolzhno rabotat' k ponedel'niku:
1. `session_manager` — broker na ZeroMQ
2. `preparation_service` — anketa + indeksatsiya (bez auto-sbora)
3. `audio_capturer` — zahvat sistemnogo zvuka
4. `asr_engine` — Vosk, bazoviy
5. `prompt_engine` — lokal'niy poisk po skriptam (bez API fallback)
6. `overlay_ui` — Rezhim A (kompaktniy overlay)
7. `post_analyzer` — bazoviy protokol
8. `storage` — SQLite + ChromaDB

Chto ostavlyaem na potom:
- Auto-sbor informatsii o kompanii (parsing)
- LLM API fallback
- Rezhim B (polnoe okno)
- Universal'naya rol' (intervyuer)
- Podderzhka drugih platform krome Skype
- Dashboard istorii

## Future: Phase 0 — Training (obuchenie na primerah)

**Istochniki:**
- Video (YouTube / fayli) → izvlechenie audio (yt-dlp) → transkribatsiya (Whisper)
- Audiozapisi (MP3/WAV/OGG) → transkribatsiya + diarization
- Ssilki / tekst (stat'i, Glassdoor, gajdi po sobesam) → scraping → razmetka

**Pipeline:** Zagruzka → izvlechenie audio → transkribatsiya → razmetka (voprosi/otveti/temi) → indeksatsiya v ChromaDB

**Chemu uchitsya sistema:**
- Patterni voprosov (kakie chasche, posledovatel'nost', formulirovki)
- Uspeshnie otveti (struktura, klyuchevie slova, primeri)
- Antipatterni (slabie otveti, slova-paraziti, chego izbegat')
- Stil' konkretnih kompaniy (esli est' zapisi ih sobesov)

**Novie moduli:**
- `training_service` — orkestratsiya obucheniya
- `content_extractor` — izvlechenie kontenta iz istochnikov
- `interview_analyzer` — razmetka interv'yu, izvlechenie patternov
