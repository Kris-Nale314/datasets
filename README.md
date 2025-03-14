# 🗃️ Datasets

> Where data dreams come true! A delightful collection of datasets and data generation scripts for all your AI adventures.

## 🌟 Overview

Welcome to the `datasets` repository! This is my personal treasure trove of datasets and data generation scripts that I've created, curated, and collected throughout my AI journey. Whether you're looking for financial data from FMP API, text corpora for NLP, or utilities to wrangle your own datasets into submission, you'll find it all neatly organized here.

## 📂 Repository Structure

```
datasets/
├── financial/       # Financial datasets and generation scripts
├── nlp/             # Natural language processing datasets
├── vision/          # Image and video datasets
├── multimodal/      # Datasets combining multiple modalities
├── utils/           # Utility scripts for data processing
└── templates/       # Templates for dataset documentation
```

## 🔍 Dataset Categories

### 💰 Financial

The `financial/` directory contains datasets and scripts related to financial data, including:

- **FMP API**: Scripts to pull and process data from Financial Modeling Prep API
- **Market Data**: Historical stock prices, indices, and related financial instruments
- **Financial Reports**: Structured data from quarterly and annual reports

### 🔤 NLP

The `nlp/` directory houses text-based datasets and generation scripts, including:

- **Text Corpora**: Collections of text for training language models
- **Embeddings**: Pre-computed embeddings for various text datasets
- **Conversational Data**: Dialogue datasets for training conversational AI

### 👁️ Vision

The `vision/` directory contains image and video datasets, including:

- **Image Collections**: Categorized images for computer vision tasks
- **Video Snippets**: Short video clips for motion analysis
- **Annotations**: Bounding boxes, segmentation masks, and other annotations

### 🔮 Multimodal

The `multimodal/` directory contains datasets that span multiple modalities, perfect for training models that can understand both text and images, or other combinations.

## 🛠️ Utilities

The `utils/` directory contains scripts to help you work with the datasets:

- **Data Cleaning**: Scripts to sanitize and normalize data
- **Format Conversion**: Tools to convert between different data formats
- **Metadata Generation**: Utilities to generate and validate dataset metadata

## 📋 Using the Templates

The `templates/` directory contains standardized templates for:

- Dataset metadata in JSON format
- Dataset README files
- Script headers with standardized documentation

## 🚀 Getting Started

To use these datasets and scripts:

1. Clone this repository:
   ```bash
   git clone https://github.com/Kris-Nale314/datasets.git
   cd datasets
   ```

2. Explore the directories to find datasets or scripts you're interested in.

3. Each dataset comes with its own README providing specific usage instructions.

## 📊 Example: Using the FMP API Script

The FMP API script allows you to pull financial data and store it in a structured JSON format for use in LLMs or RAG systems:

```python
from financial.fmp_api.scripts.fetcher import FMPDataFetcher

# Initialize the fetcher with your API key
fetcher = FMPDataFetcher(api_key="your_api_key_here")

# Fetch financial data for a specific company
apple_data = fetcher.get_company_profile("AAPL")

# Save the data to a JSON file
fetcher.save_to_json(apple_data, "apple_profile.json")
```

## 🤝 Contributing

While this is primarily a personal repository, contributions, suggestions, and issues are welcome! If you have ideas for improving the organization or want to add your own datasets/scripts, please:

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

## 📝 Dataset Documentation Standard

Each dataset in this repository follows a standard documentation format:

- **Name**: What the dataset is called
- **Description**: What the dataset contains
- **Source**: Where the data came from
- **Size**: How big the dataset is
- **Format**: What format the data is in
- **License**: How the dataset can be used
- **Last Updated**: When the dataset was last modified
- **Usage Examples**: Code snippets showing how to use the dataset

## 📜 License

This repository and its contents are available under the MIT License - see the LICENSE file for details.

---

Happy data wrangling! 🎉

*"Data is the new oil, but unlike oil, it becomes more valuable the more it's refined." - Unknown*