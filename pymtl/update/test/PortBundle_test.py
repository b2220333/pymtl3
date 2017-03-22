from pymtl import *

from pclib.bundle import TestSource
from pclib.bundle import TestSink
from pclib.bundle import ValRdyBundle

def test_simple():

  class Top(Updates):

    def __init__( s ):

      s.src  = TestSource( input_=[ [0], [1], [2] ] )
      s.sink = TestSink  ( [ 0, 1, 2] )

      s.sink.in_ |= s.src.out

    def done( s ):
      return s.src.done() and s.sink.done()

    def line_trace( s ):
      return s.src.line_trace() + " >>> " + \
             " >>> " + s.sink.line_trace()

  A = Top()
  A.elaborate()
  A.print_schedule()

  while not A.done():
    A.cycle()
    print A.line_trace()

def test_nested_port_bundle():

  class SuperBundle( PortBundle ):

    def __init__( s ):
      s.req  = [ [ ValRdyBundle() for i in xrange(4) ] for j in xrange(4) ]

  class Top(Updates):

    def __init__( s ):

      s.src  = [ TestSource( 1, [ [i],[i+1],[i+2],[i],[i+1],[i+2] ] ) for i in xrange(4) ]
      # (0+1+2+3)*4=24, (1+2+3+4)*4=40, (2+3+4+5)*5=56
      s.sink = TestSink  ( [ 24, 40, 56, 24, 40, 56] )

      s.sb = SuperBundle()
      s.wire = [ [ Wire(int) for i in xrange(4) ] for j in xrange(4) ]

      for i in xrange(4):
        s.src[i].out.rdy      |= s.sink.in_.rdy
        for j in xrange(4):
          s.sb.req[i][j].msg[0] |= s.src[i].out.msg[0]
          s.wire[i][j]          |= s.sb.req[i][j].msg[0]

      s.out = ValRdyBundle()
      s.out |= s.sink.in_
      
      @s.update
      def up_from_req():
        s.out.val = 1
        s.out.msg[0] = 0
        for i in xrange(4):
          for j in xrange(4):
            s.out.msg[0] += s.wire[i][j]

    def done( s ):
      return reduce( lambda x,y: x or y.done(), s.src ) and s.sink.done()

    def line_trace( s ):
      return "|".join( [ x.line_trace() for x in s.src] ) + " >>> " + \
             " >>> " + s.sink.line_trace()

  A = Top()
  A.elaborate()
  A.print_schedule()

  while not A.done():
    A.cycle()
    print A.line_trace()