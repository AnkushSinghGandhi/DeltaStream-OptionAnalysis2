// Documentation Site App
// Dynamically loads and renders markdown files

// Configuration - automatically detects deployment environment
const isGitHubPages = window.location.hostname.includes('github.io');
const repoName = 'DeltaStream-OptionAnalysis2'; // Change to your repo name

// Determine base path
// Since index.html is now IN the docs folder, we use current directory
const DOCS_BASE = isGitHubPages
    ? `/${repoName}/docs`  // GitHub Pages: /repo-name/docs
    : '.';                  // Local: current directory (we're already in docs/)

console.log('Documentation base path:', DOCS_BASE);
console.log('Is GitHub Pages:', isGitHubPages);

let allDocs = [];
let currentDoc = null;

// Helper to construct full path
function getDocPath(relativePath) {
    // Remove leading slash if present
    const cleanPath = relativePath.startsWith('/') ? relativePath.slice(1) : relativePath;
    return DOCS_BASE === '.' ? cleanPath : `${DOCS_BASE}/${cleanPath}`;
}

// Document structure (manually defined for now - could be auto-generated)
const docsStructure = {
    'Getting Started': [
        { title: 'README', path: 'README.md' },
        { title: 'Quick Start', path: 'quick-start.md' },
    ],
    'Tutorials': [
        {
            title: 'Complete Guide', path: 'tutorials/complete-guide/README.md', children: [
                { title: 'Chapter 1: Architecture', path: 'tutorials/complete-guide/chapter01.md' },
                { title: 'Chapter 2: Feed Generator', path: 'tutorials/complete-guide/chapter02.md' },
                { title: 'Chapter 3: Worker Enricher', path: 'tutorials/complete-guide/chapter03.md' },
                { title: 'Chapter 4: Storage & Auth', path: 'tutorials/complete-guide/chapter04.md' },
                { title: 'Chapter 5: API Gateway', path: 'tutorials/complete-guide/chapter05.md' },
                { title: 'Chapter 6: WebSocket Gateway', path: 'tutorials/complete-guide/chapter06.md' },
                { title: 'Chapter 7: Analytics', path: 'tutorials/complete-guide/chapter07.md' },
                { title: 'Chapter 8: Testing', path: 'tutorials/complete-guide/chapter08.md' },
                { title: 'Chapter 9: AI Analyst', path: 'tutorials/complete-guide/chapter09.md' },
                { title: 'Chapter 10: Logging', path: 'tutorials/complete-guide/chapter10.md' },
                { title: 'Chapter 11: Kubernetes', path: 'tutorials/complete-guide/chapter11.md' },
                { title: 'Chapter 12: Observability', path: 'tutorials/complete-guide/chapter12.md' },
                { title: 'Chapter 13: Trade Simulator', path: 'tutorials/complete-guide/chapter13.md' },
                { title: 'Appendix A: Makefile', path: 'tutorials/complete-guide/appendix-a.md' },
            ]
        },
        { title: 'Deployment Guide', path: 'deployment/README.md' },
    ],
    'Architecture': [
        { title: 'Overview', path: 'architecture/README.md' },
        { title: 'System Design', path: 'architecture/system-design.md' },
        { title: 'Microservices', path: 'architecture/microservices.md' },
        { title: 'Data Flow', path: 'architecture/data-flow.md' },
        { title: 'Tech Stack', path: 'architecture/tech-stack.md' },
    ],
    'API Reference': [
        { title: 'Overview', path: 'api-reference/README.md' },
        { title: 'Auth Service', path: 'api-reference/auth-service.md' },
        { title: 'Storage Service', path: 'api-reference/storage-service.md' },
        { title: 'WebSocket API', path: 'api-reference/websocket-api.md' },
        { title: 'Analytics Service', path: 'api-reference/analytics-service.md' },
        { title: 'AI Analyst Service', path: 'api-reference/ai-analyst-service.md' },
        { title: 'Trade Simulator', path: 'api-reference/trade-simulator.md' },
    ],
    'Development': [
        { title: 'Setup', path: 'development/setup.md' },
        { title: 'Testing', path: 'development/testing.md' },
        { title: 'Makefile Guide', path: 'development/makefile-guide.md' },
        { title: 'Contributing', path: 'development/contributing.md' },
    ],
    'Interview Prep': [
        { title: 'Overview', path: 'interview-prep/README.md' },
    ],
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    renderNavigation();
    setupSearch();
    loadDefaultDoc();
    setupScrollSpy();
});

