"""
salt related tasks
"""
import os
import time
import tempfile
import re

from fabric.api import sudo, local, task, env, put
from cotton.colors import green, yellow
from cotton.api import vm_task
from cotton.fabextras import smart_rsync_project
from cotton.salt import get_pillar_location, smart_salt, Shaker, salt_call, salt_run
from yaml import safe_load, safe_dump
from cStringIO import StringIO

@vm_task
def salt(
        selector="'*'",
        args='state.highstate',
        parse_highstate=False,
        timeout=60,
        prefix='',
        salt_environment=None
):
    """
    `salt` / `salt-call` wrapper that:
    - checks if `env.saltmaster` is set to select between `salt` or `salt-call` command
    - checks for output of state.highstate / state.sls and aborts on failure
    param selector: i.e.: '*', -G 'roles:foo'
    param args: i.e. state.highstate
    param parse_highstate: If True then salt output is yaml and parsed for
        Successes/Changes/Failures. Works for both state.highstate and state.sls
    param timeout: Passed to salt as a timeout value (-t) in seconds
    """
    smart_salt(
        selector=selector,
        args=args,
        parse_highstate=parse_highstate,
        timeout=timeout,
        prefix=prefix,
        salt_environment=salt_environment
    )


@vm_task
def unattended_highstate():
    """
    Fire a custom event to highstate the environments
    """
    salt_event('salt/custom/start_highstate')


@vm_task
def highstate_complete():
    """
    Poll jobs active waiting for it to become empty after an unattended_highstate was started
    """
    timeout = 15
    result = StringIO()
    salt_run(method='jobs.active', stdout=result)

    while len(result.getvalue().strip()):
        result.truncate(0)
        print yellow("Highstate is still running.\nPolling again in {} seconds.\n".format(timeout))
        time.sleep(timeout)
        salt_run(method='jobs.active', stdout=result)

    print green("Highstate complete.\n")

    result.close()

@vm_task
def salt_event(args):
    """
    Fire a custom reactor event
    :param args: tag for the custom event
    """
    salt_call('event.send', args)


@vm_task
def rsync(target=None):
    """
    Invokes salt_rsync overriding the formula-requirements file path if specified
    """
    __rsync_salt()
    __rsync_pillars(target)
    __rsync_salt_formulas()


def __rsync_salt():
    """
    rsync the contents of the salt directories
    """
    # -L will follow symlinks and pull vendor formula
    sudo("mkdir -p /srv/salt")
    smart_rsync_project('/srv/salt', 'salt/', for_user='root', extra_opts='-L', delete=True)


def __rsync_pillars(target):
    """
    rsync the contents of the pillar directories
    """
    # Sync our project pillar to /srv/pillar
    pillar_location = get_pillar_location(parse_top_sls=False, target=target)

    base_pillar_path = '/srv/pillar'
    if target:
        base_pillar_path = '{}/{}'.format(base_pillar_path, target)

    keys = {}
    paths = [base_pillar_path]

    pillar_path = base_pillar_path

    smart_rsync_project(
        '{}'.format(pillar_path),
        '{}/'.format(pillar_location),
        for_user='root',
        extra_opts='-L',
        delete=True,
        target=target
    )

    # Now if we have pillar roots, lets sync them
    if 'pillar_roots' in env:
        base_root_path = '/srv'
        for pillar in env.pillar_roots:

            if 'pillar_roots' in os.path.split(pillar)[-1]:
                root_path = base_root_path
            else:
                root_path = '{}/pillar_roots'.format(base_root_path)

            pillar_path = "{}/{}".format(root_path, os.path.split(pillar)[-1])

            dirs = os.listdir(pillar)

            if len(dirs):
                # If we have subdirectories, lets iterate them
                # and add them independently if they are a directory
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
        common_pillars = [path for path in paths if path != '/srv/pillar']
        keys['base'] = common_pillars
        for pillar_dir in env.pillar_dirs:
            if 'pillar' in pillar_dir:
                stack_name = os.path.basename(pillar_dir)
                keys[stack_name] = ["{}/{}/{}".format(
                    base_root_path,
                    'pillar',
                    stack_name
                )] + common_pillars
    __reset_pillar_owner(base_root_path=pillar_path)
    __update_master_config(keys, target)


