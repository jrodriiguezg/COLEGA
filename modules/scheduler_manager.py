import logging
from flask_apscheduler import APScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
import subprocess
import time

# Logger
logger = logging.getLogger("SchedulerManager")

class SchedulerManager:
    def __init__(self, app=None):
        self.scheduler = APScheduler()
        self.app = app
        
        # Configuration
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize scheduler with Flask app."""
        self.app = app
        
        # Configuración de persistencia (SQLite)
        # APScheduler usa esto para guardar jobs entre reinicios
        app.config['SCHEDULER_JOBSTORES'] = {
            'default': SQLAlchemyJobStore(url='sqlite:///database/jobs.sqlite')
        }
        app.config['SCHEDULER_API_ENABLED'] = True # /scheduler/jobs endpoint enabled by default in Flask-APScheduler, but we might build our own API
        app.config['SCHEDULER_TIMEZONE'] = "Europe/Madrid" # Ajustar según config?

        self.scheduler.init_app(app)
        self.scheduler.start()
        logger.info("Scheduler started.")

    # --- Allowed Job Functions ---
    # These must be static or standalone functions ideally to be pickleable/callable easily, 
    # but methods on instance work if instance is global.
    # Flask-APScheduler usually looks for 'func' as string path 'module:function'.
    
    def add_bash_job(self, name, command, cron_expression):
        """
        Adds a cron job that executes a bash command.
        cron_expression: string format "minute hour day month day_of_week" (standard cron)
                         OR specific params like "*/5 * * * *"
        """
        # Parse cron string "min hour day month dow"
        # Example: "0 3 * * 2" -> At 03:00 on Tuesday.
        
        try:
            parts = cron_expression.split()
            if len(parts) != 5:
                return False, "Invalid cron format. Expected 5 parts: min hour day month dow"
            
            minute, hour, day, month, day_of_week = parts
            
            # Create a unique ID
            job_id = f"job_{int(time.time())}_{name.replace(' ', '_')}"
            
            self.scheduler.add_job(
                id=job_id,
                func='modules.scheduler_manager:run_bash_command', # Referencia string
                args=[command],
                trigger=CronTrigger(
                    minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week
                ),
                name=name,
                replace_existing=True
            )
            return True, f"Job {name} added."
            
        except Exception as e:
            logger.error(f"Error adding job: {e}")
            return False, str(e)

    def delete_job(self, job_id):
        try:
            self.scheduler.remove_job(job_id)
            return True, "Job deleted."
        except Exception as e:
            return False, str(e)
            
    def get_jobs(self):
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': str(job.next_run_time),
                'trigger': str(job.trigger)
            })
        return jobs

# --- Standalone Functions for Jobs ---
def run_bash_command(command):
    """Ejecuta un comando bash y loguea el resultado."""
    try:
        logger.info(f"Executing Scheduled Job: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        logger.info(f"Job Output: {result.stdout}")
        if result.stderr:
            logger.warning(f"Job Stderr: {result.stderr}")
    except Exception as e:
        logger.error(f"Job Execution Error: {e}")
