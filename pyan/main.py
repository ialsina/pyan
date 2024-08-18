#!/usr/bin/env python3

# -*- coding: utf-8 -*-
"""
    pyan.py - Generate approximate call graphs for Python programs.

    This program takes one or more Python source files, does a superficial
    analysis, and constructs a directed graph of the objects in the combined
    source, and how they define or use each other.  The graph can be output
    for rendering by e.g. GraphViz or yEd.
"""

from argparse import ArgumentParser
from glob import glob
import os
import sys

from .analyzer import CallGraphVisitor
from .visgraph import VisualGraph
from .writers import DotWriter, HTMLWriter, SVGWriter, TgfWriter, YedWriter
from .log import setup_logging, logger

def _get_parser():
    usage = """%(prog)s FILENAME... [--dot|--tgf|--yed|--svg|--html]"""
    desc = (
        "Analyse one or more Python source files and generate an "
        "approximate call graph of the modules, classes and functions "
        "within them."
    )

    parser = ArgumentParser(usage=usage, description=desc)
    parser.add_argument("glob", action="store", nargs="+", metavar="FILENAME(S)")
    parser.add_argument("--dot", action="store_true", default=False, help="output in GraphViz dot format")
    parser.add_argument("--tgf", action="store_true", default=False, help="output in Trivial Graph Format")
    parser.add_argument("--svg", action="store_true", default=False, help="output in SVG Format")
    parser.add_argument("--html", action="store_true", default=False, help="output in HTML Format")
    parser.add_argument("--yed", action="store_true", default=False, help="output in yEd GraphML Format")
    parser.add_argument("-o", "--output", dest="output", help="write graph to OUTPUT", metavar="OUTPUT", default=None)
    parser.add_argument("--namespace", dest="namespace", help="filter for NAMESPACE", metavar="NAMESPACE", default=None)
    parser.add_argument("--function", dest="function", help="filter for FUNCTION", metavar="FUNCTION", default=None)
    parser.add_argument("-l", "--log", dest="logname", help="write log to LOG", metavar="LOG")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, dest="verbose", help="verbose output")
    parser.add_argument(
        "-V",
        "--very-verbose",
        action="store_true",
        default=False,
        dest="very_verbose",
        help="even more verbose output (mainly for debug)",
    )
    parser.add_argument(
        "-d",
        "--defines",
        action="store_true",
        dest="draw_defines",
        help="add edges for 'defines' relationships [default]",
    )
    parser.add_argument(
        "-n",
        "--no-defines",
        action="store_false",
        default=True,
        dest="draw_defines",
        help="do not add edges for 'defines' relationships",
    )
    parser.add_argument(
        "-u",
        "--uses",
        action="store_true",
        default=True,
        dest="draw_uses",
        help="add edges for 'uses' relationships [default]",
    )
    parser.add_argument(
        "-N",
        "--no-uses",
        action="store_false",
        default=True,
        dest="draw_uses",
        help="do not add edges for 'uses' relationships",
    )
    parser.add_argument(
        "-c",
        "--colored",
        action="store_true",
        default=False,
        dest="colored",
        help="color nodes according to namespace [dot only]",
    )
    parser.add_argument(
        "-G",
        "--grouped-alt",
        action="store_true",
        default=False,
        dest="grouped_alt",
        help="suggest grouping by adding invisible defines edges [only useful with --no-defines]",
    )
    parser.add_argument(
        "-g",
        "--grouped",
        action="store_true",
        default=False,
        dest="grouped",
        help="group nodes (create subgraphs) according to namespace [dot only]",
    )
    parser.add_argument(
        "-e",
        "--nested-groups",
        action="store_true",
        default=False,
        dest="nested_groups",
        help="create nested groups (subgraphs) for nested namespaces (implies -g) [dot only]",
    )
    parser.add_argument(
        "--dot-rankdir",
        default="TB",
        dest="rankdir",
        help=(
            "specifies the dot graph 'rankdir' property for "
            "controlling the direction of the graph. "
            "Allowed values: ['TB', 'LR', 'BT', 'RL']. "
            "[dot only]"
        ),
    )
    parser.add_argument(
        "-a",
        "--annotated",
        action="store_true",
        default=False,
        dest="annotated",
        help="annotate with module and source line number",
    )
    parser.add_argument(
        "--root",
        default=None,
        dest="root",
        help="Package root directory. Is inferred by default.",
    )
    return parser

def _get_graph_options(args):
    # TODO: Use subparser
    return {
        "draw_defines": args.draw_defines,
        "draw_uses": args.draw_uses,
        "colored": args.colored,
        "grouped_alt": args.grouped_alt,
        "grouped": args.grouped,
        "nested_groups": args.nested_groups,
        "annotated": args.annotated,
    }

def _write_graphs(graph, args):
    writers = []
    if args.dot:
        DotWriter(graph, options=["rankdir=" + args.rankdir], output=args.output).run()
    if args.html:
        HTMLWriter(graph, options=["rankdir=" + args.rankdir], output=args.output).run()
    if args.svg:
        SVGWriter(graph, options=["rankdir=" + args.rankdir], output=args.output).run()
    if args.tgf:
        TgfWriter(graph, output=args.output).run()
    if args.yed:
        YedWriter(graph, output=args.output).run()

def main(cli_args=None):
    if cli_args is None:
        cli_args = sys.argv[1:]

    parser = _get_parser()
    args = parser.parse_args(cli_args)
    filenames = [fn2 for fn in args.glob for fn2 in glob(fn, recursive=True)]

    if len(args.glob) == 0:
        parser.error("Need one or more filenames to process")
    elif len(filenames) == 0:
        parser.error("No files found matching given glob: %s" % " ".join(args.glob))

    if args.nested_groups:
        args.grouped = True

    graph_options = _get_graph_options(args)
    setup_logging(verbose=args.verbose,
                  very_verbose=args.very_verbose,
                  file=args.logname,
                  )

    # determine root
    if args.root is not None:
        root = os.path.abspath(args.root)
    else:
        root = None

    visitor = CallGraphVisitor(filenames, root=root)

    if args.function or args.namespace:
        if args.function:
            function_name = args.function.split(".")[-1]
            namespace = ".".join(args.function.split(".")[:-1])
            node = visitor.create_node(namespace, function_name)
        else:
            node = None
        visitor.filter(node=node, namespace=args.namespace)

    graph = VisualGraph.from_visitor(visitor, options=graph_options)
    _write_graphs(graph, args)


if __name__ == "__main__":
    main()