// Render Navigation
function renderNavigation() {
    const navTree = document.getElementById('nav-tree');

    Object.entries(docsStructure).forEach(([section, items]) => {
        const sectionDiv = document.createElement('div');
        sectionDiv.className = 'nav-section';

        const sectionTitle = document.createElement('div');
        sectionTitle.className = 'nav-section-title';
        sectionTitle.textContent = section;
        sectionDiv.appendChild(sectionTitle);

        items.forEach(item => {
            const navItem = createNavItem(item);
            sectionDiv.appendChild(navItem);
        });

        navTree.appendChild(sectionDiv);
    });
}

function createNavItem(item, level = 0) {
    const itemDiv = document.createElement('div');

    const link = document.createElement('a');
    link.className = 'nav-item';
    if (item.children) link.classList.add('has-children');
    link.textContent = item.title;
    link.onclick = (e) => {
        e.preventDefault();
        loadDoc(item.path, e);
    };

    itemDiv.appendChild(link);

    if (item.children) {
        const childrenDiv = document.createElement('div');
        childrenDiv.className = 'nav-children';
        item.children.forEach(child => {
            const childItem = createNavItem(child, level + 1);
            childrenDiv.appendChild(childItem);
        });
        itemDiv.appendChild(childrenDiv);
    }

    return itemDiv;
}

// Load Document
async function loadDoc(path, event = null) {
    try {
        const response = await fetch(`${DOCS_BASE}/${path}`);
        if (!response.ok) throw new Error('Document not found');

        const markdown = await response.text();
        renderMarkdown(markdown, path);
        currentDoc = path;

        // Update active nav item
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });

        // Only update active class if called from click event
        if (event && event.target) {
            event.target.classList.add('active');
        } else {
            // Find and activate the nav item matching the current path
            document.querySelectorAll('.nav-item').forEach(item => {
                if (item.onclick && item.onclick.toString().includes(path)) {
                    item.classList.add('active');
                }
            });
        }

        // Scroll to top
        window.scrollTo(0, 0);
    } catch (error) {
        console.error('Failed to load document:', error);
        document.getElementById('content-area').innerHTML = `
      <div class="error">
        <h2>Document Not Found</h2>
        <p>The requested document could not be loaded.</p>
      </div>
    `;
    }
}

function renderMarkdown(markdown, path) {
    // Configure marked
    marked.setOptions({
        highlight: function (code, lang) {
            if (lang && hljs.getLanguage(lang)) {
                return hljs.highlight(code, { language: lang }).value;
            }
            return hljs.highlightAuto(code).value;
        },
        breaks: true,
        gfm: true,
    });

    const html = marked.parse(markdown);
    const contentArea = document.getElementById('content-area');
    contentArea.innerHTML = html;

    // Generate TOC
    generateTOC(contentArea);

    // Add copy buttons to code blocks
    addCopyButtons();

    // Fix relative links
    fixRelativeLinks(path);
}

function generateTOC(contentArea) {
    const headings = contentArea.querySelectorAll('h2, h3, h4');
    const tocContent = document.getElementById('toc-content');
    tocContent.innerHTML = '';

    headings.forEach((heading, index) => {
        const id = `heading-${index}`;
        heading.id = id;

        const link = document.createElement('a');
        link.href = `#${id}`;
        link.className = `toc-item toc-${heading.tagName.toLowerCase()}`;
        link.textContent = heading.textContent;
        link.onclick = (e) => {
            e.preventDefault();
            heading.scrollIntoView({ behavior: 'smooth' });
        };

        tocContent.appendChild(link);
    });
}

