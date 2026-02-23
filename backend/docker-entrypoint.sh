#!/bin/sh
set -e
# Ensure chroma_data is writable by appuser (volume may be root-owned)
if [ -d /app/chroma_data ]; then
  chown -R appuser:appuser /app/chroma_data
fi
exec gosu appuser "$@"
