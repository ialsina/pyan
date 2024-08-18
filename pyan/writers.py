#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Graph markup writers."""

from abc import ABC, abstractmethod
from io import StringIO
import os
import subprocess
import sys
from pathlib import Path

from jinja2 import Template
from .log import logger
from .visgraph import VisualGraph



class Writer(ABC):
    def __init__(self, graph: VisualGraph, output=None, tabstop=4):
        self.graph = graph
        self.indent_level = 0
        self.output = self._validate_output(output)
        self.tabstop = self._validate_tabstop(tabstop)
        self._outstream = None

    @staticmethod
    def _validate_output(output):
        if output is None:
            return None
        if not isinstance(output, (str, Path, StringIO)):
            raise TypeError(
                "output must be of type 'str', 'Path', 'StringIO' or None, "
                f"but was '{output.__class__.__name__}'."
            )
        return output

    @staticmethod
    def _validate_tabstop(tabstop):
        if not isinstance(tabstop, int):
            raise TypeError(
                "tabstop must be of type 'int', "
                f"but was '{tabstop.__class__.__name__}'."
            )
        return " " * tabstop

    @abstractmethod
    def start_graph(self):
        pass

    @abstractmethod
    def start_subgraph(self, graph):
        pass

    @abstractmethod
    def write_node(self, node):
        pass

    @abstractmethod
    def start_edges(self):
        pass

    @abstractmethod
    def write_edge(self, edge):
        pass

    @abstractmethod
    def finish_edges(self):
        pass

    @abstractmethod
    def finish_subgraph(self, graph):
        pass

    @abstractmethod
    def finish_graph(self):
        pass

    @property
    def outstream(self):
        if self._outstream is None:
            raise IOError(
                "Stream isn't open yet. Please call method `open`."
            )
        return self._outstream

    def close(self):
        if self.output is None:
            return
        if not isinstance(self.outstream, StringIO):
            self.outstream.close()

    def open(self):
        if self.output is None:
            self._outstream = sys.stdout
        elif isinstance(self.output, StringIO):  # write to stream
            self._outstream = self.output
        else:
            self._outstream = open(self.output, "w", encoding="utf-8")

    def dedent(self, level=1):
        self.indent_level -= level

    def indent(self, level=1):
        self.indent_level += level

    def run(self):
        logger.info("%s running" % type(self))
        self.open()
        self.start_graph()
        self.write_subgraph(self.graph)
        self.write_edges()
        self.finish_graph()
        self.close()

    def write(self, line):
        self.outstream.write(
            self.tabstop * self.indent_level + line + "\n"
        )

    def write_subgraph(self, graph):
        self.start_subgraph(graph)
        for node in graph.nodes:
            self.write_node(node)
        for subgraph in graph.subgraphs:
            self.write_subgraph(subgraph)
        self.finish_subgraph(graph)

    def write_edges(self):
        self.start_edges()
        for edge in self.graph.edges:
            self.write_edge(edge)
        self.finish_edges()


class TgfWriter(Writer):
    def __init__(self, graph, output):
        super().__init__(graph, output=output)
        self.i = 1
        self.id_map = {}

    def start_graph(self):
        pass

    def start_subgraph(self, graph):
        # WARN: Check if it really isn't needed
         pass

    def write_node(self, node):
        self.write("%d %s" % (self.i, node.label))
        self.id_map[node] = self.i
        self.i += 1

    def start_edges(self):
        self.write("#")

    def write_edge(self, edge):
        flavor = "U" if edge.flavor == "uses" else "D"
        self.write("%s %s %s" % (self.id_map[edge.source], self.id_map[edge.target], flavor))

    def finish_edges(self):
        pass

    def finish_subgraph(self, graph):
        # WARN: Check if it really isn't needed
         pass

    def finish_graph(self):
        pass


class DotWriter(Writer):
    def __init__(self, graph, options, output, tabstop=4):
        super().__init__(graph=graph, output=output, tabstop=tabstop)
        options = options or []
        if graph.grouped:
            options += ['clusterrank="local"']
        self.options = ", ".join(options)
        self.grouped = graph.grouped

    def start_graph(self):
        self.write("digraph G {")
        self.write("    graph [" + self.options + "];")
        self.indent()

    def start_subgraph(self, graph):
        logger.info("Start subgraph %s" % graph.label)
        # Name must begin with "cluster" to be recognized as a cluster by GraphViz.
        self.write("subgraph cluster_%s {\n" % graph.id)
        self.indent()

        # translucent gray (no hue to avoid visual confusion with any
        # group of colored nodes)
        self.write('graph [style="filled,rounded", fillcolor="#80808018", label="%s"];' % graph.label)

    def write_node(self, node):
        logger.info("Write node %s" % node.label)
        self.write(
            '%s [label="%s", style="filled", fillcolor="%s",'
            ' fontcolor="%s", group="%s"];' % (node.id, node.label, node.fill_color, node.text_color, node.group)
        )

    def start_edges(self):
        pass

    def write_edge(self, edge):
        source = edge.source
        target = edge.target
        color = edge.color
        if edge.flavor == "defines":
            self.write('    %s -> %s [style="dashed",  color="%s"];' % (source.id, target.id, color))
        else:  # edge.flavor == 'uses':
            self.write('    %s -> %s [style="solid",  color="%s"];' % (source.id, target.id, color))

    def finish_edges(self):
        pass

    def finish_subgraph(self, graph):
        logger.info("Finish subgraph %s" % graph.label)
        # terminate previous subgraph
        self.dedent()
        self.write("}")

    def finish_graph(self):
        self.write("}")  # terminate "digraph G {"


