# Arquitetura proposta — Linux e Windows

Estado: decisões de planejamento, sujeitas às provas descritas no
[plano de validação](plano-validacao.md). A [referência EMUG27](protocolo-emug27.md)
define o comportamento; os mecanismos abaixo precisam demonstrar equivalência.

## 1. Critério de escolha

Exigência: substituição virtual do adaptador GIMX/EMUG27, mantendo entrada,
retorno de força e compatibilidade com o caminho do driver de volante. Não
reduzir o escopo para gamepad, XInput ou joystick apenas com eixos equivalentes.

Existem três níveis de equivalência, a registrar separadamente:

1. **Funcional:** mesmos controles/efeitos observáveis no jogo.
2. **HID:** mesmos descritores e relatórios, incluindo OUT/feature.
3. **USB/driver:** device/configuration/interface/endpoints e comportamento
   suficientes para que a pilha e os drivers existentes operem como na referência.

O objetivo inclui os três níveis nos fluxos utilizados. Não exige simular
eletricamente os fios ou conservar a taxa serial. Comparação byte a byte de
eventos determinísticos e traces USB deve comprovar o que é equivalente.

## 2. Matriz de tecnologias

| Mecanismo | Entrada | Retorno | Topologia USB equivalente | Posição no plano |
|---|---|---|---|---|
| Linux uinput | Sim, eventos input | FF exige implementação de upload/erase/play | Não | Fora da linha principal; alternativa funcional só com mudança explícita de escopo |
| Linux UHID | Sim, relatórios HID | OUTPUT/GET_REPORT/SET_REPORT em userspace | Não cria interface/dispositivo USB pai | Não atende sozinho ao driver Logitech consultado |
| Linux USB/IP + VHCI | Dispositivo USB importado pelo host virtual | URBs IN/OUT/control | Candidato adequado | Primeira prova Linux |
| Linux dummy_hcd + gadget/Raw Gadget | Dispositivo entre host e UDC virtuais | Control e endpoints, conforme implementação | Candidato adequado | Alternativa se USB/IP inviável no kernel alvo |
| Windows VHF | HID virtual | Callbacks de relatórios | Não emula USB completo | Não assumir compatibilidade com driver Logitech |
| Windows UDE/UdeCx | USB virtual via driver KMDF | Endpoints/control/filas WDF | Candidato adequado | Primeira prova Windows |

