"""Tests for core QC Engine functionality."""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch

from mri_qc_intelligence.core import QCEngine


class TestQCEngine:
    """Test cases for QCEngine class."""
    
    def test_init(self):
        """Test QCEngine initialization."""
        engine = QCEngine()
        assert engine is not None
        assert hasattr(engine, 'data_loader')
        assert hasattr(engine, 'metrics')
        assert hasattr(engine, 'scorer')
        
    def test_init_with_config(self, tmp_path):
        """Test QCEngine initialization with config file."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("test: value")
        
        # Should not fail even with non-existent config
        engine = QCEngine(config_path=config_file)
        assert engine is not None
        
    @patch('mri_qc_intelligence.core.BIDSLoader')
    def test_load_bids_dataset(self, mock_loader):
        """Test BIDS dataset loading."""
        # Mock the BIDSLoader
        mock_loader_instance = Mock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load.return_value = {
            'subjects': ['sub-01', 'sub-02'],
            'modalities': ['T1w', 'bold']
        }
        
        engine = QCEngine()
        result = engine.load_bids_dataset("/fake/path")
        
        assert 'subjects' in result
        assert 'modalities' in result
        mock_loader_instance.load.assert_called_once_with("/fake/path")
        
    def test_analyze_empty_dataset(self):
        """Test analysis with empty dataset."""
        engine = QCEngine()
        result = engine.analyze({})
        
        # Should return empty results without crashing
        assert isinstance(result, dict)
        
    def test_analyze_with_modalities(self):
        """Test analysis with specific modalities."""
        engine = QCEngine()
        dataset = {'subjects': ['sub-01'], 'modalities': ['T1w']}
        
        result = engine.analyze(dataset, modalities=['T1w'])
        assert isinstance(result, dict)
        
    @patch('mri_qc_intelligence.core.ReportGenerator')
    def test_generate_report(self, mock_report_gen):
        """Test report generation."""
        mock_gen_instance = Mock()
        mock_report_gen.return_value = mock_gen_instance
        
        engine = QCEngine()
        engine.generate_report({}, "/fake/output")
        
        mock_gen_instance.generate.assert_called_once_with({}, "/fake/output")