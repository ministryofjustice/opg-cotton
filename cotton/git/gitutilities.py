import os
from git import Repo
from git.exc import GitCommandError


class GitUtilities(object):
    """Simple way to commit and rebase our change sets from a jenkins job"""

    change_set = []
    message = ''
    git = None

    def init(self, changes=[], message=''):
        self.change_set = changes
        self.message = message
        self.git = Repo(os.path.join(os.path.realpath(), '.git/'))

    def commit_change_set(self):
        self._stash_changes()
        self._checkout_master()
        self._pop_changes()
        self._rebase_master()

    def _stash_changes(self):
        self.git.stash_save()

    def _pop_changes(self):
        self.git.stash_pop()

    def _checkout_master(self):
        self.git.checkout('master')

    def _rebase_master(self):
        self.git.pull('--rebase')
