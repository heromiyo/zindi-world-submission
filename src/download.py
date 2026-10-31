"""Download only explicitly permitted challenge inputs; record exact source hashes."""
import concurrent.futures, hashlib, json, pathlib, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE='https://s3.us-west-2.amazonaws.com/us-west-2.opendata.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge'
REGIONS=['maricopa-az','northern-ca','eastern-ok','south-central-tx','eastern-wa']
def paths():
 for r in REGIONS:
  yield f'reference/{r}/{r}-sample-submission.csv'
  yield f'reference/{r}/{r}-census-acs-housing.csv'
  yield f'strata/{r}/{r}-strata-tract-table.parquet'
  yield f'strata/{r}/{r}-census-tracts.parquet'
  yield f'reference/{r}/{r}-overture-pois.parquet'
def get(rel):
 p=ROOT/'data'/rel;p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists():
  tmp=p.with_suffix(p.suffix+'.part')
  with urllib.request.urlopen(BASE+'/'+rel,timeout=120) as resp,open(tmp,'wb') as out:
   while b:=resp.read(1024*1024):out.write(b)
  tmp.rename(p)
 result={'path':rel,'url':BASE+'/'+rel,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 print(rel,result['bytes'],flush=True);return result
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: records=list(ex.map(get,paths()))
 (ROOT/'metadata'/'download-manifest.json').write_text(json.dumps(records,indent=2))
