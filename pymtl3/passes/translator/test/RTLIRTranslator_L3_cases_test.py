#=========================================================================
# RTLIRTranslator_L3_cases_test.py
#=========================================================================
# Author : Peitian Pan
# Date   : May 23, 2019
"""Test the RTLIR transaltor."""
from __future__ import absolute_import, division, print_function

from ..behavioral.test.BehavioralTranslatorL3_test import *
from ..structural.test.StructuralTranslatorL3_test import *
from .TestRTLIRTranslator import TestRTLIRTranslator


def local_do_test( m ):
  if not m._dsl.constructed:
    m.elaborate()
  tr = TestRTLIRTranslator(m)
  tr.translate( m )
  src = tr.hierarchy.src
  try:
    assert src == m._ref_src
  except AttributeError:
    pass