class DotAdapter(DotWriter, ABC):

    def __init__(self, graph, options, output, tabstop=4):
        super().__init__(graph=graph, options=options, output=StringIO(), tabstop=tabstop)
        self.converted_output = self._validate_output(output)

    @staticmethod
    @abstractmethod
    def convert(stream) -> str:
        pass

    def close(self):
        converted_output = self.converted_output
        converted = self.convert(self.outstream)
        if converted_output is None:
            sys.stdout.write(converted)
        elif isinstance(converted_output, StringIO):
            converted_output.write(converted)
        else:
            with open(converted, "w", encoding="utf-8") as f:
                f.write(converted)
        super().close()


class SVGWriter(DotAdapter):
    @staticmethod
    def convert(stream):
        return subprocess.run(
            "dot -Tsvg", shell=True, stdout=subprocess.PIPE, input=stream.getvalue().encode()
        ).stdout.decode()


class HTMLWriter(SVGWriter):
    @staticmethod
    def convert(stream):
        svg = SVGWriter.convert(stream)
        # TODO: Import a root directory from a config file in settings
        with open(os.path.join(os.path.dirname(__file__), "callgraph.html"), "r") as f:
            template = Template(f.read())
        html = template.render(svg=svg)
        return html


class YedWriter(Writer):
    def __init__(self, graph, output, tabstop=2):
        super().__init__(graph, output=output, tabstop=tabstop)
        self.grouped = graph.grouped
        self.indent_level = 0
        self.edge_id = 0

    def start_graph(self):
        self.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
        self.write(
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"'
            " xmlns:java="
            '"http://www.yworks.com/xml/yfiles-common/1.0/java"'
            " xmlns:sys="
            '"http://www.yworks.com/xml/yfiles-common/markup/primitives'
            '/2.0" xmlns:x="http://www.yworks.com/xml/yfiles-common/'
            'markup/2.0" xmlns:xsi="http://www.w3.org/2001/'
            'XMLSchema-instance" xmlns:y="http://www.yworks.com/xml/'
            'graphml" xmlns:yed="http://www.yworks.com/xml/yed/3"'
            ' xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns'
            " http://www.yworks.com/xml/schema/graphml/1.1/"
            'ygraphml.xsd">'
        )
        self.indent()
        self.write('<key for="node" id="d0" yfiles.type="nodegraphics"/>')
        self.write('<key for="edge" id="d1" yfiles.type="edgegraphics"/>')
        self.write('<graph edgedefault="directed" id="Graph">')
        self.indent()

    def start_subgraph(self, graph):
        logger.info("Start subgraph %s" % graph.label)

        self.write('<node id="%s:" yfiles.foldertype="group">' % graph.id)
        self.indent()
        self.write('<data key="d0">')
        self.indent()
        self.write("<y:ProxyAutoBoundsNode>")
        self.indent()
        self.write('<y:Realizers active="0">')
        self.indent()
        self.write("<y:GroupNode>")
        self.indent()
        self.write('<y:Fill color="#CCCCCC" transparent="false"/>')
        self.write(
            '<y:NodeLabel modelName="internal" modelPosition="t" alignment="right">%s</y:NodeLabel>' % graph.label
        )
        self.write('<y:Shape type="roundrectangle"/>')
        self.dedent()
        self.write("</y:GroupNode>")
        self.dedent()
        self.write("</y:Realizers>")
        self.dedent()
        self.write("</y:ProxyAutoBoundsNode>")
        self.dedent()
        self.write("</data>")
        self.write('<graph edgedefault="directed" id="%s::">' % graph.id)
        self.indent()

    def write_node(self, node):
        logger.info("Write node %s" % node.label)
        width = 20 + 10 * len(node.label)
        self.write('<node id="%s">' % node.id)
        self.indent()
        self.write('<data key="d0">')
        self.indent()
        self.write("<y:ShapeNode>")
        self.indent()
        self.write('<y:Geometry height="%s" width="%s"/>' % ("30", width))
        self.write('<y:Fill color="%s" transparent="false"/>' % node.fill_color)
        self.write('<y:BorderStyle color="#000000" type="line" width="1.0"/>')
        self.write("<y:NodeLabel>%s</y:NodeLabel>" % node.label)
        self.write('<y:Shape type="ellipse"/>')
        self.dedent()
        self.write("</y:ShapeNode>")
        self.dedent()
        self.write("</data>")
        self.dedent()
        self.write("</node>")

    def start_edges(self):
        pass

    def write_edge(self, edge):
        self.edge_id += 1
        source = edge.source
        target = edge.target
        self.write('<edge id="%s" source="%s" target="%s">' % (self.edge_id, source.id, target.id))
        self.indent()
        self.write('<data key="d1">')
        self.indent()
        self.write("<y:PolyLineEdge>")
        self.indent()
        if edge.flavor == "defines":
            self.write('<y:LineStyle color="%s" type="dashed" width="1.0"/>' % edge.color)
        else:
            self.write('<y:LineStyle color="%s" type="line" width="1.0"/>' % edge.color)
        self.write('<y:Arrows source="none" target="standard"/>')
        self.write('<y:BendStyle smoothed="true"/>')
        self.dedent()
        self.write("</y:PolyLineEdge>")
        self.dedent()
        self.write("</data>")
        self.dedent()
        self.write("</edge>")

    def finish_edges(self):
        pass

    def finish_subgraph(self, graph):
        logger.info("Finish subgraph %s" % graph.label)
        self.dedent()
        self.write("</graph>")
        self.dedent()
        self.write("</node>")

    def finish_graph(self):
        self.dedent(2)
        self.write("  </graph>")
        self.dedent()
        self.write("</graphml>")

