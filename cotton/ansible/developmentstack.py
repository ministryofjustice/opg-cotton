from cotton.colors import yellow, green, red
import shutil
from os import path
import yaml
from datetime import datetime, timedelta


class TargetViolationError(Exception):
    """
    Custom exception
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class DevelopmentStack(object):

    target_stackname = ''

    def remove_development_stack(
            self,
            target_stackname,
            sources_section=''
    ):
        """
        Remove a target development stack completely
        :param target_stackname:
        :param sources_section:
        :return:
        """

        target_stackname = self.__generate_stack_name(target_stackname)
        self.is_protected_stack()

        print(
            yellow(
                "Deleting development stack {}".format(target_stackname)
            )
        )

        if path.exists('ansible/{}'.format(target_stackname)) and \
                path.exists('pillar/{}'.format(target_stackname)):

            shutil.rmtree('ansible/{}'.format(target_stackname))
            shutil.rmtree('pillar/{}'.format(target_stackname))

            # add new development stack to the truth file
            self.__remove_stack_from_sources_file(
                'pillar/{}'.format(target_stackname),
                sources_section
            )
        else:
            print(yellow("Feature stack does not exist"))

    def create_development_stack(
            self,
            target_stackname,
            source_stackname='aws-develop',
            sources_section='',
            lifetime_days=5
    ):
        """
        Creates a target stack based on the aws-develop stack
        :param target_stackname: string
        :param source_stackname: string
        :param sources_section: string target for non production environment
        :param lifetime_days:
        :return:
        """
        self.target_stackname = self.__generate_stack_name(target_stackname)

        if 'prod' in sources_section or 'production' in sources_section:
            raise TargetViolationError('This feature is for development purposes and supports only'
                                       ' non production targets')

        print(
            yellow(
                "Creating {} environment {} from {}".format(
                    sources_section,
                    self.target_stackname,
                    source_stackname
                )
            )
        )

        if not path.exists('ansible/{}'.format(self.target_stackname)):

            # Copy ansible feature to new stack
            print(green('Creating ansible/{}'.format(self.target_stackname)))
            shutil.copytree(
                src='ansible/{}'.format(source_stackname),
                dst='ansible/{}'.format(self.target_stackname)
            )

            # Copy pillar to new stack
            print(green('Creating pillar/{}'.format(self.target_stackname)))
            shutil.copytree(
                src='pillar/{}'.format(source_stackname),
                dst='pillar/{}'.format(self.target_stackname)
            )

            # update top.sls in new stack
            print(yellow('Updating pillar references'))
            self._update_top_sls(
                "pillar/{}/top.sls".format(self.target_stackname),
                source_stackname
            )

            # Create an expiration file
            self._write_expiry_to_pillar(
                target_path="pillar/{}".format(self.target_stackname),
                expiry_days=lifetime_days
            )

            # add new feature branch to truth file
            self.__add_feature_to_sources_file(
                'pillar/{}'.format(self.target_stackname),
                sources_section
            )
        else:
            print(yellow("Development stack already exists"))

    @staticmethod
    def __generate_stack_name(target_stackname):
        """
        Ensures our stackname has -feature in it
        :param target_stackname:
        :return: target_stackname
        """
        if 'feat' in target_stackname and '-feature' not in target_stackname:
            target_stackname.replace('feat', 'feature')

        if 'feature' not in target_stackname:
            target_stackname += '-feature'

        return target_stackname

    @staticmethod
    def __add_feature_to_sources_file(feature_pillar, sources_section):
        """
        Adds the newly created feature branch to our truth file
        :param feature_pillar:
        :param sources_section:
        """
        with open('sources.yml', 'r') as stream:
            source = yaml.safe_load(stream)

        source['pillar'][sources_section].append('./{}'.format(feature_pillar))

        with open('sources.yml', 'w+') as stream:
            yaml.safe_dump(
                data=source,
                stream=stream,
                default_flow_style=False
            )

    @staticmethod
    def __remove_stack_from_sources_file(feature_pillar, sources_section):
        """
        Removes our feature stack from the truth file
        :param feature_pillar:
        :param sources_section:
        """
        with open('sources.yml', 'r') as stream:
            source = yaml.safe_load(stream)

        source['pillar'][sources_section].remove('./{}'.format(feature_pillar))

        with open('sources.yml', 'w+') as stream:
            yaml.safe_dump(
                data=source,
                stream=stream,
                default_flow_style=False
            )

    def _update_top_sls(self, target_top_file, source_stackname):
        """
        Replace the source with our target in the copied top.sls file
        :param target_top_file:
        :param source_stackname:
        :return:
        """
        file_lines = []

        with open(target_top_file, "r") as stream:
            for line in stream:
                if source_stackname in line:
                    line = line.replace(source_stackname, self.target_stackname)
                file_lines.append(line)

        with open(target_top_file.format(self.target_stackname), "w+") as stream:
            stream.writelines(file_lines)

    @staticmethod
    def _write_expiry_to_pillar(target_path, expiry_days):
        """
        Write an expiry date time to the pillar
        :param target_path:
        :param expiry_days:
        :return:
        """
        expiry_time = datetime.now() + timedelta(days=int(expiry_days))
        file_data = dict(expiry_date='{}'.format(expiry_time))

        with open(target_path + '/stack_expiry.sls', 'w+') as stream:
            yaml.safe_dump(file_data, stream=stream, default_flow_style=False)

    def commit_development_stack(self, target_branch='master', action='Creation'):
        """
        Add the stack to git
        :return:
        """
        from cotton.gitutils import gitutilities
        utils = gitutilities.GitUtilities(
            changes=[
                'ansible/{}'.format(self.target_stackname),
                'pillar/{}'.format(self.target_stackname),
                'sources.yml'
            ],
            message='{} of {} development stack'.format(action, self.target_stackname),
            target_branch=target_branch
        )

        utils.commit_change_set()

    def is_protected_stack(self):
        """Validate the stack is not protected, if it is raise a TargetViolationError"""
        protected_stacks = ['aws-develop', 'staging', 'production']

        if self.target_stackname in protected_stacks:
            raise TargetViolationError("Target stack is protected")
