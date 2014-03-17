"""
basic api

it's recommended to wrap every task with decorator @workon_fallback

@task
@workon_fallback
def mytask():
    pass

TODO: create task decorator that does the above

"""
from __future__ import print_function
import pprint
import time
from functools import wraps
from cotton.config import get_provider_zone_config

from cotton.provider.driver import provider_class
from cotton.common import *
from cotton.colors import *


def load_provider(func):
    """
    Decorator for all functions that need access to cloud
    Sets: env.provider to initialized driver object
    Make sure that env.provider_zone is initialized beforehand
    """
    @wraps(func)
    def inner(*args, **kwargs):
        start_time = time.time()

        get_provider_connection()
        ret = func(*args, **kwargs)

        end_time = time.time()
        print(yellow("Duration: {:.2f}s".format(end_time - start_time)))
        return ret
    return inner


def get_provider_connection():
    """
    returns initialized provider object and caches it in env.provider
    """
    zone_config = get_provider_zone_config()
    if not 'provider' in env or not env.provider:
        p_class = provider_class(zone_config['driver'])
        env.provider = p_class(**zone_config)
    return env.provider


def workon_fallback(func):
    """
    Decorator loads provider and configures current host based on env.vm_name
    unless env.vm is already set

    updated variables:
    env.provider
    env.vm
    env.host_string
    env.host
    env.key_filename
    env.user if in provisioning mode
    """

    @wraps(func)
    def inner(*args, **kwargs):
        start_time = time.time()

        get_workon_fallback()
        ret = func(*args, **kwargs)

        end_time = time.time()
        print(yellow("Duration: {:.2f}s".format(end_time - start_time)))
        return ret
    return inner


def get_workon_fallback():
    """
    loads provider and configures current host based on env.vm_name
    unless env.vm is already set

    updated variables:
    env.provider
    env.vm
    env.host_string
    env.host
    env.key_filename
    env.user if in provisioning mode
    """
    if 'vm' in env and env.vm:
        return
    assert env.vm_name
    workon_vm_name(env.vm_name)


def workon_vm_name(name):
    """
    updates fabric env context to work on selected vm
    sets:
    env.vm
    env.host_string
    """
    get_provider_connection()
    vms = env.provider.filter(name=name)
    assert len(vms) == 1
    workon_vm_object(vms[0])


def workon_vm_object(server):
    get_provider_connection()
    env.vm = server
    env.host_string = env.provider.host_string(env.vm)
    env.host = env.provider.host_string(env.vm)
    apply_configuration()


@task
@load_provider
def create(name=None, size=None):
    if size:
        print(red("size argument for cotton.api.create is deprecated and will be removed shortly"))
    from cotton.fabextras import wait_for_shell
    vm = env.provider.create(name=name)
    workon_vm_object(vm)
    wait_for_shell()


@task
@workon_fallback
def destroy():
    env.provider.terminate(env.vm)


@task
@workon_fallback
def info():
    pprint.pprint(env.provider.info(env.vm))


@task
@load_provider
def status():
    #TODO: format output
    statuses = env.provider.status()
    for line in statuses:
        pprint.pprint(line)


@task
@load_provider
def filter(**kwargs):
    """
    supported args:
    name
    """
    hosts = env.provider.filter(**kwargs)
    assert len(hosts) == 1
    workon_vm_object(hosts[0])


@task
@load_provider
def workon(name=None):
    """
    shortcut to filter host based on name (falls back to env.vm_name)
    """
    if name is None and 'vm_name' in env and env.vm_name:
        name = env.vm_name
    hosts = env.provider.filter(name=name)
    assert len(hosts) == 1
    workon_vm_object(hosts[0])
