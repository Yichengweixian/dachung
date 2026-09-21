"""Real-browser (Chrome DevTools Protocol) acceptance run for the U13 prototype.

Standard library only: no browser-automation package is added to the frozen environment.
This produces *automation-level* browser evidence (page render + button/tab clicks in a
real Chromium engine). It is NOT human confirmation and must not be reported as such.
"""
import argparse
import base64
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def http_json(url, method="GET"):
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


class WebSocket:
    """Minimal RFC6455 client (text frames, ping/pong, fragmentation)."""

    def __init__(self, url, timeout=600):
        rest = url[5:]
        hostport, _, path = rest.partition("/")
        host, _, port = hostport.partition(":")
        self.sock = socket.create_connection((host, int(port or 80)), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        request = (
            f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode())
        buffer = b""
        while b"\r\n\r\n" not in buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("handshake closed by peer")
            buffer += chunk
        head, _, self.buffer = buffer.partition(b"\r\n\r\n")
        status = head.split(b"\r\n")[0]
        if b" 101" not in status:
            raise ConnectionError(status.decode("latin-1"))

    def _read(self, count):
        while len(self.buffer) < count:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("websocket closed")
            self.buffer += chunk
        out, self.buffer = self.buffer[:count], self.buffer[count:]
        return out

    @staticmethod
    def _header(opcode, length, mask):
        header = bytearray([0x80 | opcode])
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", length)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", length)
        header += mask
        return bytes(header)

    @staticmethod
    def _mask(payload, mask):
        return bytes(b ^ mask[i % 4] for i, b in enumerate(payload))

    def send(self, text):
        payload = text.encode("utf-8")
        mask = os.urandom(4)
        self.sock.sendall(self._header(0x1, len(payload), mask) + self._mask(payload, mask))

    def _pong(self, payload):
        mask = os.urandom(4)
        self.sock.sendall(self._header(0xA, len(payload), mask) + self._mask(payload, mask))

    def recv(self):
        while True:
            first, second = self._read(2)
            fin, opcode, length = first & 0x80, first & 0x0F, second & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read(8))[0]
            mask = self._read(4) if second & 0x80 else None
            data = self._read(length)
            if mask:
                data = self._mask(data, mask)
            if opcode == 0x9:
                self._pong(data)
                continue
            if opcode == 0xA:
                continue
            if opcode == 0x8:
                raise ConnectionError("websocket closed by peer")
            if opcode in (0x1, 0x2):
                if fin:
                    return data.decode("utf-8")
                parts = [data]
                while True:
                    first, second = self._read(2)
                    length = second & 0x7F
                    if length == 126:
                        length = struct.unpack(">H", self._read(2))[0]
                    elif length == 127:
                        length = struct.unpack(">Q", self._read(8))[0]
                    mask = self._read(4) if second & 0x80 else None
                    chunk = self._read(length)
                    if mask:
                        chunk = self._mask(chunk, mask)
                    parts.append(chunk)
                    if first & 0x80:
                        return b"".join(parts).decode("utf-8")

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class CDP:
    def __init__(self, ws):
        self.ws = ws
        self.next_id = 0
        self.events = []

    def call(self, method, **params):
        self.next_id += 1
        mid = self.next_id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("id") == mid:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message.get("result", {})
            if "method" in message:
                self.events.append(message)

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", expression=expression,
                           returnByValue=True, awaitPromise=True)
        if result.get("exceptionDetails"):
            raise RuntimeError(str(result["exceptionDetails"])[:400])
        return result.get("result", {}).get("value")

    def wait_for(self, expression, timeout, label="", interval=1.0):
        end = time.time() + timeout
        while time.time() < end:
            try:
                if self.evaluate(expression):
                    return True
            except Exception:
                pass
            time.sleep(interval)
        raise TimeoutError(f"wait_for: {label or expression}")

    def screenshot(self, path):
        data = self.call("Page.captureScreenshot", format="png", captureBeyondViewport=True)["data"]
        Path(path).write_bytes(base64.b64decode(data))
        return Path(path).stat().st_size


def click_button(text):
    return ("(()=>{const b=[...document.querySelectorAll('button')]"
            f".find(x=>x.innerText.includes({json.dumps(text)}));if(!b)return false;b.click();return true;}})()")


def click_tab(text):
    return ("(()=>{const t=[...document.querySelectorAll('[role=tab],button[role=tab]')]"
            f".find(x=>x.innerText.includes({json.dumps(text)}));if(!t)return false;t.click();return true;}})()")


