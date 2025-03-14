#!/usr/bin/env python3
"""
Script to run the tests.
"""

import pytest
import sys

if __name__ == "__main__":
    sys.exit(pytest.main(["-v", "tests"])) 