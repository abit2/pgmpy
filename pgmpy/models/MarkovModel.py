#!/usr/bin/env python3

from pgmpy.base import UndirectedGraph
import itertools
import networkx as nx
import numpy as np


class MarkovModel(UndirectedGraph):
    """
    Base class for markov model.

    A MarkovModel stores nodes and edges with potentials

    MarkovModel hold undirected edges.

    Parameters
    ----------
    data : input graph
        Data to initialize graph.  If data=None (default) an empty
        graph is created.  The data can be an edge list, or any
        NetworkX graph object.

    Examples
    --------
    Create an empty Markov Model with no nodes and no edges.

    >>> from pgmpy.models import MarkovModel
    >>> G = MarkovModel()

    G can be grown in several ways.

    **Nodes:**

    Add one node at a time:

    >>> G.add_node('a')

    Add the nodes from any container (a list, set or tuple or the nodes
    from another graph).

    >>> G.add_nodes_from(['a', 'b'])

    **Edges:**

    G can also be grown by adding edges.

    Add one edge,

    >>> G.add_edge('a', 'b')

    a list of edges,

    >>> G.add_edges_from([('a', 'b'), ('b', 'c')])

    If some edges connect nodes not yet in the model, the nodes
    are added automatically.  There are no errors when adding
    nodes or edges that already exist.

    **Shortcuts:**

    Many common graph features allow python syntax to speed reporting.

    >>> 'a' in G     # check if node in graph
    True
    >>> len(G)  # number of nodes in graph
    3

    Public Methods
    --------------
    add_node('node1')
    add_nodes_from(['node1', 'node2', ...])
    add_edge('node1', 'node2')
    add_edges_from([('node1', 'node2'),('node3', 'node4')])
    """

    def __init__(self, ebunch=None):
        super(MarkovModel, self).__init__(ebunch)

    def add_edge(self, u, v, **kwargs):
        """
        Add an edge between u and v.

        The nodes u and v will be automatically added if they are
        not already in the graph

        Parameters
        ----------
        u,v : nodes
            Nodes can be any hashable Python object.

        See Also
        --------
        add_edges_from : add a collection of edges

        Examples
        --------
        >>> from pgmpy.models import MarkovModel
        >>> G = MarkovModel()
        >>> G.add_nodes_from(['Alice', 'Bob', 'Charles'])
        >>> G.add_edge('Alice', 'Bob')
        """
        # check that there is no self loop.
        if u != v:
            super(MarkovModel, self).add_edge(u, v, **kwargs)
        else:
            raise ValueError('Self loops are not allowed')

    def add_factors(self, *factors):
        """
        Associate a factor to the graph.
        See factors class for the order of potential values

        Parameters
        ----------
        *factor: pgmpy.factors.factors object
            A factor object on any subset of the variables of the model which
            is to be associated with the model.

        Returns
        -------
        None

        See Also
        --------
        get_factors

        Examples
        --------
        >>> from pgmpy.models import MarkovModel
        >>> from pgmpy.factors import Factor
        >>> student = MarkovModel([('Alice', 'Bob'), ('Bob', 'Charles'),
        ...                        ('Charles', 'Debbie'), ('Debbie', 'Alice')])
        >>> factor = Factor(['Alice', 'Bob'], cardinality=[3, 2], np.random.rand(6))
        >>> student.add_factors(factor)
        """
        for factor in factors:
            if set(factor.variables) - set(factor.variables).intersection(
                    set(self.nodes())):
                raise ValueError("Factors defined on variable not in the model",
                                 factor)

            super(MarkovModel, self).add_factors(factor)

    def to_factor_graph(self):
        """
        Converts the markov model into factor graph.

        A factor graph contains two types of nodes. One type corresponds to
        random variables whereas the second type corresponds to factors over
        these variables. The graph only contains edges between variables and
        factor nodes. Each factor node is associated with one factor whose
        scope is the set of variables that are its neighbors.

        Examples
        --------
        >>> from pgmpy.models import MarkovModel
        >>> from pgmpy.factors import Factor
        >>> student = MarkovModel([('Alice', 'Bob'), ('Bob', 'Charles')])
        >>> factor1 = Factor(['Alice', 'Bob'], [3, 2], np.random.rand(6))
        >>> factor2 = Factor(['Bob', 'Charles'], [2, 2], np.random.rand(4))
        >>> student.add_factors(factor1, factor2)
        >>> factor_graph = student.to_factor_graph()
        """
        from pgmpy.models import FactorGraph
        factor_graph = FactorGraph()

        if not self.factors:
            raise ValueError('Factors not associated with the random variables.')

        factor_graph.add_nodes_from(self.nodes())
        for factor in self.factors:
            scope = factor.scope()
            factor_node = 'phi_' + '_'.join(scope)
            factor_graph.add_edges_from(itertools.product(scope, [factor_node]))
            factor_graph.add_factors(factor)

        return factor_graph

    def to_junction_tree(self):
        """
        Creates a junction tree (or clique tree) for a given markov model.

        For a given markov model (H) a junction tree (G) is a graph
        1. where each node in G corresponds to a maximal clique in H
        2. each sepset in G separates the variables strictly on one side of the
        edge to other.

        Examples
        --------
        >>> from pgmpy.models import MarkovModel
        >>> from pgmpy.factors import Factor
        >>> mm = MarkovModel()
        >>> mm.add_nodes_from(['x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7'])
        >>> mm.add_edges_from([('x1', 'x3'), ('x1', 'x4'), ('x2', 'x4'),
        ...                    ('x2', 'x5'), ('x3', 'x6'), ('x4', 'x6'),
        ...                    ('x4', 'x7'), ('x5', 'x7')])
        >>> phi = [Factor(edge, [2, 2], np.random.rand(4)) for edge in mm.edges()]
        >>> mm.add_factors(*phi)
        >>> junction_tree = mm.to_junction_tree()
        """
        from pgmpy.models import JunctionTree

        # Triangulate the graph to make it chordal
        triangulated_graph = self.triangulate()

        # Find maximal cliques in the chordal graph
        cliques = list(map(tuple, nx.find_cliques(triangulated_graph)))

        # Create a complete graph with all the cliques as nodes and
        # weight of the edges being the length of sepset between two cliques
        complete_graph = UndirectedGraph()
        edges = list(itertools.combinations(cliques, 2))
        weights = list(map(lambda x: len(set(x[0]) - set(x[1])), edges))
        for edge, weight in zip(edges, weights):
            complete_graph.add_edge(*edge, weight=-weight)

        # Create clique trees by minimum (or maximum) spanning tree method
        clique_trees = JunctionTree(nx.minimum_spanning_tree(complete_graph).edges())

        factor = self.factors[0]
        factor = factor.product(*[self.factors[i] for i in
                                  range(1, len(self.factors))])
        if set(factor.scope()) != set(self.nodes()):
            ValueError('Factor for all the random variables not specified')

        all_vars = set(self.nodes())

        for node in clique_trees.nodes():
            marginalised_nodes = all_vars - set(node)
            factor_copy = factor.marginalize(list(marginalised_nodes),
                                             inplace=False)
            clique_trees.add_factors(factor_copy)

        return clique_trees