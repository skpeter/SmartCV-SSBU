"""Parse helpers — no PaddleOCR import."""
import unittest

from core.ocr_parse import apply_stock_pair, paddle_texts, parse_stock_ocr_result


class PaddleTextsTests(unittest.TestCase):
    def test_none_and_empty(self):
        self.assertIsNone(paddle_texts(None))
        self.assertIsNone(paddle_texts([]))

    def test_allowlist_and_low_text(self):
        raw = [{"rec_texts": ["12a", "x"], "rec_scores": [0.9, 0.1]}]
        self.assertEqual(paddle_texts(raw, allowlist="123", low_text=0.3), ["12"])

    def test_missing_score_is_dropped(self):
        raw = [{"rec_texts": ["3"], "rec_scores": []}]
        self.assertIsNone(paddle_texts(raw, low_text=0.3))

    def test_wrapped_json_res(self):
        class R:
            def json(self):
                return {"res": {"rec_texts": ["3"], "rec_scores": [0.99]}}

        self.assertEqual(paddle_texts([R()]), ["3"])

    def test_allowlist_strips_all(self):
        raw = [{"rec_texts": ["abc"], "rec_scores": [0.99]}]
        self.assertIsNone(paddle_texts(raw, allowlist="123"))

    def test_below_low_text(self):
        raw = [{"rec_texts": ["1"], "rec_scores": [0.1]}]
        self.assertIsNone(paddle_texts(raw, low_text=0.3))


class StockOcrTests(unittest.TestCase):
    def test_parse_list_join_and_first_digit(self):
        self.assertEqual(parse_stock_ocr_result(["1"]), 1)
        self.assertEqual(parse_stock_ocr_result("12"), 1)
        self.assertIsNone(parse_stock_ocr_result(None))
        self.assertIsNone(parse_stock_ocr_result(""))
        self.assertIsNone(parse_stock_ocr_result("abc"))

    def test_apply_stock_pair_both_ok(self):
        payload = {"players": [{"stocks": 3}, {"stocks": 3}]}
        self.assertEqual(apply_stock_pair(payload, [2, 1]), [2, 1])
        self.assertEqual(payload["players"][0]["stocks"], 2)
        self.assertEqual(payload["players"][1]["stocks"], 1)

    def test_apply_stock_pair_partial_leaves_payload(self):
        payload = {"players": [{"stocks": 3}, {"stocks": 3}]}
        self.assertIsNone(apply_stock_pair(payload, [None, 1]))
        self.assertEqual(payload["players"][0]["stocks"], 3)
        self.assertEqual(payload["players"][1]["stocks"], 3)


if __name__ == "__main__":
    unittest.main()
