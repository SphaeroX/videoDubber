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
setx TTS_INSTRUCTION "Speak clearly, warmly."
setx TRANSLATION_MODEL "gpt-4o"
setx TTS_VOICE "alloy"
setx MAX_CONCURRENCY "10"
setx TEMP_DIR "artifacts"
```
`Settings.from_env()` supplies sane defaults; override them as needed.

When using a `.env` file on Windows, keep the classic `VAR=value` format so `python-dotenv` can load the values correctly:
```env
OPENAI_API_KEY=sk-...
TTS_INSTRUCTION=Speak clearly, warmly and without background noise.
TRANSLATION_MODEL=gpt-4o
TTS_VOICE=alloy
MAX_CONCURRENCY=10
TEMP_DIR=artifacts
```

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
4. The script saves the dubbed video next to the source file (for example `demo.dubbed.mp4`).

## Demo
The repository ships with a sample before/after pair you can open locally:

<figure>
  <figcaption>Before: original narration (`demo.mp4`).</figcaption>
  <video controls src="demo.mp4">
    Sorry, your browser cannot play this embedded video. Download <a href="demo.mp4">demo.mp4</a>.
  </video>
</figure>

<figure>
  <figcaption>After: dubbed output lang "it" (`demo.dubbed.mp4`).</figcaption>
  <video controls src="demo.dubbed.mp4">
    Sorry, your browser cannot play this embedded video. Download <a href="demo.dubbed.mp4">demo.dubbed.mp4</a>.
  </video>
</figure>

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
