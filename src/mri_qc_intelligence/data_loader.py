"""BIDS dataset loading and validation.

This module handles:
- BIDS dataset validation
- Metadata extraction
- Modality detection
- File organization
"""

from pathlib import Path
from typing import Dict, List, Optional, Union

import logging
import pandas as pd

# TODO: Add pybids import once implemented
# from bids import BIDSLayout
import shutil
import gzip
import json

logger = logging.getLogger(__name__)


class BIDSLoader:
    """BIDS dataset loader and validator."""
    
    def __init__(self):
        """Initialize BIDS loader."""
        self.layout = None
        
    def load(self, bids_dir: Union[str, Path], auto_fix: bool = False) -> Dict:
        """Load and validate BIDS dataset.
        
        Parameters
        ----------
        bids_dir : str or Path
            Path to BIDS dataset
            
        Returns
        -------
        dict
            Dataset information including:
            - subjects: List of subject IDs
            - sessions: List of session IDs
            - modalities: Available modalities
            - metadata: Acquisition parameters
        """
        bids_path = Path(bids_dir)
        
        if not bids_path.exists():
            raise FileNotFoundError(f"BIDS directory not found: {bids_path}")
            
        if auto_fix:
            self._check_and_fix_bids_structure(bids_path)
            
        logger.info(f"Loading BIDS dataset: {bids_path}")
        
        # TODO: Implement actual BIDS loading with pybids
        # self.layout = BIDSLayout(bids_path)
        
        # Placeholder implementation
        dataset_info = {
            'bids_dir': str(bids_path),
            'subjects': self._get_subjects(bids_path),
            'sessions': self._get_sessions(bids_path),
            'modalities': self._detect_modalities(bids_path),
            'metadata': self._extract_metadata(bids_path)
        }
        
        self._validate_dataset(dataset_info)
        
        return dataset_info
        
    def _get_subjects(self, bids_path: Path) -> List[str]:
        """Extract subject IDs from BIDS dataset."""
        # TODO: Implement subject detection
        subjects_dirs = [d for d in bids_path.iterdir() 
                        if d.is_dir() and d.name.startswith('sub-')]
        return [d.name for d in subjects_dirs]
        
    def _get_sessions(self, bids_path: Path) -> List[str]:
        """Extract session IDs from BIDS dataset."""
        # TODO: Implement session detection
        sessions = set()
        for sub_dir in bids_path.glob('sub-*'):
            for ses_dir in sub_dir.glob('ses-*'):
                sessions.add(ses_dir.name)
        return list(sessions)
        
    def _detect_modalities(self, bids_path: Path) -> List[str]:
        """Detect available MRI modalities."""
        modalities = set()
        
        # Look for common MRI file patterns
        for nii_file in bids_path.rglob('*.nii.gz'):
            if '_T1w.nii.gz' in nii_file.name:
                modalities.add('T1w')
            elif '_bold.nii.gz' in nii_file.name:
                modalities.add('bold')
            elif '_dwi.nii.gz' in nii_file.name:
                modalities.add('dwi')
                
        return list(modalities)
        
    def _extract_metadata(self, bids_path: Path) -> Dict:
        """Extract acquisition metadata from JSON sidecars."""
        # TODO: Implement comprehensive metadata extraction
        metadata = {
            'acquisition_params': {},
            'scanner_info': {},
            'participants': self._load_participants_tsv(bids_path)
        }
        
        return metadata
        
    def _load_participants_tsv(self, bids_path: Path) -> Optional[pd.DataFrame]:
        """Load participants.tsv file."""
        participants_file = bids_path / 'participants.tsv'
        if participants_file.exists():
            return pd.read_csv(participants_file, sep='\t')
        return None
        
    def _validate_dataset(self, dataset_info: Dict):
        """Validate BIDS dataset structure and content."""
        if not dataset_info['subjects']:
            raise ValueError("No subjects found in BIDS dataset")
            
        if not dataset_info['modalities']:
            raise ValueError("No supported MRI modalities found")
            
        logger.info(
            f"Validated BIDS dataset: "
            f"{len(dataset_info['subjects'])} subjects, "
            f"modalities: {dataset_info['modalities']}"
        )

    def _check_and_fix_bids_structure(self, root_path: Path):
        """Check for flat structure and reorganize into BIDS format."""
        
        # Check if anatomy folder exists but is flat
        anat_source = root_path / "anat"
        if not anat_source.exists():
            return
            
        # Check if it contains flat files that look like subjects
        flat_files = list(anat_source.glob("sub-*_T1w.nii")) + list(anat_source.glob("sub-*_T1w.nii.gz"))
        if not flat_files:
            return
            
        logger.info(f"Found flat anatomy directory with {len(flat_files)} files. Reorganizing...")
        
        # Create dataset_description.json if missing
        desc_file = root_path / "dataset_description.json"
        if not desc_file.exists():
            description = {
                "Name": "Auto-Reorganized Dataset",
                "BIDSVersion": "1.6.0",
                "Authors": ["MRI QC Intelligence Engine"]
            }
            with open(desc_file, "w") as f:
                json.dump(description, f, indent=4)
        
        moved_count = 0
        for file_path in flat_files:
            filename = file_path.name
            parts = filename.split('_')
            subject_id = next((p for p in parts if p.startswith('sub-')), None)
            
            if not subject_id:
                continue
                
            target_dir = root_path / subject_id / "anat"
            target_dir.mkdir(parents=True, exist_ok=True)
            
            if filename.endswith(".nii"):
                target_filename = filename + ".gz"
                target_path = target_dir / target_filename
                with open(file_path, 'rb') as f_in:
                    with gzip.open(target_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                file_path.unlink()
            else:
                target_path = target_dir / filename
                shutil.move(str(file_path), str(target_path))
                
            moved_count += 1
            
        # Cleanup
        if not any(anat_source.iterdir()):
            anat_source.rmdir()
            
        logger.info(f"Reorganized {moved_count} files into BIDS format")