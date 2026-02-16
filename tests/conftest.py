"""Pytest configuration and fixtures for MRI QC tests."""

import pytest
import numpy as np
import tempfile
from pathlib import Path
from unittest.mock import Mock


@pytest.fixture
def sample_bids_dataset():
    """Sample BIDS dataset structure for testing."""
    return {
        'bids_dir': '/fake/bids/dataset',
        'subjects': ['sub-01', 'sub-02', 'sub-03'],
        'sessions': ['ses-baseline', 'ses-followup'],
        'modalities': ['T1w', 'bold', 'dwi'],
        'metadata': {
            'acquisition_params': {},
            'scanner_info': {},
            'participants': None
        }
    }


@pytest.fixture
def sample_t1_metrics():
    """Sample T1w QC metrics for testing."""
    return {
        'snr': 25.5,
        'cnr_gm_wm': 15.2,
        'inu': 0.15,
        'background_noise': 3.2,
        'brain_mask_quality': 0.92,
        'artifact_score': 0.85
    }


@pytest.fixture
def sample_fmri_metrics():
    """Sample fMRI QC metrics for testing."""
    return {
        'tsnr_mean': 65.3,
        'dvars': np.array([12.5, 15.2, 13.8]),
        'fd_mean': 0.25,
        'signal_drift': 0.02,
        'motion_spikes': 3,
        'temporal_smoothness': 0.75
    }


@pytest.fixture
def sample_dwi_metrics():
    """Sample DWI QC metrics for testing."""
    return {
        'snr_b0': 22.1,
        'signal_dropout_slices': 2,
        'volume_outliers': 1,
        'motion_estimate': 0.15,
        'direction_coverage': 0.88,
        'signal_intensity_consistency': 0.92
    }


@pytest.fixture
def sample_dataset_metrics(sample_t1_metrics, sample_fmri_metrics, sample_dwi_metrics):
    """Sample complete dataset metrics for testing."""
    return {
        'sub-01': {
            'T1w': sample_t1_metrics,
            'bold': sample_fmri_metrics,
            'dwi': sample_dwi_metrics
        },
        'sub-02': {
            'T1w': {k: v * 0.9 for k, v in sample_t1_metrics.items()},
            'bold': {k: (v * 1.1 if isinstance(v, (int, float)) else v) 
                    for k, v in sample_fmri_metrics.items()},
            'dwi': {k: v * 0.95 for k, v in sample_dwi_metrics.items() 
                   if isinstance(v, (int, float))}
        }
    }


@pytest.fixture
def sample_qc_scores():
    """Sample QC scores for testing."""
    return {
        'subject_scores': {
            'sub-01': {
                'T1w': {
                    'composite_score': 78.5,
                    'quality_rating': 'Pass',
                    'individual_scores': {}
                },
                'bold': {
                    'composite_score': 72.3,
                    'quality_rating': 'Warning',
                    'individual_scores': {}
                },
                'overall': {
                    'composite_score': 75.4,
                    'quality_rating': 'Pass'
                }
            }
        },
        'dataset_summary': {
            'total_subjects': 2,
            'modality_stats': {},
            'quality_distribution': {'Pass': 1, 'Warning': 1, 'Fail': 0}
        }
    }


@pytest.fixture
def temp_output_dir():
    """Temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def mock_nifti_image():
    """Mock NIfTI image for testing."""
    mock_img = Mock()
    
    # 3D brain-like data
    brain_data = np.random.rand(64, 64, 32) * 100
    # Add some structure
    brain_data[16:48, 16:48, 8:24] += 50  # "brain" region
    
    mock_img.get_fdata.return_value = brain_data
    mock_img.shape = brain_data.shape
    
    return mock_img


@pytest.fixture
def mock_4d_fmri_image():
    """Mock 4D fMRI image for testing."""
    mock_img = Mock()
    
    # 4D fMRI-like data (64x64x32x100 timepoints)
    fmri_data = np.random.rand(64, 64, 32, 100) * 100
    # Add temporal structure
    for t in range(100):
        fmri_data[16:48, 16:48, 8:24, t] += 50 + 10 * np.sin(t / 10)
        
    mock_img.get_fdata.return_value = fmri_data
    mock_img.shape = fmri_data.shape
    
    return mock_img


@pytest.fixture
def sample_motion_params():
    """Sample motion parameters for testing."""
    # 100 timepoints, 6 parameters (x, y, z, pitch, yaw, roll)
    n_timepoints = 100
    motion = np.zeros((n_timepoints, 6))
    
    # Add some realistic motion
    for i in range(1, n_timepoints):
        motion[i] = motion[i-1] + np.random.normal(0, 0.01, 6)
        
    # Add some sudden motion spikes
    motion[25] += [0.5, 0.3, 0.2, 0.02, 0.01, 0.015]
    motion[75] += [0.3, 0.4, 0.1, 0.015, 0.02, 0.01]
    
    return motion


@pytest.fixture
def sample_bvalues():
    """Sample b-values for DWI testing."""
    return np.array([0, 0, 0] + [1000] * 30 + [2000] * 60)


@pytest.fixture
def sample_bvectors():
    """Sample gradient directions for DWI testing."""
    n_dirs = 93  # 3 b=0 + 30 b=1000 + 60 b=2000
    bvecs = np.zeros((3, n_dirs))
    
    # b=0 directions (zeros)
    # b=1000 and b=2000 directions (random unit vectors)
    for i in range(3, n_dirs):
        # Random direction on unit sphere
        vec = np.random.normal(size=3)
        vec = vec / np.linalg.norm(vec)
        bvecs[:, i] = vec
        
    return bvecs