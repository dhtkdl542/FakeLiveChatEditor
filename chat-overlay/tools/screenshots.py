"""README 용 스크린샷을 실제 앱 화면(헤드리스 Chrome)과 실제 결과 영상에서 찍는다.

    python tools/screenshots.py            → ../docs/screenshots/*.png

Chrome(또는 Edge) · ffmpeg · websockets 가 필요하다. 채팅 · 후원 시드를 고정해서 매번 같은 장면이 나온다."""
import asyncio
import base64
import json
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import chat_app  # noqa: E402
from chatov.server import make_handler  # noqa: E402
from tests.cdp import HeadlessChrome, Page, websockets  # noqa: E402

OUT = HERE.parent.parent / "docs" / "screenshots"
W, H = 1280, 720
SEED = "window.__chatApp.preview.seed = 20261002; window.__chatApp.preview.phases = [0.4, 1.7, 2.9];"
# README 에 싣는 화면이라 예시 닉네임 · 대사는 무난한 것으로 바꿔서 찍는다
SAMPLE_NICKS = ["별빛여우", "감자칩", "새벽산책", "코코넛", "구름빵", "오늘도출근", "노래방왕", "초코우유", "고양이집사", "라면한그릇"]
SAMPLE_MSGS = ["ㅋㅋㅋㅋㅋ", "오늘 텐션 좋다", "이 노래 뭐예요?", "와 미쳤다", "방금 거 다시 보여줘요", "배고프다", "화이팅!!",
               "이게 되네 ㅋㅋ", "첫 방송부터 봤어요", "실화냐"]
SAMPLE_LINES = ("(() => { const f = (k, v) => { const e = document.querySelector(`[data-field=${k}]`); e.value = v;"
                " e.dispatchEvent(new Event('input', { bubbles: true })); };"
                f" f('nicks', {json.dumps(chr(10).join(SAMPLE_NICKS), ensure_ascii=False)});"
                f" f('msgs', {json.dumps(chr(10).join(SAMPLE_MSGS), ensure_ascii=False)}); return true; }})()")
# 메시지가 붙은 후원 중 앞 알림과 겹치지 않는 것이 다 튀어나온 시점
LONE_DONATION = ("(() => { const d = window.__chatApp.preview.donations();"
                 " const i = d.findIndex((x, i) => x.msg && (i === 0 || x.t - d[i - 1].t > 5));"
                 " return i >= 0 ? d[i].t + 1.2 : d.length ? d[0].t + 1.2 : 8; })()")


class FixedDialogs:
    def __init__(self, src, dest):
        self.src, self.dest = src, dest

    def open_video(self):
        return str(self.src)

    def save_mp4(self, suggest):
        return str(self.dest)

    def open_image(self):
        return ""


def apply_template(key):
    return (f"(() => {{ const s = document.querySelector('#templateSelect'); s.value = '{key}'; s.onchange();"
            " document.querySelector('#btnApplyTemplate').click(); })();")


def set_platform(key):
    return (f"(() => {{ const s = document.querySelector('#platformSelect'); s.value = '{key}';"
            " s.dispatchEvent(new Event('change', { bubbles: true })); })();")


def chat_template(key):
    return (f"(() => {{ document.querySelector('#chatTemplateSelect').value = '{key}';"
            " document.querySelector('#btnApplyChatTemplate').click(); })();")


MSGS_100 = ("(() => { const m = document.querySelector('[data-field=donationMsgChance]'); m.value = '100';"
            " m.dispatchEvent(new Event('input', { bubbles: true })); })();")


class Shooter:
    def __init__(self, clip: Path, work: Path):
        self.clip, self.work = clip, work

    async def scene(self, setup_js, at_js=LONE_DONATION, tab="deco", render_to=None):
        """앱을 새로 열어 setup_js 로 꾸미고 at_js 시점에서 멈춘 Page 를 돌려준다(async with)."""
        dest = render_to or self.work / "unused.mp4"
        app = chat_app.build_app(dialogs=FixedDialogs(self.clip, dest))
        srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app, log=False))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return _Scene(self, srv, setup_js, at_js, tab)


