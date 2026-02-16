"""T1-weighted MRI QC metrics computation.

This module implements quality control metrics specific to T1-weighted
structural MRI data.
"""

from pathlib import Path
from typing import Dict, Any, Union, Optional

import numpy as np
import nibabel as nib
from scipy import ndimage
from skimage import measure, morphology

from .base import BaseQCMetrics


class T1QCMetrics(BaseQCMetrics):
    """T1-weighted MRI quality control metrics.
    
    Computes:
    - Signal-to-Noise Ratio (SNR)
    - Contrast-to-Noise Ratio (GM vs WM)
    - Intensity Non-Uniformity (INU)
    - Background noise estimation
    - Brain mask quality assessment
    """
    
    def compute(self, 
                image_path: Union[str, Path], 
                brain_mask_path: Optional[Union[str, Path]] = None,
                **kwargs) -> Dict[str, Any]:
        """Compute T1w QC metrics.
        
        Parameters
        ----------
        image_path : str or Path
            Path to T1w image
        brain_mask_path : str or Path, optional
            Path to brain mask (if None, will be estimated)
        **kwargs
            Additional parameters
            
        Returns
        -------
        dict
            Computed QC metrics
        """
        # Load image
        img = self.load_image(image_path)
        data = img.get_fdata()
        
        # Load or create brain mask
        if brain_mask_path:
            mask_img = self.load_image(brain_mask_path)
            brain_mask = mask_img.get_fdata().astype(bool)
        else:
            brain_mask = self._estimate_brain_mask(data)
            
        # Compute metrics
        metrics = {
            'snr': self._compute_t1_snr(data, brain_mask),
            'cnr_gm_wm': self._compute_gm_wm_cnr(data, brain_mask),
            'inu': self._compute_intensity_nonuniformity(data, brain_mask),
            'background_noise': self._compute_background_noise(data, brain_mask),
            'brain_mask_quality': self._assess_brain_mask_quality(brain_mask),
            'artifact_score': self._detect_artifacts(data, brain_mask)
        }
        
        return metrics
        
    def _estimate_brain_mask(self, data: np.ndarray) -> np.ndarray:
        """Estimate brain mask using simple thresholding."""
        # Simple Otsu-like thresholding for brain extraction
        threshold = np.percentile(data[data > 0], 25)
        mask = data > threshold
        
        # Morphological operations to clean up mask
        mask = ndimage.binary_fill_holes(mask)
        mask = morphology.opening(mask, np.ones((3, 3, 3)))
        
        # Keep only largest connected component
        labeled, num_labels = measure.label(mask, return_num=True)
        if num_labels > 1:
            sizes = [np.sum(labeled == i) for i in range(1, num_labels + 1)]
            largest_label = np.argmax(sizes) + 1
            mask = labeled == largest_label
            
        return mask.astype(bool)
        
    def _compute_t1_snr(self, data: np.ndarray, brain_mask: np.ndarray) -> float:
        """Compute SNR for T1w image."""
        # Signal from brain tissue
        signal = data[brain_mask]
        
        # Noise from background (corners of image)
        shape = data.shape
        corner_size = min(20, min(shape) // 10)
        noise_regions = [
            data[:corner_size, :corner_size, :corner_size],
            data[-corner_size:, :corner_size, :corner_size],
            data[:corner_size, -corner_size:, :corner_size], 
            data[:corner_size, :corner_size, -corner_size:]
        ]
        noise = np.concatenate([region.flatten() for region in noise_regions])
        
        return self.compute_snr(signal, noise)
        
    def _compute_gm_wm_cnr(self, data: np.ndarray, brain_mask: np.ndarray) -> float:
        """Compute contrast-to-noise ratio between GM and WM."""
        # Simple tissue segmentation based on intensity values
        brain_data = data[brain_mask]
        
        # Rough tissue separation using percentiles
        p25, p75 = np.percentile(brain_data, [25, 75])
        
        # GM typically has intermediate intensities
        gm_mask = (data >= p25) & (data <= p75) & brain_mask
        
        # WM typically has higher intensities  
        wm_mask = (data > p75) & brain_mask
        
        if np.sum(gm_mask) == 0 or np.sum(wm_mask) == 0:
            return 0.0
            
        gm_data = data[gm_mask]
        wm_data = data[wm_mask]
        
        # Use background for noise estimate
        noise = self._get_background_noise(data, brain_mask)
        
        return self.compute_cnr(gm_data, wm_data, noise)
        
    def _compute_intensity_nonuniformity(self, 
                                        data: np.ndarray, 
                                        brain_mask: np.ndarray) -> float:
        """Compute intensity non-uniformity metric."""
        # Simple coefficient of variation within brain
        brain_data = data[brain_mask]
        if len(brain_data) == 0:
            return 1.0
            
        return np.std(brain_data) / np.mean(brain_data)
        
    def _compute_background_noise(self, 
                                 data: np.ndarray, 
                                 brain_mask: np.ndarray) -> float:
        """Estimate background noise level."""
        noise = self._get_background_noise(data, brain_mask)
        return np.std(noise)
        
    def _get_background_noise(self, data: np.ndarray, brain_mask: np.ndarray) -> np.ndarray:
        """Extract background noise samples."""
        # Background is everything outside brain
        background_mask = ~brain_mask & (data > 0)  # Exclude zero padding
        return data[background_mask]
        
    def _assess_brain_mask_quality(self, brain_mask: np.ndarray) -> float:
        """Assess quality of brain mask."""
        # Simple heuristics for mask quality
        # 1. Check if mask is reasonable size
        total_voxels = np.prod(brain_mask.shape)
        brain_voxels = np.sum(brain_mask)
        brain_fraction = brain_voxels / total_voxels
        
        # Brain should be roughly 10-30% of total volume
        size_score = 1.0 - abs(brain_fraction - 0.2) / 0.2
        size_score = max(0, min(1, size_score))
        
        # 2. Check connectivity (should be mostly one component)
        labeled, num_labels = measure.label(brain_mask, return_num=True)
        connectivity_score = 1.0 / num_labels if num_labels > 0 else 0.0
        
        # Combined score
        return 0.7 * size_score + 0.3 * connectivity_score
        
    def _detect_artifacts(self, data: np.ndarray, brain_mask: np.ndarray) -> float:
        """Detect common T1w artifacts."""
        # Simple artifact detection based on intensity patterns
        
        # 1. Motion artifacts (high frequency noise)
        brain_data = data[brain_mask]
        
        # Compute gradient magnitude
        grad_x = np.gradient(data, axis=0)
        grad_y = np.gradient(data, axis=1) 
        grad_z = np.gradient(data, axis=2)
        grad_mag = np.sqrt(grad_x**2 + grad_y**2 + grad_z**2)
        
        # High gradient values in brain may indicate artifacts
        brain_gradients = grad_mag[brain_mask]
        gradient_score = np.percentile(brain_gradients, 95)
        
        # Normalize to 0-1 scale (lower is better)
        artifact_score = min(1.0, gradient_score / np.mean(brain_data))
        
        return 1.0 - artifact_score  # Convert to quality score (higher is better)