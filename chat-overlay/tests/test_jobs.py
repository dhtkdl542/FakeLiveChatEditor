import unittest

from chatov.jobs import JobCancelled, JobRunner


def run_now(fn):
    fn()


class Deferred:
    """나중에 실행하는 spawn 대역. 작업이 '실행 중' 인 상태를 만들 때 쓴다."""

    def __init__(self):
        self.pending = []

    def __call__(self, fn):
        self.pending.append(fn)

    def finish(self):
        while self.pending:
            self.pending.pop(0)()


class JobRunnerTest(unittest.TestCase):
    def test_idle_at_start(self):
        self.assertEqual(JobRunner(run_now).snapshot()["status"], "idle")

    def test_successful_job_reports_done_with_message(self):
        jobs = JobRunner(run_now)
        jobs.start("pull", lambda ctx: "다 받았습니다")
        self.assertEqual(jobs.snapshot(), {"kind": "pull", "status": "done", "message": "다 받았습니다",
                                           "completed": 0, "total": 0})

    def test_progress_is_visible_while_running(self):
        spawn = Deferred()
        jobs = JobRunner(spawn)
        seen = {}

        def work(ctx):
            ctx.report(message="받는 중", completed=5, total=10)
            seen.update(jobs.snapshot())
            return "끝"

        jobs.start("pull", work)
        self.assertEqual(jobs.snapshot()["status"], "running")
        spawn.finish()
        self.assertEqual((seen["message"], seen["completed"], seen["total"]), ("받는 중", 5, 10))

    def test_failure_reports_error(self):
        jobs = JobRunner(run_now)

        def boom(ctx):
            raise RuntimeError("망함")

        jobs.start("install", boom)
        self.assertEqual((jobs.snapshot()["status"], jobs.snapshot()["message"]), ("error", "망함"))

    def test_second_job_rejected_while_busy(self):
        spawn = Deferred()
        jobs = JobRunner(spawn)
        jobs.start("a", lambda ctx: "")
        with self.assertRaises(RuntimeError):
            jobs.start("b", lambda ctx: "")
        spawn.finish()
        jobs.start("b", lambda ctx: "")  # 끝나면 다시 받을 수 있음

    def test_cancel_is_seen_by_job(self):
        spawn = Deferred()
        jobs = JobRunner(spawn)

        def work(ctx):
            ctx.check_cancel()
            return "안 옴"

        jobs.start("pull", work)
        jobs.cancel()
        spawn.finish()
        self.assertEqual(jobs.snapshot()["status"], "error")
        self.assertIn("취소", jobs.snapshot()["message"])

    def test_cancelled_error_type(self):
        self.assertTrue(issubclass(JobCancelled, RuntimeError))


if __name__ == "__main__":
    unittest.main()
