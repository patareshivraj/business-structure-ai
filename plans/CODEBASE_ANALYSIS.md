# Business Structure Intelligence - Technical Evaluation

## 1️⃣ System Overview

### What Problem Does This System Solve?
This system is a **Business Structure Intelligence Platform** that researches companies and visualizes their organizational hierarchy as an interactive tree diagram. It aggregates data from multiple sources (web search, Wikipedia, financial websites, annual reports) and uses AI to extract and structure business segments, products, services, and subsidiaries.

### Core Functionality
- **Company Research**: Automated data collection from Tavily search, Wikipedia, MoneyControl, NSE India, and PDF annual reports
- **AI-Powered Structure Extraction**: Uses Groq LLM (Llama 3.1) to parse research data into hierarchical business structure
- **Interactive Visualization**: React-based org chart with collapsible nodes, dark/light themes, and animated edges
- **Caching**: In-memory cache to avoid redundant API calls

### Tech Stack Used

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, ReactFlow, Dagre (layout), CSS-in-JS |
| **Backend** | FastAPI, Python |
| **AI/ML** | Groq (Llama 3.1), Tavily Search API |
| **Data Processing** | BeautifulSoup4, PyPDF, newspaper3k |
| **Workflow** | LangGraph (stateful pipeline) |
| **APIs** | REST (FastAPI) |

### High-Level Architecture Style
**Pipeline Architecture with Agent Pattern**

```
┌─────────────┐    ┌──────────────┐    ┌────────────────┐
│   Frontend  │───▶│   FastAPI    │───▶│  LangGraph     │
│  (React)    │◀───│   Backend    │◀───│  Workflow      │
└─────────────┘    └──────────────┘    └────────────────┘
                                               │
                    ┌───────────────────────────┼───────────────────────────┐
                    ▼                           ▼                           ▼
            ┌──────────────┐           ┌──────────────┐           ┌──────────────┐
            │  Research    │           │  Structure   │           │ Intelligence │
            │  Agent       │           │  Agent       │           │  Agent       │
            └──────────────┘           └──────────────┘           └──────────────┘
                    │                           │                           
                    ▼                           ▼                           
            ┌──────────────────────────────────────────────────────────────┐
            │  Data Sources: Tavily, Wikipedia, MoneyControl, NSE, PDF   │
            └──────────────────────────────────────────────────────────────┘
```

---

## 2️⃣ Code Structure Analysis

### Folder/Module Breakdown

```
backend/
├── api.py                 # FastAPI endpoints (single route)
├── workflow.py           # LangGraph state machine definition
├── requirements.txt      # Python dependencies
├── .env                  # API keys (⚠️ security issue)
├── agents/
│   ├── research_agent.py     # Data collection (242 lines)
│   ├── structure_agent.py   # AI extraction (215 lines)
│   ├── intelligence_agent.py # Insight generation (87 lines)
│   ├── news_agent.py         # News fetching (27 lines)
│   ├── pdf_agent.py          # PDF text extraction (60 lines)
│   ├── wiki_agent.py         # Wikipedia API (20 lines)
│   └── web_scraper.py        # Generic scraper (22 lines)
└── utils/
    └── cache.py              # In-memory dict (9 lines)

frontend/
├── src/
│   ├── App.js            # Main React component (437 lines)
│   ├── App.css           # Unused default styles
│   ├── index.js          # React entry point
│   └── index.css         # Global styles
└── package.json
```

### Data Flow Explanation

1. **User Input**: Frontend sends company name via `GET /company/{name}`
2. **Cache Check**: Backend checks in-memory cache first
3. **Research Phase**: `research_node` calls `research_company()` which:
   - Queries Tavily for 6 results
   - Scrapes Wikipedia, MoneyControl, NSE India
   - Finds and extracts annual report PDF
4. **Extraction Phase**: `extract_node` calls `extract_structure()` which:
   - Sends research data to Groq LLM
   - Validates against source text (hallucination filter)
   - Normalizes tree structure
5. **Response**: Tree JSON returned to frontend
6. **Visualization**: ReactFlow renders interactive org chart

### Separation of Concerns

| Component | Responsibility |
|-----------|-----------------|
| `api.py` | HTTP routing, CORS, cache orchestration |
| `workflow.py` | LangGraph state management, node definitions |
| `research_agent.py` | Multi-source data aggregation |
| `structure_agent.py` | LLM prompting, JSON parsing, validation |
| `intelligence_agent.py` | Business insight generation |
| `cache.py` | Simple key-value storage |

**Assessment**: Good separation at agent level, but workflow is minimal (only 2 nodes).

### Dependency Handling

