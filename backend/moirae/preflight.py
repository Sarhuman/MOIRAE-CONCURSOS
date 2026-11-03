"""Read-only local configuration check. Prints booleans, never credentials."""
import json
import os
import re
from pathlib import Path

def check(env):
    origin=env.get('MOIRAE_ORIGIN','http://127.0.0.1:8000')
    flags={k:env.get(k,'false').lower()=='true' for k in ('MOIRAE_ESSAY_AI','MOIRAE_ESSAY_AI_REVIEWED','MOIRAE_MP_SANDBOX')}
    checks=dict(loopback_origin=bool(re.fullmatch(r'http://(127\.0\.0\.1|localhost):[0-9]{1,5}',origin)),
        local_cookie=env.get('MOIRAE_SECURE_COOKIE','true').lower()=='false',
        database_exists=bool(env.get('MOIRAE_DB') and Path(env['MOIRAE_DB']).is_file()),
        external_integrations_disabled=not any(flags.values()))
    return dict(local_test_config_ok=all(checks.values()),checks=checks,
        api_key_present=bool(env.get('OPENAI_API_KEY')),model_configured=bool(env.get('MOIRAE_ESSAY_MODEL')),
        notice='Verificação local de configuração, sem rede. Não comprova funcionamento, segurança de produção ou qualidade pedagógica.')

def main():
    result=check(os.environ);print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['local_test_config_ok'] else 1)
if __name__=='__main__':main()
