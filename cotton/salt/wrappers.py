from StringIO import StringIO
from collections import OrderedDict
import yaml

from fabric.api import env, sudo, get, abort

from cotton.colors import red, yellow, blue, white


def yaml_ordered_load(stream, loader_class=yaml.Loader, object_pairs_hook=OrderedDict):
    class OrderedLoader(loader_class):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)


def smart_salt(selector, args, parse_highstate=False, timeout=60, skip_manage_down=False, prefix=''):

    if 'saltmaster' in env and env.saltmaster:
        have_saltmaster = True
    else:
        have_saltmaster = False

    if not have_saltmaster:
        skip_manage_down = True

    def manage_down():
        if not skip_manage_down:
            unresponsive = False
            remote_temp_salt_manage = sudo('mktemp')

            sudo("salt-run manage.down -t {} > {}".format(timeout, remote_temp_salt_manage))
            sudo("chmod 664 {}".format(remote_temp_salt_manage))

            output_fd_salt_manage = StringIO()
            get(remote_temp_salt_manage, output_fd_salt_manage)
            output_salt_manage = output_fd_salt_manage.getvalue()

            print(white("\nUnresponsive minions:", bold=True))
            if not output_salt_manage:
                output_salt_manage = "None"
                color = yellow
            else:
                color = red
                unresponsive = True
            print(color("\n\t{}".format(output_salt_manage.replace("\n", "\n\t")), bold=True))

            if unresponsive:
                abort("Unresponsive salt minions")

            # Tidy up if minions all ok
            sudo('rm {}'.format(remote_temp_salt_manage))

    manage_down()

    if parse_highstate:
        parsed_summary = []
        remote_temp_salt = sudo('mktemp')
        # Fabric merges stdout & stderr for sudo. So output is useless
        # Store the stdout in yaml format to a temp file and parse after

        # Salt does not return unresponsive minion information unless -v is used and since this
        # adds jid and header information it causes the yaml parser to thrown an exception.
        # Therefore run a manage.down separately to check for problematic minions

        if have_saltmaster:
            sudo("salt {} '{}' {} --out=yaml -t {} > {}".format(prefix, selector, args, timeout, remote_temp_salt))
        else:
            sudo("salt-call {} --out=yaml > {}".format(args, remote_temp_salt))

        sudo("chmod 664 {}".format(remote_temp_salt))

        output_fd_salt = StringIO()
        get(remote_temp_salt, output_fd_salt)
        output_salt = output_fd_salt.getvalue()

        failed = 0
        changed = 0
        worked = 0
        salt_yml = yaml_ordered_load(output_salt)

        for salted_host in salt_yml:
            host_fail = 0
            host_work = 0
            host_change = 0
            parsed_summary.append(blue("\n{}:".format(salted_host), bold=True))
            for salt_event in salt_yml[salted_host]:
                event = salt_yml[salted_host][salt_event]
                for salt_event_type in event:
                    if salt_event_type == "result":
                        if event[salt_event_type]:
                            worked += 1
                            host_work += 1
                        else:
                            failed += 1
                            host_fail += 1
                            parsed_summary.append(red("\tFailure: {}".format(salt_event), bold=True))
                            parsed_summary.append(red("\t Reason: {}".format(event['comment']), bold=False))
                            parsed_summary.append(red("\t  Debug: {}".format(event), bold=False))
                    elif salt_event_type == "changes" and len(event[salt_event_type]):
                        changed += 1
                        host_change += 1
                        parsed_summary.append(
                            white("\tChange: {name} - Comment: {comment}".format(
                                name=event['name'],
                                comment=event['comment']), bold=False))

            parsed_summary.append(yellow("\tSuccess: {}".format(host_work), bold=False))
            parsed_summary.append(white("\tChanged: {}".format(host_change), bold=False))
            parsed_summary.append(red("\tFailed: {}".format(host_fail), bold=False))

        parsed_summary.append(blue("\nSummary:", bold=True))
        parsed_summary.append(yellow("\tSuccess: {}".format(worked), bold=True))
        parsed_summary.append(white("\tChanged: {}".format(changed), bold=True))
        parsed_summary.append(red("\tFailed: {}".format(failed), bold=True))

        # Any failures print the yaml in full then the summary otherwise just the summary
        if failed:
            sudo("cat {}".format(remote_temp_salt))

        for summary_line in parsed_summary:
            print(summary_line)

        if failed:
            abort("Failures encountered: {}".format(failed))

        # let's cleanup but only if everything was ok
        sudo('rm {}'.format(remote_temp_salt))
    else:
        if have_saltmaster:
            sudo("salt {} '{}' {} -t {}".format(prefix, selector, args, timeout))
        else:
            sudo("salt-call {}".format(args))

    manage_down()
