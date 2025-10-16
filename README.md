# FinPulse 📊

FinPulse is an AI-powered financial report generator that analyzes SEC filings to create intelligent, data-driven insights using Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG).

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Google Gemini API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/arokah25/FinPulse-chatbot-.git
   cd FinPulse-chatbot-
   ```

2. **Set up environment**
   ```bash
   make setup
   ```

3. **Configure API keys**
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

4. **Test the CLI**
   ```bash
   make run-cli
   ```

5. **Launch web interface**
   ```bash
   make app
   ```

## 💡 Usage

### Command Line Interface
```bash
# Generate quarterly report for Apple
python -m finpulse --ticker AAPL --scope 10Q

# Generate annual report for Microsoft
python -m finpulse --ticker MSFT --scope 10K

# Custom analysis query
python -m finpulse --ticker GOOGL --scope 10Q --query "revenue growth and profitability"
```

### Web Interface
Launch the Streamlit app for an interactive experience:
```bash
make app
# or
streamlit run app/streamlit_app.py
```

## 🏗️ Architecture

### Core Components

- **📥 Data Ingestion** (`src/finpulse/ingest/`)
  - SEC EDGAR API client
  - Company ticker → CIK mapping
  - Financial KPI extraction

- **🔍 RAG Pipeline** (`src/finpulse/rag/`)
  - Document chunking and indexing
  - Vector embeddings with sentence-transformers
  - ChromaDB for similarity search

- **🤖 LLM Integration** (`src/finpulse/llm/`)
  - Google Gemini for report generation
  - Structured prompts with citations
  - KPI table formatting

- **📊 Report Generation** (`src/finpulse/report/`)
  - End-to-end pipeline orchestration
  - Report formatting and presentation

### Key Features

- ✅ **Automated KPI Extraction**: Revenues, Net Income, EPS, Cash, Debt
- ✅ **RAG-Powered Analysis**: Retrieves relevant context from SEC filings
- ✅ **AI-Generated Insights**: Professional financial summaries with citations
- ✅ **Dual Interface**: CLI and web interface
- ✅ **Caching**: Efficient data storage and retrieval
- ✅ **Type Safety**: Full type hints and documentation

## 📋 Environment Setup

### Required Environment Variables

Create a `.env` file with:

```env
# Google Gemini API Key (required)
GEMINI_API_KEY=your_gemini_api_key_here

# SEC EDGAR API User Agent (required for compliance)
FINPULSE_USER_AGENT="FinPulse/1.0 (team@example.com)"

# Optional: Custom directories
CHROMA_DIR=data/cache/chroma
CACHE_DIR=data/cache
```

### Getting API Keys

1. **Google Gemini API**: Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **SEC EDGAR**: Free, but requires proper User-Agent header

## 🔧 Development

### Project Structure
```
FinPulse-chatbot-/
├── src/finpulse/          # Main package
│   ├── ingest/            # SEC data ingestion
│   ├── rag/               # Retrieval-Augmented Generation
│   ├── llm/               # LLM integration
│   ├── report/            # Report generation
│   └── utils/             # Utility functions
├── app/                   # Web interface
├── tests/                 # Test suite
├── data/cache/            # Cached data
└── Makefile              # Development commands
```

### Available Commands
```bash
make help          # Show available commands
make setup         # Set up development environment
make run-cli       # Run CLI example
make app           # Launch web interface
make test          # Run tests
make clean         # Clean cache and temp files
```

### Testing
```bash
# Run all tests
make test

# Quick import test
make quick-test
```

## 📊 Example Output

```
FINANCIAL REPORT: AAPL (10-Q)
============================================================

Company: Apple Inc.
CIK: 320193
Filings Analyzed: 3
Query: latest quarterly performance

----------------------------------------
KEY FINANCIAL METRICS
----------------------------------------
Revenues                         $89,498.00M (2024-09-28)
NetIncomeLoss                    $22,956.00M (2024-09-28)
EarningsPerShareDiluted                  $1.53 (2024-09-28)
CashAndCashEquivalentsAtCarryingValue $99,395.00M (2024-09-28)

----------------------------------------
FINANCIAL ANALYSIS
----------------------------------------
Apple Inc. reported strong quarterly performance with revenues of $89.5 billion [S1], 
representing solid growth in their core product segments. Net income reached $22.96 billion [S2], 
demonstrating continued profitability and operational efficiency...

Sources:
[S1] https://www.sec.gov/Archives/edgar/data/320193/... (relevance: 0.892)
[S2] https://www.sec.gov/Archives/edgar/data/320193/... (relevance: 0.845)
```

## ⚠️ Important Notes

### Rate Limiting & Compliance
- **SEC EDGAR**: Respects rate limits (10 requests/second)
- **User Agent**: Required for SEC compliance
- **Caching**: Implements intelligent caching to reduce API calls

### Data Sources
- **SEC EDGAR**: Official SEC filings (10-K, 10-Q)
- **Real-time**: Always fetches latest available data
- **Transparency**: All sources are cited with direct links

### Limitations
- **Not Investment Advice**: For informational purposes only
- **Data Lag**: SEC filings may have reporting delays
- **API Dependencies**: Requires stable internet connection

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License © 2025 FinPulse Team

## 👥 Team

- **Adam Rokah** - Lead Developer
- **Christoff Armann** - Research & Development  
- **Lavy Selvaraj** - UI/UX & Testing

---

**Disclaimer**: This tool is for educational and informational purposes only. It is not intended as investment advice. Always consult with a qualified financial advisor before making investment decisions.
