import json
import tempfile
import unittest
from pathlib import Path

from chatov.jobs import JobCancelled, JobRunner
from chatov.ollama import (OllamaApi, OllamaInstaller, OllamaLauncher, OllamaLocator, OllamaManager,
                           UrlDownloader)
from chatov.transport import ServiceError
from tests.fakes import FakeTransport, local_server
from tests.test_jobs import run_now

BASE = "http://127.0.0.1:11434"


class Ctx:
    """JobContext 대역."""

    def __init__(self, cancel_after=None):
        self.reports, self.cancel_after = [], cancel_after

    def report(self, message=None, completed=None, total=None):
        self.reports.append((message, completed, total))

    def check_cancel(self):
        if self.cancel_after is not None and len(self.reports) >= self.cancel_after:
            raise JobCancelled("취소했습니다.")


class OllamaApiTest(unittest.TestCase):
    def test_version_none_when_not_running(self):
        t = FakeTransport({("GET", BASE + "/api/version"): ServiceError("refused")})
        self.assertIsNone(OllamaApi(t).version())

    def test_version_and_models(self):
        t = FakeTransport({
            ("GET", BASE + "/api/version"): {"version": "0.17.1"},
            ("GET", BASE + "/api/tags"): {"models": [{"name": "phi4:14b", "size": 9}]},
        })
        api = OllamaApi(t)
        self.assertEqual(api.version(), "0.17.1")
        self.assertEqual(api.models(), [{"name": "phi4:14b", "size": 9}])

    def test_delete_sends_model_name(self):
        t = FakeTransport({("DELETE", BASE + "/api/delete"): {}})
        OllamaApi(t).delete("x:1b")
        self.assertEqual(t.requests[0][2], {"model": "x:1b"})

    def test_pull_sums_layer_progress_and_finishes_on_success(self):
        t = FakeTransport(streams={BASE + "/api/pull": [
            {"status": "pulling manifest"},
            {"status": "downloading", "digest": "a", "total": 100, "completed": 50},
            {"status": "downloading", "digest": "b", "total": 300, "completed": 30},
            {"status": "downloading", "digest": "a", "total": 100, "completed": 100},
            {"status": "success"},
        ]})
        ctx = Ctx()
        self.assertIn("설치 완료", OllamaApi(t).pull("m", ctx))
        self.assertEqual(ctx.reports[-1][1:], (130, 400))
        self.assertEqual(t.requests[0][2], {"model": "m", "stream": True})

    def test_pull_error_event_raises(self):
        t = FakeTransport(streams={BASE + "/api/pull": [{"error": "file does not exist"}]})
        with self.assertRaisesRegex(ServiceError, "file does not exist"):
            OllamaApi(t).pull("m", Ctx())

    def test_pull_cut_short_raises(self):
        t = FakeTransport(streams={BASE + "/api/pull": [{"status": "pulling manifest"}]})
        with self.assertRaisesRegex(ServiceError, "끊겼"):
            OllamaApi(t).pull("m", Ctx())

    def test_pull_stops_when_cancelled(self):
        t = FakeTransport(streams={BASE + "/api/pull": [{"status": "a"}, {"status": "b"}, {"status": "success"}]})
        with self.assertRaises(JobCancelled):
            OllamaApi(t).pull("m", Ctx(cancel_after=1))


class OllamaLocatorTest(unittest.TestCase):
    def test_prefers_path_then_default_install_dir(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d, "Programs", "Ollama", "ollama.exe")
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b"")
            self.assertEqual(OllamaLocator({"LOCALAPPDATA": d}, which=lambda n: None).exe(), exe)
            self.assertEqual(OllamaLocator({"LOCALAPPDATA": d}, which=lambda n: "C:/x/ollama.exe").exe(),
                             Path("C:/x/ollama.exe"))

    def test_nothing_installed(self):
        self.assertIsNone(OllamaLocator({}, which=lambda n: None).exe())


class FakeApi:
    base = BASE

    def __init__(self, running_after=0, models=()):
        self.calls, self.running_after, self._models, self.deleted = 0, running_after, list(models), []

    def version(self):
        self.calls += 1
        return "0.20" if self.calls > self.running_after else None

    def models(self):
        return self._models

    def delete(self, name):
        self.deleted.append(name)

    def pull(self, name, ctx):
        return f"{name} 설치 완료"


class FakeLocator:
    def __init__(self, exe=None):
        self._exe = exe

    def exe(self):
        return self._exe


class OllamaLauncherTest(unittest.TestCase):
    def test_already_running_does_nothing(self):
        popen = []
        msg = OllamaLauncher(FakeApi(), FakeLocator(), popen.append, sleep=lambda s: None).launch()
        self.assertIn("이미", msg)
        self.assertEqual(popen, [])

    def test_runs_headless_server_not_the_desktop_app(self):
        # 창(트레이 앱·채팅 창)을 띄우지 않고 API 서버만 백그라운드로 켠다
        popen = []
        launcher = OllamaLauncher(FakeApi(running_after=2), FakeLocator(exe=Path("o.exe")), popen.append,
                                  sleep=lambda s: None)
        self.assertIn("켜졌", launcher.launch())
        self.assertEqual(popen, [[str(Path("o.exe")), "serve"]])

    def test_not_installed_raises(self):
        with self.assertRaisesRegex(ServiceError, "설치"):
            OllamaLauncher(FakeApi(running_after=99), FakeLocator(), lambda c: None, sleep=lambda s: None).launch()

    def test_timeout_raises(self):
        launcher = OllamaLauncher(FakeApi(running_after=10 ** 6), FakeLocator(exe=Path("o")), lambda c: None,
                                  sleep=lambda s: None, timeout=1)
        with self.assertRaisesRegex(ServiceError, "응답이 없습니다"):
            launcher.launch()


