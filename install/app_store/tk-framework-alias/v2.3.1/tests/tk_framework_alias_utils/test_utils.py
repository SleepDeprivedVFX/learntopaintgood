# Copyright (c) 2021 Autoiesk Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk Inc.

import pytest

from tk_framework_alias_utils import utils


####################################################################################################
# tk_framework_alias_utils utils.py Test Cases
####################################################################################################


@pytest.mark.parametrize(
    "v1,v2,expected_result",
    [
        ("2022", "2023", -1),
        ("2022.0", "2023", -1),
        ("2022.1", "2023", -1),
        ("2022.2.2", "2023", -1),
        ("2022.3.3.3", "2023", -1),
        ("2022", "2023.0", -1),
        ("2022.4.5.3", "2023.1.2", -1),
        ("2022.0", "2022.1", -1),
        ("2022.0", "2022.0.1", -1),
        ("2022.1", "2022.1.1", -1),
        ("2022.1", "2022.1.0.1", -1),
        ("1.0", "2023", -1),
        ("2022", "2022", 0),
        ("2019", "2019", 0),
        ("2024", "2024.0", 0),
        ("2024.0", "2024", 0),
        ("2024.1", "2024.1", 0),
        ("2024.1.2", "2024.1.2", 0),
        ("2024.1.2.3", "2024.1.2.3", 0),
        ("2023", "2022", 1),
        ("2023.0", "2022", 1),
        ("2023.1", "2022", 1),
        ("2023.1.2", "2022", 1),
        ("2023.1.2.3", "2022", 1),
        ("2023.1.2.3", "2022.6", 1),
        ("2023.1.2.3", "2022.6.7", 1),
        ("2023.1.2.3", "2022.6.7.8", 1),
        ("2023", "2022.0", 1),
        ("2023.0", "2022.1", 1),
        ("2023.1", "2023.0", 1),
        ("2023.0.1", "2023.0", 1),
        ("2023.1", "2023.0.1", 1),
        ("2023.1.1", "2023.1", 1),
    ],
)
def test_version_cmp(v1, v2, expected_result):
    """Test the utils.py version_cmp function."""

    result = utils.version_cmp(v1, v2)
    assert result == expected_result
