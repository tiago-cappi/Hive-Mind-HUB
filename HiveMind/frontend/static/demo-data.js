export const DEMO_NOTICE = 'Demonstração simulada · separada do backend real; não controla missões reais';
export const MISSION = 'Conferir pedidos recebidos por e-mail e preparar um relatório de divergências.';

export const STEPS = [
  ['Plano', 'Receber e planejar', 'Rainha'],
  ['Coleta', 'Extrair e consultar', 'Documentos, Cadastros'],
  ['Análise', 'Comparar entregas', 'Análise'],
  ['Revisão', 'Conferir divergências', 'Revisão'],
  ['Aprovação', 'Aprovar resultado', 'Você'],
  ['Relatório', 'Preparar relatório', 'Relatórios'],
  ['Entrega', 'Consolidar entrega', 'Rainha'],
];

export const DIVERGENCES = [
  ['4817', 'Mercado Bom Preço', 'Preço unitário diferente da tabela: R$ 12,90 no pedido e R$ 13,40 na tabela.', 'Confirmar o preço com o cliente.'],
  ['4822', 'Padaria Central', 'Quantidade acima do limite do cliente: 120 caixas para um limite de 80.', 'Pedir aprovação comercial.'],
  ['4825', 'Distribuidora Lima', 'CNPJ do pedido não encontrado no cadastro.', 'Atualizar o cadastro do cliente.'],
  ['4831', 'Empório Real', 'O mesmo item aparece duas vezes no pedido.', 'Confirmar com o cliente se é duplicidade.'],
];

export const STATE_INFO = {
  idle: ['Sem atividade', 'Nenhuma tarefa ou resultado passa por aqui agora.'],
  out: ['Tarefa delegada', 'Instruções a caminho do destino, em pulsos simples.'],
  del: ['Tarefa em execução', 'A tarefa foi entregue e o destino está trabalhando.'],
  wait: ['Aguardando etapa anterior', 'O destino depende desta entrega para continuar.'],
  flow: ['Resultado encaminhado', 'A entrega segue para a próxima operária, em pulsos duplos.'],
  in: ['Resultado retornando', 'O resultado volta para a Rainha, em pulsos duplos.'],
  done: ['Resultado entregue', 'A entrega chegou ao destino.'],
  ret: ['Resultado entregue', 'O resultado chegou à Rainha.'],
  fail: ['Etapa com falha', 'A comunicação não foi concluída.'],
};

export const LINK_INFO = {
  'q-doc': ['Rainha → Documentos', 'A Rainha delega a Documentos a extração dos pedidos recebidos por e-mail.'],
  'q-cad': ['Rainha → Cadastros', 'A Rainha delega a Cadastros a consulta de clientes e da tabela de preços.'],
  'q-ana': ['Rainha ↔ Análise', 'A Rainha delega a comparação a Análise, que devolve a lista de divergências.'],
  'q-rev': ['Rainha ↔ Revisão', 'A Rainha encaminha as divergências a Revisão. Quando há ajuste, Revisão devolve as observações.'],
  'q-rel': ['Rainha ↔ Relatórios', 'A Rainha delega o relatório a Relatórios, que devolve o documento pronto.'],
  'doc-ana': ['Documentos → Análise', 'Dependência: Análise só começa com os pedidos extraídos por Documentos.'],
  'cad-ana': ['Cadastros → Análise', 'Dependência: Análise só começa com os registros consultados por Cadastros.'],
  'rev-rel': ['Revisão → Relatórios', 'Revisão encaminha a lista aprovada para Relatórios.'],
  'doc-s1': ['Documentos ↔ Anexos', 'Documentos repassa os anexos em PDF ao subagente Anexos, que devolve os campos encontrados.'],
  'doc-s2': ['Documentos ↔ Mensagens', 'Documentos repassa os e-mails ao subagente Mensagens, que devolve os campos encontrados.'],
};

