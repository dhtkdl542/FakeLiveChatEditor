"""꾸미기 탭: 템플릿 적용 · 스티커 끌어 옮기기 · 후원 알림 · 저장 복원을 실제 브라우저로 확인한다."""
import asyncio
import threading
import unittest
from http.server import ThreadingHTTPServer

import chat_app
from chatov.server import make_handler
from tests.cdp import BROWSER, HeadlessChrome, Page, websockets


@unittest.skipUnless(BROWSER and websockets, "Chrome · websockets 필요")
class DecoratingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(chat_app.build_app(), log=False))
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}/"
        cls.chrome = HeadlessChrome(port=9339)
        cls.results = asyncio.run(cls._drive())

    @classmethod
    def tearDownClass(cls):
        cls.chrome.close()
        cls.srv.shutdown()
        cls.srv.server_close()

    @classmethod
    async def _drive(cls):
        r = {}
        async with websockets.connect(cls.chrome.page_ws(), max_size=80_000_000) as ws:
            p = Page(ws)
            await p.cmd("Page.enable")
            await p.cmd("Page.navigate", url=cls.url)
            await p.wait_for("document.body.dataset.ready === '1'")
            await p.js("localStorage.clear()")
            await p.js("document.querySelector('[data-tab=deco]').click()")
            await p.js("document.querySelector('#btnApplyTemplate').click()")
            await asyncio.sleep(0.6)
            r["error"] = await p.js("document.body.dataset.error || null")
            r["prims"] = await p.js("document.querySelectorAll('#stickers .prim').length")
            r["text"] = await p.js("document.querySelector('#stickers').textContent")
            r["handle_ids"] = await p.js("[...document.querySelectorAll('#stickerHit .handle')].map(h => h.dataset.id)")
            r["sticker_ids"] = await p.js("window.__chatApp.stickers.items.filter(s => s.type !== 'alert').map(s => s.id)")
            r["list"] = await p.js("document.querySelectorAll('#stickerList .sticker-item').length")
            r["donationsOn"] = await p.js("document.querySelector('[data-field=donationsOn]').checked")

            # 첫 번째 핸들(배너)을 오른쪽으로 끌기
            box = await p.js("(() => { const h = document.querySelector('#stickerHit .handle'); const b = h.getBoundingClientRect();"
                             " return [b.left + b.width / 2, b.top + b.height / 2, h.dataset.id]; })()")
            r["before"] = await p.js(f"JSON.parse(localStorage.getItem('chatOverlay')).stickers[0].x")
            x, y, _ = box
            await p.cmd("Input.dispatchMouseEvent", type="mousePressed", x=x, y=y, button="left", clickCount=1)
            for i in range(1, 9):
                await p.cmd("Input.dispatchMouseEvent", type="mouseMoved", x=x + 12 * i, y=y, button="left", buttons=1)
            await p.cmd("Input.dispatchMouseEvent", type="mouseReleased", x=x + 96, y=y, button="left", clickCount=1)
            await asyncio.sleep(0.3)
            r["after"] = await p.js("JSON.parse(localStorage.getItem('chatOverlay')).stickers[0].x")
            r["selected"] = await p.js("document.querySelectorAll('#stickerHit .handle.selected').length")
            r["editor"] = await p.js("document.querySelectorAll('#stickerEditor [data-key]').length")

            # 첫 후원 1초 뒤로 가면 알림과 채팅창 후원 줄
            first = await p.js("window.__chatApp.preview.donations()[0].t")
            await p.js(f"window.__chatApp.preview.seek({first} + 1)")
            await asyncio.sleep(0.4)
            r["alert"] = await p.js("document.querySelector('#alerts').textContent")
            r["chat"] = await p.js("document.querySelector('#overlay').textContent")

            # 다시 열어도 스티커가 남아 있다
            await p.cmd("Page.reload")
            await p.wait_for("document.body.dataset.ready === '1'")
            await asyncio.sleep(0.4)
            r["reloaded"] = await p.js("document.querySelectorAll('#stickerList .sticker-item').length")

            # 엑셀방송 템플릿으로 바꾸기
            await p.js("document.querySelector('[data-tab=deco]').click()")
            await p.js("(() => { const s = document.querySelector('#templateSelect'); s.value = 'excel'; s.onchange(); })()")
            await p.js("document.querySelector('#btnApplyTemplate').click()")
            await asyncio.sleep(0.5)
            r["excel_error"] = await p.js("document.body.dataset.error || null")
            r["excel_text"] = await p.js("document.querySelector('#stickers').textContent")
            r["excel_unit"] = await p.js("document.querySelector('[data-field=donationUnit]').value")
            first = await p.js("window.__chatApp.preview.donations()[0].t")
            await p.js(f"window.__chatApp.preview.seek({first} + 1)")
            await asyncio.sleep(0.4)
            r["excel_alert"] = await p.js("document.querySelector('#alerts').textContent")
            table = await p.js("window.__chatApp.stickers.items.find(s => s.type === 'table').id")
            await p.js(f"window.__chatApp.stickers.select('{table}')")
            await asyncio.sleep(0.3)
            r["excel_editor"] = await p.js("[...document.querySelectorAll('#stickerEditor [data-key]')].map(e => e.dataset.key)")

            # 세 가지를 따로 고른다: 플랫폼 · 방송 템플릿 · 채팅창 템플릿
            r["selects"] = await p.js("['#platformSelect', '#templateSelect', '#chatTemplateSelect']"
                                      ".map(q => [...document.querySelector(q).options].map(o => o.value))")
            # 엑셀방송 그대로 플랫폼만 유튜브로: 단위 · 금액이 바뀌고 후원창이 슈퍼챗
            await p.js("(() => { const s = document.querySelector('#platformSelect'); s.value = 'youtube';"
                       " s.dispatchEvent(new Event('change', { bubbles: true })); })()")
            await asyncio.sleep(0.3)
            r["yt_unit"] = await p.js("document.querySelector('[data-field=donationUnit]').value")
            r["yt_amounts"] = await p.js("document.querySelector('[data-field=donationAmounts]').value")
            r["yt_table"] = await p.js("window.__chatApp.stickers.items.some(s => s.type === 'table')")
            first = await p.js("window.__chatApp.preview.donations()[0].t")
            await p.js(f"window.__chatApp.preview.seek({first} + 1)")
            await asyncio.sleep(0.4)
            r["yt_alert"] = await p.js("document.querySelector('#alerts').textContent")
            r["yt_chat"] = await p.js("document.querySelector('#overlay').textContent")
            # 사용자가 단위를 바꾸면 그 단위를 쓴다
            await p.js("(() => { const i = document.querySelector('[data-field=donationUnit]'); i.value = '$';"
                       " i.dispatchEvent(new Event('input', { bubbles: true })); })()")
            await asyncio.sleep(0.3)
            r["custom_alert"] = await p.js("document.querySelector('#alerts').textContent")
            # 채팅창 템플릿은 채팅 모양만 바꾼다
            await p.js("(() => { const s = document.querySelector('#chatTemplateSelect'); s.value = 'youtube'; })()")
            await p.js("document.querySelector('#btnApplyChatTemplate').click()")
            await asyncio.sleep(0.3)
            r["chat_icon"] = await p.js("document.querySelector('[data-field=icon]').value")
            r["chat_box"] = await p.js("document.querySelector('[data-field=box]').checked")
            r["chat_kept"] = await p.js("[window.__chatApp.stickers.items.length, document.querySelector('[data-field=platform]').value]")
            # 다시 열어도 플랫폼 · 단위가 남는다
            await p.cmd("Page.reload")
            await p.wait_for("document.body.dataset.ready === '1'")
            await asyncio.sleep(0.4)
            r["reload_platform"] = await p.js("[document.querySelector('#platformSelect').value,"
                                              " document.querySelector('[data-field=donationUnit]').value]")
        return r

    def test_template_applies_without_errors(self):
        self.assertIsNone(self.results["error"])
        self.assertTrue(self.results["donationsOn"])

    def test_template_stickers_are_drawn(self):
        self.assertGreater(self.results["prims"], 20)
        for word in ("오늘의 후원 순위", "오늘의 하트 목표", "방송시간", "별사"):
            self.assertIn(word, self.results["text"])

    def test_every_sticker_gets_a_handle_and_list_item(self):
        # 알림 자리는 알림이 떠 있거나 선택했을 때만 핸들이 생긴다 (시드에 따라 달라서 나머지만 확인)
        self.assertEqual(self.results["list"], 8)
        self.assertEqual(len(self.results["sticker_ids"]), 7)
        self.assertTrue(set(self.results["sticker_ids"]) <= set(self.results["handle_ids"]))

    def test_dragging_moves_the_sticker_and_selects_it(self):
        self.assertGreater(self.results["after"], self.results["before"] + 0.02)
        self.assertEqual(self.results["selected"], 1)
        self.assertGreater(self.results["editor"], 3)

    def test_donation_shows_alert_and_chat_row(self):
        self.assertIn("선물!", self.results["alert"])
        self.assertIn("♥ 하트", self.results["chat"])

    def test_stickers_survive_reload(self):
        self.assertEqual(self.results["reloaded"], 8)

    def test_excel_template_draws_spreadsheet_and_star_balloons(self):
        self.assertIsNone(self.results["excel_error"])
        for word in ("BJ 엑셀", "별풍점수", "기여도", "총합", "오늘의 별풍선", "야식대전", "줍줍"):
            self.assertIn(word, self.results["excel_text"])
        self.assertEqual(self.results["excel_unit"], "별풍선")
        self.assertIn("별풍선", self.results["excel_alert"])

    def test_three_separate_selectors(self):
        platforms, broadcast, chat = self.results["selects"]
        self.assertEqual(platforms, ["panda", "afreeca", "youtube"])
        self.assertEqual(broadcast, ["panda", "excel", "afreeca"])
        for key in ("outline", "panda", "afreeca", "youtube"):
            self.assertIn(key, chat)

    def test_youtube_platform_switches_unit_and_alert(self):
        self.assertEqual(self.results["yt_unit"], "₩")
        self.assertTrue(self.results["yt_amounts"].startswith("1000, 2000"))
        self.assertTrue(self.results["yt_table"], "방송 템플릿(엑셀 표)은 그대로")
        self.assertIn("₩", self.results["yt_alert"])
        self.assertNotIn("선물!", self.results["yt_alert"])
        self.assertIn("후원!", self.results["yt_chat"])

    def test_user_unit_wins_over_platform_default(self):
        self.assertIn("$", self.results["custom_alert"])

    def test_chat_template_changes_only_chat_look(self):
        self.assertEqual(self.results["chat_icon"], "circle")
        self.assertTrue(self.results["chat_box"])
        self.assertEqual(self.results["chat_kept"][1], "youtube")
        self.assertGreater(self.results["chat_kept"][0], 5)

    def test_platform_and_unit_survive_reload(self):
        self.assertEqual(self.results["reload_platform"], ["youtube", "$"])

    def test_excel_table_editor_has_headers_and_members(self):
        for key in ("headers", "entries", "highlightRow", "showTotal"):
            self.assertIn(key, self.results["excel_editor"])


if __name__ == "__main__":
    unittest.main()
