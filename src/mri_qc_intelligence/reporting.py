"""QC report generation and visualization.

This module generates comprehensive QC reports in multiple formats
including HTML dashboards, JSON summaries, and CSV exports.
"""

from pathlib import Path
from typing import Dict, Any, Union, List, Optional
import json
import pandas as pd
from datetime import datetime
import logging

# Visualization imports (will be optional)
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    
logger = logging.getLogger(__name__)


class ReportGenerator:
    """QC report generator for multiple output formats.
    
    Generates:
    - HTML interactive dashboards
    - JSON summary reports
    - CSV data exports
    - Individual subject reports
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize report generator.
        
        Parameters
        ----------
        config : dict, optional
            Report generation configuration
        """
        self.config = config or {}
        
        # Report templates and styling
        self.html_template = self._get_html_template()
        
    def generate_report(self, 
                       qc_results: Dict[str, Any],
                       output_path: Union[str, Path],
                       report_type: str = 'html') -> None:
        """Generate QC report in specified format.
        
        Parameters
        ----------
        qc_results : dict
            Complete QC analysis results
        output_path : str or Path
            Output file path
        report_type : str
            Report format: 'html', 'json', or 'csv'
        """
        output_path = Path(output_path)
        
        logger.info(f"Generating {report_type.upper()} report: {output_path}")
        
        if report_type.lower() == 'html':
            self._generate_html_report(qc_results, output_path)
        elif report_type.lower() == 'json':
            self._generate_json_report(qc_results, output_path)
        elif report_type.lower() == 'csv':
            self._generate_csv_report(qc_results, output_path)
        else:
            raise ValueError(f"Unsupported report type: {report_type}")
            
    def _generate_html_report(self, 
                             qc_results: Dict[str, Any],
                             output_path: Path) -> None:
        """Generate interactive HTML dashboard."""
        # Create report content
        report_content = {
            'title': 'MRI Quality Control Report',
            'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'summary': self._create_summary_section(qc_results),
            'datasets_overview': self._create_dataset_overview(qc_results),
            'subject_details': self._create_subject_details(qc_results),
            'visualizations': self._create_visualizations(qc_results) if PLOTTING_AVAILABLE else None
        }
        
        # Generate HTML content
        html_content = self._render_html_template(report_content)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        logger.info(f"HTML report generated: {output_path}")
        
    def _generate_json_report(self, 
                             qc_results: Dict[str, Any],
                             output_path: Path) -> None:
        """Generate JSON summary report."""
        # Create JSON-serializable summary
        json_report = {
            'metadata': {
                'generation_time': datetime.now().isoformat(),
                'generator': 'MRI QC Intelligence Engine v0.1.0'
            },
            'dataset_summary': qc_results.get('scores', {}).get('dataset_summary', {}),
            'subject_scores': qc_results.get('scores', {}).get('subject_scores', {}),
            'outlier_analysis': qc_results.get('outliers', {}),
            'site_analysis': qc_results.get('scores', {}).get('site_summary', {})
        }
        
        # Convert numpy types to native Python types for JSON serialization
        json_report = self._convert_for_json(json_report)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)
            
        logger.info(f"JSON report generated: {output_path}")
        
    def _generate_csv_report(self, 
                            qc_results: Dict[str, Any],
                            output_path: Path) -> None:
        """Generate CSV data export."""
        # Create DataFrames for different data types
        dfs = []
        
        # Subject scores DataFrame
        subject_scores = qc_results.get('scores', {}).get('subject_scores', {})
        if subject_scores:
            scores_data = []
            for subject_id, scores in subject_scores.items():
                row = {'subject_id': subject_id}
                
                for modality, modality_data in scores.items():
                    if isinstance(modality_data, dict) and 'composite_score' in modality_data:
                        row[f'{modality}_score'] = modality_data['composite_score']
                        row[f'{modality}_rating'] = modality_data.get('quality_rating', '')
                        
                scores_data.append(row)
                
            if scores_data:
                scores_df = pd.DataFrame(scores_data)
                dfs.append(('subject_scores', scores_df))
                
        # Raw metrics DataFrame
        dataset_metrics = qc_results.get('dataset_metrics', {})
        if dataset_metrics:
            metrics_data = []
            for subject_id, subject_metrics in dataset_metrics.items():
                row = {'subject_id': subject_id}
                
                for modality, metrics in subject_metrics.items():
                    for metric_name, value in metrics.items():
                        row[f'{modality}_{metric_name}'] = value
                        
                metrics_data.append(row)
                
            if metrics_data:
                metrics_df = pd.DataFrame(metrics_data)
                dfs.append(('raw_metrics', metrics_df))
                
        # Outlier information DataFrame
        outliers = qc_results.get('outliers', {}).get('subject_outliers', {})
        if outliers:
            outlier_data = []
            for subject_id, outlier_info in outliers.items():
                row = {
                    'subject_id': subject_id,
                    'detection_count': outlier_info.get('detection_count', 0),
                    'is_consensus': outlier_info.get('is_consensus', False),
                    'detected_by': ', '.join(outlier_info.get('detected_by', []))
                }
                outlier_data.append(row)
                
            if outlier_data:
                outlier_df = pd.DataFrame(outlier_data)
                dfs.append(('outliers', outlier_df))
                
        # Write to CSV files
        if output_path.suffix == '.csv':
            # Single CSV file - combine all data
            if dfs:
                combined_df = dfs[0][1]  # Start with first DataFrame
                for name, df in dfs[1:]:
                    combined_df = pd.merge(combined_df, df, on='subject_id', how='outer')
                combined_df.to_csv(output_path, index=False)
        else:
            # Multiple CSV files
            output_dir = output_path
            output_dir.mkdir(parents=True, exist_ok=True)
            
            for name, df in dfs:
                csv_path = output_dir / f'{name}.csv'
                df.to_csv(csv_path, index=False)
                
        logger.info(f"CSV report(s) generated: {output_path}")
        
    def _create_summary_section(self, qc_results: Dict[str, Any]) -> Dict:
        """Create executive summary section."""
        dataset_summary = qc_results.get('scores', {}).get('dataset_summary', {})
        
        summary = {
            'total_subjects': dataset_summary.get('total_subjects', 0),
            'quality_distribution': dataset_summary.get('quality_distribution', {}),
            'modalities_analyzed': list(dataset_summary.get('modality_stats', {}).keys()),
            'outliers_detected': len(qc_results.get('outliers', {}).get('subject_outliers', {})),
            'consensus_outliers': len(qc_results.get('outliers', {}).get('outlier_summary', {}).get('consensus_outliers', []))
        }
        
        return summary
        
    def _create_dataset_overview(self, qc_results: Dict[str, Any]) -> Dict:
        """Create dataset overview section."""
        return {
            'modality_statistics': qc_results.get('scores', {}).get('dataset_summary', {}).get('modality_stats', {}),
            'site_statistics': qc_results.get('scores', {}).get('site_summary', {}),
            'outlier_summary': qc_results.get('outliers', {}).get('outlier_summary', {})
        }
        
    def _create_subject_details(self, qc_results: Dict[str, Any]) -> List[Dict]:
        """Create detailed subject information."""
        subject_details = []
        
        subject_scores = qc_results.get('scores', {}).get('subject_scores', {})
        outliers = qc_results.get('outliers', {}).get('subject_outliers', {})
        
        for subject_id, scores in subject_scores.items():
            detail = {
                'subject_id': subject_id,
                'modality_scores': {},
                'overall_score': scores.get('overall', {}).get('composite_score', 0),
                'overall_rating': scores.get('overall', {}).get('quality_rating', ''),
                'is_outlier': subject_id in outliers,
                'outlier_info': outliers.get(subject_id, {})
            }
            
            for modality, modality_data in scores.items():
                if modality != 'overall':
                    detail['modality_scores'][modality] = {
                        'score': modality_data.get('composite_score', 0),
                        'rating': modality_data.get('quality_rating', '')
                    }
                    
            subject_details.append(detail)
            
        return sorted(subject_details, key=lambda x: x['overall_score'], reverse=True)
        
    def _create_visualizations(self, qc_results: Dict[str, Any]) -> Dict:
        """Create visualizations for the report."""
        if not PLOTTING_AVAILABLE:
            return {}
            
        visualizations = {}
        
        try:
            # Score distribution plot
            visualizations['score_distribution'] = self._create_score_distribution_plot(qc_results)
            
            # Quality rating pie chart
            visualizations['quality_pie_chart'] = self._create_quality_pie_chart(qc_results)
            
            # Modality comparison plot
            visualizations['modality_comparison'] = self._create_modality_comparison_plot(qc_results)
            
            # Site comparison plot (if applicable)
            if qc_results.get('scores', {}).get('site_summary'):
                visualizations['site_comparison'] = self._create_site_comparison_plot(qc_results)
                
        except Exception as e:
            logger.warning(f"Visualization creation failed: {e}")
            
        return visualizations
        
    def _create_score_distribution_plot(self, qc_results: Dict[str, Any]) -> str:
        """Create score distribution histogram."""
        subject_scores = qc_results.get('scores', {}).get('subject_scores', {})
        
        overall_scores = [scores.get('overall', {}).get('composite_score', 0) 
                         for scores in subject_scores.values() 
                         if 'overall' in scores]
        
        if not overall_scores:
            return ""
            
        fig = go.Figure(data=[go.Histogram(x=overall_scores, nbinsx=20)])
        fig.update_layout(
            title='Distribution of Overall QC Scores',
            xaxis_title='QC Score',
            yaxis_title='Number of Subjects',
            showlegend=False
        )
        
        return fig.to_html(include_plotlyjs='cdn', div_id='score_distribution')
        
    def _create_quality_pie_chart(self, qc_results: Dict[str, Any]) -> str:
        """Create quality rating pie chart."""
        quality_dist = qc_results.get('scores', {}).get('dataset_summary', {}).get('quality_distribution', {})
        
        if not quality_dist:
            return ""
            
        labels = list(quality_dist.keys())
        values = list(quality_dist.values())
        
        fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
        fig.update_layout(title='Quality Rating Distribution')
        
        return fig.to_html(include_plotlyjs='cdn', div_id='quality_pie')
        
    def _create_modality_comparison_plot(self, qc_results: Dict[str, Any]) -> str:
        """Create modality score comparison plot."""
        modality_stats = qc_results.get('scores', {}).get('dataset_summary', {}).get('modality_stats', {})
        
        if not modality_stats:
            return ""
            
        modalities = list(modality_stats.keys())
        mean_scores = [stats['mean_score'] for stats in modality_stats.values()]
        std_scores = [stats['std_score'] for stats in modality_stats.values()]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='Mean Score',
            x=modalities,
            y=mean_scores,
            error_y=dict(type='data', array=std_scores)
        ))
        
        fig.update_layout(
            title='Mean QC Scores by Modality',
            xaxis_title='Modality',
            yaxis_title='QC Score',
            showlegend=False
        )
        
        return fig.to_html(include_plotlyjs='cdn', div_id='modality_comparison')
        
    def _create_site_comparison_plot(self, qc_results: Dict[str, Any]) -> str:
        """Create site comparison plot."""
        site_stats = qc_results.get('scores', {}).get('site_summary', {})
        
        if not site_stats:
            return ""
            
        sites = list(site_stats.keys())
        mean_scores = [stats['mean_score'] for stats in site_stats.values()]
        std_scores = [stats['std_score'] for stats in site_stats.values()]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='Mean Score',
            x=sites,
            y=mean_scores,
            error_y=dict(type='data', array=std_scores)
        ))
        
        fig.update_layout(
            title='Mean QC Scores by Site',
            xaxis_title='Site',
            yaxis_title='QC Score',
            showlegend=False
        )
        
        return fig.to_html(include_plotlyjs='cdn', div_id='site_comparison')
        
    def _get_html_template(self) -> str:
        """Get HTML template for report generation."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{title}}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; }
        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .summary-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #667eea; }
        .summary-card h3 { margin: 0 0 10px 0; color: #333; }
        .summary-card .value { font-size: 2em; font-weight: bold; color: #667eea; }
        .section { margin: 30px 0; }
        .section h2 { color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; font-weight: bold; }
        .pass { color: #28a745; font-weight: bold; }
        .warning { color: #ffc107; font-weight: bold; }
        .fail { color: #dc3545; font-weight: bold; }
        .visualization { margin: 20px 0; text-align: center; }
        .footer { text-align: center; margin-top: 30px; padding: 20px; background-color: #f8f9fa; border-radius: 8px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 {{title}}</h1>
            <p>Generated on {{generation_time}}</p>
        </div>
        
        {{content}}
        
        <div class="footer">
            <p>Generated by MRI QC Intelligence Engine v0.1.0 | <a href="https://github.com/patrick-filima/mri-qc-intelligence">GitHub</a></p>
        </div>
    </div>
</body>
</html>
        """
        
    def _render_html_template(self, report_content: Dict) -> str:
        """Render HTML template with report content."""
        # Simple template rendering (in production, use Jinja2 or similar)
        content_html = self._generate_html_content(report_content)
        
        html = self.html_template
        html = html.replace('{{title}}', report_content['title'])
        html = html.replace('{{generation_time}}', report_content['generation_time'])
        html = html.replace('{{content}}', content_html)
        
        return html
        
    def _generate_html_content(self, report_content: Dict) -> str:
        """Generate main HTML content sections."""
        content_parts = []
        
        # Summary section
        if 'summary' in report_content:
            content_parts.append(self._render_summary_section(report_content['summary']))
            
        # Visualizations
        if report_content.get('visualizations'):
            content_parts.append('<div class="section"><h2>📊 Data Visualizations</h2>')
            for viz_name, viz_html in report_content['visualizations'].items():
                if viz_html:
                    content_parts.append(f'<div class="visualization">{viz_html}</div>')
            content_parts.append('</div>')
            
        # Subject details table
        if 'subject_details' in report_content:
            content_parts.append(self._render_subject_table(report_content['subject_details']))
            
        return '\n'.join(content_parts)
        
    def _render_summary_section(self, summary: Dict) -> str:
        """Render summary section HTML."""
        html = ['<div class="section"><h2>📋 Executive Summary</h2>', '<div class="summary-grid">']
        
        # Total subjects card
        html.append(f'''
        <div class="summary-card">
            <h3>Total Subjects</h3>
            <div class="value">{summary.get('total_subjects', 0)}</div>
        </div>
        ''')
        
        # Quality distribution cards
        quality_dist = summary.get('quality_distribution', {})
        for rating, count in quality_dist.items():
            css_class = rating.lower()
            html.append(f'''
            <div class="summary-card">
                <h3>{rating}</h3>
                <div class="value {css_class}">{count}</div>
            </div>
            ''')
            
        # Outliers card
        html.append(f'''
        <div class="summary-card">
            <h3>Outliers Detected</h3>
            <div class="value">{summary.get('outliers_detected', 0)}</div>
        </div>
        ''')
        
        html.extend(['</div>', '</div>'])
        return '\n'.join(html)
        
    def _render_subject_table(self, subject_details: List[Dict]) -> str:
        """Render subject details table."""
        html = ['<div class="section"><h2>👥 Subject Details</h2>', '<table>']
        
        # Table header
        html.append('''
        <thead>
            <tr>
                <th>Subject ID</th>
                <th>Overall Score</th>
                <th>Quality Rating</th>
                <th>T1w Score</th>
                <th>fMRI Score</th>
                <th>DWI Score</th>
                <th>Outlier Status</th>
            </tr>
        </thead>
        <tbody>
        ''')
        
        # Table rows
        for subject in subject_details[:50]:  # Limit to first 50 subjects
            rating_class = subject['overall_rating'].lower()
            outlier_status = '🔍 Outlier' if subject['is_outlier'] else '✅ Normal'
            
            html.append(f'''
            <tr>
                <td>{subject['subject_id']}</td>
                <td>{subject['overall_score']:.1f}</td>
                <td><span class="{rating_class}">{subject['overall_rating']}</span></td>
                <td>{subject['modality_scores'].get('T1w', {}).get('score', 'N/A')}</td>
                <td>{subject['modality_scores'].get('bold', {}).get('score', 'N/A')}</td>
                <td>{subject['modality_scores'].get('dwi', {}).get('score', 'N/A')}</td>
                <td>{outlier_status}</td>
            </tr>
            ''')
            
        html.extend(['</tbody>', '</table>', '</div>'])
        return '\n'.join(html)
        
    def _convert_for_json(self, obj: Any) -> Any:
        """Convert numpy types to JSON-serializable types."""
        if isinstance(obj, dict):
            return {k: self._convert_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_for_json(item) for item in obj]
        elif hasattr(obj, 'item'):  # numpy scalar
            return obj.item()
        elif hasattr(obj, 'tolist'):  # numpy array
            return obj.tolist()
        else:
            return obj