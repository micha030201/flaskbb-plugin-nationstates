# -*- coding: utf-8 -*-
"""
    nationstates
    ~~~~~~~~~~~~

    A nationstates Plugin for FlaskBB.

    :copyright: (c) 2018 by Михаил Лебедев.
    :license: BSD License, see LICENSE for more details.
"""
import os
import logging

import requests
from wtforms import StringField
from wtforms.validators import DataRequired, regexp, ValidationError
from flask import render_template_string

from .models import User


__version__ = "0.0.1"


logger = logging.getLogger(__name__)


# connect the hooks
def flaskbb_load_migrations():
    return os.path.join(os.path.dirname(__file__), "migrations")


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


SETTINGS = {}
