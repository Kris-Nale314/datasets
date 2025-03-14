"""
Advanced Financial Modeling Prep (FMP) Data Fetcher

This module provides a comprehensive toolkit for retrieving, processing, and organizing
financial data from the Financial Modeling Prep API. Built for reusability across
agentic AI applications, RAG systems, and financial analysis workflows.

Features:
- Fetches comprehensive company data (profiles, metrics, financials, SEC filings)
- Retrieves and processes earnings call transcripts with speaker segmentation
- Collects and standardizes news articles and press releases
- Organizes data in a consistent schema for AI model consumption
- Implements smart rate limiting and caching to optimize API usage
- Provides flexible output formats (JSON, CSV, Parquet)

Author: Kris
Created: 2025-03-14
Last Modified: 2025-03-14
Version: 2.0.0
"""

import os
import json
import time
import logging
import requests
import hashlib
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple, Set
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FMPAdvancedFetcher:
    """
    Advanced toolkit for accessing and processing Financial Modeling Prep API data.
    Designed for reusability across AI applications with standardized data schemas.
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://financialmodelingprep.com/api/v3",
        data_dir: Optional[str] = None,
        cache_dir: Optional[str] = None,
        rate_limit: int = 300,  # Requests per minute (FMP's standard limit)
        cache_expiry: int = 24,  # Cache expiry in hours
        parallel_requests: int = 3  # Number of parallel requests
    ):
        """
        Initialize the Enhanced FMP API tool.
        
        Args:
            api_key: FMP API key
            base_url: Base URL for the FMP API
            data_dir: Directory for saving processed datasets
            cache_dir: Directory for caching API responses
            rate_limit: Maximum requests per minute
            cache_expiry: Hours before cached data expires
            parallel_requests: Maximum number of parallel requests
        """
        if not api_key:
            raise ValueError("API key is required")
        
        self.api_key = api_key
        self.base_url = base_url
        
        # Set up data directory
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "../../datasets/financial/fmp_api/datasets"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "../../.cache/fmp_api"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Rate limiting setup
        self.rate_limit = rate_limit
        self.request_timestamps = []
        self.cache_expiry = timedelta(hours=cache_expiry)
        self.parallel_requests = parallel_requests
        
        logger.info(f"Initialized FMPAdvancedFetcher (cache: {self.cache_dir})")
    
    def _get_cache_path(self, endpoint: str, params: Dict[str, Any] = None) -> Path:
        """
        Generate a cache file path for a specific API request.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Path to cache file
        """
        # Create a unique key based on endpoint and parameters
        param_str = json.dumps(params or {}, sort_keys=True)
        key = f"{endpoint}:{param_str}"
        hash_key = hashlib.md5(key.encode()).hexdigest()
        
        return self.cache_dir / f"{hash_key}.json"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """
        Check if a cached file is still valid (not expired).
        
        Args:
            cache_path: Path to cache file
            
        Returns:
            True if cache is valid, False otherwise
        """
        if not cache_path.exists():
            return False
        
        # Check file modification time
        mod_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        return datetime.now() - mod_time < self.cache_expiry
    
    def _enforce_rate_limit(self):
        """
        Enforce API rate limiting by adding delays when necessary.
        """
        current_time = time.time()
        
        # Remove timestamps older than 1 minute
        self.request_timestamps = [t for t in self.request_timestamps if current_time - t < 60]
        
        # Check if we've hit the rate limit
        if len(self.request_timestamps) >= self.rate_limit:
            # Calculate how long to wait - when the oldest timestamp will be more than 1 minute old
            oldest_timestamp = min(self.request_timestamps)
            wait_time = 60 - (current_time - oldest_timestamp) + 0.1  # Add a small buffer
            
            if wait_time > 0:
                logger.debug(f"Rate limit reached. Waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
    
    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Make a request to the FMP API with caching and rate limiting.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            use_cache: Whether to use/update cache
            
        Returns:
            API response as dictionary
        """
        # Check cache first if enabled
        if use_cache:
            cache_path = self._get_cache_path(endpoint, params)
            if self._is_cache_valid(cache_path):
                try:
                    with open(cache_path, 'r') as f:
                        logger.debug(f"Using cached response for {endpoint}")
                        return json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Error reading cache: {e}")
        
        # Enforce rate limiting
        self._enforce_rate_limit()
        
        # Initialize parameters
        request_params = params.copy() if params else {}
        request_params["apikey"] = self.api_key
        
        # Construct URL
        url = f"{self.base_url}/{endpoint}"
        
        # Make request
        try:
            logger.debug(f"Making request to {url}")
            response = requests.get(url, params=request_params)
            self.request_timestamps.append(time.time())
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            # Cache the response if enabled
            if use_cache:
                cache_path = self._get_cache_path(endpoint, params)
                with open(cache_path, 'w') as f:
                    json.dump(data, f)
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Error making request to {url}: {e}")
            
            # If we get a 429 (Too Many Requests), wait and retry
            if hasattr(e, 'response') and e.response and e.response.status_code == 429:
                logger.warning("Rate limit exceeded. Waiting 60 seconds before retrying...")
                time.sleep(60)
                return self._make_request(endpoint, params, use_cache)
            
            raise
    
    def _parallel_requests(
        self,
        requests_info: List[Tuple[str, Dict[str, Any]]],
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple API requests in parallel.
        
        Args:
            requests_info: List of (endpoint, params) tuples
            use_cache: Whether to use/update cache
            
        Returns:
            List of API responses
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.parallel_requests) as executor:
            # Submit all requests
            future_to_idx = {
                executor.submit(
                    self._make_request, endpoint, params, use_cache
                ): i for i, (endpoint, params) in enumerate(requests_info)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    data = future.result()
                    results.append((idx, data))
                except Exception as e:
                    logger.error(f"Error in parallel request {idx}: {e}")
                    results.append((idx, None))
        
        # Sort results back to original order
        results.sort(key=lambda x: x[0])
        return [data for _, data in results]
    
    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive company profile information.
        
        Args:
            symbol: Company stock symbol
            
        Returns:
            Company profile data with standardized fields
        """
        logger.info(f"Getting company profile for {symbol}")
        
        try:
            # Get company profile
            data = self._make_request(f"profile/{symbol}")
            
            if not data or len(data) == 0:
                logger.warning(f"No profile data found for {symbol}")
                return {}
            
            # Get additional company information
            try:
                rating_data = self._make_request(f"rating/{symbol}")
                rating = rating_data[0] if rating_data and len(rating_data) > 0 else {}
            except Exception as e:
                logger.warning(f"Could not get rating data: {e}")
                rating = {}
            
            # Standardize and enrich profile data
            profile = data[0]
            enriched_profile = {
                "symbol": symbol,
                "name": profile.get("companyName", ""),
                "exchange": profile.get("exchangeShortName", ""),
                "industry": profile.get("industry", ""),
                "sector": profile.get("sector", ""),
                "description": profile.get("description", ""),
                "ceo": profile.get("ceo", ""),
                "employees": profile.get("fullTimeEmployees", 0),
                "address": {
                    "street": profile.get("address", ""),
                    "city": profile.get("city", ""),
                    "state": profile.get("state", ""),
                    "zip": profile.get("zip", ""),
                    "country": profile.get("country", "")
                },
                "contact": {
                    "phone": profile.get("phone", ""),
                    "website": profile.get("website", "")
                },
                "tickers": {
                    "primary": symbol,
                    "cik": profile.get("cik", ""),
                    "cusip": profile.get("cusip", ""),
                    "isin": profile.get("isin", "")
                },
                "metrics": {
                    "marketCap": profile.get("mktCap", 0),
                    "beta": profile.get("beta", 0),
                    "lastDiv": profile.get("lastDiv", 0),
                    "dcf": profile.get("dcf", 0),
                    "price": profile.get("price", 0),
                    "changes": profile.get("changes", 0),
                    "volume": profile.get("volAvg", 0)
                },
                "dates": {
                    "ipoDate": profile.get("ipoDate", ""),
                    "updated": datetime.now().isoformat()
                },
                "rating": {
                    "score": rating.get("ratingScore", 0),
                    "recommendation": rating.get("recommendation", ""),
                    "details": {
                        "dcfScore": rating.get("dcfScore", 0),
                        "roe": rating.get("roe", 0),
                        "roa": rating.get("roa", 0),
                        "de": rating.get("de", 0),
                        "pe": rating.get("pe", 0),
                        "pb": rating.get("pb", 0)
                    }
                },
                "flags": {
                    "isActivelyTrading": profile.get("isActivelyTrading", False),
                    "isEtf": profile.get("isEtf", False),
                    "isAdr": profile.get("isAdr", False),
                    "isFund": profile.get("isFund", False)
                }
            }
            
            return enriched_profile
            
        except Exception as e:
            logger.error(f"Error getting company profile for {symbol}: {e}")
            raise
    
    def get_company_metrics(self, symbol: str, period: str = "annual", limit: int = 5) -> Dict[str, Any]:
        """
        Get company financial metrics with historical trends.
        
        Args:
            symbol: Company stock symbol
            period: 'annual' or 'quarter'
            limit: Number of periods to retrieve
            
        Returns:
            Financial metrics data with trends
        """
        logger.info(f"Getting financial metrics for {symbol} ({period}, limit: {limit})")
        
        try:
            # Get current metrics (TTM)
            current_data = self._make_request(f"key-metrics-ttm/{symbol}")
            
            # Get historical metrics
            historical_data = self._make_request(f"key-metrics/{symbol}", {
                "period": period,
                "limit": limit
            })
            
            # Get ratios
            ratio_data = self._make_request(f"ratios/{symbol}", {
                "period": period,
                "limit": limit
            })
            
            # Get financial growth rates
            growth_data = self._make_request(f"financial-growth/{symbol}", {
                "period": period,
                "limit": limit
            })
            
            # Process and combine metrics
            current_metrics = current_data[0] if current_data and len(current_data) > 0 else {}
            historical_metrics = historical_data if historical_data else []
            ratios = ratio_data if ratio_data else []
            growth = growth_data if growth_data else []
            
            # Build standardized metrics object
            metrics = {
                "symbol": symbol,
                "current": self._standardize_metrics(current_metrics),
                "historical": [
                    self._combine_historical_metrics(h, r, g)
                    for h, r, g in zip(
                        historical_metrics[:limit],
                        ratios[:limit] if ratios else [{}] * limit,
                        growth[:limit] if growth else [{}] * limit
                    )
                ],
                "period": period,
                "updated": datetime.now().isoformat()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting financial metrics for {symbol}: {e}")
            raise
    
    def _standardize_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize raw metrics into a consistent format.
        
        Args:
            metrics: Raw metrics data
            
        Returns:
            Standardized metrics
        """
        # Create categorized metrics dictionary
        return {
            "date": metrics.get("date", ""),
            "valuation": {
                "peRatio": metrics.get("peRatio", 0),
                "pbRatio": metrics.get("pbRatio", 0),
                "evToEbitda": metrics.get("enterpriseValueOverEBITDA", 0),
                "evToRevenue": metrics.get("evToSales", 0),
                "priceToSales": metrics.get("priceToSalesRatio", 0),
                "grahamNumber": metrics.get("grahamNumber", 0)
            },
            "profitability": {
                "roe": metrics.get("roe", 0),
                "roa": metrics.get("roa", 0),
                "roic": metrics.get("roic", 0),
                "grossMargin": metrics.get("grossProfitMargin", 0),
                "operatingMargin": metrics.get("operatingProfitMargin", 0),
                "netMargin": metrics.get("netProfitMargin", 0),
                "fcfMargin": metrics.get("freeCashFlowMargin", 0)
            },
            "liquidity": {
                "currentRatio": metrics.get("currentRatio", 0),
                "quickRatio": metrics.get("quickRatio", 0),
                "cashRatio": metrics.get("cashRatio", 0),
                "daysOfSalesOutstanding": metrics.get("daysOfSalesOutstanding", 0),
                "daysOfInventoryOutstanding": metrics.get("daysOfInventoryOutstanding", 0),
                "operatingCycle": metrics.get("operatingCycle", 0)
            },
            "solvency": {
                "debtToEquity": metrics.get("debtToEquity", 0),
                "debtToAssets": metrics.get("debtToAssets", 0),
                "netDebtToEBITDA": metrics.get("netDebtToEBITDA", 0),
                "interestCoverage": metrics.get("interestCoverage", 0)
            },
            "cashFlow": {
                "fcfPerShare": metrics.get("freeCashFlowPerShare", 0),
                "capexPerShare": metrics.get("capexPerShare", 0),
                "fcfToRevenue": metrics.get("freeCashFlowToRevenue", 0),
                "fcfYield": metrics.get("freeCashFlowYield", 0)
            },
            "perShare": {
                "revenuePerShare": metrics.get("revenuePerShare", 0),
                "ebitdaPerShare": metrics.get("ebitdaPerShare", 0),
                "operatingCashFlowPerShare": metrics.get("operatingCashFlowPerShare", 0),
                "bookValuePerShare": metrics.get("bookValuePerShare", 0),
                "tangibleBookValuePerShare": metrics.get("tangibleBookValuePerShare", 0),
                "shareholdersEquityPerShare": metrics.get("shareholdersEquityPerShare", 0),
                "dividendPerShare": metrics.get("dividendPerShare", 0)
            }
        }
    
    def _combine_historical_metrics(
        self,
        metrics: Dict[str, Any],
        ratios: Dict[str, Any] = None,
        growth: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Combine historical metrics, ratios and growth data.
        
        Args:
            metrics: Historical metrics
            ratios: Historical ratios
            growth: Historical growth rates
            
        Returns:
            Combined historical data
        """
        # Start with standardized metrics
        combined = self._standardize_metrics(metrics)
        
        # Add ratios
        if ratios:
            combined["ratios"] = {
                "priceEarningsToGrowth": ratios.get("pegRatio", 0),
                "priceToCashFlow": ratios.get("priceCashFlowRatio", 0),
                "priceToOperatingCashFlow": ratios.get("priceToOperatingCashFlowsRatio", 0),
                "priceToFreeCashFlow": ratios.get("priceToFreeCashFlowsRatio", 0),
                "enterpriseValue": ratios.get("enterpriseValue", 0),
                "payoutRatio": ratios.get("payoutRatio", 0),
                "dividendYield": ratios.get("dividendYield", 0)
            }
        
        # Add growth rates
        if growth:
            combined["growth"] = {
                "revenueGrowth": growth.get("revenueGrowth", 0),
                "grossProfitGrowth": growth.get("grossProfitGrowth", 0),
                "ebitgrowth": growth.get("ebitgrowth", 0),
                "netIncomeGrowth": growth.get("netIncomeGrowth", 0),
                "epsgrowth": growth.get("epsgrowth", 0),
                "fcfGrowth": growth.get("freeCashFlowGrowth", 0),
                "dividendGrowth": growth.get("dividendsperShareGrowth", 0)
            }
        
        return combined
    
    def get_financial_statements(
        self,
        symbol: str,
        statement_type: str = "income",
        period: str = "annual",
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get standardized financial statements.
        
        Args:
            symbol: Company stock symbol
            statement_type: 'income', 'balance-sheet', or 'cash-flow'
            period: 'annual' or 'quarter'
            limit: Number of statements to retrieve
            
        Returns:
            List of standardized financial statements
        """
        valid_types = ["income", "balance-sheet", "cash-flow"]
        if statement_type not in valid_types:
            raise ValueError(f"Invalid statement type. Must be one of {valid_types}")
        
        logger.info(f"Getting {period} {statement_type} statements for {symbol} (limit: {limit})")
        
        try:
            # Get statement data
            endpoint = f"{statement_type}-statement/{symbol}"
            data = self._make_request(endpoint, {"period": period, "limit": limit})
            
            if not data:
                logger.warning(f"No {statement_type} statement data found for {symbol}")
                return []
            
            # Process statements based on type
            if statement_type == "income":
                return self._standardize_income_statements(data[:limit])
            elif statement_type == "balance-sheet":
                return self._standardize_balance_sheets(data[:limit])
            elif statement_type == "cash-flow":
                return self._standardize_cash_flow_statements(data[:limit])
            
        except Exception as e:
            logger.error(f"Error getting {statement_type} statements for {symbol}: {e}")
            raise
    
    def _standardize_income_statements(self, statements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Standardize income statements.
        
        Args:
            statements: Raw income statements
            
        Returns:
            Standardized income statements
        """
        standardized = []
        
        for stmt in statements:
            # Create standardized statement
            standard_stmt = {
                "date": stmt.get("date", ""),
                "period": stmt.get("period", ""),
                "revenue": {
                    "total": stmt.get("revenue", 0),
                    "costOfRevenue": stmt.get("costOfRevenue", 0),
                    "grossProfit": stmt.get("grossProfit", 0)
                },
                "operatingExpenses": {
                    "research": stmt.get("researchAndDevelopmentExpenses", 0),
                    "selling": stmt.get("sellingGeneralAndAdministrativeExpenses", 0),
                    "administrative": stmt.get("generalAndAdministrativeExpenses", 0),
                    "depreciation": stmt.get("depreciationAndAmortization", 0),
                    "total": stmt.get("operatingExpenses", 0)
                },
                "operatingIncome": stmt.get("operatingIncome", 0),
                "nonOperatingIncome": {
                    "interest": {
                        "income": stmt.get("interestIncome", 0),
                        "expense": stmt.get("interestExpense", 0)
                    },
                    "other": stmt.get("otherNonOperatingIncome", 0),
                    "total": stmt.get("totalNonOperatingIncome", 0)
                },
                "pretaxIncome": stmt.get("incomeBeforeTax", 0),
                "taxExpense": stmt.get("incomeTaxExpense", 0),
                "netIncome": stmt.get("netIncome", 0),
                "eps": {
                    "basic": stmt.get("eps", 0),
                    "diluted": stmt.get("epsdiluted", 0)
                },
                "sharesOutstanding": {
                    "basic": stmt.get("weightedAverageShsOut", 0),
                    "diluted": stmt.get("weightedAverageShsOutDil", 0)
                },
                "ebitda": stmt.get("ebitda", 0),
                "ebit": stmt.get("ebit", 0)
            }
            
            standardized.append(standard_stmt)
        
        return standardized
    
    def _standardize_balance_sheets(self, statements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Standardize balance sheets.
        
        Args:
            statements: Raw balance sheets
            
        Returns:
            Standardized balance sheets
        """
        standardized = []
        
        for stmt in statements:
            # Create standardized balance sheet
            standard_stmt = {
                "date": stmt.get("date", ""),
                "period": stmt.get("period", ""),
                "assets": {
                    "current": {
                        "cash": stmt.get("cashAndCashEquivalents", 0),
                        "shortTermInvestments": stmt.get("shortTermInvestments", 0),
                        "receivables": stmt.get("netReceivables", 0),
                        "inventory": stmt.get("inventory", 0),
                        "prepaid": stmt.get("otherCurrentAssets", 0),
                        "total": stmt.get("totalCurrentAssets", 0)
                    },
                    "nonCurrent": {
                        "property": stmt.get("propertyPlantEquipmentNet", 0),
                        "intangibles": stmt.get("intangibleAssets", 0),
                        "goodwill": stmt.get("goodwill", 0),
                        "investments": stmt.get("longTermInvestments", 0),
                        "taxAssets": stmt.get("deferredTaxAssets", 0),
                        "other": stmt.get("otherNonCurrentAssets", 0),
                        "total": stmt.get("totalNonCurrentAssets", 0)
                    },
                    "total": stmt.get("totalAssets", 0)
                },
                "liabilities": {
                    "current": {
                        "accounts": stmt.get("accountPayables", 0),
                        "shortTermDebt": stmt.get("shortTermDebt", 0),
                        "taxes": stmt.get("taxPayables", 0),
                        "deferred": stmt.get("deferredRevenue", 0),
                        "other": stmt.get("otherCurrentLiabilities", 0),
                        "total": stmt.get("totalCurrentLiabilities", 0)
                    },
                    "nonCurrent": {
                        "longTermDebt": stmt.get("longTermDebt", 0),
                        "deferredRevenue": stmt.get("deferredRevenueNonCurrent", 0),
                        "deferredTax": stmt.get("deferredTaxLiabilitiesNonCurrent", 0),
                        "other": stmt.get("otherNonCurrentLiabilities", 0),
                        "total": stmt.get("totalNonCurrentLiabilities", 0)
                    },
                    "total": stmt.get("totalLiabilities", 0)
                },
                "equity": {
                    "commonStock": stmt.get("commonStock", 0),
                    "retainedEarnings": stmt.get("retainedEarnings", 0),
                    "aoci": stmt.get("accumulatedOtherComprehensiveIncomeLoss", 0),
                    "treasury": stmt.get("treasuryStock", 0),
                    "other": stmt.get("otherStockholderEquity", 0),
                    "total": stmt.get("totalStockholdersEquity", 0)
                },
                "totalLiabilitiesAndEquity": stmt.get("totalLiabilitiesAndStockholdersEquity", 0),
                "netDebt": stmt.get("netDebt", 0),
                "workingCapital": stmt.get("totalCurrentAssets", 0) - stmt.get("totalCurrentLiabilities", 0)
            }
            
            standardized.append(standard_stmt)
        
        return standardized
    
    def _standardize_cash_flow_statements(self, statements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Standardize cash flow statements.
        
        Args:
            statements: Raw cash flow statements
            
        Returns:
            Standardized cash flow statements
        """
        standardized = []
        
        for stmt in statements:
            # Create standardized cash flow statement
            standard_stmt = {
                "date": stmt.get("date", ""),
                "period": stmt.get("period", ""),
                "operating": {
                    "netIncome": stmt.get("netIncome", 0),
                    "depreciation": stmt.get("depreciationAndAmortization", 0),
                    "inventoryChanges": stmt.get("changeInInventory", 0),
                    "accountsReceivableChanges": stmt.get("changeInAccountReceivables", 0),
                    "accountsPayableChanges": stmt.get("changeInAccountPayables", 0),
                    "other": stmt.get("otherOperatingActivities", 0),
                    "total": stmt.get("netCashProvidedByOperatingActivities", 0)
                },
                "investing": {
                    "capex": stmt.get("capitalExpenditure", 0),
                    "acquisitions": stmt.get("acquisitionsNet", 0),
                    "investments": stmt.get("purchasesOfInvestments", 0),
                    "salesOfInvestments": stmt.get("salesMaturitiesOfInvestments", 0),
                    "other": stmt.get("otherInvestingActivites", 0),
                    "total": stmt.get("netCashUsedForInvestingActivites", 0)
                },
                "financing": {
                    "debtRepayment": stmt.get("debtRepayment", 0),
                    "stockIssue": stmt.get("commonStockIssued", 0),
                    "stockRepurchase": stmt.get("commonStockRepurchased", 0),
                    "dividends": stmt.get("dividendsPaid", 0),
                    "other": stmt.get("otherFinancingActivites", 0),
                    "total": stmt.get("netCashUsedProvidedByFinancingActivities", 0)
                },
                "exchangeRateEffect": stmt.get("effectOfForexChangesOnCash", 0),
                "netCashChange": stmt.get("netChangeInCash", 0),
                "freeCashFlow": stmt.get("freeCashFlow", 0),
                "cashAtBeginning": stmt.get("cashAtBeginningOfPeriod", 0),
                "cashAtEnd": stmt.get("cashAtEndOfPeriod", 0)
            }
            
            standardized.append(standard_stmt)
        
        return standardized
    
    def get_earnings_call_transcripts(
        self,
        symbol: str,
        limit: int = 1,
        parse_speakers: bool = True,
        include_sentiment: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get earnings call transcripts with speaker segmentation and optional sentiment analysis.
        
        Args:
            symbol: Company stock symbol
            limit: Maximum number of transcripts to retrieve
            parse_speakers: Whether to parse and segment speakers
            include_sentiment: Whether to include basic sentiment analysis
            
        Returns:
            List of transcript data with enhanced structure
        """
        logger.info(f"Getting earnings call transcripts for {symbol} (limit: {limit})")
        
        try:
            # Get transcript list
            transcript_list = self._make_request(f"earning_call_transcript/{symbol}", {"quarter": "0"})
            
            if not transcript_list:
                logger.warning(f"No transcripts found for {symbol}")
                return []
            
            # Take only the requested number of transcripts
            transcripts = []
            for i, info in enumerate(transcript_list[:limit]):
                try:
                    quarter = info.get("quarter", "")
                    year = info.get("year", "")
                    
                    if quarter and year:
                        full_transcript = self._make_request(f"earning_call_transcript/{symbol}", {
                            "quarter": quarter,
                            "year": year
                        })
                        
                        if full_transcript and len(full_transcript) > 0:
                            transcript_data = full_transcript[0]
                            content = transcript_data.get("content", "")
                            
                            # Parse transcript with speaker segmentation if requested
                            if parse_speakers:
                                parsed_content = self._parse_transcript_speakers(content)
                            else:
                                parsed_content = {"full_text": content, "segments": []}
                            
                            # Add sentiment analysis if requested
                            if include_sentiment and parsed_content["segments"]:
                                parsed_content = self._add_segment_sentiment(parsed_content)
                            
                            # Create structured transcript data
                            transcript_obj = {
                                "symbol": symbol,
                                "title": f"{symbol} Earnings Call Q{quarter} {year}",
                                "date": transcript_data.get("date", ""),
                                "fiscal_period": {
                                    "quarter": quarter,
                                    "year": year
                                },
                                "content": parsed_content,
                                "metadata": {
                                    "source": "Financial Modeling Prep API",
                                    "processed_at": datetime.now().isoformat()
                                }
                            }
                            
                            transcripts.append(transcript_obj)
                    
                    # Add a small delay to avoid hitting rate limits
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"Error getting transcript details: {e}")
            
            return transcripts
            
        except Exception as e:
            logger.error(f"Error getting transcripts for {symbol}: {e}")
            raise
    
    def _parse_transcript_speakers(self, text: str) -> Dict[str, Any]:
        """
        Parse earnings call transcript to segment by speaker.
        
        Args:
            text: Raw transcript text
            
        Returns:
            Parsed transcript with speaker segments
        """
        if not text:
            return {"full_text": "", "segments": []}
        
        segments = []
        current_speaker = ""
        current_text = []
        
        # Basic pattern matching for speakers
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Check for typical speaker patterns
            speaker_match = False
            
            # Pattern: "Name - Title:" or "Name:"
            if ':' in line:
                parts = line.split(':', 1)
                potential_speaker = parts[0].strip()
                
                # Check if this looks like a speaker identification
                if len(potential_speaker) > 3 and (
                    '-' in potential_speaker or  # Contains role separator
                    potential_speaker.isupper() or  # All caps
                    any(word.lower() in potential_speaker.lower() for word in [
                        "CEO", "CFO", "COO", "CTO", "President", "Director", "Manager",
                        "Analyst", "Operator", "Moderator", "Executive", "Vice", "Chairman",
                        "Officer", "Investor", "Relations"
                    ])
                ):
                    if current_speaker and current_text:
                        segments.append({
                            "speaker": current_speaker,
                            "text": ' '.join(current_text)
                        })
                    
                    current_speaker = potential_speaker
                    current_text = [parts[1].strip()] if len(parts) > 1 else []
                    speaker_match = True
            
            # No speaker pattern, add to current text
            if not speaker_match:
                current_text.append(line)
        
        # Add final segment
        if current_speaker and current_text:
            segments.append({
                "speaker": current_speaker,
                "text": ' '.join(current_text)
            })
            
        # Handle case where parsing didn't work well
        if not segments and text:
            segments.append({
                "speaker": "Unknown",
                "text": text
            })
        
        return {
            "full_text": text,
            "segments": segments
        }
    
    def _add_segment_sentiment(self, parsed_transcript: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add basic sentiment analysis to transcript segments.
        
        Args:
            parsed_transcript: Parsed transcript with segments
            
        Returns:
            Transcript with sentiment scores added
        """
        # Very basic sentiment analysis using keyword matching
        # In a real implementation, you'd use a proper NLP library
        positive_words = [
            "growth", "increase", "profit", "success", "strong", "positive", "gain",
            "opportunity", "improve", "favorable", "exceed", "beat", "happy", "pleased",
            "excited", "confident", "optimistic", "bullish", "robust", "excellent"
        ]
        
        negative_words = [
            "decline", "decrease", "loss", "weak", "negative", "challenge", "difficult",
            "disappointing", "miss", "below", "concern", "risk", "uncertain", "bearish",
            "cautious", "headwind", "struggle", "pressure", "poor", "problem"
        ]
        
        for segment in parsed_transcript["segments"]:
            text = segment["text"].lower()
            
            # Count occurrences of sentiment words
            pos_count = sum(text.count(word) for word in positive_words)
            neg_count = sum(text.count(word) for word in negative_words)
            
            # Calculate simple sentiment score (-1 to 1)
            total = pos_count + neg_count
            score = 0
            if total > 0:
                score = (pos_count - neg_count) / total
            
            # Add sentiment data
            segment["sentiment"] = {
                "score": round(score, 2),
                "positive_count": pos_count,
                "negative_count": neg_count,
                "assessment": "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"
            }
        
        return parsed_transcript
    
    def get_company_news(self, symbol: str, limit: int = 10, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Get company news articles with enhanced metadata.
        
        Args:
            symbol: Company stock symbol
            limit: Maximum number of news items to retrieve
            days_back: How many days back to look for news
            
        Returns:
            List of enhanced news data
        """
        logger.info(f"Getting news for {symbol} (limit: {limit}, days_back: {days_back})")
        
        try:
            # Calculate date range
            today = datetime.now()
            from_date = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
            to_date = today.strftime('%Y-%m-%d')
            
            # Get company news with date range
            news_data = self._make_request(f"stock_news", {
                "tickers": symbol,
                "limit": limit,
                "from": from_date,
                "to": to_date
            })
            
            if not news_data:
                logger.warning(f"No news found for {symbol}")
                return []
            
            # Process and return news items
            processed_news = []
            for item in news_data:
                # Extract keywords from title and text
                keywords = self._extract_keywords(
                    f"{item.get('title', '')} {item.get('text', '')}"
                )
                
                # Create standardized news item
                news_item = {
                    "symbol": symbol,
                    "title": item.get("title", ""),
                    "date": item.get("publishedDate", ""),
                    "source": {
                        "name": item.get("site", ""),
                        "url": item.get("url", "")
                    },
                    "content": item.get("text", ""),
                    "summary": self._generate_summary(item.get("text", "")),
                    "metadata": {
                        "keywords": keywords,
                        "image_url": item.get("image", ""),
                        "relevance_score": self._calculate_relevance_score(item, symbol)
                    }
                }
                processed_news.append(news_item)
            
            # Sort by date (newest first)
            processed_news.sort(key=lambda x: x["date"], reverse=True)
            
            return processed_news
            
        except Exception as e:
            logger.error(f"Error getting news for {symbol}: {e}")
            raise
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from text.
        
        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            List of keywords
        """
        # Basic keyword extraction - in a real implementation, use NLP
        if not text:
            return []
        
        # Convert to lowercase and clean text
        text = text.lower()
        
        # Remove punctuation
        for char in ",.;:!?()[]{}\"'":
            text = text.replace(char, " ")
        
        # Split into words
        words = text.split()
        
        # Remove stop words (very basic list, would be more comprehensive in real implementation)
        stop_words = {
            "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", 
            "in", "on", "at", "to", "for", "with", "by", "about", "from", "of",
            "this", "that", "these", "those", "it", "its", "has", "have", "had",
            "will", "would", "could", "should", "can", "may", "might"
        }
        filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Count frequencies
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in keywords[:max_keywords]]
    
    def _generate_summary(self, text: str, max_length: int = 150) -> str:
        """
        Generate a simple summary of text.
        
        Args:
            text: Text to summarize
            max_length: Maximum summary length
            
        Returns:
            Summary text
        """
        if not text:
            return ""
        
        # Very simple summarization - first sentence or truncation
        # In a real implementation, use proper summarization algorithms
        
        # Try to get first few sentences
        sentences = text.split('.')
        summary = ""
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            if len(summary) + len(sentence) <= max_length:
                summary += sentence.strip() + ". "
            else:
                # If adding another sentence would exceed max length, 
                # truncate the current summary
                if not summary:
                    summary = sentence.strip()[:max_length-3] + "..."
                break
        
        return summary.strip()
    
    def _calculate_relevance_score(self, news_item: Dict[str, Any], symbol: str) -> float:
        """
        Calculate relevance score for a news item.
        
        Args:
            news_item: News item data
            symbol: Company symbol
            
        Returns:
            Relevance score (0-1)
        """
        score = 0.5  # Default score
        
        # Check if symbol is in title (high relevance)
        if symbol.lower() in news_item.get("title", "").lower():
            score += 0.3
        
        # Count mentions of symbol in text
        mentions = news_item.get("text", "").lower().count(symbol.lower())
        if mentions > 0:
            score += min(mentions * 0.05, 0.2)  # Cap at 0.2
        
        # Check if it's from a reputable source (simplified)
        reputable_sources = [
            "bloomberg", "reuters", "wsj", "wall street journal", 
            "cnbc", "financial times", "ft.com", "seeking alpha"
        ]
        if any(source in news_item.get("site", "").lower() for source in reputable_sources):
            score += 0.1
        
        # Cap score at 1.0
        return min(score, 1.0)
    
    def get_sec_filings(
        self,
        symbol: str,
        filing_type: str = "10-K",
        limit: int = 1,
        include_text: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get SEC filings with enhanced metadata and content parsing.
        
        Args:
            symbol: Company stock symbol
            filing_type: Type of filing (10-K, 10-Q, 8-K, etc.)
            limit: Maximum number of filings to retrieve
            include_text: Whether to include filing text
            
        Returns:
            List of filing data
        """
        logger.info(f"Getting {filing_type} filings for {symbol} (limit: {limit})")
        
        try:
            # Get filing list
            filings = self._make_request(f"financial-statement-full-as-reported/{symbol}", {
                "type": filing_type,
                "limit": limit
            })
            
            if not filings:
                logger.warning(f"No {filing_type} filings found for {symbol}")
                return []
            
            # Process filings
            processed_filings = []
            for filing in filings[:limit]:
                filing_data = {
                    "symbol": symbol,
                    "type": filing_type,
                    "date": filing.get("date", ""),
                    "fiscal_year": filing.get("year", ""),
                    "fiscal_period": filing.get("period", ""),
                    "metadata": {
                        "acceptance_datetime": filing.get("acceptedDate", ""),
                        "cik": filing.get("cik", ""),
                        "report_url": filing.get("finalLink", "")
                    }
                }
                
                # Get full text if requested
                if include_text and filing.get("finalLink"):
                    try:
                        filing_data["content"] = self._get_filing_text(filing.get("finalLink"))
                        filing_data["sections"] = self._parse_filing_sections(filing_data["content"], filing_type)
                    except Exception as e:
                        logger.warning(f"Could not get filing text: {e}")
                        filing_data["content"] = ""
                        filing_data["sections"] = {}
                
                processed_filings.append(filing_data)
            
            return processed_filings
            
        except Exception as e:
            logger.error(f"Error getting {filing_type} filings for {symbol}: {e}")
            raise
    
    def _get_filing_text(self, url: str) -> str:
        """
        Get the text content of an SEC filing.
        
        Args:
            url: URL to the filing
            
        Returns:
            Filing text content
        """
        # This is a simplified implementation
        # In practice, you'd need to handle various filing formats and clean the HTML
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            # Very basic HTML cleaning - in practice, use a proper HTML parser
            text = response.text
            
            # Remove HTML tags (very basic)
            # In practice, use BeautifulSoup or similar
            import re
            clean_text = re.sub(r'<[^>]+>', ' ', text)
            clean_text = re.sub(r'\s+', ' ', clean_text)
            
            return clean_text.strip()
            
        except Exception as e:
            logger.warning(f"Error getting filing text: {e}")
            return ""
    
    def _parse_filing_sections(self, text: str, filing_type: str) -> Dict[str, str]:
        """
        Parse sections from SEC filing text.
        
        Args:
            text: Filing text
            filing_type: Type of filing
            
        Returns:
            Dictionary of sections
        """
        # This is a simplified implementation
        # In practice, you'd need a more sophisticated parser
        
        if not text:
            return {}
        
        sections = {}
        
        # Define common section patterns by filing type
        section_patterns = {
            "10-K": [
                ("Business", r"Item\s*1\.?\s*Business"),
                ("Risk Factors", r"Item\s*1A\.?\s*Risk\s*Factors"),
                ("MD&A", r"Item\s*7\.?\s*Management's\s*Discussion\s*and\s*Analysis"),
                ("Financial Statements", r"Item\s*8\.?\s*Financial\s*Statements"),
                ("Controls and Procedures", r"Item\s*9A\.?\s*Controls\s*and\s*Procedures")
            ],
            "10-Q": [
                ("Financial Statements", r"Item\s*1\.?\s*Financial\s*Statements"),
                ("MD&A", r"Item\s*2\.?\s*Management's\s*Discussion\s*and\s*Analysis"),
                ("Risk Factors", r"Item\s*1A\.?\s*Risk\s*Factors"),
                ("Controls and Procedures", r"Item\s*4\.?\s*Controls\s*and\s*Procedures")
            ],
            "8-K": [
                ("Event", r"Item\s*[1-9]\.[\d\.]*\s*[A-Za-z]"),
                ("Financial Statements", r"Item\s*9\.01\.?\s*Financial\s*Statements")
            ]
        }
        
        # Use patterns for the specific filing type, or default to generic
        patterns = section_patterns.get(filing_type, [
            ("Full Text", r"^")  # Just capture everything
        ])
        
        import re
        
        # Extract sections based on patterns
        for section_name, pattern in patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                for i, match in enumerate(matches):
                    start_pos = match.start()
                    
                    # Find the end of this section (start of next section or end of text)
                    end_pos = len(text)
                    if i < len(matches) - 1:
                        end_pos = matches[i+1].start()
                    
                    section_text = text[start_pos:end_pos].strip()
                    if section_text:
                        sections[section_name] = section_text
        
        return sections
    
    def save_company_dataset(
        self,
        symbol: str,
        include_profile: bool = True,
        include_metrics: bool = True,
        include_financials: bool = True,
        include_transcripts: bool = True,
        include_news: bool = True,
        include_filings: bool = True,
        output_format: str = "json",
        output_file: Optional[str] = None
    ) -> str:
        """
        Generate and save a comprehensive company dataset.
        
        Args:
            symbol: Company stock symbol
            include_profile: Whether to include company profile
            include_metrics: Whether to include financial metrics
            include_financials: Whether to include financial statements
            include_transcripts: Whether to include earnings call transcripts
            include_news: Whether to include company news
            include_filings: Whether to include SEC filings
            output_format: Output format ("json", "csv", or "parquet")
            output_file: Custom output file path
            
        Returns:
            Path to saved file
        """
        logger.info(f"Generating comprehensive dataset for {symbol}")
        
        try:
            company_data = {
                "symbol": symbol,
                "generated_at": datetime.now().isoformat(),
                "data_sources": []
            }
            
            # Get company profile
            if include_profile:
                logger.info(f"Including profile for {symbol}")
                company_data["profile"] = self.get_company_profile(symbol)
                company_data["data_sources"].append("profile")
            
            # Get financial metrics
            if include_metrics:
                logger.info(f"Including metrics for {symbol}")
                company_data["metrics"] = self.get_company_metrics(symbol)
                company_data["data_sources"].append("metrics")
            
            # Get financial statements
            if include_financials:
                logger.info(f"Including financial statements for {symbol}")
                company_data["financials"] = {
                    "income_statements": self.get_financial_statements(symbol, "income", "annual", 5),
                    "balance_sheets": self.get_financial_statements(symbol, "balance-sheet", "annual", 5),
                    "cash_flow_statements": self.get_financial_statements(symbol, "cash-flow", "annual", 5),
                    "quarterly_income": self.get_financial_statements(symbol, "income", "quarter", 4)
                }
                company_data["data_sources"].append("financials")
            
            # Get earnings call transcripts
            if include_transcripts:
                logger.info(f"Including earnings call transcripts for {symbol}")
                company_data["earnings_calls"] = self.get_earnings_call_transcripts(
                    symbol, limit=2, parse_speakers=True, include_sentiment=True
                )
                company_data["data_sources"].append("earnings_calls")
            
            # Get company news
            if include_news:
                logger.info(f"Including news for {symbol}")
                company_data["news"] = self.get_company_news(symbol, limit=10)
                company_data["data_sources"].append("news")
            
            # Get SEC filings
            if include_filings:
                logger.info(f"Including SEC filings for {symbol}")
                company_data["filings"] = {
                    "annual": self.get_sec_filings(symbol, "10-K", 1, include_text=True),
                    "quarterly": self.get_sec_filings(symbol, "10-Q", 2, include_text=False)
                }
                company_data["data_sources"].append("filings")
            
            # Determine output file path
            if not output_file:
                file_name = f"{symbol.lower()}_comprehensive_data"
                if output_format == "json":
                    file_name += ".json"
                elif output_format == "csv":
                    file_name += ".csv"
                elif output_format == "parquet":
                    file_name += ".parquet"
                else:
                    raise ValueError(f"Unsupported output format: {output_format}")
                
                output_file = str(self.data_dir / file_name)
            
            # Save data in the specified format
            if output_format == "json":
                self._save_json(company_data, output_file)
            elif output_format == "csv":
                self._save_csv(company_data, output_file)
            elif output_format == "parquet":
                self._save_parquet(company_data, output_file)
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
            
            logger.info(f"Saved company dataset: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error generating dataset for {symbol}: {e}")
            raise
    
    def _save_json(self, data: Dict[str, Any], file_path: str) -> None:
        """
        Save data to a JSON file.
        
        Args:
            data: Data to save
            file_path: Output file path
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_csv(self, data: Dict[str, Any], file_path: str) -> None:
        """
        Save data to CSV files (one per data type).
        
        Args:
            data: Data to save
            file_path: Base output file path
        """
        base_path = Path(file_path).with_suffix('')
        base_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a metadata file with links to all CSVs
        metadata = {
            "symbol": data["symbol"],
            "generated_at": data["generated_at"],
            "data_sources": data["data_sources"],
            "files": {}
        }
        
        # Save each data type to its own CSV
        for key in data["data_sources"]:
            if key not in data:
                continue
                
            if key == "profile":
                # Flatten profile data
                df = pd.json_normalize(data["profile"])
                csv_path = f"{base_path}_{key}.csv"
                df.to_csv(csv_path, index=False)
                metadata["files"][key] = csv_path
                
            elif key == "metrics":
                # Save current metrics
                df_current = pd.json_normalize(data["metrics"]["current"])
                csv_path = f"{base_path}_{key}_current.csv"
                df_current.to_csv(csv_path, index=False)
                metadata["files"][f"{key}_current"] = csv_path
                
                # Save historical metrics
                df_hist = pd.json_normalize(data["metrics"]["historical"])
                csv_path = f"{base_path}_{key}_historical.csv"
                df_hist.to_csv(csv_path, index=False)
                metadata["files"][f"{key}_historical"] = csv_path
                
            elif key == "financials":
                # Save each statement type
                for stmt_type, statements in data["financials"].items():
                    if not statements:
                        continue
                        
                    df = pd.json_normalize(statements)
                    csv_path = f"{base_path}_{stmt_type}.csv"
                    df.to_csv(csv_path, index=False)
                    metadata["files"][stmt_type] = csv_path
                    
            elif key == "earnings_calls":
                # Save transcript metadata
                transcript_meta = []
                for i, call in enumerate(data["earnings_calls"]):
                    meta = {
                        "symbol": call["symbol"],
                        "title": call["title"],
                        "date": call["date"],
                        "quarter": call["fiscal_period"]["quarter"],
                        "year": call["fiscal_period"]["year"],
                        "content_file": f"{base_path}_transcript_{i+1}.txt"
                    }
                    transcript_meta.append(meta)
                    
                    # Save full transcript text to separate file
                    with open(meta["content_file"], 'w') as f:
                        f.write(call["content"]["full_text"])
                
                # Save transcript metadata
                if transcript_meta:
                    df = pd.DataFrame(transcript_meta)
                    csv_path = f"{base_path}_{key}_meta.csv"
                    df.to_csv(csv_path, index=False)
                    metadata["files"][f"{key}_meta"] = csv_path
                    
            elif key == "news":
                # Extract basic news info
                news_data = []
                for item in data["news"]:
                    news_data.append({
                        "symbol": item["symbol"],
                        "title": item["title"],
                        "date": item["date"],
                        "source": item["source"]["name"],
                        "url": item["source"]["url"],
                        "summary": item["summary"],
                        "keywords": ", ".join(item["metadata"]["keywords"]),
                        "relevance_score": item["metadata"]["relevance_score"]
                    })
                
                if news_data:
                    df = pd.DataFrame(news_data)
                    csv_path = f"{base_path}_{key}.csv"
                    df.to_csv(csv_path, index=False)
                    metadata["files"][key] = csv_path
                    
            elif key == "filings":
                # Save filing metadata
                filing_data = []
                for filing_type, filings in data["filings"].items():
                    for filing in filings:
                        filing_data.append({
                            "symbol": filing["symbol"],
                            "type": filing["type"],
                            "date": filing["date"],
                            "fiscal_year": filing["fiscal_year"],
                            "fiscal_period": filing["fiscal_period"],
                            "url": filing["metadata"]["report_url"]
                        })
                
                if filing_data:
                    df = pd.DataFrame(filing_data)
                    csv_path = f"{base_path}_{key}.csv"
                    df.to_csv(csv_path, index=False)
                    metadata["files"][key] = csv_path
        
        # Save metadata file
        with open(f"{base_path}_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _save_parquet(self, data: Dict[str, Any], file_path: str) -> None:
        """
        Save data to a Parquet file.
        
        Args:
            data: Data to save
            file_path: Output file path
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to DataFrame
        try:
            # Create a flattened version of the data for Parquet
            flat_data = {
                "symbol": data["symbol"],
                "generated_at": data["generated_at"],
                "data_sources": ",".join(data["data_sources"])
            }
            
            # Add flattened profile data if available
            if "profile" in data:
                profile = data["profile"]
                flat_data.update({
                    "profile_name": profile.get("name", ""),
                    "profile_industry": profile.get("industry", ""),
                    "profile_sector": profile.get("sector", ""),
                    "profile_employees": profile.get("employees", 0),
                    "profile_market_cap": profile.get("metrics", {}).get("marketCap", 0)
                })
            
            # Add some key metrics if available
            if "metrics" in data and "current" in data["metrics"]:
                metrics = data["metrics"]["current"]
                for category, values in metrics.items():
                    if isinstance(values, dict):
                        for key, value in values.items():
                            flat_data[f"metric_{category}_{key}"] = value
            
            # Add financial summary if available
            if "financials" in data:
                financials = data["financials"]
                
                # Get the most recent income statement
                if "income_statements" in financials and financials["income_statements"]:
                    latest = financials["income_statements"][0]
                    flat_data.update({
                        "latest_revenue": latest.get("revenue", {}).get("total", 0),
                        "latest_gross_profit": latest.get("revenue", {}).get("grossProfit", 0),
                        "latest_operating_income": latest.get("operatingIncome", 0),
                        "latest_net_income": latest.get("netIncome", 0),
                        "latest_eps_basic": latest.get("eps", {}).get("basic", 0)
                    })
            
            # Create DataFrame and save as Parquet
            df = pd.DataFrame([flat_data])
            df.to_parquet(path, index=False)
            
            logger.info(f"Saved data to Parquet: {path}")
            
        except Exception as e:
            logger.error(f"Error saving to Parquet: {e}")
            # Fall back to JSON if Parquet fails
            json_path = path.with_suffix('.json')
            logger.warning(f"Falling back to JSON: {json_path}")
            self._save_json(data, str(json_path))
    
    def create_multi_company_dataset(
        self,
        symbols: List[str],
        dataset_type: str = "comparison",
        content_types: List[str] = None,
        output_file: Optional[str] = None
    ) -> str:
        """
        Create a dataset combining data from multiple companies.
        
        Args:
            symbols: List of company symbols
            dataset_type: Type of dataset ("comparison", "sector", "custom")
            content_types: Types of content to include
            output_file: Output file path
            
        Returns:
            Path to saved file
        """
        logger.info(f"Creating {dataset_type} dataset for: {symbols}")
        
        # Default output file
        if not output_file:
            symbols_str = '_'.join(symbols).lower()
            output_file = str(self.data_dir / f"{dataset_type}_{symbols_str}.json")
        
        # Default content types based on dataset type
        if not content_types:
            if dataset_type == "comparison":
                content_types = ["profile", "metrics", "financials"]
            elif dataset_type == "sector":
                content_types = ["profile", "metrics"]
            else:
                content_types = ["profile"]
        
        # Collect data for each company
        company_data = {}
        for symbol in symbols:
            company_data[symbol] = {}
            
            # Get requested content types
            if "profile" in content_types:
                company_data[symbol]["profile"] = self.get_company_profile(symbol)
            
            if "metrics" in content_types:
                company_data[symbol]["metrics"] = self.get_company_metrics(symbol)
            
            if "financials" in content_types:
                company_data[symbol]["financials"] = {
                    "income": self.get_financial_statements(symbol, "income", "annual", 3),
                    "balance": self.get_financial_statements(symbol, "balance-sheet", "annual", 3),
                    "cash_flow": self.get_financial_statements(symbol, "cash-flow", "annual", 3)
                }
            
            if "transcripts" in content_types:
                company_data[symbol]["transcripts"] = self.get_earnings_call_transcripts(
                    symbol, limit=1, parse_speakers=True
                )
            
            if "news" in content_types:
                company_data[symbol]["news"] = self.get_company_news(symbol, limit=5)
            
            if "filings" in content_types:
                company_data[symbol]["filings"] = self.get_sec_filings(
                    symbol, "10-K", 1, include_text=False
                )
        
        # Create comparative metrics if this is a comparison dataset
        comparative_analysis = {}
        if dataset_type == "comparison" and "metrics" in content_types:
            comparative_analysis = self._generate_comparative_analysis(company_data)
        
        # Create the final dataset
        dataset = {
            "type": dataset_type,
            "symbols": symbols,
            "content_types": content_types,
            "generated_at": datetime.now().isoformat(),
            "companies": company_data,
            "comparative_analysis": comparative_analysis
        }
        
        # Save to file
        self._save_json(dataset, output_file)
        
        logger.info(f"Saved multi-company dataset: {output_file}")
        return output_file
    
    def _generate_comparative_analysis(self, company_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comparative analysis for multiple companies.
        
        Args:
            company_data: Data for multiple companies
            
        Returns:
            Comparative analysis
        """
        analysis = {
            "metrics_comparison": {},
            "financial_comparison": {},
            "rankings": {},
            "averages": {}
        }
        
        # Extract key metrics for comparison
        metrics_to_compare = [
            # Valuation metrics
            ("valuation", "peRatio"),
            ("valuation", "pbRatio"),
            ("valuation", "evToRevenue"),
            
            # Profitability metrics
            ("profitability", "roe"),
            ("profitability", "grossMargin"),
            ("profitability", "netMargin"),
            
            # Liquidity and solvency
            ("liquidity", "currentRatio"),
            ("solvency", "debtToEquity"),
            
            # Cash flow
            ("cashFlow", "fcfYield")
        ]
        
        # Collect metrics
        metrics_data = {}
        for symbol, data in company_data.items():
            if "metrics" in data and "current" in data["metrics"]:
                metrics = data["metrics"]["current"]
                metrics_data[symbol] = {}
                
                for category, key in metrics_to_compare:
                    if category in metrics and isinstance(metrics[category], dict):
                        value = metrics[category].get(key, 0)
                        metrics_data[symbol][f"{category}_{key}"] = value
        
        # Create comparison tables
        for category, key in metrics_to_compare:
            metric_key = f"{category}_{key}"
            
            # Skip if we don't have this metric for any company
            if not any(metric_key in company_metrics for company_metrics in metrics_data.values()):
                continue
            
            # Collect values for each company
            values = {}
            for symbol, metrics in metrics_data.items():
                if metric_key in metrics:
                    values[symbol] = metrics[metric_key]
            
            # Skip if we have no values
            if not values:
                continue
            
            # Calculate statistics
            avg_value = sum(values.values()) / len(values) if values else 0
            min_value = min(values.values()) if values else 0
            max_value = max(values.values()) if values else 0
            
            # Create rankings
            ranked_symbols = sorted(values.keys(), key=lambda s: values[s], reverse=True)
            
            # Add to analysis
            analysis["metrics_comparison"][metric_key] = {
                "values": values,
                "average": avg_value,
                "min": min_value,
                "max": max_value
            }
            
            analysis["rankings"][metric_key] = ranked_symbols
            analysis["averages"][metric_key] = avg_value
        
        # Financial comparison (if available)
        financial_metrics = [
            "revenue_total",
            "grossProfit",
            "operatingIncome",
            "netIncome"
        ]
        
        financial_data = {}
        for symbol, data in company_data.items():
            if "financials" in data and "income" in data["financials"] and data["financials"]["income"]:
                latest = data["financials"]["income"][0]
                financial_data[symbol] = {
                    "revenue_total": latest.get("revenue", {}).get("total", 0),
                    "grossProfit": latest.get("revenue", {}).get("grossProfit", 0),
                    "operatingIncome": latest.get("operatingIncome", 0),
                    "netIncome": latest.get("netIncome", 0)
                }
        
        # Create comparison for financial metrics
        for metric in financial_metrics:
            values = {}
            for symbol, finances in financial_data.items():
                values[symbol] = finances.get(metric, 0)
            
            if values:
                avg_value = sum(values.values()) / len(values)
                ranked_symbols = sorted(values.keys(), key=lambda s: values[s], reverse=True)
                
                analysis["financial_comparison"][metric] = {
                    "values": values,
                    "average": avg_value
                }
                
                analysis["rankings"][metric] = ranked_symbols
        
        return analysis

    def create_market_overview_dataset(
        self, 
        sector: Optional[str] = None, 
        market_cap_min: Optional[float] = None,
        limit: int = 20
    ) -> str:
        """
        Create a market overview dataset for a sector or the entire market.
        
        Args:
            sector: Optional sector to filter by
            market_cap_min: Minimum market cap (in billions)
            limit: Maximum number of companies to include
            
        Returns:
            Path to saved file
        """
        logger.info(f"Creating market overview dataset for {'all sectors' if not sector else sector}")
        
        try:
            # Get list of companies
            stocks = self._make_request("stock/list")
            
            # Filter by sector and market cap if specified
            filtered_stocks = []
            for stock in stocks:
                # Skip if no symbol
                if not stock.get("symbol"):
                    continue
                
                # Get company profile to check sector and market cap
                try:
                    profile = self.get_company_profile(stock["symbol"])
                    
                    # Skip if no profile
                    if not profile:
                        continue
                    
                    # Filter by sector if specified
                    if sector and profile.get("sector") != sector:
                        continue
                    
                    # Filter by market cap if specified
                    market_cap = profile.get("metrics", {}).get("marketCap", 0)
                    if market_cap_min and (market_cap < market_cap_min * 1e9):
                        continue
                    
                    # Add to filtered list
                    filtered_stocks.append({
                        "symbol": profile.get("symbol"),
                        "name": profile.get("name"),
                        "sector": profile.get("sector"),
                        "industry": profile.get("industry"),
                        "marketCap": market_cap
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing {stock.get('symbol')}: {e}")
                
                # Limit to specified number of companies
                if len(filtered_stocks) >= limit:
                    break
            
            # Sort by market cap
            filtered_stocks.sort(key=lambda x: x.get("marketCap", 0), reverse=True)
            
            # Limit to specified number of companies
            filtered_stocks = filtered_stocks[:limit]
            
            # Get basic metrics for each company
            symbols = [stock["symbol"] for stock in filtered_stocks]
            all_metrics = {}
            
            for symbol in symbols:
                try:
                    metrics = self.get_company_metrics(symbol)
                    all_metrics[symbol] = metrics
                except Exception as e:
                    logger.warning(f"Error getting metrics for {symbol}: {e}")
            
            # Create the dataset
            dataset = {
                "type": "market_overview",
                "sector": sector,
                "market_cap_min": market_cap_min,
                "generated_at": datetime.now().isoformat(),
                "companies": filtered_stocks,
                "metrics": all_metrics,
                "sector_analysis": self._generate_sector_analysis(filtered_stocks, all_metrics)
            }
            
            # Save to file
            sector_str = sector.lower().replace(" ", "_") if sector else "all_sectors"
            output_file = str(self.data_dir / f"market_overview_{sector_str}.json")
            self._save_json(dataset, output_file)
            
            logger.info(f"Saved market overview dataset: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error creating market overview dataset: {e}")
            raise
    
    def _generate_sector_analysis(
        self,
        companies: List[Dict[str, Any]],
        metrics: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate sector analysis for market overview.
        
        Args:
            companies: List of companies
            metrics: Metrics for each company
            
        Returns:
            Sector analysis
        """
        analysis = {
            "industry_breakdown": {},
            "market_cap_distribution": {
                "ranges": {
                    "mega_cap": {"min": 200e9, "count": 0, "total": 0},
                    "large_cap": {"min": 10e9, "count": 0, "total": 0},
                    "mid_cap": {"min": 2e9, "count": 0, "total": 0},
                    "small_cap": {"min": 300e6, "count": 0, "total": 0},
                    "micro_cap": {"min": 0, "count": 0, "total": 0}
                },
                "total": 0
            },
            "average_metrics": {
                "pe_ratio": 0,
                "pb_ratio": 0,
                "dividend_yield": 0,
                "debt_to_equity": 0,
                "roe": 0,
                "net_margin": 0
            }
        }
        
        # Industry breakdown
        for company in companies:
            industry = company.get("industry", "Unknown")
            if industry not in analysis["industry_breakdown"]:
                analysis["industry_breakdown"][industry] = {
                    "count": 0,
                    "market_cap": 0,
                    "companies": []
                }
            
            analysis["industry_breakdown"][industry]["count"] += 1
            analysis["industry_breakdown"][industry]["market_cap"] += company.get("marketCap", 0)
            analysis["industry_breakdown"][industry]["companies"].append(company.get("symbol"))
        
        # Market cap distribution
        for company in companies:
            market_cap = company.get("marketCap", 0)
            analysis["market_cap_distribution"]["total"] += market_cap
            
            # Categorize by market cap
            if market_cap >= 200e9:
                category = "mega_cap"
            elif market_cap >= 10e9:
                category = "large_cap"
            elif market_cap >= 2e9:
                category = "mid_cap"
            elif market_cap >= 300e6:
                category = "small_cap"
            else:
                category = "micro_cap"
            
            analysis["market_cap_distribution"]["ranges"][category]["count"] += 1
            analysis["market_cap_distribution"]["ranges"][category]["total"] += market_cap
        
        # Calculate average metrics
        metric_counts = {
            "pe_ratio": 0,
            "pb_ratio": 0,
            "dividend_yield": 0,
            "debt_to_equity": 0,
            "roe": 0,
            "net_margin": 0
        }
        
        for symbol, company_metrics in metrics.items():
            current = company_metrics.get("current", {})
            
            # PE ratio
            if "valuation" in current and "peRatio" in current["valuation"]:
                pe = current["valuation"]["peRatio"]
                if pe and pe > 0 and pe < 1000:  # Filter outliers
                    analysis["average_metrics"]["pe_ratio"] += pe
                    metric_counts["pe_ratio"] += 1
            
            # PB ratio
            if "valuation" in current and "pbRatio" in current["valuation"]:
                pb = current["valuation"]["pbRatio"]
                if pb and pb > 0 and pb < 100:  # Filter outliers
                    analysis["average_metrics"]["pb_ratio"] += pb
                    metric_counts["pb_ratio"] += 1
            
            # Dividend yield
            if "ratios" in current and "dividendYield" in current["ratios"]:
                div_yield = current["ratios"]["dividendYield"]
                if div_yield and div_yield >= 0 and div_yield < 20:  # Filter outliers
                    analysis["average_metrics"]["dividend_yield"] += div_yield
                    metric_counts["dividend_yield"] += 1
            
            # Debt to equity
            if "solvency" in current and "debtToEquity" in current["solvency"]:
                de = current["solvency"]["debtToEquity"]
                if de and de >= 0 and de < 10:  # Filter outliers
                    analysis["average_metrics"]["debt_to_equity"] += de
                    metric_counts["debt_to_equity"] += 1
            
            # ROE
            if "profitability" in current and "roe" in current["profitability"]:
                roe = current["profitability"]["roe"]
                if roe and roe > -1 and roe < 1:  # Filter outliers
                    analysis["average_metrics"]["roe"] += roe
                    metric_counts["roe"] += 1
            
            # Net margin
            if "profitability" in current and "netMargin" in current["profitability"]:
                net_margin = current["profitability"]["netMargin"]
                if net_margin and net_margin > -1 and net_margin < 1:  # Filter outliers
                    analysis["average_metrics"]["net_margin"] += net_margin
                    metric_counts["net_margin"] += 1
        
        # Calculate averages
        for metric, total in analysis["average_metrics"].items():
            count = metric_counts.get(metric, 0)
            analysis["average_metrics"][metric] = total / count if count > 0 else 0
        
        return analysis