"""Simple decision tree implementation"""

import numpy as np
import pandas as pd
from math import inf
import logging

logger = logging.getLogger(__name__)


class Node(object):
    """Node - a basic element of a decision tree structure."""

    def __init__(self, data: pd.DataFrame, target_column=0, level: int=0,
                 indices=None, terminal=False, parent=None, which_child=0):
        """Initialise a tree node.

        Parameters
        ----------
        data            :   pd.DataFrame
            data frame containing all attributes (including the target attribute) for the training set
        target_column   :   int
            index of a column containing the target variable
        level           :   int
            node level (0 for a root)
        indices         :   iterable
            set of sample indices belonging to the given node (as distributed by the parent)
        terminal        :   bool
            True if a node should be a leaf (not for further splitting)
        parent          :   Node
            the parent instance
        which_child     :   0
            which child in a row is the current instance from the point of view of the parent
        """

        self._level = level
        self._terminal = terminal
        self._class = None

        if level and not parent:
            raise ValueError(f"Non-root node (level {level}) must have a parent")

        if not level and parent:
            raise ValueError("Root node should not have any parent")

        self._parent = parent

        self._target = target_column if not level else parent.target_column
        self._validate_data(data, self._target)
        self._data = data

        self._which_child = which_child

        self._children = []

        self._split_attribute = None
        self._split_thresholds = []

        if indices is None:
            if not level:
                indices = set(data.index)
            else:
                raise ValueError("indices=None not allowed for a non-root node (use empty set if necessary)")
        else:
            indices = set(indices)

        self._indices_distributed = set()
        self._indices_remaining = indices

        self._entropy = self.calculate_entropy_labels((self.class_labels.to_list()))

    @staticmethod
    def _validate_data(data, target_column):
        target = data.keys().to_list()[target_column]
        labels = data[target]

        if labels.dtype not in [int, np.int64]:
            raise TypeError(f"Class labels (column '{target}') must be integers (got {labels.dtype})")

    def __str__(self):
        if self.level:
            attr, th = self.get_creation_stamp()
            root = f'for {th[0]} < {attr} <= {th[1]}, trace: {self.trace()}'
        else:
            root = 'root'

        leaf = '(leaf)' if self._terminal else f'with {len(self.children)} children'

        split = ""
        if self._split_attribute:
            split = f"; split at attribute '{self._split_attribute}' with thresholds: {self._split_thresholds[1:-1]}"

        sub = f'; subtree depth: {self.depth}' if len(self._children) else ''

        return f"Level {self.level} tree node ({root}); {'' if self.resolved else 'not '}resolved {leaf}{sub}{split}"

    @property
    def full_data(self):
        return self._data

    @property
    def data(self):
        return self._data.loc[self.indices]

    @property
    def level(self):
        return self._level

    @property
    def depth(self):
        if self.children:
            return max(child.depth for child in self.children) + 1

        return 0

    @property
    def indices_distributed(self):
        return self._indices_distributed

    @property
    def indices_remaining(self):
        return self._indices_remaining

    @property
    def indices(self):
        return self._indices_distributed | self._indices_remaining  # set union

    @property
    def resolved(self):
        return True if (self._terminal or not self._indices_remaining) else False

    @property
    def split_thresholds(self):
        return self._split_thresholds

    def split_thresholds_for_child(self, which_child):
        return self._split_thresholds[which_child:which_child+2]

    def get_creation_stamp(self):
        return self.parent.split_attribute, self.parent.split_thresholds_for_child(self._which_child)

    @property
    def split_attribute(self):
        return self._split_attribute

    @property
    def target_attribute(self):
        return self.data.keys().to_list()[self.target_column]

    @property
    def input_attributes(self):
        all_keys = self.data.keys().to_list()
        return all_keys[:self.target_column] + all_keys[self.target_column+1:]

    @property
    def target_column(self):
        return self._target

    @property
    def class_labels(self):
        return self.data[self.target_attribute]

    @property
    def n_classes(self):
        return len(set(self.class_labels))

    @property
    def n_points(self):
        return len(self.data)

    @property
    def uniform(self):
        return self.n_classes == 1

    @staticmethod
    def get_label_occurrences(labels: list):
        """Count how many times each label is repeated"""

        return [labels.count(c) for c in set(labels)]

    @staticmethod
    def get_prevalent_label(labels: list):
        """Get label of the node - the most frequent from the samples of the node"""

        return list(set(labels))[np.argmax(Node.get_label_occurrences(labels))]

    @staticmethod
    def calculate_entropy_probs(probs):
        """Calculate variable entropy from variable value probabilities (list of probabilities/value occurrences)"""

        probs_norm = np.array(probs)
        probs_norm = probs_norm / probs_norm.sum()

        return - (probs_norm * np.log2(probs_norm)).sum()

    @staticmethod
    def calculate_entropy_labels(labels):
        """Calculate variable entropy from variable values (list of labels)"""

        return Node.calculate_entropy_probs(Node.get_label_occurrences(labels))

    def entropy(self):
        """Calculate entropy of the node (considering occurrences of each class label)"""

        return self._entropy

    @property
    def parent(self):
        return self._parent

    @property
    def children(self):
        return self._children

    def _add_child(self, child):
        if not isinstance(child, type(self)):
            raise TypeError(f"Child should be of type {type(self)}")

        chis = child.indices

        if not chis.issubset(self._indices_remaining):
            raise ValueError("Child indices are not a subset of the parent indices remaining to be distributed)")

        self._indices_distributed |= chis   # set union
        self._indices_remaining -= chis     # set difference
        self._children.append(child)

    def add_new_child(self, indices):
        """Create a new child instance and add it to the node's children.

        Parameters
        ----------
        indices     :   iterable
            indices from the node's samples to be assigned to the child
        """

        child = self.__class__(self._data, level=self.level+1, indices=indices, parent=self,
                               which_child=len(self.children))
        self._add_child(child)

    def add_final_child(self):
        """Add a child to the node such as the rest of the not yet distributed indices are assigned to the child"""

        self.add_new_child(self.indices_remaining)

    def _get_split_indices(self, attribute, thresholds):
        """Split node sample indices for given attribute and threshold"""

        th = sorted(list(thresholds) + [-inf, inf])

        vals = self.data[attribute]

        all_indices = []

        for i in range(1, len(th)):
            indices = vals.index[(vals > th[i - 1]) & (vals <= th[i])]
            all_indices.append(indices)

        return th, all_indices

    def get_split_information_gain(self, attribute, thresholds):
        """Calculate expected information gain after splitting at given attribute with given thresholds"""

        _, all_indices = self._get_split_indices(attribute, thresholds)
        split_labels = [self.class_labels.loc[indices].to_list() for indices in all_indices]

        n_tot = len(self.data)
        remainder = sum([(len(labels)/n_tot * self.calculate_entropy_labels(labels)) for labels in split_labels])

        return self.entropy() - remainder

    def split_at(self, attribute, thresholds):
        """Split node on a continuous attribute."""

        if attribute == self.target_attribute:
            raise ValueError(f"Cannot split on the target attribute ('{attribute}')")

        if self.resolved:
            logger.warning("Splitting an already resolved node - existing children will be removed")
            self.undo_split()

        th, all_indices = self._get_split_indices(attribute, thresholds)

        for i, indices in enumerate(all_indices):
            if not len(indices):
                logger.warning(f"No observations in value range ({th[i]}, {th[i+1]}] for attribute '{attribute}'")
            self.add_new_child(indices)

        if not self.resolved:
            logger.warning(f"Could not perform full split on attribute {attribute} - possibly missing values")
            self.add_final_child()

        self._split_thresholds = th
        self._split_attribute = attribute

    def undo_split(self):
        """Remove children of a node and make it terminal"""

        logger.debug(f"Undoing split at node {self.trace()}")
        self._children = []
        self._indices_remaining = self._indices_distributed.copy()
        self._indices_distributed = set()

    def choose_split_threshold(self, attribute, n=10):
        """Perform search for the best threshold for split at given attribute.

        'n' - granularity of the search (check every n-th threshold candidate)"""

        vals = np.sort(np.array(self.data[attribute]))  # values for the attribute
        th_cand = 0.5 * (vals[1:] + vals[:-1])  # threshold candidates - consecutive mid-points
        th_cand = th_cand[::n]  # check every n-th

        gains = [self.get_split_information_gain(attribute, [th]) for th in th_cand]

        idx = np.argmax(gains)

        chosen_gain = gains[idx]
        chosen_threshold = th_cand[idx]
        logger.debug(f"For attribute '{attribute}', best gain is {chosen_gain:.2g} "
                     f"(at threshold {chosen_threshold:.3g})")

        return chosen_gain, chosen_threshold

    def choose_split_attribute(self, **kwargs):
        """Compute information gains for splits at each attribute (for each of them, adjust the threshold) and choose
        the best one."""

        all_attributes = self.input_attributes
        all_gains = len(all_attributes) * [0]
        all_thresholds = all_gains[:]

        logger.debug(f"Choosing split attribute for {self}")
        for i, attribute in enumerate(all_attributes):
            all_gains[i], all_thresholds[i] = self.choose_split_threshold(attribute, **kwargs)

        idx = np.argmax(all_gains)
        chosen_attribute = all_attributes[idx]
        logger.debug(f"Chosen attribute: {chosen_attribute} (expected gain: {all_gains[idx]:.3g})")

        return chosen_attribute, [all_thresholds[idx]]

    def split(self, **kwargs):
        """Split a node automatically (determine the attribute and threshold)."""

        s = self.choose_split_attribute(**kwargs)
        logger.info(f"Splitting at attribute '{s[0]}' with threshold: {s[1][0]:.2g}")
        self.split_at(*s)

    def terminate(self):
        """Mark node as terminal."""

        if self.children:
            raise RuntimeError("Could not terminate a node with children")

        self._terminal = True
        self._class = self.get_prevalent_label(self.class_labels.to_list())

    def learn(self, max_depth=5, **kwargs):
        """Grow the decision tree to a certain maximal depth."""

        if max_depth < 0:
            raise ValueError(f"Invalid maximal depth ({max_depth})")

        if max_depth == 0:
            logger.info(f"Reached the maximal depth (at {self.trace()}) - no further splitting")
            self.terminate()
            return 1

        if self.uniform:
            logger.info(f"Node {self.trace()} is an uniform node - no further splitting")
            self.terminate()
            return 1

        if self._terminal:
            logger.info(f"Splitting a node previously marked as terminal: {self.trace()}")
            self._terminal = False

        logger.info(f"Performing split of node {self.trace()}")
        self.split(**kwargs)

        logger.debug(f"Learning children of node {self.trace()}")
        for child in self.children:
            child.learn(max_depth=max_depth-1, **kwargs)

    def print_terminal_labels(self):
        """Print sample labels at each terminal node."""

        if len(self.children):
            for child in self.children:
                child.print_terminal_labels()

        else:
            print(f"Level {self.level} node, {self.trace()}: class {self._class} ({self.class_labels.to_list()})")

    def trace(self):
        """Return a node stamp - 'which child' parameter from the root to the node."""

        if self.parent:
            return self.parent.trace() + [self._which_child]

        else:
            return []

    def prune(self, min_points=2):
        """Prune the tree - remove children if any of them has less than min_points samples."""

        if len(self.children):
            if any(child.n_points < min_points for child in self.children):
                logger.info(f"Pruning at node {self.trace()}")
                self.undo_split()
                self.terminate()

            else:
                for child in self.children:
                    child.prune(min_points=min_points)

    def get_child(self, obs):
        """Return the relevant child instance based on the range the attribute value falls into"""

        if isinstance(obs, pd.DataFrame):
            if len(obs) > 1:
                raise ValueError(f"Observation should be a single-line DataFrame (got {len(obs)})")
            return self._get_child_from_df(obs)
        elif isinstance(obs, (int, float)):
            return self._get_child_from_value(obs)
        else:
            raise TypeError(f"Observation should be either a single-line DataFrame instance or a number (int, float)")

    def _get_child_from_value(self, attr_value):
        """Pick the relevant child instance based on the attribute value (assume it is the split attribute)"""

        return self.children[np.searchsorted(self._split_thresholds, attr_value) - 1]

    def _get_child_from_df(self, observation):
        """Pick the relevant child instance based on a new DataFrame-like object (pick the attribute first)"""

        return self._get_child_from_value(observation[self._split_attribute].item())

    def predict_class(self, observation):
        """Predict class for a single observation."""

        if self._terminal:
            return self._class

        return self._get_child_from_df(observation).predict_class(observation)

    def predict_classes(self, observations: pd.DataFrame):
        """Predict classes for a set of observations."""

        classes = []

        n = len(observations)

        for i in range(n):
            obs = observations.iloc[i]
            classes.append(self.predict_class(obs))

        return classes

    def test(self, observations: pd.DataFrame):
        """Predict classes for a set of observations and report the testing score."""

        pred_classes = self.predict_classes(observations)               # predicted classes
        true_classes = observations[self.target_attribute].to_list()    # actual classes

        n = len(true_classes)
        correct = sum(pred_classes[i] == true_classes[i] for i in range(n))
        score = correct / n

        logger.info(f"Testing score: {score} ({correct}/{n} samples)")

        return true_classes, pred_classes

    @staticmethod
    def train_and_test(data: pd.DataFrame, train_idx, test_idx, target_column=0, max_depth=5, min_points=2, n=10):
        """Initialise, train and test a decision tree.

        Parameters
        ----------
        data            :   pandas.DataFrame
            classification data (containing the class labels; both training and testing data)
        train_idx       :   iterable
            indices of samples from the data to be used in training
        test_idx        :   iterable
            indices of samples from the data to be used in testing
        target_column   :   int
            index of the class labels column in data
        max_depth       :   int
            maximal depth of the tree (number of children generations of the root)
        min_points      :   int
            minimal number of samples in a leaf (if less, the node will be pruned - its parent's split will be undone
        n               :   int
            granularity for the threshold search (use every n-th value);
            learning time grows approximately inversely proportionally to n
        """

        # Initialise a decision tree
        tree = Node(data, target_column=target_column, indices=train_idx)

        # perform learning
        tree.learn(max_depth=max_depth, n=n)

        # prune
        tree.prune(min_points=min_points)

        return tree.test(data.iloc[test_idx])
