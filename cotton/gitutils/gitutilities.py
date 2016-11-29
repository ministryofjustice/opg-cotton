import os
from git import Repo
from cotton.colors import yellow, red
from git import Actor
from git.exc import GitCommandError


class GitUtilities(object):
    """Simple way to commit and rebase our change sets from a jenkins job"""

    change_set = []
    message = ''
    repository = None
    author = None
    target_branch = ''

    def __init__(self,
                 changes=[],
                 message='',
                 root_path='',
                 author='OPG Cotton',
                 author_email='opg-cotton@nowhere',
                 target_branch="master"):
        self.change_set = changes
        self.message = message
        self.target_branch = target_branch

        self.repository = Repo(os.path.join(os.path.realpath(root_path), '.git/'))
        assert not self.repository.bare
        self.author = Actor(name=author, email=author_email)

    def commit_change_set(self):

        files_exist = False
        for change in self.change_set:
            files_exist |= change in self._git_status()

        if files_exist:
            try:
                self._stash_changes()
                self._checkout_branch()
                self._pull_branch()
                self._pop_changes()
                self._remove_deleted_files()
                self._git_commit(self.change_set, self.message)
            except GitCommandError as e:
                if e.stderr != 'No stash found.':
                    print(red("Git returned: {}".format(e.stderr)))
                    exit(e.status)
        else:
            print(yellow('No changes to commit'))

    def _remove_deleted_files(self):
        index = self.repository.index
        print(yellow("Removing deleted files from repository"))

        items = self.repository.git.ls_files('-d').split('\n')
        index.remove(items=items, working_tree=True, r=True)

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

    def _checkout_branch(self):
        print(yellow("Checking out {}".format(self.target_branch)))
        self.repository.git.checkout(self.target_branch)

    def _pull_branch(self):
        print(yellow("Rebasing against branch"))
        self.repository.git.pull('--rebase')

    def _reset_uncommitted_files(self):
        print(yellow("Resetting uncommitted files"))
        self.repository.git.checkout('.')

    def _clean_unstaged_files(self):
        print(yellow("Cleaning up unstaged files"))
        for untracked_file in self.repository.untracked_files:
            os.unlink(untracked_file)
