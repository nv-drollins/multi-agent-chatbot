#!/usr/bin/env python3
import argparse
import base64
import datetime as dt
import html as html_lib
import json
import math
import mimetypes
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
TEMPLATE_DIR = ROOT / "templates"
DATA_DIR = ROOT / "data"
IMAGE_DIR = DATA_DIR / "images"
VIDEO_DIR = DATA_DIR / "videos"
UPLOAD_DIR = DATA_DIR / "uploads"
GENERATION_DIR = DATA_DIR / "generated"
REPORT_DIR = ROOT / "reports"
DOC_INDEX = DATA_DIR / "index" / "docs.json"
EVENTS_PATH = DATA_DIR / "events.json"
STATE_PATH = DATA_DIR / "state.json"
WORKSPACE_DIR = ROOT / "demo-workspace"
CODE_DIR = WORKSPACE_DIR / "shopflow"

INVENTORY_BUCKETS = {
    "images": {
        "label": "Images",
        "directory": IMAGE_DIR,
        "suffixes": {".jpg", ".jpeg", ".png", ".webp", ".gif"},
    },
    "videos": {
        "label": "Videos",
        "directory": VIDEO_DIR,
        "suffixes": {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"},
    },
    "documents": {
        "label": "Documents",
        "directory": UPLOAD_DIR,
        "suffixes": {".pdf", ".txt", ".md", ".csv", ".log"},
    },
}

STATE_LOCK = threading.Lock()

OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
if not OLLAMA_BASE.startswith(("http://", "https://")):
    OLLAMA_BASE = f"http://{OLLAMA_BASE}"
OLLAMA_BASE = OLLAMA_BASE.rstrip("/")

SUPERVISOR_MODEL = os.environ.get("SUPERVISOR_MODEL", os.environ.get("LLM_MODEL", "qwen3:14b"))
CODING_MODEL = os.environ.get("CODING_MODEL", "qwen2.5-coder:7b")
VISION_MODEL = os.environ.get("VISION_MODEL", os.environ.get("VLM_MODEL", "llama3.2-vision:11b"))
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
DEMO_GPU_INDEX = os.environ.get("DEMO_GPU_INDEX", os.environ.get("CUDA_VISIBLE_DEVICES", "0"))
VISION_PROVIDER = os.environ.get("VISION_PROVIDER", "cosmos").lower()
COSMOS_NIM_BASE = os.environ.get("COSMOS_NIM_BASE", "http://127.0.0.1:8000/v1").rstrip("/")
COSMOS_MODEL = os.environ.get("COSMOS_MODEL", "nvidia/cosmos-reason2-2b")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:7860").rstrip("/")

GAME_VARIANTS = [
    {
        "title": "Neon Paddle Arena",
        "status": "Power-ups active",
        "accent": "#76b900",
        "accent_light": "#b7f34a",
        "secondary": "#5ed7c7",
        "power": "#f0b84d",
        "field": "#151812",
        "body": "#0f120f",
        "grid": "#30382b",
        "border": "#3d4638",
        "panel": "#1a1e18",
        "star_count": 80,
        "paddle_height": 126,
        "wide_height": 170,
        "ai_speed": 4.9,
        "powerup_rate": 0.006,
        "max_powerups": 2,
        "grid_step": 64,
        "win_score": 7,
        "ball_min": 6.8,
        "ball_max": 8.4,
        "start_text": "Click or press Space",
    },
    {
        "title": "Circuit Breaker Rally",
        "status": "Charge nodes online",
        "accent": "#8bd80a",
        "accent_light": "#d5ff66",
        "secondary": "#72a7ff",
        "power": "#ffd166",
        "field": "#111719",
        "body": "#0c1012",
        "grid": "#2e4143",
        "border": "#41575a",
        "panel": "#172022",
        "star_count": 55,
        "paddle_height": 112,
        "wide_height": 160,
        "ai_speed": 5.7,
        "powerup_rate": 0.011,
        "max_powerups": 3,
        "grid_step": 48,
        "win_score": 9,
        "ball_min": 7.6,
        "ball_max": 9.4,
        "start_text": "Click to energize grid",
    },
    {
        "title": "Tensor Drift Duel",
        "status": "Boost lanes armed",
        "accent": "#65d46e",
        "accent_light": "#b6ff8a",
        "secondary": "#84d5ff",
        "power": "#ffb45c",
        "field": "#14151b",
        "body": "#0d0f14",
        "grid": "#353847",
        "border": "#454b5e",
        "panel": "#1a1c25",
        "star_count": 115,
        "paddle_height": 142,
        "wide_height": 188,
        "ai_speed": 4.1,
        "powerup_rate": 0.004,
        "max_powerups": 2,
        "grid_step": 80,
        "win_score": 6,
        "ball_min": 6.1,
        "ball_max": 7.6,
        "start_text": "Press Space to drift",
    },
    {
        "title": "Warehouse Pulse Pong",
        "status": "Autonomous pickups live",
        "accent": "#76c043",
        "accent_light": "#c6f56a",
        "secondary": "#57d0b0",
        "power": "#f7c948",
        "field": "#121812",
        "body": "#0d110d",
        "grid": "#31402f",
        "border": "#44513e",
        "panel": "#171f16",
        "star_count": 70,
        "paddle_height": 98,
        "wide_height": 150,
        "ai_speed": 6.2,
        "powerup_rate": 0.014,
        "max_powerups": 4,
        "grid_step": 56,
        "win_score": 8,
        "ball_min": 7.2,
        "ball_max": 10.2,
        "start_text": "Click to start pickup run",
    },
]

SAMPLE_FILES = {
    "README.md": """# ShopFlow Checkout Service

ShopFlow is a tiny local repo for the coding agent. One test intentionally fails
because regional inventory is cached by SKU only.
""",
    "app/__init__.py": "",
    "app/inventory.py": """class DemoInventory:
    def __init__(self, units_by_region):
        self.units_by_region = dict(units_by_region)

    def available(self, sku, region):
        return self.units_by_region.get((sku, region), 0)
""",
    "app/checkout.py": """_INVENTORY_CACHE = {}


def availability_cache_key(sku, region):
    # BUG: region-specific inventory is being cached by SKU only.
    return sku


def available_units(inventory, sku, region):
    key = availability_cache_key(sku, region)
    if key not in _INVENTORY_CACHE:
        _INVENTORY_CACHE[key] = inventory.available(sku, region)
    return _INVENTORY_CACHE[key]


def reserve_cart(cart, region, inventory):
    for item in cart:
        if available_units(inventory, item["sku"], region) < item["qty"]:
            return {"status": "rejected", "reason": "insufficient regional inventory"}
    return {"status": "reserved", "region": region, "items": len(cart)}
""",
    "tests/test_checkout.py": """import unittest

from app.checkout import _INVENTORY_CACHE, reserve_cart
from app.inventory import DemoInventory


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        _INVENTORY_CACHE.clear()

    def test_region_specific_inventory_cache(self):
        inventory = DemoInventory({
            ("rtx-pro-devkit", "us-west"): 0,
            ("rtx-pro-devkit", "us-east"): 3,
        })
        cart = [{"sku": "rtx-pro-devkit", "qty": 1}]

        west = reserve_cart(cart, "us-west", inventory)
        east = reserve_cart(cart, "us-east", inventory)

        self.assertEqual(west["status"], "rejected")
        self.assertEqual(east["status"], "reserved")


if __name__ == "__main__":
    unittest.main()
""",
    "docs/architecture.md": """# Architecture Note

Inventory availability is region-specific. Cache keys for availability must
include both `sku` and `region`.
""",
    "logs/checkout.log": """2026-04-30T09:02:44-04:00 WARN cache_hit sku=rtx-pro-devkit region=us-east cached_units=0
2026-04-30T09:02:44-04:00 ERROR reservation_rejected region=us-east source_inventory_units=3
""",
}


def now_iso():
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def event(agent, action, detail, status="ok"):
    item = {
        "id": f"evt-{int(time.time() * 1000)}",
        "ts": now_iso(),
        "agent": agent,
        "action": action,
        "detail": detail,
        "status": status,
    }
    with STATE_LOCK:
        events = read_json(EVENTS_PATH, [])
        if not isinstance(events, list):
            events = []
        events.append(item)
        write_json(EVENTS_PATH, events[-100:])
    return item


def events():
    return read_json(EVENTS_PATH, [])


def reset_events():
    write_json(EVENTS_PATH, [])


def state():
    value = read_json(STATE_PATH, {})
    return value if isinstance(value, dict) else {}


def update_state(**values):
    current = state()
    current.update(values)
    write_json(STATE_PATH, current)
    return current


def reset_state():
    write_json(STATE_PATH, {})


def trace(agent, tool, detail, status="ok"):
    return {"agent": agent, "tool": tool, "detail": detail, "status": status, "ts": now_iso()}


def ensure_workspace(overwrite=False):
    for rel, content in SAMPLE_FILES.items():
        path = CODE_DIR / rel
        if overwrite or not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")


def http_json(url, payload, timeout=180):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def ollama_chat(model, messages, temperature=0.2, timeout=180, num_ctx=4096):
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": os.environ.get("OLLAMA_KEEP_ALIVE", "30m"),
        "options": {"temperature": temperature, "num_ctx": num_ctx},
    }
    result = http_json(f"{OLLAMA_BASE}/api/chat", payload, timeout=timeout)
    return result.get("message", {}).get("content", "").strip()


def ollama_embedding(text):
    try:
        result = http_json(f"{OLLAMA_BASE}/api/embeddings", {"model": EMBED_MODEL, "prompt": text[:8000]}, timeout=45)
        return result.get("embedding")
    except Exception:
        return None


