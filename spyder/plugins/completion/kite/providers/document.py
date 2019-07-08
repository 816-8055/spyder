# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite document requests handlers and senders."""

import os.path as osp

from qtpy.QtCore import QMutexLocker
from spyder.plugins.completion.kite.decorators import send_request, handles
from spyder.plugins.completion.languageserver import (
    LSPRequestTypes, CompletionItemKind)


KITE_DOCUMENT_TYPES = {
    'function': CompletionItemKind.FUNCTION,
    'module': CompletionItemKind.MODULE,
    'type': CompletionItemKind.CLASS,
    'instance': CompletionItemKind.VARIABLE,
    'descriptor': CompletionItemKind.FILE,
    'union': CompletionItemKind.VALUE,
    'global': CompletionItemKind.PROPERTY,
    'unknown': CompletionItemKind.TEXT
}


class DocumentProvider:
    @send_request(method=LSPRequestTypes.DOCUMENT_DID_OPEN)
    def document_did_open(self, params):
        request = {
            'source': 'spyder',
            'filename': osp.realpath(params['file']),
            'text': params['text'],
            'action': 'focus',
            'selections': []
        }

        default_info = {'text': '', 'count': 0}
        with QMutexLocker(self.mutex):
            file_info = self.opened_files.get(params['file'], default_info)
            file_info['count'] += 1
            file_info['text'] = params['text']
            self.opened_files[params['file']] = file_info
        return request

    @send_request(method=LSPRequestTypes.DOCUMENT_DID_CHANGE)
    def document_did_change(self, params):
        request = {
            'source': 'spyder',
            'filename': osp.realpath(params['file']),
            'text': params['text'],
            'action': 'edit',
            'selections': []
        }
        with QMutexLocker(self.mutex):
            file_info = self.opened_files[params['file']]
            file_info['text'] = params['text']
        return request

    @send_request(method=LSPRequestTypes.DOCUMENT_COMPLETION)
    def request_document_completions(self, params):
        text = self.opened_files[params['file']]['text']
        request = {
            'filename': osp.realpath(params['file']),
            'editor': 'spyder',
            'text': text,
            'position': {
                'begin': params['offset']
            },
            'placeholders': []
        }
        return request

    @handles(LSPRequestTypes.DOCUMENT_COMPLETION)
    def convert_completion_request(self, response):
        spyder_completions = []
        completions = response['completions']
        if completions is not None:
            for completion in completions:
                entry = {
                    'kind': KITE_DOCUMENT_TYPES.get(
                        completion['hint'], CompletionItemKind.TEXT),
                    'insertText': completion['snippet']['text'],
                    'filterText': completion['display'],
                    'sortText': completion['display'][0],
                    'documentation': completion['documentation']['text']
                }
                spyder_completions.append(entry)
        print(spyder_completions)
        return {'params': spyder_completions}
