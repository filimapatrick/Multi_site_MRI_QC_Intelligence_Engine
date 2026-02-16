"""Base class for QC metrics computation.

This module defines the common interface for all modality-specific QC metrics.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Union

import numpy as np
import nibabel as nib


class BaseQCMetrics(ABC):
    """Abstract base class for QC metrics computation."""
    
    def __init__(self):
        """Initialize base metrics class."""
        self.metrics = {}
        
    @abstractmethod
    def compute(self, image_path: Union[str, Path], **kwargs) -> Dict[str, Any]:
        """Compute QC metrics for given image.
        
        Parameters
        ----------
        image_path : str or Path
            Path to MRI image file
        **kwargs
            Additional modality-specific parameters
            
        Returns
        -------
        dict
            Dictionary of computed QC metrics
        """
        pass
        
    def load_image(self, image_path: Union[str, Path]) -> nib.Nifti1Image:
        """Load NIfTI image.
        
        Parameters
        ----------
        image_path : str or Path
            Path to image file
            
        Returns
        -------
        nibabel.Nifti1Image
            Loaded image object
        """
        return nib.load(str(image_path))
        
    def compute_snr(self, 
                    signal_data: np.ndarray, 
                    noise_data: np.ndarray) -> float:
        """Compute Signal-to-Noise Ratio.
        
        Parameters
        ----------
        signal_data : np.ndarray
            Signal region intensities
        noise_data : np.ndarray
            Noise region intensities
            
        Returns
        -------
        float
            SNR value
        """
        signal_mean = np.mean(signal_data)
        noise_std = np.std(noise_data)
        
        if noise_std == 0:
            return np.inf
            
        return signal_mean / noise_std
        
    def compute_cnr(self,
                    tissue1_data: np.ndarray,
                    tissue2_data: np.ndarray, 
                    noise_data: np.ndarray) -> float:
        """Compute Contrast-to-Noise Ratio.
        
        Parameters
        ----------
        tissue1_data : np.ndarray
            First tissue region intensities
        tissue2_data : np.ndarray
            Second tissue region intensities
        noise_data : np.ndarray
            Noise region intensities
            
        Returns
        -------
        float
            CNR value
        """
        contrast = abs(np.mean(tissue1_data) - np.mean(tissue2_data))
        noise_std = np.std(noise_data)
        
        if noise_std == 0:
            return np.inf
            
        return contrast / noise_std