export const AGENTS = [
  {id:'rainha', kind:'queen', slot:'Q', name:'Rainha', spec:'Coordena o trabalho da colmeia', mission:MISSION, task:'Planejar, delegar, acompanhar e consolidar a entrega.', duty:'Coordenar e consolidar', skills:[], tools:[], from:[], to:[]},
  {id:'documentos', kind:'worker', slot:'NW', name:'Documentos', spec:'Leitura e extração de documentos', mission:'Ler os documentos que chegam à empresa e transformar o conteúdo em informações organizadas.', task:'Extrair número do pedido, cliente, itens, quantidades e valores dos e-mails recebidos nesta semana.', duty:'Extrair os dados dos pedidos', from:['rainha'], to:['analise'], skills:['Ler e-mails','Abrir anexos em PDF','Extrair campos do pedido','Separar documentos ilegíveis'], tools:[['Caixa de e-mail de pedidos','Somente leitura'],['Pasta de anexos','Somente leitura'],['Planilha de pedidos','Leitura e escrita']]},
  {id:'cadastros', kind:'worker', slot:'E', name:'Cadastros', spec:'Consulta e conferência de cadastros', mission:'Manter as informações de clientes e produtos consistentes com os registros da empresa.', task:'Consultar o cadastro de clientes e a tabela de preços de cada pedido da semana.', duty:'Consultar clientes e preços', from:['rainha'], to:['analise'], skills:['Consultar registros','Localizar duplicidades','Validar CNPJ','Conferir tabela de preços'], tools:[['Cadastro de clientes','Somente leitura'],['Tabela de preços','Somente leitura']]},
  {id:'analise', kind:'worker', slot:'NE', name:'Análise', spec:'Análise de dados e divergências', mission:'Encontrar diferenças, padrões e desvios nos dados da operação.', task:'Comparar os pedidos extraídos com os registros e listar divergências de preço, quantidade e cadastro.', duty:'Comparar as duas entregas', from:['documentos','cadastros'], to:['rainha'], skills:['Comparar valores','Classificar divergências','Calcular diferenças','Indicar prioridades'], tools:[['Planilha de pedidos','Somente leitura'],['Planilha de divergências','Leitura e escrita']]},
  {id:'revisao', kind:'worker', slot:'SE', name:'Revisão', spec:'Revisão de resultados', mission:'Conferir cada resultado antes da entrega, seguindo os critérios que você definiu.', task:'Conferir cada divergência com os critérios da empresa e pedir sua aprovação.', duty:'Conferir e pedir aprovação', from:['rainha'], to:['relatorios'], skills:['Verificar critérios','Revisar amostras','Sinalizar inconsistências','Pedir aprovação'], tools:[['Planilha de divergências','Somente leitura'],['Critérios de conferência','Somente leitura']]},
  {id:'relatorios', kind:'worker', slot:'SW', name:'Relatórios', spec:'Relatórios e comunicação', mission:'Transformar resultados revisados em relatórios claros e mensagens prontas para envio.', task:'Preparar o relatório de divergências no modelo da empresa.', duty:'Preparar o relatório', from:['revisao'], to:['rainha'], skills:['Montar relatórios','Resumir resultados','Seguir o modelo da empresa'], tools:[['Modelo de relatório','Somente leitura'],['Pasta de relatórios','Leitura e escrita']]},
  {id:'sub-anexos', kind:'sub', parent:'documentos', slot:'S1', name:'Anexos', spec:'Leitura dos anexos em PDF', total:14, unit:'anexos lidos', mission:'Ler os anexos em PDF dos e-mails e devolver os campos encontrados para Documentos.', task:'Ler os 14 anexos em PDF e extrair os campos de cada pedido.', duty:'Extrair anexos', from:['documentos'], to:['documentos'], skills:['Abrir PDF','Ler tabelas de itens'], tools:[['Pasta de anexos','Somente leitura']]},
  {id:'sub-mensagens', kind:'sub', parent:'documentos', slot:'S2', name:'Mensagens', spec:'Leitura do texto dos e-mails', total:9, unit:'e-mails lidos', mission:'Ler pedidos escritos no corpo dos e-mails e devolver os campos encontrados para Documentos.', task:'Ler os 9 pedidos escritos diretamente no corpo do e-mail.', duty:'Extrair mensagens', from:['documentos'], to:['documentos'], skills:['Ler texto livre','Identificar quantidades'], tools:[['Caixa de e-mail de pedidos','Somente leitura']]},
];

