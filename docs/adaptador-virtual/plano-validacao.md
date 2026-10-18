# Plano de execução, validação e esforço

Estado em 18/10/2026: levantamento concluído; implementação e homologação
pendentes. Este plano segue a equivalência com EMUG27 descrita na
[especificação](protocolo-emug27.md) e a [arquitetura proposta](arquitetura.md).

## 1. Decisões já tomadas e pendências

| Item | Estado |
|---|---|
| Primeiro uso | Linux/Proton no mesmo PC |
| Windows | Obrigatório no desenho e na prova inicial; entrega própria |
| Referência | Adaptador GIMX/EMUG27, não joystick genérico |
| Configuração | Preservar config e XML atuais |
| Linguagem | C/C++ existente; nenhuma migração Rust |
| Linux USB/IP + VHCI / Windows UDE | Candidatos principais; ainda sem prova de execução |
| Perfil padrão legado/atual | Decidir após referência/captura; bytes já extraídos |
| Jogos prioritários | Ainda não informados; necessários para homologação |
| Windows e driver Logitech exatos | Ainda não informados/instalados para teste |
| Referência física estável | UART atual falha; não usar como única fonte de verdade |

As pendências não impedem especificar o adaptador nem iniciar provas isoladas.
Impedem afirmar que determinado jogo/driver já está suportado.

## 2. Fases e entregas

### Fase 0 — congelar a referência (1–2 semanas de desenvolvimento)

- [x] Identificar os fontes GIMX/firmware e fixar commits.
- [x] Extrair os dois descritores HID e comparar tamanhos/campos.
- [x] Documentar os opcodes e o ciclo TYPE/VERSION/RESET/START.
- [x] Identificar limitações de haptics e de UHID/VHF.
- [ ] Decodificar automaticamente todos os descritores USB de configuração.
- [ ] Criar fixtures binárias de relatório neutro, extremos e botões/marchas.
- [ ] Selecionar perfil padrão e registrar justificativa.
- [ ] Capturar enumeração/controles/OUT da placa, se houver referência estável.

Entrega: especificação congelada, corpus de testes e lista de divergências
conhecidas. Capturas úteis, mas o defeito UART não deve bloquear a análise de
fontes. Se a placa não for confiável, registrar cada inferência não observada.

### Fase 1 — provas de USB virtual em ambos os sistemas (3–5 semanas)

Linux: implementar ou integrar servidor de dispositivo USB/IP em loopback,
importar por VHCI e provar enumeração G27 com os descritores fixados. Receber
OUT e responder ao mínimo de controle com relatório neutro/sintético.

Windows: driver mínimo UDE em ambiente de desenvolvimento, mesmos descritores,
associação do driver e registro de requests, sem motor. Validar se o pacote
Logitech escolhido opera sobre essa topologia.

**Gate A:** device enumera, driver esperado se associa, entrada funciona e há
caminho de retorno demonstrável em ambos os sistemas. Sem isso, não consolidar
API compartilhada nem anunciar compatibilidade. Se Linux/Windows falhar,
registrar o motivo e reavaliar backend, mantendo o requisito de equivalência.

### Fase 2 — núcleo comum e entrada real (3–5 semanas)

- Perfil/versionamento, máquina de estados e contrato de transferências.
- Integração no construtor G27 atual e no fluxo de controller/args/mainloop.
- Entradas selecionadas pelo XML, com exclusão automática da própria saída.
- IPC/filas limitadas, sequência de comandos e timeout/cancelamento.
- Validação de dispositivos físicos e virtuais simultâneos.
- Linux/Proton e Windows reconhecem direção/pedais/botões/câmbio.

**Gate B:** mesmas saídas binárias para o mesmo estado lógico e controles
corretos nos jogos de teste. Nenhuma dependência de CP2102/Pro Micro na saída.

### Fase 3 — retorno de força e ciclo de vida (4–7 semanas)

- Receber OUT e validar comprimentos antes do parser atual.
- Comparar comandos e eventos internos com fixtures de referência.
- Integrar `haptic_source_lg`, tweaks e sink do OpenFFBoard.
- Validar ganho, inversão, slots simultâneos e stop/play/refresh.
- Confirmar limites reais de range/LEDs e efeitos não suportados.
- Testar pausa, reset, close do jogo, perda do IPC e encerramento inesperado.
- Definir/testar supervisão e parada em perda de processo.

**Gate C:** força com direção e escala corretas, ausência de força residual nos
cenários especificados e recuperação sem reconectar hardware. Primeiro testes
sem motor, depois intensidade reduzida e só então uso normal.

### Fase 4 — produto e empacotamento (3–5 semanas)

