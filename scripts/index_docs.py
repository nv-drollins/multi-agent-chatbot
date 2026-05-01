#!/usr/bin/env python3
import hashlib
import json
import os
import pathlib
import re
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "data" / "docs"
INDEX_DIR = ROOT / "data" / "index"
INDEX_PATH = INDEX_DIR / "docs.json"

CURATED = [
    {
        "source": "rtx-pro-6000-blackwell-workstation-edition.pdf",
        "title": "RTX PRO 6000 Blackwell Workstation Edition",
        "text": (
            "The NVIDIA RTX PRO 6000 Blackwell Workstation Edition is positioned as an ultimate "
            "single-GPU workstation powerhouse for AI, graphics, simulation, and agentic AI. "
            "It provides 96 GB of GDDR7 ECC memory, 1.8 TB/s memory bandwidth, 4000 AI TOPS, "
            "125 TFLOPS single-precision performance, 380 TFLOPS RT Core performance, fifth "
            "generation Tensor Cores with FP4 support, fourth generation RT Cores, PCIe Gen 5, "
            "four DisplayPort 2.1b connectors, 4x ninth-generation NVENC, and 4x sixth-generation NVDEC. "
            "The total board power is 600 W."
        ),
    },
    {
        "source": "rtx-pro-6000-blackwell-max-q-workstation-edition.pdf",
        "title": "RTX PRO 6000 Blackwell Max-Q Workstation Edition",
        "text": (
            "The NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition is designed for scalable "
            "high-density workstation performance. It provides 96 GB of GDDR7 ECC memory, "
            "1792 GB/s memory bandwidth, 3511 AI TOPS, 110 TFLOPS single-precision performance, "
            "333 TFLOPS RT Core performance, fifth generation Tensor Cores with FP4 support, "
            "fourth generation RT Cores, PCIe Gen 5, 4x ninth-generation NVENC, 4x sixth-generation "
            "NVDEC, and up to four MIG instances. The total board power is 300 W."
        ),
    },
]


def normalize_ollama_host(value: str) -> str:
    value = value or "127.0.0.1:11445"
    if value.startswith("http://") or value.startswith("https://"):
        return value.rstrip("/")
    return f"http://{value.rstrip('/')}"


def ollama_embedding(text: str):
    host = normalize_ollama_host(os.environ.get("OLLAMA_HOST"))
    model = os.environ.get("EMBED_MODEL", "nomic-embed-text")
    data = json.dumps({"model": model, "prompt": text[:8000]}).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/api/embeddings",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("embedding")
    except Exception:
        return None


def extract_pdf_text(path: pathlib.Path) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        return ""

    try:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def chunk_text(text: str, size: int = 1300):
    text = re.sub(r"\s+", " ", text).strip()
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


def main():
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    docs = []

    for pdf in sorted(DOC_DIR.glob("*.pdf")):
        text = extract_pdf_text(pdf)
        for i, chunk in enumerate(chunk_text(text)):
            docs.append(
                {
                    "id": f"{pdf.stem}-{i}",
                    "source": pdf.name,
                    "title": pdf.stem.replace("-", " ").title(),
                    "text": chunk,
                }
            )

    if not docs:
        docs = [
            {
                "id": hashlib.sha1(item["text"].encode("utf-8")).hexdigest()[:12],
                **item,
            }
            for item in CURATED
        ]

    for doc in docs:
        if "id" not in doc:
            doc["id"] = hashlib.sha1((doc["source"] + doc["text"]).encode("utf-8")).hexdigest()[:12]
        doc["embedding"] = ollama_embedding(doc["text"])

    INDEX_PATH.write_text(json.dumps({"chunks": docs}, indent=2), encoding="utf-8")
    print(f"Indexed {len(docs)} documentation chunks at {INDEX_PATH}")


if __name__ == "__main__":
    main()
