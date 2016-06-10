import os
from git import Repo
from git.exc import GitCommandError


class GitUtilities(object):
    """Simple way to commit and rebase our change sets from a jenkins job"""

    change_set = []
    message = ''
    git = None

    def __init__(self, changes=[], message='', root_path=''):
        self.change_set = changes
        self.message = message

        self.git = Repo(os.path.join(os.path.realpath(root_path), '.git/'))
        assert not self.git.bare

    def commit_change_set(self):
        self._stash_changes()
        self._checkout_branch()
        self._pop_changes()
        self._pull_branch()

    def _git_status(self):
        return self.git.git.status()

    def _stash_changes(self):
        self.git.git.stash('save')

    def _pop_changes(self):
        self.git.git.stash('pop')

    def _checkout_branch(self, branch_name='master'):
        self.git.git.checkout(branch_name)

    def _pull_branch(self):
        self.git.git.pull('--rebase')
