# Advanced Financial Modeling Prep (FMP) Data Fetcher

> A powerful, reusable component for retrieving, processing, and organizing financial data through the FMP API for AI applications, RAG systems, and financial analysis.

## 🌟 Overview

The FMP Advanced Fetcher is a comprehensive toolkit designed for building robust financial datasets from the Financial Modeling Prep API. Built with reusability in mind, it standardizes data formats, implements intelligent rate limiting and caching, and provides rich processing capabilities that make it perfect for agentic AI applications, RAG systems, and financial analysis workflows.

## ✨ Features

- **Comprehensive Data Collection**
  - Company profiles with enhanced metadata
  - Financial metrics with historical trends and standardized formats
  - Full financial statements (income, balance sheet, cash flow)
  - Earnings call transcripts with speaker segmentation and sentiment analysis
  - News articles with relevance scoring and keyword extraction
  - SEC filings (10-K, 10-Q, 8-K) with section parsing

- **Intelligent Processing**
  - Smart rate limiting to prevent API usage exceeded errors
  - Efficient caching to reduce API calls
  - Parallel request execution for faster data retrieval
  - Standardized data schemas for consistent AI model consumption
  - Multi-company comparison and sector analysis capabilities

- **Flexible Outputs**
  - JSON, CSV, and Parquet output formats
  - Hierarchical data organization for complex relationships
  - Customizable datasets (single-company, multi-company, market overview)

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/Kris-Nale314/datasets.git
cd datasets

# Install dependencies
pip install -r requirements.txt
```

## 🚀 Quick Start

```python
from financial.fmp_api.scripts.fmp_advanced_fetcher import FMPAdvancedFetcher

# Initialize the fetcher with your API key
fetcher = FMPAdvancedFetcher(api_key="your_api_key_here")

# Create a comprehensive dataset for a single company
apple_dataset = fetcher.save_company_dataset(
    symbol="AAPL",
    include_transcripts=True,
    include_news=True,
    output_format="json"
)

# Create a comparison dataset for multiple companies
tech_comparison = fetcher.create_multi_company_dataset(
    symbols=["AAPL", "MSFT", "GOOGL"],
    dataset_type="comparison",
    content_types=["profile", "metrics", "financials"]
)

# Generate a sector overview
tech_sector = fetcher.create_market_overview_dataset(
    sector="Technology",
    market_cap_min=10,  # $10B minimum
    limit=15
)
```

## 📋 Data Types

### Company Profile
Comprehensive company information including:
- Basic identifiers (name, symbol, exchange)
- Industry classification (sector, industry)
- Corporate details (CEO, employees, address)
- Market metrics (market cap, beta, volume)
- Company ratings and investment recommendations

### Financial Metrics
Standardized metrics in categories including:
- Valuation (P/E, P/B, EV/EBITDA)
- Profitability (ROE, ROA, margins)
- Liquidity (current ratio, quick ratio)
- Solvency (debt ratios, interest coverage)
- Cash flow (FCF yield, capex/share)
- Per-share metrics (EPS, book value, dividends)

### Financial Statements
Standardized statements including:
- Income statements (revenue, expenses, profits)
- Balance sheets (assets, liabilities, equity)
- Cash flow statements (operating, investing, financing)

### Earnings Call Transcripts
Enhanced transcripts with:
- Speaker segmentation (separates executives, analysts, operators)
- Sentiment analysis by segment
- Structured metadata (date, quarter, fiscal year)

### News Articles
Processed news with:
- Source information and publication date
- Automated text summarization
- Keyword extraction
- Relevance scoring

### SEC Filings
Structured filing data including:
- Filing metadata (date, type, fiscal period)
- Full text content (optional)
- Automatic section parsing (for 10-K, 10-Q, 8-K)

## 💡 Advanced Usage

### Creating a Comprehensive Company Dataset

```python
dataset_path = fetcher.save_company_dataset(
    symbol="TSLA",
    include_profile=True,
    include_metrics=True,
    include_financials=True,
    include_transcripts=True,
    include_news=True,
    include_filings=True,
    output_format="json"
)
```

### Retrieving Earnings Call Transcripts with Speaker Segmentation

```python
transcripts = fetcher.get_earnings_call_transcripts(
    symbol="AMZN",
    limit=2,                 # Get last 2 earnings calls
    parse_speakers=True,     # Segment by speaker
    include_sentiment=True   # Add basic sentiment analysis
)

# Extract CEO comments
for transcript in transcripts:
    ceo_segments = [
        segment for segment in transcript["content"]["segments"]
        if "CEO" in segment["speaker"]
    ]
    print(f"CEO comments in {transcript['title']}:")
    for segment in ceo_segments:
        print(f"- {segment['text'][:100]}...")
        print(f"  Sentiment: {segment['sentiment']['assessment']}")