function addCopyButtons() {
    document.querySelectorAll('pre code').forEach(codeBlock => {
        const pre = codeBlock.parentElement;
        const button = document.createElement('button');
        button.className = 'copy-btn';
        button.textContent = 'Copy';
        button.style.cssText = `
      position: absolute;
      top: 0.5rem;
      right: 0.5rem;
      padding: 0.25rem 0.75rem;
      background: var(--bg-tertiary);
      border: 1px solid var(--border-color);
      border-radius: 4px;
      color: var(--text-secondary);
      font-size: 0.75rem;
      cursor: pointer;
      transition: all 0.2s;
    `;

        pre.style.position = 'relative';
        pre.appendChild(button);

        button.onclick = () => {
            navigator.clipboard.writeText(codeBlock.textContent);
            button.textContent = 'Copied!';
            setTimeout(() => button.textContent = 'Copy', 2000);
        };
    });
}

function fixRelativeLinks(currentPath) {
    const basePath = currentPath.split('/').slice(0, -1).join('/');

    document.querySelectorAll('#content-area a').forEach(link => {
        const href = link.getAttribute('href');
        if (href && href.endsWith('.md')) {
            link.onclick = (e) => {
                e.preventDefault();
                const fullPath = href.startsWith('/') ? href.slice(1) : `${basePath}/${href}`;
                loadDoc(fullPath, e);
            };
        }
    });
}

// Search
function setupSearch() {
    const searchInput = document.getElementById('search-input');
    const modal = document.getElementById('search-modal');
    const closeBtn = document.getElementById('close-search');

    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            const query = e.target.value.trim();
            if (query.length > 2) {
                performSearch(query);
                modal.classList.remove('hidden');
            } else {
                modal.classList.add('hidden');
            }
        }, 300);
    });

    closeBtn.addEventListener('click', () => {
        modal.classList.add('hidden');
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.add('hidden');
        }
    });
}

async function performSearch(query) {
    const results = [];
    const lowerQuery = query.toLowerCase();

    // Search through all docs
    for (const [section, items] of Object.entries(docsStructure)) {
        for (const item of items) {
            await searchInDoc(item, lowerQuery, section, results);
        }
    }

    displaySearchResults(results, query);
}

async function searchInDoc(item, query, section, results) {
    try {
        const response = await fetch(`${DOCS_BASE}/${item.path}`);
        const content = await response.text();
        const lowerContent = content.toLowerCase();

        if (lowerContent.includes(query)) {
            const index = lowerContent.indexOf(query);
            const snippet = content.substring(Math.max(0, index - 100), index + 100);

            results.push({
                title: item.title,
                path: item.path,
                section: section,
                snippet: snippet,
            });
        }

        // Search in children
        if (item.children) {
            for (const child of item.children) {
                await searchInDoc(child, query, section, results);
            }
        }
    } catch (error) {
        console.error(`Failed to search ${item.path}:`, error);
    }
}

function displaySearchResults(results, query) {
    const container = document.getElementById('search-results');

    if (results.length === 0) {
        container.innerHTML = '<p style="padding: 2rem; text-align: center; color: var(--text-muted);">No results found</p>';
        return;
    }

    container.innerHTML = results.map(result => `
    <div class="search-result" onclick="loadDoc('${result.path}'); document.getElementById('search-modal').classList.add('hidden');">
      <div class="search-result-title">${result.title}</div>
      <div class="search-result-path">${result.section} / ${result.path}</div>
      <div class="search-result-snippet">${highlightQuery(result.snippet, query)}</div>
    </div>
  `).join('');
}

function highlightQuery(text, query) {
    const regex = new RegExp(query, 'gi');
    return text.replace(regex, match => `<mark>${match}</mark>`);
}

// Scroll Spy
function setupScrollSpy() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const id = entry.target.id;
                document.querySelectorAll('.toc-item').forEach(item => {
                    item.classList.remove('active');
                    if (item.getAttribute('href') === `#${id}`) {
                        item.classList.add('active');
                    }
                });
            }
        });
    }, { threshold: 0.5 });

    // Observe headings (after they're added)
    setInterval(() => {
        document.querySelectorAll('#content-area h2, #content-area h3').forEach(heading => {
            observer.observe(heading);
        });
    }, 1000);
}

// Load default document
function loadDefaultDoc() {
    loadDoc('README.md');
}
