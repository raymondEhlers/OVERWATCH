#!/usr/bin/env bash

# Setup serverParams.py
sed -e 's/defaultUsername = ""/defaultUsername = "user"/g' ../../config/serverParams.py > serverParams.py