- **Environment**: Uses `python-dotenv` for API keys
- **No dependency injection**: Direct imports between modules
- **API clients**: Singleton clients initialized at module level
- **Circular risk**: None detected

### Code Organization Quality

**Strengths:**
- Agent-based modular design
- Clear function naming conventions
- Reasonable file sizes (except App.js at 437 lines)

**Weaknesses:**
- Mixed concerns in `App.js` (UI, layout, state, CSS injection)
- No service layer in frontend (direct API calls in component)
- Cache is process-local (not shared across workers)

---

## 3️⃣ Strengths

### Clean Implementations
- ✅ **LangGraph Workflow**: Well-structured state graph with clear node definitions
- ✅ **PDF Validation**: Robust `is_valid_pdf()` checking both Content-Type and magic bytes (`%PDF`)
- ✅ **Error Handling**: Most functions have try/except with fallback returns
- ✅ **Hallucination Filter**: `validate_items()` cross-references AI output with source text
- ✅ **Graceful Degradation**: Fallback structure when AI fails

### Good Patterns Used
- ✅ **Agent Pattern**: Distinct agents for research, extraction, intelligence
- ✅ **Factory Pattern**: Multiple model fallback in `structure_agent.py`
- ✅ **Debouncing**: Frontend search has 400ms debounce
- ✅ **Memoization**: `useCallback` for `rebuildGraph`
- ✅ **CSS Injection**: Dynamic CSS for Marching Ants animation

### Scalable Design Decisions
- ✅ **API Client Abstraction**: Easy to swap Tavily/Groq providers
- ✅ **Configurable Models**: Model list allows fallback
- ✅ **Extensible Agents**: New agents can be added easily

### Maintainability Positives
- ✅ **Type Hints**: `TypedDict` in workflow.py
- ✅ **Console Logging**: Clear emoji-prefixed log messages
- ✅ **Constants**: Color palette, node dimensions centralized
- ✅ **Component Extraction**: `OrgNode`, `AnimatedEdge`, `DynamicLegend` as separate functions

---

## 4️⃣ ⚠️ Red Flags

### 🔴 Critical Issues

1. **API Keys Exposed in Version Control**
   - [`backend/.env`](backend/.env:1) contains `TAVILY_API_KEY` and `GROQ_API_KEY`
   - These are committed to the repository
   - **Fix**: Add `.env` to `.gitignore` immediately

2. **CORS Allows All Origins**
   - [`api.py:10`](backend/api.py:10) sets `allow_origins=["*"]`
   - Any website can make requests to this API
   - **Fix**: Restrict to frontend domain in production

3. **No Input Validation/Sanitization**
   - Company name passed directly to external APIs and LLM prompts
   - Potential for prompt injection
   - **Fix**: Add input length limits and sanitization

4. **Process-Local Cache**
   - [`cache.py:3`](backend/utils/cache.py:3) uses module-level `CACHE = {}`
   - Won't work with multiple uvicorn workers
   - **Fix**: Use Redis or database-backed cache

### 🟠 Major Issues

5. **Unused CSS File**
   - [`App.css`](frontend/src/App.css) contains unused CRA boilerplate
   - App.js uses inline styles and injected CSS instead

6. **Frontend/Backend API Mismatch**
   - Frontend calls `http://127.0.0.1:8000/company/{q}/intelligence` ([`App.js:249`](frontend/src/App.js:249))
   - Backend only defines `/company/{name}` ([`api.py:16`](backend/api.py:16))
   - **The API will return 404!**

7. **No Rate Limiting**
   - Tavily and Groq APIs have rate limits
   - No protection against abuse

8. **No Request Timeout Handling**
   - External API calls don't have proper timeout handling in frontend
   - User sees generic "Backend error" message

9. **India-Specific Focus**
   - MoneyControl and NSE scrapers hardcoded for Indian market
   - Limited global applicability

10. **PDF Extraction Limited**
    - [`pdf_agent.py:45`](backend/agents/pdf_agent.py:45) only extracts first 20 pages
    - Annual reports can be 200+ pages

### 🟡 Minor Issues

11. **Inconsistent Exception Handling**
    - Some places use bare `except:` (lines 78, 104, 124)
    - Should specify exception types

12. **Magic Numbers**
    - `max_results=6`, `max_results=5`, `[:10]`, `[:20]` scattered throughout
    - Should be constants

13. **Duplicate Code**
    - `wiki_company()` in `wiki_agent.py` duplicates logic in `research_agent.py`

14. **No TypeScript**
    - Frontend has no type safety
    - `data.structure` accessed without validation

