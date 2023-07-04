# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# ZenodoRDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Additional views."""

from flask import Blueprint, current_app, g, render_template
from invenio_rdm_records.proxies import current_rdm_records
from invenio_rdm_records.resources.serializers import UIJSONSerializer
from invenio_records_resources.resources.records.utils import search_preference
from marshmallow import ValidationError

from .support.support import ZenodoSupport


#
# Views
#
def frontpage_view_function():
    """Zenodo frontpage view."""
    recent_uploads = current_rdm_records.records_service.search(
        identity=g.identity,
        params={"sort": "newest", "size": 10},
        search_preference=search_preference(),
        expand=False,
    )

    records_ui = []

    for record in recent_uploads:
        record_ui = UIJSONSerializer().dump_obj(record)
        records_ui.append(record_ui)

    return render_template(
        current_app.config["THEME_FRONTPAGE_TEMPLATE"],
        show_intro_section=current_app.config["THEME_SHOW_FRONTPAGE_INTRO_SECTION"],
        recent_uploads=records_ui,
    )


#
# Registration
#
def create_blueprint(app):
    """Register blueprint routes on app."""

    @app.errorhandler(ValidationError)
    def handle_validation_errors(e):
        if isinstance(e, ValidationError):
            dic = e.messages
            deserialized = []
            for error_tuple in dic.items():
                field, value = error_tuple
                deserialized.append({"field": field, "messages": value})
            return {"errors": deserialized}, 400
        return e.message, 400

    blueprint = Blueprint(
        "zenodo_rdm",
        __name__,
        template_folder="./templates",
    )

    # Support URL rule
    support_endpoint = app.config["SUPPORT_ENDPOINT"] or "/support"
    blueprint.add_url_rule(
        support_endpoint,
        view_func=ZenodoSupport.as_view("support_form"),
    )

    app.register_error_handler(400, handle_validation_errors)

    return blueprint
