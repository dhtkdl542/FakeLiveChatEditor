import unittest

from chatov.llm import (ChatLineWriter, ChatReply, LineCleaner, LlmService, OllamaNativeClient,
                        OpenAICompatClient)
from chatov.transport import ServiceError
from tests.fakes import FakeTransport

BASE = "http://127.0.0.1:11434/v1"
ROOT = "http://127.0.0.1:11434"
LMSTUDIO = "http://127.0.0.1:1234/v1"


class LineCleanerTest(unittest.TestCase):
    def test_strips_numbering_bullets_quotes_and_preamble(self):
        raw = '물론이죠! 다음은 채팅입니다:\n1. ㅋㅋ 미쳤다\n2) "실화냐"\n- 와\n10 사레들림 ㅠㅠ\n채팅:\n'
        self.assertEqual(LineCleaner(60, True).clean(raw), ["ㅋㅋ 미쳤다", "실화냐", "와", "사레들림 ㅠㅠ"])

    def test_removes_think_blocks(self):
        self.assertEqual(LineCleaner(60, True).clean("<think>음...\n생각</think>\nㅋㅋ"), ["ㅋㅋ"])

    def test_unclosed_think_keeps_text_after_close_tag(self):
        self.assertEqual(LineCleaner(60, True).clean("생각중\n</think>\n안녕"), ["안녕"])

    def test_speaker_prefix_removed_only_when_asked(self):
        self.assertEqual(LineCleaner(60, True).clean("뷰럴러버: 오늘 웃김"), ["오늘 웃김"])
        self.assertEqual(LineCleaner(60, False).clean("뷰럴러버: 오늘 웃김"), ["뷰럴러버: 오늘 웃김"])

    def test_drops_duplicates_ignoring_spaces_and_too_long_lines(self):
        self.assertEqual(LineCleaner(5, True).clean("ㅋ ㅋ\nㅋㅋ\n너무너무긴줄입니다"), ["ㅋ ㅋ"])


class OpenAICompatClientTest(unittest.TestCase):
    def test_adds_v1_to_base_url(self):
        self.assertEqual(OpenAICompatClient("http://127.0.0.1:1234/", FakeTransport()).base, LMSTUDIO)
        self.assertEqual(OpenAICompatClient(LMSTUDIO, FakeTransport()).base, LMSTUDIO)

    def test_empty_base_rejected(self):
        with self.assertRaises(ServiceError):
            OpenAICompatClient("  ", FakeTransport())

    def test_models_skip_embedding_models(self):
        t = FakeTransport({("GET", LMSTUDIO + "/models"): {"data": [{"id": "phi4:14b"}, {"id": "nomic-embed-text"}]}})
        self.assertEqual(OpenAICompatClient(LMSTUDIO, t).models(), ["phi4:14b"])

    def test_chat_sends_messages_and_returns_reply(self):
        t = FakeTransport({("POST", LMSTUDIO + "/chat/completions"):
                           {"choices": [{"message": {"content": "ㅋㅋ"}, "finish_reason": "stop"}]}})
        self.assertEqual(OpenAICompatClient(LMSTUDIO, t).chat("m", "sys", "user", 0.7), ChatReply("ㅋㅋ"))
        body = t.requests[0][2]
        self.assertEqual(body["model"], "m")
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])
        self.assertFalse(body["stream"])

    def test_cut_off_reply_is_marked(self):
        t = FakeTransport({("POST", LMSTUDIO + "/chat/completions"):
                           {"choices": [{"message": {"content": "", "reasoning": "생각..."}, "finish_reason": "length"}]}})
        reply = OpenAICompatClient(LMSTUDIO, t).chat("m", "s", "u", 0.7)
        self.assertTrue(reply.truncated)
        self.assertTrue(reply.thought_only)

    def test_chat_with_unexpected_reply_raises(self):
        t = FakeTransport({("POST", LMSTUDIO + "/chat/completions"): {"weird": 1}})
        with self.assertRaises(ServiceError):
            OpenAICompatClient(LMSTUDIO, t).chat("m", "s", "u", 0.7)


class OllamaNativeClientTest(unittest.TestCase):
    """Ollama 는 전용 API 로 부른다. 생각(think) 단계를 끄고 대화 길이 한도를 늘려야 대사가 잘리지 않는다."""

    def test_strips_v1_from_base(self):
        self.assertEqual(OllamaNativeClient(BASE, FakeTransport()).root, ROOT)
        self.assertEqual(OllamaNativeClient(ROOT + "/", FakeTransport()).root, ROOT)

    def test_chat_turns_thinking_off_and_raises_context(self):
        t = FakeTransport({("POST", ROOT + "/api/chat"): {"message": {"content": "ㅋㅋ\n와"}, "done_reason": "stop"}})
        reply = OllamaNativeClient(BASE, t).chat("gemma", "sys", "user", 0.8)
        self.assertEqual(reply, ChatReply("ㅋㅋ\n와"))
        body = t.requests[0][2]
        self.assertIs(body["think"], False)
        self.assertFalse(body["stream"])
        self.assertEqual(body["options"]["temperature"], 0.8)
        self.assertGreaterEqual(body["options"]["num_ctx"], 8192)
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])

    def test_length_cut_is_marked(self):
        t = FakeTransport({("POST", ROOT + "/api/chat"):
                           {"message": {"content": "", "thinking": "음..."}, "done_reason": "length"}})
        reply = OllamaNativeClient(BASE, t).chat("m", "s", "u", 0.8)
        self.assertEqual((reply.truncated, reply.thought_only), (True, True))

    def test_models_from_tags_without_embeddings(self):
        t = FakeTransport({("GET", ROOT + "/api/tags"): {"models": [{"name": "gemma:12b"}, {"name": "nomic-embed-text"}]}})
        self.assertEqual(OllamaNativeClient(BASE, t).models(), ["gemma:12b"])


