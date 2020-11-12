#=========================================================================
# StreamingMemUnitHost.py
#=========================================================================
# Author : Peitian Pan
# Date   : Nov 10, 2020

from pymtl3 import *
from pymtl3.stdlib.ifcs import mk_xcel_msg, XcelMasterIfcRTL

IDLE = 0
WR_SRC_BASE_ADDR = 1
WR_SRC_X_STRIDE  = 2
WR_SRC_X_COUNT   = 3
WR_SRC_Y_STRIDE  = 4
WR_SRC_Y_COUNT   = 5
WR_DST_BASE_ADDR = 6
WR_DST_ACK_ADDR  = 7
WR_GO            = 8

class StreamingMemUnitHost( Component ):

  def construct( s, DataType, AddrType, StrideType, CountType,
                 src_base_addr, src_x_stride, src_x_count,
                 src_y_stride, src_y_count, dst_base_addr, dst_ack_addr ):

    CfgReq, CfgResp = mk_xcel_msg( AddrType.nbits, DataType.nbits )

    s.cfg = XcelMasterIfcRTL( CfgReq, CfgResp )

    s.state_r = Wire( 4 )
    s.state_n = Wire( 4 )

    @update_ff
    def smu_host_fsm_r():
      if s.reset:
        s.state_r <<= IDLE
      else:
        s.state_r <<= s.state_n

    @update
    def smu_host_fsm_n():
      s.state_n @= s.state_r
      if s.state_r == IDLE:
        s.state_n @= WR_SRC_BASE_ADDR
      elif s.state_r == WR_SRC_BASE_ADDR:
        if s.cfg.req.en:
          s.state_n @= WR_SRC_X_STRIDE
      elif s.state_r == WR_SRC_X_STRIDE:
        if s.cfg.req.en:
          s.state_n @= WR_SRC_X_COUNT
      elif s.state_r == WR_SRC_X_COUNT:
        if s.cfg.req.en:
          s.state_n @= WR_SRC_Y_STRIDE
      elif s.state_r == WR_SRC_Y_STRIDE:
        if s.cfg.req.en:
          s.state_n @= WR_SRC_Y_COUNT
      elif s.state_r == WR_SRC_Y_COUNT:
        if s.cfg.req.en:
          s.state_n @= WR_DST_BASE_ADDR
      elif s.state_r == WR_DST_BASE_ADDR:
        if s.cfg.req.en:
          s.state_n @= WR_DST_ACK_ADDR
      elif s.state_r == WR_DST_ACK_ADDR:
        if s.cfg.req.en:
          s.state_n @= WR_GO
      elif s.state_r == WR_GO:
        if s.cfg.req.en:
          s.state_n @= IDLE

    @update
    def smu_host_msg():
      s.cfg.req.msg.type_ @= 1
      s.cfg.req.msg.addr @= 0
      s.cfg.req.msg.data @= 0

      if s.state_r == WR_SRC_BASE_ADDR:
        s.cfg.req.en @= s.cfg.req.rdy
        s.cfg.req.msg.addr @= 2
        s.cfg.req.msg.data @= src_base_addr
      elif s.state_r == WR_SRC_X_STRIDE:
        s.cfg.req.en @= s.cfg.req.rdy
        s.cfg.req.msg.addr @= 3
        s.cfg.req.msg.data @= src_x_stride
      elif s.state_r == WR_SRC_X_COUNT:
        s.cfg.req.en @= s.cfg.req.rdy
        s.cfg.req.msg.addr @= 4
        s.cfg.req.msg.data @= src_x_count
      elif s.state_r == WR_SRC_Y_STRIDE:
        s.cfg.req.en @= s.cfg.req.rdy
        s.cfg.req.msg.addr @= 5
        s.cfg.req.msg.data @= src_y_stride
      elif s.state_r == WR_SRC_Y_COUNT:
        s.cfg.req.en @= s.cfg.req.rdy
        s.cfg.req.msg.addr @= 6
        s.cfg.req.msg.data @= src_y_count
      elif s.state_r == WR_DST_BASE_ADDR:
        s.cfg.req.en @= s.cfg.req.rdy
        s.cfg.req.msg.addr @= 7
        s.cfg.req.msg.data @= dst_base_addr
      elif s.state_r == WR_DST_ACK_ADDR:
        s.cfg.req.en @= s.cfg.req.rdy
        s.cfg.req.msg.addr @= 8
        s.cfg.req.msg.data @= dst_ack_addr

      s.cfg.resp.rdy @= 1