- Opção explícita no launcher; XML/config continuam o fluxo de mapeamento.
- Diagnóstico distingue fonte ausente, falha virtual, driver e haptics.
- Pacote Arch/helper/permissões e instalação/desinstalação Windows.
- Integrar builds/checagens Linux e Windows em CI.
- Documentar Proton, Steam Input, drivers e jogos homologados.
- Definir como atualizar perfis sem quebrar configurações existentes.

**Gate D:** usuário instala, inicia e remove sem comandos manuais de laboratório;
driver Windows tem caminho de distribuição definido.

### Fase 5 — regressão prolongada e lançamento (2–4 semanas)

- Sessões de 30 minutos e 2 horas; observar CPU, filas, memória e latência.
- Repetir 100 ciclos de criação/início/parada sem instâncias órfãs.
- Rodar matriz de jogos, kernels, Proton e Windows selecionados.
- Comparar caminho físico quando existir referência estável.
- Corrigir bloqueadores e publicar limites comprovados.

## 3. Estimativa consolidada

Faixa inicial: **16–28 pessoas-semana**, aproximadamente 4–7 pessoas-mês, para
um escopo EMUG27 Linux + Windows com experiência em C/C++, USB e driver WDF.
A soma das faixas de fases é 16–28; não é prazo fechado de calendário.

Uma pessoa pode precisar de 4–7 meses ou mais. Duas pessoas não dividem o prazo
automaticamente pela metade: protocolo comum, validação com driver e acesso ao
hardware criam dependências. Aprovações/certificação de assinatura, aprendizagem
de WDF, compatibilidade de jogos e problemas de firmware podem estender o prazo.

Refinar depois do Gate A. Antes dele, não há estimativa responsável de uma
entrega completa em poucos dias. A primeira decisão de investimento é financiar
a prova de enumeração e retorno em Linux e Windows, não toda a reescrita.

## 4. Matriz de testes e critérios

Todos os itens abaixo estão **pendentes de execução**, exceto a extração estática
dos descritores. Resultado válido deve identificar plataforma, perfil e revisão.

| ID | Ensaio | Aprovação |
|---|---|---|
| REF-01 | Extrair arrays dos commits fixados | Hashes e totais iguais ao JSON; executado neste levantamento |
| REF-02 | Relatório neutro e extremos de direção | 11 bytes, centro 8192 e extremos sem inversão inesperada |
| REF-03 | Pedais independentes | Resolução de 8 bits; sem acoplamento não presente na referência |
| REF-04 | Hat/botões/marchas, combinações | Bits e semântica correspondem ao perfil selecionado |
| USB-01 | Enumerar/GET_DESCRIPTOR | Comprimentos, IDs, bcdDevice, interfaces e endpoints corretos |
| USB-02 | SET_CONFIGURATION e reconfiguração | Estado e endpoints consistentes, sem dupla conclusão |
| USB-03 | GET/SET_REPORT e SET_IDLE | Resposta/erro conforme referência documentada |
| USB-04 | Feature 144 bytes vs buffers | Sem overflow/truncamento silencioso; política explicitada |
| USB-05 | IN pendente, OUT e cancelamento | Sem deadlock, perda de STOP ou request órfã |
| USB-06 | Transferências inválidas/curtas | Erro controlado; processo/driver permanece íntegro |
| USB-07 | Reset, suspend/resume, desconexão | Estado limpo e reencontro do dispositivo, conforme plataforma |
| LIN-01 | Associação hid-logitech/lg4ff | Driver carregado e capacidades FFB efetivas registradas |
| LIN-02 | Proton por jogo | Eixos completos e efeitos observados; versão registrada |
| WIN-01 | Driver Logitech selecionado | Associação e funcionamento demonstrados, não só nome no painel |
| WIN-02 | DirectInput/FFB | Entrada, criação/atualização/parada dos efeitos necessários |
| WIN-03 | Cancelamento e PnP/power | Sem falha kernel, fuga de objetos ou espera sem limite |
| WIN-04 | Assinatura/instalação/desinstalação | Procedimento de distribuição reproduzível para SO alvo |
| FFB-01 | Download/play/stop/refresh | Mesma ordem e estado de slots do caminho existente |
| FFB-02 | Constante/spring/damper/variável | Conversão compatível ou limitação explícita da referência |
| FFB-03 | Ganho/inversão e saturação | Escala correta e limites verificados em ambos os sentidos |
| FFB-04 | Range e LEDs | Reconhecimento não confundido com suporte no sink físico |
| FFB-05 | Jogo fecha/processo morre/motor desconecta | Parada/recuperação comprovadas ou bloqueio de lançamento |
| CFG-01 | XML existente | Mesmo mapeamento físico, sem migração obrigatória |
| CFG-02 | Dispositivo virtual reaparece como input | Excluído pela identidade da sessão, sem excluir G27 físico |
| CFG-03 | Entradas duplicadas no jogo | Estratégia documentada sem perda do acesso físico pelo GIMX |
| PERF-01 | Padrão de atualização 10 ms | Sem deriva crescente; p50/p95/p99 e máximos registrados |
| PERF-02 | Atualização 1 ms, se solicitada | Sem prometer suporte até medir filas/CPU/latência |
| SOAK-01 | 100 ciclos e sessão de 2 horas | Sem requests órfãs, filas ilimitadas ou crescimento contínuo |

