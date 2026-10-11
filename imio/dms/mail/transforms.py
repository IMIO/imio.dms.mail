# -*- coding: utf-8 -*-

from plone.base.utils import safe_bytes
from plone.base.utils import safe_text
from Products.PortalTransforms.interfaces import ITransform
from Products.PortalTransforms.libtransforms.commandtransform import popentransform  # noqa
from zope.interface import implementer

import subprocess
import tempfile


@implementer(ITransform)
class odt_2_text(popentransform):
    """
    Use odt2text to get plain text.
    Header and footer are skipped !
    Images and frames are replaced by tags [-- Image: Image1 --] or [-- Image: Cadre1 --] => remove it
    """

    __name__ = "odt_to_text"
    inputs = ("application/vnd.oasis.opendocument.text",)
    output = "text/plain"
    output_encoding = "utf-8"

    __version__ = "2017-08-03.01"

    binaryName = "odt2txt"
    binaryArgs = "--encoding=UTF-8 --width=-1 --subst=all"

    def convert(self, data, cache, **kwargs):
        """odt2txt reads a file (PortalTransforms 5 popentransform only pipes stdin)."""
        with tempfile.NamedTemporaryFile(suffix=".odt") as infile:
            infile.write(data)
            infile.flush()
            out = subprocess.run([self.binary] + self.binaryArgs.split() + [infile.name], stdout=subprocess.PIPE).stdout
        cache.setData(safe_bytes(self.getData(safe_text(out).splitlines())))
        return cache

    def getData(self, lines):
        out = []
        for line in lines:
            line = line.strip(" \n")
            if not line:
                continue
            if line.startswith("[-- ") and line.endswith(" --]"):
                continue
            out.append(line)
        return "\n".join(out)


def register():
    return odt_2_text()
