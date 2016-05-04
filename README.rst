cotton
======

Project independent shared fabric extensions to bootstrap first VM.

It solves three problems:
 - how to easily reach and manage VM
 - how to store
   - shared organisation config
   - shared project config
   - user unique/confidential config (typically used to store credentials only)

Depends on following fabric env variables::

    env.provider_zone = 'aws_dev'
    env.project = 'foo-dev'  # can also be a path
    env.vm_name = 'foo.master'

    #uncomment to always use shared provisioning key (only for early dev)
    env.provisioning = True


Environment is provider configuration.


Assumes that your config directory is next to directory containing fabfile.py::

    root/
    |-- application-deployment/
    |   `-- fabfile.py
    |
    |-- ~/.cotton.yaml / ${COTTON_CONFIG}
    |-- config/projects/{env.project}/cotton.yaml
    ...
    |-- config/projects/{env.project|split('/')[1]}/cotton.yaml
    |-- config/projects/{env.project|split('/')[0]}/cotton.yaml
    |-- config/projects/cotton.yaml
    |-- config/cotton.yaml
    |-- application-deployment/vagrant/cotton.yaml  # deprecated in favour to application-deployment/cotton.yaml
    `-- application-deployment/cotton.yaml

    I.e.:
    env.project = nomis/pvb/production

    cotton.yaml search path will look like:
    root/
    |
    |-- ~/.cotton.yaml / ${COTTON_CONFIG}
    |
    |-- config/projects/nomis/pvb/production/cotton.yaml
    |-- config/projects/nomis/pvb/cotton.yaml
    |-- config/projects/nomis/cotton.yaml
    |
    |-- config/projects/cotton.yaml
    |-- config/cotton.yaml
    |
    `-- application-deployment/cotton.yaml


example ~/.cotton.yaml::

    provider_zones:
      aws_dev:
        driver: aws
        aws_access_key_id: 'TBV'
        aws_secret_access_key: 'TBD'
        ssh_key: /Users/aceventura/.ssh/default
      my_static_name:
        driver: static
        hosts:
          - name: master
            ip: 1.2.3.4
          - name: master-staging
            ip: 1.2.3.5
      aws_staging:
        provisioning_ssh_key: ../config/default.pem
        provisioning_ssh_key_name: default
        provisioning_user: ubuntu
        gateway: 1.2.3.4
        region_name: eu-west-1
        driver: aws


driver status
-------------

:aws: fully implemented
:static: fully implemented (a good fallback if api access is not available)

merging pillars
---------------

We now have the ability to specify multiple pillar paths on the source machine, these are loaded into the Jinja environment
as paths to search in when compiling from the top.sls file. The search paths are fifo and are searched in the following order
 * config project specific path
 * merge paths (if they exist, passed as arguments)
 * all config project paths


To pass a list of merge paths to the task you will need to implement support for a custom list format, as fabric only supports
strings as command line arguments. The easiest being `;` us for separation, then you can set the :code:`env.pillar_roots`
using something similar to below:

.. code-block:: python

    if args is not None:
        env.pillar_roots = args.split(';')


tests
-----

run tests with the following command

.. code-block:: bash

    $python setup.py test