Não usar o período USB de 2 ms como prova de latência ponta a ponta de 2 ms.
Definir o limite numérico de regressão após medir a referência; antes disso,
o critério é ausência de acúmulo/atraso patológico, não um número inventado.

## 5. Como obter evidências sem osciloscópio

Este desenvolvimento é majoritariamente software; não depende de reparar a UART
atual nem de comprar instrumento de bancada.

- Linux: usbmon/Wireshark ou captura equivalente para enumeração e endpoints;
  inspeção de sysfs/driver, evdev e logs do backend.
- Windows: USBPcap/Wireshark quando aplicáveis à topologia; tracing WDF/ETW e
  logs de URBs do próprio backend UDE. Confirmar cobertura da captura no host
  virtual, sem pressupor que a ferramenta veja toda topologia.
- Replay: alimentar relatórios IN e comandos OUT conhecidos sem dispositivos
  físicos. Comparar bytes e eventos traduzidos, não screenshots de reconhecimento.
- Descritores: script Python fornecido, sem conexão ao hardware.

Captura da placa atual é suplementar. Como há instabilidade e versão não
confirmada, preservar bruto, marcar sessão/perfil e não copiar automaticamente
timeouts ocasionais como comportamento obrigatório da emulação.

## 6. Formato de registro por execução

```text
ID de teste:
Data e commit GIMX / backend:
Perfil de firmware e hash do descritor:
SO / kernel / driver / arquitetura:
Proton / Steam Input / jogo e versão:
Dispositivos físicos e versão OpenFFBoard:
XML (hash, sem publicar dados pessoais):
Passos / resultado esperado / resultado observado:
Captura USB / log de transferências / efeitos:
Métricas e incidentes:
Estado: PASS / FAIL / BLOCKED / NOT RUN
```

Não commitar dumps com identificadores pessoais, caminhos de usuário ou tráfego
de outros dispositivos sem revisão. Fixtures pequenas e sanitizadas devem
conter fonte, perfil, licença/proveniência e resultado esperado.

## 7. Registro de riscos

| Risco | Impacto | Redução/decisão |
|---|---|---|
| UHID não aciona driver Logitech | Sem FFB equivalente | USB virtual real na pilha, validar Gate A |
| Driver proprietário exige comportamento adicional | Windows incompleto | Trace de init/feature/OUT, prova Windows cedo |
| Firmware “5.8” inferido incorretamente | Perfil de referência errado | Dois snapshots explícitos; log não é identificação definitiva |
| Diferença HID 108/133 bytes | Botões e câmbio diferentes | Fixtures separadas; não misturar perfis |
| Feature declarado sem handler completo | Timeouts/overflow ao copiar ingenuamente | Validar limites, mapear referência e requests reais |
| GIMX lê a própria saída | Loop ou duplicação | Identidade de sessão e fontes físicas preservadas |
| Cleanup não para motor | Força residual | Testar watchdog/supervisão antes de homologar |
| USB/IP adiciona atraso | Direção/FFB degradados | Medir filas e latência, alternativa dummy_hcd condicionada |
| Driver Windows sem assinatura distribuível | Instalação inviável | Tratar assinatura/instalador como entrega, não pós-projeto |
| Parser haptic assume tamanho válido | Leitura fora de limites | Validação de payload no novo ponto de entrada |
| Driver alternativo do Linux | Diferenças de efeitos/quirks | Registrar driver real por execução |

## 8. Backlog inicial, em ordem

1. Criar fixtures dos dois perfis e um oráculo de relatórios G27 do construtor atual.
2. Completar tabela de setup requests e limites da LUFA para cada perfil.
3. Provar enumeração Linux USB/IP/VHCI, sem motor e sem alterar o XML.
4. Provar enumeração Windows UDE e associação do driver esperado.
5. Revisar o contrato comum com as diferenças encontradas nas duas provas.
6. Integrar report builder/config e exclusão da saída virtual.
7. Integrar OUT/FFB, validação de tamanho e parada explícita.
8. Executar falhas e concorrência antes de sessões com força normal.
9. Integrar launcher, pacotes e diagnósticos.
10. Homologar jogos/Proton/Windows e publicar somente o suporte observado.

O levantamento não autoriza implicitamente instalação de driver, mudanças no
kernel, atualização de firmware, commit ou push. Esses atos pertencem à etapa
de implementação, conforme o trabalho solicitado e as permissões do ambiente.
