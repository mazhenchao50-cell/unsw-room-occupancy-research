from pathlib import Path
import numpy as np
import pandas as pd
import joblib, shap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from revised import ROOT,load,raw_features,dump

def run():
    out=ROOT/'02、模型实验/生成产物/revised'; bundle=joblib.load(out/'model.joblib'); d=load(); te=d[d.week.eq(12)]
    x=raw_features(bundle['reference'],te).fillna(bundle['median'])
    explainer=shap.TreeExplainer(bundle['model']); values=explainer.shap_values(x)
    expected=float(np.asarray(explainer.expected_value).reshape(-1)[0])
    assert np.allclose(values.sum(axis=1)+expected,bundle['model'].predict(x),atol=1e-7)
    imp=np.abs(values).mean(axis=0); total=float(imp.sum()); records=[]
    for j,col in enumerate(x.columns):
        constant=x[col].nunique()<2 or np.ptp(values[:,j])==0
        corr=None if constant else float(spearmanr(x[col],values[:,j]).statistic)
        if corr is not None and not np.isfinite(corr): corr=None
        records.append({'feature':col,'mean_abs_shap':float(imp[j]),'share':float(imp[j]/total) if total else 0,'spearman':corr,'direction':'常量或无变化，无法计算' if corr is None else '正相关' if corr>0 else '负相关'})
    rank=pd.DataFrame(records).sort_values('mean_abs_shap',ascending=False); rank.to_csv(out/'shap_feature_ranking.csv',index=False)
    dump(out/'shap_report.json',{'sample':'week12 held-out from model fitting; retrospective revision evaluation','n':len(x),'expected_value':expected,'ranking':sorted(records,key=lambda r:-r['mean_abs_shap']),'note':'Association only; course mean is course-level, not course-room. SHAP explains raw model output before lower clipping.'})
    dump(out/'shap_viz.json',{'features':list(x.columns),'values':values.tolist(),'x':x.to_numpy().tolist(),'session_id':te.session_id.tolist()})
    np.savez_compressed(out/'shap_values.npz',values=values,x=x.to_numpy(),features=np.array(x.columns),session_id=te.session_id.to_numpy(dtype=str))
    plt.figure(figsize=(9,5)); plt.barh(rank.feature[::-1],rank.mean_abs_shap[::-1]); plt.xlabel('Mean absolute SHAP, week 12'); plt.tight_layout(); plt.savefig(out/'shap_importance.png',dpi=160); plt.close()
    np.random.seed(42); shap.summary_plot(values,x,show=False); plt.tight_layout(); plt.savefig(out/'shap_beeswarm.png',dpi=160); plt.close()
    local=pd.DataFrame(values,columns=x.columns); local.insert(0,'session_id',te.session_id.to_numpy()); local.to_csv(out/'shap_local.csv',index=False)
    html='<meta charset="utf-8"><title>测试集 SHAP</title><h1>第12周测试集 SHAP</h1><p>模型关联，不代表因果。解释原始回归输出。</p>'+rank.to_html(index=False)+'<img width="850" src="shap_importance.png"><img width="850" src="shap_beeswarm.png">'
    (out/'shap_visualization.html').write_text(html,encoding='utf-8')
if __name__=='__main__':run()
