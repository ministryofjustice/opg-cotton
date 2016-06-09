import unittest
from cotton.gitutils import GitUtilities
from git import Repo


class TestGitUtilities(unittest.TestCase):

    gutil = GitUtilities(root_path='./')

    def test_init(self):
        self.assertEqual([], self.gutil.change_set)
        self.assertEqual('', self.gutil.message)
        self.assertIsInstance(self.gutil.git, Repo)

    def test_