class OllamaInstallerTest(unittest.TestCase):
    def test_downloads_runs_silent_setup_and_waits(self):
        with tempfile.TemporaryDirectory() as d:
            downloads, runs = [], []

            def download(url, dest, ctx):
                downloads.append((url, dest))
                Path(dest).write_bytes(b"exe")

            def run(cmd):
                runs.append(cmd)
                return 0

            launcher = OllamaLauncher(FakeApi(running_after=1), FakeLocator(exe=Path("o")), lambda c: None,
                                      sleep=lambda s: None)
            msg = OllamaInstaller(launcher, download, run, Path(d)).install(Ctx())
            self.assertIn("설치 완료", msg)
            self.assertEqual(downloads[0][0], OllamaInstaller.SETUP_URL)
            # 설치 진행 창도 띄우지 않는다
            self.assertEqual(runs[0][1:], ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"])

    def test_setup_failure_raises(self):
        with tempfile.TemporaryDirectory() as d:
            installer = OllamaInstaller(None, lambda u, dest, ctx: None, lambda cmd: 5, Path(d))
            with self.assertRaisesRegex(ServiceError, "코드 5"):
                installer.install(Ctx())


class UrlDownloaderTest(unittest.TestCase):
    def test_downloads_with_progress(self):
        payload = "x" * 5000
        with local_server({("GET", "/f"): lambda b: (200, payload)}) as base, tempfile.TemporaryDirectory() as d:
            ctx = Ctx()
            UrlDownloader(chunk=1000).download(base + "/f", Path(d, "f.bin"), ctx)
            self.assertEqual(Path(d, "f.bin").read_text(), payload)
            self.assertEqual(ctx.reports[-1][1], 5000)


class OllamaManagerTest(unittest.TestCase):
    def make(self, api=None):
        api = api or FakeApi(models=[{"name": "a", "size": 1}])
        launcher = OllamaLauncher(api, FakeLocator(exe=Path("o")), lambda c: None, sleep=lambda s: None)
        installer = OllamaInstaller(launcher, lambda u, d, c: None, lambda c: 0, Path("."))
        return OllamaManager(api, FakeLocator(exe=Path("o")), launcher, installer, JobRunner(run_now)), api

    def test_status_shape(self):
        mgr, _ = self.make()
        s = mgr.status()
        self.assertEqual((s["installed"], s["running"], s["version"]), (True, True, "0.20"))
        self.assertEqual(s["models"], [{"name": "a", "size": 1}])
        self.assertEqual(s["job"]["status"], "idle")

    def test_not_running_has_no_models(self):
        mgr, _ = self.make(FakeApi(running_after=10 ** 6, models=[{"name": "a", "size": 1}]))
        self.assertEqual(mgr.status()["models"], [])

    def test_pull_runs_as_job(self):
        mgr, _ = self.make()
        mgr.start_pull("m:1b")
        self.assertEqual(mgr.status()["job"]["message"], "m:1b 설치 완료")

    def test_pull_requires_name(self):
        mgr, _ = self.make()
        with self.assertRaises(ServiceError):
            mgr.start_pull("  ")

    def test_delete(self):
        mgr, api = self.make()
        mgr.delete("a")
        self.assertEqual(api.deleted, ["a"])

    def test_ensure_running_starts_ollama_in_background_for_its_address(self):
        popen = []
        api = FakeApi(running_after=1)
        launcher = OllamaLauncher(api, FakeLocator(exe=Path("o")), popen.append, sleep=lambda s: None)
        mgr = OllamaManager(api, FakeLocator(exe=Path("o")), launcher, None, JobRunner(run_now))
        mgr.ensure_running("http://127.0.0.1:11434/v1")
        self.assertEqual(popen, [[str(Path("o")), "serve"]])

    def test_ensure_running_accepts_localhost_alias(self):
        popen = []
        api = FakeApi(running_after=1)
        launcher = OllamaLauncher(api, FakeLocator(exe=Path("o")), popen.append, sleep=lambda s: None)
        OllamaManager(api, FakeLocator(exe=Path("o")), launcher, None, JobRunner(run_now)).ensure_running(
            "http://localhost:11434")
        self.assertEqual(len(popen), 1)

    def test_ensure_running_ignores_other_servers(self):
        popen = []
        api = FakeApi(running_after=10 ** 6)
        launcher = OllamaLauncher(api, FakeLocator(exe=Path("o")), popen.append, sleep=lambda s: None)
        mgr = OllamaManager(api, FakeLocator(exe=Path("o")), launcher, None, JobRunner(run_now))
        mgr.ensure_running("http://127.0.0.1:1234/v1")  # LM Studio
        self.assertEqual(popen, [])

    def test_ensure_running_without_install_is_quiet(self):
        # 설치가 안 돼 있으면 조용히 넘어가고, 연결 오류는 LLM 호출에서 알려준다
        api = FakeApi(running_after=10 ** 6)
        launcher = OllamaLauncher(api, FakeLocator(), lambda c: None, sleep=lambda s: None)
        OllamaManager(api, FakeLocator(), launcher, None, JobRunner(run_now)).ensure_running(
            "http://127.0.0.1:11434/v1")


if __name__ == "__main__":
    unittest.main()
