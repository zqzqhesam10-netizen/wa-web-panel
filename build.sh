#!/usr/bin/env bash
set -o errexit

# 1. تثبيت المكتبات (بدون sudo)
pip install -r requirements.txt

# 2. تحميل المتصفح فقط (هذا لا يحتاج لصلاحيات root ويعمل في مجلد المستخدم)
playwright install chromium
