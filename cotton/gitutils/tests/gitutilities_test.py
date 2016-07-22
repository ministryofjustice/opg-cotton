import unittest
import os
import random
import string
from cotton.gitutils import GitUtilities
from git import Repo


class TestGitUtilities(unittest.TestCase):

    gutil = GitUtilities(root_path='./')

    @staticmethod
    def random_filename(size=20, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    def test_init(self):
        self.assertEqual([], self.gutil.change_set)
        self.assertEqual('', self.gutil.message)
        self.assertIsInstance(self.gutil.repository, Repo)

    def test_status(self):
        test_file = 'test-requirements.txt'
        result = self.gutil._git_status()
        self.assertIn('nothing to commit, working directory clean', result)
        local_file = open(test_file, 'w')
        local_file.write('Test data')
        local_file.close()
        result = self.gutil._git_status()
        self.assertNotIn('nothing to commit, working directory clean', result)

        self.gutil._stash_changes()
        result = self.gutil._git_status()
        self.assertIn('nothing to commit, working directory clean', result)

        self.gutil._pop_changes()
        result = self.gutil._git_status()
        self.assertNotIn('nothing to commit, working directory clean', result)

        self.gutil._reset_uncommitted_files()
        result = self.gutil._git_status()
        self.assertIn('nothing to commit, working directory clean', result)

    def test_new_file_found_for_staging(self):
        result = self.gutil._git_status()
        self.assertIn('nothing to commit, working directory clean', result)

        change_set = self.gutil.change_set
        new_file = self.random_filename()

        self.gutil.change_set = [new_file]
        os.mknod(new_file)
        self.assertNotIn('nothing to commit, working directory clean', self.gutil._git_status())

        self.gutil._clean_unstaged_files()
        self.assertIn('nothing to commit, working directory clean', self.gutil._git_status())

        new_dirname = self.random_filename(size=10)
        os.mkdir(new_dirname)
        os.mknod('{}/{}'.format(new_dirname, new_file))
        self.assertNotIn('nothing to commit, working directory clean', self.gutil._git_status())

        self.gutil._clean_unstaged_files()
        self.assertIn('nothing to commit, working directory clean', self.gutil._git_status())
        self.gutil.change_set = change_set
