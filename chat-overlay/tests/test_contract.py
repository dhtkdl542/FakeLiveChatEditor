import json
import unittest
from pathlib import Path

from tools.gen_contract import OUT, build


class ContractTest(unittest.TestCase):
    """shared/contract.json 이 현재 Python 동작과 같은지 확인한다. 다르면 브라우저와 어긋난 것."""

    def test_contract_file_matches_python_behaviour(self):
        self.assertTrue(OUT.exists(), "python tools/gen_contract.py 로 계약 파일을 만드세요")
        saved = json.loads(OUT.read_text(encoding="utf-8"))
        self.assertEqual(saved, json.loads(json.dumps(build(), ensure_ascii=False)))

    def test_generator_case_with_reversed_interval_still_produces_events(self):
        saved = json.loads(Path(OUT).read_text(encoding="utf-8"))
        self.assertGreater(len(saved["events"][1]["events"]), 5)


if __name__ == "__main__":
    unittest.main()
