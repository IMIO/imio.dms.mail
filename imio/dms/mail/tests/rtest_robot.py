from imio.dms.mail.testing import DMSMAIL_ROBOT_TESTING
from plone.testing import layered

import robotsuite


def test_suite():
    return layered(robotsuite.RobotTestSuite('robot/dmsmail.robot'),
                   layer=DMSMAIL_ROBOT_TESTING)
#, 'robot/doc.robot'
