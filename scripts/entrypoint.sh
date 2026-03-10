#!/bin/bash
set -e
# Apply runtime Sybase/ODBC config from mounted volume when present (real configs).
# When configs are placeholder/empty, base image defaults are used.
SYBASE_CFG="/app/configs/sybase_config"
if [ -d "$SYBASE_CFG" ]; then
  if [ -s "$SYBASE_CFG/odbc.ini" ]; then
    cp "$SYBASE_CFG/odbc.ini" /etc/odbc.ini
    sed -i 's/\r$//' /etc/odbc.ini
  fi
  if [ -s "$SYBASE_CFG/interfaces" ]; then
    cp "$SYBASE_CFG/interfaces" /opt/sybase16/interfaces
    sed -i 's/\r$//' /opt/sybase16/interfaces
  fi
  if [ -s "$SYBASE_CFG/odbcinst.ini" ]; then
    cp "$SYBASE_CFG/odbcinst.ini" /etc/odbcinst.ini
    sed -i 's/\r$//' /etc/odbcinst.ini
  fi
fi
exec "$@"