class _Scene:
    def __init__(self, shooter, srv, setup_js, at_js, tab):
        self.shooter, self.srv, self.setup_js, self.at_js, self.tab = shooter, srv, setup_js, at_js, tab

    async def __aenter__(self):
        self.chrome = HeadlessChrome(port=9351, size=(1600, 1000))
        self.ws = await websockets.connect(self.chrome.page_ws(), max_size=80_000_000)
        p = Page(self.ws)
        await p.cmd("Page.enable")
        await p.cmd("Emulation.setDeviceMetricsOverride", width=1600, height=1000, deviceScaleFactor=1, mobile=False)
        await p.cmd("Page.navigate", url=f"http://127.0.0.1:{self.srv.server_address[1]}/")
        await p.wait_for("document.body.dataset.ready === '1'")
        await p.js("localStorage.clear()")
        await p.js("document.querySelector('#btnPick').click()")
        await p.wait_for(f"document.querySelector('#videoMeta').textContent.includes('{W}×{H}')")
        await p.js(SEED)
        assert await p.js(SAMPLE_LINES), "예시 대사를 넣지 못했습니다"
        await p.js(f"document.querySelector('[data-tab={self.tab}]').click()")
        await p.js(self.setup_js)
        await asyncio.sleep(0.4)
        at = await p.js(self.at_js)
        await p.js(f"(() => {{ const v = document.querySelector('#video'); v.pause(); v.currentTime = {at}; }})()")
        await asyncio.sleep(1.2)
        self.page = p
        return p

    async def __aexit__(self, *exc):
        await self.ws.close()
        self.chrome.close()
        self.srv.shutdown()
        self.srv.server_close()


async def viewport(p: Page) -> bytes:
    return base64.b64decode((await p.cmd("Page.captureScreenshot", format="png"))["data"])


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="shots_") as tmp:
        work = Path(tmp)
        clip = work / "clip.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                        f"gradients=s={W}x{H}:d=30:r=30:c0=0x2b3a55:c1=0x5a4a78:c2=0x1f5f6b:speed=0.004",
                        "-pix_fmt", "yuv420p", str(clip)], check=True)
        shooter = Shooter(clip, work)
        shots = {}

        async with await shooter.scene(apply_template("panda") + chat_template("panda")) as p:
            shots["app.png"] = await viewport(p)
        async with await shooter.scene(apply_template("panda"), tab="timing") as p:
            await p.js("(() => { const a = window.__chatApp.preview; a.sections.add(6, 11, 3); a.sections.add(17, 22, 0.4);"
                       " a.invalidate(); })()")
            await asyncio.sleep(0.5)
            shots["timeline.png"] = await p.screenshot_element("#timeline", 1100)
        async with await shooter.scene(apply_template("afreeca") + chat_template("afreeca") + MSGS_100) as p:
            shots["afreeca.png"] = await p.screenshot_element("#stage", W)
        result = work / "excel_youtube.mp4"
        async with await shooter.scene(apply_template("excel") + set_platform("youtube") + chat_template("youtube")
                                       + MSGS_100, render_to=result) as p:
            shots["excel-youtube.png"] = await p.screenshot_element("#stage", W)
            shots["templates.png"] = await p.screenshot_element("[data-panel=deco] .card", 520)
            at = await p.js("document.querySelector('#video').currentTime")
            await p.js("document.querySelector('#btnRender').click()")
            await p.wait_for("/저장 완료|실패/.test(document.querySelector('#exportStatus').textContent)", 180)
        frame = OUT / "result-frame.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(at), "-i", str(result), "-frames:v", "1", str(frame)],
                       check=True)
        async with await shooter.scene(chat_template("pill") + apply_template("panda"), tab="style") as p:
            shots["chat-pill.png"] = await p.screenshot_element("#stage", W)
            await p.js("document.querySelector('#badgeCard').scrollIntoView()")
            await asyncio.sleep(0.3)
            shots["badges.png"] = await p.screenshot_element("#badgeCard", 520)
        async with await shooter.scene("", at_js="0", tab="ai") as p:
            shots["ai.png"] = await p.screenshot_element("[data-panel=ai] .card", 520)

        for name, data in shots.items():
            (OUT / name).write_bytes(data)
        print("저장:", ", ".join(sorted([*shots, frame.name])), "→", OUT)


if __name__ == "__main__":
    asyncio.run(main())
