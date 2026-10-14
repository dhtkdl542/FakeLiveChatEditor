"""미리보기(브라우저)와 결과 영상(ffmpeg + libass)의 채팅이 같은 자리에 같은 모양으로 그려지는지 확인한다.

같은 시점의 미리보기 화면과 결과 영상 프레임에서 '배경이 아닌 픽셀' 마스크를 뽑아 두 가지를 잰다.
  - 면적: 2px 여유를 두고 서로 얼마나 덮는지 (같으면 0.99 이상, 박스가 7px 밀리면 0.976)
  - 윤곽선: 미리보기 가장자리가 영상 가장자리 2px 안에 있는 비율 (같으면 0.95 이상, 7px 밀리면 0.87)
느린 테스트(프리셋당 20초 안팎)라 Chrome · ffmpeg · websockets 가 없으면 건너뛴다."""
import asyncio
from collections import Counter
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

import chat_app
from chatov.server import make_handler
from tests.cdp import BROWSER, HeadlessChrome, Page, websockets

W, H = 1280, 720
CHAT_CROP = (640, 400, 640, 320)  # 오른쪽 아래 (w, h, x, y)
FULL = (W, H, 0, 0)
ALERT_CROP = (600, 240, 240, 480)  # 아래 가운데 후원창 자리 (w, h, x, y)
AT = 6.0
AREA_THRESHOLD = 0.985
EDGE_THRESHOLD = 0.92


def mask(png: Path, scale: bool, crop=CHAT_CROP):
    vf = (f"scale={W}:{H}," if scale else "") + "crop={}:{}:{}:{},format=rgb24".format(*crop)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(png), "-vf", vf, "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    w = crop[0]
    # 배경색 = 가장 많이 나오는 색 (구석은 미리보기 화면의 둥근 모서리라 배경이 아닐 수 있다)
    bg = Counter(raw[i:i + 3] for i in range(0, len(raw), 3 * 97)).most_common(1)[0][0]
    return {(i // 3 % w, i // 3 // w) for i in range(0, len(raw), 3)
            if abs(raw[i] - bg[0]) + abs(raw[i + 1] - bg[1]) + abs(raw[i + 2] - bg[2]) > 60}


def closed(m: set, r: int = 1) -> set:
    """작은 구멍 메우기(팽창 → 침식). 아주 작은 글씨는 브라우저와 libass 의 진하기가 달라서
    글자 가장자리 픽셀이 마스크에 구멍을 내는데, 그건 위치 차이가 아니라 렌더링 차이다."""
    near = [(dx, dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1)]
    grown = {(x + dx, y + dy) for x, y in m for dx, dy in near}
    return {(x, y) for x, y in grown if all((x + dx, y + dy) in grown for dx, dy in near)}


def edges(m: set) -> set:
    return {(x, y) for x, y in m if any((x + dx, y + dy) not in m for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))}


def covered(a: set, b: set, r: int = 2) -> float:
    grown = {(x + dx, y + dy) for x, y in b for dx in range(-r, r + 1) for dy in range(-r, r + 1)}
    return len(a & grown) / len(a) if a else 1.0


class FixedDialogs:
    def __init__(self, src, dest):
        self.src, self.dest = src, dest

    def open_video(self):
        return str(self.src)

    def save_mp4(self, suggest):
        return str(self.dest)

    def open_image(self):
        return ""


