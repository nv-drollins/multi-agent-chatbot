# Local Multi-Agent Chatbot

Local multi-agent AI demo for NVIDIA RTX PRO and DGX Spark class systems.

The demo runs inference locally through Ollama plus an optional local NVIDIA NIM
for Cosmos-Reason2. It uses one GPU by default (`CUDA_VISIBLE_DEVICES=0`) even
on multi-GPU systems.

## What It Shows

- A supervisor routing work to specialist local agents.
- Uploaded image identification with Cosmos-Reason2-2B when the local NIM is
  running, with the local Ollama VLM as a fallback.
- Short uploaded video summarization using local frame sampling plus
  Cosmos-Reason2-2B visual reasoning when the local NIM is running, or the local
  Ollama VLM as a fallback.
- Uploaded PDF, text, or Markdown document RAG using local embeddings.
- A coding agent that generates a self-contained briefing page from uploaded
  image, video, and document context, then copies it to the desktop for
  double-click launch.
- Local PDF-backed retrieval from NVIDIA RTX PRO 6000 datasheets.
- Live GPU telemetry showing the demo GPU only.
- A visible MCP-style local tool bus.

## Default Models

- Supervisor LLM: `qwen3:14b`
- Coding LLM: `qwen2.5-coder:7b`
- Briefing/Coding LLM: `qwen2.5-coder:7b`
- Vision VLM: `nvidia/cosmos-reason2-2b` through local NIM on port `8000`
- Vision fallback: `llama3.2-vision:11b`
- Embeddings: `nomic-embed-text`

Override these with `SUPERVISOR_MODEL`, `CODING_MODEL`, `VISION_PROVIDER`, `COSMOS_NIM_BASE`, `COSMOS_MODEL`, `VISION_MODEL`, and `EMBED_MODEL`.

## Prerequisites

Validated on Ubuntu 24.04 with one NVIDIA RTX PRO 6000 Blackwell Max-Q GPU.
The demo should also be portable to other NVIDIA workstation-class GPUs with
enough memory for the selected local models.

System software:

- NVIDIA GPU driver with `nvidia-smi` working. The clean deployment test used
  driver `595.58.03`.
- Docker with the NVIDIA Container Toolkit configured.
- Docker runnable by the demo user without `sudo`.
- Ollama installed and listening on the standard local endpoint
  `127.0.0.1:11434`.
- Git access to this repository. If the repository is private, authenticate
  GitHub on the target machine before cloning or deploy from a local archive.
- Python 3 with venv support, ffmpeg, fontconfig, and DejaVu fonts.

Ubuntu package baseline:

```bash
sudo apt update
sudo apt install -y git curl ca-certificates python3 python3-venv python3-pip ffmpeg fontconfig fonts-dejavu-core jq
```

Required API keys for first-time model setup:

- `NGC_API_KEY` for the Cosmos-Reason2 NIM container and model assets.
- `NVIDIA_API_KEY`, `HF_TOKEN`, and `OLLAMA_API_KEY` are useful for related
  model access workflows and future variants.

The NIM startup script can read standard export lines from `~/.bashrc`, for
example:

```bash
export NGC_API_KEY="..."
export NVIDIA_API_KEY="..."
export HF_TOKEN="..."
export OLLAMA_API_KEY="..."
```

First-time downloads include Ollama LLMs, the optional Ollama backup VLM, the
Cosmos-Reason2 NIM image/model cache, and local NVIDIA PDF docs. Plan for at
least 100 GB of free disk; 200 GB is more comfortable for repeated testing.

Ports:

- `7860`: demo web UI, should be reachable from the presenter browser.
- `11434`: Ollama, can remain local-only.
- `8000`: Cosmos-Reason2 NIM OpenAI-compatible endpoint, can remain local-only.

## Quick Start

```bash
git clone https://github.com/<owner>/multi-agent-chatbot.git
cd multi-agent-chatbot
bash scripts/start_cosmos_nim.sh
./scripts/download_docs.sh
./scripts/prepare_models.sh
./start.sh
```

To keep it running after closing the terminal:

```bash
./scripts/run_background.sh
```

To stop the demo web app, unload active Ollama model sessions, and stop the
Cosmos-Reason2 NIM container:

```bash
./stop.sh
```

Open:

```text
http://<host-ip>:7860
```

## Notes

- A clean Ubuntu deployment test on May 1, 2026 used Ubuntu 24.04.4 LTS,
  NVIDIA driver 595.58.03, Docker 29.4.2, Ollama 0.22.1, and one RTX PRO 6000
  Blackwell Max-Q.
- The demo uses the standard local Ollama endpoint `127.0.0.1:11434` by
  default. Override it with `OLLAMA_HOST` if you need a different port.
- If `start.sh` needs to launch Ollama itself, it sets `CUDA_VISIBLE_DEVICES=0`
  by default so model inference uses one GPU.
- If the Cosmos-Reason2 NIM is running at `COSMOS_NIM_BASE`, image and video
  agents use it first. If the NIM is not available, the demo still runs with the
  existing local Ollama VLM.
- Cosmos-Reason2-8B works on this RTX PRO 6000 and the NIM selected an NVFP4
  profile, but it can reserve most of the GPU for long-context KV cache. The
  default demo path uses Cosmos-Reason2-2B to leave room for document RAG and
  briefing generation on the same GPU.
- Generated briefing pages are written to `data/generated/` and copied to
  `~/Desktop/`.
- Three lightweight matching case-file sets can be generated with
  `./scripts/create_case_files.sh`. Each set includes one PNG image, one short
  MP4 video under 30 seconds, and one TXT document for a coherent briefing
  story under `content_sets/demo-case-files/`.
- The app accepts uploaded images; it does not require image URLs.
- Uploaded documents are indexed locally for the current demo session and are
  cleared from active context by Reset demo.
- Uploaded videos are sampled locally with `ffmpeg`/`ffprobe`; clips should be
  under five minutes.
- At the show, models and docs are already local. No model downloads are needed.
## Briefing Page Prompt Shape

The Coding Agent uses the active local context from Image ID, Video ID, Document
RAG, GPU telemetry, and the agent timeline to create a portable HTML briefing.
The generated desktop HTML embeds available image evidence, sampled video
frames, document excerpts, upload-store statistics, GPU snapshot, and concise
next actions. The Images, Videos, and Documents totals link to local inventory
pages with thumbnails, video previews, and document previews. The briefing page
uses no external libraries, images, fonts, or cloud services.

## Matching Content Sets

For the best conference flow, use one case file at a time: one image, one short
video, and one document that describe the same situation. Suggested sets are in
`content_sets/README.md`: autonomous vehicle shuttle, manufacturing quality
inspection, and media and entertainment virtual production.
