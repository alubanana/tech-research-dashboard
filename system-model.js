/* odds-v1: subjective evidence scenarios, not calibrated probabilities. */
const ResearchModel=(()=>{
 const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
 const logit=p=>Math.log(p/(1-p)),sigmoid=x=>1/(1+Math.exp(-x));
 function probability(scores,{prior=.2,dependence=.65}={}){if(!(prior>0&&prior<1))throw Error('prior');if(scores.length!==5||scores.some(s=>!Number.isFinite(s)||s< -2||s>2))throw Error('scores');return sigmoid(logit(prior)+dependence*Math.LN2*scores.reduce((a,b)=>a+b,0));}
 function estimate(scores,settings={}){const center=probability(scores,settings),values=[];for(const prior of [.1,.35])for(const dependence of [.4,.8])for(const delta of [-.5,.5])values.push(probability(scores.map(s=>clamp(s+delta,-2,2)),{prior,dependence}));return{p:center,low:Math.min(...values,center),high:Math.max(...values,center)};}
 function brier(p,outcome){if(!(p>=0&&p<=1)||![0,1].includes(outcome))throw Error('settlement');return(p-outcome)**2;}
 function available(evidence,cutoff){return evidence.filter(e=>e.date&&e.date<=cutoff&&(!e.sources||e.sources.every(s=>s.date&&s.date<=cutoff)));}
 function assertCutoff(evidence,cutoff){if(available(evidence,cutoff).length!==evidence.length)throw Error('lookahead evidence');return true;}
 function edgesAt(edges,date,clock='recordedAt'){return edges.filter(e=>e[clock]<=date&&(!e.validTo||e.validTo>date));}
 return{probability,estimate,brier,available,assertCutoff,edgesAt};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=ResearchModel;
