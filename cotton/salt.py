"""
root/
|-- application-deployment/
|   `-- fabfile.py
`-- config/projects/{project}/pillar/
"""

import os
import sys
import pkgutil
import tempfile
import yaml
import json

from StringIO import StringIO
from collections import defaultdict
from collections import OrderedDict
from pprint import pformat

from fabric.api import env, put, sudo, task, get, abort

from cotton.colors import red, yellow, green, blue, white
from cotton.api import vm_task, get_provider_zone_config


def get_unrendered_pillar_location():
    """
    returns local pillar location
    """
    assert 'project' in env
    assert env.project

    # TODO: render pillar template to stdout / temp directory to sync it? (or just generate one file for remote)
    fab_location = os.path.dirname(env.real_fabfile)
    pillar_location = os.path.abspath(os.path.join(fab_location, '../config/projects/{}/pillar'.format(env.project)))

    return pillar_location


def _get_projects_location():
    fab_location = os.path.dirname(env.real_fabfile)
    return os.path.abspath(os.path.join(fab_location, '../config/projects/'))


def get_rendered_pillar_location(pillar_dir=None, projects_location=None, parse_top_sls=True):
    """
    Returns path to rendered pillar.
    Use to render pillars written in jinja locally not to upload unwanted data to network.

    i.e. you can use constructs like:
    {% include 'opg-lpa-dev/pillar/services.sls' %}

    If you want salt to later render pillars with grain context use constructs like:
    {% raw %} {{grains.get('roles')}} {% endraw %}
    {{" {{grains.get('roles')}} "}}

    To allow for server side templating of top.sls, you will need set: `parse_top_sls=False`

    In case there is no top.sls in pillar root than it returns: None
    """
    from jinja2 import Environment
    from jinja2 import FileSystemLoader
    from jinja2.exceptions import TemplateNotFound

    if projects_location is None:
        projects_location = _get_projects_location()

    if pillar_dir is None:
        if "pillar_dir" in env:
            pillar_dir = env.pillar_dir
        else:
            assert env.project, "env.project or env.pillar_dir must be specified"
            pillar_dir = os.path.join(projects_location, env.project, 'pillar')

    jinja_env = Environment(
        loader=FileSystemLoader([pillar_dir, projects_location]))

    files_to_render = []
    dest_location = tempfile.mkdtemp()

    if parse_top_sls:
        # let's parse top.sls to only select files being referred in top.sls
        try:
            top_sls = jinja_env.get_template('top.sls').render(env=env)
        except TemplateNotFound:
            raise RuntimeError("Missing top.sls in pillar location. Skipping rendering.")

        top_content = yaml.load(top_sls)

        filename = os.path.join(dest_location, 'top.sls')
        with open(filename, 'w') as f:
            print("Pillar template_file: {} --> {}".format('top.sls', filename))
            f.write(top_sls)

        for k0, v0 in top_content.iteritems():
            for k1, v1 in v0.iteritems():
                for file_short in v1:
                    # We force this file to be relative in case jinja failed rendering
                    # a variable. This would make the filename start with / and instead of
                    # writing under dest_location it will try to write in /
                    if isinstance(file_short, str):
                        files_to_render.append('./' + file_short.replace('.', '/') + '.sls')
    else:
        # let's select all files from pillar directory
        for root, dirs, files in os.walk(pillar_dir):
            rel_path = os.path.relpath(root, pillar_dir)
            for file_name in files:
                files_to_render.append(os.path.join(rel_path, file_name))

    # render and save templates
    for template_file in files_to_render:
        filename = os.path.abspath(os.path.join(dest_location, template_file))
        print("Pillar template_file: {} --> {}".format(template_file, filename))
        if not os.path.isdir(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        try:
            template_rendered = jinja_env.get_template(template_file).render(env=env)
        except TemplateNotFound:
            template_rendered = ''
            print(red("Pillar template_file not found: {} --> {}".format(template_file, filename)))
        with open(os.path.join(dest_location, template_file), 'w') as f:
            f.write(template_rendered)

    print(green("Pillar was successfully rendered in: {}".format(dest_location)))
    return dest_location


get_pillar_location = get_rendered_pillar_location


@vm_task
def reset_roles(salt_roles=None):
    """
    Reset salt role grains to the values specified in the provider_zone
    configuration for the current host
    """
    if isinstance(salt_roles, basestring):
        salt_roles = salt_roles.split(';')
    elif salt_roles is None:
        assert env.vm
        info = env.provider.info(env.vm)
        salt_roles = info.get('roles', [])
    sudo('salt-call --local grains.setval roles "{}"'.format(salt_roles))


def _reconfig_minion(salt_server):
    """

    """
    assert salt_server
    assert env.vm_name
    assert env.domainname
    # The base-image may have a minion_id already defined - delete it
    sudo('/bin/rm -f /etc/salt/minion_id')

    if '.' in env.vm_name:
        fqdn = env.vm_name
    else:
        fqdn = "{}.{}".format(env.vm_name, env.domainname)
    minion_contents = {
        'master': salt_server,
        'id': str(fqdn),
    }
    put(StringIO(fqdn), '/etc/hostname', use_sudo=True, mode=0644)
    sudo("echo '127.0.0.1 {}' >> /etc/hosts".format(fqdn))
    sudo("hostname {}".format(fqdn))


    minion_configIO = StringIO(repr(minion_contents))
    env.sudo_user = 'root'
    sudo("mkdir -p /etc/salt")
    put(minion_configIO, "/etc/salt/minion", use_sudo=True, mode=0644)
    sudo("/bin/chown root:root /etc/salt/minion")


def _bootstrap_salt(master=None, flags='', install_type='', salt_roles=None):
    if master is None:
        (server,) = env.provider.filter(name="master")
        if server:
            master_info = env.provider.info(server)
            master = master_info['ip']
        else:
            raise ValueError("No salt master hostname provided and no server 'master' found")

    _reconfig_minion(master)
    bootstrap_fh = StringIO(pkgutil.get_data(__package__, 'share/bootstrap-salt.sh'))
    put(bootstrap_fh, "/tmp/bootstrap-salt.sh")
    sudo("bash /tmp/bootstrap-salt.sh {} -A {} {}".format(flags, master, install_type))
    reset_roles(salt_roles)


@vm_task
def bootstrap_minion(**kwargs):
    """
    Bootstrap a salt minion and connect it to the master in the current
    enviroment.

    It relies upon get_provider_zone_config_ to have a host called 'master'. It
    will also set the roles via `reset_roles`_ funciton.

    An example of the provider config project.yaml::

        provider_zones:
          mv_project_staging2:
            driver: static
            domainname: staging2.my_project
            hosts:
              - name: jump
                ip: 10.3.31.10
                roles: [ jump ]
              - name: master
                ip: 10.3.31.11
                roles: [ master ]
              - name: monitoring-01
                ip: 10.3.31.20
                roles: [ monitoring.server ]
                aliases: [ monitoring.local, sensu.local, graphite.local ]


    ``roles`` is the authoritative list of salt roles to apply to this box.

    ``aliases`` can be used by putting this snippet in your pillar/hosts.yaml file::

        hosts:
        {%- for host in env.zone_config['hosts'] %}
          {{ host['ip'] }}:
            - {{ host['name'] }}.{{ env.environment }}
            {% for alias in host['aliases'] -%}
            - {{ alias }}
            {% endfor %}
        {% endfor -%}

    """
    _bootstrap_salt(**kwargs)


@vm_task
def bootstrap_master(salt_roles=None, master='localhost', flags='-M', **kwargs):
    """
    Bootstrap a minimal salt master on the current server (as configued via
    ``workon``).

    """
    # One extra step = push master config file
    master_conf_fh = StringIO(pkgutil.get_data(__package__, 'share/bootstrap_master.conf'))
    sudo("mkdir -p /etc/salt")
    put(master_conf_fh, "/etc/salt/master", use_sudo=True, mode=0644)
    sudo("/bin/chown root:root /etc/salt/master")

    # Pass the -M flag to ensure master is created
    _bootstrap_salt(master=master, flags=flags, salt_roles=salt_roles, **kwargs)


@vm_task
def salt(selector, args, parse_highstate=False, timeout=60, skip_manage_down=False):
    """
    `salt` / `salt-call` wrapper that:
    - checks if `env.saltmaster` is set to select between `salt` or `salt-call` command
    - checks for output state.highstate and aborts on failure
    param selector: i.e.: '*', -G 'roles:foo'
    param args: i.e. state.highstate
    param parse_highstate: If True then salt output is yaml and parsed for Successes/Changes/Failures
    param timeout: Passed to salt as a timeout value (-t) in seconds
    param skip_manage_down: If True then skip the check to run a manage.down to establish unresponsive minions
    """

    parsed_summary = []

    def manage_down():
      if not skip_manage_down:
        unresponsive = False
        remote_temp_salt_manage = sudo('mktemp')

        sudo("salt-run manage.down -t {} > {}".format(timeout, remote_temp_salt_manage))
        sudo("chmod 664 {}".format(remote_temp_salt_manage))

        output_fd_salt_manage = StringIO()
        get(remote_temp_salt_manage, output_fd_salt_manage)
        output_salt_manage = output_fd_salt_manage.getvalue()

        parsed_summary.append(white("\nUnresponsive minions:", bold=True))
        if not output_salt_manage:
          output_salt_manage = "None"
          color = yellow
        else:
          color = red
          unresponsive = True
        parsed_summary.append(color("\n\t{}".format(output_salt_manage.replace("\n","\n\t")), bold=True))

        assert (not unresponsive),"Unresponsive salt minions: %s" % ''.join(parsed_summary)

        # Tidy up if minions all ok
        sudo('rm {}'.format(remote_temp_salt_manage))

    if parse_highstate:
        remote_temp_salt = sudo('mktemp')
        # Fabric merges stdout & stderr for sudo. So output is useless
        # Store the stdout in yaml format to a temp file and parse after

        # Salt does not return unresponsive minion information unless -v is used and since this
        # adds jid and header information it causes the yaml parser to thrown an exception.
        # Therefore run a manage.down separately to check for problematic minions

        if 'saltmaster' in env and env.saltmaster:
          manage_down()
          sudo("salt {} {} --out=yaml -t {} > {}".format(selector, args, timeout, remote_temp_salt))
          manage_down()
        else:
            sudo("salt-call {} --out=yaml > {}".format(args, remote_temp_salt))

        sudo("chmod 664 {}".format(remote_temp_salt))

        output_fd_salt = StringIO()
        get(remote_temp_salt, output_fd_salt)
        output_salt = output_fd_salt.getvalue()

        failed = 0
        changed = 0
        worked = 0
        salt_yml = yaml.safe_load(output_salt)

        for salted_host in salt_yml:
          host_fail = 0
          host_work = 0
          host_change = 0
          parsed_summary.append(blue("\n{}:".format(salted_host), bold=True))
          for salt_event in salt_yml[salted_host]:
            event = salt_yml[salted_host][salt_event]
            for salt_event_type in event:
              if salt_event_type == "result":
                if event[salt_event_type] is False:
                  failed +=1
                  host_fail += 1
                  parsed_summary.append(red("\tFailure: {}".format(salt_event), bold=True))
                  if len(event['changes']) == 0:
                    parsed_summary.append(red("\tReason: {}".format(event['comment']), bold=False))
                  else:
                    parsed_summary.append(red("\tReason: {} (rc={} ; error={})".format(event['comment'],
                          event['changes']['retcode'],event['changes']['stderr']), bold=False))
                elif event[salt_event_type] is True:
                  worked += 1
                  host_work += 1
              if salt_event_type == "changes" and len(event[salt_event_type]) != 0:
                changed += 1
                host_change += 1
                parsed_summary.append(white("\tChange: {}".format(event['comment']), bold=False))

          parsed_summary.append(yellow("\tSuccess: {}".format(host_work), bold=False))
          parsed_summary.append(white("\tChanged: {}".format(host_change), bold=False))
          parsed_summary.append(red("\tFailed: {}".format(host_fail), bold=False))

        parsed_summary.append(blue("\nSummary:",bold=True))
        parsed_summary.append(yellow("\tSuccess: {}".format(worked), bold=True))
        parsed_summary.append(white("\tChanged: {}".format(changed), bold=True))
        parsed_summary.append(red("\tFailed: {}".format(failed), bold=True))

        # Any failures print the yaml in full then the summary otherwise just the summary
        if failed > 0:
          sudo("cat {}".format(remote_temp_salt))

        for summary_line in parsed_summary:
          print(summary_line)

        assert (failed == 0),"Failures encountered: %d" % failed

        # let's cleanup but only if everything was ok
        sudo('rm {}'.format(remote_temp_salt))
    else:
        if 'saltmaster' in env and env.saltmaster:
          manage_down()
          sudo("salt {} {} -t {}".format(selector, args, timeout))
          manage_down()
        else:
            sudo("salt-call {}".format(args))

