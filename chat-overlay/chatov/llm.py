# -*- coding: utf-8 -*-
"""sLLM(Ollama / LM Studio 등 OpenAI 호환 서버)으로 채팅 대사와 닉네임을 만든다."""
import re
from dataclasses import dataclass
from typing import List

from .transport import HttpTransport, ServiceError


class LineCleaner:
    """모델이 붙이는 번호, 따옴표, 머리말, 생각(<think>) 블록을 걷어내고 한 줄씩 나눈다."""

    THINK = re.compile(r"<think>.*?</think>", re.S | re.I)
    BULLET = re.compile(r"^\s*(?:[-*•·>]+|\(?\d{1,3}\s*[.)\]:]|\d{1,3}\s+)\s*")
    SPEAKER = re.compile(r"^[^\s:：]{1,12}\s*[:：]\s*(.+)$")
    PREAMBLE = re.compile(r"^(물론|다음은|여기|아래는|알겠|sure|here|okay)", re.I)
    QUOTES = "\"'“”‘’「」『』`*"

    def __init__(self, max_len: int, strip_speaker: bool):
        self.max_len = max_len
        self.strip_speaker = strip_speaker

    def clean(self, text: str) -> List[str]:
        text = self.THINK.sub("", text or "")
        if "</think>" in text:
            text = text.rsplit("</think>", 1)[1]
        out, seen = [], set()
        for raw in text.splitlines():
            s = self.BULLET.sub("", raw).strip().strip(self.QUOTES).strip()
            if self.strip_speaker:
                m = self.SPEAKER.match(s)
                if m:
                    s = m.group(1).strip()
            if not s or len(s) > self.max_len or s.endswith((":", "：")) or self.PREAMBLE.match(s):
                continue
            key = s.replace(" ", "")
            if key not in seen:
                seen.add(key)
                out.append(s)
        return out


@dataclass(frozen=True)
class ChatReply:
    text: str
    truncated: bool = False     # 길이 한도에 걸려 중간에 끊김
    thought_only: bool = False  # 생각(reasoning)만 하고 본문은 비어 있음


