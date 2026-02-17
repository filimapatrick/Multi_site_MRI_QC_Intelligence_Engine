"""Core QC Engine implementation.

This module contains the main QCEngine class that orchestrates the entire
MRI quality control analysis workflow.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union

import logging
from .data_loader import BIDSLoader
from .metrics import T1QCMetrics, FMRIQCMetrics, DWIQCMetrics
from .scoring import QCScorer
from .outlier_detection import OutlierDetector
from .reporting import ReportGenerator

logger = logging.getLogger(__name__)


class QCEngine:
    """Main QC Engine for automated MRI quality control analysis.
    
    This class orchestrates the entire QC workflow:
    1. Load and validate BIDS dataset
    2. Compute modality-specific QC metrics
    3. Generate standardized QC scores
    4. Detect outliers and site effects
    5. Generate comprehensive reports
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize QC Engine.
        
        Parameters
        ----------
        config_path : Path, optional
            Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.data_loader = BIDSLoader()
        self.metrics = {
            'T1w': T1QCMetrics(),
            'bold': FMRIQCMetrics(), 
            'dwi': DWIQCMetrics()
        }
        self.scorer = QCScorer(self.config.get('scoring', {}))
        self.outlier_detector = OutlierDetector()
        self.report_generator = ReportGenerator()
        
    def load_bids_dataset(self, bids_dir: Union[str, Path], auto_fix: bool = False) -> Dict:
        """Load and validate BIDS dataset.
        
        Parameters
        ----------
        bids_dir : str or Path
            Path to BIDS dataset
        auto_fix : bool, optional
            Whether to automatically fix BIDS structure issues
            
        Returns
        -------
        dict
            Loaded dataset information
        """
        logger.info(f"Loading BIDS dataset from {bids_dir}")
        return self.data_loader.load(bids_dir, auto_fix=auto_fix)
        
    def analyze(self, 
                dataset: Dict,
                modalities: Optional[List[str]] = None,
                subjects: Optional[List[str]] = None) -> Dict:
        """Run comprehensive QC analysis.
        
        Parameters
        ----------
        dataset : dict
            BIDS dataset information
        modalities : list of str, optional
            Modalities to analyze (default: all available)
        subjects : list of str, optional
            Subjects to analyze (default: all)
            
        Returns
        -------
        dict
            QC analysis results
        """
        logger.info("Starting QC analysis")
        
        if modalities is None:
            modalities = list(self.metrics.keys())
            
        bids_dir = Path(dataset['bids_dir'])
        subject_list = subjects if subjects else dataset['subjects']
        
        # Mapping for BIDS folders and suffixes
        modality_map = {
            'T1w': {'folder': 'anat', 'suffix': 'T1w'},
            'bold': {'folder': 'func', 'suffix': 'bold'},
            'dwi': {'folder': 'dwi', 'suffix': 'dwi'}
        }
        
        # Structure to hold raw metrics: subject -> modality -> metrics
        raw_metrics = {}
        
        for subject in subject_list:
            logger.info(f"Processing subject: {subject}")
            raw_metrics[subject] = {}
            
            for modality in modalities:
                if modality not in self.metrics:
                    continue
                    
                info = modality_map.get(modality)
                if not info:
                    continue
                    
                # Construct path search strategy
                subject_dir = bids_dir / subject
                modality_dir = subject_dir / info['folder']
                
                if not modality_dir.exists():
                    continue
                    
                # Find matching file (using glob for robustness)
                files = list(modality_dir.glob(f"*{info['suffix']}.nii.gz"))
                
                if not files:
                    logger.warning(f"No {modality} file found for {subject}")
                    continue
                    
                # Take first file found
                file_path = files[0]
                
                try:
                    logger.info(f"Computing {modality} metrics for {subject}")
                    
                    # Compute metrics based on modality type
                    if modality == 'T1w':
                        metric_results = self.metrics[modality].compute(file_path)
                    elif modality == 'bold':
                         # TODO: Add motion params finding
                        metric_results = self.metrics[modality].compute(file_path)
                    elif modality == 'dwi':
                        # TODO: Add bval/bvec finding
                        bval_files = list(modality_dir.glob(f"*{info['suffix']}.bval"))
                        bvec_files = list(modality_dir.glob(f"*{info['suffix']}.bvec"))
                        bval_path = bval_files[0] if bval_files else None
                        bvec_path = bvec_files[0] if bvec_files else None
                        
                        metric_results = self.metrics[modality].compute(
                            file_path, 
                            bval_path=bval_path, 
                            bvec_path=bvec_path
                        )
                    else:
                        metric_results = self.metrics[modality].compute(file_path)
                    
                    raw_metrics[subject][modality] = metric_results
                    
                    # Log computed metrics
                    logger.info(f"📊 {subject} {modality} Metrics Computed:")
                    for key, value in metric_results.items():
                        if isinstance(value, float):
                            logger.info(f"   - {key}: {value:.4f}")
                        else:
                            logger.info(f"   - {key}: {value}")
                            
                except Exception as e:
                    logger.error(f"Failed to compute {modality} metrics for {subject}: {e}")
                
        # Compute scoring and detection
        scores = self.scorer.compute_scores(raw_metrics)
        outliers = self.outlier_detector.detect_outliers(raw_metrics, scores)
        
        return {
            'dataset_metrics': raw_metrics,
            'scores': scores,
            'outliers': outliers
        }
        
    def generate_report(self, results: Dict, output_path: Union[str, Path]):
        """Generate QC report.
        
        Parameters
        ----------
        results : dict
            QC analysis results
        output_path : str or Path
            Output path for report
        """
        logger.info(f"Generating report at {output_path}")
        self.report_generator.generate_report(results, output_path)
        
    def _load_config(self, config_path: Optional[Path]) -> Dict:
        """Load configuration file."""
        if config_path is None:
            return {}
        # TODO: Implement YAML config loading
        return {}