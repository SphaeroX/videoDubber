# Video Dubber

Async Python pipeline that replaces the audio track of a recorded video with a clean GPT-4o voiceover generated from the original speech.

> Entirely Vibe coded with **Codex**, ensuring a fully AI-assisted and consistent development workflow.

## Features
- Extracts the source audio from any supported video file.
- Transcribes speech with GPT-4o Transcribe and preserves timing information.
- Streams GPT-4o Mini TTS to synthesize a replacement narration for each segment.
- Reassembles the video with the synthesized audio, producing a fully dubbed result.

## Requirements
- Python 3.11 or newer
- `ffmpeg` available on `PATH`
- Valid OpenAI API credentials

## Installation
```bash
python -m venv .venv
.venv\Scripts\activate  # PowerShell
pip install --upgrade pip
pip install -e .
```

## Configuration
Provide the required environment variables (or create a `.env` file in the project root):
```bash
setx OPENAI_API_KEY "sk-..."
setx TRANSLATION_MODEL "gpt-4o"
setx TRANSLATION_INSTRUCTION "Fix grammar but keep the speaker's tone."
setx TTS_VOICE "alloy"
setx MAX_CONCURRENCY "10"
setx TEMP_DIR "artifacts"
```
`Settings.from_env()` supplies sane defaults; override them as needed.

When using a `.env` file on Windows, keep the classic `VAR=value` format so `python-dotenv` can load the values correctly:
```env
OPENAI_API_KEY=sk-...
TRANSLATION_MODEL=gpt-4o
TRANSLATION_INSTRUCTION=Fix grammar but keep the speaker's tone.
TTS_VOICE=alloy
MAX_CONCURRENCY=10
TEMP_DIR=artifacts
```

`translation_instruction` prompts GPT-4o to polish the transcript and now doubles as guidance for synthesizing speech. The pipeline automatically asks GPT-4o to summarize the desired tone and pacing for TTS; set `TTS_INSTRUCTION` only if you need to hard-override the generated directive.

## Usage
1. Place the video to be processed (for example `demo.mp4`) inside the project directory.
2. Run the pipeline:
   ```bash
   .venv\Scripts\activate
   python scripts/run_pipeline.py -i demo.mp4
   ```
3. Optionally specify a target language so the narration is translated before dubbing:
   ```bash
   python scripts/run_pipeline.py -i demo.mp4 -l en
   ```
4. Provide GPT-4o with extra rewriting guidance (for example to simplify the transcript) using:
   ```bash
   python scripts/run_pipeline.py -i demo.mp4 --translation-instruction "Rewrite in child-friendly German."
   ```
   Combine `--language` and `--translation-instruction` to translate and tweak the style in one pass.
5. The script saves the dubbed video next to the source file (for example `demo.dubbed.mp4`).

## Demo
The repository ships with a sample before/after pair you can open locally:


## Extending
- Modify `src/video_dubber/pipeline.py` to plug in additional processing steps.
- OpenAI integration lives under `src/video_dubber/services/`.
- Media extraction and assembly helpers reside in `src/video_dubber/media/`.
- Manage defaults through `Settings` in `src/video_dubber/config.py`.

## Tests
Place future tests under `tests/` and execute them with:
```bash
pytest
```
