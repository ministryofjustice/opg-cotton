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
as paths to search in when compiling from the top.sls file. The search paths are fifo and are searched in the following order:
 * If enabled via the enviroment variable :code:`env.use_project_dir` the project directory
 * Merge paths passed as arguments via the :code:`pillar_dirs=` directive. This is a delimited string, and supports both absolute and relative paths
 * If enabled via the enviroment variable :code:`env.use_project_dir` the config directory

To pass a list of merge paths to the task you will need to implement support for a custom list format, as fabric only supports
strings as command line arguments. The easiest being `;` us for separation, then you can set the :code:`env.pillar_dirs`
using something similar to below in your projects fabfile:

.. code-block:: python

    @task
    def target_stackname(stackname='develop', pillar_dirs=None, use_project_dir=False):
        env.stackname = stackname
        env.provider_zone = 'my_provider_zone'
        env.domainname = 'develop.tld'
        env.pillar_dirs = pillar_dirs.split(';')
        env.use_project_dir = use_project_dir

This can them be called from the command line with something similar to below:

.. code-block:: bash

    $> ${FAB} -H salt -u ${RSYNC_USER_NAME} target_stackname:pillar_dirs="/path/to/project;../common_pillars/" insecure rsync

This will merge the pillars before rsyncing them to the server based on the directory structure passed through, to emulate
the more traditional behaviour of cotton, call the above code snippet as below

.. code-block:: bash

    $> ${FAB} -H salt -u ${RSYNC_USER_NAME} target_stackname:use_project_dir=True insecure rsync


pillar roots
------------

We can now support pillar roots via a command line argument, each of the pillars get uploaded to a separate directory under
/srv/pillar_roots.

To add multiple pillars for pillar_roots you need to set the :code:`env.pillar_roots` variable, this can be done similarly to merging pillars.

.. code-block:: python

    @task
    def target_stackname(stackname='develop', pillar_roots=None, use_project_dir=False):
        env.stackname = stackname
        env.provider_zone = 'my_provider_zone'
        env.domainname = 'develop.tld'
        env.pillar_roots = pillar_roots.split(';')
        env.use_project_dir = use_project_dir

.. code-block:: bash

    $> ${FAB} -H salt -u ${RSYNC_USER_NAME} target_stackname:pillar_roots="/common/data/;/more/common/data" insecure rsync

unattended high stating and grain targeting
--------------------------------------

Cotton now supports targetting on grains or compound queries. To target via a grain you can use the following

.. code-block:: bash

    $> ${FAB} -H salt -u ${RSYNC_USER_NAME} target_stackname insecure highstate:prefix='-G',selector='${ROLE1}'


To target via a compound match

.. code-block:: bash

    $> ${FAB} -H salt -u ${RSYNC_USER_NAME} target_stackname:use_project_dir=True insecure highstate:prefix='-C',selector='@${ROLE1} or @{$ROLE2}'

Finally you can use a remote_highstate call to now get the system to highstate without any intervention

.. code-block:: bash

    $> ${FAB} -H salt -u ${RSYNC_USER_NAME} target_stackname insecure unattended_highstate

highstate polling
-----------------

We can poll if a highstate is completed now by running a command against the salt-master from the build environment

.. code-block:: bash

    $> ${FAB} -H salt -u ${RSYNC_USER_NAME} target_stackname highstate_complete

commit change sets from jenkins
-------------------------------

We now have a task to rebase master and commit changes from jenkins jobs, we can override the author to commit the files
This has to be run from the fabfile location however as the library binds to the hidden .git directory there. Files have to
be relative to this directory as well

.. code-block:: bash
    # Commit with defaults for user and email
    $> ${FAB} commit_build_files:changes='path/to/file1 another/path/file2', message='My commit message'

    # Commit with provided user and email
    $> ${FAB} commit_build_files:changes='path/to/file1 another/path/file2',message='My commit message',author='my author',author_email='me@domain.tld'

tests
-----

run tests with the following command

.. code-block:: bash

    $ sh runtests.sh
