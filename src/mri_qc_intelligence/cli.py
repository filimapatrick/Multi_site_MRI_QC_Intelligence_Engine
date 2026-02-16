"""Command Line Interface for MRI QC Intelligence Engine.

This module provides the main CLI entry point for the QC engine.
"""

import click
from pathlib import Path
from typing import List, Optional

from .core import QCEngine
import logging


@click.command()
@click.option('--bids-dir', 
              type=click.Path(exists=True, path_type=Path),
              required=True,
              help='Path to BIDS dataset directory')
@click.option('--output-dir',
              type=click.Path(path_type=Path),
              default='./qc_reports',
              help='Output directory for QC reports')
@click.option('--modality',
              type=click.Choice(['T1w', 'bold', 'dwi', 'all']),
              multiple=True,
              default=['all'],
              help='MRI modalities to analyze')
@click.option('--subjects',
              help='Comma-separated list of subject IDs to analyze')
@click.option('--format',
              'report_format',
              type=click.Choice(['html', 'json', 'csv']),
              multiple=True,
              default=['html'],
              help='Report output formats')
@click.option('--config',
              type=click.Path(exists=True, path_type=Path),
              help='Path to configuration file')
@click.option('--multi-site',
              is_flag=True,
              help='Enable multi-site analysis')
@click.option('--detect-outliers',
              is_flag=True, 
              help='Enable outlier detection')
@click.option('--verbose', '-v',
              is_flag=True,
              help='Enable verbose logging')
def main(bids_dir: Path,
         output_dir: Path,
         modality: tuple,
         subjects: Optional[str],
         report_format: tuple,
         config: Optional[Path],
         multi_site: bool,
         detect_outliers: bool,
         verbose: bool):
    """Run automated MRI Quality Control analysis.
    
    This tool performs comprehensive quality control analysis on BIDS-formatted
    MRI datasets, computing quality metrics, standardized scores, and generating
    detailed reports.
    
    Examples:
    
        # Basic analysis for all modalities
        qc_engine --bids-dir /path/to/dataset
        
        # T1-weighted only with custom output
        qc_engine --bids-dir /data --modality T1w --output-dir ./reports
        
        # Multi-site analysis with outlier detection
        qc_engine --bids-dir /data --multi-site --detect-outliers
    """
    
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize QC Engine
        logger.info("Initializing MRI QC Intelligence Engine")
        engine = QCEngine(config_path=config)
        
        # Load BIDS dataset
        dataset = engine.load_bids_dataset(bids_dir)
        
        # Process modality selection
        if 'all' in modality:
            modalities = None  # Use all available
        else:
            modalities = list(modality)
            
        # Process subject selection
        subject_list = None
        if subjects:
            subject_list = [s.strip() for s in subjects.split(',')]
            
        # Run QC analysis
        logger.info("Starting QC analysis...")
        results = engine.analyze(
            dataset=dataset,
            modalities=modalities,
            subjects=subject_list
        )
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate reports
        for fmt in report_format:
            report_path = output_dir / f"qc_report.{fmt}"
            logger.info(f"Generating {fmt.upper()} report: {report_path}")
            engine.generate_report(results, report_path)
            
        logger.info("QC analysis completed successfully!")
        click.echo(f"\n✅ QC analysis completed!")
        click.echo(f"📊 Reports generated in: {output_dir}")
        
    except Exception as e:
        logger.error(f"QC analysis failed: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
        
        
if __name__ == '__main__':
    main()