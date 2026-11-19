# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Shared identifiers and dimensions for load presentation symbols."""

LOAD_GROUPS = frozenset({"sym_load", "asym_load"})

LOAD_SYMBOL_GROUP = "load_symbol"
LOAD_SYMBOL_CLASS = "load-symbol"
LOAD_ORIGINAL_HIDDEN_CLASS = "load-original-hidden"
LOAD_CONNECTION_CLASS = "load-visual-connection"
LOAD_OPEN_CLASS = "load-visual-open"

LOAD_VISUAL_PREFIX = "__visual_load__"
LOAD_SYMBOL_SUFFIX = "__symbol"
LOAD_CONNECTION_SUFFIX = "__connection"

LOAD_SYMBOL_WIDTH = 100
LOAD_SYMBOL_HEIGHT = 60
LOAD_CONNECTION_LENGTH = 90

VISUAL_ONLY_KEY = "visual_only"
