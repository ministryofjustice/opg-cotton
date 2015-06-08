from cotton.salt import smart_salt
from fabric.api import env
import argparse


def argparser_parsed_salt(add_selector=False):
    """
    create arg parser for parsed-salt(*) command line scripts
    """
    parser = argparse.ArgumentParser(description="Tags git repository with next release seq_number")
    parser.add_argument('--skip-parse',
                        help='Skip parsing output (function assumes you are calling state.sls/state.highstate)',
                        action="store_true")
    parser.add_argument('--timeout', default=60,
                        help='Timeout (default: %(default)s)')
    parser.add_argument('--skip-manage-down', default=False,
                        help='Skip verification if host are reachable',
                        action="store_true")
    if add_selector:
        parser.add_argument('selector',
                            help="I.e. '*'")
    parser.add_argument('args',
                        nargs='+',
                        help="I.e. state.sls foo.bar")
    return parser


def parsed_salt_call():
    """
    using fabric it ssh to localhost and calls `salt-call ...`
    """
    env.host_string = 'localhost'
    parser = argparser_parsed_salt()
    args = parser.parse_args()
    smart_salt(None, args=' '.join(args.args), parse_highstate=not args.skip_parse, timeout=args.timeout, skip_manage_down=args.skip_manage_down)


def parsed_salt():
    """
    using fabric it ssh to localhost and calls `salt ...`
    """
    env.host_string = 'localhost'
    env.saltmaster = True
    parser = argparser_parsed_salt(add_selector=True)
    args = parser.parse_args()
    smart_salt(selector=args.selector, args=' '.join(args.args), parse_highstate=not args.skip_parse, timeout=args.timeout, skip_manage_down=args.skip_manage_down)
