import unittest
from cotton.git import GitUtilities
from git import Repo


class TestGitUtilities(unittest.TestCase):

    gutil = GitUtilities()

    def test_init(self):
        self.assertEqual([], self.gutil.change_set)
        self.assertEqual('', self.gutil.message)
        self.assertIsInstance(self.gutil.git, Repo)

