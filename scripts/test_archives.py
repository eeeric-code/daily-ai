import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

spec = importlib.util.spec_from_file_location("render_archives", Path(__file__).with_name("render_archives.py"))
archives = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archives)

class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        archives.write(self.root/"example/archive.html", "<html><head><style>body{color:#123}</style></head><body></body></html>")

    def tearDown(self):
        self.temp.cleanup()

    def issue(self, path, title="Specific paper and evidence headline"):
        body = f'<html><head><title>{title}</title></head><body><section class="exec"><ol><li><span class="num">1</span><strong>{title}</strong>Research evidence and limitations are explained in this issue for reproducibility.</li></ol></section><div class="card"><div class="card-title">{title}</div></div></body></html>'
        archives.write(self.root/path/"index.html", body)
        return body

    def test_scan_fills_missing_issue_and_keeps_body(self):
        path = "ai-products/gpt/2026-10-20"
        body = self.issue(path)
        output,audit = archives.build(self.root)
        soup = BeautifulSoup(output["ai-products/gpt/archive.html"],"html.parser")
        self.assertEqual(len(soup.select(".archive-item")),1)
        self.assertEqual(audit["ai-products/gpt"]["available"],1)
        self.assertEqual(soup.select_one(".open-btn")["href"],"./2026-10-20/")
        self.assertEqual((self.root/path/"index.html").read_text(),body)
        self.assertEqual(str(soup.style),"<style>body{color:#123}</style>")
        self.assertEqual(output["ai-products/gpt/archive.html"],output["ai-products/gpt/briefs.html"])

    def test_corrupt_duplicate_and_missing_records_survive_idempotently(self):
        self.issue("ai-products/minimax/2026-10-20")
        orphan = '<li class="archive-item"><div class="title">An original now missing</div><div class="summary">A preserved historical summary with no available original file.</div><a href="./2026-08-12/">View</a></li>'
        broken = "<html "+orphan+'> <body><ul class="archive-list"'+orphan+"</ul></body></html>"
        archives.write(self.root/"ai-products/minimax/archive.html",broken)
        first,audit = archives.build(self.root)
        soup = BeautifulSoup(first["ai-products/minimax/archive.html"],"html.parser")
        self.assertEqual(audit["ai-products/minimax"]["missing"],1)
        self.assertEqual(len(soup.select('[data-date="2026-08-12"]')),1)
        self.assertFalse(soup.select_one('[data-date="2026-08-12"]').select("a[href]"))
        self.assertTrue(all(n.find_parent("ul") for n in soup.select(".archive-item")))
        for path,text in first.items():
            archives.write(self.root/path,text)
        second,_ = archives.build(self.root)
        self.assertEqual(first,second)

    def test_editorial_override_escaped_and_mixed_history_separated(self):
        path="ai-academic/gpt/2026-10-20"
        self.issue(path)
        self.issue("ai-daily/gpt/2026-10-19","Prior mixed scientific and commercial developments")
        archives.write(self.root/path/"archive.json",json.dumps(dict(
            title="Research <script> & evidence",
            summary="This specific issue summary describes verified research contributions and limits.")))
        output,audit=archives.build(self.root)
        soup=BeautifulSoup(output["ai-academic/gpt/archive.html"],"html.parser")
        self.assertFalse(soup.select("script"))
        self.assertEqual(len(soup.select("section")),2)
        self.assertIn("分栏前历史稿",soup.get_text())
        self.assertEqual(audit["ai-academic/gpt"]["available"],1)
        self.assertEqual(soup.select_one(".title").get_text(),"Research <script> & evidence")

    def test_descending_real_dates_and_same_date_different_models(self):
        for path in ["ai-products/gpt/2026-10-19","ai-products/gpt/2026-10-20",
                     "ai-products/minimax/2026-10-20"]:
            self.issue(path)
        output,_=archives.build(self.root)
        soup=BeautifulSoup(output["archive.html"],"html.parser")
        rows=soup.select(".archive-item")
        self.assertEqual([r["data-date"] for r in rows],["2026-10-20","2026-10-20","2026-10-19"])
        self.assertEqual(len({r["data-path"] for r in rows}),3)

if __name__=="__main__":
    unittest.main()
