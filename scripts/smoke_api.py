#!/usr/bin/env python3
import argparse
import base64
import json
import mimetypes
import pathlib
import urllib.request


def post(base_url, path, payload, timeout=900):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def data_url(path):
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def summarize(result):
    answer = (result.get("answer") or "").replace("\n", " ")[:700]
    steps = [item.get("tool") for item in result.get("steps", [])]
    summary = {
        "active_model": result.get("active_model"),
        "answer_preview": answer,
        "steps": steps,
    }
    if result.get("artifact"):
        summary["artifact"] = result["artifact"]
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["image", "video", "document", "briefing", "chat", "reset"])
    parser.add_argument("path", nargs="?")
    parser.add_argument("--base-url", default="http://127.0.0.1:7860")
    parser.add_argument("--prompt", default="")
    parser.add_argument("--mode", default="image")
    args = parser.parse_args()

    if args.kind == "reset":
        result = post(args.base_url, "/api/reset", {})
    elif args.kind == "chat":
        result = post(args.base_url, "/api/chat", {"question": args.prompt, "mode": args.mode})
    elif args.kind == "briefing":
        result = post(args.base_url, "/api/generate", {"prompt": args.prompt or "Build a local briefing page from active context."})
    else:
        if not args.path:
            raise SystemExit(f"{args.kind} requires a file path")
        path = pathlib.Path(args.path)
        if args.kind == "image":
            result = post(
                args.base_url,
                "/api/image",
                {"image_data": data_url(path), "prompt": args.prompt or "Identify this image in one sentence."},
            )
        elif args.kind == "video":
            result = post(
                args.base_url,
                "/api/video",
                {
                    "video_data": data_url(path),
                    "name": path.name,
                    "mime": mimetypes.guess_type(str(path))[0] or "",
                    "prompt": args.prompt or "Summarize this video in two concise sentences.",
                },
            )
        elif args.kind == "document":
            result = post(
                args.base_url,
                "/api/document",
                {
                    "documents": [
                        {
                            "name": path.name,
                            "mime": mimetypes.guess_type(str(path))[0] or "text/plain",
                            "data": data_url(path),
                        }
                    ]
                },
            )
        else:
            raise SystemExit(f"Unsupported kind: {args.kind}")
    print(json.dumps(summarize(result), indent=2))


if __name__ == "__main__":
    main()
