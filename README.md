# Local Multi-Agent Chatbot

Local autonomous AI demo for NVIDIA RTX PRO 6000 and DGX Spark class systems.

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

## Quick Start

```bash
cd ~/autonomous-demo-ops-agent
bash scripts/start_cosmos_nim.sh
./scripts/download_docs.sh
./scripts/prepare_models.sh
./start.sh
```

To keep it running after closing the terminal:

```bash
./scripts/run_background.sh
```

Open:

```text
http://<host-ip>:7860
```

For the current workstation:

```text
http://192.168.1.141:7860
```

## Notes

- `start.sh` starts a demo-scoped Ollama server on `127.0.0.1:11445` with
  `CUDA_VISIBLE_DEVICES=0`, leaving the system Ollama service on port `11434`
  untouched.
- If the Cosmos-Reason2 NIM is running at `COSMOS_NIM_BASE`, image and video
  agents use it first. If the NIM is not available, the demo still runs with the
  existing local Ollama VLM.
- Cosmos-Reason2-8B works on this RTX PRO 6000 and the NIM selected an NVFP4
  profile, but it can reserve most of the GPU for long-context KV cache. The
  default demo path uses Cosmos-Reason2-2B to leave room for document RAG and
  briefing generation on the same GPU.
- The bundled sample repo lives in `demo-workspace/shopflow` and powers the
  coding-agent path.
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
- Reports are written to `reports/`.

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
