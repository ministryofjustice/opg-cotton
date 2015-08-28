import os
import tempfile
import yaml

from fabric.api import env

from cotton.colors import red, green


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
