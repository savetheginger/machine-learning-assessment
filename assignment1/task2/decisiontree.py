"""Simple decision tree implementation"""

import numpy as np
import pandas as pd
from math import inf
import logging
import coloredlogs

logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)


class Node(object):
    def __init__(self, data: pd.DataFrame, target_column=0, level: int=0,
                 indices=None, terminal=False, parent=None, which_child=0):

        self._level = level
        self.terminal = terminal

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

        if not level:
            indices = set(range(len(data)))
        else:
            if indices is None:
                raise ValueError("indices=None not allowed for a non-root node (use empty set if necessary)")
            else:
                indices = set(indices)

        self._indices_distributed = set()
        self._indices_remaining = indices

    @staticmethod
    def _validate_data(data, target_column):
        target = data.keys().to_list()[target_column]
        labels = data[target]

        if labels.dtype != int:
            raise TypeError(f"Class labels (column '{target}') must be integers (got {labels.dtype})")

    def __str__(self):
        if self.level:
            attr, th = self.get_creation_stamp()
            root = f'for {th[0]} < {attr} <= {th[1]}'
        else:
            root = 'root'

        leaf = '(leaf)' if self.terminal else f'with {len(self.children)} children'

        split = ""
        if self._split_attribute:
            split = f", split at attribute '{self._split_attribute}' with thresholds: {self._split_thresholds[1:-1]}"

        return f"Level {self.level} tree node ({root}); {'' if self.resolved else 'not '}resolved {leaf}{split}"

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
        return True if (self.terminal or not self._indices_remaining) else False

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
    def target_column(self):
        return self._target

    @property
    def class_labels(self):
        return self.data[self.target_attribute]

    def calculate_entropy(self):
        """Calculate entropy of the node (considering occurrences of each class label)"""

        labels = self.class_labels.to_list()
        occurrences = np.array([labels.count(c) for c in set(labels)])
        probs = occurrences / occurrences.sum()
        entropy = - (probs * np.log2(probs)).sum()
        return entropy

    @property
    def parent(self):
        return self._parent

    @property
    def children(self):
        return self._children

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

        return self._get_child_from_value(observation[self._split_attribute].values.item())

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
        child = self.__class__(self._data, level=self.level+1, indices=indices, parent=self,
                               which_child=len(self.children))
        self._add_child(child)

    def add_final_child(self):
        self.add_new_child(self.indices_remaining)

    def split(self, attribute, thresholds):
        """Split node on a continuous attribute."""

        if attribute == self.target_attribute:
            raise ValueError(f"Cannot split on the target attribute ('{attribute}')")

        if self.resolved:
            logger.warning("Splitting an already resolved node - existing children will be removed")
            self._children = []
            self._indices_remaining = self._indices_distributed.copy()
            self._indices_distributed = set()

        th = sorted(list(thresholds) + [-inf, inf])

        vals = self.data[attribute]

        for i in range(1, len(th)):
            indices = vals.index[(vals > th[i-1]) & (vals <= th[i])]

            if not len(indices):
                logger.warning(f"No observations in value range [{th[i-1]}, {th[i]}) for attribute '{attribute}'")

            self.add_new_child(indices)

        if not self.resolved:
            logger.warning(f"Could not perform full split on attribute {attribute} - possibly missing values")
            self.add_final_child()

        self._split_attribute = attribute
        self._split_thresholds = th