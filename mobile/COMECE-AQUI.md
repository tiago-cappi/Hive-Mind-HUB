# Conversar com o Claude pelo celular — passo a passo

> Rede de casa apenas. Nada é exposto na internet.

## Antes de tudo: você não precisa configurar nada

O token é gerado sozinho na primeira vez que o servidor sobe e fica guardado em
`mobile/.secret`. Você **não** cria, não escolhe e não digita valor nenhum em
lugar nenhum. Só usa o link que aparece na tela.

---

## Preparação (uma vez só, ~3 minutos)

### 1. Reiniciar o Hub

Necessário só desta vez: o `server.py` ganhou o campo que faz o computador
**ficar calado** quando você está falando pelo celular. O Hub que está rodando
agora ainda tem o código antigo na memória.

```powershell
cd "C:\Users\m.rafael\Desktop\Projetos Pessoais\core-voice-hub-v2-main\core-voice-hub-v2-main"
./restart_hub.ps1
```

> ⚠️ Isso encerra as conversas abertas no Hub, inclusive a que está no ar agora.

### 2. Preparar a rede (pede senha de administrador)

Clique com o **botão direito** em `mobileirewall.ps1` → **Executar com o
PowerShell**, e aceite o aviso do Windows.

Ele faz as duas coisas que travam o celular, e só isso:

- **Marca a sua rede Wi-Fi como "privada".** Hoje ela está como *pública* — e
  nesse modo o Windows recusa qualquer conexão vinda do celular. Ele pergunta
  antes de mudar; responda `s`.
- **Libera a porta 8766**, apenas em redes privadas.

No fim, ele mostra o link para abrir no celular.

---

## Ligar o servidor do celular

Duplo clique em:

```
mobile\start_mobile.vbs
```

Sobe sem janela nenhuma. Para conferir se está no ar, ou para ver o link, abra
o arquivo `mobile\LINK.txt`.

Prefere ver a tela com o link e o token? Rode em vez disso:

```powershell
./.venv/Scripts/python.exe -m mobile.run
```

(nesse modo, **fechar a janela encerra** o servidor do celular)

---

## Entrar pelo celular (uma vez só)

O seu link, hoje, é:

```
http://192.168.15.32:8766/login?t=D3VzL77-KRcdD1EW-SpZJf8iZkrMXr7f
```

1. Mande esse link para você mesmo — WhatsApp na conversa "só você", Telegram
   Saved Messages, e-mail, o que for mais rápido. (Ele também está em
   `mobile\LINK.txt`, dá para copiar de lá.)
2. Abra o link **no celular**, conectado no **mesmo Wi-Fi** de casa.
3. Pronto. O celular guarda o acesso por **60 dias** — nas próximas vezes basta
   abrir `http://192.168.15.32:8766`.
4. No Chrome do celular: **menu ⋮ → Adicionar à tela inicial**. Vira um ícone e
   abre em tela cheia, com cara de aplicativo.

---

## Falar em vez de digitar

Toque no campo de texto e use o **microfone do teclado do próprio celular**
(aquele ícone ao lado da barra de espaço). Você fala, ele escreve, você envia.

É o jeito mais simples e funciona igual em qualquer aparelho.

---

## O que tem na tela

| Botão | O que faz |
|---|---|
| **✚** | Nova conversa (zera o contexto e a tela) |
| **▤** | Lista os relatórios visuais gerados no vault — abre no celular |
| **⋯** | Opções |
| **parar** | Interrompe o turno em andamento |
| bolinha ao lado de "C.O.R.E." | verde = tudo certo · dourada piscando = pensando · vermelha = o Hub caiu |

Duas opções dentro do **⋯**:

- **Falar a resposta no computador** — desligado por padrão. Ligue quando você
  estiver em casa e quiser ouvir pelas caixas do PC.
- **Ler a resposta aqui no celular** — usa a voz do próprio aparelho. Ligue
  quando estiver longe do computador e quiser ouvir em vez de ler.

---

## Coisas boas de saber

- **Pode apagar a tela do celular no meio da resposta.** O turno roda no
  servidor, não no navegador. Quando você voltar, a resposta está lá inteira.
- **O histórico fica salvo** e volta quando você reabre a página.
- **O Hub tem que estar no ar.** Se a bolinha ficar vermelha, o `server.py`
  caiu — suba de novo com `restart_hub.ps1`.
- **O celular ocupa 1 das 6 sessões** simultâneas do Hub.
- **A conversa do celular é separada** das abas abertas no computador: contexto
  próprio, não se misturam.

---

## Se não funcionar

| Sintoma | O que fazer |
|---|---|
| A página não abre no celular | Confira se os dois estão no **mesmo Wi-Fi** (nada de rede de convidados nem 4G) |
| Continua não abrindo | Rode o passo 2 (`firewall.ps1`) — é ele que marca a rede como privada e abre a porta |
| "Fora da rede local" | O celular está saindo por outro caminho — desligue o 4G/VPN dele |
| O IP mudou e o link não abre | Rode `./.venv/Scripts/python.exe -m mobile.run` e use o link novo, ou reserve o IP fixo no roteador |
| Quer trocar o token | Apague `mobile\.secret` e suba de novo — todos os celulares saem |

---

## Desligar

```powershell
./mobile/stop_mobile.ps1
```

O Hub continua funcionando normalmente no computador — este módulo é
independente dele.
