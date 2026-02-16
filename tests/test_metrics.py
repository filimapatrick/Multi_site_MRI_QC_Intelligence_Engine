"""Tests for QC metrics computation."""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from mri_qc_intelligence.metrics import T1QCMetrics, FMRIQCMetrics, DWIQCMetrics
from mri_qc_intelligence.metrics.base import BaseQCMetrics


class TestBaseQCMetrics:
    """Test cases for BaseQCMetrics class."""
    
    def test_compute_snr(self):
        """Test SNR computation."""
        # Create a concrete implementation for testing
        class TestMetrics(BaseQCMetrics):
            def compute(self, image_path, **kwargs):
                return {}
                
        base_metrics = TestMetrics()
        
        signal = np.array([100, 110, 90, 105, 95])
        noise = np.array([5, 3, 7, 4, 6])
        
        snr = base_metrics.compute_snr(signal, noise)
        
        expected_snr = np.mean(signal) / np.std(noise)
        assert abs(snr - expected_snr) < 1e-10
        
    def test_compute_cnr(self):
        """Test CNR computation."""
        # Create a concrete implementation for testing
        class TestMetrics(BaseQCMetrics):
            def compute(self, image_path, **kwargs):
                return {}
                
        base_metrics = TestMetrics()
        
        tissue1 = np.array([100, 110, 90])
        tissue2 = np.array([150, 160, 140])
        noise = np.array([5, 3, 7, 4, 6])
        
        cnr = base_metrics.compute_cnr(tissue1, tissue2, noise)
        
        contrast = abs(np.mean(tissue1) - np.mean(tissue2))
        noise_std = np.std(noise)
        expected_cnr = contrast / noise_std
        
        assert abs(cnr - expected_cnr) < 1e-10
        
    def test_snr_zero_noise(self):
        """Test SNR with zero noise (should return inf)."""
        # Create a concrete implementation for testing
        class TestMetrics(BaseQCMetrics):
            def compute(self, image_path, **kwargs):
                return {}
                
        base_metrics = TestMetrics()
        
        signal = np.array([100, 100, 100])
        noise = np.array([0, 0, 0])
        
        snr = base_metrics.compute_snr(signal, noise)
        assert snr == np.inf


class TestT1QCMetrics:
    """Test cases for T1QCMetrics class."""
    
    def test_init(self):
        """Test T1QCMetrics initialization."""
        metrics = T1QCMetrics()
        assert isinstance(metrics, BaseQCMetrics)
        
    @patch('nibabel.load')
    def test_compute_placeholder(self, mock_nib_load):
        """Test T1 metrics computation (placeholder test)."""
        # Mock nibabel image
        mock_img = Mock()
        mock_data = np.random.rand(64, 64, 32)  # 3D brain-like data
        mock_img.get_fdata.return_value = mock_data
        mock_nib_load.return_value = mock_img
        
        metrics = T1QCMetrics()
        
        # Should not crash with mock data
        try:
            result = metrics.compute("/fake/path/t1.nii.gz")
            assert isinstance(result, dict)
        except Exception as e:
            # Expected for mock data - just ensure it's a reasonable error
            assert "mask" in str(e).lower() or "brain" in str(e).lower() or "index" in str(e).lower()


class TestFMRIQCMetrics:
    """Test cases for FMRIQCMetrics class."""
    
    def test_init(self):
        """Test FMRIQCMetrics initialization."""
        metrics = FMRIQCMetrics()
        assert isinstance(metrics, BaseQCMetrics)
        
    def test_compute_framewise_displacement(self):
        """Test framewise displacement computation."""
        metrics = FMRIQCMetrics()
        
        # Mock motion parameters (6 columns: x, y, z, pitch, yaw, roll)
        motion_params = np.array([
            [0, 0, 0, 0, 0, 0],
            [0.1, 0.2, 0.1, 0.01, 0.01, 0.01],
            [0.2, 0.3, 0.2, 0.02, 0.02, 0.02]
        ])
        
        fd_mean = metrics._compute_framewise_displacement(motion_params)
        assert fd_mean > 0
        assert isinstance(fd_mean, float)
        
    def test_invalid_motion_params(self):
        """Test with invalid motion parameters."""
        metrics = FMRIQCMetrics()
        
        # Wrong number of columns
        invalid_params = np.array([[1, 2, 3]])  # Only 3 columns
        
        with pytest.raises(ValueError, match="Motion parameters should have 6 columns"):
            metrics._compute_framewise_displacement(invalid_params)


class TestDWIQCMetrics:
    """Test cases for DWIQCMetrics class."""
    
    def test_init(self):
        """Test DWIQCMetrics initialization."""
        metrics = DWIQCMetrics()
        assert isinstance(metrics, BaseQCMetrics)
        
    def test_validate_bvalues_valid(self):
        """Test b-values validation with valid values."""
        metrics = DWIQCMetrics()
        
        valid_bvals = np.array([0, 0, 1000, 1000, 2000, 2000])
        score = metrics._validate_bvalues(valid_bvals)
        
        assert 0 <= score <= 1
        assert score > 0  # Should be positive for valid b-values
        
    def test_validate_bvalues_invalid(self):
        """Test b-values validation with invalid values."""
        metrics = DWIQCMetrics()
        
        # Negative b-values
        invalid_bvals = np.array([-100, 1000, 2000])
        score = metrics._validate_bvalues(invalid_bvals)
        
        assert score == 0.0
        
        # Extremely high b-values
        invalid_bvals = np.array([0, 1000, 15000])
        score = metrics._validate_bvalues(invalid_bvals)
        
        assert score == 0.0
        
    def test_assess_shell_coverage(self):
        """Test b-value shell coverage assessment."""
        metrics = DWIQCMetrics()
        
        bvals = np.array([0, 0, 0, 1000, 1000, 1000, 2000, 2000])
        coverage = metrics._assess_shell_coverage(bvals)
        
        assert isinstance(coverage, dict)
        assert 'shell_0' in coverage
        assert 'shell_1000' in coverage
        assert 'shell_2000' in coverage
        assert coverage['shell_0'] == 3
        assert coverage['shell_1000'] == 3
        assert coverage['shell_2000'] == 2