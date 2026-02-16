"""Functional MRI QC metrics computation.

This module implements quality control metrics specific to functional
MRI (BOLD) data.
"""

from pathlib import Path
from typing import Dict, Any, Union, Optional

import numpy as np
import nibabel as nib
from scipy import stats

from .base import BaseQCMetrics


class FMRIQCMetrics(BaseQCMetrics):
    """Functional MRI quality control metrics.
    
    Computes:
    - Framewise Displacement (FD)
    - DVARS (temporal derivative of BOLD signal variance)
    - Temporal Signal-to-Noise Ratio (tSNR)
    - Motion spike detection
    - Signal drift estimation
    """
    
    def compute(self, 
                image_path: Union[str, Path],
                motion_params_path: Optional[Union[str, Path]] = None,
                brain_mask_path: Optional[Union[str, Path]] = None,
                **kwargs) -> Dict[str, Any]:
        """Compute fMRI QC metrics.
        
        Parameters
        ----------
        image_path : str or Path
            Path to 4D fMRI image
        motion_params_path : str or Path, optional
            Path to motion parameters file
        brain_mask_path : str or Path, optional
            Path to brain mask
        **kwargs
            Additional parameters
            
        Returns
        -------
        dict
            Computed QC metrics
        """
        # Load 4D fMRI data
        img = self.load_image(image_path)
        data = img.get_fdata()
        
        if data.ndim != 4:
            raise ValueError(f"Expected 4D fMRI data, got {data.ndim}D")
            
        # Load brain mask if provided
        if brain_mask_path:
            mask_img = self.load_image(brain_mask_path)
            brain_mask = mask_img.get_fdata().astype(bool)
        else:
            brain_mask = self._estimate_brain_mask(data)
            
        # Load motion parameters if provided
        motion_params = None
        if motion_params_path:
            motion_params = np.loadtxt(motion_params_path)
            
        # Compute metrics
        metrics = {
            'tsnr_mean': self._compute_tsnr(data, brain_mask),
            'dvars': self._compute_dvars(data, brain_mask),
            'signal_drift': self._compute_signal_drift(data, brain_mask),
            'motion_spikes': self._detect_motion_spikes(data, brain_mask),
            'temporal_smoothness': self._compute_temporal_smoothness(data, brain_mask)
        }
        
        # Add motion-based metrics if motion parameters available
        if motion_params is not None:
            metrics.update({
                'fd_mean': self._compute_framewise_displacement(motion_params),
                'fd_spikes': self._count_fd_spikes(motion_params),
                'motion_outliers': self._detect_motion_outliers(motion_params)
            })
            
        return metrics
        
    def _estimate_brain_mask(self, data: np.ndarray) -> np.ndarray:
        """Estimate brain mask from 4D fMRI data."""
        # Use mean image across time for mask estimation
        mean_img = np.mean(data, axis=3)
        
        # Simple thresholding
        threshold = np.percentile(mean_img[mean_img > 0], 25)
        mask = mean_img > threshold
        
        return mask.astype(bool)
        
    def _compute_tsnr(self, data: np.ndarray, brain_mask: np.ndarray) -> float:
        """Compute temporal Signal-to-Noise Ratio."""
        # Extract brain voxel time series
        brain_ts = data[brain_mask]  # Shape: (n_voxels, n_timepoints)
        
        if brain_ts.size == 0:
            return 0.0
            
        # Compute tSNR for each voxel
        temporal_mean = np.mean(brain_ts, axis=1)
        temporal_std = np.std(brain_ts, axis=1)
        
        # Avoid division by zero
        temporal_std[temporal_std == 0] = np.inf
        
        tsnr_voxelwise = temporal_mean / temporal_std
        
        # Return median tSNR across brain voxels
        return np.median(tsnr_voxelwise[np.isfinite(tsnr_voxelwise)])
        
    def _compute_dvars(self, data: np.ndarray, brain_mask: np.ndarray) -> np.ndarray:
        """Compute DVARS (temporal derivative of variance)."""
        brain_ts = data[brain_mask]
        
        if brain_ts.size == 0:
            return np.array([])
            
        # Compute temporal differences
        brain_diff = np.diff(brain_ts, axis=1)
        
        # Compute variance of differences at each timepoint
        dvars = np.var(brain_diff, axis=0)
        
        return np.sqrt(dvars)  # RMS DVARS
        
    def _compute_signal_drift(self, data: np.ndarray, brain_mask: np.ndarray) -> float:
        """Estimate linear signal drift."""
        brain_ts = data[brain_mask]
        n_timepoints = data.shape[3]
        
        if brain_ts.size == 0 or n_timepoints < 3:
            return 0.0
            
        # Global signal (mean across brain voxels)
        global_signal = np.mean(brain_ts, axis=0)
        
        # Fit linear trend
        time_points = np.arange(n_timepoints)
        slope, _, r_value, _, _ = stats.linregress(time_points, global_signal)
        
        # Return slope normalized by mean signal
        mean_signal = np.mean(global_signal)
        if mean_signal != 0:
            return abs(slope) / mean_signal
        else:
            return 0.0
            
    def _detect_motion_spikes(self, data: np.ndarray, brain_mask: np.ndarray) -> int:
        """Detect motion spikes using DVARS."""
        dvars = self._compute_dvars(data, brain_mask)
        
        if len(dvars) == 0:
            return 0
            
        # Spikes are timepoints with DVARS > threshold
        threshold = np.median(dvars) + 2 * np.std(dvars)
        spikes = np.sum(dvars > threshold)
        
        return int(spikes)
        
    def _compute_temporal_smoothness(self, 
                                   data: np.ndarray, 
                                   brain_mask: np.ndarray) -> float:
        """Compute temporal smoothness metric."""
        brain_ts = data[brain_mask]
        
        if brain_ts.size == 0:
            return 0.0
            
        # Compute temporal autocorrelation at lag 1
        autocorrs = []
        for voxel_ts in brain_ts:
            if len(voxel_ts) > 1:
                corr = np.corrcoef(voxel_ts[:-1], voxel_ts[1:])[0, 1]
                if not np.isnan(corr):
                    autocorrs.append(corr)
                    
        if len(autocorrs) == 0:
            return 0.0
            
        return np.median(autocorrs)
        
    def _compute_framewise_displacement(self, motion_params: np.ndarray) -> float:
        """Compute mean Framewise Displacement.
        
        Assumes motion_params has 6 columns: [x, y, z, pitch, yaw, roll]
        """
        if motion_params.shape[1] != 6:
            raise ValueError("Motion parameters should have 6 columns")
            
        # Convert rotations to mm (assuming 50mm sphere)
        radius = 50.0  # mm
        
        # Separate translations and rotations
        translations = motion_params[:, :3]  # x, y, z
        rotations = motion_params[:, 3:]     # pitch, yaw, roll
        
        # Convert rotations from radians to mm
        rotations_mm = rotations * radius
        
        # Combine translations and converted rotations
        motion_mm = np.column_stack([translations, rotations_mm])
        
        # Compute frame-to-frame differences
        motion_diff = np.abs(np.diff(motion_mm, axis=0))
        
        # Sum across parameters (FD)
        fd = np.sum(motion_diff, axis=1)
        
        return np.mean(fd)
        
    def _count_fd_spikes(self, motion_params: np.ndarray, threshold: float = 0.5) -> int:
        """Count number of FD spikes above threshold."""
        fd_values = self._compute_framewise_displacement_timeseries(motion_params)
        return np.sum(fd_values > threshold)
        
    def _compute_framewise_displacement_timeseries(self, 
                                                  motion_params: np.ndarray) -> np.ndarray:
        """Compute FD timeseries."""
        if motion_params.shape[1] != 6:
            raise ValueError("Motion parameters should have 6 columns")
            
        radius = 50.0
        
        translations = motion_params[:, :3]
        rotations = motion_params[:, 3:] * radius
        
        motion_mm = np.column_stack([translations, rotations])
        motion_diff = np.abs(np.diff(motion_mm, axis=0))
        
        fd = np.sum(motion_diff, axis=1)
        
        return fd
        
    def _detect_motion_outliers(self, motion_params: np.ndarray) -> int:
        """Detect motion outlier timepoints."""
        fd_values = self._compute_framewise_displacement_timeseries(motion_params)
        
        # Outliers are points > median + 2*MAD
        median_fd = np.median(fd_values)
        mad_fd = np.median(np.abs(fd_values - median_fd))
        threshold = median_fd + 2 * mad_fd
        
        return np.sum(fd_values > threshold)