def ollama_models():
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return [m.get("name") for m in payload.get("models", [])]
    except Exception:
        return []


def vision_model_label():
    if VISION_PROVIDER == "cosmos":
        return f"{COSMOS_MODEL} (NIM preferred)"
    return VISION_MODEL


def strip_reasoning_tags(text):
    text = (text or "").strip()
    answer = re.search(r"<answer>\s*(.*?)\s*</answer>", text, re.IGNORECASE | re.DOTALL)
    if answer:
        return answer.group(1).strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"</?answer>", "", text, flags=re.IGNORECASE)
    return text.strip()


def nim_chat_completion(content, timeout=300, max_tokens=1024):
    payload = {
        "model": COSMOS_MODEL,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{COSMOS_NIM_BASE}/chat/completions",
        data=data,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))
    return strip_reasoning_tags(result.get("choices", [{}])[0].get("message", {}).get("content", ""))


def public_media_url(path, prefix):
    base = {"images": IMAGE_DIR, "videos": VIDEO_DIR}.get(prefix)
    if not base:
        raise ValueError(f"Unknown media prefix: {prefix}")
    rel = pathlib.Path(path).resolve().relative_to(base.resolve()).as_posix()
    return f"{PUBLIC_BASE_URL}/media/{prefix}/{urllib.parse.quote(rel, safe='/')}"


def cosmos_vision(prompt, image_path=None, video_path=None, timeout=300):
    content = [{"type": "text", "text": prompt}]
    if image_path:
        prefix = "images" if str(pathlib.Path(image_path).resolve()).startswith(str(IMAGE_DIR.resolve())) else "videos"
        content.append({"type": "image_url", "image_url": {"url": public_media_url(image_path, prefix)}})
    if video_path:
        content.append({"type": "video_url", "video_url": {"url": public_media_url(video_path, "videos")}})
    return nim_chat_completion(content, timeout=timeout, max_tokens=1200)


def vision_image_answer(prompt, image_b64, path):
    if VISION_PROVIDER == "cosmos":
        try:
            return cosmos_vision(prompt, image_path=path, timeout=300), f"{COSMOS_MODEL} (NIM)", "local.nim.cosmos_reason2"
        except Exception as exc:
            fallback = ollama_chat(
                VISION_MODEL,
                [{"role": "user", "content": prompt, "images": [image_b64]}],
                temperature=0.1,
                timeout=240,
            )
            return fallback, VISION_MODEL, "local.vlm.fallback"
    out = ollama_chat(
        VISION_MODEL,
        [{"role": "user", "content": prompt, "images": [image_b64]}],
        temperature=0.1,
        timeout=240,
    )
    return out, VISION_MODEL, "local.vlm"


def run_cmd(args, cwd=None, timeout=30):
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {"exit_code": result.returncode, "output": result.stdout[-12000:]}
    except Exception as exc:
        return {"exit_code": 124, "output": str(exc)}


def gpu_stats():
    result = run_cmd(
        [
            "nvidia-smi",
            "--query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits",
        ],
        timeout=8,
    )
    rows = []
    for line in result["output"].splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 7:
            rows.append(
                {
                    "index": parts[0],
                    "name": parts[1],
                    "memory_used_mib": to_num(parts[2]),
                    "memory_total_mib": to_num(parts[3]),
                    "utilization_gpu_pct": to_num(parts[4]),
                    "temperature_c": to_num(parts[5]),
                    "power_w": to_num(parts[6]),
                    "demo_gpu": parts[0] == str(DEMO_GPU_INDEX).split(",")[0],
                }
            )
    return rows


def to_num(value):
    try:
        return float(value)
    except Exception:
        return value


def load_docs():
    payload = read_json(DOC_INDEX, {"chunks": []})
    chunks = payload.get("chunks", [])
    return chunks if isinstance(chunks, list) else []


def uploaded_doc_chunks():
    chunks = state().get("uploaded_doc_chunks") or []
    return chunks if isinstance(chunks, list) else []


def active_doc_names():
    names = []
    for chunk in uploaded_doc_chunks():
        source = chunk.get("source")
        if source and source not in names:
            names.append(source)
    return names


def cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def keyword_score(query, text):
    terms = set(re.findall(r"[a-z0-9_-]{3,}", query.lower()))
    if not terms:
        return 0.0
    lower = text.lower()
    return sum(1 for term in terms if term in lower) / len(terms)


def chunk_text(text, size=1300):
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    words = text.split(" ")
    chunks = []
    current = []
    current_len = 0
    for word in words:
        current.append(word)
        current_len += len(word) + 1
        if current_len >= size:
            chunks.append(" ".join(current))
            current = []
            current_len = 0
    if current:
        chunks.append(" ".join(current))
    return chunks


def retrieve_docs(query, limit=4):
    query_vec = ollama_embedding(query)
    scored = []
    for chunk in load_docs():
        score = keyword_score(query, chunk.get("text", ""))
        if query_vec and chunk.get("embedding"):
            score = max(score, cosine(query_vec, chunk["embedding"]))
        scored.append((score, chunk))
    scored.sort(key=lambda row: row[0], reverse=True)
    return [
        {"source": chunk.get("source"), "kind": "pdf", "score": round(score, 4), "text": chunk.get("text", "")[:900]}
        for score, chunk in scored[:limit]
        if score > 0
    ]


def retrieve_uploaded_docs(query, limit=5):
    chunks = uploaded_doc_chunks()
    if not chunks:
        return []
    query_vec = ollama_embedding(query or "summarize uploaded document")
    scored = []
    for chunk in chunks:
        score = keyword_score(query or "", chunk.get("text", ""))
        if query_vec and chunk.get("embedding"):
            score = max(score, cosine(query_vec, chunk["embedding"]))
        scored.append((score, chunk))
    scored.sort(key=lambda row: row[0], reverse=True)
    if scored and scored[0][0] <= 0:
        scored = [(1 / (idx + 2), chunk) for idx, (_, chunk) in enumerate(scored)]
    return [
        {"source": chunk.get("source"), "kind": "upload", "score": round(score, 4), "text": chunk.get("text", "")[:900]}
        for score, chunk in scored[:limit]
    ]


def workspace_sources(query, limit=6):
    ensure_workspace()
    scored = []
    for path in CODE_DIR.rglob("*"):
        if path.is_file() and path.suffix in {".py", ".md", ".log"}:
            rel = path.relative_to(CODE_DIR).as_posix()
            text = path.read_text(encoding="utf-8", errors="replace")
            scored.append((keyword_score(query, rel + "\n" + text), rel, text[:1400]))
    scored.sort(key=lambda row: row[0], reverse=True)
    return [
        {"source": rel, "kind": "workspace", "score": round(score, 4), "text": text}
        for score, rel, text in scored[:limit]
        if score > 0
    ]


