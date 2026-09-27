"""Bounded, cancellable HTTP transport; credentials stay in inherited environment."""
import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path


def strict_json(text, *, max_bytes=16384, max_depth=32):
    if not isinstance(text, str) or len(text.encode("utf-8")) > max_bytes:
        raise ValueError("JSON size limit")
    depth = 0
    quoted = escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > max_depth:
                raise ValueError("JSON depth limit")
        elif char in "]}":
            depth -= 1
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("Duplicate JSON key")
            value[key] = item
        return value
    return json.loads(text, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "Redirect refused", headers, fp)


def worker():
    """Separate process so a slow DNS/connect/read cannot outlive the parent deadline."""
    try:
        # Pipes are UTF-8 regardless of the Windows console's GBK default.
        data = strict_json(sys.stdin.buffer.read().decode("utf-8"), max_bytes=4 * 1024 * 1024, max_depth=64)
        key = os.environ[data["api_key_env"]]
        url = data["base_url"].rstrip("/")
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"
        request = urllib.request.Request(url, data=json.dumps(data["payload"], ensure_ascii=False,
            allow_nan=False, separators=(",", ":")).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=data["timeout_s"]) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
        result = strict_json(raw.decode().replace(key, "[REDACTED]"),
                             max_bytes=4 * 1024 * 1024, max_depth=64)
        output = {"response": result}
    except urllib.error.HTTPError as exc:
        output = {"http_error": exc.code}
    except Exception as exc:
        # Never serialize exception messages/headers/credentials.
        output = {"error": type(exc).__name__}
    sys.stdout.write(json.dumps(output, ensure_ascii=True, allow_nan=False))


class BoundedTransport:
    def __init__(self, config):
        self.config = config
        if not os.environ.get(config.api_key_env):
            raise ValueError(f"Missing API key environment variable: {config.api_key_env}")
        self.lock = threading.Lock()
        self.process = None
        self.closed = False
        self.generation = 0

    def cancel(self):
        with self.lock:
            self.generation += 1
            process = self.process
            if process is not None and process.poll() is None:
                process.kill()

    def close(self):
        with self.lock:
            self.closed = True
        self.cancel()

    def __call__(self, payload):
        with self.lock:
            if self.closed:
                raise RuntimeError("Transport closed")
            generation = self.generation
        env = dict(os.environ, PYGAME_HIDE_SUPPORT_PROMPT="1")
        process = subprocess.Popen(
            [sys.executable, "-B", str(Path(__file__).resolve()), "--worker"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        with self.lock:
            self.process = process
            if self.closed or generation != self.generation:
                process.kill()
        try:
            body = json.dumps({"base_url": self.config.base_url, "api_key_env": self.config.api_key_env,
                "timeout_s": self.config.timeout_s, "payload": payload}, ensure_ascii=False, allow_nan=False)
            try:
                raw, _ = process.communicate(body.encode(), timeout=self.config.timeout_s)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=2)
                raise TimeoutError("Request total deadline exceeded") from None
            if process.returncode != 0:
                raise RuntimeError("Request worker stopped")
            result = strict_json(raw.decode(), max_bytes=8 * 1024 * 1024, max_depth=66)
            if "http_error" in result:
                raise urllib.error.HTTPError(self.config.base_url, result["http_error"], "HTTP error", {}, None)
            if "error" in result:
                if result["error"] in ("TimeoutError", "timeout"):
                    raise TimeoutError("Request timed out")
                raise urllib.error.URLError("Request worker failed: " + result["error"])
            return result["response"]
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=2)
            with self.lock:
                if self.process is process:
                    self.process = None


if __name__ == "__main__":
    worker()
