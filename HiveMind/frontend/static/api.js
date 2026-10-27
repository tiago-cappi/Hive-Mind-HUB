async function request(path, options={}) {
  const response=await fetch(`/hive-api${path}`,options);
  const data=await response.json().catch(()=>({error:'resposta_inválida'}));
  if(!response.ok)throw Object.assign(new Error(data.error||'falha_na_solicitação'),{detail:data});
  return data;
}
export const hiveApi={
  get:path=>request(path),
  post:(path,data)=>request(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}),
};