def wait_button(cdp, text, timeout=120):
    return cdp.wait_for(
        "!![...document.querySelectorAll('button')]"
        f".some(b=>b.innerText.includes({json.dumps(text)}))", timeout, f"button {text}")


def body_text(cdp, limit=6000):
    try:
        return (cdp.evaluate("document.body.innerText") or "")[:limit]
    except Exception:
        return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8513")
    parser.add_argument("--port", type=int, default=9333)
    parser.add_argument("--out", default="results/prototype/browser_check_v01")
    parser.add_argument("--chrome", default="")
    args = parser.parse_args()

    out = (ROOT / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    chrome = args.chrome or next((p for p in CHROME_CANDIDATES if Path(p).exists()), None)
    if not chrome:
        raise SystemExit("No Chrome/Edge binary found")
    profile = Path(tempfile.mkdtemp(prefix="u13_chrome_"))
    log = (out / "chrome_launch.log").open("w", encoding="utf-8")
    process = subprocess.Popen(
        [chrome, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
         "--disable-extensions", "--disable-sync", "--hide-scrollbars", "--window-size=1440,2600",
         f"--remote-debugging-port={args.port}", f"--user-data-dir={profile}", args.url],
        stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)

    checks = {"automation_level": "chrome-cdp", "url": args.url,
              "human_confirmation": False, "started_at": datetime.now(timezone.utc).isoformat(),
              "steps": {}}
    snapshot = []
    ws = None
    try:
        version = None
        for _ in range(60):
            try:
                version = http_json(f"http://127.0.0.1:{args.port}/json/version")
                break
            except Exception:
                time.sleep(1)
        if version is None:
            raise RuntimeError("Chrome DevTools endpoint never became ready")
        checks["chrome_version"] = version.get("Browser")
        targets = [t for t in http_json(f"http://127.0.0.1:{args.port}/json/list") if t.get("type") == "page"]
        if not targets:
            targets = [http_json(f"http://127.0.0.1:{args.port}/json/new?{args.url}", method="PUT")]
        ws = WebSocket(targets[0]["webSocketDebuggerUrl"])
        cdp = CDP(ws)
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")
        cdp.call("Log.enable")
        cdp.call("Page.navigate", url=args.url)

        def step(name, fn, shot=None):
            record = {"status": "passed"}
            try:
                fn(record)
            except Exception as exc:
                record.update(status="failed", error=repr(exc)[:500])
            if shot:
                try:
                    record["screenshot_bytes"] = cdp.screenshot(out / shot)
                except Exception as exc:
                    record["screenshot_error"] = repr(exc)[:200]
            record["body_text_excerpt"] = body_text(cdp, 1200)
            checks["steps"][name] = record
            snapshot.append(f"===== {name} :: {record['status']} =====\n{body_text(cdp)}\n")
            return record

        step("01_page_load", lambda r: (
            cdp.wait_for("document.body.innerText.includes('风光储')", 60, "title"),
            cdp.wait_for("document.querySelectorAll('[role=tab]').length>=4", 60, "tabs"),
            cdp.wait_for("document.querySelectorAll('[data-testid=stNumberInput] input').length>=9", 60, "number inputs"),
            wait_button(cdp, "计算调度", 60),
            r.update(page_title_ok=True,
                     number_inputs=cdp.evaluate("document.querySelectorAll('[data-testid=stNumberInput] input').length"),
                     sidebar_present=bool(cdp.evaluate("!!document.querySelector('[data-testid=stSidebar]')")),
                     tabs=cdp.evaluate("[...document.querySelectorAll('[role=tab]')].map(t=>t.innerText)"))),
            shot="01_page_load.png")

        step("02_milp_solve", lambda r: (
            wait_button(cdp, "计算调度", 60),
            cdp.evaluate(click_button("计算调度")),
            cdp.wait_for("document.querySelectorAll('[data-testid=stMetric]').length>=4", 240, "milp metrics"),
            cdp.wait_for("document.querySelectorAll('img[src^=\"data:image/png\"], [data-testid=stImage] img, canvas').length>=1", 120, "chart"),
            cdp.wait_for("document.querySelectorAll('[data-testid=stDataFrame]').length>=1", 120, "hourly table"),
            cdp.wait_for("!![...document.querySelectorAll('button')].some(b=>b.innerText.includes('加入方案对比'))", 60, "comparison button"),
            r.update(metrics=cdp.evaluate(
                         "[...document.querySelectorAll('[data-testid=stMetric]')].map(m=>m.innerText.replace(/\\n/g,'='))"),
                     status_line=cdp.evaluate("[...document.querySelectorAll('[data-testid=stAlert]')].map(a=>a.innerText).join(' | ')"),
                     charts=cdp.evaluate("document.querySelectorAll('img[src^=\"data:image/png\"]').length"),
                     download_labels=cdp.evaluate("[...document.querySelectorAll('button')].map(b=>b.innerText).filter(t=>t.includes('CSV')||t.includes('PNG'))"),
                     table_rows=cdp.evaluate("document.querySelectorAll('[data-testid=stDataFrame] tbody tr').length"))),
            shot="02_milp_result.png")

        step("03_add_comparison", lambda r: (
            wait_button(cdp, "加入方案对比", 60),
            cdp.evaluate(click_button("加入方案对比")),
            cdp.wait_for("document.body.innerText.includes('已加入当前会话对比')", 120, "comparison added"),
            cdp.evaluate(click_tab("03 / 方案对比")),
            cdp.wait_for("document.querySelectorAll('[data-testid=stDataFrame] tbody tr').length>=1", 120, "comparison table"),
            r.update(comparison_table_rows=cdp.evaluate("document.querySelectorAll('[data-testid=stDataFrame] tbody tr').length"),
                     download_labels=cdp.evaluate("[...document.querySelectorAll('button')].map(b=>b.innerText).filter(t=>t.includes('对比'))"))),
            shot="03_comparison.png")

        step("04_grid_101", lambda r: (
            cdp.evaluate(click_tab("02 / 容量寻优")),
            wait_button(cdp, "运行 101 点网格", 60),
            cdp.evaluate(click_button("运行 101 点网格")),
            cdp.wait_for("document.body.innerText.includes('网格最优')", 300, "grid best"),
            cdp.wait_for("document.querySelectorAll('[data-testid=stDataFrame] tbody tr').length>=1", 120, "grid table"),
            r.update(best_line=cdp.evaluate("(()=>{const t=document.body.innerText;const i=t.indexOf('网格最优');return t.slice(i,i+120);})()"),
                     table_rows=cdp.evaluate("document.querySelectorAll('[data-testid=stDataFrame] tbody tr').length"))),
            shot="04_grid_result.png")

        step("05_validation_error", lambda r: (
            cdp.evaluate("(()=>{const box=[...document.querySelectorAll('[data-testid=stNumberInput]')]"
                         ".find(b=>b.innerText.includes('能量容量'));if(!box)return 'no-box';"
                         "const i=box.querySelector('input');"
                         "const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
                         "s.call(i,'-1');i.dispatchEvent(new Event('input',{bubbles:true}));"
                         "i.dispatchEvent(new FocusEvent('focusout',{bubbles:true}));i.blur();return 'set';})()"),
            cdp.wait_for("document.body.innerText.includes('输入校验失败')", 120, "validation error"),
            r.update(error_text=cdp.evaluate("(()=>{const t=document.body.innerText;const i=t.indexOf('输入校验失败');return i<0?'':t.slice(i,i+160);})()"))),
            shot="05_negative_capacity.png")

        errors = [e for e in cdp.events
                  if e.get("method") in ("Runtime.exceptionThrown",) or
                  (e.get("method") == "Log.entryAdded" and e.get("params", {}).get("entry", {}).get("level") == "error")]
        checks["console_error_events"] = [json.dumps(e)[:300] for e in errors][:20]
        checks["console_error_count"] = len(errors)
        checks["finished_at"] = datetime.now(timezone.utc).isoformat()
        checks["screenshots"] = sorted(p.name for p in out.glob("*.png"))
        checks["failed_steps"] = [k for k, v in checks["steps"].items() if v["status"] != "passed"]
        checks["verdict"] = "browser_automation_passed" if not checks["failed_steps"] else "browser_automation_failed"
        (out / "browser_dom_text.txt").write_text("\n".join(snapshot), encoding="utf-8")
        (out / "browser_checks.json").write_text(
            json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({k: checks[k] for k in
                          ("verdict", "failed_steps", "console_error_count", "chrome_version")},
                         ensure_ascii=False))
        return 0 if not checks["failed_steps"] else 1
    finally:
        if ws:
            ws.close()
        process.terminate()
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()


if __name__ == "__main__":
    sys.exit(main())
