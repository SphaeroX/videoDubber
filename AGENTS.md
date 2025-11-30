# Video Dubber

This tool is designed to re-voice recorded videos. The original audio track is removed and replaced with an AI-generated voice without background noise. The OpenAI API is used for transcription, translation, and speech synthesis.

> [!IMPORTANT]
> Before running any scripts or tests, you must always activate the virtual environment first:
> `.venv\Scripts\activate`

## How It Works
1. The video file (e.g., `demo.mp4`) is loaded and the audio track is extracted.  
2. GPT-4o Transcribe creates a transcript.  
3. Segments are time-aligned and re-voiced using GPT-4o Mini TTS.  
4. The new audio replaces the original, resulting in a fully re-dubbed video.  

The system runs asynchronously with up to ten concurrent requests to maximize processing speed.

A special feature of GPT-4o Mini TTS: in addition to the voice preset, it accepts an *instruction* parameter that controls tone, style, or language.

When new mechanisms are added or the project is extended, always update the `AGENTS.md` file. It serves as a short-term memory so other AI systems can understand how the system is structured.

## Branding Note (2025-10-13)
- Project name and package were changed from *Video Transcriber* to *Video Dubber*, including the main Python class `VideoDubbingPipeline`.

## Documentation Update (2025-10-13)
- README now includes HTML5 `<video>` tags for `demo.mp4` and `demo.dubbed.mp4`, allowing GitHub to display playable demos.  
- Configuration section describes `.env` files using Windows-compatible `VAR=value` syntax alongside `setx`.

## Project Structure (2025-10-13)
- Python source uses the `src` layout with package `video_dubber`.  
- Core modules: `pipeline.py` orchestrates the workflow, `config.py` defines runtime settings, `models.py` holds dataclasses.  
- The `services/` layer wraps OpenAI SDK access for transcription and TTS.  
- `media/` contains audio extraction and video assembly helpers; shared functions live in `utils/`.  
- Entry script `scripts/run_pipeline.py` wires everything together and runs the async pipeline.  
- Default configuration uses `gpt-4o-transcribe`, `gpt-4o-mini-tts`, and a maximum concurrency of 10.

## Implementation Notes (2025-10-13)
- `VideoDubbingPipeline` runs end-to-end: audio extraction -> transcription -> streaming TTS rendering -> video assembly with synthesized tracks.  
- `AudioWorkspace` stores intermediate data in `TEMP_DIR/<video_stem>/`, extracts source audio via MoviePy, and prepares segment exports when transcript JSONs are available.  
- `TextToSpeechService` streams GPT-4o Mini TTS output per transcript segment and writes PCM WAV files; tasks are throttled using `bounded_gather` to honor `MAX_CONCURRENCY`.  
- `VideoEditor` removes audio losslessly with ffmpeg, mixes rendered clips via Pydub, and remuxes a normalized 44.1 kHz stereo track with ffmpeg. MoviePy is no longer used for the final mux step.  
- MoviePy 2.x deprecated the `moviepy.editor` convenience module; imports now use `from moviepy import VideoFileClip, AudioFileClip`.  
- Python 3.13 removed the stdlib `audioop`, so the project depends on `audioop-lts` to keep Pydub waveform utilities functional.  
- GPT-4o Transcribe only supports `response_format='json'`; when timestamps are missing, sentence-level segments are approximated by splitting the transcript and distributing source audio duration proportionally.  
- `Settings.translation_instruction` (optional) feeds an extra rewrite prompt into the GPT-4o translation pass so text can be polished or restyled even when the target language stays the same. The translation call now also returns a summarized TTS directive that is forwarded to the Mini TTS service, so manual `TTS_INSTRUCTION` overrides are only needed for hard overrides.
- When no `TTS_INSTRUCTION` override is supplied, the translation service still calls GPT-4o to derive a speech directive while leaving the transcript text unchanged, ensuring TTS guidance is always informed by the source content.
- All prompts sent to OpenAI services are snapshotted under `TEMP_DIR/<video>/prompts/<category>/` via `utils.save_prompt`, covering transcription setup, translation requests, and each TTS segment for auditability.

## CLI Notes (2025-10-13)
- `scripts/run_pipeline.py` requires `-i/--input` to specify the source video and outputs the dubbed version beside it using `<stem>.dubbed<suffix>`.  
- Passing `-l/--language` sets `Settings.target_language`; when provided, the pipeline translates transcript segments with the `gpt-4o` chat model before TTS synthesis so the generated speech uses the requested language automatically.  
- `--translation-instruction` overrides `Settings.translation_instruction`, allowing per-run guidance such as 'simplify wording' or 'make it child-friendly'; the same instruction can also be configured via the `TRANSLATION_INSTRUCTION` environment variable.
