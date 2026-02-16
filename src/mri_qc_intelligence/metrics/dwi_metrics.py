"""Diffusion MRI QC metrics computation.

This module implements quality control metrics specific to diffusion
weighted imaging (DWI) data.
"""

from pathlib import Path
from typing import Dict, Any, Union, Optional, List

import numpy as np
import nibabel as nib
from scipy import stats

from .base import BaseQCMetrics


class DWIQCMetrics(BaseQCMetrics):
    """Diffusion MRI quality control metrics.
    
    Computes:
    - Signal dropout detection (slice-wise)
    - B-value consistency validation
    - Gradient direction coverage assessment
    - Motion estimation across volumes
    - Eddy current artifact detection
    """
    
    def compute(self, 
                image_path: Union[str, Path],
                bval_path: Optional[Union[str, Path]] = None,
                bvec_path: Optional[Union[str, Path]] = None,
                brain_mask_path: Optional[Union[str, Path]] = None,
                **kwargs) -> Dict[str, Any]:
        """Compute DWI QC metrics.
        
        Parameters
        ----------
        image_path : str or Path
            Path to 4D DWI image
        bval_path : str or Path, optional
            Path to b-values file
        bvec_path : str or Path, optional
            Path to gradient directions file
        brain_mask_path : str or Path, optional
            Path to brain mask
        **kwargs
            Additional parameters
            
        Returns
        -------
        dict
            Computed QC metrics
        """
        # Load 4D DWI data
        img = self.load_image(image_path)
        data = img.get_fdata()
        
        if data.ndim != 4:
            raise ValueError(f"Expected 4D DWI data, got {data.ndim}D")
            
        # Load b-values and directions if provided
        bvals, bvecs = None, None
        if bval_path:
            bvals = np.loadtxt(bval_path)
        if bvec_path:
            bvecs = np.loadtxt(bvec_path)
            
        # Load brain mask if provided
        if brain_mask_path:
            mask_img = self.load_image(brain_mask_path)
            brain_mask = mask_img.get_fdata().astype(bool)
        else:
            brain_mask = self._estimate_brain_mask(data, bvals)
            
        # Compute metrics
        metrics = {
            'signal_dropout_slices': self._detect_signal_dropout(data, brain_mask),
            'volume_outliers': self._detect_volume_outliers(data, brain_mask),
            'snr_b0': self._compute_b0_snr(data, brain_mask, bvals),
            'signal_intensity_consistency': self._assess_signal_consistency(data, brain_mask),
            'motion_estimate': self._estimate_motion(data, brain_mask)
        }
        
        # Add b-value/direction specific metrics if available
        if bvals is not None:
            metrics.update({
                'bvalue_consistency': self._validate_bvalues(bvals),
                'shell_coverage': self._assess_shell_coverage(bvals)
            })
            
        if bvecs is not None:
            metrics.update({
                'direction_coverage': self._assess_direction_coverage(bvecs, bvals),
                'gradient_consistency': self._validate_gradients(bvecs)
            })
            
        return metrics
        
    def _estimate_brain_mask(self, 
                           data: np.ndarray, 
                           bvals: Optional[np.ndarray] = None) -> np.ndarray:
        """Estimate brain mask from DWI data."""
        # Use b0 volume (first volume or lowest b-value)
        if bvals is not None:
            b0_idx = np.argmin(bvals)
        else:
            b0_idx = 0
            
        b0_vol = data[..., b0_idx]
        
        # Simple thresholding
        threshold = np.percentile(b0_vol[b0_vol > 0], 25)
        mask = b0_vol > threshold
        
        return mask.astype(bool)
        
    def _detect_signal_dropout(self, 
                              data: np.ndarray, 
                              brain_mask: np.ndarray) -> int:
        """Detect slices with signal dropout."""
        n_slices = data.shape[2]
        n_volumes = data.shape[3]
        dropout_slices = 0
        
        for vol_idx in range(n_volumes):
            vol_data = data[..., vol_idx]
            
            # Check each slice
            for slice_idx in range(n_slices):
                slice_data = vol_data[:, :, slice_idx]
                slice_mask = brain_mask[:, :, slice_idx]
                
                if np.sum(slice_mask) == 0:
                    continue
                    
                # Signal in this slice
                slice_signal = slice_data[slice_mask]
                
                # Compare to adjacent slices
                adjacent_signals = []
                for adj_idx in [slice_idx-1, slice_idx+1]:
                    if 0 <= adj_idx < n_slices:
                        adj_data = vol_data[:, :, adj_idx]
                        adj_mask = brain_mask[:, :, adj_idx]
                        if np.sum(adj_mask) > 0:
                            adjacent_signals.append(np.mean(adj_data[adj_mask]))
                            
                if len(adjacent_signals) > 0:
                    mean_adjacent = np.mean(adjacent_signals)
                    mean_slice = np.mean(slice_signal)
                    
                    # Dropout if slice signal is much lower than adjacent
                    if mean_slice < 0.5 * mean_adjacent:
                        dropout_slices += 1
                        break  # Count each slice only once
                        
        return dropout_slices
        
    def _detect_volume_outliers(self, 
                               data: np.ndarray, 
                               brain_mask: np.ndarray) -> int:
        """Detect outlier volumes based on signal intensity."""
        n_volumes = data.shape[3]
        volume_means = []
        
        for vol_idx in range(n_volumes):
            vol_data = data[..., vol_idx]
            brain_signal = vol_data[brain_mask]
            if len(brain_signal) > 0:
                volume_means.append(np.mean(brain_signal))
            else:
                volume_means.append(0)
                
        volume_means = np.array(volume_means)
        
        # Outliers are volumes with mean signal > 2 std from median
        median_signal = np.median(volume_means)
        mad_signal = np.median(np.abs(volume_means - median_signal))
        threshold = median_signal + 2 * mad_signal
        
        outliers = np.sum(volume_means > threshold)
        
        return int(outliers)
        
    def _compute_b0_snr(self, 
                        data: np.ndarray, 
                        brain_mask: np.ndarray,
                        bvals: Optional[np.ndarray] = None) -> float:
        """Compute SNR in b=0 volumes."""
        if bvals is not None:
            # Find b=0 volumes (b-value < 100)
            b0_indices = np.where(bvals < 100)[0]
        else:
            # Assume first volume is b=0
            b0_indices = [0]
            
        if len(b0_indices) == 0:
            return 0.0
            
        # Average b=0 volumes
        b0_data = np.mean(data[..., b0_indices], axis=3)
        
        # Signal from brain
        signal = b0_data[brain_mask]
        
        # Noise from background
        background_mask = ~brain_mask & (b0_data > 0)
        if np.sum(background_mask) == 0:
            return np.inf
            
        noise = b0_data[background_mask]
        
        return self.compute_snr(signal, noise)
        
    def _assess_signal_consistency(self, 
                                  data: np.ndarray, 
                                  brain_mask: np.ndarray) -> float:
        """Assess signal intensity consistency across volumes."""
        n_volumes = data.shape[3]
        volume_means = []
        
        for vol_idx in range(n_volumes):
            vol_data = data[..., vol_idx]
            brain_signal = vol_data[brain_mask]
            if len(brain_signal) > 0:
                volume_means.append(np.mean(brain_signal))
                
        if len(volume_means) < 2:
            return 1.0
            
        volume_means = np.array(volume_means)
        
        # Coefficient of variation
        cv = np.std(volume_means) / np.mean(volume_means)
        
        # Convert to quality score (lower CV = higher quality)
        return max(0, 1 - cv)
        
    def _estimate_motion(self, 
                        data: np.ndarray, 
                        brain_mask: np.ndarray) -> float:
        """Estimate motion between volumes."""
        n_volumes = data.shape[3]
        motion_scores = []
        
        # Use first volume as reference
        ref_vol = data[..., 0]
        ref_signal = ref_vol[brain_mask]
        
        for vol_idx in range(1, n_volumes):
            vol_data = data[..., vol_idx]
            vol_signal = vol_data[brain_mask]
            
            # Correlation between volumes (motion reduces correlation)
            if len(ref_signal) > 0 and len(vol_signal) > 0:
                corr = np.corrcoef(ref_signal, vol_signal)[0, 1]
                if not np.isnan(corr):
                    motion_scores.append(1 - corr)  # Higher = more motion
                    
        if len(motion_scores) == 0:
            return 0.0
            
        return np.mean(motion_scores)
        
    def _validate_bvalues(self, bvals: np.ndarray) -> float:
        """Validate b-value consistency."""
        # Check for reasonable b-value ranges
        if np.any(bvals < 0) or np.any(bvals > 10000):
            return 0.0  # Invalid b-values
            
        # Check for expected shells
        unique_bvals = np.unique(np.round(bvals / 100) * 100)
        expected_shells = [0, 1000, 2000, 3000]  # Common shells
        
        found_shells = 0
        for shell in expected_shells:
            if np.any(np.abs(unique_bvals - shell) < 100):
                found_shells += 1
                
        return found_shells / len(expected_shells)
        
    def _assess_shell_coverage(self, bvals: np.ndarray) -> Dict[str, int]:
        """Assess number of directions per b-value shell."""
        shells = {}
        
        # Round b-values to nearest 100
        rounded_bvals = np.round(bvals / 100) * 100
        unique_shells = np.unique(rounded_bvals)
        
        for shell in unique_shells:
            count = np.sum(rounded_bvals == shell)
            shells[f'shell_{int(shell)}'] = count
            
        return shells
        
    def _assess_direction_coverage(self, 
                                  bvecs: np.ndarray, 
                                  bvals: Optional[np.ndarray] = None) -> float:
        """Assess gradient direction coverage quality."""
        if bvecs.shape[0] != 3:
            # Transpose if needed
            if bvecs.shape[1] == 3:
                bvecs = bvecs.T
            else:
                return 0.0
                
        # Focus on non-zero b-value directions
        if bvals is not None:
            dwi_mask = bvals > 100
            dwi_dirs = bvecs[:, dwi_mask]
        else:
            dwi_dirs = bvecs
            
        if dwi_dirs.shape[1] < 6:
            return 0.0  # Too few directions
            
        # Normalize directions
        norms = np.linalg.norm(dwi_dirs, axis=0)
        norms[norms == 0] = 1  # Avoid division by zero
        dwi_dirs = dwi_dirs / norms
        
        # Assess spherical coverage using electrostatic energy
        n_dirs = dwi_dirs.shape[1]
        energy = 0
        
        for i in range(n_dirs):
            for j in range(i+1, n_dirs):
                # Distance on unit sphere
                dot_product = np.dot(dwi_dirs[:, i], dwi_dirs[:, j])
                dot_product = np.clip(dot_product, -1, 1)  # Numerical stability
                distance = np.arccos(np.abs(dot_product))  # Antipodal symmetry
                
                if distance > 0:
                    energy += 1.0 / distance
                    
        # Normalize by number of direction pairs
        if n_dirs > 1:
            energy /= (n_dirs * (n_dirs - 1) / 2)
            
        # Convert to quality score (lower energy = better coverage)
        max_expected_energy = 10.0  # Approximate threshold
        quality = max(0, 1 - energy / max_expected_energy)
        
        return quality
        
    def _validate_gradients(self, bvecs: np.ndarray) -> float:
        """Validate gradient direction consistency."""
        if bvecs.shape[0] != 3:
            if bvecs.shape[1] == 3:
                bvecs = bvecs.T
            else:
                return 0.0
                
        # Check for unit vectors (approximately)
        norms = np.linalg.norm(bvecs, axis=0)
        
        # Non-zero directions should have norm close to 1
        nonzero_mask = norms > 0.1
        if np.sum(nonzero_mask) == 0:
            return 0.0
            
        nonzero_norms = norms[nonzero_mask]
        norm_consistency = 1 - np.std(nonzero_norms - 1)
        
        return max(0, norm_consistency)