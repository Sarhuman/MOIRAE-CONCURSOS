"""Read-only commercial proposals. Never creates payment/access or guesses buyer interest."""
import json
from pathlib import Path
from fastapi import HTTPException

PATH=Path(__file__).resolve().parents[2]/'web'/'portfolio-offers.json'
def catalog():return json.loads(PATH.read_text())

def quote(product,cycles=1,installments=1):
    data=catalog();plans={p['id']:p for p in data['plans']};packs={p['id']:p for p in data['credit_packs']}
    if type(cycles) is not int or type(installments) is not int:raise HTTPException(422,'Ciclos e parcelas devem ser inteiros.')
    if product in plans:
        p=plans[product]
        if cycles not in data['cycles']:raise HTTPException(422,'Escolha 1, 6 ou 12 ciclos.')
        base=p['cycle_prices'][str(cycles)]*cycles;limit=cycles
        credits=p['credits_per_cycle'];days=cycles*30
    elif product in packs:
        p=packs[product]
        if cycles!=1:raise HTTPException(422,'Créditos avulsos são uma compra única.')
        base=p['price_cents'];limit=p['max_installments'];credits=p['credits'];days=None
    else:raise HTTPException(404,'Produto não encontrado.')
    if not 1<=installments<=limit:raise HTTPException(422,'Número de parcelas indisponível nesta proposta.')
    total=(base*(10000+data['markup_basis_points'])+9999)//10000
    rate=data['fee_reference']['installment_basis_points'].get(str(installments),0)
    extra=(total*rate+9999)//10000
    estimate=total+extra
    part,remainder=divmod(estimate,installments)
    return dict(reference_installment_basis_points=rate,estimated_financing_cents=extra,estimated_buyer_total_cents=estimate,estimated_installments_cents=[part+int(i<remainder) for i in range(installments)],product=product,cycles=cycles,access_days=days,credits=credits,credits_policy='por ciclo de 30 dias, sem acúmulo' if days else 'avulsos; validade proposta de 90 dias',
        base_cents=base,markup_cents=total-base,product_total_cents=total,requested_installments=installments,
        installment_payer='buyer',buyer_total_cents=total if installments==1 else None,
        installment_cents=total if installments==1 else None,provider_quote_required=installments>1,
        checkout_enabled=False,mode='proposal',notice='Juros de parcelamento dependem da cotação do Mercado Pago e são pagos pelo comprador. Taxas de processamento do vendedor não equivalem a juros do comprador. Acréscimo de 10% não garante lucro líquido.')
