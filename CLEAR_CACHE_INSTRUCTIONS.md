# How to Clear Cache in Google Chrome

## Quick Method (Hard Refresh)
1. Open Chrome and go to `http://0.0.0.0:8000/admin/`
2. Press **Ctrl+Shift+R** (Windows/Linux) or **Cmd+Shift+R** (Mac)
   - This does a hard refresh and clears the page cache

## Full Cache Clear
1. Open Chrome
2. Press **Ctrl+Shift+Delete** (Windows/Linux) or **Cmd+Shift+Delete** (Mac)
3. In the dialog that appears:
   - Select "All time" from the time range dropdown
   - Check these boxes:
     - ✅ Cookies and other site data
     - ✅ Cached images and files
   - Click "Clear data"

## Alternative: Clear for Specific Site
1. Go to `http://0.0.0.0:8000/admin/`
2. Click the **lock icon** (or info icon) in the address bar
3. Click "Site settings"
4. Click "Clear data"
5. Check both options and click "Clear"

## Developer Mode Method
1. Open Chrome DevTools (F12 or Right-click → Inspect)
2. Right-click the refresh button (while DevTools is open)
3. Select "Empty Cache and Hard Reload"

---

## Also Clear Django Server Cache

If you're still seeing the error, also clear Django's cache:

```bash
# Stop your Django server (Ctrl+C)

# Clear Python cache files
find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null
find . -name "*.pyc" -delete

# Restart server
python manage.py runserver 0.0.0.0:8000
```

---

## Verify Changes Are Loaded

After clearing cache, you should see:
- No AttributeError when logging in
- Groups working properly
- Users can see only their group permissions

