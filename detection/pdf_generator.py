# pdf_generator.py
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus import Image as RLImage
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.widgets.markers import makeMarker

class PDFReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.doc = None  # Will be set during report generation
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the report"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#00FF9C'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#60A5FA'),
            spaceAfter=20,
            spaceBefore=10
        ))
        
        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#FACC15'),
            spaceAfter=12,
            spaceBefore=8,
            borderPadding=(0, 0, 0, 8),
            borderWidth=0,
            borderColor=colors.HexColor('#FACC15'),
            borderBottomWidth=2
        ))
        
        # Body text
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#D1D5DB'),
            spaceAfter=6,
            leading=14
        ))
        
        # Metric value
        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['Normal'],
            fontSize=28,
            textColor=colors.HexColor('#00FF9C'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Metric label
        self.styles.add(ParagraphStyle(
            name='MetricLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#9CA3AF'),
            alignment=TA_CENTER
        ))
        
    def generate_report(self, analysis_data, recommendations, logo_path=None):
        """
        Generate PDF report from analysis data
        
        Args:
            analysis_data: Dictionary containing analysis results
            recommendations: List of recommendation dictionaries
            logo_path: Optional path to logo image
        
        Returns:
            BytesIO buffer containing PDF data
        """
        buffer = io.BytesIO()
        
        # Create the PDF document
        self.doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        # Build the story (content)
        story = []
        
        # Add header
        story.extend(self._create_header(analysis_data))
        story.append(Spacer(1, 10*mm))
        
        # Add metrics overview
        story.extend(self._create_metrics_overview(analysis_data))
        story.append(Spacer(1, 8*mm))
        
        # Add severity distribution
        story.extend(self._create_severity_section(analysis_data))
        story.append(Spacer(1, 8*mm))
        
        # Add frequent objects section
        story.extend(self._create_frequent_objects_section(analysis_data))
        story.append(Spacer(1, 8*mm))
        
        # Add hourly pattern chart
        story.extend(self._create_hourly_pattern_section(analysis_data))
        story.append(PageBreak())
        
        # Add recommendations section
        story.extend(self._create_recommendations_section(recommendations))
        story.append(Spacer(1, 10*mm))
        
        # Add footer
        story.extend(self._create_footer())
        
        # Build PDF
        self.doc.build(story)
        
        buffer.seek(0)
        return buffer
    
    def _create_header(self, data):
        """Create report header"""
        elements = []
        
        # Title
        title = Paragraph("SmartGlass AI Detection Report", self.styles['CustomTitle'])
        elements.append(title)
        
        # Report metadata
        meta_style = ParagraphStyle(
            'Meta',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6B7280'),
            alignment=TA_CENTER
        )
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        period = f"Analysis Period: {data.get('first_detection', 'N/A')} to {data.get('last_detection', 'N/A')}"
        
        elements.append(Paragraph(f"Generated: {timestamp}", meta_style))
        elements.append(Paragraph(period, meta_style))
        
        return elements
    
    def _create_metrics_overview(self, data):
        """Create metrics overview cards"""
        elements = []
        
        elements.append(Paragraph("Executive Summary", self.styles['CustomSubtitle']))
        
        # Calculate available width for columns
        page_width = self.doc.width
        col_width = (page_width / 4.0) - 5
        
        # Create metrics table
        metrics_data = [
            [
                self._create_metric_cell("Total Detections", str(data.get('total_detections', 0)), colors.HexColor('#00FF9C')),
                self._create_metric_cell("Unique Objects", str(data.get('unique_objects', 0)), colors.HexColor('#60A5FA')),
                self._create_metric_cell("Risk Score", f"{data.get('risk_score', 0):.1f}", self._get_risk_color(data.get('risk_score', 0))),
                self._create_metric_cell("High Risk Hours", str(len(data.get('high_risk_hours', []))), colors.HexColor('#F87171'))
            ]
        ]
        
        table = Table(metrics_data, colWidths=[col_width] * 4)
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1F2937')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#374151')),
        ]))
        
        elements.append(table)
        return elements
    
    def _create_metric_cell(self, label, value, color):
        """Create a metric cell with label and value"""
        # Create temporary styles with the specified color
        value_style = ParagraphStyle(
            'TempValue',
            parent=self.styles['MetricValue'],
            textColor=color
        )
        
        return [
            Paragraph(value, value_style),
            Spacer(1, 2),
            Paragraph(label, self.styles['MetricLabel'])
        ]
    
    def _create_severity_section(self, data):
        """Create severity distribution section with pie chart"""
        elements = []
        
        elements.append(Paragraph("Severity Distribution", self.styles['SectionHeader']))
        
        severity_data = data.get('severity_distribution', {})
        if severity_data:
            # Create pie chart
            drawing = Drawing(400, 200)
            pie = Pie()
            pie.x = 150
            pie.y = 50
            pie.width = 150
            pie.height = 150
            
            # Prepare data
            labels = []
            values = []
            colors_list = []
            
            severity_map = {
                '4': ('Critical', colors.HexColor('#F87171')),
                '3': ('High', colors.HexColor('#FB923C')),
                '2': ('Medium', colors.HexColor('#FACC15')),
                '1': ('Low', colors.HexColor('#94A3B8'))
            }
            
            for sev, (label, color) in severity_map.items():
                count = severity_data.get(sev, 0)
                if count > 0:
                    labels.append(f"{label} ({count})")
                    values.append(count)
                    colors_list.append(color)
            
            if values:
                pie.data = values
                pie.labels = labels
                pie.slices.strokeWidth = 1
                pie.slices.strokeColor = colors.HexColor('#1F2937')
                pie.slices.labelRadius = 1.2
                
                for i, color in enumerate(colors_list):
                    pie.slices[i].fillColor = color
                
                drawing.add(pie)
                elements.append(drawing)
            else:
                elements.append(Paragraph("No severity data available", self.styles['CustomBody']))
        else:
            elements.append(Paragraph("No severity data available", self.styles['CustomBody']))
        
        return elements
    
    def _create_frequent_objects_section(self, data):
        """Create frequent objects bar chart"""
        elements = []
        
        elements.append(Paragraph("Most Frequent Obstacles", self.styles['SectionHeader']))
        
        frequent_objects = data.get('frequent_objects', [])[:5]  # Top 5
        if frequent_objects:
            # Create bar chart
            drawing = Drawing(500, 250)
            bc = VerticalBarChart()
            bc.x = 80
            bc.y = 50
            bc.width = 380
            bc.height = 150
            
            # Prepare data
            objects = [obj['object'][:15] + '...' if len(obj['object']) > 15 else obj['object'] 
                      for obj in frequent_objects]
            counts = [obj['count'] for obj in frequent_objects]
            
            bc.data = [counts]
            bc.categoryAxis.categoryNames = objects
            bc.categoryAxis.labels.angle = 45
            bc.categoryAxis.labels.fontSize = 8
            bc.categoryAxis.labels.fillColor = colors.HexColor('#9CA3AF')
            bc.categoryAxis.labels.dx = -5
            bc.categoryAxis.labels.dy = -5
            
            bc.valueAxis.valueMin = 0
            bc.valueAxis.valueMax = max(counts) * 1.2 if counts else 10
            bc.valueAxis.valueStep = max(1, int(max(counts) / 5)) if counts else 2
            bc.valueAxis.labels.fontSize = 8
            bc.valueAxis.labels.fillColor = colors.HexColor('#9CA3AF')
            
            bc.bars[0].fillColor = colors.HexColor('#FACC15')
            bc.bars[0].strokeColor = colors.HexColor('#1F2937')
            bc.bars[0].strokeWidth = 1
            
            # Add value labels on bars
            bc.barLabels.nudge = 5
            bc.barLabels.fontSize = 8
            bc.barLabels.fillColor = colors.white
            
            drawing.add(bc)
            elements.append(drawing)
        else:
            elements.append(Paragraph("No object frequency data available", self.styles['CustomBody']))
        
        return elements
    
    def _create_hourly_pattern_section(self, data):
        """Create hourly pattern line chart"""
        elements = []
        
        elements.append(Paragraph("Hourly Activity Pattern", self.styles['SectionHeader']))
        
        hourly_data = data.get('hourly_pattern', {})
        if hourly_data:
            # Create line chart
            drawing = Drawing(500, 250)
            lc = HorizontalLineChart()
            lc.x = 80
            lc.y = 50
            lc.width = 380
            lc.height = 150
            
            # Prepare data
            hours = list(range(24))
            counts = [hourly_data.get(str(h), 0) for h in hours]
            
            lc.data = [counts]
            lc.categoryAxis.categoryNames = [str(h) if h % 3 == 0 else '' for h in hours]
            lc.categoryAxis.labels.fontSize = 7
            lc.categoryAxis.labels.fillColor = colors.HexColor('#9CA3AF')
            
            lc.valueAxis.valueMin = 0
            lc.valueAxis.valueMax = max(counts) * 1.2 if max(counts) > 0 else 10
            lc.valueAxis.valueStep = max(1, int(max(counts) / 5)) if max(counts) > 0 else 2
            lc.valueAxis.labels.fontSize = 8
            lc.valueAxis.labels.fillColor = colors.HexColor('#9CA3AF')
            
            lc.lines[0].strokeColor = colors.HexColor('#00FF9C')
            lc.lines[0].strokeWidth = 2
            lc.lines[0].symbol = makeMarker('FilledCircle')
            
            drawing.add(lc)
            elements.append(drawing)
            
            # Add risk level indicators
            if any(counts):
                avg_activity = sum(counts) / len([c for c in counts if c > 0])
                elements.append(Spacer(1, 10))
                
                legend_style = ParagraphStyle(
                    'Legend',
                    parent=self.styles['Normal'],
                    fontSize=8,
                    textColor=colors.HexColor('#9CA3AF')
                )
                
                elements.append(Paragraph(
                    f"<font color='#00FF9C'>●</font> Low Activity (&lt; {avg_activity:.0f})  "
                    f"<font color='#FACC15'>●</font> Medium Activity  "
                    f"<font color='#F87171'>●</font> High Activity (&gt; {avg_activity*1.5:.0f})",
                    legend_style
                ))
        else:
            elements.append(Paragraph("No hourly pattern data available", self.styles['CustomBody']))
        
        return elements
    
    def _create_recommendations_section(self, recommendations):
        """Create recommendations section"""
        elements = []
        
        elements.append(Paragraph("Caregiver Recommendations", self.styles['SectionHeader']))
        
        if recommendations:
            rec_data = []
            
            # Add headers
            rec_data.append([
                Paragraph('<b>Priority</b>', self.styles['CustomBody']),
                Paragraph('<b>Recommendation</b>', self.styles['CustomBody'])
            ])
            
            # Add recommendations
            for rec in recommendations:
                priority_color = {
                    'high': '#F87171',
                    'medium': '#FACC15',
                    'low': '#00FF9C'
                }.get(rec.get('priority', 'low'), '#00FF9C')
                
                priority_text = f'<font color="{priority_color}"><b>{rec.get("priority", "low").upper()}</b></font>'
                
                rec_data.append([
                    Paragraph(priority_text, self.styles['CustomBody']),
                    Paragraph(rec.get('message', ''), self.styles['CustomBody'])
                ])
            
            # Create table
            col_width = self.doc.width - 100
            table = Table(rec_data, colWidths=[80, col_width])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#374151')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#4B5563')),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            elements.append(table)
        else:
            elements.append(Paragraph("No recommendations available", self.styles['CustomBody']))
        
        return elements
    
    def _create_footer(self):
        """Create report footer"""
        elements = []
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#6B7280'),
            alignment=TA_CENTER
        )
        
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(
            "SmartGlass AI Detection System - Confidential Report<br/>"
            "Generated automatically by Vision Agent system",
            footer_style
        ))
        
        return elements
    
    def _get_risk_color(self, risk_score):
        """Get color based on risk score"""
        if risk_score > 3:
            return colors.HexColor('#F87171')
        elif risk_score > 2:
            return colors.HexColor('#FACC15')
        else:
            return colors.HexColor('#00FF9C')