def run_tests():
    ensure_workspace()
    return {
        "command": "python3 -m unittest discover -s tests -v",
        **run_cmd(["python3", "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=CODE_DIR, timeout=30),
    }


def code_patch():
    ensure_workspace()
    path = CODE_DIR / "app" / "checkout.py"
    text = path.read_text(encoding="utf-8")
    new_text = text.replace(
        '    # BUG: region-specific inventory is being cached by SKU only.\n    return sku\n',
        '    return f"{sku}:{region}"\n',
    )
    changed = new_text != text
    if changed:
        path.write_text(new_text, encoding="utf-8")
    return changed


def reset_demo():
    ensure_workspace(overwrite=True)
    reset_events()
    reset_state()
    event("Supervisor", "Reset", "Restored demo repo and cleared trace.")
    return {"ok": True, "events": events(), "active_role": "supervisor", "active_model": SUPERVISOR_MODEL}


def decode_data_url(data):
    if not data:
        raise ValueError("file data is required")
    if "," in data:
        _, encoded = data.split(",", 1)
    else:
        encoded = data
    return encoded, base64.b64decode(encoded)


def safe_filename(name, default="upload.bin"):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name or default).strip("-._")
    return cleaned[:90] or default


def image_bytes_from_payload(payload):
    data = payload.get("image_data", "")
    if not data:
        raise ValueError("image_data is required")
    encoded, raw = decode_data_url(data)
    suffix = ".jpg"
    if data.startswith("data:image/png"):
        suffix = ".png"
    elif data.startswith("data:image/webp"):
        suffix = ".webp"
    elif data.startswith("data:image/gif"):
        suffix = ".gif"
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    path = IMAGE_DIR / f"upload-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}{suffix}"
    path.write_bytes(raw)
    return encoded, path


def image_agent(payload):
    image_b64, path = image_bytes_from_payload(payload)
    prompt = payload.get("prompt") or (
        "Identify this uploaded image for a three-minute local multi-agent demo. "
        "Describe what is visible, likely object or scene, useful technical details, "
        "and one practical follow-up for a coding or documentation agent. Answer in English."
    )
    out, active_model, tool = vision_image_answer(prompt, image_b64, path)
    steps = [
        trace("Supervisor", "mcp.router.route", "Routed uploaded image to Image ID Agent"),
        trace("Image ID Agent", "mcp.image.upload", str(path.relative_to(ROOT))),
        trace("Image ID Agent", tool, active_model),
    ]
    update_state(
        last_image={
            "path": str(path),
            "rel": str(path.relative_to(ROOT)),
            "summary": out[:1200],
            "ts": now_iso(),
        }
    )
    event("Image ID Agent", "Image identified", str(path.relative_to(ROOT)))
    return {
        "answer": out,
        "steps": steps,
        "image": str(path.relative_to(ROOT)),
        "sources": [],
        "gpu": gpu_stats(),
        "active_role": "vision",
        "active_model": active_model,
    }


def latest_image_payload():
    latest = state().get("last_image") or {}
    path = pathlib.Path(latest.get("path", ""))
    try:
        resolved = path.resolve()
    except Exception:
        return None
    if not resolved.exists() or not str(resolved).startswith(str(IMAGE_DIR.resolve())):
        return None
    encoded = base64.b64encode(resolved.read_bytes()).decode("ascii")
    return latest, encoded


def image_followup_agent(question):
    latest = latest_image_payload()
    if not latest:
        return {
            "answer": "Upload and identify an image first, then I can answer follow-up questions about it.",
            "steps": [trace("Supervisor", "mcp.router.route", "No uploaded image context found", "warn")],
            "sources": [],
            "gpu": gpu_stats(),
        }
    image_meta, image_b64 = latest
    prompt = (
        "Answer this follow-up about the previously uploaded image. "
        "Use only visual evidence from the image and be concise. "
        f"Question: {question}"
    )
    out, active_model, tool = vision_image_answer(prompt, image_b64, pathlib.Path(image_meta.get("path", "")))
    steps = [
        trace("Supervisor", "mcp.router.route", "Routed image follow-up to Image ID Agent"),
        trace("Image ID Agent", "mcp.image.context", image_meta.get("rel", "latest upload")),
        trace("Image ID Agent", tool, active_model),
    ]
    event("Image ID Agent", "Image follow-up answered", question[:120])
    return {
        "answer": out,
        "steps": steps,
        "image": image_meta.get("rel"),
        "sources": [{"source": image_meta.get("rel"), "kind": "image", "score": 1, "text": image_meta.get("summary", "")}],
        "gpu": gpu_stats(),
        "active_role": "vision",
        "active_model": active_model,
    }


def video_duration(path):
    result = run_cmd(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        timeout=20,
    )
    try:
        return float(result["output"].strip().splitlines()[-1])
    except Exception:
        return 0.0


def sample_video_frames(path, duration, max_frames=8):
    frame_dir = VIDEO_DIR / f"frames-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    frame_dir.mkdir(parents=True, exist_ok=True)
    if duration <= 0:
        times = [0]
    else:
        count = min(max_frames, max(2, int(duration // 20) + 1))
        times = [duration * (index + 1) / (count + 1) for index in range(count)]
    frames = []
    for index, timestamp in enumerate(times, start=1):
        target = frame_dir / f"frame-{index:02d}.jpg"
        result = run_cmd(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{timestamp:.2f}",
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-vf",
                "scale=768:-1",
                "-q:v",
                "3",
                str(target),
            ],
            timeout=30,
        )
        if result["exit_code"] == 0 and target.exists() and target.stat().st_size > 0:
            frames.append(target)
    return frames


def video_bytes_from_payload(payload):
    data = payload.get("video_data", "")
    if not data:
        raise ValueError("video_data is required")
    _, raw = decode_data_url(data)
    name = safe_filename(payload.get("name") or "uploaded-video.mp4")
    suffix = pathlib.Path(name).suffix.lower()
    if suffix not in {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}:
        suffix = ".mp4"
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    path = VIDEO_DIR / f"upload-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}{suffix}"
    path.write_bytes(raw)
    return path


def frame_b64s(frame_paths):
    return [base64.b64encode(path.read_bytes()).decode("ascii") for path in frame_paths]


def compact_text(text, limit=420):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:limit].rstrip()


def format_frame_descriptions(descriptions):
    return "\n".join(f"- Frame {item.get('frame')}: {compact_text(item.get('description', ''), 360)}" for item in descriptions)


def describe_video_frame(frame, index, total):
    frame_prompt = (
        f"Describe sampled video frame {index} of {total} in one concise sentence. "
        "Mention visible objects, scene, actions, and readable text if present."
    )
    if VISION_PROVIDER == "cosmos":
        try:
            return compact_text(cosmos_vision(frame_prompt, image_path=frame, timeout=240), 420), f"{COSMOS_MODEL} (NIM)", "local.nim.cosmos_reason2.describe_frame"
        except Exception:
            pass
    desc = ollama_chat(
        VISION_MODEL,
        [{"role": "user", "content": frame_prompt, "images": [base64.b64encode(frame.read_bytes()).decode("ascii")]}],
        temperature=0.1,
        timeout=180,
        num_ctx=2048,
    )
    return compact_text(desc, 420), VISION_MODEL, "local.vlm.describe_frame"


def summarize_video_descriptions(prompt, descriptions):
    summary_prompt = f"""
You are Video ID Agent. Summarize a short uploaded video using these chronological sampled-frame descriptions.
Describe the overall clip, key actions, visible objects, scene changes, and any readable text.
Keep it concise and useful.

User request:
{prompt}

Frame descriptions:
{format_frame_descriptions(descriptions)}
"""
    if VISION_PROVIDER == "cosmos":
        try:
            return nim_chat_completion([{"type": "text", "text": summary_prompt}], timeout=180, max_tokens=800), f"{COSMOS_MODEL} (NIM)", "local.nim.cosmos_reason2.summarize"
        except Exception:
            pass
    return ollama_chat(SUPERVISOR_MODEL, [{"role": "user", "content": summary_prompt}], temperature=0.1, timeout=180), SUPERVISOR_MODEL, "local.llm.summarize"


def video_agent(payload):
    path = video_bytes_from_payload(payload)
    duration = video_duration(path)
    if duration > 305:
        raise ValueError("Please use a short clip under five minutes for this demo.")
    prompt = payload.get("prompt") or "Summarize this short uploaded video for a local AI demo."
    frames = sample_video_frames(path, duration, max_frames=6)
    if not frames:
        raise ValueError("Could not sample frames from this video. Try MP4, MOV, or WebM.")
    descriptions = []
    frame_model = VISION_MODEL
    frame_tool = "local.vlm.describe_frame"
    for index, frame in enumerate(frames, start=1):
        desc, frame_model, frame_tool = describe_video_frame(frame, index, len(frames))
        descriptions.append({"frame": index, "description": desc})
    out, summary_model, summary_tool = summarize_video_descriptions(prompt, descriptions)
    rel_frames = [str(frame.relative_to(ROOT)) for frame in frames]
    provider = "cosmos_frames" if "cosmos" in frame_tool or "cosmos" in summary_tool else "frame_sampler"
    update_state(
        last_video={
            "path": str(path),
            "rel": str(path.relative_to(ROOT)),
            "frames": [str(frame) for frame in frames],
            "rel_frames": rel_frames,
            "descriptions": descriptions,
            "duration": duration,
            "summary": out[:1600],
            "provider": provider,
            "ts": now_iso(),
        }
    )
    steps = [
        trace("Supervisor", "mcp.router.route", "Routed uploaded video to Video ID Agent"),
        trace("Video ID Agent", "mcp.video.upload", str(path.relative_to(ROOT))),
        trace("Video ID Agent", "mcp.video.sample_frames", f"{len(frames)} frames"),
        trace("Video ID Agent", frame_tool, frame_model),
        trace("Video ID Agent", summary_tool, summary_model),
    ]
    event("Video ID Agent", "Video summarized", str(path.relative_to(ROOT)))
    return {
        "answer": out,
        "steps": steps,
        "video": str(path.relative_to(ROOT)),
        "sources": [{"source": str(path.relative_to(ROOT)), "kind": "video", "score": 1, "text": out[:900]}],
        "gpu": gpu_stats(),
        "active_role": "vision",
        "active_model": summary_model if "cosmos" in summary_tool else frame_model,
    }


def latest_video_payload():
    latest = state().get("last_video") or {}
    source_path = None
    path = pathlib.Path(latest.get("path", ""))
    try:
        resolved_source = path.resolve()
    except Exception:
        resolved_source = None
    if resolved_source and resolved_source.exists() and str(resolved_source).startswith(str(VIDEO_DIR.resolve())):
        source_path = resolved_source
    frames = []
    for item in latest.get("frames") or []:
        path = pathlib.Path(item)
        try:
            resolved = path.resolve()
        except Exception:
            continue
        if resolved.exists() and str(resolved).startswith(str(VIDEO_DIR.resolve())):
            frames.append(resolved)
    if not frames and not source_path:
        return None
    return latest, frame_b64s(frames)


def video_followup_agent(question):
    latest = latest_video_payload()
    if not latest:
        return {
            "answer": "Upload and summarize a short video first, then I can answer follow-up questions about it.",
            "steps": [trace("Supervisor", "mcp.router.route", "No uploaded video context found", "warn")],
            "sources": [],
            "gpu": gpu_stats(),
            "active_role": "vision",
            "active_model": VISION_MODEL,
        }
    video_meta, _ = latest
    video_path = pathlib.Path(video_meta.get("path", ""))
    if video_meta.get("provider") in {"cosmos", "cosmos_frames"} and VISION_PROVIDER == "cosmos":
        try:
            resolved = video_path.resolve()
            if resolved.exists() and str(resolved).startswith(str(VIDEO_DIR.resolve())):
                prompt = (
                    "You are Video ID Agent in a local multi-agent demo. "
                    "Answer this follow-up using the prior video summary and sampled-frame descriptions. "
                    "If the answer is not visible in that context, say so.\n\n"
                    f"Question: {question}\n\n"
                    f"Prior summary:\n{video_meta.get('summary', '')}\n\n"
                    f"Frame descriptions:\n{format_frame_descriptions(video_meta.get('descriptions') or [])}"
                )
                out = nim_chat_completion([{"type": "text", "text": prompt}], timeout=180, max_tokens=700)
                steps = [
                    trace("Supervisor", "mcp.router.route", "Routed video follow-up to Video ID Agent"),
                    trace("Video ID Agent", "mcp.video.context", video_meta.get("rel", "latest upload")),
                    trace("Video ID Agent", "local.nim.cosmos_reason2.answer", COSMOS_MODEL),
                ]
                event("Video ID Agent", "Video follow-up answered", question[:120])
                return {
                    "answer": out,
                    "steps": steps,
                    "video": video_meta.get("rel"),
                    "sources": [{"source": video_meta.get("rel"), "kind": "video", "score": 1, "text": video_meta.get("summary", "")}],
                    "gpu": gpu_stats(),
                    "active_role": "vision",
                    "active_model": f"{COSMOS_MODEL} (NIM)",
                }
        except Exception:
            pass
    descriptions = video_meta.get("descriptions") or []
    prompt = (
        "You are Video ID Agent. Answer this follow-up using only the prior video summary "
        "and sampled-frame descriptions. If the answer is not visible in that context, say so.\n\n"
        f"Question: {question}\n\n"
        f"Prior summary:\n{video_meta.get('summary', '')}\n\n"
        f"Frame descriptions:\n{format_frame_descriptions(descriptions)}"
    )
    out = ollama_chat(SUPERVISOR_MODEL, [{"role": "user", "content": prompt}], temperature=0.1, timeout=180)
    steps = [
        trace("Supervisor", "mcp.router.route", "Routed video follow-up to Video ID Agent"),
        trace("Video ID Agent", "mcp.video.context", video_meta.get("rel", "latest upload")),
        trace("Video ID Agent", "local.llm.answer", SUPERVISOR_MODEL),
    ]
    event("Video ID Agent", "Video follow-up answered", question[:120])
    return {
        "answer": out,
        "steps": steps,
        "video": video_meta.get("rel"),
        "sources": [{"source": video_meta.get("rel"), "kind": "video", "score": 1, "text": video_meta.get("summary", "")}],
        "gpu": gpu_stats(),
        "active_role": "vision",
        "active_model": VISION_MODEL,
    }


def extract_pdf_text(path):
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if text.strip():
            return text
    except Exception:
        pass

    result = run_cmd(["pdftotext", str(path), "-"], timeout=20)
    return result["output"] if result["exit_code"] == 0 else ""


def extract_uploaded_document_text(path, raw, mime, name):
    suffix = pathlib.Path(name).suffix.lower()
    if suffix == ".pdf" or mime == "application/pdf":
        return extract_pdf_text(path)
    if suffix in {".txt", ".md", ".csv", ".log"} or mime.startswith("text/"):
        return raw.decode("utf-8", errors="replace")
    return raw.decode("utf-8", errors="replace")


def document_upload_agent(payload):
    incoming = payload.get("documents")
    if not incoming:
        incoming = [
            {
                "name": payload.get("name", "uploaded-document.txt"),
                "data": payload.get("document_data", ""),
                "mime": payload.get("mime", ""),
            }
        ]
    if not isinstance(incoming, list) or not incoming:
        raise ValueError("documents are required")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    existing = uploaded_doc_chunks()
    created = []
    skipped = []
    for item in incoming[:5]:
        name = safe_filename(item.get("name"), "uploaded-document.txt")
        mime = item.get("mime") or mimetypes.guess_type(name)[0] or "application/octet-stream"
        _, raw = decode_data_url(item.get("data", ""))
        path = UPLOAD_DIR / f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{name}"
        path.write_bytes(raw)
        text = extract_uploaded_document_text(path, raw, mime, name)
        chunks = chunk_text(text, size=1300)[:24]
        if not chunks:
            skipped.append(name)
            continue
        for index, chunk in enumerate(chunks):
            created.append(
                {
                    "id": f"{path.stem}-{index}",
                    "source": name,
                    "path": str(path),
                    "kind": "upload",
                    "text": chunk,
                    "embedding": ollama_embedding(chunk),
                    "ts": now_iso(),
                }
            )

    if not created:
        raise ValueError("No readable text was found. Try a text, Markdown, or text-based PDF file.")

    all_chunks = (existing + created)[-80:]
    update_state(uploaded_doc_chunks=all_chunks, last_doc_upload=now_iso())
    names = sorted({chunk["source"] for chunk in created})
    steps = [
        trace("Supervisor", "mcp.router.route", "Routed upload to Document RAG Agent"),
        trace("Document RAG Agent", "mcp.document.upload", ", ".join(names)),
        trace("Document RAG Agent", "mcp.document.extract", f"{len(created)} chunks"),
        trace("Document RAG Agent", "mcp.embedding.index", EMBED_MODEL),
    ]
    if skipped:
        steps.append(trace("Document RAG Agent", "mcp.document.skip", ", ".join(skipped), "warn"))
    event("Document RAG Agent", "Documents indexed", ", ".join(names))
    answer = f"Indexed {len(created)} local chunks from {', '.join(names)}. Supervisor chat can now answer questions about the uploaded document context."
    return {
        "answer": answer,
        "steps": steps,
        "sources": retrieve_uploaded_docs(" ".join(names), limit=4),
        "gpu": gpu_stats(),
        "documents": active_doc_names(),
        "active_role": "document",
        "active_model": SUPERVISOR_MODEL,
    }


def document_rag_agent(question):
    docs = retrieve_uploaded_docs(question or "summarize uploaded document", limit=5)
    if not docs:
        return {
            "answer": "Upload a PDF, text, or Markdown file first, then switch chat context to Document and ask about it.",
            "steps": [trace("Supervisor", "mcp.router.route", "No uploaded document context found", "warn")],
            "sources": [],
            "gpu": gpu_stats(),
            "active_role": "document",
            "active_model": SUPERVISOR_MODEL,
        }
    prompt = f"""
You are Document RAG Agent in a local multi-agent demo.
Answer the user's question using only the uploaded document excerpts below.
If the answer is not present, say that it is not in the uploaded document context.
Keep the answer concise and mention the source filename when useful.

Question:
{question or "Summarize the uploaded document."}

Uploaded document excerpts:
{json.dumps(docs, indent=2)}
"""
    llm_tool = "local.llm.answer"
    llm_model = SUPERVISOR_MODEL
    try:
        answer = ollama_chat(SUPERVISOR_MODEL, [{"role": "user", "content": prompt}], temperature=0.1, timeout=180)
    except Exception as exc:
        llm_tool = "local.llm.answer_fallback"
        answer = (
            "I indexed the uploaded document and retrieved the most relevant local excerpts, "
            "but the answer model could not complete the generation cleanly. "
            f"Top source: {docs[0].get('source') if docs else 'uploaded document'}.\n\n"
            + "\n\n".join(f"{item.get('source')}: {compact_text(item.get('text'), 420)}" for item in docs[:3])
        )
    steps = [
        trace("Supervisor", "mcp.router.route", "Routed question to Document RAG Agent"),
        trace("Document RAG Agent", "mcp.document.retrieve", f"{len(docs)} uploaded chunks"),
        trace("Document RAG Agent", llm_tool, llm_model),
    ]
    event("Document RAG Agent", "Question answered", (question or "summary")[:120])
    return {
        "answer": answer,
        "steps": steps,
        "sources": docs,
        "gpu": gpu_stats(),
        "documents": active_doc_names(),
        "active_role": "document",
        "active_model": SUPERVISOR_MODEL,
    }


def coding_agent(apply=True):
    before = run_tests()
    sources = workspace_sources("checkout cache region inventory failing test architecture logs", limit=6)
    patch_text = """--- a/app/checkout.py
+++ b/app/checkout.py
@@
 def availability_cache_key(sku, region):
-    # BUG: region-specific inventory is being cached by SKU only.
-    return sku
+    return f"{sku}:{region}"
"""
    changed = code_patch() if apply else False
    after = run_tests() if apply else None
    prompt = f"""
You are Coding Agent, part of a local multi-agent demo. Explain the result in under 120 words.
Use English only. Mention the failing test, root cause, patch, and validation status.

Initial test output:
{before['output']}

Patch:
{patch_text}

After test output:
{after['output'] if after else 'Patch proposed only.'}

Evidence:
{json.dumps(sources, indent=2)}
"""
    answer = ollama_chat(CODING_MODEL, [{"role": "user", "content": prompt}], temperature=0.1, timeout=180)
    steps = [
        trace("Supervisor", "mcp.router.route", "Routed request to Coding Agent"),
        trace("Coding Agent", "mcp.filesystem.search", "app/checkout.py, tests/test_checkout.py, docs/architecture.md"),
        trace("Coding Agent", "mcp.test.run", f"before exit={before['exit_code']}"),
        trace("Coding Agent", "mcp.filesystem.patch", "app/checkout.py" if changed else "patch proposal only"),
    ]
    if after:
        steps.append(trace("Coding Agent", "mcp.test.run", f"after exit={after['exit_code']}"))
    event("Coding Agent", "Code workflow completed", f"before={before['exit_code']} after={after['exit_code'] if after else 'n/a'}")
    return {
        "answer": answer,
        "steps": steps,
        "tests_before": before,
        "tests_after": after,
        "patch": patch_text,
        "sources": sources,
        "gpu": gpu_stats(),
    }


def slugify(value, default="agent-built-app"):
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return (slug[:48] or default).strip("-")


def generated_html_is_offline(html):
    blocked = [
        r"https?://",
        r"<script[^>]+src=",
        r"<link[^>]+href=",
        r"\bfetch\s*\(",
        r"XMLHttpRequest",
        r"\bimport\s*\(",
    ]
    return not any(re.search(pattern, html, re.IGNORECASE) for pattern in blocked)


def is_game_prompt(prompt):
    tokens = set(re.findall(r"[a-z0-9]+", (prompt or "").lower()))
    return bool(
        tokens
        & {
            "game",
            "pong",
            "mario",
            "platformer",
            "arcade",
            "shooter",
            "racing",
            "snake",
            "breakout",
            "runner",
            "playable",
        }
    )


def generated_html_is_rich_enough(html, prompt):
    if not generated_html_is_offline(html):
        return False
    if not is_game_prompt(prompt):
        return True
    lower = html.lower()
    return len(html) >= 9000 and "<canvas" in lower and "requestanimationframe" in lower


def extract_html(raw):
    text = (raw or "").strip()
    fenced = re.search(r"```(?:html)?\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    start = text.lower().find("<!doctype")
    if start < 0:
        start = text.lower().find("<html")
    if start > 0:
        text = text[start:].strip()
    end = text.lower().rfind("</html>")
    if end >= 0:
        text = text[: end + len("</html>")].strip()
    if "<html" not in text.lower() or "</html>" not in text.lower():
        return None
    if not generated_html_is_offline(text):
        return None
    return text


def pick_game_variant():
    current = state()
    index = int(current.get("game_variant_index", -1)) + 1
    update_state(game_variant_index=index)
    return GAME_VARIANTS[index % len(GAME_VARIANTS)]


def extract_design_title(design_brief):
    for line in (design_brief or "").splitlines():
        if "title" not in line.lower():
            continue
        candidate = re.sub(r"^[\s*\-\d.)]+", "", line)
        candidate = re.sub(r"(?i)^title\s*[:\-]\s*", "", candidate)
        candidate = re.sub(r"[*_`\"']", "", candidate).strip()
        if 3 <= len(candidate) <= 48:
            return candidate
    return ""


def apply_game_variant(html, variant, prompt, design_brief=""):
    safe_prompt = re.sub(r"\s+", " ", prompt or "Pong").strip()[:120]
    design_title = extract_design_title(design_brief)
    subtitle = safe_prompt
    if design_title:
        subtitle = f"{design_title}: {safe_prompt}"[:150]
    replacements = {
        "__PROMPT__": html_lib.escape(subtitle),
        "Neon Paddle Arena": html_lib.escape(variant["title"]),
        "Power-ups active": html_lib.escape(variant["status"]),
        "#76b900": variant["accent"],
        "#b7f34a": variant["accent_light"],
        "#5ed7c7": variant["secondary"],
        "#f0b84d": variant["power"],
        "#151812": variant["field"],
        "#0f120f": variant["body"],
        "#30382b": variant["grid"],
        "#3d4638": variant["border"],
        "#1a1e18": variant["panel"],
        "__STAR_COUNT__": str(variant["star_count"]),
        "__PADDLE_HEIGHT__": str(variant["paddle_height"]),
        "__WIDE_HEIGHT__": str(variant["wide_height"]),
        "__AI_SPEED__": str(variant["ai_speed"]),
        "__POWERUP_RATE__": str(variant["powerup_rate"]),
        "__MAX_POWERUPS__": str(variant["max_powerups"]),
        "__GRID_STEP__": str(variant["grid_step"]),
        "__WIN_SCORE__": str(variant["win_score"]),
        "__BALL_MIN_SPEED__": str(variant["ball_min"]),
        "__BALL_MAX_SPEED__": str(variant["ball_max"]),
        "__START_TEXT__": json.dumps(variant["start_text"])[1:-1],
    }
    for old, new in replacements.items():
        html = html.replace(old, new)
    return html


def fallback_game_html(prompt, design_brief=""):
    template = TEMPLATE_DIR / "neon_paddle_arena.html"
    variant = pick_game_variant()
    title = "Agent Arcade"
    safe_prompt = re.sub(r"\s+", " ", prompt or "Pong").strip()[:120]
    if template.exists():
        return apply_game_variant(template.read_text(encoding="utf-8"), variant, prompt, design_brief)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #10120f;
      color: #f2f5ee;
      font-family: Segoe UI, system-ui, sans-serif;
    }}
    main {{
      width: min(960px, 96vw);
      display: grid;
      gap: 12px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 16px;
    }}
    h1 {{ margin: 0; font-size: 24px; }}
    p {{ margin: 0; color: #aeb8a8; }}
    canvas {{
      width: 100%;
      aspect-ratio: 16 / 9;
      background: #151812;
      border: 1px solid #3d4638;
      border-radius: 8px;
      box-shadow: 0 18px 50px rgba(0,0,0,.35);
    }}
    .hud {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      color: #aeb8a8;
      font-size: 14px;
    }}
    button {{
      border: 1px solid #76b900;
      background: #76b900;
      color: #10140d;
      border-radius: 6px;
      padding: 8px 12px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Agent Arcade: Local Pong</h1>
        <p>{html_lib.escape(safe_prompt)}</p>
      </div>
      <button id="restart">Restart</button>
    </header>
    <canvas id="game" width="960" height="540"></canvas>
    <div class="hud">
      <span>W/S or mouse controls the left paddle</span>
      <span id="score">0 : 0</span>
      <span>First to 7 wins</span>
    </div>
  </main>
  <script>
    const canvas = document.getElementById("game");
    const ctx = canvas.getContext("2d");
    const score = document.getElementById("score");
    const state = {{
      player: {{ x: 34, y: 220, w: 14, h: 94, vy: 0 }},
      ai: {{ x: 912, y: 220, w: 14, h: 94 }},
      ball: {{ x: 480, y: 270, r: 9, vx: 6, vy: 3.4 }},
      left: 0,
      right: 0,
      running: true
    }};
    function resetBall(dir = 1) {{
      state.ball.x = 480;
      state.ball.y = 270;
      state.ball.vx = 6 * dir;
      state.ball.vy = (Math.random() * 4 - 2) || 2.4;
    }}
    function restart() {{
      state.left = 0;
      state.right = 0;
      state.running = true;
      state.player.y = 220;
      state.ai.y = 220;
      resetBall(Math.random() > .5 ? 1 : -1);
    }}
    function clamp(v, min, max) {{ return Math.max(min, Math.min(max, v)); }}
    function drawRect(obj, color) {{
      ctx.fillStyle = color;
      ctx.fillRect(obj.x, obj.y, obj.w, obj.h);
    }}
    function step() {{
      if (state.running) {{
        state.player.y = clamp(state.player.y + state.player.vy, 0, canvas.height - state.player.h);
        const target = state.ball.y - state.ai.h / 2;
        state.ai.y += clamp(target - state.ai.y, -4.5, 4.5);
        state.ai.y = clamp(state.ai.y, 0, canvas.height - state.ai.h);
        state.ball.x += state.ball.vx;
        state.ball.y += state.ball.vy;
        if (state.ball.y < state.ball.r || state.ball.y > canvas.height - state.ball.r) {{
          state.ball.vy *= -1;
        }}
        for (const paddle of [state.player, state.ai]) {{
          const hit = state.ball.x + state.ball.r > paddle.x &&
            state.ball.x - state.ball.r < paddle.x + paddle.w &&
            state.ball.y + state.ball.r > paddle.y &&
            state.ball.y - state.ball.r < paddle.y + paddle.h;
          if (hit) {{
            state.ball.vx *= -1.08;
            const offset = (state.ball.y - (paddle.y + paddle.h / 2)) / (paddle.h / 2);
            state.ball.vy = offset * 6;
            state.ball.x += state.ball.vx > 0 ? 8 : -8;
          }}
        }}
        if (state.ball.x < -20) {{ state.right++; resetBall(1); }}
        if (state.ball.x > canvas.width + 20) {{ state.left++; resetBall(-1); }}
        if (state.left >= 7 || state.right >= 7) state.running = false;
      }}
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#1a1e18";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.strokeStyle = "#3d4638";
      ctx.setLineDash([10, 12]);
      ctx.beginPath();
      ctx.moveTo(canvas.width / 2, 0);
      ctx.lineTo(canvas.width / 2, canvas.height);
      ctx.stroke();
      ctx.setLineDash([]);
      drawRect(state.player, "#76b900");
      drawRect(state.ai, "#5ed7c7");
      ctx.fillStyle = "#f2f5ee";
      ctx.beginPath();
      ctx.arc(state.ball.x, state.ball.y, state.ball.r, 0, Math.PI * 2);
      ctx.fill();
      score.textContent = `${{state.left}} : ${{state.right}}`;
      if (!state.running) {{
        ctx.fillStyle = "#f2f5ee";
        ctx.font = "700 36px Segoe UI, system-ui";
        ctx.textAlign = "center";
        ctx.fillText(state.left > state.right ? "You win" : "AI wins", 480, 260);
        ctx.font = "18px Segoe UI, system-ui";
        ctx.fillText("Click Restart to play again", 480, 296);
      }}
      requestAnimationFrame(step);
    }}
    window.addEventListener("keydown", event => {{
      if (event.key.toLowerCase() === "w") state.player.vy = -7;
      if (event.key.toLowerCase() === "s") state.player.vy = 7;
    }});
    window.addEventListener("keyup", event => {{
      if (["w", "s"].includes(event.key.toLowerCase())) state.player.vy = 0;
    }});
    canvas.addEventListener("mousemove", event => {{
      const rect = canvas.getBoundingClientRect();
      const y = (event.clientY - rect.top) * (canvas.height / rect.height);
      state.player.y = clamp(y - state.player.h / 2, 0, canvas.height - state.player.h);
    }});
    document.getElementById("restart").addEventListener("click", restart);
    restart();
    step();
  </script>
</body>
</html>
"""


def data_uri_for_file(path, limit_bytes=8_000_000):
    try:
        path = pathlib.Path(path)
        if not path.exists() or path.stat().st_size > limit_bytes:
            return ""
        mime, _ = mimetypes.guess_type(str(path))
        mime = mime or "application/octet-stream"
        return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
    except Exception:
        return ""


def file_size_label(path):
    try:
        size = pathlib.Path(path).stat().st_size
    except Exception:
        return "n/a"
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def as_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def upload_store_stats():
    stats = []
    for kind, bucket in INVENTORY_BUCKETS.items():
        label = bucket["label"]
        directory = bucket["directory"]
        suffixes = bucket["suffixes"]
        files = [path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in suffixes]
        total = sum(path.stat().st_size for path in files if path.exists())
        stats.append({"kind": kind, "label": label, "count": len(files), "size_mb": round(total / (1024 * 1024), 2)})
    return stats


def absolute_url(path):
    return f"{PUBLIC_BASE_URL}{path if path.startswith('/') else '/' + path}"


def media_url(kind, path):
    bucket = INVENTORY_BUCKETS[kind]
    rel = pathlib.Path(path).resolve().relative_to(bucket["directory"].resolve()).as_posix()
    return f"/media/{kind}/{urllib.parse.quote(rel)}"


def inventory_items(kind, limit=80):
    bucket = INVENTORY_BUCKETS.get(kind)
    if not bucket:
        return []
    directory = bucket["directory"]
    suffixes = bucket["suffixes"]
    files = []
    for path in directory.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        preview = ""
        if kind == "documents" and path.suffix.lower() in {".txt", ".md", ".csv", ".log"}:
            try:
                preview = compact_text(path.read_text(encoding="utf-8", errors="ignore"), 900)
            except Exception:
                preview = ""
        files.append(
            {
                "name": path.name,
                "rel": str(path.relative_to(ROOT)),
                "url": media_url(kind, path),
                "size": file_size_label(path),
                "modified": dt.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "preview": preview,
            }
        )
    files.sort(key=lambda item: item["modified"], reverse=True)
    return files[:limit]


def active_briefing_context():
    current = state()
    image = current.get("last_image") or {}
    image_path = pathlib.Path(image.get("path", ""))
    if image_path.exists() and str(image_path.resolve()).startswith(str(IMAGE_DIR.resolve())):
        image["data_uri"] = data_uri_for_file(image_path)
        image["size"] = file_size_label(image_path)
    else:
        image = {}

    video = current.get("last_video") or {}
    frame_items = []
    for index, frame in enumerate(video.get("frames") or [], start=1):
        frame_path = pathlib.Path(frame)
        try:
            resolved = frame_path.resolve()
        except Exception:
            continue
        if resolved.exists() and str(resolved).startswith(str(VIDEO_DIR.resolve())):
            frame_items.append({"index": index, "data_uri": data_uri_for_file(resolved, limit_bytes=2_000_000), "rel": str(resolved.relative_to(ROOT))})
    if video:
        video["frames_embedded"] = [item for item in frame_items if item.get("data_uri")][:6]
        video["duration_label"] = f"{float(video.get('duration') or 0):.1f}s"
        video_path = pathlib.Path(video.get("path", ""))
        if video_path.exists():
            video["size"] = file_size_label(video_path)

    doc_chunks = uploaded_doc_chunks()
    doc_names = active_doc_names()
    doc_excerpts = [
        {"source": chunk.get("source", "document"), "text": compact_text(chunk.get("text", ""), 520)}
        for chunk in doc_chunks[:8]
    ]

    return {
        "image": image,
        "video": video if video else {},
        "documents": {"names": doc_names, "chunk_count": len(doc_chunks), "excerpts": doc_excerpts},
        "store_stats": upload_store_stats(),
        "gpu": gpu_stats(),
        "events": events()[-12:],
    }


def coding_agent_briefing_notes(prompt, context):
    source_payload = {
        "image_summary": (context.get("image") or {}).get("summary", ""),
        "video_summary": (context.get("video") or {}).get("summary", ""),
        "video_frame_descriptions": (context.get("video") or {}).get("descriptions", [])[:6],
        "document_names": (context.get("documents") or {}).get("names", []),
        "document_excerpts": (context.get("documents") or {}).get("excerpts", [])[:5],
        "upload_stats": context.get("store_stats", []),
    }
    notes_prompt = f"""
You are Coding Agent in a local multi-agent demo. Create concise briefing copy for a self-contained HTML page.
Use only the local context below. Do not invent facts. If an image, video, or document is missing, say so plainly.

User request:
{prompt}

Local context:
{json.dumps(source_payload, indent=2)}

Return:
- One sentence executive summary.
- 3 to 5 evidence bullets.
- 2 to 4 suggested next actions.
"""
    try:
        return ollama_chat(CODING_MODEL, [{"role": "user", "content": notes_prompt}], temperature=0.2, timeout=180, num_ctx=4096)
    except Exception as exc:
        return f"Briefing notes fallback: the coding model could not complete notes generation ({compact_text(str(exc), 120)}). The page still includes all local evidence, summaries, excerpts, and upload statistics."


def escape_block(value):
    return html_lib.escape(str(value or "")).replace("\n", "<br>")


def briefing_stat_cards(stats):
    cards = []
    for item in stats:
        kind = item.get("kind", str(item.get("label", "")).lower())
        href = absolute_url(f"/inventory/{urllib.parse.quote(kind)}")
        cards.append(
            f"""
            <article class="stat">
              <span>{html_lib.escape(item['label'])}</span>
              <a class="stat-count" href="{html_lib.escape(href)}" target="_blank" rel="noopener">{item['count']}</a>
              <small>{item['size_mb']} MB retained locally</small>
            </article>
            """
        )
    return "\n".join(cards)


def briefing_event_rows(items):
    if not items:
        return '<p class="muted">No agent timeline events yet.</p>'
    return "\n".join(
        f"<li><time>{html_lib.escape(item.get('ts', ''))}</time><b>{html_lib.escape(item.get('agent', 'Agent'))}</b><span>{html_lib.escape(item.get('action', ''))}</span></li>"
        for item in items[-8:]
    )


def build_briefing_html(prompt, context, notes):
    image = context.get("image") or {}
    video = context.get("video") or {}
    documents = context.get("documents") or {}
    doc_names = ", ".join(documents.get("names") or []) or "No active documents"
    gpu = next((item for item in context.get("gpu", []) if item.get("demo_gpu")), (context.get("gpu") or [{}])[0] if context.get("gpu") else {})
    image_block = (
        f'<img src="{image.get("data_uri")}" alt="Uploaded image preview"><p class="evidence-text">{escape_block(image.get("summary", "No image summary available."))}</p>'
        if image.get("data_uri")
        else '<p class="muted">No active image upload in this case file.</p>'
    )
    frame_blocks = "".join(
        f'<figure><img src="{item["data_uri"]}" alt="Sampled video frame {item["index"]}"><figcaption>Frame {item["index"]}</figcaption></figure>'
        for item in video.get("frames_embedded", [])
    )
    video_block = (
        f'<p class="evidence-text">{escape_block(video.get("summary", ""))}</p><div class="frames">{frame_blocks}</div>'
        if video.get("summary")
        else '<p class="muted">No active video upload in this case file.</p>'
    )
    excerpts = documents.get("excerpts") or []
    doc_block = "\n".join(
        f'<article class="excerpt"><strong>{html_lib.escape(item["source"])}</strong><p>{escape_block(item["text"])}</p></article>'
        for item in excerpts[:5]
    ) or '<p class="muted">No active document excerpts indexed.</p>'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Local Agent Briefing</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #0f1210; color: #eef4eb; font-family: Segoe UI, system-ui, sans-serif; }}
    header {{ padding: 28px clamp(18px, 4vw, 48px); border-bottom: 1px solid #2d3a2b; background: #151a14; }}
    main {{ display: grid; gap: 18px; padding: 20px clamp(18px, 4vw, 48px) 42px; }}
    h1 {{ margin: 0; font-size: 30px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 10px; font-size: 18px; }}
    p {{ line-height: 1.52; overflow-wrap: anywhere; }}
    a {{ color: #9be15d; }}
    .meta, .muted {{ color: #aeb8a8; }}
    .grid {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: 14px; }}
    .panel {{ border: 1px solid #344432; border-radius: 8px; background: #171d16; padding: 16px; overflow: visible; }}
    .wide {{ grid-column: span 12; }}
    .half {{ grid-column: span 6; }}
    .third {{ grid-column: span 4; }}
    .stats {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .stat {{ border: 1px solid #334330; border-radius: 8px; padding: 14px; background: #111710; }}
    .stat span, .stat small {{ display: block; color: #aeb8a8; }}
    .stat-count {{ display: inline-block; font-size: 30px; color: #9be15d; margin: 4px 0; font-weight: 800; text-decoration: none; }}
    .stat-count:hover {{ text-decoration: underline; }}
    img {{ max-width: 100%; border-radius: 6px; border: 1px solid #334330; background: #0f120f; }}
    .frames {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }}
    figure {{ margin: 0; }}
    figcaption {{ color: #aeb8a8; font-size: 12px; margin-top: 4px; }}
    .excerpt {{ border-top: 1px solid #2c392a; padding-top: 10px; margin-top: 10px; }}
    .notes, .evidence-text, .excerpt p {{ white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; }}
    .notes {{ background: #10160f; border: 1px solid #334330; border-radius: 8px; padding: 14px; }}
    .timeline {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }}
    .timeline li {{ display: grid; grid-template-columns: 170px 160px 1fr; gap: 10px; color: #dfe8d8; }}
    .timeline time, .timeline span {{ color: #aeb8a8; }}
    @media (max-width: 880px) {{
      .half, .third {{ grid-column: span 12; }}
      .stats, .frames {{ grid-template-columns: 1fr; }}
      .timeline li {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Local Agent Briefing</h1>
    <p class="meta">Generated locally by the Coding Agent from active image, video, and document context. No cloud calls or external page assets.</p>
  </header>
  <main>
    <section class="grid">
      <article class="panel wide">
        <h2>Coding Agent Notes</h2>
        <div class="notes">{escape_block(notes)}</div>
      </article>
      <article class="panel wide">
        <h2>Upload Store</h2>
        <div class="stats">{briefing_stat_cards(context.get("store_stats", []))}</div>
      </article>
      <article class="panel half">
        <h2>Image Evidence</h2>
        {image_block}
        <p class="meta">Source: {html_lib.escape(image.get("rel", "none"))} {html_lib.escape(image.get("size", ""))}</p>
      </article>
      <article class="panel half">
        <h2>Video Evidence</h2>
        {video_block}
        <p class="meta">Source: {html_lib.escape(video.get("rel", "none"))} {html_lib.escape(video.get("duration_label", ""))} {html_lib.escape(video.get("size", ""))}</p>
      </article>
      <article class="panel wide">
        <h2>Document Evidence</h2>
        <p class="meta">Active documents: {html_lib.escape(doc_names)}; chunks indexed: {documents.get("chunk_count", 0)}</p>
        {doc_block}
      </article>
      <article class="panel half">
        <h2>GPU Snapshot</h2>
        <p>GPU {html_lib.escape(gpu.get("index", "0"))}: {html_lib.escape(gpu.get("name", "local GPU"))}</p>
        <p class="meta">{as_float(gpu.get("memory_used_mib")):.0f} / {as_float(gpu.get("memory_total_mib")):.0f} MiB, {as_float(gpu.get("utilization_gpu_pct")):.0f}% utilization, {as_float(gpu.get("temperature_c")):.0f} C</p>
      </article>
      <article class="panel half">
        <h2>Agent Timeline</h2>
        <ul class="timeline">{briefing_event_rows(context.get("events", []))}</ul>
      </article>
    </section>
  </main>
</body>
</html>
"""


def inventory_page(kind):
    bucket = INVENTORY_BUCKETS.get(kind)
    if not bucket:
        return None
    items = inventory_items(kind)
    if not items:
        cards = '<p class="muted">No local files are retained in this bucket yet.</p>'
    else:
        blocks = []
        for item in items:
            href = absolute_url(item["url"])
            title = html_lib.escape(item["name"])
            rel = html_lib.escape(item["rel"])
            meta = html_lib.escape(f'{item["size"]} | modified {item["modified"]}')
            if kind == "images":
                media = f'<a href="{html_lib.escape(href)}" target="_blank" rel="noopener"><img src="{html_lib.escape(href)}" alt="{title}"></a>'
            elif kind == "videos":
                media = f'<video src="{html_lib.escape(href)}" controls muted preload="metadata"></video>'
            else:
                preview = escape_block(item.get("preview") or "Preview unavailable for this document type.")
                media = f'<pre>{preview}</pre><a class="open" href="{html_lib.escape(href)}" target="_blank" rel="noopener">Open local document</a>'
            blocks.append(
                f"""
                <article class="card">
                  {media}
                  <h2>{title}</h2>
                  <p>{rel}</p>
                  <small>{meta}</small>
                </article>
                """
            )
        cards = "\n".join(blocks)

    label = html_lib.escape(bucket["label"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Local {label} Inventory</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #0f1210; color: #eef4eb; font-family: Segoe UI, system-ui, sans-serif; }}
    header {{ padding: 24px clamp(18px, 4vw, 46px); background: #151a14; border-bottom: 1px solid #2d3a2b; }}
    main {{ padding: 20px clamp(18px, 4vw, 46px) 42px; }}
    h1 {{ margin: 0; font-size: 28px; letter-spacing: 0; }}
    h2 {{ margin: 10px 0 6px; font-size: 15px; overflow-wrap: anywhere; }}
    p, small, pre {{ overflow-wrap: anywhere; }}
    p {{ margin: 0; color: #aeb8a8; line-height: 1.45; }}
    small {{ color: #8f9b88; }}
    a {{ color: #9be15d; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; }}
    .card {{ border: 1px solid #344432; border-radius: 8px; background: #171d16; padding: 12px; min-width: 0; }}
    img, video {{ width: 100%; aspect-ratio: 16 / 9; object-fit: cover; border-radius: 6px; border: 1px solid #334330; background: #0f120f; }}
    pre {{ min-height: 130px; max-height: 260px; overflow: auto; white-space: pre-wrap; border: 1px solid #334330; border-radius: 6px; background: #10160f; padding: 10px; color: #dfe8d8; }}
    .open {{ display: inline-block; margin-top: 8px; }}
    .muted {{ color: #aeb8a8; }}
  </style>
</head>
<body>
  <header>
    <h1>Local {label} Inventory</h1>
    <p>Files retained by this demo on the local workstation. No cloud storage or external page assets.</p>
  </header>
  <main>
    <section class="grid">{cards}</section>
  </main>
</body>
</html>
"""


def generate_app_agent(prompt):
    prompt = (prompt or "").strip() or "Build a local briefing page from the active image, video, and document context."
    context = active_briefing_context()
    notes = coding_agent_briefing_notes(prompt, context)
    html = build_briefing_html(prompt, context, notes)
    GENERATION_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"local-agent-briefing-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    generated_path = GENERATION_DIR / filename
    generated_path.write_text(html, encoding="utf-8")

    desktop = pathlib.Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    desktop_path = desktop / filename
    shutil.copy2(generated_path, desktop_path)

    steps = [
        trace("Supervisor", "mcp.router.route", "Routed briefing request to Coding Agent"),
        trace("Coding Agent", "mcp.context.collect", "image, video, document, timeline, GPU telemetry"),
        trace("Coding Agent", "local.llm.briefing_notes", CODING_MODEL),
        trace("Coding Agent", "mcp.artifact.package", "self-contained local briefing HTML"),
        trace("Coding Agent", "mcp.filesystem.write", str(generated_path.relative_to(ROOT))),
        trace("Coding Agent", "mcp.desktop.package", str(desktop_path)),
    ]
    event("Coding Agent", "Briefing page generated", filename)
    answer = (
        f"Built a self-contained local briefing page from the active uploaded context.\n\n"
        f"Coding model: {CODING_MODEL}\n"
        f"Image context: {'yes' if context.get('image') else 'no'}\n"
        f"Video context: {'yes' if context.get('video') else 'no'}\n"
        f"Document chunks: {context.get('documents', {}).get('chunk_count', 0)}\n"
        f"Generated file: {generated_path.relative_to(ROOT)}\n"
        + f"Desktop copy: {desktop_path}\n\n"
        + "It opens as a local HTML report with embedded image/frame evidence, document excerpts, upload stats, GPU telemetry, and the agent timeline."
    )
    return {
        "answer": answer,
        "steps": steps,
        "artifact": {"name": filename, "url": f"/generated/{urllib.parse.quote(filename)}", "desktop_path": str(desktop_path)},
        "terminal": html,
        "sources": (
            ([{"source": context["image"].get("rel"), "kind": "image", "score": 1, "text": context["image"].get("summary", "")}] if context.get("image") else [])
            + ([{"source": context["video"].get("rel"), "kind": "video", "score": 1, "text": context["video"].get("summary", "")}] if context.get("video") else [])
            + retrieve_uploaded_docs(" ".join(context.get("documents", {}).get("names", [])) or "uploaded context", limit=4)
        ),
        "gpu": gpu_stats(),
        "active_role": "app",
        "active_model": CODING_MODEL,
    }


def rag_agent(question):
    docs = retrieve_docs(question or "RTX PRO 6000 local agents image coding", limit=5)
    answer = (
        "RTX PRO 6000 is a strong fit for this single-GPU local multi-agent demo because "
        "the local PDFs describe 96 GB of GDDR7 ECC memory, 5th Gen Tensor Cores with FP4 "
        "support, Blackwell AI performance, PCIe Gen 5, and 9th Gen NVENC / 6th Gen NVDEC. "
        "That is enough headroom to keep a supervisor, coding model, vision model, embeddings, "
        "document retrieval, and GPU telemetry local without using cloud inference."
    )
    steps = [
        trace("Supervisor", "mcp.router.route", "Routed hardware/docs question to RAG Agent"),
        trace("RAG Agent", "mcp.docs.retrieve", f"{len(docs)} local RTX PRO PDF chunks"),
    ]
    event("RAG Agent", "Docs retrieved", question[:120])
    return {"answer": answer, "steps": steps, "sources": docs, "gpu": gpu_stats()}


def gpu_agent():
    stats = gpu_stats()
    steps = [
        trace("Supervisor", "mcp.router.route", "Routed health question to GPU Agent"),
        trace("GPU Agent", "mcp.gpu.telemetry", "nvidia-smi"),
    ]
    answer = "GPU 0 is the demo GPU. GPU 1 is left idle as proof this is a single-GPU run."
    if stats:
        demo = next((g for g in stats if g["demo_gpu"]), stats[0])
        answer = (
            f"Demo GPU {demo['index']} is {demo['name']} with "
            f"{demo['memory_used_mib']:.0f}/{demo['memory_total_mib']:.0f} MiB used, "
            f"{demo['utilization_gpu_pct']:.0f}% utilization, and {demo['temperature_c']:.0f} C."
        )
    event("GPU Agent", "Telemetry checked", "nvidia-smi")
    return {"answer": answer, "steps": steps, "sources": [], "gpu": stats}


def is_app_generation_request(lower):
    action = any(word in lower for word in ["generate", "build", "create", "make", "write"])
    artifact = any(word in lower for word in ["briefing", "report", "page", "dashboard", "artifact", "summary", "html", "browser", "demo"])
    return action and artifact


def is_code_repair_request(lower):
    return any(word in lower for word in ["code", "test", "bug", "fix", "patch", "checkout"])


def is_gpu_request(lower):
    return any(word in lower for word in ["gpu", "health", "memory", "utilization", "temperature"])


def is_rag_request(lower):
    return any(word in lower for word in ["rtx", "spec", "pdf", "hardware", "workstation", "datasheet", "document"])


def is_document_question(lower):
    tokens = set(re.findall(r"[a-z0-9]+", lower))
    return any(
        word in tokens
        for word in [
            "document",
            "pdf",
            "file",
            "uploaded",
            "text",
            "summarize",
            "summary",
            "explain",
            "section",
            "page",
            "contract",
            "manual",
            "spec",
        ]
    )


def is_image_question(lower):
    tokens = set(re.findall(r"[a-z0-9]+", lower))
    return any(
        word in tokens
        for word in [
            "image",
            "picture",
            "photo",
            "screenshot",
            "uploaded",
            "visible",
            "see",
            "shown",
            "object",
            "logo",
            "color",
            "text",
            "read",
            "identify",
            "this",
            "that",
            "it",
        ]
    )


def is_video_question(lower):
    tokens = set(re.findall(r"[a-z0-9]+", lower))
    return any(
        word in tokens
        for word in [
            "video",
            "clip",
            "movie",
            "frame",
            "frames",
            "scene",
            "action",
            "summarize",
            "summary",
            "watch",
            "visible",
            "happens",
            "happening",
            "person",
            "people",
        ]
    )


def supervisor(payload):
    question = (payload.get("question") or "").strip()
    lower = question.lower()
    mode = (payload.get("mode") or "image").lower()
    if is_app_generation_request(lower):
        return generate_app_agent(question)
    if mode == "document":
        return document_rag_agent(question)
    if mode == "video":
        if payload.get("video_data"):
            video_payload = dict(payload)
            if question:
                video_payload["prompt"] = question
            return video_agent(video_payload)
        return video_followup_agent(question)
    if mode == "image":
        if payload.get("image_data"):
            image_payload = dict(payload)
            if question:
                image_payload["prompt"] = question
            return image_agent(image_payload)
        return image_followup_agent(question)
    if is_code_repair_request(lower):
        return coding_agent(apply=True)
    if is_gpu_request(lower):
        return gpu_agent()
    if payload.get("image_data") and (not question or is_image_question(lower)):
        image_payload = dict(payload)
        if question:
            image_payload["prompt"] = question
        return image_agent(image_payload)
    if latest_image_payload() and is_image_question(lower):
        return image_followup_agent(question)
    if payload.get("video_data") and (not question or is_video_question(lower)):
        video_payload = dict(payload)
        if question:
            video_payload["prompt"] = question
        return video_agent(video_payload)
    if latest_video_payload() and is_video_question(lower):
        return video_followup_agent(question)
    if uploaded_doc_chunks() and (is_document_question(lower) or not latest_image_payload()):
        return document_rag_agent(question)
    if is_rag_request(lower):
        return document_rag_agent(question) if uploaded_doc_chunks() else rag_agent(question)
    if payload.get("image_data"):
        image_payload = dict(payload)
        if question:
            image_payload["prompt"] = question
        return image_agent(image_payload)
    if uploaded_doc_chunks():
        return document_rag_agent(question)

    docs = retrieve_docs(question, limit=3)
    code = workspace_sources(question, limit=3)
    prompt = f"""
You are Supervisor Agent for a local multi-agent chatbot demo. Choose the best specialist
and answer in under 100 words. Specialists: Image ID Agent, Coding Agent, RAG Agent, GPU Agent.
Question: {question}
Local docs: {json.dumps(docs, indent=2)}
Local code: {json.dumps(code, indent=2)}
"""
    answer = ollama_chat(SUPERVISOR_MODEL, [{"role": "user", "content": prompt}], temperature=0.2, timeout=160)
    steps = [trace("Supervisor", "mcp.router.plan", "Answered with local context")]
    event("Supervisor", "Question answered", question[:120])
    return {"answer": answer, "steps": steps, "sources": docs + code, "gpu": gpu_stats()}


def demo_script():
    return {
        "title": "Three-minute local multi-agent path",
        "steps": [
            "Upload one matching image, video, and document from a prepared case file.",
            "Run Image ID, Summarize Video, and Index Document to build local context.",
            "Ask a follow-up question in Supervisor Chat against Image, Video, or Document.",
            "Click Build Briefing Page and open the desktop HTML report generated by the Coding Agent.",
        ],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalMultiAgentDemo/0.3"

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def send_json(self, value, status=200):
        encoded = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_html(self, value, status=200):
        encoded = value.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/status":
            self.send_json(
                {
                    "ollama": OLLAMA_BASE,
                    "models": ollama_models(),
                    "supervisor_model": SUPERVISOR_MODEL,
                    "coding_model": CODING_MODEL,
                    "vision_model": vision_model_label(),
                    "embed_model": EMBED_MODEL,
                    "model_roles": {
                        "supervisor": SUPERVISOR_MODEL,
                        "vision": vision_model_label(),
                        "document": SUPERVISOR_MODEL,
                        "app": CODING_MODEL,
                        "embedding": EMBED_MODEL,
                    },
                    "demo_gpu_index": DEMO_GPU_INDEX,
                    "gpu": gpu_stats(),
                    "events": events(),
                    "docs": len(load_docs()),
                    "active_image": (state().get("last_image") or {}).get("rel"),
                    "active_video": (state().get("last_video") or {}).get("rel"),
                    "active_documents": active_doc_names(),
                    "uploaded_doc_chunks": len(uploaded_doc_chunks()),
                    "script": demo_script(),
                }
            )
            return
        if parsed.path.startswith("/generated/"):
            self.serve_generated(parsed.path)
            return
        if parsed.path.startswith("/inventory/"):
            self.serve_inventory(parsed.path)
            return
        if parsed.path.startswith("/media/"):
            self.serve_media(parsed.path)
            return
        self.serve_static(parsed.path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            payload = self.read_body()
            if parsed.path == "/api/chat":
                self.send_json(supervisor(payload))
            elif parsed.path == "/api/image":
                self.send_json(image_agent(payload))
            elif parsed.path == "/api/video":
                self.send_json(video_agent(payload))
            elif parsed.path == "/api/document":
                self.send_json(document_upload_agent(payload))
            elif parsed.path == "/api/code":
                self.send_json(coding_agent(apply=payload.get("apply", True)))
            elif parsed.path == "/api/generate":
                self.send_json(generate_app_agent(payload.get("prompt", "")))
            elif parsed.path == "/api/rag":
                self.send_json(rag_agent(payload.get("question", "")))
            elif parsed.path == "/api/gpu":
                self.send_json(gpu_agent())
            elif parsed.path == "/api/reset":
                self.send_json(reset_demo())
            else:
                self.send_json({"error": "not found"}, status=404)
        except Exception as exc:
            self.log_message("handler error for %s: %s", parsed.path, exc)
            traceback.print_exc()
            self.send_json({"error": str(exc)}, status=500)

    def serve_static(self, path):
        if path == "/":
            path = "/index.html"
        rel = pathlib.Path(path.lstrip("/"))
        target = (STATIC_DIR / rel).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.exists():
            self.send_error(404)
            return
        content = target.read_bytes()
        mime, _ = mimetypes.guess_type(str(target))
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def serve_generated(self, path):
        name = urllib.parse.unquote(path.removeprefix("/generated/"))
        rel = pathlib.Path(name)
        target = (GENERATION_DIR / rel).resolve()
        if not str(target).startswith(str(GENERATION_DIR.resolve())) or not target.exists():
            self.send_error(404)
            return
        content = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def serve_inventory(self, path):
        kind = urllib.parse.unquote(path.removeprefix("/inventory/")).strip("/")
        html = inventory_page(kind)
        if html is None:
            self.send_error(404)
            return
        self.send_html(html)

    def serve_media(self, path):
        parts = path.split("/", 3)
        if len(parts) < 4:
            self.send_error(404)
            return
        prefix = parts[2]
        bucket = INVENTORY_BUCKETS.get(prefix)
        base = bucket["directory"] if bucket else None
        if not base:
            self.send_error(404)
            return
        rel = pathlib.PurePosixPath(urllib.parse.unquote(parts[3]))
        if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
            self.send_error(404)
            return
        target = (base / pathlib.Path(*rel.parts)).resolve()
        if not str(target).startswith(str(base.resolve())) or not target.exists():
            self.send_error(404)
            return
        content = target.read_bytes()
        mime, _ = mimetypes.guess_type(str(target))
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    for directory in [DATA_DIR, IMAGE_DIR, VIDEO_DIR, UPLOAD_DIR, REPORT_DIR, DOC_INDEX.parent]:
        directory.mkdir(parents=True, exist_ok=True)
    ensure_workspace()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Local Multi-Agent Chatbot listening on http://{args.host}:{args.port}")
    print(f"Supervisor={SUPERVISOR_MODEL}; Coding={CODING_MODEL}; Vision={vision_model_label()}; GPU={DEMO_GPU_INDEX}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
