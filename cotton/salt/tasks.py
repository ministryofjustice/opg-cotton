import os
import time

from fabric.api import sudo, local, task, env
from cotton.colors import green, yellow
from cotton.api import vm_task
from cotton.fabextras import smart_rsync_project, is_not_empty
from cotton.salt import get_pillar_location, smart_salt, Shaker, salt_call, salt_run


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
def highstate_complete():
    timeout = 15
    from cStringIO import StringIO
    result = StringIO()

    salt_run(method='jobs.active', stdout=result)

    if len(result.getvalue().strip()):
        print(yellow("Highstate is still running.\nPolling again in {} seconds.\n".format(timeout)))
        time.sleep(timeout)
        highstate_complete()
    else:
        print(green("Highstate complete.\n"))

    result.close()

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
    Invokes salt_rsync overriding the formula-requirements file path if specified
    '''
    __rsync_salt()
    __rsync_pillars()
    __rsync_salt_formulas()


def __rsync_salt():
    # -L will follow symlinks and pull vendor formula
    sudo("mkdir -p /srv/salt")
    smart_rsync_project('/srv/salt', 'salt/', for_user='root', extra_opts='-L', delete=True)


def __rsync_pillars():

    # Sync our project pillar to /srv/pillar
    pillar_location = get_pillar_location(parse_top_sls=False)

    base_pillar_path = '/srv/pillar'
    __create_remote_pillar_location()

    keys = []
    paths = [base_pillar_path]

    pillar_path = base_pillar_path

    smart_rsync_project(
        '{}'.format(pillar_path),
        '{}/'.format(pillar_location),
        for_user='root',
        extra_opts='-L',
        delete=True)

    # Now if we have pillar roots, lets sync them
    if 'pillar_roots' in env:
        base_root_path = '/srv'
        for pillar in env.pillar_roots:

            pillar_path = "{}/{}".format(base_root_path, os.path.split(pillar)[-1])

            dirs = os.listdir(pillar)

            if len(dirs):
                # If we have subdirectories, lets iterate them and add them independantly if they are a directory
                for root_dir in dirs:
                    if os.path.isdir("{}/{}".format(pillar, root_dir)):
                        paths.append("{}/{}".format(pillar_path, root_dir))

            paths.append(pillar_path)

            for path in paths:
                sudo("mkdir -p {}".format(path))

            smart_rsync_project(
                '{}'.format(pillar_path),
                '{}/'.format(pillar),
                for_user='root',
                extra_opts='-L',
                delete=True,
                do_not_reset_mask=True
            )

        # Only run this if we have roots set up
        keys.append({'salt_env': 'base', 'paths': paths})
        __update_master_config(keys)

    __reset_pillar_owner(base_root_path=pillar_path)


def __create_remote_pillar_location(pillar_path='/srv/pillar'):
    if is_not_empty(pillar_path):
        # Clean out this directory, if we swap between pillar_roots and non pillar_roots versions we get gruff
        sudo("rm -rf {}".format(pillar_path))

    sudo("mkdir -p {}".format(pillar_path))
    sudo("chown -R {} {}".format(env.user, pillar_path))


def __reset_pillar_owner(pillar_owner='root', base_pillar_path='/srv/pillar', base_root_path='/srv/pillar_roots'):
    # Finally we reset our pillar owner
    sudo("chown -R {} {}".format(pillar_owner, base_pillar_path))
    sudo("chown -R {} {}".format(pillar_owner, base_root_path))


def __rsync_salt_formulas():
    sudo("mkdir -p /srv/salt-formulas")
    smart_rsync_project('/srv/salt-formulas', 'vendor/_root/', for_user='root', extra_opts='-L', delete=True)


def __update_master_config(keys):
    config = []
    # Remove all the config between the blocks
    sudo("sed -i '/##PILLAR_ROOT_TOKEN_BEGIN##/,/##PILLAR_ROOT_TOKEN_END##/{//!d}' /etc/salt/master")

    config.append('pillar_roots:')

    for roots in keys:
        config.append('  {}:'.format(roots['salt_env']))
        for path in roots['paths']:
            config.append('    - {}'.format(path))

    # Write this out
    for line in config:
        line = line.replace('/', '\\/')
        sudo("sed -i 's/.*##PILLAR_ROOT_TOKEN_END##.*/{}\\n&/' /etc/salt/master".format(line))

    # Bounce the service
    sudo("stop salt-master || true && start salt-master")

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

