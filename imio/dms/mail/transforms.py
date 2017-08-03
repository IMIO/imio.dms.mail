# -*- coding: utf-8 -*-

from Products.PortalTransforms.interfaces import ITransform
from Products.PortalTransforms.libtransforms.commandtransform import popentransform  # noqa
from zope.interface import implementer


@implementer(ITransform)
class odt_2_text(popentransform):
    """
        Use odt2text to get plain text.
        Header and footer are skipped !
        Images and frames are replaced by tags [-- Image: Image1 --] or [-- Image: Cadre1 --] => remove it
    """
    __name__ = "odt_to_text"
    inputs = ('application/vnd.oasis.opendocument.text',)
    output = 'text/plain'
    output_encoding = 'utf-8'

    __version__ = '2017-08-03.01'

    binaryName = "odt2txt"
    binaryArgs = '--encoding=UTF-8 --width=-1 --subst=all %(infile)s'
    useStdin = False

    def getData(self, couterr):
        out = []
        for line in couterr.readlines():
            line = line.strip(' \n')
            if not line:
                continue
            if line.startswith('[-- ') and line.endswith(' --]'):
                continue
            out.append(line)
        return '\n'.join(out)


def register():
    return odt_2_text()
