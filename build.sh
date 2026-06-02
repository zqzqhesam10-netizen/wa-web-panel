#!/usr/bin/env bash
set -o errexit

# تثبيت المكتبات
pip install -r requirements.txt

# إجبار Playwright على التثبيت في مسار ثابت يمكننا الوصول إليه
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/.playwright
playwright install chromium
