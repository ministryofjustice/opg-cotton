import os
import time

from fabric.api import sudo, local, task, env
from cotton.colors import green, yellow
from cotton.api import vm_task
from cotton.fabextras import smart_rsync_project
from cotton.salt import get_pillar_location, smart_salt, Shaker, salt_call


@vm_task
def salt(selector="'*'", args='state.highstate', parse_highstate=False, timeout=60, skip_manage_down=False, prefix=''):
    """
    `salt` / `salt-call` wrapper that:
    - checks if `env.saltmaster` is set to select between `salt` or `salt-call` command
    - checks for output of state.highstate / state.sls and aborts on failure
    param selector: i.e.: '*', -G 'roles:foo'
    param args: i.e. state.highstate
    param parse_highstate: If True then salt output is yaml and parsed for Successes/Changes/Failures
                           Works for both state.highstate and state.sls
    param timeout: Passed to salt as a timeout value (-t) in seconds
    param skip_manage_down: If True then skip the check to run a manage.down to establish unresponsive minions
    """
    smart_salt(selector, args, parse_highstate=parse_highstate, timeout=timeout, skip_manage_down=skip_manage_down, prefix=prefix)


@vm_task
def unattended_highstate():
    salt_event('salt/custom/start_highstate')


@vm_task
def salt_event(args):
    """
    Fire a custom reactor event
    :param args: tag for the custom event
    :return:
    """
    salt_call('event.send', args)


@vm_task
def rsync():
    '''
    Invokes salt_rync overriding the formula-requirements file path if specified
    '''

    # -L will follow symlinks and pull vendor formula
    sudo("mkdir -p /srv/salt")
    smart_rsync_project('/srv/salt', 'salt/', for_user='root', extra_opts='-L', delete=True)

    pillar_location = get_pillar_location(parse_top_sls=False)
    sudo("mkdir -p /srv/pillar")
    smart_rsync_project('/srv/pillar', '{}/'.format(pillar_location), for_user='root', extra_opts='-L', delete=True)

    sudo("mkdir -p /srv/salt-formulas")
    smart_rsync_project('/srv/salt-formulas', 'vendor/_root/', for_user='root', extra_opts='-L', delete=True)


@vm_task
def update(selector="'*'", skip_highstate=False, parse_highstate=False, timeout=60, skip_manage_down=False):
    """
    shaker, rsync, highstate
    """
    shaker()
    rsync()
    if skip_highstate == 'False' or not skip_highstate:
        highstate(selector, parse_highstate, timeout, skip_manage_down)


@vm_task
def highstate(selector="'*'", parse_highstate=False, timeout=60, skip_manage_down=False, prefix=''):
    salt(selector, 'state.highstate', parse_highstate, timeout, skip_manage_down, prefix)


@task
def shaker():
    """
    utility task to initiate Shaker in the most typical way
    """
    shaker_instance = Shaker(root_dir=os.path.dirname(env.real_fabfile))
    shaker_instance.install_requirements()


@task
def shaker_freeze():
    """
    utility task to check current versions
    """
    local('for d in vendor/formula-repos/*; do echo -n "$d "; git --git-dir=$d/.git describe --tags 2>/dev/null || git --git-dir=$d/.git rev-parse --short HEAD; done', shell='/bin/bash')


@task
def shaker_check():
    """
    utility task to check if there are no new versions available
    """
    local('for d in vendor/formula-repos/*; do (export GIT_DIR=$d/.git; git fetch --tags -q 2>/dev/null; echo -n "$d: "; latest_tag=$(git describe --tags $(git rev-list --tags --max-count=1 2>/dev/null) 2>/dev/null || echo "no tags"); current=$(git describe --tags 2>/dev/null || echo "no tags"); echo "\tlatest: $latest_tag  current: $current"); done', shell='/bin/bash')