@unittest.skipUnless(BROWSER and websockets and shutil.which("ffmpeg"), "Chrome · ffmpeg · websockets 필요")
class PreviewMatchesRenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.src = cls.dir / "clip.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x6a7f8f:s={W}x{H}:d=10:r=30",
                        "-pix_fmt", "yuv420p", str(cls.src)], check=True)
        cls.long_src = cls.dir / "long.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x6a7f8f:s={W}x{H}:d=30:r=30",
                        "-pix_fmt", "yuv420p", str(cls.long_src)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def compare(self, name: str, setup_js: str, at_js: str = str(AT), crop=CHAT_CROP, src=None):
        """setup_js 로 화면을 꾸미고, at_js 시각의 미리보기와 결과 영상 프레임을 비교한다."""
        dest = self.dir / f"out_{name}.mp4"
        app = chat_app.build_app(dialogs=FixedDialogs(src or self.src, dest))
        srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app, log=False))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        chrome = HeadlessChrome()
        preview = self.dir / f"preview_{name}.png"
        try:
            at = asyncio.run(self._drive(chrome, f"http://127.0.0.1:{srv.server_address[1]}/", setup_js, at_js, preview))
        finally:
            chrome.close()
            srv.shutdown()
            srv.server_close()
        frame = self.dir / f"frame_{name}.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(at), "-i", str(dest), "-frames:v", "1", str(frame)],
                       check=True)
        a, b = mask(preview, scale=True, crop=crop), mask(frame, scale=False, crop=crop)
        self.assertGreater(len(b), 2000, "결과 영상에 채팅이 거의 안 보입니다")
        self.assertGreaterEqual(covered(a, b), AREA_THRESHOLD, "미리보기에만 있는 그림이 많습니다")
        self.assertGreaterEqual(covered(b, a), AREA_THRESHOLD, "결과 영상에만 있는 그림이 많습니다")
        # 테두리 글자는 원래 윤곽선이, 아주 작은 글씨는 구멍을 메운 윤곽선이 렌더링 차이에 덜 흔들린다
        edge = max(covered(edges(a), edges(b)), covered(edges(closed(a)), edges(closed(b))))
        self.assertGreaterEqual(edge, EDGE_THRESHOLD, "윤곽선 위치가 어긋났습니다")

    async def _drive(self, chrome, url, setup_js, at_js, out_png):
        async with websockets.connect(chrome.page_ws(), max_size=80_000_000) as ws:
            page = Page(ws)
            await page.cmd("Page.enable")
            await page.cmd("Page.navigate", url=url)
            await page.wait_for("document.body.dataset.ready === '1'")
            await page.js("document.querySelector('#btnPick').click()")
            await page.wait_for(f"document.querySelector('#videoMeta').textContent.includes('{W}×{H}')")
            # 같은 장면을 비교하도록 채팅 · 후원 시드와 출렁임 패턴을 고정한다
            await page.js("window.__chatApp.preview.seed = 20261002; window.__chatApp.preview.phases = [0.4, 1.7, 2.9];")
            await page.js(setup_js)
            await asyncio.sleep(0.4)
            at = await page.js(at_js)
            await page.js(f"(() => {{ const v = document.querySelector('#video'); v.pause(); v.currentTime = {at}; }})()")
            await asyncio.sleep(1.2)
            out_png.write_bytes(await page.screenshot_element("#stage", W))
            await page.js("document.querySelector('#btnRender').click()")
            await page.wait_for("/저장 완료|실패/.test(document.querySelector('#exportStatus').textContent)", 180)
            status = await page.js("document.querySelector('#exportStatus').textContent")
            self.assertIn("저장 완료", status)
            return at

    def test_box_with_icon(self):
        self.compare("box", "document.querySelectorAll('#presets button')[2].click()")  # 박스 + 닉 색 아이콘

    def test_outline_with_heart_icon(self):
        self.compare("heart", "document.querySelectorAll('#presets button')[3].click()")  # 하트 + 굵은 닉

    def test_panda_template_with_stickers_and_donation_alert(self):
        # 스티커가 화면 전체에 있으니 전체를 비교하고, 첫 후원 알림이 다 튀어나온 뒤 시점으로 잡는다
        self.compare("panda", "localStorage.clear(); document.querySelector('#btnApplyTemplate').click()",
                     "(() => { const d = window.__chatApp.preview.donations(); return d.length ? d[0].t + 1.2 : 8; })()",
                     crop=FULL, src=self.long_src)

    def test_afreeca_template_with_donation_cards_and_mvp(self):
        self.compare("afreeca", "localStorage.clear(); (() => { const s = document.querySelector('#templateSelect');"
                                " s.value = 'afreeca'; s.onchange(); })(); document.querySelector('#btnApplyTemplate').click()",
                     "(() => { const d = window.__chatApp.preview.donations(); return d.length ? d[0].t + 1.2 : 8; })()",
                     crop=FULL, src=self.long_src)

    def test_excel_template_with_spreadsheet_and_star_balloon_alert(self):
        self.compare("excel", "localStorage.clear(); (() => { const s = document.querySelector('#templateSelect');"
                              " s.value = 'excel'; s.onchange(); })(); document.querySelector('#btnApplyTemplate').click()",
                     "(() => { const d = window.__chatApp.preview.donations(); return d.length ? d[0].t + 1.2 : 8; })()",
                     crop=FULL, src=self.long_src)

    # 메시지가 붙은 후원 중 앞 알림과 겹치지 않는 것 (줄 서기 없이 바로 뜨는 것) 1.2초 뒤
    LONE_MSG_DONATION = ("(() => { const d = window.__chatApp.preview.donations();"
                         " const i = d.findIndex((x, i) => x.msg && (i === 0 || x.t - d[i - 1].t > 5));"
                         " return i >= 0 ? d[i].t + 1.2 : d.length ? d[0].t + 1.2 : 8; })()")

    def test_excel_template_on_youtube_shows_super_chat(self):
        self.compare("excel_youtube", "localStorage.clear(); (() => { const s = document.querySelector('#templateSelect');"
                                      " s.value = 'excel'; s.onchange(); })(); document.querySelector('#btnApplyTemplate').click();"
                                      " (() => { const s = document.querySelector('#platformSelect'); s.value = 'youtube';"
                                      " s.dispatchEvent(new Event('change', { bubbles: true })); })();"
                                      " (() => { const m = document.querySelector('[data-field=donationMsgChance]'); m.value = '100';"
                                      " m.dispatchEvent(new Event('input', { bubbles: true })); })()",  # 메시지 칸까지 있는 슈퍼챗
                     self.LONE_MSG_DONATION, crop=ALERT_CROP, src=self.long_src)

    def test_afreeca_platform_alert_card(self):
        self.compare("afreeca_alert", "localStorage.clear(); (() => { const s = document.querySelector('#templateSelect');"
                                      " s.value = 'afreeca'; s.onchange(); })(); document.querySelector('#btnApplyTemplate').click()",
                     self.LONE_MSG_DONATION, crop=ALERT_CROP, src=self.long_src)

    def test_youtube_chat_template(self):
        self.compare("chat_youtube", "(() => { document.querySelector('#chatTemplateSelect').value = 'youtube';"
                                     " document.querySelector('#btnApplyChatTemplate').click(); })()")


if __name__ == "__main__":
    unittest.main()
