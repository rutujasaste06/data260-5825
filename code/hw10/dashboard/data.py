"""Shared loaders for the HW10 dashboard. Everything is read from reports/hw10/raw/ (our own logs)."""

import json
import os
import sys
from datetime import datetime

import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ("..", os.path.join("..", "..", "pipeline")):
    sys.path.insert(0, os.path.abspath(os.path.join(HERE, sub)))

from tracing import load_spans, raw_dir  # noqa: E402


def _mtime(name):
    try:
        return os.path.getmtime(os.path.join(raw_dir(), name))
    except OSError:
        return 0


@st.cache_data(ttl=30)
def spans(mtime_key):
    """All spans (cache key = file modification time, so new data shows up after a refresh)."""
    return load_spans()


@st.cache_data(ttl=30)
def jsonl(name, mtime_key):
    path = os.path.join(raw_dir(), name)
    rows = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    return rows


@st.cache_data(ttl=30)
def json_file(name, mtime_key):
    path = os.path.join(raw_dir(), name)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def get_spans():
    return spans(_mtime("spans.jsonl"))


def get_jsonl(name):
    return jsonl(name, _mtime(name))


def get_json(name):
    return json_file(name, _mtime(name))


def fmt_time(epoch):
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