def _root_of(base_url: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if not base:
        raise ServiceError("LLM 서버 주소가 비었습니다.")
    return base[:-3] if base.endswith("/v1") else base


def _messages(system: str, user: str) -> list:
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _without_embeddings(names) -> List[str]:
    return [n for n in names if n and "embed" not in n.lower()]


class OpenAICompatClient:
    """LM Studio 등 OpenAI 호환 서버"""

    def __init__(self, base_url: str, transport: HttpTransport):
        self.base = _root_of(base_url) + "/v1"
        self._t = transport

    def models(self) -> List[str]:
        data = self._t.json("GET", self.base + "/models", timeout=10)
        return _without_embeddings(m.get("id", "") for m in data.get("data", []))

    def chat(self, model: str, system: str, user: str, temperature: float) -> ChatReply:
        data = self._t.json("POST", self.base + "/chat/completions", {
            "model": model, "messages": _messages(system, user), "temperature": temperature, "stream": False,
        })
        try:
            choice = data["choices"][0]
            msg = choice["message"]
        except (KeyError, IndexError, TypeError):
            raise ServiceError(f"LLM 응답 형식을 읽을 수 없습니다: {str(data)[:300]}")
        text = msg.get("content") or ""
        thought = msg.get("reasoning") or msg.get("reasoning_content") or ""
        return ChatReply(text, truncated=choice.get("finish_reason") == "length",
                         thought_only=bool(thought) and not text.strip())


class OllamaNativeClient:
    """Ollama 전용 API. 생각(think) 단계를 끄고 대화 길이 한도를 늘려서,
    생각만 하다가 한도(기본 4096토큰)에 걸려 대사를 못 쓰는 일을 막는다."""

    NUM_CTX = 8192

    def __init__(self, base_url: str, transport: HttpTransport):
        self.root = _root_of(base_url)
        self._t = transport

    def models(self) -> List[str]:
        data = self._t.json("GET", self.root + "/api/tags", timeout=10)
        return _without_embeddings(m.get("name", "") for m in data.get("models", []))

    def chat(self, model: str, system: str, user: str, temperature: float) -> ChatReply:
        data = self._t.json("POST", self.root + "/api/chat", {
            "model": model, "messages": _messages(system, user), "stream": False, "think": False,
            "options": {"temperature": temperature, "num_ctx": self.NUM_CTX},
        })
        msg = data.get("message")
        if not isinstance(msg, dict):
            raise ServiceError(f"Ollama 응답 형식을 읽을 수 없습니다: {str(data)[:300]}")
        text = msg.get("content") or ""
        return ChatReply(text, truncated=data.get("done_reason") == "length",
                         thought_only=bool(msg.get("thinking")) and not text.strip())


class ChatLineWriter:
    MSG_SYSTEM = """너는 한국 인터넷 방송의 실시간 채팅창을 흉내 내는 작가다.
시청자들이 치는 짧은 채팅을 만든다.
규칙:
- 한 줄에 채팅 하나. 대부분 2~20자로 짧게, 가끔만 조금 길게.
- 번호, 따옴표, 닉네임, 설명, 머리말 없이 채팅 내용만 쓴다.
- ㅋㅋ, ㅠㅠ, ?, 초성, 줄임말, 맞춤법 틀린 말투 등 실제 채팅 느낌을 섞는다.
- 같은 말 반복 금지. 반응, 질문, 드립, 감탄, 딴소리를 골고루 섞는다."""

    NICK_SYSTEM = """너는 한국 인터넷 방송 시청자 닉네임을 지어내는 작가다.
규칙:
- 한 줄에 닉네임 하나. 2~8자.
- 번호, 따옴표, 설명 없이 닉네임만 쓴다.
- 한글, 영어, 숫자, 초성을 섞어 실제 커뮤니티 닉네임처럼."""

    MAX_COUNT = 100
    MAX_NICKS = 50
    ROUNDS = 3

    def __init__(self, client, model: str, temperature: float = 0.9):
        self._client = client
        self.model = (model or "").strip()
        self.temperature = float(temperature)

    @staticmethod
    def _usable_text(reply: ChatReply) -> str:
        # 길이 한도로 끊긴 답의 마지막 줄은 문장 중간에 잘렸을 수 있어 버린다
        if reply.truncated:
            return "\n".join(reply.text.rstrip().splitlines()[:-1])
        return reply.text

    def _collect(self, system: str, topic: str, count: int, cleaner: LineCleaner, what: str) -> List[str]:
        got: List[str] = []
        replies: List[ChatReply] = []
        for _ in range(self.ROUNDS):
            need = count - len(got)
            if need <= 0:
                break
            user = f"주제/분위기:\n{topic}\n\n위 분위기에 맞는 {what} {need}개를 한 줄에 하나씩 써라."
            if got:
                user += "\n\n아래와 겹치지 않게:\n" + "\n".join(got[-40:])
            reply = self._client.chat(self.model, system, user, self.temperature)
            replies.append(reply)
            for line in cleaner.clean(self._usable_text(reply)):
                if line not in got:
                    got.append(line)
        if not got:
            raise ServiceError(self._empty_reason(replies))
        return got[:count]

    @staticmethod
    def _empty_reason(replies: List[ChatReply]) -> str:
        if any(r.thought_only for r in replies):
            return ("모델이 생각하는 단계만 길게 하다가 길이 한도에 걸려 대사를 쓰지 못했습니다. "
                    "대사 개수를 줄이거나 생각하지 않는 모델(EXAONE 등)을 써 보세요.")
        if any(r.truncated for r in replies):
            return "모델 응답이 길이 한도에 걸려 잘렸습니다. 대사 개수를 줄여 보세요."
        return "LLM이 쓸 만한 줄을 돌려주지 않았습니다. 프롬프트나 모델을 바꿔보세요."

    def write(self, topic: str, count: int, nick_count: int = 0) -> dict:
        topic = (topic or "").strip()
        if not topic:
            raise ServiceError("주제나 분위기를 적으세요.")
        if not self.model:
            raise ServiceError("모델 이름을 적으세요.")
        count = min(self.MAX_COUNT, max(1, int(count)))
        result = {"msgs": self._collect(self.MSG_SYSTEM, topic, count, LineCleaner(60, True), "채팅")}
        if nick_count and int(nick_count) > 0:
            n = min(self.MAX_NICKS, int(nick_count))
            result["nicks"] = self._collect(self.NICK_SYSTEM, topic, n, LineCleaner(16, False), "닉네임")
        return result


class LlmService:
    """화면 요청(JSON)을 받아 알맞은 클라이언트와 작성기를 만들어 처리한다."""

    def __init__(self, transport: HttpTransport):
        self._t = transport

    def client_for(self, base: str):
        """Ollama 면 전용 API 로, 아니면 OpenAI 호환 방식으로 부른다. /api/version 이 답하면 Ollama."""
        try:
            self._t.json("GET", _root_of(base) + "/api/version", timeout=2)
            return OllamaNativeClient(base, self._t)
        except ServiceError:
            return OpenAICompatClient(base, self._t)

    def models(self, base: str) -> List[str]:
        return self.client_for(base).models()

    def generate(self, payload: dict) -> dict:
        client = self.client_for(payload.get("base"))
        writer = ChatLineWriter(client, payload.get("model"), float(payload.get("temperature") or 0.9))
        return writer.write(payload.get("prompt"), int(payload.get("count") or 35),
                            int(payload.get("nickCount") or 0))
