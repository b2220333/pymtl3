#=========================================================================
# VerilogPlaceholderPass.py
#=========================================================================
# For each placeholder in the component hierarchy, set up default values,
# check if all configs are valid, and pickle the specified Verilog
# source files.
#
# Author : Peitian Pan
# Date   : Jan 27, 2020

import inspect
import os
import re
import sys

from pymtl3 import Placeholder, MetadataKey
from pymtl3.passes.backends.verilog.util.utility import (
    gen_mapped_ports,
    get_component_unique_name,
)
from pymtl3.passes.errors import InvalidPassOptionValue
from pymtl3.passes.PlaceholderConfigs import expand
from pymtl3.passes.PlaceholderPass import PlaceholderPass
from pymtl3.passes.rtlir import RTLIRDataType as rdt
from pymtl3.passes.rtlir import RTLIRType as rt
from pymtl3.passes.rtlir import get_component_ifc_rtlir


class VerilogPlaceholderPass( PlaceholderPass ):

  # Placeholder pass public pass data

  params     = MetadataKey()
  port_map   = MetadataKey()
  top_module = MetadataKey()
  src_file   = MetadataKey()
  v_flist    = MetadataKey()
  v_include  = MetadataKey()

  @staticmethod
  def get_placeholder_config():
    from pymtl3.passes.backends.verilog.VerilogPlaceholderConfigs import VerilogPlaceholderConfigs
    return VerilogPlaceholderConfigs

  def visit_placeholder( s, m ):
    c = s.__class__
    super().visit_placeholder( m )
    irepr = get_component_ifc_rtlir( m )
    s.setup_default_configs( m, irepr )
    cfg = m.get_metadata( c.placeholder_config )

    if cfg.enable:
      s.check_valid( m, cfg, irepr )
      s.pickle( m, cfg, irepr )

  def setup_default_configs( s, m, irepr ):
    c = s.__class__
    cfg = m.get_metadata( c.placeholder_config )

    if cfg.enable:
      # If top_module is unspecified, infer it from the component and its
      # parameters. Note we need to make sure the infered top_module matches
      # the default translation result.
      if not cfg.top_module:
        cfg.top_module = irepr.get_name()

      # If the placeholder has parameters, use the mangled unique component
      # name. Otherwise use {class_name}_wrapper to avoid duplicated defs.
      has_params = bool( irepr.get_params() ) or bool( cfg.params )
      if has_params:
        cfg.pickled_top_module = get_component_unique_name( irepr )
      else:
        cfg.pickled_top_module = f"{irepr.get_name()}_wrapper"

      # Only try to infer the name of Verilog source file if both
      # flist and the source file are not specified.
      if not cfg.src_file and not cfg.v_flist:
        parent_dir = os.path.dirname(inspect.getfile(m.__class__))
        cfg.src_file = f"{parent_dir}{os.sep}{cfg.top_module}.v"

      # Pickled file name should always be the same as the top level
      # module name.
      cfg.pickled_source_file = f"{cfg.pickled_top_module}.v"

      # What is the original file/flist of the pickled source file?
      if cfg.src_file:
        cfg.pickled_orig_file = cfg.src_file
      else:
        cfg.pickled_orig_file = cfg.v_flist

      # The unique placeholder name
      cfg.orig_comp_name = get_component_unique_name( irepr )

      # The `ifdef dependency guard is a function of the placeholder
      # class name
      cfg.dependency_guard_symbol = m.__class__.__name__.upper()

      # The `ifdef placeholder guard is a function of the placeholder
      # wrapper name
      cfg.wrapper_guard_symbol = cfg.pickled_top_module.upper()

  def check_valid( s, m, cfg, irepr ):
    pmap, src, flist, include = \
        cfg.port_map, cfg.src_file, cfg.v_flist, cfg.v_include

    # Check params
    for param_name, value in cfg.params.items():
      if not isinstance( value, int ):
        raise InvalidPassOptionValue("params", cfg.params, cfg.Pass.__name__,
            f"non-integer parameter {param_name} is not supported yet!")

    # Check port map
    # TODO: this should be based on RTLIR
    for name in pmap.keys():
      try:
        eval(f'm.{name}')
      except:
        raise InvalidPassOptionValue("port_map", pmap, cfg.Pass.__name__,
          f"Port {name} does not exist in component {irepr.get_name()}!")

    # Check src_file
    if cfg.src_file and not os.path.isfile(expand(cfg.src_file)):
      raise InvalidPassOptionValue("src_file", cfg.src_file, cfg.Pass.__name__,
          'src_file should be a file path!')

    if cfg.v_flist:
      raise InvalidPassOptionValue("v_flist", cfg.v_flist, cfg.Pass.__name__,
          'Placeholders backed by Verilog flist are not supported yet!')

    # Check v_flist
    if cfg.v_flist and not os.path.isfile(expand(cfg.v_flist)):
      raise InvalidPassOptionValue("v_flist", cfg.v_flist, cfg.Pass.__name__,
          'v_flist should be a file path!')

    # Check v_include
    if cfg.v_include:
      for include in cfg.v_include:
        if not os.path.isdir(expand(include)):
          raise InvalidPassOptionValue("v_include", cfg.v_include, cfg.Pass.__name__,
              'v_include should be an array of dir paths!')

    # Check if the top module name appears in the file
    if cfg.src_file:
      found = False
      with open(cfg.src_file) as src_file:
        for line in src_file.readlines():
          if cfg.top_module in line:
            found = True
            break
      if not found:
        raise InvalidPassOptionValue("top_module", cfg.top_module, cfg.Pass.__name__,
            f'cannot find top module {cfg.top_module} in source file {cfg.src_file}.\n'
            f'Please make sure you have specified the correct top module name through '
            f'the VerilogPlaceholderPass.top_module pass data name!')

  def pickle( s, m, cfg, irepr ):
    pickled_dependency    = s._get_dependent_verilog_modules( m, cfg, irepr )
    pickled_wrapper, tplt = s._gen_verilog_wrapper( m, cfg, irepr )

    pickled_dependency_source = (
        f"//***********************************************************\n"
        f"// Pickled source file of placeholder {cfg.orig_comp_name}\n"
        f"//***********************************************************\n"
        f"\n"
        f"//-----------------------------------------------------------\n"
        f"// Dependency of placeholder {m.__class__.__name__}\n"
        f"//-----------------------------------------------------------\n"
        f"\n"
        f"`ifndef {cfg.dependency_guard_symbol}\n"
        f"`define {cfg.dependency_guard_symbol}\n"
        f"\n"
        f"{pickled_dependency}"
        f"\n"
        f"`endif /* {cfg.dependency_guard_symbol} */\n"
    )

    pickled_wrapper_source = (
        f"\n"
        f"//-----------------------------------------------------------\n"
        f"// Wrapper of placeholder {cfg.orig_comp_name}\n"
        f"//-----------------------------------------------------------\n"
        f"\n"
        f"`ifndef {cfg.wrapper_guard_symbol}\n"
        f"`define {cfg.wrapper_guard_symbol}\n"
        f"\n"
        f"{{pickled_wrapper}}\n"
        f"\n"
        f"`endif /* {cfg.wrapper_guard_symbol} */\n"
    )

    pickled_source = pickled_dependency_source + \
                     pickled_wrapper_source.format(pickled_wrapper=pickled_wrapper)

    cfg.pickled_wrapper_template = pickled_wrapper_source.format(pickled_wrapper=tplt)
    cfg.pickled_wrapper_lineno   = len(pickled_dependency_source.split('\n'))-1

    with open( cfg.pickled_source_file, 'w' ) as fd:
      fd.write( pickled_source )

  def _get_dependent_verilog_modules( s, m, cfg, irepr ):
    return s._import_sources( cfg, [cfg.src_file] )

  def _gen_verilog_wrapper( s, m, cfg, irepr ):
    rtlir_ports = gen_mapped_ports( m, cfg.port_map, cfg.has_clk, cfg.has_reset )

    all_port_names = list(map(lambda x: x[1], rtlir_ports))

    if not cfg.params:
      parameters = irepr.get_params()
    else:
      parameters = cfg.params.items()

    # Port definitions of wrapper
    ports = []
    for idx, (_, name, p, _) in enumerate(rtlir_ports):
      if name:
        if isinstance(p, rt.Array):
          n_dim = p.get_dim_sizes()
          s_dim = ''.join([f'[0:{idx-1}]' for idx in n_dim])
          p = p.get_next_dim_type()
        else:
          s_dim = ''
        ports.append(
            f"  {p.get_direction()} logic [{p.get_dtype().get_length()}-1:0]"\
            f" {name} {s_dim}{'' if idx == len(rtlir_ports)-1 else ','}"
        )

    # The wrapper has to have an unused clk port to make verilator
    # VCD tracing work.
    if 'clk' not in all_port_names:
      ports.insert( 0, '  input logic clk,' )

    if 'reset' not in all_port_names:
      ports.insert( 0, '  input logic reset,' )

    # Parameters passed to the module to be parametrized
    params = [
      f"    .{param}( {val} ){'' if idx == len(parameters)-1 else ','}"\
      for idx, (param, val) in enumerate(parameters)
    ]

    # Connections between top module and inner module
    connect_ports = [
      f"    .{name}( {name} ){'' if idx == len(rtlir_ports)-1 else ','}"\
      for idx, (_, name, p, _) in enumerate(rtlir_ports) if name
    ]

    lines = [
      f"module {cfg.pickled_top_module}",
      "(",
    ] + ports + [
      ");",
      f"  {cfg.top_module}",
      "  #(",
    ] + params + [
      "  ) v",
      "  (",
    ] + connect_ports + [
      "  );",
      "endmodule",
    ]

    template_lines = [
      "module {top_module_name}",
      "(",
    ] + ports + [
      ");",
      f"  {cfg.top_module}",
      "  #(",
    ] + params + [
      "  ) v",
      "  (",
    ] + connect_ports + [
      "  );",
      "endmodule",
    ]

    return '\n'.join( line for line in lines ), '\n'.join( line for line in template_lines )

  #-----------------------------------------------------------------------
  # import_sources
  #-----------------------------------------------------------------------
  # The right way to do this is to use a recursive function like I have
  # done below. This ensures that files are inserted into the output stream
  # in the correct order. -cbatten

  # Regex to extract verilog filenames from `include statements

  _include_re = re.compile( r'"(?P<filename>[\w/\.-]*)"' )

  def _output_verilog_file( s, include_path, verilog_file ):
    code = ""
    with open(verilog_file) as fp:

      short_verilog_file = verilog_file
      if verilog_file.startswith( include_path+"/" ):
        short_verilog_file = verilog_file[len(include_path+"/"):]

      code += '`line 1 "{}" 0\n'.format( short_verilog_file )

      line_num = 0
      for line in fp:
        line_num += 1
        if '`include' in line:
          filename = s._include_re.search( line ).group( 'filename' )
          fullname = os.path.join( include_path, filename )
          code += s._output_verilog_file( include_path, fullname )
          code += '\n'
          code += '`line {} "{}" 0\n'.format( line_num+1, short_verilog_file )
        else:
          code += line
    return code

  def _import_sources( s, cfg, source_list ):
    """Import Verilog source from all Verilog files source_list, as well
    as any source files specified by `include within those files.
    """

    code = ""

    if not source_list:
      return

    # We will use the first verilog file to find the root of PyMTL project

    first_verilog_file = source_list[0]

    # All verilog includes are relative to the root of the PyMTL project.
    # We identify the root of the PyMTL project by looking for the special
    # .pymtl_sim_root file.

    _path = os.path.dirname( first_verilog_file )
    special_file_found = False
    include_path = os.path.dirname( os.path.abspath( first_verilog_file ) )
    while include_path != "/":
      if os.path.exists( include_path + os.path.sep + ".pymtl_sim_root" ):
        special_file_found = True
        sys.path.insert(0,include_path)
        break
      include_path = os.path.dirname(include_path)

    # Append the user-defined include path to include_path
    # NOTE: the current pickler only supports one include path. If v_include
    # config is present, use it instead.

    if cfg.v_include:
      if len(cfg.v_include) != 1:
        raise InvalidPassOptionValue("v_include", cfg.v_include, cfg.Pass.__name__,
            'the current pickler only supports one user-defined v_include path...')
      include_path = cfg.v_include[0]

    # If we could not find the special .pymtl-python-path file, then assume
    # the include directory is the same as the directory that contains the
    # first verilog file.

    if not special_file_found and not cfg.v_include:
      include_path = os.path.dirname( os.path.abspath( first_verilog_file ) )

    # Regex to extract verilog filenames from `include statements

    s._include_re = re.compile( r'"(?P<filename>[\w/\.-]*)"' )

    # Iterate through all source files and add any `include files to the
    # list of source files to import.

    for source in source_list:
      code += s._output_verilog_file( include_path, source )

    return code
