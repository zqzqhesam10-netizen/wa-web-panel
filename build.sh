
#!/usr/bin/env bash
set -o errexit

# تثبيت المكتبات
pip install -r requirements.txt

# تحميل المتصفح وتثبيت المكتبات المعتمدة للنظام (مهم جداً للينكس على Render)
playwright install chromium
playwright install-deps
