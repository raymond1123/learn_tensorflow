# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Common methods to display parts of SQL query results."""

from functools import partial
from apitools.base.py import encoding
from googlecloudsdk.core.resource import resource_printer


def _GetAdditionalProperty(properties, property_key, not_found_value='Unknown'):
  """Gets the value for the given key in a list of properties.

  Looks through a list of properties and tries to find the value for the given
  key. If it's not found, not_found_value is returned.

  Args:
    properties: A dictionary of key string, value string pairs.
    property_key: The key string for which we want to get the value.
    not_found_value: The string value to return if the key is not found.

  Returns:
    A string containing the value for the given key, or `not_found_value` if
    the key is not found.
  """
  for prop in properties:
    if prop.key == property_key:
      if hasattr(prop, 'value'):
        return prop.value
      break
  return not_found_value


def _ConvertToTree(plan_nodes):
  """Creates tree of Node objects from the plan_nodes in server response.

  Args:
    plan_nodes (spanner_v1_messages.PlanNode[]): The plan_nodes from the server
      response. Plan nodes are topologically sorted.

  Returns:
    A Node, root of a tree built from `plan_nodes`.
  """
  # A dictionary from the index in plan_nodes to Node object.
  node_dict = {}
  # If we start at the end then by the time we get to a node's parent, that
  # node must already exist in node_dict.
  for node in reversed(plan_nodes):
    n = Node(node)
    if node.childLinks:
      for link in node.childLinks:
        n.children.append(node_dict[link.childIndex])
    if node.index:
      node_dict[node.index] = n
    # The only node without an index is the root.
    else:
      return n


def QueryHasAggregateStats(result):
  """Checks if the given results have aggregate statistics.

  Args:
    result (spanner_v1_messages.ResultSetStats): The stats for a query.

  Returns:
    A boolean indicating whether 'results' contain aggregate statistics.
  """
  return hasattr(
      result, 'stats') and getattr(result.stats, 'queryStats', None) is not None


def DisplayQueryAggregateStats(query_stats, out):
  """Displays the aggregate stats for a Spanner SQL query.

  Looks at the queryStats portion of the query response and prints some of
  the aggregate statistics.

  Args:
    query_stats (spanner_v1_messages.ResultSetStats.QueryStatsValue): The query
      stats taken from the server response to a query.
    out: Output stream to which we print.
  """
  # additional_properties = query_stats.additionalProperties

  get_prop = partial(_GetAdditionalProperty, query_stats.additionalProperties)
  stats = {
      'total_elapsed_time': get_prop('elapsed_time'),
      'cpu_time': get_prop('cpu_time'),
      'rows_returned': get_prop('rows_returned'),
      'rows_scanned': get_prop('rows_scanned')
  }
  resource_printer.Print(
      stats,
      'table[box](total_elapsed_time, cpu_time, rows_returned, rows_scanned)',
      out=out)


def DisplayQueryPlan(result, out):
  """Displays a graphical query plan for a query.

  Args:
    result (spanner_v1_messages.ResultSet): The server response to a query.
    out: Output stream to which we print.
  """
  node_tree_root = _ConvertToTree(result.stats.queryPlan.planNodes)
  node_tree_root.PrettyPrint(out)


def DisplayQueryResults(result, out):
  """Prints the result rows for a query.

  Args:
    result (spanner_v1_messages.ResultSet): The server response to a query.
    out: Output stream to which we print.
  """
  fields = [field.name for field in result.metadata.rowType.fields]
  # Create the format string we pass to the table layout.
  table_format = ','.join('row.slice({0}).join():label="{1}"'.format(i, f)
                          for i, f in enumerate(fields))
  rows = [{'row': encoding.MessageToPyValue(row.entry)} for row in result.rows]

  # Can't use the PrintText method because we want special formatting.
  resource_printer.Print(rows, 'table({0})'.format(table_format), out=out)


class Node(object):
  """Represents a single node in a Spanner query plan.

  Attributes:
    properties (spanner_v1_messages.PlanNode): The details about a given node
      as returned from the server.
    children: A list of children in the query plan of type Node.
  """

  def __init__(self, properties, children=None):
    self.children = children or []
    self.properties = properties

  def _DisplayKindAndName(self, out, prepend, stub):
    """Prints the kind of the node (SCALAR or RELATIONAL) and its name."""
    kind_and_name = '{}{} {} {}'.format(prepend, stub, self.properties.kind,
                                        self.properties.displayName)
    out.Print(kind_and_name)

  def PrettyPrint(self, out, prepend=None, is_last=True, is_root=True):
    """Prints a string representation of this node in the tree.

    Args:
      out: Output stream to which we print.
      prepend: String that precedes any information about this node to maintain
        a visible hierarchy.
      is_last: Boolean indicating whether this node is the last child of its
        parent.
      is_root: Boolean indicating whether this node is the root of the tree.
    """
    prepend = prepend or ''
    # The symbol immediately before node kind to indicate that this is a child
    # of its parents. All nodes except the root get one.
    stub = '' if is_root else (r'\-' if is_last else '+-')

    self._DisplayKindAndName(out, prepend, stub)

    for idx, child in enumerate(self.children):
      is_last_child = idx == len(self.children) - 1
      # The amount each subsequent level in the tree is indented.
      indent = '   '
      # Connect all immediate children to each other with a vertical line
      # of '|'. Don't extend this line down past the last child node. It's
      # cleaner.
      child_prepend = prepend + (' ' if is_last else '|') + indent
      child.PrettyPrint(
          out, prepend=child_prepend, is_last=is_last_child, is_root=False)