import unittest

from hdrpackage import omp_connect


class TestDBConnection(unittest.TestCase):

    def test_database_removed(self):
        """Database usage should be explicitly disabled."""
        with self.assertRaises(RuntimeError):
            omp_connect.connect_to_db()


if __name__ == '__main__':
    unittest.main()
