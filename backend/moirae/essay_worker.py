"""Run explicitly: python -m backend.moirae.essay_worker [--once]."""
import argparse
import os
import time
from .store import Store
from .essay_jobs import EssayWorker
from .essay_provider import OpenAIEvaluator

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args()
    if os.getenv('MOIRAE_ESSAY_AI','false').lower()!='true' or os.getenv('MOIRAE_ESSAY_AI_REVIEWED','false').lower()!='true':
        parser.error('Correção real desativada; validação pedagógica e configuração são necessárias.')
    if not os.getenv('MOIRAE_DB'):parser.error('MOIRAE_DB explícito é obrigatório no worker.')
    try:
        evaluator=OpenAIEvaluator(os.getenv('OPENAI_API_KEY',''),os.getenv('MOIRAE_ESSAY_MODEL',''))
        worker=EssayWorker(Store(os.environ['MOIRAE_DB']),evaluator,daily_limit=int(os.getenv('MOIRAE_ESSAY_DAILY_CALLS','20')))
    except ValueError:parser.error('Configuração do worker incompleta ou inválida.')
    while True:
        processed=worker.run_once()
        if args.once:return
        if not processed:time.sleep(2)
if __name__=='__main__':main()
