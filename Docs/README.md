# DeltaStream Documentation

**Comprehensive documentation for the DeltaStream Options Trading Platform**

## 📚 Browse Documentation

**Live Site**: [View Documentation](https://yourusername.github.io/option-aro-clone/)

Or run locally:
```bash
cd docs
python3 serve.py
# Open http://localhost:8080
```

## 📖 What's Inside

### Getting Started
- [README](README.md) - Project overview
- [Quick Start](quick-start.md) - Get up and running fast

### Tutorials
- [Complete Guide](tutorials/complete-guide/) Complete 13-chapter tutorial
- [Deployment Guide](deployment/) - Deploy to production

### Architecture
- [System Design](architecture/system-design.md) - HLD/LLD diagrams
- [Microservices](architecture/microservices.md) - Service details
- [Data Flow](architecture/data-flow.md) - Request flow & caching
- [Tech Stack](architecture/tech-stack.md) - Technologies used

### API Reference
- [Auth Service](api-reference/auth-service.md) - Authentication
- [Storage Service](api-reference/storage-service.md) - Data persistence
- [WebSocket API](api-reference/websocket-api.md) - Real-time data
- [Analytics Service](api-reference/analytics-service.md) - PCR, IV surface
- [AI Analyst](api-reference/ai-analyst-service.md) - LLM integration
- [Trade Simulator](api-reference/trade-simulator.md) - Paper trading

### Development
- [Setup](development/setup.md) - Local development
- [Testing](development/testing.md) - Testing guide
- [Makefile Guide](development/makefile-guide.md) - Build automation
- [Contributing](development/contributing.md) - Contribution guide

### Interview Prep
- [Overview](interview-prep/README.md) - System design prep

## 🚀 Deployment

This documentation site is GitHub Pages ready!

### Quick Deploy

1. **Enable GitHub Pages**
   - Go to Settings → Pages
   - Source: **GitHub Actions**

2. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Add documentation"
   git push origin main
   ```

3. **Done!** Site will be live at:
   ```
   https://yourusername.github.io/option-aro-clone/
   ```

See [DEPLOYMENT.md](DEPLOYMENT.md) for details.

## 🔧 Local Development

### Serve Locally

```bash
cd docs
python3 serve.py
```

Or:
```bash
python3 -m http.server 8080
```

Then open: http://localhost:8080

### Features

✅ **Markdown Rendering** - All docs in markdown  
✅ **Syntax Highlighting** - Code blocks with language support  
✅ **Full-Text Search** - Search across all documentation  
✅ **Table of Contents** - Auto-generated from headings  
✅ **Dark Theme** - Professional GitHub-dark theme  
✅ **Responsive** - Works on desktop, tablet, mobile  

## 📝 Structure

```
docs/
├── index.html              # Documentation site
├── assets/
│   ├── style.css          # Styles
│   └── app.js             # JavaScript
├── serve.py               # Local server
├── .nojekyll              # GitHub Pages config
│
├── README.md              # This file
├── quick-start.md         # Quick start guide
│
├── tutorials/             # Step-by-step guides
│   └── complete-guide/    # 13 chapters
│
├── architecture/          # System design docs
├── api-reference/         # API documentation
├── development/           # Dev guides
├── deployment/            # Deployment guides
└── interview-prep/        # Interview preparation
```

## 🎨 Customization

### Update Repo Name

Edit `assets/app.js`:
```javascript
const repoName = 'your-repo-name'; // Line 6
```

### Change Theme

Edit `assets/style.css`:
```css
:root {
  --primary-color: #4dabf7;  /* Main accent */
  --bg-primary: #0d1117;     /* Background */
}
```

## 📊 Statistics

- **Total Documentation**: 50+ markdown files
- **Tutorial Chapters**: 13 complete chapters
- **API Services**: 7 services documented
- **Code Examples**: 400+ code blocks
- **Lines of Content**: 10,000+ lines

## 🤝 Contributing

See [Contributing Guide](development/contributing.md)

## 📄 License

Part of DeltaStream Options Trading Platform

---

**Ready to explore?** Start with the [Quick Start Guide](quick-start.md)!
