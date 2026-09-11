"""F01-contract-temporal v3B.1. No trading, timestamps repaired, or missing-field defaults."""
VERSION='F01-contract-temporal v3B.1'
class Unsupported(ValueError):pass
ECONOMIC_FIELDS=['venue','market_type','base_asset','quote_asset','settlement_asset','margin_asset','quantity_unit','price_unit','multiplier','linear_inverse','payoff','expiry']
def require_contract(contract,claims=None):
 # A received metadata hash is not a certificate of complete economic terms.
 for k,v in (claims or {}).items():
  f=contract['fields'][k]
  if f['status']=='PROVEN' and v!=f['value']:raise ValueError('Contradiction to proven field: '+k)
  if f['status']=='UNKNOWN':raise Unsupported('Claim needs evidence: '+k)
 missing=[k for k in ECONOMIC_FIELDS if contract['fields'][k]['status'] not in ['PROVEN','N/A']]
 if missing:raise Unsupported('Incomplete economic contract: '+','.join(missing))
 if not contract['complete_for_replay']:raise Unsupported('Scoped evidence gate not certified')
 return True
def require_metric(observation,requested):
 if observation['type']!=requested:raise ValueError('Different observation semantics')
 return True
def states(clock,cutoff_local_ns,contract):
 if type(cutoff_local_ns) is not int:raise ValueError('Integer local ns required')
 c=clock['clocks'];receipt=c['LOCAL_RECEIPT_TIME'];observed=receipt['status']=='PROVEN' and receipt['value']<=cutoff_local_ns
 attached=c['SOURCE_EVENT_TIME']['status']!='UNKNOWN'
 # No max of remote event and local receipt; crossing domains needs separate evidence.
 event='TIMESTAMP_ATTACHED_LOCAL_OCCURRENCE_NOT_PROVEN' if attached else 'UNKNOWN'
 reasons=[]
 if not observed:reasons.append('NOT_OBSERVED_AT_LOCAL_CUTOFF')
 try:require_contract(contract)
 except (ValueError,Unsupported):reasons.append('ECONOMIC_CONTRACT_NOT_PROVEN')
 if clock.get('clock_mapping')!='PROVEN':reasons.append('SOURCE_TO_LOCAL_CLOCK_MAPPING_NOT_PROVEN')
 for k in ['valid_from','valid_until','contract_version']:
  if contract['fields'][k]['status']=='UNKNOWN':reasons.append(k.upper()+'_NOT_PROVEN')
 return {'OBSERVED':observed,'EVENT_OCCURRED':event,'ECONOMICALLY_ELIGIBLE':not reasons,'reasons':reasons}
def dimension_product(left,right,expected):
 # Algebra for explicitly declared units. Does not assign units to any real receipt.
 out=left.copy()
 for k,v in right.items():out[k]=out.get(k,0)+v
 out={k:v for k,v in out.items() if v}
 if out!=expected:raise ValueError('Dimension mismatch')
 return out
