# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os

from flask import Blueprint
from flask import current_app
from flask import jsonify
from flask import request
from werkzeug.exceptions import BadRequest
from repository import MercurialException
from repository import Repository
from repository import UnknownRevisionException
from relengapi import apimethod
from relengapi import p

import tasks
import actions
import rest

logger = logging.getLogger(__name__)
bp = Blueprint('transplant', __name__)

p.transplant.transplant.doc('Perform a transplant')

@bp.route('/repositories/<repository_id>/revsets/<revset>', methods=['GET'])
@apimethod(rest.RevsetInfo, unicode, unicode)
@p.transplant.transplant.require()
def revset_info(repository_id, revset):
    """Get commit info by revset."""

    try:
        return actions.get_revset_info(repository_id, revset)
    except actions.TooManyCommitsError, e:
        raise BadRequest(e.message)
    except actions.TransplantError, e:
        raise BadRequest(e.message)
    except MercurialException, e:
        raise BadRequest(e.message)


@bp.route('/transplant', methods=['POST'])
@apimethod(rest.TransplantTaskAsyncResult, body=rest.TransplantTask)
@p.transplant.transplant.require()
def transplant(transplant_task):
    """Request a transplant job."""

    src = transplant_task.src
    dst = transplant_task.dst
    items = []
    for transplant_item in transplant_task.items:
        item = {}
        if transplant_item.commit:
            item['commit'] = transplant_item.commit
        if transplant_item.revset:
            item['revset'] = transplant_item.revset
        if transplant_item.message:
            item['message'] = transplant_item.message

        items.append(item)

    if not actions.has_repo(src):
        msg = 'Unknown src repository: {}'.format(src)
        raise BadRequest(msg)

    if not actions.has_repo(dst):
        msg = 'Unknown dst repository: {}'.format(dst)
        raise BadRequest(msg)

    if not actions.is_allowed_transplant(src, dst):
        msg = 'Transplant from {} to {} is not allowed'.format(src, dst)
        raise BadRequest(msg)


    async_result = tasks.transplant.apply_async((src, dst, items), queue='transplant')
    return rest.TransplantTaskAsyncResult(task=async_result.id), 202

@bp.route('/result/<task_id>', methods=['GET'])
@apimethod(rest.TransplantTaskResult, unicode)
@p.transplant.transplant.require()
def result(task_id):
    """Get transplant job result."""

    task = current_app.celery.AsyncResult(task_id)
    task_result = rest.TransplantTaskResult(
        task=task.id,
        state=task.state
    )

    if task.ready():
        value = None
        try:
            value = task.get()
        except Exception, e:
            task_result.error = str(e)
            return task_result

        task_result.tip = value['tip']

    return task_result