# Add to pdf_generator.py after the PDFReportGenerator class

class LogPDFGenerator:
    """Generate PDF export of detection log with current filters"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_styles()
    
    def _setup_styles(self):
        """Setup custom styles for log PDF"""
        self.styles.add(ParagraphStyle(
            name='LogTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#00FF9C'),
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='LogHeader',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#9CA3AF'),
            alignment=TA_LEFT
        ))
        
        self.styles.add(ParagraphStyle(
            name='LogCell',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#D1D5DB'),
            alignment=TA_LEFT,
            leading=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='LogCellCenter',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#D1D5DB'),
            alignment=TA_CENTER,
            leading=12
        ))
    
    def generate_log_pdf(self, events, filters=None):
        """
        Generate PDF from detection log events
        
        Args:
            events: List of detection event dictionaries
            filters: Dictionary of applied filters
        
        Returns:
            BytesIO buffer containing PDF data
        """
        buffer = io.BytesIO()
        
        # Use landscape for better table fit
        from reportlab.lib.pagesizes import landscape, A4
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )
        
        story = []
        
        # Title
        story.append(Paragraph("SmartGlass Detection Log", self.styles['LogTitle']))
        
        # Metadata
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        story.append(Paragraph(f"Generated: {timestamp}", self.styles['LogHeader']))
        
        # Filters applied
        if filters:
            filter_text = "Filters: "
            if filters.get('search'):
                filter_text += f"Search: '{filters['search']}' | "
            if filters.get('severity'):
                sev_labels = {'1':'Low', '2':'Medium', '3':'High', '4':'Critical'}
                filter_text += f"Severity: {sev_labels.get(str(filters['severity']), filters['severity'])} | "
            if filters.get('source'):
                filter_text += f"Model: {filters['source']} | "
            if filters.get('device_id'):
                filter_text += f"Device: {filters['device_id']} | "
            
            filter_text = filter_text.rstrip(' | ')
            story.append(Paragraph(filter_text, self.styles['LogHeader']))
        
        story.append(Paragraph(f"Total Records: {len(events)}", self.styles['LogHeader']))
        story.append(Spacer(1, 5*mm))
        
        # Create table
        table_data = self._create_log_table(events)
        table = Table(table_data, colWidths=[60, 45, 80, 50, 55, 65, 60, 65, 200])
        table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F2937')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#00FF9C')),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#374151')),
            
            # Row styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#111827')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#111827'), colors.HexColor('#1F2937')]),
            
            # Cell alignment
            ('ALIGN', (0, 1), (1, -1), 'CENTER'),  # Date, Time
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Confidence
            ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Severity
            ('ALIGN', (6, 1), (6, -1), 'CENTER'),  # Model
            ('ALIGN', (7, 1), (7, -1), 'CENTER'),  # Device
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            
            # Font size
            ('FONTSIZE', (0, 1), (-1, -1), 7),
        ]))
        
        story.append(table)
        
        # Footer
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph(
            f"SmartGlass AI Detection System - Page 1 of 1",
            self.styles['LogHeader']
        ))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def _create_log_table(self, events):
        """Create table data for log PDF"""
        # Headers
        table_data = [[
            Paragraph('<b>Date</b>', self.styles['LogCellCenter']),
            Paragraph('<b>Time</b>', self.styles['LogCellCenter']),
            Paragraph('<b>Object</b>', self.styles['LogCell']),
            Paragraph('<b>Conf</b>', self.styles['LogCellCenter']),
            Paragraph('<b>Severity</b>', self.styles['LogCellCenter']),
            Paragraph('<b>Category</b>', self.styles['LogCell']),
            Paragraph('<b>Model</b>', self.styles['LogCellCenter']),
            Paragraph('<b>Device</b>', self.styles['LogCellCenter']),
            Paragraph('<b>AI Agent Note</b>', self.styles['LogCell']),
        ]]
        
        # Data rows
        for event in events:
            # Format severity with color
            sev_color = {
                1: '#94A3B8',  # Low - gray
                2: '#FACC15',  # Medium - yellow
                3: '#FB923C',  # High - orange
                4: '#F87171',  # Critical - red
            }.get(event.get('severity', 1), '#94A3B8')
            
            sev_label = event.get('sev_label', 'Low')
            
            # Format confidence
            conf = f"{event.get('conf', 0) * 100:.0f}%" if isinstance(event.get('conf'), float) else f"{event.get('conf', 0)}%"
            
            # Truncate agent note
            agent_note = event.get('agent', '') or '—'
            if len(agent_note) > 50:
                agent_note = agent_note[:47] + '...'
            
            table_data.append([
                Paragraph(event.get('date', ''), self.styles['LogCellCenter']),
                Paragraph(event.get('time', ''), self.styles['LogCellCenter']),
                Paragraph(event.get('object', ''), self.styles['LogCell']),
                Paragraph(conf, self.styles['LogCellCenter']),
                Paragraph(f'<font color="{sev_color}"><b>{sev_label}</b></font>', self.styles['LogCellCenter']),
                Paragraph(event.get('category', ''), self.styles['LogCell']),
                Paragraph(event.get('source', ''), self.styles['LogCellCenter']),
                Paragraph(event.get('device', '')[:10], self.styles['LogCellCenter']),
                Paragraph(agent_note, self.styles['LogCell']),
            ])
        
        return table_data