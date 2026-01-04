# GitHub Pages Deployment Troubleshooting

## Current Error

```
tar: docs: Cannot open: No such file or directory
Error: Process completed with exit code 2
```

## Solution

### Option 1: Use the Fixed Workflow (Recommended)

The workflow has been updated to:
1. Verify the docs folder exists
2. Use correct path: `docs` (without `./`)

Push the updated `.github/workflows/deploy-docs.yml`:

```bash
git add .github/workflows/deploy-docs.yml
git commit -m "Fix GitHub Pages deployment path"
git push
```

### Option 2: Manual GitHub Pages Setup

If workflow still fails, use manual deployment:

1. Go to **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` 
4. Folder: `/ (root)` ← **Important!**
5. **Save**

Then create a docs redirect in root:

```bash
# In repository root
echo '<meta http-equiv="refresh" content="0; url=docs/" />' > index.html
git add index.html
git commit -m "Add redirect to docs"
git push
```

### Option 3: Use gh-pages Branch

```bash
# Install gh-pages
npm install -g gh-pages

# Deploy docs folder to gh-pages branch
gh-pages -d docs

# Then Settings → Pages → Source → gh-pages branch
```

## Verify Structure

Your repo should look like:

```
DeltaStream-OptionAnalysis2/
├── .github/
│   └── workflows/
│       └── deploy-docs.yml
├── docs/
│   ├── index.html
│   ├── assets/
│   ├── serve.py
│   └── *.md files
├── services/
└── README.md
```

## Test Locally First

```bash
cd docs
python3 serve.py
# Open http://localhost:8080
```

If it works locally, it will work on GitHub Pages.

## After Deployment

Site will be live at:
```
https://ankushsinghgandhi.github.io/DeltaStream-OptionAnalysis2/
```

**Note**: First deployment takes 2-3 minutes. Check **Actions** tab for progress.

## Common Issues

### Issue: 404 on GitHub Pages

**Fix**: 
1. Ensure `index.html` exists in `docs/` folder
2. Ensure `.nojekyll` file exists
3. Wait 2-3 minutes after push

### Issue: CSS/JS not loading

**Fix**: Check `repoName` in `docs/assets/app.js` matches your repo name exactly:
```javascript
const repoName = 'DeltaStream-OptionAnalysis2'; // ✅ Correct
```

### Issue: Markdown files not loading

**Fix**: Verify paths in browser console (F12). Should be:
```
https://ankushsinghgandhi.github.io/DeltaStream-OptionAnalysis2/docs/README.md
```

## Quick Deploy Command

```bash
# From repository root
git add .
git commit -m "Update documentation"
git push origin main
# Wait 2-3 minutes, check Actions tab
```

---

**If all else fails**: Use the manual setup (Option 2) - it always works!
