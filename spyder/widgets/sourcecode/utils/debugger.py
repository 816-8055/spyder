# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Contains the text debugger manager.
"""
import os.path as osp

from qtpy.QtWidgets import QInputDialog, QLineEdit

from spyder.config.main import CONF
from spyder.config.base import _
from spyder.py3compat import to_text_string
from spyder.api.manager import Manager
from spyder.widgets.sourcecode.utils.editor import BlockUserData


def _load_all_breakpoints():
    bp_dict = CONF.get('run', 'breakpoints', {})
    for filename in list(bp_dict.keys()):
        if not osp.isfile(filename):
            bp_dict.pop(filename)
    return bp_dict


def load_breakpoints(filename):
    breakpoints = _load_all_breakpoints().get(filename, [])
    if breakpoints and isinstance(breakpoints[0], int):
        # Old breakpoints format
        breakpoints = [(lineno, None) for lineno in breakpoints]
    return breakpoints


def save_breakpoints(filename, breakpoints):
    if not osp.isfile(filename):
        return
    bp_dict = _load_all_breakpoints()
    bp_dict[filename] = breakpoints
    CONF.set('run', 'breakpoints', bp_dict)


def clear_all_breakpoints():
    CONF.set('run', 'breakpoints', {})


def clear_breakpoint(filename, lineno):
    breakpoints = load_breakpoints(filename)
    if breakpoints:
        for breakpoint in breakpoints[:]:
            if breakpoint[0] == lineno:
                breakpoints.remove(breakpoint)
        save_breakpoints(filename, breakpoints)


class DebuggerManager(Manager):
    """
    Manages adding/removing breakpoint from the editor.
    """
    def __init__(self, editor):
        super(DebuggerManager, self).__init__(editor)
        self.breakpoints = self.get_breakpoints()
        self.editor.sig_breakpoints_changed.connect(self.breakpoints_changed)

    def toogle_breakpoint(self, line_number=None, condition=None,
                          edit_condition=False):
        """Add/remove breakpoint."""
        if not self.editor.is_python_like():
            return
        if line_number is None:
            block = self.editor.textCursor().block()
        else:
            block = self.editor.document().findBlockByNumber(line_number-1)
        data = block.userData()
        if not data:
            data = BlockUserData(self.editor)
            data.breakpoint = True
        elif not edit_condition:
            data.breakpoint = not data.breakpoint
            data.breakpoint_condition = None
        if condition is not None:
            data.breakpoint_condition = condition
        if edit_condition:
            condition = data.breakpoint_condition
            condition, valid = QInputDialog.getText(self,
                                        _('Breakpoint'),
                                        _("Condition:"),
                                        QLineEdit.Normal, condition)
            if not valid:
                return
            data.breakpoint = True
            data.breakpoint_condition = str(condition) if condition else None
        if data.breakpoint:
            text = to_text_string(block.text()).strip()
            if len(text) == 0 or text.startswith(('#', '"', "'")):
                data.breakpoint = False
        block.setUserData(data)
        self.editor.sig_flags_changed.emit()
        self.editor.sig_breakpoints_changed.emit()

    def get_breakpoints(self):
        """Get breakpoints"""
        breakpoints = []
        block = self.editor.document().firstBlock()
        for line_number in range(1, self.editor.document().blockCount()+1):
            data = block.userData()
            if data and data.breakpoint:
                breakpoints.append((line_number, data.breakpoint_condition))
            block = block.next()
        return breakpoints

    def clear_breakpoints(self):
        """Clear breakpoints"""
        self.breakpoints = []
        for data in self.editor.blockuserdata_list[:]:
            data.breakpoint = False
            # data.breakpoint_condition = None  # not necessary, but logical
            if data.is_empty():
                # This is not calling the __del__ in BlockUserData.  Not
                # sure if it's supposed to or not, but that seems to be the
                # intent.
                del data

    def set_breakpoints(self, breakpoints):
        """Set breakpoints"""
        self.clear_breakpoints()
        for line_number, condition in breakpoints:
            self.toogle_breakpoint(line_number, condition)

    def update_breakpoints(self):
        """Update breakpoints"""
        self.editor.sig_breakpoints_changed.emit()

    def breakpoints_changed(self):
        """Breakpoint list has changed"""
        breakpoints = self.get_breakpoints()
        if self.breakpoints != breakpoints:
            self.breakpoints = breakpoints
            self.save_breakpoints(self.filename, repr(breakpoints))

    def save_breakpoints(self, filename, breakpoints):
        filename = to_text_string(filename)
        breakpoints = to_text_string(breakpoints)
        filename = osp.normpath(osp.abspath(filename))
        if breakpoints:
            breakpoints = eval(breakpoints)
        else:
            breakpoints = []
        save_breakpoints(filename, breakpoints)
        self.editor.sig_breakpoints_saved.emit()

    def load_breakpoints(self, filename):
        self.set_breakpoints(load_breakpoints(filename))
