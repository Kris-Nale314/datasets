{
  "dataset_info": {
    "name": "dataset_name",
    "version": "0.1.0",
    "description": "A brief description of the dataset",
    "created_by": "Kris",
    "created_at": "YYYY-MM-DD",
    "last_updated": "YYYY-MM-DD",
    "license": "MIT",
    "tags": ["tag1", "tag2", "tag3"],
    "category": "financial|nlp|vision|multimodal|other"
  },
  "source_info": {
    "type": "created|curated|downloaded",
    "origin": "Description of where the data came from",
    "url": "https://example.com/source-url",
    "citation": "Cite the source if applicable",
    "collection_method": "API|Web Scraping|Manual Collection|Generated",
    "collection_date_range": {
      "start": "YYYY-MM-DD",
      "end": "YYYY-MM-DD"
    }
  },
  "content_info": {
    "format": "JSON|CSV|Parquet|Other",
    "encoding": "UTF-8",
    "size_bytes": 0,
    "record_count": 0,
    "file_count": 1,
    "languages": ["en"],
    "fields": [
      {
        "name": "field_name",
        "description": "Description of what this field contains",
        "type": "string|number|boolean|object|array",
        "required": true,
        "example": "Example value"
      }
    ],
    "schema_version": "1.0"
  },
  "quality_info": {
    "completeness": 100,
    "accuracy": 100,
    "consistency": 100,
    "timeliness": 100,
    "known_issues": [
      "Description of any known issues with the dataset"
    ],
    "validation_method": "Description of how the dataset was validated",
    "validation_results": "Summary of validation results"
  },
  "usage_info": {
    "intended_use": "Description of what this dataset is intended to be used for",
    "limitations": [
      "Description of any limitations or biases in the dataset"
    ],
    "ethical_considerations": [
      "Description of any ethical considerations when using this dataset"
    ],
    "recommended_preprocessing": [
      "Description of recommended preprocessing steps"
    ],
    "example_code": "Path to example code for using this dataset",
    "related_datasets": [
      "Path to related datasets in the repository"
    ]
  },
  "maintenance_info": {
    "update_frequency": "never|daily|weekly|monthly|yearly|as-needed",
    "last_validation": "YYYY-MM-DD",
    "maintainer": "Kris",
    "changelog": [
      {
        "version": "0.1.0",
        "date": "YYYY-MM-DD",
        "description": "Initial version"
      }
    ]
  }
}