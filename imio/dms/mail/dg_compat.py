# -*- coding: utf-8 -*-
"""collective.documentgenerator 3.44-3.49 helpers missing in collective.documentgenerator 4.0.

ponytail: copied from collective.documentgenerator 3.49 utils, drop when a 4.x release provides them.
"""
from appy.pod.renderer import Renderer
from collective.documentgenerator import _
from collective.documentgenerator import config
from collective.documentgenerator.config import DEFAULT_OO_PORT
from collective.documentgenerator.utils import create_temporary_file
from collective.documentgenerator.utils import remove_tmp_file
from collective.documentgenerator.utils import temporary_file_name
from imio.dms.mail import BLDT_DIR
from imio.helpers.content import uuidToObject
from imio.pyutils.system import runCommand
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from Products.CMFPlone.utils import safe_unicode
from zope.annotation import IAnnotations
from zope.component.hooks import getSite
from zope.interface import Invalid

import appy.pod
import os


# appy 1.0: the command line converter is appy/bin/convert.py (appy/pod/converter.py has no main any more)
CONVSCRIPT = os.path.join(os.path.dirname(os.path.dirname(appy.pod.__file__)), "bin", "convert.py")


def convert_odt(afile, fmt="pdf", gen_context=None, delete_temp_files=True, **kwargs):
    """Convert an odt file (NamedBlobFile) to another format using appy.pod. Return the converted content."""
    temp_file = create_temporary_file(afile, ".odt")
    converted_filename = temporary_file_name(suffix=".{}".format(fmt))
    if not gen_context:
        gen_context = {}
    try:
        renderer = Renderer(
            temp_file.name,
            gen_context,
            converted_filename,
            pythonWithUnoPath=config.get_uno_path(),
            ooServer=config.get_oo_server(),
            ooPort=config.get_oo_port_list(),
            raiseOnError=True,
            forceOoCall=True,
            **kwargs
        )
        if "view" in gen_context:
            gen_context["view"]._set_appy_renderer(renderer)
        renderer.run()
        if not os.path.exists(converted_filename):
            msg = "Conversion failed, no converted file '{}'".format(safe_unicode(converted_filename))
            api.portal.show_message(message=_(msg), request=getSite().REQUEST, type="error")
            raise Invalid(msg)
        with open(converted_filename, "rb") as f:
            converted_file = f.read()
    finally:
        if delete_temp_files:
            remove_tmp_file(temp_file.name)
            if os.path.exists(converted_filename):
                remove_tmp_file(converted_filename)
    return converted_file


def convert_file(afile, fmt="pdf", renderer=False, gen_context=None, delete_temp_files=True):
    """Convert a file (NamedBlobFile) to another LibreOffice format, with appy.pod Renderer (odt only) or the
    appy converter script. Return the converted content."""
    if renderer:
        if not afile.filename.endswith(".odt"):
            raise Invalid(_("Conversion with renderer only works from odt files."))
        return convert_odt(afile, fmt=fmt, gen_context=gen_context, delete_temp_files=delete_temp_files)

    file_ext = afile.filename.split(".")[-1].lower()
    temp_file = create_temporary_file(afile, base_name=".{}".format(file_ext))
    converted_filename = temp_file.name.replace(".{}".format(file_ext), ".{}".format(fmt))
    converted_file = ""
    try:
        ports = config.get_oo_port_list()
        port = ports[0] if ports else DEFAULT_OO_PORT
        command = "{} {} {} {} -p {} -e {}".format(
            config.get_uno_path(), CONVSCRIPT, temp_file.name, fmt, port, config.get_oo_server()
        )
        out, err, code = runCommand(command)
        # This command has no output on success
        if code != 0 or err or not os.path.exists(converted_filename):
            raise Invalid(_("Conversion failed, no converted file '{}'".format(safe_unicode(converted_filename))))
        with open(converted_filename, "rb") as f:
            converted_file = f.read()
    except Exception as e:
        api.portal.show_message(message=str(e), request=getSite().REQUEST, type="error")
    finally:
        if delete_temp_files:
            remove_tmp_file(temp_file.name)
            if os.path.exists(converted_filename):
                remove_tmp_file(converted_filename)
    return converted_file


def convert_and_save_file(
    afile,
    container,
    portal_type,
    output_name,
    fmt="pdf",
    from_uid=None,
    attributes=None,
    renderer=False,
    gen_context=None,
):
    """Convert a file and save it as a new content (portal_type) in container."""
    converted_file = convert_file(afile, fmt=fmt, gen_context=gen_context, renderer=renderer)
    file_object = NamedBlobFile(converted_file, filename=safe_unicode(output_name))
    if attributes is None:
        attributes = {}
    attributes["conv_from_uid"] = from_uid
    new_file = createContentInContainer(
        container, portal_type, title=safe_unicode(output_name), file=file_object, **attributes
    )
    if from_uid:
        IAnnotations(new_file)["documentgenerator"] = {"conv_from_uid": from_uid}
    return new_file


def get_original_template(obj):
    """Return the template used to generate a document (the mailing template's one for a mailed document)."""
    obj_annot = IAnnotations(obj).get("documentgenerator", {})
    if not obj_annot:
        return None
    if obj_annot.get("mailed", False):  # mailed documents, template_uid is mailing template uid
        if "from_doc_uid" not in obj_annot:
            return None
        doc = uuidToObject(obj_annot["from_doc_uid"], unrestricted=True)
        template_uid = IAnnotations(doc).get("documentgenerator", {}).get("template_uid", None)
    else:
        template_uid = obj_annot.get("template_uid", None)
    if template_uid:
        return uuidToObject(template_uid, unrestricted=True)
    return None


def need_mailing_value(document=None, document_uid=None):
    """Return the need_mailing flag stored on a generated document."""
    if not document:
        document = uuidToObject(document_uid, unrestricted=True)
    return bool(IAnnotations(document).get("documentgenerator", {}).get("need_mailing", False))


def odfsplit(content):
    """Split an ODT document (bytes) on page breaks with bin/odfsplit.

    :return: (exit code, generator of each subfile content or error string, number of files)
    """

    def get_subfiles(temp_file, nb_files):
        if nb_files == 1:
            with open(temp_file, "rb") as f:
                yield f.read()
            remove_tmp_file(temp_file)
            return
        for i in range(1, nb_files + 1):
            subfile = temp_file.replace(".odt", ".{}.odt".format(i))
            with open(subfile, "rb") as sf:
                yield sf.read()
            remove_tmp_file(subfile)
        remove_tmp_file(temp_file)

    temp_file = temporary_file_name(suffix=".odt")
    with open(temp_file, "wb") as f:
        f.write(content)
    out, err, code = runCommand("{}/bin/odfsplit {}".format(BLDT_DIR, temp_file))
    nb_files = 0
    if out and code == 0:
        part0 = out[0].split(" ")[0]  # Ex: "2 files were generated."
        if part0.isdigit():
            nb_files = int(part0)
            value = get_subfiles(temp_file, nb_files)
        else:
            nb_files = 1
            value = get_subfiles(temp_file, 1)
    else:
        value = "".join(err)
    return code, value, nb_files