def __reset_pillar_owner(
        pillar_owner='root',
        base_pillar_path='/srv/pillar',
        base_root_path='/srv/pillar_roots'
):
    """
    Resets the owner on the pillars after a rsync, we need to defer
    this to the end when synching multiple directories
    :param pillar_owner: string, owner
    :param base_pillar_path: string path to pillar root
    :param base_root_path:  string path to pillar_roots root
    """
    # Finally we reset our pillar owner
    sudo("chown -R {} {}".format(pillar_owner, base_pillar_path))
    sudo("chown -R {} {}".format(pillar_owner, base_root_path))


def __rsync_salt_formulas():
    """
    Upload our salt formulas
    """
    sudo("mkdir -p /srv/salt-formulas")
    smart_rsync_project(
        '/srv/salt-formulas',
        'vendor/_root/',
        for_user='root',
        extra_opts='-L',
        delete=True
    )

@vm_task
def __update_master_config(keys, target):
    """
    Updates the master config if needed, adds pillar_roots to the config and restarts the server
    :param keys: List of keys containing pillar_roots
    """
    refresh = False
    restart = False

    # read master config into dict
    master_data = StringIO()
    sudo('cat /etc/salt/master|grep -v ^# | grep -v ^$', stdout=master_data)
    salt_output = master_data.getvalue().strip()
    yaml_string = ''
    pattern = re.compile(r'(\W+.*out:)')
    for line in salt_output.split('\n'):
        yaml_string = "{}\n{}".format(yaml_string, re.sub(pattern, '', line))
    master_config = safe_load(yaml_string)
    # master_config = safe_load(master_data.getvalue())
    current_pillar_roots = master_config['pillar_roots'] if 'pillar_roots' in master_config else []
    new_pillar_roots = keys
    if target is not None and target not in new_pillar_roots:
        print "[WARN] Invalid target environment: {} \n Not updating salt configuration".format(target)
        return True

    if target and target not in current_pillar_roots:
        master_config['pillar_roots'] = new_pillar_roots
        restart = True
    else:
        refresh = True

    if restart:
        try:
            tmp_dir = tempfile.mkdtemp()
            master_config_file = '{}/master.auto'.format(tmp_dir)
            with open(master_config_file, 'w') as master_file:
                master_file.write(safe_dump(master_config, default_flow_style=False))
            put(master_file.name, 'master.auto')
            local('rm -rf {}'.format(tmp_dir))
            sudo('mv  -v master.auto /etc/salt/master', stdout=master_data)
            print "{}".format(master_data.getvalue())

            restart_service('salt-master')
            time.sleep(30)
        except Exception as err:
            print str(err)
    elif refresh:
        print 'Refreshing pillar cache'
        if target:
            print 'Target stack: {}'.format(target)
            reload_pillar(selector='opg_stackname:{}'.format(target), prefix='-G')
        else:
            reload_pillar()


@vm_task
def restart_service(service_name):
    """
    Remote execution call to restart a service, tries to asscertain the correct call
    :param service_name: string
    :return:
    """
    # Bounce the service
    result = StringIO()

    sudo("stat /proc/1/exe | awk '/systemd/' {print NF} | wc -l", stdout=result)

    if result.getvalue().strip() != '0':
        cmd = "service {} restart".format(service_name)
    else:
        cmd = "stop {} || true && start {}".format(service_name, service_name)

    sudo(cmd)


def reload_pillar(selector="'*'", prefix='', salt_environment=None):
    """
    Reload our targets pillar data
    :param selector: String for selector, defaults to '*'
    :param prefix: String for selector type, default ''
    :param salt_environment: string for our target environment, default None
    :return:
    """
    salt(
        selector=selector,
        args='saltutil.refresh_pillar',
        prefix=prefix,
        salt_environment=salt_environment
    )


