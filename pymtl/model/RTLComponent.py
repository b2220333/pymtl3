#=========================================================================
# RTLComponent.py
#=========================================================================

from pymtl.datatypes import Bits1
from ComponentLevel3 import ComponentLevel3
from Connectable import Connectable, Signal, InVPort, OutVPort, Wire, Const, _overlap
from errors      import InvalidConnectionError, SignalTypeError, NoWriterError, MultiWriterError
from collections import defaultdict, deque

import inspect, ast # for error message

class RTLComponent( ComponentLevel3 ):

  # Override
  def _construct( s ):
    """ We override _construct here to add clk/reset signals. I add signal
    declarations before constructing child components and bring up them
    to parent after construction of all children. """

    if not s._constructed:
      s.clk   = InVPort( Bits1 )
      s.reset = InVPort( Bits1 )

      if not s._kwargs: s.construct( *s._args )
      else:             s.construct( *s._args, **s._kwargs )

      try:
        s.connect( s.clk, s._parent_obj.clk )
        s.connect( s.reset, s._parent_obj.reset )
      except AttributeError:
        pass

      if hasattr( s, "_call_kwargs" ): # s.a = A()( b = s.b )
        s._continue_call_connect()

      s._constructed = True

  def sim_reset( s ):
    assert s._elaborate_top is s # assert sim_reset is top

    s.reset = Bits1( 1 )
    s.tick() # This tick propagates the reset signal
    s.tick()
    s.reset = Bits1( 0 )

