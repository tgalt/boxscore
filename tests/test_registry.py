import os
import tempfile
import unittest

from boxscore.registry import load_registry

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestRegistry(unittest.TestCase):
    def _write(self, text, name="projects.toml"):
        d = tempfile.mkdtemp()
        path = os.path.join(d, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_demo_registry_loads(self):
        cwd = os.getcwd()
        os.chdir(ROOT)
        try:
            projects = load_registry("examples/demo.toml")
        finally:
            os.chdir(cwd)
        self.assertEqual([p.slug for p in projects], ["atlas", "beacon", "comet", "boxscore"])
        self.assertEqual(projects[3].link, "https://github.com/tgalt/boxscore")
        self.assertTrue(all(not p.missing for p in projects))

    def test_defaults_and_tilde(self):
        path = self._write('[[projects]]\nname = "My App"\nrepo = "~"\n')
        (p,) = load_registry(path)
        self.assertEqual(p.slug, "my-app")
        self.assertEqual(p.repo, os.path.expanduser("~"))
        self.assertEqual(p.checklists, ["CHECKLIST.md"])

    def test_invalid_toml_fails_loud(self):
        with self.assertRaisesRegex(SystemExit, "invalid TOML"):
            load_registry(self._write("[[projects]\nname = "))

    def test_no_projects_fails_loud(self):
        with self.assertRaisesRegex(SystemExit, r"\[\[projects\]\]"):
            load_registry(self._write('title = "x"\n'))

    def test_yaml_rejected_with_hint(self):
        with self.assertRaisesRegex(SystemExit, "convert it to TOML"):
            load_registry(self._write("projects: []\n", name="projects.yaml"))


if __name__ == "__main__":
    unittest.main()