def clear_cache(selector="'*'", prefix='', salt_environment=None):
    """
    Clear our targets cache
    :param selector: String for selector, defaults to '*'
    :param prefix: String for selector type, default ''
    :param salt_environment: string for our target environment, default None
    :return:
    """
    salt(
        selector=selector,
        args='saltutil.clear_cache',
        prefix=prefix,
        salt_environment=salt_environment
    )


@vm_task
def refresh_pillars(selector="'*'", prefix='', salt_environment=None):
    """
    Wrapper for clear_cache and reload_pillar
    :param selector: String selector
    :param prefix: String used for compound or grain matches
    :param salt_environment: string representing our target environment
    :return:
    """
    print yellow("Clearing pillar cache")
    clear_cache(
        selector=selector,
        prefix=prefix,
        salt_environment=salt_environment
    )
    print yellow("Refreshing pillar data")
    reload_pillar(
        selector=selector,
        prefix=prefix,
        salt_environment=salt_environment
    )


@vm_task
def update(selector="'*'", skip_highstate=False, parse_highstate=False, timeout=60):
    """
    shaker, rsync, highstate
    """
    shaker()
    rsync()
    if skip_highstate == 'False' or not skip_highstate:
        highstate(selector, parse_highstate, timeout)


@vm_task
def highstate(
        selector="'*'",
        parse_highstate=False,
        timeout=60,
        prefix='',
        salt_environment=None
):
    """
    Highstate the target node(s)
    :param selector: defaults to all, can get a wildcard or with the use of the prefix
    parameter, grain or compound match
    :param parse_highstate: boolean, default False, parse the output and summarise our errors
    :param timeout: timeout in seconds
    :param prefix: string, default empty, can be -C or -G for compound or grain matches
    :param salt_environment: string, default None, if set will force a compound match (-C)
    """
    salt(selector, 'state.highstate', parse_highstate, timeout, prefix, salt_environment)


@vm_task
def remove_dead_minions():
    """
    Allows us to remove all down minions from the master
    """
    salt_run(method='manage.down', args='removekeys=True')


@task
def commit_build_files(
        changes='',
        message='',
        author='OPG Cotton',
        author_email='opg-cotton@nowhere',
        target_branch="master"
):
    """
    Commit changed files to the git repository, especially useful for jenkins and terraform
    :param changes: string, paths to the files to commit, space separated
    :param message: string, the commit message
    :param author: string, the commit author
    :param author_email: string, the commit author's email
    :param target_branch: string, the target branch
    """
    changes = list(set(changes.split(' ')))
    from cotton.gitutils import GitUtilities
    gutils = GitUtilities(
        changes=changes,
        message=message,
        root_path=os.path.dirname(env.real_fabfile),
        author=author,
        author_email=author_email,
        target_branch=target_branch
    )

    gutils.commit_change_set()


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
    local(
        'for d in vendor/formula-repos/*; '
        'do echo -n "$d "; '
        'git --git-dir=$d/.git describe --tags 2>/dev/null '
        ' || git --git-dir=$d/.git rev-parse --short HEAD; done',
        shell='/bin/bash'
    )


@task
def shaker_check():
    """
    utility task to check if there are no new versions available
    """
    local(
        'for d in vendor/formula-repos/*; '
        'do (export GIT_DIR=$d/.git; git fetch --tags -q 2>/dev/null; '
        'echo -n "$d: "; '
        'latest_tag=$(git describe --tags '
        '$(git rev-list --tags --max-count=1 2>/dev/null) 2>/dev/null || echo "no tags"); '
        'current=$(git describe --tags 2>/dev/null || echo "no tags"); '
        'echo "\tlatest: $latest_tag  current: $current"); done',
        shell='/bin/bash'
    )


@vm_task
def healthcheck():
    """
    run commands to show state of stack
    """
    salt(args='test.ping')
    salt(args='cmd.run "docker ps"')
    salt(args='cmd.run "df -hl && echo && btrfs filesystem show"')


@task
def workon_short(workon_short):
    from cotton.api import workon
    env.vm_name = '{workon_short}.{stackname}.{domainname}'.format(
        workon_short=workon_short,
        stackname=env.stackname,
        domainname=env.domainname
    )
    workon(env.vm_name)

