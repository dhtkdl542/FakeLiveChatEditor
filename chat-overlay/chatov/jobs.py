# -*- coding: utf-8 -*-
"""설치나 모델 다운로드처럼 오래 걸리는 일을 하나씩 백그라운드에서 돌리고 진행률을 알려준다."""
import threading
from typing import Callable, Optional


class JobCancelled(RuntimeError):
    pass


def spawn_thread(fn: Callable[[], None]) -> None:
    threading.Thread(target=fn, daemon=True).start()


class JobContext:
    """작업 함수가 진행 상황을 알리고 취소 여부를 확인하는 창구."""

    def __init__(self, runner: "JobRunner"):
        self._runner = runner

    def report(self, message: Optional[str] = None, completed: Optional[int] = None,
               total: Optional[int] = None) -> None:
        self._runner._update(message=message, completed=completed, total=total)

    def check_cancel(self) -> None:
        if self._runner._cancel:
            raise JobCancelled("취소했습니다. 다시 하면 이어서 진행합니다.")


class JobRunner:
    def __init__(self, spawn: Callable[[Callable[[], None]], None] = spawn_thread):
        self._spawn = spawn
        self._lock = threading.Lock()
        self._state = {"kind": "", "status": "idle", "message": "", "completed": 0, "total": 0}
        self._cancel = False

    def _update(self, **kw) -> None:
        with self._lock:
            self._state.update({k: v for k, v in kw.items() if v is not None})

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._state)

    @property
    def busy(self) -> bool:
        return self.snapshot()["status"] == "running"

    def start(self, kind: str, work: Callable[[JobContext], str]) -> None:
        with self._lock:
            if self._state["status"] == "running":
                raise RuntimeError(f"이미 다른 작업이 진행 중입니다: {self._state['message']}")
            self._state = {"kind": kind, "status": "running", "message": "준비 중...", "completed": 0, "total": 0}
            self._cancel = False
        ctx = JobContext(self)

        def run():
            try:
                message = work(ctx)
                self._update(status="done", message=message or "완료")
            except Exception as e:  # 작업 실패는 화면에 보여줄 상태로 바꾼다
                self._update(status="error", message=str(e))

        self._spawn(run)

    def cancel(self) -> None:
        self._cancel = True
