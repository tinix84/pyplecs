import unittest
from pathlib import Path
from pyplecs.plecs_parser import (
    parse_plecs_file,
    plecs_overview,
    scan_plecs_dir
)


class ParserTestSuite(unittest.TestCase):
    """Test cases for PLECS file parser."""

    def test_parse_plecs_file(self):
        """Test parsing a single .plecs file."""
        test_file = Path('../data/simple_buck.plecs')
        result = parse_plecs_file(str(test_file))

        self.assertIsInstance(result, dict)
        self.assertIn('file', result)
        self.assertIn('components', result)
        self.assertIn('init_vars', result)
        self.assertGreater(len(result['components']), 0)

    def test_plecs_overview(self):
        """Test generating an overview for a .plecs file."""
        test_file = Path('../data/simple_buck.plecs')
        overview = plecs_overview(str(test_file))

        self.assertIsInstance(overview, dict)
        self.assertIn('file', overview)
        self.assertIn('components', overview)
        self.assertIn('init_vars', overview)
        self.assertGreater(len(overview['components']), 0)

    def test_scan_plecs_dir(self):
        """Test scanning a directory for .plecs files."""
        test_dir = Path('../data')
        results = scan_plecs_dir(str(test_dir))

        self.assertIsInstance(results, dict)
        self.assertGreater(len(results), 0)
        for _, result in results.items():
            self.assertIn('file', result)
            self.assertIn('components', result)
            self.assertIn('init_vars', result)


if __name__ == '__main__':
    unittest.main()
