# transcription

Audio or video → TXT / SRT / VTT with OpenAI's Whisper models running locally on a GPU, plus an optional punctuation/casing pass that **never changes a word**.

## Pipeline

1. **ASR**
   - `transcribe.py`: Hugging Face transformers, any ffmpeg-readable file; writes txt/srt/vtt with timestamps.
   - `transcribe_faster_whisper.py`: CTranslate2 build of `whisper-large-v3-turbo`, much faster on long files.
2. **Punctuation pass** (`punctuate.py`)
   - On long recordings every Whisper variant tested drifts into all-lowercase text without punctuation, and prompting causes repetition. This pass sends ~120-word chunks to a local LLM (any OpenAI-compatible endpoint, run with thinking disabled).
   - A chunk is accepted only if its words are identical to the input. Otherwise the punctuation and casing are transferred onto the original words by sequence alignment.
   - Result: the word sequence is provably unchanged (WER is identical before and after).
3. Read-through by a person before delivery. A few stray capitals can remain.

## Measured (public test data only)

| Set | Audio | Error | Speed (one 16 GB consumer GPU) |
|---|---|---|---|
| LibriSpeech clean, EN, 30 clips | 3.8 min | WER 3.6 % (mostly "mister" vs "Mr" normalisation) | ~11× realtime (large-v3, unbatched) |
| FLEURS dev, Japanese, 30 clips | 6.7 min | CER 4.1 % | ~11× |
| FLEURS dev, Chinese, 30 clips | 6.2 min | CER 10.3 % (simplified/traditional mixing counts as errors) | ~10× |
| LibriVox audiobook chapter, EN, vs Project Gutenberg text | 27.8 min | WER 2.0 % | 20 s (~80×, turbo + faster-whisper) |

`eval.py` and `score_long.py` reproduce these numbers. The datasets are public (LibriSpeech and FLEURS: CC-BY 4.0; LibriVox and Project Gutenberg: public domain). They are downloaded by you, not shipped here.

## Not covered

- Speaker labels (diarization).
- Translation: Whisper's built-in translate was tested and judged too rough to offer.
- Burned-in subtitles.
- Re-timing SRT segments after punctuation.
- Long-form Japanese/Chinese has not been measured.
