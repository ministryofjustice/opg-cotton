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


def salt_call(method, args=''):
    """
    Wrapper for salt-call
    :param method: string, the salt method we are wanting to invoke
    :param args: string, the argument to pass to the salt method
    """
    sudo("salt-call {} {}".format(method, args))


# Allow us to call methods like jobs.active
def salt_run(method, args='', pty=False, quiet=False, stdout=None):
    """
    Wrapper for salt-run
    :param method: string, the salt method we are wanting to invoke
    :param args: string, the argument to pass to the salt method
    :param pty: boolean, do we want a sudo terminal
    :param quiet: boolean, do we want to suppress the output
    :param stdout: list, default None, container for our output
    """
    sudo("salt-run {} {}".format(method, args), pty=pty, quiet=quiet, stdout=stdout, combine_stderr=True)


def smart_salt(
        selector,
        args,
        parse_highstate=False,
        timeout=60,
        prefix='',
        salt_environment=None
):
    """
    Method to execute salt on a remote device

    :param selector: string selector, can be a string, compound or grain match
    :param args: string, arguments to pass to the salt command
    :param parse_highstate: boolean, default false, parse the output of the highstate
    :param timeout: int, timeout in seconds
    :param prefix: string, either -C or -G for a compound or grain match
    :param salt_environment:
    """
    if 'saltmaster' in env and env.saltmaster:
        have_saltmaster = True
    else:
        have_saltmaster = False

    if salt_environment is not None:
        prefix = "-C"
        selector = 'G@opg_stackname:{} and {}'.format(salt_environment, selector)

    if parse_highstate:
        parsed_summary = []
        remote_temp_salt = sudo('mktemp')
        # Fabric merges stdout & stderr for sudo. So output is useless
        # Store the stdout in yaml format to a temp file and parse after

        # Salt does not return unresponsive minion information unless -v is used and since this
        # adds jid and header information it causes the yaml parser to thrown an exception.
        # Therefore run a manage.down separately to check for problematic minions

        if have_saltmaster:
            sudo("salt {} {} {} --out=yaml -t {} > {}".format(prefix, selector, args, timeout, remote_temp_salt))
        else:
            sudo("salt-call {} {} --out=yaml > {}".format(args, remote_temp_salt))

        sudo("chmod 664 {}".format(remote_temp_salt))

        output_fd_salt = StringIO()
        get(remote_temp_salt, output_fd_salt)
        output_salt = output_fd_salt.getvalue()

        failed = parse_salt_output(output_salt, parsed_summary)

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


def parse_salt_output(output_salt, parsed_summary):
    """
    Parse our salt output from a yamly file and return a summary
    :param output_salt: string, yaml contents
    :param parsed_summary: list
    :return: int, the number of calls that failed
    """

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

    return failed

