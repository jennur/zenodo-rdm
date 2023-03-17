# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 CERN.
#
# ZenodoRDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Zenodo migrator records transformers."""

from invenio_rdm_migrator.streams.records import RDMRecordEntry, RDMRecordTransform
from nameparser import HumanName


class ZenodoRecordEntry(RDMRecordEntry):
    """Transform Zenodo record to RDM record."""

    def _created(self, entry):
        """Returns the creation date of the record."""
        return entry["created"]

    def _updated(self, entry):
        """Returns the creation date of the record."""
        return entry["updated"]

    def _version_id(self, entry):
        """Returns the version id of the record."""
        return entry["version_id"]

    def _index(self, entry):
        """Returns the index of the record."""
        return entry.get("index", 0) + 1  # in legacy we start at 0

    def _recid(self, entry):
        """Returns the recid of the record."""
        return str(entry["json"]["recid"])

    def _pids(self, entry):
        record = entry["json"]
        r = {
            "oai": {
                "provider": "oai",
                "identifier": record["_oai"]["id"],
            },
        }
        if record.get("doi"):
            r["doi"] = {
                "client": "datacite",
                "provider": "datacite",
                "identifier": record["doi"],
            }

        return r

    def _files(self, entry):
        """Transform the files of a record."""
        return {"enabled": True}

    def _access(self, entry):
        record = entry["json"]
        is_open = record["access_right"] == "open"
        r = {
            "record": "public",
            "files": "public" if is_open else "restricted",
        }
        if record["access_right"] == "embargoed":
            r["embargo"] = {
                "until": record["embargo_date"],
                "active": True,
            }
        return r

    def _metadata(self, entry):
        """Transform the metadata of a record."""

        def _creators(data):
            ret = []
            for c in data:
                r = {"person_or_org": {"type": "personal"}}
                if c.get("affiliation"):
                    r["affiliations"] = [{"name": c["affiliation"]}]
                if c.get("orcid"):
                    r["person_or_org"]["identifiers"] = [
                        {"scheme": "orcid", "identifier": c["orcid"]},
                    ]
                name = HumanName(c["name"])
                r["person_or_org"]["given_name"] = name.first
                r["person_or_org"]["family_name"] = name.surnames
                # autocompleted by RDM Metadata schema
                r["person_or_org"]["name"] = f"{name.surnames}, {name.first}"

                ret.append(r)
            return ret

        def _resource_type(data):
            t = data["type"]
            st = data.get("subtype")
            return {"id": f"{t}-{st}"} if st else {"id": t}

        record = entry["json"]
        r = {
            "title": record["title"],
            "description": record["description"],
            "publication_date": record["publication_date"],
            "resource_type": _resource_type(record["resource_type"]),
            "creators": _creators(record["creators"]),
        }

        return r


class ZenodoRecordTransform(RDMRecordTransform):
    """Zenodo to RDM Record class for data transformation."""

    def _community_id(self, entry):
        communities = entry["json"].get("communities")
        if communities:
            # TODO: handle all slugs
            slug = communities[0]
            if slug:
                return {"ids": [slug], "default": slug}
        return {}

    def _parent(self, entry):
        parent = {
            "created": entry["created"],  # same as the record
            "updated": entry["updated"],  # same as the record
            "version_id": entry["version_id"],
            "json": {
                # loader is responsible for creating/updating if the PID exists.
                "id": entry["json"]["conceptrecid"],
                "access": {
                    "owned_by": [{"user": o} for o in entry["json"].get("owners", [])]
                },
                "communities": self._community_id(entry),
            },
        }

        return parent

    def _record(self, entry):
        return ZenodoRecordEntry().transform(entry)

    def _draft(self, entry):
        return None

    def _draft_files(self, entry):
        return None

    def _record_files(self, entry):
        files = entry["json"].get("_files", [])
        return [
            {
                "key": f["key"],
                "object_version": {
                    "file": {
                        "size": f["size"],
                        "checksum": f["checksum"],
                    },
                },
            }
            for f in files
        ]
