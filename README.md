# FinPulse

FinPulse is an AI-powered financial report generator that analyzes SEC filings to create intelligent, data-driven insights using Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG).

### Prerequisites
- Python 3.10+
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

4. **Launch web interface**
   ```bash
   make app
   ```

## Usage

### Web Interface
Launch the Gradio app for an interactive experience:
```bash
make app
# or
python app/gradio_app.py
```

## Architecture

### Core Components

- ** Data Ingestion** (`src/finpulse/ingest/`)
  - SEC EDGAR API client
  - Company ticker → CIK mapping
  - Financial KPI extraction

- ** RAG Pipeline** (`src/finpulse/rag/`)
  - Document chunking and indexing
  - Keyword-based document matching
  - JSON-based document indexing for similarity search

- ** LLM Integration** (`src/finpulse/llm/`)
  - Google Gemini for report generation
  - Structured prompts with citations
  - KPI table formatting

- ** Report Generation** (`src/finpulse/report/`)
  - End-to-end pipeline orchestration
  - Report formatting and presentation

- ** Web Interface** (`app/`)
  - Gradio-based interactive UI
  - Real-time report generation
  - Tabbed interface for organized results

### Key Features

-  **Automated KPI Extraction**: Net Income, EPS, Cash, Debt
-  **RAG-Powered Analysis**: Retrieves relevant context from SEC filings
-  **AI-Generated Insights**: Professional financial summaries with citations
-  **Web Interface**: Interactive Gradio-based UI

## Environment Setup

### Required Environment Variables

Create a `.env` file with:

```env
# Google Gemini API Key (required)
GEMINI_API_KEY=your_gemini_api_key_here

# SEC EDGAR API User Agent (required for compliance)
FINPULSE_USER_AGENT="FinPulse/1.0 (team@example.com)"

```

### Getting API Keys

1. **Google Gemini API**: Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **SEC EDGAR**: Free, but requires proper User-Agent header

## Development

### Available Commands
```bash
make help          # Show available commands
make setup         # Set up development environment
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

## Important Notes

### Data Sources
- **SEC EDGAR**: Official SEC filings (10-Q quarterly reports)
- **Real-time**: Always fetches latest available data
- **Transparency**: All sources are cited with direct links

### Limitations
- **Not Investment Advice**: For informational purposes only
- **Data Lag**: SEC filings may have reporting delays
- **API Dependencies**: Requires stable internet connection
- **Revenue Data**: Currently excluded due to inconsistent reporting formats across companies and unreliable extraction methods

### Future Improvements
- **Revenue Integration**: Implement robust revenue extraction with better pattern matching and validation
- **Enhanced KPIs**: Add more financial metrics like operating income, EBITDA, and cash flow
- **Dense Embeddings**: Upgrade from keyword-based to semantic search for better retrieval
- **Multi-Form Support**: Extend beyond 10-Q to include 10-K annual reports

## License

MIT License © 2025 FinPulse Team

## Team

- **Adam Rokah**
- **Christoph Armann**
- **Lavy Selvaraj**

---

**Disclaimer**: This tool is for educational and informational purposes only. It is not intended as investment advice. Always consult with a qualified financial advisor before making investment decisions.
