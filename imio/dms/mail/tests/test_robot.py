from plone.testing import layered

import robotsuite

from imio.dms.mail.testing import DMSMAIL_ROBOT_TESTING


def test_suite():
    return layered(robotsuite.RobotTestSuite('robot/dmsmail.robot', 'robot/doc.robot'),
                   layer=DMSMAIL_ROBOT_TESTING)
