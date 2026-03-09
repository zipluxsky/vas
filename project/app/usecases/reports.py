import logging
from datetime import datetime
from typing import Dict, Any

from app.services.db_service import DatabaseService
from app.services.email_service import EmailService
from app.reports.file_confirmation.engine import FileConfirmationEngine
from app.reports.config_loader import report_config_loader
from app.schemas.report_models import ReportGenerationResponse

logger = logging.getLogger(__name__)

async def generate_file_confirmation_report(
    db_service: DatabaseService, 
    email_service: EmailService,
    target_date: datetime = None
) -> ReportGenerationResponse:
    """Generate and distribute the file confirmation report"""
    
    if target_date is None:
        target_date = datetime.now()
        
    logger.info(f"Initiating file confirmation report for {target_date.date()}")

    try:
        # Load configuration
        config = report_config_loader.load_report_config("file_confirmation")
        
        # Initialize engine
        engine = FileConfirmationEngine(db_service, config)
        
        # Generate report
        result = engine.generate(target_date)
        
        if not result.get("success"):
            return ReportGenerationResponse(
                success=False,
                message=f"Generation failed: {result.get('error')}"
            )
            
        # Send via email
        output_paths = result.get("output_paths", [])
        if output_paths:
            email_sent = email_service.send_report(
                "File Confirmation", 
                output_paths, 
                target_date
            )
            
            if not email_sent:
                logger.warning("Report generated but email sending failed")
                
        return ReportGenerationResponse(
            success=True,
            message="Report generated successfully",
            output_paths=output_paths,
            record_count=result.get("record_count", 0)
        )
        
    except Exception as e:
        logger.error(f"Unhandled error in report generation: {e}")
        return ReportGenerationResponse(
            success=False,
            message=str(e)
        )
