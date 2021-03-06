"""
a provider for "Static" server

basically it assumes that server is there

expects ~/.cotton.yaml

provider_zone:
  my_static_name:
    driver: static
    hosts:
      - name: master
        ip: 1.2.3.4

"""
from __future__ import print_function
from cotton.colors import yellow
from cotton.provider.driver import Provider
from cotton.config import get_provider_zone_config


class StaticProvider(Provider):

    connection = None

    def __init__(self, **kwargs):
        """
        nothing to do
        """
        pass

    def status(self):

        zone_config = get_provider_zone_config()
        return zone_config['hosts']

    def filter(self, **kwargs):
        """
        return: list of objects matching filter args
        typically provide should support filter 'name'='foo'
        """
        instances = []

        if 'name' in kwargs:
            name = kwargs['name']

            zone_config = get_provider_zone_config()
            assert zone_config['driver'] == 'static'
            for host_spec in zone_config['hosts']:
                if host_spec['name'] == name:
                    print("selected static instance: {}".format(host_spec['name']))
                    instances.append(host_spec)
                    break
            else:
                print(yellow("Warning: {} not found!".format(name), bold=True))
        else:
            raise NotImplementedError()

        return instances

    def info(self, server):
        """
        returns dictionary with info about server
        """
        # Clone it to make sure people don't change it unintentionally
        return dict(server)

    def host_string(self, server):
        return self.info(server)["ip"]