class ScriptedClient:
    """chat() 호출마다 준비된 답을 차례로 돌려주는 대역."""

    def __init__(self, replies):
        self.replies = [r if isinstance(r, ChatReply) else ChatReply(r) for r in replies]
        self.prompts = []

    def chat(self, model, system, user, temperature):
        self.prompts.append((system, user))
        return self.replies.pop(0) if self.replies else ChatReply("")


class ChatLineWriterTest(unittest.TestCase):
    def test_returns_requested_count(self):
        client = ScriptedClient(["a\nb\nc\nd"])
        self.assertEqual(ChatLineWriter(client, "m").write("먹방", 3)["msgs"], ["a", "b", "c"])

    def test_asks_again_until_enough_and_avoids_repeats(self):
        client = ScriptedClient(["a\nb", "b\nc", "d"])
        result = ChatLineWriter(client, "m").write("먹방", 4)
        self.assertEqual(result["msgs"], ["a", "b", "c", "d"])
        self.assertIn("겹치지 않게", client.prompts[1][1])
        self.assertIn("2개", client.prompts[1][1])

    def test_gives_up_after_three_rounds(self):
        client = ScriptedClient(["a", "a", "a", "b"])
        self.assertEqual(ChatLineWriter(client, "m").write("t", 5)["msgs"], ["a"])
        self.assertEqual(len(client.prompts), 3)

    def test_nothing_usable_raises(self):
        with self.assertRaisesRegex(ServiceError, "쓸 만한"):
            ChatLineWriter(ScriptedClient(["", "", ""]), "m").write("t", 5)

    def test_cut_off_replies_explain_the_cause(self):
        cut = ChatReply("", truncated=True, thought_only=True)
        with self.assertRaisesRegex(ServiceError, "생각.*길이 한도|길이 한도"):
            ChatLineWriter(ScriptedClient([cut, cut, cut]), "m").write("t", 35)

    def test_cut_off_reply_still_keeps_usable_lines(self):
        client = ScriptedClient([ChatReply("a\nb\n세번째줄이 중간에 잘", truncated=True), "c"])
        self.assertEqual(ChatLineWriter(client, "m").write("t", 3)["msgs"], ["a", "b", "c"])

    def test_nicknames_only_when_requested(self):
        client = ScriptedClient(["말1\n말2", "닉1\n닉2"])
        result = ChatLineWriter(client, "m").write("t", 2, nick_count=2)
        self.assertEqual(result, {"msgs": ["말1", "말2"], "nicks": ["닉1", "닉2"]})
        self.assertIn("닉네임", client.prompts[1][0])
        self.assertNotIn("nicks", ChatLineWriter(ScriptedClient(["x"]), "m").write("t", 1))

    def test_topic_and_model_required(self):
        with self.assertRaises(ServiceError):
            ChatLineWriter(ScriptedClient([]), "m").write("  ", 3)
        with self.assertRaises(ServiceError):
            ChatLineWriter(ScriptedClient([]), "").write("t", 3)

    def test_count_is_clamped(self):
        client = ScriptedClient(["\n".join(str(i) for i in range(200))])
        self.assertEqual(len(ChatLineWriter(client, "m").write("t", 999)["msgs"]), ChatLineWriter.MAX_COUNT)


class LlmServiceTest(unittest.TestCase):
    def test_ollama_server_gets_native_client(self):
        t = FakeTransport({("GET", ROOT + "/api/version"): {"version": "0.35.0"},
                           ("POST", ROOT + "/api/chat"): {"message": {"content": "ㅋㅋ\n와"}, "done_reason": "stop"}})
        result = LlmService(t).generate({"base": BASE, "model": "m", "prompt": "먹방", "count": 2,
                                         "temperature": 0.5, "nickCount": 0})
        self.assertEqual(result, {"msgs": ["ㅋㅋ", "와"]})
        self.assertIs(t.requests[-1][2]["think"], False)

    def test_other_servers_get_openai_client(self):
        t = FakeTransport({("GET", "http://127.0.0.1:1234/api/version"): ServiceError("404"),
                           ("POST", LMSTUDIO + "/chat/completions"):
                               {"choices": [{"message": {"content": "ㅋㅋ"}, "finish_reason": "stop"}]}})
        result = LlmService(t).generate({"base": LMSTUDIO, "model": "m", "prompt": "p", "count": 1})
        self.assertEqual(result, {"msgs": ["ㅋㅋ"]})

    def test_models_for_base(self):
        t = FakeTransport({("GET", ROOT + "/api/version"): {"version": "1"},
                           ("GET", ROOT + "/api/tags"): {"models": [{"name": "a"}]}})
        self.assertEqual(LlmService(t).models(ROOT), ["a"])


if __name__ == "__main__":
    unittest.main()
