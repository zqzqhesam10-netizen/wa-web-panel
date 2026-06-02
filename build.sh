#!/usr/bin/env bash
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/.playwright
pip install -r requirements.txt
playwright install chromium