const done = {
  documentos:['done','Entregue','23 pedidos extraídos e enviados para Análise.'],
  cadastros:['done','Entregue','23 clientes consultados e enviados para Análise.'],
};
const analyzed = {...done, analise:['done','Entregue','{n} divergências encontradas em 23 pedidos.']};
const reviewed = {...analyzed, revisao:['done','Aprovado por você','Lista aprovada e enviada para Relatórios.']};
const reported = {...reviewed, relatorios:['done','Entregue','Relatório enviado à Rainha.']};
const coord = (label, detail) => ['coord', label, detail];

export const PHASES = {
  idle:{step:0,text:'A missão de exemplo está pronta. Clique em “Simular missão” para acompanhar cada etapa.',agents:{rainha:['idle','Aguardando pedido','Pronta para receber a missão de exemplo.']},links:{},next:'p1a'},
  p1a:{step:1,dur:1500,text:'A Rainha recebeu o pedido e lê o objetivo e os limites definidos por você.',agents:{rainha:coord('Recebendo o pedido','Lendo o objetivo e os limites da missão.')},links:{},next:'p1b'},
  p1b:{step:1,dur:1900,text:'A Rainha organiza o plano: quais tarefas existem, quem faz cada uma e em que ordem.',agents:{rainha:coord('Organizando o plano','Dividindo a missão em 7 etapas.')},links:{},next:'p2a'},
  p2a:{step:2,dur:1300,text:'A Rainha delega a coleta. Documentos e Cadastros começam em paralelo, e Análise já recebe sua tarefa.',agents:{rainha:coord('Delegando tarefas','Enviando instruções, contexto e critérios.'),documentos:['working','Recebendo a tarefa','Instruções e critérios recebidos da Rainha.'],cadastros:['working','Recebendo a tarefa','Instruções e critérios recebidos da Rainha.'],analise:['waiting','Aguardando informação','Depende das entregas de Documentos e Cadastros.']},links:{'q-doc':'out','q-cad':'out','q-ana':'out','doc-ana':'wait','cad-ana':'wait'},next:'p2b'},
  p2b:{step:2,dur:3600,subs:'work',text:'Documentos extrai informações dos e-mails enquanto Cadastros consulta os registros.',agents:{rainha:coord('Acompanhando o andamento','2 operárias trabalhando em paralelo.'),documentos:['working','Extraindo informações',null,[0,23,'e-mails lidos']],cadastros:['working','Consultando registros',null,[0,23,'clientes consultados']],analise:['waiting','Aguardando informação','Depende das entregas de Documentos e Cadastros.']},links:{'q-doc':'del','q-cad':'del','q-ana':'del','doc-ana':'wait','cad-ana':'wait'},next:'p2c'},
  p2c:{step:2,dur:1300,subs:'back',text:'Documentos e Cadastros encaminham suas entregas para Análise.',agents:{rainha:coord('Acompanhando o andamento','As entregas seguem para Análise.'),documentos:['done','Entrega enviada','23 pedidos extraídos e enviados para Análise.'],cadastros:['done','Entrega enviada','23 clientes consultados e enviados para Análise.'],analise:['working','Recebendo as entregas','Chegando: pedidos extraídos e registros consultados.']},links:{'q-ana':'del','doc-ana':'flow','cad-ana':'flow'},next:'p3a'},
  p3a:{step:3,dur:3000,text:'Análise compara as duas entregas e procura divergências de preço, quantidade e cadastro.',agents:{...done,rainha:coord('Acompanhando o andamento','Análise está comparando as entregas.'),analise:['working','Comparando as entregas',null,[0,23,'pedidos comparados']]},links:{'doc-ana':'done','cad-ana':'done','q-ana':'del'},next:'p3b'},
  p3b:{step:3,dur:1300,text:'Análise encontrou {n} divergências e devolve o resultado à Rainha.',agents:{...done,rainha:coord('Recebendo o resultado','Análise devolveu a lista de divergências.'),analise:['done','Entrega enviada','{n} divergências encontradas em 23 pedidos.']},links:{'doc-ana':'done','cad-ana':'done','q-ana':'in'},next:'p4a'},
  p4a:{step:4,dur:1300,text:'A Rainha encaminha as divergências para Revisão, com os critérios de conferência.',agents:{...analyzed,rainha:coord('Delegando a revisão','Enviando a lista e os critérios.'),revisao:['working','Recebendo a tarefa','Lista de divergências recebida da Rainha.']},links:{'doc-ana':'done','cad-ana':'done','q-ana':'ret','q-rev':'out'},next:'p4b'},
  p4b:{step:4,dur:2600,text:'Revisão confere cada divergência com os critérios definidos.',agents:{...analyzed,rainha:coord('Acompanhando o andamento','Revisão está conferindo.'),revisao:['working','Conferindo divergências',null,[0,'n','divergências conferidas']]},links:{'doc-ana':'done','cad-ana':'done','q-ana':'ret','q-rev':'del'},next:'approval'},
  approval:{step:5,text:'Revisão conferiu as divergências e pede sua aprovação para seguir com o relatório.',agents:{...analyzed,rainha:['approval','Aguardando sua decisão','A missão continua depois da sua escolha.'],revisao:['approval','Aguardando aprovação','{n} divergências conferidas. Precisa da sua decisão.']},links:{'doc-ana':'done','cad-ana':'done','q-ana':'ret','q-rev':'del'}},
  adj1:{step:5,dur:1200,text:'Você pediu um ajuste. Revisão devolve suas observações à Rainha.',agents:{...analyzed,rainha:coord('Encaminhando o ajuste','Repassando suas observações.'),revisao:['working','Enviando observações','Ajuste solicitado por você.']},links:{'doc-ana':'done','cad-ana':'done','q-ana':'ret','q-rev':'in'},next:'adj2'},
  adj2:{step:5,dur:1200,text:'A Rainha pede à Análise que revise a classificação das divergências.',agents:{...done,rainha:coord('Delegando o ajuste','Enviando as observações para Análise.'),analise:['working','Recebendo o ajuste','Observações recebidas da Rainha.'],revisao:['waiting','Aguardando informação','Depende do ajuste da Análise.']},links:{'doc-ana':'done','cad-ana':'done','q-ana':'out','q-rev':'wait'},next:'adj3'},
  adj3:{step:5,dur:2200,text:'Análise revisa as divergências considerando as suas observações.',agents:{...done,rainha:coord('Acompanhando o ajuste','Análise está revisando a lista.'),analise:['working','Ajustando a análise',null,[0,4,'divergências revistas']],revisao:['waiting','Aguardando informação','Depende do ajuste da Análise.']},links:{'doc-ana':'done','cad-ana':'done','q-ana':'del','q-rev':'wait'},next:'adj4'},
  adj4:{step:5,dur:1300,text:'Análise devolve a lista ajustada, e a Rainha encaminha para Revisão.',agents:{...done,rainha:coord('Encaminhando o ajuste','Lista ajustada a caminho de Revisão.'),analise:['done','Ajuste entregue','{n} divergências após o ajuste.'],revisao:['working','Recebendo o ajuste','Lista ajustada recebida da Rainha.']},links:{'doc-ana':'done','cad-ana':'done','q-ana':'in','q-rev':'out'},next:'adj5'},
  adj5:{step:5,dur:1800,text:'Revisão confere novamente a lista ajustada.',agents:{...analyzed,rainha:coord('Acompanhando o andamento','Revisão está conferindo de novo.'),revisao:['working','Conferindo novamente',null,[0,'n','divergências conferidas']]},links:{'doc-ana':'done','cad-ana':'done','q-ana':'ret','q-rev':'del'},next:'approval'},
  p6a:{step:6,dur:1300,text:'Aprovado. Revisão encaminha a lista para Relatórios, e a Rainha delega o relatório.',agents:{...reviewed,rainha:coord('Delegando o relatório','Enviando o modelo e o resultado aprovado.'),relatorios:['working','Recebendo a tarefa','Resultado aprovado recebido de Revisão.']},links:{'doc-ana':'done','cad-ana':'done','q-ana':'ret','rev-rel':'flow','q-rel':'out'},next:'p6b'},
  p6b:{step:6,dur:2600,text:'Relatórios prepara o relatório de divergências no modelo da empresa.',agents:{...reviewed,rainha:coord('Acompanhando o andamento','Relatórios está montando o documento.'),relatorios:['working','Preparando o relatório',null,[0,4,'seções prontas']]},links:{'doc-ana':'done','cad-ana':'done','q-ana':'ret','rev-rel':'done','q-rel':'del'},next:'p7a'},
  p7a:{step:7,dur:1300,text:'Relatórios entrega o relatório à Rainha.',agents:{...reviewed,rainha:coord('Recebendo a entrega','O relatório está chegando.'),relatorios:['done','Entrega enviada','Relatório pronto para consolidação.']},links:{'doc-ana':'done','cad-ana':'done','q-ana':'ret','rev-rel':'done','q-rel':'in'},next:'p7b'},
  p7b:{step:7,dur:1700,text:'A Rainha confere se cada tarefa cumpriu seus critérios e consolida o resultado.',agents:{...reported,rainha:coord('Consolidando a entrega','Conferindo os critérios de cada tarefa.')},links:{'doc-ana':'done','cad-ana':'done','q-ana':'ret','rev-rel':'done','q-rel':'ret'},next:'done'},
  done:{step:8,final:true,text:'Missão concluída. A entrega de exemplo está pronta para consulta.',agents:{...reported,rainha:['done','Entrega concluída','Relatório de divergências pronto.']},links:{'q-doc':'ret','q-cad':'ret','q-ana':'ret','q-rev':'ret','q-rel':'ret','doc-ana':'done','cad-ana':'done','rev-rel':'done'}},
  fail:{step:2,failed:true,subs:'done',text:'A coleta falhou: Cadastros não conseguiu consultar o cadastro de clientes.',agents:{rainha:['approval','Impedimento encontrado','Cadastros não concluiu a consulta. Você pode tentar de novo.'],documentos:['done','Entrega enviada','23 pedidos extraídos e enviados para Análise.'],cadastros:['failed','Falhou','O cadastro de clientes não respondeu após 3 tentativas.'],analise:['waiting','Aguardando informação','Recebeu a entrega de Documentos. Falta Cadastros.']},links:{'q-cad':'fail','q-ana':'del','doc-ana':'done','cad-ana':'wait'}},
  retry:{step:2,dur:2600,subs:'done',text:'Cadastros tenta a consulta novamente.',agents:{rainha:coord('Acompanhando a nova tentativa','Cadastros está consultando de novo.'),documentos:['done','Entrega enviada','23 pedidos extraídos e enviados para Análise.'],cadastros:['working','Consultando registros',null,[0,23,'clientes consultados']],analise:['waiting','Aguardando informação','Recebeu a entrega de Documentos. Falta Cadastros.']},links:{'q-cad':'out','q-ana':'del','doc-ana':'done','cad-ana':'wait'},next:'retry2'},
  retry2:{step:2,dur:1300,subs:'done',text:'Cadastros encaminha sua entrega para Análise.',agents:{rainha:coord('Acompanhando o andamento','As entregas seguem para Análise.'),documentos:['done','Entregue','23 pedidos extraídos e enviados para Análise.'],cadastros:['done','Entrega enviada','23 clientes consultados e enviados para Análise.'],analise:['working','Recebendo as entregas','Falta pouco para começar a comparação.']},links:{'q-ana':'del','doc-ana':'done','cad-ana':'flow'},next:'p3a'},
};

export const CONNECTIONS = [
  ['q-doc','rainha','documentos'],['q-ana','rainha','analise'],['q-cad','rainha','cadastros'],
  ['q-rev','rainha','revisao'],['q-rel','rainha','relatorios'],['doc-ana','documentos','analise'],
  ['cad-ana','cadastros','analise'],['rev-rel','revisao','relatorios'],
];