Fontes: [uinput](https://docs.kernel.org/input/uinput.html),
[UHID](https://docs.kernel.org/hid/uhid.html),
[USB/IP](https://docs.kernel.org/usb/usbip_protocol.html),
[Raw Gadget](https://docs.kernel.org/usb/raw-gadget.html),
[VHF](https://learn.microsoft.com/en-us/windows-hardware/drivers/hid/virtual-hid-framework--vhf-),
[UDE](https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/usb-emulated-device--ude--architecture).

### Por que não basta UHID com VID/PID Logitech

No Linux v6.12, `lg_probe()` em `hid-lg.c` rejeita dispositivos que não passem
`hid_is_usb()` e converte o pai em uma `usb_interface`. Em `lg4ff_init()`,
`hid-lg4ff.c` acessa o descritor do dispositivo USB e `bcdDevice`.

UHID cria objetos HID sem esse transporte USB completo. Alterar só o campo bus
para USB não cria os objetos pai que o driver espera. Forçar associação dessa
forma não é uma solução de projeto e pode produzir acessos inválidos dependendo
da versão do kernel. A biblioteca `gimxuhid` atual ainda usa BUS_VIRTUAL, altera
usages e ignora OUTPUT; ela não é um backend G27 pronto.

Referências fixadas: [hid-lg.c v6.12](https://github.com/torvalds/linux/blob/v6.12/drivers/hid/hid-lg.c),
[hid-lg4ff.c v6.12](https://github.com/torvalds/linux/blob/v6.12/drivers/hid/hid-lg4ff.c).
A prova deve verificar o kernel real e eventuais drivers alternativos instalados.

## 3. Organização compartilhada proposta

```text
Entradas físicas → gimxinput/config XML → g27 report builder
                                            ↓ input de 11 bytes
                             núcleo de emulação EMUG27
                                ↙                  ↘
                       backend Linux          backend Windows
                       USB/IP + VHCI          driver UDE + ponte
                                ↘                  ↙
                             host USB / driver G27
                                        ↕
                         Linux/Proton ou jogo Windows

OUT de 7 bytes → validação → haptic_source_lg → haptic_core/tweaks
               → sink físico escolhido pela configuração
```

Separar o perfil de dispositivo das APIs de cada sistema. Não colocar structs
WDF, UHID ou Linux input no contrato comum. O núcleo reaproveita C/C++ e não
depende do launcher para funcionar.

Estrutura candidata, ainda não criada:

```text
shared/gimxvirtual/          perfil, descritores, estado e filas
core/connectors/virtual.*   integração ao adapter/controller existente
virtual/linux/              servidor USB/IP local e attach/detach
virtual/windows/driver/     KMDF/UDE, INF e integração de build
virtual/windows/service/    ponte de IPC para GIMX
tests/virtual/              fixtures, replay e verificação de protocolo
```

Avaliar biblioteca local antes de criar novo submódulo; não multiplicar
repositórios durante a prova. Não mover código de haptics sem necessidade.

## 4. Contrato comum: representar o adaptador, não redesenhar o volante

O perfil contém bytes exatos dos descritores da referência, VID/PID/bcdDevice,
endpoints, limites e políticas de requisições USB versionadas.

Operações conceituais, não uma API/ABI final:

| Operação | Responsabilidade |
|---|---|
| `create(profile)` | Validar perfil e reservar recursos sem acionar força |
| `start()` | Permitir publicação e enumeração do dispositivo |
| `submit_input(bytes, length)` | Aceitar relatório de 11 bytes validado |
| `handle_setup(setup8, data)` | Classificar transferência control, retornar resultado ou pendência |
| `take_output()` | Entregar relatório OUT íntegro e ordenado ao haptic core |
| `complete_transfer(id, status, data)` | Concluir uma transferência exatamente uma vez |
| `reset(reason)` | Limpar filas/estado e executar ciclo equivalente do perfil |
| `stop()` / `destroy()` | Parar efeitos, cancelar transferências e remover dispositivo |
| `get_status()` | Informar publicação, configuração, falha, filas e métricas |

Identificador de transferência, geração de sessão, comprimentos, direção,
endpoint, timestamp monotônico e status são explícitos. Nunca transportar
ponteiros entre processos nem structs C com padding como protocolo de IPC.

Payloads de controle, interrupt e mensagens internas são categorias distintas.
O limite de 64 bytes encontrado no firmware não deve truncar silenciosamente
um feature anunciado de 144 bytes. A implementação deve ter limites próprios
verificados e política explícita por requisição.

Modelo de concorrência: um proprietário do estado do perfil; callbacks do
backend enfileiram eventos. O loop do GIMX não pode bloquear esperando uma URB
IN do jogo ou um cliente de IPC. A conclusão de transferências pertence ao
backend. Atualizações de estado IN podem usar último estado disponível quando
permitido pela referência; comandos FFB/STOP/control não podem ser descartados
ou reordenados como se fossem posições de eixo.

## 5. Linux: primeira prova com USB/IP em loopback

### Componentes

1. Servidor userspace de dispositivo USB emulado, com bind somente em loopback.
2. Implementação do protocolo USB/IP para anunciar/importar o dispositivo e
   receber SUBMIT/UNLINK; não confundir com `usbip-host`, que exporta hardware real.
3. Controlador virtual `vhci_hcd` importando esse dispositivo.
4. Pilha USB/HID Logitech existente no kernel e aplicações Linux/Proton.
5. Integração local ao GIMX por chamada de biblioteca ou IPC restrito.

Não basta executar `usbip bind` em um dispositivo inexistente. Será necessário
implementar ou integrar um servidor emulador, avaliar licença/manutenção e
validar sua compatibilidade. USB/IP transporta URBs; ele não contém o protocolo
Logitech nem gera o descritor G27 por conta própria.

### Trabalho específico

- Verificar disponibilidade de VHCI/USB-IP e ferramentas no kernel/Arch alvo.
- Enumerar device/config/string/HID/report e concluir EP0 corretamente.
- Preservar características full-speed, endpoints 81/02 e packet sizes.
- Implementar URBs IN pendentes, OUT, cancelamento e status de erro.
- Confirmar associação de `hid-logitech` e inicialização do FFB.
- Registrar o caminho real de entrada usado pelo Proton: evdev, hidraw e/ou
  outras camadas, conforme versão e jogo. Não presumir driver Windows Logitech
  carregado dentro do Proton nem que seu instalador resolverá isso.
- Avaliar Steam Input por jogo; registrar estado nos resultados, sem desativação
  global automática.
- Restringir attach/detach privilegiado a um helper pequeno; processo principal
  e GUI continuam como usuário normal. Não publicar a emulação na LAN.

USB/IP em loopback adiciona filas e cópias: medir, não prometer menor latência.
Se a disponibilidade de VHCI ou a fidelidade de endpoints falhar, testar
`dummy_hcd` com gadget/Raw Gadget. A documentação de Raw Gadget o trata como
interface de baixo nível para desenvolvimento/teste: isso requer avaliação
adicional para distribuição, não é uma troca sem custo.

## 6. Windows: prova UDE desde o primeiro ciclo

UDE oferece a emulação de host/device USB por driver KMDF integrado a UdeCx.
O driver cria o dispositivo/endpoints e atende callbacks; um processo/serviço
transfere estados e comandos entre GIMX e o driver. A lógica de mapeamento e
tradução de efeitos deve permanecer em userspace sempre que possível.

### Fronteira kernel/userspace

- Driver: objetos USB, filas, cancelamento, conclusão de requests, PnP/power,
  buffers validados, remoção surpresa e controle de acesso ao canal.
- Serviço/ponte: sessão, heartbeat, registros, IPC versionado e entrega ao GIMX.
- GIMX: XML, estado de controles, construção G27 e efeitos físicos.

Se o serviço morrer, o driver não pode deixar solicitações presas esperando
indefinidamente. Precisa cancelar/concluir ou retirar o dispositivo conforme
estado, sem acessar buffers de processos encerrados. Validar tamanhos no driver
mesmo que o serviço já os tenha validado.

### Validação obrigatória

1. Enumerar e identificar qual driver Windows realmente se associa ao dispositivo.
2. Instalar separadamente a versão escolhida do software Logitech para teste.
3. Validar DirectInput/FFB e quaisquer requisições específicas recebidas.
4. Testar reset, suspensão, remoção e reinstalação sem dispositivos órfãos.
5. Rodar verificações de driver em ambiente de teste e confirmar política de
   assinatura/distribuição para Windows alvo.

Usar UDE não garante que qualquer versão do driver Logitech aceite o dispositivo.
Compatibilidade com seu pacote proprietário, arquitetura x64, Secure Boot e
integridade de memória é pendência de execução. Não distribuir binários do
driver Logitech dentro do projeto por conveniência.

Assinatura de desenvolvimento e assinatura de distribuição são trabalhos
distintos. Não propor desativar permanentemente proteções do sistema como
procedimento de instalação. [Política Microsoft](https://learn.microsoft.com/en-us/windows-hardware/drivers/install/kernel-mode-code-signing-policy--windows-vista-and-later-).

## 7. Integração no GIMX e no config

**O config continua responsável por selecionar os controles físicos.** Não
introduzir um novo editor, copiar XML nem substituir nomes de dispositivos
automaticamente. O XML G27 existente é a configuração de referência.

Mudanças previstas:

- `core/args.c`: saída virtual explícita; sintaxe proposta
  `--virtual-adapter emug27`, a definir sem quebrar `--port` atual.
- `core/controller.h/.c`: tipo/instância de saída virtual, ciclo de vida,
  envio de relatórios e despacho de retorno. Não fingir que é uma porta serial.
- `adapter_detect()`: perfil virtual conhecido, validação do backend e handshake
  interno, sem aplicar o fallback de firmware físico à versão virtual.
- `adapter_start()`: inicializar `ff_core` também para saída virtual; hoje o
  reconhecimento do caminho GIMX depende de serial/proxy em `is_gimx_adapter()`.
- `adapter_send()`: preservar o construtor G27 e trocar só o destino.
- `adapter_clean()`: remoção e parada explícita de efeitos, inclusive falhas.
- `core/mainloop.c`: integrar eventos do backend a gpoll/fila sem espera ativa.
- `launcher/`: selecionar adaptador físico ou virtual e apresentar diagnósticos.
- `config/`: preservar funcionalidades; opcionalmente marcar dispositivos
  virtuais como saídas reservadas, sem contaminar a lista de fontes físicas.

Exclusão automática por identidade de sessão/caminho do dispositivo virtual,
não por comparação genérica de VID/PID: um G27 físico legítimo pode estar conectado.
Evitar índices instáveis após enumeração; revisar correspondência nome/ordinal
das entradas físicas antes/depois de criar o virtual.

O XML não impede que o próprio jogo abra também os controles físicos. Resolver
entrada duplicada por configuração do jogo e, se necessário, uma estratégia de
ocultação/grab específica de plataforma. Não prometer que o config esconde
globalmente dispositivos do sistema. Qualquer ocultação deve preservar o
acesso do GIMX ao OpenFFBoard e ao caminho de force feedback.

## 8. O protocolo serial será conservado?

O núcleo de referência pode ter um adaptador opcional do enquadramento serial
para replay/testes, preservando TYPE/START/RESET/IN/OUT. Isso ajuda a comparar o
comportamento existente sem exigir COM virtual nem pseudo-TTY em produção.

Decisão proposta: integração direta por operações do backend na execução normal;
shim serial apenas como ferramenta de compatibilidade. Se o shim for adotado,
não anunciar baudrates/versões fictícias como se fossem hardware validado.

## 9. Falhas, força e instalação

Estados de sessão possuem geração para rejeitar respostas antigas após reset.
Métricas: IN enviados, OUT recebidos, bytes inválidos, filas, descartes de estado,
tempo até conclusão e desconexões. Log distingue erro USB, IPC e haptics físico.

Proposta de segurança operacional: força inicial zero, ganho limitado em teste,
STOP em encerramento normal/falha detectada, watchdog no caminho que efetivamente
consegue parar os efeitos. Um processo morto por SIGKILL não executa cleanup;
`haptic_core_clean()` e `haptic_sink_os_clean()` atuais não provam parada de motor.
Não declarar fail-safe até testar o comportamento físico/driver após perda do
processo e definir supervisão e suporte de watchdog do OpenFFBoard.

Arch: pacote com backend/helper e dependências efetivas, regras/grupo dedicados
se necessários, sem setuid amplo e sem daemon em rede exposto. Windows: pacote
driver/serviço com desinstalação e assinatura previstas. A instalação do driver
Logitech permanece separada, conforme licença e necessidade homologada.
