import os
from git import Repo
from cotton.colors import yellow


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
        self._pull_branch()
        self._pop_changes()
        self._git_commit(self.change_set, self.message)

    def _git_commit(self, changes=[], message=''):
        print(yellow("Staging change-set"))
        for change in changes:
            self.git.git.add(change)
        print(yellow("Committing files with message {}".format(message)))
        self.git.git.commit('-a -m "{}"'.format(message))

    def _git_status(self):
        return self.git.git.status()

    def _stash_changes(self):
        print(yellow("Stashing changes"))
        self.git.git.stash('save')

    def _pop_changes(self):
        print(yellow("Popping changes"))
        self.git.git.stash('pop')

    def _checkout_branch(self, branch_name='master'):
        print(yellow("Checking out {}".format(branch_name)))
        self.git.git.checkout(branch_name)

    def _pull_branch(self):
        print(yellow("Rebasing against branch"))
        self.git.git.pull('--rebase')
