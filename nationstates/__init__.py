# -*- coding: utf-8 -*-
"""
    nationstates
    ~~~~~~~~~~~~

    A nationstates Plugin for FlaskBB.

    :copyright: (c) 2018 by Михаил Лебедев.
    :license: BSD License, see LICENSE for more details.
"""
import os
import re
import logging

import bbcode
from pluggy import HookimplMarker
import requests
import mistune
from wtforms import StringField
from wtforms.validators import DataRequired, regexp, ValidationError
from flask import render_template_string, Markup, Blueprint
from flaskbb.utils.helpers import render_template

from .models import User


__version__ = "0.0.1"


hookimpl = HookimplMarker("flaskbb")
logger = logging.getLogger(__name__)


# connect the hooks
def flaskbb_load_migrations():
    return os.path.join(os.path.dirname(__file__), "migrations")


bp = Blueprint("nationstates", __name__, template_folder="templates")


def flaskbb_load_blueprints(app):
    app.register_blueprint(
        bp,
        url_prefix="/nationstates"
    )


# Monkeypatch registration

# the registration-handling code in flaskbb is convoluted as hell,
# easier not to bother and work around it
_usernames_to_nations = {}

_re_nation_name = r'^[A-Za-z0-9_ -]+$'
validate_nation_name = regexp(
    _re_nation_name, message='Invalid characters in nation name'
)


def validate_nation_checksum(form, field):
    nation_name = form.nation.data
    params = {
        'a': 'verify',
        'nation': nation_name,
        'checksum': field.data}

    try:
        resp = requests.get('https://www.nationstates.net/cgi-bin/api.cgi',
                            params=params, timeout=10)
        resp.raise_for_status()
    except Exception:
        # don't block registration if ns is down or we're being ratelimited
        logger.exception('error verifying nation')
        _usernames_to_nations[form.username.data] = None
        return

    if not bool(int(resp.text.strip())):
        raise ValidationError('Code incorrect')
    _usernames_to_nations[form.username.data] = nation_name


def flaskbb_form_registration(form):
    form.nation = StringField(
        'Nation name',
        validators=[
            DataRequired(
                message='A NationStates nation is required to register'),
            validate_nation_name
        ]
    )
    form.nation_checksum = StringField(  # TODO setting
        'Verification code from <a href="https://www.nationstates.net/page=verify_login/">this page</a>',
        validators=[
            DataRequired(message='A code is required to verify your nation'),
            validate_nation_checksum
        ]
    )


# template macro imports are broken in plugins, blergh
# copied them from flaskbb/templates/macros.html
_tpl = '''\
{%- macro field_errors(field) -%}
    {% if field.errors %}
        {%- for error in field.errors -%}
        <span class="help-block">{{error}}</span>
        {%- endfor -%}
    {% endif %}
{%- endmacro -%}
{%- macro field_description(field) -%}
    {% if field.description %}
        <span class="help-block">{{ field.description|safe }}</span>
    {% endif %}
{%- endmacro -%}
{%- macro horizontal_field(field, placeholder=None) -%}
<div class="form-group row {%- if field.errors %} has-error{%- endif %}">
    {{ field.label(class="col-sm-3 control-label") }}
    <div class="col-sm-4">
        {{ field(class='form-control', placeholder=placeholder or field.label.text, **kwargs) }}
        {{ field_description(field) }}
        {{ field_errors(field) }}
    </div>
</div>
{%- endmacro -%}


{{ horizontal_field(form.nation) }}
{{ horizontal_field(form.nation_checksum, placeholder='Verification code') }}
'''


def flaskbb_tpl_form_registration_before(form):
    return render_template_string(_tpl, form=form)


def flaskbb_event_user_registered(username):
    user = User.query.filter(User.username == username).first()
    nation = _usernames_to_nations.pop(username)
    logger.info('assigned user {} nation {}'.format(user.id, nation))
    user.nation = nation
    user.save()


# Actually display it where we can

def flaskbb_tpl_post_author_info_after(user, post):
    if user.nation is not None:
        return ('<a href="https://nationstates.net/{0}">{0}</a>'
                .format(user.nation))


# Post syntax extensions:

class BlockGrammar(mistune.BlockGrammar):
    nsquote = re.compile(
        '\[quote=([A-Za-z0-9_-]+);([0-9]+)\](.+?)\[/quote\]',
        flags=re.DOTALL
    )


class BlockLexer(mistune.BlockLexer):
    grammar_class = BlockGrammar
    default_rules = ['nsquote'] + mistune.BlockLexer.default_rules

    def parse_nsquote(self, m):
        self.tokens.append({
            'type': 'nsquote',
            'author': m.group(1),
            'post_id': m.group(2),
            'text': m.group(3),
        })


class Markdown(mistune.Markdown):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.block = BlockLexer(BlockGrammar())

    def output_nsquote(self):
        author = self.token['author']
        post_id = self.token['post_id']
        text = self.token['text']
        return self.renderer.nsquote(author=author, post_id=post_id, text=text)


bbcode_parser = bbcode.Parser(
    newline='<br />',
    install_defaults=False,
    escape_html=True,
    replace_links=True,
    url_template='<a target="_blank" href="{href}">{text}</a>',
    replace_cosmetic=True,
)
bbcode_parser.add_simple_formatter('b', '<strong>%(value)s</strong>')
bbcode_parser.add_simple_formatter('i', '<i>%(value)s</i>')
bbcode_parser.add_simple_formatter('u', '<u>%(value)s</u>')


def render_nation_region(tag_name, value, options, parent, context):
    if value[0].isupper():
        name = value.replace('_', ' ')
    else:
        name = value.replace('_', ' ').title()
    return (
        '<a target="_blank" href="https://www.nationstates.net/'
        '{type}={name_url}">{name}</a>'
        .format(type=tag_name, name=name,
                name_url=name.replace(' ', '_').lower())
    )


bbcode_parser.add_formatter('nation', render_nation_region)
bbcode_parser.add_formatter('region', render_nation_region)


class Renderer:
    def nsquote(self, author, post_id, text):
        return render_template(
            'rmb_quote.html',
            author=author,
            post_id=post_id,
            text=Markup(bbcode_parser.format(text))
        )


def flaskbb_load_post_markdown_class():
    return Renderer


def make_renderer(classes):
    RenderCls = type('FlaskBBRenderer', tuple(classes), {})

    markup = Markdown(renderer=RenderCls(escape=True, hard_wrap=True))
    return lambda text: Markup(markup.render(text))


# Unfortunately, it's not possible to extend the mistune.BlockLexer
# without re-running this hook
@hookimpl(trylast=True)
def flaskbb_jinja_directives(app):
    render_classes = app.pluggy.hook.flaskbb_load_post_markdown_class(app=app)
    app.jinja_env.filters['markup'] = make_renderer(render_classes)


SETTINGS = {}
