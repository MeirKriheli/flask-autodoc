import os
import re
from collections import defaultdict
from flask import current_app, render_template, render_template_string
from jinja2 import evalcontextfilter


try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack


class Autodoc(object):

    

    def __init__(self, app=None):
        self.app = app
        self.groups = defaultdict(set)
        self.query_params = {}
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        if hasattr(app, 'teardown_appcontext'):
            app.teardown_appcontext(self.teardown)
        else:
            app.teardown_request(self.teardown)
        self.add_custom_template_filters(app)

    def teardown(self, exception):
        ctx = stack.top

    def add_custom_template_filters(self, app):
        """Add custom filters to jinja2 templating engine"""
        self.add_custom_nl2br_filters(app)

    def add_custom_nl2br_filters(self, app):
        """Add a custom filter nl2br to jinja2
         Replaces all newline to <BR>
        """
        _paragraph_re = re.compile(r'(?:\r\n|\r|\n){3,}')
        @app.template_filter()
        @evalcontextfilter
        def nl2br(eval_ctx, value):
            result = u'\n\n'.join(u'%s' % p.replace('\n', '<br>\n') for p in _paragraph_re.split(value))
            return result

    def doc(self, group=None, aa=None, groups=None, query_params=None):
        """Decorator to add flask route to autodoc for automatic documentation\

        Any route decorated with this method will be added to the list of routes to be documented by the generate() or
        html() methods.

        By default, the route is added to the 'all' group.
        By specifying group or groups argument, the route can be added to one or multiple other groups as well, besides
        the 'all' group.
        """
        def decorator(f):
            if groups:
                groupset = set(groups)
            else:
                groupset = set()
                if group:
                    groupset.add(group)
            groupset.add("all")
            for g in groupset:
                self.groups[g].add(f)
                
            if query_params:
                self.query_params[f] = query_params
                
            return f
        return decorator

    def generate(self, group="all", groups=[], sort=None):
        """Returns a list of dict describing the routes specified by the doc() method

        Each dict contains:
         - methods: the set of allowed methods (ie ['GET', 'POST'])
         - rule: relative url (ie '/user/<int:id>')
         - endpoint: function name (ie 'show_user')
         - doc: docstring of the function
         - args: function arguments
         - defaults: defaults values for the arguments

        By specifying the group or groups arguments, only routes belonging to those groups will be returned.

        Routes are sorted alphabetically based on the rule.
        """
        links = []
        for rule in current_app.url_map.iter_rules():

            if rule.endpoint == 'static':
                continue

            func = current_app.view_functions[rule.endpoint]

            if (groups and [True for g in groups if func in self.groups[g]]) or \
                    (not groups and func in self.groups[group]):
                
                links.append(
                    dict(
                        methods = rule.methods,
                        rule = "%s" % rule,
                        endpoint = rule.endpoint,
                        docstring = func.__doc__,
                        args = list(func.__code__.co_varnames),
                        query_params = self.query_params.get(func, []),
                        defaults = rule.defaults
                    )
                )
        if sort:
            return sort(links)
        else:
            return sorted(links, key=lambda x: x['rule'])

    def html(self, template=None, group="all", groups=None, **context):
        """Returns an html string of the routes specified by the doc() method

        A template can be specified. A list of routes is available under the 'autodoc' value (refer to the documentation
        for the generate() for a description of available values). If no template is specified, a default template is
        used.

        By specifying the group or groups arguments, only routes belonging to those groups will be returned.
        """
        if template:
            return render_template(template, autodoc=self.generate(group), **context)
        else:
            filename = os.path.dirname(__file__)+"/templates/autodoc_default.html"
            with open(filename) as file:
                content = file.read()
                with current_app.app_context():
                    return render_template_string(content, autodoc=self.generate(group=group, groups=groups), **context)