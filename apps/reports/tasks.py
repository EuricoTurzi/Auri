"""
Celery tasks para o app reports — execução periódica de relatórios agendados.
"""
from celery import shared_task

from apps.reports.services import process_due_reports


@shared_task
def send_scheduled_reports_task():
    """
    Task periódica que processa relatórios agendados pendentes.
    Configurar no Celery Beat para execução a cada hora.
    """
    process_due_reports()
