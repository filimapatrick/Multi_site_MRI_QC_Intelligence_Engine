"""QC scoring and normalization engine.

This module implements the standardized QC scoring system that converts
raw quality metrics into normalized scores (0-100 scale).
"""

from typing import Dict, Any, List, Optional
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class QCScorer:
    """QC scoring engine for computing standardized quality scores.
    
    This class:
    - Normalizes raw metrics across subjects/sites
    - Applies weighted scoring based on metric importance
    - Generates composite QC scores per modality
    - Provides dataset-level quality assessment
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize QC scorer.
        
        Parameters
        ----------
        config : dict, optional
            Scoring configuration including weights and thresholds
        """
        self.config = config or {}
        
        # Default scoring weights (can be overridden by config)
        self.default_weights = {
            'T1w': {
                'snr': 0.3,
                'cnr_gm_wm': 0.25,
                'inu': 0.2,
                'background_noise': 0.1,
                'brain_mask_quality': 0.1,
                'artifact_score': 0.05
            },
            'bold': {
                'tsnr_mean': 0.3,
                'fd_mean': 0.25,
                'dvars': 0.2,
                'signal_drift': 0.1,
                'motion_spikes': 0.1,
                'temporal_smoothness': 0.05
            },
            'dwi': {
                'snr_b0': 0.25,
                'signal_dropout_slices': 0.2,
                'volume_outliers': 0.2,
                'motion_estimate': 0.15,
                'direction_coverage': 0.1,
                'signal_intensity_consistency': 0.1
            }
        }
        
        # Quality thresholds for pass/warning/fail
        self.thresholds = {
            'pass': 75,    # Score >= 75: Pass
            'warning': 50, # 50 <= Score < 75: Warning
            'fail': 50     # Score < 50: Fail
        }
        
    def compute_scores(self, 
                      dataset_metrics: Dict[str, Dict],
                      site_info: Optional[Dict] = None) -> Dict[str, Any]:
        """Compute standardized QC scores for entire dataset.
        
        Parameters
        ----------
        dataset_metrics : dict
            Nested dict: {subject_id: {modality: {metric: value}}}
        site_info : dict, optional
            Site information for each subject: {subject_id: site_id}
            
        Returns
        -------
        dict
            Computed scores and statistics
        """
        logger.info("Computing QC scores for dataset")
        
        scores = {
            'subject_scores': {},
            'dataset_summary': {},
            'site_summary': {} if site_info else None
        }
        
        # Extract all metrics by modality for normalization
        normalized_metrics = self._normalize_metrics(dataset_metrics)
        
        # Compute subject-level scores
        for subject_id, subject_metrics in dataset_metrics.items():
            scores['subject_scores'][subject_id] = self._compute_subject_scores(
                subject_metrics, normalized_metrics
            )
            
        # Compute dataset-level statistics
        scores['dataset_summary'] = self._compute_dataset_summary(
            scores['subject_scores']
        )
        
        # Compute site-level statistics if site info provided
        if site_info:
            scores['site_summary'] = self._compute_site_summary(
                scores['subject_scores'], site_info
            )
            
        return scores
        
    def _normalize_metrics(self, dataset_metrics: Dict[str, Dict]) -> Dict:
        """Normalize metrics across all subjects."""
        logger.info("Normalizing metrics across dataset")
        
        # Collect all metric values by modality
        metric_collections = {}
        
        for subject_metrics in dataset_metrics.values():
            for modality, metrics in subject_metrics.items():
                if modality not in metric_collections:
                    metric_collections[modality] = {}
                    
                for metric_name, value in metrics.items():
                    if metric_name not in metric_collections[modality]:
                        metric_collections[modality][metric_name] = []
                    metric_collections[modality][metric_name].append(value)
                    
        # Compute normalization parameters
        normalization_params = {}
        
        for modality, metrics in metric_collections.items():
            normalization_params[modality] = {}
            
            for metric_name, values in metrics.items():
                # Filter out non-scalar values (dicts, lists, arrays)
                scalar_values = [v for v in values if isinstance(v, (int, float, np.number)) and not isinstance(v, (bool, np.bool_))]
                
                if not scalar_values:
                    continue
                    
                values = np.array(scalar_values)
                values = values[np.isfinite(values)]  # Remove inf/nan
                
                if len(values) > 0:
                    normalization_params[modality][metric_name] = {
                        'median': np.median(values),
                        'mad': np.median(np.abs(values - np.median(values))),
                        'min': np.min(values),
                        'max': np.max(values),
                        'percentile_5': np.percentile(values, 5),
                        'percentile_95': np.percentile(values, 95)
                    }
                    
        return normalization_params
        
    def _compute_subject_scores(self, 
                               subject_metrics: Dict, 
                               normalization_params: Dict) -> Dict:
        """Compute QC scores for a single subject."""
        subject_scores = {}
        
        for modality, metrics in subject_metrics.items():
            if modality in self.default_weights:
                modality_score = self._compute_modality_score(
                    metrics, modality, normalization_params.get(modality, {})
                )
                
                subject_scores[modality] = {
                    'composite_score': modality_score,
                    'quality_rating': self._get_quality_rating(modality_score),
                    'individual_scores': self._score_individual_metrics(
                        metrics, modality, normalization_params.get(modality, {})
                    )
                }
                
        # Overall subject score (average across modalities)
        if subject_scores:
            all_scores = [score['composite_score'] for score in subject_scores.values()]
            subject_scores['overall'] = {
                'composite_score': np.mean(all_scores),
                'quality_rating': self._get_quality_rating(np.mean(all_scores))
            }
            
        return subject_scores
        
    def _compute_modality_score(self, 
                               metrics: Dict, 
                               modality: str,
                               norm_params: Dict) -> float:
        """Compute weighted composite score for a modality."""
        weights = self.config.get(f'{modality}_weights', 
                                 self.default_weights.get(modality, {}))
        
        weighted_scores = []
        total_weight = 0
        
        for metric_name, value in metrics.items():
            weight = weights.get(metric_name, 0)
            if weight > 0 and metric_name in norm_params:
                normalized_score = self._normalize_metric_to_score(
                    value, metric_name, norm_params[metric_name]
                )
                weighted_scores.append(normalized_score * weight)
                total_weight += weight
                
        if total_weight > 0:
            return sum(weighted_scores) / total_weight
        else:
            return 50  # Default neutral score
            
    def _normalize_metric_to_score(self, 
                                  value: float, 
                                  metric_name: str,
                                  norm_param: Dict) -> float:
        """Convert raw metric value to 0-100 score."""
        if not np.isfinite(value):
            return 50  # Neutral score for invalid values
            
        # Define which metrics are "higher is better" vs "lower is better"
        higher_is_better = {
            'snr', 'cnr_gm_wm', 'tsnr_mean', 'brain_mask_quality', 
            'artifact_score', 'direction_coverage', 'signal_intensity_consistency',
            'temporal_smoothness'
        }
        
        lower_is_better = {
            'inu', 'background_noise', 'fd_mean', 'dvars', 'signal_drift',
            'motion_spikes', 'motion_estimate', 'signal_dropout_slices',
            'volume_outliers'
        }
        
        # Use robust z-score for normalization
        median_val = norm_param['median']
        mad_val = norm_param['mad']
        
        if mad_val == 0:
            z_score = 0
        else:
            z_score = (value - median_val) / (1.4826 * mad_val)  # MAD to std conversion
            
        # Convert z-score to 0-100 scale
        if metric_name in higher_is_better:
            # Higher values = higher scores
            score = 50 + z_score * 15  # ±3 sigma maps to roughly 0-100
        elif metric_name in lower_is_better:
            # Lower values = higher scores
            score = 50 - z_score * 15
        else:
            # Default: assume higher is better
            score = 50 + z_score * 15
            
        # Clamp to 0-100 range
        return np.clip(score, 0, 100)
        
    def _score_individual_metrics(self, 
                                 metrics: Dict, 
                                 modality: str,
                                 norm_params: Dict) -> Dict:
        """Score individual metrics for detailed reporting."""
        individual_scores = {}
        
        for metric_name, value in metrics.items():
            if metric_name in norm_params:
                score = self._normalize_metric_to_score(
                    value, metric_name, norm_params[metric_name]
                )
                individual_scores[metric_name] = {
                    'raw_value': value,
                    'normalized_score': score,
                    'rating': self._get_quality_rating(score)
                }
                
        return individual_scores
        
    def _get_quality_rating(self, score: float) -> str:
        """Convert numeric score to quality rating."""
        if score >= self.thresholds['pass']:
            return 'Pass'
        elif score >= self.thresholds['warning']:
            return 'Warning'
        else:
            return 'Fail'
            
    def _compute_dataset_summary(self, subject_scores: Dict) -> Dict:
        """Compute dataset-level summary statistics."""
        summary = {
            'total_subjects': len(subject_scores),
            'modality_stats': {},
            'quality_distribution': {'Pass': 0, 'Warning': 0, 'Fail': 0}
        }
        
        # Collect scores by modality
        modality_scores = {}
        
        for subject_id, scores in subject_scores.items():
            for modality, modality_data in scores.items():
                if modality == 'overall':
                    continue
                    
                if modality not in modality_scores:
                    modality_scores[modality] = []
                    
                modality_scores[modality].append(modality_data['composite_score'])
                
            # Count quality ratings
            if 'overall' in scores:
                rating = scores['overall']['quality_rating']
                summary['quality_distribution'][rating] += 1
                
        # Compute statistics for each modality
        for modality, scores in modality_scores.items():
            if scores:
                summary['modality_stats'][modality] = {
                    'mean_score': np.mean(scores),
                    'median_score': np.median(scores),
                    'std_score': np.std(scores),
                    'min_score': np.min(scores),
                    'max_score': np.max(scores)
                }
                
        return summary
        
    def _compute_site_summary(self, 
                             subject_scores: Dict, 
                             site_info: Dict) -> Dict:
        """Compute site-level summary statistics."""
        site_summary = {}
        
        # Group subjects by site
        sites = {}
        for subject_id in subject_scores.keys():
            site_id = site_info.get(subject_id, 'unknown')
            if site_id not in sites:
                sites[site_id] = []
            sites[site_id].append(subject_id)
            
        # Compute statistics for each site
        for site_id, subject_ids in sites.items():
            site_scores = [subject_scores[subj_id] for subj_id in subject_ids 
                          if 'overall' in subject_scores[subj_id]]
            
            if site_scores:
                overall_scores = [scores['overall']['composite_score'] 
                                for scores in site_scores]
                
                site_summary[site_id] = {
                    'n_subjects': len(subject_ids),
                    'mean_score': np.mean(overall_scores),
                    'median_score': np.median(overall_scores),
                    'std_score': np.std(overall_scores)
                }
                
        return site_summary