15. **Hardcoded API Endpoints**
    - Frontend has `http://127.0.0.1:8000` hardcoded
    - Should use environment variable

---

## 5️⃣ Key Findings & Insights

### Architectural Insights

| Finding | Impact |
|---------|--------|
| **Simple 2-Node Pipeline** | The workflow is very linear; could benefit from parallel agent execution |
| **Single API Route** | Backend is essentially a monolith endpoint; limited scalability |
| **No Database** | All data is ephemeral; cache lost on restart |
| **India Focus** | System designed for Indian market (NSE, MoneyControl) |

### Hidden Risks

1. **LLM Hallucination**: Despite validation, the AI can still produce incorrect structures
2. **Scraping Fragility**: External website scrapers (MoneyControl, NSE) will break when websites change
3. **API Key Exhaustion**: Free tier APIs have limits; no budget monitoring
4. **Memory Growth**: Indefinite cache growth with no TTL or eviction policy

### Technical Debt Indicators

- ❌ No tests
- ❌ No error monitoring (Sentry, etc.)
- ❌ No API documentation (Swagger not enabled)
- ❌ No CI/CD pipeline visible
- ❌ Hardcoded credentials

### Design Pattern Correctness

| Pattern | Implementation | Assessment |
|---------|----------------|------------|
| State Machine | LangGraph | ✅ Good |
| Agent | Separate agent modules | ✅ Good |
| Factory | Model fallback list | ✅ Good |
| Cache-Aside | Check cache before research | ⚠️ Incomplete (single-instance) |
| Strategy | Multiple scrapers | ✅ Good |

### Code Smell Observations

- **God Component**: `App.js` at 437 lines handles UI, state, layout, CSS, theme
- **Feature Envy**: `research_company()` does too much (7 different data sources)
- ** shotgun surgery**: Color/theme changes require editing multiple places
- **Primitive Obsession**: Using dicts instead of typed data classes

---

## 6️⃣ Improvement Areas

### Code-Level Improvements

1. **Split App.js**
   ```python
   # Suggested structure:
   # components/
   #   ├── Header.js
   #   ├── SearchBar.js
   #   ├── OrgChart.js
   #   ├── OrgNode.js
   #   └── Legend.js
   # hooks/
   #   ├── useCompanySearch.js
   #   └── useTheme.js
   ```

2. **Add Input Validation**
   ```python
   # backend/api.py
   @app.get("/company/{name}")
   def get_company(name: str):
       if not name or len(name) < 2 or len(name) > 100:
           raise HTTPException(400, "Invalid company name")
       # sanitization...
   ```

3. **Create Typed Data Classes**
   ```python
   # backend/models.py
   from pydantic import BaseModel
   
   class CompanyStructure(BaseModel):
       name: str
       children: List["CompanyStructure"] = []
   ```

4. **Extract Constants**
   ```python
   # backend/config.py
   MAX_SEARCH_RESULTS = 6
   MAX_PDF_PAGES = 20
   MAX_RESEARCH_TEXT = 10000
   ```

### Structural Refactoring Suggestions

1. **Add Database Layer**
   - Store company research results persistently
   - Enable historical lookups
   - Consider PostgreSQL or MongoDB

2. **Enable Swagger**
   ```python
   # backend/api.py
   app = FastAPI()
   app.include_router(app, docs_url="/docs")
   ```

3. **Add Health Check Endpoint**
   ```python
   @app.get("/health")
   def health():
       return {"status": "ok", "cache_size": len(CACHE)}
   ```

### Testing Improvements

1. **Add Unit Tests**
   - Test `clean_text()` edge cases
   - Test `validate_items()` hallucination filter
   - Test JSON extraction regex

2. **Add Integration Tests**
   - Test API endpoint with mock agents
   - Test workflow state transitions

3. **Add E2E Tests**
   - Test full flow: search → API → render

### Error Handling Improvements

1. **Add Structured Error Responses**
   ```python
   class ErrorResponse(BaseModel):
       error: str
       code: str
       details: Optional[dict]
   ```

2. **Add Frontend Error Boundaries**
   ```javascript
   // React error boundary for graceful degradation
   ```

### Documentation Gaps

1. **API Documentation**: No Swagger/OpenAPI docs
2. **Architecture Docs**: No ADR or architecture decision records
3. **README**: Frontend has one, backend doesn't
4. **Agent Contracts**: No clear interfaces between agents

---

## 7️⃣ Enhancement Opportunities

### Performance Optimization

| Area | Current | Improvement |
|------|---------|-------------|
| **PDF Extraction** | Sequential pages | Parallel page extraction with ThreadPoolExecutor |
| **Research** | Sequential scraping | Async/await with aiohttp |
| **LLM Calls** | Single call | Batch related queries |
| **Frontend** | No memoization | Memoize layout calculations |
| **Cache** | Dict | Redis with TTL |

