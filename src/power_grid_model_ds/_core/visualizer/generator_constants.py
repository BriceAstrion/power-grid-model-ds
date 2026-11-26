# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Constants for generator presentation symbols."""

GENERATOR_GROUPS = frozenset({"sym_gen", "asym_gen"})

GENERATOR_SYMBOL_GROUP = "generator_symbol"
GENERATOR_SYMBOL_CLASS = "generator-symbol"
GENERATOR_ORIGINAL_HIDDEN_CLASS = "generator-original-hidden"

GENERATOR_CONNECTION_CLASS = "generator-visual-connection"
GENERATOR_OPEN_CLASS = "generator-visual-open"

GENERATOR_VISUAL_PREFIX = "__visual_generator__"
GENERATOR_SYMBOL_SUFFIX = "__symbol"
GENERATOR_CONNECTION_SUFFIX = "__connection"

GENERATOR_SYMBOL_SIZE = 80
GENERATOR_CONNECTION_LENGTH = 100
