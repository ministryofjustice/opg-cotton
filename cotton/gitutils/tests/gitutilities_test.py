import unittest
import os
from cotton.gitutils import GitUtilities
from git import Repo


class TestGitUtilities(unittest.TestCase):

    gutil = GitUtilities(root_path='./')

    def test_init(self):
        self.assertEqual([], self.gutil.change_set)
        self.assertEqual('', self.gutil.message)
        self.assertIsInstance(self.gutil.git, Repo)

    def test_status(self):
        test_file = 'test-requirements.txt'
        result = self.gutil._git_status()
        self.assertIn('nothing to commit, working directory clean', result)
        file = open(test_file, 'w')
        file.write('Test data')
        file.close()
        result = self.gutil._git_status()
        self.assertNotIn('nothing to commit, working directory clean', result)

        self.gutil._stash_changes()
        result = self.gutil._git_status()
        self.assertIn('nothing to commit, working directory clean', result)

        self.gutil._pop_changes()
        result = self.gutil._git_status()
        self.assertNotIn('nothing to commit, working directory clean', result)

    # def test_checkout(self):
    #     self.gutil._checkout_branch()