### Scalability Improvements

1. **Add Worker Queue**
   - Celery or Redis Queue for background processing
   - WebSocket for progress updates

2. **Multi-Instance Cache**
   - Redis instead of in-memory dict
   - Cache invalidation strategy

3. **Rate Limiting**
   - Implement per-user/request limits
   - Add API key-based quotas

### Security Hardening

1. **Environment Variables**
   ```
   # .env should NOT be in git
   TAVILY_API_KEY=
   GROQ_API_KEY=
   FRONTEND_URL=http://localhost:3000
   ```

2. **CORS Configuration**
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[os.getenv("FRONTEND_URL")],
       allow_credentials=True,
   )
   ```

3. **Add Authentication**
   - API key or JWT for production

### Observability & Logging

1. **Structured Logging**
   ```python
   import logging
   logging.basicConfig(
       format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
   )
   ```

2. **Add Metrics**
   - Request latency
   - API usage
   - Cache hit rate
   - LLM token usage

3. **Error Tracking**
   - Sentry integration
   - Health check endpoint

### DevOps Readiness

1. **Dockerfile for Backend**
   ```dockerfile
   FROM python:3.11
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["uvicorn", "api:app", "--host", "0.0.0.0"]
   ```

2. **Docker Compose**
   ```yaml
   services:
     backend:
       build: ./backend
     frontend:
       build: ./frontend
     redis:
       image: redis
   ```

3. **Environment-Specific Config**
   - Development vs Production settings

---

## 8️⃣ Overall Quality Rating

### **Rating: 5.5 / 10**

### Reasoning

| Category | Score | Notes |
|----------|-------|-------|
| Functionality | 7/10 | Works for happy path, but API mismatch breaks it |
| Code Quality | 5/10 | Good agent pattern, but App.js is a monolith |
| Security | 2/10 | Exposed keys, open CORS, no input validation |
| Scalability | 4/10 | Single endpoint, local cache, no queue |
| Maintainability | 5/10 | Needs tests, docs, error handling |
| UX/UI | 8/10 | Beautiful visualization, good animations |

### Summary

This is a **functional prototype** with excellent visualization and a well-designed agent architecture. However, it has **critical production-readiness issues**:

1. 🔴 API keys in repo
2. 🔴 API endpoint mismatch
3. 🔴 No authentication
4. 🟠 No testing
5. 🟠 No rate limiting
6. 🟠 Process-local cache

**Recommendation**: Fix critical issues before any production deployment. The codebase shows good engineering instincts (LangGraph, agent pattern, validation) but needs hardening for production use.

---

## 9️⃣ Actionable Fix Guide (Based on Code Review)

### 🔴 CRITICAL FIXES

#### Fix 1 — API Keys Exposed
**Priority: IMMEDIATE**

1. Rotate all exposed API keys (Tavily, Groq)
2. Remove from Git history: `bfg --delete-files .env`
3. Add `.env` to `.gitignore`
4. Create `.env.example` template
5. Add pre-commit hook with `detect-secrets`

#### Fix 2 — Remove News Integration Layer
**Priority: HIGH**

1. Delete MoneyControl/NSE scraper code
2. Remove imports from `api.py`, `workflow.py`
3. Update LLM prompts to remove news context
4. Test `/company/{name}/intelligence` endpoint

#### Fix 3 — Lock Down CORS
**Priority: HIGH**

```python
# Before (insecure)
allow_origins=["*"]

# After (secure)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in allowed_origins])
```

#### Fix 4 — Input Validation
**Priority: HIGH**

1. Add Pydantic validation for company name:
```python
SAFE_COMPANY_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9\s\.\-\&\,\' ]{2,100}$")
```
2. Sanitize LLM prompt injection
3. Add rate limiting with `slowapi`

### 🟠 MODERATE FIXES

#### Fix 5 — Redis Cache
1. Replace dict cache with Redis:
```python
import redis.asyncio as redis
async def cache_get(key: str): ...
async def cache_set(key: str, value: dict): ...
```
2. Add Docker Compose for local dev

#### Fix 6 — Add Tests
1. Install: `pytest pytest-asyncio httpx pytest-cov`
2. Create `backend/tests/` structure
3. Set 60% minimum coverage threshold

#### Fix 7 — Dynamic Scraper Architecture
1. Replace hardcoded scrapers with `ScraperRegistry` pattern
2. Add company resolver for region detection
3. Use web search as global fallback

---

*Report generated: 2026-03-22*
