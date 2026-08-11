# -*- coding: utf-8 -*-
"""Helpers shared by several test modules."""

from collective.contact.plonegroup.config import get_registry_organizations
from collective.iconifiedcategory.utils import calculate_category_id
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.utils import sub_create
from io import BytesIO
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from xml.sax.saxutils import escape

import datetime
import zipfile


def acroform_tag(nb):
    """Return an acroform tag: the signature tag of the given signer number,
    or the seal tag when nb is the string u"SCEAU"."""
    ident = nb == u"SCEAU" and u"SCEAU" or u"Signer%s" % nb
    return u'{{#"ID":"%s","Size":{"Height":"70","Width":"200"}#}}' % ident


def odt_with_tags(*tag_ids):
    """Return a minimal odt NamedBlobFile holding the acroform tag of each given tag id."""
    body = u"".join(
        [u"<text:p>" + escape(acroform_tag(nb), {u'"': u"&quot;"}) + u"</text:p>" for nb in tag_ids]
    )
    xml = (
        u"<?xml version='1.0' encoding='UTF-8'?><office:document-content><office:body><office:text>"
        + body
        + u"</office:text></office:body></office:document-content>"
    )
    buf = BytesIO()
    zip_file = zipfile.ZipFile(buf, "w")
    zip_file.writestr("content.xml", xml.encode("utf-8"))
    zip_file.close()
    return NamedBlobFile(
        data=buf.getvalue(), filename=u"tagged.odt", contentType="application/vnd.oasis.opendocument.text"
    )


def create_om_with_tags(portal, oid, tag_ids=(1,), nb_signers=1, esign=True, seal=False):
    """Create an outgoing mail holding one signable dmsommainfile carrying the given tags.

    :param tag_ids: tag ids written in the file: signer numbers and u"SCEAU" for the seal
    :param nb_signers: number of signers set on the mail
    :param esign: electronic signature enabled on the mail
    :param seal: seal enabled on the mail
    :return: an (outgoing mail, main file) tuple
    """
    pf = portal["contacts"]["personnel-folder"]
    hps = [pf["dirg"]["directeur-general"], pf["bourgmestre"]["bourgmestre"]]
    signers = [
        {"number": i + 1, "signer": hps[i].UID(), "approvings": [u"_themself_"], "editor": False}
        for i in range(nb_signers)
    ]
    omail = sub_create(
        portal["outgoing-mail"], "dmsoutgoingmail", datetime.datetime.now(), oid,
        title=u"Acroform test", treating_groups=get_registry_organizations()[0],
        signers=signers, esign=esign, seal=seal,
    )
    ct = portal["annexes_types"]["outgoing_dms_files"]["outgoing-dms-file"]
    filename = u"Réponse salle.odt"
    with open("%s/batchimport/toprocess/outgoing-mail/%s" % (PRODUCT_DIR, filename), "rb") as fo:
        file_object = NamedBlobFile(fo.read(), filename=filename)
    afile = createContentInContainer(
        omail, "dmsommainfile", id="mainfile", file=file_object, content_category=calculate_category_id(ct)
    )
    afile.file = odt_with_tags(*tag_ids)
    afile.to_sign = True
    return omail, afile
