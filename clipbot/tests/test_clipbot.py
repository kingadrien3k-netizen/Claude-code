import random
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from clipbot import captions, config, style, tiktok, video
from clipbot.detector import SpikeDetector, Trigger, top_terms
from clipbot.tokens import TokenStore

DET = config.DEFAULTS["detector"]


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def feed(det, clock, seconds, per_second, text="hello there"):
    for _ in range(int(seconds)):
        for _ in range(per_second):
            det.add(text)
        clock.t += 1
        trig = det.check()
        if trig:
            return trig
    return None


class DetectorTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.det = SpikeDetector(DET, clock=self.clock)

    def test_steady_chat_never_triggers(self):
        self.assertIsNone(feed(self.det, self.clock, 400, 3))

    def test_spike_after_warmup_triggers(self):
        feed(self.det, self.clock, 200, 1)
        trig = feed(self.det, self.clock, 10, 8, "OMEGALUL OMEGALUL")
        self.assertIsNotNone(trig)
        self.assertIn("OMEGALUL", trig.top_terms)

    def test_no_trigger_during_warmup(self):
        self.assertIsNone(feed(self.det, self.clock, 30, 20))

    def test_cooldown(self):
        feed(self.det, self.clock, 200, 1)
        self.assertIsNotNone(feed(self.det, self.clock, 10, 10))
        self.assertIsNone(feed(self.det, self.clock, 30, 10))

    def test_tiny_chat_ignores_small_bursts(self):
        feed(self.det, self.clock, 200, 0)
        self.assertIsNone(feed(self.det, self.clock, 12, 1))

    def test_keywords_trigger_without_rate_spike(self):
        feed(self.det, self.clock, 200, 2)
        self.assertEqual(feed(self.det, self.clock, 10, 2, "CLIP IT").reason, "keywords")

    def test_keyword_matching_is_whole_word(self):
        self.assertTrue(self.det.is_keyword("that was a W"))
        self.assertFalse(self.det.is_keyword("wow nice"))

    def test_top_terms_counts_once_per_message(self):
        msgs = ["LUL LUL LUL LUL"] + ["Pog"] * 3
        self.assertEqual(top_terms(msgs, 1), ["Pog"])


class CaptionTests(unittest.TestCase):
    def test_caption_has_credit_and_tags(self):
        trig = Trigger("spike", 30, 3.0, 0.5, 4, ["KEKW", "LUL"])
        hook, cap = captions.build("coolguy", "Grand Theft Auto V", trig,
                                   config.DEFAULTS["captions"], ["gta"], random.Random(1))
        self.assertEqual(captions.mood(trig), "funny")
        self.assertIn("twitch.tv/coolguy", cap)
        self.assertIn("#grandtheftautov", cap)
        self.assertEqual(cap.count("#coolguy"), 1)
        self.assertNotIn("#", hook)


class TikTokTests(unittest.TestCase):
    def test_chunk_plan(self):
        MB = tiktok.MB
        self.assertEqual(tiktok.chunk_plan(3 * MB), (3 * MB, 1))
        self.assertEqual(tiktok.chunk_plan(64 * MB), (64 * MB, 1))
        size = 105 * MB
        chunk, n = tiktok.chunk_plan(size)
        self.assertEqual((chunk, n), (10 * MB, 10))
        self.assertLessEqual(size - chunk * (n - 1), 128 * MB)  # last chunk absorbs remainder

    def test_direct_upload_flow(self):
        with tempfile.TemporaryDirectory() as d:
            tokens = TokenStore(f"{d}/t.json")
            tokens.set("tiktok", {"access_token": "a", "refresh_token": "r", "expires_in": 86400})
            vid = Path(d, "v.mp4")
            vid.write_bytes(b"x" * 1000)
            client = tiktok.TikTok(config.DEFAULTS["tiktok"], tokens)

            def post(url, json=None, **kw):
                r = mock.Mock(ok=True)
                if url.endswith("creator_info/query/"):
                    r.json.return_value = {"data": {"privacy_level_options": ["SELF_ONLY"]}, "error": {"code": "ok"}}
                else:
                    self.assertEqual(json["post_info"]["title"], "my caption")
                    self.assertEqual(json["source_info"]["video_size"], 1000)
                    r.json.return_value = {"data": {"publish_id": "p1", "upload_url": "https://up"},
                                           "error": {"code": "ok"}}
                return r

            client.http.post = post
            client.http.put = mock.Mock(return_value=mock.Mock(status_code=201))
            self.assertEqual(client.upload(vid, "my caption", "direct"), "p1")
            headers = client.http.put.call_args.kwargs["headers"]
            self.assertEqual(headers["Content-Range"], "bytes 0-999/1000")


class VideoTests(unittest.TestCase):
    def test_render_vertical(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d, "in.mp4"), Path(d, "out.mp4")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30",
                            "-f", "lavfi", "-i", "sine", "-t", "2", "-shortest", str(src)], check=True)
            video.render(src, dst, "chat went crazy 😂", config.DEFAULTS["video"])
            out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                  "stream=width,height", "-of", "csv=p=0", str(dst)],
                                 capture_output=True, text=True, check=True).stdout.strip()
            self.assertEqual(out, "1080,1920")


class StyleTests(unittest.TestCase):
    WORDS = [style.Word(0.0, 0.3, "bro"), style.Word(0.3, 0.6, "what"), style.Word(0.6, 0.9, "is"),
             style.Word(0.9, 1.2, "this"), style.Word(3.0, 3.4, "NAH")]

    def test_groups_split_on_size_and_pauses(self):
        groups = [[w.text for w in g] for g in style.group_words(self.WORDS)]
        self.assertEqual(groups, [["bro", "what", "is"], ["this"], ["NAH"]])

    def test_ass_highlights_one_word_per_event(self):
        ass = style.build_ass(self.WORDS, "hook {x} 😭", 5.0, 1300)
        events = [l for l in ass.splitlines() if l.startswith("Dialogue: 0")]
        self.assertEqual(len(events), 5)
        self.assertTrue(all(e.count("\\c&H0000E5FF&") == 1 for e in events))
        self.assertIn("Hook,,0,0,0,,hook (x)", ass)

    def test_render_layouts(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "in.mp4")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=30",
                            "-f", "lavfi", "-i", "sine", "-t", "2", "-shortest", str(src)], check=True)
            for layout, cam in (("center", None), ("split", (0.7, 0.05, 0.28, 0.3)), ("blur", None)):
                dst = Path(d, f"{layout}.mp4")
                style.render_pro(src, dst, "hook", layout=layout, facecam=cam, words=self.WORDS[:2])
                out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                      "stream=width,height", "-of", "csv=p=0", str(dst)],
                                     capture_output=True, text=True, check=True).stdout.strip()
                self.assertEqual(out, "1080,1920", layout)


if __name__ == "__main__":
    unittest.main()
