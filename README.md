# Local Multi-Agent Chatbot

Local multi-agent AI demo for NVIDIA RTX PRO and DGX Spark class systems.

The demo runs inference locally through Ollama plus an optional local NVIDIA NIM
for Cosmos-Reason2. It uses one GPU by default (`CUDA_VISIBLE_DEVICES=0`) even
on multi-GPU systems.

## Sudo Prompts

First-time setup may need sudo for host packages, Docker/NVIDIA toolkit configuration, or setup preflight checks. Passwordless sudo is not required, but install commands must run from an interactive terminal so sudo can prompt. When installing over SSH, use:

```bash
ssh -t nvidia@<spark-ip>
```

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
- Ollama installed and reachable on port `11434`.
- Git access to this repository. If the repository is private, authenticate
  GitHub on the target machine before cloning or deploy from a local archive.
- Python 3 with venv support, ffmpeg, fontconfig, and DejaVu fonts.

Ubuntu package baseline:

```bash
sudo apt update
sudo apt install -y git curl ca-certificates python3 python3-venv python3-pip ffmpeg fontconfig fonts-dejavu-core jq
```

### Enable Docker access without sudo

DGX Spark systems may not add the current user to the `docker` group by
default. If you skip this step, run Docker commands with `sudo`.

Open a new terminal and test Docker access:

```bash
docker ps
```

If you see a permission denied error while connecting to the Docker daemon
socket, add your user to the `docker` group:

```bash
sudo usermod -aG docker "$USER"
newgrp docker
```

`newgrp docker` updates group membership for the current shell. You can also
log out and back in, then rerun `docker ps`.

### Configure Docker GPU runtime

DGX Spark systems may include the NVIDIA Container Toolkit out of the box, but
Docker still needs the NVIDIA runtime configured:

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Optional verification:

```bash
sudo docker run --rm --runtime=nvidia --gpus all ubuntu nvidia-smi
```

### Install and expose Ollama

Install Ollama on the host. **Important for DGX Spark / GB10: pin Ollama to
`0.22.1`; newer `0.23.x` builds have been observed to fall back to CPU-only
execution on GB10.**

```bash
OLLAMA_VERSION=0.22.1
OLLAMA_ARCH="$(case "$(uname -m)" in aarch64|arm64) echo arm64 ;; x86_64|amd64) echo amd64 ;; *) uname -m ;; esac)"
curl -fL --show-error -o "/tmp/ollama-linux-${OLLAMA_ARCH}.tar.zst" \
  "https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-${OLLAMA_ARCH}.tar.zst"
sudo useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama 2>/dev/null || true
sudo usermod -a -G video,render ollama 2>/dev/null || true
sudo tar --zstd -xf "/tmp/ollama-linux-${OLLAMA_ARCH}.tar.zst" -C /usr/local
sudo chmod -R a+rX /usr/local/lib/ollama
sudo tee /etc/systemd/system/ollama.service >/dev/null <<'EOF'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=default.target
EOF
```

Configure Ollama to listen on all interfaces. The multi-agent chatbot runs on
the host and can use `127.0.0.1:11434`, but this setting also makes the same
Ollama service reachable by local containers, sandboxes, and related demos:

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
printf '[Service]\nEnvironment="OLLAMA_HOST=0.0.0.0"\n' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

Verify it is running:

```bash
curl http://0.0.0.0:11434
```

Expected response:

```text
Ollama is running
```

If it is not running, start it with:

```bash
sudo systemctl start ollama
```

Always start Ollama via systemd, for example with
`sudo systemctl restart ollama`. Do not use `ollama serve &` for this setup,
because a manually started process does not pick up the systemd
`OLLAMA_HOST=0.0.0.0` override.

Only expose port `11434` on networks you trust. If you use a host firewall,
keep the port closed to untrusted machines.

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
git clone https://github.com/nv-drollins/multi-agent-chatbot.git
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

After the first install, use the restart helper during an event. It stops any
leftover demo processes, starts the Cosmos-Reason2 NIM from the local Docker/NIM
cache, and starts the web app in the background:

```bash
# RTX PRO 6000 profile, conservative 2B vision NIM
./restart.sh rtx

# DGX Spark / GB10 profile, higher-quality 8B vision NIM
./restart.sh gb10
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
- `scripts/start_cosmos_nim.sh` waits for the NIM to become ready before it
  returns. It checks `http://127.0.0.1:8000/v1/models` and the container log
  line `Uvicorn running on http://0.0.0.0:8000`, with a default 20-minute
  timeout. Override with `COSMOS_NIM_READY_TIMEOUT_SECONDS` if needed.
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

## Event Restart Loop

Use this loop after the machine has already been prepared with
`scripts/download_docs.sh`, `scripts/prepare_models.sh`, and the first NIM start.

Start or restart on RTX PRO:

```bash
cd multi-agent-chatbot
./restart.sh rtx
```

Start or restart on DGX Spark / GB10:

```bash
cd multi-agent-chatbot
./restart.sh gb10
```

Stop between demos or at the end of the day:

```bash
./stop.sh
```

Useful logs:

- Web app and startup log: `.run/server.log`
- Demo-started Ollama log, if `start.sh` had to launch Ollama: `.run/ollama.log`
- Cosmos NIM container log while running:
  `docker logs cosmos-reason2-2b` or `docker logs cosmos-reason2-8b`

If restart appears slow, the NIM is usually still loading weights and starting
the OpenAI-compatible server. The restart helper waits until the NIM readiness
endpoint responds or the container logs show:

```text
Uvicorn running on http://0.0.0.0:8000
```

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