```

### Comparing Multiple Companies

```python
comparison = fetcher.create_multi_company_dataset(
    symbols=["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
    dataset_type="comparison",
    content_types=["profile", "metrics", "financials"]
)

# The comparison dataset includes:
# - Individual company data
# - Comparative analysis across metrics
# - Rankings for key performance indicators
# - Industry averages
```

### Creating a Sector Overview

```python
sector_overview = fetcher.create_market_overview_dataset(
    sector="Healthcare",
    market_cap_min=5,    # $5B minimum market cap
    limit=20             # Top 20 companies by market cap
)

# The sector overview includes:
# - Company profiles and basic metrics
# - Industry breakdown within the sector
# - Market cap distribution
# - Average valuation and performance metrics
```

## 🧩 Integration with Other Components

### RAG System Integration

The standardized data format makes it easy to create embeddings for RAG systems:

```python
import json

# Load a company dataset
with open("datasets/financial/fmp_api/datasets/aapl_comprehensive_data.json", "r") as f:
    company_data = json.load(f)

# Extract text for embedding
texts = []

# Add company description
texts.append(company_data["profile"]["description"])

# Add key financial facts
metrics = company_data["metrics"]["current"]
texts.append(f"Revenue: ${company_data['financials']['income_statements'][0]['revenue']['total']/1e9:.2f}B")
texts.append(f"Net Income: ${company_data['financials']['income_statements'][0]['netIncome']/1e9:.2f}B")
texts.append(f"P/E Ratio: {metrics['valuation']['peRatio']:.2f}")

# Add earnings call highlights
for call in company_data["earnings_calls"]:
    for segment in call["content"]["segments"]:
        if "CEO" in segment["speaker"] or "CFO" in segment["speaker"]:
            texts.append(segment["text"])

# Create embeddings (using your preferred embedding model)
# embeddings = create_embeddings(texts)
```

### Financial Analysis Integration

The data can easily be converted to pandas DataFrames for analysis:

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load multiple company datasets for comparison
companies = ["AAPL", "MSFT", "AMZN", "GOOGL"]
metrics_data = []

for symbol in companies:
    with open(f"datasets/financial/fmp_api/datasets/{symbol.lower()}_comprehensive_data.json", "r") as f:
        data = json.load(f)
        
    # Extract key metrics
    current = data["metrics"]["current"]
    metrics_data.append({
        "Symbol": symbol,
        "P/E Ratio": current["valuation"]["peRatio"],
        "P/B Ratio": current["valuation"]["pbRatio"],
        "ROE": current["profitability"]["roe"] * 100,  # Convert to percentage
        "Net Margin": current["profitability"]["netMargin"] * 100,  # Convert to percentage
        "Debt to Equity": current["solvency"]["debtToEquity"]
    })

# Create DataFrame
df = pd.DataFrame(metrics_data)
df.set_index("Symbol", inplace=True)

# Visualize
ax = df.plot(kind="bar", figsize=(12, 8))
ax.set_title("Comparison of Key Financial Metrics")
plt.tight_layout()
plt.show()
```

## 🔧 Customization

### Custom Rate Limiting

Adjust rate limiting based on your API plan:

```python
fetcher = FMPAdvancedFetcher(
    api_key="your_api_key_here",
    rate_limit=600,          # Requests per minute (premium plan)
    parallel_requests=5      # Run 5 requests in parallel
)
```

### Custom Caching

Configure caching to reduce API calls:

```python
fetcher = FMPAdvancedFetcher(
    api_key="your_api_key_here",
    cache_dir="/path/to/custom/cache",
    cache_expiry=48          # Cache expiry in hours
)
```

## ⚠️ Limitations and Notes

- **API Key Required**: An FMP API key is required (available at [financialmodelingprep.com](https://financialmodelingprep.com))
- **Rate Limits**: The free tier has strict rate limits; consider premium plans for larger datasets
- **Data Accuracy**: Financial data may have delays or inaccuracies; always verify critical information
- **Filing Content**: SEC filing text extraction is basic and may not capture all formatting or tables
- **Sentiment Analysis**: The built-in sentiment analysis is basic; consider integrating with dedicated NLP services for production use

## 🤝 Contributing

Contributions are welcome! Here are ways you can help improve this component:

1. **Data Schema Enhancements**: Suggest improvements to standardized data formats
2. **Processing Algorithms**: Add advanced processing capabilities (e.g., better sentiment analysis)
3. **New Data Types**: Implement access to additional FMP endpoints
4. **Performance Optimizations**: Improve caching or parallel processing
5. **Documentation**: Help improve examples and usage patterns

## 📝 License

This component is available under the MIT License - see the LICENSE file for details.

---
