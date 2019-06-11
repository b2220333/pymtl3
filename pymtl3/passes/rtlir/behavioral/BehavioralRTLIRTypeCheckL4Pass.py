#=========================================================================
# BehavioralRTLIRTypeCheckL4Pass.py
#=========================================================================
# Author : Peitian Pan
# Date   : March 30, 2019
"""Provide L4 behavioral RTLIR type check pass."""
from __future__ import absolute_import, division, print_function

from pymtl3.passes.BasePass import BasePass, PassMetadata
from pymtl3.passes.rtlir.errors import PyMTLTypeError
from pymtl3.passes.rtlir.rtype import RTLIRType as rt

from .BehavioralRTLIRTypeCheckL3Pass import BehavioralRTLIRTypeCheckVisitorL3


class BehavioralRTLIRTypeCheckL4Pass( BasePass ):
  def __call__( s, m ):
    """Perform type checking on all RTLIR in rtlir_upblks."""
    if not hasattr( m, '_pass_behavioral_rtlir_type_check' ):
      m._pass_behavioral_rtlir_type_check = PassMetadata()
    m._pass_behavioral_rtlir_type_check.rtlir_freevars = {}
    m._pass_behavioral_rtlir_type_check.rtlir_tmpvars = {}
    m._pass_behavioral_rtlir_type_check.rtlir_accessed = set()
    visitor = BehavioralRTLIRTypeCheckVisitorL4(
      m,
      m._pass_behavioral_rtlir_type_check.rtlir_freevars,
      m._pass_behavioral_rtlir_type_check.rtlir_accessed,
      m._pass_behavioral_rtlir_type_check.rtlir_tmpvars
    )

    for blk in m.get_update_blocks():
      visitor.enter( blk, m._pass_behavioral_rtlir_gen.rtlir_upblks[ blk ] )

class BehavioralRTLIRTypeCheckVisitorL4( BehavioralRTLIRTypeCheckVisitorL3 ):
  def __init__( s, component, freevars, accessed, tmpvars ):
    super( BehavioralRTLIRTypeCheckVisitorL4, s ). \
        __init__( component, freevars, accessed, tmpvars )
    s.type_expect[ 'Attribute' ] = {
      'value':( (rt.Component, rt.Signal, rt.InterfaceView),
        'the base of an attribute must be one of: module, struct, interface!' )
    }

  def visit_Attribute( s, node ):
    if isinstance( node.value.Type, rt.InterfaceView ):
      if not node.value.Type.has_property( node.attr ):
        raise PyMTLTypeError( s.blk, node.ast,
          '{} does not have field {}!'.format( dtype.get_name(), node.attr))
      node.Type = node.value.Type.get_property( node.attr )
    else:
      super( BehavioralRTLIRTypeCheckVisitorL4, s ).visit_Attribute( node )

  def visit_Index( s, node ):
    if isinstance( node.value.Type, rt.Array ) and \
       isinstance( node.value.Type.get_sub_type(), rt.InterfaceView ):
      try:
        # if no exception is raised, L1 visit_Index will generate type for `node`
        nbits = node.idx._value
        node.Type = node.value.Type.get_sub_type()
      except AttributeError:
        raise PyMTLTypeError( s.blk, node.ast,
          'index of interface array must be a static constant expression!' )
    else:
      super( BehavioralRTLIRTypeCheckVisitorL4, s ).visit_Index( node )