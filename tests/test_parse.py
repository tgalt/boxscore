import unittest

from boxscore.parse import parse_checklist


class TestParse(unittest.TestCase):
    def test_basic_sections_and_counts(self):
        text = """# Title

## Alpha
- [x] done thing
- [ ] open thing

## Beta
- [X] capital x counts
* [ ] star bullets count
"""
        cl = parse_checklist(text)
        self.assertEqual([s.title for s in cl.sections], ["Alpha", "Beta"])
        self.assertEqual((cl.done, cl.total), (2, 4))
        self.assertEqual(cl.first_open.text, "open thing")

    def test_no_headings(self):
        cl = parse_checklist("- [ ] a\n- [x] b\n")
        self.assertEqual(len(cl.sections), 1)
        self.assertEqual(cl.sections[0].title, "")
        self.assertEqual((cl.done, cl.total), (1, 2))

    def test_nested_items_counted_individually(self):
        text = "## S\n- [ ] parent\n  - [x] child one\n  - [ ] child two\n"
        cl = parse_checklist(text)
        self.assertEqual(cl.total, 3)
        self.assertEqual(cl.done, 1)
        self.assertEqual(cl.sections[0].items[1].indent, 2)

    def test_fenced_code_ignored(self):
        text = """## Real
- [ ] real item

```markdown
- [ ] fake item in a code block
# fake heading
```

- [x] second real item
"""
        cl = parse_checklist(text)
        self.assertEqual(cl.total, 2)
        self.assertEqual([s.title for s in cl.sections], ["Real"])

    def test_empty_and_garbage(self):
        self.assertEqual(parse_checklist("").total, 0)
        self.assertEqual(parse_checklist("plain prose\nno items\n").total, 0)
        # malformed boxes are not items
        self.assertEqual(parse_checklist("- [y] not a box\n- [] nope\n").total, 0)

    def test_line_numbers_are_1_based(self):
        cl = parse_checklist("# H\n- [ ] first\n")
        self.assertEqual(cl.sections[0].items[0].line, 2)


if __name__ == "__main__":
    unittest.main()
