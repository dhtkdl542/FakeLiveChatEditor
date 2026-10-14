import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from chatov.files import StaticFiles, VideoRegistry
from chatov.media import RenderError, VideoInfo
from chatov.server import App, make_handler

JSON = {"Content-Type": "application/json", "Host": "127.0.0.1:8765"}


class FakeDialogs:
    def __init__(self, video="", save="", image=""):
        self.video, self.save, self.image, self.suggested = video, save, image, None

    def open_video(self):
        return self.video

    def open_image(self):
        return self.image

    def save_mp4(self, suggest):
        self.suggested = suggest
        return self.save


class FakeProbe:
    def __init__(self, info=None, error=None):
        self.info, self.error = info, error

    def probe(self, path):
        if self.error:
            raise self.error
        return self.info


class FakeRenderer:
    def __init__(self, error=None):
        self.calls, self.error = [], error

    def render(self, src, settings, dest=None):
        self.calls.append((src, settings, dest))
        if self.error:
            raise self.error
        return Path("C:/out/result.mp4")


class FakeLlm:
    def models(self, base):
        return ["m1"]

    def generate(self, payload):
        return {"msgs": ["ㅋㅋ"], "echo": payload["prompt"]}


class FakeOllama:
    def __init__(self):
        self.actions = []

    def status(self):
        return {"running": True, "actions": list(self.actions)}

    def start_install(self):
        self.actions.append("install")

    def start_launch(self):
        self.actions.append("start")

    def start_pull(self, name):
        self.actions.append(("pull", name))

    def delete(self, name):
        self.actions.append(("delete", name))

    def cancel(self):
        self.actions.append("cancel")

    def ensure_running(self, base):
        self.actions.append(("ensure", base))


def make_app(tmp, **kw):
    web = Path(tmp, "web")
    web.mkdir(exist_ok=True)
    (web / "index.html").write_text("<html>앱</html>", encoding="utf-8")
    deps = dict(static=StaticFiles(web), videos=VideoRegistry(token_factory=lambda: "tok"),
                images=VideoRegistry(token_factory=lambda: "tok", prefix="/media/"),
                dialogs=FakeDialogs(), probe=FakeProbe(VideoInfo(1920, 1080, 12.0)), renderer=FakeRenderer(),
                llm=FakeLlm(), ollama=FakeOllama())
    deps.update(kw)
    return App(**deps), deps


def body_json(resp):
    return json.loads(resp.body.decode("utf-8"))


class AppTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def post(self, app, path, payload=None, headers=JSON):
        return app.post(path, headers, json.dumps(payload or {}).encode("utf-8"))

    def test_pick_video_registers_and_probes(self):
        app, _ = make_app(self.tmp.name, dialogs=FakeDialogs(video="C:/v/clip.mp4"))
        data = body_json(self.post(app, "/api/pick-video"))
        self.assertEqual(data, {"ok": True, "path": "C:/v/clip.mp4", "url": "/video/tok.mp4",
                                "width": 1920, "height": 1080, "duration": 12.0})

    def test_pick_video_without_ffprobe_still_gives_url(self):
        app, _ = make_app(self.tmp.name, dialogs=FakeDialogs(video="C:/v/a.mkv"), probe=FakeProbe(error=RuntimeError()))
        data = body_json(self.post(app, "/api/pick-video"))
        self.assertEqual((data["url"], "duration" in data), ("/video/tok.mkv", False))

    def test_pick_video_cancelled(self):
        app, _ = make_app(self.tmp.name)
        self.assertEqual(body_json(self.post(app, "/api/pick-video")), {"ok": True, "path": ""})

    def test_pick_save_passes_suggestion(self):
        dialogs = FakeDialogs(save="C:/o.mp4")
        app, _ = make_app(self.tmp.name, dialogs=dialogs)
        self.assertEqual(body_json(self.post(app, "/api/pick-save", {"suggest": "a_chat.mp4"}))["path"], "C:/o.mp4")
        self.assertEqual(dialogs.suggested, "a_chat.mp4")

    def test_render(self):
        app, deps = make_app(self.tmp.name)
        data = body_json(self.post(app, "/api/render", {"videoPath": "C:/v.mp4", "outputPath": "C:/o.mp4",
                                                         "settings": {"NICKS": ["a"]}}))
        self.assertEqual(data["output"], str(Path("C:/out/result.mp4")))
        src, settings, dest = deps["renderer"].calls[0]
        self.assertEqual((src, settings, dest), (Path("C:/v.mp4"), {"NICKS": ["a"]}, Path("C:/o.mp4")))

    def test_render_without_video_is_bad_request(self):
        app, _ = make_app(self.tmp.name)
        self.assertEqual(self.post(app, "/api/render", {"settings": {}}).status, 400)

    def test_errors_become_500_with_message(self):
        app, _ = make_app(self.tmp.name, renderer=FakeRenderer(error=RenderError("ffmpeg 터짐")))
        resp = self.post(app, "/api/render", {"videoPath": "C:/v.mp4", "settings": {}})
        self.assertEqual(resp.status, 500)
        self.assertIn("ffmpeg 터짐", resp.body.decode("utf-8"))

    def test_llm_routes(self):
        app, _ = make_app(self.tmp.name)
        self.assertEqual(body_json(self.post(app, "/api/llm-models", {"base": "x"}))["models"], ["m1"])
        self.assertEqual(body_json(self.post(app, "/api/generate", {"prompt": "먹방"}))["echo"], "먹방")

    def test_llm_routes_wake_ollama_in_background_first(self):
        app, deps = make_app(self.tmp.name)
        self.post(app, "/api/llm-models", {"base": "http://127.0.0.1:11434/v1"})
        self.post(app, "/api/generate", {"base": "http://127.0.0.1:11434/v1", "prompt": "p"})
        self.assertEqual(deps["ollama"].actions, [("ensure", "http://127.0.0.1:11434/v1")] * 2)

    def test_ollama_routes(self):
        app, deps = make_app(self.tmp.name)
        for action, payload in [("install", {}), ("start", {}), ("pull", {"model": "m"}),
                                ("delete", {"model": "m"}), ("cancel", {})]:
            self.post(app, f"/api/ollama/{action}", payload)
        data = body_json(self.post(app, "/api/ollama/status"))
        self.assertEqual(data["actions"], ["install", "start", ["pull", "m"], ["delete", "m"], "cancel"])

    def test_pick_image_gives_media_url(self):
        app, _ = make_app(self.tmp.name, dialogs=FakeDialogs(image="C:/s/heart.png"))
        data = body_json(self.post(app, "/api/pick-image"))
        self.assertEqual((data["path"], data["url"]), ("C:/s/heart.png", "/media/tok.png"))
        self.assertEqual(body_json(self.post(make_app(self.tmp.name)[0], "/api/pick-image")), {"ok": True, "path": ""})

    def test_register_image_again_after_restart(self):
        png = Path(self.tmp.name, "s.png")
        png.write_bytes(b"png")
        app, _ = make_app(self.tmp.name)
        self.assertEqual(body_json(self.post(app, "/api/register-image", {"path": str(png)}))["url"], "/media/tok.png")
        self.assertEqual(app.get("/media/tok.png", {}).status, 200)

    def test_register_image_refuses_non_images_and_missing_files(self):
        txt = Path(self.tmp.name, "secret.txt")
        txt.write_text("secret")
        app, _ = make_app(self.tmp.name)
        self.assertEqual(self.post(app, "/api/register-image", {"path": str(txt)}).status, 400)
        self.assertEqual(self.post(app, "/api/register-image", {"path": "C:/없음.png"}).status, 400)

    def test_unknown_route_404(self):
        app, _ = make_app(self.tmp.name)
        self.assertEqual(self.post(app, "/api/nope").status, 404)
        self.assertEqual(self.post(app, "/api/ollama/explode").status, 404)

    def test_post_requires_json_content_type(self):
        # 다른 사이트가 form 으로 몰래 보내는 요청(CSRF)을 막는다
        app, _ = make_app(self.tmp.name)
        resp = self.post(app, "/api/ollama/install", headers={"Content-Type": "text/plain", "Host": "127.0.0.1:8765"})
        self.assertEqual(resp.status, 415)

    def test_cross_site_requests_rejected(self):
        app, deps = make_app(self.tmp.name)
        evil = {**JSON, "Origin": "https://evil.example"}
        self.assertEqual(self.post(app, "/api/ollama/install", headers=evil).status, 403)
        self.assertEqual(deps["ollama"].actions, [])
        same = {**JSON, "Origin": "http://127.0.0.1:8765"}
        self.assertEqual(self.post(app, "/api/ollama/status", headers=same).status, 200)

    def test_bad_json_is_400(self):
        app, _ = make_app(self.tmp.name)
        self.assertEqual(app.post("/api/render", JSON, b"{nope").status, 400)

    def test_get_static_and_404(self):
        app, _ = make_app(self.tmp.name)
        resp = app.get("/", {})
        self.assertEqual((resp.status, resp.ctype), (200, "text/html; charset=utf-8"))
        self.assertEqual(app.get("/missing.js", {}).status, 404)


class HttpIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.video = Path(self.tmp.name, "clip.mp4")
        self.video.write_bytes(bytes(range(256)) * 4)
        app, self.deps = make_app(self.tmp.name, dialogs=FakeDialogs(video=str(self.video)))
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()

    def request(self, path, data=None, headers=None):
        req = urllib.request.Request(self.base + path, data=data, headers=headers or {})
        try:
            return urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as e:
            return e

    def test_index_served_without_cors_header(self):
        resp = self.request("/")
        self.assertEqual(resp.status, 200)
        self.assertIn("앱", resp.read().decode("utf-8"))
        self.assertIsNone(resp.headers.get("Access-Control-Allow-Origin"))

    def test_picked_video_streams_with_ranges(self):
        resp = self.request("/api/pick-video", b"{}", {"Content-Type": "application/json"})
        url = json.loads(resp.read())["url"]
        whole = self.request(url)
        self.assertEqual((whole.status, whole.headers["Accept-Ranges"]), (200, "bytes"))
        self.assertEqual(len(whole.read()), 1024)
        part = self.request(url, headers={"Range": "bytes=10-19"})
        self.assertEqual(part.status, 206)
        self.assertEqual(part.headers["Content-Range"], "bytes 10-19/1024")
        self.assertEqual(part.read(), bytes(range(10, 20)))
        self.assertEqual(self.request(url, headers={"Range": "bytes=5000-"}).status, 416)

    def test_unregistered_video_404(self):
        self.assertEqual(self.request("/video/whatever.mp4").status, 404)

    def test_read_only_server_rejects_api_posts(self):
        # 앱 창 모드에서는 API 를 브리지로만 부르고, HTTP 로는 화면 파일과 영상만 내보낸다
        srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(make_app(self.tmp.name)[0], allow_post=False))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/api/ollama/install", data=b"{}",
                                         headers={"Content-Type": "application/json"})
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req, timeout=5)
            self.assertEqual(ctx.exception.code, 405)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_post_round_trip(self):
        resp = self.request("/api/llm-models", b'{"base":"x"}', {"Content-Type": "application/json"})
        self.assertEqual(json.loads(resp.read())["models"], ["m1"])


if __name__ == "__main__":
    unittest.main()
