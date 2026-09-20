Building a local-first video sermon assistant requires balancing complex AI pipelines with end-user hardware constraints. The most reliable approach for a single-click local installation is packaging a lightweight web-based UI wrapped in a desktop framework, connected to a highly optimized Python backend that runs quantized versions of the AI models.

## Core Architecture & Tech Stack

To ensure everything runs locally without complicated setup steps, you must use tools that do not require standalone background services (like Docker or separate Ollama installations).

| Component | Recommended Tool | Rationale |
| --- | --- | --- |
| **Desktop Wrapper** | Tauri (with React/Vue) | Much lighter than Electron. Creates a native desktop window that interacts with your local backend. |
| **Backend Engine** | Python + FastAPI | Natively supports the AI/ML ecosystem and handles local file management efficiently. |
| **Downloader** | `yt-dlp` | Industry standard for YouTube and Facebook Live extraction. Can be imported directly as a Python module. |
| **Video Trimming** | `FFmpeg` | The backend can use `ffmpeg-python` to quickly slice the downloaded MP4 based on timestamps sent from the UI. |
| **Transcription** | `faster-whisper` | A reimplementation of OpenAI Whisper using CTranslate2. It is up to 4x faster than standard Whisper and runs well on CPUs. |
| **Local LLM** | `llama-cpp-python` | Allows you to run quantized models (like Llama-3 8B or Mistral 7B) locally on CPU or GPU without requiring a separate server. |
| **Database** | SQLite | A single-file, zero-configuration local database perfect for storing generated notes and chat histories. |

## Development Phases

### Phase 1: The Media Pipeline

Start by building the core utility functions in Python before touching the UI.

1. Integrate `yt-dlp` to download a video locally and return the file path.
2. Build an API endpoint that takes a video path, start time, and end time, and executes an `FFmpeg` command to extract that specific clip losslessly (using `-c copy`).
3. Set up `faster-whisper` to process the trimmed audio. Ensure it outputs timestamps alongside the text, which is critical for linking notes back to specific moments in the sermon.

### Phase 2: The LLM & Note-Generation Engine

The LLM requires careful prompting to generate structured sermon notes.

1. Download a highly capable quantized model in `.gguf` format (e.g., `Meta-Llama-3-8B-Instruct-Q4_K_M.gguf`). This keeps the model size around 4.5GB, allowing it to run on machines with 8GB+ of RAM.
2. Build an inference pipeline using `llama-cpp-python`.
3. Create system prompts designed for sermons. The LLM should receive the Whisper transcript and output a structured JSON response containing the main theme, key scriptures referenced, bulleted takeaways, and a summary.
4. Implement a chat endpoint that retains the transcript and generated notes in its context window, allowing the user to ask questions like, "What did the pastor mean by X?"

### Phase 3: The User Interface

Build the frontend that users will actually interact with using React.

1. **Import View:** A simple input field for the video URL and a local file upload dropzone.
2. **Trimming Studio:** An HTML5 video player with a custom dual-handle range slider on the progress bar. When the user sets the handles and clicks "Trim," the frontend sends the start/end timestamps to the FastAPI backend.
3. **Workspace:** A split-screen layout. The left side contains the trimmed video player and the timestamped transcript. The right side contains the LLM-generated notes, an editable text area for the user's personal additions, and a chat interface to converse with the LLM about the sermon.

### Phase 4: The "One-Go" Packaging Strategy

Deploying local Python apps with heavy ML dependencies is notoriously difficult. To achieve a single-click install, you must bundle the environment.

* **The Executable:** Use `PyInstaller` to compile the FastAPI backend and its dependencies into a single executable folder.
* **Model Downloading:** Do not bundle the 5GB LLM model or the Whisper model into the installer itself, or the download will be too massive. Instead, write a first-run startup script in your app that automatically downloads the required `.gguf` files and Whisper `.bin` files from HuggingFace to a local `AppData` directory with a progress bar.
* **The Installer:** Use a tool like Inno Setup (for Windows) or create an Apple Disk Image (DMG) (for macOS) that packages the Tauri frontend, the PyInstaller backend, and `FFmpeg` binaries. The installer simply places these files on the user's machine, creates a desktop shortcut, and handles the initial model download on the first launch.

Because local LLMs and Whisper models require significant computational power, you will need to implement hardware detection on startup to configure `faster-whisper` and `llama.cpp` to use GPU acceleration (CUDA/Metal) if available, and gracefully fall back to CPU-only execution for users on standard laptops.