import os
from git import Repo
from cotton.colors import yellow
from git import Actor


class GitUtilities(object):
    """Simple way to commit and rebase our change sets from a jenkins job"""

    change_set = []
    message = ''
    repository = None
    author = None

    def __init__(self, changes=[], message='', root_path='', author='OPG Cotton', author_email='opg-cotton@nowhere'):
        self.change_set = changes
        self.message = message

        self.repository = Repo(os.path.join(os.path.realpath(root_path), '.git/'))
        assert not self.repository.bare
        self.author = Actor(name=author, email=author_email)

    def commit_change_set(self):
        self._stash_changes()
        self._checkout_branch()
        self._pull_branch()
        self._pop_changes()
        self._git_commit(self.change_set, self.message)

    def _git_commit(self, changes=[], message=''):
        index = self.repository.index
        print(yellow("Staging change-set"))
        for change in changes:
            self.repository.git.add(change)
            print(yellow("Staged: {}".format(change)))
        print(yellow("Committing files with message: {}".format(message)))

        index.commit(message, author=self.author, committer=self.author)

    def _git_status(self):
        return self.repository.git.status()

    def _stash_changes(self):
        print(yellow("Stashing changes"))
        self.repository.git.stash('save')

    def _pop_changes(self):
        print(yellow("Popping changes"))
        self.repository.git.stash('pop')

    def _checkout_branch(self, branch_name='master'):
        print(yellow("Checking out {}".format(branch_name)))
        self.repository.git.checkout(branch_name)

    def _pull_branch(self):
        print(yellow("Rebasing against branch"))
        self.repository.git.pull('--rebase')
