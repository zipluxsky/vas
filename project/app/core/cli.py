import click
import logging
import asyncio
from datetime import datetime

from app.core.config import settings
from app.services.db_service import DatabaseService
from app.services.email_service import EmailService
from app.integrations.db.mysql import MySQLDatabase
from app.integrations.db.isql import ISQLDatabase
from app.integrations.email_client import EmailClient
from app.usecases.reports import generate_file_confirmation_report

logger = logging.getLogger(__name__)

def get_services():
    """Helper to initialize services for CLI commands"""
    mysql_db = MySQLDatabase(settings.db_config.get('mysql', {}))
    sybase_db = ISQLDatabase(settings.db_config.get('sybase', {}))
    db_service = DatabaseService(mysql_db, sybase_db)
    
    email_config = settings.email_config
    email_service = EmailService(
        username=email_config.get("username", "admin"),
        password=email_config.get("password", ""),
        email=email_config.get("email", "admin@vasi.com"),
        server=email_config.get("server", "mail.vasi.com")
    )
    
    return db_service, email_service

@click.group()
def commands():
    """Core commands for VASCULAR"""
    pass

@commands.command('test-db')
def test_db():
    """Test database connections"""
    logger.info("Testing database connections...")
    try:
        db_service, _ = get_services()
        
        # This would actually attempt connection in a real implementation
        mysql_status = db_service.mysql.connect()
        sybase_status = db_service.sybase.connect()
        
        if mysql_status and sybase_status:
            click.secho("Successfully connected to all databases!", fg="green")
        else:
            if not mysql_status:
                click.secho("Failed to connect to MySQL database", fg="red")
            if not sybase_status:
                click.secho("Failed to connect to Sybase database", fg="red")
            
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        click.secho(f"Error testing database connections: {e}", fg="red")

@commands.command('process-reports')
@click.option('--date', help='Date to process in YYYY-MM-DD format (defaults to today)')
def process_reports(date):
    """Process file confirmation reports"""
    process_date = datetime.now()
    if date:
        try:
            process_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            click.secho("Invalid date format. Use YYYY-MM-DD", fg="red")
            return
            
    click.echo(f"Processing reports for date: {process_date.strftime('%Y-%m-%d')}")

    try:
        db_service, email_service = get_services()
        
        # Use asyncio to run the async usecase
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            generate_file_confirmation_report(
                db_service=db_service,
                email_service=email_service,
                target_date=process_date
            )
        )
        
        if result.success:
            click.secho(f"Successfully processed reports: {result.message}", fg="green")
        else:
            click.secho(f"Report processing completed with issues: {result.message}", fg="yellow")
            
    except Exception as e:
        logger.error(f"Error processing reports: {e}")
        click.secho(f"Failed to process reports: {e}", fg="red")

@commands.command('test-email')
def test_email():
    """Test email connectivity"""
    logger.info("Testing email connectivity...")
    try:
        _, email_service = get_services()
        
        # Test connection by trying to get the account/folder
        # exchangelib will attempt to authenticate here
        account = email_service._get_account()
        # Accessing the sent folder is a good way to verify the connection works
        _ = account.sent
        
        click.secho("Successfully connected to Exchange email server!", fg="green")
            
    except Exception as e:
        logger.error(f"Email connection error: {e}")
        click.secho(f"Error testing email connectivity: {e}", fg="red")