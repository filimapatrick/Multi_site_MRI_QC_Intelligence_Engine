"""Statistical outlier detection for multi-site QC analysis.

This module implements various outlier detection methods for identifying
problematic subjects and site-level effects in QC metrics.
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.covariance import EllipticEnvelope
import logging

logger = logging.getLogger(__name__)


class OutlierDetector:
    """Multi-method outlier detection for QC metrics.
    
    Implements:
    - Statistical outlier detection (z-score, modified z-score)
    - Isolation Forest (unsupervised anomaly detection)
    - Robust covariance outlier detection
    - Site-aware outlier detection
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize outlier detector.
        
        Parameters
        ----------
        config : dict, optional
            Configuration parameters for outlier detection
        """
        self.config = config or {}
        
        # Default thresholds
        self.thresholds = {
            'z_score': 2.5,
            'modified_z_score': 3.5,
            'isolation_contamination': 0.1,
            'robust_covariance_contamination': 0.1
        }
        
        # Update with user config
        self.thresholds.update(self.config.get('thresholds', {}))
        
    def detect_outliers(self, 
                       dataset_metrics: Dict[str, Dict],
                       scores: Dict[str, Any],
                       site_info: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Detect outliers using multiple methods.
        
        Parameters
        ----------
        dataset_metrics : dict
            Raw QC metrics for all subjects
        scores : dict
            Computed QC scores
        site_info : dict, optional
            Site information: {subject_id: site_id}
            
        Returns
        -------
        dict
            Outlier detection results
        """
        logger.info("Running outlier detection analysis")
        
        outlier_results = {
            'subject_outliers': {},
            'metric_outliers': {},
            'site_effects': {} if site_info else None,
            'outlier_summary': {},
            'detection_methods': {
                'statistical': {},
                'machine_learning': {},
                'site_aware': {}
            }
        }
        
        # Prepare data for analysis
        subjects, features, feature_names = self._prepare_feature_matrix(
            dataset_metrics, scores
        )
        
        if len(subjects) < 3:
            logger.warning("Too few subjects for reliable outlier detection")
            return outlier_results
            
        # 1. Statistical outlier detection
        outlier_results['detection_methods']['statistical'] = (
            self._statistical_outlier_detection(subjects, features, feature_names)
        )
        
        # 2. Machine learning outlier detection
        outlier_results['detection_methods']['machine_learning'] = (
            self._ml_outlier_detection(subjects, features)
        )
        
        # 3. Site-aware outlier detection
        if site_info:
            outlier_results['detection_methods']['site_aware'] = (
                self._site_aware_outlier_detection(
                    subjects, features, feature_names, site_info
                )
            )
            
        # Combine results and create consensus
        outlier_results.update(
            self._combine_outlier_results(
                outlier_results['detection_methods'], subjects
            )
        )
        
        return outlier_results
        
    def _prepare_feature_matrix(self, 
                               dataset_metrics: Dict[str, Dict],
                               scores: Dict[str, Any]) -> Tuple[List[str], np.ndarray, List[str]]:
        """Prepare feature matrix for outlier detection."""
        subjects = list(dataset_metrics.keys())
        feature_names = []
        feature_matrix = []
        
        # Collect all available features
        for subject_id in subjects:
            subject_features = []
            
            # Add composite scores
            if subject_id in scores.get('subject_scores', {}):
                subject_scores = scores['subject_scores'][subject_id]
                
                for modality, modality_data in subject_scores.items():
                    if modality != 'overall' and 'composite_score' in modality_data:
                        if len(feature_names) == len(subject_features):
                            feature_names.append(f'{modality}_score')
                        subject_features.append(modality_data['composite_score'])
                        
            # Add key raw metrics
            subject_metrics = dataset_metrics[subject_id]
            for modality, metrics in subject_metrics.items():
                for metric_name, value in metrics.items():
                    # Skip non-scalar values
                    if not isinstance(value, (int, float, np.number)) or isinstance(value, (bool, np.bool_)):
                        continue
                        
                    if np.isfinite(value):  # Skip inf/nan values
                        feature_name = f'{modality}_{metric_name}'
                        if len(feature_names) == len(subject_features):
                            feature_names.append(feature_name)
                        subject_features.append(value)
                        
            feature_matrix.append(subject_features)
            
        # Convert to numpy array and handle missing values
        feature_matrix = np.array(feature_matrix)
        
        # Fill missing values with median
        for col in range(feature_matrix.shape[1]):
            col_data = feature_matrix[:, col]
            finite_mask = np.isfinite(col_data)
            if np.any(finite_mask):
                median_val = np.median(col_data[finite_mask])
                feature_matrix[~finite_mask, col] = median_val
                
        return subjects, feature_matrix, feature_names
        
    def _statistical_outlier_detection(self, 
                                      subjects: List[str],
                                      features: np.ndarray,
                                      feature_names: List[str]) -> Dict:
        """Statistical outlier detection using z-scores."""
        results = {
            'z_score_outliers': [],
            'modified_z_score_outliers': [],
            'feature_outliers': {}
        }
        
        n_subjects, n_features = features.shape
        
        # Z-score outlier detection
        z_scores = np.abs(stats.zscore(features, axis=0, nan_policy='omit'))
        z_outliers = np.any(z_scores > self.thresholds['z_score'], axis=1)
        results['z_score_outliers'] = [subjects[i] for i in range(n_subjects) if z_outliers[i]]
        
        # Modified Z-score (using median and MAD)
        modified_z_outliers = []
        for i in range(n_subjects):
            subject_outlier = False
            for j in range(n_features):
                median_val = np.median(features[:, j])
                mad_val = np.median(np.abs(features[:, j] - median_val))
                
                if mad_val != 0:
                    mod_z_score = 0.6745 * (features[i, j] - median_val) / mad_val
                    if abs(mod_z_score) > self.thresholds['modified_z_score']:
                        subject_outlier = True
                        break
                        
            if subject_outlier:
                modified_z_outliers.append(subjects[i])
                
        results['modified_z_score_outliers'] = modified_z_outliers
        
        # Per-feature outliers
        for j, feature_name in enumerate(feature_names):
            feature_z_scores = z_scores[:, j]
            feature_outliers = [subjects[i] for i in range(n_subjects) 
                              if feature_z_scores[i] > self.thresholds['z_score']]
            if feature_outliers:
                results['feature_outliers'][feature_name] = feature_outliers
                
        return results
        
    def _ml_outlier_detection(self, 
                             subjects: List[str],
                             features: np.ndarray) -> Dict:
        """Machine learning outlier detection."""
        results = {
            'isolation_forest_outliers': [],
            'robust_covariance_outliers': []
        }
        
        if features.shape[0] < 10:  # Need sufficient samples
            logger.warning("Too few samples for ML outlier detection")
            return results
            
        try:
            # Isolation Forest
            iso_forest = IsolationForest(
                contamination=self.thresholds['isolation_contamination'],
                random_state=42
            )
            iso_predictions = iso_forest.fit_predict(features)
            iso_outliers = [subjects[i] for i, pred in enumerate(iso_predictions) if pred == -1]
            results['isolation_forest_outliers'] = iso_outliers
            
            # Robust Covariance (Elliptic Envelope)
            if features.shape[1] > 1:  # Need multiple features
                elliptic_env = EllipticEnvelope(
                    contamination=self.thresholds['robust_covariance_contamination'],
                    random_state=42
                )
                elliptic_predictions = elliptic_env.fit_predict(features)
                elliptic_outliers = [subjects[i] for i, pred in enumerate(elliptic_predictions) 
                                   if pred == -1]
                results['robust_covariance_outliers'] = elliptic_outliers
                
        except Exception as e:
            logger.warning(f"ML outlier detection failed: {e}")
            
        return results
        
    def _site_aware_outlier_detection(self, 
                                     subjects: List[str],
                                     features: np.ndarray,
                                     feature_names: List[str],
                                     site_info: Dict[str, str]) -> Dict:
        """Site-aware outlier detection."""
        results = {
            'site_outliers': {},
            'cross_site_outliers': [],
            'site_effects': {}
        }
        
        # Group subjects by site
        sites = {}
        for i, subject_id in enumerate(subjects):
            site_id = site_info.get(subject_id, 'unknown')
            if site_id not in sites:
                sites[site_id] = []
            sites[site_id].append((i, subject_id))
            
        # Within-site outlier detection
        for site_id, site_subjects in sites.items():
            if len(site_subjects) < 3:  # Need minimum subjects per site
                continue
                
            site_indices = [idx for idx, _ in site_subjects]
            site_features = features[site_indices]
            site_subject_ids = [subj_id for _, subj_id in site_subjects]
            
            # Z-score within site
            site_z_scores = np.abs(stats.zscore(site_features, axis=0, nan_policy='omit'))
            site_outliers = np.any(site_z_scores > self.thresholds['z_score'], axis=1)
            
            outlier_subjects = [site_subject_ids[i] for i in range(len(site_subject_ids)) 
                              if site_outliers[i]]
            
            if outlier_subjects:
                results['site_outliers'][site_id] = outlier_subjects
                
        # Cross-site comparison
        if len(sites) > 1:
            site_means = {}
            
            for site_id, site_subjects in sites.items():
                site_indices = [idx for idx, _ in site_subjects]
                if len(site_indices) > 0:
                    site_features = features[site_indices]
                    site_means[site_id] = np.mean(site_features, axis=0)
                    
            # Detect sites with significantly different means
            if len(site_means) > 1:
                all_site_means = np.array(list(site_means.values()))
                overall_mean = np.mean(all_site_means, axis=0)
                overall_std = np.std(all_site_means, axis=0)
                
                for j, feature_name in enumerate(feature_names):
                    if overall_std[j] > 0:
                        site_z_scores = np.abs(
                            (all_site_means[:, j] - overall_mean[j]) / overall_std[j]
                        )
                        outlier_sites = [list(site_means.keys())[i] 
                                       for i in range(len(site_means)) 
                                       if site_z_scores[i] > 2.0]
                        
                        if outlier_sites:
                            if feature_name not in results['site_effects']:
                                results['site_effects'][feature_name] = []
                            results['site_effects'][feature_name].extend(outlier_sites)
                            
        return results
        
    def _combine_outlier_results(self, 
                               detection_results: Dict,
                               subjects: List[str]) -> Dict:
        """Combine results from multiple detection methods."""
        combined_results = {
            'subject_outliers': {},
            'outlier_summary': {
                'total_outliers': 0,
                'consensus_outliers': [],
                'method_agreement': {}
            }
        }
        
        # Count outlier detections per subject across methods
        outlier_counts = {subject: 0 for subject in subjects}
        method_detections = {}
        
        # Statistical methods
        for method_name, method_results in detection_results['statistical'].items():
            if isinstance(method_results, list):
                method_detections[method_name] = method_results
                for subject in method_results:
                    if subject in outlier_counts:
                        outlier_counts[subject] += 1
                        
        # ML methods
        for method_name, method_results in detection_results['machine_learning'].items():
            if isinstance(method_results, list):
                method_detections[method_name] = method_results
                for subject in method_results:
                    if subject in outlier_counts:
                        outlier_counts[subject] += 1
                        
        # Site-aware methods
        if detection_results.get('site_aware'):
            site_results = detection_results['site_aware']
            if 'site_outliers' in site_results:
                all_site_outliers = []
                for site_outliers in site_results['site_outliers'].values():
                    all_site_outliers.extend(site_outliers)
                method_detections['site_aware'] = all_site_outliers
                
                for subject in all_site_outliers:
                    if subject in outlier_counts:
                        outlier_counts[subject] += 1
                        
        # Determine consensus outliers (detected by multiple methods)
        consensus_threshold = max(2, len(method_detections) // 2)
        consensus_outliers = [subject for subject, count in outlier_counts.items() 
                            if count >= consensus_threshold]
        
        # Create subject-level outlier information
        for subject in subjects:
            if outlier_counts[subject] > 0:
                detected_by = [method for method, outliers in method_detections.items() 
                             if subject in outliers]
                
                combined_results['subject_outliers'][subject] = {
                    'detection_count': outlier_counts[subject],
                    'detected_by': detected_by,
                    'is_consensus': subject in consensus_outliers
                }
                
        # Summary statistics
        combined_results['outlier_summary'] = {
            'total_outliers': len([s for s in subjects if outlier_counts[s] > 0]),
            'consensus_outliers': consensus_outliers,
            'method_agreement': method_detections
        }
        
        return combined_results