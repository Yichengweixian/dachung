import tempfile
from pathlib import Path
import unittest
from scripts.make_baseline_manifest import snapshot,differences,clean

class BaselineManifestTests(unittest.TestCase):
    def test_snapshot_repeat_and_exclusions(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'keep.txt').write_text('evidence',encoding='utf-8')
            (root/'.git').mkdir();(root/'.git/ignored').write_text('x')
            a=snapshot(root);self.assertEqual(set(a),{'keep.txt'});self.assertTrue(clean(differences(a,snapshot(root))))
            out=root/'generated';out.mkdir();(out/'receipt.json').write_text('{}')
            self.assertEqual(a,snapshot(root,out))
    def test_changed_added_and_missing_are_separate(self):
        self.assertEqual(differences({'a':'1','b':'2'},{'a':'3','c':'4'}),dict(added=['c'],missing=['b'],changed=['a']))
    def test_sensitive_file_is_not_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'.env').touch()
            with self.assertRaises(ValueError):snapshot(root)
