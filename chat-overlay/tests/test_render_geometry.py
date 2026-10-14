"""미리보기가 스티커 도형을 계산된 자리 · 크기에 정확히 그리는지 브라우저에서 확인한다.
픽셀 비교와 달리 글꼴 렌더링(안티앨리어싱) 차이에 흔들리지 않는다. 결과 영상 쪽은 ASS 작성기 테스트가 맡는다."""
import asyncio
import threading
import unittest
from http.server import ThreadingHTTPServer

import chat_app
from chatov.server import make_handler
from tests.cdp import BROWSER, HeadlessChrome, Page, websockets

# 템플릿마다: 스티커별로 (도형, 화면 요소의 실제 상자) 를 모은다
COLLECT = """(() => {
  const app = window.__chatApp, stage = document.querySelector('#stage').getBoundingClientRect();
  const k = stage.width / app.preview.source.resolution.width;
  const out = [];
  for (const [id, prims] of app.layer.lastPrims) {
    const group = document.querySelector(`.group[data-id="${id}"]`);
    if (!group) { out.push({ id, missing: true }); continue; }
    [...group.children].forEach((el, i) => {
      const b = el.getBoundingClientRect();
      out.push({ id, i, prim: prims[i], k, box: { l: b.left - stage.left, t: b.top - stage.top, r: b.right - stage.left,
        b: b.bottom - stage.top } });
    });
  }
  return out;
})()"""


@unittest.skipUnless(BROWSER and websockets, "Chrome · websockets 필요")
class StickerGeometryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(chat_app.build_app(), log=False))
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.chrome = HeadlessChrome(port=9343)
        cls.items = asyncio.run(cls._collect(f"http://127.0.0.1:{cls.srv.server_address[1]}/"))

    @classmethod
    def tearDownClass(cls):
        cls.chrome.close()
        cls.srv.shutdown()
        cls.srv.server_close()

    @classmethod
    async def _collect(cls, url):
        items = {}
        async with websockets.connect(cls.chrome.page_ws(), max_size=80_000_000) as ws:
            p = Page(ws)
            await p.cmd("Page.enable")
            await p.cmd("Page.navigate", url=url)
            await p.wait_for("document.body.dataset.ready === '1'")
            for key in ("panda", "excel", "afreeca"):
                await p.js("localStorage.clear()")
                await p.js(f"(() => {{ const s = document.querySelector('#templateSelect'); s.value = '{key}'; s.onchange(); }})()")
                await p.js("document.querySelector('#btnApplyTemplate').click()")
                await asyncio.sleep(0.4)
                items[key] = await p.js(COLLECT)
        return items

    def check(self, key):
        items = self.items[key]
        self.assertGreater(len(items), 20)
        rects = texts = 0
        for it in items:
            self.assertNotIn("missing", it, f"{key}: 화면에 그려지지 않은 스티커 {it['id']}")
            p, b, k = it["prim"], it["box"], it["k"]
            where = f"{key} {p['kind']} #{it['i']}"
            if p["kind"] in ("rect", "image"):
                rects += 1
                self.assertAlmostEqual(b["l"], (p["cx"] - p["w"] / 2) * k, delta=0.6, msg=where)
                self.assertAlmostEqual(b["t"], (p["cy"] - p["h"] / 2) * k, delta=0.6, msg=where)
                self.assertAlmostEqual(b["r"] - b["l"], p["w"] * k, delta=0.6, msg=where)
                self.assertAlmostEqual(b["b"] - b["t"], p["h"] * k, delta=0.6, msg=where)
            elif p["kind"] == "text" and p["outlineW"] == 0:
                texts += 1
                anchor = {"left": b["l"], "center": (b["l"] + b["r"]) / 2, "right": b["r"]}[p["align"]]
                self.assertAlmostEqual(anchor, p["x"] * k, delta=1.0, msg=where)
                self.assertAlmostEqual((b["t"] + b["b"]) / 2, p["y"] * k, delta=1.0, msg=where)
        self.assertGreater(rects, 3)
        self.assertGreater(texts, 10)

    def test_panda_template_prims_land_where_computed(self):
        self.check("panda")

    def test_excel_template_prims_land_where_computed(self):
        self.check("excel")

    def test_afreeca_template_prims_land_where_computed(self):
        self.check("afreeca")


if __name__ == "__main__":
    unittest.main()
