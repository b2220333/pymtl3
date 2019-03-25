#=========================================================================
# ComponentLevel5_test.py
#=========================================================================
#
# Author : Shunning Jiang
# Date   : Jan 4, 2019

from pymtl import *
from pymtl.dsl.ComponentLevel5 import ComponentLevel5
from sim_utils import simple_sim_pass
from collections import deque

def _test_model( cls ):
  A = cls()
  A.elaborate()
  simple_sim_pass( A, 0x123 )

  T, time = 0, 20
  while not A.done() and T < time:
    A.tick()
    print A.line_trace()
    T += 1

class SimpleTestSource( ComponentLevel5 ):

  def construct( s, msgs ):
    s.msgs = deque( msgs )

    s.req     = CallerPort()
    s.req_rdy = CallerPort()

    s.v = 0
    @s.update
    def up_src():
      s.v = None
      if s.req_rdy() and s.msgs:
        s.v = s.msgs.popleft()
        s.req( s.v )

  def done( s ):
    return not s.msgs

  def line_trace( s ):
    return "{:4}".format( "" if s.v is None else s.v )

class TestSinkError( Exception ):
  pass

class SimpleTestSink( ComponentLevel5 ):

  def resp_( s, msg ):
    ref = s.msgs[ s.idx ]
    s.idx += 1

    if msg != ref:
      raise TestSinkError( """
The test sink received an incorrect message!
- sink name    : {}
- msg number   : {}
- expected msg : {}
- actual msg   : {}
""".format( s, s.idx, ref, msg )
      )

  def resp_rdy_( s ):
    return True

  def construct( s, msgs ):
    s.msgs = list( msgs )
    s.idx  = 0

    s.resp     = CalleePort( s.resp_     )
    s.resp_rdy = CalleePort( s.resp_rdy_ )

  def done( s ):
    return s.idx >= len(s.msgs)

  def line_trace( s ):
    return ""

def test_simple_src_dumb_sink():

  class Top( ComponentLevel5 ):

    def construct( s ):
      s.src  = SimpleTestSource( [1,2,3,4] )
      s.sink = SimpleTestSink( [1,2,3,4] )

      s.connect_pairs(
        s.src.req,     s.sink.resp,
        s.src.req_rdy, s.sink.resp_rdy,
      )

    def done( s ):
      return s.src.done() and s.sink.done()

    def line_trace( s ):
      return  s.src.line_trace() + " >>> " + s.sink.line_trace()


  _test_model( Top )

class TestSinkUp( ComponentLevel5 ):

  def resp_rdy_( s ):
    return s.idx < len(s.msgs)

  def resp_( s, v ):
    s.queue.appendleft(v)

  def construct( s, msgs ):
    s.msgs  = list( msgs )
    s.queue = deque( maxlen=1 )
    s.idx  = 0

    s.resp     = CalleePort( s.resp_ )
    s.resp_rdy = CalleePort( s.resp_rdy_ )

    s.v = None

    @s.update
    def up_sink():
      s.v = None

      if s.queue:
        msg = s.queue.pop()
        s.v = msg

        if s.idx >= len(s.msgs):
          raise TestSinkError( """
  The test sink received a message that !
  - sink name    : {}
  - msg number   : {}
  - actual msg   : {}
  """.format( s, s.idx, msg )
          )
        else:
          ref = s.msgs[ s.idx ]
          s.idx += 1

          if msg != ref:
            raise TestSinkError( """
  The test sink received an incorrect message!
  - sink name    : {}
  - msg number   : {}
  - expected msg : {}
  - actual msg   : {}
  """.format( s, s.idx, ref, msg )
          )

    s.add_constraints(
      U(up_sink) < M(s.resp_    ), # pipe behavior
      U(up_sink) < M(s.resp_rdy_),
    )

  def done( s ):
    return s.idx >= len(s.msgs)

  def line_trace( s ):
    return "{:4}".format( "" if s.v is None else s.v )

def test_simple_src_up_sink():

  class Top( ComponentLevel5 ):

    def construct( s ):
      s.src  = SimpleTestSource( [1,2,3,4] )
      s.sink = TestSinkUp( [1,2,3,4] )

      s.connect_pairs(
        s.src.req,     s.sink.resp,
        s.src.req_rdy, s.sink.resp_rdy,
      )

    def done( s ):
      return s.src.done() and s.sink.done()

    def line_trace( s ):
      return  s.src.line_trace() + " >>> " + s.sink.line_trace()


  _test_model( Top )

def test_method_interface():

  class RecvIfcCL( Interface ):
    def construct( s, recv=None, rdy=None):
      s.msg = CalleePort( recv )
      s.rdy = CalleePort( rdy )

  class SendIfcCL( Interface ):
    def construct( s ):
      s.msg = CallerPort()
      s.rdy = CallerPort()

  class SimpleTestSourceIfc( ComponentLevel5 ):

    def construct( s, msgs ):
      s.msgs = deque( msgs )

      s.req = SendIfcCL()

      s.v = 0
      @s.update
      def up_src():
        s.v = None
        if s.req.rdy() and s.msgs:
          s.v = s.msgs.popleft()
          s.req.msg( s.v )

    def done( s ):
      return not s.msgs

    def line_trace( s ):
      return "{:4}".format( "" if s.v is None else s.v )

  class SimpleTestSinkIfc( ComponentLevel5 ):

    def resp_( s, msg ):
      ref = s.msgs[ s.idx ]
      s.idx += 1

      if msg != ref:
        raise TestSinkError( """
  The test sink received an incorrect message!
  - sink name    : {}
  - msg number   : {}
  - expected msg : {}
  - actual msg   : {}
  """.format( s, s.idx, ref, msg )
        )

    def resp_rdy_( s ):
      return True

    def construct( s, msgs ):
      s.msgs = list( msgs )
      s.idx  = 0

      s.resp = RecvIfcCL( recv = s.resp_, rdy = s.resp_rdy_ )

    def done( s ):
      return s.idx >= len(s.msgs)

    def line_trace( s ):
      return ""

  class Top( ComponentLevel5 ):

    def construct( s ):
      s.src  = SimpleTestSourceIfc( [1,2,3,4] )
      s.sink = SimpleTestSinkIfc( [1,2,3,4] )

      s.connect_pairs(
        s.src.req,     s.sink.resp,
      )

    def done( s ):
      return s.src.done() and s.sink.done()

    def line_trace( s ):
      return  s.src.line_trace() + " >>> " + s.sink.line_trace()

  _test_model( Top )