import unittest
import os
import random
import string
from cotton.gitutils import GitUtilities
from git import Repo
import sys
from StringIO import StringIO


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
        stdout = sys.stdout

        try:
            new_stdout = StringIO()
            sys.stdout = new_stdout

            test_file = 'test-requirements.txt'
            result = self.gutil._git_status()
            self.assertIn('nothing to commit, working directory clean', result)
            local_file = open(test_file, 'w')
            local_file.write('Test data')
            local_file.close()
            result = self.gutil._git_status()
            self.assertNotIn('nothing to commit, working directory clean', result)
            self.assertFalse(self.gutil.stashed_changes)

            self.gutil._stash_changes()
            result = self.gutil._git_status()
            self.assertTrue(self.gutil.stashed_changes)
            self.assertIn('nothing to commit, working directory clean', result)

            self.gutil._pop_changes()
            result = self.gutil._git_status()
            self.assertNotIn('nothing to commit, working directory clean', result)

            self.gutil._reset_uncommitted_files()
            result = self.gutil._git_status()
            self.assertIn('nothing to commit, working directory clean', result)
        finally:
            sys.stdout = stdout

    def test_new_file_found_for_staging(self):
        stdout = sys.stdout

        try:
            new_stdout = StringIO()
            sys.stdout = new_stdout
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
        finally:
            sys.stdout = stdout

    def test_non_existent_files_for_staging_do_not_commit(self):
        stdout = sys.stdout

        try:
            new_stdout = StringIO()
            sys.stdout = new_stdout
            result = self.gutil._git_status()
            self.assertIn('nothing to commit, working directory clean', result)

            change_set = self.gutil.change_set
            self.gutil.change_set = []
            self.gutil.change_set.append(self.random_filename())
            self.gutil.change_set.append(self.random_filename())

            result = self.gutil.commit_change_set()
            self.assertEquals(self.gutil.NO_CHANGES_TO_COMMIT, result)

            self.assertIn('nothing to commit, working directory clean', self.gutil._git_status())
            self.gutil.change_set = change_set
        finally:
            sys.stdout = stdout

    def test_no_stash_not_fatal(self):
        result = self.gutil._git_status()
        self.assertIn('nothing to commit, working directory clean', result)

        self.gutil._stash_changes()
        self.assertFalse(self.gutil.stashed_changes)
        self.gutil._pop_changes()
        self.assertFalse(self.gutil.stashed_changes)
