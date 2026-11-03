"""Uma cota mensal compartilhada entre prática e simulados."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from .domain import FREE_MONTHLY_LIMIT, remaining, study_day


def monthly_quota(db,user,day=None):
    day=day or study_day();period=day[:7]
    year,month=map(int,period.split('-'))
    next_year,next_month=(year+1,1) if month==12 else (year,month+1)
    reset=datetime(next_year,next_month,1,tzinfo=ZoneInfo('America/Sao_Paulo'))
    practice=db.execute('SELECT count(*) FROM attempts WHERE user_id=? AND day>=? AND day<?',(user,period+'-01',f'{next_year:04d}-{next_month:02d}-01')).fetchone()[0]
    exams=db.execute('SELECT coalesce(sum(charged_questions),0) FROM mock_exams WHERE user_id=? AND quota_period=?',(user,period)).fetchone()[0]
    used=practice+exams
    return dict(limit=FREE_MONTHLY_LIMIT,used=used,remaining=remaining(used),period=period,day=day,
                resets_at=reset.astimezone(timezone.utc).isoformat(),timezone='America/Sao_Paulo')
